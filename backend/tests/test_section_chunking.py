"""
Unit tests for section-aware chunking in DocumentProcessor — verifies header
detection and that chunks are tagged with their source section, without needing
a real PDF (operates directly on text).
"""

from app.utils.document_processor import DocumentProcessor


SAMPLE_PAPER = """Title of the Paper

Abstract
This paper proposes a novel method for testing. We summarize our contributions.

1 Introduction
Research in this area has grown rapidly. We motivate the problem and outline
our approach in the following sections of the paper.

2 Methods
We describe our methodology in detail. The approach uses a pipeline of steps
that process the input data and produce the output predictions for evaluation.

3 Results
Our experiments show strong performance. The accuracy reached high values on
the benchmark datasets used throughout this study and the related work.

4 Conclusion
We conclude that the method is effective. Future work will extend it further
to additional domains and larger datasets for broader validation overall.
"""


class TestSectionChunking:
    def test_sections_detected_and_tagged(self):
        dp = DocumentProcessor(chunk_size=200, chunk_overlap=20, min_chunk_length=20,
                               chunk_strategy="sections")
        sections = dp._detect_sections(SAMPLE_PAPER)
        titles = [t for t, _ in sections]
        assert any("Introduction" in t for t in titles)
        assert any("Methods" in t for t in titles)
        assert any("Conclusion" in t for t in titles)

    def test_chunks_carry_section_metadata(self):
        dp = DocumentProcessor(chunk_size=200, chunk_overlap=20, min_chunk_length=20,
                               chunk_strategy="sections")
        chunks = dp._chunk_sections(SAMPLE_PAPER, "doc1", {"source": "x.pdf"})
        assert chunks, "expected section chunks"
        # Every chunk is tagged with a section.
        assert all(c.metadata.get("section") for c in chunks)
        sections_seen = {c.metadata["section"] for c in chunks}
        assert any("Conclusion" in s for s in sections_seen)
        # Original metadata is preserved.
        assert all(c.metadata.get("source") == "x.pdf" for c in chunks)

    def test_no_sections_returns_empty_for_fallback(self):
        """Free text with no headers → empty list so process_pdf can fall back."""
        dp = DocumentProcessor(chunk_strategy="sections")
        flat = "just a single run-on paragraph with no headings at all " * 20
        assert dp._detect_sections(flat) == []

    def test_fixed_strategy_has_no_section_tags(self):
        dp = DocumentProcessor(chunk_size=200, chunk_overlap=20, min_chunk_length=20,
                               chunk_strategy="fixed")
        chunks = dp._chunk_text(SAMPLE_PAPER, "doc1", {"source": "x.pdf"})
        assert chunks
        assert all("section" not in c.metadata for c in chunks)
