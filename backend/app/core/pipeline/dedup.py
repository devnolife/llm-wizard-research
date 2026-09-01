"""Exact-duplicate chunk removal (TAHAP 1 masalah 9).

The legacy output contained chunks with byte-identical text. We drop later
duplicates by a normalised-text hash, keeping the first occurrence and its
``chunk_index`` order.
"""

from __future__ import annotations

import hashlib
import re
from typing import List

from loguru import logger

from .schema import PipelineChunk


def _text_hash(text: str) -> str:
    norm = re.sub(r"\s+", " ", (text or "").strip().lower())
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()


def deduplicate_chunks(chunks: List[PipelineChunk]) -> List[PipelineChunk]:
    """Return chunks with byte/whitespace-identical duplicates removed."""
    seen = set()
    out: List[PipelineChunk] = []
    dropped = 0
    for chunk in chunks:
        h = _text_hash(chunk.text)
        if h in seen:
            dropped += 1
            continue
        seen.add(h)
        out.append(chunk)
    if dropped:
        logger.debug(f"Deduplicated {dropped} identical chunk(s)")
    return out
