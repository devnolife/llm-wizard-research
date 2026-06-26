"""
Unit tests for the gap-benchmark matching core (cosine, greedy 1-1 match,
Precision/Recall/F1) — pure functions, no embeddings/services.
"""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR / "experiments"))

from gap_matching import cosine, greedy_match, prf, evaluate  # noqa: E402


class TestCosine:
    def test_identical(self):
        assert cosine([1, 0, 1], [1, 0, 1]) == pytest.approx(1.0)

    def test_orthogonal(self):
        assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_zero_vector(self):
        assert cosine([0, 0], [1, 1]) == 0.0


class TestGreedyMatch:
    def test_one_to_one_highest_first(self):
        # detected x gold similarity
        sim = [
            [0.9, 0.2],  # d0 best with g0
            [0.8, 0.85],  # d1 would like g0 (0.8) but g0 taken → g1 (0.85)
        ]
        matches = greedy_match(sim, threshold=0.5)
        pairs = {(i, j) for i, j, _ in matches}
        assert pairs == {(0, 0), (1, 1)}

    def test_threshold_excludes(self):
        sim = [[0.4, 0.3]]
        assert greedy_match(sim, threshold=0.5) == []

    def test_no_double_assignment(self):
        sim = [[0.9], [0.95]]  # two detected, one gold → only one matches
        matches = greedy_match(sim, threshold=0.5)
        assert len(matches) == 1
        assert matches[0][0] == 1  # the 0.95 (higher) wins the single gold


class TestPRF:
    def test_perfect(self):
        p = prf(n_detected=5, n_gold=5, tp=5)
        assert p.precision == 1.0 and p.recall == 1.0 and p.f1 == 1.0

    def test_half_recall(self):
        # detected 4, gold 8, tp 4 → precision 1.0, recall 0.5
        p = prf(n_detected=4, n_gold=8, tp=4)
        assert p.precision == 1.0
        assert p.recall == 0.5
        assert p.f1 == pytest.approx(2 * 1.0 * 0.5 / 1.5)
        assert p.fp == 0 and p.fn == 4

    def test_low_precision(self):
        p = prf(n_detected=10, n_gold=3, tp=3)
        assert p.precision == pytest.approx(0.3)
        assert p.recall == 1.0

    def test_empty(self):
        p = prf(0, 0, 0)
        assert p.precision == 0.0 and p.recall == 0.0 and p.f1 == 0.0


class TestEvaluateEmb:
    def test_end_to_end_with_vectors(self):
        # 2 detected, 2 gold; d0~g0, d1~g1 (distinct axes)
        detected = [[1, 0, 0], [0, 1, 0]]
        gold = [[1, 0, 0], [0, 1, 0]]
        p, matches = evaluate(detected, gold, threshold=0.5)
        assert p.recall == 1.0 and p.precision == 1.0
        assert len(matches) == 2

    def test_partial_recall(self):
        # detected only covers 1 of 2 gold
        detected = [[1, 0, 0]]
        gold = [[1, 0, 0], [0, 1, 0]]
        p, _ = evaluate(detected, gold, threshold=0.5)
        assert p.recall == 0.5
        assert p.precision == 1.0

    def test_empty_detected_zero_recall(self):
        p, _ = evaluate([], [[1, 0]], threshold=0.5)
        assert p.recall == 0.0 and p.n_gold == 1
