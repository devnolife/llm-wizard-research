"""🧾 Log Event — riwayat event mentah per job (metadata-only)."""

import time

import streamlit as st

from common import (
    JOB_STATUS_BADGES,
    REFRESH_SECONDS,
    fetch_events,
    fetch_jobs,
    fmt_clock,
    fmt_datetime,
    fmt_duration,
)

st.title("🧾 Log Event Mentah")
st.caption(
    "Deretan event teknis tiap job (metadata-only, tersanitasi backend) — "
    "berguna untuk menelusuri durasi tiap langkah dan jenis error."
)

if err := st.session_state.pop("last_error", None):
    st.error(err)

jobs = fetch_jobs(limit=30)
job_id = st.session_state.get("job_id", "").strip()

if jobs:
    options = [j["job_id"] for j in jobs]
    if job_id and job_id not in options:
        options.insert(0, job_id)

    def _label(jid: str) -> str:
        job = next((j for j in jobs if j["job_id"] == jid), None)
        if not job:
            return f"{jid[:8]}… (manual)"
        icon, label, _ = JOB_STATUS_BADGES.get(job.get("status", ""), ("❔", "?", "gray"))
        return f"{icon} {jid[:8]}… · {fmt_datetime(job.get('created_at'))} · {label}"

    selected = st.selectbox(
        "Pilih job",
        options,
        index=options.index(job_id) if job_id in options else 0,
        format_func=_label,
    )
    if selected != job_id:
        st.session_state["job_id"] = selected
        st.rerun()
    job_id = selected
else:
    job_id = st.text_input("Job ID", value=job_id).strip()

if not job_id:
    st.info("Belum ada job — mulai analisis dari halaman 🔬 Proses & Hasil.")
    st.stop()

payload = fetch_events(job_id)
if not isinstance(payload, dict):
    st.error(f"Event untuk job `{job_id}` tidak dapat diambil.")
    st.stop()

job_status = payload.get("status") or "?"
events = payload.get("events", [])
icon, label, color = JOB_STATUS_BADGES.get(job_status, ("❔", job_status, "gray"))
st.markdown(f"**{icon} Job `{job_id[:8]}…` — :{color}[{label}]** · {len(events)} event")

if events:
    log_rows = []
    for ev in events:
        log_rows.append({
            "waktu": fmt_clock(ev.get("created_at")),
            "event": ev.get("type"),
            "tahap": ev.get("phase") or "—",
            "durasi": fmt_duration(ev.get("duration_ms")) if ev.get("duration_ms") else "",
            "data": ", ".join(f"{k}={v}" for k, v in (ev.get("data") or {}).items()) or "",
        })
    st.dataframe(log_rows, width="stretch", height=560, hide_index=True)
else:
    st.info("Belum ada event untuk job ini (job lama sebelum fitur, atau belum mulai).")

# ── Auto refresh ──
if (
    st.session_state.get("auto_refresh", True)
    and not st.session_state.get("_no_autorefresh")  # hook untuk AppTest
    and job_status in ("queued", "running")
):
    time.sleep(REFRESH_SECONDS)
    st.rerun()
