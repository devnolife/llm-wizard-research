"""
External Paper API Integration
Supports multiple academic paper APIs: arXiv, Semantic Scholar, PubMed,
CrossRef, CORE, Europe PMC, and ScienceDirect.

Split into per-provider modules; this package re-exports the public API so
`from app.services.paper_apis import AggregatedPaperAPI` keeps working.
"""

from .base import PaperMetadata, _strip_markup
from .arxiv import ArXivAPI
from .semantic_scholar import SemanticScholarAPI
from .crossref import CrossRefAPI
from .pubmed import PubMedAPI
from .core import CoreAPI
from .europe_pmc import EuropePMCAPI
from .sciencedirect import ScienceDirectAPI
from .aggregator import AggregatedPaperAPI

__all__ = [
    "PaperMetadata",
    "_strip_markup",
    "ArXivAPI",
    "SemanticScholarAPI",
    "CrossRefAPI",
    "PubMedAPI",
    "CoreAPI",
    "EuropePMCAPI",
    "ScienceDirectAPI",
    "AggregatedPaperAPI",
]
