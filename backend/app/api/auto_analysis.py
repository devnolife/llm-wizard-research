"""Worker for the legacy 8-stage upload-and-analyze job.

The queue (``services/analysis_queue.py``) calls :func:`process_auto_analysis`
from its thread pool; nothing here runs on FastAPI's event loop. The HTTP
endpoints live in ``routes/analysis.py`` and only share the two job-store
wrappers ``_get_analysis_job`` / ``_set_analysis_job``.
"""

from loguru import logger
from typing import List
from pathlib import Path
import time

from .dependencies import (
    get_analysis_context,
    get_document_processor,
    release_analysis_context,
)
from ..core.recommendation.novelty import rank_proposals
from ..core.pipeline.pipeline import process_pdf_as_document
from ..core.pipeline.io import read_jsonl
from ..core.gap_detection.paper_profiles import build_profiles
from ..utils.job_store import (
    add_stage_artifact,
    complete_job,
    get_job,
    get_stage_artifacts,
    is_cancel_requested,
    record_job_event,
    save_job,
)
from ..services import skill_guidance
from .routes.analysis_helpers import (
    _build_recommendations_from_gaps,
    _is_degenerate_text,
    _parse_gap_json,
    _parse_paper_groups_json,
    _parse_recommendations_json,
    _parse_roadmap_json,
    _parse_selection_json,
    _parse_weaknesses_json,
    _verify_paper_weaknesses,
)

# Skill AI-Research-SKILLs yang terpakai per job (diisi _traced_generate,
# dimasukkan ke results.skills_used saat job selesai).
_JOB_SKILLS: dict[str, set] = {}


def _set_analysis_job(job_id: str, **updates):
    job = dict(get_job(job_id) or {})
    job.update(updates)
    save_job(job_id, job)
    return job


def _get_analysis_job(job_id: str):
    return get_job(job_id)


class JobCancelled(Exception):
    """Raised between analysis phases after a user requests cancellation."""


def _load_author_gaps(gap_job_id: str) -> tuple[list[dict], str]:
    """Gap-mining records of a research job, reduced to author statements.

    Returns ``(records, note)``; ``records`` is empty and ``note`` explains why
    when the job never finished gap mining or its JSONL file is gone. The path
    comes from a server-written artifact, never from the request.
    """
    for art in reversed(get_stage_artifacts(gap_job_id, "gap_mining")):
        if art.get("kind") != "result":
            continue
        raw = ((art.get("payload") or {}).get("outputs") or {}).get("gaps_jsonl")
        if not raw or not Path(raw).exists():
            return [], f"job gap mining {gap_job_id[:8]} tidak menyimpan berkas gaps_jsonl"
        records = []
        for rec in read_jsonl(str(raw)):
            if rec.get("record") == "meta" or not rec.get("gap_statement"):
                continue
            evidence = rec.get("evidence_chunk_ids") or []
            records.append({
                "source": rec.get("source"),
                "statement": rec.get("gap_statement"),
                "paraphrase": rec.get("gap_paraphrase"),
                "kind": rec.get("gap_type"),
                "chunk_id": evidence[0] if evidence else None,
                "grounding_score": rec.get("grounding_score"),
                "topic": rec.get("topic"),
            })
        return records, ""
    return [], f"job gap mining {gap_job_id[:8]} belum menyelesaikan tahap gap_mining"


def _ensure_job_active(job_id: str) -> None:
    if is_cancel_requested(job_id):
        raise JobCancelled("Analisis dibatalkan oleh pengguna")


def _save_stage_artifact(job_id: str, phase: str, kind: str, label: str = "", payload=None) -> None:
    """Best-effort persistence — artifact failures must never break the pipeline."""
    try:
        add_stage_artifact(job_id, phase, kind, label=label, payload=payload or {})
    except Exception as exc:
        logger.debug(f"Stage artifact skipped ({phase}/{kind}): {exc}")


def _traced_generate(glm, job_id: str, phase: str, label: str, prompt: str, **kwargs) -> str:
    """Run ``glm.generate`` and persist the prompt + raw response for the process UI.

    Prompt otomatis diperkaya panduan AI-Research-SKILLs sesuai fase
    (lihat services/skill_guidance.py) — skill dipakai di semua tahap analisis.
    """
    prompt, skills_used = skill_guidance.wrap_prompt(phase, prompt)
    if skills_used:
        _JOB_SKILLS.setdefault(job_id, set()).update(skills_used)
    response = glm.generate(prompt, **kwargs)
    _save_stage_artifact(
        job_id,
        phase,
        "llm",
        label=label,
        payload={
            "prompt": prompt,
            "response": response,
            "model": getattr(glm, "active_model_name", None)
            or getattr(getattr(glm, "config", None), "model_name", "")
            or "",
            "skills_used": skills_used,
            "params": {k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool))},
        },
    )
    return response


def _add_uploaded_paper_similarity(papers, vector_store) -> None:
    """Attach each paper's mean semantic similarity to the other uploads.

    The score is deliberately scoped to the current upload set, not the shared
    corpus.  It gives a researcher a quick indication of topical overlap while
    preserving the detailed evidence analysis elsewhere in the result.
    """
    for paper in papers:
        paper["similarity_percent"] = None
    if len(papers) < 2:
        return

    try:
        import numpy as np

        texts = [str(paper.get("content", ""))[:6000] for paper in papers]
        embeddings = np.asarray(
            vector_store.embedding_model.encode(texts, show_progress_bar=False),
            dtype=float,
        )
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / np.maximum(norms, 1e-12)
        similarity_matrix = normalized @ normalized.T
        for index, paper in enumerate(papers):
            other_scores = np.delete(similarity_matrix[index], index)
            average = float(np.clip(other_scores.mean(), 0.0, 1.0))
            paper["similarity_percent"] = round(average * 100)
    except Exception as exc:
        logger.warning(f"Could not calculate uploaded-paper similarity: {exc}")


def process_auto_analysis(job_id: str, pdf_paths: List[Path] | None = None):
    """Run one durable job with an isolated context and scoped retrieval.

    The local queue calls this synchronous function from its worker pool.  It
    intentionally does not run on FastAPI's event loop.  ``pdf_paths`` remains
    optional for legacy/manual callers; durable queue workers load it from the
    persisted job payload.
    """
    try:
        job = _get_analysis_job(job_id)
        if job is None:
            raise RuntimeError("Analysis job not found")
        if pdf_paths is None:
            pdf_paths = [Path(path) for path in (job.get("payload") or {}).get("pdf_paths", [])]
        if not pdf_paths or any(not path.exists() for path in pdf_paths):
            raise FileNotFoundError("Input PDF for this analysis job is unavailable")

        _ensure_job_active(job_id)
        _set_analysis_job(job_id, status="running", progress=5, message="Processing PDFs...")
        record_job_event(job_id, "phase.started", phase="ingestion", status="running")
        _phase_started = time.monotonic()

        analysis_context = get_analysis_context(job_id)
        vector_store = analysis_context.vector_store
        document_processor = get_document_processor()
        glm = analysis_context.llm

        # Retries must not reuse partial chunks from an earlier worker attempt.
        vector_store.delete_by_metadata({"analysis_job_id": job_id})

        # ── Step 1: Ingest PDFs into vector store ──────────────
        total_chunks = 0
        paper_contents = []
        new_papers = 0
        duplicate_papers = 0
        for i, pdf_path in enumerate(pdf_paths):
            _ensure_job_active(job_id)
            # Inputs are stored as "{index}_{original-name}" in their job directory.
            source_name = pdf_path.name.split('_', 1)[-1]
            _set_analysis_job(
                job_id,
                message=f"Processing {source_name}...",
                progress=5 + (i / len(pdf_paths)) * 15,
            )
            record_job_event(
                job_id,
                "file.started",
                phase="ingestion",
                status="running",
                data={"file": source_name, "index": i + 1, "of": len(pdf_paths)},
            )
            _file_started = time.monotonic()

            processed_doc = process_pdf_as_document(
                str(pdf_path), source=source_name, job_id=job_id
            )
            # Each analysis is intentionally scoped to its own source chunks.
            # Re-ingesting an identical filename is preferable to leaking data
            # from an earlier job through the shared corpus.
            already_indexed = False
            for chunk in processed_doc.chunks:
                # chunk.metadata already carries the full new schema
                # (source, section_normalized, is_reference, page_start,
                # token_count, doi, extraction_quality, chunk_id, ...).
                metadata = dict(chunk.metadata)
                metadata["analysis_job_id"] = job_id
                metadata["source"] = source_name
                metadata.setdefault("title", processed_doc.title or source_name)
                vector_store.add_document(chunk.content, metadata)
                total_chunks += 1
            new_papers += 1

            paper_contents.append({
                "source": source_name,
                "title": processed_doc.title or source_name,
                "year": processed_doc.metadata.get("year"),
                "content": " ".join(c.content for c in processed_doc.chunks[:10]),
                "full_content": processed_doc.content or " ".join(
                    c.content for c in processed_doc.chunks
                ),
                "num_chunks": len(processed_doc.chunks),
                # Sampel potongan ASLI utk UI "lihat isi dokumen dipotong":
                # 3 chunk pertama, teks verbatim (dipangkas 350 char).
                "sample_chunks": [
                    {
                        "chunk_index": c.chunk_index,
                        "section": (c.metadata or {}).get("section"),
                        "text": c.content[:350],
                    }
                    for c in processed_doc.chunks[:3]
                ],
                "weakness_context": document_processor.extract_weakness_sections(
                    processed_doc.content or " ".join(
                        c.content for c in processed_doc.chunks
                    )
                ),
                "already_indexed": already_indexed,
            })

            record_job_event(
                job_id,
                "file.completed",
                phase="ingestion",
                status="running",
                duration_ms=int((time.monotonic() - _file_started) * 1000),
                data={
                    "file": source_name,
                    "index": i + 1,
                    "of": len(pdf_paths),
                    "extraction_method": processed_doc.metadata.get("extraction_method", ""),
                    "ocr_used": bool(processed_doc.metadata.get("ocr_used", False)),
                    "chars": len(processed_doc.content or ""),
                    "chunks": len(processed_doc.chunks),
                },
            )
            _save_stage_artifact(
                job_id,
                "ingestion",
                "extraction",
                label=source_name,
                payload={
                    "file": source_name,
                    "index": i + 1,
                    "of": len(pdf_paths),
                    "title": processed_doc.title or source_name,
                    "year": processed_doc.metadata.get("year"),
                    "extraction_method": processed_doc.metadata.get("extraction_method", ""),
                    "ocr_used": bool(processed_doc.metadata.get("ocr_used", False)),
                    "chars": len(processed_doc.content or ""),
                    "chunks": len(processed_doc.chunks),
                    "preview": (processed_doc.content or "")[:4000],
                    "sample_chunks": [
                        {
                            "chunk_index": c.chunk_index,
                            "section": (c.metadata or {}).get("section"),
                            "text": c.content[:350],
                        }
                        for c in processed_doc.chunks[:3]
                    ],
                },
            )

        # Once, after every upload is parsed: the pairwise matrix embeds all
        # papers, so calling it inside the loop re-encoded the whole set on
        # each iteration (O(n^2) encodings) for values that were overwritten.
        _add_uploaded_paper_similarity(paper_contents, vector_store)

        record_job_event(
            job_id,
            "phase.completed",
            phase="ingestion",
            status="running",
            duration_ms=int((time.monotonic() - _phase_started) * 1000),
            data={"files_processed": len(paper_contents), "chunks": total_chunks},
        )

        _set_analysis_job(job_id, progress=20, message="Extracting topics...")
        _ensure_job_active(job_id)
        record_job_event(job_id, "phase.started", phase="topics", status="running")
        _phase_started = time.monotonic()

        # ── Step 2: Extract topics from UPLOADED papers only ────
        sample_text = " ".join([p["content"] for p in paper_contents])

        topic_prompt = f"""Analisis konten penelitian berikut dan ekstrak 5 topik utama penelitian.
Kembalikan HANYA dalam bentuk daftar bernomor, satu topik per baris. Gunakan Bahasa Indonesia.

Konten: {sample_text[:3000]}

Topik:"""

        topics_text = _traced_generate(
            glm, job_id, "topics", "Ekstraksi topik utama", topic_prompt, max_tokens=200
        )
        topics = [
            line.strip()
            for line in topics_text.strip().split("\n")
            if line.strip() and line.strip()[0].isdigit()
        ]
        record_job_event(
            job_id,
            "phase.completed",
            phase="topics",
            status="running",
            duration_ms=int((time.monotonic() - _phase_started) * 1000),
            data={"topics": len(topics)},
        )
        _save_stage_artifact(job_id, "topics", "result", payload={"topics": topics})

        # ── Steps 2b/2c/2d run CONCURRENTLY (they are independent) ──────────
        # 2b: classify papers by basis · 2c: shared keywords/themes ·
        # 2d: per-paper weaknesses. Each is defined as a closure and executed in
        # parallel threads; the ollama client releases the GIL during requests.
        _set_analysis_job(job_id, message="Menganalisis basis, persamaan & kekurangan jurnal...")
        record_job_event(job_id, "phase.started", phase="paper_analysis", status="running")
        _phase_started = time.monotonic()

        def _compute_groups():
            paper_list = "\n".join(
                f"- {p['title']}: {p['content'][:300]}" for p in paper_contents
            )
            group_prompt = (
                "Klasifikasikan setiap jurnal berikut berdasarkan BASIS utamanya "
                "(metode, algoritma, model, atau pendekatan inti yang digunakan). "
                "Gunakan label basis yang singkat dan konsisten dalam Bahasa Indonesia "
                "(mis. 'Algoritma Greedy', 'Deep Learning / CNN', 'Optimasi Metaheuristik'). "
                "Jurnal dengan basis serupa harus memakai label yang sama persis.\n\n"
                f"Daftar jurnal:\n{paper_list}\n\n"
                "Kembalikan HANYA JSON array (tanpa teks lain): "
                '[{"title": "judul jurnal", "basis": "label basis"}]'
            )
            raw_groups = _traced_generate(
                glm, job_id, "paper_analysis", "Klasifikasi basis paper",
                group_prompt, max_tokens=400,
            ).strip()
            return _parse_paper_groups_json(raw_groups)

        def _compute_similarity():
            sim_block = "\n\n".join(
                f"Paper {i + 1}:\nJudul: {p['title']}\nKonten: {p['content'][:400]}"
                for i, p in enumerate(paper_contents)
            )
            sim_prompt = (
                "Analisis jurnal-jurnal berikut dan temukan PERSAMAANNYA. Gunakan Bahasa Indonesia.\n\n"
                f"{sim_block}\n\n"
                "Tugas:\n"
                "1. common_keywords: 5-8 kata kunci/konsep/metode yang SAMA atau berulang di jurnal-jurnal ini.\n"
                "2. shared_themes: 2-4 tema bersama (apa yang sama-sama dikerjakan jurnal-jurnal ini).\n"
                "3. summary: ringkasan 1-2 kalimat tentang benang merah jurnal-jurnal ini.\n\n"
                "Kembalikan HANYA JSON (tanpa teks lain): "
                '{"common_keywords": [...], "shared_themes": [...], "summary": "..."}'
            )
            raw_sim = _traced_generate(
                glm, job_id, "paper_analysis", "Persamaan antar paper",
                sim_prompt, max_tokens=500, format="json",
            )
            parsed_sim = _parse_selection_json(raw_sim if isinstance(raw_sim, str) else str(raw_sim))
            return {
                "common_keywords": parsed_sim.get("common_keywords", []),
                "shared_themes": parsed_sim.get("shared_themes", []),
                "summary": parsed_sim.get("summary", ""),
            }

        def _compute_weaknesses():
            def _weak_prompt(p):
                # Ground the analysis in the sections where authors actually
                # state weaknesses (Limitations / Future Work / Conclusion),
                # plus a short lead-in for context — NOT just the intro.
                weakness_ctx = (p.get("weakness_context") or "").strip()
                lead_in = (p.get("content") or "")[:600]
                evidence_block = (
                    f"[BAGIAN KETERBATASAN/KESIMPULAN JURNAL]\n{weakness_ctx}\n\n"
                    f"[CUPLIKAN AWAL JURNAL]\n{lead_in}"
                ) if weakness_ctx else f"Konten: {(p.get('content') or '')[:1800]}"
                return (
                    "Anda adalah reviewer jurnal ilmiah. Analisis SATU jurnal berikut dan temukan "
                    "KEKURANGAN/keterbatasannya secara KONKRET berdasarkan isinya (bukan tebakan umum).\n\n"
                    "Bedakan dua jenis. Untuk SETIAP poin WAJIB sertakan 'dasar' (bukti/alasan dari isi jurnal):\n"
                    "- tersurat: kelemahan yang DITULIS EKSPLISIT oleh penulis. WAJIB sertakan 'kutipan' = "
                    "potongan kalimat (5-20 kata) yang DISALIN PERSIS dari teks jurnal (verbatim) tempat "
                    "kelemahan itu disebut (mis. bagian keterbatasan, saran, atau future work). 'dasar' = "
                    "parafrase singkat dari kutipan itu.\n"
                    "- tersirat: kelemahan yang TIDAK ditulis tapi DISIMPULKAN dari isi. 'dasar' = fakta "
                    "spesifik di jurnal yang jadi alasannya (mis. 'hanya menguji 1 dataset', 'tidak ada "
                    "perbandingan dengan metode lain', 'tidak ada uji statistik', 'ruang lingkup hanya 1 kasus').\n\n"
                    "LARANGAN: jangan memakai kata ragu seperti 'mungkin', 'sepertinya', 'kemungkinan', "
                    "'bisa jadi'. Nyatakan observasi + simpulan secara tegas. Jika tidak ada dasar nyata di "
                    "teks, JANGAN mengarang poin (kembalikan array kosong saja). Untuk tersurat, kalau tidak "
                    "ada kutipan verbatim yang bisa disalin, JANGAN buat poin tersurat.\n\n"
                    f"Judul: {p['title']}\n"
                    f"{evidence_block}\n\n"
                    "Aturan: maksimal 3 poin per kategori; 'poin' = 1 kalimat singkat & spesifik, "
                    "'dasar' = 1 kalimat berisi bukti dari jurnal. Gunakan Bahasa Indonesia.\n"
                    "Kembalikan HANYA JSON (tanpa teks lain): "
                    '{"tersurat": [{"poin": "...", "dasar": "...", "kutipan": "..."}], '
                    '"tersirat": [{"poin": "...", "dasar": "..."}]}'
                )

            prompts = [_weak_prompt(p) for p in paper_contents]
            raws = glm.generate_batch(prompts, max_tokens=600, format="json")
            out = []
            for p, weak_prompt, raw_weak in zip(paper_contents, prompts, raws):
                raw_weak_text = raw_weak if isinstance(raw_weak, str) else str(raw_weak)
                _save_stage_artifact(
                    job_id,
                    "paper_analysis",
                    "llm",
                    label=f"Kekurangan jurnal: {p['title'][:70]}",
                    payload={"prompt": weak_prompt, "response": raw_weak_text},
                )
                parsed_weak = _parse_weaknesses_json(raw_weak_text)
                # Verify each point against the paper text so the UI's promise
                # ("disertai dasar dari jurnal — bukan tebakan") actually holds.
                verified = _verify_paper_weaknesses(
                    parsed_weak, p.get("full_content", ""),
                    source_name=p.get("source", ""),
                    vector_store=vector_store,
                    analysis_job_id=job_id,
                )
                out.append({
                    "title": p["title"],
                    "source": p["source"],
                    "tersurat": verified["tersurat"],
                    "tersirat": verified["tersirat"],
                })
            return out

        paper_groups = []
        paper_similarity = {"common_keywords": [], "shared_themes": [], "summary": ""}
        paper_weaknesses = []

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as _stage_pool:
            _f_groups = _stage_pool.submit(_compute_groups)
            _f_sim = _stage_pool.submit(_compute_similarity)
            _f_weak = _stage_pool.submit(_compute_weaknesses)
            try:
                paper_groups = _f_groups.result()
            except Exception as group_err:
                logger.warning(f"Paper grouping failed: {group_err}")
            try:
                paper_similarity = _f_sim.result()
            except Exception as sim_err:
                logger.warning(f"Paper similarity analysis failed: {sim_err}")
            try:
                paper_weaknesses = _f_weak.result()
            except Exception as weak_err:
                logger.warning(f"Paper weakness analysis failed: {weak_err}")

        # Per-journal side-channel for the gap analyzer: the coordinator only
        # hands it RAG passages, so author-stated weaknesses would otherwise
        # never reach the indicators as corroborating evidence.
        author_gaps: list[dict] = []
        gap_note = ""
        gap_job_id = str((job.get("payload") or {}).get("gap_job_id") or "")
        if gap_job_id:
            author_gaps, gap_note = _load_author_gaps(gap_job_id)
        paper_profiles = build_profiles(
            paper_contents, weaknesses=paper_weaknesses, author_gaps=author_gaps,
        )
        matched_gaps = sum(len(prof.author_gaps) for prof in paper_profiles.values())
        if gap_job_id and author_gaps and not matched_gaps:
            gap_note = "tidak ada jurnal job gap mining yang cocok dengan jurnal job ini"
        if gap_note:
            logger.warning(f"Author gaps from {gap_job_id[:8]} not attached: {gap_note}")
        profile_summary = [
            {
                "source": prof.source,
                "tersurat": len(prof.weaknesses.get("tersurat") or []),
                "tersirat": len(prof.weaknesses.get("tersirat") or []),
                "author_gaps": len(prof.author_gaps),
            }
            for prof in paper_profiles.values()
        ]

        record_job_event(
            job_id,
            "phase.completed",
            phase="paper_analysis",
            status="running",
            duration_ms=int((time.monotonic() - _phase_started) * 1000),
            data={
                "groups": len(paper_groups),
                "weaknesses": len(paper_weaknesses),
                "common_keywords": len(paper_similarity.get("common_keywords", [])),
                "profiles": len(paper_profiles),
            },
        )
        _save_stage_artifact(
            job_id,
            "paper_analysis",
            "result",
            payload={
                "groups": paper_groups,
                "similarity": paper_similarity,
                "weaknesses": paper_weaknesses,
                "profiles": profile_summary,
                "author_gaps": {
                    "gap_job_id": gap_job_id or None,
                    "loaded": len(author_gaps),
                    "matched": matched_gaps,
                    "note": gap_note,
                },
            },
        )

        _ensure_job_active(job_id)

        # ── Step 3: Run Coordinator (full neuro-symbolic pipeline) ──
        _set_analysis_job(
            job_id,
            progress=30,
            message="Running neuro-symbolic analysis (Observe \u2192 Think \u2192 Act \u2192 Evaluate)...",
        )
        record_job_event(job_id, "phase.started", phase="neuro_symbolic", status="running")
        _phase_started = time.monotonic()

        coordinator_result = None
        execution_mode = "llm_fallback"
        reasoning_trace = []
        gap_indicators = []
        rule_engine_report = {}
        fact_table_stats = {}
        sample_facts = []

        try:
            coordinator = analysis_context.coordinator
            main_topic = topics[0] if topics else "research analysis"

            coordinator_result = coordinator.process_research_query(
                query=main_topic,
                context={
                    "topics": topics,
                    "paper_contents": paper_contents,
                    "total_chunks": total_chunks,
                    "paper_profiles": {k: v.to_dict() for k, v in paper_profiles.items()},
                },
            )

            execution_mode = coordinator_result.get("execution_mode", "sequential")
            reasoning_trace = coordinator_result.get("reasoning_trace", [])
            gap_indicators = coordinator_result.get("gap_indicators", [])
            rule_engine_report = coordinator_result.get("rule_engine_report", {})
            fact_table_stats = coordinator_result.get("fact_table_stats", {})

            # Sampel fakta NYATA (SPO) utk UI "perlihatkan proses LLM":
            # nama entitas di-resolve agar terbaca manusia.
            try:
                ft = analysis_context.fact_table
                for fact in list(ft.query())[:8]:
                    subj = ft.get_entity(fact.subject_id)
                    obj = ft.get_entity(fact.object_id)
                    sample_facts.append({
                        "subject": subj.name if subj else fact.subject_id,
                        "subject_type": subj.entity_type.value if subj else "?",
                        "predicate": fact.predicate.value if hasattr(fact.predicate, "value") else str(fact.predicate),
                        "object": obj.name if obj else fact.object_id,
                        "object_type": obj.entity_type.value if obj else "?",
                        "confidence": float(fact.confidence),
                        "source_paper": fact.source_paper or "",
                    })
            except Exception as fact_err:
                logger.debug(f"Could not sample facts for UI: {fact_err}")

            _set_analysis_job(
                job_id,
                progress=70,
                message=f"Coordinator complete ({execution_mode}). Generating summary...",
            )

            _ensure_job_active(job_id)

            logger.info(
                f"Coordinator finished: mode={execution_mode}, "
                f"gaps={len(gap_indicators)}, "
                f"facts={fact_table_stats.get('total_facts', 0)}"
            )
            record_job_event(
                job_id,
                "phase.completed",
                phase="neuro_symbolic",
                status="running",
                duration_ms=int((time.monotonic() - _phase_started) * 1000),
                data={
                    "indicators": len(gap_indicators),
                    "facts": fact_table_stats.get("total_facts", 0),
                    "mode": execution_mode,
                },
            )
            _save_stage_artifact(
                job_id,
                "neuro_symbolic",
                "result",
                payload={
                    "mode": execution_mode,
                    "indicators": gap_indicators,
                    "sample_facts": sample_facts,
                    "rule_engine_report": rule_engine_report,
                    "fact_table_stats": fact_table_stats,
                    "reasoning_trace": reasoning_trace,
                },
            )

        except JobCancelled:
            raise
        except Exception as e:
            logger.warning(f"Coordinator pipeline failed, falling back to LLM: {e}")
            _set_analysis_job(job_id, message="Coordinator unavailable, using LLM fallback...")
            record_job_event(
                job_id,
                "phase.failed",
                phase="neuro_symbolic",
                status="running",
                duration_ms=int((time.monotonic() - _phase_started) * 1000),
                data={"error_type": type(e).__name__, "fallback": "llm"},
            )
            reasoning_trace.append({
                "phase": "coordinator_fallback",
                "error": str(e),
            })

        # ── Step 4: Generate summary (always via LLM) ──────────
        _set_analysis_job(job_id, progress=75, message="Generating research summary...")
        _ensure_job_active(job_id)
        record_job_event(job_id, "phase.started", phase="summary", status="running")
        _phase_started = time.monotonic()

        if topics:
            search_results = analysis_context.retriever.retrieve(topics[0], top_k=15)
            context = "\n\n".join(
                [f"Document {i+1}: {r.document.content}" for i, r in enumerate(search_results)]
            )

            summary_prompt = f"""Berikan ringkasan penelitian yang komprehensif untuk topik: {topics[0]}
Gunakan Bahasa Indonesia.

Konteks dari paper:
{context[:3000]}

Ringkasan:"""
            summary = _traced_generate(
                glm, job_id, "summary", "Ringkasan penelitian", summary_prompt, max_tokens=500
            )
        else:
            summary = "No topics extracted."
        record_job_event(
            job_id,
            "phase.completed",
            phase="summary",
            status="running",
            duration_ms=int((time.monotonic() - _phase_started) * 1000),
            data={"chars": len(summary or "")},
        )
        _save_stage_artifact(job_id, "summary", "result", payload={"summary": summary})

        # ── Step 5: Gap detection (use coordinator result or LLM fallback) ──
        _set_analysis_job(job_id, progress=80, message="Finalizing gap analysis...")
        _ensure_job_active(job_id)
        record_job_event(job_id, "phase.started", phase="gaps", status="running")
        _phase_started = time.monotonic()

        gaps = []
        if gap_indicators:
            # Coordinator returned structured gap indicators — normalise to dicts
            for gi in gap_indicators:
                gaps.append({
                    "title": gi.get("title", ""),
                    "description": gi.get("description", ""),
                    "type": gi.get("type", gi.get("indicator_type", "FRAGMENTATION")),
                    "confidence": gi.get("confidence", 0.0),
                    "calibrated_confidence": gi.get("calibrated_confidence"),
                    "needs_review": bool(gi.get("needs_review", False)),
                    "abstention_reasons": gi.get("abstention_reasons", []),
                    "calibration": gi.get("calibration", {}),
                    "provenance": gi.get("provenance", {}),
                    "rule_engine_verdict": gi.get("rule_engine_verdict", None),
                    "evidence": gi.get("evidence", []),
                    "suggested_directions": gi.get("suggested_directions", []),
                    "related_papers": [
                        str(rp).strip() for rp in (gi.get("related_papers") or [])
                        if str(rp).strip()
                    ],
                    "detection_method": gi.get("detection_method", ""),
                    "supporting_quotes": gi.get("supporting_quotes", []),
                    "sub_indicators": gi.get("sub_indicators", []),
                })
        else:
            # LLM fallback — generate structured gaps then validate via Rule Engine
            rule_engine = analysis_context.rule_engine

            for topic in topics[:3]:
                _ensure_job_active(job_id)
                search_results = analysis_context.retriever.retrieve(topic, top_k=10)
                context = "\n\n".join(
                    [f"Document {i+1}: {r.document.content}" for i, r in enumerate(search_results)]
                )

                gap_prompt = f"""Identifikasi SATU indikator SYNTHESIS GAP untuk topik: {topic}. Gunakan Bahasa Indonesia.

Definisi (Cooper, 1998; Booth et al., 2012) — synthesis gap HANYA salah satu dari 3 ini:
- FRAGMENTATION: paper membahas fenomena sama dari sudut berbeda tetapi tidak terintegrasi.
- INCONSISTENCY: temuan empiris antar-paper saling bertentangan dan belum direkonsiliasi.
- INCOMPLETENESS: aspek kritis fenomena belum dicakup bersama oleh paper-paper yang ada.

BUKAN synthesis gap (JANGAN keluarkan ini):
- kombinasi "Metode A + Domain B" yang belum ada (itu sekadar penerapan/belum diterapkan).
- topik yang sama sekali belum diteliti (itu knowledge gap).
- saran "future work" yang ditulis penulis paper (itu explicit gap).

Konteks dari paper:
{context[:2000]}

Kembalikan gap dalam format JSON TEPAT ini (tanpa teks tambahan):
{{"title": "Judul gap singkat", "description": "2-3 kalimat menjelaskan indikator gap berbasis perbandingan antar-paper", "type": "FRAGMENTATION atau INCONSISTENCY atau INCOMPLETENESS"}}

JSON:"""
                raw = _traced_generate(
                    glm, job_id, "gaps", f"Deteksi gap topik: {topic[:70]}",
                    gap_prompt, max_tokens=300,
                ).strip()

                # Parse LLM output into structured dict
                gap_dict = _parse_gap_json(raw)

                # Apply Rule Engine validation to LLM-generated gap
                verdict = None
                if rule_engine and gap_dict:
                    try:
                        claim = {
                            "claim": gap_dict.get("description", ""),
                            "indicator_type": gap_dict.get("type", "FRAGMENTATION"),
                        }
                        validation = rule_engine.validate(claim, {"topic": topic})
                        verdict = getattr(validation, "overall_verdict", None)
                        if isinstance(verdict, str):
                            pass
                        elif hasattr(verdict, "value"):
                            verdict = verdict.value
                        else:
                            verdict = str(verdict) if verdict else None

                        # Track in report
                        if verdict == "PASS":
                            rule_engine_report["passed"] = rule_engine_report.get("passed", 0) + 1
                        elif verdict == "FLAG":
                            rule_engine_report["flagged"] = rule_engine_report.get("flagged", 0) + 1
                        elif verdict == "REJECT":
                            rule_engine_report["rejected"] = rule_engine_report.get("rejected", 0) + 1
                        rule_engine_report["total"] = rule_engine_report.get("total", 0) + 1
                    except Exception as re_err:
                        logger.warning(f"Rule Engine validation failed for LLM gap: {re_err}")

                gap_dict["rule_engine_verdict"] = verdict
                gap_dict["confidence"] = gap_dict.get("confidence", 0.5)
                gap_dict["evidence"] = gap_dict.get("evidence", [])
                gap_dict["suggested_directions"] = gap_dict.get("suggested_directions", [])
                gap_dict["related_papers"] = gap_dict.get("related_papers", [])

                # Skip REJECT gaps
                if verdict != "REJECT":
                    gaps.append(gap_dict)

        # ── Step 6: Usulan penelitian (SELALU berlabuh ke indikator synthesis gap) ──
        # Sesuai revisi penguji: usulan harus mengacu pada 3 indikator Cooper/Booth
        # (fragmentasi, inkonsistensi, ketidaklengkapan kolektif), BUKAN kombinasi
        # metode+domain dangkal atau pengulangan "future work". Diposisikan sebagai
        # INDIKATOR usulan (decision-support) yang tetap perlu validasi peneliti.
        record_job_event(
            job_id,
            "phase.completed",
            phase="gaps",
            status="running",
            duration_ms=int((time.monotonic() - _phase_started) * 1000),
            data={"gaps": len(gaps)},
        )
        _save_stage_artifact(job_id, "gaps", "result", payload={"gaps": gaps})
        _set_analysis_job(
            job_id,
            progress=85,
            message="Menyusun usulan penelitian (berbasis indikator synthesis gap)...",
        )
        record_job_event(job_id, "phase.started", phase="proposal", status="running")
        _phase_started = time.monotonic()

        # Rekomendasi paper relevan dari coordinator disimpan terpisah sebagai rujukan,
        # bukan sebagai "usulan penelitian baru".
        related_paper_refs = []
        if coordinator_result and isinstance(coordinator_result.get("recommendations"), list):
            for r in coordinator_result["recommendations"]:
                if isinstance(r, dict) and r.get("title"):
                    related_paper_refs.append({
                        "title": r.get("title", ""),
                        "reason": r.get("reason", r.get("description", "")),
                    })

        gaps_context = "\n".join([
            f"- [{g.get('type','UNKNOWN')}] {g.get('title','')}: {g.get('description','')}"
            for i, g in enumerate(gaps)
        ]) or "(indikator gap belum terdeteksi secara eksplisit)"

        rec_prompt = f"""Anda membantu menyusun USULAN PENELITIAN BARU dari hasil sintesis beberapa jurnal.
Gunakan Bahasa Indonesia.

PENTING — kerangka synthesis gap (Cooper, 1998; Booth et al., 2012). Setiap usulan WAJIB
menjawab salah satu dari 4 indikator berikut:
1. FRAGMENTASI — jurnal membahas fenomena sama dari sudut berbeda tetapi tidak terintegrasi.
2. INKONSISTENSI — temuan antar-jurnal saling bertentangan dan belum direkonsiliasi.
3. KETIDAKLENGKAPAN KOLEKTIF — aspek kritis fenomena belum tercakup bersama oleh jurnal-jurnal itu.
4. KETIADAAN DUKUNGAN BUKTI — aspek justru sering diklaim lintas jurnal, tetapi tidak ada
   bukti primer yang dapat ditelusuri untuk mendukungnya (klaim berulang tanpa pembuktian).

LARANGAN KERAS (usulan seperti ini DITOLAK penguji):
- JANGAN mengusulkan sekadar "kombinasi Metode A + Domain B" (itu penerapan, bukan sintesis).
- JANGAN mengulang kalimat "future work"/saran yang sudah ditulis penulis jurnal (itu explicit gap).
- JANGAN mengusulkan topik yang sama sekali belum diteliti (itu knowledge gap, bukan synthesis gap).

Topik dari jurnal: {', '.join(topics[:3])}

Indikator synthesis gap yang terdeteksi:
{gaps_context}

Buat 5 usulan. Untuk tiap usulan:
- "title": judul usulan penelitian yang spesifik.
- "description": apa yang diteliti, dirumuskan sebagai upaya MENGINTEGRASIKAN / MEREKONSILIASI /
  MELENGKAPI literatur (sesuai indikator gap-nya).
- "gap_type": salah satu dari FRAGMENTATION / INCONSISTENCY / INCOMPLETENESS / SUPPORT_GAP.
- "why": mengapa penting — sebutkan indikator gap mana yang dijawab.
- "how": metodologi yang disarankan secara ringkas.

Catatan: usulan ini bersifat INDIKATIF (alat bantu keputusan) dan tetap memerlukan
penilaian peneliti — jangan menyatakannya sebagai temuan yang pasti.

Kembalikan HANYA JSON array (tanpa teks tambahan):
[{{"title": "...", "description": "...", "gap_type": "FRAGMENTATION", "why": "...", "how": "..."}}]

JSON:"""
        try:
            raw = _traced_generate(
                glm, job_id, "proposal", "Usulan penelitian (berbasis gap)",
                rec_prompt, max_tokens=800, format="json",
            ).strip()
            recommendations = _parse_recommendations_json(raw)
        except Exception as rec_err:
            logger.warning(f"Recommendation generation failed: {rec_err}")
            recommendations = []

        # Drop any leftover degenerate entries (e.g. "[INCOMPLETENESS]").
        recommendations = [
            r for r in recommendations
            if not (_is_degenerate_text(r.get("title", "")) and _is_degenerate_text(r.get("description", "")))
        ]

        # Robust fallback: if the (small) model produced nothing usable, synthesise
        # gap-anchored proposals deterministically from the detected gap indicators.
        if not recommendations and gaps:
            logger.info("LLM recommendations empty/degenerate — building deterministically from gaps.")
            recommendations = _build_recommendations_from_gaps(gaps)

        # Rank the (already gap-anchored) proposals by semantic novelty against
        # the corpus. Novelty is a PRIORITY signal, never a gap in itself —
        # BAB II Subbab 2.2.2 rules out "an untried method-domain combination" as a
        # synthesis gap, so it may only reorder defensible proposals.
        if recommendations:
            try:
                embedder = getattr(
                    getattr(analysis_context, "vector_store", None),
                    "embedding_model",
                    None,
                )
                recommendations = rank_proposals(
                    recommendations,
                    [
                        {
                            "source": p.get("source", ""),
                            "title": p.get("title", ""),
                            "content": str(p.get("content") or "")[:1500],
                        }
                        for p in paper_contents
                    ],
                    gaps,
                    embedder=embedder,
                )
            except Exception as rank_err:
                logger.warning(f"Novelty ranking skipped: {rank_err}")

        # ── Step 7: Roadmap (always via LLM) ────────────────────
        record_job_event(
            job_id,
            "phase.completed",
            phase="proposal",
            status="running",
            duration_ms=int((time.monotonic() - _phase_started) * 1000),
            data={"recommendations": len(recommendations)},
        )
        _save_stage_artifact(
            job_id,
            "proposal",
            "result",
            payload={
                "recommendations": recommendations,
                "related_paper_refs": related_paper_refs,
            },
        )
        _set_analysis_job(job_id, progress=95, message="Creating roadmap...")
        _ensure_job_active(job_id)
        record_job_event(job_id, "phase.started", phase="roadmap", status="running")
        _phase_started = time.monotonic()

        roadmap_topic = topics[0] if topics else "research"
        roadmap_prompt = f"""Buat peta jalan penelitian terstruktur untuk: {roadmap_topic}
Gunakan Bahasa Indonesia.

Kembalikan sebagai JSON array fase (tanpa teks tambahan):
[
  {{"phase": "Jangka Pendek (1-3 bulan)", "items": ["tugas 1", "tugas 2"]}},
  {{"phase": "Jangka Menengah (3-6 bulan)", "items": ["tugas 1", "tugas 2"]}},
  {{"phase": "Jangka Panjang (6-12 bulan)", "items": ["tugas 1", "tugas 2"]}}
]

JSON:"""
        raw_roadmap = _traced_generate(
            glm, job_id, "roadmap", "Peta jalan penelitian",
            roadmap_prompt, max_tokens=500, format="json",
        ).strip()
        roadmap = _parse_roadmap_json(raw_roadmap)
        record_job_event(
            job_id,
            "phase.completed",
            phase="roadmap",
            status="running",
            duration_ms=int((time.monotonic() - _phase_started) * 1000),
            data={"phases": len(roadmap)},
        )
        _save_stage_artifact(job_id, "roadmap", "result", payload={"roadmap": roadmap})

        # ── Step 8: Proposal intro (1-sentence AI synthesis, decision-support) ──
        proposal_intro = ""
        try:
            if recommendations:
                top_gap_desc = gaps[0].get("description", "") if gaps else ""
                top_gap_type = gaps[0].get("type", "") if gaps else ""
                top_rec = recommendations[0]
                rec_title = top_rec.get("title", "") if isinstance(top_rec, dict) else str(top_rec)
                intro_prompt = (
                    f"Tulis SATU kalimat ringkas (maksimal 40 kata) dalam Bahasa Indonesia yang "
                    f"merangkum INDIKATOR usulan penelitian hasil sintesis dari {len(paper_contents)} jurnal. "
                    f"Indikator synthesis gap ({top_gap_type}): {top_gap_desc}. Arah usulan: {rec_title}. "
                    f"Posisikan sebagai indikator/peluang yang masih PERLU DIVALIDASI peneliti — "
                    f"gunakan kata seperti 'berpotensi', 'mengindikasikan', atau 'dapat dipertimbangkan', "
                    f"JANGAN menyatakannya sebagai temuan pasti. Tanpa awalan 'Berikut' atau label."
                )
                proposal_intro = _traced_generate(
                    glm, job_id, "proposal", "Kalimat pembuka usulan",
                    intro_prompt, max_tokens=120,
                ).strip()
        except Exception as intro_err:
            logger.warning(f"Proposal intro generation failed: {intro_err}")

        # ── Assemble final results ──────────────────────────────
        if not fact_table_stats:
            fact_table_stats = analysis_context.fact_table.get_statistics()

        # ── Compute evaluation metrics ────────────────────────
        eval_metrics = {}
        try:
            n_gaps = len(gaps)
            n_recs = len(recommendations)
            n_topics = len(topics)
            n_facts = fact_table_stats.get("total_facts", 0) if fact_table_stats else 0
            n_entities = fact_table_stats.get("total_entities", 0) if fact_table_stats else 0

            # Coverage: how many topics have at least one gap
            topic_coverage = min(n_gaps / max(n_topics, 1), 1.0)
            # Recommendation completeness: gaps addressed by recommendations
            rec_completeness = min(n_recs / max(n_gaps, 1), 1.0)
            # KG density: facts per entity
            kg_density = n_facts / max(n_entities, 1)
            # Pipeline completeness score
            pipeline_score = sum([
                0.2 if execution_mode == "langgraph" else 0.1,
                0.2 if n_facts > 0 else 0,
                0.2 if gap_indicators else 0,
                0.2 if rule_engine_report else 0,
                0.2 if n_recs > 0 else 0,
            ])

            eval_metrics = {
                "topic_coverage": round(topic_coverage, 3),
                "recommendation_completeness": round(rec_completeness, 3),
                "kg_density": round(kg_density, 3),
                "pipeline_score": round(pipeline_score, 3),
                "total_topics": n_topics,
                "total_gaps": n_gaps,
                "total_recommendations": n_recs,
                "total_facts": n_facts,
                "total_entities": n_entities,
            }
        except Exception as eval_err:
            logger.warning(f"Evaluation metrics computation failed: {eval_err}")

        _ensure_job_active(job_id)
        graph_snapshot = analysis_context.graph_snapshot()
        completed = complete_job(
            job_id,
            message="Analysis complete!",
            results={
                "topics": topics,
                "summary": summary,
                "gaps": gaps,
                "recommendations": recommendations,
                "roadmap": roadmap,
                "total_chunks": total_chunks,
                "files_processed": len(pdf_paths),
                "papers": [p["title"] for p in paper_contents],
                "papers_info": [
                    {
                        "title": p["title"],
                        "source": p["source"],
                        "year": p.get("year"),
                        "similarity_percent": p.get("similarity_percent"),
                        "already_indexed": p["already_indexed"],
                        "num_chunks": p.get("num_chunks"),
                        "sample_chunks": p.get("sample_chunks", []),
                    }
                    for p in paper_contents
                ],
                "new_papers": new_papers,
                "duplicate_papers": duplicate_papers,
                "paper_groups": paper_groups,
                "paper_similarity": paper_similarity,
                "paper_weaknesses": paper_weaknesses,
                "proposal_intro": proposal_intro,
                "related_paper_refs": related_paper_refs,
                "execution_mode": execution_mode,
                "gap_indicators": gap_indicators,
                "rule_engine_report": rule_engine_report,
                "fact_table_stats": fact_table_stats,
                "sample_facts": sample_facts,
                "llm_info": {
                    "model": getattr(glm, "active_model_name", None)
                    or getattr(getattr(glm, "config", None), "model_name", "")
                    or ""
                },
                "skills_used": sorted(_JOB_SKILLS.get(job_id, set())),
                "reasoning_trace": reasoning_trace,
                "eval_metrics": eval_metrics,
            },
            graph_snapshot=graph_snapshot,
        )
        if completed is None:
            # cancel landed after the last cooperative check above
            raise JobCancelled("Analisis dibatalkan oleh pengguna")
        record_job_event(
            job_id,
            "job.completed",
            status="completed",
            data={
                "files_processed": len(pdf_paths),
                "chunks": total_chunks,
                "indicators": len(gaps),
                "facts": fact_table_stats.get("total_facts", 0),
            },
        )

    except JobCancelled:
        # no usable result is kept, so the bar must not stay at e.g. 95%
        _set_analysis_job(
            job_id,
            status="cancelled",
            progress=0,
            message="Analisis dibatalkan oleh pengguna",
            error=None,
        )
        record_job_event(job_id, "job.cancelled", status="cancelled")
    except Exception as e:
        logger.error(f"Auto-analysis failed for job {job_id}: {e}")
        _set_analysis_job(
            job_id,
            status="failed",
            error="Analisis gagal. Silakan coba ulang atau periksa log server.",
            message="Analisis gagal. Silakan coba ulang.",
        )
        record_job_event(job_id, "job.failed", status="failed", data={"error_type": type(e).__name__})
    finally:
        # Inputs stay on disk until retention cleanup so a retry can rebuild a
        # clean scoped corpus after a restart.
        _JOB_SKILLS.pop(job_id, None)
        release_analysis_context(job_id)
