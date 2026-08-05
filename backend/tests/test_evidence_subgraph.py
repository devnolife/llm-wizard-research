"""Tests for KG evidence-subgraph extraction on gap indicators (Fase 3)."""

from app.core.gap_detection.analyzer import GapAnalyzer, GapIndicator, GapIndicatorType
from app.core.knowledge.fact_table import (
    Entity,
    EntityType,
    Fact,
    FactTable,
    PredicateType,
)
from app.core.knowledge_graph.graph_builder import KnowledgeGraphBuilder


def _build_kg():
    """FactTable + KG: finding A (paper1) CONTRADICTS finding B (paper2)."""
    ft = FactTable()
    ft.add_entity(Entity(
        entity_id="finding_a", name="Dropout improves generalization strongly",
        entity_type=EntityType.FINDING, source_paper="paper1.pdf",
    ))
    ft.add_entity(Entity(
        entity_id="finding_b", name="Dropout degrades generalization notably",
        entity_type=EntityType.FINDING, source_paper="paper2.pdf",
    ))
    ft.add_entity(Entity(
        entity_id="method_x", name="Regularization method X",
        entity_type=EntityType.METHOD, source_paper="paper1.pdf",
    ))
    ft.add_fact(Fact(
        fact_id="f1", subject_id="finding_a", predicate=PredicateType.CONTRADICTS,
        object_id="finding_b", confidence=0.9, source="Sec 3", source_paper="paper1.pdf",
    ))
    ft.add_fact(Fact(
        fact_id="f2", subject_id="method_x", predicate=PredicateType.IMPROVES,
        object_id="finding_a", confidence=0.8, source="Sec 4", source_paper="paper1.pdf",
    ))
    kg = KnowledgeGraphBuilder()
    kg.build_from_fact_table(ft)
    return ft, kg


class TestExtractEvidenceSubgraph:
    def test_direct_contradicts_edge_found(self):
        ft, kg = _build_kg()
        analyzer = GapAnalyzer(knowledge_graph=kg, fact_table=ft)
        edges = analyzer._extract_evidence_subgraph("finding_a", "finding_b")
        assert edges, "expected at least the CONTRADICTS edge"
        e = edges[0]
        assert e["predicate"] == "CONTRADICTS"
        assert e["from_name"] == "Dropout improves generalization strongly"
        assert e["to_name"] == "Dropout degrades generalization notably"
        assert e["source_paper"] == "paper1.pdf"
        assert e["confidence"] == 0.9

    def test_reverse_direction_searched(self):
        ft, kg = _build_kg()
        analyzer = GapAnalyzer(knowledge_graph=kg, fact_table=ft)
        # b → a has no directed path, but a → b does; reversed args must still work
        edges = analyzer._extract_evidence_subgraph("finding_b", "finding_a")
        assert edges and edges[0]["predicate"] == "CONTRADICTS"

    def test_no_kg_returns_empty(self):
        analyzer = GapAnalyzer(knowledge_graph=None)
        assert analyzer._extract_evidence_subgraph("a", "b") == []

    def test_unknown_entities_empty(self):
        ft, kg = _build_kg()
        analyzer = GapAnalyzer(knowledge_graph=kg, fact_table=ft)
        assert analyzer._extract_evidence_subgraph("nope1", "nope2") == []


class TestInconsistencyCarriesSubgraph:
    def test_detect_inconsistency_attaches_subgraph(self):
        ft, kg = _build_kg()
        analyzer = GapAnalyzer(knowledge_graph=kg, fact_table=ft)
        papers = [
            {"content": "Dropout improves generalization strongly in our tests here.",
             "metadata": {"source": "paper1.pdf"}},
            {"content": "Dropout degrades generalization notably across benchmarks.",
             "metadata": {"source": "paper2.pdf"}},
        ]
        indicators = analyzer._detect_inconsistency("regularization", papers)
        contradicts = [i for i in indicators if i.detection_method == "fact_table_contradicts"]
        assert contradicts, "expected a fact-table contradiction indicator"
        ind = contradicts[0]
        assert ind.evidence_subgraph, "indicator must carry KG evidence subgraph"
        assert ind.evidence_subgraph[0]["predicate"] == "CONTRADICTS"
        # And the model serialization keeps it
        assert ind.to_model().evidence_subgraph[0]["predicate"] == "CONTRADICTS"
        assert ind.to_dict()["evidence_subgraph"][0]["from_name"].startswith("Dropout")
