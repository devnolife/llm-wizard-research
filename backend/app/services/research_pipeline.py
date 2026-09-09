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
import json
import re
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from loguru import logger

from ..core.gap_detection.quote_grounding import QUOTE_MATCH_THRESHOLD
from ..core.gap_mining.candidates import matched_phrases, select_candidates, with_context
from ..core.gap_mining.extractor import extract_gaps_from_candidate
from ..core.gap_mining.novelty import (DISABLED_REASON, LIMIT_REASON, STRONG_MATCH_THRESHOLD,
                                       annotate_gaps, novelty_disabled)
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
from ..core.recommendation.novelty import (
    NOVELTY_SWEET_SPOT,
    W_ACTIONABILITY,
    W_GAP,
    W_NOVELTY,
    rank_proposals,
)
from ..core.recommendation.themes import THEME_SIMILARITY_THRESHOLD, build_themes
from ..utils.config_loader import get_config
from ..utils.job_store import (
    add_stage_artifact,
    complete_job,
    get_job,
    is_cancel_requested,
    record_job_event,
    update_job,
)
from . import copilot_client

# Nama pipeline di field ``job["pipeline"]``; antrean memakainya untuk memilih
# handler (lihat ``AnalysisJobQueue.register``).
PIPELINE_NAME = "research"

# Satu run bisa ratusan panggilan LLM; menyimpan semuanya membanjiri basis data.
DEFAULT_LLM_TRACE_LIMIT = 15
# Panggilan LLM didominasi waktu tunggu jaringan, jadi diparalelkan seperti CLI.
# Menaikkan lebih jauh sia-sia: klien Copilot membatasi 2 permintaan serentak, dan
# 12 kandidat terukur 135,4 dtk (1 worker) vs 47,7 dtk (4 worker).
DEFAULT_EXTRACT_WORKERS = 4
SAMPLE_ROWS = 8
# Batas atas run gap mining per job: tiap run = satu lintasan LLM penuh atas
# kandidat yang sama, jadi biayanya linear.
MAX_GAP_RUNS = 5
# Butir teratas yang dinarasikan LLM (judul, latar belakang, alasan, metode) pada
# tahap rekomendasi: satu panggilan per job. Tema lintas-jurnal dulu, lalu proposal
# berperingkat; tanpa batas per jurnal (keputusan pengguna 9 Sep 2026).
NARRATION_TOP = 8

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


def _sub(key: str, label: str, teknis: str, penjelasan: str, *,
         masuk: Optional[str] = None, keluar: Optional[str] = None,
         dibuang: Optional[str] = None, contoh: Optional[str] = None,
         dalam: Optional[str] = None, jenis: str = "saring") -> Dict[str, Any]:
    return {"key": key, "label": label, "label_teknis": teknis, "penjelasan": penjelasan,
            "in_metric": masuk, "out_metric": keluar, "drop_metric": dibuang,
            "sample_key": contoh, "inside": dalam, "jenis": jenis}


# Peta proses tiap tahap: sumber kebenaran tunggal untuk UI. Kunci ``in/out/
# drop_metric`` harus ada di ``StageOutcome.metrics`` tahap itu (dijaga tes),
# ``sample_key`` merujuk ``substep_samples``. Event ``substep.*`` memakai ``key``
# yang sama sehingga UI bisa menandai sub-langkah mana yang sedang berjalan.
#
# ``inside`` menandai sub-langkah yang terjadi DI DALAM induknya per berkas/per
# gap (mis. pengenalan seksi di dalam process_pdf) sehingga tidak punya event
# sendiri; UI menampilkannya bersarang dan mewarisi status induk.
#
# ``jenis``: "saring" = keluar adalah yang lolos (corong masuk → keluar);
# "periksa" = tidak ada yang dibuang, keluar adalah jumlah yang DITANDAI.
SUBSTEPS: Dict[str, List[Dict[str, Any]]] = {
    "chunking": [
        _sub("proses_pdf", "Memproses tiap PDF satu per satu",
             "process_pdf per berkas; event file.started/completed per PDF",
             "Setiap PDF dibaca, bagian-bagiannya dikenali, lalu dipotong menjadi "
             "chunk. Tiga hal di bawah ini terjadi untuk tiap berkas.",
             masuk="pdf_masuk", keluar="jurnal", dibuang="pdf_gagal", contoh="pdf_gagal"),
        _sub("baca_teks", "Membaca teks dari PDF",
             "PyMuPDF/GROBID; OCR (ocrd) bila kualitas ekstraksi 'poor'",
             "Teks diambil dari lapisan teks PDF. Bila rusak atau hasil scan, halaman "
             "dikirim ke layanan OCR.",
             dalam="proses_pdf"),
        _sub("kenali_seksi", "Mengenali bagian-bagian jurnal",
             "section_normalizer \u2192 abstract/introduction/methods/results/discussion/"
             "conclusion/references/other",
             "Judul bagian dikenali agar sistem tahu mana abstrak, metode, hasil, "
             "diskusi, kesimpulan, dan daftar pustaka.",
             keluar="distribusi_seksi", dalam="proses_pdf"),
        _sub("potong_chunk", "Memotong teks jadi potongan (chunk)",
             f"chunk_document: per kalimat, target {DEFAULT_TARGET_TOKENS} token, maks "
             f"{DEFAULT_MAX_TOKENS}, overlap {DEFAULT_OVERLAP_RATIO:.1%}",
             "Teks dipotong per kalimat menjadi potongan berukuran sedang yang "
             "sedikit bertumpang tindih, supaya kalimat di batas tidak terputus.",
             keluar="chunk", contoh="chunk_kecil", dalam="proses_pdf"),
        _sub("cek_koherensi", "Mengecek jurnal yang tampak di luar bidang",
             "check_corpus_relevance: cosine ke centroid korpus, ambang 0.50",
             "Tiap jurnal dibandingkan dengan yang lain; yang jauh berbeda "
             "ditandai sebagai peringatan, bukan ditolak.",
             masuk="jurnal", keluar="jurnal_ditandai_tak_sedomain", jenis="periksa"),
    ],
    "gap_mining": [
        _sub("pilih_kandidat", "Memilih bagian teks yang mungkin memuat gap",
             "select_candidates: seksi conclusion/discussion + pola kata "
             "(matched_phrases) + abstrak, 2 chunk intro, 2 chunk terakhir",
             "Tidak semua potongan dibaca LLM. Yang dipilih adalah kesimpulan, "
             "diskusi, dan potongan yang memuat kata-kata seperti 'limitation', "
             "'future work', 'belum', 'keterbatasan'.",
             masuk="chunk_masuk", keluar="kandidat"),
        _sub("ekstrak_llm", "LLM menyalin kalimat gap apa adanya",
             f"extract_gaps_from_candidate: JSON mode, temperature tidak dapat diatur "
             f"(Copilot), {DEFAULT_EXTRACT_WORKERS} worker paralel",
             "Untuk tiap kandidat, LLM diminta menyalin kalimat yang menyatakan "
             "keterbatasan atau saran penelitian lanjutan — persis seperti tertulis, "
             "tanpa mengubah kata.",
             masuk="kandidat", keluar="gap_mentah"),
        _sub("verifikasi_verbatim", "Memastikan kalimat benar-benar ada di jurnal",
             f"verify_gaps: fuzzy_contains ke semua chunk sumber, ambang "
             f"{QUOTE_MATCH_THRESHOLD}",
             "Setiap kalimat yang dikembalikan LLM dicocokkan kembali ke teks asli "
             "jurnal. Yang tidak ditemukan dibuang sebagai dugaan halusinasi.",
             masuk="gap_mentah", keluar="lolos_verifikasi_verbatim",
             dibuang="gugur_di_verifikasi", contoh="verifikasi_gugur"),
        _sub("dedup", "Menghitung kalimat yang sama hanya sekali",
             "_split_duplicates: kunci (source, gap_statement.lower())",
             "Karena kandidat bertumpang tindih, kalimat yang sama bisa muncul dua "
             "kali dari satu jurnal. Duplikat dibuang.",
             masuk="lolos_verifikasi_verbatim", keluar="gap_final_setelah_dedup",
             dibuang="duplikat_dibuang", contoh="dedup_dibuang"),
        _sub("konsensus_run", "Menghitung kemunculan gap lintas run (k/n)",
             "_merge_runs: gap stabil bila run_hits >= min_run_hits (bawaan ceil(2n/3)); "
             "kunci gabungan sama dengan dedup",
             "LLM tidak deterministik: dua run pada chunk identik hanya ~75% tumpang "
             "tindih. Bila job dijalankan n run, tiap gap dicatat muncul di k run; "
             "yang di bawah ambang ditandai tidak stabil dan tidak diteruskan ke "
             "tahap kebaruan. Dengan 1 run semua gap dianggap stabil.",
             masuk="gap_final_setelah_dedup", keluar="gap_stabil",
             dibuang="gap_tidak_stabil", contoh="tidak_stabil"),
    ],
    "novelty": [
        _sub("cek_kebaruan", "Mengecek tiap gap ke literatur terbaru",
             "annotate_gaps \u2192 classify_novelty per gap; progres per gap",
             "Satu per satu, tiap gap dicek apakah sudah ada paper 2024+ yang "
             "menjawabnya. Tiga hal di bawah ini terjadi untuk tiap gap.",
             masuk="gap_dicek", keluar="open", contoh="contoh_addressed"),
        _sub("susun_kata_kunci", "Menyusun kata kunci pencarian",
             "build_keywords: maks 8 term dari gap_statement + istilah topik",
             "Dari kalimat gap diambil kata-kata penting untuk dijadikan kueri "
             "pencarian literatur.",
             dalam="cek_kebaruan"),
        _sub("cari_openalex", "Mencari paper 2024+ di OpenAlex",
             "OpenAlexAPI.search_recent: from_date, maks 8 hasil, rate-limit + cache",
             "Kata kunci dicari di OpenAlex, basis data literatur terbuka, dibatasi "
             "paper terbaru saja.",
             keluar="punya_match_literatur", dalam="cek_kebaruan"),
        _sub("klasifikasi", "Menilai apakah gap sudah dijawab",
             f"_overlap_score \u2265 {STRONG_MATCH_THRESHOLD} = strong; \u22653 strong \u2192 "
             "addressed, 1-2 \u2192 partially_addressed, 0 \u2192 open",
             "Bila \u22653 paper baru sangat cocok, gap dianggap sudah dijawab "
             "(addressed); 1-2 paper berarti sebagian (partially); tidak ada berarti "
             "masih terbuka (open).",
             keluar="open", dalam="cek_kebaruan"),
    ],
    "recommendation": [
        _sub("filter_open", "Meneruskan hanya gap yang masih terbuka",
             "novelty_status in ('open', 'unchecked')",
             "Gap yang sudah dijawab literatur tidak layak jadi topik baru, jadi "
             "hanya yang 'open' yang diteruskan; gap yang gagal dicek (unchecked) "
             "ikut diteruskan tetapi ditandai.",
             masuk="gap_dicek", keluar="gap_open", dibuang="gap_bukan_open",
             contoh="dibuang_bukan_open"),
        _sub("skor_prioritas", "Menghitung skor prioritas tiap gap",
             f"rank_proposals: {W_GAP}\u00d7gap_confidence + {W_NOVELTY}\u00d7novelty_credit + "
             f"{W_ACTIONABILITY}\u00d7actionability; sweet spot {NOVELTY_SWEET_SPOT}",
             "Tiap gap dinilai dari tiga sisi: seberapa yakin kalimatnya asli, "
             "seberapa baru dibanding korpus (tidak terlalu mirip, tidak terlalu "
             "asing), dan seberapa konkret bisa dikerjakan.",
             masuk="gap_open", keluar="proposal_dinilai"),
        _sub("kelompokkan_tema", "Menggabungkan gap serupa jadi tema",
             f"build_themes: cluster_papers single-linkage, ambang "
             f"{THEME_SIMILARITY_THRESHOLD}",
             "Gap yang mirip dari jurnal berbeda dikelompokkan jadi satu tema. Tema "
             "yang didukung banyak jurnal lebih kuat daripada satu jurnal yang "
             "banyak bicara.",
             masuk="proposal_dinilai", keluar="tema", contoh="tema_terbesar"),
        _sub("narasi_judul", "Merumuskan judul, latar belakang, alasan, dan metode",
             f"copilot_client.generate (JSON, 1 panggilan) untuk {NARRATION_TOP} butir teratas: "
             "tema lintas-jurnal dulu, lalu proposal berperingkat; peringkat tidak diubah",
             "Untuk beberapa butir teratas, LLM diminta menuliskan judul penelitian siap "
             "pakai beserta latar belakang singkat, alasan kelayakan, dan usulan metode — "
             "hanya dari kutipan gap yang ada. LLM tidak menilai dan tidak mengubah urutan; "
             "bila LLM tidak tersedia, tahap tetap selesai tanpa narasi.",
             masuk="narasi_diminta", keluar="narasi_dibuat", contoh="narasi_contoh",
             jenis="periksa"),
    ],
}

# Ambang dan bobot yang dipakai pipeline, diimpor dari modul aslinya agar UI
# menampilkan nilai yang benar-benar berjalan.
PIPELINE_CONSTANTS: Dict[str, Dict[str, Any]] = {
    "chunking": {"target_tokens": DEFAULT_TARGET_TOKENS, "max_tokens": DEFAULT_MAX_TOKENS,
                 "overlap_ratio": DEFAULT_OVERLAP_RATIO},
    "gap_mining": {"quote_match_threshold": QUOTE_MATCH_THRESHOLD,
                   "llm_temperature": "tidak dapat diatur (Copilot)",
                   "workers": DEFAULT_EXTRACT_WORKERS,
                   "max_runs": MAX_GAP_RUNS,
                   "default_min_run_hits": "ceil(2n/3)"},
    "novelty": {"strong_match_threshold": STRONG_MATCH_THRESHOLD,
                "addressed_min_strong": 3, "partially_min_strong": 1,
                "from_date": "2024-01-01", "max_results": 8},
    "recommendation": {"w_gap": W_GAP, "w_novelty": W_NOVELTY,
                       "w_actionability": W_ACTIONABILITY,
                       "sweet_spot": list(NOVELTY_SWEET_SPOT),
                       "theme_similarity_threshold": THEME_SIMILARITY_THRESHOLD,
                       "narration_top": NARRATION_TOP},
}


@dataclass
class StageOutcome:
    """Hasil satu tahap: parameter, angka, contoh data, dan berkas keluaran.

    ``substep_samples`` memuat contoh per sub-langkah, termasuk data yang
    DIBUANG (gap gugur verifikasi, duplikat) — bukti bahwa penyaringan
    benar-benar bekerja, bukan sekadar angka.
    """

    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    samples: List[Dict[str, Any]] = field(default_factory=list)
    outputs: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    substep_samples: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)


def _split_duplicates(
    gaps: Sequence[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Pisahkan gap unik dari duplikatnya (sumber + kalimat sama, abaikan kapital)."""
    seen: set = set()
    unique: List[Dict[str, Any]] = []
    duplicates: List[Dict[str, Any]] = []
    for gap in gaps:
        key = (gap.get("source"), (gap.get("gap_statement") or "").strip().lower())
        digest = hashlib.sha1(str(key).encode()).hexdigest()
        if digest in seen:
            duplicates.append(gap)
            continue
        seen.add(digest)
        unique.append(gap)
    return unique, duplicates


def _dedup_gaps(gaps: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _split_duplicates(gaps)[0]


def _gap_digest(gap: Dict[str, Any]) -> str:
    key = (gap.get("source"), (gap.get("gap_statement") or "").strip().lower())
    return hashlib.sha1(str(key).encode()).hexdigest()


def default_min_run_hits(runs: int) -> int:
    """Ambang bawaan 'stabil': muncul di >= 2/3 run (1 run -> 1, 3 run -> 2, 5 run -> 4)."""
    runs = max(1, int(runs))
    return max(1, -(-2 * runs // 3))


def _merge_runs(
    gaps: Sequence[Dict[str, Any]],
    runs: int,
    min_run_hits: int,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Gabungkan gap dari beberapa run menjadi union beranotasi k/n.

    Kunci gabungan sama dengan ``_split_duplicates``. Kemunculan kedua dalam
    run yang SAMA adalah duplikat biasa; kemunculan di run LAIN adalah bukti
    stabilitas dan dihitung ke ``run_hits``. Mengembalikan
    ``(unik, duplikat_dalam_run, gabungan_lintas_run, konsensus)``; tiap gap unik
    membawa ``run_hits``, ``run_total``, ``run_ids`` (1-based) dan ``stable``.
    Dengan ``runs == 1`` hasilnya identik dengan dedup lama plus anotasi itu.
    """
    groups: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    duplicates: List[Dict[str, Any]] = []
    merged: List[Dict[str, Any]] = []
    per_run: Dict[int, set] = defaultdict(set)
    for gap in gaps:
        run = int(gap.pop("_run", 0))
        digest = _gap_digest(gap)
        per_run[run].add(digest)
        group = groups.get(digest)
        if group is None:
            groups[digest] = {"gap": gap, "runs": {run}}
            order.append(digest)
        elif run in group["runs"]:
            duplicates.append(gap)
        else:
            group["runs"].add(run)
            merged.append(gap)
            kept = group["gap"]
            kept["grounding_score"] = max(
                float(kept.get("grounding_score") or 0.0),
                float(gap.get("grounding_score") or 0.0),
            )

    unique: List[Dict[str, Any]] = []
    hits_distribution: Dict[int, int] = defaultdict(int)
    for digest in order:
        gap, seen = groups[digest]["gap"], groups[digest]["runs"]
        gap["run_hits"] = len(seen)
        gap["run_total"] = runs
        gap["run_ids"] = sorted(r + 1 for r in seen)
        gap["stable"] = len(seen) >= min_run_hits
        hits_distribution[len(seen)] += 1
        unique.append(gap)

    jaccards: List[float] = []
    run_keys = list(range(runs))
    for i, a in enumerate(run_keys):
        for b in run_keys[i + 1:]:
            union = per_run[a] | per_run[b]
            if union:
                jaccards.append(len(per_run[a] & per_run[b]) / len(union))
    consensus = {
        "runs": runs,
        "min_run_hits": min_run_hits,
        "stable": sum(1 for g in unique if g["stable"]),
        "unstable": sum(1 for g in unique if not g["stable"]),
        "hits_distribution": {str(k): v for k, v in sorted(hits_distribution.items())},
        "jaccard_between_runs": round(sum(jaccards) / len(jaccards), 3) if jaccards else None,
    }
    return unique, duplicates, merged, consensus


def merge_gap_runs(
    gap_runs: Sequence[Sequence[Dict[str, Any]]],
    min_run_hits: int = 0,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Gabungkan gap dari beberapa run TERPISAH (mis. berkas gaps_*.jsonl) menjadi
    union beranotasi k/n memakai kunci yang sama dengan tahap gap_mining.

    ``min_run_hits`` <= 0 memakai ambang bawaan ceil(2n/3). Mengembalikan
    ``(gap_unik, konsensus)``; ``experiments/consensus_gaps.py`` memanggil ini agar
    angka k/n dari CLI dan dari job identik.
    """
    runs = len(gap_runs)
    if runs == 0:
        return [], {"runs": 0, "min_run_hits": 0, "stable": 0, "unstable": 0,
                    "hits_distribution": {}, "jaccard_between_runs": None}
    threshold = int(min_run_hits or 0)
    if threshold <= 0:
        threshold = default_min_run_hits(runs)
    threshold = max(1, min(threshold, runs))
    tagged: List[Dict[str, Any]] = []
    for idx, gaps in enumerate(gap_runs):
        for gap in gaps:
            if not gap.get("gap_statement"):
                continue
            row = dict(gap)
            row["_run"] = idx
            tagged.append(row)
    unique, _dups, _merged, consensus = _merge_runs(tagged, runs, threshold)
    return unique, consensus


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
            "substep_samples": outcome.substep_samples,
            "duration_ms": duration_ms,
        })
        record_job_event(
            self.job_id, "phase.completed", phase=self.phase, status="running",
            duration_ms=duration_ms, data=dict(outcome.metrics),
        )


class _substep:
    """Catat awal/akhir satu sub-langkah agar UI bisa menunjukkannya live.

    Angka ``masuk`` diberi saat masuk; ``keluar`` (dan ``dibuang``) diisi lewat
    ``done()`` sebelum blok berakhir. Sub-langkah yang gagal tetap dicatat
    selesai dengan ``error`` supaya urutan di UI tidak menggantung; galatnya
    sendiri dilempar ulang dan ditangani ``_StageRecorder``.
    """

    def __init__(self, job_id: str, phase: str, key: str, masuk: Optional[int] = None):
        self.job_id, self.phase, self.key = job_id, phase, key
        self._data: Dict[str, Any] = {"substep": key}
        if masuk is not None:
            self._data["masuk"] = masuk
        self._t0 = 0.0

    def __enter__(self) -> "_substep":
        self._t0 = time.monotonic()
        record_job_event(self.job_id, "substep.started", phase=self.phase,
                         status="running", data=dict(self._data))
        return self

    def done(self, keluar: Optional[int] = None, **extra: Any) -> None:
        if keluar is not None:
            self._data["keluar"] = keluar
        self._data.update(extra)

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is not None and not isinstance(exc, ResearchCancelled):
            self._data["error"] = str(exc)[:300]
        record_job_event(
            self.job_id, "substep.completed", phase=self.phase, status="running",
            duration_ms=int((time.monotonic() - self._t0) * 1000), data=dict(self._data),
        )
        return False


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
    ocr_mode: str = "auto",
) -> StageOutcome:
    results = []
    failed: List[Dict[str, Any]] = []
    total = len(pdf_paths)
    with _substep(job_id, "chunking", "proses_pdf", masuk=total) as sub:
        for i, pdf in enumerate(pdf_paths, 1):
            source = source_name(pdf)
            record_job_event(job_id, "file.started", phase="chunking",
                             data={"file": source, "index": i, "of": total})
            try:
                result = process_pdf(str(pdf), source=source, target_tokens=target_tokens,
                                     max_tokens=max_tokens, overlap_ratio=overlap_ratio,
                                     ocr_mode=ocr_mode)
            except Exception as exc:
                logger.error(f"chunking gagal pada {source}: {exc}")
                record_job_event(job_id, "file.failed", phase="chunking",
                                 data={"file": source, "error": str(exc)[:300]})
                failed.append({"file": source, "error": str(exc)[:300]})
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
        sub.done(keluar=len(results), dibuang=len(failed))

    summary = write_chunks_jsonl(str(out_path), results, job_id=job_id)
    chunks = [c for r in results for c in r.chunks]
    tokens = [c.token_count for c in chunks]
    sections: Dict[str, int] = defaultdict(int)
    for c in chunks:
        sections[c.section_normalized] += 1

    outcome = StageOutcome(
        params={"target_tokens": target_tokens, "max_tokens": max_tokens,
                "overlap_ratio": overlap_ratio, "ocr_mode": ocr_mode},
        metrics={
            "pdf_masuk": total,
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
        substep_samples={
            "pdf_gagal": failed[:SAMPLE_ROWS],
            "chunk_kecil": [
                {"source": c.source, "chunk_index": c.chunk_index,
                 "section": c.section_normalized, "tokens": c.token_count,
                 "text": c.text[:300]}
                for c in sorted((c for c in chunks if c.token_count < 150),
                                key=lambda c: c.token_count)[:SAMPLE_ROWS]
            ],
        },
    )

    if embedder is not None and len(results) > 1:
        with _substep(job_id, "chunking", "cek_koherensi", masuk=len(results)) as sub:
            probes = {
                r.meta.source: build_probe(
                    r.meta.paper_title,
                    [{"text": c.text, "is_reference": c.is_reference,
                      "chunk_index": c.chunk_index} for c in r.chunks])
                for r in results
            }
            reports = check_corpus_relevance(probes, embedder=embedder)
            flagged = [rep.to_dict() for rep in reports if rep.flagged]
            sub.done(keluar=len(flagged))
        outcome.metrics["jurnal_ditandai_tak_sedomain"] = len(flagged)
        if flagged:
            outcome.notes.append(
                f"{len(flagged)} jurnal tampak di luar bidang batch ini — peringatan, "
                "bukan penolakan; hanya andal untuk penyusup minoritas.")
            outcome.samples.extend(flagged)
    else:
        # Kunci tetap ada agar peta proses bisa menunjukkan langkah ini dilewati,
        # bukan menyamarkannya sebagai "0 jurnal ditandai".
        outcome.metrics["jurnal_ditandai_tak_sedomain"] = "tidak dicek"
    return outcome


# ── TAHAP 2 ────────────────────────────────────────────────────────────────

def stage_gap_mining(
    job_id: str,
    chunks_path: Path,
    out_path: Path,
    limit: int = 0,
    llm_trace_limit: int = DEFAULT_LLM_TRACE_LIMIT,
    workers: int = DEFAULT_EXTRACT_WORKERS,
    runs: int = 1,
    min_run_hits: int = 0,
) -> StageOutcome:
    """TAHAP 2. ``runs`` > 1 mengulang lintasan LLM atas kandidat yang sama dan
    menandai tiap gap dengan k/n kemunculannya; ``min_run_hits`` <= 0 memakai
    ambang bawaan ``default_min_run_hits`` (ceil(2n/3))."""
    runs = max(1, min(int(runs or 1), MAX_GAP_RUNS))
    min_run_hits = int(min_run_hits or 0)
    if min_run_hits <= 0:
        min_run_hits = default_min_run_hits(runs)
    min_run_hits = max(1, min(min_run_hits, runs))
    chunks = [c for c in read_jsonl(str(chunks_path)) if c.get("record") == "chunk"]
    by_source: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in chunks:
        by_source[c.get("source")].append(c)

    with _substep(job_id, "gap_mining", "pilih_kandidat", masuk=len(chunks)) as sub:
        candidates = select_candidates(chunks)
        if limit:
            candidates = candidates[:limit]
        regex_baseline = sum(
            1 for c in chunks
            if not c.get("is_reference") and matched_phrases(c.get("text", "")))
        sub.done(keluar=len(candidates), baseline_regex=regex_baseline)

    traced = {"n": 0, "calls": 0, "empty": 0}
    trace_lock = threading.Lock()
    # Jejak per kandidat: chunk mana dibaca → LLM menjawab apa → gap apa yang
    # ter-parse. Dianotasi hasil verifikasi & dedup di bawah, lalu ditulis ke JSONL
    # agar UI bisa menelusuri rantai lengkapnya untuk SEMUA kandidat (jejak DB
    # hanya menyimpan prompt/balasan 15 pertama).
    cand_trace: List[Dict[str, Any]] = []

    def _work(cand: Dict[str, Any], run_idx: int = 0) -> List[Dict[str, Any]]:
        captured: Dict[str, Any] = {"response": None, "model": ""}

        def _generate(prompt: str, system: str) -> Optional[str]:
            result = copilot_client.generate(prompt, system=system, json_mode=True)
            text = result[0] if result else None
            captured["response"], captured["model"] = text, (result[1] if result else "")
            with trace_lock:
                traced["calls"] += 1
                if not text:
                    traced["empty"] += 1
                keep = traced["n"] < llm_trace_limit
                if keep:
                    traced["n"] += 1
                    seq = traced["n"]
            if keep:
                add_stage_artifact(job_id, "gap_mining", "llm", f"kandidat {seq}", {
                    "prompt": prompt,
                    "response": text or "",
                    "model": captured["model"],
                    "system": system,
                    "source": cand.get("source"),
                    "chunk_id": cand.get("chunk_id"),
                    "candidate_reason": cand.get("candidate_reason"),
                    "run": run_idx + 1,
                })
            return text

        context = with_context(cand, by_source)
        gaps = extract_gaps_from_candidate(cand, context, generate_fn=_generate)
        for g in gaps:
            g["_run"] = run_idx  # dilepas _merge_runs menjadi run_ids
        with trace_lock:
            cand_trace.append({
                "source": cand.get("source"),
                "paper_title": cand.get("paper_title"),
                "chunk_id": cand.get("chunk_id"),
                "chunk_index": cand.get("chunk_index"),
                "section_normalized": cand.get("section_normalized"),
                "token_count": cand.get("token_count"),
                "candidate_reason": cand.get("candidate_reason"),
                "matched_phrases": cand.get("matched_phrases") or [],
                "context_chars": len(context),
                "run": run_idx + 1,
                "llm_answered": bool(captured["response"]),
                "model": captured["model"],
                "response": captured["response"] or "",
                "_gaps": gaps,  # referensi objek; dianotasi setelah verifikasi
            })
        return gaps

    raw_gaps: List[Dict[str, Any]] = []
    done = 0
    total_calls = len(candidates) * runs
    with _substep(job_id, "gap_mining", "ekstrak_llm", masuk=len(candidates)) as sub, \
            ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_work, c, r) for r in range(runs) for c in candidates]
        try:
            for fut in as_completed(futures):
                done += 1
                try:
                    raw_gaps.extend(fut.result())
                except Exception as exc:
                    logger.warning(f"kandidat gagal: {exc}")
                if done % 10 == 0 or done == total_calls:
                    _ensure_active(job_id)
                    _progress(job_id, 30 + 26 * done / max(1, total_calls),
                              f"Ekstraksi gap {done}/{total_calls} kandidat"
                              + (f" ({runs} run)" if runs > 1 else ""))
        except ResearchCancelled:
            # Kandidat yang belum mulai dibuang; yang sedang berjalan dibiarkan
            # selesai oleh ``with`` agar tidak ada thread yatim.
            for fut in futures:
                fut.cancel()
            raise
        sub.done(keluar=len(raw_gaps), llm_tanpa_jawaban=traced["empty"], run=runs)

    # LLM mati/tidak terautentikasi tidak melempar galat: generate() mengembalikan
    # None dan ekstraksi diam-diam menghasilkan 0 gap. Tanpa peringatan ini,
    # "100 kandidat → 0 gap" terbaca seperti hasil analisis yang sah.
    llm_notes: List[str] = []
    if traced["calls"] and traced["empty"] == traced["calls"]:
        llm_notes.append(
            f"LLM TIDAK MENJAWAB satu pun dari {traced['calls']} panggilan — hasil "
            "0 gap ini BUKAN temuan, melainkan gagal sistem (CLI Copilot mati, belum login, atau "
            "autentikasi hilang). Perbaiki layanan LLM lalu jalankan ulang.")
    elif traced["empty"]:
        llm_notes.append(
            f"{traced['empty']} dari {traced['calls']} panggilan LLM tidak dijawab; "
            "cakupan gap di bawah normal. Pertimbangkan menjalankan ulang.")

    raw_path = str(out_path) + ".raw.jsonl"
    write_jsonl(raw_path, raw_gaps)

    _progress(job_id, 57, f"Verifikasi verbatim {len(raw_gaps)} gap ke teks sumber")
    with _substep(job_id, "gap_mining", "verifikasi_verbatim", masuk=len(raw_gaps)) as sub:
        grounded = verify_gaps(raw_gaps, by_source)
        # verify_gaps menulis grounding_score ke SEMUA gap, termasuk yang ditolak,
        # jadi contoh yang gugur bisa diambil tanpa menghitung ulang.
        kept_ids = {id(g) for g in grounded}
        rejected = [g for g in raw_gaps if id(g) not in kept_ids]
        sub.done(keluar=len(grounded), dibuang=len(rejected))

    _progress(job_id, 59, f"Menghapus duplikat dari {len(grounded)} gap")
    with _substep(job_id, "gap_mining", "dedup", masuk=len(grounded)) as sub:
        gaps, duplicates, merged, consensus = _merge_runs(grounded, runs, min_run_hits)
        sub.done(keluar=len(gaps), dibuang=len(duplicates), gabungan_lintas_run=len(merged))
    with _substep(job_id, "gap_mining", "konsensus_run", masuk=len(gaps)) as sub:
        stable_gaps = [g for g in gaps if g["stable"]]
        unstable_gaps = [g for g in gaps if not g["stable"]]
        sub.done(keluar=len(stable_gaps), dibuang=len(unstable_gaps), run=runs,
                 min_run_hits=min_run_hits)
    journals = len({g["source"] for g in stable_gaps})

    # Anotasi jejak kandidat dengan nasib tiap gap-nya. verify_gaps menulis
    # grounding_score in-place, jadi objek gap yang sama sudah membawa skornya.
    dup_ids = {id(g) for g in duplicates} | {id(g) for g in merged}
    cand_trace.sort(key=lambda t: (str(t.get("source")), t.get("chunk_index") or 0,
                                   t.get("run") or 0))
    for seq, trace in enumerate(cand_trace, 1):
        trace["seq"] = seq
        gap_rows = []
        for g in trace.pop("_gaps"):
            gap_rows.append({
                "gap_statement": g.get("gap_statement"),
                "gap_type": g.get("gap_type"),
                "topic": g.get("topic"),
                "gap_paraphrase": g.get("gap_paraphrase"),
                "grounding_score": g.get("grounding_score"),
                "lolos_verifikasi": id(g) in kept_ids,
                "duplikat": id(g) in dup_ids,
            })
        trace["gaps"] = gap_rows
        trace["gap_mentah"] = len(gap_rows)
        trace["gap_lolos"] = sum(1 for r in gap_rows if r["lolos_verifikasi"])
        trace["gap_final"] = sum(1 for r in gap_rows
                                 if r["lolos_verifikasi"] and not r["duplikat"])
    candidates_path = Path(out_path).with_name(f"candidates_{Path(out_path).stem}.jsonl")
    write_jsonl(str(candidates_path), cand_trace)

    meta = {
        "record": "meta", "job_id": job_id,
        "diekspor_pada": datetime.now().isoformat(timespec="seconds"),
        "jumlah_gap": len(gaps), "jumlah_gap_stabil": len(stable_gaps),
        "jumlah_jurnal_bergap": journals,
        "jumlah_kandidat": len(candidates),
        "konsensus": consensus,
        "catatan": "Gap terstruktur; gap_statement diverifikasi verbatim di chunk sumber. "
                   "run_hits/run_total = kemunculan lintas run; stable=false tidak "
                   "diteruskan ke tahap kebaruan.",
    }
    write_jsonl(str(out_path), [meta] + gaps)

    def _gap_row(g: Dict[str, Any]) -> Dict[str, Any]:
        return {"source": g.get("source"), "gap_type": g.get("gap_type"),
                "topic": g.get("topic"), "grounding_score": g.get("grounding_score"),
                "run_hits": g.get("run_hits"), "run_total": g.get("run_total"),
                "stable": g.get("stable"),
                "gap_statement": (g.get("gap_statement") or "")[:300],
                "gap_paraphrase": (g.get("gap_paraphrase") or "")[:200]}

    return StageOutcome(
        params={"limit": limit or "semua", "llm_trace_limit": llm_trace_limit,
                "workers": workers, "temperature": "tidak dapat diatur (Copilot)",
                "runs": runs, "min_run_hits": min_run_hits,
                "seksi_sasaran": "conclusion + discussion",
                "aturan_cadangan": "abstract, 2 chunk introduction, 2 chunk terakhir"},
        metrics={
            "chunk_masuk": len(chunks),
            "kandidat": len(candidates),
            "baseline_regex_saja": regex_baseline,
            "llm_dipanggil": traced["calls"],
            "llm_tanpa_jawaban": traced["empty"],
            "gap_mentah": len(raw_gaps),
            "lolos_verifikasi_verbatim": len(grounded),
            "gugur_di_verifikasi": len(rejected),
            "duplikat_dibuang": len(duplicates),
            "gabungan_lintas_run": len(merged),
            "gap_final_setelah_dedup": len(gaps),
            "run_total": runs,
            "min_run_hits": min_run_hits,
            "gap_stabil": len(stable_gaps),
            "gap_tidak_stabil": len(unstable_gaps),
            "jaccard_antar_run": consensus["jaccard_between_runs"],
            "jurnal_bergap": journals,
        },
        samples=[_gap_row(g) for g in stable_gaps[:SAMPLE_ROWS]],
        outputs={"gaps_jsonl": str(out_path), "gaps_raw_jsonl": raw_path,
                 "candidates_jsonl": str(candidates_path)},
        substep_samples={
            # Skor terendah dulu: itulah kandidat halusinasi yang paling jelas.
            "verifikasi_gugur": [
                _gap_row(g) for g in sorted(
                    rejected, key=lambda g: g.get("grounding_score") or 0.0)[:SAMPLE_ROWS]
            ],
            "dedup_dibuang": [_gap_row(g) for g in duplicates[:SAMPLE_ROWS]],
            "tidak_stabil": [_gap_row(g) for g in unstable_gaps[:SAMPLE_ROWS]],
        },
        notes=llm_notes + [
               "Tiap gap_statement wajib muncul verbatim di chunk sumbernya; "
               "yang di bawah ambang grounding dibuang sebagai dugaan halusinasi.",
               "Cakupan gap tidak reproducible penuh: dua run pada chunk identik "
               "hanya ~75% tumpang tindih."] + (
               [f"{runs} run pada kandidat yang sama (Jaccard antar-run "
                f"{consensus['jaccard_between_runs']}); gap dianggap stabil bila muncul di "
                f">= {min_run_hits} run: {len(stable_gaps)} stabil, {len(unstable_gaps)} tidak "
                "stabil (ditandai stable=false, tidak diteruskan ke tahap kebaruan)."]
               if runs > 1 else
               ["Hanya 1 run: k/n belum informatif; jalankan dengan gap_runs=3 untuk "
                "mengukur stabilitas tiap gap."]),
    )


# ── TAHAP 3 ────────────────────────────────────────────────────────────────

def stage_novelty(
    job_id: str,
    gaps_path: Path,
    out_path: Path,
    from_date: str = "2024-01-01",
    min_interval: float = 1.0,
    max_retries: int = 4,
    limit: int = 0,
) -> StageOutcome:
    rows = list(read_jsonl(str(gaps_path)))
    meta = next((r for r in rows if r.get("record") == "meta"), {})
    all_gaps = [r for r in rows if "gap_statement" in r]
    # Gap yang tidak stabil lintas run (stable=false) tidak dikirim ke OpenAlex:
    # menghemat kuota dan mencegah gap satu-undian dilaporkan sebagai kebaruan.
    gaps = [g for g in all_gaps if g.get("stable", True)]
    skipped_unstable = len(all_gaps) - len(gaps)
    offline = novelty_disabled()
    tick_label = "Menandai unchecked" if offline else "Cek OpenAlex"

    def _tick(done: int, total: int) -> None:
        # OpenAlex dibatasi ~1 permintaan/dtk, jadi tahap ini lambat dan tanpa
        # progres per gap pengguna hanya melihat angka diam selama beberapa menit.
        if done % 5 == 0 or done == total:
            _ensure_active(job_id)
            _progress(job_id, 62 + 18 * done / max(1, total),
                      f"{tick_label} {done}/{total} gap")

    if offline:
        _progress(job_id, 62, f"Cek kebaruan dimatikan (OPENALEX_DISABLED) — {len(gaps)} gap "
                  "ditandai unchecked")
    else:
        _progress(job_id, 62, f"Cek kebaruan {len(gaps)} gap ke OpenAlex"
                  + (f" (maks {limit})" if limit else ""))
    with _substep(job_id, "novelty", "cek_kebaruan", masuk=len(gaps)) as sub:
        enriched = annotate_gaps(gaps, from_date=from_date, min_interval=min_interval,
                                 max_retries=max_retries, on_progress=_tick, limit=limit)
        counts: Dict[str, int] = defaultdict(int)
        for g in enriched:
            counts[g.get("novelty_status", "?")] += 1
        sub.done(keluar=counts.get("open", 0), **{k: v for k, v in counts.items()
                                                  if k != "open"})
    with_matches = sum(1 for g in enriched if g.get("related_recent_papers"))
    unchecked = [g for g in enriched if g.get("novelty_status") == "unchecked"]
    disabled = any(g.get("novelty_error") == DISABLED_REASON for g in unchecked)
    quota_hit = sorted({g.get("novelty_error") for g in unchecked
                        if g.get("novelty_error")
                        and g.get("novelty_error") not in (LIMIT_REASON, DISABLED_REASON)})

    out_meta = dict(meta)
    out_meta.update({
        "novelty_checked_at": datetime.now().isoformat(timespec="seconds"),
        "novelty_from_date": from_date,
        "novelty_status_counts": dict(counts),
    })
    write_jsonl(str(out_path), [out_meta] + enriched)

    def _nov_row(g: Dict[str, Any]) -> Dict[str, Any]:
        return {"source": g.get("source"), "novelty_status": g.get("novelty_status"),
                "novelty_query": g.get("novelty_query"),
                "gap_statement": (g.get("gap_statement") or "")[:200],
                "literatur_2024plus": [
                    {"title": (p.get("title") or "")[:100], "year": p.get("year"),
                     "match_score": p.get("match_score")}
                    for p in (g.get("related_recent_papers") or [])[:3]]}

    return StageOutcome(
        params={"from_date": from_date, "min_interval": min_interval,
                "max_retries": max_retries,
                "sumber": "OpenAlex (dimatikan)" if disabled else "OpenAlex",
                "dimatikan": disabled,
                "ambang_strong_match": STRONG_MATCH_THRESHOLD,
                "batas_cek": limit or "semua"},
        metrics={
            "gap_dicek": len(enriched) - len(unchecked),
            "open": counts.get("open", 0),
            "partially_addressed": counts.get("partially_addressed", 0),
            "addressed": counts.get("addressed", 0),
            "unchecked": len(unchecked),
            "punya_match_literatur": with_matches,
            "tanpa_match_literatur": len(enriched) - len(unchecked) - with_matches,
            "gap_tidak_stabil_dilewati": skipped_unstable,
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
        substep_samples={
            # Yang "sudah dijawab" adalah bukti bahwa pengecekan bekerja; yang
            # "open" tanpa paper sama sekali perlu dicurigai sebagai efek throttle.
            "contoh_addressed": [_nov_row(g) for g in enriched
                                 if g.get("novelty_status") == "addressed"][:SAMPLE_ROWS],
            "contoh_open": [_nov_row(g) for g in enriched
                            if g.get("novelty_status") == "open"][:SAMPLE_ROWS],
            "contoh_unchecked": [_nov_row(g) for g in unchecked][:SAMPLE_ROWS],
        },
        notes=(
            [f"Cek kebaruan DIMATIKAN (env OPENALEX_DISABLED=1): {len(unchecked)} gap berstatus "
             "'unchecked' tanpa permintaan jaringan dan tetap diteruskan ke rekomendasi. Skor "
             "prioritas tidak bergantung OpenAlex — kebaruan proposal diukur terhadap korpus "
             "unggahan; yang hilang hanya penyaringan gap yang sudah dijawab literatur 2024+."]
            if disabled else []
        ) + (
            [f"{skipped_unstable} gap tidak stabil lintas run (stable=false) tidak dicek "
             "kebaruannya dan tidak diteruskan ke rekomendasi."]
            if skipped_unstable else []
        ) + (
            [f"{len(unchecked)} gap TIDAK dicek ({'; '.join(quota_hit)}). Statusnya "
             "'unchecked', bukan 'open' — jalankan ulang tahap ini setelah kuota pulih."]
            if quota_hit else []
        ) + (
            [f"{sum(1 for g in unchecked if g.get('novelty_error') == LIMIT_REASON)} gap "
             f"di luar batas cek ({limit}) sengaja tidak dikirim ke OpenAlex."]
            if limit and any(g.get("novelty_error") == LIMIT_REASON for g in unchecked) else []
        ) + (
            [] if disabled else [
                "Kuota gratis OpenAlex ≈ 100 pencarian/hari per IP; gap yang gagal dicek "
                "berstatus 'unchecked' agar gangguan layanan tidak terbaca sebagai 'semua gap baru'.",
            ]
        ),
    )


# ── TAHAP 4 ────────────────────────────────────────────────────────────────

NARRATION_FIELDS = ("judul", "latar_belakang", "alasan", "metode")
_NARRATION_SYSTEM = (
    "Anda pakar metodologi penelitian yang menulis dalam Bahasa Indonesia. Tugas Anda "
    "hanya MERUMUSKAN teks dari bahan yang diberikan: Anda tidak menilai, tidak "
    "memeringkat, dan tidak menambah temuan yang tidak ada dalam kutipan."
)
_NOVELTY_WORDS = {"open": "masih terbuka", "unchecked": "belum dicek ke literatur luar",
                  "partially_addressed": "sebagian sudah dijawab", "addressed": "sudah dijawab"}


def _novelty_summary(items: Sequence[Dict[str, Any]]) -> str:
    """Ringkasan status kebaruan sekelompok proposal, untuk bahan 'alasan'."""
    counts = Counter(str(p.get("novelty_status") or "unchecked") for p in items)
    parts = [f"{n} {_NOVELTY_WORDS.get(k, k)}" for k, n in counts.most_common()]
    recent = sum(len(p.get("related_recent_papers") or []) for p in items)
    return ", ".join(parts) + (f"; {recent} paper 2024+ terkait ditemukan" if recent else "")


def _narration_seeds(ranked: Sequence[Dict[str, Any]], themes: Sequence[Any],
                     top: int = NARRATION_TOP) -> List[Dict[str, Any]]:
    """Butir yang dinarasikan: tema lintas-jurnal dulu (bukti terkuat), lalu proposal
    berperingkat yang belum terwakili tema tersebut. Urutan peringkat rumus project
    dipertahankan; tidak ada batas per jurnal."""
    rank_of = {id(p): i for i, p in enumerate(ranked, 1)}
    seeds: List[Dict[str, Any]] = []
    covered: set = set()
    for t in themes:
        if len(seeds) >= top:
            break
        if t.journal_support < 2:
            continue
        covered.update(id(m) for m in t.members)
        seeds.append({
            "basis": "tema_lintas_jurnal", "theme_id": t.theme_id,
            "peringkat": min((rank_of.get(id(m), 10**6) for m in t.members), default=None),
            "teks": t.label, "topik": ", ".join(t.topics) or "-",
            "jurnal": list(t.journals), "jumlah_jurnal": t.journal_support,
            "jumlah_gap": len(t.members), "kebaruan": _novelty_summary(t.members),
            "skor_prioritas": round(t.top_priority, 4),
            "kutipan": [{"source": m.get("source"),
                        "gap_statement": (m.get("description") or "")[:300]}
                       for m in t.members[:3]],
        })
    for i, p in enumerate(ranked, 1):
        if len(seeds) >= top:
            break
        if id(p) in covered:
            continue
        seeds.append({
            "basis": "proposal", "theme_id": None, "peringkat": i,
            "teks": p.get("title"), "topik": p.get("topic") or "-",
            "jurnal": [p.get("source")], "jumlah_jurnal": 1, "jumlah_gap": 1,
            "kebaruan": _novelty_summary([p]),
            "skor_prioritas": (p.get("novelty") or {}).get("priority_score"),
            "kutipan": [{"source": p.get("source"),
                        "gap_statement": (p.get("description") or "")[:300]}],
        })
    return seeds


def _narration_prompt(seeds: Sequence[Dict[str, Any]]) -> str:
    lines = [
        f"Berikut {len(seeds)} butir gap penelitian yang SUDAH diperingkat oleh sistem; "
        "urutan dan jumlahnya tidak boleh diubah. Untuk TIAP butir tulis:",
        '- "judul": satu judul penelitian Bahasa Indonesia yang spesifik dan layak '
        "skripsi/tesis (maksimal 25 kata).",
        '- "latar_belakang": 2-3 kalimat: apa masalahnya dan mengapa penting, HANYA dari '
        "kutipan gap dan nama jurnal yang diberikan (sebut jurnal sumbernya).",
        '- "alasan": 1-2 kalimat mengapa layak diteliti: sebutkan jumlah jurnal pendukung '
        "dan status kebaruan yang diberikan, apa adanya.",
        '- "metode": 2-3 kalimat pendekatan penelitian yang disarankan (desain, data, '
        "metrik evaluasi). Istilah teknis boleh dalam bahasa Inggris.",
        "Jangan mengarang angka atau temuan yang tidak ada dalam bahan. Kembalikan HANYA "
        'JSON array: [{"no": 1, "judul": "...", "latar_belakang": "...", "alasan": "...", '
        '"metode": "..."}, ...]',
        "", "Butir:",
    ]
    for i, s in enumerate(seeds, 1):
        basis = (f"tema lintas-jurnal · {s['jumlah_jurnal']} jurnal · {s['jumlah_gap']} gap"
                 if s["basis"] == "tema_lintas_jurnal"
                 else f"proposal peringkat #{s['peringkat']} · 1 jurnal")
        lines.append(f"{i}. [{basis} · topik {s['topik']} · kebaruan: {s['kebaruan']}] {s['teks']}")
        for q in s["kutipan"]:
            lines.append(f'   - Kutipan ({q["source"]}): "{q["gap_statement"]}"')
    return "\n".join(lines)


def _parse_narration(raw: Optional[str], n: int) -> List[Optional[Dict[str, str]]]:
    """Selaraskan jawaban LLM ke ``n`` butir (indeks = ``no`` - 1); butir yang hilang
    atau tanpa judul menjadi None. Toleran terhadap pagar kode dan pembungkus objek."""
    slots: List[Optional[Dict[str, str]]] = [None] * n
    if not raw:
        return slots
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.S)
        if not match:
            return slots
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return slots
    if isinstance(data, dict):
        data = next((v for v in data.values() if isinstance(v, list)), [])
    if not isinstance(data, list):
        return slots
    for idx, item in enumerate(data):
        if not isinstance(item, dict) or not str(item.get("judul") or "").strip():
            continue
        try:
            pos = int(item.get("no", idx + 1)) - 1
        except (TypeError, ValueError):
            pos = idx
        if 0 <= pos < n and slots[pos] is None:
            slots[pos] = {f: str(item.get(f) or "").strip() for f in NARRATION_FIELDS}
    return slots


def _narrate_titles(job_id: str, seeds: Sequence[Dict[str, Any]],
                    generate: Optional[Callable[..., Any]] = None,
                    ) -> tuple[List[Dict[str, Any]], Optional[str], str]:
    """Satu panggilan LLM untuk semua butir. Mengembalikan (record narasi, alasan gagal,
    model). Tidak pernah melempar: narasi adalah pelengkap, bukan syarat tahap selesai."""
    if not seeds:
        return [], "tidak ada proposal untuk dinarasikan", ""
    generate = generate or copilot_client.generate
    prompt = _narration_prompt(seeds)
    try:
        result = generate(prompt, system=_NARRATION_SYSTEM, json_mode=True)
    except Exception as exc:  # jaringan/CLI mati: tahap tetap selesai tanpa narasi
        logger.warning(f"narasi judul gagal: {exc}")
        return [], f"LLM gagal: {str(exc)[:200]}", ""
    text, model = (result[0], result[1]) if result else (None, "")
    add_stage_artifact(job_id, "recommendation", "llm", "narasi judul", {
        "prompt": prompt, "response": text or "", "model": model,
        "system": _NARRATION_SYSTEM, "butir": len(seeds),
    })
    if not text:
        return [], "LLM tidak tersedia atau tidak menjawab", model
    slots = _parse_narration(text, len(seeds))
    records = []
    for i, (seed, item) in enumerate(zip(seeds, slots), 1):
        if item is None:
            continue
        records.append({"no": i, **seed, **item, "model": model})
    reason = None if records else "jawaban LLM tidak berbentuk JSON butir yang diminta"
    return records, reason, model


def _narration_markdown(records: Sequence[Dict[str, Any]], requested: int,
                        reason: Optional[str]) -> List[str]:
    lines = ["", "## Judul Siap-Pakai (narasi LLM)", "",
             "> Judul, latar belakang, alasan, dan metode dirumuskan LLM dari kutipan gap; "
             "peringkat tetap dari rumus project, LLM tidak menilai. Tema lintas-jurnal "
             "didahulukan, lalu proposal teratas.", ""]
    if not records:
        lines.append(f"_Tidak ada narasi ({reason or 'tidak diketahui'}); {requested} butir diminta._")
        return lines
    for r in records:
        basis = (f"tema lintas-jurnal · {r['jumlah_jurnal']} jurnal · {r['jumlah_gap']} gap"
                 if r["basis"] == "tema_lintas_jurnal" else f"proposal peringkat #{r['peringkat']}")
        lines += [f"### {r['no']}. {r['judul']}",
                  f"_{basis} · topik {r['topik']} · kebaruan: {r['kebaruan']} · "
                  f"jurnal: {'; '.join(str(j) for j in r['jurnal'])}_", "",
                  f"**Latar belakang.** {r['latar_belakang']}", "",
                  f"**Alasan.** {r['alasan']}", "",
                  f"**Metode.** {r['metode']}", ""]
    return lines


def stage_recommendation(
    job_id: str,
    gaps_novelty_path: Path,
    chunks_path: Path,
    out_path: Path,
    embedder=None,
    top: int = 15,
    narrate_top: int = NARRATION_TOP,
    generate_fn: Optional[Callable[..., Any]] = None,
) -> StageOutcome:
    """``narrate_top`` butir teratas dinarasikan LLM (0 = tanpa narasi); ``generate_fn``
    menggantikan ``copilot_client.generate`` (tes)."""
    gaps = [g for g in read_jsonl(str(gaps_novelty_path)) if "gap_statement" in g]
    _progress(job_id, 82, f"Menyaring gap open dari {len(gaps)} gap")
    with _substep(job_id, "recommendation", "filter_open", masuk=len(gaps)) as sub:
        # 'unchecked' (kuota/gangguan OpenAlex) ikut diteruskan seperti perilaku
        # lama yang melabelinya 'open', tetapi dihitung terpisah agar terlihat.
        open_gaps = [g for g in gaps if g.get("novelty_status") in ("open", "unchecked")]
        not_open = [g for g in gaps if g.get("novelty_status") not in ("open", "unchecked")]
        unchecked_kept = sum(1 for g in open_gaps if g.get("novelty_status") == "unchecked")
        sub.done(keluar=len(open_gaps), dibuang=len(not_open), unchecked_ikut=unchecked_kept)
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
            # Bahan narasi (bukan masukan rumus): status kebaruan & paper 2024+ terkait.
            "novelty_status": g.get("novelty_status"),
            "related_recent_papers": g.get("related_recent_papers") or [],
        })

    _progress(job_id, 85, f"Memeringkat {len(proposals)} proposal")
    with _substep(job_id, "recommendation", "skor_prioritas", masuk=len(proposals)) as sub:
        ranked = rank_proposals(proposals, corpus, gap_conf, embedder=embedder)
        sub.done(keluar=len(ranked))
    _progress(job_id, 92, f"Mengelompokkan {len(ranked)} proposal jadi tema")
    with _substep(job_id, "recommendation", "kelompokkan_tema", masuk=len(ranked)) as sub:
        themes = build_themes(ranked, embedder=embedder)
        sub.done(keluar=len(themes))
    cross = [t for t in themes if t.journal_support >= 2]
    singletons = sum(1 for t in themes if len(t.members) == 1)

    # Narasi: LLM hanya menulis judul/latar belakang/alasan/metode untuk butir
    # teratas; peringkat & skor di atas tidak disentuh. Gagal = tahap tetap selesai.
    seeds = _narration_seeds(ranked, themes, top=max(0, int(narrate_top)))
    _progress(job_id, 95, f"Merumuskan judul siap-pakai untuk {len(seeds)} butir teratas")
    with _substep(job_id, "recommendation", "narasi_judul", masuk=len(seeds)) as sub:
        narration, narration_reason, narration_model = (
            _narrate_titles(job_id, seeds, generate=generate_fn) if seeds
            else ([], "narasi dimatikan (narrate_top=0)" if not narrate_top
                  else "tidak ada proposal untuk dinarasikan", ""))
        sub.done(keluar=len(narration), model=narration_model,
                 **({"alasan": narration_reason} if narration_reason else {}))

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
    if narrate_top:
        lines += _narration_markdown(narration, len(seeds), narration_reason)
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")

    # Markdown hanya memuat top-N; JSONL menyimpan seluruh proposal agar UI bisa
    # menelusuri semuanya beserta tema induknya.
    theme_of = {id(p): t for t in themes for p in t.members}
    proposals_path = Path(out_path).with_suffix(".jsonl")
    themes_path = Path(out_path).with_name(f"{Path(out_path).stem}_tema.jsonl")
    narration_path = Path(out_path).with_name(f"{Path(out_path).stem}_judul.jsonl")
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
            "novelty_status": p.get("novelty_status"),
            "priority_score": nov.get("priority_score"),
            "novelty": nov.get("novelty"),
            "band": nov.get("band"),
            "actionability": nov.get("actionability"),
            # Tiga suku rumus + tetangga terdekat, agar UI bisa menunjukkan dari
            # mana priority_score berasal, bukan hanya angkanya.
            "gap_confidence": nov.get("gap_confidence"),
            "novelty_credit": nov.get("novelty_credit"),
            "nearest_paper": nov.get("nearest_paper"),
            "nearest_similarity": nov.get("nearest_similarity"),
            "score_notes": nov.get("notes"),
            "theme_id": theme.theme_id if theme else None,
            "theme_label": theme.label if theme else None,
            "theme_journal_support": theme.journal_support if theme else None,
            "theme_size": len(theme.members) if theme else None,
        })
    write_jsonl(str(proposals_path), proposal_records)
    write_jsonl(str(themes_path), [t.to_dict() for t in themes])
    write_jsonl(str(narration_path), narration)

    return StageOutcome(
        params={"rumus": "0.5*gap_confidence + 0.3*novelty + 0.2*actionability",
                "filter": "novelty_status in (open, unchecked)",
                "pemecah_seri": "jarak novelty ke tengah sweet spot",
                "embedder": "multilingual-MiniLM" if embedder is not None else "leksikal",
                "top": top,
                "narasi_butir": narrate_top,
                "narasi_model": narration_model or "-",
                "narasi_urutan": "tema lintas-jurnal dulu, lalu proposal berperingkat; "
                                 "tanpa batas per jurnal"},
        metrics={
            "gap_dicek": len(gaps),
            "gap_open": len(open_gaps),
            "gap_bukan_open": len(not_open),
            "proposal_dinilai": len(proposals),
            "tema": len(themes),
            "tema_lintas_jurnal": len(cross),
            "tema_satu_gap": singletons,
            "tema_satu_gap_pct": round(100 * singletons / max(1, len(themes)), 1),
            "skor_tertinggi": ranked[0]["novelty"]["priority_score"] if ranked else 0,
            "narasi_diminta": len(seeds),
            "narasi_dibuat": len(narration),
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
                 "themes_jsonl": str(themes_path),
                 "narasi_jsonl": str(narration_path)},
        substep_samples={
            "dibuang_bukan_open": [
                {"source": g.get("source"), "novelty_status": g.get("novelty_status"),
                 "gap_statement": (g.get("gap_statement") or "")[:200],
                 "paper_penjawab": [(p.get("title") or "")[:100] for p in
                                    (g.get("related_recent_papers") or [])[:2]]}
                for g in not_open[:SAMPLE_ROWS]
            ],
            "tema_terbesar": [
                {"theme_id": t.theme_id, "label": t.label, "journal_support": t.journal_support,
                 "size": len(t.members), "topics": t.topics,
                 "anggota": [{"source": m.get("source"), "title": (m.get("title") or "")[:120]}
                             for m in t.members[:6]]}
                for t in sorted(themes, key=lambda t: -len(t.members))[:3]
            ],
            "narasi_contoh": [
                {"no": r["no"], "basis": r["basis"], "judul": r["judul"],
                 "jurnal": r["jurnal"], "metode": r["metode"][:200]}
                for r in narration[:3]
            ],
        },
        notes=["journal_support pada tema besar adalah batas atas, bukan bukti "
               "bahwa N jurnal menyatakan gap yang sama (chaining single-linkage)."]
        + ([f"Narasi judul tidak dibuat: {narration_reason}. Peringkat dan skor tidak "
            "terpengaruh."] if narrate_top and narration_reason and not narration else [])
        + (["Judul/latar belakang/alasan/metode adalah tulisan LLM dari kutipan gap — "
            "bahan awal, bukan hasil penilaian; LLM tidak mengubah peringkat."]
           if narration else []),
    )


# ── Orkestrator ────────────────────────────────────────────────────────────

# Berkas keluaran yang harus sudah ada bila pipeline dilanjutkan dari sebuah tahap.
_STAGE_INPUTS = {
    "chunking": [],
    "gap_mining": ["chunks"],
    "novelty": ["gaps"],
    "recommendation": ["novelty", "chunks"],
}


def run_research_pipeline(
    job_id: str,
    pdf_paths: Sequence[Path],
    out_dir: Path,
    embedder=None,
    limit: int = 0,
    from_date: str = "2024-01-01",
    until: Optional[str] = None,
    ocr_mode: str = "auto",
    start_from: Optional[str] = None,
    novelty_limit: int = 0,
    stages_done: Optional[Sequence[str]] = None,
    gap_runs: int = 1,
    min_run_hits: int = 0,
) -> Dict[str, Any]:
    """Jalankan tahap-tahap berurutan, merekam progres dan hasil detailnya.

    ``until`` menghentikan pipeline setelah tahap itu selesai (mis. ``"gap_mining"``
    untuk UI bertahap yang belum ingin memanggil OpenAlex); bawaan = semua tahap.
    ``start_from`` melanjutkan dari sebuah tahap memakai berkas keluaran tahap
    sebelumnya di ``out_dir`` — gap mining (LLM) tidak diulang sehingga gap yang
    sudah dilihat pengguna tetap sama. ``stages_done`` = tahap yang sudah selesai
    pada run sebelumnya, diakumulasi ke job. ``gap_runs`` > 1 mengulang gap mining
    dan menandai k/n kemunculan tiap gap (``min_run_hits`` 0 = ceil(2n/3)).
    """
    stage_keys = [s[0] for s in RESEARCH_STAGES]
    if until is not None and until not in stage_keys:
        raise ValueError(f"until harus salah satu dari {stage_keys}, bukan {until!r}")
    if start_from is not None and start_from not in stage_keys:
        raise ValueError(f"start_from harus salah satu dari {stage_keys}, bukan {start_from!r}")
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
            job_id, pdf_paths, paths["chunks"], embedder=embedder, ocr_mode=ocr_mode)),
        ("gap_mining", lambda: stage_gap_mining(
            job_id, paths["chunks"], paths["gaps"], limit=limit,
            runs=gap_runs, min_run_hits=min_run_hits)),
        ("novelty", lambda: stage_novelty(
            job_id, paths["gaps"], paths["novelty"], from_date=from_date, limit=novelty_limit)),
        ("recommendation", lambda: stage_recommendation(
            job_id, paths["novelty"], paths["chunks"], paths["rekomendasi"],
            embedder=embedder)),
    ]
    first = stage_keys.index(start_from) if start_from else 0
    last = stage_keys.index(until) + 1 if until else len(stage_keys)
    if first >= last:
        raise ValueError(f"start_from={start_from!r} berada setelah until={until!r}")
    stages = stages[first:last]
    if start_from:
        missing = [k for k in _STAGE_INPUTS[start_from] if not paths[k].exists()]
        if missing:
            raise FileNotFoundError(
                f"Tidak bisa melanjutkan dari {start_from}: berkas tahap sebelumnya hilang "
                f"({', '.join(paths[k].name for k in missing)})")

    update_job(job_id, status="running", progress=1.0,
               message=("Memulai pipeline penelitian" if not start_from
                        else f"Melanjutkan pipeline dari tahap {start_from}"))
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
        update_job(job_id, status="cancelled", progress=0,
                   message=f"Dibatalkan oleh pengguna saat tahap {phase}")
        raise
    except Exception as exc:
        logger.exception(f"tahap {phase} gagal")
        update_job(job_id, status="failed", error=f"{phase}: {exc}",
                   message=f"Gagal di tahap {phase}")
        raise

    done_message = ("Pipeline penelitian selesai" if until is None
                    else f"Selesai sampai tahap {until}")
    all_done = list(stages_done or []) + [s[0] for s in stages if s[0] not in (stages_done or [])]
    # Atomic with the cancel flag: a cancel that arrived during the last stage
    # must not be overwritten by "completed".
    if complete_job(job_id, message=done_message, stages_done=all_done) is None:
        update_job(job_id, status="cancelled", progress=0,
                   message=f"Dibatalkan oleh pengguna saat tahap {phase}")
        raise ResearchCancelled("Pipeline penelitian dibatalkan oleh pengguna")
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
    start_from = payload.get("start_from") or None
    # Saat melanjutkan, PDF asli tidak dibaca lagi; berkas chunk/gap-lah yang dipakai.
    if not start_from and (not pdf_paths or any(not p.exists() for p in pdf_paths)):
        raise FileNotFoundError("PDF masukan job penelitian ini sudah tidak tersedia")
    out_dir = payload.get("output_dir") or str(
        Path(get_config().data.processed_path) / "research" / job_id)
    try:
        run_research_pipeline(job_id, pdf_paths, Path(out_dir), embedder=_shared_embedder(),
                              until=payload.get("until") or None,
                              ocr_mode=payload.get("ocr_mode") or "auto",
                              start_from=start_from,
                              novelty_limit=int(payload.get("novelty_limit") or 0),
                              stages_done=job.get("stages_done") or [],
                              gap_runs=int(payload.get("gap_runs") or 1),
                              min_run_hits=int(payload.get("min_run_hits") or 0))
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
    "recommendation": [stage_recommendation, rank_proposals, build_themes,
                       _narration_seeds, _narrate_titles],
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
