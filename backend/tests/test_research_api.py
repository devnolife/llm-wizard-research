"""Tests for the research pipeline endpoints."""

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

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
    """The pipeline itself never runs here; only the durable hand-off is tested."""

    def setup_method(self):
        from app.api.routes import research as research_routes
        from app.services import analysis_queue

        self.notified: list = []
        queue = analysis_queue.AnalysisJobQueue(max_workers=1)
        queue.notify = lambda: self.notified.append(True)  # type: ignore[method-assign]
        self._orig = research_routes.get_analysis_queue
        research_routes.get_analysis_queue = lambda: queue
        self._dirs: list[Path] = []

    def teardown_method(self):
        from app.api.routes import research as research_routes

        research_routes.get_analysis_queue = self._orig
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
        assert job["pipeline"] == "research", "antrean & UI memilih handler lewat field ini"

    def test_job_is_queued_for_the_durable_worker(self):
        """Dulu status langsung `running` di thread lepas: job menggantung bila
        server restart dan tak bisa dibatalkan. Kini ia diantrekan dan worker
        memilih handler dari field pipeline."""
        from app.utils.job_store import get_job

        job = get_job(self._start().json()["job_id"])
        assert job["status"] == "queued"
        assert job["payload"]["pdf_paths"] and job["payload"]["output_dir"]
        assert job["max_attempts"] >= 1

    def test_queue_is_woken_after_enqueue(self):
        self._start()
        assert self.notified == [True]

    def test_rejects_request_without_files(self):
        assert client.post("/api/research/start").status_code == 422


class TestRecordEndpoints:
    """Endpoint yang membaca berkas keluaran penuh, bukan 8 sampel di artefak."""

    JOB = "job-records"

    def setup_method(self):
        job_store.save_job(self.JOB, {"job_id": self.JOB, "status": "completed",
                                      "pipeline": "research"})
        self.chunks = SCRATCH / "chunks.jsonl"
        self.chunks.write_text(
            '{"record":"meta","jumlah_chunk":2}\n'
            '{"record":"chunk","source":"a.pdf","chunk_index":0,"section_normalized":"intro",'
            '"paper_title":"A","text":"gajah berenang","token_count":3}\n'
            '{"record":"chunk","source":"b.pdf","chunk_index":1,"section_normalized":"methods",'
            '"paper_title":"B","text":"kucing terbang","token_count":3}\n',
            encoding="utf-8")
        job_store.add_stage_artifact(self.JOB, "chunking", "result", "chunking", {
            "outputs": {"chunks_jsonl": str(self.chunks)}})
        # Meniru job lama: tahap selesai, tapi ditulis sebelum proposals_jsonl ada.
        job_store.add_stage_artifact(self.JOB, "recommendation", "result", "recommendation", {
            "outputs": {"rekomendasi_md": str(SCRATCH / "rekomendasi.md")}})

    def test_meta_line_is_not_returned_as_a_record(self):
        body = client.get(f"/api/research/{self.JOB}/records/chunking").json()
        assert body["total"] == 2
        assert all(r["record"] == "chunk" for r in body["records"])

    def test_facets_list_available_filter_values(self):
        facets = client.get(f"/api/research/{self.JOB}/records/chunking").json()["facets"]
        assert facets["source"] == ["a.pdf", "b.pdf"]
        assert facets["section_normalized"] == ["intro", "methods"]

    def test_facet_filter_narrows_records(self):
        body = client.get(f"/api/research/{self.JOB}/records/chunking",
                          params={"source": "a.pdf"}).json()
        assert body["filtered"] == 1 and body["total"] == 2
        assert body["records"][0]["source"] == "a.pdf"

    def test_search_matches_record_content(self):
        body = client.get(f"/api/research/{self.JOB}/records/chunking",
                          params={"q": "terbang"}).json()
        assert [r["source"] for r in body["records"]] == ["b.pdf"]

    def test_unknown_query_param_is_ignored_not_applied(self):
        """Hanya kolom di daftar putih yang boleh memfilter."""
        body = client.get(f"/api/research/{self.JOB}/records/chunking",
                          params={"text": "gajah berenang"}).json()
        assert body["filtered"] == 2

    def test_pagination_slices_records(self):
        body = client.get(f"/api/research/{self.JOB}/records/chunking",
                          params={"offset": 1, "limit": 1}).json()
        assert len(body["records"]) == 1 and body["records"][0]["source"] == "b.pdf"

    def test_missing_output_key_explains_rerun(self):
        """Job lama punya artefak rekomendasi tapi belum menulis proposals_jsonl."""
        detail = client.get(f"/api/research/{self.JOB}/records/recommendation").json()["detail"]
        assert "proposals_jsonl" in detail and "jalankan ulang" in detail.lower()

    def test_incomplete_stage_is_reported_separately(self):
        detail = client.get(f"/api/research/{self.JOB}/records/novelty").json()["detail"]
        assert "belum selesai" in detail.lower()

    def test_fulltext_lists_journals_with_chunk_counts(self):
        body = client.get(f"/api/research/{self.JOB}/fulltext").json()
        assert {j["source"]: j["chunks"] for j in body["journals"]} == {"a.pdf": 1, "b.pdf": 1}

    def test_fulltext_returns_chunks_ordered_for_one_journal(self):
        body = client.get(f"/api/research/{self.JOB}/fulltext",
                          params={"source": "b.pdf"}).json()
        assert [c["chunk_index"] for c in body["chunks"]] == [1]

    def test_fulltext_rejects_journal_outside_job(self):
        resp = client.get(f"/api/research/{self.JOB}/fulltext", params={"source": "../etc"})
        assert resp.status_code == 404


class TestStageSourceEndpoint:
    def test_returns_source_of_functions_the_stage_runs(self):
        body = client.get("/api/research/stages/chunking/source").json()
        names = [f["name"] for f in body["functions"]]
        assert "stage_chunking" in names and "chunk_document" in names
        assert all(f["source"].lstrip().startswith("def ") for f in body["functions"])

    def test_reports_repo_relative_file_and_line_range(self):
        fn = client.get("/api/research/stages/novelty/source").json()["functions"][0]
        assert fn["file"].startswith("backend/") and fn["line_end"] > fn["line_start"]

    def test_unknown_stage_is_rejected(self):
        assert client.get("/api/research/stages/bogus/source").status_code == 404
