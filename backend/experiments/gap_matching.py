"""
Pure matching + Precision/Recall/F1 helpers for gap-benchmark evaluation.

Kept dependency-free (no numpy/sklearn needed) so the matching logic is unit
testable in isolation. The embedding step lives in evaluate_gaps.py; here we
only operate on similarity scores.

Matching model: a *detected* indicator is a true positive when it can be paired
with a distinct *gold* gap whose semantic similarity is >= threshold. We use
greedy one-to-one matching (highest-similarity pairs first), which is the
standard, defensible choice for set-to-set alignment and prevents one strong
detection from "covering" several gold gaps (or vice-versa).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity between two equal-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def similarity_matrix(
    detected: List[Sequence[float]],
    gold: List[Sequence[float]],
) -> List[List[float]]:
    """Full cosine similarity matrix, rows = detected, cols = gold."""
    return [[cosine(d, g) for g in gold] for d in detected]


def greedy_match(
    sim: List[List[float]],
    threshold: float = 0.5,
) -> List[Tuple[int, int, float]]:
    """
    Greedy one-to-one matching above `threshold`.

    Returns list of (detected_idx, gold_idx, score) sorted by descending score;
    each detected and each gold index appears at most once.
    """
    pairs: List[Tuple[int, int, float]] = []
    for i, row in enumerate(sim):
        for j, s in enumerate(row):
            if s >= threshold:
                pairs.append((i, j, s))
    pairs.sort(key=lambda p: p[2], reverse=True)

    used_d, used_g = set(), set()
    matches = []
    for i, j, s in pairs:
        if i in used_d or j in used_g:
            continue
        used_d.add(i)
        used_g.add(j)
        matches.append((i, j, s))
    return matches


@dataclass
class PRF:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int
    n_detected: int
    n_gold: int

    def to_dict(self) -> dict:
        return {
            "precision": round(self.precision, 3),
            "recall": round(self.recall, 3),
            "f1": round(self.f1, 3),
            "tp": self.tp, "fp": self.fp, "fn": self.fn,
            "n_detected": self.n_detected, "n_gold": self.n_gold,
        }


def prf(n_detected: int, n_gold: int, tp: int) -> PRF:
    """Precision / Recall / F1 from match counts."""
    fp = n_detected - tp
    fn = n_gold - tp
    precision = tp / n_detected if n_detected else 0.0
    recall = tp / n_gold if n_gold else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return PRF(precision, recall, f1, tp, fp, fn, n_detected, n_gold)


def evaluate(
    detected_emb: List[Sequence[float]],
    gold_emb: List[Sequence[float]],
    threshold: float = 0.5,
) -> Tuple[PRF, List[Tuple[int, int, float]]]:
    """Embed-free evaluation: similarity → greedy match → PRF."""
    if not detected_emb or not gold_emb:
        return prf(len(detected_emb), len(gold_emb), 0), []
    sim = similarity_matrix(detected_emb, gold_emb)
    matches = greedy_match(sim, threshold)
    return prf(len(detected_emb), len(gold_emb), len(matches)), matches
