"""Rincian per jurnal lintas tahap: apa yang terjadi pada tiap PDF dari awal
sampai akhir, dalam satu tabel — lalu bisa ditelusuri satu per satu.

Semua angka dihitung dari record lengkap keempat tahap, jadi totalnya sama
dengan corong per tahap. Kolom 'kandidat' & 'gap mentah' hanya ada bila job
menulis berkas kandidat (analisis setelah pembaruan).
"""

from __future__ import annotations

from collections import Counter, defaultdict

import pandas as pd
import streamlit as st

from research_common import fetch_all_records
from research_vocab import enum_label, label, mode_teknis

_GAP_TYPES = ("stated_limitation", "explicit_future_work", "implicit_gap")
_STATUSES = ("open", "partially_addressed", "addressed")


def _col(key: str, fallback: str) -> str:
    return key if mode_teknis() else fallback


def build_journal_table(job_id: str) -> tuple[pd.DataFrame, dict]:
    """Satu baris per jurnal; juga kembalikan record mentah per koleksi."""
    data = {c: fetch_all_records(job_id, c)
            for c in ("chunking", "candidates", "gap_mining", "novelty", "recommendation")}
    rows: dict[str, dict] = {}

    def row(src: str) -> dict:
        return rows.setdefault(src, {"source": src})

    for c in data["chunking"]:
        r = row(c.get("source"))
        r.setdefault("title", c.get("paper_title"))
        r.setdefault("year", c.get("year"))
        r.setdefault("language", c.get("language"))
        r.setdefault("quality", c.get("extraction_quality"))
        r["chunk"] = r.get("chunk", 0) + 1
        if not c.get("is_reference"):
            r["chunk_isi"] = r.get("chunk_isi", 0) + 1
        r["token"] = r.get("token", 0) + (c.get("token_count") or 0)
        secs = r.setdefault("_sections", Counter())
        secs[c.get("section_normalized") or "?"] += 1

    for c in data["candidates"]:
        r = row(c.get("source"))
        r["kandidat"] = r.get("kandidat", 0) + 1
        r["gap_mentah"] = r.get("gap_mentah", 0) + (c.get("gap_mentah") or 0)
        if not c.get("llm_answered", True):
            r["llm_kosong"] = r.get("llm_kosong", 0) + 1

    for g in data["gap_mining"]:
        r = row(g.get("source"))
        r["gap"] = r.get("gap", 0) + 1
        t = g.get("gap_type")
        if t in _GAP_TYPES:
            r[t] = r.get(t, 0) + 1

    for g in data["novelty"]:
        r = row(g.get("source"))
        s = g.get("novelty_status")
        if s in _STATUSES:
            r[s] = r.get(s, 0) + 1

    for p in data["recommendation"]:
        r = row(p.get("source"))
        r["proposal"] = r.get("proposal", 0) + 1
        sc = p.get("priority_score") or 0
        r["skor_maks"] = max(r.get("skor_maks", 0), sc)
        if p.get("rank") is not None:
            r["peringkat_terbaik"] = min(r.get("peringkat_terbaik", 10**9), p["rank"])
        if p.get("theme_id") is not None:
            r.setdefault("_themes", set()).add(p["theme_id"])

    out = []
    for src, r in rows.items():
        themes = r.pop("_themes", set())
        r.pop("_sections", None)
        r["tema"] = len(themes)
        if r.get("peringkat_terbaik", 10**9) == 10**9:
            r.pop("peringkat_terbaik", None)
        out.append(r)
    df = pd.DataFrame(out)
    return df, {"data": data, "sections": {s: rows[s].get("_sections") for s in rows}}


_DISPLAY = [
    ("source", "jurnal"), ("title", "judul"), ("year", "tahun"), ("quality", "kualitas"),
    ("chunk", "chunk"), ("chunk_isi", "chunk isi (non-pustaka)"), ("kandidat", "kandidat"),
    ("gap_mentah", "gap mentah"), ("gap", "gap final"),
    ("stated_limitation", "keterbatasan"), ("explicit_future_work", "saran lanjutan"),
    ("implicit_gap", "tersirat"), ("open", "open"), ("partially_addressed", "partially"),
    ("addressed", "addressed"), ("proposal", "proposal"), ("skor_maks", "skor maks"),
    ("peringkat_terbaik", "peringkat terbaik"), ("tema", "tema"), ("llm_kosong", "LLM kosong"),
]


def render_journal_crosstab(job_id: str) -> None:
    df, extra = build_journal_table(job_id)
    if df.empty:
        st.info("Belum ada record chunking untuk job ini.")
        return

    has_cands = bool(extra["data"]["candidates"])
    st.markdown(
        "Satu baris per jurnal, dari PDF sampai proposal. **Angka di tiap kolom adalah "
        "hitungan record**, bukan perkiraan — totalnya sama dengan corong di tab tahap.")
    if not has_cands:
        st.caption("Kolom kandidat & gap mentah tidak tersedia: analisis ini berjalan sebelum "
                   "jejak kandidat direkam.")

    cols = [k for k, _ in _DISPLAY if k in df.columns]
    show = df[cols].copy()
    show = show.sort_values(by=[c for c in ("gap", "chunk") if c in show.columns],
                            ascending=False)
    if not mode_teknis():
        show = show.rename(columns=dict(_DISPLAY))
        if "kualitas" in show:
            show["kualitas"] = show["kualitas"].map(
                lambda v: enum_label("extraction_quality", v).split(" (")[0] if v else v)
    for c in show.columns:
        if show[c].dtype.kind in "fi" and c not in ("skor maks", "skor_maks", "year", "tahun"):
            show[c] = show[c].fillna(0).astype(int)
    st.dataframe(show, width="stretch", hide_index=True,
                 column_config={
                     "skor maks": st.column_config.NumberColumn(format="%.4f"),
                     "skor_maks": st.column_config.NumberColumn(format="%.4f"),
                     "judul": st.column_config.TextColumn(width="large"),
                     "title": st.column_config.TextColumn(width="large"),
                 })

    total = {k: int(df[k].fillna(0).sum()) for k in ("chunk", "gap", "open", "proposal")
             if k in df.columns}
    st.caption("Total: " + " · ".join(f"{label(k)} **{v}**" for k, v in total.items()) +
               f" · jurnal **{len(df)}**" +
               (f" · jurnal tanpa gap **{int((df.get('gap', pd.Series()).fillna(0) == 0).sum())}**"
                if "gap" in df else ""))

    st.divider()
    _render_drilldown(df, extra)


def _render_drilldown(df: pd.DataFrame, extra: dict) -> None:
    st.markdown("**Telusuri satu jurnal**")
    sources = list(df["source"])
    titles = dict(zip(df["source"], df.get("title", df["source"])))
    src = st.selectbox("Jurnal", sources, key="jurnal_drill",
                       format_func=lambda s: f"{s} — {str(titles.get(s) or '')[:60]}")
    r = df[df["source"] == src].iloc[0].to_dict()
    data = extra["data"]

    k = st.columns(6)
    k[0].metric(label("chunk"), int(r.get("chunk") or 0))
    k[1].metric("kandidat", int(r.get("kandidat") or 0) if pd.notna(r.get("kandidat")) else "—")
    k[2].metric("gap final", int(r.get("gap") or 0) if pd.notna(r.get("gap")) else 0)
    k[3].metric("open", int(r.get("open") or 0) if pd.notna(r.get("open")) else 0)
    k[4].metric("proposal", int(r.get("proposal") or 0) if pd.notna(r.get("proposal")) else 0)
    k[5].metric("skor maks", f"{r.get('skor_maks'):.4f}" if pd.notna(r.get("skor_maks")) else "—")

    secs = extra["sections"].get(src) or Counter()
    if secs:
        sdf = pd.DataFrame([{"bagian": s, "chunk": n} for s, n in secs.most_common()])
        st.dataframe(sdf.set_index("bagian").T, width="stretch")

    tab_gap, tab_nov, tab_prop, tab_cand = st.tabs(
        ["🕳️ Gap", "🔭 Kebaruan", "🎯 Proposal", "🔍 Kandidat"])
    with tab_gap:
        gaps = [g for g in data["gap_mining"] if g.get("source") == src]
        if not gaps:
            st.caption("Tidak ada gap final dari jurnal ini.")
        for g in gaps:
            total = int(g.get("run_total") or 1)
            kn = ""
            if total > 1:
                kn = (f" · ✅ {g.get('run_hits')}/{total} run" if g.get("stable", True)
                      else f" · ⚠️ tidak stabil {g.get('run_hits')}/{total} run")
            st.markdown(f"- **{enum_label('gap_type', g.get('gap_type'))}** · "
                        f"{label('grounding_score')} {g.get('grounding_score')}{kn} — "
                        f"{g.get('gap_statement')}")
            if g.get("gap_paraphrase"):
                st.caption(f"  ↳ {g['gap_paraphrase']}")
    with tab_nov:
        novs = [g for g in data["novelty"] if g.get("source") == src]
        if not novs:
            st.caption("Belum ada hasil kebaruan untuk jurnal ini.")
        else:
            st.dataframe(pd.DataFrame([{
                "status": enum_label("novelty_status", g.get("novelty_status")),
                "paper terkait": len(g.get("related_recent_papers") or []),
                "kata kunci": g.get("novelty_query"),
                "gap": (g.get("gap_paraphrase") or g.get("gap_statement") or "")[:120],
            } for g in novs]), width="stretch", hide_index=True)
    with tab_prop:
        props = sorted([p for p in data["recommendation"] if p.get("source") == src],
                       key=lambda p: p.get("rank") or 0)
        if not props:
            st.caption("Tidak ada proposal dari jurnal ini (tidak ada gap open).")
        else:
            st.dataframe(pd.DataFrame([{
                "peringkat": p.get("rank"), "judul usulan": p.get("title"),
                "skor": p.get("priority_score"),
                "kebaruan": enum_label("band", p.get("band")),
                "tema": p.get("theme_id"),
            } for p in props]), width="stretch", hide_index=True)
    with tab_cand:
        cands = sorted([c for c in data["candidates"] if c.get("source") == src],
                       key=lambda c: c.get("chunk_index") or 0)
        if not cands:
            st.caption("Jejak kandidat tidak tersedia untuk analisis ini." if not data["candidates"]
                       else "Tidak ada kandidat dari jurnal ini.")
        else:
            st.dataframe(pd.DataFrame([{
                "chunk": c.get("chunk_index"), "bagian": c.get("section_normalized"),
                "alasan": c.get("candidate_reason"), "LLM menjawab": c.get("llm_answered"),
                "gap mentah": c.get("gap_mentah"), "lolos": c.get("gap_lolos"),
                "final": c.get("gap_final"),
            } for c in cands]), width="stretch", hide_index=True)
            st.caption("Rantai lengkap tiap kandidat (chunk → LLM → gap → verifikasi) ada di "
                       "tab **Penambangan Gap → Jejak per kandidat**.")
