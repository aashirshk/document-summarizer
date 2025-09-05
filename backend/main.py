# main.py
import time
from pathlib import Path
from pdf_sum_rag_llm import PDFSummarizer

# 👇 Add your PDF paths here
PDFS = [
    "/Users/aashir/Documents/Advanced-Project/document-summarization/backend/2112.04426v3.pdf",
    # "another_paper.pdf",
]

def run_and_time(title: str, fn, *args, **kwargs):
    print(f"\n=== {title} ===")
    t0 = time.time()
    out = fn(*args, **kwargs)
    t1 = time.time()
    print(out)
    print(f"\n[Time taken: {t1 - t0:.2f} seconds]")
    return out, t1 - t0

def build_summarizer() -> PDFSummarizer:
    """
    Both stages on Ollama + RAG in front.
    - Stage-1 (extract): Mistral (q4 for speed on M-series)
    - Stage-2 (merge):   Gemma 3 1B (very fast)
    - Ultrafast:         Gemma 3 1B (single call)
    - RAG:               Ollama embeddings (nomic-embed-text)
    """
    return PDFSummarizer(
        backend="ollama",
        model="mistral:instruct",   # extractor
        merge_model="gemma3:1b",           # merger (try "gemma3:4b" if you want smoother prose)
        single_call_model="gemma3:1b",     # ultrafast single call
        # ---- RAG settings ----
        use_rag=True,
        embed_backend="ollama",            # or "sentence-transformers"
        embed_model="nomic-embed-text",    # pull once: `ollama pull nomic-embed-text`
        rag_topk=60,                       # keep top-K chunks for Stage-1
        rag_mmr_lambda=0.65,               # 0.5–0.7 is typical
        # ---- Ollama perf knobs ----
        stream=False,
        ollama_options={
            "num_ctx": 1536,               # smaller = faster on M-series
            "num_batch": 256,
            "temperature": 0.0,
            "repeat_penalty": 1.05,
        },
        # transformers backend params are ignored since we're using Ollama
    )

def main():
    summ = build_summarizer()

    for pdf in PDFS:
        p = Path(pdf)
        print("\n" + "=" * 88)
        print(f"FILE: {p.resolve() if p.exists() else p}  {'(found)' if p.exists() else '(NOT FOUND)'}")
        print("=" * 88)
        if not p.exists():
            continue

        # 1) Two-stage (default settings)
        _, t_default = run_and_time(
            "TWO-STAGE (default + RAG)",
            summ.summarize,
            str(p),
            group_size=16,
            chunk_chars=3200,
            final_num_tokens=520,
            target_sentences=(6, 7),
            fast=False,
        )

        # 2) Two-stage (fast)
        _, t_fast = run_and_time(
            "TWO-STAGE (fast + RAG)",
            summ.summarize,
            str(p),
            group_size=16,           # fast presets are applied inside summarize(fast=True)
            chunk_chars=3200,
            final_num_tokens=520,    # in fast mode, code caps merge budget internally (~≤380)
            target_sentences=(6, 7),
            fast=True,
        )

        # 3) Ultrafast (single call)
        _, t_ultra = run_and_time(
            "ULTRAFAST (single call + skim)",
            summ.summarize,
            str(p),
            group_size=0,            # triggers single-call path
            final_num_tokens=180,    # 6–7 sentences is usually fine with ~160–200 tokens
            target_sentences=(6, 7),
        )

        # 4) Ask a custom question
        question = "What is the core idea and why is it useful?"
        _, t_qa = run_and_time(
            f"QUESTION: {question}",
            summ.ask_question,
            str(p),
            question,
        )

        # 5) Generate questions
        _, gen_question = run_and_time(
            "Generating Questions",
            summ.generate_sample_questions,
            str(p),   
        )
        

        # Quick summary
        print("\n--- Summary of times ---")
        print(f"Two-stage (default): {t_default:.2f}s")
        print(f"Two-stage (fast):    {t_fast:.2f}s")
        print(f"Ultrafast:           {t_ultra:.2f}s")
        print(f"Q&A:                 {t_qa:.2f}s")
        print(f"Sample Questions:    {gen_question:.2f}s")

if __name__ == "__main__":
    main()
