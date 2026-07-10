"""Per-job analysis state and retrieval scoping.

Only immutable or intentionally shared resources (the vector store, embedding
model, reranker, NLI model, and stateless Ollama client) are reused.  Facts,
knowledge graph state, validation, agents, and coordinator state are created
for each analysis job, preventing one user's job from affecting another.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any

from ..agents.coordinator import CoordinatorAgent
from ..agents.gap_detector import GapDetectorAgent
from ..agents.recommender import RecommenderAgent
from ..agents.research_analyzer import ResearchAnalyzerAgent
from ..agents.tools.kg_querier_tool import KGQuerierTool
from ..agents.tools.nli_checker_tool import NLICheckerTool
from ..agents.tools.paper_analyzer_tool import PaperAnalyzerTool
from ..agents.tools.rag_tool import RAGTool
from ..agents.tools.self_critic_tool import SelfCriticTool
from ..gap_detection.analyzer import GapAnalyzer
from ..knowledge.fact_extractor import FactExtractor
from ..knowledge.fact_table import FactTable
from ..knowledge_graph.graph_builder import KnowledgeGraphBuilder
from ..retrieval.rag_retriever import RAGRetriever
from ..validation.relation_classifier import RelationClassifier
from ..validation.rule_engine import RuleEngine


class ScopedRAGRetriever(RAGRetriever):
    """RAG retriever that can only return chunks from one analysis job."""

    def __init__(self, *args: Any, analysis_job_id: str | None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.analysis_job_id = analysis_job_id

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_metadata: dict[str, Any] | None = None,
        rerank: bool = True,
    ):
        scope = {"analysis_job_id": self.analysis_job_id} if self.analysis_job_id else filter_metadata
        if self.analysis_job_id and filter_metadata:
            scope = {"$and": [scope, filter_metadata]}
        return super().retrieve(
            query=query,
            top_k=top_k,
            filter_metadata=scope,
            rerank=rerank,
        )


@dataclass
class AnalysisContext:
    """Mutable state belonging to exactly one durable analysis job."""

    job_id: str
    vector_store: Any
    llm: Any
    retriever: ScopedRAGRetriever
    fact_table: FactTable
    knowledge_graph: KnowledgeGraphBuilder
    fact_extractor: FactExtractor
    relation_classifier: RelationClassifier
    rule_engine: RuleEngine
    gap_analyzer: GapAnalyzer
    coordinator: CoordinatorAgent

    def graph_snapshot(self) -> dict[str, Any]:
        """Return a serialization that the graph endpoint can render safely."""
        self.knowledge_graph.build_from_fact_table(self.fact_table)
        facts = []
        for fact in self.fact_table.query():
            subject = self.fact_table.get_entity(fact.subject_id)
            obj = self.fact_table.get_entity(fact.object_id)
            facts.append(
                {
                    "subject": subject.name if subject else fact.subject_id,
                    "subject_type": subject.entity_type.value if subject and subject.entity_type else "CONCEPT",
                    "predicate": fact.predicate.value if hasattr(fact.predicate, "value") else str(fact.predicate),
                    "object": obj.name if obj else fact.object_id,
                    "object_type": obj.entity_type.value if obj and obj.entity_type else "CONCEPT",
                    "confidence": float(fact.confidence),
                    "source_paper": fact.source_paper,
                }
            )
        return {
            "job_id": self.job_id,
            "facts": facts,
            "raw_graph": self.knowledge_graph.export_to_dict(),
            "fact_table_stats": self.fact_table.get_statistics(),
        }


class AnalysisContextManager:
    """Thread-safe lifecycle manager for active job contexts."""

    def __init__(self):
        self._contexts: dict[str, AnalysisContext] = {}
        self._lock = RLock()

    def get_or_create(self, job_id: str) -> AnalysisContext:
        with self._lock:
            context = self._contexts.get(job_id)
            if context is None:
                context = create_analysis_context(job_id)
                self._contexts[job_id] = context
            return context

    def get(self, job_id: str) -> AnalysisContext | None:
        with self._lock:
            return self._contexts.get(job_id)

    def release(self, job_id: str) -> None:
        """Drop transient state after its durable result/snapshot was persisted."""
        with self._lock:
            self._contexts.pop(job_id, None)

    def active_job_ids(self) -> list[str]:
        with self._lock:
            return list(self._contexts)


def create_analysis_context(job_id: str, *, scope_retrieval: bool = True) -> AnalysisContext:
    """Construct a fresh agent graph, fact table, and KG for ``job_id``.

    Ephemeral API requests can opt out of job filtering while still avoiding
    mutable FactTable/KG/Coordinator state shared with other requests.
    """
    # Delay dependency imports so the core module does not create an import
    # cycle while FastAPI builds its router graph.
    from ...api.dependencies import (
        get_glm_interface,
        get_nli_model,
        get_reranker,
        get_vector_store,
    )
    from ...utils.config_loader import get_config

    config = get_config()
    vector_store = get_vector_store()
    llm = get_glm_interface()
    retriever = ScopedRAGRetriever(
        vector_store=vector_store,
        top_k=config.retrieval.top_k,
        min_relevance_score=config.retrieval.min_relevance_score,
        reranker=get_reranker(),
        analysis_job_id=job_id if scope_retrieval else None,
    )
    fact_table = FactTable()
    knowledge_graph = KnowledgeGraphBuilder()
    fact_extractor = FactExtractor(llm_interface=llm)
    relation_classifier = RelationClassifier(
        llm_interface=llm,
        nli_model=get_nli_model(),
    )
    rule_engine = RuleEngine(fact_table=fact_table)
    gap_analyzer = GapAnalyzer(
        vector_store=vector_store,
        knowledge_graph=knowledge_graph,
        llm_interface=llm,
        fact_table=fact_table,
        relation_classifier=relation_classifier,
        rule_engine=rule_engine,
    )

    research_analyzer = ResearchAnalyzerAgent(llm_interface=llm, retriever=retriever)
    gap_detector = GapDetectorAgent(
        llm_interface=llm,
        retriever=retriever,
        knowledge_graph=knowledge_graph,
        fact_table=fact_table,
        fact_extractor=fact_extractor,
        gap_analyzer=gap_analyzer,
        relation_classifier=relation_classifier,
        rule_engine=rule_engine,
    )
    recommender = RecommenderAgent(
        llm_interface=llm,
        retriever=retriever,
        knowledge_graph=knowledge_graph,
    )
    coordinator = CoordinatorAgent(
        research_analyzer=research_analyzer,
        gap_detector=gap_detector,
        recommender=recommender,
        rag_tool=RAGTool(retriever=retriever),
        paper_analyzer_tool=PaperAnalyzerTool(
            llm_interface=llm,
            fact_extractor=fact_extractor,
            fact_table=fact_table,
        ),
        nli_checker_tool=NLICheckerTool(
            relation_classifier=relation_classifier,
            llm_interface=llm,
        ),
        kg_querier_tool=KGQuerierTool(
            graph_builder=knowledge_graph,
            fact_table=fact_table,
        ),
        self_critic_tool=SelfCriticTool(
            rule_engine=rule_engine,
            llm_interface=llm,
            fact_table=fact_table,
        ),
        fact_extractor=fact_extractor,
        fact_table=fact_table,
        rule_engine=rule_engine,
        relation_classifier=relation_classifier,
        graph_builder=knowledge_graph,
        llm_interface=llm,
    )
    return AnalysisContext(
        job_id=job_id,
        vector_store=vector_store,
        llm=llm,
        retriever=retriever,
        fact_table=fact_table,
        knowledge_graph=knowledge_graph,
        fact_extractor=fact_extractor,
        relation_classifier=relation_classifier,
        rule_engine=rule_engine,
        gap_analyzer=gap_analyzer,
        coordinator=coordinator,
    )


analysis_contexts = AnalysisContextManager()
