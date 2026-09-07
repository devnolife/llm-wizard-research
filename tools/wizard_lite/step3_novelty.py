"""Langkah 3 — cek kebaruan tiap gap ke literatur terbaru (OpenAlex ≥ 2024).

Melanjutkan job langkah 2 (``POST /api/research/{job}/continue``, tahap
``novelty``): gap yang sudah dilihat pengguna TIDAK ditambang ulang. Untuk tiap
gap, kalimatnya dijadikan kata kunci, dicari di OpenAlex, dan diputuskan:
``open`` (belum ada yang menjawab), ``partially_addressed``, ``addressed``, atau
``unchecked`` bila OpenAlex tidak bisa dihubungi (kuota harian ≈ 100 pencarian).
"""

from __future__ import annotations

import json

import streamlit as st

from step2_gaps import GAP_TYPE_LABELS, _short
from wl_common import (
    TERMINAL_STATUSES,
    continue_research_job,
    render_reading_text,
    render_view_switch,
    stage_records,
)

STATUS_LABELS = {
    "open": ("🟢", "Masih terbuka", "Tidak ada paper 2024+ yang sangat cocok dengan kata kunci gap."),
    "partially_addressed": ("🟡", "Sebagian dijawab", "1–2 paper 2024+ sangat cocok (≥50 % kata kunci)."),
    "addressed": ("🔴", "Sudah dijawab", "≥3 paper 2024+ sangat cocok — gap ini kemungkinan sudah ditutup."),
    "unchecked": ("⚪", "Belum dicek", "OpenAlex tidak bisa dihubungi (kuota/gangguan) atau di luar batas cek."),
}
STATUS_ORDER = ["open", "partially_addressed", "addressed", "unchecked"]
QUOTA_PER_DAY = 100  # kredit gratis OpenAlex: 1000/hari, 10 kredit per pencarian


def _status_badge(status: str) -> str:
    icon, label, _ = STATUS_LABELS.get(status, ("❔", status, ""))
    return f"{icon} {label}"


def _paper_line(p: dict) -> str:
    title = (p.get("title") or "—").strip()
    if p.get("doi"):
        doi = str(p["doi"]).replace("https://doi.org/", "")
        title = f"[{title}](https://doi.org/{doi})"
    return f"- {title} ({p.get('year') or '?'}) · kecocokan {p.get('match_score', 0):.2f}"


def _render_gap_card(g: dict) -> None:
    status = g.get("novelty_status", "unchecked")
    icon, label, explain = STATUS_LABELS.get(status, ("❔", status, ""))
    with st.container(border=True):
        st.markdown(f"**{icon} {label}** · {g.get('source')} · "
                    f"*{GAP_TYPE_LABELS.get(g.get('gap_type'), g.get('gap_type'))}*")
        render_reading_text(g.get("gap_statement", ""))
        if g.get("gap_paraphrase"):
            st.caption(f"Parafrase: {g['gap_paraphrase']}")
        st.caption(f"{explain} Kata kunci pencarian: `{g.get('novelty_query', '')}`")
        if status == "unchecked":
            st.warning(f"Alasan: {g.get('novelty_error') or 'tidak diketahui'}")
        papers = g.get("related_recent_papers") or []
        if papers:
            st.markdown("**Paper 2024+ paling mirip:**\n" + "\n".join(_paper_line(p) for p in papers))
        elif status == "open":
            st.caption("Tidak ada paper 2024+ yang cocok dengan kata kunci ini.")


def _render_results(records: list) -> None:
    counts = {s: sum(1 for g in records if g.get("novelty_status") == s) for s in STATUS_ORDER}
    cols = st.columns(4)
    for col, s in zip(cols, STATUS_ORDER):
        col.metric(_status_badge(s), counts[s])

    unchecked = [g for g in records if g.get("novelty_status") == "unchecked"]
    quota = [g for g in unchecked if g.get("novelty_error") and g["novelty_error"] != "di luar batas cek"]
    if quota:
        st.error(
            f"{len(quota)} gap **tidak bisa dicek**: {quota[0]['novelty_error']}. "
            "Statusnya *Belum dicek*, bukan *terbuka*. Cek ulang setelah kuota pulih "
            "(hasil yang sudah ada dibaca dari cache, tidak menghabiskan kuota lagi)."
        )
    skipped = len(unchecked) - len(quota)
    if skipped:
        st.info(f"{skipped} gap sengaja tidak dikirim (di luar batas cek yang Anda pilih).")

    sources = sorted({g.get("source") for g in records})
    f1, f2 = st.columns(2)
    status_sel = f1.multiselect("Status", STATUS_ORDER, default=STATUS_ORDER, key="nov-status",
                                format_func=_status_badge)
    src_sel = f2.multiselect("Jurnal", sources, default=sources, key="nov-src", format_func=_short)
    shown = [g for g in records
             if g.get("novelty_status") in status_sel and g.get("source") in src_sel]

    def row(g: dict) -> dict:
        return {
            "Status": _status_badge(g.get("novelty_status", "unchecked")),
            "Jurnal": _short(g.get("source", "")),
            "Paper mirip": len(g.get("related_recent_papers") or []),
            "Parafrase (ID)": g.get("gap_paraphrase", ""),
            "Kalimat asli": g.get("gap_statement", ""),
        }

    render_view_switch(
        shown, "novelty", row, lambda i: _render_gap_card(shown[i]),
        column_config={
            "Paper mirip": st.column_config.NumberColumn(width="small"),
            "Kalimat asli": st.column_config.TextColumn(width="large"),
            "Parafrase (ID)": st.column_config.TextColumn(width="medium"),
        },
    )
    jsonl = "\n".join(json.dumps(g, ensure_ascii=False) for g in records)
    st.download_button("⬇️ Unduh gap + kebaruan (.jsonl)", data=jsonl.encode("utf-8"),
                       file_name="gaps_novelty.jsonl", mime="application/x-ndjson", key="dl-nov")


def _render_start(api_base: str, job_id: str, n_gaps: int, rerun: bool) -> None:
    default = min(n_gaps, 50)
    limit = st.slider("Berapa gap yang dikirim ke OpenAlex?", 1, max(1, n_gaps), default,
                      key="nov-limit",
                      help="Kuota gratis OpenAlex ≈ 100 pencarian per hari (per IP/e-mail). "
                           "Gap di luar batas ditandai *Belum dicek* dan bisa dicek belakangan.")
    if limit > QUOTA_PER_DAY:
        st.warning(f"{limit} pencarian melebihi kuota harian gratis (~{QUOTA_PER_DAY}); sisanya "
                   "akan berstatus *Belum dicek*.")
    st.caption(f"Perkiraan waktu ≈ {limit} detik (1 permintaan/detik), lebih cepat bila hasil "
               "sudah ada di cache.")
    label = "🔁 Cek ulang kebaruan" if rerun else "🔭 Cek kebaruan"
    if st.button(label, type="primary", key="nov-start"):
        try:
            continue_research_job(api_base, job_id, until="novelty", novelty_limit=limit)
            st.session_state.pop("novelty_records", None)
            st.rerun()
        except Exception as exc:
            st.error(f"Gagal melanjutkan job: {exc}")


def render(api_base: str, job_id, status, gaps: list) -> None:
    st.header("Langkah 3 — apakah gap ini masih terbuka? (cek literatur 2024+)")
    st.write(
        "Tiap kalimat gap diubah menjadi kata kunci dan dicari di **OpenAlex** (paper terbit "
        "≥ 2024). Bila ≥3 paper sangat cocok, gap dianggap **sudah dijawab**; 1–2 paper "
        "**sebagian**; tidak ada → **masih terbuka**. Ini pencocokan kata kunci, bukan "
        "pemahaman makna — perlakukan sebagai penyaring awal, bukan vonis."
    )
    if not job_id or not status or not gaps:
        st.info("Selesaikan langkah 2 dulu — cek kebaruan dilakukan pada gap final di atas.")
        return

    state = status.get("status")
    stages_done = status.get("stages_done") or []
    payload = status.get("payload") or {}
    if state not in TERMINAL_STATUSES and payload.get("start_from") == "novelty":
        st.progress(min(100, int(status.get("progress") or 0)) / 100,
                    text=status.get("message") or "Mengecek OpenAlex…")
        return
    if state != "completed":
        return

    if "novelty" in stages_done:
        cache = st.session_state.get("novelty_records") or {}
        if cache.get("job_id") != job_id:
            with st.spinner("Mengambil hasil kebaruan…"):
                cache = {"job_id": job_id, "records": stage_records(api_base, job_id, "novelty")}
            st.session_state["novelty_records"] = cache
        _render_results(cache["records"])
        with st.expander("Cek ulang (misalnya setelah kuota OpenAlex pulih)"):
            _render_start(api_base, job_id, len(gaps), rerun=True)
    else:
        _render_start(api_base, job_id, len(gaps), rerun=False)
