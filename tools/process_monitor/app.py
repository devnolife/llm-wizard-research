"""Monitor Analisis Jurnal — entry multi-halaman (full Streamlit).

Jalankan:  .venv/bin/streamlit run app.py
Halaman:   📊 Dashboard · 🔎 Cari Paper · 🔬 Proses & Hasil · 📚 Jurnal & Gap ·
           🚀 Tindak Lanjut Gap · 🎓 Metode & Uji Coba · 🧠 Skill Riset · 🧾 Log Event
"""

import streamlit as st

from common import DEFAULT_API

st.set_page_config(
    page_title="Wizard Research — Monitor Analisis",
    page_icon="🔬",
    layout="wide",
)

st.session_state.setdefault("api_base", DEFAULT_API)
st.session_state.setdefault("auto_refresh", True)

pages = [
    st.Page("page_dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("page_papers.py", title="Cari Paper", icon="🔎"),
    st.Page("page_analysis.py", title="Proses & Hasil", icon="🔬"),
    st.Page("page_journals.py", title="Jurnal & Gap", icon="📚"),
    st.Page("page_followup.py", title="Tindak Lanjut Gap", icon="🚀"),
    st.Page("page_method.py", title="Metode & Uji Coba", icon="🎓"),
    st.Page("page_skills.py", title="Skill Riset", icon="🧠"),
    st.Page("page_events.py", title="Log Event", icon="🧾"),
]

with st.sidebar:
    st.title("🔬 Wizard Research")
    st.caption("Analisis jurnal · LLM + Neuro-Symbolic")
    if st.session_state.get("job_id"):
        st.caption(f"Job aktif: `{st.session_state['job_id'][:8]}…`")
    with st.expander("⚙️ Pengaturan", expanded=False):
        st.text_input("API backend", key="api_base")
        st.toggle("Auto-refresh saat berjalan", key="auto_refresh")

st.navigation(pages).run()
