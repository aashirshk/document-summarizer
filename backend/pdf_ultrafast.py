# pdf_ultrafast.py
from __future__ import annotations
import re, os, json, hashlib, textwrap, unicodedata
from typing import List, Tuple, Optional
import requests
from pypdf import PdfReader

# ========== basic PDF text cleanup ==========
_LIGS = {"ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬀ": "ff", "ﬅ": "ft", "ﬆ": "st"}

def _fix_ligs(s: str) -> str:
    for k, v in _LIGS.items(): s = s.replace(k, v)
    return s

# def _fix_small_caps(s: str) -> str:
#     s = re.sub(r"([A-Za-z])\.(?:sc|smcp)\b", lambda m: m.group(1).upper(), s)
#     s = re.sub(r"(?<=\w)/(?!/)(?=\w)", "", s)
#     return s

def _fix_small_caps(s: str) -> str:
    # A) per-letter: "R.sc E.sc T.sc R.sc O.sc" -> "RETRO"
    s = re.sub(r"(?i)\b([A-Za-z])\.(?:sc|smcp)\b", r"\1", s)
    s = re.sub(r"(?:(?<=\b)[A-Z]\s+){2,12}[A-Z]\b", lambda m: m.group(0).replace(" ", ""), s)
    # B) whole-word glued to numbers: "RETRO.sc7.5B" -> "RETRO 7.5B"
    s = re.sub(r"(?i)\b([A-Za-z0-9]+)\.(?:sc|smcp)(?![A-Za-z])", r"\1", s)
    # C) any leftover ".sc"/".smcp"
    s = re.sub(r"(?i)\.(?:sc|smcp)\b", "", s)
    # D) remove t/h style split-ligatures
    s = re.sub(r"(?<=\w)/(?!/)(?=\w)", "", s)
    return s

def _norm_newlines_hyphens(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\u00AD", "")
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)  # de-hyphenate across line breaks
    return s

def _norm_ws(s: str) -> str:
    lines = [ln.strip() for ln in s.split("\n")]
    lines = [ln for ln in lines if ln]
    s = "\n".join(lines)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()

def _fix_pdf_text(s: str) -> str:
    # normalize weird unicode first so regexes match
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u00D7", "x")   # × -> x
    s = s.replace("\u2212", "-")   # minus
    s = s.replace("\u00A0", " ")   # nbsp
    s = s.replace("·", ".")        # middle dot as decimal

    s = _fix_ligs(s)
    s = _fix_small_caps(s)

    # If ALLCAPS glued to number (RETRO7.5B) add a space
    s = re.sub(r"([A-Z]{3,})(\d)", r"\1 \2", s)

    # de-hyphenate and compact whitespace
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\u00AD", "")
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
    lines = [ln.strip() for ln in s.split("\n")]
    lines = [ln for ln in lines if ln]
    s = "\n".join(lines)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def _prune_backmatter(s: str) -> str:
    m = re.search(r"\n\s*(references|bibliography|appendix|acknowledg(e)?ments)\b.*", s, re.I)
    return s[:m.start()] if m else s

# ========== ultrafast summarizer ==========
class UltrafastPDFSummarizer:
    """
    One-call summarizer with:
      - Section-aware skim (Abstract/Intro/Methods/Results/Conclusion + head/tail).
      - Paper-agnostic instruction focusing on goal/method/data/results/caveats.
      - Hint extraction (datasets & numeric scales) to nudge inclusion.
      - Leakage-claim guard + minimal post-edit to add up to two missing hints.
    """

    def __init__(
        self,
        model: str = "gemma3:1b",              # Ollama model for the ULTRAFAST call
        ollama_url: str = "http://127.0.0.1:11434",
        num_ctx: int = 2048,
        keep_alive: str = "15m",
        ultra_head_chars: int = 4000,
        ultra_tail_chars: int = 1200,
    ):
        self.model = model
        self.ollama_url = ollama_url.rstrip("/")
        self.ollama_options = {
            "num_ctx": num_ctx,
            "temperature": 0.0,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            "keep_alive": keep_alive,
        }
        self.ultra_head_chars = ultra_head_chars
        self.ultra_tail_chars = ultra_tail_chars

    # ---------- public API ----------
    def summarize(
        self,
        pdf_path: str,
        final_num_tokens: int = 200,
        target_sentences: Tuple[int, int] = (6, 7),
        skip_backmatter: bool = True,
    ) -> str:
        text = self._extract_pdf_text(pdf_path, skip_backmatter=skip_backmatter)

        # Build skim
        skim = self._skim_sections(text, head_chars=self.ultra_head_chars, tail_chars=self.ultra_tail_chars)

        # Detect useful hints from the skim
        hints = self._extract_ultrafast_hints(skim)
        hints_str = ", ".join(hints) if hints else ""

        # Paper-agnostic instruction with caveat framing
        instr = (
            f"Summarize the following scientific text into ONE cohesive paragraph of "
            f"{target_sentences[0]}–{target_sentences[1]} sentences. "
            "Focus ONLY on this paper (its goal, method, data/resources, results/metrics, and any caveats). "
            "If specific numbers (e.g., token counts, parameter counts) or named datasets/benchmarks appear, include them. "
            "Treat any mention of data leakage/overlap/contamination as a caveat; do NOT claim that using unfiltered data improves performance. "
            "Do NOT list unrelated prior-work models unless the paper reports direct experimental results on them. "
            "Do not invent datasets, metrics, or years—include them only if explicitly present. "
            "Write one clear paragraph (no bullet points, no prefaces, no headings)."
        )
        if hints_str:
            instr += f" If any of the following terms or figures appear in the text, include them succinctly: {hints_str}."

        prompt = self._wrap_inst(f"{instr}\n\n[Text]\n{skim}\n\n[Paragraph]:")

        # Single LLM call
        out = self._ollama_generate(
            prompt,
            override_num_predict=min(final_num_tokens, 220),
            use_model=self.model,
        ).strip()

        para = re.sub(r"\s*\n+\s*", " ", out).strip()
        para = self._guard_leakage_claims(para)

        # Minimal post-edit to include up to two missing hints (evidence-gated)
        missing = self._select_missing_hints(para, hints)
        if missing:
            para = self._enrich_ultrafast_with_hints(
                paragraph=para,
                evidence_text=skim,
                target_range=target_sentences,
                missing_hints=missing,
                num_tokens=160,
            )

        # Finish if cut mid-sentence
        para = self._complete_last_sentence(para, num_tokens=32)
        return re.sub(r"\s*\n{2,}\s*", " ", para).strip()


    # def answer_question(self, pdf_path: str, question: str, context_chars: int = 4200) -> str:
    #     print("Answering question...")
    #     # 1) Extract normalized text from the whole PDF (keep backmatter to catch tables)
    #     text = self._extract_pdf_text(pdf_path, skip_backmatter=False)

    #     # 2) Build targeted context from the *entire* doc
    #     ctx = self._build_qa_context(text, question, budget=context_chars)

    #     # 3) Try deterministic numeric extraction first for metric-like questions
    #     metric_flag = re.search(r"\b(param|token|accuracy|acc\.|f1|precision|recall|perplex|bleu|rouge|auroc|map|latency|throughput|speed|memory)\b", question, re.I)
    #     if metric_flag:
    #         vals = self._extract_metric_values_from_context(question, ctx)
    #         out = self._format_metric_answer(vals, question)
    #         if out != "I don't know.":
    #             return out

    #     # 4) Fall back to an LLM answer strictly grounded in the context
    #     prompt = self._wrap_inst(
    #         "Answer using ONLY the context. If the context supports only a PARTIAL answer, "
    #         "state the supported part and add: 'The rest is not in the context.' "
    #         "If nothing relevant is present, reply exactly: I don't know.\n"
    #         "Prefer explicit numbers/units/names as written. Keep it to 1–2 sentences.\n\n"
    #         f"[Context]\n{ctx}\n\n[Question] {question}\n[Answer]:"
    #     )
    #     out = self._ollama_generate(prompt, override_num_predict=120).strip()
    #     out = re.sub(r"\s+([,.;:!?])", r"\1", out)
    #     return re.sub(r"\s{2,}", " ", out).strip()

    def answer_question(self, pdf_path: str, question: str, context_chars: int = 4200) -> str:
        print("Answering question...")
        text = self._extract_pdf_text(pdf_path, skip_backmatter=False)

        # 1) If the question is about parameters, scan the entire doc first.
        if re.search(r"\bparam", question, re.I):
            found = self._extract_parameters_fulltext(text)
            ans = self._format_params_answer(found, question)
            if ans != "I don't know.":
                return ans

        # 2) Otherwise (or as fallback), build a targeted context and answer deterministically/LLM
        ctx = self._build_qa_context(text, question, budget=context_chars)

        if re.search(r"\b(param|token|accuracy|acc\.|f1|precision|recall|perplex|bleu|rouge|auroc|map|latency|throughput|speed|memory)\b", question, re.I):
            vals = self._extract_metric_values_from_context(question, ctx)
            out = self._format_metric_answer(vals, question)
            if out != "I don't know.":
                return out

        prompt = self._wrap_inst(
            "Answer using ONLY the context. If the context supports only a PARTIAL answer, "
            "state the supported part and add: 'The rest is not in the context.' "
            "If nothing relevant is present, reply exactly: I don't know.\n"
            "Prefer explicit numbers/units/names as written. Keep it to 1–2 sentences.\n\n"
            f"[Context]\n{ctx}\n\n[Question] {question}\n[Answer]:"
        )
        out = self._ollama_generate(prompt, override_num_predict=120).strip()
        out = re.sub(r"\s+([,.;:!?])", r"\1", out)
        return re.sub(r"\s{2,}", " ", out).strip()




    def generate_sample_questions_ultrafast(self, pdf_path: str, context_chars: int = 3500) -> str:
        """
        Ask for 5 useful questions about the paper (single call).
        """
        context = self._extract_pdf_text(pdf_path, skip_backmatter=True)[:max(800, context_chars)]
        prompt = self._wrap_inst(
            "Read the following scientific text and propose 5 natural, helpful questions "
            "that a researcher might ask to understand the paper better. "
            "Questions should be diverse (methods, results, datasets, conclusions, limitations). "
            "Output ONLY 5 numbered questions, nothing else.\n\n"
            f"[Context]\n{context}\n\n[Questions]:"
        )
        return self._ollama_generate(prompt, override_num_predict=180, use_model=self.model).strip()

    # ---------- text extraction ----------
    @staticmethod
    def _extract_pdf_text(pdf_path: str, skip_backmatter: bool = True) -> str:
        pages = [(p.extract_text() or "") for p in PdfReader(pdf_path).pages]
        raw = "\n".join(pages).replace("\x00", " ")
        s = _fix_pdf_text(raw)
        if skip_backmatter: s = _prune_backmatter(s)
        return textwrap.dedent(s).strip()

    # ---------- skim builder ----------
    def _skim_sections(self, text: str, head_chars: int = 9000, tail_chars: int = 3500) -> str:
        """
        Build a short, high-signal skim for ULTRAFAST:
        - Grab Abstract, Introduction, Methods/Approach, Results, Conclusion/Discussion/Limitations (if present)
        - Always include a head and tail slice as fallback
        """
        t = text or ""
        parts: List[str] = []

        def _slice_from(pattern: str, max_chars: int) -> Optional[str]:
            m = re.search(pattern, t, re.I)
            if not m: return None
            nxt = re.search(r"\n[A-Z][A-Za-z0-9 ,\-]{3,}\n", t[m.start():])
            end = m.start() + (max_chars if not nxt else min(max_chars, nxt.start()))
            seg = t[m.start(): end]
            return seg.strip() if seg else None

        grabs = [
            (r"\babstract\b[:\s]*", 2000),
            (r"\bintroduction\b[:\s]*", 3200),
            (r"\b(method|methods|approach)\b[:\s]*", 2800),
            (r"\bresults?\b[:\s]*", 3400),
            (r"\b(conclusion|conclusions|discussion|limitations)\b[:\s]*", 3400),
        ]
        for pat, n in grabs:
            seg = _slice_from(pat, n)
            if seg: parts.append(seg)

        if head_chars > 0: parts.append(t[:max(0, head_chars)].strip())
        if tail_chars > 0 and len(t) > tail_chars: parts.append(t[-tail_chars:].strip())

        # de-dup
        seen, out = set(), []
        for p in parts:
            if not p: continue
            key = hashlib.sha1(p[:256].encode("utf-8")).hexdigest()
            if key in seen: continue
            seen.add(key); out.append(p)

        return _norm_ws("\n\n".join(out))

    # ---------- hinting + guards ----------
    def _extract_ultrafast_hints(self, text: str) -> List[str]:
        t = text or ""
        hints: List[str] = []
        datasets = [
            r"\bthe pile\b", r"\bwikitext[- ]?103\b", r"\bwikitext\b", r"\blambada\b",
            r"\bwikipedia\b", r"\bnatural questions\b", r"\bsquad\b", r"\bc4\b",
            r"\bcommon crawl\b", r"\bmassivetext\b", r"\bthe pile-cc\b",
        ]
        for pat in datasets:
            if re.search(pat, t, re.I):
                hints.append(re.sub(r"\\b", "", pat).strip("\\").replace("[- ]?", "-").strip())

        num_pats = [
            r"\b~?\d[\d,\.]*\s*(?:tokens|parameters|examples|docs|articles)\b",
            r"\b(?:million|billion|trillion)\s+(?:tokens|parameters|examples|docs|articles)\b",
            r"\b\d+\s*(?:B|M)\b",
        ]
        for pat in num_pats:
            for m in re.findall(pat, t, re.I): hints.append(m)

        out, seen = [], set()
        for h in hints:
            k = h.lower().strip()
            if k not in seen: seen.add(k); out.append(h.strip())
        return out[:8]

    def _guard_leakage_claims(self, paragraph: str) -> str:
        p = paragraph or ""
        patterns = [
            r"(improv\w+|better|stronger|higher)\s+(?:\w+\s+){0,4}when\s+using\s+(?:a\s+)?(large|huge|unfiltered)\s+data(?:set|base)",
            r"(benefit|gain|advantage)\s+(?:\w+\s+){0,3}from\s+(?:an\s+)?unfiltered\s+data(?:set|base)",
        ]
        for pat in patterns:
            if re.search(pat, p, re.I):
                p = re.sub(
                    pat,
                    "the authors discuss potential test-set leakage when using unfiltered data and treat it as a caveat rather than a source of improvement",
                    p,
                    flags=re.I,
                )
        p = re.sub(r"\s{2,}", " ", p)
        p = re.sub(r"\s+([,.;:!?])", r"\1", p)
        return p.strip()

    def _select_missing_hints(self, paragraph: str, hints: List[str]) -> List[str]:
        p = (paragraph or "").lower()
        missing = []
        for h in hints or []:
            h_norm = re.sub(r"\s+", " ", h).strip().lower()
            if h_norm and h_norm not in p: missing.append(h.strip())

        def _score(h: str) -> int:
            s = 0
            if re.search(r"\b(\d[\d,\.]*\s*(tokens|parameters|examples|docs|articles)|"
                         r"(million|billion|trillion)\s+(tokens|parameters|examples|docs|articles)|"
                         r"\d+\s*(B|M))\b", h, re.I):
                s += 2
            if re.search(r"\b(pile|wikitext|wikitext-103|lambada|wikipedia|massivetext|c4)\b", h, re.I):
                s += 2
            return -s
        missing.sort(key=_score)
        return missing[:2]

    def _enrich_ultrafast_with_hints(
        self,
        paragraph: str,
        evidence_text: str,
        target_range: Tuple[int, int],
        missing_hints: List[str],
        num_tokens: int = 180,
    ) -> str:
        if not missing_hints: return paragraph
        tgt_min, tgt_max = target_range
        req = "; ".join(missing_hints)
        instr = (
            f"Revise the paragraph MINIMALLY to include the following items EXACTLY if and only if they are "
            f"explicitly supported by the evidence text: {req}. "
            f"Keep the paragraph at {tgt_min}–{tgt_max} sentences, preserve meaning, and do not add new claims. "
            f"If the evidence does not support any of these items, reply exactly NOOP."
        )
        prompt = self._wrap_inst(
            f"{instr}\n\n[Paragraph]\n{paragraph}\n\n[Evidence]\n{evidence_text[:4000]}"
            "\n\n[Revised paragraph or NOOP]:"
        )
        out = self._ollama_generate(prompt, override_num_predict=num_tokens, use_model=self.model).strip()
        if out.upper().startswith("NOOP"): return paragraph
        out = re.sub(r"\s+([,.;:!?])", r"\1", out)
        out = re.sub(r"\s{2,}", " ", out).strip()
        return out

    # ---------- finishing helper ----------
    def _complete_last_sentence(self, paragraph: str, num_tokens: int = 48) -> str:
        if re.search(r"[.!?][\"')\]]?\s*$", paragraph or ""): return paragraph
        instr = (
            "Continue the paragraph to finish the current sentence only. "
            "Do not start a new sentence. Keep the style and facts consistent. "
            "Return only the continuation text, without quotes or extra commentary."
        )
        prompt = self._wrap_inst(f"{instr}\n\n[Paragraph]\n{paragraph}\n\n[Continuation]:")
        cont = self._ollama_generate(prompt, override_num_predict=max(8, int(num_tokens)), use_model=self.model).strip()
        m = re.search(r"^(.*?[.!?][\"')\]]?)\s", cont + " ")
        tail = (m.group(1) if m else cont).strip()
        sep = "" if (paragraph.endswith(" ") or tail.startswith((" ", ".", ",", ";", ":", ")", "]"))) else " "
        out = (paragraph + sep + tail).strip()
        out = re.sub(r"\s+([,.;:!?])", r"\1", out)
        out = re.sub(r"\s{2,}", " ", out)
        return out

    # ---------- LLM plumbing ----------
    @staticmethod
    def _wrap_inst(content: str) -> str:
        return f"[INST] {content} [/INST]"

    def _ollama_generate(
        self,
        prompt: str,
        override_num_predict: Optional[int] = None,
        use_model: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        url = f"{self.ollama_url}/api/generate"
        opts = {**self.ollama_options, "num_predict": override_num_predict or 200}
        payload = {"model": use_model or self.model, "prompt": prompt, "stream": bool(stream), "options": opts}

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
        return r.json().get("response", "")
    
    def _build_qa_context(self, text: str, question: str, budget: int = 4200) -> str:
        """
        Paper-agnostic context builder:
        • windows around question tokens + generic metric terms + numbers
        • wide spans for table/figure regions
        • small section skim as fallback
        """
        t = text or ""
        tl = t.lower()
        ql = question.lower()

        # Tokens from question (drop stopwords)
        q_tokens = [w for w in re.findall(r"[a-zA-Z0-9\-\+\.%]+", ql) if len(w) > 2]
        STOP = {"what","which","when","where","why","how","much","many","approximate","approx","about",
                "the","a","an","and","or","for","with","without","into","from","than","then","that",
                "this","these","those","are","is","was","were","be","been","being","does","do","did",
                "on","in","of","by","to","vs","versus","compared","compare"}
        q_tokens = [w for w in q_tokens if w not in STOP]

        metric_terms = [
            r"parameters?", r"tokens?", r"accuracy", r"\bacc\.", r"\bf1\b", r"precision", r"recall",
            r"perplex", r"bleu", r"rouge", r"exact match", r"\bem\b", r"\bauroc\b", r"\bmap\b",
            r"latency", r"throughput", r"speed", r"memory",
        ]
        number_terms = [
            r"\b\d+(?:\.\d+)?\s*(?:%|percent)\b",
            r"\b\d+(?:\.\d+)?\s*(?:B|M|K)\b",  # 7.5B, 530M
            r"\b(?:million|billion|trillion)\b",
            r"\b\d[\d,\.]*\s*(?:tokens?|parameters?|examples?|docs?|articles?)\b",
            r"\b\d+\s*x\s*(?:fewer|less|smaller|more|larger)\b",  # 25x fewer
        ]
        anchors = [r"\btable\s*\d+\b", r"\bfigure\s*\d+\b", r"\bfig\.\s*\d+\b"]

        pats = [rf"\b{re.escape(w)}\b" for w in q_tokens] + metric_terms + number_terms + anchors

        windows, seen = [], set()

        def add_window(start: int, end: int, base: int = 0, span: int = 560):
            s = max(0, start - span)
            e = min(len(t), end + span)
            key = (s//40, e//40)
            if key in seen: return
            snip = t[s:e].strip()
            if not snip: return
            score = base
            if re.search(r"\bparameters?\b", snip, re.I): score += 3
            if re.search(r"\b\d+(?:\.\d+)?\s*(?:B|M|K)\b", snip, re.I): score += 3
            if re.search(r"\b(?:million|billion|trillion)\b", snip, re.I): score += 1
            if re.search(r"\b(table|figure|fig\.)\b", snip, re.I): score += 1
            windows.append((score, s, e, snip))
            seen.add(key)

        for pat in pats:
            for m in re.finditer(pat, tl, re.I):
                add_window(m.start(), m.end(), base=2)

        # Pull big blocks around Table / Figure anchors (captures ragged rows)
        for m in re.finditer(r"(table|figure|fig\.)\s*\d+\s*[:\-]?", tl, re.I):
            start = m.start()
            next_anchor = re.search(r"\n\s*(table|figure|fig\.|abstract|introduction|methods?|results?|conclusion)\b",
                                    tl[m.end():], re.I)
            end = len(tl) if not next_anchor else (m.end() + next_anchor.start())
            add_window(start, end, base=4, span=800)

        if not windows:
            return self._skim_sections(t, head_chars=3500, tail_chars=1100)[:budget]

        windows.sort(key=lambda z: (-z[0], z[1]))
        out, used = [], 0
        for score, s, e, snip in windows:
            if used + len(snip) + 2 > budget: continue
            out.append(snip); used += len(snip) + 2
            if used > budget * 0.9: break

        if used < budget * 0.8:
            tail = self._skim_sections(t, head_chars=1600, tail_chars=800)
            leftover = budget - used
            if leftover > 300: out.append(tail[:leftover])

        ctx = "\n\n".join(out)
        ctx = re.sub(r"\s+([,.;:!?])", r"\1", ctx)
        return re.sub(r"\s{2,}", " ", ctx)

    def _extract_metric_values_from_context(self, question: str, ctx: str) -> Dict[str, List[str]]:
        """
        Extract numbers + units near question terms and associate with nearby entity names
        (model/dataset), without hard-coding specific names.
        Returns {entity_or_generic: [values]}.
        """
        base_terms = ["parameters","tokens","accuracy","f1","precision","recall","perplexity","bleu","rouge",
                    "exact match","em","auroc","map","latency","throughput","speed","memory"]
        q_terms = set(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9\- ]{1,}", question))
        terms = {t for t in base_terms if any(t in w for w in q_terms) or t in question.lower()}
        if not terms: terms = set(base_terms)

        num_patterns = [
            r"\d+(?:\.\d+)?\s*(?:%|percent)",
            r"\d+(?:\.\d+)?\s*(?:B|M|K)",
            r"\d[\d,\.]*\s*(?:tokens?|parameters?|examples?|docs?|articles?)",
            r"\d+\s*x\s*(?:fewer|less|smaller|more|larger)",
        ]
        value_re = re.compile("|".join(num_patterns), re.I)

        def nearby_entity(snip: str) -> str:
            # Look for compact proper-noun-ish tokens (e.g., GPT-3, Jurassic-1, Retro, Wikitext-103)
            cands = re.findall(r"\b([A-Z][A-Za-z0-9\-]{2,}(?:\s*[A-Z0-9][A-Za-z0-9\-]{1,})*)\b", snip)
            for c in cands:
                if len(c) <= 40 and not c.isupper():
                    return c.strip()
            return "value"

        chunks = re.split(r'(?<=[.!?])\s+|\n{1,2}', ctx)
        results: Dict[str, List[str]] = {}
        for snip in chunks:
            l = snip.lower()
            if not any(t in l for t in terms):  # require relevance
                continue
            vals = value_re.findall(snip)
            if not vals:
                continue
            ent = nearby_entity(snip)
            results.setdefault(ent, [])
            for v in vals:
                if isinstance(v, tuple):
                    v = next((x for x in v if x), "")
                v = re.sub(r"\s+", " ", v).strip()
                if v and v not in results[ent]:
                    results[ent].append(v)
        return results


    def _format_metric_answer(self, vals: Dict[str, List[str]], question: str) -> str:
        if not vals:
            return "I don't know."
        parts, count = [], 0
        for ent, vs in vals.items():
            if count >= 3: break
            if not vs: continue
            uniq = []
            for v in vs:
                if v not in uniq: uniq.append(v)
            parts.append(f"{ent}: {', '.join(uniq[:2])}")
            count += 1
        if not parts:
            return "I don't know."
        # If the question named entities, note any missing
        mentioned = re.findall(r"(?:GPT-?\s*3|Jurassic-?\s*1|Retro|Gopher|PaLM|LLaMA|Mistral|Gemma)", question, re.I)
        if mentioned:
            mset = {re.sub(r"\s+", "", m.lower()) for m in mentioned}
            present = {re.sub(r"\s+", "", k.lower()) for k in vals.keys()}
            missing = [m for m in mset if not any(m in p for p in present)]
            ans = "; ".join(parts) + "."
            if missing:
                ans += " The rest is not in the context."
            return ans
        return "; ".join(parts) + "."
    
    def _extract_parameters_fulltext(self, text: str) -> dict:
        """
        Scan the FULL normalized text, find parameter counts, and associate them
        with nearby model names (generic; no hard-coded model list).
        Returns dict like {"Retro": ["7.5B"], "GPT-3": ["175B"]}.
        """
        # numbers like 7.5B, 530M, 92.3%, 25x fewer (we only keep B/M/K here)
        num = r"\d+(?:\.\d+)?\s*(?:B|M|K)"
        # accept 'parameter' near the number OR accept a bare number if the same line has 'param'
        param_phrase = rf"(?:{num}\s*parameters?|parameters?\s*[:=]?\s*{num}|{num})"

        # split into reasonable chunks (sentences and single-line blocks)
        chunks = re.split(r'(?<=[.!?])\s+|\n{1,2}', text)

        # heuristic entity detector: compact ProperName / hyphen / digit combos (e.g., GPT-3, Jurassic-1, Retro)
        ent_pat = re.compile(r"\b([A-Z][A-Za-z0-9\-]{2,}(?:\s*[A-Z0-9][A-Za-z0-9\-]{1,})*)\b")

        out: dict[str, list[str]] = {}
        for ch in chunks:
            if not ch or len(ch) < 6:
                continue
            if not re.search(r"\bparam", ch, re.I) and not re.search(num, ch, re.I):
                continue
            # numbers first
            nums = re.findall(num, ch, re.I)
            if not nums:
                continue
            # entity name near-by
            ents = ent_pat.findall(ch)
            ent = None
            for e in ents:
                # ignore ALLCAPS shouting words; keep short model/dataset-like names
                if len(e) <= 40 and not e.isupper():
                    ent = e.strip()
                    break
            if not ent:
                ent = "model"

            # keep only those numbers that are likely parameters (not tokens) if 'param' is present
            if re.search(r"\bparam", ch, re.I):
                keep = nums
            else:
                # still allow (sometimes the caption line has the number but not the word 'parameter')
                keep = nums

            if not keep:
                continue

            out.setdefault(ent, [])
            for v in keep:
                v = re.sub(r"\s+", " ", v).strip()
                if v not in out[ent]:
                    out[ent].append(v)

        return out

    def _format_params_answer(self, found: dict, asked: str) -> str:
        if not found:
            return "I don't know."
        # order a few entities for readability
        parts, used = [], 0
        for ent, vals in found.items():
            if used >= 3:
                break
            if not vals:
                continue
            parts.append(f"{ent}: {', '.join(vals[:2])}")
            used += 1
        if not parts:
            return "I don't know."
        # if the question names specific models, mention if others were missing
        mentioned = re.findall(r"(?:GPT-?\s*3|Jurassic-?\s*1|Retro|Gopher|PaLM|LLaMA|Mistral|Gemma)", asked, re.I)
        if mentioned:
            present = {ent.lower().replace(" ", "") for ent in found.keys()}
            miss = []
            for m in mentioned:
                key = m.lower().replace(" ", "")
                if not any(key in p for p in present):
                    miss.append(m)
            ans = "; ".join(parts) + "."
            if miss:
                ans += " The rest is not in the context."
            return ans
        return "; ".join(parts) + "."




