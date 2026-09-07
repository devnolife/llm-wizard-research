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
from app.core.pipeline.io import read_jsonl, source_name, write_jsonl
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
        assert job["progress"] == 0
        assert "gap_mining" in job["message"], "tahap berikutnya tidak boleh dimulai"
        assert calls == ["stage_chunking"]

    def test_cancel_during_last_stage_is_not_overwritten_by_completed(self, monkeypatch):
        """No cooperative check runs after the final stage; the completion write
        itself must refuse when cancel_requested is already set."""
        calls = self._stub_stages(monkeypatch)
        pdf = SCRATCH / "d.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        self._queued_job("rq-late", pdf)
        original = research_pipeline.stage_recommendation

        def recommend_then_cancel(*a, **k):
            outcome = original(*a, **k)
            job_store.request_cancel("rq-late")
            return outcome
        monkeypatch.setattr(research_pipeline, "stage_recommendation", recommend_then_cancel)

        run_research_job("rq-late")

        job = job_store.get_job("rq-late")
        assert job["status"] == "cancelled"
        assert job["progress"] == 0
        assert len(calls) == 4, "semua tahap sudah berjalan; hanya status akhir yang berubah"
        types = [e["type"] for e in job_store.get_job_events("rq-late")]
        assert "job.cancelled" in types and "job.completed" not in types

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


# ── Peta proses & pencatatan sub-langkah ───────────────────────────────────

from app.core.gap_detection.quote_grounding import QUOTE_MATCH_THRESHOLD  # noqa: E402
from app.core.gap_mining.novelty import STRONG_MATCH_THRESHOLD, annotate_gaps  # noqa: E402
from app.core.pipeline.schema import PaperMeta, PipelineChunk  # noqa: E402
from app.core.recommendation import novelty as rec_novelty  # noqa: E402
from app.services.research_pipeline import (  # noqa: E402
    PIPELINE_CONSTANTS,
    SUBSTEPS,
    _split_duplicates,
    _substep,
    stage_chunking,
    stage_gap_mining,
    stage_novelty,
)


class _FakePdfResult:
    """Bentuk minimal yang dibaca stage_chunking dan write_chunks_jsonl."""

    def __init__(self, source: str, texts: list[str], sections: list[str]):
        self.meta = PaperMeta(source=source, paper_title=f"Judul {source}", year=2024,
                              language="id", extraction_quality="good")
        self.extraction_method = "pymupdf"
        self.grobid_used = False
        self.num_pages = 3
        self.chunks = [
            PipelineChunk(source=source, chunk_index=i, text=t, token_count=len(t.split()),
                          section_normalized=s, paper_title=self.meta.paper_title, year=2024)
            for i, (t, s) in enumerate(zip(texts, sections))
        ]


_CONCLUSION = ("Penelitian ini masih terbatas pada satu institusi sehingga generalisasi "
               "hasil perlu diuji ulang pada konteks yang berbeda. Studi lanjutan disarankan.")


def _chunks_file(path: Path) -> Path:
    """Dua chunk, tetapi hanya kesimpulannya yang jadi kandidat: pendahuluan
    dibuat < 80 karakter agar aturan cadangan intro/tail tidak memilihnya."""
    write_jsonl(str(path), [
        {"record": "meta", "job_id": "x"},
        {"record": "chunk", "source": "a.pdf", "chunk_index": 0, "chunk_id": "a::0",
         "section_normalized": "introduction", "token_count": 8, "is_reference": False,
         "text": "Pendahuluan singkat tentang deteksi anomali pembelajaran."},
        {"record": "chunk", "source": "a.pdf", "chunk_index": 1, "chunk_id": "a::1",
         "section_normalized": "conclusion", "token_count": 40, "is_reference": False,
         "text": _CONCLUSION},
    ])
    return path


def _llm_stub(reply: str):
    def generate(prompt, system=None, json_mode=False, temperature=None):
        return reply, "model-uji"
    return generate


class TestProcessMap:
    def test_every_stage_has_substeps_with_both_labels(self):
        assert set(SUBSTEPS) == {s[0] for s in RESEARCH_STAGES}
        for subs in SUBSTEPS.values():
            assert subs, "tiap tahap harus punya minimal satu sub-langkah"
            for s in subs:
                assert s["key"] and s["label"] and s["label_teknis"] and s["penjelasan"]

    def test_nested_substeps_point_at_an_existing_parent(self):
        for subs in SUBSTEPS.values():
            keys = {s["key"] for s in subs}
            for s in subs:
                if s["inside"]:
                    assert s["inside"] in keys

    def test_constants_come_from_the_modules_that_use_them(self):
        assert PIPELINE_CONSTANTS["gap_mining"]["quote_match_threshold"] == QUOTE_MATCH_THRESHOLD
        assert PIPELINE_CONSTANTS["novelty"]["strong_match_threshold"] == STRONG_MATCH_THRESHOLD
        rec = PIPELINE_CONSTANTS["recommendation"]
        assert (rec["w_gap"], rec["w_novelty"], rec["w_actionability"]) == (
            rec_novelty.W_GAP, rec_novelty.W_NOVELTY, rec_novelty.W_ACTIONABILITY)
        assert rec["sweet_spot"] == list(rec_novelty.NOVELTY_SWEET_SPOT)

    def test_metric_keys_in_map_exist_in_stage_outputs(self, monkeypatch):
        """Peta proses merujuk kunci metrik; kalau tahapnya berhenti menulis kunci
        itu, UI akan menampilkan corong kosong tanpa galat. Tes ini menjaganya."""
        job_store.save_job("pm", {"status": "running", "progress": 0})
        pdf = SCRATCH / "00_a.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        monkeypatch.setattr(research_pipeline, "process_pdf", lambda *a, **k: _FakePdfResult(
            "a.pdf", ["Pendahuluan " * 30, _CONCLUSION], ["introduction", "conclusion"]))
        chunk_out = stage_chunking("pm", [pdf], SCRATCH / "chunks.jsonl")

        reply = ('[{"gap_type":"stated_limitation","gap_statement":"Penelitian ini masih '
                 'terbatas pada satu institusi sehingga generalisasi hasil perlu diuji ulang '
                 'pada konteks yang berbeda.","gap_paraphrase":"Terbatas satu institusi.",'
                 '"topic":"other"}]')
        monkeypatch.setattr(research_pipeline.copilot_client, "generate", _llm_stub(reply))
        gap_out = stage_gap_mining("pm", SCRATCH / "chunks.jsonl", SCRATCH / "gaps.jsonl",
                                   workers=1)

        def fake_annotate(gaps, on_progress=None, **_):
            out = []
            for i, g in enumerate(gaps, 1):
                out.append({**g, "novelty_status": "open", "novelty_query": "q",
                            "related_recent_papers": []})
                if on_progress:
                    on_progress(i, len(gaps))
            return out
        monkeypatch.setattr(research_pipeline, "annotate_gaps", fake_annotate)
        nov_out = stage_novelty("pm", SCRATCH / "gaps.jsonl", SCRATCH / "gaps_nov.jsonl")
        rec_out = stage_recommendation("pm", SCRATCH / "gaps_nov.jsonl",
                                       SCRATCH / "chunks.jsonl", SCRATCH / "rek.md")

        outcomes = {"chunking": chunk_out, "gap_mining": gap_out,
                    "novelty": nov_out, "recommendation": rec_out}
        for stage_key, subs in SUBSTEPS.items():
            metrics = outcomes[stage_key].metrics
            samples = outcomes[stage_key].substep_samples
            for s in subs:
                for field in ("in_metric", "out_metric", "drop_metric"):
                    key = s[field]
                    assert key is None or key in metrics, \
                        f"{stage_key}/{s['key']}: metrik '{key}' tidak ditulis tahap"
                if s["sample_key"]:
                    assert s["sample_key"] in samples, \
                        f"{stage_key}/{s['key']}: substep_samples '{s['sample_key']}' hilang"


class TestSubstepRecorder:
    def test_records_start_and_completion_with_counts(self):
        job_store.save_job("ss", {"status": "running", "progress": 0})
        with _substep("ss", "gap_mining", "dedup", masuk=10) as sub:
            sub.done(keluar=7, dibuang=3)
        events = [e for e in job_store.get_job_events("ss") if e["type"].startswith("substep.")]
        assert [e["type"] for e in events] == ["substep.started", "substep.completed"]
        assert events[0]["data"] == {"substep": "dedup", "masuk": 10}
        assert events[1]["data"] == {"substep": "dedup", "masuk": 10, "keluar": 7, "dibuang": 3}
        assert events[1]["duration_ms"] is not None

    def test_error_is_recorded_then_reraised(self):
        job_store.save_job("ss2", {"status": "running", "progress": 0})
        with pytest.raises(RuntimeError):
            with _substep("ss2", "novelty", "cek_kebaruan"):
                raise RuntimeError("putus")
        done = [e for e in job_store.get_job_events("ss2") if e["type"] == "substep.completed"]
        assert done and done[0]["data"]["error"] == "putus"


class TestGapMiningKeepsWhatItDiscards:
    """Contoh yang DIBUANG harus terlihat: itu bukti penyaringan bekerja."""

    def _run(self, monkeypatch, reply: str):
        job_store.save_job("gm", {"status": "running", "progress": 0})
        monkeypatch.setattr(research_pipeline.copilot_client, "generate", _llm_stub(reply))
        return stage_gap_mining("gm", _chunks_file(SCRATCH / "chunks.jsonl"),
                                SCRATCH / "gaps.jsonl", workers=1)

    def test_hallucinated_statement_lands_in_rejected_samples(self, monkeypatch):
        reply = ('[{"gap_type":"stated_limitation","gap_statement":"Penelitian ini masih '
                 'terbatas pada satu institusi sehingga generalisasi hasil perlu diuji ulang '
                 'pada konteks yang berbeda.","topic":"other"},'
                 '{"gap_type":"implicit_gap","gap_statement":"Kalimat ini tidak pernah ada '
                 'di dalam jurnal mana pun sama sekali.","topic":"other"}]')
        out = self._run(monkeypatch, reply)
        assert out.metrics["gap_mentah"] == 2
        assert out.metrics["gugur_di_verifikasi"] == 1
        rejected = out.substep_samples["verifikasi_gugur"]
        assert len(rejected) == 1
        assert rejected[0]["gap_statement"].startswith("Kalimat ini tidak pernah")
        assert rejected[0]["grounding_score"] < QUOTE_MATCH_THRESHOLD

    def test_duplicate_statement_lands_in_dedup_samples(self, monkeypatch):
        stmt = ("Penelitian ini masih terbatas pada satu institusi sehingga generalisasi "
                "hasil perlu diuji ulang pada konteks yang berbeda.")
        reply = (f'[{{"gap_type":"stated_limitation","gap_statement":"{stmt}","topic":"other"}},'
                 f'{{"gap_type":"stated_limitation","gap_statement":"{stmt.upper()}",'
                 f'"topic":"legal"}}]')
        out = self._run(monkeypatch, reply)
        assert out.metrics["duplikat_dibuang"] == 1
        assert out.metrics["gap_final_setelah_dedup"] == 1
        assert out.substep_samples["dedup_dibuang"][0]["topic"] == "legal"

    def test_substep_events_follow_the_process_map_order(self, monkeypatch):
        self._run(monkeypatch, "[]")
        started = [e["data"]["substep"] for e in job_store.get_job_events("gm")
                   if e["type"] == "substep.started"]
        assert started == [s["key"] for s in SUBSTEPS["gap_mining"] if not s["inside"]]

    def test_verification_progress_message_is_surfaced(self, monkeypatch):
        seen: list[str] = []
        original = research_pipeline.update_job

        def spy(job_id, **fields):
            if "message" in fields:
                seen.append(fields["message"])
            return original(job_id, **fields)
        monkeypatch.setattr(research_pipeline, "update_job", spy)
        self._run(monkeypatch, "[]")
        assert any("Verifikasi verbatim" in m for m in seen)
        assert any("duplikat" in m for m in seen)


class TestCandidateTraceIsPersisted:
    """Rantai chunk → LLM → gap → verifikasi harus bisa ditelusuri untuk SEMUA
    kandidat, bukan hanya 15 yang prompt-nya disimpan di basis data."""

    _REAL = ("Penelitian ini masih terbatas pada satu institusi sehingga generalisasi "
             "hasil perlu diuji ulang pada konteks yang berbeda.")
    _FAKE = "Kalimat ini tidak pernah ada di dalam jurnal mana pun sama sekali."

    def _run(self, monkeypatch, reply):
        job_store.save_job("ct", {"status": "running", "progress": 0})
        monkeypatch.setattr(research_pipeline.copilot_client, "generate", _llm_stub(reply))
        out = stage_gap_mining("ct", _chunks_file(SCRATCH / "chunks.jsonl"),
                               SCRATCH / "gaps.jsonl", workers=1)
        return out, read_jsonl(out.outputs["candidates_jsonl"])

    def test_one_record_per_candidate_with_chunk_and_reason(self, monkeypatch):
        out, rows = self._run(monkeypatch, "[]")
        assert out.metrics["kandidat"] == len(rows) == 1
        row = rows[0]
        assert row["chunk_id"] == "a::1" and row["source"] == "a.pdf"
        assert "section:conclusion" in row["candidate_reason"]
        assert row["llm_answered"] is True and row["model"] == "model-uji"
        assert row["seq"] == 1 and row["context_chars"] > 0

    def test_each_parsed_gap_carries_its_verification_fate(self, monkeypatch):
        reply = (f'[{{"gap_type":"stated_limitation","gap_statement":"{self._REAL}","topic":"other"}},'
                 f'{{"gap_type":"stated_limitation","gap_statement":"{self._REAL.upper()}","topic":"other"}},'
                 f'{{"gap_type":"implicit_gap","gap_statement":"{self._FAKE}","topic":"other"}}]')
        _, rows = self._run(monkeypatch, reply)
        gaps = rows[0]["gaps"]
        fate = {g["gap_statement"][:20]: (g["lolos_verifikasi"], g["duplikat"]) for g in gaps}
        assert fate[self._REAL[:20]] == (True, False)
        assert fate[self._REAL.upper()[:20]] == (True, True)
        assert fate[self._FAKE[:20]] == (False, False)
        assert all(g["grounding_score"] is not None for g in gaps)
        assert (rows[0]["gap_mentah"], rows[0]["gap_lolos"], rows[0]["gap_final"]) == (3, 2, 1)

    def test_raw_llm_response_is_kept_for_audit(self, monkeypatch):
        _, rows = self._run(monkeypatch, "[]")
        assert rows[0]["response"] == "[]"

    def test_unanswered_call_is_marked(self, monkeypatch):
        job_store.save_job("ct2", {"status": "running", "progress": 0})
        monkeypatch.setattr(research_pipeline.copilot_client, "generate",
                            lambda *a, **k: None)
        out = stage_gap_mining("ct2", _chunks_file(SCRATCH / "chunks.jsonl"),
                               SCRATCH / "gaps.jsonl", workers=1)
        rows = read_jsonl(out.outputs["candidates_jsonl"])
        assert rows[0]["llm_answered"] is False and rows[0]["gaps"] == []

    def test_db_llm_trace_links_back_to_its_candidate(self, monkeypatch):
        self._run(monkeypatch, "[]")
        llm = [a for a in job_store.get_stage_artifacts("ct", "gap_mining") if a["kind"] == "llm"]
        assert llm and llm[0]["payload"]["chunk_id"] == "a::1"
        assert llm[0]["payload"]["source"] == "a.pdf"


class TestSilentLLMOutageIsNotAFinding:
    """copilotd mati/401 membuat generate() mengembalikan None tanpa galat;
    ekstraksi lalu menghasilkan 0 gap yang tampak sah. Terjadi nyata 4 Sep 2026:
    lima job berturut-turut '100 kandidat → 0 gap' tanpa satu pun peringatan."""

    def _run(self, monkeypatch, generate):
        job_store.save_job("gm-out", {"status": "running", "progress": 0})
        monkeypatch.setattr(research_pipeline.copilot_client, "generate", generate)
        return stage_gap_mining("gm-out", _chunks_file(SCRATCH / "chunks.jsonl"),
                                SCRATCH / "gaps.jsonl", workers=1)

    def test_all_calls_unanswered_is_flagged_as_system_failure(self, monkeypatch):
        out = self._run(monkeypatch, lambda *a, **k: None)
        assert out.metrics["llm_dipanggil"] > 0
        assert out.metrics["llm_tanpa_jawaban"] == out.metrics["llm_dipanggil"]
        assert out.metrics["gap_mentah"] == 0
        assert any("TIDAK MENJAWAB" in n and "BUKAN temuan" in n for n in out.notes)

    def test_partial_outage_is_reported_with_counts(self, monkeypatch):
        # Fixture bawaan hanya punya 1 kandidat; tambahkan jurnal kedua agar ada
        # dua panggilan LLM dan salah satunya bisa gagal.
        path = _chunks_file(SCRATCH / "chunks.jsonl")
        records = read_jsonl(str(path))
        records.append({"record": "chunk", "source": "b.pdf", "chunk_index": 0,
                        "chunk_id": "b::0", "section_normalized": "conclusion",
                        "token_count": 40, "is_reference": False, "text": _CONCLUSION})
        write_jsonl(str(path), records)
        calls = {"n": 0}

        def flaky(prompt, system=None, json_mode=False, temperature=None):
            calls["n"] += 1
            return None if calls["n"] == 1 else ("[]", "model-uji")
        job_store.save_job("gm-out", {"status": "running", "progress": 0})
        monkeypatch.setattr(research_pipeline.copilot_client, "generate", flaky)
        out = stage_gap_mining("gm-out", path, SCRATCH / "gaps.jsonl", workers=1)
        assert calls["n"] == 2
        assert out.metrics["llm_tanpa_jawaban"] == 1
        assert out.metrics["llm_dipanggil"] == 2
        assert any("1 dari 2" in n and "tidak dijawab" in n for n in out.notes)
        assert not any("BUKAN temuan" in n for n in out.notes)

    def test_healthy_llm_adds_no_outage_note(self, monkeypatch):
        out = self._run(monkeypatch, _llm_stub("[]"))
        assert out.metrics["llm_tanpa_jawaban"] == 0
        assert not any("tidak dijawab" in n or "TIDAK MENJAWAB" in n for n in out.notes)

    def test_unanswered_count_is_recorded_on_the_substep_event(self, monkeypatch):
        self._run(monkeypatch, lambda *a, **k: None)
        done = next(e for e in job_store.get_job_events("gm-out")
                    if e["type"] == "substep.completed"
                    and e["data"].get("substep") == "ekstrak_llm")
        assert done["data"]["llm_tanpa_jawaban"] == done["data"]["masuk"]


class TestSplitDuplicates:
    def test_returns_unique_and_duplicates_separately(self):
        gaps = [{"source": "a", "gap_statement": "X"}, {"source": "a", "gap_statement": "x "},
                {"source": "b", "gap_statement": "X"}]
        unique, dups = _split_duplicates(gaps)
        assert len(unique) == 2 and len(dups) == 1
        assert _dedup_gaps(gaps) == unique


class TestNoveltyProgress:
    def test_annotate_gaps_reports_progress_per_gap(self):
        class _NoHits:
            def search_recent(self, *a, **k):
                return []
        ticks: list[tuple[int, int]] = []
        annotate_gaps([{"gap_statement": "alpha beta"}, {"gap_statement": "gamma delta"}],
                      openalex=_NoHits(), on_progress=lambda d, t: ticks.append((d, t)))
        assert ticks == [(1, 2), (2, 2)]

    def test_annotate_gaps_without_callback_still_works(self):
        class _NoHits:
            def search_recent(self, *a, **k):
                return []
        out = annotate_gaps([{"gap_statement": "alpha beta"}], openalex=_NoHits())
        assert out[0]["novelty_status"] == "open"

    def test_stage_surfaces_openalex_progress_and_examples(self, monkeypatch):
        job_store.save_job("nv", {"status": "running", "progress": 0})
        write_jsonl(str(SCRATCH / "gaps.jsonl"), [
            {"record": "meta"},
            *[{"source": "a.pdf", "gap_statement": f"gap {i}", "gap_type": "implicit_gap"}
              for i in range(10)],
        ])

        def fake_annotate(gaps, on_progress=None, **_):
            out = []
            for i, g in enumerate(gaps, 1):
                status = "addressed" if i <= 3 else "open"
                out.append({**g, "novelty_status": status, "novelty_query": "q",
                            "related_recent_papers": [{"title": "P", "year": 2025,
                                                       "match_score": 0.8}]
                            if status == "addressed" else []})
                if on_progress:
                    on_progress(i, len(gaps))
            return out
        monkeypatch.setattr(research_pipeline, "annotate_gaps", fake_annotate)
        messages: list[str] = []
        original = research_pipeline.update_job

        def spy(job_id, **fields):
            if "message" in fields:
                messages.append(fields["message"])
            return original(job_id, **fields)
        monkeypatch.setattr(research_pipeline, "update_job", spy)

        out = stage_novelty("nv", SCRATCH / "gaps.jsonl", SCRATCH / "nov.jsonl")

        assert "Cek OpenAlex 5/10 gap" in messages and "Cek OpenAlex 10/10 gap" in messages
        assert len(out.substep_samples["contoh_addressed"]) == 3
        assert out.substep_samples["contoh_addressed"][0]["literatur_2024plus"][0]["match_score"] == 0.8
        done = next(e for e in job_store.get_job_events("nv")
                    if e["type"] == "substep.completed" and e["data"]["substep"] == "cek_kebaruan")
        assert done["data"]["masuk"] == 10 and done["data"]["keluar"] == 7
        assert done["data"]["addressed"] == 3


class TestScoreBreakdownIsPersisted:
    def test_proposal_records_carry_the_three_terms_that_sum_to_priority(self):
        job_store.save_job("sb", {"status": "running", "progress": 0})
        write_jsonl(str(SCRATCH / "nov.jsonl"), [
            {"record": "meta"},
            {"source": "a.pdf", "gap_statement": "Protokol pengujian alat forensik belum ada.",
             "gap_paraphrase": "Belum ada protokol pengujian alat.", "gap_type": "stated_limitation",
             "topic": "tools", "grounding_score": 0.9, "novelty_status": "open"},
            {"source": "b.pdf", "gap_statement": "Sudah dijawab.", "gap_type": "implicit_gap",
             "topic": "legal", "grounding_score": 1.0, "novelty_status": "addressed"},
        ])
        write_jsonl(str(SCRATCH / "chunks.jsonl"), [
            {"record": "meta"},
            {"record": "chunk", "source": "a.pdf", "paper_title": "A", "text": "Alat forensik."},
            {"record": "chunk", "source": "b.pdf", "paper_title": "B", "text": "Hukum digital."},
        ])
        out = stage_recommendation("sb", SCRATCH / "nov.jsonl", SCRATCH / "chunks.jsonl",
                                   SCRATCH / "rek.md")
        rec = research_pipeline.read_jsonl(out.outputs["proposals_jsonl"])[0]
        for key in ("gap_confidence", "novelty_credit", "actionability",
                    "nearest_paper", "nearest_similarity"):
            assert key in rec, key
        expected = (rec_novelty.W_GAP * rec["gap_confidence"]
                    + rec_novelty.W_NOVELTY * rec["novelty_credit"]
                    + rec_novelty.W_ACTIONABILITY * rec["actionability"])
        assert abs(expected - rec["priority_score"]) < 1e-3
        assert out.metrics["gap_bukan_open"] == 1
        assert out.substep_samples["dibuang_bukan_open"][0]["novelty_status"] == "addressed"
        assert out.substep_samples["tema_terbesar"][0]["size"] >= 1
