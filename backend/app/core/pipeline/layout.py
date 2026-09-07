"""Font-aware PDF layout extraction (TAHAP 1 support for masalah 5).

Header detection from raw text is unreliable on narrow multi-column PDFs: prose
gets shattered into short lines, and many begin with a section keyword
("analysis", "findings", ...), producing false section boundaries that cut
sentences in half. Real section headers are almost always visually distinct —
larger and/or bold. This module reads pymupdf's ``dict`` layout so the pipeline
can detect headers by font size/weight, with the text heuristic as a fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from loguru import logger

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None

_BOLD_FLAG = 1 << 4  # pymupdf span flag bit for bold
# Horizontal gap between two spans (as a fraction of font size) that means a word
# break. Kerning/font changes inside a word leave gaps far below this.
_WORD_GAP_RATIO = 0.12


@dataclass
class LineInfo:
    text: str
    size: float       # dominant (max) font size on the line
    bold: bool
    page: int         # 1-based page number


def join_spans(spans: List[dict]) -> str:
    """Concatenate a line's spans, restoring the spaces ``dict`` mode drops.

    Many PDF generators position each word as its own span without a space
    glyph; joining span texts directly then glues words together
    (``Weproposeanewsimplenetworkarchitecture``). Whenever neither side already
    has whitespace and the spans are visibly apart, a space is inserted.
    """
    parts: List[str] = []
    prev_bbox = None
    for span in spans:
        text = span.get("text", "")
        if not text:
            continue
        bbox = span.get("bbox")
        if parts and not text[0].isspace() and not parts[-1][-1].isspace():
            gap = (bbox[0] - prev_bbox[2]) if (bbox and prev_bbox) else 0.0
            size = float(span.get("size") or 0.0)
            if gap > max(_WORD_GAP_RATIO * size, 0.5):
                parts.append(" ")
        parts.append(text)
        prev_bbox = bbox or prev_bbox
    return "".join(parts)


def extract_layout_lines(pdf_path: str) -> List[LineInfo]:
    """Return the document's text lines with font size + bold flag per line.

    Empty list when pymupdf is unavailable or the PDF has no usable text layer
    (the caller then falls back to plain-text extraction).
    """
    if fitz is None:
        return []
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:  # pragma: no cover
        logger.warning(f"pymupdf could not open {pdf_path}: {e}")
        return []

    lines: List[LineInfo] = []
    try:
        for pno in range(doc.page_count):
            page = doc[pno]
            data = page.get_text("dict")
            for block in data.get("blocks", []):
                for line in block.get("lines", []):
                    spans = [s for s in line.get("spans", []) if (s.get("text") or "").strip()]
                    if not spans:
                        continue
                    text = join_spans(spans).strip()
                    if not text:
                        continue
                    size = max((s.get("size", 0.0) for s in spans), default=0.0)
                    bold = any(
                        (s.get("flags", 0) & _BOLD_FLAG)
                        or ("bold" in (s.get("font", "") or "").lower())
                        for s in spans
                    )
                    lines.append(LineInfo(text=text, size=round(size, 1),
                                          bold=bold, page=pno + 1))
    finally:
        doc.close()
    return lines


def body_font_size(lines: List[LineInfo]) -> float:
    """Estimate the body-text font size = size covering the most characters."""
    weight: dict = {}
    for ln in lines:
        weight[ln.size] = weight.get(ln.size, 0) + len(ln.text)
    if not weight:
        return 0.0
    return max(weight.items(), key=lambda kv: kv[1])[0]


def has_font_variation(lines: List[LineInfo]) -> bool:
    """True when there is enough font-size variety for size-based header detection."""
    sizes = {ln.size for ln in lines if ln.size > 0}
    return len(sizes) >= 2
