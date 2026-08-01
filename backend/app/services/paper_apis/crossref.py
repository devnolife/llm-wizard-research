"""CrossRef API client."""

import os
import aiohttp
from typing import Dict, List, Optional
from loguru import logger

from .base import PaperMetadata, _strip_markup


class CrossRefAPI:
    """CrossRef API client - No API key required (but recommended)"""
    
    BASE_URL = "https://api.crossref.org/works"
    
    def __init__(self, email: Optional[str] = None):
        """
        Initialize CrossRef API
        
        Args:
            email: Optional email for polite pool (faster responses)
        """
        self.email = email or os.getenv("CROSSREF_EMAIL")
        self.headers = {}
        if self.email:
            self.headers["User-Agent"] = f"ResearchBot/1.0 (mailto:{self.email})"
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        filter_params: Dict[str, str] = None
    ) -> List[PaperMetadata]:
        """
        Search CrossRef papers
        
        Args:
            query: Search query
            max_results: Maximum number of results
            filter_params: Additional filters (e.g., {"type": "journal-article"})
        
        Returns:
            List of paper metadata
        """
        params = {
            "query": query,
            "rows": max_results,
            "sort": "relevance",
            "order": "desc"
        }
        
        if filter_params:
            params["filter"] = ",".join([f"{k}:{v}" for k, v in filter_params.items()])
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_crossref_response(data)
                    else:
                        logger.error(f"CrossRef API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"CrossRef API request failed: {e}")
            return []
    
    def _parse_crossref_response(self, data: Dict) -> List[PaperMetadata]:
        """Parse CrossRef API response"""
        papers = []
        
        for item in data.get("message", {}).get("items", []):
            try:
                # Authors
                authors = []
                for author in item.get("author", []):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    authors.append(f"{given} {family}".strip())
                
                # Year
                year = None
                if item.get("published-print"):
                    year = item["published-print"]["date-parts"][0][0]
                elif item.get("published-online"):
                    year = item["published-online"]["date-parts"][0][0]
                
                # Abstract (CrossRef returns JATS-tagged abstracts)
                abstract = _strip_markup(item.get("abstract", ""))
                
                # URLs
                doi = item.get("DOI", "")
                url = f"https://doi.org/{doi}" if doi else item.get("URL")
                
                papers.append(PaperMetadata(
                    paper_id=doi or item.get("URL", ""),
                    title=item.get("title", [""])[0],
                    authors=authors,
                    abstract=abstract,
                    year=year,
                    journal=item.get("container-title", [""])[0],
                    doi=doi,
                    url=url,
                    pdf_url=None,
                    citation_count=item.get("is-referenced-by-count", 0),
                    source_api="crossref",
                    raw_data=item
                ))
            except Exception as e:
                logger.warning(f"Failed to parse CrossRef entry: {e}")
                continue
        
        return papers
