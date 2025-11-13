"""
Gap Detector Agent

Identifies research gaps and unexplored areas in a research domain.
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict

from loguru import logger


class GapDetectorAgent:
    """
    Detects research gaps in a domain
    
    Capabilities:
    - Identify unexplored research areas
    - Find contradictions in literature
    - Detect methodological gaps
    - Suggest novel research directions
    """
    
    def __init__(
        self,
        llm_interface=None,
        retriever=None,
        knowledge_graph=None
    ):
        """
        Initialize gap detector agent
        
        Args:
            llm_interface: GLM interface for gap analysis
            retriever: RAG retriever for document access
            knowledge_graph: Knowledge graph for relationship analysis
        """
        self.llm = llm_interface
        self.retriever = retriever
        self.knowledge_graph = knowledge_graph
        
        logger.info("GapDetectorAgent initialized")
    
    def detect_gaps(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect research gaps for a given query/domain
        
        Args:
            query: Research query or domain
            context: Additional context (analyzed papers, themes, etc.)
            
        Returns:
            Detected gaps and recommendations
        """
        logger.info(f"Detecting gaps for: '{query[:50]}...'")
        
        gaps = {
            "query": query,
            "unexplored_areas": [],
            "methodological_gaps": [],
            "application_gaps": [],
            "contradictions": [],
            "future_directions": [],
            "summary": ""
        }
        
        # Get analyzed papers from context
        papers = []
        if context and "analysis" in context:
            papers = context["analysis"].get("key_papers", [])
        
        # If no papers, retrieve them
        if not papers and self.retriever:
            results = self.retriever.retrieve(query, top_k=10)
            papers = [
                {
                    "title": r.document.metadata.get("title", "Unknown"),
                    "content": r.document.content,
                    "metadata": r.document.metadata
                }
                for r in results
            ]
        
        # Detect different types of gaps
        if papers:
            gaps["unexplored_areas"] = self._find_unexplored_areas(papers, query)
            gaps["methodological_gaps"] = self._find_methodological_gaps(papers)
            gaps["application_gaps"] = self._find_application_gaps(papers)
            
            # Use LLM for sophisticated gap analysis
            if self.llm:
                try:
                    papers_summary = "\n\n".join([
                        f"- {p['title']}: {p['content'][:300]}"
                        for p in papers[:5]
                    ])
                    
                    llm_gaps = self.llm.detect_gaps(
                        context=query,
                        papers=[p['title'] for p in papers[:10]]
                    )
                    gaps["summary"] = llm_gaps
                    
                except Exception as e:
                    logger.error(f"LLM gap detection failed: {e}")
        
        logger.info(f"Detected {len(gaps['unexplored_areas'])} unexplored areas")
        return gaps
    
    def _find_unexplored_areas(
        self,
        papers: List[Dict],
        query: str
    ) -> List[Dict[str, str]]:
        """
        Find areas not covered in existing research
        
        Uses topic analysis and coverage mapping
        """
        unexplored = []
        
        # Extract all mentioned topics
        covered_topics = set()
        for paper in papers:
            content = paper.get("content", "").lower()
            keywords = paper.get("metadata", {}).get("keywords", [])
            covered_topics.update([k.lower() for k in keywords])
        
        # Common research areas to check
        potential_areas = [
            "real-world applications",
            "scalability challenges",
            "interpretability",
            "robustness",
            "efficiency",
            "edge deployment",
            "privacy concerns",
            "bias and fairness",
            "cross-domain transfer",
            "multi-modal integration"
        ]
        
        # Find areas not well covered
        for area in potential_areas:
            if area not in " ".join(covered_topics):
                unexplored.append({
                    "area": area.title(),
                    "reason": f"Limited coverage in existing {query} research"
                })
        
        return unexplored[:5]
    
    def _find_methodological_gaps(
        self,
        papers: List[Dict]
    ) -> List[Dict[str, str]]:
        """Find gaps in research methodologies"""
        gaps = []
        
        # Count methodology mentions
        methodology_counts = defaultdict(int)
        
        method_keywords = {
            "supervised": "supervised learning",
            "unsupervised": "unsupervised learning",
            "reinforcement": "reinforcement learning",
            "semi-supervised": "semi-supervised learning",
            "self-supervised": "self-supervised learning",
            "transfer learning": "transfer learning",
            "meta-learning": "meta-learning",
            "few-shot": "few-shot learning"
        }
        
        for paper in papers:
            content = paper.get("content", "").lower()
            for key, method in method_keywords.items():
                if key in content:
                    methodology_counts[method] += 1
        
        # Find underrepresented methods
        total_papers = len(papers)
        for method, count in methodology_counts.items():
            if count < total_papers * 0.2:  # Less than 20% coverage
                gaps.append({
                    "method": method.title(),
                    "coverage": f"{count}/{total_papers} papers",
                    "suggestion": f"Limited exploration of {method}"
                })
        
        return gaps[:3]
    
    def _find_application_gaps(
        self,
        papers: List[Dict]
    ) -> List[Dict[str, str]]:
        """Find gaps in practical applications"""
        gaps = []
        
        # Check for application domains
        application_domains = [
            "healthcare", "finance", "education", "manufacturing",
            "transportation", "retail", "agriculture", "energy"
        ]
        
        mentioned_domains = set()
        for paper in papers:
            content = paper.get("content", "").lower()
            for domain in application_domains:
                if domain in content:
                    mentioned_domains.add(domain)
        
        # Find underrepresented domains
        unexplored_domains = set(application_domains) - mentioned_domains
        
        for domain in list(unexplored_domains)[:3]:
            gaps.append({
                "domain": domain.title(),
                "opportunity": f"Potential for applying research to {domain} sector"
            })
        
        return gaps
    
    def analyze_citation_gaps(
        self,
        papers: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Analyze citation patterns to find gaps
        
        Identifies:
        - Orphan papers (low citations but potentially important)
        - Missing connections between research areas
        """
        citation_gaps = []
        
        # This would use knowledge graph in production
        if self.knowledge_graph:
            # Placeholder for knowledge graph analysis
            pass
        
        return citation_gaps


# Example usage
if __name__ == "__main__":
    gap_detector = GapDetectorAgent()
    print("GapDetectorAgent ready")
