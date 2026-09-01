"""Elsevier Scopus Search API client."""

import os
import aiohttp
from typing import Dict, List, Optional
from loguru import logger

from .base import PaperMetadata


class ScopusAPI:
    """
    Elsevier Scopus Search API client.

    Uses the same free Elsevier API key as ScienceDirect (ELSEVIER_API_KEY,
    from https://dev.elsevier.com/). Unlike the ScienceDirect search API —
    which requires the request to originate from a subscribing institution's
    IP range (or an ELSEVIER_INSTTOKEN) — the Scopus search API works with
    the API key alone, returning metadata (title, authors, venue, year, DOI,
    citation counts) for 90M+ records across all publishers. Abstracts are
    only included for subscriber-entitled requests; DOI + Unpaywall can then
    resolve open-access PDFs.
    """

    BASE_URL = "https://api.elsevier.com/content/search/scopus"

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
        """Search Scopus records"""
        if not self.api_key:
            logger.warning(
                "Scopus skipped: no ELSEVIER_API_KEY set. Get a free key at "
                "https://dev.elsevier.com/ and add ELSEVIER_API_KEY to backend/.env."
            )
            return []

        # Scopus uses fielded boolean syntax; TITLE-ABS-KEY covers title,
        # abstract and keywords. Unquoted terms are implicitly AND-ed
        # (quoting the whole query would force an exact phrase → 0 hits).
        scopus_query = f"TITLE-ABS-KEY({query})"
        if year_from:
            scopus_query += f" AND PUBYEAR > {year_from - 1}"
        if year_to:
            scopus_query += f" AND PUBYEAR < {year_to + 1}"

        params = {
            "query": scopus_query,
            "count": min(max_results, 25),
            "sort": "-citedby-count",
        }

        try:
            async with aiohttp.ClientSession(headers=self._headers()) as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_scopus_response(data)
                    elif response.status == 401:
                        logger.error("Scopus API error 401: invalid ELSEVIER_API_KEY.")
                        return []
                    elif response.status == 429:
                        logger.error("Scopus API error 429: rate/quota limit reached.")
                        return []
                    else:
                        body = (await response.text())[:200]
                        logger.error(f"Scopus API error: {response.status} - {body}")
                        return []
        except Exception as e:
            logger.error(f"Scopus API request failed: {e}")
            return []

    def _parse_scopus_response(self, data: Dict) -> List[PaperMetadata]:
        """Parse Scopus Search API response"""
        papers = []
        entries = data.get("search-results", {}).get("entry", [])

        for item in entries:
            # An empty result set is a single entry carrying an error field.
            if item.get("error"):
                logger.info(f"Scopus: {item.get('error')}")
                continue
            try:
                authors = []
                if item.get("dc:creator"):
                    authors = [item["dc:creator"]]

                year = None
                cover_date = item.get("prism:coverDate")
                if cover_date:
                    try:
                        year = int(str(cover_date)[:4])
                    except (ValueError, TypeError):
                        year = None

                doi = item.get("prism:doi")
                url = None
                for link in item.get("link", []):
                    if link.get("@ref") == "scopus":
                        url = link.get("@href")
                        break
                if url is None:
                    url = f"https://doi.org/{doi}" if doi else item.get("prism:url")

                journal = item.get("prism:publicationName")
                subtype = item.get("subtypeDescription")
                if journal and subtype and subtype not in ("Article",):
                    journal = f"{journal} ({subtype})"

                papers.append(PaperMetadata(
                    paper_id=doi or item.get("eid", "") or item.get("dc:identifier", ""),
                    title=item.get("dc:title", ""),
                    authors=authors[:10],
                    abstract=(item.get("dc:description") or "").strip()[:2000],
                    year=year,
                    journal=journal,
                    doi=doi,
                    url=url,
                    pdf_url=None,
                    citation_count=int(item.get("citedby-count", 0) or 0),
                    source_api="scopus",
                    raw_data=item
                ))
            except Exception as e:
                logger.warning(f"Failed to parse Scopus entry: {e}")
                continue

        return papers
