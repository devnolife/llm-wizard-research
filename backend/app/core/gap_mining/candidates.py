"""Layer 1 — section-targeted, multilingual gap candidate selection (no LLM).

Thanks to TAHAP 1's ``section_normalized``, we can target the sections where
authors state gaps (conclusion/discussion) instead of scanning all chunks with
regex (the old approach found 49 noisy hits). We also keep any chunk that
matches a multilingual gap phrase, so explicit gaps stated elsewhere are caught.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# Multilingual gap-phrase cues (spec TAHAP 2 A.1).
GAP_PHRASES_EN = [
    r"future work", r"further research", r"future studies", r"future research",
    r"open problem", r"research gap", r"limitation", r"remains? unexplored",
    r"not yet been", r"little attention", r"has not been", r"have not been",
    r"remains? to be", r"should be (explored|investigated|studied|addressed)",
    r"under-?explored", r"under-?studied", r"lack of", r"scarce", r"few studies",
    r"no (study|research|work) has",
]
GAP_PHRASES_ID = [
    r"penelitian selanjutnya", r"penelitian lebih lanjut", r"penelitian mendatang",
    r"belum dilakukan", r"belum pernah", r"belum banyak", r"belum ada",
    r"keterbatasan penelitian", r"keterbatasan", r"saran penelitian", r"saran",
    r"masih terbatas", r"perlu diteliti", r"perlu dikaji", r"dapat dikembangkan",
]

_PHRASE_RE = re.compile(
    "|".join(GAP_PHRASES_EN + GAP_PHRASES_ID), re.IGNORECASE
)

# Sections where authors typically state gaps/limitations/future work.
_TARGET_SECTIONS = {"conclusion", "discussion"}


def matched_phrases(text: str) -> List[str]:
    """Return the distinct gap phrases found in ``text`` (for provenance)."""
    return sorted({m.group(0).lower() for m in _PHRASE_RE.finditer(text or "")})


def select_candidates(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pick gap-bearing candidate chunks from a chunks JSONL (list of dicts).

    A chunk is a candidate when it is not a reference AND any of:
      * its section is conclusion/discussion (where gaps are stated), or
      * it matches a multilingual gap phrase, or
      * it is an abstract chunk, or
      * it is one of the paper's last two chunks (conclusions/limitations live at
        the end even when section detection labelled them ``other``).

    The last two rules give coverage to papers whose structure was not detected
    (all-``other`` sections), so gap mining is not limited to well-structured PDFs.
    Candidates are de-duplicated by ``chunk_id``.
    """
    from collections import defaultdict

    by_source: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in chunks:
        if not c.get("is_reference"):
            by_source[c.get("source")].append(c)

    selected: Dict[Any, Dict[str, Any]] = {}

    def _add(chunk: Dict[str, Any], reason: str, phrases=None):
        cid = chunk.get("chunk_id") or id(chunk)
        if cid in selected:
            if reason not in selected[cid]["candidate_reason"]:
                selected[cid]["candidate_reason"] += f",{reason}"
            return
        cand = dict(chunk)
        cand["candidate_reason"] = reason
        cand["matched_phrases"] = phrases or []
        selected[cid] = cand

    for c in chunks:
        if c.get("is_reference"):
            continue
        text = c.get("text") or ""
        if len(text) < 40:
            continue
        section = c.get("section_normalized")
        phrases = matched_phrases(text)
        if section in _TARGET_SECTIONS:
            _add(c, f"section:{section}", phrases)
        elif phrases:
            _add(c, "phrase", phrases)

    # Coverage rules: abstract + first two introduction chunks + last two chunks.
    # Introductions and conclusions are the two places authors most often state a
    # gap (explicitly or implicitly); the tail rule rescues papers whose sections
    # were not detected (all-``other``).
    for src, cs in by_source.items():
        ordered = sorted(cs, key=lambda c: c.get("chunk_index", 0))
        for c in ordered:
            if c.get("section_normalized") == "abstract" and len(c.get("text") or "") >= 80:
                _add(c, "abstract")
        intro = [c for c in ordered if c.get("section_normalized") == "introduction"]
        for c in intro[:2]:
            if len(c.get("text") or "") >= 80:
                _add(c, "introduction")
        for c in ordered[-2:]:
            if len(c.get("text") or "") >= 80:
                _add(c, "tail")

    return list(selected.values())


def with_context(
    candidate: Dict[str, Any], by_source: Dict[str, List[Dict[str, Any]]]
) -> str:
    """Build the LLM context: previous + candidate + next chunk (same source)."""
    src = candidate.get("source")
    idx = candidate.get("chunk_index")
    siblings = by_source.get(src, [])
    ordered = sorted(siblings, key=lambda c: c.get("chunk_index", 0))
    pos = next((i for i, c in enumerate(ordered) if c.get("chunk_index") == idx), None)
    if pos is None:
        return candidate.get("text") or ""
    lo = max(0, pos - 1)
    hi = min(len(ordered), pos + 2)
    return "\n\n".join((ordered[i].get("text") or "") for i in range(lo, hi))
