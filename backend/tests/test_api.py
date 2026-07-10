"""FastAPI contract tests that never require Ollama, OCR, or a real corpus."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.routes import analysis, documents, health
from app.main import app
from app.utils import job_store


@pytest.fixture(autouse=True)
def isolated_job_store(tmp_path):
    """Point durable jobs/conversations at a temporary SQLite database."""
    job_store.load_jobs(tmp_path / "analysis_jobs.sqlite3")
    yield


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.mark.api
def test_health_endpoint_uses_mocked_dependencies(client, monkeypatch):
    glm = Mock()

    async def health_check():
        return {"status": "healthy"}

    glm.health_check = health_check
    vector_store = Mock()
    vector_store.count.return_value = 0
    monkeypatch.setattr(health, "get_glm_interface", lambda: glm)
    monkeypatch.setattr(health, "get_vector_store", lambda: vector_store)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["components"] == {"glm": True, "vector_store": True}


@pytest.mark.api
def test_chat_history_isolated_by_conversation_id(client, monkeypatch):
    class FakeGLM:
        def __init__(self):
            self.histories = []

        def chat(self, *, message, history=None, **_):
            self.histories.append(list(history or []))
            return f"answer:{message}"

    glm = FakeGLM()
    retriever = Mock()
    retriever.retrieve.return_value = []
    monkeypatch.setattr(analysis, "get_glm_interface", lambda: glm)
    monkeypatch.setattr(analysis, "get_retriever", lambda: retriever)

    first = client.post("/api/chat", json={"message": "paper A", "conversation_id": "a"})
    second = client.post("/api/chat", json={"message": "follow up", "conversation_id": "a"})
    other = client.post("/api/chat", json={"message": "paper B", "conversation_id": "b"})

    assert first.status_code == second.status_code == other.status_code == 200
    assert glm.histories[0] == []
    assert [item["content"] for item in glm.histories[1]] == ["paper A", "answer:paper A"]
    assert glm.histories[2] == []


@pytest.mark.api
def test_chat_reset_removes_only_requested_session(client, monkeypatch):
    glm = Mock()
    glm.chat.return_value = "ok"
    retriever = Mock()
    retriever.retrieve.return_value = []
    monkeypatch.setattr(analysis, "get_glm_interface", lambda: glm)
    monkeypatch.setattr(analysis, "get_retriever", lambda: retriever)

    client.post("/api/chat", json={"message": "one", "conversation_id": "a"})
    client.post("/api/chat", json={"message": "two", "conversation_id": "b"})
    response = client.delete("/api/chat/a")

    assert response.status_code == 200
    assert job_store.get_conversation_messages("a") == []
    assert [message["content"] for message in job_store.get_conversation_messages("b")] == ["two", "ok"]


@pytest.mark.api
def test_chat_rejects_an_empty_message_before_persisting(client):
    response = client.post("/api/chat", json={"message": "", "conversation_id": "empty"})

    assert response.status_code == 422
    assert job_store.get_conversation_messages("empty") == []


@pytest.mark.api
def test_job_status_and_cancel_contract(client):
    job_store.save_job(
        "queued-job",
        {
            "status": "queued",
            "progress": 0,
            "message": "queued",
            "payload": {"pdf_paths": ["/tmp/input.pdf"]},
        },
    )

    status = client.get("/api/analysis-status/queued-job")
    cancel = client.post("/api/analysis-status/queued-job/cancel")

    assert status.status_code == 200
    assert status.json()["status"] == "queued"
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"


@pytest.mark.api
def test_delete_missing_document_remains_404(client, monkeypatch):
    vector_store = Mock()
    vector_store.delete_document.return_value = False
    monkeypatch.setattr(documents, "get_vector_store", lambda: vector_store)

    response = client.delete("/api/documents/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.api
def test_graph_endpoint_uses_requested_job_snapshot_not_experiment_fallback(client):
    job_store.save_job(
        "graph-job",
        {
            "status": "completed",
            "progress": 100,
            "results": {},
            "graph_snapshot": {
                "facts": [
                    {
                        "subject": "Method A",
                        "subject_type": "METHOD",
                        "predicate": "USES_METHOD",
                        "object": "Dataset B",
                        "object_type": "DATASET",
                        "confidence": 0.9,
                        "source_paper": "paper.pdf",
                    }
                ],
                "raw_graph": {"nodes": [], "edges": []},
            },
        },
    )

    response = client.get("/api/graph", params={"job_id": "graph-job"})

    assert response.status_code == 200
    assert response.json()["source"] == "job_snapshot"
    assert response.json()["job_id"] == "graph-job"
    assert {node["label"] for node in response.json()["nodes"]} == {"Method A", "Dataset B"}
