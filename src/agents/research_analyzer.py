"""
Research Analyzer Agent

Analyzes research papers and domains to extract insights.
"""

from typing import Dict, Any, List, Optional

from loguru import logger


class ResearchAnalyzerAgent:
    """
    Analyzes research papers and domains
    
    Capabilities:
    - Extract key themes and topics
    - Identify methodologies and approaches
    - Analyze citation patterns
    - Assess research impact and significance
    """
    
    def __init__(self, llm_interface=None, retriever=None):
        """
        Initialize research analyzer agent
        
        Args:
            llm_interface: GLM interface for analysis
            retriever: RAG retriever for document access
        """
        self.llm = llm_interface
        self.retriever = retriever
        
        logger.info("ResearchAnalyzerAgent initialized")
    
    def analyze(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze research domain based on query
        
        Args:
            query: Research query
            context: Additional context
            
        Returns:
            Analysis results
        """
        logger.info(f"Analyzing research for: '{query[:50]}...'")
        
        analysis = {
            "query": query,
            "themes": [],
            "methodologies": [],
            "key_papers": [],
            "summary": ""
        }
        
        # Retrieve relevant papers
        if self.retriever:
            results = self.retriever.retrieve(query, top_k=10)
            
            # Extract papers
            papers = []
            for result in results:
                paper_info = {
                    "title": result.document.metadata.get("title", "Unknown"),
                    "content": result.document.content[:500],
                    "score": result.score,
                    "metadata": result.document.metadata
                }
                papers.append(paper_info)
            
            analysis["key_papers"] = papers[:5]
            
            # Analyze with LLM if available
            if self.llm and papers:
                try:
                    # Prepare context for LLM
                    papers_text = "\n\n".join([
                        f"Title: {p['title']}\nContent: {p['content']}"
                        for p in papers[:5]
                    ])
                    
                    # Get analysis from LLM
                    llm_analysis = self.llm.analyze_research(papers_text)
                    analysis["summary"] = llm_analysis
                    
                    # Extract themes (simplified)
                    analysis["themes"] = self._extract_themes(papers)
                    analysis["methodologies"] = self._extract_methodologies(papers)
                    
                except Exception as e:
                    logger.error(f"LLM analysis failed: {e}")
                    analysis["summary"] = "Analysis unavailable"
        
        logger.info("Research analysis completed")
        return analysis
    
    def _extract_themes(self, papers: List[Dict]) -> List[str]:
        """Extract common themes from papers"""
        # Simplified theme extraction
        # In production, use NLP/topic modeling
        themes = set()
        
        keywords_list = []
        for paper in papers:
            keywords = paper.get("metadata", {}).get("keywords", [])
            keywords_list.extend(keywords)
        
        # Count frequency
        from collections import Counter
        theme_counts = Counter(keywords_list)
        
        # Return top themes
        themes = [theme for theme, _ in theme_counts.most_common(5)]
        return themes
    
    def _extract_methodologies(self, papers: List[Dict]) -> List[str]:
        """Extract methodologies mentioned in papers"""
        # Common research methodologies
        methodology_keywords = [
            "machine learning", "deep learning", "neural network",
            "transformer", "attention mechanism", "supervised learning",
            "unsupervised learning", "reinforcement learning",
            "statistical analysis", "experimental", "survey"
        ]
        
        methodologies = set()
        for paper in papers:
            content = paper.get("content", "").lower()
            for method in methodology_keywords:
                if method in content:
                    methodologies.add(method)
        
        return list(methodologies)[:5]
    
    def analyze_paper(
        self,
        paper_content: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single research paper
        
        Args:
            paper_content: Paper content
            metadata: Paper metadata
            
        Returns:
            Paper analysis
        """
        analysis = {
            "metadata": metadata or {},
            "summary": "",
            "key_contributions": [],
            "limitations": [],
            "future_work": []
        }
        
        if self.llm:
            try:
                # Get summary from LLM
                title = metadata.get("title", "Research Paper") if metadata else "Research Paper"
                summary = self.llm.summarize_paper(title, paper_content)
                analysis["summary"] = summary
            except Exception as e:
                logger.error(f"Paper analysis failed: {e}")
        
        return analysis


# Example usage
if __name__ == "__main__":
    analyzer = ResearchAnalyzerAgent()
    print("ResearchAnalyzerAgent ready")
