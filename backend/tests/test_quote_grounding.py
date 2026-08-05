"""Tests for verbatim-quote grounding of gap indicators (Fase 1)."""

from app.core.gap_detection.quote_grounding import (
    QUOTE_MATCH_THRESHOLD,
    extract_supporting_quotes,
    fuzzy_contains,
    normalize_text,
    split_sentences,
    verify_quote_against_papers,
)

PAPERS = [
    {
        "content": (
            "Deep residual networks enable training of much deeper models. "
            "We show that residual connections mitigate the degradation problem in very deep networks. "
            "Batch normalization accelerates convergence significantly on ImageNet."
        ),
        "metadata": {"source": "resnet_paper.pdf", "title": "Deep Residual Learning"},
    },
    {
        "content": (
            "Dense connectivity patterns improve gradient flow between layers substantially. "
            "Our experiments demonstrate that dropout degrades accuracy in densely connected settings."
        ),
        "metadata": {"source": "densenet_paper.pdf", "title": "Densely Connected Networks"},
    },
]


class TestFuzzyContains:
    def test_exact_substring(self):
        assert fuzzy_contains("residual connections mitigate", PAPERS[0]["content"]) == 1.0

    def test_near_match_above_threshold(self):
        # Slight paraphrase with same char length profile
        quote = "residual connections mitigate the degradation problem in very deep network"
        assert fuzzy_contains(quote, PAPERS[0]["content"]) >= QUOTE_MATCH_THRESHOLD

    def test_unrelated_below_threshold(self):
        assert fuzzy_contains("quantum biology in marine ecosystems", PAPERS[0]["content"]) < 0.5

    def test_empty(self):
        assert fuzzy_contains("", "text") == 0.0
        assert normalize_text("  A  B ") == "a b"


class TestSplitSentences:
    def test_splits_and_filters_short(self):
        sents = split_sentences(PAPERS[0]["content"])
        assert len(sents) == 3
        assert all(len(s) >= 30 for s in sents)


class TestExtractSupportingQuotes:
    def test_finds_verbatim_sentence_per_paper(self):
        quotes = extract_supporting_quotes(["residual", "dropout"], PAPERS)
        assert 1 <= len(quotes) <= 2
        sources = {q["source_paper"] for q in quotes}
        assert sources <= {"resnet_paper.pdf", "densenet_paper.pdf"}
        for q in quotes:
            assert q["match_score"] == 1.0
            # verbatim by construction: quote must exist in some paper content
            assert any(q["quote"] in p["content"] for p in PAPERS)

    def test_one_quote_per_paper_max(self):
        quotes = extract_supporting_quotes(["networks"], PAPERS, max_quotes=5)
        sources = [q["source_paper"] for q in quotes]
        assert len(sources) == len(set(sources))

    def test_no_terms_no_quotes(self):
        assert extract_supporting_quotes([], PAPERS) == []
        assert extract_supporting_quotes(["zz"], PAPERS) == []  # <3 chars filtered


class TestVerifyQuoteAgainstPapers:
    def test_genuine_quote_verified(self):
        res = verify_quote_against_papers(
            "Batch normalization accelerates convergence significantly on ImageNet.", PAPERS
        )
        assert res["verified"] is True
        assert res["source_paper"] == "resnet_paper.pdf"
        assert res["match_score"] >= QUOTE_MATCH_THRESHOLD

    def test_hallucinated_quote_rejected(self):
        res = verify_quote_against_papers(
            "Transformers eliminate the need for convolutions entirely in vision tasks.", PAPERS
        )
        assert res["verified"] is False
        assert res["source_paper"] is None


class TestIndicatorCarriesQuotes:
    def test_gap_indicator_model_field(self):
        from app.core.gap_detection.analyzer import GapIndicator, GapIndicatorType

        ind = GapIndicator(
            indicator_type=GapIndicatorType.INCONSISTENCY,
            description="x vs y",
            confidence=0.7,
            related_papers=["a.pdf"],
            evidence=["e"],
            suggested_directions=[],
            supporting_quotes=[{"quote": "q", "source_paper": "a.pdf", "match_score": 1.0}],
        )
        model = ind.to_model()
        assert model.supporting_quotes[0]["quote"] == "q"
        assert ind.to_dict()["supporting_quotes"][0]["source_paper"] == "a.pdf"
