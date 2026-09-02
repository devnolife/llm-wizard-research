"""🔬 Analisis Penelitian — satu halaman berpanduan dari unggah sampai hasil.

Menggantikan alur lama yang menyebar ke enam menu sidebar. Langkah ditentukan
dari status job, bukan dari klik pengguna, supaya tidak ada layar yang muncul
sebelum datanya siap.
"""

import streamlit as st

from common import JOB_STATUS_BADGES, cancel_job, fetch_status, fmt_datetime
from research_common import (
    fetch_stages,
    render_stage_body,
    render_timeline,
    research_jobs,
    set_active_job,
    start_research,
)

LANGKAH = ["1 · Unggah jurnal", "2 · Pipeline berjalan", "3 · Baca hasil"]


def _label(job_id: str, jobs: list[dict]) -> str:
    job = next((j for j in jobs if j["job_id"] == job_id), None)
    if not job:
        return f"{job_id[:8]}…"
    icon, label, _ = JOB_STATUS_BADGES.get(job.get("status", ""), ("❔", "?", "gray"))
    return (f"{icon} {job_id[:8]}… · {fmt_datetime(job.get('created_at'))} · "
            f"{len(job.get('files') or [])} berkas · {label}")


st.title("🔬 Analisis Penelitian")

if err := st.session_state.pop("last_error", None):
    st.error(err)

jobs = research_jobs(limit=30)
active = st.session_state.get("research_job_id") or st.query_params.get("job", "")
status = fetch_status(active) if active else {}
state = (status or {}).get("status", "")

if not active or state not in ("queued", "running", "completed", "failed", "cancelled"):
    langkah = 1
elif state in ("queued", "running"):
    langkah = 2
else:
    langkah = 3

# ── Penunjuk langkah ──
for col, (i, label) in zip(st.columns(3), enumerate(LANGKAH, 1)):
    if i < langkah:
        col.success(f"✅ {label}")
    elif i == langkah:
        col.info(f"➡️ **{label}**")
    else:
        col.caption(f"⚪ {label}")

st.divider()


# ── LANGKAH 1 ──────────────────────────────────────────────────────────────
if langkah == 1:
    st.subheader("Langkah 1 — Unggah jurnal PDF")
    st.markdown(
        "Pilih beberapa PDF jurnal sekaligus, lalu tekan **Jalankan**. "
        "Sistem mengerjakan empat tahap ini otomatis tanpa perlu kamu klik lagi:")
    for i, stage in enumerate(fetch_stages(), 1):
        st.markdown(f"&nbsp;&nbsp;**{i}. {stage['icon']} {stage['title']}** — "
                    f"{stage['description']}", unsafe_allow_html=True)

    st.info("Perkiraan waktu: sekitar **4–5 menit untuk 14 jurnal**. "
            "Tahap penambangan gap memakan ~90% waktu karena memanggil LLM per kandidat.")

    uploads = st.file_uploader("PDF jurnal (bisa pilih banyak sekaligus)",
                               type="pdf", accept_multiple_files=True)
    if uploads:
        st.caption(f"{len(uploads)} berkas siap diproses.")
    if st.button("🚀 Jalankan analisis", disabled=not uploads, type="primary",
                 width="stretch"):
        job_id = start_research(uploads)
        if job_id:
            set_active_job(job_id)
            st.rerun()

    if jobs:
        st.divider()
        st.subheader("…atau buka analisis sebelumnya")
        pilihan = st.selectbox(
            "Analisis yang tersimpan", [j["job_id"] for j in jobs],
            format_func=lambda jid: _label(jid, jobs), key="pilih_lama")
        if st.button("📂 Buka analisis ini", width="stretch"):
            set_active_job(pilihan)
            st.rerun()


# ── LANGKAH 2 ──────────────────────────────────────────────────────────────
elif langkah == 2:
    st.subheader("Langkah 2 — Sedang diproses")
    progress = float(status.get("progress") or 0)
    st.progress(min(1.0, progress / 100), text=status.get("message") or "—")
    render_timeline(active)
    if state == "queued":
        st.info("Job **menunggu giliran worker** (maksimal dua analisis berjalan "
                "bersamaan). Ia mulai otomatis; biarkan halaman ini terbuka.")
    else:
        st.info("**Tidak ada yang perlu kamu lakukan.** Biarkan halaman ini terbuka; "
                "hasil muncul sendiri setelah keempat tahap selesai.")
    col_refresh, col_cancel = st.columns([3, 1])
    if col_refresh.button("🔄 Segarkan sekarang", width="stretch"):
        st.rerun()
    with col_cancel.popover("⏹️ Batalkan", width="stretch"):
        st.markdown("Hentikan analisis ini? Job antre berhenti seketika; job berjalan "
                    "berhenti di batas tahap berikutnya. Tahap yang sudah rampung tetap "
                    "bisa dibaca.")
        if st.button("✅ Ya, batalkan", type="primary", key="cancel_research"):
            if cancel_job(active):
                st.toast("Pembatalan diminta", icon="⏹️")
            st.rerun()


# ── LANGKAH 3 ──────────────────────────────────────────────────────────────
else:
    if state == "failed":
        st.error(f"Analisis gagal: {status.get('error') or status.get('message')}")
    elif state == "cancelled":
        st.warning(f"Analisis dibatalkan: {status.get('message') or '—'}. Tahap yang "
                   "sudah rampung tetap bisa dibaca di tab bawah.")
    else:
        st.subheader("Langkah 3 — Hasil siap dibaca")
    st.caption(f"Analisis `{active[:8]}…` · {fmt_datetime(status.get('created_at'))}")
    render_timeline(active)

    st.markdown("**Buka tab di bawah untuk menelusuri tiap tahap.** Di dalam tiap tab "
                "ada *Ringkasan* (angka), *Data lengkap* (semua record, bisa dicari), "
                "dan *Kode & rumus* (kode Python yang dijalankan).")

    stages = fetch_stages()
    for tab, stage in zip(st.tabs([f"{s['icon']} {s['title']}" for s in stages]), stages):
        with tab:
            render_stage_body(active, stage["key"])

    st.divider()
    if st.button("🔁 Mulai analisis baru", width="stretch"):
        st.session_state.pop("research_job_id", None)
        st.query_params.clear()
        st.rerun()
    st.caption("Ingin membaca teks jurnal apa adanya? Buka **📖 Teks Sumber Jurnal** "
               "di sidebar.")
