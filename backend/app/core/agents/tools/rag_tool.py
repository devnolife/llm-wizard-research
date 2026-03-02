"""
RAG Tool - Retrieves relevant documents from vector store.

Used by the Agent to search for specific information across papers.
"""

from typing import Any, Dict, List, Optional
from loguru import logger


class RAGTool:
    """Tool wrapper for RAG retrieval within the agentic system."""
    
    name = "rag_retriever"
    description = (
        "Search for relevant passages across research papers. "
        "Use this to find specific information, evidence, or context "
        "about a topic, method, or finding."
    )
    
    def __init__(self, retriever=None):
        self.retriever = retriever
    
    def run(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Retrieve relevant passages.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            Dict with retrieved passages and metadata
        """
        if not self.retriever:
            return {"error": "Retriever not available", "results": []}
        
        try:
            results = self.retriever.retrieve(query, top_k=top_k)
            passages = []
            for r in results:
                passages.append({
                    "content": r.document.content[:500],
                    "title": r.document.metadata.get("title", "Unknown"),
                    "source": r.document.metadata.get("source", ""),
                    "score": r.score if hasattr(r, 'score') else 0.0,
                })
            
            logger.debug(f"RAG retrieved {len(passages)} passages for: {query[:50]}")
            return {
                "query": query,
                "results": passages,
                "total": len(passages),
            }
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return {"error": str(e), "results": []}
