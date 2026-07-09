"""
Unit tests for experiment statistical helpers (effect sizes + bootstrap CI)
and the confidence-calibration metrics — pure functions, no external services.
"""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR / "experiments"))
sys.path.insert(0, str(BACKEND_DIR / "experiments" / "expert_eval"))

from stats_utils import (  # noqa: E402
    holm_bonferroni,
    per_run_mean_confidences,
    cliffs_delta,
    rank_biserial_from_u,
    bootstrap_ci_diff,
    format_effect,
)
from calibration import calibration_metrics  # noqa: E402


class TestHolmBonferroni:
    def test_known_example_preserves_original_order(self):
        assert holm_bonferroni([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])

    def test_none_values_are_preserved(self):
        assert holm_bonferroni([0.02, None, 0.5]) == pytest.approx([0.04, None, 0.5])


class TestPerRunAggregation:
    def test_mean_confidence_collapses_each_run(self):
        runs = [
            {"confidences": [0.2, 0.4]},
            {"confidences": [0.9]},
            {"confidences": []},
        ]
        assert per_run_mean_confidences(runs) == pytest.approx([0.3, 0.9])

    def test_falls_back_to_recorded_average(self):
        assert per_run_mean_confidences([{"avg_confidence": 0.7}]) == [0.7]


class TestCliffsDelta:
    def test_full_dominance(self):
        d, mag = cliffs_delta([5, 6, 7], [1, 2, 3])
        assert d == 1.0 and mag == "large"

    def test_reverse_dominance(self):
        d, _ = cliffs_delta([1, 2, 3], [5, 6, 7])
        assert d == -1.0

    def test_identical_negligible(self):
        d, mag = cliffs_delta([3, 3, 3], [3, 3, 3])
        assert d == 0.0 and mag == "negligible"

    def test_empty_returns_none(self):
        assert cliffs_delta([], [1, 2]) is None


class TestRankBiserial:
    def test_known_value(self):
        # U=0 with equal n → maximal effect r=1.0
        assert rank_biserial_from_u(0, 4, 4) == 1.0
        # U = n1*n2 → r = -1.0
        assert rank_biserial_from_u(16, 4, 4) == -1.0

    def test_zero_n(self):
        assert rank_biserial_from_u(5, 0, 3) is None


class TestBootstrapCI:
    def test_point_and_interval(self):
        a = [10, 11, 12, 13, 14]
        b = [1, 2, 3, 4, 5]
        res = bootstrap_ci_diff(a, b, seed=1)
        assert res is not None
        point, lo, hi = res
        assert point > 0          # a clearly greater
        assert lo <= point <= hi  # point within CI

    def test_insufficient_data(self):
        assert bootstrap_ci_diff([1], [2, 3]) is None

    def test_deterministic_with_seed(self):
        a, b = [5, 6, 7, 8], [1, 2, 3, 4]
        assert bootstrap_ci_diff(a, b, seed=7) == bootstrap_ci_diff(a, b, seed=7)


class TestFormatEffect:
    def test_contains_delta_and_ci(self):
        s = format_effect([5, 6, 7, 8], [1, 2, 3, 4], u=2.0)
        assert "δ=" in s and "Δmed=" in s and "r=" in s

    def test_empty(self):
        assert format_effect([], []) == "—"


class TestCalibration:
    def test_perfectly_calibrated_low_ece(self):
        # conf 0.5 with exactly half genuine → gap 0 in that bin
        pairs = [(0.5, 1), (0.5, 0), (0.5, 1), (0.5, 0)]
        m = calibration_metrics(pairs, n_bins=10)
        assert m["n"] == 4
        assert m["ece"] == pytest.approx(0.0, abs=1e-9)
        assert m["base_rate"] == 0.5

    def test_miscalibrated_high_ece(self):
        # high confidence but none genuine → large gap
        pairs = [(0.9, 0), (0.9, 0), (0.9, 0)]
        m = calibration_metrics(pairs, n_bins=10)
        assert m["ece"] > 0.5
        assert m["brier"] == pytest.approx(0.81, abs=1e-6)

    def test_empty_returns_none(self):
        assert calibration_metrics([]) is None
