"""
Integration tests — end-to-end flow verification.

Covers:
    1. FactTable → RuleEngine  (F1/K1 rules, REJECT explanations)
    2. FactTable → RelationClassifier  (causal vs co-occurrence validation)
    3. GapAnalyzer → RuleEngine  (verdict, filtering, confidence adjustment)
    4. Full pipeline mock  (coordinator-style flow with all components)

All tests run offline — no Ollama, no ChromaDB.
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
    RuleEngine,
    ValidationReport,
)
from app.core.validation.relation_classifier import (
    RelationClassifier,
    RelationType,
)
from app.core.gap_detection.analyzer import (
    GapAnalyzer,
    GapIndicator,
)
from app.core.knowledge.fact_extractor import FactExtractor
from app.models.responses import (
    IndicatorType,
    RuleVerdictType,
    AnalysisResponseModel,
    GapIndicatorModel,
    RuleEngineReportModel,
    RuleResultModel,
    ReasoningStep,
)


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def fact_table():
    """Empty FactTable ready for population."""
    return FactTable()


@pytest.fixture
def populated_fact_table(fact_table):
    """
    FactTable pre-loaded with a realistic research scenario:

    - METHOD: deep_learning (requires high GPU)
    - METHOD: random_forest (low resource)
    - DOMAIN: edge_computing (low-resource constraint)
    - DOMAIN: medical_imaging
    - FINDING: finding_A ("DL achieves 95% accuracy")
    - FINDING: finding_B ("RF achieves 91% accuracy")
    - FINDING: finding_C (contradicts finding_A)
    """
    ft = fact_table

    # Entities
    dl = Entity("deep_learning", EntityType.METHOD, "Deep Learning",
                properties={"resource_requirement": "high"})
    rf = Entity("random_forest", EntityType.METHOD, "Random Forest",
                properties={"resource_requirement": "low"})
    edge = Entity("edge_computing", EntityType.DOMAIN, "Edge Computing",
                  properties={"constraint": "low_resource"})
    med = Entity("medical_imaging", EntityType.DOMAIN, "Medical Imaging")
    fa = Entity("finding_A", EntityType.FINDING, "DL achieves 95% accuracy")
    fb = Entity("finding_B", EntityType.FINDING, "RF achieves 91% accuracy")
    fc = Entity("finding_C", EntityType.FINDING, "DL only reaches 80% on noisy data")

    for e in [dl, rf, edge, med, fa, fb, fc]:
        ft.add_entity(e)

    # Facts
    ft.add_fact(Fact(
        fact_id="f1", subject_id="deep_learning",
        predicate=PredicateType.REQUIRES_RESOURCE,
        object_id="high_gpu", source="Sec 3", source_paper="paper1",
        confidence=0.95,
    ))
    ft.add_fact(Fact(
        fact_id="f2", subject_id="edge_computing",
        predicate=PredicateType.HAS_CONSTRAINT,
        object_id="low_power_device", source="Sec 2", source_paper="paper2",
        confidence=0.9,
    ))
    ft.add_fact(Fact(
        fact_id="f3", subject_id="deep_learning",
        predicate=PredicateType.APPLIES_TO,
        object_id="medical_imaging", source="Sec 4", source_paper="paper1",
        confidence=0.9,
    ))
    ft.add_fact(Fact(
        fact_id="f4", subject_id="deep_learning",
        predicate=PredicateType.ACHIEVES,
        object_id="finding_A", source="Sec 5", source_paper="paper1",
        confidence=0.92,
    ))
    # Contradiction
    ft.add_fact(Fact(
        fact_id="f5", subject_id="finding_A",
        predicate=PredicateType.CONTRADICTS,
        object_id="finding_C", source="Sec 6", source_paper="paper3",
        confidence=0.85,
    ))

    return ft


@pytest.fixture
def rule_engine(populated_fact_table):
    """RuleEngine wired to the populated FactTable (no KG)."""
    return RuleEngine(fact_table=populated_fact_table)


@pytest.fixture
def relation_classifier():
    """RelationClassifier without LLM."""
    return RelationClassifier(llm_interface=None, similarity_threshold=0.3)


@pytest.fixture
def mock_llm():
    """Deterministic mock LLM that returns empty JSON."""
    llm = MagicMock()
    llm.generate.return_value = "[]"
    return llm


# ===================================================================
# 1. FactTable → RuleEngine
# ===================================================================

class TestFactTableRuleEngine:
    """Verify that KG facts feed correctly into rule evaluation."""

    def test_f1_rejects_high_resource_method_on_low_resource_domain(
        self, rule_engine,
    ):
        """F1: high-resource method + low-resource domain → REJECT."""
        claim = {
            "type": "gap_indicator",
            "description": "Apply deep learning to edge computing",
            "method": "deep_learning",
            "domain": "edge_computing",
            "confidence": 0.8,
        }
        report: ValidationReport = rule_engine.validate(claim)

        assert report.overall_verdict == "REJECT"
        f1_results = [r for r in report.results if r.rule.rule_id == "F1"]
        assert len(f1_results) == 1
        assert f1_results[0].verdict == "REJECT"
        assert f1_results[0].reason  # explanation is non-empty

    def test_f1_passes_when_no_resource_conflict(self, rule_engine):
        """F1: low-resource method on any domain → PASS."""
        claim = {
            "method": "random_forest",
            "domain": "edge_computing",
            "confidence": 0.7,
        }
        report = rule_engine.validate(claim)
        f1 = [r for r in report.results if r.rule.rule_id == "F1"][0]
        assert f1.passed is True

    def test_k1_flags_contradictory_findings(self, rule_engine):
        """K1: two contradicting findings in the same claim → FLAG."""
        claim = {
            "type": "gap_indicator",
            "description": "Both findings cited together",
            "findings": ["finding_A", "finding_C"],
            "confidence": 0.75,
        }
        report = rule_engine.validate(claim)

        k1 = [r for r in report.results if r.rule.rule_id == "K1"][0]
        assert k1.verdict == "FLAG"
        assert "contradict" in k1.reason.lower()

    def test_rejected_items_have_explanations(self, rule_engine):
        """Every REJECT result must include a non-empty reason string."""
        claim = {
            "method": "deep_learning",
            "domain": "edge_computing",
            "confidence": 0.8,
        }
        report = rule_engine.validate(claim)

        for r in report.results:
            if r.verdict == "REJECT":
                assert r.reason, f"Rule {r.rule.rule_id} REJECT has empty reason"

    def test_confidence_adjusted_after_validation(self, rule_engine):
        """Adjusted confidence must differ from original when rules fire."""
        claim = {
            "method": "deep_learning",
            "domain": "edge_computing",
            "confidence": 0.9,
        }
        report = rule_engine.validate(claim)
        assert report.adjusted_confidence != report.original_confidence

    def test_validate_returns_all_nine_rules(self, rule_engine):
        """Report must contain results for all 9 rules."""
        report = rule_engine.validate({"confidence": 0.5})
        assert report.rules_checked == 9

    def test_report_to_dict_serialisable(self, rule_engine):
        """ValidationReport.to_dict() must be JSON-serialisable."""
        import json

        report = rule_engine.validate({
            "method": "deep_learning",
            "domain": "edge_computing",
            "confidence": 0.8,
        })
        d = report.to_dict()
        json.dumps(d)  # raises if not serialisable


# ===================================================================
# 2. FactTable → RelationClassifier
# ===================================================================

class TestFactTableRelationClassifier:
    """Verify that KG facts influence relation classification (Layer 3)."""

    def test_causal_validated_with_kg_facts(self, relation_classifier):
        """Causal relation backed by KG facts → rule_validated=True."""
        text = "Deep learning leads to better accuracy on medical images."
        kg_facts = [
            {"subject_id": "Deep learning", "object_id": "medical images"},
        ]
        result = relation_classifier.classify(
            entity_a="Deep learning",
            entity_b="medical images",
            text_context=text,
            semantic_similarity=0.8,
            kg_facts=kg_facts,
        )
        assert result.relation_type == RelationType.CAUSAL
        assert result.rule_validated is True

    def test_causal_without_kg_support_not_validated(self, relation_classifier):
        """Causal relation with NO KG support → rule_validated=False."""
        text = "Quantum computing leads to breakthroughs in protein folding."
        result = relation_classifier.classify(
            entity_a="Quantum computing",
            entity_b="protein folding",
            text_context=text,
            semantic_similarity=0.7,
            kg_facts=[],
        )
        assert result.relation_type == RelationType.CAUSAL
        assert result.rule_validated is False
        assert "NOT supported" in result.explanation

    def test_co_occurrence_not_upgraded_to_causal(self, relation_classifier):
        """Pure co-occurrence must remain CO_OCCURRENCE, not causal."""
        text = "The study discusses deep learning and also mentions edge computing."
        result = relation_classifier.classify(
            entity_a="deep learning",
            entity_b="edge computing",
            text_context=text,
            semantic_similarity=0.6,
            kg_facts=[
                {"subject_id": "deep learning", "object_id": "edge computing"},
            ],
        )
        assert result.relation_type == RelationType.CO_OCCURRENCE

    def test_low_similarity_discarded(self, relation_classifier):
        """Below similarity threshold → UNKNOWN, not promoted."""
        result = relation_classifier.classify(
            entity_a="A", entity_b="B",
            text_context="Nothing relevant",
            semantic_similarity=0.1,
        )
        assert result.relation_type == RelationType.UNKNOWN

    def test_contradiction_detected_via_markers(self, relation_classifier):
        """Contradiction markers → CONTRADICTION relation type."""
        text = (
            "Study A reports high accuracy. However, Study B contradicts "
            "this claim, showing lower accuracy on the same dataset."
        )
        result = relation_classifier.classify(
            entity_a="Study A",
            entity_b="Study B",
            text_context=text,
            semantic_similarity=0.7,
        )
        assert result.relation_type == RelationType.CONTRADICTION

    def test_batch_classify(self, relation_classifier):
        """classify_batch processes multiple pairs."""
        pairs = [
            {"entity_a": "A", "entity_b": "B", "similarity": 0.8},
            {"entity_a": "C", "entity_b": "D", "similarity": 0.1},
        ]
        text = "A leads to B. C and D are unrelated."
        results = relation_classifier.classify_batch(pairs, text)
        assert len(results) == 2
        assert results[1].relation_type == RelationType.UNKNOWN


# ===================================================================
# 3. GapAnalyzer → RuleEngine
# ===================================================================

class TestGapAnalyzerRuleEngine:
    """Verify GapAnalyzer delegates to RuleEngine and honours verdicts."""

    def _make_analyzer(self, fact_table, rule_engine, llm=None):
        return GapAnalyzer(
            llm_interface=llm,
            fact_table=fact_table,
            rule_engine=rule_engine,
        )

    def test_indicators_have_rule_engine_verdict(
        self, populated_fact_table, rule_engine,
    ):
        """Each returned indicator should carry a rule_engine_verdict."""
        analyzer = self._make_analyzer(populated_fact_table, rule_engine)
        papers = [
            {"doc_id": "p1", "content": "Deep learning for medical imaging achieves high accuracy.",
             "metadata": {"title": "Paper 1", "keywords": ["deep learning"]}},
            {"doc_id": "p2", "content": "Random forest for edge computing shows decent results.",
             "metadata": {"title": "Paper 2", "keywords": ["random forest"]}},
            {"doc_id": "p3", "content": "Survey of methods in education domain.",
             "metadata": {"title": "Paper 3", "keywords": ["survey"]}},
        ]
        indicators = analyzer.analyze_gaps("AI methods", papers)

        for ind in indicators:
            assert ind.rule_engine_verdict is not None, (
                f"Indicator missing verdict: {ind.description[:60]}"
            )
            assert ind.rule_engine_verdict in (
                RuleVerdictType.PASS, RuleVerdictType.FLAG, RuleVerdictType.REJECT,
            )

    def test_rejected_gaps_filtered_from_output(
        self, populated_fact_table,
    ):
        """REJECTED indicators must NOT appear in the returned list."""
        # Build a rule engine that always rejects
        always_reject_engine = MagicMock()
        reject_report = MagicMock()
        reject_report.overall_verdict = "REJECT"
        reject_report.adjusted_confidence = 0.0
        always_reject_engine.validate.return_value = reject_report

        analyzer = self._make_analyzer(
            populated_fact_table, always_reject_engine,
        )
        papers = [
            {"doc_id": "p1", "content": "Study about deep learning.",
             "metadata": {"title": "P1", "keywords": ["deep learning"]}},
            {"doc_id": "p2", "content": "Study about random forests.",
             "metadata": {"title": "P2", "keywords": ["random forest"]}},
            {"doc_id": "p3", "content": "Study about statistics.",
             "metadata": {"title": "P3", "keywords": ["statistics"]}},
        ]
        indicators = analyzer.analyze_gaps("AI methods", papers)
        assert len(indicators) == 0, "REJECTED indicators should be filtered out"

    def test_confidence_adjusted_by_rule_engine(
        self, populated_fact_table, rule_engine,
    ):
        """adjusted_confidence should be set on surviving indicators."""
        analyzer = self._make_analyzer(populated_fact_table, rule_engine)
        papers = [
            {"doc_id": "p1", "content": "Experiment on deep learning.",
             "metadata": {"title": "P1", "keywords": ["deep learning"]}},
            {"doc_id": "p2", "content": "Experiment on SVM.",
             "metadata": {"title": "P2", "keywords": ["SVM"]}},
            {"doc_id": "p3", "content": "Survey on transformers.",
             "metadata": {"title": "P3", "keywords": ["transformers"]}},
        ]
        indicators = analyzer.analyze_gaps("AI methods", papers)

        for ind in indicators:
            assert ind.adjusted_confidence is not None

    def test_gap_indicator_to_model_conversion(
        self, populated_fact_table, rule_engine,
    ):
        """GapIndicator.to_model() must produce a valid GapIndicatorModel."""
        analyzer = self._make_analyzer(populated_fact_table, rule_engine)
        papers = [
            {"doc_id": "p1", "content": "Paper about NLP.", "metadata": {"title": "P1", "keywords": ["NLP"]}},
            {"doc_id": "p2", "content": "Paper about CV.", "metadata": {"title": "P2", "keywords": ["CV"]}},
        ]
        indicators = analyzer.analyze_gaps("AI", papers)

        for ind in indicators:
            model = ind.to_model()
            assert isinstance(model, GapIndicatorModel)
            assert model.indicator_type in IndicatorType


# ===================================================================
# 4. Full pipeline (mock) — coordinator-style end-to-end
# ===================================================================

class TestFullPipelineMock:
    """Simulate the entire coordinator flow with mocked LLM."""

    @pytest.fixture
    def pipeline_components(self):
        """Build all pipeline components with mock LLM."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "[]"

        ft = FactTable()
        # Populate with representative data
        ft.add_entity(Entity("cnn", EntityType.METHOD, "CNN",
                             properties={"resource_requirement": "high"}))
        ft.add_entity(Entity("bert", EntityType.METHOD, "BERT",
                             properties={"resource_requirement": "high"}))
        ft.add_entity(Entity("nlp", EntityType.DOMAIN, "NLP"))
        ft.add_entity(Entity("edge_dev", EntityType.DOMAIN, "Edge Device",
                             properties={"constraint": "low_resource"}))
        ft.add_entity(Entity("acc_95", EntityType.FINDING,
                             "achieves 95% accuracy"))
        ft.add_entity(Entity("acc_70", EntityType.FINDING,
                             "only achieves 70% on edge"))
        ft.add_entity(Entity("gpu_req", EntityType.CONSTRAINT, "GPU >= 16 GB"))

        ft.add_fact(Fact(fact_id="pf1", subject_id="cnn",
                         predicate=PredicateType.REQUIRES_RESOURCE,
                         object_id="high_gpu", source_paper="paper_a",
                         confidence=0.95))
        ft.add_fact(Fact(fact_id="pf2", subject_id="cnn",
                         predicate=PredicateType.ACHIEVES,
                         object_id="acc_95", source_paper="paper_a",
                         confidence=0.9))
        ft.add_fact(Fact(fact_id="pf3", subject_id="cnn",
                         predicate=PredicateType.APPLIES_TO,
                         object_id="nlp", source_paper="paper_a",
                         confidence=0.85))
        ft.add_fact(Fact(fact_id="pf4", subject_id="edge_dev",
                         predicate=PredicateType.HAS_CONSTRAINT,
                         object_id="limited_compute",
                         source_paper="paper_b", confidence=0.9))
        ft.add_fact(Fact(fact_id="pf5", subject_id="acc_95",
                         predicate=PredicateType.CONTRADICTS,
                         object_id="acc_70",
                         source_paper="paper_c", confidence=0.8))
        # acc_70 must also be a subject of some fact so find_contradictions
        # can locate a pair (it queries subject_id for both sides).
        ft.add_fact(Fact(fact_id="pf6", subject_id="acc_70",
                         predicate=PredicateType.ACHIEVES,
                         object_id="edge_dev",
                         source_paper="paper_c", confidence=0.7))

        re = RuleEngine(fact_table=ft)
        fe = FactExtractor(llm_interface=mock_llm)
        rc = RelationClassifier(llm_interface=None)
        ga = GapAnalyzer(
            llm_interface=mock_llm,
            fact_table=ft,
            rule_engine=re,
        )

        return {
            "fact_table": ft,
            "rule_engine": re,
            "fact_extractor": fe,
            "relation_classifier": rc,
            "gap_analyzer": ga,
            "llm": mock_llm,
        }

    def test_extract_then_validate_flow(self, pipeline_components):
        """FactExtractor → FactTable → RuleEngine validate."""
        ft = pipeline_components["fact_table"]
        re = pipeline_components["rule_engine"]

        # Validate a claim that references entities already in FactTable
        claim = {
            "type": "recommendation",
            "description": "Use CNN for edge device deployment",
            "method": "cnn",
            "domain": "edge_dev",
            "confidence": 0.85,
        }
        report = re.validate(claim)

        assert report.overall_verdict == "REJECT"
        assert report.adjusted_confidence < report.original_confidence

    def test_gap_analysis_with_rule_validation(self, pipeline_components):
        """GapAnalyzer detects gaps → RuleEngine validates → proper output."""
        ga = pipeline_components["gap_analyzer"]

        papers = [
            {"doc_id": "pa", "content": "CNN for NLP achieves 95% accuracy using deep learning techniques.",
             "metadata": {"title": "CNN NLP", "keywords": ["CNN", "NLP", "deep learning"]}},
            {"doc_id": "pb", "content": "Edge computing with random forest shows promise for IoT.",
             "metadata": {"title": "Edge RF", "keywords": ["edge", "random forest", "IoT"]}},
            {"doc_id": "pc", "content": "Survey of transfer learning in computer vision with experiment methodology.",
             "metadata": {"title": "TL Survey", "keywords": ["transfer learning", "survey"]}},
        ]
        indicators = ga.analyze_gaps("AI deployment", papers)

        # All surviving indicators should have verdicts
        for ind in indicators:
            assert ind.rule_engine_verdict is not None
            assert ind.rule_engine_verdict != RuleVerdictType.REJECT

    def test_relation_classification_uses_kg_facts(self, pipeline_components):
        """Relation classifier honours KG facts for Layer 3 validation."""
        rc = pipeline_components["relation_classifier"]
        ft = pipeline_components["fact_table"]

        # Build kg_facts list from FactTable
        kg_facts = [f.to_dict() for f in ft.query(subject_id="cnn")]

        text = "CNN leads to improved accuracy in NLP tasks."
        result = rc.classify(
            entity_a="cnn", entity_b="nlp",
            text_context=text,
            semantic_similarity=0.85,
            kg_facts=kg_facts,
        )
        assert result.relation_type == RelationType.CAUSAL
        assert result.rule_validated is True

    def test_full_output_structure(self, pipeline_components):
        """Final output assembles into a valid AnalysisResponseModel."""
        ga = pipeline_components["gap_analyzer"]
        re = pipeline_components["rule_engine"]
        ft = pipeline_components["fact_table"]

        papers = [
            {"doc_id": "pa", "content": "Deep learning for NLP.",
             "metadata": {"title": "DL NLP", "keywords": ["deep learning"]}},
            {"doc_id": "pb", "content": "Edge computing constraints.",
             "metadata": {"title": "Edge", "keywords": ["edge"]}},
        ]
        indicators = ga.analyze_gaps("AI", papers)

        # Build the response model (mirroring coordinator output)
        indicator_models = [ind.to_model() for ind in indicators]

        # Build rule engine report model
        sample_claim = {"confidence": 0.7}
        val_report = re.validate(sample_claim)
        rule_models = [
            RuleResultModel(
                rule_id=r.rule.rule_id,
                rule_name=r.rule.name,
                category=r.rule.category.value,
                verdict=RuleVerdictType(r.verdict),
                confidence=max(0.0, min(1.0, 0.7 + r.confidence_adjustment)),
                explanation=r.reason,
            )
            for r in val_report.results
        ]
        report_model = RuleEngineReportModel(
            overall_verdict=RuleVerdictType(val_report.overall_verdict),
            adjusted_confidence=val_report.adjusted_confidence,
            total_rules=val_report.rules_checked,
            passed=val_report.rules_passed,
            flagged=val_report.rules_flagged,
            rejected=val_report.rules_rejected,
            rules=rule_models,
            summary=val_report.summary,
        )

        reasoning = [
            ReasoningStep(phase="observe", actions=["Retrieved 2 papers"]),
            ReasoningStep(phase="think", actions=[f"Detected {len(indicators)} gap indicators"]),
            ReasoningStep(phase="act", actions=["Rule Engine validated indicators"]),
            ReasoningStep(phase="evaluate", actions=["Self-critique complete"]),
        ]

        response = AnalysisResponseModel(
            query="AI deployment",
            execution_mode="sequential",
            gap_indicators=indicator_models,
            total_indicators=len(indicator_models),
            rule_engine_report=report_model,
            reasoning_trace=reasoning,
            metadata={
                "papers_processed": 2,
                "fact_table": ft.get_statistics(),
            },
        )

        # Structural assertions
        assert response.query == "AI deployment"
        assert response.total_indicators == len(indicator_models)
        assert response.rule_engine_report is not None
        assert len(response.reasoning_trace) == 4
        assert response.reasoning_trace[0].phase == "observe"

        # Verify serialisation round-trip
        d = response.model_dump()
        assert isinstance(d["gap_indicators"], list)
        assert isinstance(d["rule_engine_report"], dict)

    def test_contradictory_findings_detected_in_pipeline(
        self, pipeline_components,
    ):
        """Pipeline correctly surfaces contradictions from FactTable."""
        ft = pipeline_components["fact_table"]

        contradictions = ft.find_contradictions()
        assert len(contradictions) >= 1

        # Validate the contradiction through rule engine
        re = pipeline_components["rule_engine"]
        claim = {
            "findings": ["acc_95", "acc_70"],
            "confidence": 0.8,
        }
        report = re.validate(claim)
        k1 = [r for r in report.results if r.rule.rule_id == "K1"][0]
        assert k1.verdict == "FLAG"

    def test_fact_table_statistics_in_output(self, pipeline_components):
        """FactTable statistics are non-zero and well-formed."""
        ft = pipeline_components["fact_table"]
        stats = ft.get_statistics()

        assert stats["total_entities"] > 0
        assert stats["total_facts"] > 0
        assert "entities_by_type" in stats
        assert "facts_by_predicate" in stats
