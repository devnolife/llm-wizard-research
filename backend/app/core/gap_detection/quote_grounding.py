"""Verbatim-quote grounding for gap indicators (Fase 1 — ala paper-qa).

Setiap indikator gap membawa kutipan kalimat VERBATIM dari chunk korpus yang
mendukungnya, plus skor verifikasi fuzzy — sehingga setiap klaim dapat
ditelusuri kembali ke kalimat sumber (anti-halusinasi).

Algoritme fuzzy identik dengan verifikasi kelemahan paper di
``app.api.routes.analysis_helpers`` (threshold 0.82).
"""

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

QUOTE_MATCH_THRESHOLD = 0.82


def normalize_text(s: str) -> str:
    """Lowercase + collapse whitespace for robust substring matching."""
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def fuzzy_contains(needle: str, haystack: str) -> float:
    """
    Best similarity (0-1) of `needle` against any same-length window of
    `haystack`. Cheap anti-hallucination check for verbatim-ish quotes.
    """
    needle = normalize_text(needle)
    haystack = normalize_text(haystack)
    if not needle or not haystack:
        return 0.0
    if needle in haystack:
        return 1.0
    nlen = len(needle)
    best = 0.0
    step = max(1, nlen // 2)
    for start in range(0, max(1, len(haystack) - nlen + 1), step):
        window = haystack[start:start + nlen]
        ratio = SequenceMatcher(None, needle, window).ratio()
        if ratio > best:
            best = ratio
            if best >= 0.97:
                break
    return best


def split_sentences(text: str) -> List[str]:
    """Naive sentence splitter good enough for paper chunk text."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", text or "")
    return [p.strip() for p in parts if len(p.strip()) >= 30]


def _paper_label(paper: Dict[str, Any]) -> str:
    meta = paper.get("metadata", {}) or {}
    return meta.get("source") or meta.get("title") or paper.get("doc_id", paper.get("id", "?"))


def extract_supporting_quotes(
    terms: List[str],
    papers: List[Dict[str, Any]],
    max_quotes: int = 3,
    max_sentence_len: int = 300,
) -> List[Dict[str, Any]]:
    """
    Ambil kalimat verbatim dari chunk papers yang memuat term kunci indikator.

    Kutipan diambil LANGSUNG dari ``paper["content"]`` (teks chunk asli), jadi
    verbatim by construction — match_score 1.0. Dipakai untuk indikator yang
    dibangun dari sinyal terstruktur (clustering, fact table, NLI).

    Returns: [{"quote", "source_paper", "match_score"}] terurut relevansi
    (jumlah term yang cocok), maks `max_quotes`, satu kutipan per paper agar
    bukti tersebar antar-jurnal (bukan menumpuk di satu paper).
    """
    wanted = [normalize_text(t) for t in terms if t and len(normalize_text(t)) >= 3]
    if not wanted:
        return []
    candidates: List[Dict[str, Any]] = []
    for paper in papers:
        label = _paper_label(paper)
        best_for_paper: Optional[Dict[str, Any]] = None
        for sentence in split_sentences(paper.get("content", "")):
            sent_norm = normalize_text(sentence)
            hits = sum(1 for t in wanted if t in sent_norm)
            if hits == 0:
                continue
            entry = {
                "quote": sentence[:max_sentence_len],
                "source_paper": label,
                "match_score": 1.0,  # verbatim by construction
                "_hits": hits,
            }
            if best_for_paper is None or hits > best_for_paper["_hits"]:
                best_for_paper = entry
        if best_for_paper:
            candidates.append(best_for_paper)
    candidates.sort(key=lambda c: c["_hits"], reverse=True)
    for c in candidates:
        c.pop("_hits", None)
    return candidates[:max_quotes]


def verify_quote_against_papers(
    quote: str,
    papers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Verifikasi fuzzy kutipan yang DIHASILKAN LLM terhadap chunk korpus.

    Returns {"verified": bool, "match_score": float, "source_paper": str|None}.
    Kutipan di bawah QUOTE_MATCH_THRESHOLD dianggap tidak terverifikasi
    (kemungkinan halusinasi) dan TIDAK boleh disimpan sebagai bukti.
    """
    best_score, best_paper = 0.0, None
    for paper in papers:
        score = fuzzy_contains(quote, paper.get("content", ""))
        if score > best_score:
            best_score, best_paper = score, _paper_label(paper)
            if best_score >= 0.97:
                break
    return {
        "verified": best_score >= QUOTE_MATCH_THRESHOLD,
        "match_score": round(best_score, 3),
        "source_paper": best_paper if best_score >= QUOTE_MATCH_THRESHOLD else None,
    }
