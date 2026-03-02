"""
Paper Analyzer Tool - Extracts structured information from papers.

Extracts key findings, methods, contributions, and metadata from papers.
Used by the Agent in its analysis phase.
"""

from typing import Any, Dict, List, Optional
from loguru import logger


class PaperAnalyzerTool:
    """Tool for analyzing individual papers and extracting structured info."""
    
    name = "paper_analyzer"
    description = (
        "Analyze a research paper to extract its key findings, methods, "
        "contributions, and limitations. Use this to understand what "
        "each paper contributes to the field."
    )
    
    def __init__(self, llm_interface=None, fact_extractor=None, fact_table=None):
        self.llm = llm_interface
        self.fact_extractor = fact_extractor
        self.fact_table = fact_table
    
    def run(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a paper and extract structured information.
        
        Args:
            paper: Dict with 'content', 'metadata' keys
            
        Returns:
            Structured analysis with findings, methods, etc.
        """
        paper_id = paper.get("doc_id", paper.get("id", "unknown"))
        content = paper.get("content", "")
        title = paper.get("metadata", {}).get("title", "Unknown")
        
        result = {
            "paper_id": paper_id,
            "title": title,
            "analysis": {},
            "facts_extracted": 0,
        }
        
        # Extract facts via FactExtractor
        if self.fact_extractor and self.fact_table and content:
            try:
                stats = self.fact_extractor.extract_from_text(
                    content, paper_id, self.fact_table
                )
                result["facts_extracted"] = stats.get("total_facts", 0)
            except Exception as e:
                logger.error(f"Fact extraction failed for {paper_id}: {e}")
        
        # LLM-based analysis
        if self.llm and content:
            try:
                analysis = self.llm.analyze_research(content[:3000])
                result["analysis"] = {"llm_summary": analysis}
            except Exception as e:
                logger.error(f"LLM analysis failed for {paper_id}: {e}")
        
        logger.debug(f"Analyzed paper: {title} ({result['facts_extracted']} facts)")
        return result
    
    def run_batch(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze multiple papers."""
        return [self.run(paper) for paper in papers]
