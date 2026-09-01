"""Tests for cross-journal theme aggregation of ranked proposals."""

from app.core.recommendation.themes import THEME_SIMILARITY_THRESHOLD, Theme, build_themes


def _p(title, source, score, topic="tools", run_support=None):
    item = {
        "title": title,
        "description": title,
        "source": source,
        "topic": topic,
        "novelty": {"priority_score": score},
    }
    if run_support is not None:
        item["run_support"] = run_support
    return item


PROPOSALS = [
    _p("Protokol pengujian terstandar untuk validasi alat forensik", "a.pdf", 0.90),
    _p("Protokol pengujian terstandar untuk validasi alat forensik", "b.pdf", 0.80),
    _p("Protokol pengujian terstandar untuk validasi alat forensik", "c.pdf", 0.70),
    _p("Steganografi citra digital dengan lapisan kriptografi", "d.pdf", 0.95),
]


class TestBuildThemes:
    def test_empty_returns_empty(self):
        assert build_themes([]) == []

    def test_identical_proposals_group_into_one_theme(self):
        themes = build_themes(PROPOSALS, embedder=None, threshold=0.5)
        assert any(t.journal_support == 3 for t in themes)

    def test_cross_journal_theme_outranks_higher_scoring_singleton(self):
        """A single verbose paper must not outrank evidence from three journals."""
        themes = build_themes(PROPOSALS, embedder=None, threshold=0.5)
        assert themes[0].journal_support == 3
        assert themes[0].top_priority < 0.95  # the singleton scores higher alone

    def test_journals_are_deduplicated(self):
        themes = build_themes(
            [_p("Topik sama persis", "a.pdf", 0.5), _p("Topik sama persis", "a.pdf", 0.4)],
            embedder=None, threshold=0.5,
        )
        assert themes[0].journal_support == 1
        assert len(themes[0].members) == 2

    def test_run_support_is_averaged(self):
        themes = build_themes(
            [_p("Topik sama persis", "a.pdf", 0.5, run_support=3),
             _p("Topik sama persis", "b.pdf", 0.5, run_support=1)],
            embedder=None, threshold=0.5,
        )
        assert themes[0].run_support == 2.0

    def test_to_dict_is_serialisable(self):
        block = build_themes(PROPOSALS, embedder=None, threshold=0.5)[0].to_dict()
        assert block["journal_support"] >= 1
        assert isinstance(block["priority"], float)
        assert isinstance(block["journals"], list)

    def test_default_threshold_is_calibrated_above_paper_default(self):
        assert THEME_SIMILARITY_THRESHOLD > 0.45
