"""
Confidence calibration, selective abstention and provenance (LeapSpace P9).

The P9 review's central finding is that a raw model confidence is a weak gap
signal: what makes a claimed research gap defensible is (a) a *calibrated*
probability, (b) the ability to *abstain* instead of guessing, and (c) a
traceable provenance chain from claim back to evidence.

Implemented here:

    Expected Calibration Error
        ECE = SUM_m (|B_m| / N) * |acc(B_m) - conf(B_m)|      (10 bins)

    Brier score
        BS = (1/N) * SUM_i SUM_k (p_ik - y_ik)^2

    Selective prediction
        C     = E[g(x)]                              (coverage)
        R_sel = E[l(f(x), y) * g(x)] / E[g(x)]       (selective risk)

    Provenance chain (minimum viable, per the report)
        claim -> cited record -> retrieved passage -> validation outcome

Post-hoc calibration uses temperature scaling with a conformal fallback,
which the report identifies as the realistic choice when expert labels are
scarce — exactly the situation in this thesis, where the gold standard is a
small expert-annotated set.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from loguru import logger

DEFAULT_BINS = 10

# Temperature scaling is only trustworthy with a minimum of held-out labels;
# below this the calibrator deliberately stays an identity map.
MIN_CALIBRATION_LABELS = 4

# Below this calibrated confidence an indicator is not presented as a finding.
# Chosen as an abstention band, not a truth threshold: the system withholds
# rather than asserts.
ABSTENTION_THRESHOLD = 0.45

# Conformal miscoverage level: 1 - alpha nominal coverage.
CONFORMAL_ALPHA = 0.1

# How the rule engine verdict moves a calibrated confidence. PASS is corroborating
# symbolic evidence, FLAG is a warning, REJECT forces abstention upstream.
_VERDICT_MULTIPLIER = {"PASS": 1.10, "FLAG": 0.80, "REJECT": 0.0}


# ---------------------------------------------------------------------------
# Calibration metrics
# ---------------------------------------------------------------------------

def expected_calibration_error(
    confidences: Sequence[float],
    correctness: Sequence[int],
    n_bins: int = DEFAULT_BINS,
) -> float:
    """ECE with equal-width bins.

        ECE = SUM_m (|B_m| / N) * |acc(B_m) - conf(B_m)|
    """
    pairs = [(float(c), int(y)) for c, y in zip(confidences, correctness)]
    n = len(pairs)
    if n == 0:
        return 0.0
    bins: List[List[Tuple[float, int]]] = [[] for _ in range(n_bins)]
    for confidence, label in pairs:
        index = min(n_bins - 1, max(0, int(confidence * n_bins)))
        bins[index].append((confidence, label))
    ece = 0.0
    for bucket in bins:
        if not bucket:
            continue
        accuracy = sum(y for _, y in bucket) / len(bucket)
        mean_confidence = sum(c for c, _ in bucket) / len(bucket)
        ece += (len(bucket) / n) * abs(accuracy - mean_confidence)
    return round(ece, 4)


def brier_score(
    confidences: Sequence[float], correctness: Sequence[int]
) -> float:
    """Two-class Brier score.

        BS = (1/N) * SUM_i SUM_k (p_ik - y_ik)^2
    """
    pairs = list(zip(confidences, correctness))
    if not pairs:
        return 0.0
    total = 0.0
    for confidence, label in pairs:
        p_positive = float(confidence)
        p_negative = 1.0 - p_positive
        y_positive = float(label)
        y_negative = 1.0 - y_positive
        total += (p_positive - y_positive) ** 2 + (p_negative - y_negative) ** 2
    return round(total / len(pairs), 4)


def reliability_bins(
    confidences: Sequence[float],
    correctness: Sequence[int],
    n_bins: int = DEFAULT_BINS,
) -> List[Dict[str, Any]]:
    """Per-bin accuracy vs confidence, for a reliability diagram."""
    bins: List[List[Tuple[float, int]]] = [[] for _ in range(n_bins)]
    for confidence, label in zip(confidences, correctness):
        index = min(n_bins - 1, max(0, int(float(confidence) * n_bins)))
        bins[index].append((float(confidence), int(label)))
    output = []
    for i, bucket in enumerate(bins):
        output.append({
            "bin": i,
            "range": [round(i / n_bins, 2), round((i + 1) / n_bins, 2)],
            "count": len(bucket),
            "accuracy": round(sum(y for _, y in bucket) / len(bucket), 4) if bucket else None,
            "mean_confidence": round(sum(c for c, _ in bucket) / len(bucket), 4) if bucket else None,
        })
    return output


# ---------------------------------------------------------------------------
# Selective prediction
# ---------------------------------------------------------------------------

def risk_coverage_curve(
    confidences: Sequence[float], correctness: Sequence[int]
) -> List[Dict[str, float]]:
    """Selective risk at every coverage level, highest confidence first.

        C     = E[g(x)]
        R_sel = E[l(f(x), y) * g(x)] / E[g(x)]
    """
    pairs = sorted(zip(confidences, correctness), key=lambda x: -float(x[0]))
    n = len(pairs)
    if n == 0:
        return []
    curve = []
    errors = 0
    for i, (_, label) in enumerate(pairs, start=1):
        errors += 1 - int(label)
        curve.append({
            "coverage": round(i / n, 4),
            "selective_risk": round(errors / i, 4),
        })
    return curve


def area_under_risk_coverage(
    confidences: Sequence[float], correctness: Sequence[int]
) -> float:
    """AURC — lower is better; a perfect ranker pushes all errors to the tail."""
    curve = risk_coverage_curve(confidences, correctness)
    if not curve:
        return 0.0
    return round(sum(point["selective_risk"] for point in curve) / len(curve), 4)


# ---------------------------------------------------------------------------
# Post-hoc calibration
# ---------------------------------------------------------------------------

def _logit(p: float, eps: float = 1e-6) -> float:
    p = min(1.0 - eps, max(eps, p))
    return math.log(p / (1.0 - p))


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    exp_z = math.exp(z)
    return exp_z / (1.0 + exp_z)


def fit_temperature(
    confidences: Sequence[float],
    correctness: Sequence[int],
    grid: Optional[Sequence[float]] = None,
) -> float:
    """Fit a single temperature T by minimizing NLL on a grid.

    Grid search rather than gradient descent because the label set is tiny
    (tens of expert annotations) and a grid is deterministic and auditable.
    """
    pairs = [(float(c), int(y)) for c, y in zip(confidences, correctness)]
    if len(pairs) < 4:
        return 1.0
    grid = grid or [round(0.25 + 0.05 * i, 2) for i in range(0, 76)]  # 0.25 .. 4.0
    best_t, best_nll = 1.0, float("inf")
    for temperature in grid:
        if temperature <= 0:
            continue
        nll = 0.0
        for confidence, label in pairs:
            p = _sigmoid(_logit(confidence) / temperature)
            p = min(1.0 - 1e-9, max(1e-9, p))
            nll -= label * math.log(p) + (1 - label) * math.log(1.0 - p)
        if nll < best_nll:
            best_nll, best_t = nll, temperature
    return best_t


def apply_temperature(confidence: float, temperature: float) -> float:
    if temperature <= 0:
        return confidence
    return round(_sigmoid(_logit(confidence) / temperature), 4)


def conformal_threshold(
    confidences: Sequence[float],
    correctness: Sequence[int],
    alpha: float = CONFORMAL_ALPHA,
) -> Optional[float]:
    """Split-conformal cutoff giving ~(1 - alpha) coverage on true positives.

    Returns the confidence below which predictions should be withheld.
    """
    positives = sorted(
        float(c) for c, y in zip(confidences, correctness) if int(y) == 1
    )
    if len(positives) < 5:
        return None
    n = len(positives)
    index = max(0, min(n - 1, int(math.floor(alpha * (n + 1))) - 1))
    return round(positives[index], 4)


@dataclass
class Calibrator:
    """Post-hoc calibrator with abstention.

    Without expert labels the calibrator is an identity map that still applies
    the abstention band and rule-engine fusion, so the pipeline behaves
    consistently before and after a labelled set exists.
    """

    temperature: float = 1.0
    conformal_cutoff: Optional[float] = None
    abstention_threshold: float = ABSTENTION_THRESHOLD
    fitted: bool = False
    n_labels: int = 0

    @classmethod
    def fit(
        cls,
        confidences: Sequence[float],
        correctness: Sequence[int],
        alpha: float = CONFORMAL_ALPHA,
        abstention_threshold: float = ABSTENTION_THRESHOLD,
    ) -> "Calibrator":
        temperature = fit_temperature(confidences, correctness)
        cutoff = conformal_threshold(confidences, correctness, alpha=alpha)
        return cls(
            temperature=temperature,
            conformal_cutoff=cutoff,
            abstention_threshold=abstention_threshold,
            fitted=len(list(confidences)) >= 4,
            n_labels=len(list(confidences)),
        )

    def calibrate(
        self, raw_confidence: float, rule_verdict: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return the calibrated confidence plus the abstention decision.

        Fusion with the symbolic layer follows the plan: PASS corroborates,
        FLAG discounts, REJECT abstains outright. The rule engine is treated as
        evidence about the claim, not as a second opinion to be averaged.
        """
        calibrated = apply_temperature(float(raw_confidence), self.temperature)
        verdict = (rule_verdict or "").upper()
        multiplier = _VERDICT_MULTIPLIER.get(verdict)
        if multiplier is not None:
            calibrated = round(min(1.0, calibrated * multiplier), 4)

        reasons: List[str] = []
        abstain = False
        if verdict == "REJECT":
            abstain = True
            reasons.append("verdict rule engine REJECT")
        if calibrated < self.abstention_threshold:
            abstain = True
            reasons.append(
                f"keyakinan terkalibrasi {calibrated:.0%} di bawah ambang "
                f"abstain {self.abstention_threshold:.0%}"
            )
        if self.conformal_cutoff is not None and calibrated < self.conformal_cutoff:
            abstain = True
            reasons.append(
                f"di bawah batas konformal {self.conformal_cutoff:.0%} "
                f"(target cakupan {(1 - CONFORMAL_ALPHA):.0%})"
            )

        return {
            "raw_confidence": round(float(raw_confidence), 4),
            "calibrated_confidence": calibrated,
            "temperature": self.temperature,
            "conformal_cutoff": self.conformal_cutoff,
            "rule_verdict": verdict or None,
            "needs_review": abstain,
            "abstention_reasons": reasons,
            "calibrator_fitted": self.fitted,
            "calibration_labels": self.n_labels,
        }


def evaluate_calibration(
    confidences: Sequence[float],
    correctness: Sequence[int],
    n_bins: int = DEFAULT_BINS,
) -> Dict[str, Any]:
    """Full calibration report for BAB IV reporting."""
    confidences = [float(c) for c in confidences]
    correctness = [int(y) for y in correctness]
    return {
        "n": len(confidences),
        "ece": expected_calibration_error(confidences, correctness, n_bins),
        "brier": brier_score(confidences, correctness),
        "aurc": area_under_risk_coverage(confidences, correctness),
        "bins": reliability_bins(confidences, correctness, n_bins),
        "risk_coverage": risk_coverage_curve(confidences, correctness),
    }


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

@dataclass
class ProvenanceChain:
    """Minimum viable provenance chain required by the P9 report:

        claim -> cited record -> retrieved passage -> validation outcome
    """

    claim: str
    cited_records: List[str] = field(default_factory=list)
    retrieved_passages: List[Dict[str, Any]] = field(default_factory=list)
    validation_outcome: str = ""
    validation_detail: str = ""

    @property
    def complete(self) -> bool:
        """A chain is only traceable when every link is present."""
        return bool(
            self.claim
            and self.cited_records
            and self.retrieved_passages
            and self.validation_outcome
        )

    @property
    def broken_links(self) -> List[str]:
        missing = []
        if not self.claim:
            missing.append("klaim")
        if not self.cited_records:
            missing.append("jurnal terkutip")
        if not self.retrieved_passages:
            missing.append("kutipan terambil")
        if not self.validation_outcome:
            missing.append("hasil validasi")
        return missing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim[:300],
            "cited_records": self.cited_records[:10],
            "retrieved_passages": [
                {
                    "source_paper": p.get("source_paper", ""),
                    "quote": str(p.get("quote", ""))[:240],
                    "match_score": p.get("match_score"),
                }
                for p in self.retrieved_passages[:5]
            ],
            "validation_outcome": self.validation_outcome,
            "validation_detail": self.validation_detail,
            "complete": self.complete,
            "broken_links": self.broken_links,
        }


def build_provenance(
    claim: str,
    cited_records: Sequence[str],
    retrieved_passages: Sequence[Dict[str, Any]],
    validation_outcome: str = "",
    validation_detail: str = "",
) -> ProvenanceChain:
    """Assemble the provenance chain for one gap indicator."""
    return ProvenanceChain(
        claim=claim or "",
        cited_records=[r for r in cited_records if r],
        retrieved_passages=[p for p in retrieved_passages if p],
        validation_outcome=validation_outcome or "",
        validation_detail=validation_detail or "",
    )


# ---------------------------------------------------------------------------
# Persistence of the expert-labelled calibration set
# ---------------------------------------------------------------------------

DEFAULT_LABEL_FILENAME = "calibration_labels.json"


def _label_path(path: Optional[str] = None) -> Path:
    if path:
        return Path(path)
    env = os.getenv("GAP_CALIBRATION_LABELS")
    if env:
        return Path(env)
    # backend/data/calibration_labels.json — calibration.py lives at
    # backend/app/core/gap_detection/, so four parents up is `backend/`.
    return Path(__file__).resolve().parents[3] / "data" / DEFAULT_LABEL_FILENAME


def load_calibrator(path: Optional[str] = None) -> Calibrator:
    """Fit a calibrator from the stored expert-label set.

    The file holds records of ``{"confidence": float, "correct": 0|1}`` produced
    by human adjudication of past indicators. With fewer than
    ``MIN_CALIBRATION_LABELS`` records the calibrator stays an identity map, so
    the pipeline never silently rescales confidences on evidence that is too
    thin to support it.
    """
    target = _label_path(path)
    try:
        if not target.exists():
            return Calibrator()
        raw = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"Calibration labels unreadable ({target}): {exc}")
        return Calibrator()

    records = raw.get("labels", raw) if isinstance(raw, dict) else raw
    confidences: List[float] = []
    correctness: List[int] = []
    for rec in records or []:
        try:
            confidences.append(float(rec["confidence"]))
            correctness.append(1 if int(rec["correct"]) else 0)
        except (KeyError, TypeError, ValueError):
            continue

    if len(confidences) < MIN_CALIBRATION_LABELS:
        logger.info(
            f"Calibration set has {len(confidences)} label(s) "
            f"(< {MIN_CALIBRATION_LABELS}); using identity calibration"
        )
        return Calibrator(n_labels=len(confidences))

    calibrator = Calibrator.fit(confidences, correctness)
    logger.info(
        f"Calibrator fitted on {calibrator.n_labels} expert label(s): "
        f"T={calibrator.temperature}, cutoff={calibrator.conformal_cutoff}"
    )
    return calibrator
