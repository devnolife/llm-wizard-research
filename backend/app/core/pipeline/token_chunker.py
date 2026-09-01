"""Token-aware, sentence-safe, section-bounded chunker (TAHAP 1 bagian B).

Fixes:
  * masalah 1 — never cut a chunk in the middle of a sentence. Chunks are built
    by accumulating whole sentences.
  * masalah 2 — consistent overlap. Every chunk (except the first of a section)
    begins with the trailing sentences of the previous chunk, sized to
    ~10-15% of the target token budget, so consecutive chunks always overlap.

Chunks never cross a section boundary. Sizing is measured in TOKENS (tiktoken),
targeting 256-512 tokens per chunk.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

from loguru import logger

from .schema import PaperMeta, PipelineChunk
from .section_normalizer import classify_reference

try:
    import tiktoken

    _ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - tiktoken ships wheels; fallback just in case
    _ENCODER = None

try:
    import pysbd

    _SEGMENTER = pysbd.Segmenter(language="en", clean=False)
except Exception:  # pragma: no cover
    _SEGMENTER = None


DEFAULT_TARGET_TOKENS = 384   # middle of the 256-512 band
DEFAULT_MAX_TOKENS = 512
DEFAULT_MIN_TOKENS = 64
DEFAULT_OVERLAP_RATIO = 0.125  # 12.5% -> within the required 10-15%
# Absolute floor: chunks smaller than this are noise (spurious headers, stray
# table cells) and are never emitted on their own.
HARD_FLOOR_TOKENS = 24
# A single unsplittable "sentence" (usually a flattened table with no periods)
# is kept intact up to this ceiling rather than cut mid-content; only genuinely
# pathological blobs beyond it are split on word boundaries.
SENTENCE_HARD_CEILING = 1100


def count_tokens(text: str) -> int:
    if not text:
        return 0
    if _ENCODER is not None:
        return len(_ENCODER.encode(text))
    # crude fallback ~ 0.75 words/token
    return max(1, int(len(text.split()) / 0.75))


def split_sentences(text: str) -> List[str]:
    """Split into sentences without ever losing text (masalah 1)."""
    text = (text or "").strip()
    if not text:
        return []
    if _SEGMENTER is not None:
        try:
            sents = [s.strip() for s in _SEGMENTER.segment(text) if s.strip()]
            if sents:
                return sents
        except Exception:
            pass
    # Fallback splitter on sentence-final punctuation.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Þ0-9(\"'])", text)
    return [p.strip() for p in parts if p.strip()]


def _split_long_sentence(sentence: str, ceiling: int) -> List[str]:
    """Split only genuinely pathological blobs, on WORD boundaries.

    Normal prose sentences (and flattened tables up to ``ceiling`` tokens) are
    returned intact so a chunk never ends mid-sentence/mid-word. Only content
    above ``ceiling`` (e.g. an entire multi-page table with no punctuation) is
    broken, and then on spaces rather than inside a token/word.
    """
    if count_tokens(sentence) <= ceiling:
        return [sentence]
    words = sentence.split()
    out: List[str] = []
    buf: List[str] = []
    for word in words:
        buf.append(word)
        if count_tokens(" ".join(buf)) >= ceiling:
            out.append(" ".join(buf))
            buf = []
    if buf:
        out.append(" ".join(buf))
    return [p for p in out if p]


def _overlap_sentences(
    sentences: Sequence[str], overlap_tokens: int
) -> List[str]:
    """Trailing sentences of a chunk whose token sum ~= overlap_tokens."""
    if overlap_tokens <= 0:
        return []
    picked: List[str] = []
    total = 0
    for sent in reversed(sentences):
        if total >= overlap_tokens and picked:
            break
        picked.insert(0, sent)
        total += count_tokens(sent)
    # Never let the overlap swallow the whole previous chunk.
    if len(picked) >= len(sentences):
        picked = picked[1:]
    return picked


def _pack_sentences(
    sentences: Sequence[str],
    target_tokens: int,
    max_tokens: int,
    min_tokens: int,
) -> List[List[str]]:
    """Group whole sentences into 256-512 token groups (no overlap yet).

    A small final remainder is merged back into the previous group so we never
    emit a tail fragment (masalah 1/2 — no lost or truncated content).
    """
    groups: List[List[str]] = []
    cur: List[str] = []
    cur_tok = 0
    for sent in sentences:
        st = count_tokens(sent)
        if cur and cur_tok + st > max_tokens:
            groups.append(cur)
            cur, cur_tok = [], 0
        cur.append(sent)
        cur_tok += st
        if cur_tok >= target_tokens:
            groups.append(cur)
            cur, cur_tok = [], 0
    if cur:
        rem = sum(count_tokens(s) for s in cur)
        if groups and rem < min_tokens:
            groups[-1].extend(cur)  # merge tiny tail into previous group
        else:
            groups.append(cur)
    return groups


def chunk_document(
    sections: Sequence[Tuple[Optional[str], str, str, Optional[int]]],
    meta: PaperMeta,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    min_tokens: int = DEFAULT_MIN_TOKENS,
    overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
) -> List[PipelineChunk]:
    """Chunk a document given its resolved sections.

    Each section is ``(section_raw, section_normalized, section_text,
    page_start)`` — the normalized label is resolved upstream (with subsection
    inheritance), so it is used as-is here.

    Two phases: (1) pack whole sentences into token-sized groups within each
    section, merging any tiny tail back; (2) prepend the trailing sentences of
    the previous group as overlap. Chunks never cross a section boundary, never
    cut a sentence, and always overlap their predecessor.
    """
    overlap_tokens = int(round(target_tokens * overlap_ratio))
    chunks: List[PipelineChunk] = []
    chunk_index = 0

    for section_raw, section_norm, section_text, page_start in sections:
        sentences = split_sentences(section_text)
        expanded: List[str] = []
        for sent in sentences:
            expanded.extend(_split_long_sentence(sent, SENTENCE_HARD_CEILING))
        sentences = expanded
        if not sentences:
            continue

        groups = _pack_sentences(sentences, target_tokens, max_tokens, min_tokens)

        for gi, group in enumerate(groups):
            if gi > 0:
                overlap = _overlap_sentences(groups[gi - 1], overlap_tokens)
                group_sents = list(overlap) + list(group)
            else:
                group_sents = list(group)
            text = " ".join(group_sents).strip()
            tok = count_tokens(text)
            # Drop lone noise fragments (e.g. "NATURE &") but keep genuine short
            # sections (a brief abstract) that clear the hard floor.
            if tok < HARD_FLOOR_TOKENS:
                continue
            is_ref = classify_reference(section_norm, text)
            chunks.append(PipelineChunk(
                source=meta.source,
                chunk_index=chunk_index,
                text=text,
                token_count=tok,
                section_raw=section_raw,
                section_normalized=section_norm,
                is_reference=is_ref,
                page_start=page_start,
                doi=meta.doi,
                paper_title=meta.paper_title,
                authors=list(meta.authors or []),
                year=meta.year,
                language=meta.language,
                extraction_quality=meta.extraction_quality,
            ))
            chunk_index += 1

    logger.debug(
        f"{meta.source}: chunked into {len(chunks)} token-aware chunks "
        f"(target={target_tokens}, max={max_tokens}, overlap~{overlap_tokens} tok)"
    )
    return chunks
