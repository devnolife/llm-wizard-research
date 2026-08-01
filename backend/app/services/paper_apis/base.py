"""Shared primitives for the paper API clients."""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _strip_markup(text: str) -> str:
    """Remove JATS/HTML tags (e.g. CrossRef's <jats:p>) and collapse whitespace."""
    if not text:
        return ""
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
