import json
import shutil
from pathlib import Path

from app.utils import job_store


SCRATCH_DIR = Path(__file__).parent / ".scratch_job_store"


def setup_function():
    shutil.rmtree(SCRATCH_DIR, ignore_errors=True)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)


def teardown_function():
    shutil.rmtree(SCRATCH_DIR, ignore_errors=True)


def test_save_and_load_roundtrip():
    store_path = SCRATCH_DIR / "analysis_jobs.json"
    job_store.load_jobs(store_path)

    job_store.save_job("job-1", {"status": "completed", "progress": 100, "results": {"ok": True}})
    jobs = job_store.load_jobs(store_path)

    assert jobs["job-1"]["status"] == "completed"
    assert jobs["job-1"]["results"] == {"ok": True}


def test_load_marks_processing_jobs_interrupted():
    store_path = SCRATCH_DIR / "analysis_jobs.json"
    store_path.write_text(
        json.dumps({"job-1": {"status": "processing", "progress": 30, "message": "Running"}}),
        encoding="utf-8",
    )

    jobs = job_store.load_jobs(store_path)

    assert jobs["job-1"]["status"] == "interrupted"
    assert "di-restart" in jobs["job-1"]["message"]


def test_save_job_writes_valid_json_atomically_without_leftover_tmp():
    store_path = SCRATCH_DIR / "analysis_jobs.json"
    job_store.load_jobs(store_path)

    job_store.save_job("job-1", {"status": "completed"})
    job_store.save_job("job-2", {"status": "failed", "error": "boom"})

    data = json.loads(store_path.read_text(encoding="utf-8"))
    assert set(data) == {"job-1", "job-2"}
    assert not list(SCRATCH_DIR.glob("*.tmp"))
    assert not list(SCRATCH_DIR.glob(".*.tmp"))


def test_sqlite_claims_each_queued_job_once():
    store_path = SCRATCH_DIR / "analysis_jobs.sqlite3"
    job_store.load_jobs(store_path)
    job_store.save_job("job-1", {"status": "queued", "payload": {"pdf_paths": ["a.pdf"]}})
    job_store.save_job("job-2", {"status": "queued", "payload": {"pdf_paths": ["b.pdf"]}})

    first = job_store.claim_next_job()
    second = job_store.claim_next_job()
    third = job_store.claim_next_job()

    assert {first["job_id"], second["job_id"]} == {"job-1", "job-2"}
    assert first["status"] == second["status"] == "running"
    assert third is None


def test_sqlite_conversations_are_isolated_and_clearable():
    store_path = SCRATCH_DIR / "analysis_jobs.sqlite3"
    job_store.load_jobs(store_path)
    job_store.append_conversation_message("a", "user", "paper A")
    job_store.append_conversation_message("b", "user", "paper B")
    job_store.append_conversation_message("a", "assistant", "answer A")

    assert [item["content"] for item in job_store.get_conversation_messages("a")] == ["paper A", "answer A"]
    assert [item["content"] for item in job_store.get_conversation_messages("b")] == ["paper B"]
    assert job_store.clear_conversation("a")
    assert job_store.get_conversation_messages("a") == []


def test_sqlite_requeues_running_job_after_restart():
    store_path = SCRATCH_DIR / "analysis_jobs.sqlite3"
    job_store.load_jobs(store_path)
    job_store.save_job(
        "job-1",
        {"status": "running", "progress": 40, "payload": {"pdf_paths": ["a.pdf"]}},
    )

    jobs = job_store.load_jobs(store_path)

    assert jobs["job-1"]["status"] == "queued"
    assert "di-restart" in jobs["job-1"]["message"]


def test_stage_artifacts_roundtrip_keeps_content_and_order():
    store_path = SCRATCH_DIR / "analysis_jobs.sqlite3"
    job_store.load_jobs(store_path)
    job_store.save_job("job-art", {"status": "running"})

    job_store.add_stage_artifact(
        "job-art", "ingestion", "extraction", label="paper.pdf",
        payload={"preview": "Isi dokumen hasil ekstraksi", "chars": 123},
    )
    job_store.add_stage_artifact(
        "job-art", "topics", "llm", label="Ekstraksi topik",
        payload={"prompt": "Analisis konten...", "response": "1. Topik A"},
    )

    all_artifacts = job_store.get_stage_artifacts("job-art")
    assert [a["kind"] for a in all_artifacts] == ["extraction", "llm"]
    assert all_artifacts[0]["payload"]["preview"] == "Isi dokumen hasil ekstraksi"
    assert all_artifacts[1]["payload"]["prompt"] == "Analisis konten..."

    only_topics = job_store.get_stage_artifacts("job-art", phase="topics")
    assert len(only_topics) == 1
    assert only_topics[0]["label"] == "Ekstraksi topik"


def test_stage_artifacts_bound_long_strings_and_lists():
    store_path = SCRATCH_DIR / "analysis_jobs.sqlite3"
    job_store.load_jobs(store_path)
    job_store.save_job("job-big", {"status": "running"})

    job_store.add_stage_artifact(
        "job-big", "summary", "result",
        payload={"text": "x" * 10000, "items": list(range(200)), "nested": {"deep": "y" * 9000}},
        max_field_chars=100,
    )

    payload = job_store.get_stage_artifacts("job-big")[0]["payload"]
    assert payload["text"].startswith("x" * 100)
    assert payload["text"].endswith("…[terpotong]")
    assert len(payload["items"]) == 50
    assert payload["nested"]["deep"].endswith("…[terpotong]")


def test_cleanup_expired_removes_old_stage_artifacts():
    store_path = SCRATCH_DIR / "analysis_jobs.sqlite3"
    job_store.load_jobs(store_path)
    job_store.save_job("job-old", {"status": "running"})
    job_store.add_stage_artifact("job-old", "topics", "result", payload={"topics": ["a"]})

    fresh = job_store.cleanup_expired(telemetry_retention_days=14)
    assert fresh["artifacts"] == 0
    assert len(job_store.get_stage_artifacts("job-old")) == 1

    # Backdate the artifact past the retention window, then clean again.
    import sqlite3 as _sqlite3
    conn = _sqlite3.connect(store_path)
    conn.execute("UPDATE job_stage_artifacts SET created_at = created_at - 15*86400")
    conn.commit()
    conn.close()

    aged = job_store.cleanup_expired(telemetry_retention_days=14)
    assert aged["artifacts"] == 1
    assert job_store.get_stage_artifacts("job-old") == []


def test_retry_job_resets_attempt_counter_so_claim_succeeds():
    store_path = SCRATCH_DIR / "analysis_jobs.sqlite3"
    job_store.load_jobs(store_path)
    job_store.save_job(
        "job-retry",
        {
            "status": "failed",
            "attempt": 2,
            "max_attempts": 2,
            "payload": {"pdf_paths": ["/tmp/some.pdf"]},
        },
    )

    requeued = job_store.retry_job("job-retry")
    assert requeued is not None
    assert requeued["status"] == "queued"
    assert requeued["attempt"] == 0

    claimed = job_store.claim_next_job()
    assert claimed is not None
    assert claimed["job_id"] == "job-retry"
    assert claimed["status"] == "running"
    assert claimed["attempt"] == 1
