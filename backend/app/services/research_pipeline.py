"""Jalankan pipeline penelitian (TAHAP 1-3 + rekomendasi) sebagai job terpantau.

Keempat tahap sebelumnya hanya bisa lewat CLI (``scripts/run_pipeline.py``,
``scripts/mine_gaps.py``, ``scripts/check_novelty.py``,
``experiments/recommend_topics.py``) dan tidak pernah menulis ke ``job_store``,
sehingga UI tidak punya apa pun untuk ditampilkan. Modul ini memanggil komponen
inti yang sama, tetapi mencatat event dan artefak per tahap.

Tahap ekstraksi sengaja memanggil komponennya langsung alih-alih ``mine()`` di
``scripts/``: ``mine()`` tidak mengekspos ``generate_fn``, padahal itu satu-
satunya cara merekam prompt dan balasan LLM. Arah impor juga tetap benar,
``app`` tidak boleh bergantung pada ``scripts``.
"""

from __future__ import annotations

import hashlib
import inspect
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from loguru import logger

from ..core.gap_mining.candidates import matched_phrases, select_candidates, with_context
from ..core.gap_mining.extractor import extract_gaps_from_candidate
from ..core.gap_mining.novelty import annotate_gaps
from ..core.gap_mining.verify import verify_gaps
from ..core.pipeline.corpus_relevance import build_probe, check_corpus_relevance
from ..core.pipeline.io import read_jsonl, source_name, write_chunks_jsonl, write_jsonl
from ..core.pipeline.pipeline import process_pdf
from ..core.pipeline.token_chunker import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_OVERLAP_RATIO,
    DEFAULT_TARGET_TOKENS,
    chunk_document,
)
from ..core.recommendation.novelty import rank_proposals
from ..core.recommendation.themes import build_themes
from ..utils.config_loader import get_config
from ..utils.job_store import (
    add_stage_artifact,
    get_job,
    is_cancel_requested,
    record_job_event,
    update_job,
)
from . import copilot_client

# Nama pipeline di field ``job["pipeline"]``; antrean memakainya untuk memilih
# handler (lihat ``AnalysisJobQueue.register``).
PIPELINE_NAME = "research"

# Urutan tahap penelitian; dipakai UI untuk menggambar timeline.
RESEARCH_STAGES = [
    ("chunking", "📄", "Ekstraksi & Chunking",
     "PDF dibersihkan, seksi dikenali, lalu dipotong per kalimat dengan batas token"),
    ("gap_mining", "🕳️", "Penambangan Gap",
     "Kandidat per seksi disaring, LLM mengekstrak gap, tiap kalimat diverifikasi verbatim"),
    ("novelty", "🔭", "Verifikasi Kebaruan",
     "Tiap gap dicek ke literatur 2024+ lewat OpenAlex: open / partially / addressed"),
    ("recommendation", "🎯", "Rekomendasi Topik",
     "Gap open diperingkat rumus project, lalu dikelompokkan jadi tema lintas-jurnal"),
]

# Satu run bisa ratusan panggilan LLM; menyimpan semuanya membanjiri basis data.
DEFAULT_LLM_TRACE_LIMIT = 15
# Panggilan LLM didominasi waktu tunggu jaringan, jadi diparalelkan seperti CLI.
# Menaikkan lebih jauh sia-sia: copilotd sendiri melayani max_concurrency 2, dan
# 12 kandidat terukur 135,4 dtk (1 worker) vs 47,7 dtk (4 worker).
DEFAULT_EXTRACT_WORKERS = 4
SAMPLE_ROWS = 8


@dataclass
class StageOutcome:
    """Hasil satu tahap: parameter, angka, contoh data, dan berkas keluaran."""

    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    samples: List[Dict[str, Any]] = field(default_factory=list)
    outputs: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


def _dedup_gaps(gaps: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for gap in gaps:
        key = (gap.get("source"), (gap.get("gap_statement") or "").strip().lower())
        digest = hashlib.sha1(str(key).encode()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        out.append(gap)
    return out


def _median(values: Sequence[int]) -> int:
    ordered = sorted(values)
    return ordered[len(ordered) // 2] if ordered else 0


class ResearchCancelled(Exception):
    """Dilempar di antara tahap/kandidat setelah pengguna meminta pembatalan."""


def _ensure_active(job_id: str) -> None:
    if is_cancel_requested(job_id):
        raise ResearchCancelled("Pipeline penelitian dibatalkan oleh pengguna")


class _StageRecorder:
    """Menulis event mulai/selesai plus artefak hasil satu tahap."""

    def __init__(self, job_id: str, phase: str):
        self.job_id = job_id
        self.phase = phase
        self._t0 = 0.0

    def __enter__(self) -> "_StageRecorder":
        self._t0 = time.monotonic()
        record_job_event(self.job_id, "phase.started", phase=self.phase, status="running")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if isinstance(exc, ResearchCancelled):
            record_job_event(
                self.job_id, "phase.cancelled", phase=self.phase, status="cancelled",
                duration_ms=self._elapsed_ms(),
            )
        elif exc is not None:
            record_job_event(
                self.job_id, "phase.failed", phase=self.phase, status="failed",
                duration_ms=self._elapsed_ms(), data={"error": str(exc)[:500]},
            )
        return False

    def _elapsed_ms(self) -> int:
        return int((time.monotonic() - self._t0) * 1000)

    def finish(self, outcome: StageOutcome) -> None:
        duration_ms = self._elapsed_ms()
        add_stage_artifact(self.job_id, self.phase, "result", self.phase, {
            "params": outcome.params,
            "metrics": outcome.metrics,
            "samples": outcome.samples,
            "outputs": outcome.outputs,
            "notes": outcome.notes,
            "duration_ms": duration_ms,
        })
        record_job_event(
            self.job_id, "phase.completed", phase=self.phase, status="running",
            duration_ms=duration_ms, data=dict(outcome.metrics),
        )


def _progress(job_id: str, pct: float, message: str) -> None:
    update_job(job_id, progress=round(pct, 1), message=message)


# ── TAHAP 1 ────────────────────────────────────────────────────────────────

def stage_chunking(
    job_id: str,
    pdf_paths: Sequence[Path],
    out_path: Path,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_ratio: float = DEFAULT_OVERLAP_RATIO,
    embedder=None,
) -> StageOutcome:
    results = []
    total = len(pdf_paths)
    for i, pdf in enumerate(pdf_paths, 1):
        source = source_name(pdf)
        record_job_event(job_id, "file.started", phase="chunking",
                         data={"file": source, "index": i, "of": total})
        try:
            result = process_pdf(str(pdf), source=source, target_tokens=target_tokens,
                                 max_tokens=max_tokens, overlap_ratio=overlap_ratio)
        except Exception as exc:
            logger.error(f"chunking gagal pada {source}: {exc}")
            record_job_event(job_id, "file.failed", phase="chunking",
                             data={"file": source, "error": str(exc)[:300]})
            continue
        results.append(result)
        add_stage_artifact(job_id, "chunking", "extraction", source, {
            "file": source,
            "title": result.meta.paper_title,
            "year": result.meta.year,
            "language": result.meta.language,
            "extraction_method": result.extraction_method,
            "extraction_quality": result.meta.extraction_quality,
            "grobid_used": result.grobid_used,
            "pages": result.num_pages,
            "chunks": len(result.chunks),
            "sample_chunks": [
                {"chunk_index": c.chunk_index, "section": c.section_normalized,
                 "tokens": c.token_count, "text": c.text[:400]}
                for c in result.chunks[:3]
            ],
        })
        record_job_event(job_id, "file.completed", phase="chunking",
                         data={"file": source, "index": i, "of": total,
                               "chunks": len(result.chunks)})
        _progress(job_id, 5 + 25 * i / max(1, total), f"Chunking {i}/{total} — {source}")

    summary = write_chunks_jsonl(str(out_path), results, job_id=job_id)
    chunks = [c for r in results for c in r.chunks]
    tokens = [c.token_count for c in chunks]
    sections: Dict[str, int] = defaultdict(int)
    for c in chunks:
        sections[c.section_normalized] += 1

    outcome = StageOutcome(
        params={"target_tokens": target_tokens, "max_tokens": max_tokens,
                "overlap_ratio": overlap_ratio, "pdf_masuk": total},
        metrics={
            "jurnal": summary.get("jurnal", len(results)),
            "chunk": summary.get("chunk", len(chunks)),
            "pdf_gagal": total - len(results),
            "token_total": sum(tokens),
            "token_median": _median(tokens),
            "chunk_kecil_pct": round(100 * sum(1 for t in tokens if t < 150) / max(1, len(tokens)), 1),
            "referensi_ditandai": sum(1 for c in chunks if c.is_reference),
            "section_other_pct": round(100 * sections.get("other", 0) / max(1, len(chunks)), 1),
            "distribusi_seksi": dict(sorted(sections.items(), key=lambda kv: -kv[1])),
        },
        samples=[
            {"source": c.source, "chunk_index": c.chunk_index,
             "section": c.section_normalized, "tokens": c.token_count,
             "text": c.text[:300]}
            for c in chunks[:SAMPLE_ROWS]
        ],
        outputs={"chunks_jsonl": str(out_path)},
    )

    if embedder is not None and len(results) > 1:
        probes = {
            r.meta.source: build_probe(
                r.meta.paper_title,
                [{"text": c.text, "is_reference": c.is_reference,
                  "chunk_index": c.chunk_index} for c in r.chunks])
            for r in results
        }
        reports = check_corpus_relevance(probes, embedder=embedder)
        flagged = [rep.to_dict() for rep in reports if rep.flagged]
        outcome.metrics["jurnal_ditandai_tak_sedomain"] = len(flagged)
        if flagged:
            outcome.notes.append(
                f"{len(flagged)} jurnal tampak di luar bidang batch ini — peringatan, "
                "bukan penolakan; hanya andal untuk penyusup minoritas.")
            outcome.samples.extend(flagged)
    return outcome


# ── TAHAP 2 ────────────────────────────────────────────────────────────────

def stage_gap_mining(
    job_id: str,
    chunks_path: Path,
    out_path: Path,
    limit: int = 0,
    llm_trace_limit: int = DEFAULT_LLM_TRACE_LIMIT,
    workers: int = DEFAULT_EXTRACT_WORKERS,
) -> StageOutcome:
    chunks = [c for c in read_jsonl(str(chunks_path)) if c.get("record") == "chunk"]
    by_source: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in chunks:
        by_source[c.get("source")].append(c)

    candidates = select_candidates(chunks)
    if limit:
        candidates = candidates[:limit]
    regex_baseline = sum(
        1 for c in chunks
        if not c.get("is_reference") and matched_phrases(c.get("text", "")))

    traced = {"n": 0}
    trace_lock = threading.Lock()

    def _generate(prompt: str, system: str) -> Optional[str]:
        result = copilot_client.generate(prompt, system=system, json_mode=True, temperature=0)
        text = result[0] if result else None
        with trace_lock:
            keep = traced["n"] < llm_trace_limit
            if keep:
                traced["n"] += 1
                seq = traced["n"]
        if keep:
            add_stage_artifact(job_id, "gap_mining", "llm", f"kandidat {seq}", {
                "prompt": prompt,
                "response": text or "",
                "model": result[1] if result else "",
                "system": system,
            })
        return text

    def _work(cand: Dict[str, Any]) -> List[Dict[str, Any]]:
        return extract_gaps_from_candidate(
            cand, with_context(cand, by_source), generate_fn=_generate)

    raw_gaps: List[Dict[str, Any]] = []
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_work, c) for c in candidates]
        try:
            for fut in as_completed(futures):
                done += 1
                try:
                    raw_gaps.extend(fut.result())
                except Exception as exc:
                    logger.warning(f"kandidat gagal: {exc}")
                if done % 10 == 0 or done == len(candidates):
                    _ensure_active(job_id)
                    _progress(job_id, 30 + 30 * done / max(1, len(candidates)),
                              f"Ekstraksi gap {done}/{len(candidates)} kandidat")
        except ResearchCancelled:
            # Kandidat yang belum mulai dibuang; yang sedang berjalan dibiarkan
            # selesai oleh ``with`` agar tidak ada thread yatim.
            for fut in futures:
                fut.cancel()
            raise

    raw_path = str(out_path) + ".raw.jsonl"
    write_jsonl(raw_path, raw_gaps)
    grounded = verify_gaps(raw_gaps, by_source)
    gaps = _dedup_gaps(grounded)
    journals = len({g["source"] for g in gaps})

    meta = {
        "record": "meta", "job_id": job_id,
        "diekspor_pada": datetime.now().isoformat(timespec="seconds"),
        "jumlah_gap": len(gaps), "jumlah_jurnal_bergap": journals,
        "jumlah_kandidat": len(candidates),
        "catatan": "Gap terstruktur; gap_statement diverifikasi verbatim di chunk sumber.",
    }
    write_jsonl(str(out_path), [meta] + gaps)

    return StageOutcome(
        params={"limit": limit or "semua", "llm_trace_limit": llm_trace_limit,
                "workers": workers, "temperature": 0,
                "seksi_sasaran": "conclusion + discussion",
                "aturan_cadangan": "abstract, 2 chunk introduction, 2 chunk terakhir"},
        metrics={
            "chunk_masuk": len(chunks),
            "kandidat": len(candidates),
            "baseline_regex_saja": regex_baseline,
            "gap_mentah": len(raw_gaps),
            "lolos_verifikasi_verbatim": len(grounded),
            "gugur_di_verifikasi": len(raw_gaps) - len(grounded),
            "gap_final_setelah_dedup": len(gaps),
            "jurnal_bergap": journals,
        },
        samples=[
            {"source": g.get("source"), "gap_type": g.get("gap_type"),
             "topic": g.get("topic"), "grounding_score": g.get("grounding_score"),
             "gap_statement": (g.get("gap_statement") or "")[:300],
             "gap_paraphrase": (g.get("gap_paraphrase") or "")[:200]}
            for g in gaps[:SAMPLE_ROWS]
        ],
        outputs={"gaps_jsonl": str(out_path), "gaps_raw_jsonl": raw_path},
        notes=["Tiap gap_statement wajib muncul verbatim di chunk sumbernya; "
               "yang di bawah ambang grounding dibuang sebagai dugaan halusinasi.",
               "Cakupan gap tidak reproducible penuh: dua run pada chunk identik "
               "hanya ~75% tumpang tindih."],
    )


# ── TAHAP 3 ────────────────────────────────────────────────────────────────

def stage_novelty(
    job_id: str,
    gaps_path: Path,
    out_path: Path,
    from_date: str = "2024-01-01",
    min_interval: float = 1.0,
    max_retries: int = 4,
) -> StageOutcome:
    rows = list(read_jsonl(str(gaps_path)))
    meta = next((r for r in rows if r.get("record") == "meta"), {})
    gaps = [r for r in rows if "gap_statement" in r]

    _progress(job_id, 62, f"Cek kebaruan {len(gaps)} gap ke OpenAlex")
    enriched = annotate_gaps(gaps, from_date=from_date,
                             min_interval=min_interval, max_retries=max_retries)

    counts: Dict[str, int] = defaultdict(int)
    for g in enriched:
        counts[g.get("novelty_status", "?")] += 1
    with_matches = sum(1 for g in enriched if g.get("related_recent_papers"))

    out_meta = dict(meta)
    out_meta.update({
        "novelty_checked_at": datetime.now().isoformat(timespec="seconds"),
        "novelty_from_date": from_date,
        "novelty_status_counts": dict(counts),
    })
    write_jsonl(str(out_path), [out_meta] + enriched)

    return StageOutcome(
        params={"from_date": from_date, "min_interval": min_interval,
                "max_retries": max_retries, "sumber": "OpenAlex"},
        metrics={
            "gap_dicek": len(enriched),
            "open": counts.get("open", 0),
            "partially_addressed": counts.get("partially_addressed", 0),
            "addressed": counts.get("addressed", 0),
            "punya_match_literatur": with_matches,
            "tanpa_match_literatur": len(enriched) - with_matches,
        },
        samples=[
            {"source": g.get("source"), "novelty_status": g.get("novelty_status"),
             "novelty_query": g.get("novelty_query"),
             "gap_statement": (g.get("gap_statement") or "")[:200],
             "literatur_2024plus": [p.get("title", "")[:80]
                                    for p in (g.get("related_recent_papers") or [])[:2]]}
            for g in enriched[:SAMPLE_ROWS]
        ],
        outputs={"gaps_novelty_jsonl": str(out_path)},
        notes=["Saat OpenAlex tak terjangkau atau kena throttle, gap tetap "
               "dihitung 'open' secara konservatif — cakupan 100% tapi bisa "
               "terlalu optimistis."],
    )


# ── TAHAP 4 ────────────────────────────────────────────────────────────────

def stage_recommendation(
    job_id: str,
    gaps_novelty_path: Path,
    chunks_path: Path,
    out_path: Path,
    embedder=None,
    top: int = 15,
) -> StageOutcome:
    gaps = [g for g in read_jsonl(str(gaps_novelty_path)) if "gap_statement" in g]
    open_gaps = [g for g in gaps if g.get("novelty_status") == "open"]
    chunks = [c for c in read_jsonl(str(chunks_path)) if c.get("record") == "chunk"]

    # Bentuk korpus & confidence harus sama persis dengan experiments/recommend_topics.py,
    # kalau tidak skornya tidak sebanding dengan hasil CLI.
    by_source: Dict[str, List[str]] = defaultdict(list)
    title_by_source: Dict[str, str] = {}
    for c in chunks:
        src = c.get("source")
        by_source[src].append(c.get("text") or "")
        title_by_source.setdefault(src, c.get("paper_title") or src)
    corpus = [{"source": src, "title": title_by_source.get(src, src),
               "content": " ".join(texts)[:1500]}
              for src, texts in by_source.items()]
    gap_conf = [{"type": g.get("gap_type"), "confidence": g.get("grounding_score") or 0.0}
                for g in open_gaps]

    proposals = []
    for g in open_gaps:
        para = (g.get("gap_paraphrase") or "").strip()
        stmt = (g.get("gap_statement") or "").strip()
        if not (para or stmt):
            continue
        proposals.append({
            "title": para or stmt[:120], "description": stmt, "how": stmt,
            "gap_type": g.get("gap_type"), "topic": g.get("topic"),
            "source": g.get("source"), "year": g.get("year"),
            "grounding_score": g.get("grounding_score"),
        })

    _progress(job_id, 85, f"Memeringkat {len(proposals)} proposal")
    ranked = rank_proposals(proposals, corpus, gap_conf, embedder=embedder)
    themes = build_themes(ranked, embedder=embedder)
    cross = [t for t in themes if t.journal_support >= 2]
    singletons = sum(1 for t in themes if len(t.members) == 1)

    lines = [
        "# Rekomendasi Topik Penelitian", "",
        f"Basis: {len(gaps)} gap terverifikasi, {len(open_gaps)} open, "
        f"{len(proposals)} proposal dinilai.", "",
        "## Peringkat Proposal", "",
    ]
    for i, p in enumerate(ranked[:top], 1):
        nov = p.get("novelty", {})
        lines.append(f"{i}. **[{nov.get('priority_score')}]** {p.get('title')}")
        lines.append(f"   - topik={p.get('topic')} · novelty={nov.get('novelty')} "
                     f"({nov.get('band')}) · sumber: {p.get('source')}")
    lines += ["", "## Tema Lintas-Jurnal", ""]
    for i, t in enumerate(cross, 1):
        lines.append(f"{i}. **[{t.journal_support} jurnal · {len(t.members)} gap]** {t.label}")
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")

    # Markdown hanya memuat top-N; JSONL menyimpan seluruh proposal agar UI bisa
    # menelusuri semuanya beserta tema induknya.
    theme_of = {id(p): t for t in themes for p in t.members}
    proposals_path = Path(out_path).with_suffix(".jsonl")
    themes_path = Path(out_path).with_name(f"{Path(out_path).stem}_tema.jsonl")
    proposal_records = []
    for i, p in enumerate(ranked, 1):
        nov = p.get("novelty") or {}
        theme = theme_of.get(id(p))
        proposal_records.append({
            "rank": i,
            "title": p.get("title"),
            "description": p.get("description"),
            "topic": p.get("topic"),
            "gap_type": p.get("gap_type"),
            "source": p.get("source"),
            "year": p.get("year"),
            "grounding_score": p.get("grounding_score"),
            "priority_score": nov.get("priority_score"),
            "novelty": nov.get("novelty"),
            "band": nov.get("band"),
            "actionability": nov.get("actionability"),
            "theme_id": theme.theme_id if theme else None,
            "theme_label": theme.label if theme else None,
            "theme_journal_support": theme.journal_support if theme else None,
            "theme_size": len(theme.members) if theme else None,
        })
    write_jsonl(str(proposals_path), proposal_records)
    write_jsonl(str(themes_path), [t.to_dict() for t in themes])

    return StageOutcome(
        params={"rumus": "0.5*gap_confidence + 0.3*novelty + 0.2*actionability",
                "filter": "novelty_status == open",
                "pemecah_seri": "jarak novelty ke tengah sweet spot",
                "embedder": "multilingual-MiniLM" if embedder is not None else "leksikal",
                "top": top},
        metrics={
            "gap_open": len(open_gaps),
            "proposal_dinilai": len(proposals),
            "tema": len(themes),
            "tema_lintas_jurnal": len(cross),
            "tema_satu_gap": singletons,
            "tema_satu_gap_pct": round(100 * singletons / max(1, len(themes)), 1),
            "skor_tertinggi": ranked[0]["novelty"]["priority_score"] if ranked else 0,
        },
        samples=[
            {"rank": i, "title": p.get("title"), "topic": p.get("topic"),
             "priority_score": p["novelty"]["priority_score"],
             "novelty": p["novelty"]["novelty"], "band": p["novelty"]["band"],
             "source": p.get("source")}
            for i, p in enumerate(ranked[:SAMPLE_ROWS], 1)
        ],
        outputs={"rekomendasi_md": str(out_path),
                 "proposals_jsonl": str(proposals_path),
                 "themes_jsonl": str(themes_path)},
        notes=["journal_support pada tema besar adalah batas atas, bukan bukti "
               "bahwa N jurnal menyatakan gap yang sama (chaining single-linkage)."],
    )


# ── Orkestrator ────────────────────────────────────────────────────────────

def run_research_pipeline(
    job_id: str,
    pdf_paths: Sequence[Path],
    out_dir: Path,
    embedder=None,
    limit: int = 0,
    from_date: str = "2024-01-01",
) -> Dict[str, Any]:
    """Jalankan keempat tahap berurutan, merekam progres dan hasil detailnya."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    short = job_id[:8]
    paths = {
        "chunks": out_dir / f"chunks_{short}.jsonl",
        "gaps": out_dir / f"gaps_{short}.jsonl",
        "novelty": out_dir / f"gaps_{short}_novelty.jsonl",
        "rekomendasi": out_dir / f"rekomendasi_{short}.md",
    }
    stages: List[tuple[str, Callable[[], StageOutcome]]] = [
        ("chunking", lambda: stage_chunking(
            job_id, pdf_paths, paths["chunks"], embedder=embedder)),
        ("gap_mining", lambda: stage_gap_mining(
            job_id, paths["chunks"], paths["gaps"], limit=limit)),
        ("novelty", lambda: stage_novelty(
            job_id, paths["gaps"], paths["novelty"], from_date=from_date)),
        ("recommendation", lambda: stage_recommendation(
            job_id, paths["novelty"], paths["chunks"], paths["rekomendasi"],
            embedder=embedder)),
    ]

    update_job(job_id, status="running", progress=1.0,
               message="Memulai pipeline penelitian")
    summary: Dict[str, Any] = {}
    phase = "persiapan"
    try:
        for phase, run in stages:
            _ensure_active(job_id)
            with _StageRecorder(job_id, phase) as rec:
                outcome = run()
                rec.finish(outcome)
            summary[phase] = outcome.metrics
    except ResearchCancelled:
        update_job(job_id, status="cancelled",
                   message=f"Dibatalkan oleh pengguna saat tahap {phase}")
        raise
    except Exception as exc:
        logger.exception(f"tahap {phase} gagal")
        update_job(job_id, status="failed", error=f"{phase}: {exc}",
                   message=f"Gagal di tahap {phase}")
        raise

    update_job(job_id, status="completed", progress=100.0,
               message="Pipeline penelitian selesai", completed_at=time.time())
    return {"job_id": job_id, "stages": summary,
            "outputs": {k: str(v) for k, v in paths.items()}}


def _shared_embedder():
    """Embedder milik vector store, agar model tidak dimuat dua kali."""
    try:
        from ..api.dependencies import get_vector_store
        return getattr(get_vector_store(), "embedding_model", None)
    except Exception as exc:
        logger.warning(f"Embedder tidak tersedia, novelty memakai leksikal: {exc}")
        return None


def run_research_job(job_id: str) -> None:
    """Handler antrean: jalankan pipeline penelitian dari payload job tersimpan.

    Dipanggil worker ``AnalysisJobQueue`` (thread pool), bukan event loop.
    Payload hanya berisi path lokal — ``pdf_paths`` dan ``output_dir`` — yang
    ditulis ``/api/research/start``; job yang diretry atau dipulihkan setelah
    restart memakai payload yang sama. Kegagalan sudah dicatat oleh
    ``run_research_pipeline`` (status, error, event), jadi tidak dilempar
    ulang: handler generik antrean akan menimpanya dengan pesan umum.
    Pembatalan diselesaikan di sini pula agar antrean tidak menjadwalkan retry.
    """
    job = get_job(job_id)
    if job is None:
        raise RuntimeError(f"Job penelitian tidak ditemukan: {job_id}")
    payload = job.get("payload") or {}
    pdf_paths = [Path(p) for p in payload.get("pdf_paths") or []]
    if not pdf_paths or any(not p.exists() for p in pdf_paths):
        raise FileNotFoundError("PDF masukan job penelitian ini sudah tidak tersedia")
    out_dir = payload.get("output_dir") or str(
        Path(get_config().data.processed_path) / "research" / job_id)
    try:
        run_research_pipeline(job_id, pdf_paths, Path(out_dir), embedder=_shared_embedder())
    except ResearchCancelled:
        logger.info(f"Pipeline penelitian {job_id} dibatalkan")
        record_job_event(job_id, "job.cancelled", status="cancelled")
    except Exception as exc:
        logger.error(f"Pipeline penelitian {job_id} gagal: {exc}")
        if (get_job(job_id) or {}).get("status") != "failed":
            update_job(job_id, status="failed", error=str(exc)[:500],
                       message="Pipeline penelitian gagal")


# ── Kode sumber tiap tahap ─────────────────────────────────────────────────

# Fungsi nyata yang dieksekusi tiap tahap, urut dari orkestrator ke komponen
# inti. Diambil lewat ``inspect`` supaya yang ditampilkan UI selalu kode yang
# benar-benar berjalan; salinan manual pasti basi begitu implementasinya berubah.
STAGE_SOURCE_FUNCS: Dict[str, List[Callable]] = {
    "chunking": [stage_chunking, process_pdf, chunk_document],
    "gap_mining": [stage_gap_mining, select_candidates,
                   extract_gaps_from_candidate, verify_gaps],
    "novelty": [stage_novelty, annotate_gaps],
    "recommendation": [stage_recommendation, rank_proposals, build_themes],
}

_REPO_ROOT = Path(__file__).resolve().parents[3]


def stage_source(stage_key: str) -> List[Dict[str, Any]]:
    """Kode sumber fungsi-fungsi yang dijalankan satu tahap."""
    entries: List[Dict[str, Any]] = []
    for fn in STAGE_SOURCE_FUNCS.get(stage_key, []):
        try:
            lines, lineno = inspect.getsourcelines(fn)
            path = Path(inspect.getsourcefile(fn) or "")
        except (OSError, TypeError) as exc:
            logger.warning(f"kode sumber {getattr(fn, '__name__', fn)} tak terbaca: {exc}")
            continue
        try:
            rel = str(path.relative_to(_REPO_ROOT))
        except ValueError:
            rel = str(path)
        entries.append({
            "name": fn.__name__,
            "module": fn.__module__,
            "file": rel,
            "line_start": lineno,
            "line_end": lineno + len(lines) - 1,
            "doc": inspect.getdoc(fn) or "",
            "source": "".join(lines),
        })
    return entries
