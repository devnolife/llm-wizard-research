"""
Unit tests for AggregatedPaperAPI relevance ordering + markup stripping —
ensures cross-source results are ranked by query relevance (not source order)
and that CrossRef JATS/HTML is cleaned. No network calls.
"""

from app.services.paper_apis import AggregatedPaperAPI, PaperMetadata, _strip_markup


def _paper(title, abstract="", doi=None, cites=0):
    return PaperMetadata(
        paper_id=doi or title, title=title, authors=[], abstract=abstract,
        year=2020, journal=None, doi=doi, url=None, pdf_url=None,
        citation_count=cites,
    )


class TestStripMarkup:
    def test_removes_jats(self):
        assert _strip_markup("<jats:p>Algoritma <jats:italic>Genetika</jats:italic></jats:p>") == "Algoritma Genetika"

    def test_collapses_whitespace(self):
        assert _strip_markup("a\n\n  b   c") == "a b c"

    def test_empty(self):
        assert _strip_markup("") == ""
        assert _strip_markup(None) == ""


class TestRelevanceOrdering:
    def test_query_relevant_titles_rank_first(self):
        api = AggregatedPaperAPI()
        # arXiv listed first (source order) but irrelevant; crossref relevant.
        results = {
            "arxiv": [_paper("Levensthein String Archival System"),
                      _paper("NAMD Cluster Molecular Simulation")],
            "crossref": [_paper("Penjadwalan Mata Pelajaran dengan Algoritma Genetika"),
                         _paper("Algoritma Round Robin pada Penjadwalan CPU")],
        }
        ordered = api.deduplicate_papers(results, query="penjadwalan algoritma")
        # Both penjadwalan+algoritma titles must come before the arXiv ones.
        assert "Penjadwalan" in ordered[0].title
        assert "Penjadwalan" in ordered[1].title or "Penjadwalan" in ordered[0].title
        assert ordered[-1].title.startswith(("Levensthein", "NAMD"))

    def test_title_weighted_over_abstract(self):
        api = AggregatedPaperAPI()
        in_title = _paper("Penjadwalan Algoritma X")
        in_abstract = _paper("Some Other Topic", abstract="discusses penjadwalan algoritma briefly")
        score_t = api._relevance_score(in_title, "penjadwalan algoritma")
        score_a = api._relevance_score(in_abstract, "penjadwalan algoritma")
        assert score_t > score_a

    def test_no_query_preserves_source_order(self):
        api = AggregatedPaperAPI()
        results = {"arxiv": [_paper("A")], "crossref": [_paper("B")]}
        ordered = api.deduplicate_papers(results)  # no query
        assert [p.title for p in ordered] == ["A", "B"]

    def test_dedup_by_doi_still_works(self):
        api = AggregatedPaperAPI()
        results = {
            "arxiv": [_paper("Same Paper", doi="10.1/x")],
            "crossref": [_paper("Same Paper", doi="10.1/x")],
        }
        ordered = api.deduplicate_papers(results, query="paper")
        assert len(ordered) == 1
