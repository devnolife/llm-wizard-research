import threading

from app.services.analysis_queue import AnalysisJobQueue
from app.utils import job_store


def test_local_queue_claims_and_completes_a_durable_job(tmp_path):
    job_store.load_jobs(tmp_path / "analysis_jobs.sqlite3")
    job_store.save_job(
        "job-1",
        {
            "status": "queued",
            "payload": {"pdf_paths": ["/tmp/example.pdf"]},
            "max_attempts": 2,
        },
    )
    completed = threading.Event()

    def handler(job_id):
        job_store.update_job(job_id, status="completed", progress=100, message="done")
        completed.set()

    queue = AnalysisJobQueue(max_workers=2, poll_interval=0.01)
    try:
        queue.start(handler)
        assert completed.wait(timeout=2)
    finally:
        queue.stop()

    job = job_store.get_job("job-1")
    assert job["status"] == "completed"
    assert job["attempt"] == 1
    assert job_store.get_job_events("job-1")
