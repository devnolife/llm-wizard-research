"""Tests for the corpus coherence warning."""

from app.core.pipeline.corpus_relevance import (
    RELEVANCE_WARN_THRESHOLD,
    build_probe,
    check_corpus_relevance,
)


class _FakeEmbedder:
    """Maps each text to a unit vector keyed by its leading topic marker."""

    VECTORS = {
        "forensik": [1.0, 0.0, 0.0],
        "dekat": [0.9, 0.436, 0.0],
        "asing": [0.0, 0.0, 1.0],
    }

    def encode(self, texts):
        out = []
        for t in texts:
            key = next((k for k in self.VECTORS if k in t.lower()), "asing")
            out.append(self.VECTORS[key])
        return out


class TestBuildProbe:
    def test_uses_title_and_first_body_chunks(self):
        chunks = [
            {"text": "isi kedua", "chunk_index": 1, "is_reference": False},
            {"text": "isi pertama", "chunk_index": 0, "is_reference": False},
        ]
        probe = build_probe("Judul Paper", chunks)
        assert probe.startswith("Judul Paper")
        assert "isi pertama" in probe and "isi kedua" in probe

    def test_skips_reference_chunks(self):
        chunks = [
            {"text": "daftar pustaka", "chunk_index": 0, "is_reference": True},
            {"text": "isi asli", "chunk_index": 1, "is_reference": False},
        ]
        assert "daftar pustaka" not in build_probe("Judul", chunks)

    def test_handles_missing_title(self):
        assert build_probe(None, [{"text": "isi", "chunk_index": 0}]) == "isi"


class TestCheckCorpusRelevance:
    def test_flags_the_odd_one_out(self):
        probes = {
            "a.pdf": "forensik digital",
            "b.pdf": "forensik bukti",
            "c.pdf": "dekat forensik",
            "x.pdf": "asing sekali",
        }
        reports = check_corpus_relevance(probes, embedder=_FakeEmbedder())
        assert reports[0].source == "x.pdf"
        assert reports[0].flagged
        assert not any(r.flagged for r in reports if r.source != "x.pdf")

    def test_sorted_least_related_first(self):
        probes = {"a.pdf": "forensik", "b.pdf": "forensik", "x.pdf": "asing"}
        scores = [r.score for r in check_corpus_relevance(probes, embedder=_FakeEmbedder())]
        assert scores == sorted(scores)

    def test_no_embedder_flags_nothing(self):
        """The threshold is calibrated for embedding cosine, so stay silent."""
        probes = {"a.pdf": "forensik", "x.pdf": "asing"}
        assert not any(r.flagged for r in check_corpus_relevance(probes, embedder=None))

    def test_single_journal_is_not_flagged(self):
        reports = check_corpus_relevance({"a.pdf": "forensik"}, embedder=_FakeEmbedder())
        assert len(reports) == 1 and not reports[0].flagged

    def test_threshold_is_a_warning_level_not_a_gate(self):
        assert 0.0 < RELEVANCE_WARN_THRESHOLD < 1.0
