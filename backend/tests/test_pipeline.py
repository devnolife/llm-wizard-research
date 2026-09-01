"""Unit tests for the upgraded chunking pipeline (TAHAP 1).

Operate directly on text/synthetic input (no PDF, no network) so they are fast
and deterministic, mirroring the style of test_section_chunking.py.
"""

import pytest

from app.core.pipeline.text_cleaning import (
    assess_quality,
    dehyphenate,
    find_repeated_lines,
    is_noise_line,
    normalize_unicode,
    reflow_paragraphs,
)
from app.core.pipeline.section_normalizer import (
    classify_reference,
    looks_like_references,
    normalize_section,
)
from app.core.pipeline.token_chunker import (
    chunk_document,
    count_tokens,
    split_sentences,
)
from app.core.pipeline.dedup import deduplicate_chunks
from app.core.pipeline.schema import PaperMeta, PipelineChunk
from app.core.pipeline.metadata_resolver import (
    extract_doi,
    extract_doi_candidates,
    valid_year,
)


class TestTextCleaning:
    def test_ligature_repair(self):
        assert "specifically" in normalize_unicode("speciﬁcally")
        assert "verification" in normalize_unicode("veriﬁcation")

    def test_dehyphenation_joins_split_word(self):
        assert dehyphenate("investiga-\ntive") == "investigative"

    def test_dehyphenation_keeps_compound(self):
        # A common connector tail signals a genuine compound.
        assert dehyphenate("state-\nof-the-art") == "state-of-the-art"

    def test_non_latin_preserved(self):
        # masalah 10: Cyrillic must survive cleaning (no ASCII strip).
        cyr = "криміналістична техніка"
        assert cyr == normalize_unicode(cyr)

    def test_repeated_header_detected_and_stripped(self):
        pages = [f"Journal of X\nBody content number {i} here." for i in range(4)]
        repeated = find_repeated_lines(pages)
        assert any("journal of x" == r for r in repeated)
        assert is_noise_line("Journal of X", repeated)

    def test_page_number_and_toc_are_noise(self):
        assert is_noise_line("12", set())
        assert is_noise_line("Introduction .......... 5", set())

    def test_table_row_is_noise(self):
        assert is_noise_line("5(4.1) 10(8.3) 23(19.0) 3.73 1.031", set())
        assert not is_noise_line("This is a normal prose sentence here.", set())

    def test_reflow_reconnects_sentence_across_break(self):
        # A sentence split by a blank line (column/page break) is rejoined.
        out = reflow_paragraphs("the evidence\n\ncollected is admissible.")
        assert "the evidence collected is admissible." in out

    def test_quality_poor_on_garbled(self):
        assert assess_quality("\ufffd\ufffd\ufffd 1234 \ufffd\ufffd") == "poor"
        assert assess_quality("A perfectly normal English sentence here.") == "good"


class TestSectionNormalizer:
    @pytest.mark.parametrize("raw,expected", [
        ("3.1 Results and Discussion", "discussion"),
        ("IV. METHODOLOGY", "methods"),
        ("REFERENCES", "references"),
        ("Tinjauan Pustaka", "related_work"),
        ("2 Pendahuluan", "introduction"),
        ("Future Work", "conclusion"),
        ("ABSTRACT", "abstract"),
        ("NATURE &", "other"),
        ("P-ISSN: 2356-4962", "other"),
    ])
    def test_normalize_section(self, raw, expected):
        assert normalize_section(raw) == expected

    def test_reference_detection(self):
        refs = "[1] A. Smith et al., Foo, 2019. doi:10.1000/x pp. 12-20\n[2] B. Lee (2020) Bar, vol. 3"
        assert looks_like_references(refs)
        assert classify_reference("other", refs)

    def test_prose_not_reference(self):
        prose = "Digital forensics is the process of recovering evidence from devices."
        assert not classify_reference("introduction", prose)


class TestTokenChunker:
    def _long_section(self, n=40):
        return " ".join(
            f"This is sentence number {i} describing the methodology in detail."
            for i in range(n)
        )

    def test_no_midsentence_cuts(self):
        meta = PaperMeta(source="p.pdf")
        sections = [("1 Introduction", "introduction", self._long_section(), 1)]
        chunks = chunk_document(sections, meta)
        assert len(chunks) >= 2
        for c in chunks:
            assert c.text.rstrip()[-1] in ".!?", c.text[-40:]

    def test_token_bounds(self):
        meta = PaperMeta(source="p.pdf")
        sections = [("1 Introduction", "introduction", self._long_section(60), 1)]
        chunks = chunk_document(sections, meta)
        assert all(c.token_count <= 512 for c in chunks)
        # Most chunks are in the target band.
        assert any(256 <= c.token_count <= 512 for c in chunks)

    def test_consecutive_chunks_overlap(self):
        meta = PaperMeta(source="p.pdf")
        sections = [("1 Introduction", "introduction", self._long_section(), 1)]
        chunks = chunk_document(sections, meta)
        for a, b in zip(chunks, chunks[1:]):
            first_sentence_b = split_sentences(b.text)[0]
            assert first_sentence_b in a.text  # overlap present

    def test_never_crosses_section(self):
        meta = PaperMeta(source="p.pdf")
        sections = [
            ("1 Introduction", "introduction", self._long_section(20), 1),
            ("5 Conclusion", "conclusion", self._long_section(20), 8),
        ]
        chunks = chunk_document(sections, meta)
        for c in chunks:
            # No chunk mixes both sections.
            assert c.section_normalized in ("introduction", "conclusion")

    def test_section_label_used_as_given(self):
        meta = PaperMeta(source="p.pdf")
        # Even a "Study Population" raw head keeps the resolved (inherited) label.
        sections = [("Study Population", "methods", self._long_section(10), 3)]
        chunks = chunk_document(sections, meta)
        assert all(c.section_normalized == "methods" for c in chunks)


class TestDedup:
    def test_removes_identical(self):
        meta = PaperMeta(source="p.pdf")
        c = PipelineChunk(source="p.pdf", chunk_index=0, text="Hello world.", token_count=3)
        c2 = PipelineChunk(source="p.pdf", chunk_index=1, text="Hello   world.", token_count=3)
        c3 = PipelineChunk(source="p.pdf", chunk_index=2, text="Different text here.", token_count=3)
        out = deduplicate_chunks([c, c2, c3])
        assert len(out) == 2


class TestMetadata:
    def test_valid_year(self):
        assert valid_year(2022)
        assert valid_year(1999)
        assert not valid_year(1980)
        assert not valid_year(None)

    def test_doi_extraction(self):
        text = "See https://doi.org/10.1234/abc.def for details."
        assert extract_doi(text) == "10.1234/abc.def"

    def test_doi_candidates_prefer_article_over_issn(self):
        text = "journal 10.37284/2707-5354 article 10.37284/eajit.5.1.1015 end"
        cands = extract_doi_candidates(text)
        assert cands[0] == "10.37284/eajit.5.1.1015"


class TestSchema:
    def test_chunk_record_has_new_fields(self):
        c = PipelineChunk(
            source="x.pdf", chunk_index=0, text="hello", token_count=1,
            section_raw="1 Introduction", section_normalized="introduction",
            paper_title="T", year=2022, doi="10.1/x", authors=["A"], language="en",
        )
        rec = c.to_json_record()
        for key in ("doi", "paper_title", "authors", "year", "language",
                    "section_raw", "section_normalized", "is_reference",
                    "page_start", "token_count", "extraction_quality", "chunk_id"):
            assert key in rec

    def test_chunk_id_stable(self):
        c = PipelineChunk(source="x.pdf", chunk_index=0, text="hello world", token_count=2)
        assert c.chunk_id == c.make_chunk_id()
