"""Tests for the research pipeline endpoints."""

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes import research
from app.main import app
from app.services.research_pipeline import RESEARCH_STAGES
from app.utils import job_store

client = TestClient(app)

SCRATCH = Path(__file__).parent / ".scratch_research_api"

_MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def setup_module():
    """Arahkan job_store ke berkas sementara agar tes tidak mencemari basis data
    produksi — job uji di sana sempat diklaim worker analisis lalu gagal berulang.

    Harus .sqlite3: path .json memakai mode legacy dan artefak tetap ditulis ke
    basis data bawaan.
    """
    shutil.rmtree(SCRATCH, ignore_errors=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    job_store.load_jobs(SCRATCH / "analysis_jobs.sqlite3")


def teardown_module():
    shutil.rmtree(SCRATCH, ignore_errors=True)
    job_store.load_jobs()  # kembalikan ke lokasi bawaan


class TestStagesEndpoint:
    def test_lists_pipeline_stages_in_order(self):
        body = client.get("/api/research/stages").json()
        assert [s["key"] for s in body["stages"]] == [s[0] for s in RESEARCH_STAGES]

    def test_each_stage_carries_ui_metadata(self):
        for stage in client.get("/api/research/stages").json()["stages"]:
            assert stage["icon"] and stage["title"] and stage["description"]


class TestStartEndpoint:
    """The pipeline itself is stubbed; only the job hand-off is under test."""

    def setup_method(self):
        self._real = research._run_in_background
        self.calls: list = []
        research._run_in_background = lambda *a, **k: self.calls.append(a)
        self._dirs: list[Path] = []

    def teardown_method(self):
        research._run_in_background = self._real
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _start(self):
        resp = client.post(
            "/api/research/start",
            files=[("files", ("uji.pdf", _MINIMAL_PDF, "application/pdf"))],
        )
        if resp.status_code == 200:
            from app.utils.config_loader import get_config
            self._dirs.append(
                Path(get_config().data.raw_path) / "analysis_jobs" / resp.json()["job_id"])
        return resp

    def test_returns_job_id_and_stage_keys(self):
        body = self._start().json()
        assert body["success"] and body["files_count"] == 1
        assert body["stages"] == [s[0] for s in RESEARCH_STAGES]

    def test_job_is_persisted_as_research_pipeline(self):
        from app.utils.job_store import get_job

        job = get_job(self._start().json()["job_id"])
        assert job["pipeline"] == "research", "UI membedakan job lama vs penelitian lewat field ini"

    def test_job_starts_running_so_legacy_worker_cannot_claim_it(self):
        """Worker antrean lama mengklaim job `queued` apa pun tanpa cek pipeline."""
        from app.utils.job_store import get_job

        assert get_job(self._start().json()["job_id"])["status"] == "running"

    def test_background_worker_is_dispatched(self):
        self._start()
        assert len(self.calls) == 1, "pipeline harus dijalankan di latar belakang"

    def test_rejects_request_without_files(self):
        assert client.post("/api/research/start").status_code == 422
