"""Europe PMC REST API client."""

import aiohttp
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from .base import PaperMetadata


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
