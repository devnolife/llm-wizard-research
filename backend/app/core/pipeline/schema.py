"""Data model for the upgraded pipeline (TAHAP 1 schema D).

``PipelineChunk`` is the new per-chunk record. It is a superset of the legacy
``{source,title,year,section,chunk_index,chars,text}`` shape and adds the fields
required by the spec plus a stable ``chunk_id`` so TAHAP 2 gaps can cite exact
evidence chunks.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Canonical section vocabulary (spec bagian D / masalah 5).
CANONICAL_SECTIONS = [
    "abstract",
    "introduction",
    "related_work",
    "methods",
    "results",
    "discussion",
    "conclusion",
    "references",
    "other",
]

# Allowed extraction-quality tiers (spec bagian C / masalah 10).
EXTRACTION_QUALITY = ("good", "fair", "poor")


@dataclass
class PaperMeta:
    """Paper-level metadata resolved once per document."""

    source: str
    doi: Optional[str] = None
    paper_title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    language: Optional[str] = None
    abstract: Optional[str] = None
    extraction_quality: str = "good"
    # Provenance of the metadata: "grobid" | "crossref" | "heuristic".
    metadata_source: str = "heuristic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "doi": self.doi,
            "paper_title": self.paper_title,
            "authors": list(self.authors or []),
            "year": self.year,
            "language": self.language,
            "abstract": self.abstract,
            "extraction_quality": self.extraction_quality,
            "metadata_source": self.metadata_source,
        }


@dataclass
class PipelineChunk:
    """A single emitted chunk (one JSONL line, ``record="chunk"``)."""

    source: str
    chunk_index: int
    text: str
    token_count: int
    section_raw: Optional[str] = None
    section_normalized: str = "other"
    is_reference: bool = False
    page_start: Optional[int] = None
    # Paper-level fields duplicated onto every chunk for self-contained records.
    doi: Optional[str] = None
    paper_title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    language: Optional[str] = None
    extraction_quality: str = "good"
    chunk_id: str = ""

    def make_chunk_id(self) -> str:
        """Stable id from source + index (+ short text hash) for evidence links."""
        h = hashlib.md5(
            f"{self.source}|{self.chunk_index}|{self.text[:64]}".encode("utf-8")
        ).hexdigest()[:8]
        return f"{self.source}::{self.chunk_index}::{h}"

    def __post_init__(self):
        if not self.chunk_id:
            self.chunk_id = self.make_chunk_id()

    def to_json_record(self) -> Dict[str, Any]:
        """Full new-schema record (used by the CLI JSONL writer)."""
        return {
            "record": "chunk",
            "source": self.source,
            "doi": self.doi,
            "paper_title": self.paper_title,
            "authors": list(self.authors or []),
            "year": self.year,
            "language": self.language,
            "section_raw": self.section_raw,
            "section_normalized": self.section_normalized,
            "is_reference": self.is_reference,
            "page_start": self.page_start,
            "chunk_index": self.chunk_index,
            "chunk_id": self.chunk_id,
            "token_count": self.token_count,
            "chars": len(self.text or ""),
            "text": self.text,
            "extraction_quality": self.extraction_quality,
        }

    def to_vector_metadata(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """Flat metadata for Chroma (lists become comma strings downstream)."""
        meta: Dict[str, Any] = {
            "source": self.source,
            "doi": self.doi,
            "paper_title": self.paper_title,
            "title": self.paper_title,  # keep legacy key populated
            "authors": list(self.authors or []),
            "year": self.year,
            "language": self.language,
            "section_raw": self.section_raw,
            "section": self.section_raw,  # keep legacy key populated
            "section_normalized": self.section_normalized,
            "is_reference": self.is_reference,
            "page_start": self.page_start,
            "chunk_index": self.chunk_index,
            "chunk_id": self.chunk_id,
            "token_count": self.token_count,
            "extraction_quality": self.extraction_quality,
        }
        if job_id is not None:
            meta["analysis_job_id"] = job_id
        # Drop None values — Chroma stores simple scalars only.
        return {k: v for k, v in meta.items() if v is not None}
