# ############## rag_system.py ##########
import os
import time
from typing import List, Dict, Optional, Callable, Tuple

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv
import cohere
from typing import Tuple

load_dotenv()

CHUNK_SIZE = 1000
BATCH_SIZE = 10


class ImprovedRAGSystem:
    def __init__(self, embedding_model="openai", llm_model="openai"):
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.db = chromadb.PersistentClient(path="./chroma_db")
        self.setup_embedding_function()
        self.cohere = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY")) if os.getenv("COHERE_API_KEY") else None

        if llm_model == "openai":
            self.llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            self.llm = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

        self.collection = self.setup_collection()

    def setup_embedding_function(self):
        if self.embedding_model == "openai":
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="text-embedding-3-small",
            )
        elif self.embedding_model == "nomic":
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key="ollama",
                api_base="http://localhost:11434/v1",
                model_name="nomic-embed-text",
            )
        else:
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    def setup_collection(self):
        name = f"documents_{self.embedding_model}"
        try:
            return self.db.get_collection(name=name, embedding_function=self.embedding_fn)
        except Exception:
            return self.db.create_collection(
                name=name,
                embedding_function=self.embedding_fn,
                metadata={"model": self.embedding_model},
            )

    def add_documents(
        self,
        chunks: List[Dict],
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        total_chunks = len(chunks)
        processed = 0
        total_batches = max(1, (total_chunks + BATCH_SIZE - 1) // BATCH_SIZE)

        for i in range(0, total_chunks, BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            try:
                self.collection.add(
                    ids=[chunk["id"] for chunk in batch],
                    documents=[chunk["text"] for chunk in batch],
                    metadatas=[chunk["metadata"] for chunk in batch],
                )
                processed += len(batch)
                if self.embedding_model == "openai":
                    time.sleep(0.1)
                if on_progress:
                    on_progress((i // BATCH_SIZE) + 1, total_batches)
            except Exception as e:
                print(f"Error processing batch {i//BATCH_SIZE + 1}: {e}")
                continue

        return processed

    def query_documents(self, query: str, n_results: int = 3, namespace: Optional[str] = None):
        where = {"namespace": namespace} if namespace else None
        return self.collection.query(query_texts=[query], n_results=n_results, where=where)

    def query_documents_multi(self, query: str, n_results: int = 6, namespace: Optional[str] = None):
        where = {"namespace": namespace} if namespace else None
        # NEW: recall more for headroom (precision improves after rerank)
        recall_k = max(n_results * 5, 50)  # NEW
        res = self.collection.query(query_texts=[query], n_results=recall_k, where=where)
        docs = res.get("documents", [[]])[0] if res else []
        metas = res.get("metadatas", [[]])[0] if res else []
        passages = list(zip(docs, metas))

        # Rerank (keep your _rerank_with_cohere as you already added)
        ranked = self._rerank_with_cohere(query, passages, top_k=max(n_results * 2, 12))  # NEW

        # NEW: cap per source so one long PDF doesn't dominate
        seen: Dict[str, int] = {}
        capped: List[Tuple[str, Dict, float]] = []
        for t, m, s in ranked:
            src = (m or {}).get("source", "unknown")
            if seen.get(src, 0) >= 2:  # at most 2 chunks per source (tune if needed)
                continue
            seen[src] = seen.get(src, 0) + 1
            capped.append((t, m, s))
            if len(capped) >= n_results:
                break
        return capped


    

    def generate_response(self, query, context):
        prompt = f"""Based on the following context, please answer the question.
If you can't find the answer in the context, say so.

Context: {context}

Question: {query}

Answer:"""
        response = self.llm.chat.completions.create(
            model="gpt-4o-mini" if self.llm_model == "openai" else "llama3.2",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            timeout=30,
        )
        return response.choices[0].message.content

    def generate_response_multi(self, query: str, passages_scored: List[Tuple[str, Dict, float]],
                            max_context_chars: int = 12000, dedupe_by_source: bool = True) -> Dict:
        if dedupe_by_source:
            best_per_source = {}
            for text, meta, score in passages_scored:
                src = (meta or {}).get("source", "unknown")
                if src not in best_per_source:
                    best_per_source[src] = (text, meta, score)
            passages_scored = list(best_per_source.values())

        labeled_blocks = []
        used = []
        total = 0
        for i, (text, meta, score) in enumerate(passages_scored, start=1):
            label = f"[{i}]"
            block = f"{label} {text.strip()}\n"
            if total + len(block) > max_context_chars: break
            labeled_blocks.append(block)
            total += len(block)
            used.append({"label": label, "source": (meta or {}).get("source", "unknown"),
                        "chunk_index": (meta or {}).get("chunk_index"), "namespace": (meta or {}).get("namespace"),
                        "score": round(float(score), 3)})

        legend = "\n".join(f"{u['label']} {u['source']} (score={u['score']})" for u in used)
        context = "\n".join(labeled_blocks) if labeled_blocks else "N/A"

        prompt = f"""You are synthesizing an answer using multiple documents.
    Write ONE coherent paragraph. Cite with the numeric labels right after the relevant sentences (e.g., [1], [2][3]).
    If the context doesn't contain the answer, say so.

    Source labels (with relevance scores):
    {legend}

    Context:
    {context}

    Question: {query}

    Final answer (with [n] citations):"""

        response = self.llm.chat.completions.create(
            model="gpt-4o-mini" if self.llm_model == "openai" else "llama3.2",
            messages=[
                {"role": "system", "content": "You are concise and always add [n] citations to claims grounded in the context."},
                {"role": "user", "content": prompt},
            ],
            timeout=60,
        )
        return {"answer": response.choices[0].message.content, "sources": used}


    def _rerank_with_cohere(self, query: str, passages: List[Tuple[str, Dict]], top_k: int) -> List[Tuple[str, Dict, float]]:
        """
        Input: [(text, meta), ...] from Chroma
        Output: [(text, meta, score)] sorted desc by score
        """
        if not self.cohere or not passages:
            # Fallback: keep original order with flat scores
            return [(t, m, 0.5) for (t, m) in passages[:top_k]]

        docs = [t for (t, _) in passages]
        try:
            resp = self.cohere.rerank(model="rerank-v3.5", query=query, documents=docs, top_n=min(top_k, len(docs)))
            ranked = []
            for r in resp.results:
                text, meta = passages[r.index]
                ranked.append((text, meta, float(r.relevance_score)))
            return ranked
        except Exception as e:
            print(f"[rerank] cohere error: {e}")
            return [(t, m, 0.5) for (t, m) in passages[:top_k]]
    
    def coverage_pack(
        self,
        namespace: Optional[str],
        total: int = 40,
        per_source: int = 2,
    ) -> List[Tuple[str, Dict, float]]:
        """
        Return diverse chunks across sources for summarization,
        with neutral scores so the UI can still show badges.
        """
        where = {"namespace": namespace} if namespace else None
        # bias retrieval to overview sections
        coverage_query = (
            "overview abstract introduction conclusion summary goals methods findings limitations"
        )
        res = self.collection.query(  # NEW
            query_texts=[coverage_query],
            n_results=max(total, 40),
            where=where,
        )
        docs = res.get("documents", [[]])[0] if res else []
        metas = res.get("metadatas", [[]])[0] if res else []
        pairs = list(zip(docs, metas))

        by_src: Dict[str, List[Tuple[str, Dict]]] = {}  # NEW
        for t, m in pairs:
            src = (m or {}).get("source", "unknown")
            by_src.setdefault(src, [])
            if len(by_src[src]) < per_source:
                by_src[src].append((t, m))

        out: List[Tuple[str, Dict, float]] = []  # NEW
        for src, items in by_src.items():
            for t, m in items:
                out.append((t, m, 0.45))  # neutral-ish score == “Medium”
                if len(out) >= total:
                    return out
        return out


rag_system = ImprovedRAGSystem()
