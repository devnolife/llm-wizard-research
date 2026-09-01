"""Structure-aware, token-aware PDF processing pipeline (TAHAP 1).

This package is the shared core used by BOTH the FastAPI ingestion path and the
reproducible CLI. It fixes the 10 measurable defects of the legacy
``DocumentProcessor`` fixed-window chunker:

  * metadata resolution (GROBID -> CrossRef -> heuristic) with validated year
  * Unicode/ligature repair + de-hyphenation + header/footer stripping
  * canonical section normalisation + reference detection
  * token-aware, sentence-safe, section-bounded chunking with consistent overlap
  * exact-duplicate removal
  * an emitted per-chunk schema rich enough for downstream gap mining
"""

from .schema import PaperMeta, PipelineChunk, CANONICAL_SECTIONS

__all__ = ["PaperMeta", "PipelineChunk", "CANONICAL_SECTIONS"]
