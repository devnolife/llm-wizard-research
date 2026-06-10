"""
Unit tests — FactExtractor JSON parsing & retry behaviour.

Verifies the fix for the "0 facts extracted" bug:
    1. _parse_json_response handles: valid array, markdown-wrapped,
       object-wrapped (Ollama JSON mode), malformed input
    2. _generate_json retries once with stricter prompt on parse failure
    3. extract_from_text produces entities + facts end-to-end with mock LLM
    4. LLM interfaces without `format` kwarg still work (TypeError fallback)

All tests run offline — no Ollama required.
"""

import json
import pytest
from unittest.mock import MagicMock

from app.core.knowledge.fact_extractor import FactExtractor, RETRY_SUFFIX
from app.core.knowledge.fact_table import EntityType, FactTable, PredicateType


ENTITIES_JSON = json.dumps([
    {"name": "CNN", "type": "METHOD", "properties": {"resource_requirement": "high"}},
    {"name": "Medical Imaging", "type": "DOMAIN", "properties": {}},
    {"name": "achieves 92.3% Dice", "type": "FINDING", "properties": {"metric": "Dice"}},
])

RELATIONS_JSON = json.dumps([
    {
        "subject": "CNN",
        "predicate": "APPLIES_TO",
        "object": "Medical Imaging",
        "confidence": 0.95,
        "evidence": "using CNN for medical imaging",
    },
    {
        "subject": "CNN",
        "predicate": "ACHIEVES",
        "object": "achieves 92.3% Dice",
        "confidence": 0.9,
        "evidence": "achieves 92.3% Dice coefficient",
    },
])


@pytest.fixture
def extractor():
    """FactExtractor without LLM (for parser-only tests)."""
    return FactExtractor(llm_interface=None)


@pytest.fixture
def fact_table():
    return FactTable()


# ===================================================================
# _parse_json_response
# ===================================================================

class TestParseJsonResponse:
    def test_valid_json_array(self, extractor):
        result = extractor._parse_json_response('[{"name": "CNN"}]')
        assert result == [{"name": "CNN"}]

    def test_markdown_code_block(self, extractor):
        response = 'Here are the entities:\n```json\n[{"name": "CNN"}]\n```\nDone.'
        result = extractor._parse_json_response(response)
        assert result == [{"name": "CNN"}]

    def test_bare_array_with_surrounding_text(self, extractor):
        response = 'Sure! [{"name": "BERT"}] hope this helps'
        result = extractor._parse_json_response(response)
        assert result == [{"name": "BERT"}]

    def test_object_wrapped_array_ollama_json_mode(self, extractor):
        """Ollama format=json often returns {"entities": [...]} instead of a bare array."""
        response = '{"entities": [{"name": "CNN"}, {"name": "RNN"}]}'
        result = extractor._parse_json_response(response)
        assert result == [{"name": "CNN"}, {"name": "RNN"}]

    def test_single_object_becomes_one_element_list(self, extractor):
        response = '{"name": "CNN", "type": "METHOD"}'
        result = extractor._parse_json_response(response)
        assert result == [{"name": "CNN", "type": "METHOD"}]

    def test_malformed_returns_none(self, extractor):
        assert extractor._parse_json_response("I could not find any entities.") is None

    def test_empty_array_is_valid(self, extractor):
        assert extractor._parse_json_response("[]") == []

    def test_truncated_array_salvages_complete_objects(self, extractor):
        """Regression: max_tokens truncation mid-array must not zero out extraction."""
        truncated = (
            '{\n  "relations": [\n'
            '    {"subject": "A", "predicate": "IMPROVES", "object": "B", "confidence": 0.8},\n'
            '    {"subject": "C", "predicate": "EXTENDS", "object": "D", "confidence": 0.7},\n'
            '    {"subject": "E", "predicate": "APPLIES_TO", "obj'  # cut mid-object
        )
        result = extractor._parse_json_response(truncated)
        assert result is not None
        assert len(result) == 2
        assert result[0]["subject"] == "A"
        assert result[1]["predicate"] == "EXTENDS"

    def test_truncated_with_nested_braces_and_escapes(self, extractor):
        truncated = (
            '[{"name": "CNN", "properties": {"note": "uses \\"residual\\" blocks"}},'
            ' {"name": "incomplete'
        )
        result = extractor._parse_json_response(truncated)
        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "CNN"


# ===================================================================
# _generate_json (retry behaviour)
# ===================================================================

class TestGenerateJson:
    def test_success_first_attempt_no_retry(self):
        llm = MagicMock()
        llm.generate.return_value = ENTITIES_JSON
        fe = FactExtractor(llm_interface=llm)

        result = fe._generate_json("prompt", system_prompt="sys")

        assert len(result) == 3
        assert llm.generate.call_count == 1
        # format="json" must be requested
        assert llm.generate.call_args.kwargs.get("format") == "json"

    def test_retry_with_stricter_prompt_on_parse_failure(self):
        llm = MagicMock()
        llm.generate.side_effect = ["garbage not json", ENTITIES_JSON]
        fe = FactExtractor(llm_interface=llm)

        result = fe._generate_json("base prompt", system_prompt="sys")

        assert len(result) == 3
        assert llm.generate.call_count == 2
        retry_prompt = llm.generate.call_args_list[1].args[0]
        assert retry_prompt.startswith("base prompt")
        assert RETRY_SUFFIX in retry_prompt

    def test_all_attempts_fail_returns_empty_list(self):
        llm = MagicMock()
        llm.generate.return_value = "still not json"
        fe = FactExtractor(llm_interface=llm)

        result = fe._generate_json("prompt", system_prompt="sys")

        assert result == []
        assert llm.generate.call_count == 2  # initial + 1 retry

    def test_fallback_when_llm_lacks_format_kwarg(self):
        """Interfaces without `format` param (e.g. older mocks) still work."""

        class LegacyLLM:
            def __init__(self):
                self.calls = 0

            def generate(self, prompt, system_prompt=None, temperature=None, max_tokens=None):
                self.calls += 1
                return ENTITIES_JSON

        llm = LegacyLLM()
        fe = FactExtractor(llm_interface=llm)

        result = fe._generate_json("prompt", system_prompt="sys")

        assert len(result) == 3
        assert llm.calls == 1


# ===================================================================
# End-to-end extraction with mock LLM
# ===================================================================

class TestExtractFromText:
    def test_entities_and_facts_extracted(self, fact_table):
        llm = MagicMock()
        # First call = entity extraction, second = relation extraction
        llm.generate.side_effect = [ENTITIES_JSON, RELATIONS_JSON]
        fe = FactExtractor(llm_interface=llm)

        stats = fe.extract_from_text(
            "CNN applied to medical imaging achieves 92.3% Dice coefficient.",
            paper_id="paper1",
            fact_table=fact_table,
        )

        assert stats["entities_extracted"] == 3
        assert stats["llm_facts_extracted"] == 2
        assert stats["total_facts"] >= 2

        # FactTable populated with correct types
        methods = fact_table.find_entities(entity_type=EntityType.METHOD)
        assert any(e.name == "CNN" for e in methods)
        facts = fact_table.query()
        predicates = {f.predicate for f in facts}
        assert PredicateType.APPLIES_TO in predicates
        assert PredicateType.ACHIEVES in predicates

    def test_object_wrapped_llm_output_still_works(self, fact_table):
        """Regression: Ollama JSON mode wrapping must not zero out extraction."""
        llm = MagicMock()
        llm.generate.side_effect = [
            json.dumps({"entities": json.loads(ENTITIES_JSON)}),
            json.dumps({"relations": json.loads(RELATIONS_JSON)}),
        ]
        fe = FactExtractor(llm_interface=llm)

        stats = fe.extract_from_text(
            "CNN applied to medical imaging achieves 92.3% Dice coefficient.",
            paper_id="paper1",
            fact_table=fact_table,
        )

        assert stats["entities_extracted"] == 3
        assert stats["llm_facts_extracted"] == 2

    def test_garbage_llm_falls_back_to_pattern_extraction(self, fact_table):
        """If LLM output is unusable after retry, pattern fallback must kick in."""
        llm = MagicMock()
        llm.generate.return_value = "no json here at all"
        fe = FactExtractor(llm_interface=llm)

        stats = fe.extract_from_text(
            "We use CNN and evaluate on ImageNet, achieving 95% accuracy.",
            paper_id="paper1",
            fact_table=fact_table,
        )

        # Pattern-based extraction should still find CNN / ImageNet / accuracy
        assert stats["entities_extracted"] > 0
