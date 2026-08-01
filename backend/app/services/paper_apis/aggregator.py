"""Aggregated multi-source paper search."""

import asyncio
from typing import Dict, List, Optional
from loguru import logger

from .base import PaperMetadata
from .arxiv import ArXivAPI
from .semantic_scholar import SemanticScholarAPI
from .crossref import CrossRefAPI
from .pubmed import PubMedAPI
from .core import CoreAPI
from .europe_pmc import EuropePMCAPI
from .sciencedirect import ScienceDirectAPI


class AggregatedPaperAPI:
    """
    Aggregated API client that searches across multiple sources
    """
    
    def __init__(
        self,
        semantic_scholar_key: Optional[str] = None,
        pubmed_key: Optional[str] = None,
        crossref_email: Optional[str] = None,
        pubmed_email: Optional[str] = None,
        core_key: Optional[str] = None,
        elsevier_key: Optional[str] = None,
        elsevier_insttoken: Optional[str] = None
    ):
        """Initialize all API clients"""
        self.arxiv = ArXivAPI()
        self.semantic_scholar = SemanticScholarAPI(api_key=semantic_scholar_key)
        self.crossref = CrossRefAPI(email=crossref_email)
        self.pubmed = PubMedAPI(api_key=pubmed_key, email=pubmed_email)
        self.core = CoreAPI(api_key=core_key)
        self.europe_pmc = EuropePMCAPI(email=crossref_email)
        self.sciencedirect = ScienceDirectAPI(
            api_key=elsevier_key, insttoken=elsevier_insttoken
        )
    
    async def search_all(
        self,
        query: str,
        max_results_per_source: int = 10,
        sources: List[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> Dict[str, List[PaperMetadata]]:
        """
        Search across all configured sources
        
        Args:
            query: Search query
            max_results_per_source: Maximum results per source
            sources: List of sources to search (default: all)
            year_from: Filter papers from this year onwards (optional)
            year_to: Filter papers up to this year (optional)
        
        Returns:
            Dictionary mapping source name to list of papers
        """
        if sources is None:
            sources = ["arxiv", "semantic_scholar", "crossref", "pubmed", "core"]
        
        tasks = []
        source_names = []
        
        if "arxiv" in sources:
            tasks.append(self.arxiv.search(query, max_results_per_source))
            source_names.append("arxiv")
        
        if "semantic_scholar" in sources:
            tasks.append(self.semantic_scholar.search(query, max_results_per_source))
            source_names.append("semantic_scholar")
        
        if "crossref" in sources:
            tasks.append(self.crossref.search(query, max_results_per_source))
            source_names.append("crossref")
        
        if "pubmed" in sources:
            tasks.append(self.pubmed.search(query, max_results_per_source))
            source_names.append("pubmed")
        
        if "core" in sources:
            tasks.append(self.core.search(query, max_results_per_source, year_from, year_to))
            source_names.append("core")
        
        if "europe_pmc" in sources:
            tasks.append(self.europe_pmc.search(query, max_results_per_source, year_from, year_to))
            source_names.append("europe_pmc")
        
        if "sciencedirect" in sources:
            tasks.append(self.sciencedirect.search(query, max_results_per_source, year_from, year_to))
            source_names.append("sciencedirect")
        
        # Execute all searches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        combined_results = {}
        for source_name, result in zip(source_names, results):
            if isinstance(result, Exception):
                logger.error(f"Error searching {source_name}: {result}")
                combined_results[source_name] = []
            else:
                combined_results[source_name] = result
                logger.info(f"Retrieved {len(result)} papers from {source_name}")
        
        return combined_results
    
    def deduplicate_papers(
        self,
        all_papers: Dict[str, List[PaperMetadata]],
        query: Optional[str] = None
    ) -> List[PaperMetadata]:
        """
        Deduplicate papers from multiple sources based on DOI and title similarity

        Args:
            all_papers: Dictionary of papers from different sources
            query: Optional search query. When provided, results are ordered by
                relevance to the query (title/abstract term overlap) instead of
                source iteration order — otherwise the first source (e.g. arXiv)
                always dominates the top regardless of relevance.

        Returns:
            Deduplicated list of papers (relevance-ordered when query is given)
        """
        seen_dois = set()
        seen_titles = set()
        unique_papers = []
        
        # Flatten all papers
        for source, papers in all_papers.items():
            for paper in papers:
                # Check DOI first (most reliable)
                if paper.doi:
                    if paper.doi in seen_dois:
                        continue
                    seen_dois.add(paper.doi)
                
                # Check title similarity (normalized)
                title_norm = paper.title.lower().strip()
                if title_norm in seen_titles:
                    continue
                seen_titles.add(title_norm)
                
                unique_papers.append(paper)

        if query:
            unique_papers.sort(
                key=lambda p: self._relevance_score(p, query), reverse=True
            )
        return unique_papers

    @staticmethod
    def _relevance_score(paper: PaperMetadata, query: str) -> float:
        """
        Lightweight query-relevance score for cross-source ordering.

        Title term matches are weighted far higher than abstract matches, and a
        small citation bonus breaks ties. Language-agnostic (works for
        Indonesian queries), so penjadwalan-titled papers rank above unrelated
        arXiv hits.
        """
        import re
        terms = {t for t in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(t) > 2}
        if not terms:
            return 0.0
        title = (paper.title or "").lower()
        abstract = (paper.abstract or "").lower()
        title_hits = sum(1 for t in terms if t in title)
        abstract_hits = sum(1 for t in terms if t in abstract)
        score = 3.0 * (title_hits / len(terms)) + 1.0 * (abstract_hits / len(terms))
        # Tiny citation tie-breaker (log-scaled, capped) — keeps it secondary.
        cites = paper.citation_count or 0
        score += min(cites, 100) / 1000.0
        return score
