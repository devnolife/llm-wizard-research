"""OpenAlex API client."""

import os
from typing import Dict, List, Optional

from loguru import logger

from . import http_cache
from .base import PaperMetadata


class OpenAlexAPI:
    """Synchronous OpenAlex API client - No API key required."""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, email: Optional[str] = None, cache_dir=None,
                 min_interval: float = 1.0, max_retries: int = 4):
        """
        Initialize OpenAlex API.

        Args:
            email: Optional email for the OpenAlex polite pool
            cache_dir: Optional cache directory for API responses
            min_interval: Minimum seconds between requests (raise this when the
                shared IP is being rate-limited / 429'd without a polite-pool email)
            max_retries: Retry budget on 429/5xx before giving up (lower = fail
                fast when the IP is hard-throttled; the caller then treats the gap
                conservatively as still "open").
        """
        self.email = email or os.getenv("CROSSREF_EMAIL") or os.getenv("UNPAYWALL_EMAIL")
        self.cache_dir = cache_dir
        self.min_interval = min_interval
        self.max_retries = max_retries

    def search_recent(
        self,
        keywords: str,
        from_date: str = "2024-01-01",
        max_results: int = 5,
    ) -> List[PaperMetadata]:
        """Search recent OpenAlex works."""
        params = {
            "search": keywords,
            "filter": f"from_publication_date:{from_date}",
            "per-page": max_results,
        }
        if self.email:
            params["mailto"] = self.email

        data = http_cache.get_json(
            self.BASE_URL, params=params, cache_dir=self.cache_dir,
            min_interval=self.min_interval, max_retries=self.max_retries,
        )
        if not data:
            return []

        papers = []
        for work in data.get("results", []):
            try:
                papers.append(self._parse_work(work))
            except Exception as exc:
                logger.warning(f"Failed to parse OpenAlex entry: {exc}")
        return papers

    def _parse_work(self, work: Dict) -> PaperMetadata:
        """Parse a single OpenAlex work."""
        authors = []
        for authorship in work.get("authorships") or []:
            author = (authorship or {}).get("author") or {}
            display_name = author.get("display_name")
            if display_name:
                authors.append(display_name)

        doi = work.get("doi")
        if doi:
            doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

        host_venue = work.get("host_venue") or {}
        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        journal = host_venue.get("display_name") or source.get("display_name")

        title = work.get("title") or work.get("display_name") or ""
        url = work.get("id")

        return PaperMetadata(
            paper_id=doi or url or "",
            title=title,
            authors=authors,
            abstract=self._reconstruct_abstract(work.get("abstract_inverted_index")),
            year=work.get("publication_year"),
            journal=journal,
            doi=doi,
            url=url,
            pdf_url=primary_location.get("pdf_url"),
            citation_count=work.get("cited_by_count", 0) or 0,
            source_api="openalex",
            raw_data=work,
        )

    def _reconstruct_abstract(self, inverted_index: Optional[Dict]) -> str:
        """Reconstruct an abstract from OpenAlex's inverted index."""
        if not inverted_index:
            return ""

        words_by_position = {}
        for word, positions in inverted_index.items():
            for position in positions or []:
                words_by_position[position] = word

        return " ".join(
            word for _, word in sorted(words_by_position.items(), key=lambda item: item[0])
        )


if __name__ == "__main__":
    for paper in OpenAlexAPI().search_recent(
        "digital forensics image tampering detection", max_results=3
    ):
        print(paper.year, paper.title)
