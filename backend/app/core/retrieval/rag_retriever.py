"""
RAG Retriever for Research Papers

Implements semantic search, context ranking, and hybrid retrieval strategies.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

from loguru import logger

from .vector_store import VectorStore, SearchResult, Document
from ...utils.document_processor import DocumentProcessor


@dataclass
class RetrievalResult:
    """Enhanced retrieval result with context"""
    document: Document
    score: float
    rank: int
    context: Optional[str] = None  # Surrounding context
    relevance_explanation: Optional[str] = None


class RAGRetriever:
    """
    RAG (Retrieval-Augmented Generation) Retriever
    
    Features:
    - Semantic search using vector embeddings
    - Hybrid retrieval (dense + sparse)
    - Context windowing for better results
    - Re-ranking based on multiple criteria
    - Query expansion and reformulation
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        top_k: int = 5,
        min_relevance_score: float = 0.7,
        context_window: int = 2
    ):
        """
        Initialize RAG retriever
        
        Args:
            vector_store: Vector store instance
            top_k: Number of results to retrieve
            min_relevance_score: Minimum relevance threshold
            context_window: Number of surrounding chunks to include
        """
        self.vector_store = vector_store
        self.top_k = top_k
        self.min_relevance_score = min_relevance_score
        self.context_window = context_window
        
        logger.info(f"RAGRetriever initialized (top_k={top_k}, min_score={min_relevance_score})")
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        rerank: bool = True
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: Search query
            top_k: Number of results (overrides default)
            filter_metadata: Metadata filters
            rerank: Whether to rerank results
            
        Returns:
            List of RetrievalResult objects
        """
        k = top_k or self.top_k
        
        logger.info(f"Retrieving documents for query: '{query[:50]}...'")
        
        # Perform vector search
        search_results = self.vector_store.search(
            query=query,
            top_k=k * 2,  # Get more initially for reranking
            filter_metadata=filter_metadata,
            min_score=self.min_relevance_score
        )
        
        # Convert to RetrievalResult
        retrieval_results = []
        for result in search_results:
            retrieval_results.append(RetrievalResult(
                document=result.document,
                score=result.score,
                rank=result.rank
            ))
        
        # Add context windows
        retrieval_results = self._add_context_windows(retrieval_results)
        
        # Rerank if requested
        if rerank:
            retrieval_results = self._rerank_results(query, retrieval_results)
        
        # Return top k
        final_results = retrieval_results[:k]
        
        logger.info(f"Retrieved {len(final_results)} relevant documents")
        return final_results
    
    def _add_context_windows(
        self,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Add surrounding context to each result
        
        For chunked documents, retrieves adjacent chunks to provide
        better context for generation.
        """
        for result in results:
            metadata = result.document.metadata
            
            # Check if this is a chunked document
            if 'chunk_index' in metadata and 'doc_id' in metadata:
                doc_id = metadata['doc_id']
                chunk_index = metadata['chunk_index']
                
                # Get surrounding chunks
                context_chunks = []
                
                for offset in range(-self.context_window, self.context_window + 1):
                    if offset == 0:
                        continue  # Skip current chunk
                    
                    neighbor_index = chunk_index + offset
                    neighbor_id = f"{doc_id}_chunk_{neighbor_index}"
                    
                    neighbor_doc = self.vector_store.get_document(neighbor_id)
                    if neighbor_doc:
                        context_chunks.append((neighbor_index, neighbor_doc.content))
                
                # Sort by index and combine
                context_chunks.sort(key=lambda x: x[0])
                if context_chunks:
                    result.context = "\n...\n".join([chunk[1] for chunk in context_chunks])
        
        return results
    
    def _rerank_results(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Rerank results based on multiple criteria
        
        Considers:
        - Semantic similarity (from vector store)
        - Query term overlap
        - Document quality indicators
        - Recency (if available)
        """
        scored_results = []
        
        query_terms = set(query.lower().split())
        
        for result in results:
            # Base score from vector similarity
            base_score = result.score
            
            # Bonus for query term overlap
            content_terms = set(result.document.content.lower().split())
            overlap = len(query_terms & content_terms)
            overlap_score = min(overlap / len(query_terms), 1.0) * 0.2
            
            # Bonus for metadata quality
            quality_score = 0.0
            metadata = result.document.metadata
            
            if metadata.get('title'):
                quality_score += 0.05
            if metadata.get('abstract'):
                quality_score += 0.05
            if metadata.get('year'):
                # Prefer more recent papers (within last 10 years)
                year = metadata['year']
                if year >= 2014:  # 2024 - 10
                    quality_score += 0.1
            
            # Combined score
            final_score = base_score + overlap_score + quality_score
            
            result.score = min(final_score, 1.0)
            scored_results.append(result)
        
        # Sort by score
        scored_results.sort(key=lambda x: x.score, reverse=True)
        
        # Update ranks
        for i, result in enumerate(scored_results):
            result.rank = i + 1
        
        return scored_results
    
    def retrieve_with_expansion(
        self,
        query: str,
        top_k: Optional[int] = None,
        expansion_terms: Optional[List[str]] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve with query expansion
        
        Args:
            query: Original query
            top_k: Number of results
            expansion_terms: Additional terms to expand query
            
        Returns:
            List of RetrievalResult objects
        """
        # Expand query
        if expansion_terms:
            expanded_query = f"{query} {' '.join(expansion_terms)}"
        else:
            # Simple expansion with synonyms/related terms
            expanded_query = self._expand_query(query)
        
        logger.info(f"Expanded query: '{expanded_query[:100]}...'")
        
        # Retrieve with expanded query
        return self.retrieve(query=expanded_query, top_k=top_k)
    
    # Lightweight domain synonym map for query expansion (CS/ML domain)
    QUERY_EXPANSION_MAP = {
        "cnn": "convolutional neural network",
        "rnn": "recurrent neural network",
        "nlp": "natural language processing",
        "llm": "large language model",
        "gan": "generative adversarial network",
        "object detection": "object recognition localization",
        "attention": "attention mechanism transformer",
        "transformer": "attention mechanism",
        "optimization": "training optimization gradient",
        "edge": "edge device mobile resource-constrained",
        "compression": "model compression distillation quantization",
        "image recognition": "image classification computer vision",
    }

    def _expand_query(self, query: str) -> str:
        """
        Simple dictionary-based query expansion.

        Appends domain synonyms/expansions for known CS/ML terms found in
        the query. Deterministic and offline (no LLM call).
        """
        query_lower = query.lower()
        additions = [
            expansion
            for term, expansion in self.QUERY_EXPANSION_MAP.items()
            if term in query_lower and expansion.lower() not in query_lower
        ]
        if not additions:
            return query
        return f"{query} {' '.join(additions)}"
    
    def retrieve_multi_query(
        self,
        queries: List[str],
        top_k: Optional[int] = None,
        fusion_method: str = "reciprocal_rank"
    ) -> List[RetrievalResult]:
        """
        Retrieve and fuse results from multiple queries
        
        Args:
            queries: List of queries
            top_k: Number of results
            fusion_method: Fusion method ('reciprocal_rank' or 'score_average')
            
        Returns:
            Fused list of RetrievalResult objects
        """
        k = top_k or self.top_k
        
        # Retrieve for each query
        all_results = []
        for query in queries:
            results = self.retrieve(query=query, top_k=k * 2, rerank=False)
            all_results.append(results)
        
        # Fuse results
        if fusion_method == "reciprocal_rank":
            fused_results = self._fusion_reciprocal_rank(all_results)
        else:
            fused_results = self._fusion_score_average(all_results)
        
        return fused_results[:k]
    
    def _fusion_reciprocal_rank(
        self,
        results_lists: List[List[RetrievalResult]]
    ) -> List[RetrievalResult]:
        """
        Reciprocal Rank Fusion (RRF)
        
        Combines rankings from multiple result lists.
        Score = sum(1 / (k + rank)) for each result
        """
        k = 60  # RRF constant
        doc_scores = defaultdict(float)
        doc_objects = {}
        
        for results in results_lists:
            for result in results:
                doc_id = result.document.id
                doc_scores[doc_id] += 1.0 / (k + result.rank)
                doc_objects[doc_id] = result
        
        # Sort by fused score
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Create fused results
        fused_results = []
        for rank, (doc_id, score) in enumerate(sorted_docs):
            result = doc_objects[doc_id]
            result.score = score
            result.rank = rank + 1
            fused_results.append(result)
        
        return fused_results
    
    def _fusion_score_average(
        self,
        results_lists: List[List[RetrievalResult]]
    ) -> List[RetrievalResult]:
        """
        Average score fusion
        
        Combines scores from multiple result lists by averaging.
        """
        doc_scores = defaultdict(list)
        doc_objects = {}
        
        for results in results_lists:
            for result in results:
                doc_id = result.document.id
                doc_scores[doc_id].append(result.score)
                doc_objects[doc_id] = result
        
        # Calculate average scores
        doc_avg_scores = {
            doc_id: np.mean(scores)
            for doc_id, scores in doc_scores.items()
        }
        
        # Sort by average score
        sorted_docs = sorted(
            doc_avg_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Create fused results
        fused_results = []
        for rank, (doc_id, score) in enumerate(sorted_docs):
            result = doc_objects[doc_id]
            result.score = score
            result.rank = rank + 1
            fused_results.append(result)
        
        return fused_results
    
    def get_context_for_generation(
        self,
        query: str,
        max_tokens: int = 2000,
        top_k: Optional[int] = None
    ) -> Tuple[str, List[RetrievalResult]]:
        """
        Get formatted context for LLM generation
        
        Args:
            query: User query
            max_tokens: Maximum context length (approximate)
            top_k: Number of documents to retrieve
            
        Returns:
            Tuple of (formatted_context, retrieval_results)
        """
        results = self.retrieve(query=query, top_k=top_k)
        
        # Build context string
        context_parts = []
        total_chars = 0
        char_limit = max_tokens * 4  # Rough estimate: 1 token ≈ 4 chars
        
        for i, result in enumerate(results):
            doc = result.document
            metadata = doc.metadata
            
            # Format document
            doc_text = f"[Document {i+1}]\n"
            
            if metadata.get('title'):
                doc_text += f"Title: {metadata['title']}\n"
            if metadata.get('year'):
                doc_text += f"Year: {metadata['year']}\n"
            
            doc_text += f"Content: {doc.content}\n"
            
            if result.context:
                doc_text += f"Additional Context: {result.context}\n"
            
            doc_text += f"Relevance Score: {result.score:.3f}\n"
            doc_text += "-" * 80 + "\n\n"
            
            # Check if adding this would exceed limit
            if total_chars + len(doc_text) > char_limit:
                break
            
            context_parts.append(doc_text)
            total_chars += len(doc_text)
        
        formatted_context = "".join(context_parts)
        
        logger.info(f"Generated context: {total_chars} characters from {len(context_parts)} documents")
        
        return formatted_context, results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retrieval statistics"""
        return {
            "top_k": self.top_k,
            "min_relevance_score": self.min_relevance_score,
            "context_window": self.context_window,
            "total_documents": self.vector_store.count()
        }


# Example usage
if __name__ == "__main__":
    from .vector_store import VectorStore
    
    # Initialize components
    vector_store = VectorStore(
        persist_directory="./test_chroma_db",
        collection_name="test_papers"
    )
    
    retriever = RAGRetriever(
        vector_store=vector_store,
        top_k=3,
        min_relevance_score=0.5
    )
    
    # Retrieve documents
    query = "transformer attention mechanisms"
    results = retriever.retrieve(query)
    
    print(f"\n🔍 Retrieved {len(results)} documents for: '{query}'")
    for result in results:
        print(f"  {result.rank}. {result.document.metadata.get('title', 'Untitled')} (score: {result.score:.3f})")
    
    # Get context for generation
    context, _ = retriever.get_context_for_generation(query, max_tokens=1000)
    print(f"\n📄 Context length: {len(context)} characters")
