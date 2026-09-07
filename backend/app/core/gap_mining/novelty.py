"""Novelty check for mined gaps against recent literature (TAHAP 3).

For each gap we query recent (>= 2024) papers and decide whether the gap is
still ``open``, ``partially_addressed``, or ``addressed``. OpenAlex is the
primary source (reachable, no key); Semantic Scholar is queried best-effort and
skipped on failure. Responses are cached on disk (via ``http_cache``) so re-runs
do not re-query, and requests are rate-limited with backoff.

When the literature source cannot be queried at all (quota 429, network down)
the gap is labelled ``unchecked`` — never ``open`` — so an outage does not read
as "every gap is novel". OpenAlex's free tier is credit-based (~100 searches per
day per IP/mailto); a 429 with a long Retry-After puts the host in cooldown and
the remaining gaps are marked ``unchecked`` immediately.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from ...services.paper_apis import http_cache
from ...services.paper_apis.openalex import OpenAlexAPI

NOVELTY_STATUSES = ("open", "partially_addressed", "addressed", "unchecked")

# A recent paper "strongly" matches a gap when at least this share of the gap's
# keywords appears in its title+abstract. 3+ strong matches => addressed,
# 1-2 => partially_addressed, 0 => open.
STRONG_MATCH_THRESHOLD = 0.5

_STOPWORDS = set(
    """the a an and or of to in for on with from by as is are be this that these those
    we our their study paper research results method approach using used based can may
    will more most using dan yang di ke untuk pada dari adalah ini itu serta atau dengan
    penelitian studi metode hasil dapat lebih akan masih belum future work gap limitation
    keterbatasan""".split()
)

_TOPIC_TERMS = {
    "image_forensics": "image forensics tampering detection",
    "mobile_forensics": "mobile forensics android smartphone",
    "legal": "legal admissibility court evidence",
    "tools": "forensic tools software",
    "multimedia": "multimedia video audio forensics",
}


def build_keywords(gap: Dict[str, Any], max_terms: int = 8) -> str:
    """Build an English search query from the gap statement + topic terms.

    Uses the verbatim ``gap_statement`` (usually English, matching the mostly
    English recent literature) rather than the Indonesian paraphrase, so overlap
    scoring against OpenAlex results is meaningful.
    """
    text = str(gap.get("gap_statement") or "").lower()
    if len(text) < 15:
        text += " " + str(gap.get("gap_paraphrase") or "").lower()
    words = re.findall(r"[a-z][a-z\-]{2,}", text)
    freq: Dict[str, int] = {}
    for w in words:
        if w in _STOPWORDS:
            continue
        freq[w] = freq.get(w, 0) + 1
    top = sorted(freq, key=lambda w: (-freq[w], w))[:max_terms]
    topic_terms = _TOPIC_TERMS.get(gap.get("topic"), "")
    return " ".join(top + topic_terms.split()).strip() or (gap.get("paper_title") or "")


def _overlap_score(query: str, paper: Any) -> float:
    terms = {t for t in re.findall(r"[a-z\-]{3,}", query.lower()) if t not in _STOPWORDS}
    if not terms:
        return 0.0
    hay = f"{getattr(paper, 'title', '') or ''} {getattr(paper, 'abstract', '') or ''}".lower()
    return sum(1 for t in terms if t in hay) / len(terms)


def classify_novelty(
    gap: Dict[str, Any],
    openalex: Optional[OpenAlexAPI] = None,
    from_date: str = "2024-01-01",
    max_results: int = 8,
    strong_threshold: float = STRONG_MATCH_THRESHOLD,
    s2_search_fn: Optional[Callable[[str], List[Any]]] = None,
) -> Dict[str, Any]:
    """Return novelty fields for a single gap.

    ``s2_search_fn`` (optional) lets a caller add Semantic Scholar results;
    it is called best-effort and any exception is swallowed.
    """
    openalex = openalex or OpenAlexAPI()
    query = build_keywords(gap)

    papers: Optional[List[Any]] = None
    try:
        papers = openalex.search_recent(query, from_date=from_date, max_results=max_results)
    except Exception as e:  # pragma: no cover - network
        logger.warning(f"OpenAlex query failed: {e}")

    s2_papers: Optional[List[Any]] = None
    if s2_search_fn is not None:
        try:
            s2_papers = list(s2_search_fn(query) or [])
        except Exception as e:  # pragma: no cover
            logger.debug(f"Semantic Scholar skipped: {e}")

    checked_at = datetime.now().isoformat(timespec="seconds")
    if papers is None and s2_papers is None:
        cooldown = http_cache.host_cooldown(openalex.BASE_URL)
        reason = cooldown["reason"] if cooldown else "sumber literatur tidak dapat dihubungi"
        return {
            "novelty_status": "unchecked",
            "novelty_query": query,
            "novelty_error": reason,
            "related_recent_papers": [],
            "checked_at": checked_at,
        }
    papers = (papers or []) + (s2_papers or [])

    scored = sorted(
        ((p, _overlap_score(query, p)) for p in papers),
        key=lambda ps: ps[1], reverse=True,
    )
    strong = [p for p, s in scored if s >= strong_threshold]

    if len(strong) >= 3:
        status = "addressed"
    elif len(strong) >= 1:
        status = "partially_addressed"
    else:
        status = "open"

    related = []
    for p, s in scored[:5]:
        related.append({
            "title": getattr(p, "title", None),
            "year": getattr(p, "year", None),
            "doi": getattr(p, "doi", None),
            "match_score": round(s, 2),
        })

    return {
        "novelty_status": status,
        "novelty_query": query,
        "related_recent_papers": related,
        "checked_at": checked_at,
    }


def annotate_gaps(
    gaps: List[Dict[str, Any]],
    openalex: Optional[OpenAlexAPI] = None,
    from_date: str = "2024-01-01",
    s2_search_fn: Optional[Callable[[str], List[Any]]] = None,
    min_interval: float = 1.0,
    max_retries: int = 4,
    on_progress: Optional[Callable[[int, int], None]] = None,
    limit: int = 0,
) -> List[Dict[str, Any]]:
    """Attach novelty fields to every gap (100% coverage — TAHAP 3 kriteria #1).

    Gaps whose lookup failed are ``unchecked`` (see module docstring). ``limit``
    > 0 checks only the first ``limit`` gaps and marks the rest ``unchecked``
    with ``novelty_error="di luar batas cek"`` — a way to spend the daily
    OpenAlex quota deliberately.

    ``on_progress(done, total)`` is called after each gap so a caller can
    surface live progress; the CLI leaves it ``None``.
    """
    openalex = openalex or OpenAlexAPI(min_interval=min_interval, max_retries=max_retries)
    out = []
    for i, gap in enumerate(gaps, 1):
        enriched = dict(gap)
        if limit and i > limit:
            enriched.update({
                "novelty_status": "unchecked",
                "novelty_query": build_keywords(gap),
                "novelty_error": "di luar batas cek",
                "related_recent_papers": [],
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            })
        else:
            enriched.update(classify_novelty(gap, openalex=openalex, from_date=from_date,
                                             s2_search_fn=s2_search_fn))
        out.append(enriched)
        if on_progress is not None:
            on_progress(i, len(gaps))
        if i % 20 == 0:
            logger.info(f"  novelty-checked {i}/{len(gaps)} gaps")
    return out
