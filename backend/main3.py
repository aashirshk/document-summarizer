# main.py
import time
from pathlib import Path
from pdf_ultrafast import UltrafastPDFSummarizer

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

def build_summarizer() -> UltrafastPDFSummarizer:
    """
    Ultrafast single-call summarizer (Ollama).
    """
    return UltrafastPDFSummarizer(
        model="gemma3:1b",
        ollama_url="http://127.0.0.1:11434",
        num_ctx=2048,
        keep_alive="15m",
        ultra_head_chars=4000,
        ultra_tail_chars=1200,
    )

# # --- Light wrappers for Q&A and sample-question generation (same style as before) ---
# def ask_question_ultrafast(summ: UltrafastPDFSummarizer, pdf_path: str, question: str, context_chars: int = 3500) -> str:
#     text = summ._extract_pdf_text(pdf_path, skip_backmatter=False)
#     context = text[:max(500, context_chars)]
#     prompt = summ._wrap_inst(
#         "Answer using ONLY the context. If the answer is not present, reply 'I don't know'. "
#         "Write 3–6 complete sentences; no bullet points, no prefaces.\n\n"
#         f"[Context]\n{context}\n\n[Question] {question}\n[Answer]:"
#     )
#     return summ._ollama_generate(prompt, override_num_predict=220, use_model=summ.model).strip()

# def generate_sample_questions_ultrafast(summ: UltrafastPDFSummarizer, pdf_path: str, context_chars: int = 3500) -> str:
#     context = summ._extract_pdf_text(pdf_path, skip_backmatter=True)[:max(800, context_chars)]
#     prompt = summ._wrap_inst(
#         "Read the following scientific text and propose 5 natural, helpful questions "
#         "that a researcher might ask to understand the paper better. "
#         "Questions should be diverse (methods, results, datasets, conclusions, limitations). "
#         "Output ONLY 5 numbered questions, nothing else.\n\n"
#         f"[Context]\n{context}\n\n[Questions]:"
#     )
#     return summ._ollama_generate(prompt, override_num_predict=180, use_model=summ.model).strip()

def main():
    summ = build_summarizer()

    for pdf in PDFS:
        p = Path(pdf)
        print("\n" + "=" * 88)
        print(f"FILE: {p.resolve() if p.exists() else p}  {'(found)' if p.exists() else '(NOT FOUND)'}")
        print("=" * 88)
        if not p.exists():
            continue

        # 1) Ultrafast single-call summary (one paragraph)
        _, t_summary = run_and_time(
            "ULTRAFAST (single call + skim)",
            summ.summarize,
            str(p),
            final_num_tokens=220,      # ~6–7 sentences; bump to 260 if needed
            target_sentences=(6, 7),
            skip_backmatter=True,
        )

        # 2) Ask a custom question
        question = "What is the approximate number of parameters in the RETRO model compared to GPT-3 and Jurassic-1?"
        _, t_qa = run_and_time(
            f"QUESTION: {question}",
            summ.answer_question,
            str(p),
            question,
        )

        # 3) Generate sample questions
        _, t_gen = run_and_time(
            "Generating Questions",
            summ.generate_sample_questions_ultrafast,
            str(p),
        )

        # Quick summary
        print("\n--- Summary of times ---")
        print(f"Ultrafast summary:   {t_summary:.2f}s")
        print(f"Q&A:                 {t_qa:.2f}s")
        print(f"Sample Questions:    {t_gen:.2f}s")

if __name__ == "__main__":
    main()
