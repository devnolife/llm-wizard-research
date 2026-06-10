"""
Unit tests — dedicated NLI model integration (Layer 2b).

Verifies that RelationClassifier:
    1. Works unchanged without an NLI model (default — backward compatible)
    2. Promotes CO_OCCURRENCE → CONTRADICTION when NLI detects one
    3. Corroborates an existing CONTRADICTION (marker added, type kept)
    4. Ignores NLI gracefully when the model returns None (unavailable)

Uses a mock NLI model — no model download required.
"""

import pytest
from unittest.mock import MagicMock

from app.core.validation.relation_classifier import (
    RelationClassifier,
    RelationType,
)


def make_nli(is_contradiction: bool, confidence: float = 0.9, available: bool = True):
    nli = MagicMock()
    if not available:
        nli.check_contradiction.return_value = None
    else:
        nli.check_contradiction.return_value = {
            "is_contradiction": is_contradiction,
            "confidence": confidence,
            "direction": "forward",
            "forward_scores": {},
            "backward_scores": {},
        }
    return nli


NEUTRAL_TEXT = "Method A and Method B are both used in image processing tasks."
CONTRA_TEXT = "Method A improves accuracy. However, Method B conflicts with this finding."


class TestWithoutNLI:
    def test_default_behaviour_unchanged(self):
        rc = RelationClassifier()
        result = rc.classify(
            entity_a="Method A", entity_b="Method B",
            text_context=NEUTRAL_TEXT, semantic_similarity=0.8,
        )
        assert result.relation_type == RelationType.CO_OCCURRENCE
        assert "nli_model" not in result.evidence_markers


class TestWithNLI:
    def test_nli_promotes_to_contradiction(self):
        rc = RelationClassifier(nli_model=make_nli(True, 0.92))
        result = rc.classify(
            entity_a="Dropout improves generalization",
            entity_b="Dropout degrades generalization",
            text_context=NEUTRAL_TEXT,  # no contradiction markers in text
            semantic_similarity=0.8,
        )
        assert result.relation_type == RelationType.CONTRADICTION
        assert "nli_model" in result.evidence_markers
        assert "NLI model detected contradiction" in result.explanation

    def test_nli_corroborates_existing_contradiction(self):
        rc = RelationClassifier(nli_model=make_nli(True, 0.85))
        result = rc.classify(
            entity_a="Method A", entity_b="Method B",
            text_context=CONTRA_TEXT,  # has "however"/"conflicts with" markers
            semantic_similarity=0.8,
        )
        assert result.relation_type == RelationType.CONTRADICTION
        assert "nli_model" in result.evidence_markers
        assert "Corroborated by NLI model" in result.explanation

    def test_nli_negative_keeps_co_occurrence(self):
        rc = RelationClassifier(nli_model=make_nli(False))
        result = rc.classify(
            entity_a="Method A", entity_b="Method B",
            text_context=NEUTRAL_TEXT, semantic_similarity=0.8,
        )
        assert result.relation_type == RelationType.CO_OCCURRENCE
        assert "nli_model" not in result.evidence_markers

    def test_nli_unavailable_falls_back_silently(self):
        rc = RelationClassifier(nli_model=make_nli(True, available=False))
        result = rc.classify(
            entity_a="Method A", entity_b="Method B",
            text_context=NEUTRAL_TEXT, semantic_similarity=0.8,
        )
        assert result.relation_type == RelationType.CO_OCCURRENCE

    def test_layer1_filter_skips_nli(self):
        """Below similarity threshold, NLI must not even be called."""
        nli = make_nli(True)
        rc = RelationClassifier(nli_model=nli, similarity_threshold=0.3)
        result = rc.classify(
            entity_a="A", entity_b="B",
            text_context=NEUTRAL_TEXT, semantic_similarity=0.1,
        )
        assert result.relation_type == RelationType.UNKNOWN
        nli.check_contradiction.assert_not_called()
