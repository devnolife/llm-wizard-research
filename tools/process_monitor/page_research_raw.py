"""🧾 Log & Artefak — data mentah job penelitian untuk penelusuran."""

import pandas as pd
import streamlit as st

from common import fetch_artifacts, fetch_events, fmt_clock, fmt_duration
from research_common import require_job

st.title("🧾 Log & Artefak Mentah")
st.caption("Jejak lengkap yang dipakai halaman tahap — berguna saat menelusuri "
           "kenapa sebuah angka muncul.")

job_id = require_job()
if job_id:
    events = (fetch_events(job_id) or {}).get("events") or []
    artifacts = (fetch_artifacts(job_id) or {}).get("artifacts") or []

    tab_ev, tab_art = st.tabs([f"Event ({len(events)})", f"Artefak ({len(artifacts)})"])

    with tab_ev:
        if not events:
            st.info("Belum ada event.")
        else:
            st.dataframe(pd.DataFrame([{
                "waktu": fmt_clock(e.get("created_at")),
                "tipe": e.get("type"),
                "tahap": e.get("phase"),
                "durasi": fmt_duration(e["duration_ms"]) if e.get("duration_ms") else "",
                "data": str(e.get("data") or "")[:160],
            } for e in events]), width="stretch", hide_index=True)

    with tab_art:
        if not artifacts:
            st.info("Belum ada artefak.")
        else:
            kinds = sorted({a.get("kind", "?") for a in artifacts})
            pilih = st.multiselect("Jenis", kinds, default=kinds)
            for art in [a for a in artifacts if a.get("kind") in pilih]:
                with st.expander(
                    f"[{art.get('kind')}] {art.get('phase')} · {art.get('label')}"
                ):
                    st.json(art.get("payload") or {})
