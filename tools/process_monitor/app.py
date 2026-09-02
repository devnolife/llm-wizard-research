"""Monitor Analisis Jurnal — entry multi-halaman (full Streamlit).

Jalankan:  .venv/bin/streamlit run app.py

Navigasi mengikuti alur penelitian: mulai analisis, lalu satu halaman per tahap
pipeline. Pipeline lama 8 tahap tetap tersedia di grup terpisah agar job lama
masih bisa dibuka.
"""

import streamlit as st

from common import DEFAULT_API

st.set_page_config(
    page_title="Wizard Research — Alur Penelitian",
    page_icon="🔬",
    layout="wide",
)

st.session_state.setdefault("api_base", DEFAULT_API)
st.session_state.setdefault("auto_refresh", True)

pages = {
    "Alur Penelitian": [
        st.Page("page_research_start.py", title="Mulai Analisis", icon="🚀", default=True),
        st.Page("page_stage_chunking.py", title="1 · Ekstraksi & Chunking", icon="📄"),
        st.Page("page_stage_gaps.py", title="2 · Penambangan Gap", icon="🕳️"),
        st.Page("page_stage_novelty.py", title="3 · Verifikasi Kebaruan", icon="🔭"),
        st.Page("page_stage_recommendation.py", title="4 · Rekomendasi Topik", icon="🎯"),
        st.Page("page_research_raw.py", title="Log & Artefak", icon="🧾"),
    ],
    "Pustaka": [
        st.Page("page_papers.py", title="Cari Paper", icon="🔎"),
        st.Page("page_skills.py", title="Skill Riset", icon="🧠"),
    ],
    "Pipeline Lama (8 tahap)": [
        st.Page("page_dashboard.py", title="Dashboard", icon="📊"),
        st.Page("page_analysis.py", title="Proses & Hasil", icon="🔬"),
        st.Page("page_journals.py", title="Jurnal & Gap", icon="📚"),
        st.Page("page_followup.py", title="Tindak Lanjut Gap", icon="🚀"),
        st.Page("page_method.py", title="Metode & Uji Coba", icon="🎓"),
        st.Page("page_events.py", title="Log Event", icon="🧾"),
    ],
}

with st.sidebar:
    st.title("🔬 Wizard Research")
    st.caption("Analisis jurnal · LLM + Neuro-Symbolic")
    if job_id := st.session_state.get("research_job_id"):
        st.caption(f"Analisis aktif: `{job_id[:8]}…`")
    with st.expander("⚙️ Pengaturan", expanded=False):
        st.text_input("API backend", key="api_base")
        st.toggle("Auto-refresh saat berjalan", key="auto_refresh")

st.navigation(pages).run()
