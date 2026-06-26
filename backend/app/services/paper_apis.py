"""
External Paper API Integration
Supports multiple academic paper APIs: arXiv, Semantic Scholar, PubMed, CrossRef
"""

import os
import aiohttp
import httpx
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import json
from loguru import logger


def _strip_markup(text: str) -> str:
    """Remove JATS/HTML tags (e.g. CrossRef's <jats:p>) and collapse whitespace."""
    if not text:
        return ""
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class PaperMetadata:
    """Standard paper metadata structure"""
    paper_id: str
    title: str
    authors: List[str]
    abstract: str
    year: Optional[int]
    journal: Optional[str]
    doi: Optional[str]
    url: Optional[str]
    pdf_url: Optional[str]
    citation_count: int = 0
    keywords: List[str] = None
    source_api: str = ""
    raw_data: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "year": self.year,
            "journal": self.journal,
            "doi": self.doi,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "citation_count": self.citation_count,
            "keywords": self.keywords or [],
            "source_api": self.source_api,
            "source": self.source_api,
        }


class ArXivAPI:
    """arXiv API client - No API key required"""
    
    BASE_URL = "http://export.arxiv.org/api/query"
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        start: int = 0
    ) -> List[PaperMetadata]:
        """
        Search arXiv papers
        
        Args:
            query: Search query (e.g., "machine learning", "ti:transformers")
            max_results: Maximum number of results
            start: Starting index for pagination
        
        Returns:
            List of paper metadata
        """
        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        content = await response.text()
                        return self._parse_arxiv_response(content)
                    else:
                        logger.error(f"arXiv API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"arXiv API request failed: {e}")
            return []
    
    def _parse_arxiv_response(self, xml_content: str) -> List[PaperMetadata]:
        """Parse arXiv XML response"""
        import xml.etree.ElementTree as ET
        
        papers = []
        root = ET.fromstring(xml_content)
        
        # Namespace for arXiv XML
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        for entry in root.findall('atom:entry', ns):
            try:
                paper_id = entry.find('atom:id', ns).text.split('/')[-1]
                title = entry.find('atom:title', ns).text.strip()
                abstract = entry.find('atom:summary', ns).text.strip()
                
                # Authors
                authors = [
                    author.find('atom:name', ns).text
                    for author in entry.findall('atom:author', ns)
                ]
                
                # Published date
                published = entry.find('atom:published', ns).text
                year = int(published.split('-')[0]) if published else None
                
                # Links
                pdf_url = None
                page_url = None
                for link in entry.findall('atom:link', ns):
                    if link.get('title') == 'pdf':
                        pdf_url = link.get('href')
                    elif link.get('rel') == 'alternate':
                        page_url = link.get('href')
                
                # Categories (keywords)
                keywords = [
                    cat.get('term')
                    for cat in entry.findall('atom:category', ns)
                ]
                
                papers.append(PaperMetadata(
                    paper_id=paper_id,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    year=year,
                    journal="arXiv",
                    doi=None,
                    url=page_url,
                    pdf_url=pdf_url,
                    keywords=keywords,
                    source_api="arxiv"
                ))
            except Exception as e:
                logger.warning(f"Failed to parse arXiv entry: {e}")
                continue
        
        return papers


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
        arxiv_id = external_ids.get("ArXiv")
        
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
        import asyncio
        
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


class EuropePMCAPI:
    """Europe PMC REST API client (open access, no API key required)"""

    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, email: Optional[str] = None):
        self.email = email
        self.headers = {"User-Agent": "WizardResearch/1.0 (mailto:research@example.com)"}

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[PaperMetadata]:
        """
        Search Europe PMC papers

        Args:
            query: Search query
            max_results: Maximum number of results
            year_from: Filter papers from this year onwards (optional)
            year_to: Filter papers up to this year (optional)

        Returns:
            List of paper metadata
        """
        search_query = query
        if year_from or year_to:
            lo = year_from or 1900
            hi = year_to or datetime.now().year
            search_query = f"{query} AND PUB_YEAR:[{lo} TO {hi}]"

        params = {
            "query": search_query,
            "format": "json",
            "pageSize": max_results,
            "resultType": "core",
        }

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_europepmc_response(data)
                    else:
                        logger.error(f"Europe PMC API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Europe PMC API request failed: {e}")
            return []

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove simple inline HTML/JATS tags from abstracts."""
        if not text:
            return ""
        import re
        return re.sub(r"<[^>]+>", " ", text).replace("  ", " ").strip()

    def _parse_europepmc_response(self, data: Dict) -> List[PaperMetadata]:
        """Parse Europe PMC API response"""
        papers = []

        for item in data.get("resultList", {}).get("result", []):
            try:
                # Authors: "Smith J, Doe A." -> list
                author_string = item.get("authorString", "") or ""
                authors = [a.strip() for a in author_string.rstrip(".").split(",") if a.strip()]

                # Year
                year = None
                if item.get("pubYear"):
                    try:
                        year = int(item["pubYear"])
                    except (ValueError, TypeError):
                        year = None

                # URLs: prefer a full-text / DOI link, capture a PDF when offered
                url = None
                pdf_url = None
                for ft in item.get("fullTextUrlList", {}).get("fullTextUrl", []):
                    ft_url = ft.get("url")
                    if not ft_url:
                        continue
                    if url is None:
                        url = ft_url
                    if ft.get("documentStyle") == "pdf" and pdf_url is None:
                        pdf_url = ft_url

                doi = item.get("doi")
                if url is None and doi:
                    url = f"https://doi.org/{doi}"

                papers.append(PaperMetadata(
                    paper_id=doi or f"{item.get('source', 'EPMC')}:{item.get('id', '')}",
                    title=item.get("title", ""),
                    authors=authors[:10],
                    abstract=self._strip_html(item.get("abstractText", ""))[:2000],
                    year=year,
                    journal=item.get("journalTitle"),
                    doi=doi,
                    url=url,
                    pdf_url=pdf_url,
                    citation_count=item.get("citedByCount", 0) or 0,
                    keywords=item.get("keywordList", {}).get("keyword", [])[:10]
                    if item.get("keywordList") else [],
                    source_api="europe_pmc",
                    raw_data=item
                ))
            except Exception as e:
                logger.warning(f"Failed to parse Europe PMC entry: {e}")
                continue

        return papers


class ScienceDirectAPI:
    """
    Elsevier ScienceDirect Search API client.

    Requires a free Elsevier API key (ELSEVIER_API_KEY), obtainable at
    https://dev.elsevier.com/. Full-text access to subscribed content
    additionally requires either running from the institution's IP range
    (e.g. UNHAS campus network / VPN) or an institutional token
    (ELSEVIER_INSTTOKEN) issued by the institution's library. For metadata and
    abstracts (used for search + ingestion) the API key alone is sufficient.
    """

    BASE_URL = "https://api.elsevier.com/content/search/sciencedirect"

    def __init__(self, api_key: Optional[str] = None, insttoken: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELSEVIER_API_KEY")
        self.insttoken = insttoken or os.getenv("ELSEVIER_INSTTOKEN")

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-ELS-APIKey"] = self.api_key
        if self.insttoken:
            headers["X-ELS-Insttoken"] = self.insttoken
        return headers

    async def search(
        self,
        query: str,
        max_results: int = 10,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[PaperMetadata]:
        """Search ScienceDirect papers"""
        if not self.api_key:
            logger.warning(
                "ScienceDirect skipped: no ELSEVIER_API_KEY set. Get a free key at "
                "https://dev.elsevier.com/ and add ELSEVIER_API_KEY to backend/.env "
                "(use your UNHAS campus network/VPN or an ELSEVIER_INSTTOKEN for full text)."
            )
            return []

        params = {
            "query": query,
            "count": min(max_results, 100),
        }
        if year_from or year_to:
            lo = year_from or 1900
            hi = year_to or datetime.now().year
            params["date"] = f"{lo}-{hi}"

        try:
            async with aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_sciencedirect_response(data)
                    elif response.status == 401:
                        logger.error(
                            "ScienceDirect API error 401: invalid ELSEVIER_API_KEY "
                            "(or missing institutional entitlement)."
                        )
                        return []
                    elif response.status == 429:
                        logger.error("ScienceDirect API error 429: rate/quota limit reached.")
                        return []
                    else:
                        body = (await response.text())[:200]
                        logger.error(f"ScienceDirect API error: {response.status} - {body}")
                        return []
        except Exception as e:
            logger.error(f"ScienceDirect API request failed: {e}")
            return []

    def _parse_sciencedirect_response(self, data: Dict) -> List[PaperMetadata]:
        """Parse ScienceDirect Search API response"""
        papers = []
        entries = data.get("search-results", {}).get("entry", [])

        for item in entries:
            # An empty result set is returned as a single entry carrying an error.
            if item.get("error"):
                logger.info(f"ScienceDirect: {item.get('error')}")
                continue
            try:
                # Authors: prefer the structured list, fall back to dc:creator
                authors = []
                author_block = item.get("authors")
                if isinstance(author_block, dict):
                    for a in author_block.get("author", []):
                        name = " ".join(
                            part for part in [a.get("given-name"), a.get("surname")] if part
                        ).strip()
                        if name:
                            authors.append(name)
                if not authors and item.get("dc:creator"):
                    authors = [item["dc:creator"]]

                # Year from prism:coverDate (YYYY-MM-DD)
                year = None
                cover_date = item.get("prism:coverDate")
                if cover_date:
                    try:
                        year = int(str(cover_date)[:4])
                    except (ValueError, TypeError):
                        year = None

                # Public ScienceDirect URL (prefer the scidir link)
                url = None
                for link in item.get("link", []):
                    if link.get("@ref") == "scidir":
                        url = link.get("@href")
                        break
                doi = item.get("prism:doi")
                if url is None:
                    url = f"https://doi.org/{doi}" if doi else item.get("prism:url")

                papers.append(PaperMetadata(
                    paper_id=doi or item.get("dc:identifier", "") or item.get("pii", ""),
                    title=item.get("dc:title", ""),
                    authors=authors[:10],
                    abstract=(item.get("dc:description") or "").strip()[:2000],
                    year=year,
                    journal=item.get("prism:publicationName"),
                    doi=doi,
                    url=url,
                    pdf_url=None,
                    citation_count=int(item.get("citedby-count", 0) or 0),
                    source_api="sciencedirect",
                    raw_data=item
                ))
            except Exception as e:
                logger.warning(f"Failed to parse ScienceDirect entry: {e}")
                continue

        return papers


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


# Example usage and testing
async def test_apis():
    """Test all API integrations"""
    print("=" * 70)
    print("Testing Paper API Integrations")
    print("=" * 70)
    
    query = "transformer neural networks"
    
    # Test arXiv
    print("\n1. Testing arXiv API...")
    arxiv = ArXivAPI()
    arxiv_papers = await arxiv.search(query, max_results=3)
    print(f"   Found {len(arxiv_papers)} papers")
    if arxiv_papers:
        print(f"   Example: {arxiv_papers[0].title[:60]}...")
    
    # Test Semantic Scholar
    print("\n2. Testing Semantic Scholar API...")
    ss = SemanticScholarAPI()
    ss_papers = await ss.search(query, max_results=3)
    print(f"   Found {len(ss_papers)} papers")
    if ss_papers:
        print(f"   Example: {ss_papers[0].title[:60]}...")
    
    # Test CrossRef
    print("\n3. Testing CrossRef API...")
    crossref = CrossRefAPI()
    cr_papers = await crossref.search(query, max_results=3)
    print(f"   Found {len(cr_papers)} papers")
    if cr_papers:
        print(f"   Example: {cr_papers[0].title[:60]}...")
    
    # Test Aggregated Search
    print("\n4. Testing Aggregated Search...")
    aggregated = AggregatedPaperAPI()
    all_results = await aggregated.search_all(query, max_results_per_source=5)
    
    total = sum(len(papers) for papers in all_results.values())
    print(f"   Total papers retrieved: {total}")
    
    unique = aggregated.deduplicate_papers(all_results)
    print(f"   Unique papers after deduplication: {len(unique)}")
    
    print("\n✅ All API tests completed!")


if __name__ == "__main__":
    asyncio.run(test_apis())
