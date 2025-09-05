# main.py
import time
from pathlib import Path
from pdf_sum_rag_llm_v2 import PDFSummarizer

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
    Ollama-only pipeline with RAG in front.
    - Stage-1 (extract): mistral:instruct
    - Stage-2 (merge):   gemma3:1b  (use 4b if you want smoother prose)
    - Ultrafast:         gemma3:1b
    - Embeddings:        nomic-embed-text (fast) — switch to bge-m3 if you want max recall
    """
    return PDFSummarizer(
        backend="ollama",
        model="mistral:instruct",
        merge_model="gemma3:1b",
        single_call_model="gemma3:1b",
        # ---- RAG settings (focused + fast) ----
        use_rag=True,
        embed_backend="ollama",
        embed_model="nomic-embed-text",  # faster; try "bge-m3" if you want higher recall
        rag_topk=24,                     # fewer, higher-quality chunks
        rag_mmr_lambda=0.85,             # stronger diversity to avoid redundancy
        overlap_chars=320,
        section_weighting=True,
        # ---- Ollama perf knobs ----
        stream=False,
        ollama_options={
            "num_ctx": 2560,            # slightly lower than 3072 for speed; raise if truncation shows
            "num_batch": 256,
            "temperature": 0.0,
            "repeat_penalty": 1.07,
        },
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

        # 1) ULTRAFAST (single call) — recommended default for speed/quality
        ultra_out, t_ultra = run_and_time(
            "ULTRAFAST (single call + skim)",
            summ.summarize,
            str(p),
            group_size=0,              # triggers single-call path
            final_num_tokens=200,      # enough for 6–7 sentences
            target_sentences=(6, 7),
        )

        # 2) Two-stage (fast) — fewer LLM calls, no verify
        fast_out, t_fast = run_and_time(
            "TWO-STAGE (fast + RAG, verify=False)",
            summ.summarize,
            str(p),
            group_size=24,             # fewer groups → fewer LLM calls
            chunk_chars=3200,
            final_num_tokens=520,      # internal cap applies in fast=True path
            target_sentences=(6, 7),
            fast=True,
            verify=False,
        )

        # 3) Two-stage (default) — fuller pass, still without verify by default
        default_out, t_default = run_and_time(
            "TWO-STAGE (default + RAG, verify=False)",
            summ.summarize,
            str(p),
            group_size=24,
            chunk_chars=3200,
            final_num_tokens=560,      # a bit more room for 6–7 sentences
            target_sentences=(6, 7),
            fast=False,
            verify=False,              # turn on (True) only when you need extra grounding
        )

        # 4) Ask a custom question
        question = "What is the core idea and why is it useful?"
        qa_out, t_qa = run_and_time(
            f"QUESTION: {question}",
            summ.ask_question,
            str(p),
            question,
        )

        # 5) Generate sample questions
        gen_qs, t_gen = run_and_time(
            "Generating Questions",
            summ.generate_sample_questions,
            str(p),
        )

        # Quick summary
        print("\n--- Summary of times ---")
        print(f"Ultrafast:           {t_ultra:.2f}s")
        print(f"Two-stage (fast):    {t_fast:.2f}s")
        print(f"Two-stage (default): {t_default:.2f}s")
        print(f"Q&A:                 {t_qa:.2f}s")
        print(f"Sample Questions:    {t_gen:.2f}s")

if __name__ == "__main__":
    main()
