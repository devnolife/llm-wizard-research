"""Elsevier ScienceDirect Search API client."""

import os
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from .base import PaperMetadata


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
