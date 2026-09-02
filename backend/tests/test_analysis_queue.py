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


def test_queue_dispatches_jobs_by_pipeline_field(tmp_path):
    """A research job must reach the research handler, a legacy job (no
    ``pipeline`` field) the default one — a restart requeues both kinds."""
    job_store.load_jobs(tmp_path / "analysis_jobs.sqlite3")
    job_store.save_job("legacy-job", {"status": "queued", "payload": {"pdf_paths": ["/tmp/a.pdf"]}})
    job_store.save_job(
        "research-job",
        {"status": "queued", "pipeline": "research", "payload": {"pdf_paths": ["/tmp/b.pdf"]}},
    )
    seen: dict[str, str] = {}
    both_done = threading.Barrier(3, timeout=3)

    def _handler(name):
        def handler(job_id):
            seen[job_id] = name
            job_store.update_job(job_id, status="completed", progress=100)
            both_done.wait()
        return handler

    queue = AnalysisJobQueue(max_workers=2, poll_interval=0.01)
    queue.register("research", _handler("research"))
    try:
        queue.start(_handler("legacy"))
        both_done.wait()
    finally:
        queue.stop()

    assert seen == {"legacy-job": "legacy", "research-job": "research"}


def test_resolve_handler_falls_back_to_default_for_unknown_pipeline():
    queue = AnalysisJobQueue(max_workers=1)
    default = object()
    research = object()
    queue._handler = default  # what start() would set
    queue.register("research", research)

    assert queue.resolve_handler({"pipeline": "research"}) is research
    assert queue.resolve_handler({"pipeline": "something-else"}) is default
    assert queue.resolve_handler({}) is default
    assert queue.resolve_handler(None) is default


def test_job_without_any_handler_fails_clearly_instead_of_hanging(tmp_path):
    job_store.load_jobs(tmp_path / "analysis_jobs.sqlite3")
    job_store.save_job("orphan", {"status": "queued", "payload": {"pdf_paths": ["/tmp/x.pdf"]}})
    queue = AnalysisJobQueue(max_workers=1, poll_interval=0.01)
    queue._handler = None
    queue._execute("orphan")

    job = job_store.get_job("orphan")
    assert job["status"] == "failed"
    assert "tidak dikenal" in job["error"]
