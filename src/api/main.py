"""
FastAPI Application for Research Recommendation System

Provides REST API endpoints for all system functionality.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
import tempfile
from pathlib import Path

from loguru import logger

# Import our components
from ..llm.glm_interface import GLMInterface, ModelConfig
from ..retrieval.vector_store import VectorStore, Document
from ..retrieval.rag_retriever import RAGRetriever
from ..agents.coordinator import CoordinatorAgent
from ..agents.research_analyzer import ResearchAnalyzerAgent
from ..agents.gap_detector import GapDetectorAgent
from ..agents.recommender import RecommenderAgent
from ..knowledge_graph.graph_builder import KnowledgeGraphBuilder
from ..gap_detection.analyzer import GapAnalyzer
from ..recommendation.engine import RecommendationEngine
from ..utils.document_processor import DocumentProcessor
from ..utils.config_loader import get_config
from ..external.paper_apis import AggregatedPaperAPI, PaperMetadata


# Pydantic models for request/response
class QueryRequest(BaseModel):
    query: str = Field(..., description="Research query")
    top_k: Optional[int] = Field(5, description="Number of results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")


class RecommendationRequest(BaseModel):
    query: str = Field(..., description="Research query")
    max_results: Optional[int] = Field(10, description="Maximum recommendations")
    strategy: Optional[str] = Field("hybrid", description="Recommendation strategy")
    user_context: Optional[Dict[str, Any]] = Field(None, description="User context")


class GapDetectionRequest(BaseModel):
    topic: str = Field(..., description="Research topic")
    depth: Optional[str] = Field("standard", description="Analysis depth")


class ChatRequest(BaseModel):
    message: str = Field(..., description="Chat message")
    use_history: Optional[bool] = Field(True, description="Use conversation history")


class IngestResponse(BaseModel):
    success: bool
    doc_id: str
    message: str
    chunks_created: int


class HealthResponse(BaseModel):
    status: str
    components: Dict[str, bool]
    version: str


class PaperSearchRequest(BaseModel):
    query: str = Field(..., description="Search query for papers")
    max_results: Optional[int] = Field(10, description="Maximum results per source")
    sources: Optional[List[str]] = Field(None, description="API sources to search (arxiv, semantic_scholar, crossref, pubmed, core)")
    deduplicate: Optional[bool] = Field(True, description="Remove duplicate papers")
    year_from: Optional[int] = Field(None, description="Filter papers from this year onwards")
    year_to: Optional[int] = Field(None, description="Filter papers up to this year")


class PaperSearchResponse(BaseModel):
    query: str
    total_results: int
    papers: List[Dict[str, Any]]
    sources_searched: List[str]


# Initialize FastAPI app
app = FastAPI(
    title="RAG-LLM Research Recommendation System",
    description="AI-powered research paper recommendation with GLM-4.6",
    version="0.1.0"
)

# Load configuration
config = get_config()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.get("cors_origins", ["*"]) if hasattr(config.api, 'get') else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components (lazy loading)
_components = {}


def get_component(name: str):
    """Lazy load components"""
    if name in _components:
        return _components[name]
    
    if name == "glm":
        glm_config = ModelConfig(
            model_name=config.llm.model_name,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens
        )
        _components["glm"] = GLMInterface(glm_config)
    
    elif name == "vector_store":
        _components["vector_store"] = VectorStore(
            persist_directory=config.vector_db.persist_directory,
            collection_name=config.vector_db.collection_name,
            embedding_model=config.vector_db.embedding_model
        )
    
    elif name == "retriever":
        vector_store = get_component("vector_store")
        _components["retriever"] = RAGRetriever(
            vector_store=vector_store,
            top_k=config.retrieval.top_k,
            min_relevance_score=config.retrieval.min_relevance_score
        )
    
    elif name == "knowledge_graph":
        _components["knowledge_graph"] = KnowledgeGraphBuilder()
    
    elif name == "gap_analyzer":
        _components["gap_analyzer"] = GapAnalyzer(
            vector_store=get_component("vector_store"),
            knowledge_graph=get_component("knowledge_graph"),
            llm_interface=get_component("glm")
        )
    
    elif name == "recommendation_engine":
        _components["recommendation_engine"] = RecommendationEngine(
            retriever=get_component("retriever"),
            knowledge_graph=get_component("knowledge_graph"),
            gap_analyzer=get_component("gap_analyzer")
        )
    
    elif name == "paper_api":
        _components["paper_api"] = AggregatedPaperAPI(
            semantic_scholar_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
            pubmed_key=os.getenv("PUBMED_API_KEY"),
            crossref_email=os.getenv("CROSSREF_EMAIL"),
            pubmed_email=os.getenv("PUBMED_EMAIL"),
            core_key=os.getenv("CORE_API_KEY")
        )
    
    elif name == "coordinator":
        research_analyzer = ResearchAnalyzerAgent(
            llm_interface=get_component("glm"),
            retriever=get_component("retriever")
        )
        gap_detector = GapDetectorAgent(
            llm_interface=get_component("glm"),
            retriever=get_component("retriever"),
            knowledge_graph=get_component("knowledge_graph")
        )
        recommender = RecommenderAgent(
            llm_interface=get_component("glm"),
            retriever=get_component("retriever"),
            knowledge_graph=get_component("knowledge_graph")
        )
        _components["coordinator"] = CoordinatorAgent(
            research_analyzer=research_analyzer,
            gap_detector=gap_detector,
            recommender=recommender
        )
    
    elif name == "document_processor":
        _components["document_processor"] = DocumentProcessor(
            chunk_size=config.retrieval.chunk_size,
            chunk_overlap=config.retrieval.chunk_overlap
        )
    
    return _components.get(name)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve frontend HTML"""
    static_dir = Path(__file__).parent.parent.parent / "static"
    index_file = static_dir / "index.html"
    
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return HTMLResponse("""
        <html>
            <head><title>Wizard Research</title></head>
            <body>
                <h1>RAG-LLM Research Recommendation System</h1>
                <p>Version: 0.1.0</p>
                <p><a href="/docs">API Documentation</a></p>
            </body>
        </html>
        """)


@app.get("/api/sources/status")
async def get_api_sources_status():
    """Check which API sources have valid keys configured"""
    return {
        "core": bool(os.getenv("CORE_API_KEY")),
        "semantic_scholar": bool(os.getenv("SEMANTIC_SCHOLAR_API_KEY")),
        "pubmed": bool(os.getenv("PUBMED_API_KEY")),
        "crossref": bool(os.getenv("CROSSREF_EMAIL")),
        "arxiv": True  # arXiv doesn't require an API key
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    components_status = {}
    
    try:
        glm = get_component("glm")
        components_status["glm"] = glm.health_check()
    except Exception as e:
        logger.error(f"GLM health check failed: {e}")
        components_status["glm"] = False
    
    try:
        vector_store = get_component("vector_store")
        components_status["vector_store"] = vector_store.count() >= 0
    except Exception as e:
        logger.error(f"Vector store health check failed: {e}")
        components_status["vector_store"] = False
    
    # Overall status
    all_healthy = all(components_status.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        components=components_status,
        version="0.1.0"
    )


@app.post("/api/search")
async def search(request: QueryRequest):
    """Search for relevant papers"""
    try:
        retriever = get_component("retriever")
        results = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            filter_metadata=request.filters
        )
        
        return {
            "query": request.query,
            "total_results": len(results),
            "results": [
                {
                    "rank": r.rank,
                    "title": r.document.metadata.get("title", "Unknown"),
                    "content": r.document.content[:500],
                    "score": r.score,
                    "metadata": r.document.metadata
                }
                for r in results
            ]
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recommend")
async def recommend(request: RecommendationRequest):
    """Get research recommendations"""
    try:
        coordinator = get_component("coordinator")
        
        # Process through multi-agent system
        results = coordinator.process_research_query(
            query=request.query,
            context=request.user_context or {}
        )
        
        return {
            "query": request.query,
            "recommendations": results.get("recommendations", []),
            "analysis": results.get("analysis", {}),
            "gaps": results.get("gaps", {}),
            "metadata": results.get("metadata", {})
        }
    except Exception as e:
        logger.error(f"Recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gaps")
async def detect_gaps(request: GapDetectionRequest):
    """Detect research gaps"""
    try:
        gap_analyzer = get_component("gap_analyzer")
        retriever = get_component("retriever")
        
        # Get relevant papers
        results = retriever.retrieve(query=request.topic, top_k=20)
        papers = [
            {
                "content": r.document.content,
                "metadata": r.document.metadata
            }
            for r in results
        ]
        
        # Analyze gaps
        gaps = gap_analyzer.analyze_gaps(
            topic=request.topic,
            papers=papers,
            depth=request.depth
        )
        
        return {
            "topic": request.topic,
            "total_gaps": len(gaps),
            "gaps": [
                {
                    "type": gap.gap_type,
                    "description": gap.description,
                    "confidence": gap.confidence,
                    "suggested_directions": gap.suggested_directions
                }
                for gap in gaps
            ]
        }
    except Exception as e:
        logger.error(f"Gap detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat with the research assistant"""
    try:
        glm = get_component("glm")
        
        response = glm.chat(
            message=request.message,
            use_history=request.use_history
        )
        
        return {
            "message": request.message,
            "response": response
        }
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = None,
    authors: Optional[str] = None,
    year: Optional[int] = None
):
    """Ingest a research paper"""
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Save temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Process document
        processor = get_component("document_processor")
        processed_doc = processor.process_pdf(tmp_path)
        
        # Add metadata
        if title:
            processed_doc.metadata["title"] = title
        if authors:
            processed_doc.metadata["authors"] = [a.strip() for a in authors.split(",")]
        if year:
            processed_doc.metadata["year"] = year
        
        # Add to vector store
        vector_store = get_component("vector_store")
        
        # Convert chunks to documents
        docs_to_add = []
        for chunk in processed_doc.chunks:
            docs_to_add.append(Document(
                id=chunk.chunk_id,
                content=chunk.content,
                metadata=chunk.metadata
            ))
        
        doc_ids = vector_store.add_documents(docs_to_add)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return IngestResponse(
            success=True,
            doc_id=processed_doc.doc_id,
            message=f"Successfully ingested: {processed_doc.title}",
            chunks_created=len(doc_ids)
        )
        
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_statistics():
    """Get system statistics"""
    try:
        vector_store = get_component("vector_store")
        knowledge_graph = get_component("knowledge_graph")
        
        return {
            "vector_store": vector_store.get_stats(),
            "knowledge_graph": knowledge_graph.get_statistics() if knowledge_graph else {},
            "total_documents": vector_store.count()
        }
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document"""
    try:
        vector_store = get_component("vector_store")
        success = vector_store.delete_document(doc_id)
        
        if success:
            return {"message": f"Document {doc_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Document deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    logger.info("Starting RAG-LLM Research Recommendation System")
    
    # Create necessary directories
    os.makedirs(config.data.raw_path, exist_ok=True)
    os.makedirs(config.data.processed_path, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    # Pre-load critical components
    try:
        get_component("vector_store")
        logger.info("Vector store initialized")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down RAG-LLM Research Recommendation System")


# ====================================================================================
# External Paper API Endpoints
# ====================================================================================

@app.post("/api/papers/search", response_model=PaperSearchResponse)
async def search_external_papers(request: PaperSearchRequest):
    """
    Search for research papers across multiple external APIs
    
    Supported sources:
    - arxiv: arXiv papers (no API key needed)
    - semantic_scholar: Semantic Scholar (optional API key for higher limits)
    - crossref: CrossRef database (optional email for faster responses)
    - pubmed: PubMed/NCBI (optional API key for higher limits)
    - core: CORE open access (API key recommended, 10K requests/day free)
    
    Example:
    ```
    POST /api/papers/search
    {
        "query": "transformer neural networks",
        "max_results": 10,
        "sources": ["arxiv", "semantic_scholar", "core"],
        "deduplicate": true
    }
    ```
    """
    try:
        paper_api = get_component("paper_api")
        
        # Search across specified sources
        sources = request.sources or ["arxiv", "core", "crossref"]
        logger.info(f"Searching papers: '{request.query}' across {sources}")
        
        results = await paper_api.search_all(
            query=request.query,
            max_results_per_source=request.max_results,
            sources=sources,
            year_from=request.year_from,
            year_to=request.year_to
        )
        
        # Deduplicate if requested
        if request.deduplicate:
            papers = paper_api.deduplicate_papers(results)
            logger.info(f"Deduplicated to {len(papers)} unique papers")
        else:
            # Flatten all results
            papers = []
            for source_papers in results.values():
                papers.extend(source_papers)
        
        # Convert to dict format
        papers_dict = [paper.to_dict() for paper in papers]
        
        return PaperSearchResponse(
            query=request.query,
            total_results=len(papers_dict),
            papers=papers_dict,
            sources_searched=sources
        )
    
    except Exception as e:
        logger.error(f"Paper search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Paper search failed: {str(e)}")


@app.post("/api/papers/ingest-external")
async def ingest_external_paper(
    paper_id: str,
    source: str = "semantic_scholar",
    background_tasks: BackgroundTasks = None
):
    """
    Fetch and ingest a specific paper from external API into the vector store
    
    Args:
        paper_id: Paper ID (e.g., DOI, arXiv ID, PubMed ID)
        source: Source API (semantic_scholar, arxiv, etc.)
    
    Example:
    ```
    POST /api/papers/ingest-external?paper_id=2010.11929&source=arxiv
    ```
    """
    try:
        paper_api = get_component("paper_api")
        vector_store = get_component("vector_store")
        
        logger.info(f"Fetching paper {paper_id} from {source}")
        
        # Fetch paper details based on source
        paper = None
        if source == "semantic_scholar":
            paper = await paper_api.semantic_scholar.get_paper_details(paper_id)
        elif source == "arxiv":
            # arXiv search by ID
            results = await paper_api.arxiv.search(f"id:{paper_id}", max_results=1)
            paper = results[0] if results else None
        else:
            raise HTTPException(status_code=400, detail=f"Source {source} not supported for direct fetch")
        
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        
        # Create document from paper metadata
        doc = Document(
            id=paper.paper_id,
            content=f"{paper.title}\n\n{paper.abstract}",
            metadata={
                "title": paper.title,
                "authors": ", ".join(paper.authors),
                "year": paper.year,
                "journal": paper.journal,
                "doi": paper.doi,
                "url": paper.url,
                "source_api": paper.source_api,
                "keywords": ", ".join(paper.keywords or [])
            }
        )
        
        # Add to vector store
        doc_id = vector_store.add_document(doc)
        logger.info(f"Added paper {paper_id} to vector store as {doc_id}")
        
        return {
            "success": True,
            "doc_id": doc_id,
            "paper_id": paper_id,
            "title": paper.title,
            "message": f"Successfully ingested paper from {source}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest external paper: {e}")
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")


@app.post("/api/papers/batch-ingest")
async def batch_ingest_papers(
    query: str,
    max_results: int = 20,
    sources: List[str] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Search for papers and automatically ingest them into the vector store
    
    Example:
    ```
    POST /api/papers/batch-ingest
    {
        "query": "attention mechanisms in NLP",
        "max_results": 20,
        "sources": ["arxiv", "semantic_scholar"]
    }
    ```
    """
    try:
        paper_api = get_component("paper_api")
        vector_store = get_component("vector_store")
        
        # Search for papers
        sources = sources or ["arxiv", "semantic_scholar"]
        logger.info(f"Batch ingest: Searching for '{query}' across {sources}")
        
        results = await paper_api.search_all(
            query=query,
            max_results_per_source=max_results // len(sources),
            sources=sources
        )
        
        # Deduplicate
        papers = paper_api.deduplicate_papers(results)
        logger.info(f"Found {len(papers)} unique papers to ingest")
        
        # Ingest all papers
        ingested_count = 0
        failed_count = 0
        ingested_ids = []
        
        for paper in papers[:max_results]:
            try:
                doc = Document(
                    id=paper.paper_id,
                    content=f"{paper.title}\n\n{paper.abstract}",
                    metadata={
                        "title": paper.title,
                        "authors": ", ".join(paper.authors),
                        "year": paper.year,
                        "journal": paper.journal,
                        "doi": paper.doi,
                        "url": paper.url,
                        "source_api": paper.source_api,
                        "keywords": ", ".join(paper.keywords or [])
                    }
                )
                
                doc_id = vector_store.add_document(doc)
                ingested_ids.append(doc_id)
                ingested_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to ingest paper {paper.paper_id}: {e}")
                failed_count += 1
        
        return {
            "success": True,
            "query": query,
            "papers_found": len(papers),
            "papers_ingested": ingested_count,
            "papers_failed": failed_count,
            "ingested_ids": ingested_ids,
            "message": f"Successfully ingested {ingested_count} papers"
        }
    
    except Exception as e:
        logger.error(f"Batch ingest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch ingest failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        workers=config.api.workers
    )
