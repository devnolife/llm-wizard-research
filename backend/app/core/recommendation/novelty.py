"""
Semantic novelty scoring for research proposals (LeapSpace P5).

Important scope note
--------------------
The P5 review presents semantic novelty — distance from the corpus centroid —
as a gap-detection signal. This thesis deliberately does **not** use it that
way: BAB II Subbab 2.2.2 states explicitly that a synthesis gap is *not* "a
method-domain combination nobody has tried yet". Scoring an unexplored
combination as a gap would contradict the thesis's own definition.

Novelty is therefore used one step later, as a **ranking signal over already
gap-anchored proposals**. Every proposal here has already been justified by a
detected indicator; novelty only decides which of those defensible proposals is
the more interesting one to pursue first.

Score
-----
    novelty(r) = 1 - max_p cos(emb(r), emb(p))          (max over corpus)

    priority(r) = w_gap * gap_confidence
                + w_nov * novelty(r)
                + w_act * actionability(r)

Extreme novelty is penalised rather than rewarded: a proposal with no
neighbours at all in the corpus is usually off-topic, not visionary. The
`SWEET_SPOT` band encodes that intuition.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from loguru import logger

# A proposal too close to the corpus is derivative; too far is off-topic.
NOVELTY_SWEET_SPOT = (0.25, 0.65)
# Weights for the composite priority score.
W_GAP = 0.50
W_NOVELTY = 0.30
W_ACTIONABILITY = 0.20

# Concrete methodological commitments make a proposal executable.
_ACTIONABLE_CUES = (
    "protokol", "protocol", "dataset", "eksperimen", "experiment", "meta-analisis",
    "meta-analysis", "replikasi", "replication", "systematic review", "tinjauan sistematis",
    "benchmark", "ablasi", "ablation", "kuesioner", "wawancara", "survei", "survey",
    "studi kasus", "case study", "kohort", "cohort", "randomized", "acak",
    "kerangka", "framework", "taksonomi", "taxonomy", "instrumen", "metrik", "metric",
)

_VAGUE_CUES = (
    "lebih lanjut", "further research", "dapat dieksplorasi", "bisa diteliti",
    "menarik untuk", "di masa depan", "in the future", "lebih dalam",
)

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9\-]{2,}")


# ---------------------------------------------------------------------------
# Similarity backends
# ---------------------------------------------------------------------------

def _tokens(text: str) -> set:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _lexical_similarity(a: str, b: str) -> float:
    """Overlap coefficient, not Jaccard.

    A proposal paragraph is far longer than a paper abstract, and Jaccard
    punishes that length asymmetry so hard that every real proposal would look
    "off topic". The overlap coefficient asks the question that actually
    matters here: how much of the shorter text is covered by the longer one.
    """
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    shared = len(ta & tb)
    overlap = shared / min(len(ta), len(tb))
    jaccard = shared / len(ta | tb)
    return 0.75 * overlap + 0.25 * jaccard


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    na = math.sqrt(sum(float(x) * float(x) for x in a))
    nb = math.sqrt(sum(float(y) * float(y) for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _as_floats(vector) -> List[float]:
    """Coerce an embedding row (torch Tensor / numpy array / list) to floats.

    ``SentenceTransformer.encode`` may hand back tensors, and tensor arithmetic
    propagates all the way into ``round()``, which silently disables ranking.
    """
    tolist = getattr(vector, "tolist", None)
    if callable(tolist):
        vector = tolist()
    return [float(x) for x in vector]


class _Backend:
    """Embeddings when available, Jaccard otherwise."""

    def __init__(self, embedder=None):
        self.embedder = embedder

    @property
    def uses_embeddings(self) -> bool:
        return self.embedder is not None

    def similarities(self, query: str, corpus: Sequence[str]) -> List[float]:
        if not corpus:
            return []
        if self.embedder is not None:
            try:
                vectors = self.embedder.encode([query] + list(corpus))
                q = _as_floats(vectors[0])
                return [_cosine(q, _as_floats(v)) for v in vectors[1:]]
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug(f"Novelty embedding failed, using lexical: {exc}")
        return [_lexical_similarity(query, c) for c in corpus]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

@dataclass
class NoveltyScore:
    """Novelty and composite priority for one proposal."""

    novelty: float
    nearest_paper: str = ""
    nearest_similarity: float = 0.0
    actionability: float = 0.0
    gap_confidence: float = 0.0
    priority_score: float = 0.0
    band: str = ""                       # derivative | sweet_spot | off_topic
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "novelty": round(self.novelty, 4),
            "nearest_paper": self.nearest_paper,
            "nearest_similarity": round(self.nearest_similarity, 4),
            "actionability": round(self.actionability, 4),
            "gap_confidence": round(self.gap_confidence, 4),
            "priority_score": round(self.priority_score, 4),
            "band": self.band,
            "notes": self.notes,
        }


def actionability(text: str) -> float:
    """How concretely executable a proposal reads, in [0, 1]."""
    low = (text or "").lower()
    hits = sum(1 for cue in _ACTIONABLE_CUES if cue in low)
    vague = sum(1 for cue in _VAGUE_CUES if cue in low)
    score = min(1.0, hits / 3.0) - 0.15 * vague
    return round(max(0.0, min(1.0, score)), 4)


def novelty_band(novelty: float) -> str:
    low, high = NOVELTY_SWEET_SPOT
    if novelty < low:
        return "derivative"
    if novelty > high:
        return "off_topic"
    return "sweet_spot"


def score_proposal(
    proposal: Dict[str, Any],
    corpus_texts: Sequence[str],
    corpus_refs: Sequence[str],
    backend: _Backend,
    gap_confidence: float = 0.0,
) -> NoveltyScore:
    """Score one gap-anchored proposal for ranking purposes."""
    text = " ".join(
        str(proposal.get(k, "")) for k in ("title", "description", "how")
    ).strip()
    sims = backend.similarities(text, corpus_texts)
    if sims:
        best_idx = max(range(len(sims)), key=lambda i: sims[i])
        nearest_sim = sims[best_idx]
        nearest_ref = corpus_refs[best_idx] if best_idx < len(corpus_refs) else ""
    else:
        nearest_sim, nearest_ref = 0.0, ""

    novelty = round(max(0.0, min(1.0, 1.0 - nearest_sim)), 4)
    band = novelty_band(novelty)
    act = actionability(text)

    # Only the sweet spot gets full novelty credit; the extremes are discounted
    # because both "already done" and "unrelated to the corpus" are bad answers.
    low, high = NOVELTY_SWEET_SPOT
    if band == "sweet_spot":
        novelty_credit = 1.0
    elif band == "derivative":
        novelty_credit = novelty / low if low else 0.0
    else:
        novelty_credit = max(0.0, 1.0 - (novelty - high) / max(1e-6, 1.0 - high))

    priority = (
        W_GAP * max(0.0, min(1.0, gap_confidence))
        + W_NOVELTY * novelty_credit
        + W_ACTIONABILITY * act
    )

    notes: List[str] = []
    if band == "derivative":
        notes.append(
            f"sangat mirip literatur yang ada (kemiripan {nearest_sim:.2f}"
            + (f" dengan {nearest_ref}" if nearest_ref else "")
            + ") — risiko mengulang"
        )
    elif band == "off_topic":
        notes.append(
            "hampir tidak beririsan dengan korpus — periksa apakah masih "
            "menjawab gap yang terdeteksi"
        )
    else:
        notes.append("berada di rentang kebaruan yang sehat terhadap korpus")
    if act < 0.34:
        notes.append("belum menyebut metode/instrumen konkret")

    return NoveltyScore(
        novelty=novelty,
        nearest_paper=nearest_ref,
        nearest_similarity=round(nearest_sim, 4),
        actionability=act,
        gap_confidence=round(gap_confidence, 4),
        priority_score=round(priority, 4),
        band=band,
        notes=notes,
    )


def rank_proposals(
    proposals: Sequence[Dict[str, Any]],
    papers: Sequence[Dict[str, Any]],
    gaps: Optional[Sequence[Dict[str, Any]]] = None,
    embedder=None,
) -> List[Dict[str, Any]]:
    """Attach novelty/priority scores and reorder proposals by priority.

    Returns new dicts (the inputs are not mutated) carrying a ``novelty`` block
    and a ``priority`` label derived from the composite score.
    """
    if not proposals:
        return []

    corpus_texts: List[str] = []
    corpus_refs: List[str] = []
    for paper in papers or []:
        text = " ".join(
            str(paper.get(k, ""))
            for k in ("title", "abstract", "summary", "content")
        )[:1500].strip()
        if not text:
            continue
        corpus_texts.append(text)
        corpus_refs.append(
            str(paper.get("source") or paper.get("title") or "")
        )

    confidence_by_type: Dict[str, float] = {}
    for gap in gaps or []:
        gtype = str(gap.get("type") or gap.get("indicator_type") or "").upper()
        conf = gap.get("calibrated_confidence")
        if conf is None:
            conf = gap.get("confidence", 0.0)
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.0
        if gtype:
            confidence_by_type[gtype] = max(confidence_by_type.get(gtype, 0.0), conf)

    backend = _Backend(embedder)
    scored: List[Tuple[float, int, Dict[str, Any]]] = []
    for idx, proposal in enumerate(proposals):
        gtype = str(proposal.get("gap_type") or "").upper()
        score = score_proposal(
            proposal,
            corpus_texts,
            corpus_refs,
            backend,
            gap_confidence=confidence_by_type.get(gtype, 0.0),
        )
        enriched = dict(proposal)
        enriched["novelty"] = score.to_dict()
        enriched["priority"] = priority_label(score.priority_score)
        scored.append((score.priority_score, idx, enriched))

    # Stable: equal scores keep the generator's original order.
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [item for _, _, item in scored]


def priority_label(priority_score: float) -> str:
    if priority_score >= 0.62:
        return "high"
    if priority_score >= 0.45:
        return "medium"
    return "low"
