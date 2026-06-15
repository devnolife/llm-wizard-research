"""
Recommender Agent

Generates research paper recommendations based on queries and detected gaps.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from loguru import logger


@dataclass
class Recommendation:
    """Represents a research recommendation"""
    paper_id: str
    title: str
    relevance_score: float
    reason: str
    metadata: Dict[str, Any]
    rank: int


class RecommenderAgent:
    """
    Generates personalized research recommendations
    
    Capabilities:
    - Query-based paper recommendations
    - Gap-aware recommendations
    - Novelty and diversity balancing
    - Citation-aware recommendations
    """
    
    def __init__(
        self,
        llm_interface=None,
        retriever=None,
        knowledge_graph=None
    ):
        """
        Initialize recommender agent
        
        Args:
            llm_interface: GLM interface for recommendation generation
            retriever: RAG retriever for document access
            knowledge_graph: Knowledge graph for relationship-based recommendations
        """
        self.llm = llm_interface
        self.retriever = retriever
        self.knowledge_graph = knowledge_graph
        
        logger.info("RecommenderAgent initialized")
    
    def recommend(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        diversity_weight: float = 0.3
    ) -> Dict[str, Any]:
        """
        Generate research recommendations
        
        Args:
            query: User research query
            context: Additional context (gaps, preferences, etc.)
            top_k: Number of recommendations
            diversity_weight: Weight for diversity vs. relevance
            
        Returns:
            Recommendations with explanations
        """
        logger.info(f"Generating recommendations for: '{query[:50]}...'")
        
        recommendations_result = {
            "query": query,
            "recommendations": [],
            "reasoning": "",
            "metadata": {
                "total_candidates": 0,
                "diversity_weight": diversity_weight
            }
        }
        
        if not self.retriever:
            logger.warning("No retriever available for recommendations")
            return recommendations_result
        
        # Retrieve candidate papers
        retrieval_results = self.retriever.retrieve(
            query=query,
            top_k=top_k * 2  # Get more candidates for diversity
        )
        
        recommendations_result["metadata"]["total_candidates"] = len(retrieval_results)
        
        # Convert to recommendations
        candidates = []
        for result in retrieval_results:
            rec = Recommendation(
                paper_id=result.document.id,
                title=result.document.metadata.get("title", "Unknown"),
                relevance_score=result.score,
                reason=self._generate_reason(result, context),
                metadata=result.document.metadata,
                rank=result.rank
            )
            candidates.append(rec)
        
        # Apply diversity and gap-awareness
        if context and "gaps" in context:
            candidates = self._apply_gap_awareness(candidates, context["gaps"])
        
        if diversity_weight > 0:
            candidates = self._diversify_recommendations(candidates, diversity_weight)
        
        # Sort by adjusted scores
        candidates.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Update ranks
        for i, rec in enumerate(candidates[:top_k]):
            rec.rank = i + 1
        
        # Convert to dict format
        recommendations_result["recommendations"] = [
            {
                "rank": rec.rank,
                "paper_id": rec.paper_id,
                "title": rec.title,
                "relevance_score": rec.relevance_score,
                "reason": rec.reason,
                "metadata": rec.metadata
            }
            for rec in candidates[:top_k]
        ]
        
        # Generate overall reasoning with LLM
        if self.llm and recommendations_result["recommendations"]:
            try:
                papers_info = [
                    {"title": r["title"], "abstract": r["metadata"].get("abstract", "N/A")}
                    for r in recommendations_result["recommendations"][:5]
                ]
                
                llm_reasoning = self.llm.recommend_papers(
                    query=query,
                    papers=papers_info,
                    top_k=top_k
                )
                recommendations_result["reasoning"] = llm_reasoning
                
            except Exception as e:
                logger.error(f"LLM reasoning generation failed: {e}")
        
        logger.info(f"Generated {len(recommendations_result['recommendations'])} recommendations")
        return recommendations_result
    
    def _generate_reason(
        self,
        result,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate explanation for recommendation"""
        reasons = []
        
        # Relevance-based reason
        if result.score > 0.8:
            reasons.append("Highly relevant to your query")
        elif result.score > 0.6:
            reasons.append("Relevant to your research area")
        
        # Metadata-based reasons
        metadata = result.document.metadata
        
        if metadata.get("year"):
            year = metadata["year"]
            if year >= 2020:
                reasons.append(f"Recent publication ({year})")
        
        if metadata.get("keywords"):
            reasons.append("Matches key research themes")
        
        # Gap-based reasons
        if context and "gaps" in context:
            gaps = context["gaps"]
            if isinstance(gaps, dict):
                if gaps.get("unexplored_areas"):
                    reasons.append("Addresses identified research gaps")
            elif isinstance(gaps, list) and gaps:
                reasons.append("Addresses identified research gaps")
        
        return "; ".join(reasons) if reasons else "Relevant to your query"
    
    def _apply_gap_awareness(
        self,
        candidates: List[Recommendation],
        gaps: Any
    ) -> List[Recommendation]:
        """
        Boost recommendations that address identified gaps.
        Handles both dict format (legacy) and list of gap indicators.
        """
        gap_keywords = set()
        
        if isinstance(gaps, dict):
            for area in gaps.get("unexplored_areas", []):
                if isinstance(area, dict):
                    gap_keywords.add(area.get("area", "").lower())
            for method in gaps.get("methodological_gaps", []):
                if isinstance(method, dict):
                    gap_keywords.add(method.get("method", "").lower())
        elif isinstance(gaps, list):
            for gap in gaps:
                if isinstance(gap, dict):
                    desc = gap.get("description", gap.get("title", "")).lower()
                    for word in desc.split():
                        if len(word) > 4:
                            gap_keywords.add(word)
                elif isinstance(gap, str):
                    for word in gap.lower().split():
                        if len(word) > 4:
                            gap_keywords.add(word)
        
        # Boost scores for papers addressing gaps
        for candidate in candidates:
            content = candidate.metadata.get("abstract", "").lower()
            title = candidate.title.lower()
            
            gap_matches = sum(1 for keyword in gap_keywords if keyword in content or keyword in title)
            
            if gap_matches > 0:
                # Boost score
                candidate.relevance_score = min(
                    candidate.relevance_score + (gap_matches * 0.1),
                    1.0
                )
                candidate.reason += f" | Addresses {gap_matches} identified gap(s)"
        
        return candidates
    
    def _diversify_recommendations(
        self,
        candidates: List[Recommendation],
        diversity_weight: float
    ) -> List[Recommendation]:
        """
        Diversify recommendations to avoid redundancy
        
        Uses Maximal Marginal Relevance (MMR) approach
        """
        if not candidates:
            return candidates
        
        # Simple diversity: penalize papers with very similar titles
        seen_keywords = set()
        
        for candidate in candidates:
            title_words = set(candidate.title.lower().split())
            
            # Calculate overlap with seen keywords
            overlap = len(title_words & seen_keywords)
            
            if overlap > 3:  # High overlap
                # Penalize score
                penalty = overlap * diversity_weight * 0.1
                candidate.relevance_score = max(
                    candidate.relevance_score - penalty,
                    0.0
                )
            
            # Add to seen keywords
            seen_keywords.update(title_words)
        
        return candidates
    
    def recommend_by_paper(
        self,
        paper_id: str,
        top_k: int = 5
    ) -> List[Recommendation]:
        """
        Recommend papers similar to a given paper
        
        Args:
            paper_id: Source paper ID
            top_k: Number of recommendations
            
        Returns:
            List of similar paper recommendations
        """
        logger.info(f"Finding papers similar to: {paper_id}")
        
        if not self.retriever:
            return []
        
        # Get source paper
        source_doc = self.retriever.vector_store.get_document(paper_id)
        if not source_doc:
            logger.warning(f"Paper {paper_id} not found")
            return []
        
        # Search for similar papers
        results = self.retriever.retrieve(
            query=source_doc.content[:500],  # Use content for similarity
            top_k=top_k + 1  # +1 to exclude source paper
        )
        
        # Convert to recommendations (exclude source paper)
        recommendations = []
        for result in results:
            if result.document.id == paper_id:
                continue
            
            rec = Recommendation(
                paper_id=result.document.id,
                title=result.document.metadata.get("title", "Unknown"),
                relevance_score=result.score,
                reason="Similar research focus and methodology",
                metadata=result.document.metadata,
                rank=len(recommendations) + 1
            )
            recommendations.append(rec)
            
            if len(recommendations) >= top_k:
                break
        
        return recommendations
    
    def recommend_reading_order(
        self,
        paper_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Suggest optimal reading order for a list of papers
        
        Based on:
        - Foundational papers first
        - Chronological progression
        - Dependency analysis
        
        Args:
            paper_ids: List of paper IDs
            
        Returns:
            Ordered list with reading recommendations
        """
        if not self.retriever:
            return []
        
        # Get all papers
        papers = []
        for paper_id in paper_ids:
            doc = self.retriever.vector_store.get_document(paper_id)
            if doc:
                papers.append({
                    "paper_id": paper_id,
                    "title": doc.metadata.get("title", "Unknown"),
                    "year": doc.metadata.get("year", 9999),
                    "metadata": doc.metadata
                })
        
        # Sort by year (chronological order)
        papers.sort(key=lambda x: x["year"])
        
        # Add reading order suggestions
        for i, paper in enumerate(papers):
            if i == 0:
                paper["reading_note"] = "Start here: Foundational work"
            elif i < len(papers) // 2:
                paper["reading_note"] = "Core concepts"
            else:
                paper["reading_note"] = "Recent developments"
            paper["reading_order"] = i + 1
        
        return papers


# Example usage
if __name__ == "__main__":
    recommender = RecommenderAgent()
    print("RecommenderAgent ready")
