"""Wizard Research — satu aplikasi web untuk seluruh alur (full Streamlit).

Jalankan:  .venv/bin/streamlit run app.py        (port 8501; backend di :8001)

Halaman pembuka adalah 🧭 Wizard: 4 langkah dari PDF sampai judul penelitian.
Grup *Detail teknis* membuka tiap tahap kedua pipeline (penelitian: corong angka,
jejak LLM, data lengkap, kode & rumus; 8 tahap: proses & hasil, jurnal & gap,
tindak lanjut, metode). Pencarian literatur luar (halaman Cari Paper) dihapus
9 Sep 2026 — bukan bagian proposal. Dulu Wizard adalah aplikasi terpisah
``tools/wizard_lite`` (:8502) — digabung 9 Sep 2026.
"""

import streamlit as st

from common import DEFAULT_API

st.set_page_config(
    page_title="Wizard Research",
    page_icon="🧭",
    layout="wide",
)

st.session_state.setdefault("api_base", DEFAULT_API)
st.session_state.setdefault("auto_refresh", True)
st.session_state.setdefault("mode_teknis", False)

pages = {
    "Mulai di sini": [
        st.Page("page_wizard.py", title="Wizard — PDF ke judul", icon="🧭", default=True),
    ],
    "Detail teknis — pipeline penelitian": [
        st.Page("page_research_wizard.py", title="Analisis Penelitian", icon="🔬"),
        st.Page("page_research_compare.py", title="Bandingkan Dua Analisis", icon="⚖️"),
        st.Page("page_research_source.py", title="Teks Sumber Jurnal", icon="📖"),
        st.Page("page_research_raw.py", title="Log & Artefak", icon="🧾"),
    ],
    "Detail teknis — indikator synthesis gap (Langkah 3)": [
        st.Page("page_analysis.py", title="Proses & Hasil", icon="🔬"),
        st.Page("page_journals.py", title="Jurnal & Gap", icon="📚"),
        st.Page("page_followup.py", title="Tindak Lanjut Gap", icon="🚀"),
        st.Page("page_method.py", title="Metode & Uji Coba", icon="🎓"),
        st.Page("page_dashboard.py", title="Dashboard Job", icon="📊"),
        st.Page("page_events.py", title="Log Event", icon="🧾"),
    ],
    "Pustaka": [
        st.Page("page_skills.py", title="Skill Riset", icon="🧠"),
    ],
}

with st.sidebar:
    st.title("🧭 Wizard Research")
    st.caption("Analisis jurnal · LLM + Neuro-Symbolic")
    if job_id := st.session_state.get("research_job_id"):
        st.caption(f"Analisis aktif: `{job_id[:8]}…`")
    st.info("Mulai dari **🧭 Wizard** (4 langkah). Dua grup *Detail teknis* membuka isi tiap tahap: "
            "pipeline penelitian (Langkah 2 & 4) dan pipeline 8 tahap indikator synthesis gap "
            "(Langkah 3).")
    st.toggle("🔬 Mode teknis", key="mode_teknis",
              help="Tampilkan nama kunci asli (gap_type, priority_score, …) seperti di "
                   "kode dan BAB III, bukan bahasa awam.")
    with st.expander("⚙️ Pengaturan", expanded=False):
        st.text_input("API backend", key="api_base")
        st.toggle("Auto-refresh saat berjalan", key="auto_refresh")

st.navigation(pages).run()
