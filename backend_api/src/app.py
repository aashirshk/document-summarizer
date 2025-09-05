# ######## app.py #######
import asyncio
import json
import os
import shutil
import threading
import uuid
import logging
from typing import Dict, Any, List, Tuple

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from src.models import QueryRequest, QueryMultiRequest
from src.pdf_processor import ImprovedPDFProcessor
from src.rag_system import rag_system
from PyPDF2 import PdfReader


# ---------- logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("app")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # your React app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Progress store (in-memory) ------------------
PROGRESS: Dict[str, Dict[str, Any]] = {}
PROGRESS_LOCK = threading.Lock()


def _set_progress(job_id: str, **kwargs):
    with PROGRESS_LOCK:
        state = PROGRESS.get(
            job_id,
            {"stage": "queued", "progress": 0, "message": "", "done": False, "error": None},
        )
        state.update(kwargs)
        PROGRESS[job_id] = state
    log.info(f"[{job_id}] {state.get('stage')} {state.get('progress')}% - {state.get('message')}")

def _sse_pack(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ------------------ Background job (threaded) ------------------
def process_job(tmp_path: str, filename: str, job_id: str):
    """
    Same pipeline, but with granular progress updates:
      - Reading PDF (page by page) → 5%..30%
      - Chunking → 35%
      - Embedding/Indexing (per batch) → 50%..95%
      - Done → 100%
    """
    try:
        log.info(f"[{job_id}] starting job for {filename}")
        _set_progress(job_id, stage="extracting", progress=5, message="Reading PDF")

        reader = PdfReader(tmp_path)
        total_pages = len(reader.pages) or 1

        texts = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                txt = page.extract_text() or ""
            except Exception as e:
                log.warning(f"[{job_id}] extract_text error on page {i}: {e}")
                txt = ""
            texts.append(txt)
            pct = 5 + int((i / total_pages) * 25)  # 5 → 30
            _set_progress(job_id, stage="extracting", progress=min(pct, 30),
                          message=f"Reading PDF ({i}/{total_pages})")

        text = "\n".join(texts)
        if not text.strip():
            _set_progress(job_id, error="No text found in PDF.", done=True, stage="error", progress=100)
            return

        _set_progress(job_id, stage="chunking", progress=35, message="Creating chunks")
        processor = ImprovedPDFProcessor()
        chunks = processor.create_chunks(text, filename)

        _set_progress(job_id, stage="embedding", progress=50, message=f"Embedding {len(chunks)} chunks")

        def _emb_progress(batch_idx: int, total_batches: int):
            pct = 50 + int((batch_idx / max(1, total_batches)) * 45)  # 50 → 95
            _set_progress(job_id, stage="embedding", progress=min(pct, 95),
                          message=f"Embedding & indexing ({batch_idx}/{total_batches})")

        processed = rag_system.add_documents(chunks, on_progress=_emb_progress)

        _set_progress(job_id, stage="done", progress=100,
                      message=f"Indexed {processed} chunks", done=True)
        log.info(f"[{job_id}] done: {processed} chunks")

    except Exception as e:
        log.exception(f"[{job_id}] job failed")
        _set_progress(job_id, error=str(e), stage="error", progress=100, done=True)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

def process_multi_job(file_paths: List[Tuple[str, str]], job_id: str):
    """
    Processes multiple PDFs in one unified job.
    file_paths: list of (tmp_path, filename)
    Progress mapping (per total workflow):
      - Reading all PDFs → 5%..35%
      - Chunking all → 35%..50%
      - Embedding all → 50%..95%
      - Done → 100%
    """
    try:
        processor = ImprovedPDFProcessor()
        all_chunks = []
        total_files = len(file_paths) or 1

        # ---------- Read phase (accumulate text) ----------
        _set_progress(job_id, stage="extracting", progress=5, message=f"Reading {total_files} PDFs")
        for f_idx, (tmp_path, filename) in enumerate(file_paths, start=1):
            try:
                reader = PdfReader(tmp_path)
                pages = reader.pages
                total_pages = len(pages) or 1
                texts = []
                for p_idx, page in enumerate(pages, start=1):
                    try:
                        txt = page.extract_text() or ""
                    except Exception as e:
                        log.warning(f"[{job_id}] extract_text error {filename} p{p_idx}: {e}")
                        txt = ""
                    texts.append(txt)

                    # Progress within read phase: 5 → 35
                    overall_read_frac = ((f_idx - 1) + (p_idx / total_pages)) / max(1, total_files)
                    pct = 5 + int(overall_read_frac * 30)
                    _set_progress(job_id, stage="extracting", progress=min(pct, 35),
                                  message=f"Reading {filename} ({p_idx}/{total_pages})")
                text = "\n".join(texts)
                if not text.strip():
                    log.warning(f"[{job_id}] {filename}: No extractable text")
                    continue

                # ---------- Chunk phase (build chunks per file) ----------
                _set_progress(job_id, stage="chunking", progress=35, message=f"Chunking {filename}")
                chunks = processor.create_chunks(text, filename)
                all_chunks.extend(chunks)

            finally:
                # cleanup temp file
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        if not all_chunks:
            _set_progress(job_id, error="No text found in uploaded PDFs.", done=True, stage="error", progress=100)
            return

        # ---------- Embed/index all chunks ----------
        _set_progress(job_id, stage="embedding", progress=50, message=f"Embedding {len(all_chunks)} chunks")

        def _emb_progress(batch_idx: int, total_batches: int):
            pct = 50 + int((batch_idx / max(1, total_batches)) * 45)  # 50 → 95
            _set_progress(job_id, stage="embedding", progress=min(pct, 95),
                          message=f"Embedding & indexing ({batch_idx}/{total_batches})")

        processed = rag_system.add_documents(all_chunks, on_progress=_emb_progress)

        _set_progress(job_id, stage="done", progress=100,
                      message=f"Indexed {processed} chunks from {total_files} files", done=True)
        log.info(f"[{job_id}] multi done: {processed} chunks from {total_files} files")

    except Exception as e:
        log.exception(f"[{job_id}] multi job failed")
        _set_progress(job_id, error=str(e), stage="error", progress=100, done=True)

# ------------------ Endpoints ------------------

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Accept a PDF, save to /tmp, start threaded processing, return jobId immediately.
    """
    job_id = str(uuid.uuid4())
    _set_progress(job_id, stage="queued", progress=0, message="Queued", done=False, error=None)

    tmp_dir = os.path.join("/tmp", "docs")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f"{job_id}_{file.filename}")
    with open(tmp_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    t = threading.Thread(target=process_job, args=(tmp_path, file.filename, job_id), daemon=True)
    t.start()

    return {"jobId": job_id, "filename": file.filename}

@app.post("/upload_multi")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Accept multiple PDFs, save to /tmp, start a unified threaded processing job,
    return one jobId.
    """
    job_id = str(uuid.uuid4())
    _set_progress(job_id, stage="queued", progress=0, message="Queued", done=False, error=None)

    tmp_dir = os.path.join("/tmp", "docs")
    os.makedirs(tmp_dir, exist_ok=True)

    file_paths: List[Tuple[str, str]] = []
    for uf in files:
        tmp_path = os.path.join(tmp_dir, f"{job_id}_{uf.filename}")
        with open(tmp_path, "wb") as out:
            shutil.copyfileobj(uf.file, out)
        file_paths.append((tmp_path, uf.filename))

    t = threading.Thread(target=process_multi_job, args=(file_paths, job_id), daemon=True)
    t.start()

    return {"jobId": job_id, "filenames": [f for _, f in file_paths]}

@app.get("/progress")
async def progress(jobId: str):
    """
    Server-Sent Events stream. Emits JSON objects as `data: {...}\n\n`.
    """
    if jobId not in PROGRESS:
        async def one():
            yield _sse_pack({"error": "unknown jobId", "done": True})
        return StreamingResponse(one(), media_type="text/event-stream")

    async def event_stream():
        last = None
        while True:
            state = PROGRESS.get(jobId)
            if state is None:
                yield _sse_pack({"error": "job removed", "done": True})
                break

            if state != last:
                yield _sse_pack(state)
                last = state
                if state.get("done"):
                    break

            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ---------- JSON polling fallback (use this if SSE still freezes) ----------
@app.get("/progress_json")
def progress_json(jobId: str):
    state = PROGRESS.get(jobId)
    if not state:
        return JSONResponse({"error": "unknown jobId", "done": True})
    return JSONResponse(state)


@app.post("/query")
async def query_documents(req: QueryRequest):
    results = rag_system.query_documents(req.question, req.n_results)
    docs = results.get("documents", [[]])[0]
    answer = rag_system.generate_response(req.question, docs[0] if docs else "")
    return {"answer": answer, "sources": docs}

@app.post("/query_multi")
async def query_documents_multi(req: QueryMultiRequest):
    """
    Retrieve top-K passages across *all* indexed PDFs and synthesize one coherent paragraph.
    """
    top_passages = rag_system.query_documents_multi(req.question, n_results=req.n_results)
    out = rag_system.generate_response_multi(
        query=req.question,
        passages=top_passages,
        max_context_chars=req.max_context_chars,
        dedupe_by_source=req.dedupe_by_source,
    )
    return out