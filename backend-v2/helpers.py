import re
import string

NUMERIC_PAT = re.compile(
    r"""
    (?:
        \b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b      # 12,345 or 12,345.67
        |\b\d+(?:\.\d+)?\b                    # 123 or 123.45
    )
    \s*
    (?:B|M|K|billion|million|thousand|%)?     # optional unit
    """,
    re.IGNORECASE | re.VERBOSE,
)

def extract_keywords_from_question(q: str, min_len: int = 3):
    # crude keyworder: alphanumerics, drop stop-ish small words
    q = q.translate(str.maketrans("", "", string.punctuation))
    tokens = [t.lower() for t in q.split() if len(t) >= min_len]
    # keep top unique terms
    return list(dict.fromkeys(tokens))

def harvest_numeric_snippets_generic(chunks_texts, question, max_snippets=8, window=280):
    """
    From a list of chunk strings, pull short snippets that contain BOTH:
      - at least one question keyword
      - at least one numeric pattern (e.g., 7.5B, 175B, 25%, etc.)
    """
    kws = extract_keywords_from_question(question)
    if not kws:
        kws = []  # fall back: accept any numeric hit

    hits = []
    for t in chunks_texts:
        tl = t.lower()
        if kws and not any(k in tl for k in kws):
            continue
        m = NUMERIC_PAT.search(t)
        if m:
            start = max(0, m.start() - window)
            end   = min(len(t), m.end() + window)
            snippet = t[start:end].replace("\n", " ").strip()
            hits.append(snippet)
            if len(hits) >= max_snippets:
                break
    return hits
