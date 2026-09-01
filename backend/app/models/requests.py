"""
Request models for API endpoints
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000, description="Research query")
    top_k: Optional[int] = Field(5, ge=1, le=100, description="Number of results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")


class RecommendationRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000, description="Research query")
    max_results: Optional[int] = Field(10, ge=1, le=50, description="Maximum recommendations")
    strategy: Optional[str] = Field("hybrid", description="Recommendation strategy")
    user_context: Optional[Dict[str, Any]] = Field(None, description="User context")


class GapDetectionRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=4000, description="Research topic")
    depth: Optional[str] = Field("standard", description="Analysis depth")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000, description="Chat message")
    use_history: Optional[bool] = Field(True, description="Use conversation history")
    conversation_id: Optional[str] = Field(None, max_length=128, description="Conversation session ID")


class PaperSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Search query for papers")
    max_results: Optional[int] = Field(10, ge=1, le=50, description="Maximum results per source")
    sources: Optional[List[str]] = Field(None, description="API sources to search")
    deduplicate: Optional[bool] = Field(True, description="Remove duplicate papers")
    year_from: Optional[int] = Field(None, description="Filter papers from this year onwards")
    year_to: Optional[int] = Field(None, description="Filter papers up to this year")
    embedding_model: Optional[str] = Field("all-MiniLM-L6-v2", description="Embedding model")


class PaperToDownload(BaseModel):
    title: str = Field(..., min_length=1, max_length=500, description="Paper title (used for filename)")
    doi: Optional[str] = Field(None, max_length=200, description="DOI for Unpaywall OA resolution")
    pdf_url: Optional[str] = Field(None, max_length=2000, description="Direct PDF URL if already known")
    source_api: Optional[str] = Field(None, max_length=50, description="Origin source API")


class DownloadAnalyzeRequest(BaseModel):
    papers: List[PaperToDownload] = Field(..., min_length=1, max_length=15, description="Papers to download and analyze")


class IdeaToQueryRequest(BaseModel):
    idea: str = Field(..., min_length=10, max_length=2000, description="Research idea (Indonesian or English) to convert into an academic search query")


class MarkedPapersRequest(BaseModel):
    papers: List[Dict[str, Any]] = Field(..., description="User-marked papers to analyze (title, abstract, authors, year)")
    query: Optional[str] = Field(None, description="Original search query/topic")
