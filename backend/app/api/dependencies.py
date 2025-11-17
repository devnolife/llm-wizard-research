"""
Shared dependencies for API routes
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
def get_retriever() -> RAGRetriever:
    """Get or create RAG retriever instance"""
    if "retriever" not in _components:
        vector_store = get_vector_store()
        _components["retriever"] = RAGRetriever(
            vector_store=vector_store,
            top_k=config.retrieval.top_k,
            min_relevance_score=config.retrieval.min_relevance_score
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
    """Get or create gap analyzer instance"""
    if "gap_analyzer" not in _components:
        _components["gap_analyzer"] = GapAnalyzer(
            vector_store=get_vector_store(),
            knowledge_graph=get_knowledge_graph(),
            llm_interface=get_glm_interface()
        )
    return _components["gap_analyzer"]


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
            core_key=os.getenv("CORE_API_KEY")
        )
    return _components["paper_api"]


@lru_cache()
def get_coordinator() -> CoordinatorAgent:
    """Get or create coordinator agent instance"""
    if "coordinator" not in _components:
        research_analyzer = ResearchAnalyzerAgent(
            llm_interface=get_glm_interface(),
            retriever=get_retriever()
        )
        gap_detector = GapDetectorAgent(
            llm_interface=get_glm_interface(),
            retriever=get_retriever(),
            knowledge_graph=get_knowledge_graph()
        )
        recommender = RecommenderAgent(
            llm_interface=get_glm_interface(),
            retriever=get_retriever(),
            knowledge_graph=get_knowledge_graph()
        )
        _components["coordinator"] = CoordinatorAgent(
            research_analyzer=research_analyzer,
            gap_detector=gap_detector,
            recommender=recommender
        )
    return _components["coordinator"]


@lru_cache()
def get_document_processor() -> DocumentProcessor:
    """Get or create document processor instance"""
    if "document_processor" not in _components:
        _components["document_processor"] = DocumentProcessor(
            chunk_size=config.retrieval.chunk_size,
            chunk_overlap=config.retrieval.chunk_overlap
        )
    return _components["document_processor"]
