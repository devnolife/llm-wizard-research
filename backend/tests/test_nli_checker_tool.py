"""Unit tests for the NLI checker agent tool."""

from unittest.mock import MagicMock

from app.core.agents.tools.nli_checker_tool import NLICheckerTool
from app.core.validation.relation_classifier import RelationClassifier


def test_nli_checker_returns_relation_classifier_layers_without_fallback():
    """NLICheckerTool should expose RelationClassifier layers and avoid LLM fallback."""
    llm = MagicMock()
    classifier = RelationClassifier(llm_interface=None)
    tool = NLICheckerTool(relation_classifier=classifier, llm_interface=llm)

    result = tool.run(
        claim_a="A",
        claim_b="B",
        context="A leads to B improvements.",
        kg_facts=[{"subject_id": "A", "object_id": "B"}],
    )

    assert result["relation_type"] == "CAUSAL"
    assert result["confidence"] > 0
    assert result["layers_used"] == [
        "semantic_filter",
        "evidence_extraction",
        "rule_validation",
    ]
    llm.generate.assert_not_called()
