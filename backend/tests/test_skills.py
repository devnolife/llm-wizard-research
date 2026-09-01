"""Contract tests for the AI-Research-SKILLs endpoints (no LLM network)."""

import pytest
from fastapi.testclient import TestClient

from app.api.routes import skills as skills_route
from app.main import app


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def fake_skills_dir(tmp_path, monkeypatch):
    d = tmp_path / "skills"
    (d / "demo-skill").mkdir(parents=True)
    (d / "demo-skill" / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Skill demo untuk pengujian\n  unit backend.\nversion: 1.0.0\n---\n\n# Demo\nGunakan metode X.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skills_route, "SKILLS_DIR", d)
    return d


@pytest.mark.api
def test_list_skills_reads_frontmatter(client, fake_skills_dir):
    response = client.get("/api/skills")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["skills"][0]["id"] == "demo-skill"
    assert body["skills"][0]["name"] == "demo-skill"
    assert "Skill demo untuk pengujian unit backend." == body["skills"][0]["description"]


@pytest.mark.api
def test_list_skills_missing_dir_is_empty(client, tmp_path, monkeypatch):
    monkeypatch.setattr(skills_route, "SKILLS_DIR", tmp_path / "tidak-ada")
    response = client.get("/api/skills")
    assert response.status_code == 200
    assert response.json() == {
        "skills": [], "total": 0, "skills_dir": str(tmp_path / "tidak-ada")
    }


@pytest.mark.api
def test_ask_uses_copilot_with_skill_as_system(client, fake_skills_dir, monkeypatch):
    captured = {}

    def fake_copilot(prompt, system="", **kwargs):
        captured["prompt"] = prompt
        captured["system"] = system
        return "Jawaban terpandu skill.", "copilot:claude-sonnet-5"

    monkeypatch.setattr(skills_route.copilot_client, "generate", fake_copilot)

    response = client.post("/api/skills/ask", json={
        "skill": "demo-skill", "question": "Bagaimana menerapkan metode X?"
    })

    assert response.status_code == 200
    body = response.json()
    assert body["engine"] == "GitHub Copilot (claude-sonnet-5)"
    assert body["answer"] == "Jawaban terpandu skill."
    assert "Gunakan metode X." in captured["system"]
    assert captured["prompt"] == "Bagaimana menerapkan metode X?"


@pytest.mark.api
def test_ask_falls_back_to_local_llm(client, fake_skills_dir, monkeypatch):
    monkeypatch.setattr(skills_route.copilot_client, "generate", lambda *a, **k: None)

    class FakeGLM:
        def generate(self, prompt, **kwargs):
            return "Jawaban dari Ollama."

    monkeypatch.setattr(skills_route, "get_glm_interface", lambda: FakeGLM())

    response = client.post("/api/skills/ask", json={
        "skill": "demo-skill", "question": "Bagaimana menerapkan metode X?"
    })

    body = response.json()
    assert body["engine"] == "LLM lokal (Ollama)"
    assert body["answer"] == "Jawaban dari Ollama."


@pytest.mark.api
def test_ask_unknown_skill_404(client, fake_skills_dir, monkeypatch):
    monkeypatch.setattr(skills_route.copilot_client, "generate", lambda *a, **k: None)
    response = client.post("/api/skills/ask", json={
        "skill": "tidak-ada", "question": "Apapun pertanyaannya?"
    })
    assert response.status_code == 404


@pytest.mark.api
def test_ask_rejects_path_traversal(client, fake_skills_dir):
    response = client.post("/api/skills/ask", json={
        "skill": "../../etc", "question": "Coba tembus direktori?"
    })
    assert response.status_code == 400


@pytest.fixture
def two_skills_dir(tmp_path, monkeypatch):
    d = tmp_path / "skills"
    for sid, desc in [
        ("brainstorming-research-ideas", "Structured ideation frameworks for research"),
        ("ml-paper-writing", "Writing ML conference papers with strong methodology"),
    ]:
        (d / sid).mkdir(parents=True)
        (d / sid / "SKILL.md").write_text(
            f"---\nname: {sid}\ndescription: {desc}\n---\n\n# {sid}\nPanduan {sid}.\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(skills_route, "SKILLS_DIR", d)
    return d


@pytest.mark.api
def test_recommend_llm_routes_and_composes(client, two_skills_dir, monkeypatch):
    calls = []

    def fake_copilot(prompt, system="", **kwargs):
        calls.append({"prompt": prompt, "system": system})
        if len(calls) == 1:  # routing
            return (
                '{"skills": ["ml-paper-writing"], "reason": "paling relevan"}',
                "copilot:claude-sonnet-5",
            )
        return (  # komposisi rekomendasi
            '{"title": "Judul Riset", "background": "Latar.", '
            '"problem_statements": ["RM1"], "objectives": ["T1"], '
            '"methodology": [{"step": "Studi Literatur", "description": "d", "tools": "arXiv"}], '
            '"experiments": [{"name": "E1", "design": "ablasi", "metrics": "F1"}], '
            '"contributions": ["K1"], "risks": ["R1"], "keywords": ["ocr receipt"]}',
            "copilot:claude-sonnet-5",
        )

    monkeypatch.setattr(skills_route.copilot_client, "generate", fake_copilot)

    response = client.post("/api/skills/recommend", json={
        "idea": "Sistem ekstraksi struk belanja dengan OCR dan LLM"
    })

    assert response.status_code == 200
    body = response.json()
    assert body["skills_used"] == [{"id": "ml-paper-writing", "name": "ml-paper-writing"}]
    assert body["routing_reason"] == "paling relevan"
    assert body["recommendation"]["title"] == "Judul Riset"
    assert body["recommendation"]["methodology"][0]["step"] == "Studi Literatur"
    # Panggilan ke-2 harus memuat dokumen skill terpilih sebagai panduan
    assert "Panduan ml-paper-writing." in calls[1]["system"]
    # Katalog dikirim ke router
    assert "brainstorming-research-ideas" in calls[0]["prompt"]


@pytest.mark.api
def test_recommend_router_falls_back_to_heuristic(client, two_skills_dir, monkeypatch):
    calls = []

    def fake_copilot(prompt, system="", **kwargs):
        calls.append(prompt)
        if len(calls) == 1:
            return "bukan json sama sekali", "copilot:claude-sonnet-5"
        return '{"title": "Judul Heuristik"}', "copilot:claude-sonnet-5"

    monkeypatch.setattr(skills_route.copilot_client, "generate", fake_copilot)

    response = client.post("/api/skills/recommend", json={
        "idea": "Structured ideation frameworks for research methodology paper"
    })

    assert response.status_code == 200
    body = response.json()
    assert body["routing_engine"] == "heuristik"
    assert len(body["skills_used"]) >= 1
    assert body["recommendation"]["title"] == "Judul Heuristik"


@pytest.mark.api
def test_recommend_invalid_final_json_502(client, two_skills_dir, monkeypatch):
    def fake_copilot(prompt, system="", **kwargs):
        if "Skill catalog" in prompt:
            return '{"skills": ["ml-paper-writing"], "reason": "ok"}', "copilot:m"
        return "html error page", "copilot:m"

    monkeypatch.setattr(skills_route.copilot_client, "generate", fake_copilot)

    response = client.post("/api/skills/recommend", json={
        "idea": "Sistem ekstraksi struk belanja dengan OCR"
    })
    assert response.status_code == 502
