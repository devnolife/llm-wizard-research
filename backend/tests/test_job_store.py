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
