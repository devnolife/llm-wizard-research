"""PubMed/NCBI API client."""

import os
import aiohttp
from typing import Dict, List, Optional
from loguru import logger

from .base import PaperMetadata


class PubMedAPI:
    """PubMed/NCBI API client - No API key required (but recommended)"""
    
    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    
    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        """
        Initialize PubMed API
        
        Args:
            api_key: Optional API key for higher rate limits
                    Get key at: https://www.ncbi.nlm.nih.gov/account/
            email: Required by NCBI (tool identification)
        """
        self.api_key = api_key or os.getenv("PUBMED_API_KEY")
        self.email = email or os.getenv("PUBMED_EMAIL", "user@example.com")
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance"
    ) -> List[PaperMetadata]:
        """
        Search PubMed papers
        
        Args:
            query: Search query (supports PubMed syntax)
            max_results: Maximum number of results
            sort: Sort order (relevance, pub_date, etc.)
        
        Returns:
            List of paper metadata
        """
        # Step 1: Search for paper IDs
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": sort,
            "email": self.email
        }
        
        if self.api_key:
            search_params["api_key"] = self.api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get paper IDs
                async with session.get(self.SEARCH_URL, params=search_params) as response:
                    if response.status != 200:
                        logger.error(f"PubMed search error: {response.status}")
                        return []
                    
                    search_data = await response.json()
                    id_list = search_data.get("esearchresult", {}).get("idlist", [])
                    
                    if not id_list:
                        return []
                    
                    # Step 2: Fetch paper details
                    return await self._fetch_paper_details(id_list, session)
        
        except Exception as e:
            logger.error(f"PubMed API request failed: {e}")
            return []
    
    async def _fetch_paper_details(
        self,
        id_list: List[str],
        session: aiohttp.ClientSession
    ) -> List[PaperMetadata]:
        """Fetch detailed information for paper IDs"""
        summary_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "json",
            "email": self.email
        }
        
        if self.api_key:
            summary_params["api_key"] = self.api_key
        
        async with session.get(self.SUMMARY_URL, params=summary_params) as response:
            if response.status != 200:
                logger.error(f"PubMed fetch error: {response.status}")
                return []
            
            data = await response.json()
            return self._parse_pubmed_response(data)
    
    def _parse_pubmed_response(self, data: Dict) -> List[PaperMetadata]:
        """Parse PubMed API response"""
        papers = []
        
        for pmid, item in data.get("result", {}).items():
            if pmid == "uids":
                continue
            
            try:
                # Authors
                authors = [
                    author.get("name", "")
                    for author in item.get("authors", [])
                ]
                
                # Year
                year = None
                if item.get("pubdate"):
                    year_str = item["pubdate"].split()[0]
                    try:
                        year = int(year_str)
                    except ValueError:
                        pass
                
                # URLs
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                doi = None
                for article_id in item.get("articleids", []):
                    if article_id.get("idtype") == "doi":
                        doi = article_id.get("value")
                
                papers.append(PaperMetadata(
                    paper_id=f"PMID:{pmid}",
                    title=item.get("title", ""),
                    authors=authors,
                    abstract="",  # Need separate fetch for abstracts
                    year=year,
                    journal=item.get("fulljournalname", ""),
                    doi=doi,
                    url=url,
                    pdf_url=None,
                    citation_count=0,
                    source_api="pubmed",
                    raw_data=item
                ))
            except Exception as e:
                logger.warning(f"Failed to parse PubMed entry: {e}")
                continue
        
        return papers
