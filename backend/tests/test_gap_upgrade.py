"""Tests for the LeapSpace-grounded gap detection upgrade.

Covers the four new building blocks that were added alongside ``analyzer.py``:
evidence-support detection (indicator 4), calibration/abstention, the evidence
gap map, graph metrics, and novelty-based proposal ranking.

All tests run in the lexical fallback path (no embedding model is loaded) so the
suite stays fast and offline.
"""

import pytest

from app.core.gap_detection.calibration import (
    ABSTENTION_THRESHOLD,
    Calibrator,
    apply_temperature,
    area_under_risk_coverage,
    brier_score,
    build_provenance,
    expected_calibration_error,
    fit_temperature,
)
from app.core.gap_detection.analyzer import GapAnalyzer, aspect_terms
from app.core.gap_detection.coverage_map import build_coverage_matrix
from app.core.gap_detection.quote_grounding import extract_supporting_quotes
from app.core.gap_detection.graph_metrics import cluster_papers, compute_modularity
from app.core.gap_detection.support_gap import (
    UNSUPPORTED_RATIO_MIN,
    analyze_support,
    has_primary_evidence,
    is_secondary_source,
    support_confidence,
)
from app.core.recommendation.novelty import (
    _Backend,
    novelty_band,
    priority_label,
    rank_proposals,
    score_proposal,
)


def _ref(paper):
    return paper.get("source") or paper.get("title") or ""


REVIEW_CORPUS = [
    {
        "source": f"review_{i}.pdf",
        "title": f"A survey of forensic triage practice {i}",
        "content": (
            "Prior work has widely reported that automated triage improves "
            "investigator throughput in digital forensics. It is generally "
            "accepted that chain of custody documentation reduces evidence "
            "disputes. Several authors argue that mobile acquisition tools are "
            "more reliable than disk imaging."
        ),
    }
    for i in range(4)
]

PRIMARY_PAPER = {
    "source": "primary_experiment.pdf",
    "title": "An experimental evaluation of forensic triage throughput",
    "content": (
        "We conducted an experiment with 42 participants (n=42) across three "
        "law-enforcement units. Our results show that automated triage improves "
        "investigator throughput by 31 percent. The dataset and ablation study "
        "confirm that chain of custody documentation reduces evidence disputes."
    ),
}


class TestSupportGap:
    def test_primary_evidence_and_secondary_detection(self):
        assert has_primary_evidence("We conducted an experiment with n=42 participants.")
        assert not has_primary_evidence("It is generally accepted that triage helps.")
        assert is_secondary_source(REVIEW_CORPUS[0])
        assert not is_secondary_source(PRIMARY_PAPER)

    def test_review_only_corpus_is_flagged_unsupported(self):
        report = analyze_support(REVIEW_CORPUS, _ref)
        assert report.total_claims > 0
        assert report.unsupported_ratio >= UNSUPPORTED_RATIO_MIN
        assert 0.0 < support_confidence(report) <= 0.92

    def test_primary_evidence_suppresses_the_indicator(self):
        report = analyze_support(REVIEW_CORPUS + [PRIMARY_PAPER], _ref)
        with_primary = report.unsupported_ratio
        review_only = analyze_support(REVIEW_CORPUS, _ref).unsupported_ratio
        assert with_primary < review_only

    def test_single_paper_corpus_returns_empty_report(self):
        report = analyze_support(REVIEW_CORPUS[:1], _ref)
        assert report.total_claims == 0
        assert support_confidence(report) == 0.0


class TestCalibration:
    def test_ece_and_brier_penalise_overconfidence(self):
        confidences = [0.95, 0.9, 0.92, 0.88]
        labels = [0, 0, 0, 0]
        assert expected_calibration_error(confidences, labels) > 0.5
        assert brier_score(confidences, labels) > 0.5

    def test_perfect_calibration_scores_near_zero(self):
        confidences = [0.95, 0.9, 0.92, 0.88]
        labels = [1, 1, 1, 1]
        assert expected_calibration_error(confidences, labels) < 0.15
        assert brier_score(confidences, labels) < 0.05

    def test_temperature_scaling_moves_confidence_toward_truth(self):
        confidences = [0.95, 0.9, 0.92, 0.88, 0.93, 0.91]
        labels = [0, 0, 1, 0, 0, 0]
        temperature = fit_temperature(confidences, labels)
        assert temperature > 1.0
        assert apply_temperature(0.95, temperature) < 0.95

    def test_aurc_is_bounded(self):
        aurc = area_under_risk_coverage([0.9, 0.8, 0.4, 0.2], [1, 1, 0, 0])
        assert 0.0 <= aurc <= 1.0

    def test_unfitted_calibrator_is_identity(self):
        calibrator = Calibrator()
        result = calibrator.calibrate(0.8, rule_verdict="PASS")
        assert result["calibrator_fitted"] is False
        assert result["temperature"] == pytest.approx(1.0)

    def test_reject_verdict_forces_review(self):
        result = Calibrator().calibrate(0.9, rule_verdict="REJECT")
        assert result["needs_review"] is True
        assert result["calibrated_confidence"] == pytest.approx(0.0)

    def test_low_confidence_triggers_abstention(self):
        result = Calibrator().calibrate(ABSTENTION_THRESHOLD - 0.1, rule_verdict="PASS")
        assert result["needs_review"] is True
        assert result["abstention_reasons"]

    def test_provenance_flags_missing_quotes(self):
        chain = build_provenance(
            claim="Aspek X tidak dibahas oleh satu pun jurnal.",
            cited_records=["a.pdf", "b.pdf"],
            retrieved_passages=[],
            validation_outcome="PASS",
        )
        assert chain.complete is False
        assert chain.broken_links

    def test_complete_provenance_has_no_missing_links(self):
        chain = build_provenance(
            claim="Aspek X tidak dibahas oleh satu pun jurnal.",
            cited_records=["a.pdf"],
            retrieved_passages=[{"source_paper": "a.pdf", "quote": "Kutipan pendukung."}],
            validation_outcome="PASS",
        )
        assert chain.complete is True
        assert not chain.broken_links


class TestCoverageMap:
    STRUCTURED = [
        {"source": "s1.pdf", "domain": "mobile forensics", "outcome": "accuracy"},
        {"source": "s2.pdf", "domain": "mobile forensics", "outcome": "accuracy"},
        {"source": "s3.pdf", "domain": "disk forensics", "outcome": "accuracy"},
    ]

    def test_structured_axes_populate_the_matrix(self):
        matrix = build_coverage_matrix(self.STRUCTURED, paper_ref=_ref)
        assert "mobile forensics" in matrix.rows
        assert "accuracy" in matrix.columns
        assert matrix.total_papers == 3
        assert matrix.cell("mobile forensics", "accuracy").study_count == 2

    def test_uncovered_combination_is_an_empty_cell(self):
        matrix = build_coverage_matrix(
            self.STRUCTURED
            + [{"source": "s4.pdf", "domain": "cloud forensics", "outcome": "latency"}],
            paper_ref=_ref,
        )
        empties = {(c.row, c.column) for c in matrix.empty_cells}
        assert ("cloud forensics", "accuracy") in empties
        assert 0.0 <= matrix.density <= 1.0

    def test_candidate_gaps_are_bounded(self):
        matrix = build_coverage_matrix(self.STRUCTURED, paper_ref=_ref)
        assert len(matrix.candidate_gaps(limit=3)) <= 3

    def test_degenerate_single_cell_map_has_no_empty_cells(self):
        """A 1x1 map is a non-finding: nothing can be compared against it."""
        matrix = build_coverage_matrix(
            [
                {"source": "a.pdf", "domain": "mobile forensics", "outcome": "accuracy"},
                {"source": "b.pdf", "domain": "mobile forensics", "outcome": "accuracy"},
                {"source": "c.pdf", "domain": "mobile forensics", "outcome": "accuracy"},
            ],
            paper_ref=_ref,
        )
        assert len(matrix.rows) == 1 and len(matrix.columns) == 1
        assert matrix.empty_cells == []
        assert matrix.density == pytest.approx(1.0)

    def test_thin_cells_alone_are_not_an_empty_cell_signal(self):
        """Thin cells must not stand in for the P8 empty-cell signal."""
        matrix = build_coverage_matrix(
            [{"source": "a.pdf", "domain": "mobile forensics", "outcome": "accuracy"}],
            paper_ref=_ref,
        )
        assert matrix.thin_cells, "one study per cell counts as thin"
        assert matrix.empty_cells == []
        assert matrix.candidate_gaps()


class TestGraphMetrics:
    ITEMS = ["a", "b", "c", "d"]
    # Two tight pairs with no cross-links -> clearly modular structure.
    MATRIX = [
        [1.0, 0.9, 0.0, 0.0],
        [0.9, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.9],
        [0.0, 0.0, 0.9, 1.0],
    ]

    def test_modularity_is_bounded_and_rewards_separation(self):
        good = compute_modularity(
            self.ITEMS, self.MATRIX, {0: ["a", "b"], 1: ["c", "d"]}, 0.45
        )
        bad = compute_modularity(
            self.ITEMS, self.MATRIX, {0: ["a", "c"], 1: ["b", "d"]}, 0.45
        )
        assert -1.0 <= good <= 1.0
        assert good > bad

    def test_cluster_papers_separates_disjoint_vocabularies(self):
        features = {
            "a.pdf": ["mobile", "android", "acquisition"],
            "b.pdf": ["mobile", "android", "imaging"],
            "c.pdf": ["network", "packet", "capture"],
            "d.pdf": ["network", "packet", "flow"],
        }
        result = cluster_papers(features)
        assert len(result.clusters) >= 2

    def test_single_paper_clustering_is_trivial(self):
        result = cluster_papers({"a.pdf": ["mobile"]})
        assert result.method == "trivial"


class TestNovelty:
    PAPERS = [
        {
            "source": p["source"],
            "title": p["title"],
            "content": p["content"][:1500],
        }
        for p in REVIEW_CORPUS + [PRIMARY_PAPER]
    ]

    GAPS = [
        {
            "type": "INCOMPLETENESS",
            "confidence": 0.8,
            "calibrated_confidence": 0.9,
            "description": "Aspek chain of custody tidak dibahas bersama.",
        }
    ]

    PROPOSALS = [
        {
            "title": "Kerangka integratif chain of custody lintas alat forensik",
            "description": (
                "Menyintesis model proses forensik dan kendala institusional ke "
                "dalam satu kerangka, divalidasi lewat studi kasus dan eksperimen "
                "terkontrol dengan protokol pengukuran yang jelas."
            ),
            "gap_type": "INCOMPLETENESS",
            "why": "Menjawab indikator ketidaklengkapan.",
            "how": "Studi kasus + eksperimen terkontrol.",
        },
        {
            "title": "Survei triase forensik",
            "description": "Prior work has widely reported that automated triage improves throughput.",
            "gap_type": "INCOMPLETENESS",
            "why": "",
            "how": "",
        },
    ]

    def test_rank_proposals_attaches_novelty_and_priority(self):
        ranked = rank_proposals(self.PROPOSALS, self.PAPERS, self.GAPS, embedder=None)
        assert len(ranked) == len(self.PROPOSALS)
        for item in ranked:
            assert "novelty" in item, "novelty block must be attached"
            assert item["priority"] in {"high", "medium", "low"}
            assert 0.0 <= item["novelty"]["novelty"] <= 1.0

    def test_ranking_is_sorted_by_priority_score(self):
        ranked = rank_proposals(self.PROPOSALS, self.PAPERS, self.GAPS, embedder=None)
        scores = [item["novelty"]["priority_score"] for item in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_derivative_proposal_scores_lower_novelty(self):
        backend = _Backend(None)
        texts = [p["content"] for p in self.PAPERS]
        refs = [p["source"] for p in self.PAPERS]
        integrative = score_proposal(self.PROPOSALS[0], texts, refs, backend)
        derivative = score_proposal(self.PROPOSALS[1], texts, refs, backend)
        assert derivative.novelty < integrative.novelty

    def test_empty_proposals_returns_empty(self):
        assert rank_proposals([], self.PAPERS, self.GAPS) == []

    def test_bands_and_labels(self):
        assert novelty_band(0.05) == "derivative"
        assert novelty_band(0.98) == "off_topic"
        assert priority_label(0.7) == "high"
        assert priority_label(0.5) == "medium"
        assert priority_label(0.1) == "low"


class _TensorLikeEmbedder:
    """Mimics ``SentenceTransformer.encode`` returning non-float rows.

    Real embedders hand back torch tensors / numpy arrays whose scalars do not
    implement ``__round__``; if the backend does not coerce them, ranking blows
    up inside ``NoveltyScore.to_dict`` and is silently skipped.
    """

    def __init__(self, row_factory):
        self._row_factory = row_factory

    def encode(self, texts, **kwargs):
        rows = []
        for text in texts:
            tokens = sorted({t for t in text.lower().split() if len(t) > 3})[:8]
            vec = [float(len(t)) for t in tokens]
            vec += [0.0] * (8 - len(vec))
            rows.append(self._row_factory(vec))
        return rows


class TestNoveltyEmbedderCoercion:
    """Regression guard: embedder outputs must be coerced to plain floats."""

    PAPERS = TestNovelty.PAPERS
    GAPS = TestNovelty.GAPS
    PROPOSALS = TestNovelty.PROPOSALS

    def _assert_json_safe(self, ranked):
        import json

        for item in ranked:
            block = item["novelty"]
            assert isinstance(block["novelty"], float)
            assert isinstance(block["priority_score"], float)
            json.dumps(block)  # must survive API serialisation

    def test_numpy_embedder_is_coerced(self):
        np = pytest.importorskip("numpy")
        ranked = rank_proposals(
            self.PROPOSALS,
            self.PAPERS,
            self.GAPS,
            embedder=_TensorLikeEmbedder(np.array),
        )
        assert len(ranked) == len(self.PROPOSALS)
        self._assert_json_safe(ranked)

    def test_torch_embedder_is_coerced(self):
        torch = pytest.importorskip("torch")
        ranked = rank_proposals(
            self.PROPOSALS,
            self.PAPERS,
            self.GAPS,
            embedder=_TensorLikeEmbedder(torch.tensor),
        )
        assert len(ranked) == len(self.PROPOSALS)
        self._assert_json_safe(ranked)

    def test_broken_embedder_falls_back_to_lexical(self):
        class _Broken:
            def encode(self, texts, **kwargs):
                raise RuntimeError("no model")

        ranked = rank_proposals(
            self.PROPOSALS, self.PAPERS, self.GAPS, embedder=_Broken()
        )
        assert len(ranked) == len(self.PROPOSALS)
        self._assert_json_safe(ranked)


class TestAspectGroundingSymmetry:
    """Grounding and quote extraction must use the SAME terms.

    ``_ground_aspects`` marks an aspect grounded when *any* content word occurs
    in the corpus, but the quote extractor matched the *whole phrase*. Long
    aspect phrases therefore always looked grounded while never yielding a
    quote, which permanently broke the provenance chain and forced every
    incompleteness indicator into ``needs_review``.
    """

    ASPECT = "Chain of custody dan integritas bukti digital"
    PAPERS = [
        {
            "source": "p1.pdf",
            "content": (
                "Penelitian ini membahas custody bukti digital pada proses "
                "akuisisi. Integritas data dijaga melalui hashing."
            ),
        }
    ]

    def test_aspect_terms_drops_stopwords_and_short_tokens(self):
        terms = aspect_terms(self.ASPECT)
        assert "custody" in terms
        assert "integritas" in terms
        assert "dan" not in terms
        assert all(len(t) > 3 for t in terms)

    def test_whole_phrase_yields_no_quote(self):
        assert extract_supporting_quotes([self.ASPECT], self.PAPERS) == []

    def test_content_terms_yield_a_quote(self):
        quotes = extract_supporting_quotes(aspect_terms(self.ASPECT), self.PAPERS)
        assert quotes, "grounded aspect must be quotable via its content terms"
        assert quotes[0]["source_paper"]
        assert quotes[0]["quote"]

    def test_grounded_aspects_are_always_quotable(self):
        analyzer = GapAnalyzer.__new__(GapAnalyzer)
        grounded, _ = analyzer._ground_aspects([self.ASPECT], self.PAPERS)
        assert grounded == [self.ASPECT]
        terms = [t for a in grounded for t in aspect_terms(a)[:4]]
        assert extract_supporting_quotes(terms, self.PAPERS)


class TestPipelineCorpusShape:
    """Regression guard for the novelty wiring in ``routes/analysis.py``.

    ``paper_contents`` entries carry ``sample_chunks`` as a list of *dicts*, so
    joining them as strings raises ``TypeError`` and silently disables ranking.
    The pipeline must build corpus text from ``content`` instead.
    """

    PAPER_CONTENTS = [
        {
            "source": "a.pdf",
            "title": "Judul A",
            "content": "Isi dokumen A tentang forensik digital.",
            "sample_chunks": [{"chunk_index": 0, "section": None, "text": "potongan"}],
        }
    ]

    def test_sample_chunks_are_not_joinable_as_strings(self):
        with pytest.raises(TypeError):
            " ".join(self.PAPER_CONTENTS[0]["sample_chunks"])

    def test_content_based_corpus_enables_ranking(self):
        corpus = [
            {
                "source": p.get("source", ""),
                "title": p.get("title", ""),
                "content": str(p.get("content") or "")[:1500],
            }
            for p in self.PAPER_CONTENTS
        ]
        ranked = rank_proposals(
            TestNovelty.PROPOSALS, corpus, TestNovelty.GAPS, embedder=None
        )
        assert all("novelty" in item for item in ranked)
