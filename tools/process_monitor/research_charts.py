"""Grafik per tahap dan ikhtisar pipeline (Altair, render di browser).

Semua grafik dibangun dari record lengkap (``fetch_all_records``), bukan dari
8 baris contoh, sehingga angkanya sama dengan yang ada di tabel dan bisa
dikutip di BAB IV. Tiap grafik memakai label awam/teknis dari research_vocab.
"""

from __future__ import annotations

from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st

from common import fmt_duration
from research_common import fetch_all_records, substep_states
from research_vocab import ENUM_LABELS, enum_label, label, mode_teknis

_SHORT = 28  # panjang nama jurnal pada sumbu agar tidak memakan lebar grafik


def _short(name: str | None) -> str:
    name = str(name or "?")
    return name if len(name) <= _SHORT else name[:_SHORT - 1] + "…"


def _enum_col(df: pd.DataFrame, field: str) -> pd.Series:
    """Kolom enum dengan label awam (mode teknis: nilai asli)."""
    if field in ENUM_LABELS and not mode_teknis():
        return df[field].map(lambda v: enum_label(field, v))
    return df[field].astype(str)


def _bar(df: pd.DataFrame, x: str, y: str, color: str | None = None, title: str = "",
         horizontal: bool = False, sort: str = "-y") -> alt.Chart:
    enc = {
        "x": alt.X(f"{x}:N", sort=sort, title=label(x) if x in df else x),
        "y": alt.Y(f"{y}:Q", title=y),
        "tooltip": [c for c in df.columns],
    }
    if horizontal:
        enc["x"], enc["y"] = alt.X(f"{y}:Q", title=y), alt.Y(f"{x}:N", sort="-x", title=None)
    if color:
        enc["color"] = alt.Color(f"{color}:N", title=color)
    return alt.Chart(df, title=title).mark_bar().encode(**enc).properties(height=260)


def _hist(df: pd.DataFrame, col: str, title: str, bins: int = 25,
          color: str | None = None, rule: float | None = None) -> alt.Chart:
    base = alt.Chart(df, title=title).mark_bar().encode(
        x=alt.X(f"{col}:Q", bin=alt.Bin(maxbins=bins), title=label(col)),
        y=alt.Y("count():Q", title="jumlah"),
        tooltip=[alt.Tooltip("count():Q", title="jumlah")],
    )
    if color:
        base = base.encode(color=alt.Color(f"{color}:N", title=label(color)))
    chart = base.properties(height=240)
    if rule is not None:
        chart = chart + alt.Chart(pd.DataFrame({"v": [rule]})).mark_rule(
            color="red", strokeDash=[4, 4]).encode(x="v:Q")
    return chart


def _show(chart: alt.Chart, caption: str = "") -> None:
    st.altair_chart(chart, width="stretch")
    if caption:
        st.caption(caption)


# ── per tahap ──────────────────────────────────────────────────────────────

def render_stage_charts(job_id: str, stage_key: str, events: list[dict]) -> None:
    fn = {
        "chunking": _charts_chunking,
        "gap_mining": _charts_gap_mining,
        "novelty": _charts_novelty,
        "recommendation": _charts_recommendation,
    }.get(stage_key)
    if fn is None:
        st.info("Tidak ada grafik untuk tahap ini.")
        return
    fn(job_id)
    _durations_chart(events, stage_key)


def _charts_chunking(job_id: str) -> None:
    rows = fetch_all_records(job_id, "chunking")
    if not rows:
        st.info("Record chunking tidak tersedia untuk job ini.")
        return
    df = pd.DataFrame(rows)
    df["jurnal"] = df["source"].map(_short)
    df["bagian"] = _enum_col(df, "section_normalized") if "section_normalized" in df else "?"

    c1, c2 = st.columns(2)
    with c1:
        _show(_hist(df, "token_count", "Sebaran ukuran chunk (token)", rule=150),
              "Garis merah = 150 token; chunk di bawahnya biasanya sisa judul palsu atau tabel.")
    with c2:
        sec = df.groupby("bagian").size().reset_index(name="chunk")
        _show(_bar(sec, "bagian", "chunk", title="Chunk per bagian jurnal", horizontal=True),
              "Bagian 'other' yang besar berarti struktur jurnal tidak terdeteksi.")
    per_j = df.groupby(["jurnal", "bagian"]).size().reset_index(name="chunk")
    _show(_bar(per_j, "jurnal", "chunk", color="bagian", title="Chunk per jurnal, diwarnai bagian"),
          "Jurnal dengan porsi 'references' besar berarti daftar pustakanya panjang; chunk itu "
          "dikecualikan dari pencarian gap.")


def _charts_gap_mining(job_id: str) -> None:
    gaps = fetch_all_records(job_id, "gap_mining")
    cands = fetch_all_records(job_id, "candidates")
    if not gaps and not cands:
        st.info("Record gap tidak tersedia untuk job ini.")
        return

    if cands:
        cdf = pd.DataFrame(cands)
        cdf["jurnal"] = cdf["source"].map(_short)
        reasons = Counter()
        for r in cdf["candidate_reason"].fillna(""):
            for part in str(r).split(","):
                if part:
                    reasons[part] += 1
        c1, c2 = st.columns(2)
        with c1:
            rdf = pd.DataFrame([{"alasan": k, "kandidat": v} for k, v in reasons.items()])
            _show(_bar(rdf, "alasan", "kandidat", title="Kenapa chunk jadi kandidat",
                       horizontal=True),
                  "Satu kandidat bisa punya lebih dari satu alasan. 'section:conclusion' dan "
                  "'phrase' (pola kata) adalah jalur utama; 'tail'/'abstract'/'introduction' "
                  "aturan cadangan.")
        with c2:
            y = cdf.groupby("jurnal").agg(kandidat=("chunk_id", "count"),
                                           gap_mentah=("gap_mentah", "sum"),
                                           gap_final=("gap_final", "sum")).reset_index()
            m = y.melt("jurnal", var_name="ukuran", value_name="jumlah")
            _show(alt.Chart(m, title="Kandidat → gap mentah → gap final, per jurnal")
                  .mark_bar().encode(
                      x=alt.X("jurnal:N", title=None),
                      y=alt.Y("jumlah:Q"),
                      color=alt.Color("ukuran:N", title=None),
                      xOffset="ukuran:N",
                      tooltip=["jurnal", "ukuran", "jumlah"]).properties(height=260),
                  "Jurnal yang kandidatnya banyak tetapi gap finalnya sedikit: LLM tidak "
                  "menemukan pernyataan gap eksplisit di sana.")
        gpc = cdf["gap_mentah"].value_counts().sort_index().reset_index()
        gpc.columns = ["gap per kandidat", "kandidat"]
        gpc["gap per kandidat"] = gpc["gap per kandidat"].astype(str)
        _show(_bar(gpc, "gap per kandidat", "kandidat",
                   title="Berapa gap yang dikembalikan LLM per kandidat", sort=None),
              "Kandidat dengan 0 gap normal: tidak semua kesimpulan memuat keterbatasan.")

    if gaps:
        gdf = pd.DataFrame(gaps)
        gdf["jurnal"] = gdf["source"].map(_short)
        gdf["jenis"] = _enum_col(gdf, "gap_type")
        gdf["topik"] = _enum_col(gdf, "topic")
        c1, c2 = st.columns(2)
        with c1:
            per_j = gdf.groupby(["jurnal", "jenis"]).size().reset_index(name="gap")
            _show(_bar(per_j, "jurnal", "gap", color="jenis", title="Gap final per jurnal & jenis"))
        with c2:
            top = gdf.groupby("topik").size().reset_index(name="gap")
            _show(_bar(top, "topik", "gap", title="Gap per topik", horizontal=True))
        if "grounding_score" in gdf:
            _show(_hist(gdf, "grounding_score", "Sebaran skor kecocokan verbatim (gap final)",
                        bins=20),
                  "Semua gap final berada di atas ambang; skor 1,0 berarti kalimat ditemukan "
                  "persis di jurnal.")


def _charts_novelty(job_id: str) -> None:
    rows = fetch_all_records(job_id, "novelty")
    if not rows:
        st.info("Record kebaruan tidak tersedia untuk job ini.")
        return
    df = pd.DataFrame(rows)
    df["jurnal"] = df["source"].map(_short)
    df["status"] = _enum_col(df, "novelty_status")
    c1, c2 = st.columns(2)
    with c1:
        s = df.groupby("status").size().reset_index(name="gap")
        _show(_bar(s, "status", "gap", title="Status kebaruan semua gap", horizontal=True),
              "'open' tinggi bisa berarti benar-benar baru — atau OpenAlex sedang membatasi "
              "permintaan (lihat 'tanpa paper terkait').")
    with c2:
        per_j = df.groupby(["jurnal", "status"]).size().reset_index(name="gap")
        _show(_bar(per_j, "jurnal", "gap", color="status", title="Status kebaruan per jurnal"))

    papers = []
    for r in rows:
        for p in r.get("related_recent_papers") or []:
            if isinstance(p, dict):
                papers.append({"match_score": p.get("match_score"), "year": p.get("year"),
                               "status": r.get("novelty_status")})
    if papers:
        pdf_ = pd.DataFrame(papers).dropna(subset=["match_score"])
        pdf_["status"] = _enum_col(pdf_, "status") if "status" in ENUM_LABELS else pdf_["status"]
        c1, c2 = st.columns(2)
        with c1:
            _show(_hist(pdf_, "match_score", "Skor kecocokan paper 2024+ yang ditemukan",
                        bins=20, rule=0.5),
                  "Garis merah = ambang 'strong match' (0,5). Hanya paper di kanannya yang "
                  "dihitung untuk status partially/addressed.")
        with c2:
            yr = pdf_.dropna(subset=["year"]).groupby("year").size().reset_index(name="paper")
            yr["year"] = yr["year"].astype(int).astype(str)
            _show(_bar(yr, "year", "paper", title="Tahun terbit paper terkait", sort=None))
    else:
        st.caption("Tidak ada paper terkait yang tersimpan — pencarian OpenAlex kosong.")


def _charts_recommendation(job_id: str) -> None:
    props = fetch_all_records(job_id, "recommendation")
    if not props:
        st.info("Record proposal tidak tersedia untuk job ini.")
        return
    df = pd.DataFrame(props)
    df["jurnal"] = df["source"].map(_short)
    df["kategori"] = _enum_col(df, "band") if "band" in df else "?"
    c1, c2 = st.columns(2)
    with c1:
        _show(_hist(df, "priority_score", "Sebaran skor prioritas", bins=20, color="kategori"),
              "Skor maksimum 1,0. Tumpukan di satu nilai berarti banyak seri — dipecah oleh "
              "jarak kebaruan ke tengah sweet spot.")
    with c2:
        if {"novelty", "actionability"} <= set(df.columns):
            sc = alt.Chart(df, title="Kebaruan × keterlaksanaan (ukuran = skor prioritas)")
            sc = sc.mark_circle(opacity=0.7).encode(
                x=alt.X("novelty:Q", title=label("novelty")),
                y=alt.Y("actionability:Q", title=label("actionability")),
                size=alt.Size("priority_score:Q", title=label("priority_score")),
                color=alt.Color("kategori:N", title=None),
                tooltip=["rank", "title", "jurnal", "priority_score", "novelty", "actionability"],
            ).properties(height=260)
            band = alt.Chart(pd.DataFrame({"lo": [0.25], "hi": [0.65]})).mark_rect(
                opacity=0.08, color="green").encode(x="lo:Q", x2="hi:Q")
            _show(band + sc, "Pita hijau = sweet spot kebaruan (0,25–0,65).")
    if "theme_id" in df:
        t = df.groupby(["theme_id", "theme_label"]).agg(
            anggota=("rank", "count"), jurnal=("source", "nunique"),
            skor_maks=("priority_score", "max")).reset_index()
        t["tema"] = t.apply(lambda r: f"#{r['theme_id']} {_short(r['theme_label'])}", axis=1)
        t = t.sort_values(["jurnal", "anggota"], ascending=False).head(25)
        _show(alt.Chart(t, title="Tema: anggota vs jurnal pendukung (25 teratas)")
              .mark_bar().encode(
                  y=alt.Y("tema:N", sort="-x", title=None),
                  x=alt.X("anggota:Q", title="anggota (gap)"),
                  color=alt.Color("jurnal:Q", title="jurnal pendukung",
                                  scale=alt.Scale(scheme="blues")),
                  tooltip=["tema", "anggota", "jurnal", "skor_maks"]).properties(
                      height=max(200, 18 * len(t))),
              "Tema beranggota satu = gap yang tidak mirip gap lain mana pun. Pada tema besar, "
              "jumlah jurnal adalah batas atas (single-linkage bisa merantai topik berbeda).")


def _durations_chart(events: list[dict], stage_key: str) -> None:
    subs = substep_states(events, stage_key)
    rows = [{"sub-langkah": k, "detik": (v.get("duration_ms") or 0) / 1000}
            for k, v in subs.items() if v.get("duration_ms")]
    if len(rows) < 2:
        return
    df = pd.DataFrame(rows)
    _show(_bar(df, "sub-langkah", "detik", title="Waktu per sub-langkah (detik)",
               horizontal=True))


# ── ikhtisar seluruh pipeline ──────────────────────────────────────────────

def render_overview_charts(stages: list[dict], payloads: dict[str, dict],
                           events: list[dict]) -> None:
    """Corong angka lintas tahap + durasi per tahap/sub-langkah."""
    funnel = []
    order = 0
    for stage in stages:
        metrics = (payloads.get(stage["key"]) or {}).get("metrics") or {}
        for sub in stage.get("substeps") or []:
            if sub.get("inside") or sub.get("jenis") == "periksa":
                continue
            out_key = sub.get("out_metric")
            val = metrics.get(out_key) if out_key else None
            if isinstance(val, (int, float)):
                order += 1
                funnel.append({"urut": order, "langkah": f"{order}. {sub['label']}",
                               "tahap": stage["title"], "jumlah": val,
                               "metrik": out_key})
    if funnel:
        fdf = pd.DataFrame(funnel)
        _show(alt.Chart(fdf, title="Corong: berapa yang keluar dari tiap sub-langkah")
              .mark_bar().encode(
                  y=alt.Y("langkah:N", sort=alt.EncodingSortField("urut"), title=None),
                  x=alt.X("jumlah:Q", title="jumlah"),
                  color=alt.Color("tahap:N", title=None),
                  tooltip=["langkah", "tahap", "jumlah", "metrik"]).properties(
                      height=max(220, 24 * len(fdf))),
              "Angka keluar tiap sub-langkah, berurutan. Kenaikan di 'LLM menyalin' normal: satu "
              "kandidat bisa memuat beberapa gap.")

    dur = []
    for stage in stages:
        for k, v in substep_states(events, stage["key"]).items():
            if v.get("duration_ms"):
                dur.append({"tahap": stage["title"], "sub-langkah": k,
                            "detik": v["duration_ms"] / 1000})
    if dur:
        ddf = pd.DataFrame(dur)
        total = ddf["detik"].sum()
        _show(alt.Chart(ddf, title=f"Waktu per sub-langkah (total {fmt_duration(int(total * 1000))})")
              .mark_bar().encode(
                  y=alt.Y("sub-langkah:N", sort="-x", title=None),
                  x=alt.X("detik:Q"),
                  color=alt.Color("tahap:N", title=None),
                  tooltip=["tahap", "sub-langkah", alt.Tooltip("detik:Q", format=".1f")])
              .properties(height=max(200, 22 * len(ddf))),
              "Ekstraksi LLM dan cek OpenAlex mendominasi: keduanya menunggu layanan luar "
              "(LLM per kandidat; OpenAlex ~1 permintaan/detik).")
