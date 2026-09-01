"""Metadata resolution: GROBID -> CrossRef(DOI) -> heuristic (TAHAP 1 bagian A).

Fixes masalah 3 (title was the journal name/ISSN) and masalah 4 (year missing or
taken from the first number in the text). Resolution order:

  1. GROBID ``processFulltextDocument`` (when ``GROBID_URL`` is set and alive):
     authoritative title/authors/year/DOI/abstract + IMRaD section structure.
  2. Regex a DOI from the text -> CrossRef ``works/{doi}`` for title/authors/year.
  3. Heuristic title/year from the first page, as a last resort.

``year`` is always validated to a sane range (1990..current) and reconciled with
CrossRef when available.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional, Tuple

from loguru import logger

from ...services.paper_apis.grobid import GrobidClient
from .schema import PaperMeta
from .text_cleaning import detect_language

# DOI syntax per CrossRef recommendation.
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

_MIN_YEAR = 1990


def _current_year() -> int:
    return datetime.now().year


def valid_year(y: Optional[int]) -> bool:
    return isinstance(y, int) and _MIN_YEAR <= y <= _current_year()


def extract_doi(text: str) -> Optional[str]:
    """First DOI found in the text, normalised to lowercase, trailing punct trimmed."""
    cands = extract_doi_candidates(text)
    return cands[0] if cands else None


def extract_doi_candidates(text: str) -> List[str]:
    """All distinct DOIs in the text, article-like (longer suffix) ones first.

    A journal-level DOI such as ``10.37284/2707-5354`` (an embedded ISSN) is a
    valid DOI match but resolves to nothing useful, so we prefer candidates with
    a richer suffix and fall back to the rest.
    """
    if not text:
        return []
    seen = set()
    cands: List[str] = []
    for m in _DOI_RE.finditer(text):
        doi = m.group(0).rstrip(".,;)").lower()
        if doi not in seen:
            seen.add(doi)
            cands.append(doi)

    def _is_issn_like(doi: str) -> bool:
        suffix = doi.split("/", 1)[1] if "/" in doi else ""
        return bool(re.fullmatch(r"\d{4}-\d{3}[\dxX]", suffix))

    # Article-like DOIs first, ISSN-like journal DOIs last.
    cands.sort(key=lambda d: (_is_issn_like(d), -len(d)))
    return cands


def _heuristic_title(text: str) -> Optional[str]:
    """Best-effort title from the first lines (last-resort only)."""
    if not text:
        return None
    bad = re.compile(
        r"issn|e-issn|p-issn|doi|http|www\.|@|copyright|©|received|accepted|"
        r"vol\.|volume|\bno\.|journal|proceedings|conference|university|"
        r"published|license|creative commons",
        re.IGNORECASE,
    )
    lines = [ln.strip() for ln in text.splitlines()[:40]]
    candidates: List[str] = []
    for ln in lines:
        if not (15 <= len(ln) <= 250):
            continue
        if bad.search(ln):
            continue
        digits = sum(c.isdigit() for c in ln)
        if digits / max(len(ln), 1) > 0.3:
            continue
        letters = sum(c.isalpha() for c in ln)
        if letters / max(len(ln), 1) < 0.6:
            continue
        candidates.append(ln)
    if not candidates:
        return None
    # Prefer the longest of the first few candidates (titles usually longest
    # near the top and above the author line).
    return max(candidates[:5], key=len)


def _heuristic_year(text: str) -> Optional[int]:
    """A validated year, preferring copyright/date phrasings over any number."""
    if not text:
        return None
    head = text[:4000]
    # Prefer explicit copyright / published years.
    for pat in (
        r"(?:©|\(c\)|copyright)\s*(19|20)\d{2}",
        r"(?:published|accepted|received)[^\n]{0,40}?(19|20)\d{2}",
    ):
        m = re.search(pat, head, re.IGNORECASE)
        if m:
            y = int(re.search(_YEAR_RE, m.group(0)).group(0))
            if valid_year(y):
                return y
    # Otherwise the most frequent plausible year in the head.
    years = [int(y) for y in re.findall(r"(?:19|20)\d{2}", head)]
    years = [y for y in years if valid_year(y)]
    if years:
        return max(set(years), key=years.count)
    return None


def _crossref_by_doi(doi: str):
    """Sync CrossRef DOI lookup; tolerant of the client not having the method yet."""
    try:
        from ...services.paper_apis.crossref import CrossRefAPI

        api = CrossRefAPI()
        getter = getattr(api, "get_by_doi", None)
        if getter is None:
            return None
        return getter(doi)
    except Exception as e:  # pragma: no cover - network/attr issues
        logger.warning(f"CrossRef DOI lookup failed for {doi}: {e}")
        return None


def _lookup_by_title(title: str):
    """Find (year, doi) for a title via OpenAlex search (sync, cached).

    Only accepts a result whose title closely matches (>= 0.85), so we don't
    attach the wrong paper's metadata. Used to recover a missing year/DOI when
    the PDF has no in-text DOI (masalah 4).
    """
    if not title or len(title) < 12:
        return None
    try:
        from difflib import SequenceMatcher

        from ...services.paper_apis import http_cache

        data = http_cache.get_json(
            "https://api.openalex.org/works",
            params={"search": title, "per-page": 3},
        )
        if not data:
            return None
        for work in data.get("results", []):
            wt = work.get("title") or work.get("display_name") or ""
            if SequenceMatcher(None, title.lower(), wt.lower()).ratio() >= 0.85:
                year = work.get("publication_year")
                doi = (work.get("doi") or "").replace("https://doi.org/", "") or None
                return (year if valid_year(year) else None), doi
    except Exception as e:  # pragma: no cover
        logger.warning(f"OpenAlex title lookup failed: {e}")
    return None


def resolve_metadata(
    pdf_path: str,
    full_text: str,
    source: str,
    extraction_quality: str = "good",
    title_hint: Optional[str] = None,
    doi_hint: Optional[str] = None,
) -> Tuple[PaperMeta, Optional[List[Tuple[str, str]]]]:
    """Resolve paper metadata + (optionally) GROBID IMRaD sections.

    Returns ``(PaperMeta, grobid_sections | None)``. When GROBID sections are
    returned the pipeline uses them directly; otherwise it detects sections from
    the cleaned text itself. ``title_hint`` (largest-font text on page 1) and
    ``doi_hint`` (the paper's own DOI, detected before footer stripping) are used
    ahead of the in-text heuristics when GROBID/CrossRef are unavailable.
    """
    meta = PaperMeta(source=source, extraction_quality=extraction_quality)
    meta.language = detect_language(full_text)
    grobid_sections: Optional[List[Tuple[str, str]]] = None

    # ---- 1) GROBID ---------------------------------------------------
    client = GrobidClient()
    if client.is_available():
        parsed = client.process_fulltext(pdf_path)
        if parsed:
            meta.paper_title = parsed.get("title") or meta.paper_title
            meta.authors = parsed.get("authors") or []
            meta.doi = parsed.get("doi") or meta.doi
            meta.abstract = parsed.get("abstract")
            if valid_year(parsed.get("year")):
                meta.year = parsed.get("year")
            grobid_sections = parsed.get("sections") or None
            meta.metadata_source = "grobid"
            logger.debug(f"{source}: metadata via GROBID")

    # ---- Paper's own DOI (never a reference DOI) ---------------------
    if not meta.doi and doi_hint:
        meta.doi = doi_hint

    # ---- 2) CrossRef by DOI -----------------------------------------
    need_crossref = (not meta.paper_title) or (not valid_year(meta.year)) or (not meta.authors)
    if need_crossref and meta.doi:
        cr = _crossref_by_doi(meta.doi)
        if cr is not None and getattr(cr, "title", None):
            if not meta.paper_title:
                meta.paper_title = cr.title
            if not meta.authors and getattr(cr, "authors", None):
                meta.authors = cr.authors
            if not valid_year(meta.year) and valid_year(getattr(cr, "year", None)):
                meta.year = cr.year
            if meta.metadata_source != "grobid":
                meta.metadata_source = "crossref"
            logger.debug(f"{source}: metadata via CrossRef DOI {meta.doi}")

    # ---- 3) Heuristic fallback --------------------------------------
    if not meta.paper_title:
        hint = (title_hint or "").strip()
        meta.paper_title = hint or _heuristic_title(full_text)
    if not valid_year(meta.year):
        meta.year = _heuristic_year(full_text)

    # ---- 4) Title search (recover missing year/DOI, no in-text DOI) ---
    if not valid_year(meta.year) and meta.paper_title:
        found = _lookup_by_title(meta.paper_title)
        if found:
            year, doi = found
            if valid_year(year):
                meta.year = year
                if meta.metadata_source == "heuristic":
                    meta.metadata_source = "openalex"
            if doi and not meta.doi:
                meta.doi = doi

    if not valid_year(meta.year):
        meta.year = None  # never emit an out-of-range year (masalah 4)

    return meta, grobid_sections
