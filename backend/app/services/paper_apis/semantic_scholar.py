"""Semantic Scholar API client."""

import os
import aiohttp
from typing import Dict, List, Optional
from loguru import logger

from .base import PaperMetadata


class SemanticScholarAPI:
    """Semantic Scholar API client"""
    
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Semantic Scholar API
        
        Args:
            api_key: Optional API key for higher rate limits
                    Get free key at: https://www.semanticscholar.org/product/api
        """
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.headers = {}
        if self.api_key:
            self.headers["x-api-key"] = self.api_key
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        fields: List[str] = None
    ) -> List[PaperMetadata]:
        """
        Search Semantic Scholar papers
        
        Args:
            query: Search query
            max_results: Maximum number of results (max 100)
            fields: Fields to retrieve
        
        Returns:
            List of paper metadata
        """
        if fields is None:
            fields = [
                "paperId", "title", "abstract", "year", "authors",
                "citationCount", "url", "venue", "externalIds"
            ]
        
        params = {
            "query": query,
            "limit": min(max_results, 100),
            "fields": ",".join(fields)
        }
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                url = f"{self.BASE_URL}/paper/search"
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_semantic_scholar_response(data)
                    else:
                        logger.error(f"Semantic Scholar API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Semantic Scholar API request failed: {e}")
            return []
    
    async def get_paper_details(self, paper_id: str) -> Optional[PaperMetadata]:
        """Get detailed information about a specific paper"""
        fields = [
            "paperId", "title", "abstract", "year", "authors",
            "citationCount", "url", "venue", "externalIds", "openAccessPdf"
        ]
        
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                url = f"{self.BASE_URL}/paper/{paper_id}"
                params = {"fields": ",".join(fields)}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_single_paper(data)
                    else:
                        logger.error(f"Semantic Scholar API error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Failed to get paper details: {e}")
            return None
    
    def _parse_semantic_scholar_response(self, data: Dict) -> List[PaperMetadata]:
        """Parse Semantic Scholar API response"""
        papers = []
        
        for item in data.get("data", []):
            papers.append(self._parse_single_paper(item))
        
        return papers
    
    def _parse_single_paper(self, item: Dict) -> PaperMetadata:
        """Parse single paper from Semantic Scholar"""
        authors = [
            author.get("name", "Unknown")
            for author in item.get("authors", [])
        ]
        
        # Get DOI from external IDs
        external_ids = item.get("externalIds", {})
        doi = external_ids.get("DOI")
        
        # Get PDF URL if available
        pdf_url = None
        if item.get("openAccessPdf"):
            pdf_url = item["openAccessPdf"].get("url")
        
        return PaperMetadata(
            paper_id=item.get("paperId", ""),
            title=item.get("title", ""),
            authors=authors,
            abstract=item.get("abstract", ""),
            year=item.get("year"),
            journal=item.get("venue"),
            doi=doi,
            url=item.get("url"),
            pdf_url=pdf_url,
            citation_count=item.get("citationCount", 0),
            source_api="semantic_scholar",
            raw_data=item
        )
