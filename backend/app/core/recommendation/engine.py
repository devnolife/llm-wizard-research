"""
Recommendation Engine

Generates personalized research recommendations using multiple strategies.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from loguru import logger


@dataclass
class RecommendationItem:
    """Single recommendation item"""
    paper_id: str
    title: str
    score: float
    rank: int
    reasons: List[str]
    metadata: Dict[str, Any]


class RecommendationEngine:
    """
    Generates research recommendations
    
    Strategies:
    - Content-based filtering
    - Collaborative filtering (citation-based)
    - Gap-aware recommendations
    - Hybrid recommendations
    """
    
    def __init__(
        self,
        retriever=None,
        knowledge_graph=None,
        gap_analyzer=None
    ):
        """
        Initialize recommendation engine
        
        Args:
            retriever: RAG retriever for content-based recommendations
            knowledge_graph: Knowledge graph for graph-based recommendations
            gap_analyzer: Gap analyzer for gap-aware recommendations
        """
        self.retriever = retriever
        self.knowledge_graph = knowledge_graph
        self.gap_analyzer = gap_analyzer
        
        logger.info("RecommendationEngine initialized")
    
    def generate_recommendations(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None,
        strategy: str = "hybrid",
        top_k: int = 10
    ) -> List[RecommendationItem]:
        """
        Generate recommendations using specified strategy
        
        Args:
            query: User query
            user_context: User preferences and history
            strategy: Recommendation strategy ('content', 'graph', 'gap_aware', 'hybrid')
            top_k: Number of recommendations
            
        Returns:
            List of RecommendationItem objects
        """
        logger.info(f"Generating recommendations (strategy: {strategy}, top_k: {top_k})")
        
        if strategy == "content":
            return self._content_based_recommendations(query, top_k)
        elif strategy == "graph":
            return self._graph_based_recommendations(query, user_context, top_k)
        elif strategy == "gap_aware":
            return self._gap_aware_recommendations(query, user_context, top_k)
        else:  # hybrid
            return self._hybrid_recommendations(query, user_context, top_k)
    
    def _content_based_recommendations(
        self,
        query: str,
        top_k: int
    ) -> List[RecommendationItem]:
        """Content-based recommendations using semantic similarity"""
        if not self.retriever:
            logger.warning("No retriever available for content-based recommendations")
            return []
        
        results = self.retriever.retrieve(query=query, top_k=top_k)
        
        recommendations = []
        for result in results:
            recommendations.append(RecommendationItem(
                paper_id=result.document.id,
                title=result.document.metadata.get("title", "Unknown"),
                score=result.score,
                rank=result.rank,
                reasons=["High semantic similarity to your query"],
                metadata=result.document.metadata
            ))
        
        return recommendations
    
    def _graph_based_recommendations(
        self,
        query: str,
        user_context: Optional[Dict],
        top_k: int
    ) -> List[RecommendationItem]:
        """Graph-based recommendations using citation network"""
        if not self.knowledge_graph:
            logger.warning("No knowledge graph available")
            return self._content_based_recommendations(query, top_k)
        
        # Get seed papers from query
        if self.retriever:
            seed_results = self.retriever.retrieve(query=query, top_k=5)
            seed_ids = [r.document.id for r in seed_results]
        else:
            seed_ids = []
        
        # Expand recommendations using graph
        candidate_scores = {}
        
        for seed_id in seed_ids:
            # Get neighbors
            neighbors = self.knowledge_graph.get_paper_neighbors(seed_id, max_neighbors=10)
            
            for neighbor_id, neighbor_data in neighbors:
                if neighbor_id not in candidate_scores:
                    candidate_scores[neighbor_id] = 0.0
                
                # Add score based on connection strength
                candidate_scores[neighbor_id] += 0.5
        
        # Sort by score
        sorted_candidates = sorted(
            candidate_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Convert to recommendations
        recommendations = []
        for rank, (paper_id, score) in enumerate(sorted_candidates[:top_k]):
            if paper_id in self.knowledge_graph.graph:
                node_data = self.knowledge_graph.graph.nodes[paper_id]
                recommendations.append(RecommendationItem(
                    paper_id=paper_id,
                    title=node_data.get("title", "Unknown"),
                    score=score,
                    rank=rank + 1,
                    reasons=["Related through citation network"],
                    metadata=node_data.get("metadata", {})
                ))
        
        return recommendations
    
    def _gap_aware_recommendations(
        self,
        query: str,
        user_context: Optional[Dict],
        top_k: int
    ) -> List[RecommendationItem]:
        """Recommendations that address identified research gaps"""
        if not self.gap_analyzer or not self.retriever:
            return self._content_based_recommendations(query, top_k)
        
        # Get base recommendations
        base_results = self.retriever.retrieve(query=query, top_k=top_k * 2)
        
        # Get papers for gap analysis
        papers = []
        for result in base_results:
            papers.append({
                "content": result.document.content,
                "metadata": result.document.metadata
            })
        
        # Analyze gaps
        gaps = self.gap_analyzer.analyze_gaps(
            topic=query,
            papers=papers,
            depth="standard"
        )
        
        # Score papers based on gap coverage
        gap_keywords = set()
        for gap in gaps:
            gap_keywords.update(gap.description.lower().split())
        
        recommendations = []
        for result in base_results:
            # Base score from retrieval
            score = result.score
            
            # Boost if addresses gaps
            content = result.document.content.lower()
            gap_matches = sum(1 for keyword in gap_keywords if keyword in content)
            
            if gap_matches > 0:
                score += gap_matches * 0.1
                reasons = [
                    "Addresses identified research gaps",
                    f"Relevant to {gap_matches} gap area(s)"
                ]
            else:
                reasons = ["Relevant to your query"]
            
            recommendations.append(RecommendationItem(
                paper_id=result.document.id,
                title=result.document.metadata.get("title", "Unknown"),
                score=min(score, 1.0),
                rank=0,  # Will be updated after sorting
                reasons=reasons,
                metadata=result.document.metadata
            ))
        
        # Sort and update ranks
        recommendations.sort(key=lambda x: x.score, reverse=True)
        for i, rec in enumerate(recommendations[:top_k]):
            rec.rank = i + 1
        
        return recommendations[:top_k]
    
    def _hybrid_recommendations(
        self,
        query: str,
        user_context: Optional[Dict],
        top_k: int
    ) -> List[RecommendationItem]:
        """Hybrid recommendations combining multiple strategies"""
        all_recommendations = {}
        
        # Get recommendations from each strategy
        strategies = []
        
        if self.retriever:
            content_recs = self._content_based_recommendations(query, top_k)
            strategies.append(("content", content_recs, 0.5))
        
        if self.knowledge_graph:
            graph_recs = self._graph_based_recommendations(query, user_context, top_k)
            strategies.append(("graph", graph_recs, 0.3))
        
        if self.gap_analyzer:
            gap_recs = self._gap_aware_recommendations(query, user_context, top_k)
            strategies.append(("gap", gap_recs, 0.2))
        
        # Combine scores using weighted fusion
        for strategy_name, recs, weight in strategies:
            for rec in recs:
                if rec.paper_id not in all_recommendations:
                    all_recommendations[rec.paper_id] = {
                        "title": rec.title,
                        "metadata": rec.metadata,
                        "score": 0.0,
                        "reasons": set()
                    }
                
                all_recommendations[rec.paper_id]["score"] += rec.score * weight
                all_recommendations[rec.paper_id]["reasons"].update(rec.reasons)
        
        # Convert to list and sort
        final_recommendations = []
        for paper_id, data in all_recommendations.items():
            final_recommendations.append(RecommendationItem(
                paper_id=paper_id,
                title=data["title"],
                score=data["score"],
                rank=0,
                reasons=list(data["reasons"]),
                metadata=data["metadata"]
            ))
        
        # Sort by combined score
        final_recommendations.sort(key=lambda x: x.score, reverse=True)
        
        # Update ranks
        for i, rec in enumerate(final_recommendations[:top_k]):
            rec.rank = i + 1
        
        logger.info(f"Generated {len(final_recommendations[:top_k])} hybrid recommendations")
        return final_recommendations[:top_k]
    
    def explain_recommendation(
        self,
        recommendation: RecommendationItem,
        detailed: bool = False
    ) -> str:
        """
        Generate explanation for a recommendation
        
        Args:
            recommendation: RecommendationItem to explain
            detailed: Whether to provide detailed explanation
            
        Returns:
            Explanation string
        """
        explanation = f"Recommended: {recommendation.title}\n"
        explanation += f"Relevance Score: {recommendation.score:.3f}\n"
        explanation += f"Reasons:\n"
        
        for reason in recommendation.reasons:
            explanation += f"  - {reason}\n"
        
        if detailed and recommendation.metadata:
            explanation += "\nAdditional Information:\n"
            if "year" in recommendation.metadata:
                explanation += f"  - Year: {recommendation.metadata['year']}\n"
            if "authors" in recommendation.metadata:
                authors = recommendation.metadata["authors"][:3]
                explanation += f"  - Authors: {', '.join(authors)}\n"
        
        return explanation


# Example usage
if __name__ == "__main__":
    engine = RecommendationEngine()
    print("RecommendationEngine ready")
