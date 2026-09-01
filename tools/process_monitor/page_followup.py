"""🚀 Tindak Lanjut — proses SETELAH gap ditemukan: usulan → peta jalan → rencana."""

import streamlit as st

from common import (
    _FETCH_FAILED,
    GAP_TYPE_BADGES,
    JOB_STATUS_BADGES,
    _render_gap_lenses,
    fetch_jobs,
    fetch_status,
    fmt_datetime,
    render_gap_confidence,
    render_gap_method_explainer,
    render_novelty_badge,
)

PRIORITY_BADGES = {
    "high": "🔥 Prioritas tinggi",
    "medium": "🟠 Prioritas sedang",
    "low": "🟢 Prioritas rendah",
}

st.title("🚀 Tindak Lanjut Gap")
st.caption(
    "Proses **setelah gap ditemukan**: ① pilih gap yang mau dijawab → ② baca usulan "
    "penelitian yang menjawabnya → ③ ikuti peta jalan → ④ kembangkan jadi rencana "
    "penelitian lengkap (judul, rumusan masalah, metodologi) di halaman 🧠 Skill Riset."
)
st.markdown(
    "📚 Jurnal → ⚠️ Kekurangan → 🕳️ **Gap** → 💡 **Usulan** → 🗺️ **Peta Jalan** → "
    "🧠 **Rencana Penelitian**"
)

if err := st.session_state.pop("last_error", None):
    st.error(err)

# ── Pilih job ──
jobs = [
    j for j in fetch_jobs(limit=30)
    if j.get("status") == "completed" and (j.get("files_processed") or 0) > 0
]
if not jobs:
    st.info("Belum ada analisis yang selesai. Unggah jurnal di halaman 🔬 Proses & Hasil.")
    st.stop()

options = [j["job_id"] for j in jobs]
active = st.session_state.get("job_id", "")
default_idx = options.index(active) if active in options else 0


def _label(jid: str) -> str:
    job = next(j for j in jobs if j["job_id"] == jid)
    icon, _, _ = JOB_STATUS_BADGES.get(job.get("status", ""), ("❔", "?", "gray"))
    model = f" · {job['model']}" if job.get("model") else ""
    return (
        f"{icon} {jid[:8]}… · {fmt_datetime(job.get('created_at'))} · "
        f"{job.get('files_processed', '?')} jurnal{model}"
    )


selected = st.selectbox("Pilih analisis", options, index=default_idx, format_func=_label)
if selected != active:
    st.session_state["job_id"] = selected

status = fetch_status(selected)
if status is _FETCH_FAILED or not status:
    st.warning("Tidak bisa memuat hasil job ini.")
    st.stop()

results = status.get("results") or {}
gaps = results.get("gaps") or []
recs = results.get("recommendations") or []
roadmap = results.get("roadmap") or []

if not gaps:
    st.warning("Job ini belum punya gap penelitian — jalankan 🔁 analisis ulang dulu.")
    st.stop()


def _short(text, limit: int = 90) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ── ① Pilih gap ──
st.divider()
st.subheader("① Pilih gap yang mau dijawab")


def _gap_label(i: int) -> str:
    gap = gaps[i]
    badge = GAP_TYPE_BADGES.get(str(gap.get("type", "")).upper(), gap.get("type", ""))
    return f"{i + 1}. {badge} — {_short(gap.get('title') or gap.get('description'))}"


gap_idx = st.selectbox(
    "Gap dari analisis ini",
    range(len(gaps)),
    format_func=_gap_label,
    key="followup_gap",
)
gap = gaps[gap_idx]
gap_type = str(gap.get("type", "")).upper()
gap_badge = GAP_TYPE_BADGES.get(gap_type, gap.get("type", ""))

with st.container(border=True):
    conf = gap.get("confidence")
    conf_txt = f" · keyakinan {round(float(conf) * 100)}%" if conf else ""
    st.markdown(f"**{gap_badge}**{conf_txt}")
    st.markdown(gap.get("description") or "_(tanpa deskripsi)_")
    render_gap_confidence(gap)
    _render_gap_lenses(gap, results.get("papers_info") or [])
    refs = [r for r in (gap.get("related_papers") or []) if str(r).strip()]
    if refs:
        shown = ", ".join(f"`{r}`" for r in refs[:8])
        extra = f" … dan {len(refs) - 8} lainnya" if len(refs) > 8 else ""
        st.caption(f"📄 Jurnal yang terlibat: {shown}{extra}")
    for d in gap.get("suggested_directions") or []:
        st.caption(f"🧭 Arah yang disarankan: {d}")
    if st.button(
        "🔎 Cari jurnal baru untuk menguji gap ini",
        key="followup_search_gap",
        help="Buka halaman Cari Paper dengan ide pencarian sudah terisi dari gap ini",
    ):
        idea = (
            f"Cari literatur untuk menguji gap penelitian berikut ({gap_badge}): "
            f"{_short(gap.get('description'), 350)} "
        )
        dirs = gap.get("suggested_directions") or []
        if dirs:
            idea += "Arah yang dicari: " + "; ".join(str(d) for d in dirs[:2])
        st.session_state["paper_idea"] = " ".join(idea.split())
        st.session_state["paper_mode"] = "💡 Ide penelitian (AI ubah jadi kata kunci)"
        for k in ("paper_results", "paper_generated", "paper_selected"):
            st.session_state.pop(k, None)
        st.switch_page("page_papers.py")
    st.caption(
        "💡 Uji validitas gap: bila jurnal baru ternyata **sudah menutup** aspek ini, "
        "gap melemah (baik diketahui sekarang); bila **tidak ada**, klaim gap Anda "
        "makin kuat — plus dapat referensi segar untuk proposal."
    )

render_gap_method_explainer()

# ── ② Usulan yang menjawab gap ini ──
st.divider()
st.subheader("② Usulan penelitian yang menjawab gap ini")

matched = [r for r in recs if str(r.get("gap_type", "")).upper() == gap_type]
if not matched and recs:
    st.caption(
        "_(tidak ada usulan yang bertipe sama persis — menampilkan semua usulan)_"
    )
    matched = recs
if not matched:
    st.info("Job ini belum punya usulan penelitian.")

for ri, rec in enumerate(matched):
    with st.container(border=True):
        prio = PRIORITY_BADGES.get(str(rec.get("priority", "")).lower(), "")
        title = rec.get("title") or "(tanpa judul)"
        st.markdown(f"**💡 {title}**" + (f" · {prio}" if prio else ""))
        if rec.get("description"):
            st.markdown(rec["description"])
        if rec.get("why"):
            st.caption(f"❓ Mengapa penting: {rec['why']}")
        if rec.get("how"):
            st.caption(f"🛠️ Bagaimana: {rec['how']}")
        render_novelty_badge(rec)
        if st.button(
            "🧠 Kembangkan jadi rencana penelitian lengkap",
            key=f"followup_dev_{ri}",
            help="Buka halaman Skill Riset dengan ide ini sudah terisi — tinggal klik ✨",
        ):
            idea = (
                f"{title}. {rec.get('description', '')} "
                f"Penelitian ini menjawab gap sintesis ({gap_badge}): "
                f"{_short(gap.get('description'), 300)} "
            )
            if rec.get("how"):
                idea += f"Pendekatan yang dipertimbangkan: {rec['how']}"
            st.session_state["skill_idea"] = " ".join(idea.split())
            st.session_state.pop("skill_reco", None)
            st.switch_page("page_skills.py")

# ── ③ Peta jalan ──
st.divider()
st.subheader("③ Peta jalan pelaksanaan")
if roadmap:
    cols = st.columns(len(roadmap)) if 2 <= len(roadmap) <= 3 else [st] * len(roadmap)
    for col, phase in zip(cols, roadmap):
        with col.container(border=True):
            st.markdown(f"**🗓️ {phase.get('phase', '')}**")
            for item in phase.get("items", []):
                st.markdown(f"- {item}")
else:
    st.info("Job ini belum punya peta jalan.")

# ── ④ Bawa pulang ──
st.divider()
st.subheader("④ Bawa pulang")
st.caption(
    "Unduh paket tindak lanjut (gap terpilih + usulan + peta jalan) sebagai Markdown — "
    "siap ditempel ke draf proposal/tesis."
)


def _followup_md() -> str:
    lines = [
        "# Tindak Lanjut Gap Penelitian",
        f"Job `{selected}` · {fmt_datetime(status.get('created_at'))} · "
        f"{results.get('files_processed', '?')} jurnal",
        "",
        f"## Gap terpilih — {gap_badge}",
        gap.get("description") or "",
    ]
    refs = [r for r in (gap.get("related_papers") or []) if str(r).strip()]
    if refs:
        lines += ["", "Jurnal yang terlibat:"] + [f"- {r}" for r in refs]
    dirs = gap.get("suggested_directions") or []
    if dirs:
        lines += ["", "Arah yang disarankan:"] + [f"- {d}" for d in dirs]
    lines += ["", "## Usulan penelitian yang menjawab"]
    for i, rec in enumerate(matched, start=1):
        prio = PRIORITY_BADGES.get(str(rec.get("priority", "")).lower(), "")
        lines += ["", f"### {i}. {rec.get('title') or '(tanpa judul)'}"]
        if prio:
            lines.append(f"_{prio}_")
        if rec.get("description"):
            lines.append(rec["description"])
        if rec.get("why"):
            lines.append(f"- **Mengapa:** {rec['why']}")
        if rec.get("how"):
            lines.append(f"- **Bagaimana:** {rec['how']}")
    if roadmap:
        lines += ["", "## Peta jalan"]
        for phase in roadmap:
            lines += ["", f"### {phase.get('phase', '')}"]
            lines += [f"- {item}" for item in phase.get("items", [])]
    return "\n".join(lines) + "\n"


st.download_button(
    "📥 Unduh paket tindak lanjut (.md)",
    data=_followup_md(),
    file_name=f"tindak_lanjut_{selected[:8]}_gap{gap_idx + 1}.md",
    mime="text/markdown",
)
st.page_link(
    "page_skills.py",
    label="Atau langsung ke 🧠 Skill Riset untuk menyusun rencana dari ide sendiri",
    icon="🧠",
)
