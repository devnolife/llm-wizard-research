"""
Unit tests for RelationClassifier (3-layer classification pipeline).

Tests co-occurrence, causal, and contradiction classification, linguistic
marker detection, the 3-layer mechanism, and edge cases — all without
external services.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.validation.relation_classifier import (
    CAUSAL_MARKERS,
    CONTRADICTION_MARKERS,
    EXTENSION_MARKERS,
    ClassifiedRelation,
    RelationClassifier,
    RelationType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def classifier():
    """Classifier with default thresholds and no LLM."""
    return RelationClassifier(
        llm_interface=None,
        similarity_threshold=0.3,
        causal_confidence_threshold=0.5,
    )


@pytest.fixture
def strict_classifier():
    """Classifier with a high similarity threshold (filters more)."""
    return RelationClassifier(
        llm_interface=None,
        similarity_threshold=0.8,
    )


# ---------------------------------------------------------------------------
# Co-occurrence classification
# ---------------------------------------------------------------------------

class TestCoOccurrence:
    def test_plain_cooccurrence(self, classifier):
        """Text with both entities but no causal/contradiction markers → CO_OCCURRENCE."""
        text = "CNN and RNN are both neural network architectures used in NLP."
        result = classifier.classify("CNN", "RNN", text, semantic_similarity=0.6)
        assert result.relation_type == RelationType.CO_OCCURRENCE
        assert result.evidence_markers == []

    def test_cooccurrence_not_classified_as_causal(self, classifier):
        """Ensure plain co-occurrence is never labelled CAUSAL."""
        text = "Method A and Method B appear in the same survey."
        result = classifier.classify("Method A", "Method B", text, semantic_similarity=0.5)
        assert result.relation_type != RelationType.CAUSAL

    def test_cooccurrence_confidence_capped(self, classifier):
        """CO_OCCURRENCE confidence should be ≤ 0.5."""
        text = "CNN and RNN are neural network architectures."
        result = classifier.classify("CNN", "RNN", text, semantic_similarity=0.9)
        assert result.confidence <= 0.5


# ---------------------------------------------------------------------------
# Causal classification
# ---------------------------------------------------------------------------

class TestCausal:
    @pytest.mark.parametrize("marker", [
        "causes", "leads to", "results in", "because", "therefore",
        "consequently", "due to", "contributes to", "enables",
    ])
    def test_causal_with_various_markers(self, classifier, marker):
        text = f"CNN {marker} improved accuracy in medical imaging."
        result = classifier.classify("CNN", "accuracy", text, semantic_similarity=0.7)
        assert result.relation_type == RelationType.CAUSAL
        assert marker in result.evidence_markers

    def test_causal_with_kg_support(self, classifier):
        """Causal + supporting KG facts → validated=True."""
        text = "Data augmentation leads to better accuracy in image classification."
        kg = [{"subject_id": "Data augmentation", "object_id": "accuracy"}]
        result = classifier.classify(
            "Data augmentation", "accuracy", text,
            semantic_similarity=0.7, kg_facts=kg,
        )
        assert result.relation_type == RelationType.CAUSAL
        assert result.rule_validated is True

    def test_causal_without_kg_support(self, classifier):
        """Causal + no supporting KG facts → validated=False."""
        text = "Data augmentation leads to better accuracy in image classification."
        result = classifier.classify(
            "Data augmentation", "accuracy", text,
            semantic_similarity=0.7, kg_facts=[],
        )
        assert result.relation_type == RelationType.CAUSAL
        assert result.rule_validated is False

    def test_causal_multiple_markers(self, classifier):
        text = ("Transfer learning leads to improved performance because "
                "it enables knowledge reuse.")
        result = classifier.classify(
            "Transfer learning", "performance", text, semantic_similarity=0.7,
        )
        assert result.relation_type == RelationType.CAUSAL
        assert len(result.evidence_markers) >= 2


# ---------------------------------------------------------------------------
# Contradiction classification
# ---------------------------------------------------------------------------

class TestContradiction:
    @pytest.mark.parametrize("marker", [
        "however", "contradicts", "in contrast", "whereas",
        "on the other hand", "inconsistent with", "conflicts with",
        "contrary to", "disputes", "challenges",
    ])
    def test_contradiction_with_various_markers(self, classifier, marker):
        text = f"Study A finds X, {marker}, Study B finds Y."
        result = classifier.classify("Study A", "Study B", text, semantic_similarity=0.6)
        assert result.relation_type == RelationType.CONTRADICTION
        assert marker in result.evidence_markers

    def test_contradiction_always_validated(self, classifier):
        """Layer 3 always validates contradictions (linguistic evidence only)."""
        text = "Method A improves accuracy, however Method B shows no improvement."
        result = classifier.classify("Method A", "Method B", text, semantic_similarity=0.6)
        assert result.relation_type == RelationType.CONTRADICTION
        assert result.rule_validated is True

    def test_contradiction_takes_priority_over_causal(self, classifier):
        """When both contradiction and causal markers are present,
        contradiction is detected first (checked first in code)."""
        text = ("Method A leads to good results, however Method B contradicts "
                "these findings.")
        result = classifier.classify("Method A", "Method B", text, semantic_similarity=0.7)
        assert result.relation_type == RelationType.CONTRADICTION


# ---------------------------------------------------------------------------
# Layer 1 – Semantic Filtering
# ---------------------------------------------------------------------------

class TestLayer1SemanticFiltering:
    def test_below_threshold_produces_unknown(self, classifier):
        """Low similarity → UNKNOWN, discarded before evidence extraction."""
        text = "CNN achieves high accuracy because of convolutions."
        result = classifier.classify("CNN", "accuracy", text, semantic_similarity=0.1)
        assert result.relation_type == RelationType.UNKNOWN
        assert result.evidence_markers == []
        assert result.layers_used == ["semantic_filter"]

    def test_at_threshold_proceeds(self, classifier):
        """Exactly at threshold should still proceed (not <)."""
        text = "CNN and accuracy appear together."
        result = classifier.classify("CNN", "accuracy", text, semantic_similarity=0.3)
        assert result.relation_type != RelationType.UNKNOWN

    def test_strict_threshold_filters_more(self, strict_classifier):
        text = "CNN leads to better accuracy."
        result = strict_classifier.classify("CNN", "accuracy", text, semantic_similarity=0.5)
        assert result.relation_type == RelationType.UNKNOWN


# ---------------------------------------------------------------------------
# Layer 2 – Evidence Extraction / Linguistic markers
# ---------------------------------------------------------------------------

class TestLayer2LinguisticMarkers:
    def test_all_causal_markers_recognised(self, classifier):
        for marker in CAUSAL_MARKERS:
            text = f"A {marker} B in this study."
            result = classifier.classify("A", "B", text, semantic_similarity=0.5)
            assert marker in result.evidence_markers or result.relation_type in (
                RelationType.CAUSAL, RelationType.CONTRADICTION
            ), f"Marker '{marker}' was not detected"

    def test_all_contradiction_markers_recognised(self, classifier):
        for marker in CONTRADICTION_MARKERS:
            text = f"A and B, {marker}, show different trends."
            result = classifier.classify("A", "B", text, semantic_similarity=0.5)
            assert marker in result.evidence_markers, f"Marker '{marker}' was not detected"

    def test_extension_markers(self, classifier):
        text = "Method B extends Method A by adding new layers."
        result = classifier.classify("Method A", "Method B", text, semantic_similarity=0.6)
        assert result.relation_type == RelationType.EXTENSION
        assert "extends" in result.evidence_markers

    def test_no_markers_means_cooccurrence(self, classifier):
        text = "Method A and Method B are both discussed in the survey."
        result = classifier.classify("Method A", "Method B", text, semantic_similarity=0.5)
        assert result.relation_type == RelationType.CO_OCCURRENCE
        assert result.evidence_markers == []

    def test_case_insensitive_marker_detection(self, classifier):
        text = "CNN LEADS TO improved accuracy."
        result = classifier.classify("CNN", "accuracy", text, semantic_similarity=0.6)
        assert result.relation_type == RelationType.CAUSAL


# ---------------------------------------------------------------------------
# Layer 3 – Rule-Based Validation
# ---------------------------------------------------------------------------

class TestLayer3RuleValidation:
    def test_cooccurrence_always_valid(self, classifier):
        text = "A and B are both present."
        result = classifier.classify("A", "B", text, semantic_similarity=0.5)
        assert result.rule_validated is True

    def test_causal_valid_with_matching_kg(self, classifier):
        text = "A leads to B improvements."
        kg = [{"subject_id": "A", "object_id": "B"}]
        result = classifier.classify("A", "B", text, semantic_similarity=0.6, kg_facts=kg)
        assert result.rule_validated is True
        assert result.layers_used == [
            "semantic_filter",
            "evidence_extraction",
            "rule_validation",
        ]

    def test_causal_invalid_without_matching_kg(self, classifier):
        text = "A leads to B improvements."
        kg = [{"subject_id": "X", "object_id": "Y"}]
        result = classifier.classify("A", "B", text, semantic_similarity=0.6, kg_facts=kg)
        assert result.rule_validated is False

    def test_contradiction_valid_always(self, classifier):
        text = "A however contradicts B."
        result = classifier.classify("A", "B", text, semantic_similarity=0.6, kg_facts=[])
        assert result.rule_validated is True


# ---------------------------------------------------------------------------
# Confidence calculation
# ---------------------------------------------------------------------------

class TestConfidenceCalculation:
    def test_higher_similarity_higher_confidence(self, classifier):
        text = "A leads to B."
        r1 = classifier.classify("A", "B", text, semantic_similarity=0.4, kg_facts=[])
        r2 = classifier.classify("A", "B", text, semantic_similarity=0.9, kg_facts=[])
        assert r2.confidence > r1.confidence

    def test_more_markers_higher_confidence(self, classifier):
        text_one = "A leads to B."
        text_many = "A leads to B because it enables and contributes to progress."
        r1 = classifier.classify("A", "B", text_one, semantic_similarity=0.6, kg_facts=[])
        r2 = classifier.classify("A", "B", text_many, semantic_similarity=0.6, kg_facts=[])
        assert r2.confidence >= r1.confidence

    def test_validation_boosts_confidence(self, classifier):
        text = "A leads to B."
        kg = [{"subject_id": "A", "object_id": "B"}]
        r_valid = classifier.classify("A", "B", text, semantic_similarity=0.6, kg_facts=kg)
        r_invalid = classifier.classify("A", "B", text, semantic_similarity=0.6, kg_facts=[])
        assert r_valid.confidence > r_invalid.confidence

    def test_confidence_never_exceeds_1(self, classifier):
        text = "A leads to B because it enables and contributes to and results in progress."
        kg = [{"subject_id": "A", "object_id": "B"}]
        result = classifier.classify("A", "B", text, semantic_similarity=1.0, kg_facts=kg)
        assert result.confidence <= 1.0

    def test_cooccurrence_confidence_max_half_similarity(self, classifier):
        text = "A and B appear together."
        result = classifier.classify("A", "B", text, semantic_similarity=0.8)
        assert result.confidence <= 0.5


# ---------------------------------------------------------------------------
# ClassifiedRelation model
# ---------------------------------------------------------------------------

class TestClassifiedRelation:
    def test_to_dict(self, classifier):
        text = "A leads to B."
        result = classifier.classify("A", "B", text, semantic_similarity=0.6)
        d = result.to_dict()
        assert "entity_a" in d
        assert "entity_b" in d
        assert "relation_type" in d
        assert "evidence_markers" in d
        assert "confidence" in d
        assert d["layers_used"] == [
            "semantic_filter",
            "evidence_extraction",
            "rule_validation",
        ]

    def test_evidence_text_truncated_in_dict(self):
        cr = ClassifiedRelation(
            entity_a="A", entity_b="B",
            relation_type=RelationType.CAUSAL,
            semantic_similarity=0.5,
            evidence_markers=["leads to"],
            evidence_text="x" * 500,
            rule_validated=True,
            confidence=0.7,
            explanation="test",
        )
        d = cr.to_dict()
        assert len(d["evidence_text"]) <= 200
        assert d["layers_used"] == []


# ---------------------------------------------------------------------------
# Batch classification
# ---------------------------------------------------------------------------

class TestBatchClassification:
    def test_classify_batch(self, classifier):
        pairs = [
            {"entity_a": "CNN", "entity_b": "RNN", "similarity": 0.6},
            {"entity_a": "A", "entity_b": "B", "similarity": 0.7},
        ]
        text = "CNN and RNN are architectures. A leads to B improvement."
        results = classifier.classify_batch(pairs, text)
        assert len(results) == 2
        assert all(isinstance(r, ClassifiedRelation) for r in results)

    def test_classify_batch_empty(self, classifier):
        results = classifier.classify_batch([], "some text")
        assert results == []


# ---------------------------------------------------------------------------
# LLM fallback
# ---------------------------------------------------------------------------

class TestLLMFallback:
    def test_llm_extraction_called_when_available(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = (
            '{"relation_type": "CAUSAL", "evidence": "A causes B", "markers": ["causes"]}'
        )
        classifier = RelationClassifier(llm_interface=mock_llm)
        # Call the LLM-enhanced extraction directly
        rel_type, markers, evidence = classifier._extract_evidence_llm(
            "A", "B", "A causes B to improve."
        )
        mock_llm.generate.assert_called_once()
        assert rel_type == RelationType.CAUSAL

    def test_llm_extraction_fallback_on_error(self):
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = RuntimeError("LLM unavailable")
        classifier = RelationClassifier(llm_interface=mock_llm)
        # Should fall back to pattern matching
        rel_type, markers, evidence = classifier._extract_evidence_llm(
            "A", "B", "A leads to B."
        )
        assert rel_type == RelationType.CAUSAL
        assert "leads to" in markers

    def test_no_llm_uses_pattern_matching(self):
        classifier = RelationClassifier(llm_interface=None)
        rel_type, markers, evidence = classifier._extract_evidence_llm(
            "A", "B", "A leads to B."
        )
        assert rel_type == RelationType.CAUSAL


# ---------------------------------------------------------------------------
# Sentence finding utility
# ---------------------------------------------------------------------------

class TestSentenceFinding:
    def test_finds_sentence_with_both_entities(self, classifier):
        text = "First sentence. CNN leads to better accuracy in tasks. Last sentence."
        sentences = classifier._find_relevant_sentences(text, "CNN", "accuracy")
        assert any("CNN" in s and "accuracy" in s for s in sentences)

    def test_fallback_to_adjacent_when_no_shared_sentence(self, classifier):
        text = "CNN is a model. Accuracy is high."
        sentences = classifier._find_relevant_sentences(text, "CNN", "accuracy")
        assert len(sentences) > 0

    def test_limits_to_five_sentences(self, classifier):
        text = ". ".join(
            [f"A and B in sentence {i}" for i in range(20)]
        ) + "."
        sentences = classifier._find_relevant_sentences(text, "A", "B")
        assert len(sentences) <= 5


# ---------------------------------------------------------------------------
# RelationType enum
# ---------------------------------------------------------------------------

class TestRelationTypeEnum:
    def test_all_types(self):
        expected = {"CO_OCCURRENCE", "CAUSAL", "CONTRADICTION", "EXTENSION", "UNKNOWN"}
        assert {t.value for t in RelationType} == expected
