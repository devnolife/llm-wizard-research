"""Langkah 4 — rekomendasi topik & judul siap-pakai.

Melanjutkan job langkah 2 (berhenti di ``gap_mining``) ke tahap ``recommendation``
lewat ``POST /api/research/{job}/continue``: gap mining (LLM) TIDAK diulang. Tahap
kebaruan (OpenAlex) dilewati tanpa jaringan bila server menyetel
``OPENALEX_DISABLED=1``; bila aktif, pengguna diberi tahu dan dapat membatasi
jumlah gap yang dicek. Hasil: peringkat proposal (rumus project), tema
lintas-jurnal, dan judul siap-pakai (judul, latar belakang, alasan, metode —
tulisan LLM dari kutipan gap; peringkat tidak diubah LLM).
Polling status dilakukan oleh ``page_wizard.py`` (job yang sama dengan langkah 2).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from research_explorer import render_theme_browser, render_title_narration
from research_vocab import enum_label
from wl_common import (
    TERMINAL_STATUSES,
    continue_research_job,
    job_artifacts,
    research_stages,
    short_name,
    stage_records,
)


def reset() -> None:
    st.session_state.pop("rec_records", None)


def _novelty_disabled(api_base: str) -> bool | None:
    """True bila tahap kebaruan dimatikan di server; None bila tidak bisa dicek."""
    try:
        for s in research_stages(api_base):
            if s.get("key") == "novelty":
                return bool(s.get("disabled"))
    except Exception:
        return None
    return None


def _result_payload(api_base: str, job_id: str) -> dict:
    try:
        arts = [a for a in job_artifacts(api_base, job_id, "recommendation")
                if a.get("kind") == "result"]
    except Exception:
        return {}
    return (arts[-1].get("payload") or {}) if arts else {}


def _load(api_base: str, job_id: str) -> dict:
    cache = st.session_state.get("rec_records") or {}
    if cache.get("job_id") != job_id:
        with st.spinner("Mengambil rekomendasi…"):
            cache = {
                "job_id": job_id,
                "proposals": stage_records(api_base, job_id, "recommendation"),
                "result": _result_payload(api_base, job_id),
            }
        st.session_state["rec_records"] = cache
    return cache


def _render_ranking(proposals: list) -> None:
    st.caption("Skor prioritas = 0,5·gap_confidence + 0,3·novelty_credit + 0,2·actionability "
               "(rumus project); novelty diukur terhadap jurnal yang diunggah, bukan literatur "
               "luar. Skor yang sama persis memang seri — urutannya dipecah oleh jarak novelty ke "
               "tengah *sweet spot*, bukan oleh LLM.")
    sources = sorted({p.get("source") for p in proposals})
    src_sel = st.multiselect("Jurnal", sources, default=sources, key="rec-src",
                             format_func=short_name)
    shown = [p for p in proposals if p.get("source") in src_sel]
    df = pd.DataFrame([{
        "#": p.get("rank"),
        "Skor": p.get("priority_score"),
        "Gap (parafrase)": p.get("title"),
        "Jurnal": short_name(p.get("source", ""), 36),
        "Kebaruan": enum_label("band", p.get("band")).split(" (")[0],
        "Jenis gap": enum_label("gap_type", p.get("gap_type")).split(" (")[0],
        "Tema": p.get("theme_id"),
    } for p in shown])
    st.dataframe(df, width="stretch", hide_index=True, height=min(600, 38 + 35 * max(1, len(df))),
                 column_config={"Gap (parafrase)": st.column_config.TextColumn(width="large"),
                                "Skor": st.column_config.NumberColumn(format="%.4f", width="small")})


def _render_results(api_base: str, job_id: str) -> None:
    cache = _load(api_base, job_id)
    proposals, result = cache["proposals"], cache["result"]
    metrics = result.get("metrics") or {}

    m = st.columns(5)
    m[0].metric("Gap diteruskan", metrics.get("gap_open", len(proposals)),
                help="Gap berstatus open/unchecked yang dinilai sebagai proposal.")
    m[1].metric("Proposal dinilai", metrics.get("proposal_dinilai", len(proposals)))
    m[2].metric("Tema", metrics.get("tema", "—"))
    m[3].metric("Tema lintas-jurnal", metrics.get("tema_lintas_jurnal", "—"),
                help="Tema yang didukung ≥2 jurnal berbeda — bukti terkuat untuk topik baru.")
    m[4].metric("Judul siap-pakai", f"{metrics.get('narasi_dibuat', 0)}/{metrics.get('narasi_diminta', 0)}",
                help="Butir teratas yang dirumuskan LLM (tema lintas-jurnal dulu, lalu proposal).")
    for note in result.get("notes") or []:
        if "Narasi judul tidak dibuat" in note:
            st.warning(note)

    tab_titles, tab_rank, tab_themes = st.tabs([
        f"✍️ Judul siap-pakai ({metrics.get('narasi_dibuat', 0)})",
        f"🏆 Peringkat proposal ({len(proposals)})",
        f"🧩 Tema ({metrics.get('tema', '—')})",
    ])
    with tab_titles:
        render_title_narration(job_id)
    with tab_rank:
        if proposals:
            _render_ranking(proposals)
        else:
            st.info("Tidak ada gap open/unchecked yang bisa dinilai.")
    with tab_themes:
        render_theme_browser(job_id)


# ── Entri ──────────────────────────────────────────────────────────────────

def render(api_base: str, gap_job_id: str | None, gap_status: dict | None, backend_ok: bool):
    """Gambar langkah 4 untuk job langkah 2 (``gap_job_id``/``gap_status``)."""
    st.header("Langkah 4 — rekomendasi topik & judul siap-pakai")
    st.write(
        "Gap per jurnal dari langkah 2 diperingkat dengan **rumus project** (keyakinan verbatim, "
        "kebaruan terhadap jurnal yang diunggah, keterlaksanaan), lalu gap serupa lintas jurnal "
        "digabung menjadi **tema**. Untuk beberapa butir teratas — tema lintas-jurnal dulu — LLM "
        "**menuliskan** judul penelitian siap-pakai beserta latar belakang, alasan, dan metode dari "
        "kutipan gap. LLM tidak menilai dan tidak mengubah urutan."
    )

    if not gap_job_id or not gap_status:
        st.info("Selesaikan **langkah 2** dulu — rekomendasi disusun dari gap yang ditemukan di sana.")
        return
    stages_done = gap_status.get("stages_done") or []
    state = gap_status.get("status")

    if "recommendation" in stages_done:
        _render_results(api_base, gap_job_id)
        return
    if "gap_mining" not in stages_done:
        st.info("Menunggu tahap penambangan gap langkah 2 selesai.")
        return
    if state not in TERMINAL_STATUSES:
        st.info("Job sedang melanjutkan ke tahap rekomendasi — progresnya tampil di langkah 2.")
        return
    if state != "completed":
        st.error(f"Job langkah 2 berakhir dengan status {state}; tidak bisa dilanjutkan.")
        return

    disabled = _novelty_disabled(api_base)
    novelty_limit = 0
    if disabled:
        st.caption("Tahap kebaruan (OpenAlex) **dimatikan di server** — dilewati tanpa permintaan "
                   "jaringan; semua gap diteruskan ke pemeringkatan.")
    elif disabled is False:
        st.warning("Tahap kebaruan **aktif** di server: tiap gap akan dicek ke OpenAlex (kuota gratis "
                   "≈100 pencarian/hari, ~1 detik per gap). Batasi jumlahnya bila tidak perlu.")
        novelty_limit = st.number_input("Maks. gap yang dicek ke OpenAlex (0 = semua)", min_value=0,
                                        value=0, step=10, key="rec-novelty-limit")
    if st.button("🎯 Susun rekomendasi & judul", type="primary", disabled=not backend_ok,
                 key="rec-start"):
        try:
            continue_research_job(api_base, gap_job_id, until="recommendation",
                                  novelty_limit=int(novelty_limit))
            reset()
            st.rerun()
        except Exception as exc:
            st.error(f"Gagal melanjutkan job: {exc}")
    else:
        st.caption("Gap mining tidak diulang; satu panggilan LLM tambahan untuk merumuskan judul "
                   "(≈1 menit).")
