# pdf_sum_v2.py (updated, generic ULTRAFAST + packed embed cache + section bias)
from __future__ import annotations
import os, re, json, textwrap, unicodedata, hashlib, pathlib, math
from typing import Optional, List, Dict, Any

import requests
from pypdf import PdfReader

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

# Optional transformers backend
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
except Exception:
    torch = None
    AutoTokenizer = None
    AutoModelForCausalLM = None

# Optional sentence-transformers (for embeddings with HF)
try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    SentenceTransformer = None  # type: ignore

# ---------- disk caches ----------
_CACHE_DIR = pathlib.Path(".pdfsum_cache")              # Stage-1 LLM extracts
_EMBED_CACHE_DIR = pathlib.Path(".pdfsum_embed_cache")  # Embeddings per-PDF (packed)
_CACHE_DIR.mkdir(exist_ok=True)
_EMBED_CACHE_DIR.mkdir(exist_ok=True)

def _cache_key(*parts: str) -> str:
    return hashlib.sha1(("␞".join(parts)).encode("utf-8")).hexdigest()

# ---------- PDF cleaning ----------
_LIGS = {"ﬁ":"fi","ﬂ":"fl","ﬃ":"ffi","ﬄ":"ffl","ﬀ":"ff","ﬅ":"ft","ﬆ":"st"}

def _fix_small_caps(s: str) -> str:
    s = re.sub(r"([A-Za-z])\.(?:sc|smcp)\b", lambda m: m.group(1).upper(), s)
    s = re.sub(r"(?<=\w)/(?!/)(?=\w)", "", s)
    return s

def _fix_ligs(s: str) -> str:
    for k,v in _LIGS.items():
        s = s.replace(k,v)
    return s

def _norm_newlines_hyphens(s: str) -> str:
    s = s.replace("\r\n","\n").replace("\r","\n").replace("\u00AD","")
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
    return s

def _norm_ws(s: str) -> str:
    lines = [ln.strip() for ln in s.split("\n")]
    lines = [ln for ln in lines if ln]
    s = "\n".join(lines)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()

def _fix_pdf_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = _fix_ligs(s)
    s = _fix_small_caps(s)
    s = _norm_newlines_hyphens(s)
    s = _norm_ws(s)
    return s

def _prune_backmatter(s: str) -> str:
    m = re.search(r"\n\s*(references|bibliography|appendix|acknowledg(e)?ments)\b.*", s, re.I)
    return s[:m.start()] if m else s

# ---------- main class ----------
class PDFSummarizer:
    """
    backends:
      - "ollama": quantized local models via Ollama (e.g., mistral:instruct)
      - "transformers": HF transformers (heavier; needs GPU/MPS for speed)

    Features:
      - Section-aware chunking + overlap
      - RAG with Abstract/Results bias + section penalty for "Related Work"
      - Packed embedding cache (one JSON per PDF+settings)
      - Optional verification pass (verify=True)
      - Generic, context-aware ULTRAFAST summarization prompt
    """

    def __init__(
        self,
        backend: str,
        model: str,
        # Ollama
        ollama_url: str = "http://127.0.0.1:11434",
        ollama_options: Optional[Dict[str, Any]] = None,
        merge_model: Optional[str] = None,
        single_call_model: Optional[str] = None,
        ultra_head_chars: int = 4000,
        ultra_tail_chars: int = 1200,

        # Embeddings (RAG)
        use_rag: bool = True,
        embed_backend: str = "ollama",            # "ollama" or "sentence-transformers"
        embed_model: str = "nomic-embed-text",
        rag_topk: int = 40,
        rag_mmr_lambda: float = 0.8,

        # Chunking extras
        overlap_chars: int = 420,
        section_weighting: bool = True,

        # Transformers backend (optional)
        device: Optional[str] = None,
        dtype: str = "float16",
        max_new_tokens: int = 128,
        stream: bool = False,
    ):
        self.backend = backend.lower()
        self.model = model
        self.merge_model = merge_model
        self.single_call_model = single_call_model
        self.ultra_head_chars = ultra_head_chars
        self.ultra_tail_chars = ultra_tail_chars

        # RAG config
        self.use_rag = bool(use_rag)
        self.embed_backend = embed_backend.lower().strip()
        self.embed_model = embed_model
        self.rag_topk = int(rag_topk)
        self.rag_mmr_lambda = float(rag_mmr_lambda)

        # Chunking config
        self.overlap_chars = int(overlap_chars)
        self.section_weighting = bool(section_weighting)

        self.max_new_tokens = max_new_tokens
        self.stream = stream

        if self.backend == "ollama":
            self.ollama_url = ollama_url.rstrip("/")
            self.ollama_options = {
                "num_ctx": 2048,
                "num_batch": 256,
                "temperature": 0.0,
                "top_p": 0.9,
                "repeat_penalty": 1.05,
                "keep_alive": "15m",
            }
            if ollama_options:
                self.ollama_options.update(ollama_options)

        elif self.backend == "transformers":
            if AutoTokenizer is None:
                raise RuntimeError("Transformers backend selected but transformers/torch not installed.")
            self.device = device or ("mps" if (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) else "cpu")
            torch_dtype = torch.float16 if dtype == "float16" else torch.float32
            token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
            hub = {"token": token} if token else {}
            print(f"Loading {self.model} on {self.device} …")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model, use_fast=True, **hub)
            if self.tokenizer.pad_token_id is None and self.tokenizer.eos_token_id is not None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            self.model_hf = AutoModelForCausalLM.from_pretrained(
                self.model, torch_dtype=torch_dtype, low_cpu_mem_usage=True, **hub
            ).to(self.device)
            self.gen_kwargs = dict(
                max_new_tokens=max_new_tokens, temperature=0.2, top_p=0.95, do_sample=False,
                pad_token_id=self.tokenizer.pad_token_id, eos_token_id=self.tokenizer.eos_token_id
            )
            print("✅ transformers model ready.")
        else:
            raise ValueError("backend must be 'ollama' or 'transformers'")

        # Sentence-Transformers model holder (lazy)
        self._st = None

    # ---------- public API ----------
    def summarize(
        self,
        pdf_path: str,
        chunk_chars: int = 3200,
        group_size: int = 16,
        stream_final: bool | None = None,
        skip_backmatter: bool = True,
        group_num_tokens: int = 110,
        final_num_tokens: int = 520,
        target_sentences: tuple[int, int] = (6, 7),
        fast: bool = False,
        verify: bool = False,
    ) -> str:
        """
        Two-stage pipeline with RAG pre-filter:
        1) Chunk -> (RAG select top-k) -> Stage-1 extract (2–3 lines per group)
        2) Stage-2 merge into ONE paragraph; enforce 6–7 sentences

        ULTRAFAST: if group_size <= 0 → single call (uses single_call_model if provided)
        """
        if stream_final is None:
            stream_final = self.stream

        text = self._extract_pdf_text(pdf_path, skip_backmatter=skip_backmatter)

        # ----- ULTRAFAST: single-call summarize -----
        if group_size <= 0:
            print(">> ULTRAFAST path (single LLM call). No Stage-1/2.", flush=True)
            skim = self._skim_sections(
                text, head_chars=self.ultra_head_chars, tail_chars=self.ultra_tail_chars
            )
            instr = (
                f"Summarize the following scientific text into ONE cohesive paragraph of "
                f"{target_sentences[0]}–{target_sentences[1]} sentences. "
                "Focus ONLY on this paper, not on general background or unrelated work. "
                "Be precise about key aspects such as: the research problem/goal; the proposed method "
                "(e.g., model/algorithm/framework); important datasets/resources; main results/metrics/"
                "comparisons; and any strengths/limitations/caveats discussed. "
                "Do NOT list unrelated prior-work models unless the paper reports direct results on them. "
                "Do not invent datasets, metrics, or years—include them only if explicitly present. "
                "Write one clear paragraph (no bullet points, no prefaces, no headings)."
            )
            prompt = self._wrap_inst(f"{instr}\n\n[Text]\n{skim}\n\n[Paragraph]:")
            out = self._ollama_generate(
                prompt,
                stream=False,
                override_num_predict=min(final_num_tokens, 200),
                use_model=(self.single_call_model or self.model),
            )
            para = re.sub(r"\s*\n+\s*", " ", out).strip()
            para = self._complete_last_sentence(para, num_tokens=32)
            return re.sub(r"\s*\n{2,}\s*", " ", para).strip()

        # ---------- RAG pre-filter ----------
        chunks_all = self._chunk_text(text, chunk_chars, overlap=self.overlap_chars)
        if self.use_rag and len(chunks_all) > self.rag_topk:
            print(f"Building RAG index on {len(chunks_all)} chunks …")
            selected_chunks = self._rag_select_chunks(pdf_path, chunks_all, top_k=self.rag_topk)
        else:
            selected_chunks = chunks_all

        # ---------- two-stage presets (FAST tuning) ----------
        merge_tier_size = 12
        final_tokens_for_merge = final_num_tokens
        lines_per_group = 3
        if fast:
            chunk_chars = max(chunk_chars, 5200)
            group_size  = max(group_size, 24)
            group_num_tokens = min(group_num_tokens, 96)
            lines_per_group = 2
            merge_tier_size = 24
            final_tokens_for_merge = min(final_num_tokens, 380)

        # ---------- Stage-1 + Stage-2 ----------
        groups = self._group_chunks(selected_chunks, group_size)
        total = len(groups)
        print(f"Preparing summary… {len(selected_chunks)} chunks → {total} groups.\n")

        partials: list[str] = []
        iterator = tqdm(groups, desc="Extracting key sentences", unit="grp", dynamic_ncols=True) if tqdm else groups

        instr_stage1 = (
            "From EACH section below, extract 2–3 sentences that capture core facts about THIS PAPER "
            "(goal, method, data/resources, and results). Use ONLY information explicitly present. "
            "Do NOT describe generic background or prior work unless the paper reports direct experimental results on it. "
            "Never invent datasets, model names, or numbers. Each sentence must be ≤ 30 words. "
            "Output raw sentences only, one per line, in order."
        )

        for i, group in enumerate(iterator, 1):
            content = "\n\n".join(f"[Section {k+1}]\n{sec}" for k, sec in enumerate(group))
            prompt = self._wrap_inst(f"{instr_stage1}\n\n{content}\n\n[Sentences]:")

            key = _cache_key(self.model, prompt)
            cache_path = _CACHE_DIR / f"{key}.txt"
            if cache_path.exists():
                part = cache_path.read_text(encoding="utf-8")
            else:
                part = self._ollama_generate(prompt, stream=False, override_num_predict=min(group_num_tokens, 128))
                cache_path.write_text(part, encoding="utf-8")

            lines = [ln.strip() for ln in part.strip().splitlines() if ln.strip()]
            partials.append("\n".join(lines[:lines_per_group]))

        # ---- Stage 2: merge ----
        key_sentences = [p for p in partials if p]
        print("\nMerging partial summaries…", flush=True)
        final = self._tiered_merge(
            key_sentences,
            tier_size=merge_tier_size,
            num_tokens=final_tokens_for_merge,
            target_range=target_sentences,
            soft_tolerance=fast,
        )
        print("Merge complete.", flush=True)

        if verify:
            evidence = "\n".join(key_sentences)
            checked = self._self_check(final, evidence)
            if checked:
                final = checked

        final = self._complete_last_sentence(final, num_tokens=48)
        return re.sub(r"\s*\n{2,}\s*", " ", final).strip()

    def ask_question(self, pdf_path: str, question: str, context_chars: int = 3500, stream: bool | None = None) -> str:
        if stream is None:
            stream = self.stream
        text = self._extract_pdf_text(pdf_path)
        context = text[:context_chars]
        prompt = self._wrap_inst(
            "Answer using ONLY the context. If the answer is not present, reply 'I don't know'. "
            "Write 3–6 complete sentences; no bullet points, no prefaces.\n\n"
            f"[Context]\n{context}\n\n[Question] {question}\n[Answer]:"
        )
        return self._ollama_generate(prompt, stream=stream, override_num_predict=220).strip()

    def generate_sample_questions(self, pdf_path: str, context_chars: int = 3500) -> list[str]:
        instr = (
            "Read the following scientific text and propose 5 natural, helpful questions "
            "that a researcher might ask to understand the paper better. "
            "Questions should be diverse (methods, results, datasets, conclusions, limitations). "
            "Output ONLY 5 numbered questions, nothing else."
        )
        context = self._extract_pdf_text(pdf_path, skip_backmatter=True)[:context_chars]
        prompt = self._wrap_inst(f"{instr}\n\n[Context]\n{context}\n\n[Questions]:")
        out = self._ollama_generate(prompt, stream=False, override_num_predict=180)
        return [q.strip(" -") for q in out.splitlines() if q.strip()]

    # ---------- RAG: embeddings + selection ----------
    def _embed_texts(self, pdf_path: str, texts: List[str]) -> List[List[float]]:
        """
        Packed cache: store embeddings for all chunks of (pdf, embed_model, chunking) in one file.
        Avoids one-file-per-chunk explosion.
        """
        # stable fingerprint for this set of chunks
        chunk_fingerprint = hashlib.sha1("".join(texts).encode("utf-8")).hexdigest()
        pack_key = _cache_key("embedpack", self.embed_backend, self.embed_model, pdf_path, chunk_fingerprint)
        pack_path = _EMBED_CACHE_DIR / f"{pack_key}.json"

        if pack_path.exists():
            data = json.loads(pack_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "embeds" in data and len(data["embeds"]) == len(texts):
                return data["embeds"]

        # compute embeddings
        use_st = (self.embed_backend == "sentence-transformers") and (SentenceTransformer is not None)
        if use_st and self._st is None:
            device = "mps" if (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) else "cpu"
            print(f"Loading sentence-transformers model '{self.embed_model}' on {device} …")
            self._st = SentenceTransformer(self.embed_model, device=device)

        embeds: List[List[float]] = []
        iterator = tqdm(range(len(texts)), desc="Embedding chunks", unit="ch", dynamic_ncols=True) \
                   if (tqdm and len(texts) > 50) else range(len(texts))
        for i in iterator:
            t = texts[i]
            if use_st:
                vec = self._st.encode([t], normalize_embeddings=True)[0].tolist()
            else:
                url = f"{self.ollama_url}/api/embeddings"
                r = requests.post(url, json={"model": self.embed_model, "prompt": t}, timeout=(10, 120))
                r.raise_for_status()
                vec = r.json().get("embedding", [])
                # normalize
                norm = math.sqrt(sum(x*x for x in vec)) or 1.0
                vec = [x / norm for x in vec]
            embeds.append(vec)

        pack_path.write_text(json.dumps({"embeds": embeds}), encoding="utf-8")
        return embeds

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        num = sum(x*y for x,y in zip(a,b))
        da = math.sqrt(sum(x*x for x in a)) or 1.0
        db = math.sqrt(sum(x*x for x in b)) or 1.0
        return num / (da * db)

    def _rag_select_chunks(self, pdf_path: str, chunks: List[str], top_k: int) -> List[str]:
        """
        Select top_k representative chunks using centroid + MMR.
        Bias toward Abstract/Intro/Methods/Results/Conclusion; penalize 'Related Work'.
        """
        embeds = self._embed_texts(pdf_path, chunks)

        # centroid query
        d = len(embeds[0])
        centroid = [0.0]*d
        for v in embeds:
            for j in range(d): centroid[j] += v[j]
        invn = 1.0 / max(1, len(embeds))
        centroid = [x*invn for x in centroid]
        cnorm = math.sqrt(sum(x*x for x in centroid)) or 1.0
        centroid = [x/cnorm for x in centroid]

        sim_q = [self._cosine(v, centroid) for v in embeds]

        # section bias
        def _section_bias(text: str) -> float:
            if re.search(r"\b(related work|background)\b", text, re.I):
                return -0.20
            if re.search(r"\b(abstract|introduction|method|methods|approach|results?|conclusion|discussion)\b", text, re.I):
                return +0.10
            return 0.0
        sim_q = [sim + _section_bias(ch) for sim, ch in zip(sim_q, chunks)]

        selected_idx: List[int] = []
        if self.section_weighting:
            for i, ch in enumerate(chunks):
                if re.search(r"\babstract\b", ch, re.I) or re.search(r"\bresults?\b", ch, re.I):
                    selected_idx.append(i)

        selected_idx = sorted(set(selected_idx))
        candidate_idx = [i for i in range(len(chunks)) if i not in selected_idx]
        lam = self.rag_mmr_lambda

        if not selected_idx and candidate_idx:
            first = max(candidate_idx, key=lambda i: sim_q[i])
            selected_idx.append(first)
            candidate_idx.remove(first)

        while len(selected_idx) < min(top_k, len(chunks)) and candidate_idx:
            def mmr_score(i: int) -> float:
                max_div = max(self._cosine(embeds[i], embeds[j]) for j in selected_idx) if selected_idx else 0.0
                return lam * sim_q[i] - (1 - lam) * max_div
            nxt = max(candidate_idx, key=mmr_score)
            selected_idx.append(nxt)
            candidate_idx.remove(nxt)

        selected_idx.sort()
        return [chunks[i] for i in selected_idx]

    # ---------- internals ----------
    def _generate(self, prompt: str, stream: bool) -> str:
        if self.backend == "ollama":
            return self._ollama_generate(prompt, stream=stream)
        return self._hf_generate(prompt)

    def _ollama_generate(
        self,
        prompt: str,
        stream: bool,
        override_num_predict: int | None = None,
        use_model: Optional[str] = None,
    ) -> str:
        url = f"{self.ollama_url}/api/generate"
        options = {**self.ollama_options, "num_predict": self.max_new_tokens}
        if override_num_predict is not None:
            options["num_predict"] = override_num_predict

        payload = {
            "model": use_model or self.model,
            "prompt": prompt,
            "stream": bool(stream),
            "options": options,
        }

        if not stream:
            r = requests.post(url, json=payload, timeout=(10, 240))
            if r.status_code == 404:
                try:
                    detail = r.json().get("error", r.text)
                except Exception:
                    detail = r.text
                raise RuntimeError(
                    f"Ollama 404 for model '{use_model or self.model}'. Detail: {detail} "
                    f"(Did you run `ollama pull {use_model or self.model}`? Is the URL {self.ollama_url} correct?)"
                )
            r.raise_for_status()
            return r.json().get("response", "").strip()

        out = []
        with requests.post(url, json=payload, stream=True, timeout=(10, 300)) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                msg = json.loads(line.decode("utf-8"))
                if "response" in msg:
                    tok = msg["response"]
                    print(tok, end="", flush=True)
                    out.append(tok)
                if msg.get("done"):
                    break
        print()
        return "".join(out).strip()

    def _hf_generate(self, prompt: str) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        if self.device != "cpu":
            inputs = {k: v.to(self.device) for k,v in inputs.items()}
        import torch as _torch
        with _torch.no_grad():
            ids = self.model_hf.generate(**inputs, **self.gen_kwargs)
        txt = self.tokenizer.decode(ids[0], skip_special_tokens=True)
        return self._strip_echo(prompt, txt)

    # ----- merge + enforcement helpers -----
    @staticmethod
    def _wrap_inst(content: str) -> str:
        return f"[INST] {content} [/INST]"

    @staticmethod
    def _strip_echo(prompt: str, generated: str) -> str:
        return generated[len(prompt):].strip() if generated.startswith(prompt) else generated

    @staticmethod
    def _count_sentences(text: str) -> int:
        s = re.split(r'(?<=[.!?])\s+', text.strip())
        return len([x for x in s if x.strip()])

    def _expand_to_target_sentences(
        self,
        paragraph: str,
        target_min: int,
        target_max: int,
        evidence: str,
        num_tokens: int,
    ) -> str:
        target_text = f"EXACTLY {target_min} sentences" if target_min == target_max else f"{target_min}–{target_max} sentences"
        instr = (
            f"Rewrite the paragraph into {target_text}, preserving meaning while adding specific details "
            f"drawn ONLY from the evidence. Plain paragraph only; no bullets or headings. Do NOT invent information."
        )
        prompt = self._wrap_inst(
            f"{instr}\n\n[Paragraph]\n{paragraph}\n\n[Evidence]\n{evidence[:6000]}\n\n[Rewritten paragraph]:"
        )
        out = self._ollama_generate(
            prompt, stream=False, override_num_predict=num_tokens, use_model=self.merge_model
        )
        return re.sub(r"\s*\n+\s*", " ", out).strip()

    def _tiered_merge(
        self,
        items: List[str],
        tier_size: int = 12,
        num_tokens: int = 520,
        target_range: tuple[int, int] = (6, 7),
        soft_tolerance: bool = False,
    ) -> str:
        tgt_min, tgt_max = target_range
        base_instr = (
            f"You are a precise scientific writer. Combine the sentences into ONE paragraph "
            f"of {tgt_min}–{tgt_max} sentences. Keep only facts explicitly present in the evidence. "
            "NEVER introduce datasets, names, or years not in the evidence. "
            "Remove redundancy. Plain paragraph only (no bullets, no numbering, no prefaces)."
        )

        cur = items[:]
        while len(cur) > 1:
            next_level = []
            for i in range(0, len(cur), tier_size):
                block = "\n".join(cur[i:i+tier_size])
                prompt = self._wrap_inst(f"{base_instr}\n\n[Sentences]\n{block}\n\n[Paragraph]:")
                merged = self._ollama_generate(
                    prompt, stream=False, override_num_predict=num_tokens, use_model=self.merge_model
                ).strip()
                merged = re.sub(r"\s*\n+\s*", " ", merged).strip()
                next_level.append(merged)
            cur = next_level

        para = cur[0] if cur else ""
        count = self._count_sentences(para)
        if not (tgt_min <= count <= tgt_max):
            if soft_tolerance and (tgt_min - 1) <= count <= (tgt_max + 1):
                return para
            evidence = "\n".join(items)
            para = self._expand_to_target_sentences(para, tgt_min, tgt_max, evidence, num_tokens)
        return para

    # --- verification ---
    def _self_check(self, paragraph: str, evidence: str) -> str:
        """
        Quick verification: mark sentences as OK/UNSURE and drop UNSURE ones.
        """
        instr = (
            "Check factual grounding. For each sentence S from the paragraph, "
            "write 'OK' if directly supported by the evidence, otherwise 'UNSURE'. "
            "Return one label per sentence, in order, each on its own line."
        )
        prompt = self._wrap_inst(
            f"{instr}\n\n[Paragraph]\n{paragraph}\n\n[Evidence]\n{evidence[:4000]}"
        )
        out = self._ollama_generate(prompt, stream=False, override_num_predict=220, use_model=self.merge_model)
        verdicts = [ln.strip().upper() for ln in out.splitlines() if ln.strip()]
        sentences = re.split(r'(?<=[.!?])\s+', paragraph.strip())
        checked = [s for s, v in zip(sentences, verdicts) if "OK" in v]
        return " ".join(checked).strip()

    # ----- text extraction & chunking -----
    @staticmethod
    def _extract_pdf_text(pdf_path: str, skip_backmatter: bool = True) -> str:
        pages = [(p.extract_text() or "") for p in PdfReader(pdf_path).pages]
        raw = "\n".join(pages).replace("\x00"," ")
        s = _fix_pdf_text(raw)
        if skip_backmatter:
            s = _prune_backmatter(s)
        return textwrap.dedent(s).strip()

    @staticmethod
    def _chunk_text(text: str, chunk_chars: int, overlap: int = 120) -> List[str]:
        """
        Section-aware chunking with overlap.
        """
        text = text.strip()
        if not text:
            return []
        chunk_chars = max(600, int(chunk_chars))
        overlap = max(0, min(overlap, chunk_chars // 3))

        # Split on headings like "Abstract", "Introduction", "Results", etc.
        parts = re.split(r"\n(?=[A-Z][A-Za-z ]{3,}\n)", text)
        chunks: List[str] = []

        def _split_part(part: str) -> List[str]:
            sentences = re.split(r'(?<=[.!?])\s+', part.strip())
            if len(sentences) <= 1:
                # fallback to sliding window
                n = len(part)
                step = max(1, chunk_chars - overlap)
                return [part[i:min(i+chunk_chars, n)].strip() for i in range(0, n, step)]
            cur, cur_len, out = [], 0, []
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                add = (1 if cur_len else 0) + len(s)
                if cur_len + add <= chunk_chars:
                    cur.append(s); cur_len += add
                else:
                    if cur:
                        out.append(" ".join(cur).strip())
                    if out and overlap > 0:
                        tail = out[-1][-overlap:]
                        cur = [tail, s]; cur_len = len(tail) + 1 + len(s)
                    else:
                        cur = [s]; cur_len = len(s)
            if cur:
                out.append(" ".join(cur).strip())
            return out

        for part in parts:
            if part.strip():
                chunks.extend(_split_part(part))

        return [c for c in chunks if c]

    @staticmethod
    def _group_chunks(chunks: List[str], group_size: int) -> List[List[str]]:
        group_size = max(2, int(group_size))
        return [chunks[i:i+group_size] for i in range(0, len(chunks), group_size)]

    def _skim_sections(self, text: str, head_chars: int = 9000, tail_chars: int = 3500) -> str:
        """
        Build a short, high-signal skim for ULTRAFAST:
        - Grab Abstract, Introduction, Methods/Approach, Results, Conclusion/Discussion/Limitations (if present)
        - Always include a head and tail slice as fallback
        - Return a compact, de-duplicated concatenation
        """
        t = text or ""
        parts: list[str] = []

        # Helper: slice from a heading up to the next heading or max_chars
        def _slice_from(pattern: str, max_chars: int) -> str | None:
            m = re.search(pattern, t, re.I)
            if not m:
                return None
            # next ALL-CAPS-like heading after the matched one
            nxt = re.search(r"\n[A-Z][A-Za-z0-9 ,\-]{3,}\n", t[m.start():])
            end = m.start() + (max_chars if not nxt else min(max_chars, nxt.start()))
            seg = t[m.start(): end]
            return seg.strip() if seg else None

        # Priority sections (order matters)
        grabs = [
            (r"\babstract\b[:\s]*",                  2000),
            (r"\bintroduction\b[:\s]*",              3200),
            (r"\b(method|methods|approach)\b[:\s]*", 2800),
            (r"\bresults?\b[:\s]*",                  3400),
            (r"\b(conclusion|conclusions|discussion|limitations)\b[:\s]*", 3400),
        ]
        for pat, n in grabs:
            seg = _slice_from(pat, n)
            if seg:
                parts.append(seg)

        # Fallback head/tail slices to ensure context and final claims
        if head_chars > 0:
            parts.append(t[:max(0, head_chars)].strip())
        if tail_chars > 0 and len(t) > tail_chars:
            parts.append(t[-tail_chars:].strip())

        # De-duplicate roughly by prefix hash
        seen = set()
        out: list[str] = []
        for p in parts:
            if not p:
                continue
            key = hashlib.sha1(p[:256].encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            out.append(p)

        return _norm_ws("\n\n".join(out))

    def _complete_last_sentence(self, paragraph: str, num_tokens: int = 48) -> str:
        """
        If the paragraph ends mid-sentence, ask the LLM to finish ONLY the current sentence.
        - No new sentences should start.
        - Keeps style/facts consistent.
        - Uses merge_model if set, else falls back to stage-1 model.
        """
        # If it already ends with sentence punctuation, we're done
        if re.search(r"[.!?][\"')\]]?\s*$", paragraph or ""):
            return paragraph

        instr = (
            "Continue the paragraph to finish the current sentence only. "
            "Do not start a new sentence. Keep the style and facts consistent. "
            "Return only the continuation text, without quotes or extra commentary."
        )
        prompt = self._wrap_inst(
            f"{instr}\n\n[Paragraph]\n{paragraph}\n\n[Continuation]:"
        )

        # Pick a model: prefer merger if available
        use_model = self.merge_model or self.model

        # Generate a short tail
        cont = self._ollama_generate(
            prompt,
            stream=False,
            override_num_predict=max(8, int(num_tokens)),
            use_model=use_model,
        ).strip()

        # Keep only up to the first sentence terminator
        # (captures punctuation and optional closing quote/bracket)
        m = re.search(r"^(.*?[.!?][\"')\]]?)\s", cont + " ")
        tail = (m.group(1) if m else cont).strip()

        # Join cleanly
        sep = "" if (paragraph.endswith(" ") or tail.startswith((" ", ".", ",", ";", ":", ")", "]"))) else " "
        out = (paragraph + sep + tail).strip()

        # Normalize minor spacing artifacts
        out = re.sub(r"\s+([,.;:!?])", r"\1", out)
        out = re.sub(r"\s{2,}", " ", out)
        return out


