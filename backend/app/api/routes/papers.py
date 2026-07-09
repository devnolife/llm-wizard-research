"""
External paper API endpoints
"""

from fastapi import APIRouter, HTTPException
from loguru import logger
from typing import List, Dict, Any

from ...models.requests import PaperSearchRequest
from ...models.responses import PaperSearchResponse
from ...core.retrieval.vector_store import Document
from ..dependencies import get_vector_store, get_paper_api

router = APIRouter()


def clean_paper_metadata(paper) -> Dict[str, Any]:
    """Clean paper metadata by removing None values for ChromaDB compatibility"""
    metadata = {
        "title": paper.title or "Unknown",
        "authors": ", ".join(paper.authors) if paper.authors else "Unknown",
        "source_api": paper.source_api or "unknown",
    }
    
    # Add optional fields only if they have values
    if paper.year is not None:
        metadata["year"] = int(paper.year)
    if paper.journal:
        metadata["journal"] = str(paper.journal)
    if paper.doi:
        metadata["doi"] = str(paper.doi)
    if paper.url:
        metadata["url"] = str(paper.url)
    if paper.keywords:
        metadata["keywords"] = ", ".join(paper.keywords)
    if paper.citation_count is not None:
        metadata["citation_count"] = int(paper.citation_count)
    
    return metadata


@router.post("/search", response_model=PaperSearchResponse)
async def search_external_papers(request: PaperSearchRequest):
    """
    Search for research papers across multiple external APIs
    
    Supported sources:
    - arxiv: arXiv papers (no API key needed)
    - semantic_scholar: Semantic Scholar (optional API key for higher limits)
    - crossref: CrossRef database (optional email for faster responses)
    - pubmed: PubMed/NCBI (optional API key for higher limits)
    - core: CORE open access (API key recommended, 10K requests/day free)
    """
    try:
        paper_api = get_paper_api()
        
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
            papers = paper_api.deduplicate_papers(results, query=request.query)
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
            sources_searched=sources,
            embedding_model=request.embedding_model
        )
    
    except Exception as e:
        logger.error(f"Paper search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Paper search failed: {str(e)}")


@router.post("/ingest-external")
async def ingest_external_paper(
    paper_id: str,
    source: str = "semantic_scholar",
):
    """
    Fetch and ingest a specific paper from external API into the vector store
    
    Args:
        paper_id: Paper ID (e.g., DOI, arXiv ID, PubMed ID)
        source: Source API (semantic_scholar, arxiv, etc.)
    """
    try:
        paper_api = get_paper_api()
        vector_store = get_vector_store()
        
        logger.info(f"Fetching paper {paper_id} from {source}")
        
        # Fetch paper details based on source
        paper = None
        if source == "semantic_scholar":
            paper = await paper_api.semantic_scholar.get_paper_details(paper_id)
        elif source == "arxiv":
            results = await paper_api.arxiv.search(f"id:{paper_id}", max_results=1)
            paper = results[0] if results else None
        elif source == "core":
            paper = await paper_api.core.get_paper_details(paper_id)
        elif source == "pubmed":
            results = await paper_api.pubmed.search(paper_id, max_results=1)
            paper = results[0] if results else None
        elif source == "crossref":
            results = await paper_api.crossref.search(paper_id, max_results=1)
            paper = results[0] if results else None
        elif source == "europe_pmc":
            results = await paper_api.europe_pmc.search(paper_id, max_results=1)
            paper = results[0] if results else None
        elif source == "sciencedirect":
            results = await paper_api.sciencedirect.search(paper_id, max_results=1)
            paper = results[0] if results else None
        else:
            raise HTTPException(status_code=400, detail=f"Source {source} not supported")
        
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        
        # Create document from paper metadata
        metadata = clean_paper_metadata(paper)
        
        doc = Document(
            id=paper.paper_id,
            content=f"{paper.title or 'Untitled'}\n\n{paper.abstract or 'No abstract available'}",
            metadata=metadata
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


@router.post("/batch-ingest")
async def batch_ingest_papers(
    query: str,
    max_results: int = 20,
    sources: List[str] = None,
):
    """
    Search for papers and automatically ingest them into the vector store
    """
    try:
        paper_api = get_paper_api()
        vector_store = get_vector_store()
        
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
                metadata = clean_paper_metadata(paper)
                
                doc = Document(
                    id=paper.paper_id,
                    content=f"{paper.title or 'Untitled'}\n\n{paper.abstract or 'No abstract available'}",
                    metadata=metadata
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
