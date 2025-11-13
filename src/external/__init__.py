"""External API integrations package"""

from .paper_apis import (
    PaperMetadata,
    ArXivAPI,
    SemanticScholarAPI,
    CrossRefAPI,
    PubMedAPI,
    AggregatedPaperAPI
)

__all__ = [
    'PaperMetadata',
    'ArXivAPI',
    'SemanticScholarAPI',
    'CrossRefAPI',
    'PubMedAPI',
    'AggregatedPaperAPI'
]
