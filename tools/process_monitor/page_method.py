"""Halaman Metode & Uji Coba — peta metode proposal ke bagian sistem + hasil eksperimen."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from common import fetch_jobs

RESULTS_DIR = Path(__file__).resolve().parents[2] / "backend" / "experiments" / "results"

# ---------------------------------------------------------------------------
# Peta metode proposal -> bagian sistem
# ---------------------------------------------------------------------------

PIPELINE_DOT = """
digraph pipeline {
  rankdir=TB;
  bgcolor="transparent";
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11,
        color="#555555", fontcolor="#111111", margin="0.18,0.10"];
  edge [color="#888888", fontname="Helvetica", fontsize=10, fontcolor="#444444"];

  pdf  [label="📄 PDF Paper (input)", fillcolor="#eceff1"];
  ing  [label="FASE 1 — INGESTION\\npypdf / OCR → chunking → embedding → ChromaDB (RAG)", fillcolor="#e3f2fd"];
  fact [label="FASE 2 — EKSTRAKSI FAKTA  (komponen NEURAL)\\nLLM → triple Subjek-Predikat-Objek → Knowledge Graph", fillcolor="#fff3e0"];

  subgraph cluster_agent {
    label="FASE 3 — ANALISIS AGENTIC (LangGraph, maks 3 iterasi)";
    fontname="Helvetica"; fontsize=11; color="#9575cd"; style="rounded";
    obs  [label="Observe\\nRAG + fakta + KG", fillcolor="#ede7f6"];
    thk  [label="Think\\n3 indikator gap + NLI", fillcolor="#ede7f6"];
    act  [label="Act\\nRule Engine + rekomendasi", fillcolor="#ede7f6"];
    ev   [label="Evaluate\\nself-critic", fillcolor="#ede7f6"];
    obs -> thk -> act -> ev;
    ev -> thk [style=dashed, label="revisi"];
  }

  rule [label="FASE 4 — VALIDASI  (komponen SYMBOLIC)\\nRule Engine 9 aturan → PASS / FLAG / REJECT", fillcolor="#e8f5e9"];
  out  [label="🏁 Output\\nindikator gap tervalidasi + usulan + roadmap", fillcolor="#fffde7"];

  pdf -> ing -> fact -> obs;
  ev -> rule -> out;
}
"""

METHOD_CARDS = [
    {
        "title": "1️⃣ Ingestion & RAG (Retrieval-Augmented Generation)",
        "desc": "PDF dibaca (text-layer ocrd / GPU OCR / pypdf), dipotong per bagian "
                "(section-aware chunking), diubah menjadi embedding multibahasa, lalu "
                "disimpan di vector database ChromaDB untuk pencarian konteks.",
        "web": "halaman **🔬 Proses & Hasil** → tahap **📄 Baca & Potong PDF** "
               "(buka *📦 Hasil* untuk preview teks per file).",
        "code": "backend/app/core/retrieval/ · app/utils/document_processor.py",
    },
    {
        "title": "2️⃣ Ekstraksi Fakta SPO — komponen Neural",
        "desc": "LLM mengubah kalimat paper menjadi triple **Subjek–Predikat–Objek** "
                "yang tersimpan di FactTable dan dirangkai menjadi Knowledge Graph.",
        "web": "tahap **⚙️ Neuro-Symbolic** (*📦 Hasil* → sampel fakta & statistik) dan "
               "seksi **🕸️ Knowledge Graph** di halaman Proses & Hasil.",
        "code": "backend/app/core/knowledge/fact_extractor.py",
    },
    {
        "title": "3️⃣ Koordinator Agentic (LangGraph)",
        "desc": "Loop **Observe → Think → Act → Evaluate** (maks 3 iterasi). Self-critic "
                "pada langkah Evaluate memutuskan perlu revisi atau selesai.",
        "web": "tahap **⚙️ Neuro-Symbolic** → *📦 Hasil* → **reasoning trace** "
               "(jejak langkah agent per iterasi).",
        "code": "backend/app/core/agents/coordinator.py",
    },
    {
        "title": "4️⃣ Deteksi 3 Indikator Synthesis Gap (Cooper)",
        "desc": "Menghitung indikator **Fragmentasi**, **Inkonsistensi**, dan "
                "**Ketidaklengkapan** dari fakta antar-paper per topik.",
        "web": "tahap **🕳️ Synthesis Gap** dan tab **🕳️ Gap** pada 🏁 Hasil Akhir "
               "(tiap kartu gap memuat jenis indikatornya).",
        "code": "backend/app/core/agents/gap_detector.py",
    },
    {
        "title": "5️⃣ NLI Cross-check (3-Layer Discriminator)",
        "desc": "Natural Language Inference memverifikasi hubungan antar-fakta "
                "(entailment / contradiction) untuk memperkuat indikator inkonsistensi.",
        "web": "kartu gap jenis **⚡ Inkonsistensi** pada tab Gap "
               "(kontradiksi terdeteksi ditandai perlu verifikasi manusia).",
        "code": "backend/app/core/agents/tools/nli_checker_tool.py · validation/relation_classifier.py",
    },
    {
        "title": "6️⃣ Rule Engine 9 Aturan — komponen Symbolic",
        "desc": "Validasi simbolik: 9 aturan dalam 3 kategori (Feasibility, Causality, "
                "Consistency) memberi vonis **PASS / FLAG / REJECT** pada tiap indikator gap.",
        "web": "badge **Rule Engine: PASS/FLAG** pada tiap kartu gap + ringkasan "
               "vonis di *📦 Hasil* tahap ⚙️ Neuro-Symbolic.",
        "code": "backend/app/core/validation/rule_engine.py",
    },
    {
        "title": "7️⃣ LLM Lokal (Ollama)",
        "desc": "Seluruh penalaran bahasa memakai LLM lokal (mis. llama3.2) — data paper "
                "tidak keluar dari server.",
        "web": "expander **🧠 Prompt & Jawaban LLM** di setiap tahap pada halaman "
               "Proses & Hasil (dapur LLM transparan).",
        "code": "backend/app/core/llm/ · panggilan tercatat sebagai artefak per tahap",
    },
    {
        "title": "8️⃣ Usulan Penelitian & Roadmap",
        "desc": "Gap tervalidasi diubah menjadi rekomendasi judul/usulan penelitian "
                "beserta peta jalan bertahap.",
        "web": "tab **💡 Usulan** dan **🗺️ Roadmap** pada 🏁 Hasil Akhir.",
        "code": "backend/app/api/routes/analysis.py (tahap proposal & roadmap)",
    },
]

# ---------------------------------------------------------------------------
# Eksperimen ablasi
# ---------------------------------------------------------------------------

MODE_LABELS = {
    "full": "Lengkap (metode usulan)",
    "no-rule-engine": "Tanpa Rule Engine",
    "no-nli": "Tanpa NLI",
    "nli": "Varian NLI",
    "cross-critic": "Varian Cross-Critic",
    "linear-baseline": "Baseline linear (tanpa agentic)",
}

MODE_DESCRIPTIONS = {
    "full": "Semua komponen aktif — konfigurasi yang diusulkan di proposal.",
    "no-rule-engine": "Rule Engine dimatikan → mengukur kontribusi validasi simbolik.",
    "no-nli": "NLI cross-check dimatikan → mengukur kontribusi verifikasi kontradiksi.",
    "nli": "Varian dengan penekanan NLI pada deteksi inkonsistensi.",
    "cross-critic": "Varian evaluasi silang antar-agent (cross-critic) pada langkah Evaluate.",
    "linear-baseline": "Pipeline lurus tanpa loop agentic — pembanding utama (baseline).",
}

METRIC_OPTIONS = {
    "total_gap_indicators": "Indikator gap terdeteksi",
    "total_facts_extracted": "Fakta SPO terekstrak",
    "rule_engine_pass_rate": "Rule Engine PASS (%)",
    "rule_engine_flag_rate": "Rule Engine FLAG (%)",
    "adversarial_accuracy": "Akurasi uji adversarial (%)",
    "avg_confidence": "Rata-rata confidence",
    "total_pipeline_time_seconds": "Durasi pipeline (detik)",
}

MODEL_LABELS = {"llama3.2": "llama3.2", "gpt-oss": "gpt-oss"}

_RUN_RE = re.compile(
    r"^experiment_(?P<mode>.+?)_(?P<model>llama3\.2|gpt-oss)_latest(?:\.run(?P<run>\d+))?\.json$"
)


@st.cache_data(ttl=600, show_spinner=False)
def load_experiment_runs() -> pd.DataFrame:
    """Baca semua file hasil run eksperimen dari disk menjadi DataFrame."""
    rows: list[dict] = []
    if not RESULTS_DIR.is_dir():
        return pd.DataFrame(rows)
    for path in sorted(RESULTS_DIR.glob("experiment_*.json")):
        if "backup" in path.name:
            continue
        match = _RUN_RE.match(path.name)
        if not match:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        metrics = data.get("overall_metrics") or {}
        if not metrics:
            continue
        row = {
            "mode": match["mode"],
            "model": match["model"],
            "run": int(match["run"] or 0),
        }
        for key in METRIC_OPTIONS:
            value = metrics.get(key)
            if isinstance(value, (int, float)):
                row[key] = float(value)
        rows.append(row)
    return pd.DataFrame(rows)


@st.cache_data(ttl=600, show_spinner=False)
def load_adversarial_cases() -> tuple[str, list[dict]]:
    """Ambil kasus uji adversarial dari run 'full' terbaru yang memilikinya."""
    if not RESULTS_DIR.is_dir():
        return "", []
    candidates = sorted(
        (p for p in RESULTS_DIR.glob("experiment_full_*.json") if "backup" not in p.name),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        cases = (data.get("phase5_adversarial") or {}).get("cases") or []
        if cases:
            return path.name, cases
    return "", []


def _fmt_mean_std(series: pd.Series) -> str:
    mean = series.mean()
    std = series.std()
    if pd.isna(mean):
        return "—"
    if pd.isna(std) or std == 0:
        return f"{mean:.1f}"
    return f"{mean:.1f} ± {std:.1f}"


# ---------------------------------------------------------------------------
# Render halaman
# ---------------------------------------------------------------------------

st.title("🎓 Metode & Uji Coba")
st.caption(
    "Tesis: *Pendekatan Neuro-Symbolic Agentic untuk Deteksi Indikator Synthesis Gap "
    "pada Literatur Ilmiah* — halaman ini memetakan setiap metode di proposal ke bagian "
    "sistem yang mengimplementasikannya, beserta hasil uji cobanya."
)

# --- Bagian 1: peta metode -------------------------------------------------
st.header("🧭 Metode di Proposal → Bagian Sistem")
st.graphviz_chart(PIPELINE_DOT)
st.caption(
    "Alur 4 fase: *neural* (LLM) mengekstrak & menalar, *symbolic* (Rule Engine) "
    "memvalidasi — itulah makna **Neuro-Symbolic**."
)

jump_col, _ = st.columns([1, 2])
with jump_col:
    if st.button("🔬 Lihat contoh nyata di job terakhir", width="stretch"):
        jobs = fetch_jobs(limit=10)
        done = [j for j in jobs if j.get("status") == "completed"]
        if done:
            st.session_state["job_id"] = done[0]["job_id"]
            st.switch_page("page_analysis.py")
        else:
            st.info("Belum ada job selesai — jalankan analisis dulu di halaman Proses & Hasil.")

cols = st.columns(2)
for i, card in enumerate(METHOD_CARDS):
    with cols[i % 2].container(border=True):
        st.markdown(f"**{card['title']}**")
        st.markdown(card["desc"])
        st.markdown(f"👉 **Lihat di web ini:** {card['web']}")
        st.caption(f"📁 Kode: `{card['code']}`")

st.divider()

# --- Bagian 2: eksperimen ablasi -------------------------------------------
st.header("🧪 Uji Coba — Eksperimen Ablasi")
st.markdown(
    "Setiap **varian** mematikan satu komponen metode untuk membuktikan kontribusinya "
    "(*ablation study*). Tiap varian dijalankan **beberapa run dengan seed berbeda**; "
    "angka di bawah adalah **rata-rata ± simpangan baku** antar run."
)

with st.expander("ℹ️ Apa arti tiap varian?"):
    for mode, label in MODE_LABELS.items():
        st.markdown(f"- **{label}** (`{mode}`) — {MODE_DESCRIPTIONS[mode]}")

df_runs = load_experiment_runs()
if df_runs.empty:
    st.info(f"Belum ada file hasil eksperimen di `{RESULTS_DIR}`.")
else:
    pick_l, pick_r = st.columns([1, 2])
    model = pick_l.radio(
        "Model LLM",
        sorted(df_runs["model"].unique()),
        format_func=lambda m: MODEL_LABELS.get(m, m),
        horizontal=True,
    )
    metric = pick_r.selectbox(
        "Metrik yang dibandingkan",
        list(METRIC_OPTIONS),
        format_func=lambda k: METRIC_OPTIONS[k],
    )

    df_model = df_runs[df_runs["model"] == model]
    order = [m for m in MODE_LABELS if m in set(df_model["mode"])]

    if metric in df_model.columns:
        chart_df = (
            df_model.groupby("mode")[metric]
            .mean()
            .reindex(order)
            .rename(index=MODE_LABELS)
            .rename(METRIC_OPTIONS[metric])
            .to_frame()
        )
        st.bar_chart(chart_df, height=320, horizontal=True)
    else:
        st.info("Metrik ini tidak tersedia pada run yang ada.")

    st.subheader("📋 Tabel ringkasan semua metrik")
    table_rows = []
    for mode in order:
        sub = df_model[df_model["mode"] == mode]
        row = {"Varian": MODE_LABELS.get(mode, mode), "Jumlah run": len(sub)}
        for key, label in METRIC_OPTIONS.items():
            row[label] = _fmt_mean_std(sub[key]) if key in sub.columns else "—"
        table_rows.append(row)
    st.dataframe(pd.DataFrame(table_rows), width="stretch", hide_index=True)
    st.caption(
        f"Sumber: {len(df_model)} run file `backend/experiments/results/` untuk model "
        f"{MODEL_LABELS.get(model, model)}."
    )

st.divider()

# --- Bagian 3: uji adversarial ----------------------------------------------
st.header("🛡️ Uji Adversarial — Rule Engine")
st.markdown(
    "Kasus **sengaja dibuat salah** (mis. klaim yang tidak feasible) diumpankan ke "
    "Rule Engine; lulus uji berarti vonisnya **sesuai harapan**."
)

adv_file, adv_cases = load_adversarial_cases()
if not adv_cases:
    st.info("Belum ada hasil uji adversarial.")
else:
    n_match = sum(1 for c in adv_cases if c.get("match"))
    m1, m2 = st.columns(2)
    m1.metric("Kasus uji", len(adv_cases))
    m2.metric("Vonis sesuai harapan", f"{n_match}/{len(adv_cases)}")
    adv_rows = [
        {
            "Kasus": c.get("case_id", "—"),
            "Aturan diuji": c.get("rule_tested", "—"),
            "Skenario": (c.get("description") or "")[:90],
            "Harapan": c.get("expected_verdict", "—"),
            "Hasil": c.get("actual_verdict", "—"),
            "Status": "✅ sesuai" if c.get("match") else "❌ meleset",
        }
        for c in adv_cases
    ]
    st.dataframe(pd.DataFrame(adv_rows), width="stretch", hide_index=True)
    st.caption(f"Sumber: `{adv_file}`")
