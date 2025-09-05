# ############## rag_system.py ##########
import os
import time
from typing import List, Dict, Optional, Callable, Tuple

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

CHUNK_SIZE = 1000
BATCH_SIZE = 10


class ImprovedRAGSystem:
    def __init__(self, embedding_model="openai", llm_model="openai"):
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.db = chromadb.PersistentClient(path="./chroma_db")
        self.setup_embedding_function()

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

    def query_documents(self, query, n_results=3):
        return self.collection.query(query_texts=[query], n_results=n_results)

    def query_documents_multi(self, query: str, n_results: int = 6) -> List[Tuple[str, Dict]]:
        """
        Returns a flat list of (document_text, metadata) tuples for the top results.
        """
        res = self.collection.query(query_texts=[query], n_results=n_results)
        docs = res.get("documents", [[]])[0] if res else []
        metas = res.get("metadatas", [[]])[0] if res else []

        out: List[Tuple[str, Dict]] = []
        for d, m in zip(docs, metas):
            out.append((d, m or {}))
        return out

    

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

    def generate_response_multi(
    self,
    query: str,
    passages: List[Tuple[str, Dict]],
    max_context_chars: int = 12000,
    dedupe_by_source: bool = True,
) -> Dict:
        """
        passages: list of (text, metadata={'source': filename, ...})
        Returns dict: {"answer": str, "sources": List[Dict]}
        """
        # Deduplicate per source if requested (keep strongest/top passage per file)
        if dedupe_by_source:
            best_per_source = {}
            for text, meta in passages:
                src = (meta or {}).get("source", "unknown")
                if src not in best_per_source:
                    best_per_source[src] = (text, meta)
            passages = list(best_per_source.values())

        # Build a bounded context string, labeled per source
        labeled_chunks = []
        total_len = 0
        used_sources = []

        for text, meta in passages:
            src = (meta or {}).get("source", "unknown")
            label = f"[Source: {src}]"
            block = f"{label}\n{text.strip()}\n"
            if total_len + len(block) > max_context_chars:
                break
            labeled_chunks.append(block)
            total_len += len(block)
            used_sources.append({"source": src, **(meta or {})})

        context = "\n\n".join(labeled_chunks) if labeled_chunks else "N/A"

        prompt = f"""You are synthesizing an answer using multiple documents.
    Write a single coherent paragraph (no bullet points). If the provided context
    doesn't contain the answer, say so clearly.

    Context (multiple labeled excerpts):
    {context}

    User question: {query}

    Final answer (one paragraph):"""

        response = self.llm.chat.completions.create(
            model="gpt-4o-mini" if self.llm_model == "openai" else "llama3.2",
            messages=[
                {"role": "system", "content": "You are a concise, factual AI that writes in plain English."},
                {"role": "user", "content": prompt},
            ],
            timeout=60,
        )
        answer = response.choices[0].message.content
        return {"answer": answer, "sources": used_sources}


rag_system = ImprovedRAGSystem()
