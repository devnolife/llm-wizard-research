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

from common import api_base, fetch_artifacts, fetch_events, fetch_status, fmt_duration

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
    "pending": ("⚪", "menunggu"),
}


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


def stage_states(job_id: str) -> dict[str, dict]:
    """Status tiap tahap diturunkan dari event phase.* milik job."""
    payload = fetch_events(job_id) or {}
    events = payload.get("events") or []
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
    return states


def stage_artifacts(job_id: str, phase: str) -> dict[str, list[dict]]:
    """Artefak satu tahap, dikelompokkan per jenis."""
    payload = fetch_artifacts(job_id) or {}
    grouped: dict[str, list[dict]] = {"result": [], "extraction": [], "llm": []}
    for art in payload.get("artifacts") or []:
        if art.get("phase") == phase:
            grouped.setdefault(art.get("kind", "result"), []).append(art)
    return grouped


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
            col.metric(key.replace("_", " "), value)
    for key, value in metrics.items():
        if isinstance(value, dict) and value:
            st.caption(key.replace("_", " "))
            _render_table([{"kunci": k, "jumlah": v} for k, v in value.items()])


def render_stage_page(stage_key: str) -> None:
    """Halaman satu tahap: parameter, metrik, contoh data, LLM, dan berkas."""
    stage = next((s for s in fetch_stages() if s["key"] == stage_key), None)
    if stage is None:
        st.error(f"Tahap tidak dikenal: {stage_key}")
        return

    st.title(f"{stage['icon']} {stage['title']}")
    st.caption(stage["description"])

    job_id = require_job()
    if not job_id:
        return

    render_timeline(job_id)
    st.divider()

    info = stage_states(job_id).get(stage_key, {})
    state = info.get("state", "pending")
    if state == "pending":
        st.info("Tahap ini belum berjalan.")
        return
    if state == "running":
        st.warning("Tahap ini sedang berjalan — hasil detail muncul setelah selesai.")
    if state == "failed":
        st.error(f"Tahap gagal: {info.get('error', 'tidak diketahui')}")

    arts = stage_artifacts(job_id, stage_key)
    results = arts.get("result") or []
    if not results:
        st.info("Belum ada hasil detail untuk tahap ini.")
        return
    payload = results[-1].get("payload") or {}

    if payload.get("duration_ms") is not None:
        st.caption(f"⏱️ Durasi tahap: **{fmt_duration(payload['duration_ms'])}**")

    if payload.get("metrics"):
        st.subheader("📊 Metrik")
        _render_metrics(payload["metrics"])

    if payload.get("params"):
        with st.expander("⚙️ Parameter yang dipakai", expanded=False):
            _render_table([{"parameter": k, "nilai": str(v)}
                           for k, v in payload["params"].items()])

    if payload.get("samples"):
        st.subheader("🔍 Contoh hasil")
        _render_table(payload["samples"],
                      "Cuplikan data mentah tahap ini, bukan seluruh isinya.")

    if arts.get("extraction"):
        with st.expander(f"📄 Rincian per berkas ({len(arts['extraction'])})", expanded=False):
            _render_table([
                {k: v for k, v in (a.get("payload") or {}).items() if k != "sample_chunks"}
                for a in arts["extraction"]
            ])

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
        st.subheader("⚠️ Catatan & keterbatasan")
        for note in payload["notes"]:
            st.warning(note)

    if payload.get("outputs"):
        st.subheader("📦 Berkas keluaran")
        for label, path in payload["outputs"].items():
            st.code(f"{label}: {path}", language="text")
