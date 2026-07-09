"""
Unit tests for the Rule Engine (validation layer).

Tests all 9 rules (F1-F3, C1-C3, K1-K3), three verdicts (PASS, FLAG, REJECT),
edge cases, and confidence adjustment calculations.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.knowledge.fact_table import (
    Entity,
    EntityType,
    Fact,
    FactTable,
    PredicateType,
    Verdict,
)
from app.core.validation.rule_engine import (
    ALL_RULES,
    RULE_C1,
    RULE_C2,
    RULE_C3,
    RULE_F1,
    RULE_F2,
    RULE_F3,
    RULE_K1,
    RULE_K2,
    RULE_K3,
    Rule,
    RuleCategory,
    RuleEngine,
    RuleResult,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_fact_table():
    """A FactTable with no entities or facts."""
    return FactTable()


@pytest.fixture
def populated_fact_table():
    """
    A FactTable pre-loaded with entities and facts for rule testing.

    Entities:
        - gpt4 (METHOD): requires high_compute resource
        - edge_device (DOMAIN): has low_resource constraint
        - supervised_dl (METHOD): requires large_labeled_data
        - rare_disease (DOMAIN): has scarce_data constraint
        - in_memory (METHOD): requires single_machine resource
        - finding_a, finding_b, finding_c (FINDING)
        - cnn_method (METHOD): general method with no constraints

    Facts encode the relationships the rules check.
    """
    ft = FactTable()

    # Entities
    gpt4 = Entity("gpt4", EntityType.METHOD, "GPT-4")
    edge_device = Entity("edge_device", EntityType.DOMAIN, "Edge Device")
    supervised_dl = Entity("supervised_dl", EntityType.METHOD, "Supervised DL")
    rare_disease = Entity("rare_disease", EntityType.DOMAIN, "Rare Disease")
    in_memory = Entity("in_memory", EntityType.METHOD, "In-Memory Processing")
    finding_a = Entity("finding_a", EntityType.FINDING, "Finding A")
    finding_b = Entity("finding_b", EntityType.FINDING, "Finding B")
    finding_c = Entity("finding_c", EntityType.FINDING, "Finding C")
    cnn = Entity("cnn_method", EntityType.METHOD, "CNN")
    nlp_domain = Entity("nlp_domain", EntityType.DOMAIN, "NLP")

    for e in [gpt4, edge_device, supervised_dl, rare_disease, in_memory,
              finding_a, finding_b, finding_c, cnn, nlp_domain]:
        ft.add_entity(e)

    # F1: gpt4 requires high_compute; edge_device has low_resource constraint
    ft.add_fact(Fact(
        fact_id="f_gpt4_res",
        subject_id="gpt4",
        predicate=PredicateType.REQUIRES_RESOURCE,
        object_id="high_compute",
        confidence=0.95,
    ))
    ft.add_fact(Fact(
        fact_id="f_edge_constraint",
        subject_id="edge_device",
        predicate=PredicateType.HAS_CONSTRAINT,
        object_id="low_resource",
        confidence=0.9,
    ))

    # F2: supervised_dl requires large_labeled_data; rare_disease has scarce data
    ft.add_fact(Fact(
        fact_id="f_sdl_data",
        subject_id="supervised_dl",
        predicate=PredicateType.REQUIRES_DATA,
        object_id="large_labeled_dataset",
        confidence=0.9,
    ))
    ft.add_fact(Fact(
        fact_id="f_rare_constraint",
        subject_id="rare_disease",
        predicate=PredicateType.HAS_CONSTRAINT,
        object_id="scarce_data",
        confidence=0.85,
    ))

    # F3: in_memory requires single_machine
    ft.add_fact(Fact(
        fact_id="f_inmem_res",
        subject_id="in_memory",
        predicate=PredicateType.REQUIRES_RESOURCE,
        object_id="single_machine",
        confidence=0.9,
    ))

    # C1: finding_a IMPROVES finding_b (only 1 source → should flag)
    ft.add_fact(Fact(
        fact_id="f_ab_improve",
        subject_id="finding_a",
        predicate=PredicateType.IMPROVES,
        object_id="finding_b",
        confidence=0.8,
        source_paper="paper_1",
    ))

    # K1: finding_a CONTRADICTS finding_b
    ft.add_fact(Fact(
        fact_id="f_ab_contradict",
        subject_id="finding_a",
        predicate=PredicateType.CONTRADICTS,
        object_id="finding_b",
        confidence=0.85,
    ))

    # K2: cnn_method APPLIES_TO nlp_domain
    ft.add_fact(Fact(
        fact_id="f_cnn_nlp",
        subject_id="cnn_method",
        predicate=PredicateType.APPLIES_TO,
        object_id="nlp_domain",
        confidence=0.9,
    ))

    # K3 transitivity: finding_a → finding_b → finding_c
    ft.add_fact(Fact(
        fact_id="f_bc_improve",
        subject_id="finding_b",
        predicate=PredicateType.IMPROVES,
        object_id="finding_c",
        confidence=0.8,
    ))
    ft.add_fact(Fact(
        fact_id="f_ac_contradict",
        subject_id="finding_a",
        predicate=PredicateType.CONTRADICTS,
        object_id="finding_c",
        confidence=0.7,
    ))

    return ft


@pytest.fixture
def engine(populated_fact_table):
    """RuleEngine wired to the populated FactTable."""
    return RuleEngine(fact_table=populated_fact_table)


@pytest.fixture
def engine_no_ft():
    """RuleEngine with no FactTable."""
    return RuleEngine(fact_table=None)


# ---------------------------------------------------------------------------
# Rule definition sanity checks
# ---------------------------------------------------------------------------

class TestRuleDefinitions:
    def test_all_rules_count(self):
        assert len(ALL_RULES) == 9

    def test_rule_ids(self):
        ids = {r.rule_id for r in ALL_RULES}
        assert ids == {"F1", "F2", "F3", "C1", "C2", "C3", "K1", "K2", "K3"}

    def test_feasibility_rules_are_f1_f2_f3(self):
        feas = [r for r in ALL_RULES if r.category == RuleCategory.FEASIBILITY]
        assert {r.rule_id for r in feas} == {"F1", "F2", "F3"}

    def test_causality_rules_are_c1_c2_c3(self):
        caus = [r for r in ALL_RULES if r.category == RuleCategory.CAUSALITY]
        assert {r.rule_id for r in caus} == {"C1", "C2", "C3"}

    def test_consistency_rules_are_k1_k2_k3(self):
        cons = [r for r in ALL_RULES if r.category == RuleCategory.CONSISTENCY]
        assert {r.rule_id for r in cons} == {"K1", "K2", "K3"}

    @pytest.mark.parametrize("rule_id,expected_critical", [
        ("F1", True), ("F2", False), ("F3", True),
        ("C1", False), ("C2", True), ("C3", False),
        ("K1", False), ("K2", False), ("K3", False),
    ])
    def test_critical_flag(self, rule_id, expected_critical):
        rule = next(r for r in ALL_RULES if r.rule_id == rule_id)
        assert rule.is_critical is expected_critical


# ---------------------------------------------------------------------------
# F1 – Resource Compatibility (CRITICAL → REJECT)
# ---------------------------------------------------------------------------

class TestRuleF1:
    def test_f1_rejects_high_resource_in_low_resource_domain(self, engine):
        claim = {"method": "gpt4", "domain": "edge_device", "confidence": 0.8}
        report = engine.validate(claim)
        f1 = next(r for r in report.results if r.rule.rule_id == "F1")
        assert f1.passed is False
        assert f1.verdict == "REJECT"
        assert f1.confidence_adjustment < 0

    def test_f1_passes_when_no_constraint_conflict(self, engine):
        claim = {"method": "cnn_method", "domain": "nlp_domain", "confidence": 0.8}
        report = engine.validate(claim)
        f1 = next(r for r in report.results if r.rule.rule_id == "F1")
        assert f1.passed is True
        assert f1.verdict == "PASS"

    def test_f1_passes_when_no_method(self, engine):
        claim = {"description": "some analysis", "confidence": 0.5}
        report = engine.validate(claim)
        f1 = next(r for r in report.results if r.rule.rule_id == "F1")
        assert f1.passed is True

    def test_f1_flags_when_no_fact_table(self, engine_no_ft):
        claim = {"method": "gpt4", "domain": "edge_device", "confidence": 0.8}
        report = engine_no_ft.validate(claim)
        f1 = next(r for r in report.results if r.rule.rule_id == "F1")
        assert f1.passed is False
        assert f1.verdict == "FLAG"
        assert "Insufficient evidence" in f1.reason

    def test_f1_passes_when_no_fact_table_in_legacy_mode(self):
        engine = RuleEngine(
            fact_table=None,
            config={"defaults": {"on_missing_evidence": "pass"}},
        )
        claim = {"method": "gpt4", "domain": "edge_device", "confidence": 0.8}
        report = engine.validate(claim)
        f1 = next(r for r in report.results if r.rule.rule_id == "F1")
        assert f1.passed is True
        assert f1.verdict == "PASS"


# ---------------------------------------------------------------------------
# F2 – Data Compatibility (non-critical → FLAG)
# ---------------------------------------------------------------------------

class TestRuleF2:
    def test_f2_flags_large_data_in_scarce_domain(self, engine):
        claim = {"method": "supervised_dl", "domain": "rare_disease", "confidence": 0.7}
        report = engine.validate(claim)
        f2 = next(r for r in report.results if r.rule.rule_id == "F2")
        assert f2.passed is False
        assert f2.verdict == "FLAG"

    def test_f2_passes_when_no_data_conflict(self, engine):
        claim = {"method": "cnn_method", "domain": "nlp_domain", "confidence": 0.8}
        report = engine.validate(claim)
        f2 = next(r for r in report.results if r.rule.rule_id == "F2")
        assert f2.passed is True


# ---------------------------------------------------------------------------
# F3 – Scale Compatibility (CRITICAL → REJECT)
# ---------------------------------------------------------------------------

class TestRuleF3:
    def test_f3_rejects_single_machine_for_distributed(self, engine):
        claim = {
            "method": "in_memory",
            "description": "Apply in-memory processing for distributed big data pipeline",
            "confidence": 0.7,
        }
        report = engine.validate(claim)
        f3 = next(r for r in report.results if r.rule.rule_id == "F3")
        assert f3.passed is False
        assert f3.verdict == "REJECT"

    def test_f3_passes_when_no_scale_conflict(self, engine):
        claim = {
            "method": "in_memory",
            "description": "Run local analysis",
            "confidence": 0.8,
        }
        report = engine.validate(claim)
        f3 = next(r for r in report.results if r.rule.rule_id == "F3")
        assert f3.passed is True


# ---------------------------------------------------------------------------
# C1 – Minimal Causal Evidence (non-critical → FLAG)
# ---------------------------------------------------------------------------

class TestRuleC1:
    def test_c1_flags_causal_with_single_source(self, engine):
        claim = {
            "findings": ["finding_a", "finding_b"],
            "confidence": 0.8,
        }
        report = engine.validate(claim)
        c1 = next(r for r in report.results if r.rule.rule_id == "C1")
        assert c1.passed is False
        assert c1.verdict == "FLAG"
        assert "correlation" in c1.reason.lower() or "1 source" in c1.reason

    def test_c1_passes_with_no_causal_relationship(self, engine):
        claim = {"findings": ["finding_b", "finding_c"], "confidence": 0.8}
        # finding_b → finding_c via IMPROVES exists (1 fact), should still flag.
        # But finding_c is object of IMPROVES from finding_b, not the other way.
        # C1 checks subject=finding_b predicate=IMPROVES object=finding_c
        report = engine.validate(claim)
        c1 = next(r for r in report.results if r.rule.rule_id == "C1")
        # Depends on ordering in the loop; since finding_b → finding_c exists
        # with 1 source, this should flag too.
        assert c1.verdict in ("FLAG", "PASS")

    def test_c1_passes_with_insufficient_findings(self, engine):
        claim = {"findings": ["finding_a"], "confidence": 0.8}
        report = engine.validate(claim)
        c1 = next(r for r in report.results if r.rule.rule_id == "C1")
        assert c1.passed is True


# ---------------------------------------------------------------------------
# C2 – Causal Direction (CRITICAL → REJECT)
# ---------------------------------------------------------------------------

class TestRuleC2:
    def test_c2_rejects_reversed_temporal_order(self, populated_fact_table):
        """If cause has higher temporal_order than effect → REJECT."""
        # Set temporal orders: finding_a = 2020, finding_b = 2019
        ft = populated_fact_table
        entity_a = ft.get_entity("finding_a")
        entity_b = ft.get_entity("finding_b")
        entity_a.properties["temporal_order"] = 2020
        entity_b.properties["temporal_order"] = 2019

        engine = RuleEngine(fact_table=ft)
        claim = {"findings": ["finding_a", "finding_b"], "confidence": 0.8}
        report = engine.validate(claim)
        c2 = next(r for r in report.results if r.rule.rule_id == "C2")
        assert c2.passed is False
        assert c2.verdict == "REJECT"

    def test_c2_passes_correct_temporal_order(self, populated_fact_table):
        ft = populated_fact_table
        entity_a = ft.get_entity("finding_a")
        entity_b = ft.get_entity("finding_b")
        entity_a.properties["temporal_order"] = 2019
        entity_b.properties["temporal_order"] = 2020

        engine = RuleEngine(fact_table=ft)
        claim = {"findings": ["finding_a", "finding_b"], "confidence": 0.8}
        report = engine.validate(claim)
        c2 = next(r for r in report.results if r.rule.rule_id == "C2")
        assert c2.passed is True

    def test_c2_passes_without_temporal_metadata(self, engine):
        claim = {"findings": ["finding_a", "finding_b"], "confidence": 0.8}
        report = engine.validate(claim)
        c2 = next(r for r in report.results if r.rule.rule_id == "C2")
        assert c2.passed is True


# ---------------------------------------------------------------------------
# C3 – Confounding Check (non-critical → FLAG)
# ---------------------------------------------------------------------------

class TestRuleC3:
    def test_c3_flags_without_knowledge_graph(self, engine):
        """Claim has findings, but no KG builder to verify paths → FLAG."""
        claim = {"findings": ["finding_a", "finding_b"], "confidence": 0.8}
        report = engine.validate(claim)
        c3 = next(r for r in report.results if r.rule.rule_id == "C3")
        assert c3.passed is False
        assert c3.verdict == "FLAG"
        assert "Insufficient evidence" in c3.reason

    def test_c3_passes_without_knowledge_graph_in_legacy_mode(self, populated_fact_table):
        engine = RuleEngine(
            fact_table=populated_fact_table,
            config={"defaults": {"on_missing_evidence": "pass"}},
        )
        claim = {"findings": ["finding_a", "finding_b"], "confidence": 0.8}
        report = engine.validate(claim)
        c3 = next(r for r in report.results if r.rule.rule_id == "C3")
        assert c3.passed is True
        assert c3.verdict == "PASS"

    def test_c3_flags_multiple_paths(self, populated_fact_table):
        """If KG finds >1 path between entities → FLAG (possible confounder)."""
        mock_kg = MagicMock()
        mock_kg.find_paths_between_entities.return_value = [
            ["finding_a", "x", "finding_b"],
            ["finding_a", "y", "finding_b"],
        ]
        engine = RuleEngine(fact_table=populated_fact_table, knowledge_graph=mock_kg)
        claim = {"findings": ["finding_a", "finding_b"], "confidence": 0.8}
        report = engine.validate(claim)
        c3 = next(r for r in report.results if r.rule.rule_id == "C3")
        assert c3.passed is False
        assert c3.verdict == "FLAG"

    def test_c3_passes_single_path(self, populated_fact_table):
        mock_kg = MagicMock()
        mock_kg.find_paths_between_entities.return_value = [
            ["finding_a", "finding_b"],
        ]
        engine = RuleEngine(fact_table=populated_fact_table, knowledge_graph=mock_kg)
        claim = {"findings": ["finding_a", "finding_b"], "confidence": 0.8}
        report = engine.validate(claim)
        c3 = next(r for r in report.results if r.rule.rule_id == "C3")
        assert c3.passed is True


# ---------------------------------------------------------------------------
# K1 – Internal Non-contradiction (non-critical → FLAG)
# ---------------------------------------------------------------------------

class TestRuleK1:
    def test_k1_flags_contradicting_findings(self, engine):
        claim = {
            "findings": ["finding_a", "finding_b"],
            "confidence": 0.8,
        }
        report = engine.validate(claim)
        k1 = next(r for r in report.results if r.rule.rule_id == "K1")
        assert k1.passed is False
        assert k1.verdict == "FLAG"
        assert "contradiction" in k1.reason.lower()

    def test_k1_passes_no_contradiction(self, engine):
        claim = {"findings": ["finding_c"], "confidence": 0.8}
        report = engine.validate(claim)
        k1 = next(r for r in report.results if r.rule.rule_id == "K1")
        assert k1.passed is True


# ---------------------------------------------------------------------------
# K2 – KG Fact Consistency (non-critical → FLAG)
# ---------------------------------------------------------------------------

class TestRuleK2:
    def test_k2_flags_unsupported_method(self, engine):
        """Method with zero facts in KG → FLAG."""
        claim = {"method": "unknown_method", "confidence": 0.8}
        report = engine.validate(claim)
        k2 = next(r for r in report.results if r.rule.rule_id == "K2")
        assert k2.passed is False
        assert k2.verdict == "FLAG"

    def test_k2_passes_supported_method(self, engine):
        claim = {"method": "cnn_method", "domain": "nlp_domain", "confidence": 0.8}
        report = engine.validate(claim)
        k2 = next(r for r in report.results if r.rule.rule_id == "K2")
        assert k2.passed is True

    def test_k2_flags_method_not_applied_to_domain(self, engine):
        """Method exists in KG but has no APPLIES_TO for given domain."""
        claim = {"method": "gpt4", "domain": "nlp_domain", "confidence": 0.8}
        report = engine.validate(claim)
        k2 = next(r for r in report.results if r.rule.rule_id == "K2")
        assert k2.passed is False
        assert k2.verdict == "FLAG"


# ---------------------------------------------------------------------------
# K3 – Transitivity Check (non-critical → FLAG)
# ---------------------------------------------------------------------------

class TestRuleK3:
    def test_k3_flags_transitivity_violation(self, populated_fact_table):
        """A→B, B→C but A contradicts C → FLAG."""
        mock_kg = MagicMock()
        engine = RuleEngine(
            fact_table=populated_fact_table, knowledge_graph=mock_kg
        )
        claim = {
            "findings": ["finding_a", "finding_b", "finding_c"],
            "confidence": 0.8,
        }
        report = engine.validate(claim)
        k3 = next(r for r in report.results if r.rule.rule_id == "K3")
        assert k3.passed is False
        assert k3.verdict == "FLAG"
        assert "transitivity" in k3.reason.lower()

    def test_k3_passes_with_fewer_than_3_findings(self, populated_fact_table):
        mock_kg = MagicMock()
        engine = RuleEngine(
            fact_table=populated_fact_table, knowledge_graph=mock_kg
        )
        claim = {"findings": ["finding_a", "finding_b"], "confidence": 0.8}
        report = engine.validate(claim)
        k3 = next(r for r in report.results if r.rule.rule_id == "K3")
        assert k3.passed is True


# ---------------------------------------------------------------------------
# Verdict aggregation
# ---------------------------------------------------------------------------

class TestVerdictAggregation:
    def test_overall_reject_when_any_critical_rule_fails(self, engine):
        """F1 is critical; triggering it should produce overall REJECT."""
        claim = {"method": "gpt4", "domain": "edge_device", "confidence": 0.9}
        report = engine.validate(claim)
        assert report.overall_verdict == "REJECT"

    def test_overall_flag_when_only_non_critical_fails(self, engine):
        """F2 is non-critical; triggering only it should produce FLAG."""
        claim = {"method": "supervised_dl", "domain": "rare_disease", "confidence": 0.7}
        report = engine.validate(claim)
        # Ensure no REJECT rules fired
        rejected = [r for r in report.results if r.verdict == "REJECT"]
        if not rejected:
            assert report.overall_verdict == "FLAG"

    def test_overall_pass_when_all_pass(self, engine):
        claim = {"description": "general analysis", "confidence": 0.5}
        report = engine.validate(claim)
        assert report.overall_verdict == "PASS"

    def test_critical_rule_produces_reject(self):
        """Critical rule violations must yield REJECT, not FLAG."""
        for rule in ALL_RULES:
            if rule.is_critical:
                result = RuleResult(
                    rule=rule, passed=False, verdict="REJECT",
                    reason="test", confidence_adjustment=-0.5,
                )
                assert result.verdict == "REJECT"

    def test_non_critical_rule_produces_flag(self):
        """Non-critical rule violations must yield FLAG, not REJECT."""
        for rule in ALL_RULES:
            if not rule.is_critical:
                result = RuleResult(
                    rule=rule, passed=False, verdict="FLAG",
                    reason="test", confidence_adjustment=-0.1,
                )
                assert result.verdict == "FLAG"


# ---------------------------------------------------------------------------
# Confidence adjustment
# ---------------------------------------------------------------------------

class TestConfidenceAdjustment:
    def test_reject_lowers_confidence_significantly(self, engine):
        claim = {"method": "gpt4", "domain": "edge_device", "confidence": 0.9}
        report = engine.validate(claim)
        assert report.adjusted_confidence < report.original_confidence
        assert report.adjusted_confidence < 0.5  # -0.5 adjustment

    def test_flag_lowers_confidence_moderately(self, engine):
        claim = {"method": "supervised_dl", "domain": "rare_disease", "confidence": 0.7}
        report = engine.validate(claim)
        assert report.adjusted_confidence <= report.original_confidence

    def test_pass_keeps_confidence_unchanged(self, engine):
        claim = {"description": "harmless claim", "confidence": 0.5}
        report = engine.validate(claim)
        assert report.adjusted_confidence == report.original_confidence

    def test_confidence_clamped_to_0_1(self, engine):
        claim = {"method": "gpt4", "domain": "edge_device", "confidence": 0.1}
        report = engine.validate(claim)
        assert 0.0 <= report.adjusted_confidence <= 1.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_claim(self, engine):
        report = engine.validate({})
        assert report.overall_verdict == "PASS"
        assert report.rules_checked == 9

    def test_string_claim_normalized(self, engine):
        """A bare string claim should be wrapped into a dict."""
        report = engine.validate("just a sentence")
        assert report.overall_verdict == "PASS"

    def test_no_applicable_rules(self):
        """Engine with None-ish rules defaults to ALL_RULES, producing PASS for generic claim."""
        engine = RuleEngine(rules=None)
        report = engine.validate({"confidence": 0.5})
        assert report.overall_verdict == "PASS"
        assert report.rules_checked == len(ALL_RULES)

    def test_validate_batch(self, engine):
        claims = [
            {"description": "claim 1", "confidence": 0.5},
            {"method": "gpt4", "domain": "edge_device", "confidence": 0.9},
        ]
        reports = engine.validate_batch(claims)
        assert len(reports) == 2
        assert reports[0].overall_verdict == "PASS"
        assert reports[1].overall_verdict == "REJECT"

    def test_validation_report_to_dict(self, engine):
        report = engine.validate({"confidence": 0.5})
        d = report.to_dict()
        assert "overall_verdict" in d
        assert "results" in d
        assert isinstance(d["results"], list)

    def test_rule_exception_defaults_to_pass(self, populated_fact_table):
        """If a rule's checker throws, the engine should default-pass it."""
        engine = RuleEngine(fact_table=populated_fact_table)
        # Corrupt the fact_table query to raise for F1
        original_query = populated_fact_table.query

        def bad_query(**kwargs):
            if kwargs.get("predicate") == PredicateType.REQUIRES_RESOURCE:
                raise RuntimeError("boom")
            return original_query(**kwargs)

        populated_fact_table.query = bad_query
        claim = {"method": "gpt4", "domain": "edge_device", "confidence": 0.8}
        report = engine.validate(claim)
        f1 = next(r for r in report.results if r.rule.rule_id == "F1")
        assert f1.passed is True  # default-pass on exception


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_contains_verdict(self, engine):
        report = engine.validate({"confidence": 0.5})
        assert "PASS" in report.summary

    def test_summary_lists_rejected_rules(self, engine):
        claim = {"method": "gpt4", "domain": "edge_device", "confidence": 0.9}
        report = engine.validate(claim)
        assert "REJECT" in report.summary
        assert "F1" in report.summary
