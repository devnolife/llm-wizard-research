"""Tests for skill guidance injection across the analysis pipeline."""

import pytest

from app.services import skill_guidance


@pytest.mark.api
def test_wrap_prompt_injects_skill_for_known_phase():
    prompt = "Identifikasi topik utama dari paper berikut."
    wrapped, used = skill_guidance.wrap_prompt("topics", prompt)

    assert used == ["brainstorming-research-ideas"]
    assert wrapped.endswith(prompt)
    assert "RESEARCH SKILL: brainstorming-research-ideas" in wrapped
    assert "AI-Research-SKILLs" in wrapped


@pytest.mark.api
def test_wrap_prompt_passthrough_for_unknown_phase():
    prompt = "Terjemahkan teks ini."
    wrapped, used = skill_guidance.wrap_prompt("translation", prompt)
    assert wrapped == prompt
    assert used == []


@pytest.mark.api
def test_excerpt_strips_frontmatter_and_caps_budget():
    text = skill_guidance._excerpt("ml-paper-writing", 500)
    assert text
    assert len(text) <= 500
    assert not text.startswith("---")
    assert "name:" not in text.split("\n")[0]


@pytest.mark.api
def test_all_mapped_skills_exist_on_disk():
    for phase, ids in skill_guidance.PHASE_SKILLS.items():
        for sid in ids:
            assert (skill_guidance.SKILLS_DIR / sid / "SKILL.md").is_file(), (
                f"Skill '{sid}' untuk fase '{phase}' tidak ada di disk"
            )


@pytest.mark.api
def test_missing_skill_returns_prompt_unchanged(monkeypatch):
    monkeypatch.setitem(skill_guidance.PHASE_SKILLS, "ghost", ["skill-tidak-ada"])
    wrapped, used = skill_guidance.wrap_prompt("ghost", "prompt asli")
    assert wrapped == "prompt asli"
    assert used == []
