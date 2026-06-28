"""
Shared dependencies for API routes

Singleton DI pattern for all components including:
- FactTable, FactExtractor (knowledge layer)
- RuleEngine, RelationClassifier (validation layer)
- Agent tools (RAG, PaperAnalyzer, NLI, KG, SelfCritic)
- CoordinatorAgent (LangGraph orchestrator)
"""

from functools import lru_cache
from loguru import logger
import os

from ..services.llm_service import GLMInterface, ModelConfig
from ..core.retrieval.vector_store import VectorStore
from ..core.retrieval.rag_retriever import RAGRetriever
from ..core.knowledge_graph.graph_builder import KnowledgeGraphBuilder
from ..core.gap_detection.analyzer import GapAnalyzer
from ..core.recommendation.engine import RecommendationEngine
from ..core.agents.coordinator import CoordinatorAgent
from ..core.agents.research_analyzer import ResearchAnalyzerAgent
from ..core.agents.gap_detector import GapDetectorAgent
from ..core.agents.recommender import RecommenderAgent
from ..services.paper_apis import AggregatedPaperAPI
from ..utils.document_processor import DocumentProcessor
from ..utils.config_loader import get_config

# New imports — knowledge & validation layers
from ..core.knowledge.fact_table import FactTable
from ..core.knowledge.fact_extractor import FactExtractor
from ..core.validation.rule_engine import RuleEngine
from ..core.validation.relation_classifier import RelationClassifier

# New imports — agent tools
from ..core.agents.tools.rag_tool import RAGTool
from ..core.agents.tools.paper_analyzer_tool import PaperAnalyzerTool
from ..core.agents.tools.nli_checker_tool import NLICheckerTool
from ..core.agents.tools.kg_querier_tool import KGQuerierTool
from ..core.agents.tools.self_critic_tool import SelfCriticTool

config = get_config()

# Component cache
_components = {}


@lru_cache()
def get_vector_store() -> VectorStore:
    """Get or create vector store instance"""
    if "vector_store" not in _components:
        _components["vector_store"] = VectorStore(
            persist_directory=config.vector_db.persist_directory,
            collection_name=config.vector_db.collection_name,
            embedding_model=config.vector_db.embedding_model
        )
    return _components["vector_store"]


@lru_cache()
def get_glm_interface() -> GLMInterface:
    """Get or create GLM interface instance"""
    if "glm" not in _components:
        glm_config = ModelConfig(
            model_name=config.llm.model_name,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens
        )
        _components["glm"] = GLMInterface(glm_config)
    return _components["glm"]


@lru_cache()
def get_reranker():
    """Get or create the cross-encoder reranker (optional, two-stage retrieval).

    Re-scores candidate passages jointly with the query for higher precision.
    Controlled by config.retrieval.rerank_enabled and degrades gracefully to
    None when the model cannot be loaded (offline / missing weights), in which
    case the retriever falls back to its heuristic reranker.
    """
    if "reranker" not in _components:
        if not getattr(config.retrieval, "rerank_enabled", True):
            logger.info("Cross-encoder reranker disabled via config")
            _components["reranker"] = None
        else:
            try:
                from ..core.retrieval.reranker import CrossEncoderReranker
                model = CrossEncoderReranker(
                    model_name=getattr(
                        config.retrieval, "reranker_model",
                        "cross-encoder/ms-marco-MiniLM-L-6-v2",
                    )
                )
                if model.available:
                    logger.info("Cross-encoder reranker loaded")
                    _components["reranker"] = model
                else:
                    logger.warning("Reranker not available; using heuristic fallback")
                    _components["reranker"] = None
            except Exception as e:
                logger.warning(f"Failed to load reranker: {e}")
                _components["reranker"] = None
    return _components["reranker"]


@lru_cache()
def get_retriever() -> RAGRetriever:
    """Get or create RAG retriever instance"""
    if "retriever" not in _components:
        vector_store = get_vector_store()
        _components["retriever"] = RAGRetriever(
            vector_store=vector_store,
            top_k=config.retrieval.top_k,
            min_relevance_score=config.retrieval.min_relevance_score,
            reranker=get_reranker(),
        )
    return _components["retriever"]


@lru_cache()
def get_knowledge_graph() -> KnowledgeGraphBuilder:
    """Get or create knowledge graph instance"""
    if "knowledge_graph" not in _components:
        _components["knowledge_graph"] = KnowledgeGraphBuilder()
    return _components["knowledge_graph"]


@lru_cache()
def get_gap_analyzer() -> GapAnalyzer:
    """Get or create gap analyzer instance (with new components)"""
    if "gap_analyzer" not in _components:
        _components["gap_analyzer"] = GapAnalyzer(
            vector_store=get_vector_store(),
            knowledge_graph=get_knowledge_graph(),
            llm_interface=get_glm_interface(),
            fact_table=get_fact_table(),
            relation_classifier=get_relation_classifier(),
            rule_engine=get_rule_engine(),
        )
    return _components["gap_analyzer"]


@lru_cache()
def get_fact_table() -> FactTable:
    """Get or create FactTable instance"""
    if "fact_table" not in _components:
        _components["fact_table"] = FactTable()
    return _components["fact_table"]


@lru_cache()
def get_fact_extractor() -> FactExtractor:
    """Get or create FactExtractor instance"""
    if "fact_extractor" not in _components:
        _components["fact_extractor"] = FactExtractor(
            llm_interface=get_glm_interface()
        )
    return _components["fact_extractor"]


@lru_cache()
def get_rule_engine() -> RuleEngine:
    """Get or create Rule Engine instance"""
    if "rule_engine" not in _components:
        _components["rule_engine"] = RuleEngine(
            fact_table=get_fact_table()
        )
    return _components["rule_engine"]


@lru_cache()
def get_nli_model():
    """Get or create the dedicated cross-encoder NLI model (optional).

    Provides a contradiction signal that is *decoupled* from the generative
    LLM (per the thesis's neuro-symbolic claim). Controlled by the
    ENABLE_NLI_MODEL env var (default: enabled) and degrades gracefully to
    None when the model weights cannot be loaded (e.g. offline).
    """
    if "nli_model" not in _components:
        enabled = os.getenv("ENABLE_NLI_MODEL", "true").lower() in ("1", "true", "yes")
        if not enabled:
            logger.info("NLI model disabled via ENABLE_NLI_MODEL")
            _components["nli_model"] = None
        else:
            try:
                from ..core.validation.nli_model import NLIModel
                model = NLIModel()
                if model.available:
                    logger.info("Dedicated cross-encoder NLI model loaded")
                    _components["nli_model"] = model
                else:
                    logger.warning("NLI model not available; falling back to LLM/markers")
                    _components["nli_model"] = None
            except Exception as e:
                logger.warning(f"Failed to load NLI model: {e}")
                _components["nli_model"] = None
    return _components["nli_model"]


@lru_cache()
def get_relation_classifier() -> RelationClassifier:
    """Get or create RelationClassifier instance (with dedicated NLI signal)"""
    if "relation_classifier" not in _components:
        _components["relation_classifier"] = RelationClassifier(
            llm_interface=get_glm_interface(),
            nli_model=get_nli_model(),
        )
    return _components["relation_classifier"]


@lru_cache()
def get_recommendation_engine() -> RecommendationEngine:
    """Get or create recommendation engine instance"""
    if "recommendation_engine" not in _components:
        _components["recommendation_engine"] = RecommendationEngine(
            retriever=get_retriever(),
            knowledge_graph=get_knowledge_graph(),
            gap_analyzer=get_gap_analyzer()
        )
    return _components["recommendation_engine"]


@lru_cache()
def get_paper_api() -> AggregatedPaperAPI:
    """Get or create paper API client instance"""
    if "paper_api" not in _components:
        _components["paper_api"] = AggregatedPaperAPI(
            semantic_scholar_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
            pubmed_key=os.getenv("PUBMED_API_KEY"),
            crossref_email=os.getenv("CROSSREF_EMAIL"),
            pubmed_email=os.getenv("PUBMED_EMAIL"),
            core_key=os.getenv("CORE_API_KEY"),
            elsevier_key=os.getenv("ELSEVIER_API_KEY"),
            elsevier_insttoken=os.getenv("ELSEVIER_INSTTOKEN")
        )
    return _components["paper_api"]


@lru_cache()
def get_coordinator() -> CoordinatorAgent:
    """Get or create coordinator agent instance (LangGraph-based)"""
    if "coordinator" not in _components:
        # Legacy agents
        research_analyzer = ResearchAnalyzerAgent(
            llm_interface=get_glm_interface(),
            retriever=get_retriever()
        )
        gap_detector = GapDetectorAgent(
            llm_interface=get_glm_interface(),
            retriever=get_retriever(),
            knowledge_graph=get_knowledge_graph(),
            fact_table=get_fact_table(),
            fact_extractor=get_fact_extractor(),
            gap_analyzer=get_gap_analyzer(),
            relation_classifier=get_relation_classifier(),
            rule_engine=get_rule_engine(),
        )
        recommender = RecommenderAgent(
            llm_interface=get_glm_interface(),
            retriever=get_retriever(),
            knowledge_graph=get_knowledge_graph()
        )
        
        # Agent tools
        rag_tool = RAGTool(retriever=get_retriever())
        paper_analyzer_tool = PaperAnalyzerTool(
            llm_interface=get_glm_interface(),
            fact_extractor=get_fact_extractor(),
            fact_table=get_fact_table(),
        )
        nli_checker_tool = NLICheckerTool(
            relation_classifier=get_relation_classifier(),
            llm_interface=get_glm_interface(),
        )
        kg_querier_tool = KGQuerierTool(
            graph_builder=get_knowledge_graph(),
            fact_table=get_fact_table(),
        )
        self_critic_tool = SelfCriticTool(
            rule_engine=get_rule_engine(),
            llm_interface=get_glm_interface(),
            fact_table=get_fact_table(),
        )
        
        _components["coordinator"] = CoordinatorAgent(
            research_analyzer=research_analyzer,
            gap_detector=gap_detector,
            recommender=recommender,
            # New agentic components
            rag_tool=rag_tool,
            paper_analyzer_tool=paper_analyzer_tool,
            nli_checker_tool=nli_checker_tool,
            kg_querier_tool=kg_querier_tool,
            self_critic_tool=self_critic_tool,
            fact_extractor=get_fact_extractor(),
            fact_table=get_fact_table(),
            rule_engine=get_rule_engine(),
            relation_classifier=get_relation_classifier(),
            graph_builder=get_knowledge_graph(),
            llm_interface=get_glm_interface(),
        )
    return _components["coordinator"]


@lru_cache()
def get_document_processor() -> DocumentProcessor:
    """Get or create document processor instance"""
    if "document_processor" not in _components:
        ocr_cfg = getattr(config, "ocr", None)
        ocr_enabled = bool(getattr(ocr_cfg, "enabled", False))
        ocr_options = {}
        ocr_min_chars = 50
        if ocr_cfg is not None:
            ocr_options = {
                "service_url": ocr_cfg.service_url,
                "image_mode": ocr_cfg.image_mode,
                "dpi": ocr_cfg.dpi,
                "concurrency": ocr_cfg.concurrency,
                "timeout": ocr_cfg.timeout,
                "ngram_size": ocr_cfg.ngram_size,
                "ngram_window": ocr_cfg.ngram_window,
            }
            ocr_min_chars = ocr_cfg.min_chars_per_page
        _components["document_processor"] = DocumentProcessor(
            chunk_size=config.retrieval.chunk_size,
            chunk_overlap=config.retrieval.chunk_overlap,
            chunk_strategy=getattr(config.retrieval, "chunk_strategy", "sections"),
            ocr_enabled=ocr_enabled,
            ocr_options=ocr_options,
            ocr_min_chars_per_page=ocr_min_chars,
        )
    return _components["document_processor"]
