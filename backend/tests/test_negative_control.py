"""Tests for negative-control (false-gap) metric separation (Fase 2)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments"))

from run_experiment import compile_results  # noqa: E402


def _phase3(topics):
    return {"topics": topics, "total_time": 1.0}


def _empty_phases():
    phase1 = {"papers": [{"filename": "a.pdf"}], "total_chunks": 10, "total_time": 1}
    phase2 = {"papers": [], "total_facts": 50, "total_time": 1}
    phase4 = {"summary": {"pass_rate": 100.0, "flag_rate": 0.0, "reject_rate": 0.0}, "total_time": 0}
    phase5 = {"summary": {"accuracy": 100.0}, "total_time": 0}
    return phase1, phase2, phase4, phase5


def _topic(key, n_indicators, confs):
    return {
        "topic": f"query {key}",
        "topic_key": key,
        "total_indicators": n_indicators,
        "indicators": [{"confidence": c, "adjusted_confidence": c} for c in confs],
        "confidence_scores": list(confs),
    }


class TestNegativeControlSeparation:
    def test_control_topics_excluded_from_main_metrics(self):
        phase1, phase2, phase4, phase5 = _empty_phases()
        phase3 = _phase3([
            _topic("T1", 5, [0.8] * 5),
            _topic("TC", 3, [0.9] * 3),  # false gaps on control topic
        ])
        report = compile_results(
            phase1, phase2, phase3, phase4, phase5,
            mode="nli", model_name="m", topics={}, seed=42,
        )
        m = report["overall_metrics"]
        assert m["total_gap_indicators"] == 5      # TC excluded
        assert m["topics_analyzed"] == 1
        assert m["avg_confidence"] == 0.8          # TC confidences excluded
        assert m["negative_control_topics"] == 1
        assert m["negative_control_false_gaps"] == 3
        assert m["negative_control_avg_confidence"] == 0.9

    def test_clean_control_zero_false_gaps(self):
        phase1, phase2, phase4, phase5 = _empty_phases()
        phase3 = _phase3([
            _topic("T1", 4, [0.7] * 4),
            _topic("TC", 0, []),
        ])
        report = compile_results(
            phase1, phase2, phase3, phase4, phase5,
            mode="full", model_name="m", topics={}, seed=42,
        )
        m = report["overall_metrics"]
        assert m["negative_control_false_gaps"] == 0
        assert m["negative_control_avg_confidence"] == 0

    def test_no_control_topic_no_metric(self):
        phase1, phase2, phase4, phase5 = _empty_phases()
        phase3 = _phase3([_topic("T1", 4, [0.7] * 4)])
        report = compile_results(
            phase1, phase2, phase3, phase4, phase5,
            mode="full", model_name="m", topics={}, seed=42,
        )
        assert "negative_control_false_gaps" not in report["overall_metrics"]

    def test_tc_prefix_case_insensitive(self):
        phase1, phase2, phase4, phase5 = _empty_phases()
        phase3 = _phase3([
            _topic("T1", 2, [0.7] * 2),
            _topic("tc1", 1, [0.5]),
        ])
        report = compile_results(
            phase1, phase2, phase3, phase4, phase5,
            mode="full", model_name="m", topics={}, seed=42,
        )
        m = report["overall_metrics"]
        assert m["total_gap_indicators"] == 2
        assert m["negative_control_false_gaps"] == 1


class TestRunMultiControlAggregation:
    def test_aggregate_includes_control_table(self):
        from run_multi import aggregate

        data = {
            "nli": [
                {"run_index": 1, "seed": 43, "indicators": 20, "avg_confidence": 0.8,
                 "facts": 100, "rerr": 0, "confidences": [0.8], "false_gaps": 0},
                {"run_index": 2, "seed": 44, "indicators": 22, "avg_confidence": 0.79,
                 "facts": 110, "rerr": 0, "confidences": [0.79], "false_gaps": 2},
            ],
        }
        md = aggregate("test-model", data)
        assert "Kontrol Negatif" in md
        assert "| nli | 2 |" in md
        assert "1/2" in md  # one clean run out of two

    def test_aggregate_no_control_no_table(self):
        from run_multi import aggregate

        data = {
            "nli": [
                {"run_index": 1, "seed": 43, "indicators": 20, "avg_confidence": 0.8,
                 "facts": 100, "rerr": 0, "confidences": [0.8], "false_gaps": None},
            ],
        }
        md = aggregate("test-model", data)
        assert "Kontrol Negatif" not in md
