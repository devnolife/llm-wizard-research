"""Verbatim grounding for extracted gaps (TAHAP 2 A.2 anti-hallucination).

Every ``gap_statement`` must actually appear (verbatim, allowing minor OCR/space
noise) in its source chunk(s). Reuses the fuzzy matcher already used for weakness
grounding so behaviour is consistent across the codebase.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..gap_detection.quote_grounding import QUOTE_MATCH_THRESHOLD, fuzzy_contains


def verify_gap_statement(statement: str, context_text: str) -> float:
    """Return the best fuzzy match score (0-1) of ``statement`` in the context."""
    if not statement or not context_text:
        return 0.0
    return fuzzy_contains(statement, context_text)


def is_grounded(statement: str, context_text: str, threshold: float = QUOTE_MATCH_THRESHOLD) -> bool:
    """True when the statement is verbatim-present enough to be trustworthy."""
    return verify_gap_statement(statement, context_text) >= threshold


def verify_gaps(
    gaps: List[Dict[str, Any]],
    by_source: Dict[str, List[Dict[str, Any]]],
    threshold: float = QUOTE_MATCH_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Attach a ``grounding_score`` to each gap and drop ungrounded ones.

    The statement is checked against every chunk of its source paper (the LLM
    sees a candidate plus one chunk of context on each side, so a verbatim quote
    may come from a neighbouring chunk). The best-matching chunk id is recorded
    in ``evidence_chunk_ids`` so the gap points at the exact evidence.
    """
    kept: List[Dict[str, Any]] = []
    for gap in gaps:
        statement = gap.get("gap_statement") or ""
        source_chunks = by_source.get(gap.get("source"), [])
        best_score = 0.0
        best_id = None
        for chunk in source_chunks:
            score = verify_gap_statement(statement, chunk.get("text") or "")
            if score > best_score:
                best_score = score
                best_id = chunk.get("chunk_id")
                if best_score >= 0.999:
                    break
        gap["grounding_score"] = round(best_score, 3)
        if best_score >= threshold:
            if best_id:
                gap["evidence_chunk_ids"] = [best_id]
            kept.append(gap)
    return kept
