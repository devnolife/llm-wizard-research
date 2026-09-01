"""Text cleaning for the upgraded pipeline (TAHAP 1 bagian C — masalah 7, 8, 10).

Fixes, in order:

  * masalah 7 — Unicode normalisation (NFKC) + ligature/mojibake repair via
    ``ftfy`` (``speci?cally`` -> ``specifically``, ``ﬁ`` -> ``fi``) and
    de-hyphenation of line-break splits (``investiga-\ntive`` -> ``investigative``)
    while preserving genuine compounds (``state-\nof-the-art``).
  * masalah 8 — remove repeated running heads/footers and page numbers (patterns
    that recur on >= 50% of pages).
  * masalah 10 — DO NOT strip non-ASCII (the legacy processor destroyed Cyrillic).
    Instead score extraction quality and let the caller trigger OCR / mark
    ``extraction_quality="poor"``.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import List, Optional

from loguru import logger

try:
    import ftfy
except ImportError:  # pragma: no cover - dependency is declared in requirements
    ftfy = None

try:
    from langdetect import detect as _lang_detect
    from langdetect import DetectorFactory

    DetectorFactory.seed = 0  # deterministic language detection
except ImportError:  # pragma: no cover
    _lang_detect = None


# Words that indicate a genuine compound rather than a hyphenated line split.
# Keeps ``state-of-the-art`` intact while joining ``investiga-tive``.
_COMPOUND_TAIL = {
    "of", "the", "and", "a", "an", "in", "to", "for", "based", "on", "or",
    "with", "de", "dan", "yang", "di", "ke", "per",
}

_PAGE_NUMBER_RE = re.compile(
    r"^\s*(page\s+)?\d{1,4}(\s*(of|/)\s*\d{1,4})?\s*$", re.IGNORECASE
)
# Table-of-contents dotted leaders ("Introduction .......... 12") and rule lines.
_TOC_LEADER_RE = re.compile(r"\.{5,}")
# A tabular row: mostly numeric/symbolic tokens, or survey cells like "23(19.0)".
_TABLE_CELL_RE = re.compile(r"^[\d.,%/()\-]+$|^\d+\(\d+(\.\d+)?%?\)$")
_REPLACEMENT_CHAR = "\ufffd"


def _is_table_row(stripped: str) -> bool:
    """Heuristic: a flattened table row (numeric/symbol tokens dominate).

    Removing these keeps statistical tables (RAG noise, and a source of
    non-sentence chunk endings) out of the prose stream. Conservative: requires
    at least half the tokens to be pure numbers/symbols and >= 4 tokens.
    """
    toks = stripped.split()
    if len(toks) < 4:
        return False
    numeric = sum(1 for t in toks if _TABLE_CELL_RE.match(t))
    return numeric / len(toks) >= 0.5


def normalize_unicode(text: str) -> str:
    """ftfy repair (ligatures, mojibake) then NFKC normalisation."""
    if not text:
        return ""
    if ftfy is not None:
        # uncurl_quotes=False keeps typographic quotes as-is; we only want the
        # ligature / encoding repairs.
        text = ftfy.fix_text(text)
    text = unicodedata.normalize("NFKC", text)
    return text


def dehyphenate(text: str) -> str:
    """Join words split by a hyphen at a line break.

    ``investiga-\ntive`` -> ``investigative`` but ``end-\nof-life`` keeps its
    hyphen (``end-of-life``) because the tail word is a common connector.
    """
    if not text:
        return ""

    def _join(match: re.Match) -> str:
        head, tail = match.group(1), match.group(2)
        if tail.lower() in _COMPOUND_TAIL:
            return f"{head}-{tail}"  # genuine compound: keep hyphen, drop break
        return f"{head}{tail}"

    # hyphen + (optional spaces) newline (optional spaces) + word
    text = re.sub(
        r"([A-Za-zÀ-ÿ]{2,})-[ \t]*\n[ \t]*([A-Za-zÀ-ÿ]+)", _join, text
    )
    # Rare same-line artefact from pypdf: "investiga- tive"
    text = re.sub(
        r"([a-zà-ÿ]{2,})-[ \t]+([a-zà-ÿ]{2,})",
        lambda m: m.group(1) + m.group(2)
        if m.group(2).lower() not in _COMPOUND_TAIL
        else m.group(0),
        text,
    )
    return text


def _normalize_line_key(line: str) -> str:
    """Normalised form used to detect repeated headers/footers across pages."""
    line = line.strip().lower()
    line = re.sub(r"\s+", " ", line)
    line = re.sub(r"\d+", "#", line)  # page 3 / page 5 collapse to the same key
    return line


def find_repeated_lines(
    pages: List[str], threshold: float = 0.5, min_pages: int = 3
) -> set:
    """Return normalised line keys that recur on >= ``threshold`` of pages.

    These are running heads/footers, journal names, ISSN lines, copyright
    notices, etc. (spec masalah 8). Only meaningful with several pages.
    """
    if len(pages) < min_pages:
        return set()
    counts: Counter = Counter()
    for page in pages:
        seen = set()
        for raw in page.splitlines():
            key = _normalize_line_key(raw)
            if len(key) < 4 or key in seen:
                continue
            seen.add(key)
            counts[key] += 1
    cutoff = max(2, int(round(threshold * len(pages))))
    return {key for key, c in counts.items() if c >= cutoff}


def is_noise_line(line: str, repeated: set) -> bool:
    """True for page numbers, ToC leaders, rule/symbol lines, repeated heads.

    Blank lines are NOT noise (callers preserve them for structure). Shared by
    ``strip_page_artifacts`` and the font-aware layout sectioner so both apply
    the same filtering.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if _PAGE_NUMBER_RE.match(stripped):
        return True
    if _TOC_LEADER_RE.search(stripped):
        return True
    alnum = sum(c.isalnum() for c in stripped)
    if len(stripped) >= 8 and alnum / len(stripped) < 0.4:
        return True
    if _is_table_row(stripped):
        return True
    if _normalize_line_key(line) in repeated:
        return True
    return False


def strip_page_artifacts(page: str, repeated: set) -> str:
    """Drop repeated header/footer lines, page numbers, and ToC leader lines."""
    kept = []
    for raw in page.splitlines():
        if not raw.strip():
            kept.append(raw)
            continue
        if is_noise_line(raw, repeated):
            continue
        kept.append(raw)
    return "\n".join(kept)


def assess_quality(text: str) -> str:
    """Score extraction quality: ``good`` | ``fair`` | ``poor`` (masalah 10).

    Based on the ratio of alphabetic characters and the density of Unicode
    replacement characters. Garbled / undecodable extractions score ``poor`` so
    the caller can trigger OCR or flag the document.
    """
    if not text or not text.strip():
        return "poor"
    total = len(text)
    letters = sum(1 for c in text if c.isalpha())
    replacement = text.count(_REPLACEMENT_CHAR)
    alpha_ratio = letters / total if total else 0.0
    replacement_ratio = replacement / total if total else 0.0

    if replacement_ratio > 0.005 or alpha_ratio < 0.5:
        return "poor"
    if alpha_ratio < 0.62:
        return "fair"
    return "good"


def detect_language(text: str) -> Optional[str]:
    """Best-effort ISO-639-1 language code for the chunk/paper (masalah D)."""
    if not text or _lang_detect is None:
        return None
    sample = text[:3000].strip()
    if len(sample) < 20:
        return None
    try:
        return _lang_detect(sample)
    except Exception:  # langdetect.lang_detect_exception.LangDetectException
        return None


def clean_page_text(page: str, repeated: set) -> str:
    """Full per-page clean: strip artifacts, repair unicode, de-hyphenate."""
    page = strip_page_artifacts(page, repeated)
    page = normalize_unicode(page)
    page = dehyphenate(page)
    return page


def clean_pages(pages: List[str]) -> List[str]:
    """Clean a list of raw page texts, preserving page boundaries.

    Header/footer detection is cross-page, so it must see every page first.
    """
    if not pages:
        return []
    repeated = find_repeated_lines(pages)
    if repeated:
        logger.debug(f"Removing {len(repeated)} repeated header/footer patterns")
    return [clean_page_text(p, repeated) for p in pages]


def collapse_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single spaces (for chunk bodies)."""
    return re.sub(r"[ \t]+", " ", re.sub(r"\s*\n\s*", "\n", text or "")).strip()


def reflow_paragraphs(text: str) -> str:
    """Rejoin hard-wrapped lines into sentences/paragraphs.

    PDF extraction (especially narrow two-column layouts) inserts a newline after
    almost every line, and blank lines at column/page breaks — often in the
    MIDDLE of a sentence. Left as-is this shatters sentences (``cyber
    criminals\\nfrom`` -> two "lines"; ``the evidence\\n\\ncollected`` -> two
    "paragraphs") and causes mid-sentence chunk cuts (masalah 1).

    We rebuild text line by line: consecutive lines are joined with a space, and
    a blank line only starts a new paragraph when the text so far already ends a
    sentence (``.!?``). That way a sentence spanning a column/page break is
    reconstructed, while genuine paragraph breaks are preserved.
    """
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out: List[str] = []
    cur = ""
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            if cur and cur[-1] in ".!?":
                out.append(cur)
                cur = ""
            continue
        cur = f"{cur} {line}".strip() if cur else line
    if cur:
        out.append(cur)
    return "\n\n".join(re.sub(r"[ \t]+", " ", p).strip() for p in out if p.strip())
