"""CORE API client."""

import asyncio
import os
import httpx
from typing import List, Optional
from loguru import logger

from .base import PaperMetadata


class CoreAPI:
    """
    CORE API - 10+ million open access papers
    https://core.ac.uk/services/api
    FREE: 10,000 requests/day
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://api.core.ac.uk/v3"
        self.api_key = api_key or os.getenv("CORE_API_KEY")
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
    
    async def search(
        self, 
        query: str, 
        max_results: int = 10,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[PaperMetadata]:
        """Search CORE database with optional year filtering and retry logic"""
        # Retry configuration for overloaded CORE API
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Build query with year filters
                search_query = query
                if year_from or year_to:
                    year_filters = []
                    if year_from:
                        year_filters.append(f"yearPublished>={year_from}")
                    if year_to:
                        year_filters.append(f"yearPublished<={year_to}")
                    search_query = f"{query} AND ({' AND '.join(year_filters)})"
                
                # Use full max_results, cap at 100 (CORE API limit per request)
                request_limit = min(max_results, 100)
                
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    params = {
                        "q": search_query,
                        "limit": request_limit
                    }
                    
                    response = await client.get(
                        f"{self.base_url}/search/works",
                        params=params,
                        headers=self.headers
                    )
                    
                    if response.status_code == 401:
                        logger.warning("CORE API: Invalid or missing API key")
                        return []
                    elif response.status_code == 429:
                        # Rate limited — common when no CORE_API_KEY is set.
                        # Retry with exponential backoff, then give actionable advice.
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            logger.warning(
                                f"CORE API rate limited (429, attempt {attempt+1}/{max_retries}), "
                                f"retrying in {wait_time}s..."
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            logger.error(
                                "CORE API rate limited (429). Set a free CORE_API_KEY in "
                                "backend/.env to raise the limit to 10,000 requests/day "
                                "(get one at https://core.ac.uk/services/api)."
                            )
                            return []
                    elif response.status_code == 500:
                        # CORE API Elasticsearch overloaded - retry with backoff
                        error_msg = response.text[:500]
                        if "es_rejected_execution_exception" in error_msg or "rejected execution" in error_msg:
                            if attempt < max_retries - 1:
                                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                                logger.warning(f"CORE API Elasticsearch overloaded (attempt {attempt+1}/{max_retries}), retrying in {wait_time}s...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                logger.error(f"CORE API still overloaded after {max_retries} attempts, giving up")
                                return []
                        else:
                            # Try to parse partial results
                            logger.warning(f"CORE API returned 500, attempting to parse partial results")
                            try:
                                data = response.json()
                                logger.debug(f"CORE 500 response keys: {list(data.keys())}")
                            except Exception as e:
                                logger.error(f"CORE API 500 error with no parseable data: {e}")
                                return []
                    elif response.status_code != 200:
                        logger.error(f"CORE API error: {response.status_code} - {response.text[:200]}")
                        return []
                    else:
                        data = response.json()
                        # Success! Parse the results
                        papers = []
                        results = data.get("results", [])
                        logger.debug(f"CORE API returned {len(results)} results")
                        
                        for item in results:
                            # Extract authors
                            authors = []
                            for author in item.get("authors", []):
                                if isinstance(author, dict):
                                    authors.append(author.get("name", "Unknown"))
                                elif isinstance(author, str):
                                    authors.append(author)
                            
                            download_url = item.get("downloadUrl")
                            source_urls = item.get("sourceFulltextUrls", [])
                            
                            paper = PaperMetadata(
                                paper_id=str(item.get("id", "")),
                                title=item.get("title", ""),
                                authors=authors[:5],
                                abstract=item.get("abstract", "")[:2000] if item.get("abstract") else "",
                                year=item.get("yearPublished"),
                                doi=item.get("doi"),
                                url=source_urls[0] if source_urls else f"https://core.ac.uk/reader/{item.get('id')}",
                                pdf_url=download_url,
                                citation_count=item.get("citationCount", 0),
                                journal=item.get("publisher"),
                                source_api="core",
                                keywords=item.get("subjects", [])[:10] if item.get("subjects") else []
                            )
                            papers.append(paper)
                        
                        logger.info(f"CORE API: Found {len(papers)} papers")
                        return papers
                        
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"CORE API error (attempt {attempt+1}/{max_retries}): {e}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"CORE API error after {max_retries} attempts: {e}")
                    return []
        
        # If we exit the loop without returning, something went wrong
        logger.error("CORE API: Unexpected exit from retry loop")
        return []
    
    async def get_paper_details(self, paper_id: str) -> Optional[PaperMetadata]:
        """Get detailed information about a specific paper from CORE by ID"""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    f"{self.base_url}/works/{paper_id}",
                    headers=self.headers
                )
                
                if response.status_code == 404:
                    logger.warning(f"CORE API: Paper {paper_id} not found")
                    return None
                elif response.status_code != 200:
                    logger.error(f"CORE API error: {response.status_code}")
                    return None
                
                item = response.json()
                
                # Extract authors
                authors = []
                for author in item.get("authors", []):
                    if isinstance(author, dict):
                        authors.append(author.get("name", "Unknown"))
                    elif isinstance(author, str):
                        authors.append(author)
                
                download_url = item.get("downloadUrl")
                source_urls = item.get("sourceFulltextUrls", [])
                
                paper = PaperMetadata(
                    paper_id=str(item.get("id", paper_id)),
                    title=item.get("title", ""),
                    authors=authors[:5],
                    abstract=item.get("abstract", "")[:2000] if item.get("abstract") else "",
                    year=item.get("yearPublished"),
                    doi=item.get("doi"),
                    url=source_urls[0] if source_urls else f"https://core.ac.uk/reader/{item.get('id')}",
                    pdf_url=download_url,
                    citation_count=item.get("citationCount", 0),
                    journal=item.get("publisher"),
                    source_api="core",
                    keywords=item.get("subjects", [])[:10] if item.get("subjects") else []
                )
                
                logger.info(f"CORE API: Retrieved paper {paper_id}")
                return paper
                
        except Exception as e:
            logger.error(f"CORE API get_paper_details error: {e}")
            return None
