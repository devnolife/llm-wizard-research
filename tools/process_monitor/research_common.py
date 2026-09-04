"""Helper bersama untuk halaman alur penelitian (pipeline TAHAP 1-3).

Terpisah dari ``common.py`` yang melayani pipeline lama 8 tahap. Keempat halaman
tahap memakai satu perender yang sama karena bentuk artefaknya seragam:
``params`` / ``metrics`` / ``samples`` / ``outputs`` / ``notes``.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import requests
import streamlit as st

from common import api_base, fetch_artifacts, fetch_events, fmt_duration
from research_vocab import ENUM_LABELS, enum_help, enum_label, help_of, label

# Dipakai bila backend tak terjangkau; kunci harus sama dengan RESEARCH_STAGES.
FALLBACK_STAGES = [
    {"key": "chunking", "icon": "📄", "title": "Ekstraksi & Chunking",
     "description": "PDF dibersihkan, seksi dikenali, dipotong per kalimat"},
    {"key": "gap_mining", "icon": "🕳️", "title": "Penambangan Gap",
     "description": "Kandidat disaring, LLM mengekstrak gap, diverifikasi verbatim"},
    {"key": "novelty", "icon": "🔭", "title": "Verifikasi Kebaruan",
     "description": "Tiap gap dicek ke literatur 2024+ lewat OpenAlex"},
    {"key": "recommendation", "icon": "🎯", "title": "Rekomendasi Topik",
     "description": "Gap open diperingkat lalu dikelompokkan jadi tema"},
]

STATE_LABEL = {
    "done": ("✅", "selesai"),
    "running": ("⏳", "berjalan"),
    "failed": ("❌", "gagal"),
    "cancelled": ("🚫", "dibatalkan"),
    "pending": ("⚪", "menunggu"),
}

SEMUA = "— semua —"

# Kolom yang dijadikan dropdown filter; harus sama dengan PHASE_FACETS di backend.
PHASE_FACETS = {
    "chunking": ("source", "section_normalized", "extraction_quality"),
    "gap_mining": ("source", "gap_type", "topic"),
    "novelty": ("source", "novelty_status", "gap_type", "topic"),
    "recommendation": ("source", "topic", "band", "theme_id"),
}

# Judul ringkas tiap record supaya expander bisa dipindai tanpa dibuka.
RECORD_TITLE = {
    "chunking": lambda r: (f"#{r.get('chunk_index')} · {r.get('section_normalized')} · "
                           f"{r.get('token_count')} token · {r.get('source')}"),
    "gap_mining": lambda r: (f"{r.get('gap_type')} · grounding {r.get('grounding_score')} · "
                             f"{r.get('source')}"),
    "novelty": lambda r: (f"{r.get('novelty_status')} · {r.get('gap_type')} · "
                          f"{r.get('source')}"),
    "recommendation": lambda r: (f"#{r.get('rank')} · skor {r.get('priority_score')} · "
                                 f"tema {r.get('theme_id')} · {r.get('source')}"),
}

# Teks panjang ditampilkan sebagai blok, bukan sel tabel yang terpotong.
LONG_FIELDS = {"text", "gap_statement", "gap_paraphrase", "description", "title",
               "paper_title", "label", "theme_label", "novelty_query"}


@st.cache_data(ttl=300)
def fetch_stages() -> list[dict]:
    try:
        resp = requests.get(f"{api_base()}/research/stages", timeout=10)
        resp.raise_for_status()
        return resp.json().get("stages") or FALLBACK_STAGES
    except Exception:
        return FALLBACK_STAGES


def start_research(files) -> str | None:
    """Unggah PDF dan mulai pipeline penelitian; kembalikan job_id."""
    try:
        payload = [("files", (f.name, f.getvalue(), "application/pdf")) for f in files]
        resp = requests.post(f"{api_base()}/research/start", files=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("job_id")
    except Exception as exc:
        st.session_state["last_error"] = f"Gagal memulai pipeline: {exc}"
        return None


def research_jobs(limit: int = 30) -> list[dict]:
    """Hanya job pipeline penelitian; job lama 8 tahap disaring keluar."""
    try:
        resp = requests.get(f"{api_base()}/analysis-jobs", params={"limit": limit}, timeout=15)
        resp.raise_for_status()
        return [j for j in resp.json().get("jobs", []) if j.get("pipeline") == "research"]
    except Exception:
        return []


def job_events(job_id: str) -> list[dict]:
    """Semua event job; [] bila backend sedang tak terjangkau (bukan sentinel str)."""
    payload = fetch_events(job_id)
    return (payload.get("events") or []) if isinstance(payload, dict) else []


def stage_states(job_id: str, events: list[dict] | None = None) -> dict[str, dict]:
    """Status tiap tahap diturunkan dari event phase.* milik job.

    ``events`` boleh diberikan agar pemanggil yang sudah mengambilnya (fragment
    live) tidak memanggil backend dua kali.
    """
    if events is None:
        events = job_events(job_id)
    states: dict[str, dict] = {}
    for ev in events:
        phase, kind = ev.get("phase"), ev.get("type")
        if not phase or not str(kind).startswith("phase."):
            continue
        entry = states.setdefault(phase, {"state": "pending", "duration_ms": None})
        if kind == "phase.started":
            entry["state"] = "running"
        elif kind == "phase.completed":
            entry["state"] = "done"
            entry["duration_ms"] = ev.get("duration_ms")
            entry["metrics"] = ev.get("data") or {}
        elif kind == "phase.failed":
            entry["state"] = "failed"
            entry["error"] = (ev.get("data") or {}).get("error")
        elif kind == "phase.cancelled":
            entry["state"] = "cancelled"
            entry["duration_ms"] = ev.get("duration_ms")
    return states


def substep_states(events: list[dict], phase: str) -> dict[str, dict]:
    """Status sub-langkah satu tahap dari event substep.*: pending/running/done/error
    beserta angka masuk/keluar/dibuang yang dicatat backend."""
    states: dict[str, dict] = {}
    for ev in events:
        if ev.get("phase") != phase or not str(ev.get("type")).startswith("substep."):
            continue
        data = ev.get("data") or {}
        key = data.get("substep")
        if not key:
            continue
        entry = states.setdefault(key, {"state": "pending"})
        entry.update({k: v for k, v in data.items() if k != "substep"})
        if ev["type"] == "substep.started":
            entry["state"] = "running"
            entry["started_at"] = ev.get("created_at")
        elif ev["type"] == "substep.completed":
            entry["state"] = "error" if data.get("error") else "done"
            entry["duration_ms"] = ev.get("duration_ms")
    return states


def stage_artifacts(job_id: str, phase: str) -> dict[str, list[dict]]:
    """Artefak satu tahap, dikelompokkan per jenis."""
    payload = fetch_artifacts(job_id) or {}
    grouped: dict[str, list[dict]] = {"result": [], "extraction": [], "llm": []}
    for art in payload.get("artifacts") or []:
        if art.get("phase") == phase:
            grouped.setdefault(art.get("kind", "result"), []).append(art)
    return grouped


def fetch_records(job_id: str, phase: str, q: str = "", filters: dict | None = None,
                  offset: int = 0, limit: int = 25) -> dict:
    """Data lengkap satu tahap, dibaca dari berkas keluaran (bukan 8 sampel)."""
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if q:
        params["q"] = q
    for key, value in (filters or {}).items():
        if value and value != SEMUA:
            params[key] = value
    try:
        resp = requests.get(f"{api_base()}/research/{job_id}/records/{phase}",
                            params=params, timeout=60)
        if resp.status_code == 404:
            return {"error": resp.json().get("detail", "tidak ditemukan")}
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"error": str(exc)}


@st.cache_data(ttl=120, show_spinner="Memuat data lengkap…")
def fetch_all_records(job_id: str, collection: str, max_rows: int = 5000) -> list[dict]:
    """Seluruh record satu koleksi (dipaginasi 500), untuk tabel silang & grafik.

    Kosong bila koleksi tidak ada pada job ini (job lama) — pemanggil yang
    memutuskan apakah itu perlu dijelaskan ke pengguna.
    """
    rows: list[dict] = []
    offset = 0
    while offset < max_rows:
        page = fetch_records(job_id, collection, offset=offset, limit=500)
        if page.get("error"):
            break
        batch = page.get("records") or []
        rows.extend(batch)
        offset += len(batch)
        if len(batch) < 500 or offset >= page.get("total", 0):
            break
    return rows


def collection_available(job_id: str, collection: str) -> bool:
    """True bila job ini menulis berkas koleksi tersebut (bukan job lama)."""
    return not fetch_records(job_id, collection, limit=1).get("error")


@st.cache_data(ttl=60)
def fetch_stage_source(stage_key: str) -> dict:
    try:
        resp = requests.get(f"{api_base()}/research/stages/{stage_key}/source", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"error": str(exc)}


def fetch_fulltext(job_id: str, source: str = "") -> dict:
    try:
        resp = requests.get(f"{api_base()}/research/{job_id}/fulltext",
                            params={"source": source} if source else None, timeout=60)
        if resp.status_code == 404:
            return {"error": resp.json().get("detail", "tidak ditemukan")}
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"error": str(exc)}


def set_active_job(job_id: str) -> None:
    """Simpan job aktif di session sekaligus URL.

    Tanpa query param, membuka halaman tahap lewat tautan langsung atau menekan
    refresh akan kehilangan job yang sedang dilihat.
    """
    st.session_state["research_job_id"] = job_id
    st.query_params["job"] = job_id


def require_job() -> str | None:
    """Ambil job aktif dari session atau URL; beri petunjuk bila belum ada."""
    job_id = st.session_state.get("research_job_id") or st.query_params.get("job", "")
    if job_id:
        st.session_state["research_job_id"] = job_id
        return job_id
    st.info("Belum ada analisis dipilih. Buka **🚀 Mulai Analisis** untuk "
            "mengunggah PDF atau memilih job yang sudah ada.")
    return None


def render_timeline(job_id: str) -> None:
    """Rangkuman keempat tahap sebagai satu baris status."""
    states = stage_states(job_id)
    cols = st.columns(len(fetch_stages()))
    for col, stage in zip(cols, fetch_stages()):
        info = states.get(stage["key"], {})
        icon, label = STATE_LABEL.get(info.get("state", "pending"), ("⚪", "menunggu"))
        with col:
            st.markdown(f"**{stage['icon']} {stage['title']}**")
            dur = fmt_duration(info.get("duration_ms")) if info.get("duration_ms") else "—"
            st.caption(f"{icon} {label} · {dur}")


def _render_table(rows: list[dict], caption: str = "") -> None:
    if not rows:
        return
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    if caption:
        st.caption(caption)


def _render_metrics(metrics: dict[str, Any]) -> None:
    scalars = {k: v for k, v in metrics.items() if not isinstance(v, (dict, list))}
    items = list(scalars.items())
    for start in range(0, len(items), 4):
        for col, (key, value) in zip(st.columns(4), items[start:start + 4]):
            col.metric(label(key), value, help=help_of(key))
    for key, value in metrics.items():
        if isinstance(value, dict) and value:
            st.caption(label(key))
            _render_table([{"kunci": k, "jumlah": v} for k, v in value.items()])


def _display_value(field: str, value: Any) -> str:
    if field in ENUM_LABELS:
        return enum_label(field, value)
    return str(value)


def _render_record(rec: dict) -> None:
    """Satu record: teks panjang sebagai blok, sisanya sebagai tabel."""
    longs = {k: v for k, v in rec.items()
             if k in LONG_FIELDS and isinstance(v, str) and v.strip()}
    shorts = {k: v for k, v in rec.items()
              if k not in longs and k != "record" and not isinstance(v, (dict, list))}
    nested = {k: v for k, v in rec.items() if isinstance(v, (dict, list)) and v}

    for field, value in longs.items():
        st.caption(label(field), help=help_of(field))
        st.markdown(f"> {value}".replace("\n", "\n> "))
    if shorts:
        rows = []
        for k, v in shorts.items():
            note = enum_help(k, v) if k in ENUM_LABELS else (help_of(k) or "")
            rows.append({"kolom": label(k), "nilai": _display_value(k, v), "arti": note})
        _render_table(rows)
    for field, value in nested.items():
        with st.expander(f"{label(field)} ({len(value)})", expanded=False):
            st.json(value)


def render_records_tab(job_id: str, phase: str, trace=None) -> None:
    """Semua record tahap ini, bisa dicari dan difilter — bukan 8 sampel.

    ``trace(rec, phase, job_id)`` opsional: bagian jejak di bawah tiap record
    (chunk sumber, putusan kebaruan, rincian skor) — disuplai research_flow
    agar modul ini tidak mengimpornya balik.
    """
    probe = fetch_records(job_id, phase, limit=1)
    if probe.get("error"):
        st.warning(probe["error"])
        return

    facets = probe.get("facets") or {}
    cols = st.columns(len(PHASE_FACETS.get(phase, ())) + 1)
    query = cols[0].text_input("🔎 Cari teks", key=f"q_{phase}",
                               placeholder="cari di seluruh isi record")
    filters: dict[str, str] = {}
    for col, field in zip(cols[1:], PHASE_FACETS.get(phase, ())):
        options = [SEMUA] + facets.get(field, [])
        filters[field] = col.selectbox(
            label(field), options, key=f"f_{phase}_{field}",
            format_func=lambda v, f=field: v if v == SEMUA else _display_value(f, v))

    per_page = st.select_slider("Baris per halaman", [10, 25, 50, 100], value=25,
                                key=f"pp_{phase}")
    head = fetch_records(job_id, phase, query, filters, 0, 1)
    matched = head.get("filtered", 0)
    total = head.get("total", 0)
    if not matched:
        st.info(f"Tidak ada record yang cocok (total tersedia: {total}).")
        return

    pages = max(1, -(-matched // per_page))
    page = st.number_input(f"Halaman (dari {pages})", 1, pages, 1, key=f"pg_{phase}")
    data = fetch_records(job_id, phase, query, filters, (page - 1) * per_page, per_page)
    records = data.get("records") or []

    st.caption(f"Menampilkan **{len(records)}** dari **{matched}** cocok · "
               f"total tahap ini **{total}** record")
    titler = RECORD_TITLE.get(phase, lambda r: str(r)[:80])
    for rec in records:
        with st.expander(titler(rec), expanded=False):
            _render_record(rec)
            if trace is not None:
                trace(rec, phase, job_id)

    # Dua langkah: mengambil 500 record pada setiap rerun hanya untuk mengisi
    # tombol unduh terlalu boros, padahal jarang dipakai.
    dl_key = f"dl_{phase}_{job_id[:8]}_{query}_{sorted(filters.items())}"
    if st.button("⬇️ Siapkan unduhan hasil filter (JSON, maks 500)", key=f"prep_{phase}"):
        st.session_state[dl_key] = json.dumps(
            fetch_records(job_id, phase, query, filters, 0, 500).get("records", []),
            ensure_ascii=False, indent=2)
    if dl_key in st.session_state:
        st.download_button("💾 Unduh sekarang", st.session_state[dl_key],
                           file_name=f"{phase}_{job_id[:8]}.json", mime="application/json",
                           key=f"dl_{phase}")


def render_source_tab(stage_key: str, substeps: list[dict] | None = None) -> None:
    """Kode Python yang benar-benar dieksekusi tahap ini."""
    data = fetch_stage_source(stage_key)
    if data.get("error"):
        st.warning(f"Kode sumber tak terbaca: {data['error']}")
        return
    functions = data.get("functions") or []
    if substeps:
        st.markdown("**Sub-langkah → fungsi yang menjalankannya**")
        _render_table([{"sub-langkah": s["label"], "implementasi": s["label_teknis"]}
                       for s in substeps])
    st.caption("Diambil langsung dari modul yang berjalan lewat `inspect`, "
               "jadi selalu sama dengan kode yang dieksekusi.")
    for fn in functions:
        st.markdown(f"**`{fn['name']}()`** — [{fn['file']}]({fn['file']}) "
                    f"baris {fn['line_start']}–{fn['line_end']}")
        if fn.get("doc"):
            st.caption(fn["doc"].split("\n\n")[0])
        st.code(fn["source"], language="python")


def stage_result_payload(job_id: str, stage_key: str) -> tuple[dict, dict]:
    """(artefak per jenis, payload result terakhir) satu tahap."""
    arts = stage_artifacts(job_id, stage_key)
    results = arts.get("result") or []
    payload = (results[-1].get("payload") or {}) if results else {}
    return arts, payload


def render_stage_extras(arts: dict, payload: dict) -> None:
    """Parameter, rincian per berkas, jejak LLM, catatan, dan berkas keluaran."""
    if payload.get("params"):
        with st.expander("⚙️ Parameter run ini", expanded=False):
            _render_table([{"parameter": k, "nilai": str(v)}
                           for k, v in payload["params"].items()])

    if arts.get("extraction"):
        with st.expander(f"📄 Rincian per berkas ({len(arts['extraction'])})", expanded=False):
            for art in arts["extraction"]:
                p = art.get("payload") or {}
                samples = p.get("sample_chunks") or []
                st.markdown(f"**{p.get('file')}** · {p.get('chunks')} chunk · "
                            f"{p.get('pages')} halaman · kualitas "
                            f"{enum_label('extraction_quality', p.get('extraction_quality'))}")
                _render_table([{k: v for k, v in p.items() if k != "sample_chunks"}])
                for chunk in samples:
                    st.caption(f"chunk #{chunk.get('chunk_index')} · {chunk.get('section')} "
                               f"· {chunk.get('tokens')} token")
                    st.markdown(f"> {chunk.get('text', '')}".replace("\n", "\n> "))
                st.divider()

    if arts.get("llm"):
        with st.expander(f"🤖 Prompt & balasan LLM ({len(arts['llm'])} contoh)", expanded=False):
            st.caption("Hanya sebagian awal yang direkam agar basis data tidak membengkak.")
            for art in arts["llm"]:
                p = art.get("payload") or {}
                st.markdown(f"**{art.get('label')}** · model `{p.get('model', '?')}`")
                st.text_area("prompt", p.get("prompt", ""), height=140,
                             key=f"p{art['id']}", disabled=True)
                st.text_area("balasan", p.get("response", ""), height=100,
                             key=f"r{art['id']}", disabled=True)
                st.divider()

    if payload.get("notes"):
        st.markdown("**⚠️ Catatan & keterbatasan**")
        for note in payload["notes"]:
            # Catatan gagal-sistem dari backend diawali huruf kapital penuh;
            # harus mencolok agar "0 gap" tidak dibaca sebagai temuan.
            (st.error if "TIDAK MENJAWAB" in note or "BUKAN temuan" in note
             else st.warning)(note)

    if payload.get("outputs"):
        with st.expander("📦 Berkas keluaran", expanded=False):
            for name, path in payload["outputs"].items():
                st.code(f"{name}: {path}", language="text")


def render_metrics_grid(metrics: dict[str, Any]) -> None:
    _render_metrics(metrics)
