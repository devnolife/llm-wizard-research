"""Unpaywall API client — resolves legal open-access PDF locations by DOI."""

import os
from typing import Any, Dict, Optional

import aiohttp
from loguru import logger


class UnpaywallAPI:
    """Unpaywall REST client (free; only requires a contact email).

    Given a DOI, returns the best legal open-access PDF location when one
    exists (publisher OA or an author-deposited repository copy).
    """

    BASE_URL = "https://api.unpaywall.org/v2"

    def __init__(self, email: Optional[str] = None):
        self.email = (
            email
            or os.getenv("UNPAYWALL_EMAIL")
            or os.getenv("CROSSREF_EMAIL")
            or "wizard-research@example.com"
        )
        self.headers = {"User-Agent": "WizardResearch/1.0"}

    async def lookup(self, doi: str) -> Optional[Dict[str, Any]]:
        """Return the raw Unpaywall record for a DOI, or None on failure."""
        doi = (doi or "").strip().removeprefix("https://doi.org/").removeprefix("doi:")
        if not doi:
            return None
        url = f"{self.BASE_URL}/{doi}"
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(headers=self.headers, timeout=timeout) as session:
                async with session.get(url, params={"email": self.email}) as response:
                    if response.status == 200:
                        return await response.json()
                    if response.status == 404:
                        logger.info(f"Unpaywall: DOI not found: {doi}")
                    else:
                        logger.error(f"Unpaywall API error {response.status} for {doi}")
                    return None
        except Exception as e:
            logger.error(f"Unpaywall request failed for {doi}: {e}")
            return None

    async def resolve_pdf(self, doi: str) -> Optional[str]:
        """Return the best open-access PDF URL for a DOI, or None."""
        record = await self.lookup(doi)
        if not record or not record.get("is_oa"):
            return None
        return self.extract_pdf_url(record)

    @staticmethod
    def extract_pdf_url(record: Dict[str, Any]) -> Optional[str]:
        """Pick the best PDF URL from an Unpaywall record."""
        locations = []
        if isinstance(record.get("best_oa_location"), dict):
            locations.append(record["best_oa_location"])
        for loc in record.get("oa_locations") or []:
            if isinstance(loc, dict):
                locations.append(loc)
        for loc in locations:
            pdf = loc.get("url_for_pdf") or None
            if pdf:
                return pdf
        # Some records only expose a landing/page URL that is itself a PDF.
        for loc in locations:
            url = loc.get("url") or ""
            if url.lower().endswith(".pdf"):
                return url
        return None
