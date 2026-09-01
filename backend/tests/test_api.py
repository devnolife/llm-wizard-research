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


@pytest.fixture
def reanalyze_env(tmp_path, monkeypatch):
    """Isolated config + queue for the reanalyze endpoint."""
    from types import SimpleNamespace

    config = SimpleNamespace(
        data=SimpleNamespace(raw_path=str(tmp_path / "raw")),
        queue=SimpleNamespace(max_attempts=1),
    )
    queue = Mock()
    monkeypatch.setattr(analysis, "get_config", lambda: config)
    monkeypatch.setattr(analysis, "get_analysis_queue", lambda: queue)
    return tmp_path, queue


@pytest.mark.api
def test_reanalyze_creates_new_job_from_retained_pdfs(client, reanalyze_env):
    tmp_path, queue = reanalyze_env
    source_dir = tmp_path / "source-job"
    source_dir.mkdir()
    pdf = source_dir / "00_paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    job_store.save_job(
        "done-job",
        {
            "status": "completed",
            "progress": 100,
            "message": "Analysis complete!",
            "payload": {"pdf_paths": [str(pdf)], "files": [{"name": "paper.pdf"}]},
        },
    )

    response = client.post("/api/analysis-jobs/done-job/reanalyze")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["source_job_id"] == "done-job"
    assert body["files_count"] == 1
    new_job = job_store.get_job(body["job_id"])
    assert new_job["status"] == "queued"
    assert new_job["payload"]["reanalyzed_from"] == "done-job"
    copied = [p for p in map(str, new_job["payload"]["pdf_paths"])]
    assert len(copied) == 1 and copied[0] != str(pdf)
    from pathlib import Path as _Path

    assert _Path(copied[0]).read_bytes() == b"%PDF-1.4 test"
    # Source job stays untouched for comparison.
    assert job_store.get_job("done-job")["status"] == "completed"
    queue.notify.assert_called_once()


@pytest.mark.api
def test_reanalyze_unknown_job_is_404(client, reanalyze_env):
    response = client.post("/api/analysis-jobs/missing-job/reanalyze")

    assert response.status_code == 404


@pytest.mark.api
def test_reanalyze_without_retained_pdfs_is_409(client, reanalyze_env):
    job_store.save_job(
        "gone-job",
        {
            "status": "completed",
            "progress": 100,
            "message": "Analysis complete!",
            "payload": {"pdf_paths": ["/nonexistent/input.pdf"]},
        },
    )

    response = client.post("/api/analysis-jobs/gone-job/reanalyze")

    assert response.status_code == 409


@pytest.mark.api
def test_analysis_jobs_list_returns_recent_summaries(client):
    job_store.save_job(
        "list-job",
        {
            "status": "completed",
            "progress": 100,
            "message": "Analysis complete!",
            "payload": {"pdf_paths": ["/tmp/paper_satu.pdf"]},
            "results": {
                "files_processed": 1,
                "topics": ["t1", "t2"],
                "gaps": [{"title": "g"}],
                "recommendations": [{"title": "r"}],
                "llm_info": {"model": "llama3.2"},
            },
        },
    )

    response = client.get("/api/analysis-jobs", params={"limit": 5})

    assert response.status_code == 200
    body = response.json()
    entry = next(j for j in body["jobs"] if j["job_id"] == "list-job")
    assert entry["status"] == "completed"
    assert entry["files"] == ["paper_satu.pdf"]
    assert entry["topics_count"] == 2
    assert entry["gaps_count"] == 1
    assert entry["recommendations_count"] == 1
    assert entry["model"] == "llama3.2"
    assert "results" not in entry


@pytest.mark.api
def test_delete_analysis_job_removes_job_events_and_artifacts(client):
    job_store.save_job(
        "delete-job",
        {"status": "completed", "progress": 100, "message": "done"},
    )
    job_store.record_job_event("delete-job", "job.created", status="queued")
    job_store.add_stage_artifact("delete-job", "topics", "result", label="Topik")

    response = client.delete("/api/analysis-jobs/delete-job")

    assert response.status_code == 200
    assert response.json() == {"deleted": True, "job_id": "delete-job"}
    assert job_store.get_job("delete-job") is None
    assert job_store.get_job_events("delete-job") == []
    assert job_store.get_stage_artifacts("delete-job") == []
    assert client.get("/api/analysis-status/delete-job").status_code == 404


@pytest.mark.api
def test_delete_analysis_job_missing_returns_404(client):
    response = client.delete("/api/analysis-jobs/tidak-ada")
    assert response.status_code == 404


@pytest.mark.api
def test_delete_analysis_job_refuses_active_job(client):
    job_store.save_job(
        "delete-running",
        {"status": "running", "progress": 40, "message": "Processing..."},
    )

    response = client.delete("/api/analysis-jobs/delete-running")

    assert response.status_code == 409
    assert job_store.get_job("delete-running") is not None


@pytest.mark.api
def test_job_events_endpoint_returns_ordered_sanitized_history(client):
    job_store.save_job(
        "events-job",
        {"status": "running", "progress": 42, "message": "Processing PDFs..."},
    )
    job_store.record_job_event("events-job", "job.created", status="queued", data={"file_count": 2})
    job_store.record_job_event(
        "events-job",
        "file.completed",
        phase="ingestion",
        status="running",
        duration_ms=1500,
        data={"file": "paper.pdf", "extraction_method": "ocrd_text_layer", "chunks": ["a", "b", "c"]},
    )
    job_store.record_job_event("events-job", "phase.started", phase="topics", status="running")

    response = client.get("/api/analysis-status/events-job/events")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "events-job"
    assert body["status"] == "running"
    assert body["progress"] == 42
    events = body["events"]
    assert [event["type"] for event in events] == ["job.created", "file.completed", "phase.started"]
    assert [event["id"] for event in events] == sorted(event["id"] for event in events)
    file_event = events[1]
    assert file_event["phase"] == "ingestion"
    assert file_event["duration_ms"] == 1500
    assert file_event["data"]["extraction_method"] == "ocrd_text_layer"
    # Telemetry sanitizer collapses lists to their length (metadata-only contract).
    assert file_event["data"]["chunks"] == 3

    tail = client.get(
        "/api/analysis-status/events-job/events",
        params={"after_event_id": events[0]["id"]},
    )
    assert [event["type"] for event in tail.json()["events"]] == ["file.completed", "phase.started"]


@pytest.mark.api
def test_job_events_endpoint_unknown_job_is_404(client):
    response = client.get("/api/analysis-status/unknown-job/events")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


@pytest.mark.api
def test_job_artifacts_endpoint_returns_stage_content(client):
    job_store.save_job("artifact-job", {"status": "running", "progress": 30})
    job_store.add_stage_artifact(
        "artifact-job", "ingestion", "extraction", label="paper.pdf",
        payload={"preview": "Teks hasil ekstraksi dokumen", "extraction_method": "ocrd_text_layer"},
    )
    job_store.add_stage_artifact(
        "artifact-job", "topics", "llm", label="Ekstraksi topik utama",
        payload={"prompt": "Analisis konten berikut...", "response": "1. Topik A\n2. Topik B"},
    )

    response = client.get("/api/analysis-status/artifact-job/artifacts")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "artifact-job"
    artifacts = body["artifacts"]
    assert [a["kind"] for a in artifacts] == ["extraction", "llm"]
    assert artifacts[0]["payload"]["preview"] == "Teks hasil ekstraksi dokumen"
    assert artifacts[1]["payload"]["prompt"].startswith("Analisis konten")
    assert artifacts[1]["payload"]["response"].startswith("1. Topik A")

    filtered = client.get(
        "/api/analysis-status/artifact-job/artifacts", params={"phase": "topics"}
    )
    assert [a["phase"] for a in filtered.json()["artifacts"]] == ["topics"]


@pytest.mark.api
def test_job_artifacts_endpoint_unknown_job_is_404(client):
    response = client.get("/api/analysis-status/unknown-job/artifacts")

    assert response.status_code == 404


@pytest.mark.api
def test_system_stats_endpoint_reports_cpu_ram_gpu_shape(client):
    response = client.get("/api/system-stats")

    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["cpu"]["percent"] <= 100
    assert body["cpu"]["cores"] > 0
    assert len(body["cpu"]["load_avg"]) == 3
    assert body["memory"]["total_mb"] > 0
    assert 0 <= body["memory"]["percent"] <= 100
    assert body["disk"]["total_gb"] > 0
    assert isinstance(body["gpus"], list)
    for gpu in body["gpus"]:
        assert {"index", "name", "memory_used_mb", "memory_total_mb",
                "utilization_percent", "processes"} <= set(gpu)


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


def test_uploaded_paper_similarity_is_a_scoped_percentage():
    class EmbeddingModel:
        def encode(self, texts, show_progress_bar=False):
            assert show_progress_bar is False
            return [[1.0, 0.0], [0.6, 0.8]]

    class VectorStore:
        embedding_model = EmbeddingModel()

    papers = [{"content": "paper one"}, {"content": "paper two"}]

    analysis._add_uploaded_paper_similarity(papers, VectorStore())

    assert [paper["similarity_percent"] for paper in papers] == [60, 60]


def test_marked_paper_suggestions_require_two_known_source_titles():
        parsed = analysis._parse_selection_json(
                '''{
                    "suggestions": [
                        {
                            "title": "Arah yang didukung",
                            "rationale": "Ada kontras metode pada dua paper.",
                            "basis": "Paper pertama memakai A, paper kedua memakai B.",
                            "source_papers": ["Paper Alpha", "Paper Beta"],
                            "gap_type": "FRAGMENTATION"
                        },
                        {
                            "title": "Arah generik",
                            "source_papers": ["Paper Alpha"]
                        }
                    ]
                }'''
        )

        grounded = analysis._ground_selection_suggestions(
                parsed["suggestions"],
                [{"title": "Paper Alpha"}, {"title": "Paper Beta"}],
        )

        assert len(grounded) == 1
        assert grounded[0]["source_papers"] == ["Paper Alpha", "Paper Beta"]
        assert grounded[0]["gap_type"] == "FRAGMENTATION"
