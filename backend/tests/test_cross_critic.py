"""Tests for the cross-model critic debate (mode cross-critic, H10)."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments"))

from cross_critic import CrossCritic, _parse_json_array  # noqa: E402


class FakeLLM:
    """Deterministic stand-in for GLMInterface."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        if not self.responses:
            raise RuntimeError("no scripted response left")
        return self.responses.pop(0)


def make_indicator(desc="gap", conf=0.7, related=None):
    return SimpleNamespace(
        indicator_type="INCOMPLETENESS",
        description=desc,
        confidence=conf,
        evidence=["e1", "e2"],
        related_papers=related or ["paper_a.pdf", "paper_b.pdf"],
        detection_method="aspect_coverage",
    )


class TestParseJsonArray:
    def test_plain_array(self):
        assert _parse_json_array('[{"a": 1}]') == [{"a": 1}]

    def test_fenced_array(self):
        assert _parse_json_array('```json\n[{"a": 1}]\n```') == [{"a": 1}]

    def test_with_preamble(self):
        assert _parse_json_array('Here you go:\n[{"a": 1}]') == [{"a": 1}]

    def test_garbage_returns_empty(self):
        assert _parse_json_array("not json at all") == []


class TestDebateIndicators:
    def test_all_keep(self):
        critic = FakeLLM([json.dumps([
            {"index": 0, "verdict": "KEEP", "reason": "grounded"},
            {"index": 1, "verdict": "KEEP", "reason": "ok"},
        ])])
        defender = FakeLLM([])
        cc = CrossCritic(critic_llm=critic, defender_llm=defender)
        res = cc.debate_indicators("topic", [make_indicator(), make_indicator()])
        assert res["kept"] == 2 and res["rejected"] == 0
        assert all(d["keep"] for d in res["decisions"])
        assert len(defender.prompts) == 0  # no rejections → no defense round

    def test_reject_accepted_by_defender(self):
        critic = FakeLLM([json.dumps([
            {"index": 0, "verdict": "REJECT", "reason": "generic template"},
        ])])
        defender = FakeLLM([json.dumps([
            {"index": 0, "decision": "ACCEPT", "argument": ""},
        ])])
        cc = CrossCritic(critic_llm=critic, defender_llm=defender)
        res = cc.debate_indicators("topic", [make_indicator()])
        assert res["rejected"] == 1 and res["kept"] == 0 and res["defended"] == 0
        assert res["decisions"][0]["keep"] is False

    def test_reject_defended_survives(self):
        critic = FakeLLM([json.dumps([
            {"index": 0, "verdict": "REJECT", "reason": "no grounding"},
        ])])
        defender = FakeLLM([json.dumps([
            {"index": 0, "decision": "DEFEND", "argument": "fact (X, IMPROVES, Y) supports this"},
        ])])
        cc = CrossCritic(critic_llm=critic, defender_llm=defender)
        res = cc.debate_indicators("topic", [make_indicator()])
        assert res["kept"] == 1 and res["rejected"] == 0 and res["defended"] == 1
        assert res["decisions"][0]["defense"].startswith("fact (X")

    def test_critic_failure_fails_open(self):
        critic = FakeLLM([])  # raises
        cc = CrossCritic(critic_llm=critic, defender_llm=FakeLLM([]))
        res = cc.debate_indicators("topic", [make_indicator(), make_indicator()])
        assert res["kept"] == 2 and res["rejected"] == 0

    def test_defense_failure_rejections_stand(self):
        critic = FakeLLM([json.dumps([
            {"index": 0, "verdict": "REJECT", "reason": "bad"},
        ])])
        defender = FakeLLM([])  # raises
        cc = CrossCritic(critic_llm=critic, defender_llm=defender)
        res = cc.debate_indicators("topic", [make_indicator()])
        assert res["rejected"] == 1 and res["kept"] == 0

    def test_confidence_delta_clamped(self):
        critic = FakeLLM([json.dumps([
            {"index": 0, "verdict": "KEEP", "confidence_delta": -0.9},
        ])])
        cc = CrossCritic(critic_llm=critic, defender_llm=FakeLLM([]))
        res = cc.debate_indicators("topic", [make_indicator()])
        assert res["decisions"][0]["confidence_delta"] == -0.3

    def test_empty_indicators(self):
        cc = CrossCritic(critic_llm=FakeLLM([]), defender_llm=FakeLLM([]))
        res = cc.debate_indicators("topic", [])
        assert res == {"decisions": [], "kept": 0, "rejected": 0, "defended": 0}

    def test_payload_includes_inter_paper_context(self):
        """Critic prompt harus memuat daftar jurnal + related_papers per indikator."""
        critic = FakeLLM([json.dumps([{"index": 0, "verdict": "KEEP", "reason": "ok"}])])
        cc = CrossCritic(critic_llm=critic, defender_llm=FakeLLM([]))
        ind = make_indicator(related=["resnet_paper.pdf", "densenet_paper.pdf", "resnet_paper.pdf"])
        cc.debate_indicators(
            "topic", [ind],
            paper_titles=["Deep Residual Learning", "Densely Connected Nets"],
        )
        prompt = critic.prompts[0]
        assert "Deep Residual Learning" in prompt
        assert "Densely Connected Nets" in prompt
        assert '"related_papers_count": 2' in prompt  # deduplicated
        assert "INTER-PAPER" in prompt

    def test_single_paper_indicator_rejected_by_critic(self):
        """Indikator INCONSISTENCY yang merujuk 1 paper dapat di-REJECT dan dibuang."""
        critic = FakeLLM([json.dumps([
            {"index": 0, "verdict": "REJECT",
             "reason": "inter-paper violated: cites only one paper"},
        ])])
        defender = FakeLLM([json.dumps([
            {"index": 0, "decision": "ACCEPT", "argument": ""},
        ])])
        cc = CrossCritic(critic_llm=critic, defender_llm=defender)
        ind = make_indicator(related=["only_one.pdf"])
        res = cc.debate_indicators("topic", [ind])
        assert res["rejected"] == 1
        assert res["decisions"][0]["critic_reason"].startswith("inter-paper")


class TestCritiqueFacts:
    FACTS = [
        {"subject": "ResNet", "subject_type": "METHOD", "predicate": "APPLIES_TO",
         "object": "ImageNet", "object_type": "DOMAIN"},
        {"subject": "Table 1", "subject_type": "DATASET", "predicate": "REQUIRES_DATA",
         "object": "MobileNets", "object_type": "METHOD"},
    ]

    def test_flags_bad_fact(self):
        critic = FakeLLM([json.dumps([
            {"index": 1, "reason": "'Table 1' is not a dataset"},
        ])])
        cc = CrossCritic(critic_llm=critic, defender_llm=FakeLLM([]))
        bad = cc.critique_facts("EfficientNet", self.FACTS)
        assert bad == [{"index": 1, "reason": "'Table 1' is not a dataset"}]

    def test_out_of_range_index_ignored(self):
        critic = FakeLLM([json.dumps([{"index": 99, "reason": "x"}])])
        cc = CrossCritic(critic_llm=critic, defender_llm=FakeLLM([]))
        assert cc.critique_facts("p", self.FACTS) == []

    def test_failure_fails_open(self):
        cc = CrossCritic(critic_llm=FakeLLM([]), defender_llm=FakeLLM([]))
        assert cc.critique_facts("p", self.FACTS) == []

    def test_empty_facts_no_call(self):
        critic = FakeLLM([json.dumps([])])
        cc = CrossCritic(critic_llm=critic, defender_llm=FakeLLM([]))
        assert cc.critique_facts("p", []) == []
        assert critic.prompts == []
