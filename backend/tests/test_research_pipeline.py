"""Tests for the monitored research pipeline orchestrator."""

import shutil
from pathlib import Path

import pytest

from app.services import research_pipeline
from app.services.research_pipeline import (
    RESEARCH_STAGES,
    ResearchCancelled,
    StageOutcome,
    _StageRecorder,
    _dedup_gaps,
    _median,
    run_research_job,
    run_research_pipeline,
    stage_recommendation,
)
from app.core.pipeline.io import source_name, write_jsonl
from app.utils import job_store

SCRATCH = Path(__file__).parent / ".scratch_research_pipeline"


@pytest.fixture(autouse=True)
def _isolated_job_store():
    """Fixture, bukan setup_function: setup_function tidak dipanggil untuk metode
    di dalam kelas, sehingga tes kelas sempat menulis ke basis data produksi.

    Path harus .sqlite3 — path .json memakai mode legacy dan artefak tetap
    ditulis lewat _ensure_sqlite() ke basis data bawaan.
    """
    shutil.rmtree(SCRATCH, ignore_errors=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    job_store.load_jobs(SCRATCH / "analysis_jobs.sqlite3")
    yield
    shutil.rmtree(SCRATCH, ignore_errors=True)
    job_store.load_jobs()


class TestStageDefinitions:
    def test_four_stages_in_pipeline_order(self):
        keys = [s[0] for s in RESEARCH_STAGES]
        assert keys == ["chunking", "gap_mining", "novelty", "recommendation"]

    def test_every_stage_has_icon_title_and_description(self):
        assert all(len(s) == 4 and all(s) for s in RESEARCH_STAGES)


class TestHelpers:
    def test_dedup_keeps_first_of_identical_statement(self):
        gaps = [
            {"source": "a.pdf", "gap_statement": "Perlu studi lanjutan.", "topic": "legal"},
            {"source": "a.pdf", "gap_statement": "perlu studi LANJUTAN.  ", "topic": "tools"},
            {"source": "b.pdf", "gap_statement": "Perlu studi lanjutan."},
        ]
        out = _dedup_gaps(gaps)
        assert len(out) == 2, "gap sama di jurnal sama harus dilebur"
        assert out[0]["topic"] == "legal"

    def test_median_handles_empty(self):
        assert _median([]) == 0
        assert _median([5, 1, 3]) == 3

    def test_source_name_shared_with_cli(self):
        assert source_name("00_A_Process.pdf") == "A_Process.pdf"
        assert source_name("bert_paper.pdf") == "bert_paper.pdf"


class TestStageRecorder:
    def test_records_start_completion_and_artifact(self):
        job_store.save_job("job-rec", {"status": "running", "progress": 0})
        with _StageRecorder("job-rec", "chunking") as rec:
            rec.finish(StageOutcome(params={"target_tokens": 384},
                                    metrics={"chunk": 12}))

        events = job_store.get_job_events("job-rec")
        types = [e["type"] for e in events]
        assert "phase.started" in types and "phase.completed" in types
        done = next(e for e in events if e["type"] == "phase.completed")
        assert done["phase"] == "chunking"
        assert done["duration_ms"] is not None
        assert done["data"]["chunk"] == 12

        arts = job_store.get_stage_artifacts("job-rec", "chunking")
        assert len(arts) == 1 and arts[0]["kind"] == "result"
        payload = arts[0]["payload"]
        assert payload["params"]["target_tokens"] == 384
        assert "duration_ms" in payload

    def test_failure_is_recorded_and_reraised(self):
        job_store.save_job("job-fail", {"status": "running", "progress": 0})
        try:
            with _StageRecorder("job-fail", "gap_mining"):
                raise RuntimeError("ledakan")
        except RuntimeError:
            pass
        types = [e["type"] for e in job_store.get_job_events("job-fail")]
        assert "phase.failed" in types

    def test_cancellation_is_not_recorded_as_a_failure(self):
        job_store.save_job("job-cancel", {"status": "running", "progress": 0})
        try:
            with _StageRecorder("job-cancel", "gap_mining"):
                raise ResearchCancelled("stop")
        except ResearchCancelled:
            pass
        types = [e["type"] for e in job_store.get_job_events("job-cancel")]
        assert "phase.cancelled" in types and "phase.failed" not in types


class TestOrchestratorAsQueueHandler:
    """``run_research_job`` is what the durable queue calls; the stages are
    stubbed so only status transitions and payload handling are exercised."""

    def _stub_stages(self, monkeypatch, fail_at: str | None = None):
        calls: list[str] = []

        def make(name):
            def stage(*_a, **_k):
                calls.append(name)
                if name == fail_at:
                    raise RuntimeError(f"{name} meledak")
                return StageOutcome(metrics={"ok": 1})
            return stage

        for name in ("stage_chunking", "stage_gap_mining", "stage_novelty",
                     "stage_recommendation"):
            monkeypatch.setattr(research_pipeline, name, make(name))
        monkeypatch.setattr(research_pipeline, "_shared_embedder", lambda: None)
        return calls

    def _queued_job(self, job_id: str, pdf: Path) -> None:
        job_store.save_job(job_id, {
            "status": "running", "progress": 0, "pipeline": "research",
            "payload": {"pdf_paths": [str(pdf)], "output_dir": str(SCRATCH / "out")},
        })

    def test_runs_all_stages_from_payload_and_completes(self, monkeypatch):
        calls = self._stub_stages(monkeypatch)
        pdf = SCRATCH / "a.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        self._queued_job("rq-ok", pdf)

        run_research_job("rq-ok")

        job = job_store.get_job("rq-ok")
        assert job["status"] == "completed" and job["progress"] == 100
        assert calls == ["stage_chunking", "stage_gap_mining", "stage_novelty",
                         "stage_recommendation"]
        assert (SCRATCH / "out").is_dir(), "output_dir dari payload dipakai"

    def test_failure_keeps_the_specific_stage_error(self, monkeypatch):
        """The generic queue handler would overwrite the error; ours must not
        re-raise so the message 'novelty: ...' survives for the UI."""
        self._stub_stages(monkeypatch, fail_at="stage_novelty")
        pdf = SCRATCH / "b.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        self._queued_job("rq-fail", pdf)

        run_research_job("rq-fail")  # must not raise

        job = job_store.get_job("rq-fail")
        assert job["status"] == "failed"
        assert job["error"].startswith("novelty:")
        types = [e["type"] for e in job_store.get_job_events("rq-fail")]
        assert "phase.failed" in types

    def test_missing_pdfs_raise_so_queue_marks_job_failed(self, monkeypatch):
        self._stub_stages(monkeypatch)
        self._queued_job("rq-nopdf", SCRATCH / "hilang.pdf")
        with pytest.raises(FileNotFoundError):
            run_research_job("rq-nopdf")

    def test_cancel_request_stops_before_next_stage(self, monkeypatch):
        calls = self._stub_stages(monkeypatch)
        pdf = SCRATCH / "c.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        self._queued_job("rq-cancel", pdf)
        # Simulate the user pressing cancel while stage 1 runs.
        original = research_pipeline.stage_chunking

        def chunk_then_cancel(*a, **k):
            job_store.request_cancel("rq-cancel")
            return original(*a, **k)
        monkeypatch.setattr(research_pipeline, "stage_chunking", chunk_then_cancel)

        run_research_job("rq-cancel")

        job = job_store.get_job("rq-cancel")
        assert job["status"] == "cancelled"
        assert "gap_mining" in job["message"], "tahap berikutnya tidak boleh dimulai"
        assert calls == ["stage_chunking"]

    def test_run_pipeline_raises_cancelled_for_direct_callers(self, monkeypatch):
        self._stub_stages(monkeypatch)
        job_store.save_job("rq-direct", {"status": "running", "progress": 0})
        job_store.request_cancel("rq-direct")
        with pytest.raises(ResearchCancelled):
            run_research_pipeline("rq-direct", [SCRATCH / "x.pdf"], SCRATCH / "out2")
        assert job_store.get_job("rq-direct")["status"] == "cancelled"


class TestStageRecommendation:
    """Scoring must match the CLI, so the corpus/confidence shape is asserted."""

    def _write_inputs(self):
        gaps = SCRATCH / "gaps_novelty.jsonl"
        chunks = SCRATCH / "chunks.jsonl"
        write_jsonl(str(gaps), [
            {"record": "meta", "job_id": "x"},
            {"source": "a.pdf", "gap_statement": "Protokol pengujian alat forensik belum ada.",
             "gap_paraphrase": "Belum ada protokol pengujian alat forensik.",
             "gap_type": "stated_limitation", "topic": "tools",
             "grounding_score": 1.0, "novelty_status": "open"},
            {"source": "b.pdf", "gap_statement": "Sudah dibahas penelitian lain.",
             "gap_type": "stated_limitation", "topic": "legal",
             "grounding_score": 1.0, "novelty_status": "addressed"},
        ])
        write_jsonl(str(chunks), [
            {"record": "meta", "job_id": "x"},
            {"record": "chunk", "source": "a.pdf", "paper_title": "Alat Forensik",
             "text": "Alat forensik digital dan protokol pengujiannya."},
            {"record": "chunk", "source": "b.pdf", "paper_title": "Hukum Digital",
             "text": "Kerangka hukum bukti digital di pengadilan."},
        ])
        return gaps, chunks

    def test_only_open_gaps_become_proposals(self):
        job_store.save_job("job-rec2", {"status": "running", "progress": 0})
        gaps, chunks = self._write_inputs()
        out = stage_recommendation("job-rec2", gaps, chunks,
                                   SCRATCH / "rekomendasi.md", embedder=None)
        assert out.metrics["gap_open"] == 1
        assert out.metrics["proposal_dinilai"] == 1

    def test_grounding_score_feeds_gap_confidence(self):
        """Without the gap_confidences mapping every score collapses to ~0.08."""
        job_store.save_job("job-rec3", {"status": "running", "progress": 0})
        gaps, chunks = self._write_inputs()
        out = stage_recommendation("job-rec3", gaps, chunks,
                                   SCRATCH / "rekomendasi.md", embedder=None)
        assert out.metrics["skor_tertinggi"] >= 0.5, \
            "gap_confidence 1.0 menyumbang 0.5 ke skor prioritas"

    def test_writes_markdown_and_records_outputs(self):
        job_store.save_job("job-rec4", {"status": "running", "progress": 0})
        gaps, chunks = self._write_inputs()
        out_md = SCRATCH / "rekomendasi.md"
        out = stage_recommendation("job-rec4", gaps, chunks, out_md, embedder=None)
        assert out_md.exists()
        assert "Rekomendasi Topik" in out_md.read_text(encoding="utf-8")
        assert out.outputs["rekomendasi_md"] == str(out_md)
