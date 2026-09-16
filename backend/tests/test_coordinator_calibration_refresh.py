"""The coordinator's Rule Engine pass is the verdict that gets reported, so the
calibrated confidence, abstention flag and provenance chain attached earlier
by the analyzer must be re-fused with *that* verdict.

Regression: the analyzer validated with an "insufficient evidence" FLAG
(calibration x0.80), the coordinator then re-validated to PASS and overwrote
the verdict only — records ended up saying ``PASS`` while still carrying the
FLAG discount (0.878 -> 0.702 instead of 0.878 -> 0.966).
"""

from types import SimpleNamespace

from app.core.agents.coordinator import CoordinatorAgent


class _Rule:
    def __init__(self, rule_id):
        self.rule_id = rule_id


class _StubRuleEngine:
    def __init__(self, verdict, adjusted, fired=()):
        self._verdict = verdict
        self._adjusted = adjusted
        self._fired = fired

    def validate(self, claim, context=None):
        results = [
            SimpleNamespace(rule=_Rule(rid), verdict="FLAG", passed=False)
            for rid in self._fired
        ]
        return SimpleNamespace(
            overall_verdict=self._verdict,
            adjusted_confidence=self._adjusted,
            results=results,
            rules_checked=9,
        )


def _indicator(**overrides):
    base = {
        "type": "FRAGMENTATION",
        "description": "Bibliographic coupling: 26 journals split into 19 groups",
        "confidence": 0.878,
        "evidence": [],
        "related_papers": ["a.pdf", "b.pdf"],
        "supporting_quotes": [{"quote": "q", "source_paper": "a.pdf"}],
        # What the analyzer attached against its own (FLAG) validation pass.
        "rule_engine_verdict": "FLAG",
        "calibrated_confidence": 0.7024,
        "needs_review": False,
        "abstention_reasons": [],
        "calibration": {
            "raw_confidence": 0.878,
            "calibrated_confidence": 0.7024,
            "temperature": 1.0,
            "conformal_cutoff": None,
            "rule_verdict": "FLAG",
            "needs_review": False,
            "abstention_reasons": [],
            "calibrator_fitted": False,
            "calibration_labels": 0,
        },
        "provenance": {
            "claim": "Bibliographic coupling ...",
            "cited_records": ["a.pdf", "b.pdf"],
            "retrieved_passages": [{"source_paper": "a.pdf", "quote": "q"}],
            "validation_outcome": "FLAG",
            "validation_detail": "C3:FLAG, K3:FLAG",
            "complete": True,
            "broken_links": [],
        },
    }
    base.update(overrides)
    return base


def _run_act(indicator, engine):
    agent = CoordinatorAgent(rule_engine=engine)
    out = agent._node_act({
        "query": "topik",
        "context": {},
        "gap_indicators": [indicator],
        "retrieved_papers": [],
    })
    return out["gap_indicators"][0], out["rule_engine_report"]


def test_final_pass_verdict_refuses_stale_flag_calibration():
    ind, report = _run_act(_indicator(), _StubRuleEngine("PASS", 0.878))

    assert ind["rule_engine_verdict"] == "PASS"
    assert report == {"total": 1, "passed": 1, "flagged": 0, "rejected": 0}
    # PASS corroborates: 0.878 * 1.10 = 0.9658, not the FLAG discount.
    assert ind["calibrated_confidence"] == 0.9658
    assert ind["calibration"]["rule_verdict"] == "PASS"
    assert ind["calibration"]["raw_confidence"] == 0.878
    assert ind["needs_review"] is False
    assert ind["requires_human_validation"] is False
    assert ind["provenance"]["validation_outcome"] == "PASS"
    assert ind["provenance"]["validation_detail"] == "9 aturan diuji, tidak ada pelanggaran"


def test_final_flag_verdict_keeps_discount_and_lists_fired_rules():
    ind, _ = _run_act(_indicator(), _StubRuleEngine("FLAG", 0.878, fired=("C1",)))

    assert ind["rule_engine_verdict"] == "FLAG"
    assert ind["calibrated_confidence"] == 0.7024
    assert ind["requires_human_validation"] is True
    assert ind["provenance"]["validation_detail"] == "C1:FLAG"


def test_provenance_abstention_survives_refresh():
    broken = _indicator(
        supporting_quotes=[],
        needs_review=True,
        abstention_reasons=["provenans belum lengkap: kutipan terambil hilang"],
    )
    broken["provenance"].update({"complete": False, "broken_links": ["kutipan terambil"]})

    ind, _ = _run_act(broken, _StubRuleEngine("PASS", 0.711))

    # A PASS cannot heal a broken chain: the record stays flagged for review.
    assert ind["needs_review"] is True
    assert ind["requires_human_validation"] is True
    assert "provenans belum lengkap: kutipan terambil hilang" in ind["abstention_reasons"]
    assert ind["calibration"]["rule_verdict"] == "PASS"


def test_indicator_without_calibration_is_left_alone():
    plain = {"type": "INCOMPLETENESS", "description": "x", "confidence": 0.6, "evidence": []}
    ind, _ = _run_act(plain, _StubRuleEngine("PASS", 0.6))

    assert ind["rule_engine_verdict"] == "PASS"
    assert "calibration" not in ind
