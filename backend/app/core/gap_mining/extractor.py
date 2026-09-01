"""Layer 2 — structured, grounded gap extraction with an LLM (TAHAP 2 A.2).

Each candidate (plus one chunk of context on each side) is sent to the LLM
(Copilot by default) which returns structured gap records. The prompt is adapted
from FutureGen: extract only genuine future-work / limitation / gap statements,
copy the ``gap_statement`` VERBATIM from the text (so it can be verified), and
never invent content.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from ...services import copilot_client

GAP_TYPES = {"explicit_future_work", "stated_limitation", "implicit_gap"}
TOPICS = {"image_forensics", "mobile_forensics", "legal", "tools", "multimedia", "other"}

SYSTEM_PROMPT = (
    "You are a meticulous research assistant that extracts research gaps, stated "
    "limitations, and future-work directions from scientific paper text. You never "
    "invent content: every gap_statement MUST be copied verbatim from the provided "
    "text. If the text states no gap/limitation/future work, return an empty list."
)

_PROMPT_TEMPLATE = """From the paper text below, extract every research gap, stated limitation, or \
future-work direction the AUTHORS themselves express.

Return ONLY a JSON array (no prose). Each element:
{{
  "gap_type": "explicit_future_work | stated_limitation | implicit_gap",
  "gap_statement": "VERBATIM sentence(s) copied exactly from the text below",
  "gap_paraphrase": "one-sentence paraphrase in Bahasa Indonesia",
  "topic": "image_forensics | mobile_forensics | legal | tools | multimedia | other"
}}

Rules:
- gap_statement MUST be an exact substring of the text (do not fix typos/spacing).
- Prefer explicit statements; only use "implicit_gap" when a gap is clearly implied.
- If there is no genuine gap, return [].

PAPER: {title} ({year})
TEXT:
\"\"\"
{text}
\"\"\"
"""


def _default_generate(prompt: str, system: str) -> Optional[str]:
    result = copilot_client.generate(prompt, system=system, json_mode=True)
    return result[0] if result else None


def _parse_json_array(text: str) -> List[Dict[str, Any]]:
    """Best-effort parse of an LLM JSON reply into a list of dicts."""
    if not text:
        return []
    cleaned = text.strip()
    # Strip ```json fences if present.
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to locate the first JSON array in the text.
        m = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    if isinstance(data, dict):
        data = [data]
    return [d for d in data if isinstance(d, dict)]


def _normalize_gap(raw: Dict[str, Any], candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate + enrich a raw LLM gap with paper metadata + evidence id."""
    statement = (raw.get("gap_statement") or "").strip()
    if len(statement) < 15:
        return None
    gap_type = raw.get("gap_type")
    if gap_type not in GAP_TYPES:
        gap_type = "implicit_gap"
    topic = raw.get("topic")
    if topic not in TOPICS:
        topic = "other"
    return {
        "source": candidate.get("source"),
        "paper_title": candidate.get("paper_title"),
        "year": candidate.get("year"),
        "doi": candidate.get("doi"),
        "gap_type": gap_type,
        "gap_statement": statement,
        "gap_paraphrase": (raw.get("gap_paraphrase") or "").strip(),
        "topic": topic,
        "evidence_chunk_ids": [candidate.get("chunk_id")] if candidate.get("chunk_id") else [],
        "candidate_reason": candidate.get("candidate_reason"),
    }


def extract_gaps_from_candidate(
    candidate: Dict[str, Any],
    context_text: str,
    generate_fn: Callable[[str, str], Optional[str]] = _default_generate,
) -> List[Dict[str, Any]]:
    """Run the LLM on one candidate and return normalized gap dicts."""
    prompt = _PROMPT_TEMPLATE.format(
        title=candidate.get("paper_title") or candidate.get("source") or "",
        year=candidate.get("year") or "n/a",
        text=context_text[:6000],
    )
    try:
        reply = generate_fn(prompt, SYSTEM_PROMPT)
    except Exception as e:  # pragma: no cover - network
        logger.warning(f"LLM gap extraction failed for {candidate.get('source')}: {e}")
        return []
    gaps = []
    for raw in _parse_json_array(reply or ""):
        norm = _normalize_gap(raw, candidate)
        if norm:
            gaps.append(norm)
    return gaps
