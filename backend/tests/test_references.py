"""Parser daftar pustaka (pipeline.references) — pemisahan entri & kunci pencocokan."""

from app.core.pipeline.references import (
    ReferenceEntry,
    content_words,
    extract_references,
    parse_reference,
    reference_text,
    split_reference_entries,
)

BRACKETED = """
References
[1] A. Vaswani, N. Shazeer, and I. Polosukhin, "Attention is all you need," in Advances in
Neural Information Processing Systems, 2017, pp. 5998-6008.
[2] J. Devlin, M. Chang, K. Lee, and K. Toutanova, "BERT: Pre-training of deep bidirectional
transformers for language understanding," in NAACL, 2019. doi: 10.18653/v1/N19-1423
[3] K. He, X. Zhang, S. Ren, and J. Sun, "Deep residual learning for image recognition," in
CVPR, 2016, pp. 770-778.
"""

NUMBERED = """DAFTAR PUSTAKA
1. Casey, E. (2011). Digital Evidence and Computer Crime: Forensic Science, Computers and the
   Internet. Academic Press.
2. Garfinkel, S. L. (2010). Digital forensics research: The next 10 years. Digital Investigation,
   7, S64-S73. https://doi.org/10.1016/j.diin.2010.05.009
3. Quick, D., & Choo, K.-K. R. (2014). Impacts of increasing volume of digital forensic data.
   Digital Investigation, 11(4), 273-294.
"""

AUTHOR_YEAR_BLOB = (
    "Casey, E. (2011). Digital Evidence and Computer Crime: Forensic Science, Computers and the "
    "Internet. Academic Press. Garfinkel, S. L. (2010). Digital forensics research: The next 10 "
    "years. Digital Investigation, 7, S64-S73. Quick, D., & Choo, K.-K. R. (2014). Impacts of "
    "increasing volume of digital forensic data. Digital Investigation, 11(4), 273-294. "
    "Rogers, M. K. (2015). Psychological profiling as an investigative tool for digital forensics. "
    "In Digital Forensics (pp. 45-58). Springer. Vaswani, A., Shazeer, N. (2017). Attention is all "
    "you need. Advances in Neural Information Processing Systems, 30, 5998-6008."
)


class TestSplitEntries:
    def test_bracketed_markers_split_even_when_lines_are_joined(self):
        joined = " ".join(BRACKETED.split())
        entries = split_reference_entries(joined)
        assert len(entries) == 3
        assert entries[0].startswith("[1] A. Vaswani") and entries[2].startswith("[3] K. He")

    def test_numbered_lines_and_indonesian_heading(self):
        entries = split_reference_entries(NUMBERED)
        assert len(entries) == 3
        assert entries[1].startswith("2. Garfinkel")
        assert "DAFTAR PUSTAKA" not in entries[0]

    def test_author_year_blob_is_split_at_surname_boundaries(self):
        entries = split_reference_entries(AUTHOR_YEAR_BLOB)
        assert len(entries) == 5
        assert entries[0].startswith("Casey, E. (2011)")
        assert entries[-1].startswith("Vaswani, A.")

    def test_short_fragments_and_duplicates_are_dropped(self):
        text = "[1] Short.\n[2] A. Author, \"A proper reference title here,\" 2020.\n[3] a. author, " \
               "\"A PROPER REFERENCE TITLE HERE,\" 2020.\n[4] B. Other, \"Another sufficiently long entry,\" 2021."
        entries = split_reference_entries(text)
        assert len(entries) == 2
        assert split_reference_entries("") == []


class TestParseEntry:
    def test_doi_becomes_the_key(self):
        entry = parse_reference(
            '[2] J. Devlin et al., "BERT: Pre-training of deep bidirectional transformers," '
            "in NAACL, 2019. doi: 10.18653/v1/N19-1423")
        assert entry.doi == "10.18653/v1/n19-1423" and entry.key == entry.doi
        assert entry.year == 2019 and entry.first_author == "devlin", "inisial IEEE dilewati"
        assert entry.to_dict()["key"] == entry.key
        assert ReferenceEntry.from_dict(entry.to_dict()) == entry

    def test_author_year_key_without_doi(self):
        entry = parse_reference(
            "Garfinkel, S. L. (2010). Digital forensics research: The next 10 years. "
            "Digital Investigation, 7, S64-S73.")
        assert entry.doi is None and entry.year == 2010 and entry.first_author == "garfinkel"
        assert entry.title_guess.startswith("Digital forensics research")
        assert entry.key == "garfinkel|2010|digital forensics research next years"

    def test_same_work_cited_in_two_styles_shares_a_key(self):
        a = parse_reference("Garfinkel, S. L. (2010). Digital forensics research: The next 10 years. "
                            "Digital Investigation, 7, S64-S73.")
        b = parse_reference("2. Garfinkel, S. (2010). Digital forensics research: the next 10 years. "
                            "Digital Investigation 7, S64–S73.")
        assert a.key == b.key

    def test_parenthesised_year_wins_over_page_like_numbers(self):
        entry = parse_reference("Smith, J. (2019). Title words appear here clearly. Journal, 2001, 1998-2005.")
        assert entry.year == 2019

    def test_unparseable_entry_still_gets_a_raw_key(self):
        entry = parse_reference("??? --- 1234567 ---- ..... ***** ######## $$$$ &&&&")
        assert entry.key.startswith("raw|") and entry.first_author == ""

    def test_content_words_drop_stopwords_and_short_tokens(self):
        assert content_words("The Impacts of Increasing Volume of Digital Forensic Data") == [
            "impacts", "increasing", "volume", "digital", "forensic", "data"]


class TestExtractFromChunks:
    def _chunk(self, text, section="other", is_reference=False):
        return {"text": text, "section_normalized": section, "is_reference": is_reference}

    def test_reference_chunks_are_preferred(self):
        chunks = [self._chunk("Pendahuluan panjang tentang forensik digital." * 5, "introduction"),
                  self._chunk(NUMBERED, "references", True)]
        entries = extract_references(chunks, "teks penuh yang tidak dipakai")
        assert len(entries) == 3 and entries[0].first_author == "casey"

    def test_tail_fallback_from_heading_when_no_chunk_is_flagged(self):
        body = ("Bagian hasil dan pembahasan. " * 40) + "\n\nReferences\n" + " ".join(BRACKETED.split()[1:])
        entries = extract_references([self._chunk("Bagian hasil", "results")], body)
        assert len(entries) == 3

    def test_tail_without_citation_shape_yields_nothing(self):
        prose = "Kalimat pembahasan biasa tanpa tanda sitasi apa pun. " * 60
        assert reference_text([], prose) == ""
        assert extract_references([], prose) == []

    def test_object_chunks_with_metadata_are_accepted(self):
        class Chunk:
            def __init__(self, content, meta):
                self.content, self.metadata = content, meta
        chunks = [Chunk(NUMBERED, {"section_normalized": "references", "is_reference": True})]
        assert len(extract_references(chunks)) == 3
