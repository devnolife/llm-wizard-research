"""Langkah 2 — cari research gap dengan LLM.

Menjalankan job pipeline penelitian sampai tahap ``gap_mining`` saja (tanpa
OpenAlex/rekomendasi), memantau progresnya, lalu memperlihatkan dua hal:
gap final yang lolos verifikasi verbatim, dan jejak tiap kandidat chunk
(apa yang dibaca LLM, apa jawabannya, gap mana yang gugur dan mengapa).
Polling status dilakukan oleh ``app.py`` (satu untuk semua langkah).
"""

from __future__ import annotations

import json

import streamlit as st

from wl_common import (
    JOB_STATUS_BADGES,
    TERMINAL_STATUSES,
    cancel_job,
    job_events,
    job_status,
    render_reading_text,
    render_view_switch,
    section_label,
    short_name,
    stage_records,
    start_research_job,
)

GAP_TYPE_LABELS = {
    "explicit_future_work": "Saran penelitian lanjutan",
    "stated_limitation": "Keterbatasan yang dinyatakan",
    "implicit_gap": "Gap tersirat",
}
REASON_LABELS = {
    "section:conclusion": "bagian Kesimpulan",
    "section:discussion": "bagian Pembahasan",
    "phrase": "frasa penanda gap",
    "abstract": "abstrak",
    "introduction": "pendahuluan (2 chunk awal)",
    "tail": "2 chunk terakhir",
}
# Pilihan jumlah run LLM: 1 = cepat (k/n tidak informatif), 3 = ukur stabilitas
# (gap dianggap stabil bila muncul di >= 2 dari 3 run). Biaya waktu linear.
RUN_CHOICES = {1: "1 run (cepat)", 3: "3 run (ukur stabilitas k/n, ~3× lebih lama)"}


def reset() -> None:
    for key in ("gap_job_id", "gap_records"):
        st.session_state.pop(key, None)


def _reason_text(reason: str) -> str:
    return ", ".join(REASON_LABELS.get(r, r) for r in (reason or "").split(",") if r)


def _multi_run(gaps: list) -> bool:
    return any(int(g.get("run_total") or 1) > 1 for g in gaps)


def _kn_badge(g: dict) -> str:
    """'✅ stabil 3/3 run' / '⚠️ tidak stabil 1/3 run'; kosong untuk job 1 run."""
    total = int(g.get("run_total") or 1)
    if total <= 1:
        return ""
    hits = g.get("run_hits")
    return (f"✅ stabil {hits}/{total} run" if g.get("stable", True)
            else f"⚠️ tidak stabil {hits}/{total} run")


_short = short_name


# ── Progres ────────────────────────────────────────────────────────────────

def _event_line(e: dict) -> str:
    data = e.get("data") or {}
    kind, phase = e.get("type", ""), e.get("phase") or ""
    if kind == "file.completed":
        return f"📄 {data.get('file', '')} → {data.get('chunks', '?')} chunk"
    if kind.startswith("substep."):
        bits = [f"{k}={v}" for k, v in data.items()
                if k in ("masuk", "keluar", "dibuang") and v not in (None, "")]
        return f"↳ {data.get('substep', '')} {' '.join(bits)}".strip()
    if kind.startswith("phase."):
        return f"{'▶️' if kind.endswith('started') else '✅'} tahap {phase}"
    return kind


def _render_progress(api_base: str, job_id: str, status: dict) -> None:
    state = status.get("status", "queued")
    icon, label = JOB_STATUS_BADGES.get(state, ("❔", state))
    st.markdown(f"**Job `{job_id[:8]}…` — {icon} {label}**")
    if state not in TERMINAL_STATUSES:
        st.progress(min(100, int(status.get("progress") or 0)) / 100,
                    text=status.get("message") or "…")
    else:
        st.caption(status.get("message") or "")

    try:
        events = job_events(api_base, job_id)
    except Exception:
        events = []
    if events:
        with st.expander("Jejak proses", expanded=state not in TERMINAL_STATUSES):
            for e in events[-8:]:
                st.caption(_event_line(e))

    b1, b2 = st.columns(2)
    if state not in TERMINAL_STATUSES:
        if b1.button("⏹️ Batalkan", key="gap-cancel", width="stretch"):
            cancel_job(api_base, job_id)
            st.rerun()
    if b2.button("🔁 Mulai dari awal", key="gap-reset", width="stretch"):
        reset()
        st.rerun()


# ── Hasil ──────────────────────────────────────────────────────────────────

def _render_gap_card(g: dict, chunks_by_id: dict) -> None:
    with st.container(border=True):
        badge = _kn_badge(g)
        st.markdown(
            f"**{GAP_TYPE_LABELS.get(g.get('gap_type'), g.get('gap_type'))}** · "
            f"{g.get('source')} · kecocokan verbatim {g.get('grounding_score', 0):.2f}"
            + (f" · {badge}" if badge else "")
        )
        render_reading_text(g.get("gap_statement", ""))
        if g.get("gap_paraphrase"):
            st.caption(f"Parafrase: {g['gap_paraphrase']}")
        chunk_ids = g.get("evidence_chunk_ids") or []
        chunk = chunks_by_id.get(chunk_ids[0]) if chunk_ids else None
        if chunk:
            with st.expander(f"Chunk sumber #{chunk['chunk_index']} · "
                             f"{section_label(chunk['section_normalized'])} · "
                             f"hal. {chunk.get('page_start') or '?'}"):
                render_reading_text(chunk["text"], highlight=g.get("gap_statement"))
        elif chunk_ids:
            st.caption(f"Chunk sumber: `{chunk_ids[0]}` (tidak ada di hasil langkah 1 — "
                       "chunking job memakai pembaca PDF yang berbeda?)")


def _render_gaps(gaps: list, chunks_by_id: dict) -> None:
    sources = sorted({g.get("source") for g in gaps})
    types = [t for t in GAP_TYPE_LABELS if any(g.get("gap_type") == t for g in gaps)]
    multi = _multi_run(gaps)
    f1, f2, f3 = st.columns([2, 2, 1])
    src_sel = f1.multiselect("Jurnal", sources, default=sources, key="gap-src",
                             format_func=_short)
    type_sel = f2.multiselect("Jenis gap", types, default=types, key="gap-type",
                              format_func=lambda t: GAP_TYPE_LABELS.get(t, t))
    stable_only = f3.toggle("Hanya gap stabil", value=True, key="gap-stable",
                            disabled=not multi,
                            help="Gap yang muncul di cukup banyak run LLM (k/n). Nonaktif "
                                 "bila job hanya 1 run.") if multi else False
    shown = [g for g in gaps if g.get("source") in src_sel and g.get("gap_type") in type_sel
             and (not stable_only or g.get("stable", True))]
    if multi and stable_only:
        hidden = sum(1 for g in gaps if not g.get("stable", True))
        if hidden:
            st.caption(f"{hidden} gap tidak stabil (muncul di terlalu sedikit run) disembunyikan; "
                       "matikan toggle untuk melihatnya.")

    def row(g: dict) -> dict:
        r = {
            "Jurnal": _short(g.get("source", "")),
            "Jenis": GAP_TYPE_LABELS.get(g.get("gap_type"), g.get("gap_type")),
            "Verbatim": g.get("grounding_score"),
        }
        if multi:
            r["Run k/n"] = f"{g.get('run_hits')}/{g.get('run_total')}"
        r["Parafrase (ID)"] = g.get("gap_paraphrase", "")
        r["Kalimat asli"] = g.get("gap_statement", "")
        return r

    render_view_switch(
        shown, "gaps", row, lambda i: _render_gap_card(shown[i], chunks_by_id),
        column_config={
            "Verbatim": st.column_config.NumberColumn(format="%.2f", width="small"),
            "Run k/n": st.column_config.TextColumn(width="small"),
            "Kalimat asli": st.column_config.TextColumn(width="large"),
            "Parafrase (ID)": st.column_config.TextColumn(width="medium"),
        },
    )
    jsonl = "\n".join(json.dumps(g, ensure_ascii=False) for g in gaps)
    st.download_button("⬇️ Unduh gap (.jsonl)", data=jsonl.encode("utf-8"),
                       file_name="gaps.jsonl", mime="application/x-ndjson", key="dl-gaps")


def _render_candidate_card(c: dict, chunks_by_id: dict) -> None:
    with st.container(border=True):
        st.markdown(
            f"**{c.get('source')} · chunk #{c.get('chunk_index')} · "
            f"{section_label(c.get('section_normalized'))}** · dipilih karena "
            f"{_reason_text(c.get('candidate_reason', ''))}"
        )
        if c.get("matched_phrases"):
            st.caption("Frasa penanda: " + ", ".join(f"“{p}”" for p in c["matched_phrases"]))
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("LLM menjawab", "ya" if c.get("llm_answered") else "tidak")
        m2.metric("Gap mentah", c.get("gap_mentah", 0))
        m3.metric("Lolos verbatim", c.get("gap_lolos", 0))
        m4.metric("Final (unik)", c.get("gap_final", 0))

        for g in c.get("gaps") or []:
            if g.get("lolos_verifikasi") and not g.get("duplikat"):
                status = "✅ final"
            elif g.get("lolos_verifikasi"):
                status = "🔁 duplikat (dibuang)"
            else:
                status = f"❌ gugur verifikasi (skor {g.get('grounding_score') or 0:.2f})"
            st.markdown(f"- {status} · *{GAP_TYPE_LABELS.get(g.get('gap_type'), g.get('gap_type'))}*"
                        f" — {g.get('gap_statement', '')}")

        chunk = chunks_by_id.get(c.get("chunk_id"))
        if chunk:
            with st.expander("Teks chunk yang dibaca LLM (beserta chunk sebelum/sesudah)"):
                render_reading_text(chunk["text"])
        if c.get("response"):
            with st.expander("Jawaban mentah LLM"):
                st.code(c["response"], language="json")


def _render_candidates(cands: list, chunks_by_id: dict) -> None:
    def row(c: dict) -> dict:
        return {
            "Jurnal": _short(c.get("source", "")),
            "Chunk #": c.get("chunk_index"),
            "Bagian": section_label(c.get("section_normalized")),
            "Alasan dipilih": _reason_text(c.get("candidate_reason", "")),
            "LLM": "✅" if c.get("llm_answered") else "—",
            "Mentah": c.get("gap_mentah", 0),
            "Lolos": c.get("gap_lolos", 0),
            "Final": c.get("gap_final", 0),
        }

    render_view_switch(cands, "cands", row, lambda i: _render_candidate_card(cands[i], chunks_by_id))


def _render_results(api_base: str, job_id: str, chunks_by_id: dict) -> list:
    cache = st.session_state.get("gap_records") or {}
    if cache.get("job_id") != job_id:
        with st.spinner("Mengambil hasil…"):
            cache = {
                "job_id": job_id,
                "gaps": stage_records(api_base, job_id, "gap_mining"),
                "candidates": stage_records(api_base, job_id, "candidates"),
            }
        st.session_state["gap_records"] = cache
    gaps, cands = cache["gaps"], cache["candidates"]

    answered = sum(1 for c in cands if c.get("llm_answered"))
    multi = _multi_run(gaps)
    m = st.columns(7 if multi else 6)
    m[0].metric("Kandidat chunk", len(cands))
    m[1].metric("LLM menjawab", f"{answered}/{len(cands)}")
    m[2].metric("Gap mentah", sum(c.get("gap_mentah", 0) for c in cands))
    m[3].metric("Lolos verbatim", sum(c.get("gap_lolos", 0) for c in cands))
    m[4].metric("Gap final", len(gaps))
    m[5].metric("Jurnal bergap", len({g.get("source") for g in gaps}))
    if multi:
        stable = sum(1 for g in gaps if g.get("stable", True))
        runs = max(int(g.get("run_total") or 1) for g in gaps)
        m[6].metric("Gap stabil", f"{stable}/{len(gaps)}",
                    help=f"Muncul di cukup banyak dari {runs} run LLM (k/n). Gap tidak stabil "
                         "tetap tersimpan tetapi tidak diteruskan ke tahap berikutnya.")

    if cands and answered == 0:
        st.error(
            "LLM tidak menjawab satu pun kandidat — 0 gap ini **bukan temuan**, melainkan "
            "gagal sistem (CLI Copilot mati / belum login). Perbaiki layanan LLM lalu mulai ulang."
        )
    elif cands and answered < len(cands):
        st.warning(f"{len(cands) - answered} kandidat tidak dijawab LLM; cakupan gap di bawah normal.")

    tab_gaps, tab_cands = st.tabs([f"🕳️ Gap final ({len(gaps)})", f"🧭 Jejak kandidat ({len(cands)})"])
    with tab_gaps:
        if gaps:
            _render_gaps(gaps, chunks_by_id)
        else:
            st.info("Tidak ada gap yang lolos verifikasi verbatim. Lihat tab jejak kandidat "
                    "untuk melihat apa yang dijawab LLM dan mengapa gugur.")
    with tab_cands:
        if cands:
            _render_candidates(cands, chunks_by_id)
        else:
            st.info("Tidak ada chunk yang memenuhi syarat kandidat.")
    return gaps


# ── Entri ──────────────────────────────────────────────────────────────────

def render(api_base: str, uploads, ocr_mode: str, backend_ok: bool, chunks_by_id: dict):
    """Gambar langkah 2. Mengembalikan ``(job_id, status, gaps)``: ``status`` None bila
    belum ada job; ``gaps`` terisi bila tahap gap_mining sudah selesai."""
    st.header("Langkah 2 — cari research gap dengan LLM")
    st.write(
        "Dari chunk di atas, sistem memilih **kandidat** (bagian Kesimpulan/Pembahasan, "
        "chunk berfrasa penanda gap, abstrak, awal pendahuluan, dan 2 chunk terakhir). "
        "LLM membaca tiap kandidat beserta chunk tetangganya dan mengutip kalimat gap "
        "**apa adanya**; kalimat yang tidak ditemukan verbatim di teks sumber dibuang, "
        "lalu duplikat disatukan. Semua bukti berasal dari jurnal yang Anda unggah."
    )

    job_id = st.session_state.get("gap_job_id")
    if not job_id:
        c1, c2 = st.columns([1, 2])
        gap_runs = c1.selectbox("Jumlah run LLM", list(RUN_CHOICES), key="gap-runs",
                                format_func=RUN_CHOICES.get,
                                help="LLM tidak deterministik: dua run pada chunk yang sama hanya "
                                     "~75% tumpang tindih. Dengan 3 run tiap gap diberi label k/n "
                                     "dan yang muncul di < 2 run ditandai tidak stabil.")
        if c2.button("🔎 Mulai cari gap", type="primary", disabled=not uploads or not backend_ok,
                     key="gap-start"):
            try:
                body = start_research_job(api_base, uploads, ocr_mode, until="gap_mining",
                                          gap_runs=gap_runs)
                st.session_state["gap_job_id"] = body["job_id"]
                st.rerun()
            except Exception as exc:
                st.error(f"Gagal memulai: {exc}")
        else:
            st.caption("PDF yang sama dikirim ulang ke pipeline; tahap chunking diulang di server "
                       "lalu berhenti setelah penambangan gap.")
        return None, None, []

    try:
        status = job_status(api_base, job_id)
    except Exception as exc:
        st.error(f"Tidak bisa membaca status job: {exc}")
        if st.button("🔁 Mulai dari awal", key="gap-reset-err"):
            reset()
            st.rerun()
        return job_id, None, []

    _render_progress(api_base, job_id, status)
    state = status.get("status")
    gaps: list = []
    if "gap_mining" in (status.get("stages_done") or []):
        # tahap gap sudah selesai — hasilnya tetap bisa dibaca meski job sedang
        # melanjutkan tahap berikutnya
        gaps = _render_results(api_base, job_id, chunks_by_id)
    elif state in TERMINAL_STATUSES:
        st.error(status.get("error") or status.get("message") or f"Job berakhir: {state}")
    return job_id, status, gaps
