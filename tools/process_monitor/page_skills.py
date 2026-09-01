"""🧠 Skill Riset — tulis ide, LLM memilih skill sendiri, hasilnya rekomendasi
penelitian LENGKAP (judul, latar belakang, metodologi + bagan, eksperimen, dll)."""

from __future__ import annotations

import textwrap

import pandas as pd
import requests
import streamlit as st

from common import api_base

PALETTE = ["#e3f2fd", "#fff3e0", "#ede7f6", "#e8f5e9", "#fce4ec", "#fffde7", "#e0f7fa"]


def recommend(idea: str) -> dict | None:
    try:
        r = requests.post(
            f"{api_base()}/skills/recommend", json={"idea": idea}, timeout=360
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        detail = ""
        if getattr(exc, "response", None) is not None:
            try:
                detail = exc.response.json().get("detail", "")
            except Exception:
                detail = exc.response.text[:200]
        st.session_state["skill_error"] = f"Gagal membuat rekomendasi: {detail or exc}"
        return None


def _esc(s: str) -> str:
    return str(s).replace('"', "'").replace("\n", " ")


def _norm_steps(raw) -> list[dict]:
    steps = []
    for item in raw or []:
        if isinstance(item, dict):
            steps.append(item)
        else:
            steps.append({"step": str(item)})
    return steps


def _dot_from_methodology(steps: list[dict]) -> str:
    lines = [
        "digraph metodologi {",
        "  rankdir=TB;",
        '  bgcolor="transparent";',
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11,',
        '        color="#555555", fontcolor="#111111", margin="0.22,0.12"];',
        '  edge [color="#888888", penwidth=1.2];',
    ]
    for i, s in enumerate(steps):
        name = _esc(s.get("step") or f"Tahap {i + 1}")
        desc = _esc((s.get("description") or "")[:110])
        label = f"{i + 1}. {name}"
        if desc:
            label += "\\n" + "\\n".join(textwrap.wrap(desc, 46))
        color = PALETTE[i % len(PALETTE)]
        lines.append(f'  s{i} [label="{label}", fillcolor="{color}"];')
    for i in range(len(steps) - 1):
        lines.append(f"  s{i} -> s{i + 1};")
    lines.append("}")
    return "\n".join(lines)


def _listify(raw) -> list[str]:
    out = []
    for item in raw or []:
        if isinstance(item, dict):
            out.append(" — ".join(str(v) for v in item.values() if v))
        elif str(item).strip():
            out.append(str(item).strip())
    return out


st.title("🧠 Skill Riset")
st.caption(
    "Tulis ide penelitian Anda → **LLM memilih sendiri** skill paling relevan dari "
    "95 [AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) "
    "yang terpasang → menyusun **rekomendasi penelitian lengkap**: judul, latar "
    "belakang, rumusan masalah, metodologi (dengan bagan), eksperimen, kontribusi, "
    "risiko, dan kata kunci literatur."
)

if err := st.session_state.pop("skill_error", None):
    st.error(err)

idea = st.text_area(
    "Ide penelitian Anda (boleh Bahasa Indonesia)",
    value=st.session_state.get("skill_idea", ""),
    height=110,
    placeholder=(
        "contoh: Pengembangan sistem ekstraksi struk belanja otomatis menggunakan "
        "OCR dan LLM untuk membantu pencatatan keuangan pribadi"
    ),
)

if st.button(
    "✨ Buat Rekomendasi Penelitian",
    type="primary",
    disabled=len(idea.strip()) < 10,
    help="LLM akan memilih skill relevan lalu menyusun rekomendasi lengkap (±30–90 detik)",
):
    st.session_state["skill_idea"] = idea
    with st.spinner("LLM sedang memilih skill & menyusun rekomendasi penelitian… (±30–90 detik)"):
        result = recommend(idea.strip())
    if result:
        st.session_state["skill_reco"] = result
    st.rerun()

data = st.session_state.get("skill_reco")
if not data:
    st.info("💡 Masukkan ide di atas — hasilnya rekomendasi penelitian lengkap, bukan sekadar judul.")
    st.stop()

rec = data.get("recommendation") or {}
skills_used = data.get("skills_used") or []

# ── Skill yang dipilih LLM ────────────────────────────────────────────────────
chips = " ".join(f"`{s.get('name') or s.get('id')}`" for s in skills_used)
st.success(f"🤖 **LLM memilih skill:** {chips}")
reason = data.get("routing_reason") or ""
if reason:
    st.caption(f"Alasan pemilihan: {reason}")
st.caption(f"Engine: **{data.get('engine', '?')}**")

st.divider()

# ── Judul & latar belakang ────────────────────────────────────────────────────
if rec.get("title"):
    st.header(f"📌 {rec['title']}")
if rec.get("background"):
    st.markdown(rec["background"])

col_masalah, col_tujuan = st.columns(2)
with col_masalah:
    if items := _listify(rec.get("problem_statements")):
        st.subheader("❓ Rumusan Masalah")
        for i, t in enumerate(items, 1):
            st.markdown(f"{i}. {t}")
with col_tujuan:
    if items := _listify(rec.get("objectives")):
        st.subheader("🎯 Tujuan Penelitian")
        for i, t in enumerate(items, 1):
            st.markdown(f"{i}. {t}")

# ── Metodologi + bagan ────────────────────────────────────────────────────────
steps = _norm_steps(rec.get("methodology"))
if steps:
    st.subheader("🗺️ Bagan Alur Metodologi")
    st.graphviz_chart(_dot_from_methodology(steps))
    for i, s in enumerate(steps, 1):
        with st.expander(f"Tahap {i} — {s.get('step', '')}"):
            if s.get("description"):
                st.markdown(s["description"])
            if s.get("tools"):
                st.caption(f"🛠️ Tools: {s['tools']}")

# ── Eksperimen ────────────────────────────────────────────────────────────────
exps = [e for e in (rec.get("experiments") or []) if isinstance(e, dict)]
if exps:
    st.subheader("🧪 Rencana Eksperimen")
    df = pd.DataFrame(
        [
            {
                "Eksperimen": e.get("name", ""),
                "Desain": e.get("design", ""),
                "Metrik": e.get("metrics", ""),
            }
            for e in exps
        ]
    )
    st.dataframe(df, hide_index=True, width="stretch")

col_kontrib, col_risiko = st.columns(2)
with col_kontrib:
    if items := _listify(rec.get("contributions")):
        st.subheader("🏆 Kontribusi")
        for t in items:
            st.markdown(f"- {t}")
with col_risiko:
    if items := _listify(rec.get("risks")):
        st.subheader("⚠️ Risiko & Mitigasi")
        for t in items:
            st.markdown(f"- {t}")

# ── Kata kunci → Cari Paper ───────────────────────────────────────────────────
keywords = [str(k) for k in (rec.get("keywords") or []) if str(k).strip()]
if keywords:
    st.subheader("🔎 Kata Kunci Literatur")
    st.markdown(" ".join(f"`{k}`" for k in keywords))
    if st.button("🔎 Cari paper dengan kata kunci ini", type="secondary"):
        st.session_state["paper_query"] = " ".join(keywords[:3])
        st.session_state["paper_mode"] = "🔑 Kata kunci langsung"
        st.switch_page("page_papers.py")
