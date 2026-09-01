"""📚 Jurnal & Gap — halaman khusus membaca 35 jurnal beserta gap-nya satu per satu."""

import streamlit as st

from common import (
    _FETCH_FAILED,
    GAP_TYPE_BADGES,
    JOB_STATUS_BADGES,
    _render_weak_points,
    fetch_jobs,
    fetch_status,
    fmt_datetime,
    md_bold,
)

st.title("📚 Jurnal & Gap-nya")
st.caption(
    "Halaman baca per jurnal: kekurangan **tersurat** (ditulis penulisnya, dengan "
    "kutipan) dan **tersirat** (disimpulkan sistem), plus **gap kolektif** yang "
    "melibatkan jurnal tersebut."
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
    icon, label, _ = JOB_STATUS_BADGES.get(job.get("status", ""), ("❔", "?", "gray"))
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
weaknesses = results.get("paper_weaknesses") or []
gaps = results.get("gaps") or []
papers_info = results.get("papers_info") or []

if not weaknesses:
    st.warning("Job ini belum punya analisis kekurangan per jurnal.")
    st.stop()

year_by_source = {p.get("source"): p.get("year") for p in papers_info if p.get("source")}


def _norm(text) -> str:
    return " ".join(str(text or "").split()).lower()


def _gaps_for(weak: dict) -> list[tuple[int, dict]]:
    """Gap kolektif yang menyebut jurnal ini di related_papers (cocok via file/judul)."""
    keys = {_norm(weak.get("source")), _norm(weak.get("title"))} - {""}
    hits = []
    for gi, gap in enumerate(gaps, start=1):
        refs = {_norm(r) for r in (gap.get("related_papers") or [])}
        if keys & refs:
            hits.append((gi, gap))
    return hits


journals = []
for i, w in enumerate(weaknesses):
    journals.append({
        "no": i + 1,
        "weak": w,
        "title": w.get("title") or w.get("source") or f"Paper {i+1}",
        "source": w.get("source") or "",
        "year": year_by_source.get(w.get("source"), ""),
        "n_tersurat": len(w.get("tersurat") or []),
        "n_tersirat": len(w.get("tersirat") or []),
        "gap_hits": _gaps_for(w),
    })

# ── Metrik ──
m1, m2, m3, m4 = st.columns(4)
m1.metric("📄 Jurnal", len(journals))
m2.metric("✍️ Kekurangan tersurat", sum(j["n_tersurat"] for j in journals))
m3.metric("💭 Kekurangan tersirat", sum(j["n_tersirat"] for j in journals))
m4.metric("🕳️ Terlibat gap kolektif", sum(1 for j in journals if j["gap_hits"]))
if gaps and not any(j["gap_hits"] for j in journals):
    st.caption(
        "ℹ️ Gap kolektif pada run ini belum menyebut jurnal per nama — jalankan "
        "🔁 Analisis Ulang dari Dashboard agar keterkaitan jurnal ↔ gap terisi."
    )

# ── Toolbar: cari / saring / urut ──
c_search, c_filter, c_sort = st.columns([2, 1, 1])
query = c_search.text_input("🔍 Cari jurnal", placeholder="judul atau nama file…")
flt = c_filter.selectbox(
    "Saring",
    ["Semua", "Punya tersurat", "Punya tersirat", "Terlibat gap kolektif", "Tanpa temuan"],
)
sort = c_sort.selectbox("Urutkan", ["Urutan file", "Kekurangan terbanyak", "Judul A-Z"])

shown = journals
if query:
    q = _norm(query)
    shown = [j for j in shown if q in _norm(j["title"]) or q in _norm(j["source"])]
if flt == "Punya tersurat":
    shown = [j for j in shown if j["n_tersurat"]]
elif flt == "Punya tersirat":
    shown = [j for j in shown if j["n_tersirat"]]
elif flt == "Terlibat gap kolektif":
    shown = [j for j in shown if j["gap_hits"]]
elif flt == "Tanpa temuan":
    shown = [j for j in shown if not (j["n_tersurat"] or j["n_tersirat"])]
if sort == "Kekurangan terbanyak":
    shown = sorted(shown, key=lambda j: j["n_tersurat"] + j["n_tersirat"], reverse=True)
elif sort == "Judul A-Z":
    shown = sorted(shown, key=lambda j: _norm(j["title"]))

# ── Ringkasan tabel + unduh CSV ──
rows = [
    {
        "No": j["no"],
        "Jurnal": j["title"],
        "File": j["source"],
        "Tahun": j["year"],
        "Tersurat": j["n_tersurat"],
        "Tersirat": j["n_tersirat"],
        "Gap terkait": ", ".join(f"Gap {gi}" for gi, _ in j["gap_hits"]) or "—",
    }
    for j in shown
]
with st.expander(f"📋 Tabel ringkasan ({len(shown)} jurnal)", expanded=False):
    st.dataframe(rows, width="stretch", hide_index=True)
    csv_lines = ["No;Jurnal;File;Tahun;Tersurat;Tersirat;Gap terkait"]
    for r in rows:
        csv_lines.append(";".join(str(r[k]).replace(";", ",") for k in
                                  ("No", "Jurnal", "File", "Tahun", "Tersurat", "Tersirat", "Gap terkait")))
    st.download_button(
        "⬇️ Unduh CSV (untuk lampiran tesis)",
        data="\n".join(csv_lines).encode("utf-8"),
        file_name=f"gap_per_jurnal_{selected[:8]}.csv",
        mime="text/csv",
    )

st.caption(f"Menampilkan **{len(shown)}** dari {len(journals)} jurnal — klik kartu untuk membuka detail.")

# ── Kartu per jurnal ──
for j in shown:
    gap_txt = f" · 🕳️ {len(j['gap_hits'])} gap" if j["gap_hits"] else ""
    label = (
        f"{j['no']}. {j['title'][:75]} — "
        f"✍️ {j['n_tersurat']} tersurat · 💭 {j['n_tersirat']} tersirat{gap_txt}"
    )
    with st.expander(label):
        meta_bits = [f"📄 {j['source']}"] if j["source"] else []
        if j["year"]:
            meta_bits.append(f"tahun {j['year']}")
        if meta_bits:
            st.caption(" · ".join(meta_bits))

        st.markdown(md_bold("Kekurangan jurnal ini"))
        _render_weak_points(j["weak"])

        if j["gap_hits"]:
            st.markdown(md_bold("Gap kolektif yang melibatkan jurnal ini"))
            for gi, gap in j["gap_hits"]:
                badge = GAP_TYPE_BADGES.get(str(gap.get("type", "")).upper(), gap.get("type", ""))
                desc = " ".join(str(gap.get("description") or "").split())
                st.markdown(f"- **Gap {gi}** {badge} — {desc[:220]}{'…' if len(desc) > 220 else ''}")
            st.caption("Detail lengkap tiap gap ada di halaman 🔬 Proses & Hasil → tab 🕳️ Gap Penelitian.")
