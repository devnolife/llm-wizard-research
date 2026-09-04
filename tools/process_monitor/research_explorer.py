"""Penelusur: rantai per kandidat (chunk → LLM → gap → verifikasi) dan
penjelajah tema (tema → anggota → jurnal pendukung).

Keduanya membaca berkas samping yang ditulis pipeline (``candidates_jsonl``,
``themes_jsonl``) dan menyatakan terang-terangan bila job lama tidak
memilikinya, alih-alih menampilkan panel kosong.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from research_common import (
    SEMUA,
    fetch_all_records,
    fetch_records,
    stage_artifacts,
)
from research_vocab import enum_label, label

_REASON_LABEL = {
    "section:conclusion": "bagian kesimpulan",
    "section:discussion": "bagian diskusi",
    "phrase": "memuat pola kata gap",
    "abstract": "abstrak (aturan cadangan)",
    "introduction": "pendahuluan awal (aturan cadangan)",
    "tail": "dua chunk terakhir (aturan cadangan)",
}


def reason_label(reason: str | None) -> str:
    parts = [p for p in str(reason or "").split(",") if p]
    return ", ".join(_REASON_LABEL.get(p, p) for p in parts) or "—"


# ── jejak per kandidat ─────────────────────────────────────────────────────

def render_candidate_trace(job_id: str) -> None:
    probe = fetch_records(job_id, "candidates", limit=1)
    if probe.get("error"):
        st.info("Jejak per kandidat **tidak direkam pada analisis ini** — fitur ini ada sejak "
                "pembaruan. Jalankan analisis baru untuk melihat rantai chunk → LLM → gap → "
                "verifikasi untuk setiap kandidat.")
        return

    cands = fetch_all_records(job_id, "candidates")
    if not cands:
        st.info("Tidak ada kandidat pada job ini.")
        return
    prompts = _llm_prompts_by_chunk(job_id)

    st.markdown(
        f"**{len(cands)} kandidat** dibaca LLM. Untuk tiap kandidat: chunk yang dibaca, "
        "alasan dipilih, balasan mentah LLM, gap yang ter-parse, dan nasib tiap gap di "
        "verifikasi verbatim & dedup. Prompt lengkap tersimpan untuk "
        f"{len(prompts)} kandidat pertama.")

    facets = probe.get("facets") or {}
    c1, c2, c3, c4 = st.columns(4)
    f_src = c1.selectbox(label("source"), [SEMUA] + facets.get("source", []), key="ct_src")
    f_reason = c2.selectbox("alasan dipilih", [SEMUA] + facets.get("candidate_reason", []),
                            key="ct_reason", format_func=lambda v: v if v == SEMUA else reason_label(v))
    f_result = c3.selectbox("hasil", [SEMUA, "ada gap final", "gap semua gugur/duplikat",
                                     "LLM kembalikan 0 gap", "LLM tidak menjawab"], key="ct_res")
    q = c4.text_input("cari teks", key="ct_q", placeholder="kata di chunk/balasan/gap")

    rows = cands
    if f_src != SEMUA:
        rows = [c for c in rows if c.get("source") == f_src]
    if f_reason != SEMUA:
        rows = [c for c in rows if c.get("candidate_reason") == f_reason]
    if f_result == "ada gap final":
        rows = [c for c in rows if (c.get("gap_final") or 0) > 0]
    elif f_result == "gap semua gugur/duplikat":
        rows = [c for c in rows if (c.get("gap_mentah") or 0) > 0 and not c.get("gap_final")]
    elif f_result == "LLM kembalikan 0 gap":
        rows = [c for c in rows if c.get("llm_answered") and not c.get("gap_mentah")]
    elif f_result == "LLM tidak menjawab":
        rows = [c for c in rows if not c.get("llm_answered")]
    if q:
        needle = q.lower()
        rows = [c for c in rows if needle in str(c).lower()]

    summary = pd.DataFrame([{
        "#": c.get("seq"), "jurnal": c.get("source"), "chunk": c.get("chunk_index"),
        "bagian": c.get("section_normalized"), "alasan": reason_label(c.get("candidate_reason")),
        "LLM": "✔" if c.get("llm_answered") else "✘",
        "gap mentah": c.get("gap_mentah"), "lolos": c.get("gap_lolos"), "final": c.get("gap_final"),
    } for c in rows])
    st.caption(f"{len(rows)} kandidat cocok")
    if not summary.empty:
        st.dataframe(summary, width="stretch", hide_index=True, height=min(400, 38 + 35 * len(summary)))

    per_page = 10
    pages = max(1, -(-len(rows) // per_page))
    page = st.number_input(f"Halaman rincian (dari {pages})", 1, pages, 1, key="ct_pg")
    for c in rows[(page - 1) * per_page: page * per_page]:
        _render_one_candidate(job_id, c, prompts.get(c.get("chunk_id")))


def _llm_prompts_by_chunk(job_id: str) -> dict[str, dict]:
    """Prompt/balasan yang tersimpan di basis data (15 pertama), diindeks chunk_id."""
    out: dict[str, dict] = {}
    for art in stage_artifacts(job_id, "gap_mining").get("llm") or []:
        p = art.get("payload") or {}
        if p.get("chunk_id"):
            out[p["chunk_id"]] = p
    return out


def _render_one_candidate(job_id: str, c: dict, prompt: dict | None) -> None:
    fate = (f"{c.get('gap_mentah', 0)} gap mentah → {c.get('gap_lolos', 0)} lolos verbatim → "
            f"{c.get('gap_final', 0)} final")
    head = (f"#{c.get('seq')} · {c.get('source')} · chunk {c.get('chunk_index')} "
            f"({c.get('section_normalized')}) · {fate}")
    with st.expander(head, expanded=False):
        st.markdown(f"**1 · Kenapa chunk ini dibaca:** {reason_label(c.get('candidate_reason'))}")
        if c.get("matched_phrases"):
            st.caption("Pola kata yang cocok: " + ", ".join(f"`{p}`" for p in c["matched_phrases"]))

        st.markdown("**2 · Teks chunk yang dibaca** (plus satu chunk sebelum & sesudahnya "
                    f"sebagai konteks, total {c.get('context_chars')} karakter)")
        chunk = _find_chunk(job_id, c.get("chunk_id"))
        if chunk:
            st.markdown(f"> {chunk.get('text', '')}".replace("\n", "\n> "))
            st.caption(f"`{c.get('chunk_id')}` · hlm {chunk.get('page_start')} · "
                       f"{c.get('token_count')} token")
        else:
            st.caption(f"`{c.get('chunk_id')}` — teks chunk tidak ditemukan.")

        if prompt:
            with st.popover("📜 Prompt lengkap yang dikirim"):
                st.text_area("system", prompt.get("system", ""), height=90, disabled=True,
                             key=f"sys_{c.get('seq')}")
                st.text_area("prompt", prompt.get("prompt", ""), height=220, disabled=True,
                             key=f"pr_{c.get('seq')}")

        st.markdown(f"**3 · Balasan mentah LLM** (`{c.get('model') or '?'}`)")
        if not c.get("llm_answered"):
            st.error("LLM tidak menjawab panggilan ini — bukan '0 gap', melainkan gagal sistem.")
        else:
            st.code(c.get("response") or "(kosong)", language="json")

        gaps = c.get("gaps") or []
        st.markdown(f"**4 · Gap yang ter-parse & nasibnya** ({len(gaps)})")
        if not gaps:
            st.caption("LLM mengembalikan array kosong — tidak ada pernyataan gap di bagian ini.")
        else:
            st.dataframe(pd.DataFrame([{
                "kalimat (verbatim)": g.get("gap_statement"),
                "jenis": enum_label("gap_type", g.get("gap_type")),
                label("grounding_score"): g.get("grounding_score"),
                "lolos verbatim": "✔" if g.get("lolos_verifikasi") else "✘ dibuang",
                "duplikat": "✔ dibuang" if g.get("duplikat") else "",
                "final": "✔" if g.get("lolos_verifikasi") and not g.get("duplikat") else "",
            } for g in gaps]), width="stretch", hide_index=True,
                column_config={"kalimat (verbatim)": st.column_config.TextColumn(width="large")})


def _find_chunk(job_id: str, chunk_id: str | None) -> dict | None:
    if not chunk_id:
        return None
    for rec in fetch_records(job_id, "chunking", q=chunk_id, limit=5).get("records") or []:
        if rec.get("chunk_id") == chunk_id:
            return rec
    return None


# ── penjelajah tema ────────────────────────────────────────────────────────

def render_theme_browser(job_id: str) -> None:
    probe = fetch_records(job_id, "themes", limit=1)
    if probe.get("error"):
        st.info("Daftar tema **tidak tersimpan pada analisis ini** (job lama). Jalankan "
                "analisis baru; tab Rekomendasi tetap menampilkan angka temanya.")
        return
    themes = fetch_all_records(job_id, "themes")
    props = fetch_all_records(job_id, "recommendation")
    if not themes:
        st.info("Tidak ada tema — tidak ada gap open pada job ini.")
        return

    by_theme: dict[int, list[dict]] = {}
    for p in props:
        by_theme.setdefault(p.get("theme_id"), []).append(p)

    multi = [t for t in themes if (t.get("journal_support") or 0) >= 2]
    single = [t for t in themes if (t.get("size") or 0) == 1]
    k = st.columns(4)
    k[0].metric(label("tema"), len(themes))
    k[1].metric(label("tema_lintas_jurnal"), len(multi))
    k[2].metric(label("tema_satu_gap"), len(single))
    k[3].metric("tema terbesar", max((t.get("size") or 0) for t in themes))

    st.warning("**Cara membaca:** tema didukung ≥2 jurnal lebih kuat daripada satu jurnal yang "
               "banyak bicara. Namun pada tema BESAR, jumlah jurnal adalah **batas atas** — "
               "pengelompokan single-linkage bisa merantai gap yang hanya mirip berpasangan. "
               "Buka anggotanya dan nilai sendiri apakah mereka membicarakan hal yang sama.")

    only_multi = st.toggle("Hanya tema lintas-jurnal (≥2 jurnal)", value=False, key="th_multi")
    shown = multi if only_multi else themes
    tdf = pd.DataFrame([{
        "#": t.get("theme_id"), "nama tema (dari anggota berskor tertinggi)": t.get("label"),
        "jurnal pendukung": t.get("journal_support"), "anggota": t.get("size"),
        "skor rata-rata": t.get("priority"), "skor tertinggi": t.get("top_priority"),
        "topik": ", ".join(enum_label("topic", x).split(" (")[0] for x in (t.get("topics") or [])),
    } for t in shown])
    st.dataframe(tdf, width="stretch", hide_index=True,
                 column_config={"nama tema (dari anggota berskor tertinggi)":
                                st.column_config.TextColumn(width="large")})

    st.markdown("**Buka satu tema**")
    pick = st.selectbox("Tema", [t.get("theme_id") for t in shown], key="th_pick",
                        format_func=lambda i: next(
                            (f"#{t['theme_id']} · {t.get('journal_support')} jurnal · "
                             f"{t.get('size')} gap · {str(t.get('label'))[:70]}"
                             for t in shown if t.get("theme_id") == i), str(i)))
    theme = next((t for t in themes if t.get("theme_id") == pick), None)
    if not theme:
        return
    members = sorted(by_theme.get(pick, []), key=lambda p: p.get("rank") or 0)
    st.markdown(f"**Jurnal pendukung ({theme.get('journal_support')}):** " +
                ", ".join(f"`{j}`" for j in theme.get("journals") or []))
    if members:
        st.dataframe(pd.DataFrame([{
            "peringkat": m.get("rank"), "jurnal": m.get("source"),
            "usulan": m.get("title"), "skor": m.get("priority_score"),
            "kebaruan": enum_label("band", m.get("band")),
            "jenis gap": enum_label("gap_type", m.get("gap_type")),
        } for m in members]), width="stretch", hide_index=True,
            column_config={"usulan": st.column_config.TextColumn(width="large")})
        with st.expander("Kalimat asli tiap anggota", expanded=False):
            for m in members:
                st.markdown(f"- **{m.get('source')}** — {m.get('description')}")
    if (theme.get("size") or 0) >= 5 and (theme.get("journal_support") or 0) >= 3:
        st.caption("⚠️ Tema besar: periksa apakah anggota di atas benar-benar satu topik. Bila "
                   "campur, jumlah jurnal pendukungnya jangan dikutip sebagai kesepakatan.")
