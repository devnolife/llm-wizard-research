"""🚀 Mulai Analisis — unggah PDF, jalankan pipeline penelitian, pilih job."""

import streamlit as st

from common import JOB_STATUS_BADGES, fetch_status, fmt_datetime
from research_common import (
    fetch_stages,
    render_timeline,
    research_jobs,
    set_active_job,
    start_research,
)

st.title("🚀 Mulai Analisis Penelitian")

if err := st.session_state.pop("last_error", None):
    st.error(err)

st.caption(
    "Pipeline berjalan otomatis dari awal sampai akhir, tetapi setiap tahap "
    "menyimpan hasil detailnya sendiri — buka halaman tahap di sidebar untuk "
    "memeriksa apa yang terjadi di dalamnya."
)

# ── Alur yang akan dijalankan ──
st.subheader("Tahapan")
for i, stage in enumerate(fetch_stages(), 1):
    st.markdown(f"**{i}. {stage['icon']} {stage['title']}** — {stage['description']}")

st.divider()

# ── Mulai baru ──
st.subheader("📤 Unggah jurnal")
uploads = st.file_uploader("PDF jurnal (bisa banyak)", type="pdf",
                           accept_multiple_files=True)
if st.button("🚀 Jalankan pipeline", disabled=not uploads, type="primary"):
    job_id = start_research(uploads)
    if job_id:
        set_active_job(job_id)
        st.success(f"Pipeline dimulai untuk {len(uploads)} berkas.")
        st.rerun()

st.divider()

# ── Job yang sudah ada ──
jobs = research_jobs(limit=30)
st.subheader(f"📋 Analisis sebelumnya ({len(jobs)})")

if not jobs:
    st.info("Belum ada analisis penelitian. Unggah PDF di atas untuk memulai.")
else:
    active = st.session_state.get("research_job_id") or st.query_params.get("job", "")
    options = [j["job_id"] for j in jobs]
    if active and active not in options:
        options.insert(0, active)

    def _label(jid: str) -> str:
        job = next((j for j in jobs if j["job_id"] == jid), None)
        if not job:
            return f"{jid[:8]}… (manual)"
        icon, label, _ = JOB_STATUS_BADGES.get(job.get("status", ""), ("❔", "?", "gray"))
        files = len(job.get("files") or [])
        return (f"{icon} {jid[:8]}… · {fmt_datetime(job.get('created_at'))} · "
                f"{files} berkas · {label}")

    chosen = st.selectbox("Pilih analisis", options,
                          index=options.index(active) if active in options else 0,
                          format_func=_label)
    if chosen != active:
        set_active_job(chosen)
        st.rerun()

    status = fetch_status(chosen) or {}
    progress = float(status.get("progress") or 0)
    st.progress(min(1.0, progress / 100), text=status.get("message") or "—")
    render_timeline(chosen)

    if status.get("status") in ("queued", "running"):
        st.caption("Halaman menyegar sendiri saat pipeline berjalan.")
        if st.button("🔄 Segarkan"):
            st.rerun()
