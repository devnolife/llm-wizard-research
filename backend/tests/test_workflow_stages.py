"""Unit tests — workflow-stage mining (core/gap_detection/workflow_stages.py).

Offline: no LLM, no embeddings (lexical matcher).
"""

import json

import pytest

from app.core.gap_detection.workflow_stages import (
    MIN_PAPERS_FOR_HOMOGENEITY,
    STAGE_KEYS,
    STAGE_LABELS,
    build_workflow_prompt,
    compare_workflows,
    parse_workflow_json,
    select_workflow_context,
    verify_workflow,
)

PAPER_TEXT = (
    "We evaluate on the CASIA v2 image forgery dataset containing 12,614 images. "
    "Images were resized to 256x256 and normalised before training. "
    "A ResNet-50 convolutional network is fine-tuned for classification. "
    "Performance is reported using accuracy and F1-score on a held-out test split."
)


def _llm_json(**stages):
    payload = {key: {"value": "", "kutipan": ""} for key in STAGE_KEYS}
    payload.update(stages)
    return json.dumps(payload)


class TestPrompt:
    def test_prompt_lists_every_stage_and_forbids_invention(self):
        prompt = build_workflow_prompt("Judul Uji", "isi metode")
        for key in STAGE_KEYS:
            assert f"- {key}:" in prompt
        assert "JANGAN" in prompt and "verbatim" in prompt
        assert "Judul Uji" in prompt and "isi metode" in prompt


class TestParse:
    def test_parses_fenced_json_with_alias_keys_and_string_values(self):
        raw = (
            "Berikut hasilnya:\n```json\n"
            + json.dumps({
                "dataset": {"value": "CASIA v2", "quote": "CASIA v2 image forgery dataset"},
                "Method": "ResNet-50 fine-tuning",
                "evaluation_metrics": {"value": "", "kutipan": ""},
                "unknown_stage": {"value": "x"},
            })
            + "\n```"
        )
        stages = parse_workflow_json(raw)
        assert stages["data_source"] == {
            "value": "CASIA v2", "kutipan": "CASIA v2 image forgery dataset"}
        assert stages["method_model"] == {"value": "ResNet-50 fine-tuning", "kutipan": ""}
        assert "evaluation_metrics" not in stages  # empty = not stated
        assert "unknown_stage" not in stages

    def test_garbage_and_placeholder_values_yield_nothing(self):
        assert parse_workflow_json("no json here") == {}
        assert parse_workflow_json("[1, 2]") == {}
        assert parse_workflow_json(_llm_json(
            method_model={"value": "tidak dinyatakan", "kutipan": ""})) == {}


class TestVerify:
    def test_quote_present_in_text_is_verified_and_absent_quote_is_not(self):
        stages = parse_workflow_json(_llm_json(
            data_source={"value": "CASIA v2", "kutipan": "CASIA v2 image forgery dataset"},
            method_model={"value": "ResNet-50",
                          "kutipan": "a transformer with eight attention heads"},
            evaluation_metrics={"value": "accuracy and F1", "kutipan": ""},
        ))
        verified = verify_workflow(stages, PAPER_TEXT)
        assert verified["data_source"]["verified"] is True
        assert verified["data_source"]["match_score"] >= 0.82
        # Hallucinated quote: value kept, but never presentable as verbatim.
        assert verified["method_model"]["verified"] is False
        assert verified["method_model"]["value"] == "ResNet-50"
        assert verified["evaluation_metrics"]["verified"] is False
        assert verified["evaluation_metrics"]["match_score"] == 0.0

    def test_stage_order_follows_canonical_keys(self):
        verified = verify_workflow(
            {"tools_environment": {"value": "PyTorch"}, "data_source": {"value": "CASIA"}},
            PAPER_TEXT,
        )
        assert list(verified) == ["data_source", "tools_environment"]


class TestContextSelection:
    class _Chunk:
        def __init__(self, content, section, is_reference=False):
            self.content = content
            self.metadata = {"section_normalized": section, "is_reference": is_reference}

    def test_method_and_result_chunks_are_preferred_over_the_head(self):
        chunks = [
            self._Chunk("Intro text " * 100, "introduction"),
            self._Chunk("METHOD BODY " * 80, "methods"),
            self._Chunk("RESULT BODY " * 80, "results"),
            self._Chunk("[1] Some reference", "references", is_reference=True),
        ]
        ctx = select_workflow_context(chunks, "HEAD " * 500)
        assert ctx.startswith("METHOD BODY")
        assert "RESULT BODY" in ctx and "HEAD" not in ctx and "Some reference" not in ctx

    def test_thin_sections_fall_back_to_document_head_and_respect_limit(self):
        chunks = [{"text": "short methods", "section_normalized": "methods"}]
        ctx = select_workflow_context(chunks, "HEAD " * 2000, max_chars=500)
        assert ctx.startswith("short methods") and "HEAD" in ctx
        assert len(ctx) <= 500


class TestCompare:
    @staticmethod
    def _wf(model, metric, metric_quote=None, verified=True, extra=None):
        wf = {
            "method_model": {"value": model, "kutipan": "", "verified": False, "match_score": 0.0},
            "evaluation_metrics": {
                "value": metric,
                "kutipan": metric_quote or "",
                "verified": bool(metric_quote) and verified,
                "match_score": 0.9 if metric_quote else 0.0,
            },
        }
        wf.update(extra or {})
        return wf

    def test_single_variant_on_three_papers_is_homogeneous_with_verified_quotes(self):
        workflows = {
            "a.pdf": self._wf("CNN", "accuracy", "reported using accuracy"),
            "b.pdf": self._wf("SVM", "accuracy", "we report accuracy only"),
            "c.pdf": self._wf("random forest", "accuracy", "accuracy is used", verified=False),
        }
        matrix = compare_workflows(workflows)
        by_stage = {s.stage: s for s in matrix.stages}
        metrics = by_stage["evaluation_metrics"]
        assert metrics.homogeneous is True
        assert metrics.dominant.value == "accuracy"
        assert metrics.dominant.papers == ["a.pdf", "b.pdf", "c.pdf"]
        # Only verified quotes are carried as verbatim evidence.
        assert [q["source"] for q in metrics.dominant.quotes] == ["a.pdf", "b.pdf"]
        assert by_stage["method_model"].homogeneous is False
        assert len(by_stage["method_model"].variants) == 3
        assert matrix.verified_quotes == 2 and matrix.total_quotes == 3
        assert [h["stage"] for h in matrix.to_dict()["homogeneous"]] == ["evaluation_metrics"]

    def test_equivalent_phrasings_collapse_into_one_variant(self):
        workflows = {
            "a.pdf": self._wf("deep learning model", "accuracy"),
            "b.pdf": self._wf("deep learning models", "accuracy"),
            "c.pdf": self._wf("a deep learning model", "accuracy"),
        }
        matrix = compare_workflows(workflows)
        model = next(s for s in matrix.stages if s.stage == "method_model")
        assert len(model.variants) == 1 and model.homogeneous is True

    def test_unstated_papers_are_reported_and_do_not_count_as_agreement(self):
        workflows = {
            "a.pdf": self._wf("CNN", "accuracy"),
            "b.pdf": self._wf("CNN", "accuracy"),
            "c.pdf": {"method_model": {"value": "CNN", "kutipan": "", "verified": False,
                                       "match_score": 0.0}},
        }
        matrix = compare_workflows(workflows)
        by_stage = {s.stage: s for s in matrix.stages}
        assert by_stage["method_model"].homogeneous is True
        metrics = by_stage["evaluation_metrics"]
        # Two papers agree, one is silent: below the >= 3 stated floor.
        assert metrics.homogeneous is False
        assert metrics.unstated_papers == ["c.pdf"]
        assert by_stage["data_source"].unstated_papers == ["a.pdf", "b.pdf", "c.pdf"]

    def test_floor_matches_the_legacy_methodology_check(self):
        assert MIN_PAPERS_FOR_HOMOGENEITY == 3
        workflows = {"a.pdf": self._wf("CNN", "accuracy"), "b.pdf": self._wf("CNN", "accuracy")}
        assert compare_workflows(workflows).homogeneous == []

    def test_to_dict_is_json_serialisable_and_labelled(self):
        matrix = compare_workflows({"a.pdf": self._wf("CNN", "accuracy")})
        data = json.loads(json.dumps(matrix.to_dict()))
        assert data["n_papers"] == 1 and data["matcher"] == "lexical"
        assert [s["label"] for s in data["stages"]] == [STAGE_LABELS[k] for k in STAGE_KEYS]
