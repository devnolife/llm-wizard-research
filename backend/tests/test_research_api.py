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

    def _start(self, data=None):
        resp = client.post(
            "/api/research/start",
            files=[("files", ("uji.pdf", _MINIMAL_PDF, "application/pdf"))],
            data=data,
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

    def test_until_is_stored_in_payload_and_trims_planned_stages(self):
        from app.utils.job_store import get_job

        body = self._start(data={"until": "gap_mining", "ocr_mode": "force"}).json()
        assert body["stages"] == ["chunking", "gap_mining"]
        payload = get_job(body["job_id"])["payload"]
        assert payload["until"] == "gap_mining" and payload["ocr_mode"] == "force"

    def test_default_payload_has_no_until_and_auto_ocr(self):
        from app.utils.job_store import get_job

        payload = get_job(self._start().json()["job_id"])["payload"]
        assert payload["until"] is None and payload["ocr_mode"] == "auto"

    def test_unknown_until_or_ocr_mode_is_422(self):
        assert self._start(data={"until": "novelti"}).status_code == 422
        assert self._start(data={"ocr_mode": "gpu"}).status_code == 422
        assert self.notified == [], "job tidak boleh dibuat bila parameter salah"

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

    def test_gap_runs_is_stored_in_payload_with_single_run_default(self):
        from app.utils.job_store import get_job

        default_payload = get_job(self._start().json()["job_id"])["payload"]
        assert (default_payload["gap_runs"], default_payload["min_run_hits"]) == (1, 0)

        body = self._start(data={"until": "gap_mining", "gap_runs": "3",
                                 "min_run_hits": "2"}).json()
        payload = get_job(body["job_id"])["payload"]
        assert (payload["gap_runs"], payload["min_run_hits"]) == (3, 2)

    def test_gap_runs_out_of_range_is_422(self):
        from app.services.research_pipeline import MAX_GAP_RUNS

        assert self._start(data={"gap_runs": "0"}).status_code == 422
        assert self._start(data={"gap_runs": str(MAX_GAP_RUNS + 1)}).status_code == 422
        assert self._start(data={"gap_runs": "3", "min_run_hits": "4"}).status_code == 422
        assert self.notified == [], "job tidak boleh dibuat bila parameter salah"


class TestContinueEndpoint:
    """Melanjutkan job langkah 2 ke tahap berikutnya tanpa mengulang LLM."""

    def setup_method(self):
        from app.api.routes import research as research_routes
        from app.services import analysis_queue

        self.notified: list = []
        queue = analysis_queue.AnalysisJobQueue(max_workers=1)
        queue.notify = lambda: self.notified.append(True)  # type: ignore[method-assign]
        self._orig = research_routes.get_analysis_queue
        research_routes.get_analysis_queue = lambda: queue

    def teardown_method(self):
        from app.api.routes import research as research_routes
        research_routes.get_analysis_queue = self._orig

    def _done_job(self, job_id, stages_done, status="completed"):
        job_store.save_job(job_id, {
            "job_id": job_id, "status": status, "progress": 100, "pipeline": "research",
            "stages_done": stages_done, "attempt": 2, "max_attempts": 2,
            "payload": {"pdf_paths": ["/tmp/x.pdf"], "output_dir": "/tmp/out",
                        "until": "gap_mining", "ocr_mode": "force"},
        })

    def test_continue_requeues_from_next_stage_and_keeps_payload(self):
        self._done_job("rc-1", ["chunking", "gap_mining"])
        resp = client.post("/api/research/rc-1/continue",
                           data={"until": "novelty", "novelty_limit": "40"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["start_from"] == "novelty" and body["stages"] == ["novelty"]

        job = job_store.get_job("rc-1")
        assert job["status"] == "queued" and job["attempt"] == 0
        assert job["payload"]["start_from"] == "novelty"
        assert job["payload"]["until"] == "novelty"
        assert job["payload"]["novelty_limit"] == 40
        assert job["payload"]["ocr_mode"] == "force", "payload lama dipertahankan"
        assert self.notified == [True]
        assert any(e["type"] == "job.continued" for e in job_store.get_job_events("rc-1"))

    def test_continue_defaults_to_all_remaining_stages(self):
        self._done_job("rc-2", ["chunking", "gap_mining"])
        body = client.post("/api/research/rc-2/continue").json()
        assert body["stages"] == ["novelty", "recommendation"]

    def test_continue_rejects_running_job_and_finished_pipeline(self):
        self._done_job("rc-3", ["chunking"], status="running")
        assert client.post("/api/research/rc-3/continue").status_code == 409
        self._done_job("rc-4", ["chunking", "gap_mining", "novelty", "recommendation"])
        assert client.post("/api/research/rc-4/continue").status_code == 409

    def test_continue_rejects_until_before_next_stage(self):
        self._done_job("rc-5", ["chunking", "gap_mining"])
        assert client.post("/api/research/rc-5/continue",
                           data={"until": "gap_mining"}).status_code == 422

    def test_continue_can_rerun_a_finished_stage(self):
        """Cek ulang kebaruan setelah kuota OpenAlex pulih."""
        self._done_job("rc-6", ["chunking", "gap_mining", "novelty"])
        body = client.post("/api/research/rc-6/continue",
                           data={"start_from": "novelty", "until": "novelty"}).json()
        assert body["start_from"] == "novelty" and body["stages"] == ["novelty"]
        assert job_store.get_job("rc-6")["payload"]["start_from"] == "novelty"

    def test_continue_rejects_rerunning_chunking_or_skipping_ahead(self):
        self._done_job("rc-7", ["chunking", "gap_mining"])
        assert client.post("/api/research/rc-7/continue",
                           data={"start_from": "chunking"}).status_code == 422
        assert client.post("/api/research/rc-7/continue",
                           data={"start_from": "recommendation"}).status_code == 422

    def test_continue_unknown_or_legacy_job_is_404(self):
        assert client.post("/api/research/tidak-ada/continue").status_code == 404
        job_store.save_job("legacy-1", {"job_id": "legacy-1", "status": "completed"})
        assert client.post("/api/research/legacy-1/continue").status_code == 404

    def test_continue_gap_runs_only_when_rerunning_gap_mining(self):
        """Mengulang penambangan 3 run untuk mengukur k/n; di tahap lain parameternya
        tidak bermakna dan ditolak agar tidak diam-diam diabaikan."""
        self._done_job("rc-8", ["chunking", "gap_mining"])
        assert client.post("/api/research/rc-8/continue",
                           data={"gap_runs": "3"}).status_code == 422
        assert client.post("/api/research/rc-8/continue",
                           data={"start_from": "gap_mining", "gap_runs": "9"}).status_code == 422

        resp = client.post("/api/research/rc-8/continue",
                           data={"start_from": "gap_mining", "until": "gap_mining",
                                 "gap_runs": "3"})
        assert resp.status_code == 200, resp.text
        payload = job_store.get_job("rc-8")["payload"]
        assert (payload["gap_runs"], payload["min_run_hits"]) == (3, 0)
        assert payload["start_from"] == "gap_mining"

    def test_continue_without_gap_runs_keeps_previous_value(self):
        self._done_job("rc-9", ["chunking", "gap_mining"])
        job = job_store.get_job("rc-9")
        job["payload"]["gap_runs"] = 3
        job_store.save_job("rc-9", job)
        assert client.post("/api/research/rc-9/continue",
                           data={"until": "novelty"}).status_code == 200
        assert job_store.get_job("rc-9")["payload"]["gap_runs"] == 3


class TestChunkPreviewEndpoint:
    """Tahap 1 tanpa job: process_pdf di-stub agar tes offline dan cepat."""

    def setup_method(self):
        from app.api.routes import research as research_routes
        from app.core.pipeline.pipeline import PipelineResult
        from app.core.pipeline.schema import PaperMeta, PipelineChunk

        self.calls: list = []
        self.modes: list = []

        def fake_process_pdf(pdf_path, source=None, **kwargs):
            self.calls.append((Path(pdf_path).exists(), source))
            self.modes.append(kwargs.get("ocr_mode"))
            if source == "rusak.pdf":
                raise RuntimeError("PDF tidak bisa dibaca")
            meta = PaperMeta(source=source, paper_title="Judul Uji", year=2024, language="id")
            chunks = [
                PipelineChunk(source=source, chunk_index=0, text="pendahuluan", token_count=3,
                              section_normalized="introduction", page_start=1),
                PipelineChunk(source=source, chunk_index=1, text="metode", token_count=2,
                              section_normalized="methods", page_start=2),
                PipelineChunk(source=source, chunk_index=2, text="metode lanjut", token_count=4,
                              section_normalized="methods", page_start=2),
            ]
            return PipelineResult(meta=meta, chunks=chunks, num_pages=2,
                                  extraction_method="pymupdf_layout")

        self._orig = research_routes.process_pdf
        research_routes.process_pdf = fake_process_pdf

    def teardown_method(self):
        from app.api.routes import research as research_routes
        research_routes.process_pdf = self._orig

    def _post(self, *names, data=None):
        return client.post(
            "/api/research/chunk-preview",
            files=[("files", (n, _MINIMAL_PDF, "application/pdf")) for n in names],
            data=data,
        )

    def test_returns_meta_sections_and_every_chunk(self):
        body = self._post("uji.pdf").json()
        (item,) = body["files"]
        assert item["source"] == "uji.pdf"
        assert item["meta"]["paper_title"] == "Judul Uji" and item["pages"] == 2
        assert item["num_chunks"] == 3 and item["token_total"] == 9
        assert item["sections"] == {"introduction": 1, "methods": 2}
        assert [c["chunk_index"] for c in item["chunks"]] == [0, 1, 2]
        assert item["chunks"][0]["text"] == "pendahuluan"
        assert body["params"]["target_tokens"] > 0
        assert body["params"]["ocr_mode"] == "auto" and self.modes == ["auto"]

    def test_force_ocr_mode_is_forwarded_to_the_pipeline(self):
        body = self._post("uji.pdf", data={"ocr_mode": "force"}).json()
        assert body["params"]["ocr_mode"] == "force" and self.modes == ["force"]

    def test_unknown_ocr_mode_is_422(self):
        assert self._post("uji.pdf", data={"ocr_mode": "gpu"}).status_code == 422
        assert self.calls == []

    def test_no_job_is_created_and_temp_file_is_removed(self):
        before = {j["job_id"] for j in job_store.list_jobs()}
        self._post("uji.pdf")
        assert {j["job_id"] for j in job_store.list_jobs()} == before
        # the stub saw the temp file while processing; the endpoint then deletes the dir
        assert self.calls == [(True, "uji.pdf")]

    def test_one_broken_pdf_does_not_sink_the_batch(self):
        body = self._post("rusak.pdf", "baik.pdf").json()
        assert [f["source"] for f in body["files"]] == ["rusak.pdf", "baik.pdf"]
        assert "error" in body["files"][0] and body["files"][0]["chunks"] == []
        assert body["files"][1]["num_chunks"] == 3

    def test_rejects_non_pdf_upload(self):
        resp = client.post(
            "/api/research/chunk-preview",
            files=[("files", ("catatan.txt", b"bukan pdf", "text/plain"))],
        )
        assert resp.status_code == 415
        assert self.calls == []


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

    def test_side_collections_resolve_to_their_owning_stage(self):
        """'candidates' & 'themes' bukan tahap; berkasnya ditulis gap_mining &
        recommendation dan harus ditemukan lewat artefak tahap pemilik itu."""
        cands = SCRATCH / "candidates.jsonl"
        cands.write_text('{"seq":1,"source":"a.pdf","chunk_id":"a::0","candidate_reason":'
                         '"section:conclusion","llm_answered":true,"gaps":[]}\n'
                         '{"seq":2,"source":"b.pdf","chunk_id":"b::1","candidate_reason":'
                         '"tail","llm_answered":false,"gaps":[]}\n', encoding="utf-8")
        job_store.add_stage_artifact(self.JOB, "gap_mining", "result", "gap_mining", {
            "outputs": {"gaps_jsonl": str(SCRATCH / "x.jsonl"), "candidates_jsonl": str(cands)}})
        body = client.get(f"/api/research/{self.JOB}/records/candidates").json()
        assert body["total"] == 2
        assert body["facets"]["candidate_reason"] == ["section:conclusion", "tail"]
        assert body["facets"]["llm_answered"] == ["False", "True"]
        only = client.get(f"/api/research/{self.JOB}/records/candidates",
                          params={"llm_answered": "False"}).json()
        assert [r["source"] for r in only["records"]] == ["b.pdf"]

    def test_themes_collection_missing_on_old_job_explains_rerun(self):
        detail = client.get(f"/api/research/{self.JOB}/records/themes").json()["detail"]
        assert "themes_jsonl" in detail and "jalankan ulang" in detail.lower()

    def test_unknown_collection_is_rejected(self):
        assert client.get(f"/api/research/{self.JOB}/records/bogus").status_code == 404

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


class TestStagesCarryProcessMap:
    def test_each_stage_lists_substeps_and_constants(self):
        for stage in client.get("/api/research/stages").json()["stages"]:
            assert stage["substeps"], stage["key"]
            assert stage["constants"], stage["key"]
            for sub in stage["substeps"]:
                assert {"key", "label", "label_teknis", "penjelasan", "in_metric",
                        "out_metric", "drop_metric", "sample_key", "inside", "jenis"} <= set(sub)
                assert sub["jenis"] in ("saring", "periksa"), sub["key"]

    def test_coherence_check_is_an_inspection_not_a_filter(self):
        """UI menampilkan 'diperiksa N · ditandai M', bukan corong '10 → 0'."""
        chunking = next(s for s in client.get("/api/research/stages").json()["stages"]
                        if s["key"] == "chunking")
        cek = next(u for u in chunking["substeps"] if u["key"] == "cek_koherensi")
        assert cek["jenis"] == "periksa"

    def test_recommendation_constants_expose_the_formula_weights(self):
        rec = next(s for s in client.get("/api/research/stages").json()["stages"]
                   if s["key"] == "recommendation")
        c = rec["constants"]
        assert abs(c["w_gap"] + c["w_novelty"] + c["w_actionability"] - 1.0) < 1e-9
