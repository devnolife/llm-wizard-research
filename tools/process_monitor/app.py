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
st.session_state.setdefault("mode_teknis", False)

pages = {
    "Penelitian": [
        st.Page("page_research_wizard.py", title="Analisis Penelitian", icon="🔬",
                default=True),
        st.Page("page_research_source.py", title="Teks Sumber Jurnal", icon="📖"),
        st.Page("page_research_raw.py", title="Log & Artefak", icon="🧾"),
    ],
    "Pustaka": [
        st.Page("page_papers.py", title="Cari Paper", icon="🔎"),
        st.Page("page_skills.py", title="Skill Riset", icon="🧠"),
    ],
    "Arsip — Pipeline Lama": [
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
    st.info("Mulai dari **🔬 Analisis Penelitian**. Menu lain hanya pelengkap.")
    st.toggle("🔬 Mode teknis", key="mode_teknis",
              help="Tampilkan nama kunci asli (gap_type, priority_score, …) seperti di "
                   "kode dan BAB III, bukan bahasa awam.")
    with st.expander("⚙️ Pengaturan", expanded=False):
        st.text_input("API backend", key="api_base")
        st.toggle("Auto-refresh saat berjalan", key="auto_refresh")
        st.caption("Grup *Arsip* melayani job pipeline lama 8 tahap dan tidak "
                   "dipakai alur penelitian ini.")

st.navigation(pages).run()
