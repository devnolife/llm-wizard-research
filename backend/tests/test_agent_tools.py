"""Unit tests for agent tools: RAGTool, KGQuerierTool, PaperAnalyzerTool, SelfCriticTool."""

from unittest.mock import MagicMock

import pytest

from app.core.agents.tools.rag_tool import RAGTool
from app.core.agents.tools.kg_querier_tool import KGQuerierTool
from app.core.agents.tools.paper_analyzer_tool import PaperAnalyzerTool
from app.core.agents.tools.self_critic_tool import SelfCriticTool


# ---------------------------------------------------------------------------
# RAGTool
# ---------------------------------------------------------------------------

class TestRAGTool:
    def test_no_retriever_returns_error(self):
        result = RAGTool(retriever=None).run("query")
        assert result["error"] == "Retriever not available"
        assert result["results"] == []

    def test_retrieve_maps_passages(self):
        doc = MagicMock()
        doc.content = "x" * 1000
        doc.metadata = {"title": "Paper A", "source": "a.pdf"}
        hit = MagicMock(document=doc, score=0.9)
        retriever = MagicMock()
        retriever.retrieve.return_value = [hit]

        result = RAGTool(retriever=retriever).run("deep learning", top_k=3)

        retriever.retrieve.assert_called_once_with("deep learning", top_k=3)
        assert result["total"] == 1
        passage = result["results"][0]
        assert passage["title"] == "Paper A"
        assert passage["source"] == "a.pdf"
        assert passage["score"] == 0.9
        assert len(passage["content"]) == 500  # truncated

    def test_retriever_exception_is_captured(self):
        retriever = MagicMock()
        retriever.retrieve.side_effect = RuntimeError("boom")
        result = RAGTool(retriever=retriever).run("q")
        assert "boom" in result["error"]
        assert result["results"] == []


# ---------------------------------------------------------------------------
# KGQuerierTool
# ---------------------------------------------------------------------------

class TestKGQuerierTool:
    def test_unknown_action(self):
        result = KGQuerierTool().run("bogus")
        assert "Unknown action" in result["error"]
        assert "query_facts" in result["available_actions"]

    def test_query_facts_via_graph_builder(self):
        gb = MagicMock()
        gb.query_facts.return_value = [
            {"subject": "s", "predicate": "p", "object": "o"}
        ]
        result = KGQuerierTool(graph_builder=gb).run(
            "query_facts", subject="s"
        )
        gb.query_facts.assert_called_once_with(
            subject_id="s", predicate=None, object_id=None
        )
        assert result["total"] == 1
        assert result["facts"][0]["subject"] == "s"

    def test_query_facts_via_fact_table(self):
        fact = MagicMock()
        fact.subject_id = "m1"
        fact.predicate = MagicMock(value="APPLIES_TO")
        fact.object_id = "d1"
        fact.confidence = 0.8
        fact.source = "paper1"
        ft = MagicMock()
        ft.query.return_value = [fact]

        result = KGQuerierTool(fact_table=ft).run("query_facts", subject="m1")

        assert result["total"] == 1
        assert result["facts"][0] == {
            "subject": "m1",
            "predicate": "APPLIES_TO",
            "object": "d1",
            "confidence": 0.8,
            "source": "paper1",
        }

    def test_query_facts_limits_to_50(self):
        gb = MagicMock()
        gb.query_facts.return_value = [{"i": i} for i in range(120)]
        result = KGQuerierTool(graph_builder=gb).run("query_facts")
        assert result["total"] == 120
        assert len(result["facts"]) == 50

    def test_neighborhood_without_graph_builder(self):
        result = KGQuerierTool().run("neighborhood", entity_id="e1")
        assert result["error"] == "Graph builder not available"

    def test_handler_exception_is_captured(self):
        gb = MagicMock()
        gb.query_facts.side_effect = ValueError("bad filter")
        result = KGQuerierTool(graph_builder=gb).run("query_facts")
        assert result["error"] == "bad filter"
        assert result["action"] == "query_facts"


# ---------------------------------------------------------------------------
# PaperAnalyzerTool
# ---------------------------------------------------------------------------

class TestPaperAnalyzerTool:
    PAPER = {
        "doc_id": "p1",
        "content": "Some paper content.",
        "metadata": {"title": "Paper One"},
    }

    def test_run_without_dependencies(self):
        result = PaperAnalyzerTool().run(self.PAPER)
        assert result["paper_id"] == "p1"
        assert result["title"] == "Paper One"
        assert result["facts_extracted"] == 0
        assert result["analysis"] == {}

    def test_run_extracts_facts_and_llm_summary(self):
        extractor = MagicMock()
        extractor.extract_from_text.return_value = {"total_facts": 7}
        llm = MagicMock()
        llm.analyze_research.return_value = "summary"
        ft = MagicMock()

        result = PaperAnalyzerTool(
            llm_interface=llm, fact_extractor=extractor, fact_table=ft
        ).run(self.PAPER)

        extractor.extract_from_text.assert_called_once()
        assert result["facts_extracted"] == 7
        assert result["analysis"] == {"llm_summary": "summary"}

    def test_run_survives_extractor_and_llm_failures(self):
        extractor = MagicMock()
        extractor.extract_from_text.side_effect = RuntimeError("x")
        llm = MagicMock()
        llm.analyze_research.side_effect = RuntimeError("y")

        result = PaperAnalyzerTool(
            llm_interface=llm, fact_extractor=extractor, fact_table=MagicMock()
        ).run(self.PAPER)

        assert result["facts_extracted"] == 0
        assert result["analysis"] == {}

    def test_run_batch(self):
        tool = PaperAnalyzerTool()
        results = tool.run_batch([self.PAPER, {"id": "p2", "content": ""}])
        assert [r["paper_id"] for r in results] == ["p1", "p2"]


# ---------------------------------------------------------------------------
# SelfCriticTool
# ---------------------------------------------------------------------------

@pytest.fixture
def complete_analysis():
    indicator = lambda t: {  # noqa: E731
        "type": t,
        "description": f"desc {t}",
        "confidence": 0.8,
        "evidence": ["paper1"],
    }
    return {
        "indicators": [
            indicator("FRAGMENTATION"),
            indicator("INCONSISTENCY"),
            indicator("INCOMPLETENESS"),
        ],
        "gaps": ["g1"],
        "gap_indicators": ["gi1"],
        "recommendations": ["r1"],
        "fact_stats": {"total": 10},
    }


class TestSelfCriticTool:
    def test_complete_supported_analysis_scores_high(self, complete_analysis):
        evaluation = SelfCriticTool().run(complete_analysis)
        assert evaluation["dimensions"]["completeness"]["score"] == 1.0
        assert evaluation["dimensions"]["evidence_support"]["score"] == 1.0
        assert evaluation["overall_score"] > 0.6
        assert evaluation["requires_revision"] is False

    def test_missing_components_penalized(self):
        evaluation = SelfCriticTool().run({"indicators": []})
        completeness = evaluation["dimensions"]["completeness"]
        assert completeness["score"] < 1.0
        assert "gaps" in completeness["missing_components"]
        assert set(completeness["missing_indicator_types"]) == {
            "FRAGMENTATION", "INCONSISTENCY", "INCOMPLETENESS",
        }

    def test_unsupported_indicators_lower_evidence_score(self, complete_analysis):
        complete_analysis["indicators"].append(
            {"type": "FRAGMENTATION", "description": "weak", "confidence": 0.1}
        )
        evaluation = SelfCriticTool().run(complete_analysis)
        evidence = evaluation["dimensions"]["evidence_support"]
        assert evidence["supported"] == 3
        assert evidence["total_indicators"] == 4
        assert len(evidence["unsupported"]) == 1

    def test_low_score_requires_revision(self):
        evaluation = SelfCriticTool().run({})
        assert evaluation["overall_score"] < 0.6
        assert evaluation["requires_revision"] is True
