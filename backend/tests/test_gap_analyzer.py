"""
Unit tests — GapAnalyzer (3-indicator Cooper/Booth model).

Covers each indicator's detection logic plus Rule Engine integration:
    1. FRAGMENTATION   — topic clustering on divergent keyword sets
    2. INCONSISTENCY   — FactTable CONTRADICTS facts + LLM NLI detection
    3. INCOMPLETENESS  — uncovered aspects + methodology homogeneity
    4. Rule Engine     — REJECT filtering, verdict & confidence propagation
    5. Epistemological boundary — every indicator requires human validation

All tests run offline — no Ollama, no ChromaDB.
"""

import pytest
from unittest.mock import MagicMock

from app.core.gap_detection.analyzer import GapAnalyzer, GapIndicator
from app.core.knowledge.fact_table import (
    Entity,
    EntityType,
    Fact,
    FactTable,
    PredicateType,
)
from app.models.responses import IndicatorType, RuleVerdictType


# ===================================================================
# Fixtures
# ===================================================================

def make_paper(doc_id, content, keywords=None, title=None):
    return {
        "doc_id": doc_id,
        "content": content,
        "metadata": {
            "title": title or doc_id,
            "keywords": keywords or [],
        },
    }


@pytest.fixture
def divergent_papers():
    """Three papers with no keyword overlap → distinct clusters."""
    return [
        make_paper("p1", "We run a randomized experiment with statistical tests.",
                   keywords=["experiment", "statistics"]),
        make_paper("p2", "A qualitative case study based on interviews.",
                   keywords=["case study", "interviews"]),
        make_paper("p3", "Deep learning simulation of network traffic.",
                   keywords=["deep learning", "simulation"]),
    ]


@pytest.fixture
def homogeneous_papers():
    """Three papers all using the same single methodology."""
    return [
        make_paper("h1", "We use deep learning for detection.", keywords=["deep learning"]),
        make_paper("h2", "Our deep learning approach improves accuracy.", keywords=["deep learning"]),
        make_paper("h3", "A deep learning pipeline for segmentation.", keywords=["deep learning"]),
    ]


@pytest.fixture
def contradicting_fact_table():
    ft = FactTable()
    fa = Entity("find_a", EntityType.FINDING, "Dropout improves accuracy")
    fb = Entity("find_b", EntityType.FINDING, "Dropout reduces accuracy")
    ft.add_entity(fa)
    ft.add_entity(fb)
    ft.add_fact(Fact(
        fact_id="c1", subject_id="find_a",
        predicate=PredicateType.CONTRADICTS, object_id="find_b",
        source="Section 4", source_paper="paper_x", confidence=0.8,
    ))
    return ft


# ===================================================================
# Indicator 1: FRAGMENTATION
# ===================================================================

class TestFragmentation:
    def test_detected_with_distinct_clusters(self, divergent_papers):
        ga = GapAnalyzer()  # no LLM, no KG — pure clustering
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")

        frag = [i for i in indicators if i.indicator_type == IndicatorType.FRAGMENTATION]
        assert len(frag) >= 1
        assert frag[0].detection_method == "topic_clustering"
        assert 0.5 < frag[0].confidence <= 0.85
        assert frag[0].sub_indicators  # cluster traceability

    def test_not_detected_with_single_paper(self):
        ga = GapAnalyzer()
        indicators = ga.analyze_gaps(
            "test topic", [make_paper("only", "content", ["kw"])], depth="quick"
        )
        frag = [i for i in indicators if i.indicator_type == IndicatorType.FRAGMENTATION]
        assert frag == []


# ===================================================================
# Indicator 2: INCONSISTENCY
# ===================================================================

class TestInconsistency:
    def test_detected_from_fact_table(self, contradicting_fact_table, divergent_papers):
        ga = GapAnalyzer(fact_table=contradicting_fact_table)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")

        inc = [i for i in indicators if i.indicator_type == IndicatorType.INCONSISTENCY]
        assert len(inc) >= 1
        ft_based = [i for i in inc if i.detection_method == "fact_table_contradicts"]
        assert len(ft_based) == 1
        assert "Dropout improves accuracy" in ft_based[0].description
        assert ft_based[0].confidence == pytest.approx(0.8)

    def test_llm_detected_contradiction(self, divergent_papers):
        llm = MagicMock()
        llm.generate.return_value = (
            "Paper A claims dropout helps; Paper B claims it hurts. "
            "These findings are contradictory and unresolved."
        )
        ga = GapAnalyzer(llm_interface=llm)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")

        llm_inc = [i for i in indicators if i.detection_method == "llm_nli"]
        assert len(llm_inc) == 1
        # LLM-detected contradictions get LOW confidence (epistemological caution)
        assert llm_inc[0].confidence == pytest.approx(0.5)

    def test_llm_no_contradiction_found(self, divergent_papers):
        llm = MagicMock()
        llm.generate.return_value = "No contradictions detected."
        ga = GapAnalyzer(llm_interface=llm)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")

        assert [i for i in indicators if i.detection_method == "llm_nli"] == []

    def test_skipped_at_quick_depth(self, contradicting_fact_table, divergent_papers):
        ga = GapAnalyzer(fact_table=contradicting_fact_table)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")
        inc = [i for i in indicators if i.indicator_type == IndicatorType.INCONSISTENCY]
        assert inc == []


# ===================================================================
# Indicator 3: INCOMPLETENESS
# ===================================================================

class TestIncompleteness:
    def test_uncovered_aspects_detected(self, homogeneous_papers):
        llm = MagicMock()
        # First call: contradiction check; second: expected aspects.
        # Order: _detect_inconsistency (standard) runs before _detect_incompleteness.
        llm.generate.side_effect = [
            "No contradictions detected.",
            "1. Privacy\n2. Scalability\n3. Cost analysis\n4. Ethical review",
        ]
        ga = GapAnalyzer(llm_interface=llm)
        indicators = ga.analyze_gaps("test topic", homogeneous_papers, depth="standard")

        aspect = [i for i in indicators if i.detection_method == "aspect_coverage"]
        assert len(aspect) == 1
        assert aspect[0].indicator_type == IndicatorType.INCOMPLETENESS
        assert "critical aspect" in aspect[0].description

    def test_methodological_homogeneity_detected(self, homogeneous_papers):
        ga = GapAnalyzer()  # no LLM → only methodology check
        indicators = ga.analyze_gaps("test topic", homogeneous_papers, depth="quick")

        meth = [i for i in indicators if i.detection_method == "methodology_coverage"]
        assert len(meth) == 1
        assert meth[0].confidence == pytest.approx(0.6)
        assert "deep learning" in meth[0].description


# ===================================================================
# Rule Engine integration
# ===================================================================

class TestRuleEngineIntegration:
    def _engine_returning(self, verdict, adjusted=0.4):
        engine = MagicMock()
        report = MagicMock()
        report.overall_verdict = verdict
        report.adjusted_confidence = adjusted
        engine.validate.return_value = report
        return engine

    def test_rejected_indicators_filtered_out(self, divergent_papers):
        ga = GapAnalyzer(rule_engine=self._engine_returning("REJECT", 0.1))
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")
        assert indicators == []

    def test_verdict_and_confidence_propagated(self, divergent_papers):
        ga = GapAnalyzer(rule_engine=self._engine_returning("FLAG", 0.42))
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")

        assert len(indicators) >= 1
        for ind in indicators:
            assert ind.rule_engine_verdict == RuleVerdictType.FLAG
            assert ind.adjusted_confidence == pytest.approx(0.42)
            assert ind.confidence == pytest.approx(0.42)

    def test_no_rule_engine_leaves_verdict_none(self, divergent_papers):
        """Ablation mode (H7): without rule engine, verdict stays None."""
        ga = GapAnalyzer(rule_engine=None)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")
        assert len(indicators) >= 1
        for ind in indicators:
            assert ind.rule_engine_verdict is None


# ===================================================================
# Epistemological boundary (revisi.md §4 / BAB I §1.5)
# ===================================================================

class TestEpistemologicalBoundary:
    def test_all_indicators_require_human_validation(
        self, contradicting_fact_table, divergent_papers
    ):
        llm = MagicMock()
        llm.generate.side_effect = [
            "Papers contradict each other on dropout.",
            "1. Privacy\n2. Cost",
        ]
        ga = GapAnalyzer(llm_interface=llm, fact_table=contradicting_fact_table)
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="standard")

        assert len(indicators) >= 2
        assert all(ind.requires_human_validation for ind in indicators)

    def test_indicators_sorted_by_confidence(self, divergent_papers):
        ga = GapAnalyzer()
        indicators = ga.analyze_gaps("test topic", divergent_papers, depth="quick")
        confidences = [i.confidence for i in indicators]
        assert confidences == sorted(confidences, reverse=True)
