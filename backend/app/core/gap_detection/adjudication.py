"""
Contradiction adjudication: separating genuine contradictions from
heterogeneity (LeapSpace P7).

The P7 review is explicit that a raw NLI contradiction probability is not a
label: "usually no universal final contradiction-score cutoff is reported".
What the literature *does* prescribe is an adjudication step that assigns one
of four outcomes:

    contradiction   — comparable claims asserting opposite effect directions
    heterogeneous   — difference explainable by moderators / study design
    non-comparable  — claims are not about the same thing (alignment failed)
    inconclusive    — insufficient evidence to decide either way

Statistical heterogeneity thresholds follow the conventional bands cited in
the report: Cochran's Q at p < 0.10, I-squared bands 25/50/75 %, random-effects
preferred above I-squared 50 %, and tau-squared > 1.0 as substantial
between-study variance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

from .claim_normalization import (
    ALIGNMENT_GATE,
    AlignmentResult,
    NormalizedClaim,
    align_claims,
)

# Heterogeneity thresholds (P7).
Q_TEST_ALPHA = 0.10
I2_BANDS = (25.0, 50.0, 75.0)
I2_RANDOM_EFFECTS_THRESHOLD = 50.0
TAU2_SUBSTANTIAL = 1.0

# NLI probability below which a "contradiction" is treated as noise. Kept as a
# *floor* rather than a decision cutoff, precisely because the literature
# reports no universal cutoff.
NLI_NOISE_FLOOR = 0.50

# Design/moderator cues that make two diverging findings explainable rather
# than contradictory.
_MODERATOR_CUES = (
    "however", "whereas", "depending on", "moderated by", "moderator",
    "subgroup", "sub-group", "varies by", "context-dependent", "only when",
    "under certain", "in contrast to", "differs across", "heterogene",
    "tergantung", "bergantung pada", "berbeda pada",
)
_DESIGN_CUES = (
    "randomized", "randomised", "observational", "retrospective",
    "prospective", "cross-sectional", "longitudinal", "simulation",
    "case study", "survey", "meta-analysis", "systematic review",
    "benchmark", "ablation",
)


class Adjudication(str, Enum):
    """Four-class outcome of a contradiction check."""

    CONTRADICTION = "contradiction"
    HETEROGENEOUS = "heterogeneous"
    NON_COMPARABLE = "non-comparable"
    INCONCLUSIVE = "inconclusive"


@dataclass
class AdjudicationResult:
    label: Adjudication
    confidence: float
    reason: str
    alignment: Optional[AlignmentResult] = None
    nli_score: float = 0.0
    heterogeneity: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_contradiction(self) -> bool:
        return self.label is Adjudication.CONTRADICTION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label.value,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
            "nli_score": round(self.nli_score, 3),
            "alignment": self.alignment.to_dict() if self.alignment else None,
            "heterogeneity": dict(self.heterogeneity),
        }


# ---------------------------------------------------------------------------
# Heterogeneity statistics
# ---------------------------------------------------------------------------

def cochran_q(effects: Sequence[float], variances: Sequence[float]) -> float:
    """Cochran's Q statistic for between-study heterogeneity."""
    pairs = [(e, v) for e, v in zip(effects, variances) if v and v > 0]
    if len(pairs) < 2:
        return 0.0
    weights = [1.0 / v for _, v in pairs]
    weight_sum = sum(weights)
    pooled = sum(w * e for w, (e, _) in zip(weights, pairs)) / weight_sum
    return sum(w * (e - pooled) ** 2 for w, (e, _) in zip(weights, pairs))


def i_squared(q_stat: float, k_studies: int) -> float:
    """I-squared (%) — proportion of variance due to heterogeneity."""
    df = k_studies - 1
    if df <= 0 or q_stat <= df:
        return 0.0
    return round(100.0 * (q_stat - df) / q_stat, 2)


def tau_squared(
    q_stat: float, k_studies: int, variances: Sequence[float]
) -> float:
    """DerSimonian-Laird estimate of between-study variance."""
    usable = [v for v in variances if v and v > 0]
    df = k_studies - 1
    if df <= 0 or len(usable) < 2 or q_stat <= df:
        return 0.0
    weights = [1.0 / v for v in usable]
    weight_sum = sum(weights)
    c = weight_sum - sum(w * w for w in weights) / weight_sum
    if c <= 0:
        return 0.0
    return round(max(0.0, (q_stat - df) / c), 4)


def _chi_square_p_value(q_stat: float, df: int) -> float:
    """Upper-tail chi-square p-value (Wilson-Hilferty approximation).

    Avoids a hard scipy dependency; accuracy is ample for a 0.10 threshold.
    """
    if df <= 0 or q_stat <= 0:
        return 1.0
    ratio = q_stat / df
    z = (ratio ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / math.sqrt(2.0 / (9.0 * df))
    # Upper-tail standard normal
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def i2_band(i2_value: float) -> str:
    """Map I-squared onto the conventional low/moderate/substantial bands."""
    if i2_value < I2_BANDS[0]:
        return "negligible"
    if i2_value < I2_BANDS[1]:
        return "low"
    if i2_value < I2_BANDS[2]:
        return "moderate"
    return "substantial"


def assess_heterogeneity(
    effects: Sequence[float], variances: Sequence[float]
) -> Dict[str, Any]:
    """Full heterogeneity summary for a set of comparable effect estimates."""
    k = len([v for v in variances if v and v > 0])
    if k < 2:
        return {"available": False, "reason": "fewer than two usable effect estimates"}
    q_stat = cochran_q(effects, variances)
    df = k - 1
    p_value = _chi_square_p_value(q_stat, df)
    i2_value = i_squared(q_stat, k)
    tau2 = tau_squared(q_stat, k, variances)
    return {
        "available": True,
        "k": k,
        "q": round(q_stat, 4),
        "df": df,
        "p_value": round(p_value, 4),
        "q_significant": p_value < Q_TEST_ALPHA,
        "i_squared": i2_value,
        "i_squared_band": i2_band(i2_value),
        "tau_squared": tau2,
        "tau_squared_substantial": tau2 > TAU2_SUBSTANTIAL,
        "recommended_model": (
            "random-effects" if i2_value > I2_RANDOM_EFFECTS_THRESHOLD else "fixed-effect"
        ),
        "heterogeneous": (
            p_value < Q_TEST_ALPHA
            or i2_value > I2_RANDOM_EFFECTS_THRESHOLD
            or tau2 > TAU2_SUBSTANTIAL
        ),
    }


# ---------------------------------------------------------------------------
# Adjudication
# ---------------------------------------------------------------------------

def _has_cue(text: str, cues: Sequence[str]) -> bool:
    low = text.lower()
    return any(cue in low for cue in cues)


def _designs_differ(claim_a: NormalizedClaim, claim_b: NormalizedClaim) -> bool:
    def designs(claim: NormalizedClaim) -> set:
        low = claim.text.lower()
        return {cue for cue in _DESIGN_CUES if cue in low}

    designs_a, designs_b = designs(claim_a), designs(claim_b)
    return bool(designs_a and designs_b and not (designs_a & designs_b))


def _directions_oppose(claim_a: NormalizedClaim, claim_b: NormalizedClaim) -> bool:
    a, b = claim_a.signed_direction, claim_b.signed_direction
    opposing = {
        frozenset({"increase", "decrease"}),
        frozenset({"increase", "no_effect"}),
        frozenset({"decrease", "no_effect"}),
        frozenset({"increase", "not_increase"}),
        frozenset({"decrease", "not_decrease"}),
    }
    return frozenset({a, b}) in opposing


def adjudicate_contradiction(
    claim_a: NormalizedClaim,
    claim_b: NormalizedClaim,
    nli_score: float = 0.0,
    embedder=None,
    alignment: Optional[AlignmentResult] = None,
    effect_estimates: Optional[Sequence[float]] = None,
    effect_variances: Optional[Sequence[float]] = None,
) -> AdjudicationResult:
    """Decide which of the four classes a candidate contradiction belongs to.

    Order of checks follows the pipeline mandated by P7: alignment first (are
    these claims even about the same thing?), then effect direction, then
    heterogeneity adjudication, and only then a contradiction label.
    """
    if alignment is None:
        alignment = align_claims(claim_a, claim_b, embedder=embedder)

    heterogeneity: Dict[str, Any] = {}
    if effect_estimates and effect_variances:
        heterogeneity = assess_heterogeneity(effect_estimates, effect_variances)

    # Step 1 — comparability gate.
    if not alignment.comparable:
        return AdjudicationResult(
            label=Adjudication.NON_COMPARABLE,
            confidence=round(min(0.6, 1.0 - alignment.score), 3),
            reason=(
                f"variable alignment {alignment.score:.2f} < gate {ALIGNMENT_GATE:.2f}"
                + (f"; mismatched: {', '.join(alignment.mismatched_fields)}"
                   if alignment.mismatched_fields else "")
                + ("; PICO context unavailable on both sides (relaxed matching)"
                   if not alignment.matched_fields and not alignment.mismatched_fields
                   else "")
            ),
            alignment=alignment,
            nli_score=nli_score,
            heterogeneity=heterogeneity,
        )

    # Step 2 — is there any signal at all?
    directions_known = "unknown" not in (claim_a.direction, claim_b.direction)
    opposes = directions_known and _directions_oppose(claim_a, claim_b)
    if not opposes and nli_score < NLI_NOISE_FLOOR:
        return AdjudicationResult(
            label=Adjudication.INCONCLUSIVE,
            confidence=round(max(0.2, nli_score), 3),
            reason=(
                "no opposing effect direction extracted and NLI score below "
                f"noise floor ({nli_score:.2f} < {NLI_NOISE_FLOOR:.2f})"
            ),
            alignment=alignment,
            nli_score=nli_score,
            heterogeneity=heterogeneity,
        )

    # Step 3 — heterogeneity adjudication (the step raw NLI skips).
    explanations: List[str] = []
    if heterogeneity.get("available") and heterogeneity.get("heterogeneous"):
        explanations.append(
            f"statistical heterogeneity (I²={heterogeneity['i_squared']}% "
            f"[{heterogeneity['i_squared_band']}], Q p={heterogeneity['p_value']}, "
            f"τ²={heterogeneity['tau_squared']})"
        )
    if _has_cue(claim_a.text, _MODERATOR_CUES) or _has_cue(claim_b.text, _MODERATOR_CUES):
        explanations.append("moderator/subgroup language present in the claims")
    if _designs_differ(claim_a, claim_b):
        explanations.append("different study designs")
    if alignment.mismatched_fields:
        explanations.append(
            f"context differs on {', '.join(alignment.mismatched_fields)}"
        )
    if claim_a.unit and claim_b.unit and claim_a.unit != claim_b.unit:
        explanations.append(
            f"incommensurable units ({claim_a.unit} vs {claim_b.unit})"
        )

    if explanations:
        return AdjudicationResult(
            label=Adjudication.HETEROGENEOUS,
            confidence=round(min(0.75, 0.4 + 0.1 * len(explanations)), 3),
            reason="divergence explainable by " + "; ".join(explanations),
            alignment=alignment,
            nli_score=nli_score,
            heterogeneity=heterogeneity,
        )

    # Step 4 — genuine contradiction. Confidence blends the alignment quality
    # with the NLI evidence instead of using the NLI score alone.
    direction_evidence = 1.0 if opposes else 0.6
    confidence = 0.5 * alignment.score + 0.3 * max(nli_score, NLI_NOISE_FLOOR) + 0.2 * direction_evidence
    if alignment.relaxed:
        # Missing PICO context must not produce over-confident contradictions.
        confidence = min(confidence, 0.7)
    return AdjudicationResult(
        label=Adjudication.CONTRADICTION,
        confidence=round(max(0.0, min(confidence, 0.95)), 3),
        reason=(
            f"comparable claims (alignment {alignment.score:.2f}) assert opposing "
            f"directions ({claim_a.signed_direction} vs {claim_b.signed_direction})"
            f"; no moderator, design or unit explanation found"
        ),
        alignment=alignment,
        nli_score=nli_score,
        heterogeneity=heterogeneity,
    )
