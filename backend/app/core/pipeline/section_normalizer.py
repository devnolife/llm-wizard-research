"""Section title normalisation + reference detection (TAHAP 1 masalah 5, 6).

Maps a raw, messy section header (or a detected header line) to one of the
canonical labels in ``CANONICAL_SECTIONS`` so retrieval and gap mining can be
section-targeted, and flags reference/bibliography chunks so they can be
excluded from RAG indexing.
"""

from __future__ import annotations

import re
from typing import Optional

# Priority-ordered (canonical_label, patterns). First match wins, so more
# specific combined headers (e.g. "results and discussion") precede singles.
_SECTION_PATTERNS = [
    ("references", [
        r"\breferences?\b", r"\bbibliography\b", r"\bdaftar pustaka\b",
        r"\bworks cited\b", r"\bcited literature\b", r"\bliteratur\b",
        r"список\s+використаних\s+джерел", r"список\s+літератури",
        r"\bлітература\b", r"\bбібліографія\b",
    ]),
    ("abstract", [
        r"\babstract\b", r"\babstrak\b", r"\bringkasan\b", r"\bintisari\b",
        r"\bанотація\b", r"\bрезюме\b",
    ]),
    ("related_work", [
        r"\brelated works?\b", r"\bliterature review\b", r"\brelated studies\b",
        r"\bprior work\b", r"\bstate[- ]of[- ]the[- ]art\b", r"\bbackground\b",
        r"\btinjauan pustaka\b", r"\blandasan teori\b", r"\bkajian pustaka\b",
        r"\bpenelitian terkait\b", r"\bteori\b",
        r"аналіз\s+(останніх\s+)?(досліджень|публікацій)", r"огляд\s+літератури",
    ]),
    ("discussion", [
        r"\bresults?\s+and\s+discussion\b", r"\bhasil\s+dan\s+pembahasan\b",
        r"\bdiscussion\b", r"\bpembahasan\b", r"\banalysis\b", r"\banalisis\b",
        r"виклад\s+основного\s+матеріалу", r"\bобговорення\b",
    ]),
    ("conclusion", [
        r"\bconclusions?\b", r"\bconcluding remarks\b", r"\bkesimpulan\b",
        r"\bpenutup\b", r"\bfuture works?\b", r"\bfuture research\b",
        r"\blimitations?\b", r"\bketerbatasan\b", r"\bsaran\b",
        r"\bthreats to validity\b",
        r"\bвисновк", r"\bвисновок\b", r"перспективи\s+подальших",
    ]),
    ("methods", [
        r"\bmaterials? and methods?\b", r"\bmethodolog", r"\bmethods?\b",
        r"\bmetodolog", r"\bmetode\b", r"\bproposed (method|approach|model|system)\b",
        r"\bexperimental setup\b", r"\bresearch method", r"\bsystem design\b",
        r"\bproposed\b", r"\bapproach\b", r"\balgorithm\b",
        r"\bметодолог", r"\bметоди(ка)?\b", r"матеріали\s+та\s+методи",
    ]),
    ("results", [
        r"\bresults?\b", r"\bhasil\b", r"\bfindings\b", r"\bevaluation\b",
        r"\bexperiments?\b", r"\bexperimental results?\b", r"\beksperimen\b",
        r"\bevaluasi\b", r"\bpengujian\b",
        r"\bрезультат",
    ]),
    ("introduction", [
        r"\bintroduction\b", r"\bpendahuluan\b", r"\blatar belakang\b",
        r"\boverview\b", r"\bpengantar\b",
        r"\bвступ\b", r"постановка\s+проблеми", r"мета\s+статт",
    ]),
]

_LEADING_NUMBER_RE = re.compile(
    r"^\s*((\d{1,2}(\.\d{1,2})*)|([ivxlcIVXLC]{1,6}))[\.\)]?\s+"
)


def _strip_leading_numbering(title: str) -> str:
    return _LEADING_NUMBER_RE.sub("", title or "").strip()


def normalize_section(raw_title: Optional[str]) -> str:
    """Map a raw section title to a canonical label (default ``other``)."""
    if not raw_title:
        return "other"
    title = _strip_leading_numbering(raw_title).lower().strip()
    title = re.sub(r"[^\w\s/&-]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        return "other"
    for label, patterns in _SECTION_PATTERNS:
        for pat in patterns:
            if re.search(pat, title):
                return label
    return "other"


# A reference list is dominated by citation-shaped lines: "[12] Author, ...",
# "1. Author (2019)...", DOIs, "et al.", page ranges, "pp. 12-20".
_CITATION_MARKERS = [
    re.compile(r"^\s*\[\d+\]"),
    re.compile(r"^\s*\d+\.\s+[A-Z]"),
    re.compile(r"\bet al\.?\b", re.IGNORECASE),
    re.compile(r"\bdoi\b|10\.\d{4,9}/", re.IGNORECASE),
    re.compile(r"\bpp?\.\s*\d+", re.IGNORECASE),
    re.compile(r"\(\d{4}\)"),
    re.compile(r"\bvol\.?\s*\d+|\bno\.?\s*\d+", re.IGNORECASE),
]


def looks_like_references(text: str, min_ratio: float = 0.35) -> bool:
    """Heuristic: does this text read like a bibliography?

    Used to flag reference chunks even when the section header was not detected
    (spec masalah 6). Returns True when a large fraction of lines carry citation
    markers.
    """
    if not text:
        return False
    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) > 15]
    if len(lines) < 3:
        # Single-blob reference chunk: fall back to marker density per sentence.
        lines = [s.strip() for s in re.split(r"(?<=\.)\s+", text) if len(s.strip()) > 15]
    if not lines:
        return False
    hits = 0
    for ln in lines:
        if any(m.search(ln) for m in _CITATION_MARKERS):
            hits += 1
    return (hits / len(lines)) >= min_ratio


def classify_reference(section_normalized: str, text: str) -> bool:
    """Combine the section label and content heuristic into an is_reference flag."""
    if section_normalized == "references":
        return True
    return looks_like_references(text)
