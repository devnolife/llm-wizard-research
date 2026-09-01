"""Corpus coherence check — flag uploaded journals that do not fit the batch.

Nothing in the pipeline validates that the uploaded PDFs belong to the same
research area. Feeding in an unrelated paper is silently accepted, and it does
not simply add noise: ``novelty = 1 - max_similarity`` means an off-domain paper
lands in the novelty sweet spot when its similarity is merely *moderate*, so it
can be rewarded rather than penalised in the recommendation ranking.

The probe deliberately uses the title plus the first two non-reference chunks
rather than the full text. Front matter (tables of contents, prefaces) makes
book-like entries resemble any academic paper, which is why full-text probing
let 10 of 23 out-of-domain papers pass as relevant versus 2 of 23 here.

This reports a WARNING, never a rejection, and it only detects a MINORITY of
stray uploads. Measured on 35 forensics journals vs 23 out-of-domain ML papers:

    intruders added one at a time   21 of 23 flagged, 0 of 35 false alarms
    3 intruders added together       1 of 3   (they become each other's nearest
                                              neighbour and vouch for one another)
    23 intruders added together      1 of 23  (the intruders are now a coherent
                                              majority and look perfectly normal)

The classes also overlap even in the best case (legitimate minimum 0.508 vs
strongest single intruder 0.581), so this can never be an automatic gate. It
catches the common accident — one or two files dropped into the wrong batch —
and nothing more.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Calibrated on 35 forensics journals vs 23 out-of-domain ML papers added one at
# a time: 0 of 35 legitimate journals flagged, 21 of 23 intruders caught.
RELEVANCE_WARN_THRESHOLD = 0.50

_PROBE_CHARS = 1200
_PROBE_CHUNKS = 2


def build_probe(title: Optional[str], chunks: Sequence[Dict[str, Any]]) -> str:
    """Title + the first non-reference chunks, as the paper's topical signature."""
    body = [c for c in chunks if not c.get("is_reference")]
    body = sorted(body, key=lambda c: c.get("chunk_index", 0))[:_PROBE_CHUNKS]
    parts = [(title or "").strip()] + [(c.get("text") or "").strip() for c in body]
    return ". ".join(p for p in parts if p)[:_PROBE_CHARS]


@dataclass
class RelevanceReport:
    """How well one journal fits the rest of the uploaded batch."""

    source: str
    score: float
    nearest: str = ""
    flagged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "score": round(self.score, 4),
            "nearest": self.nearest,
            "flagged": self.flagged,
        }


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    na = math.sqrt(sum(float(x) * float(x) for x in a))
    nb = math.sqrt(sum(float(y) * float(y) for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _as_floats(vector) -> List[float]:
    tolist = getattr(vector, "tolist", None)
    if callable(tolist):
        vector = tolist()
    return [float(x) for x in vector]


def check_corpus_relevance(
    probes: Dict[str, str],
    embedder=None,
    threshold: float = RELEVANCE_WARN_THRESHOLD,
) -> List[RelevanceReport]:
    """Score each journal by its similarity to the most similar OTHER journal.

    Returns reports sorted ascending (least related first). Without an embedder
    nothing is flagged — the threshold is calibrated for embedding cosine only.

    Nearest-neighbour similarity is used on purpose: averaging over the batch
    punishes legitimately niche journals, which are common in a real corpus.
    The cost is that a CLUSTER of unrelated papers hides itself (see module
    docstring), so treat a clean result as "no obvious stray file", not as
    proof the batch is coherent.
    """
    sources = list(probes)
    if len(sources) < 2 or embedder is None:
        return [RelevanceReport(source=s, score=0.0) for s in sources]

    try:
        vectors = [_as_floats(v) for v in embedder.encode([probes[s] for s in sources])]
    except Exception:
        return [RelevanceReport(source=s, score=0.0) for s in sources]

    reports: List[RelevanceReport] = []
    for i, source in enumerate(sources):
        best, best_j = -1.0, None
        for j in range(len(sources)):
            if i == j:
                continue
            sim = _cosine(vectors[i], vectors[j])
            if sim > best:
                best, best_j = sim, j
        score = max(0.0, best)
        reports.append(RelevanceReport(
            source=source,
            score=score,
            nearest=sources[best_j] if best_j is not None else "",
            flagged=score < threshold,
        ))
    reports.sort(key=lambda r: r.score)
    return reports
