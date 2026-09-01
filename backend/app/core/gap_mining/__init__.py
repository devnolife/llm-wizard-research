"""Research-gap mining on top of clean, sectioned chunks (TAHAP 2).

Two layers:
  * L1 (:mod:`.candidates`) — cheap, no-LLM: pick chunks likely to state a gap
    (conclusion/discussion sections + multilingual gap-phrase matches).
  * L2 (:mod:`.extractor`) — an LLM (Copilot) turns candidates into structured,
    verbatim-grounded gap records.

Every gap keeps a verbatim ``gap_statement`` verified against its source chunk
(:mod:`.verify`) so claims are traceable and hallucinations are rejected — the
per-claim grounding idea from PaperQA2, implemented with the existing
``gap_detection.quote_grounding`` fuzzy matcher.
"""

from .candidates import GAP_PHRASES_EN, GAP_PHRASES_ID, select_candidates

__all__ = ["select_candidates", "GAP_PHRASES_EN", "GAP_PHRASES_ID"]
