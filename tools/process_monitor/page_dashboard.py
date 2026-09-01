"""📊 Dashboard — ringkasan analisis & riwayat hasil."""

import streamlit as st

from common import (
    JOB_STATUS_BADGES,
    delete_job,
    fetch_jobs,
    fmt_datetime,
    reanalyze_job,
    render_server_panel,
)

st.title("📊 Dashboard Analisis Jurnal")
st.caption(
    "Platform analisis paper berbahasa Indonesia — pipeline LLM + Neuro-Symbolic: "
    "ekstraksi topik, deteksi *synthesis gap*, usulan penelitian, dan peta jalan."
)

if err := st.session_state.pop("last_error", None):
    st.error(err)

jobs = fetch_jobs(limit=30)
completed = [j for j in jobs if j.get("status") == "completed"]
active = [j for j in jobs if j.get("status") in ("queued", "running")]
failed = [j for j in jobs if j.get("status") in ("failed", "cancelled")]
files_total = sum(j.get("files_processed") or len(j.get("files") or []) for j in completed)

m1, m2, m3, m4 = st.columns(4)
with m1, st.container(border=True):
    st.metric("📚 Total Analisis", len(jobs))
with m2, st.container(border=True):
    st.metric("✅ Selesai", len(completed))
with m3, st.container(border=True):
    st.metric("🔄 Sedang Berjalan", len(active))
with m4, st.container(border=True):
    st.metric("📄 File Dianalisis", files_total)

with st.expander("🖥️ Pemakaian Server (CPU · RAM · GPU)", expanded=False):
    render_server_panel()

st.divider()

head_l, head_r = st.columns([4, 1])
head_l.subheader("Riwayat Analisis")
if head_r.button("➕ Analisis Baru", width="stretch", type="primary"):
    st.session_state["job_id"] = ""
    st.switch_page("page_analysis.py")

if not jobs:
    st.info("Belum ada analisis. Klik **➕ Analisis Baru** untuk mengunggah PDF jurnal pertama.")
else:
    for row_start in range(0, len(jobs), 2):
        cols = st.columns(2)
        for col, job in zip(cols, jobs[row_start:row_start + 2]):
            status = job.get("status", "?")
            icon, label, color = JOB_STATUS_BADGES.get(status, ("❔", status, "gray"))
            with col, st.container(border=True):
                top_l, top_r = st.columns([3, 1])
                top_l.markdown(f"**{icon} :{color}[{label}]** · `{job['job_id'][:8]}…`")
                top_r.caption(fmt_datetime(job.get("created_at")))

                files = job.get("files") or []
                if files:
                    names = ", ".join(files[:2]) + (f" +{len(files)-2} lainnya" if len(files) > 2 else "")
                    st.caption(f"📄 {len(files)} file: {names}")

                if status == "completed":
                    st.markdown(
                        f"🧠 **{job.get('topics_count', 0)}** topik · "
                        f"🕳️ **{job.get('gaps_count', 0)}** gap · "
                        f"💡 **{job.get('recommendations_count', 0)}** usulan"
                        + (f" · 🤖 `{job['model']}`" if job.get("model") else "")
                    )
                elif status in ("queued", "running"):
                    st.progress(min(int(job.get("progress") or 0), 100) / 100)
                    st.caption(job.get("message") or "menunggu…")
                else:
                    st.caption(job.get("message") or "—")

                act_l, act_m, act_r = st.columns([3, 1, 1])
                if act_l.button("🔍 Buka detail & hasil", key=f"open_{job['job_id']}", width="stretch"):
                    st.session_state["job_id"] = job["job_id"]
                    st.switch_page("page_analysis.py")
                if status in ("queued", "running"):
                    act_m.button("🔁", key=f"norerun_{job['job_id']}", width="stretch",
                                 disabled=True, help="Job masih berjalan")
                    act_r.button("🗑️", key=f"nodel_{job['job_id']}", width="stretch",
                                 disabled=True, help="Batalkan dulu job yang sedang berjalan")
                else:
                    with act_m.popover("🔁", width="stretch",
                                       help="Analisis ulang dengan engine LLM aktif (job baru, hasil lama tetap ada)"):
                        st.markdown(
                            "Analisis ulang PDF job ini sebagai **job baru** dengan engine LLM "
                            "yang aktif sekarang? Hasil lama tetap tersimpan untuk perbandingan."
                        )
                        if st.button("✅ Ya, analisis ulang", key=f"rerun_{job['job_id']}", type="primary"):
                            new_id = reanalyze_job(job["job_id"])
                            if new_id:
                                st.session_state["job_id"] = new_id
                                st.toast(f"Analisis ulang diantrekan: {new_id[:8]}…", icon="🔁")
                            st.rerun()
                    with act_r.popover("🗑️", width="stretch", help="Hapus riwayat ini"):
                        st.markdown("Hapus analisis ini **permanen** beserta hasil, log, dan filenya?")
                        if st.button("✅ Ya, hapus", key=f"del_{job['job_id']}", type="primary"):
                            if delete_job(job["job_id"]):
                                if st.session_state.get("job_id") == job["job_id"]:
                                    st.session_state["job_id"] = ""
                                st.toast(f"Job {job['job_id'][:8]}… dihapus", icon="🗑️")
                                st.rerun()

if failed:
    st.caption(f"⚠️ {len(failed)} job gagal/dibatalkan tercantum di riwayat — buka detailnya untuk melihat alasannya.")
