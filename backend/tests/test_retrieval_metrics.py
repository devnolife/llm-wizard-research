"""
Unit tests for retrieval ranking metrics (MRR, nDCG@k, Recall@k, P@k) and the
ID/EN language heuristic — pure functions, no services.
"""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR / "experiments"))

from retrieval_metrics import (  # noqa: E402
    reciprocal_rank, recall_at_k, precision_at_k, ndcg_at_k, dcg_at_k, aggregate,
)
from evaluate_retrieval import detect_language  # noqa: E402


class TestReciprocalRank:
    def test_first_position(self):
        assert reciprocal_rank([1, 0, 0]) == 1.0

    def test_second_position(self):
        assert reciprocal_rank([0, 1, 0]) == 0.5

    def test_none_relevant(self):
        assert reciprocal_rank([0, 0, 0]) == 0.0


class TestRecallPrecision:
    def test_recall_partial(self):
        assert recall_at_k([1, 0, 1], total_relevant=4, k=3) == 0.5

    def test_recall_caps_at_k(self):
        assert recall_at_k([1, 1, 1, 1], total_relevant=4, k=2) == 0.5

    def test_recall_zero_relevant(self):
        assert recall_at_k([0], 0, 1) == 0.0

    def test_precision(self):
        assert precision_at_k([1, 1, 0], k=2) == 1.0
        assert precision_at_k([0, 0, 1], k=2) == 0.0


class TestNDCG:
    def test_perfect_ranking(self):
        assert ndcg_at_k([1, 1], total_relevant=2, k=2) == pytest.approx(1.0)

    def test_worse_than_ideal(self):
        # one relevant at rank 2 only
        v = ndcg_at_k([0, 1], total_relevant=1, k=2)
        assert 0 < v < 1.0

    def test_empty(self):
        assert ndcg_at_k([], 2, 5) == 0.0

    def test_dcg_monotonic(self):
        # relevant earlier should yield higher DCG
        assert dcg_at_k([1, 0], 2) > dcg_at_k([0, 1], 2)


class TestAggregate:
    def test_mean(self):
        rows = [{"mrr": 1.0, "ndcg@5": 0.8}, {"mrr": 0.0, "ndcg@5": 0.4}]
        agg = aggregate(rows)
        assert agg["mrr"] == 0.5
        assert agg["ndcg@5"] == 0.6

    def test_empty(self):
        assert aggregate([]) == {}


class TestLanguageDetect:
    def test_english(self):
        assert detect_language("the model was trained using the attention method") == "en"

    def test_indonesian(self):
        assert detect_language("penelitian ini menggunakan metode dengan data dari sumber") == "id"

    def test_unknown(self):
        assert detect_language("xyz qrs") == "unknown"
