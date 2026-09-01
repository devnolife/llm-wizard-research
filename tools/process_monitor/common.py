"""Helper & renderer bersama untuk semua halaman monitor Streamlit."""

from __future__ import annotations

from datetime import datetime

import requests
import streamlit as st

DEFAULT_API = "http://127.0.0.1:8001/api"
REFRESH_SECONDS = 2.5

# (phase_id, ikon, judul, deskripsi singkat)
STAGES = [
    ("ingestion", "📄", "Baca & Potong PDF",
     "Ekstraksi teks per file (ocrd text-layer / GPU OCR / pypdf) lalu dipotong menjadi chunk"),
    ("topics", "🧠", "Ekstraksi Topik",
     "LLM mengekstrak topik-topik utama dari isi paper"),
    ("paper_analysis", "🔍", "Analisis Paper",
     "Basis/kelompok paper, persamaan antar-paper, dan kekurangan (3 thread paralel)"),
    ("neuro_symbolic", "⚙️", "Neuro-Symbolic",
     "Koordinator Observe → Think → Act → Evaluate: ekstraksi fakta, deteksi indikator gap, Rule Engine"),
    ("summary", "📝", "Ringkasan",
     "Menyusun ringkasan penelitian dari topik utama"),
    ("gaps", "🕳️", "Synthesis Gap",
     "Finalisasi indikator gap: fragmentasi / inkonsistensi / ketidaklengkapan"),
    ("proposal", "💡", "Usulan Penelitian",
     "Usulan penelitian baru yang berlabuh pada indikator synthesis gap"),
    ("roadmap", "🗺️", "Peta Jalan",
     "Roadmap penelitian jangka pendek / menengah / panjang"),
]

METHOD_BADGES = {
    "ocrd_text_layer": "⚡ Text layer (ocrd)",
    "ocr": "🤖 GPU OCR (ocrd)",
    "pypdf": "📄 pypdf (fallback)",
}

JOB_STATUS_BADGES = {
    "queued": ("🕓", "Antre", "gray"),
    "running": ("🔄", "Berjalan", "blue"),
    "completed": ("✅", "Selesai", "green"),
    "failed": ("❌", "Gagal", "red"),
    "cancelled": ("🚫", "Dibatalkan", "orange"),
}

STATE_CHIPS = {
    "pending": ("⚪", "menunggu", "gray"),
    "running": ("🔵", "berjalan…", "blue"),
    "done": ("✅", "selesai", "green"),
    "fallback": ("⚠️", "fallback LLM", "orange"),
    "failed": ("❌", "terhenti (gagal)", "red"),
    "cancelled": ("🚫", "terhenti (dibatalkan)", "orange"),
}

STAGE_METRIC_LABELS = {
    "files_processed": "file diproses",
    "chunks": "chunk",
    "topics": "topik",
    "groups": "kelompok basis",
    "weaknesses": "paper dianalisis kekurangannya",
    "common_keywords": "kata kunci bersama",
    "indicators": "indikator gap",
    "facts": "fakta (SPO)",
    "mode": "mode eksekusi",
    "chars": "karakter",
    "gaps": "indikator gap final",
    "recommendations": "usulan",
    "phases": "fase roadmap",
}

GAP_TYPE_BADGES = {
    "FRAGMENTATION": "🧩 Fragmentasi",
    "INCONSISTENCY": "⚡ Inkonsistensi",
    "INCOMPLETENESS": "🕳️ Ketidaklengkapan",
    "SUPPORT_GAP": "🔍 Ketiadaan dukungan bukti",
}

_MONTHS_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
              "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


# ─────────────────────────────── API helpers ────────────────────────────────

def api_base() -> str:
    return st.session_state.get("api_base", DEFAULT_API).rstrip("/")


# Sentinel: request gagal (429/timeout/koneksi) — beda dari 404 (None = tidak ada).
_FETCH_FAILED = "__fetch_failed__"


def _get_json(path: str, params: dict | None = None, timeout: int = 15):
    try:
        r = requests.get(f"{api_base()}{path}", params=params, timeout=timeout)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        st.session_state["last_error"] = f"Gagal memanggil {path}: {exc}"
        return _FETCH_FAILED


def fetch_chunk_export(job_id: str, fmt: str = "jsonl") -> tuple[bytes | None, str | None]:
    """Ambil berkas ekspor chunk (PDF→chunk) sebagai bytes.

    Mengembalikan ``(data, pesan_error)``; tepat satu di antaranya terisi.
    Sengaja tidak lewat ``_get_json`` karena responsnya berkas biner besar
    (±2 MB) dan pesan galat dari backend perlu ditampilkan apa adanya.
    """
    try:
        r = requests.get(
            f"{api_base()}/analysis-status/{job_id}/chunks",
            params={"format": fmt},
            timeout=180,
        )
    except requests.RequestException as exc:
        return None, f"Gagal menghubungi backend: {exc}"
    if r.status_code != 200:
        try:
            return None, r.json().get("detail") or f"HTTP {r.status_code}"
        except ValueError:
            return None, f"HTTP {r.status_code}"
    return r.content, None


def fetch_status(job_id: str) -> dict | None:
    return _get_json(f"/analysis-status/{job_id}")


def fetch_events(job_id: str) -> dict | None:
    return _get_json(f"/analysis-status/{job_id}/events")


def fetch_artifacts(job_id: str) -> dict | None:
    return _get_json(f"/analysis-status/{job_id}/artifacts", timeout=30)


def fetch_system_stats() -> dict | None:
    return _get_json("/system-stats", timeout=20)


def fetch_jobs(limit: int = 30) -> list[dict]:
    data = _get_json("/analysis-jobs", params={"limit": limit})
    return data.get("jobs", []) if isinstance(data, dict) else []


def upload_and_analyze(files) -> str | None:
    payload = [("files", (f.name, f.getvalue(), "application/pdf")) for f in files]
    try:
        r = requests.post(f"{api_base()}/upload-and-analyze", files=payload, timeout=120)
        r.raise_for_status()
        return r.json().get("job_id")
    except requests.RequestException as exc:
        st.session_state["last_error"] = f"Unggah gagal: {exc}"
        return None


def delete_job(job_id: str) -> bool:
    """Hapus job (beserta hasil, event, artefak, dan file unggahannya)."""
    try:
        r = requests.delete(f"{api_base()}/analysis-jobs/{job_id}", timeout=30)
        r.raise_for_status()
        return True
    except requests.RequestException as exc:
        detail = ""
        resp = getattr(exc, "response", None)
        if resp is not None:
            try:
                detail = f" — {resp.json().get('detail', '')}"
            except ValueError:
                pass
        st.session_state["last_error"] = f"Hapus gagal: {exc}{detail}"
        return False


def reanalyze_job(job_id: str) -> str | None:
    """Analisis ulang job sebagai job BARU dari PDF tersimpannya.

    Hasil lama tetap ada (untuk perbandingan); job baru memakai engine LLM
    yang aktif sekarang. Mengembalikan job_id baru, atau None bila gagal.
    """
    try:
        r = requests.post(f"{api_base()}/analysis-jobs/{job_id}/reanalyze", timeout=60)
        r.raise_for_status()
        return r.json().get("job_id")
    except requests.RequestException as exc:
        detail = ""
        resp = getattr(exc, "response", None)
        if resp is not None:
            try:
                detail = f" — {resp.json().get('detail', '')}"
            except ValueError:
                pass
        st.session_state["last_error"] = f"Analisis ulang gagal: {exc}{detail}"
        return None


# ─────────────────────────── Event interpretation ───────────────────────────

def derive_stage_states(events: list[dict], job_status: str) -> dict[str, dict]:
    """Turunkan status tiap tahap dari deretan event (urut per event_id).

    Retry job menghasilkan event ganda — pemakaian event TERAKHIR per tahap
    membuat timeline mencerminkan percobaan terbaru.
    """
    stages: dict[str, dict] = {
        pid: {"state": "pending", "duration_ms": None, "data": {}, "started_at": None}
        for pid, *_ in STAGES
    }
    for ev in events:
        phase = ev.get("phase")
        etype = ev.get("type")
        if phase in stages:
            stage = stages[phase]
            if etype == "phase.started":
                stage.update(state="running", started_at=ev.get("created_at"),
                             duration_ms=None, data={})
            elif etype == "phase.completed":
                stage["state"] = "done"
                stage["duration_ms"] = ev.get("duration_ms")
                stage["data"] = ev.get("data") or {}
            elif etype == "phase.failed":
                stage["state"] = "fallback"
                stage["duration_ms"] = ev.get("duration_ms")
                stage["data"] = ev.get("data") or {}

    if job_status in ("failed", "cancelled"):
        for stage in stages.values():
            if stage["state"] == "running":
                stage["state"] = job_status
    return stages


def derive_file_rows(events: list[dict]) -> list[dict]:
    """Gabungkan event file.started/file.completed menjadi baris per file."""
    rows: dict[tuple, dict] = {}
    for ev in events:
        if ev.get("type") not in ("file.started", "file.completed"):
            continue
        data = ev.get("data") or {}
        key = (data.get("index"), data.get("file"))
        row = rows.setdefault(key, {
            "index": data.get("index"),
            "file": data.get("file", "?"),
            "of": data.get("of"),
            "state": "running",
            "method": None,
            "ocr_used": None,
            "chars": None,
            "chunks": None,
            "duration_ms": None,
        })
        if ev["type"] == "file.completed":
            row.update(
                state="done",
                method=data.get("extraction_method"),
                ocr_used=data.get("ocr_used"),
                chars=data.get("chars"),
                chunks=data.get("chunks"),
                duration_ms=ev.get("duration_ms"),
            )
    return [rows[k] for k in sorted(rows, key=lambda k: (k[0] or 0))]


def group_artifacts(artifacts: list[dict]) -> dict[str, dict]:
    """Kelompokkan artefak per tahap: {phase: {result, extraction[], llm[]}}.

    Untuk kind='result' dipakai artefak TERAKHIR (percobaan retry terbaru).
    """
    grouped: dict[str, dict] = {}
    for art in artifacts:
        bucket = grouped.setdefault(
            art["phase"], {"result": None, "extraction": [], "llm": []}
        )
        if art["kind"] == "result":
            bucket["result"] = art
        elif art["kind"] == "extraction":
            bucket["extraction"].append(art)
        elif art["kind"] == "llm":
            bucket["llm"].append(art)
    return grouped


def fmt_duration(ms) -> str:
    if ms is None:
        return "—"
    if ms < 1000:
        return f"{ms} ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f} dtk"
    return f"{int(seconds // 60)} mnt {seconds % 60:.0f} dtk"


def fmt_clock(epoch) -> str:
    if not epoch:
        return "—"
    return datetime.fromtimestamp(epoch).strftime("%H:%M:%S")


def fmt_datetime(epoch) -> str:
    if not epoch:
        return "—"
    dt = datetime.fromtimestamp(epoch)
    return f"{dt.day} {_MONTHS_ID[dt.month - 1]} · {dt.strftime('%H:%M')}"


def fmt_gb(mb) -> str:
    return f"{(mb or 0) / 1024:.1f} GB"


def md_bold(text) -> str:
    """Bold markdown yang aman: `**teks **` (spasi di tepi) gagal dirender
    CommonMark dan tampil sebagai tanda ** mentah — rapikan dulu."""
    cleaned = " ".join(str(text or "").split())
    return f"**{cleaned}**" if cleaned else ""


# ─────────────────────────── Render: server panel ───────────────────────────

def render_server_panel() -> None:
    """Isi panel pemakaian server (tanpa wadah luar — pemanggil yang memilih)."""
    stats = fetch_system_stats()
    if not isinstance(stats, dict):
        st.warning(
            "Statistik server sementara tidak tersedia "
            "(backend sibuk / tidak merespons — dicoba lagi otomatis)."
        )
        return
    st.caption(f"diperbarui {fmt_clock(stats.get('timestamp'))}")

    cpu, mem, disk = stats["cpu"], stats["memory"], stats["disk"]
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**CPU** — {cpu['percent']:.0f}% dari {cpu['cores']} core")
        st.progress(min(cpu["percent"], 100) / 100)
        st.caption(f"load avg 1/5/15 mnt: {cpu['load_avg'][0]} · {cpu['load_avg'][1]} · {cpu['load_avg'][2]}")
    with c2:
        st.markdown(f"**RAM** — {fmt_gb(mem['used_mb'])} / {fmt_gb(mem['total_mb'])} ({mem['percent']:.0f}%)")
        st.progress(min(mem["percent"], 100) / 100)
        swap = stats.get("swap", {})
        st.caption(f"swap: {fmt_gb(swap.get('used_mb', 0))} / {fmt_gb(swap.get('total_mb', 0))}")
    with c3:
        st.markdown(f"**Disk** — {disk['used_gb']} / {disk['total_gb']} GB ({disk['percent']:.0f}%)")
        st.progress(min(disk["percent"], 100) / 100)

    gpus = stats.get("gpus", [])
    if gpus:
        gpu_cols = st.columns(len(gpus))
        for col, gpu in zip(gpu_cols, gpus):
            with col:
                mem_pct = gpu["memory_used_mb"] / max(gpu["memory_total_mb"], 1)
                st.markdown(
                    f"**GPU {gpu['index']}** · {gpu['name']}  \n"
                    f"VRAM {fmt_gb(gpu['memory_used_mb'])} / {fmt_gb(gpu['memory_total_mb'])} "
                    f"· util {gpu['utilization_percent']}% · {gpu.get('temperature_c', '—')}°C"
                )
                st.progress(min(mem_pct, 1.0))
        all_procs = [
            {
                "GPU": gpu["index"],
                "PID": proc["pid"],
                "User": proc["user"],
                "Memori": fmt_gb(proc["memory_mb"]),
                "Proses": proc["name"],
            }
            for gpu in gpus
            for proc in gpu.get("processes", [])
        ]
        if all_procs:
            with st.popover(f"Proses di GPU ({len(all_procs)})"):
                st.dataframe(all_procs, width="stretch", hide_index=True)


# ─────────────────────── Render: hasil per tahap ────────────────────────────

def _render_extraction_results(extractions: list[dict]) -> None:
    tabs = st.tabs([art["label"] or f"File {i+1}" for i, art in enumerate(extractions)])
    for tab, art in zip(tabs, extractions):
        payload = art["payload"]
        with tab:
            badge = METHOD_BADGES.get(payload.get("extraction_method"), payload.get("extraction_method", "?"))
            st.markdown(
                f"{badge} · **{payload.get('chars', 0):,} karakter** → "
                f"**{payload.get('chunks', 0)} chunk**"
                + (f" · tahun {payload['year']}" if payload.get("year") else "")
            )
            if payload.get("title"):
                st.caption(f"Judul terdeteksi: {payload['title']}")
            st.markdown("**Teks hasil ekstraksi (awal dokumen):**")
            st.text_area(
                "preview", value=payload.get("preview", ""), height=220,
                key=f"preview_{art['id']}", label_visibility="collapsed", disabled=True,
            )
            samples = payload.get("sample_chunks") or []
            if samples:
                st.markdown("**Contoh potongan (chunk) yang masuk vector store:**")
                for chunk in samples:
                    section = f" · bagian: {chunk['section']}" if chunk.get("section") else ""
                    st.caption(f"Chunk #{chunk.get('chunk_index')}{section}")
                    st.code(chunk.get("text", ""), language=None, wrap_lines=True)


def _render_topics_result(payload: dict) -> None:
    topics = payload.get("topics") or []
    st.markdown("\n".join(f"- {topic}" for topic in topics) or "_(tidak ada topik)_")


def _first_weak_point(weak: dict) -> str:
    """First weakness point of a paper, for the summary table."""
    for kind in ("tersurat", "tersirat"):
        for p in weak.get(kind) or []:
            text = p.get("poin", "") if isinstance(p, dict) else str(p)
            text = " ".join(text.split())
            if text:
                return text[:110] + ("…" if len(text) > 110 else "")
    return "—"


def _render_weak_points(weak: dict) -> None:
    """Render tersurat/tersirat points of one paper with quotes and basis."""
    for kind_label, kind_key in (("Tersurat (ditulis penulis di jurnalnya)", "tersurat"),
                                 ("Tersirat (disimpulkan sistem dari isi)", "tersirat")):
        points = weak.get(kind_key) or []
        if points:
            st.markdown(f"*{kind_label}:*")
            for p in points:
                if isinstance(p, dict):
                    status = str(p.get("verification_status", "")).lower()
                    badge = "✅" if status == "terverifikasi" else ("⚠️" if status else "")
                    st.markdown(f"- {badge} {p.get('poin', '')}".strip())
                    if p.get("kutipan"):
                        st.caption(f"  Kutipan: “{p['kutipan']}”")
                    if p.get("dasar"):
                        st.caption(f"  Dasar: {p['dasar']}")
                else:
                    st.markdown(f"- {p}")
    if not (weak.get("tersurat") or weak.get("tersirat")):
        st.caption("_Tidak ada kekurangan terdeteksi untuk jurnal ini._")


def _render_paper_analysis_result(payload: dict, key: str = "stage") -> None:
    groups = payload.get("groups") or []
    similarity = payload.get("similarity") or {}
    weaknesses = payload.get("weaknesses") or []
    papers_info = payload.get("papers_info") or []

    if weaknesses:
        n_tersurat = sum(len(w.get("tersurat") or []) for w in weaknesses)
        n_tersirat = sum(len(w.get("tersirat") or []) for w in weaknesses)
        st.markdown("**Kekurangan / gap tiap jurnal:**")
        st.caption(
            f"{len(weaknesses)} jurnal dianalisis → **{n_tersurat} kekurangan tersurat** "
            f"(ditulis penulisnya, disertai kutipan) + **{n_tersirat} tersirat** "
            "(disimpulkan dari isi). Inilah bahan mentah yang disintesis menjadi "
            "gap kolektif di tab 🕳️ Gap Penelitian."
        )
        year_by_source = {
            p.get("source"): p.get("year") for p in papers_info if p.get("source")
        }
        rows = []
        for i, w in enumerate(weaknesses):
            row = {
                "No": i + 1,
                "Jurnal": w.get("title") or w.get("source") or f"Paper {i+1}",
                "Tersurat": len(w.get("tersurat") or []),
                "Tersirat": len(w.get("tersirat") or []),
                "Contoh kekurangan": _first_weak_point(w),
            }
            if year_by_source:
                row["Tahun"] = year_by_source.get(w.get("source"), "")
            rows.append(row)
        st.dataframe(rows, width="stretch", hide_index=True)

        def _fmt(idx: int) -> str:
            w = weaknesses[idx]
            title = w.get("title") or w.get("source") or f"Paper {idx+1}"
            return f"{idx+1}. {title[:80]}"

        sel = st.selectbox(
            "🔍 Buka detail kekurangan satu jurnal (kutipan + dasar dari teksnya)",
            options=list(range(len(weaknesses))),
            format_func=_fmt,
            key=f"weak_detail_{key}",
        )
        w = weaknesses[sel]
        with st.container(border=True):
            st.markdown(md_bold(w.get("title") or w.get("source") or f"Paper {sel+1}"))
            if w.get("source"):
                st.caption(f"📄 {w['source']}")
            _render_weak_points(w)

    if groups:
        st.markdown("**Basis / kelompok paper:**")
        st.dataframe(
            [{"Judul": g.get("title", ""), "Basis": g.get("basis", "")} for g in groups],
            width="stretch", hide_index=True,
        )
    if similarity.get("common_keywords") or similarity.get("shared_themes"):
        st.markdown("**Persamaan antar paper:**")
        if similarity.get("common_keywords"):
            st.markdown("Kata kunci bersama: " + " · ".join(f"`{k}`" for k in similarity["common_keywords"]))
        for theme in similarity.get("shared_themes", []):
            st.markdown(f"- {theme}")
        if similarity.get("summary"):
            st.caption(similarity["summary"])


def _render_neuro_symbolic_result(payload: dict) -> None:
    st.markdown(f"Mode eksekusi: `{payload.get('mode', '?')}`")
    stats = payload.get("fact_table_stats") or {}
    if stats:
        c1, c2, c3 = st.columns(3)
        c1.metric("Fakta (SPO)", stats.get("total_facts", 0))
        c2.metric("Entitas", stats.get("total_entities", 0))
        c3.metric("Indikator gap", len(payload.get("indicators") or []))
    facts = payload.get("sample_facts") or []
    if facts:
        st.markdown("**Sampel fakta Subjek–Predikat–Objek:**")
        st.dataframe(
            [
                {
                    "Subjek": f.get("subject", ""),
                    "Predikat": f.get("predicate", ""),
                    "Objek": f.get("object", ""),
                    "Keyakinan": f.get("confidence", 0),
                    "Sumber": f.get("source_paper", ""),
                }
                for f in facts
            ],
            width="stretch", hide_index=True,
        )
    indicators = payload.get("indicators") or []
    if indicators:
        st.markdown("**Indikator gap dari koordinator:**")
        for ind in indicators:
            badge = GAP_TYPE_BADGES.get(str(ind.get("type", ind.get("indicator_type", ""))).upper(), "")
            title = md_bold(ind.get("title"))
            desc = str(ind.get("description") or "").strip()
            parts = [p for p in (badge, title, desc if not title else f"— {desc}") if p]
            st.markdown("- " + " ".join(parts))
    report = payload.get("rule_engine_report") or {}
    if report:
        st.caption(
            f"Rule Engine: total {report.get('total', 0)} · lolos {report.get('passed', 0)} · "
            f"ditandai {report.get('flagged', 0)} · ditolak {report.get('rejected', 0)}"
        )
    trace = payload.get("reasoning_trace") or []
    if trace:
        with st.popover("Lihat reasoning trace"):
            st.json(trace)


def _render_summary_result(payload: dict) -> None:
    st.markdown(payload.get("summary") or "_(kosong)_")


_MILES_BASE = {
    "INCOMPLETENESS": ["Evidence gap"],
    "FRAGMENTATION": ["Theoretical gap"],
    "INCONSISTENCY": ["Contradictory-evidence gap", "Evidence gap"],
    "SUPPORT_GAP": ["Evidence gap", "Empirical gap"],
}

_MILES_KEYWORDS = [
    (("methodolog", "metodolog", "mixed-methods", "mixed methods"), "Methodological gap"),
    (("population", "populasi", "sample", "sampel", "demograf"), "Population gap"),
    (("theor", "framework", "kerangka", "integrat"), "Theoretical gap"),
    (("practic", "praktik", "practitioner", "adoption"), "Practical-knowledge gap"),
]


def _miles_lens(gap: dict) -> list[str]:
    """Label taksonomi gap (Miles 2017; Robinson 2011) sebagai lensa pelengkap.

    Pemetaan dasar dari tipe indikator + heuristik kata kunci pada deskripsi.
    INCONSISTENCY dipetakan ke contradictory-evidence gap (bukti saling
    bertentangan), bukan empirical gap. Ini label pembanding (presentasi),
    BUKAN metode deteksi gap.
    """
    text = " ".join(
        [str(gap.get("description") or "")]
        + [str(d) for d in (gap.get("suggested_directions") or [])]
    ).lower()
    labels = list(_MILES_BASE.get(str(gap.get("type", "")).upper(), []))
    for keys, label in _MILES_KEYWORDS:
        if label not in labels and any(k in text for k in keys):
            labels.append(label)
    return labels[:3]


def _gap_year_span(gap: dict, papers_info: list) -> tuple[int, int, int] | None:
    """(min, maks, median) tahun jurnal terkait gap; None bila tidak ada data."""

    def norm(t) -> str:
        return " ".join(str(t or "").split()).lower()

    year_map: dict[str, int] = {}
    for p in papers_info or []:
        try:
            year = int(p.get("year") or 0)
        except (TypeError, ValueError):
            continue
        if year <= 0:
            continue
        for k in (norm(p.get("source")), norm(p.get("title"))):
            if k:
                year_map[k] = year
    years = sorted(
        year_map[norm(r)]
        for r in (gap.get("related_papers") or [])
        if norm(r) in year_map
    )
    if not years:
        return None
    return years[0], years[-1], years[len(years) // 2]


def render_gap_confidence(gap: dict) -> None:
    """Keyakinan terkalibrasi, status abstain, dan rantai provenans satu gap.

    Menampilkan keyakinan mentah vs terkalibrasi agar pembaca tahu angka yang
    dipakai bukan skor mentah model, dan menandai gap yang sistem sendiri
    memilih untuk TIDAK klaim (needs_review) — bukan menyembunyikannya.
    """
    calib = gap.get("calibration") or {}
    raw = calib.get("raw_confidence")
    cal = gap.get("calibrated_confidence", calib.get("calibrated_confidence"))
    if cal is not None:
        try:
            bits = [f"terkalibrasi {float(cal):.0%}"]
            if raw is not None and abs(float(raw) - float(cal)) > 0.005:
                bits.append(f"mentah {float(raw):.0%}")
            temp = calib.get("temperature")
            if temp and abs(float(temp) - 1.0) > 1e-6:
                bits.append(f"T={float(temp):.2f}")
            elif calib.get("calibrator_fitted") is False:
                bits.append("belum ada label pakar (identitas)")
            st.caption("🎯 Keyakinan: " + " · ".join(bits))
        except (TypeError, ValueError):
            pass

    if gap.get("needs_review"):
        reasons = [str(r) for r in (gap.get("abstention_reasons") or []) if str(r).strip()]
        st.warning(
            "⚠️ **Sistem menahan klaim ini (perlu telaah manusia).** "
            + ("Alasan: " + "; ".join(reasons[:3]) if reasons else "")
        )

    prov = gap.get("provenance") or {}
    if prov:
        if prov.get("complete"):
            passages = prov.get("retrieved_passages") or []
            st.caption(
                f"🔗 Provenans lengkap: klaim → {len(prov.get('cited_records') or [])} jurnal "
                f"→ {len(passages)} kutipan → validasi {prov.get('validation_outcome') or '-'}"
                + (f" ({prov['validation_detail']})" if prov.get("validation_detail") else "")
            )
        else:
            st.caption(
                "🔗 Provenans belum lengkap — mata rantai hilang: "
                + ", ".join(prov.get("broken_links") or [])
            )


def _render_gap_lenses(gap: dict, papers_info: list) -> None:
    """Caption lensa pelengkap: taksonomi Miles + kemutakhiran basis literatur."""
    miles = _miles_lens(gap)
    if miles:
        st.caption(
            f"🔬 Lensa taksonomi (Miles 2017; Robinson 2011): {' · '.join(miles)} "
            "— label pembanding, bukan metode deteksi."
        )
    span = _gap_year_span(gap, papers_info)
    if span:
        lo, hi, med = span
        rng = f"{lo}–{hi}" if lo != hi else f"{lo}"
        note = ""
        if med <= datetime.now().year - 6:
            note = " — basis literatur mulai menua, pertimbangkan cek jurnal terbaru 🔎"
        st.caption(f"📅 Basis literatur gap ini: {rng} (median {med}){note}")


def _render_gaps_result(payload: dict) -> None:
    gaps = payload.get("gaps") or []
    papers_info = payload.get("papers_info") or []
    if not gaps:
        st.caption("_Tidak ada gap terdeteksi._")
        return
    st.caption(
        "Gap kolektif di bawah ini disintesis dari kekurangan tiap jurnal "
        "(lihat tab 📄 Gap per Jurnal) + analisis pola lintas-jurnal."
    )
    for i, gap in enumerate(gaps, start=1):
        badge = GAP_TYPE_BADGES.get(str(gap.get("type", "")).upper(), gap.get("type", ""))
        title = " ".join(str(gap.get("title") or "").split())
        head = f"{i}. {badge}" + (f" — {title}" if title else "")
        meta_bits = []
        if gap.get("rule_engine_verdict"):
            meta_bits.append(f"Rule Engine: {gap['rule_engine_verdict']}")
        try:
            conf = float(gap.get("confidence") or 0)
            if conf > 0:
                meta_bits.append(f"keyakinan {conf:.0%}")
        except (TypeError, ValueError):
            pass
        st.markdown(md_bold(head) + (" · " + " · ".join(meta_bits) if meta_bits else ""))
        st.markdown(gap.get("description", ""))
        render_gap_confidence(gap)
        _render_gap_lenses(gap, papers_info)

        related = [str(r).strip() for r in (gap.get("related_papers") or []) if str(r).strip()]
        if related:
            shown = related[:12]
            st.markdown("**Jurnal yang terlibat dalam gap ini:**")
            for ref in shown:
                st.markdown(f"- 📄 {ref}")
            if len(related) > len(shown):
                st.caption(f"…dan {len(related) - len(shown)} jurnal lainnya.")
        else:
            st.caption(
                "ℹ️ Jurnal terkait belum tercatat pada run ini — jalankan "
                "🔁 Analisis Ulang agar tiap gap menyebut jurnal sumbernya."
            )

        for ev in (gap.get("evidence") or [])[:5]:
            st.caption(f"🔎 Bukti: {ev}")
        directions = gap.get("suggested_directions") or []
        if directions:
            st.markdown("*Arah riset yang disarankan:*")
            for d in directions:
                st.markdown(f"- {d}")
        st.divider()


def render_gap_method_explainer() -> None:
    """Penjelas cara gap ditentukan + metode alternatif di literatur.

    Memakai st.expander — panggil hanya dari konteks halaman top-level
    (JANGAN dari RESULT_RENDERERS yang dirender di dalam expander tahap).
    """
    with st.expander("ℹ️ Bagaimana gap ditentukan? Apakah harus begini? (metode & alternatifnya)"):
        st.markdown(
            "**Metode inti yang diklaim proposal (BAB III Subbab 3.6):** deteksi "
            "**gap sintesis lintas-jurnal** memakai kerangka *synthesis gap* "
            "(Cooper, 1998; Booth, Sutton & Papaioannou, 2012; Paré dkk., 2015) "
            "dengan 4 indikator:\n"
            "- 🧩 **Fragmentasi** — klasterisasi embedding yang dilaporkan dengan "
            "*modularity* Q & *silhouette*, ditambah *link prediction* "
            "(Adamic-Adar/resource allocation) untuk mengusulkan jembatan konkret "
            "antar-klaster, serta isolasi sitasi di knowledge graph;\n"
            "- ⚡ **Inkonsistensi** — normalisasi klaim (arah, polaritas, PICO) + "
            "gerbang keselarasan variabel, lalu *adjudikasi* 4 kelas "
            "(kontradiksi / heterogenitas / beda konteks / bukan klaim) memakai "
            "uji Cochran's Q dan I²; NLI dipakai sebagai satu sinyal, bukan vonis;\n"
            "- 🕳️ **Ketidaklengkapan kolektif** — pencocokan aspek semantik "
            "(bukan sekadar sama-persis) + *evidence gap map* (matriks "
            "intervensi × luaran) yang menandai sel kosong dan sel tipis;\n"
            "- 🔍 **Ketiadaan dukungan bukti** — untuk tiap klaim dilakukan "
            "penelusuran *leave-one-out* ke seluruh korpus; klaim yang tidak "
            "menemukan paragraf bukti primer (atau hanya diulang lintas jurnal "
            "tanpa bukti baru — *citation echo*) ditandai sebagai gap. Berbeda "
            "dari ketidaklengkapan: di sini aspeknya **dibahas dan diklaim**, "
            "tetapi **tidak dibuktikan**.\n\n"
            "Gap jenis ini **hanya terlihat bila banyak jurnal dibaca bersama** — "
            "tidak bisa ditemukan dari satu jurnal.\n\n"
            "**Analisis pendukung per jurnal** (tahap *paper analysis*, tampil di "
            "tab 📄 Gap per Jurnal): kekurangan **tersurat** (pernyataan "
            "*limitations/future work* penulis, kutipan diverifikasi) dan "
            "**tersirat** (disimpulkan LLM). Sesuai proposal (BAB II Subbab 2.2.2), "
            "*explicit gap* seperti ini **bukan** klaim gap tesis — perannya "
            "sebagai bahan baku sintesis dan jejak penelusuran bagi pembaca."
        )
        st.markdown(
            "**Arti label pada tiap gap:**\n"
            "- **Rule Engine: PASS/FLAG/REJECT** — tiap kandidat gap dari LLM diuji "
            "9 aturan simbolik (kelayakan F1–F3, kausalitas C1–C3, konsistensi "
            "K1–K3) terhadap fakta SPO dari knowledge graph. Hanya yang lolos yang "
            "ditampilkan — ini lapisan *neuro-simbolik* yang mencegah halusinasi.\n"
            "- **🎯 Keyakinan terkalibrasi** — confidence mentah dari sinyal terukur "
            "(separasi klaster, cakupan aspek, adjudikasi klaim) di-*temperature "
            "scaling* lalu difusikan dengan verdict rule engine (PASS menguatkan, "
            "FLAG mendiskon, REJECT membatalkan). Sebelum ada label pakar, faktor "
            "skalanya identitas (T = 1) dan itu dinyatakan terbuka.\n"
            "- **⚠️ Perlu telaah manusia** — sistem sengaja **menahan klaim** "
            "(*selective abstention*) bila keyakinan di bawah ambang atau rantai "
            "provenans terputus. Menahan klaim lebih jujur daripada menebak.\n"
            "- **🔗 Provenans** — rantai klaim → jurnal terkutip → kutipan "
            "terambil → hasil validasi. Gap yang tak bisa ditelusuri ke kutipan "
            "otomatis ditandai perlu telaah.\n"
            "- Keluaran sistem adalah **indikator** gap (alat bantu keputusan), "
            "bukan vonis final — keputusan ilmiah tetap di tangan peneliti."
        )
        st.markdown("**Metode lain di literatur (pembanding):**")
        st.table(
            {
                "Metode": [
                    "Penambangan 'future work'/limitations",
                    "Taksonomi 7 jenis gap (Miles, 2017)",
                    "Framework systematic review (Robinson dkk., 2011)",
                    "Analisis bibliometrik / jaringan sitasi",
                    "Topic modeling (LDA/BERTopic)",
                    "Skor kebaruan semantik (jarak ke sentroid korpus)",
                ],
                "Cara kerja": [
                    "Ekstrak pernyataan gap eksplisit dari tiap paper",
                    "Klasifikasi gap: evidence, knowledge, practical, metodologi, empiris, teori, populasi",
                    "Karakterisasi gap dari hasil systematic review (mis. elemen PICOS)",
                    "Cari celah struktural dari pola sitasi/co-citation antar paper",
                    "Temukan kombinasi topik yang jarang diteliti dari distribusi topik",
                    "Anggap ide yang jauh dari literatur yang ada sebagai gap",
                ],
                "Posisi di sistem ini": [
                    "✅ Dipakai sebagai analisis pendukung ('kekurangan tersurat') — bukan diklaim sebagai gap (proposal: explicit gap ≠ synthesis gap)",
                    "✅ Dipakai sebagai lensa pelengkap — tiap gap diberi label Miles (bukan metode deteksi)",
                    "Sejiwa — sistem memfokuskan pada gap hasil sintesis lintas-jurnal",
                    "Sebagian dipakai: skor isolasi antar-paper di knowledge graph jadi sinyal fragmentasi",
                    "Serupa dengan lapisan topik & klaster embedding (sinyal fragmentasi)",
                    "⚠️ SENGAJA TIDAK dipakai sebagai indikator gap — proposal (BAB II Subbab 2.2.2) menyatakan kombinasi metode-domain yang belum pernah dicoba BUKAN synthesis gap. Hanya dipakai untuk mengurutkan prioritas usulan yang sudah berbasis gap.",
                ],
            }
        )
        st.markdown(
            "**Jembatan ke taksonomi gap (Miles 2017; Robinson 2011)** — tiap gap "
            "di atas otomatis diberi caption 🔬 *Lensa taksonomi* (pemetaan dari "
            "tipe indikator + kata kunci deskripsi): 🕳️ Ketidaklengkapan ≈ "
            "*evidence/methodological/population gap* · 🧩 Fragmentasi ≈ "
            "*theoretical gap* (integrasi kerangka) · ⚡ Inkonsistensi ≈ "
            "*contradictory-evidence gap* (temuan saling bertentangan) · "
            "🔍 Ketiadaan dukungan bukti ≈ *evidence/empirical gap* (klaim ada, "
            "bukti primernya tidak). Caption 📅 menunjukkan rentang tahun jurnal "
            "pendukung gap (kemutakhiran basis literatur)."
        )
        st.caption(
            "Mengapa tesis ini memilih kerangka synthesis gap + rule engine: "
            "pertanyaan penelitiannya adalah gap yang muncul dari MENYINTESIS "
            "puluhan jurnal sekaligus, dan tiap klaim gap harus bisa "
            "dipertanggungjawabkan ke penguji lewat fakta & kutipan terverifikasi."
        )


def render_novelty_badge(rec: dict) -> None:
    """Caption skor kebaruan usulan — sinyal PRIORITAS, bukan klaim gap.

    Ditegaskan di caption agar penguji tidak salah kira bahwa sistem memakai
    kebaruan sebagai definisi gap (BAB II Subbab 2.2.2 justru menolaknya).
    """
    nov = rec.get("novelty") or {}
    if not nov:
        return
    band_label = {
        "sweet_spot": "kebaruan sehat",
        "derivative": "mirip literatur yang ada",
        "off_topic": "jauh dari korpus",
    }.get(str(nov.get("band", "")), str(nov.get("band", "")))
    try:
        bits = [
            f"kebaruan {float(nov.get('novelty', 0)):.0%} ({band_label})",
            f"kelayakan eksekusi {float(nov.get('actionability', 0)):.0%}",
            f"skor prioritas {float(nov.get('priority_score', 0)):.2f}",
        ]
    except (TypeError, ValueError):
        return
    st.caption("📈 " + " · ".join(bits) + " — sinyal pengurut prioritas, bukan dasar klaim gap.")
    notes = [str(n) for n in (nov.get("notes") or []) if str(n).strip()]
    if notes:
        st.caption("   ↳ " + "; ".join(notes[:2]))


_INDICATOR_LABELS = {
    "FRAGMENTATION": "Fragmentasi",
    "INCONSISTENCY": "Inkonsistensi",
    "INCOMPLETENESS": "Ketidaklengkapan",
    "SUPPORT_GAP": "Ketiadaan Dukungan Bukti",
}


def render_method_layer_status(results: dict) -> None:
    """Status lapisan metode untuk SATU run: 4 indikator, kalibrasi, provenans,
    abstensi, kebaruan.

    Sinyal-sinyal ini sudah tampil per kartu gap/usulan, tetapi tersebar. Panel
    ini mengumpulkannya di satu tempat supaya pembaca (dan penguji) langsung
    melihat metode apa yang dipakai beserta hasilnya pada run ini.
    """
    gaps = results.get("gaps") or []
    recs = results.get("recommendations") or []
    if not gaps and not recs:
        return

    total = len(gaps)
    prov_known = [g for g in gaps if g.get("provenance")]
    prov_complete = sum(1 for g in prov_known if (g.get("provenance") or {}).get("complete"))
    held = sum(1 for g in gaps if g.get("needs_review"))
    calib = next((g.get("calibration") for g in gaps if g.get("calibration")), None)

    st.markdown("#### 🧪 Status Lapisan Metode (run ini)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🕳️ Indikator lolos", total)
    c2.metric(
        "🔗 Provenans lengkap",
        f"{prov_complete}/{total}" if prov_known else "—",
        help="Klaim → jurnal terkutip → kutipan verbatim → hasil validasi.",
    )
    c3.metric(
        "🛑 Ditahan (abstain)",
        f"{held}/{total}" if prov_known else "—",
        help="Indikator yang sistem pilih untuk TIDAK diklaim tanpa telaah manusia.",
    )
    if calib:
        temp = calib.get("temperature")
        fitted = calib.get("calibrator_fitted")
        c4.metric(
            "🎯 Kalibrasi",
            f"T={float(temp):.2f}" if temp is not None else "—",
            help="Temperature scaling. T=1,00 berarti kalibrator masih identitas.",
        )
        if not fitted:
            st.caption(
                f"⚠️ Kalibrator belum dilatih ({calib.get('calibration_labels', 0)} label pakar) — "
                "angka terkalibrasi berasal dari penyesuaian Rule Engine, bukan temperature "
                "scaling terlatih. ECE/Brier sengaja belum dilaporkan."
            )
    else:
        c4.metric("🎯 Kalibrasi", "—")

    counts: dict[str, int] = {}
    for g in gaps:
        key = str(g.get("type") or "").upper()
        counts[key] = counts.get(key, 0) + 1
    if counts:
        bits = [
            f"{_INDICATOR_LABELS.get(k, k)}: {v}"
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
        ]
        absent = [
            _INDICATOR_LABELS[k] for k in _INDICATOR_LABELS if k not in counts
        ]
        line = "🔬 Indikator terdeteksi — " + " · ".join(bits)
        if absent:
            line += f" · tidak terdeteksi: {', '.join(absent)}"
        st.caption(line)

    novs = [r.get("novelty") for r in recs if r.get("novelty")]
    if novs:
        try:
            vals = [float(n.get("novelty", 0)) for n in novs]
            bands: dict[str, int] = {}
            for n in novs:
                b = str(n.get("band") or "?")
                bands[b] = bands.get(b, 0) + 1
            band_label = {
                "sweet_spot": "kebaruan sehat",
                "derivative": "mirip literatur ada",
                "off_topic": "jauh dari korpus",
            }
            band_bits = ", ".join(
                f"{v} {band_label.get(k, k)}" for k, v in bands.items()
            )
            st.caption(
                f"📈 Kebaruan {len(novs)} usulan: {min(vals):.0%}–{max(vals):.0%} "
                f"({band_bits}) — mengurutkan prioritas, bukan mendefinisikan gap."
            )
        except (TypeError, ValueError):
            pass
    elif recs:
        st.caption(
            "📈 Skor kebaruan belum tersedia pada run ini — jalankan 🔁 Analisis Ulang "
            "agar usulan mendapat skor prioritas."
        )

    if not prov_known:
        st.caption(
            "ℹ️ Run ini dibuat sebelum lapisan kalibrasi/provenans ditambahkan. "
            "Jalankan 🔁 Analisis Ulang untuk mendapatkan sinyal lengkap."
        )


def _render_proposal_result(payload: dict) -> None:
    gaps = payload.get("gaps") or []
    for i, rec in enumerate(payload.get("recommendations") or [], start=1):
        gap_type = str(rec.get("gap_type", "")).upper()
        badge = GAP_TYPE_BADGES.get(gap_type, rec.get("gap_type", ""))
        head = md_bold(f"{i}. {rec.get('title') or '(tanpa judul)'}")
        st.markdown(f"{head} {badge}".strip())
        if rec.get("description"):
            st.markdown(rec["description"])
        matched = [
            g for g in gaps
            if str(g.get("type", "")).upper() == gap_type
        ]
        if matched:
            refs = "; ".join(
                " ".join(str(g.get("title") or g.get("description") or "").split())[:110]
                for g in matched[:2]
            )
            st.caption(f"🕳️ Menjawab gap: {refs}")
        if rec.get("why"):
            st.caption(f"Mengapa: {rec['why']}")
        if rec.get("how"):
            st.caption(f"Metode: {rec['how']}")
        render_novelty_badge(rec)
        st.divider()
    refs = payload.get("related_paper_refs") or []
    if refs:
        st.markdown("**Rujukan paper terkait (dari koordinator):**")
        for ref in refs:
            st.markdown(f"- {ref.get('title', '')} — {ref.get('reason', '')}")


def _render_roadmap_result(payload: dict) -> None:
    for phase in payload.get("roadmap") or []:
        head = md_bold(phase.get("phase"))
        if head:
            st.markdown(head)
        for item in phase.get("items", []):
            st.markdown(f"- {item}")


RESULT_RENDERERS = {
    "topics": _render_topics_result,
    "paper_analysis": _render_paper_analysis_result,
    "neuro_symbolic": _render_neuro_symbolic_result,
    "summary": _render_summary_result,
    "gaps": _render_gaps_result,
    "proposal": _render_proposal_result,
    "roadmap": _render_roadmap_result,
}


def _render_llm_traces(traces: list[dict]) -> None:
    for art in traces:
        payload = art["payload"]
        st.markdown(md_bold(art["label"] or "Panggilan LLM"))
        meta = []
        if payload.get("model"):
            meta.append(f"model `{payload['model']}`")
        params = payload.get("params") or {}
        if params:
            meta.append(" · ".join(f"{k}={v}" for k, v in params.items()))
        if meta:
            st.caption(" · ".join(meta))
        prompt_tab, response_tab = st.tabs(["📤 Prompt", "📥 Jawaban mentah"])
        with prompt_tab:
            st.code(payload.get("prompt", ""), language=None, wrap_lines=True)
        with response_tab:
            st.code(payload.get("response", ""), language=None, wrap_lines=True)


# ─────────────────────── Render: knowledge graph ────────────────────────────

CLUSTER_PALETTE = [
    "#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2",
    "#eeca3b", "#b279a2", "#ff9da6", "#9d755d", "#bab0ac",
]
NODE_TYPE_ICONS = {
    "PAPER": "📄", "METHOD": "🛠️", "CONCEPT": "💡", "DOMAIN": "🌐",
    "METRIC": "📏", "DATASET": "🗃️", "TOOL": "🔧", "PROBLEM": "❗",
}


@st.cache_data(ttl=300, show_spinner=False)
def fetch_graph(base: str, job_id: str, max_nodes: int) -> dict | None:
    try:
        r = requests.get(
            f"{base}/graph",
            params={"job_id": job_id, "max_nodes": max_nodes},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def _build_graph_html(nodes: list, links: list) -> str:
    from pyvis.network import Network

    net = Network(
        height="640px", width="100%", bgcolor="#0e1117", font_color="#fafafa",
        directed=False, notebook=False, cdn_resources="in_line",
    )
    for n in nodes:
        cluster = int(n.get("cluster", 0))
        ntype = str(n.get("type", "CONCEPT"))
        weight = int(n.get("weight", 1))
        icon = NODE_TYPE_ICONS.get(ntype, "")
        label = str(n.get("label", n["id"]))
        net.add_node(
            n["id"],
            label=f"{icon} {label[:38]}".strip(),
            title=(
                f"<b>{label}</b><br>Tipe: {ntype}"
                f"<br>Klaster: {cluster + 1}<br>Koneksi: {weight}"
            ),
            color=CLUSTER_PALETTE[cluster % len(CLUSTER_PALETTE)],
            size=14 + min(weight, 12) * 3,
        )
    for l in links:
        preds = ", ".join(l.get("predicates", [])) or "terkait"
        net.add_edge(
            l["source"], l["target"],
            width=1 + min(int(l.get("weight", 1)), 6),
            title=f"{preds} · conf {float(l.get('confidence', 0)):.2f}",
            color={"color": "#5c6370", "highlight": "#fafafa"},
        )
    net.set_options("""{
      "physics": {
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
          "gravitationalConstant": -80,
          "springLength": 130,
          "avoidOverlap": 0.5
        },
        "stabilization": {"iterations": 180}
      },
      "interaction": {"hover": true, "tooltipDelay": 120, "navigationButtons": true},
      "edges": {"smooth": {"enabled": true, "type": "continuous", "roundness": 0.4}},
      "nodes": {"font": {"color": "#fafafa", "size": 15}, "borderWidth": 2}
    }""")
    return net.generate_html()


def render_knowledge_graph(job_id: str) -> None:
    st.subheader("🕸️ Knowledge Graph — Fakta SPO")
    st.caption(
        "Jaringan subjek–predikat–objek hasil tahap Neuro-Symbolic. "
        "Warna = klaster komunitas, ukuran = jumlah koneksi. "
        "Node bisa digeser; scroll untuk zoom, arahkan kursor untuk detail."
    )
    max_nodes = st.slider(
        "Maksimal node ditampilkan", 20, 500, 150, 10, key="graph_max_nodes"
    )
    graph = fetch_graph(api_base(), job_id, max_nodes)
    if graph is None:
        st.warning("Gagal memuat graph dari backend — coba refresh halaman.")
        return
    nodes, links = graph.get("nodes", []), graph.get("links", [])
    if not nodes:
        st.info("Belum ada fakta SPO untuk job ini (graph kosong).")
        return

    stats = graph.get("stats", {})
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Node", stats.get("nodes", len(nodes)))
    m2.metric("Relasi", stats.get("links", len(links)))
    m3.metric("Fakta SPO", stats.get("facts", "—"))
    m4.metric("Klaster", stats.get("clusters", len(graph.get("clusters", []))))

    try:
        html = _build_graph_html(nodes, links)
    except ImportError:
        st.warning(
            "Paket `pyvis` belum terpasang di venv monitor — jalankan "
            "`tools/process_monitor/.venv/bin/pip install pyvis`."
        )
        return
    st.iframe(html, height=660)

    clusters = graph.get("clusters", [])
    if clusters:
        chips = []
        for c in clusters:
            color = CLUSTER_PALETTE[int(c.get("id", 0)) % len(CLUSTER_PALETTE)]
            terms = ", ".join(c.get("top_terms", [])[:3])
            chips.append(
                f'<span style="display:inline-block;margin:2px 6px 2px 0;'
                f'padding:2px 10px;border-radius:12px;background:{color};'
                f'color:#0e1117;font-size:0.8rem;font-weight:600;">'
                f'Klaster {int(c.get("id", 0)) + 1} · {c.get("size", "?")} node — {terms}</span>'
            )
        st.markdown(" ".join(chips), unsafe_allow_html=True)
    types_present = sorted({str(n.get("type", "CONCEPT")) for n in nodes})
    st.caption("Tipe node: " + " · ".join(
        f"{NODE_TYPE_ICONS.get(t, '•')} {t}" for t in types_present
    ))
