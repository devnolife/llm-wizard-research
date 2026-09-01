"""End-to-end upgraded pipeline orchestrator (TAHAP 1).

``process_pdf`` runs: pymupdf per-page extraction -> cross-page cleaning
(header/footer strip, unicode repair, de-hyphenation) -> metadata resolution
(GROBID/CrossRef/heuristic) -> section structuring (GROBID IMRaD or header
detection with page tracking) -> token-aware sentence-safe chunking -> dedup.

Shared by the FastAPI ingestion path and the reproducible CLI so both emit the
new chunk schema.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from loguru import logger

from .dedup import deduplicate_chunks
from .layout import LineInfo, body_font_size, extract_layout_lines, has_font_variation
from .metadata_resolver import resolve_metadata
from .schema import PaperMeta, PipelineChunk
from .section_normalizer import normalize_section
from .text_cleaning import (
    assess_quality,
    clean_pages,
    dehyphenate,
    find_repeated_lines,
    is_noise_line,
    normalize_unicode,
    reflow_paragraphs,
)
from .token_chunker import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_OVERLAP_RATIO,
    DEFAULT_TARGET_TOKENS,
    chunk_document,
)

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


# Section header keywords for the fallback (no-font) text detector. Deliberately
# excludes ambiguous words that also occur mid-prose ("analysis", "findings",
# "approach", "proposed", "model", "background", "evaluation", "experiment"),
# which otherwise create false section boundaries on shattered text.
_SECTION_KEYWORDS = [
    "abstract", "abstrak", "introduction", "pendahuluan",
    "related work", "literature review", "tinjauan pustaka", "landasan teori",
    "methodology", "methods", "metodologi", "materials and methods",
    "results and discussion", "hasil dan pembahasan", "results", "hasil",
    "discussion", "pembahasan", "conclusion", "conclusions", "kesimpulan",
    "penutup", "limitations", "keterbatasan", "future work", "acknowledgment",
    "acknowledgments", "acknowledgement", "references", "daftar pustaka",
    "bibliography", "appendix", "lampiran",
]

_NUMBERED_HEADER = re.compile(
    r"^\s*((\d{1,2}(\.\d{1,2})*)|([IVXLC]{1,5}))[\.\)]?\s+([A-Z][\w].{0,48})$"
)
_KEYWORD_HEADER = re.compile(
    r"^\s*(\d{1,2}[\.\)]?\s+)?(" + "|".join(re.escape(k) for k in _SECTION_KEYWORDS)
    + r")\b",
    re.IGNORECASE,
)
_LEADING_NUM = re.compile(r"^\s*((\d{1,2}(\.\d{1,2})*)|([IVXLCivxlc]{1,6}))[\.\)]?\s+")

# Identifier/front-matter lines that are visually header-shaped (bold, short)
# but are never section headers.
_FALSE_HEADER_RE = re.compile(
    r"orcid|^\s*(e-?mail|doi|issn|isbn|https?:|www\.)|@|\b\d{4}-\d{4}\b",
    re.IGNORECASE,
)
_ALPHA_RE = re.compile(r"[^\W\d_]", re.UNICODE)


def _is_false_header(text: str) -> bool:
    """Reject author/affiliation/identifier lines that pass the header shape test.

    Font-aware detection flags these because they are bold or set in a larger
    face than the body (ORCID lines, author blocks with superscript markers,
    stray glyphs). Each one used to open a spurious section, which is the main
    source of sub-150-token fragment chunks.
    """
    t = (text or "").strip()
    if len(_ALPHA_RE.findall(t)) < 3:
        return True
    if _FALSE_HEADER_RE.search(t):
        return True
    if t[0] in ",;&*":
        return True
    # A lowercase start means a wrapped prose/author line, except for the short
    # lowercase headers some journals use ("abstract", "article info").
    if t[0].islower() and len(t.split()) > 3:
        return True
    # Author block: name glued to a superscript affiliation marker.
    if re.search(r"[^\W\d_]\d", t, re.UNICODE) and re.search(r"[,&*\u2020\u2021]", t):
        return True
    return False


def _is_header_line(line: str) -> bool:
    """Strict header test — avoids matching wrapped prose as a section header.

    A real header is a short line, has no internal sentence punctuation, does not
    end like a sentence, and matches a numbered / keyword / ALL-CAPS shape. The
    strictness is essential because narrow-column extraction shatters prose into
    short lines, many of which begin with a section keyword (e.g. a line
    "Conclusions based on the evidence collected. This ...").
    """
    line = line.strip()
    if not line or len(line) > 60:
        return False
    if _is_false_header(line):
        return False
    if line[-1] in ".,;":  # headers don't end like sentences
        return False
    if re.search(r"\.\s+\S", line):  # an internal ". word" means it is prose
        return False
    body_words = _LEADING_NUM.sub("", line).split()
    n = len(body_words)
    if _NUMBERED_HEADER.match(line) and 1 <= n <= 6:
        return True
    if _KEYWORD_HEADER.match(line) and 1 <= n <= 5:
        return True
    if (
        line.isupper() and 3 <= len(line) <= 40 and any(c.isalpha() for c in line)
        and n <= 6 and (" " in line or line.lower() in _SECTION_KEYWORDS)
    ):
        return True
    return False


@dataclass
class PipelineResult:
    meta: PaperMeta
    chunks: List[PipelineChunk]
    full_text: str = ""
    num_pages: int = 0
    extraction_method: str = "pymupdf"
    grobid_used: bool = False


def _extract_pages(pdf_path: str) -> Tuple[List[str], str]:
    """Return (per-page text list, method). pymupdf primary, pypdf fallback."""
    if fitz is not None:
        try:
            doc = fitz.open(pdf_path)
            pages = [doc[i].get_text("text") for i in range(doc.page_count)]
            doc.close()
            if any(p.strip() for p in pages):
                return pages, "pymupdf"
        except Exception as e:
            logger.warning(f"pymupdf failed for {pdf_path}: {e}")
    # Fallback: pypdf (page-by-page).
    try:
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")
        return pages, "pypdf"
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path}: {e}")
        return [], "none"


def _build_page_index(cleaned_pages: List[str]) -> Tuple[str, List[int]]:
    """Join pages and record cumulative end offsets for char->page mapping."""
    full = "\n".join(cleaned_pages)
    ends: List[int] = []
    pos = 0
    for i, page in enumerate(cleaned_pages):
        pos += len(page)
        ends.append(pos)
        if i < len(cleaned_pages) - 1:
            pos += 1  # the joining "\n"
    return full, ends


def _page_of_offset(offset: int, page_ends: List[int]) -> int:
    """1-based page number for a character offset in the joined text."""
    idx = bisect.bisect_right(page_ends, offset)
    return min(idx + 1, len(page_ends)) if page_ends else 1


def _detect_sections_with_pages(
    full_text: str, page_ends: List[int]
) -> List[Tuple[str, str, Optional[int]]]:
    """Detect ``(head, body, page_start)`` sections from cleaned text.

    Mirrors the legacy header detector but records the page each section starts
    on so chunks can carry ``page_start``.
    """
    lines = full_text.split("\n")
    # Char offset of the start of each line in full_text.
    line_offsets: List[int] = []
    pos = 0
    for ln in lines:
        line_offsets.append(pos)
        pos += len(ln) + 1  # + "\n"

    boundaries: List[Tuple[int, str]] = []  # (line_index, title)
    for i, raw in enumerate(lines):
        if _is_header_line(raw):
            boundaries.append((i, raw.strip()))

    if len(boundaries) < 2:
        return []

    sections: List[Tuple[str, str, Optional[int]]] = []
    for idx, (line_no, title) in enumerate(boundaries):
        end_line = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        body = "\n".join(lines[line_no + 1:end_line]).strip()
        if not body:
            continue
        page = _page_of_offset(line_offsets[line_no], page_ends)
        sections.append((title, reflow_paragraphs(body), page))
    return sections


def _grobid_sections_with_pages(
    grobid_sections: List[Tuple[str, str]], full_text: str, page_ends: List[int]
) -> List[Tuple[str, str, Optional[int]]]:
    """Attach a best-effort page_start to GROBID sections by locating their text."""
    out: List[Tuple[str, str, Optional[int]]] = []
    search_from = 0
    for head, body in grobid_sections:
        probe = (body or "")[:60].strip()
        page = None
        if probe:
            loc = full_text.find(probe, search_from)
            if loc == -1:
                loc = full_text.find(probe)
            if loc != -1:
                page = _page_of_offset(loc, page_ends)
                search_from = loc + len(probe)
        out.append((head, reflow_paragraphs(body), page))
    return out


def _extract_title_by_font(pdf_path: str) -> Optional[str]:
    """Heuristic title = the largest-font text block in the top of page 1.

    Works without GROBID/CrossRef and is far more reliable than line-length
    heuristics because paper titles are almost always the biggest text on the
    first page (masalah 3). Used only as a hint; GROBID/CrossRef take priority.
    """
    if fitz is None:
        return None
    try:
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            doc.close()
            return None
        page = doc[0]
        info = page.get_text("dict")
        page_height = page.rect.height or 1000
        doc.close()
    except Exception:
        return None

    spans = []  # (size, y, text)
    for block in info.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                t = (span.get("text") or "").strip()
                if not t:
                    continue
                spans.append((round(span.get("size", 0.0), 1),
                              span.get("bbox", [0, 0, 0, 0])[1], t))
    if not spans:
        return None
    top_spans = [s for s in spans if s[1] < page_height * 0.6] or spans
    max_size = max(s[0] for s in top_spans)
    title_spans = sorted(
        [s for s in top_spans if s[0] >= max_size - 0.5], key=lambda s: s[1]
    )
    title = re.sub(r"\s+", " ", " ".join(t for _, _, t in title_spans)).strip()
    if not (10 <= len(title) <= 300):
        return None
    if re.search(r"issn|doi|http|www\.|vol\.|©", title, re.IGNORECASE):
        return None
    return title


def _extract_own_doi(raw_pages: List[str]) -> Optional[str]:
    """Find the paper's OWN DOI (not a reference DOI from the bibliography).

    Uses the raw pages (before footer stripping) because a paper's DOI is often
    printed in a per-page footer. Preference order: a DOI on the first page, then
    the most frequently repeated DOI (footer), preferring article-like DOIs over
    ISSN-like journal DOIs. Reference-list DOIs (single occurrence, late in the
    document) are deliberately ignored to avoid resolving the wrong paper.
    """
    from .metadata_resolver import _DOI_RE  # local import to avoid a cycle

    def _clean(d: str) -> str:
        return d.rstrip(".,;)").lower()

    def _issn_like(doi: str) -> bool:
        suffix = doi.split("/", 1)[1] if "/" in doi else ""
        return bool(re.fullmatch(r"\d{4}-\d{3}[\dxX]", suffix))

    if not raw_pages:
        return None
    first_page = raw_pages[0] or ""
    first = [_clean(m.group(0)) for m in _DOI_RE.finditer(first_page)]
    first = sorted(set(first), key=lambda d: (_issn_like(d), -len(d)))
    if first:
        return first[0]

    from collections import Counter

    counts: Counter = Counter()
    for page in raw_pages:
        for m in _DOI_RE.finditer(page or ""):
            counts[_clean(m.group(0))] += 1
    repeated = [d for d, c in counts.items() if c >= 2]
    if repeated:
        repeated.sort(key=lambda d: (_issn_like(d), -counts[d], -len(d)))
        return repeated[0]
    return None


def _pages_from_lines(lines: List[LineInfo]) -> List[str]:
    """Reconstruct per-page text strings from layout lines (for cleaning/DOI)."""
    by_page: dict = {}
    for ln in lines:
        by_page.setdefault(ln.page, []).append(ln.text)
    if not by_page:
        return []
    return ["\n".join(by_page.get(p, [])) for p in range(1, max(by_page) + 1)]


def _layout_is_header(text: str, size: float, bold: bool, body_size: float) -> bool:
    """A layout line is a header if visually distinct (bigger/bold) and short."""
    words = text.split()
    if not (1 <= len(words) <= 12):
        return False
    if text[-1] in ".,;":
        return False
    if _is_false_header(text):
        return False
    if re.search(r"\.\s+\S", text):  # internal sentence -> prose, not a header
        return False
    if size >= body_size + 1.0:
        return True
    if bold and size >= body_size - 0.1 and len(words) <= 8:
        return True
    return False


def _sections_from_layout(
    lines: List[LineInfo],
) -> List[Tuple[Optional[str], str, Optional[int]]]:
    """Font-aware sectioning: detect headers by size/weight, not keywords."""
    repeated = find_repeated_lines(_pages_from_lines(lines))
    cleaned: List[LineInfo] = []
    for ln in lines:
        if is_noise_line(ln.text, repeated):
            continue
        text = dehyphenate(normalize_unicode(ln.text)).strip()
        if text:
            cleaned.append(LineInfo(text=text, size=ln.size, bold=ln.bold, page=ln.page))
    if not cleaned:
        return []

    bsize = body_font_size(cleaned)
    sections: List[Tuple[Optional[str], str, Optional[int]]] = []
    cur_head: Optional[str] = None
    cur_lines: List[str] = []
    cur_page: Optional[int] = None

    def _flush():
        nonlocal cur_head, cur_lines, cur_page
        if cur_lines:
            sections.append((cur_head, reflow_paragraphs("\n".join(cur_lines)), cur_page))
        cur_head, cur_lines, cur_page = None, [], None

    for ln in cleaned:
        if (
            _layout_is_header(ln.text, ln.size, ln.bold, bsize)
            or _is_header_line(ln.text)
        ):
            _flush()
            cur_head = ln.text
            cur_page = ln.page
        else:
            if cur_page is None:
                cur_page = ln.page
            cur_lines.append(ln.text)
    _flush()
    return sections


def _postprocess_sections(
    sections: List[Tuple[Optional[str], str, Optional[int]]],
    min_section_chars: int = 120,
    min_other_chars: int = 600,
) -> List[Tuple[Optional[str], str, Optional[int]]]:
    """Heal mid-sentence splits and merge tiny sections.

    * A body that begins with a lowercase letter is a continuation of the
      previous section (a spurious header split a sentence): merge it back,
      preserving the dropped header word.
    * Very short sections (stray captions, one-line noise) are folded into the
      previous section so they do not become fragment chunks.

    Non-canonical sections (subsection/caption headers that normalize to
    ``other``) are held to the much larger ``min_other_chars`` budget — roughly
    150 tokens — because on their own they yield context-poor fragment chunks.
    Recognised sections keep the small floor so a genuinely brief abstract or
    conclusion survives with its own label.
    """
    healed: List[Tuple[Optional[str], str, Optional[int]]] = []
    for head, body, page in sections:
        if healed and body[:1].islower():
            ph, pb, pp = healed[-1]
            healed[-1] = (ph, " ".join(x for x in (pb, head, body) if x).strip(), pp)
        else:
            healed.append((head, body, page))

    merged: List[Tuple[Optional[str], str, Optional[int]]] = []
    for head, body, page in healed:
        floor = min_section_chars if normalize_section(head) != "other" else min_other_chars
        if merged and len(body) < floor:
            ph, pb, pp = merged[-1]
            merged[-1] = (ph, (pb + "\n\n" + body).strip(), pp)
        else:
            merged.append((head, body, page))
    return merged


# Main-body sections whose label propagates to their (non-canonical) subsections.
_PROPAGATING_SECTIONS = {
    "introduction", "related_work", "methods", "results", "discussion",
    "conclusion", "references",
}


def _apply_section_inheritance(
    sections: List[Tuple[Optional[str], str, Optional[int]]],
) -> List[Tuple[Optional[str], str, str, Optional[int]]]:
    """Resolve each section's canonical label, letting subsections inherit.

    Font/keyword detection also finds subsection headers ("Study Population",
    "Figure 1: ...") that normalize to ``other``. Rather than mislabel their
    (methodology/results) content as ``other`` (masalah 5), a subsection inherits
    the current main section. ``abstract`` does not propagate (it is a single
    standalone block), so citation blocks after it stay ``other``.
    """
    out: List[Tuple[Optional[str], str, str, Optional[int]]] = []
    current = "other"
    for head, body, page in sections:
        norm = normalize_section(head)
        if norm != "other":
            effective = norm
            current = norm if norm in _PROPAGATING_SECTIONS else "other"
        else:
            effective = current
        out.append((head, effective, body, page))
    return out


def process_pdf(
    pdf_path: str,
    source: Optional[str] = None,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
) -> PipelineResult:
    """Process a single PDF into (metadata, token-aware chunks)."""
    source = source or Path(pdf_path).name

    layout_lines = extract_layout_lines(pdf_path)
    use_layout = bool(layout_lines) and has_font_variation(layout_lines)
    if use_layout:
        raw_pages = _pages_from_lines(layout_lines)
        method = "pymupdf_layout"
    else:
        raw_pages, method = _extract_pages(pdf_path)

    cleaned_pages = clean_pages(raw_pages)
    full_text, page_ends = _build_page_index(cleaned_pages)

    quality = assess_quality(full_text)
    if quality == "poor":
        logger.warning(f"{source}: poor extraction quality (method={method})")

    meta, grobid_sections = resolve_metadata(
        pdf_path, full_text, source, extraction_quality=quality,
        title_hint=_extract_title_by_font(pdf_path),
        doi_hint=_extract_own_doi(raw_pages),
    )

    # Section structure: GROBID IMRaD > font-aware layout > text headers > whole.
    grobid_used = False
    if grobid_sections:
        sections = _grobid_sections_with_pages(grobid_sections, full_text, page_ends)
        grobid_used = True
    elif use_layout:
        sections = _sections_from_layout(layout_lines)
        if not sections:
            sections = _detect_sections_with_pages(full_text, page_ends)
    else:
        sections = _detect_sections_with_pages(full_text, page_ends)
    if not sections:
        # No detectable structure: treat the whole doc as one "other" section.
        sections = [(None, reflow_paragraphs(full_text), 1 if page_ends else None)]

    sections = _postprocess_sections(sections)
    resolved_sections = _apply_section_inheritance(sections)

    chunks = chunk_document(
        resolved_sections,
        meta,
        target_tokens=target_tokens,
        max_tokens=max_tokens,
        overlap_ratio=overlap_ratio,
    )
    chunks = deduplicate_chunks(chunks)
    # Re-index after dedup so chunk_index stays contiguous.
    for new_idx, chunk in enumerate(chunks):
        chunk.chunk_index = new_idx
        chunk.chunk_id = chunk.make_chunk_id()

    return PipelineResult(
        meta=meta,
        chunks=chunks,
        full_text=full_text,
        num_pages=len(cleaned_pages),
        extraction_method=method,
        grobid_used=grobid_used,
    )


# ────────────────────────────────────────────────────────────────
#  Backwards-compatible adapter for the FastAPI ingestion path
# ────────────────────────────────────────────────────────────────

class _CompatChunk:
    """Mimics the legacy ``DocumentChunk`` (``.content``/``.chunk_index``/``.metadata``)
    but carries the full new-schema metadata so the vector store keeps every field."""

    def __init__(self, pc: PipelineChunk, job_id: Optional[str] = None):
        self.content = pc.text
        self.chunk_index = pc.chunk_index
        self.metadata = pc.to_vector_metadata(job_id)


class _CompatDoc:
    """Mimics the legacy ``ProcessedDocument`` for a drop-in ingestion swap."""

    def __init__(self, result: "PipelineResult", job_id: Optional[str] = None):
        self.title = result.meta.paper_title or result.meta.source
        self.content = result.full_text
        self.metadata = {
            "year": result.meta.year,
            "doi": result.meta.doi,
            "language": result.meta.language,
            "authors": result.meta.authors,
            "extraction_method": result.extraction_method,
            "extraction_quality": result.meta.extraction_quality,
            "metadata_source": result.meta.metadata_source,
            "ocr_used": result.extraction_method == "ocr",
            "grobid_used": result.grobid_used,
        }
        self.chunks = [_CompatChunk(c, job_id) for c in result.chunks]


def process_pdf_as_document(
    pdf_path: str, source: Optional[str] = None, job_id: Optional[str] = None
) -> _CompatDoc:
    """Run the upgraded pipeline and return a legacy-shaped document.

    Lets the FastAPI ingestion path adopt the new extraction/chunking/metadata
    with a minimal diff while persisting the full new-schema chunk metadata.
    """
    result = process_pdf(pdf_path, source=source)
    return _CompatDoc(result, job_id=job_id)
