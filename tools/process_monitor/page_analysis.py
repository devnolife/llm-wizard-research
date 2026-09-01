"""🔬 Proses & Hasil — pantau tiap tahap dan lihat hasil akhirnya."""

import time

import streamlit as st

from export_bundle import build_agent_bundle_md
from common import (
    _FETCH_FAILED,
    JOB_STATUS_BADGES,
    METHOD_BADGES,
    REFRESH_SECONDS,
    RESULT_RENDERERS,
    STAGES,
    STAGE_METRIC_LABELS,
    STATE_CHIPS,
    _render_extraction_results,
    _render_gaps_result,
    _render_llm_traces,
    _render_paper_analysis_result,
    _render_proposal_result,
    _render_roadmap_result,
    _render_topics_result,
    render_gap_method_explainer,
    render_method_layer_status,
    api_base,
    derive_file_rows,
    derive_stage_states,
    fetch_artifacts,
    fetch_events,
    fetch_jobs,
    fetch_chunk_export,
    fetch_status,
    fmt_datetime,
    fmt_duration,
    group_artifacts,
    render_knowledge_graph,
    upload_and_analyze,
)

st.title("🔬 Proses & Hasil Analisis")

if err := st.session_state.pop("last_error", None):
    st.error(err)

# ── Pilih job / mulai baru ──
jobs = fetch_jobs(limit=30)
job_id = st.session_state.get("job_id", "").strip()

with st.expander("➕ Mulai analisis baru (unggah PDF jurnal)", expanded=not (job_id or jobs)):
    uploads = st.file_uploader("PDF jurnal", type="pdf", accept_multiple_files=True)
    if st.button("🚀 Unggah & Analisis", disabled=not uploads, type="primary"):
        new_job = upload_and_analyze(uploads)
        if new_job:
            st.session_state["job_id"] = new_job
            st.rerun()

if jobs:
    options = [j["job_id"] for j in jobs]
    if job_id and job_id not in options:
        options.insert(0, job_id)

    def _label(jid: str) -> str:
        job = next((j for j in jobs if j["job_id"] == jid), None)
        if not job:
            return f"{jid[:8]}… (manual)"
        icon, label, _ = JOB_STATUS_BADGES.get(job.get("status", ""), ("❔", "?", "gray"))
        return f"{icon} {jid[:8]}… · {fmt_datetime(job.get('created_at'))} · {label}"

    selected = st.selectbox(
        "Pilih analisis",
        options,
        index=options.index(job_id) if job_id in options else 0,
        format_func=_label,
    )
    if selected != job_id:
        st.session_state["job_id"] = selected
        st.rerun()
    job_id = selected

if not job_id:
    st.info("Unggah PDF baru di atas, atau buka analisis dari halaman **📊 Dashboard**.")
    st.stop()

# ── Ambil data job ──
status = fetch_status(job_id)
events_payload = fetch_events(job_id)
artifacts_payload = fetch_artifacts(job_id)

fetch_failed = _FETCH_FAILED in (status, events_payload, artifacts_payload)
status = status if isinstance(status, dict) else None
events_payload = events_payload if isinstance(events_payload, dict) else None
artifacts_payload = artifacts_payload if isinstance(artifacts_payload, dict) else None

auto_refresh = st.session_state.get("auto_refresh", True)

if status is None and events_payload is None:
    if fetch_failed:
        st.warning(
            "⏳ Backend sibuk atau tidak merespons (rate limit / timeout). "
            "Data terakhir belum bisa diambil — dicoba lagi otomatis…"
        )
        if auto_refresh and not st.session_state.get("_no_autorefresh"):
            time.sleep(REFRESH_SECONDS)
            st.rerun()
        st.stop()
    st.error(f"Job `{job_id}` tidak ditemukan di {api_base()}.")
    st.stop()

job_status = (status or events_payload).get("status") or "queued"
progress = (status or {}).get("progress") or (events_payload or {}).get("progress") or 0
message = (status or {}).get("message") or (events_payload or {}).get("message") or ""
events = (events_payload or {}).get("events", [])
results = (status or {}).get("results") or {}
artifacts_by_phase = group_artifacts((artifacts_payload or {}).get("artifacts", []))

icon, label, color = JOB_STATUS_BADGES.get(job_status, ("❔", job_status, "gray"))

# ── Header job ──
head_l, head_r = st.columns([3, 1])
with head_l:
    st.markdown(f"### {icon} Job `{job_id[:8]}…` — :{color}[{label}]")
    st.caption(message or "—")
with head_r:
    if job_status in ("queued", "running"):
        st.metric("Progress", f"{int(progress)}%")
    else:
        total_ms = None
        created = next((e["created_at"] for e in events if e["type"] == "job.created"), None)
        ended = next((e["created_at"] for e in reversed(events)
                      if e["type"] in ("job.completed", "job.failed", "job.cancelled")), None)
        if created and ended:
            total_ms = int((ended - created) * 1000)
        st.metric("Total waktu", fmt_duration(total_ms))

if job_status in ("queued", "running"):
    st.progress(min(int(progress), 100) / 100)
elif job_status == "failed":
    st.error("Analisis gagal — buka halaman 🧾 Log Event untuk melihat jenis error-nya.")
elif job_status == "cancelled":
    st.warning("Analisis dibatalkan oleh pengguna.")

# ── HASIL AKHIR (job selesai) ──
if job_status == "completed" and results:
    st.divider()
    st.subheader("🏁 Hasil Akhir")

    _weaknesses = results.get("paper_weaknesses") or []
    _n_weak = sum(
        len(w.get("tersurat") or []) + len(w.get("tersirat") or [])
        for w in _weaknesses
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📄 Jurnal", results.get("files_processed") or len(_weaknesses))
    m2.metric("⚠️ Kekurangan per jurnal", _n_weak)
    m3.metric("🕳️ Gap kolektif", len(results.get("gaps") or []))
    m4.metric("💡 Usulan", len(results.get("recommendations") or []))
    st.caption(
        "Alur baca: **📄 Gap per Jurnal** memperlihatkan kekurangan tiap jurnal "
        "(dengan kutipan) → **🕳️ Gap Penelitian** merangkum pola lintas-jurnal "
        "menjadi gap kolektif → **💡 Usulan Penelitian** menjawab gap tersebut → "
        "halaman **🚀 Tindak Lanjut Gap** memandu langkah berikutnya."
    )

    # ── Unduh paket lengkap satu berkas (ramah agen AI) ──
    _bundle_md = build_agent_bundle_md(job_id, status, results)
    _n_papers = results.get("files_processed") or len(_weaknesses)
    dl1, dl2 = st.columns([1, 2])
    with dl1:
        st.download_button(
            "🤖 Unduh paket lengkap (.md)",
            data=_bundle_md.encode("utf-8"),
            file_name=f"analisis_gap_{_n_papers}jurnal_{job_id[:8]}.md",
            mime="text/markdown",
            width="stretch",
        )
    with dl2:
        st.caption(
            f"Satu berkas Markdown (~{len(_bundle_md) // 1024} KB, "
            f"±{len(_bundle_md) // 4000}k token) berisi **seluruh** hasil run ini: "
            "korpus, ringkasan, status lapisan metode, indikator gap beserta "
            "rantai provenans dan kutipan verbatim, usulan + skor kebaruan, peta "
            "jalan, kekurangan per jurnal, metrik, dan keterbatasan. "
            "Diawali front-matter YAML agar metadatanya bisa diurai mesin — "
            "cukup lampirkan berkas ini ke agen AI tanpa akses API."
        )

    # ── Unduh data mentah PDF → chunk ──
    with st.expander(
        "📦 Unduh hasil ekstraksi PDF → chunk (teks mentah, sebelum diolah LLM)"
    ):
        st.caption(
            f"Berisi **seluruh {results.get('total_chunks') or '—'} chunk** dari "
            f"{_n_papers} jurnal — teks verbatim hasil pemotongan PDF, belum "
            "diringkas atau ditafsirkan LLM. Berguna untuk mengindeks ulang, "
            "memeriksa kualitas ekstraksi, atau memberi konteks mentah ke agen. "
            "Berkasnya besar (±2 MB), jadi disiapkan hanya saat diminta."
        )
        fmt_label = st.radio(
            "Format",
            ["JSONL — satu chunk per baris (untuk program/agen)",
             "Markdown — dikelompokkan per jurnal (untuk dibaca)"],
            key="chunk_fmt",
            horizontal=False,
        )
        fmt = "jsonl" if fmt_label.startswith("JSONL") else "md"
        _ck = f"chunk_export_{job_id}_{fmt}"

        if st.button("⚙️ Siapkan berkas", key=f"prep_{fmt}"):
            with st.spinner("Mengambil chunk dari vector store…"):
                blob, err = fetch_chunk_export(job_id, fmt)
            if err:
                st.session_state.pop(_ck, None)
                st.error(err)
            else:
                st.session_state[_ck] = blob

        blob = st.session_state.get(_ck)
        if blob:
            st.download_button(
                f"📥 Unduh chunk (.{fmt})",
                data=blob,
                file_name=f"chunks_{_n_papers}jurnal_{job_id[:8]}.{fmt}",
                mime="application/x-ndjson" if fmt == "jsonl" else "text/markdown",
            )
            st.caption(f"Siap: {len(blob) / 1024 / 1024:.1f} MB")

    tabs = st.tabs([
        "📝 Ringkasan", "📄 Gap per Jurnal", "🧠 Topik",
        "🕳️ Gap Penelitian", "💡 Usulan Penelitian", "🗺️ Peta Jalan",
    ])
    with tabs[0]:
        st.markdown(results.get("summary") or "_(ringkasan kosong)_")
        stats_bits = []
        if results.get("files_processed"):
            stats_bits.append(f"{results['files_processed']} file")
        if results.get("total_chunks"):
            stats_bits.append(f"{results['total_chunks']} chunk")
        if (results.get("llm_info") or {}).get("model"):
            stats_bits.append(f"model {results['llm_info']['model']}")
        if results.get("execution_mode"):
            stats_bits.append(f"mode {results['execution_mode']}")
        if stats_bits:
            st.caption(" · ".join(stats_bits))
        if results.get("skills_used"):
            chips = " ".join(f"`{s}`" for s in results["skills_used"])
            st.markdown(f"🧠 **Dipandu AI-Research-SKILLs:** {chips}")
            st.caption(
                "Panduan skill disisipkan otomatis ke setiap tahap LLM "
                "(topik, ringkasan, gap, usulan, peta jalan)."
            )
        st.divider()
        render_method_layer_status(results)
    with tabs[1]:
        st.page_link(
            "page_journals.py",
            label="Buka halaman khusus 📚 Jurnal & Gap (baca per jurnal, cari & saring, unduh CSV)",
            icon="📚",
        )
        _render_paper_analysis_result(
            {
                "groups": results.get("paper_groups"),
                "similarity": results.get("paper_similarity"),
                "weaknesses": results.get("paper_weaknesses"),
                "papers_info": results.get("papers_info"),
            },
            key="final",
        )
    with tabs[2]:
        _render_topics_result({"topics": results.get("topics")})
    with tabs[3]:
        st.page_link(
            "page_followup.py",
            label="Lanjutkan: pilih gap → usulan → peta jalan → rencana penelitian",
            icon="🚀",
        )
        _render_gaps_result({
            "gaps": results.get("gaps"),
            "papers_info": results.get("papers_info"),
        })
        render_gap_method_explainer()
    with tabs[4]:
        st.page_link(
            "page_followup.py",
            label="Tindak lanjut: kembangkan usulan jadi rencana penelitian lengkap",
            icon="🚀",
        )
        if results.get("proposal_intro"):
            st.markdown(f"> {results['proposal_intro']}")
        _render_proposal_result({
            "recommendations": results.get("recommendations"),
            "related_paper_refs": results.get("related_paper_refs"),
            "gaps": results.get("gaps"),
        })
    with tabs[5]:
        _render_roadmap_result({"roadmap": results.get("roadmap")})

    # ── Knowledge graph ──
    st.divider()
    render_knowledge_graph(job_id)

# ── Detail proses per tahap ──
st.divider()
st.subheader("🧭 Detail Proses per Tahap")
st.caption(
    "Klik tiap tahap untuk melihat hasilnya (📦) dan prompt + jawaban LLM (🧠) — "
    "transparansi penuh atas apa yang dilakukan sistem."
)

stage_states = derive_stage_states(events, job_status)
file_rows = derive_file_rows(events)

for pid, s_icon, s_title, s_desc in STAGES:
    stage = stage_states[pid]
    chip_icon, chip_label, chip_color = STATE_CHIPS[stage["state"]]
    bucket = artifacts_by_phase.get(pid, {"result": None, "extraction": [], "llm": []})

    with st.container(border=True):
        c1, c2 = st.columns([4, 2])
        with c1:
            st.markdown(f"**{s_icon} {s_title}**  \n:gray[{s_desc}]")
        with c2:
            if stage["state"] == "running" and stage["started_at"]:
                elapsed = int((time.time() - stage["started_at"]) * 1000)
                st.markdown(f":{chip_color}[{chip_icon} {chip_label}]  \n⏱️ {fmt_duration(elapsed)}")
            elif stage["duration_ms"] is not None:
                st.markdown(f":{chip_color}[{chip_icon} {chip_label}]  \n⏱️ {fmt_duration(stage['duration_ms'])}")
            else:
                st.markdown(f":{chip_color}[{chip_icon} {chip_label}]")

        # Ringkasan metrik tahap dari event
        if pid == "ingestion" and file_rows:
            with st.expander(f"Progres per file ({len(file_rows)})",
                             expanded=(stage["state"] == "running")):
                for fr in file_rows:
                    badge = METHOD_BADGES.get(fr["method"], fr["method"] or "⏳ sedang diekstrak…")
                    cols = st.columns([3, 2, 1, 1, 1])
                    cols[0].markdown(f"`{fr['index']}/{fr['of']}` **{fr['file']}**")
                    cols[1].markdown(badge)
                    cols[2].markdown(f"{fr['chunks']} chunk" if fr["chunks"] is not None else "…")
                    cols[3].markdown(f"{fr['chars']:,} kar" if fr["chars"] is not None else "…")
                    cols[4].markdown(fmt_duration(fr["duration_ms"]) if fr["state"] == "done" else "🔄")
        elif stage["data"]:
            metrics = [
                f"**{v}** {STAGE_METRIC_LABELS.get(k, k)}"
                for k, v in stage["data"].items()
                if k not in ("error_type", "fallback") and str(v).strip() != ""
            ]
            if stage["state"] == "fallback":
                metrics.append(
                    f"⚠️ koordinator gagal ({stage['data'].get('error_type', '?')}) — lanjut fallback LLM"
                )
            if metrics:
                st.caption(" · ".join(metrics))

        # 📦 HASIL tahap (artefak result / extraction)
        if pid == "ingestion" and bucket["extraction"]:
            with st.expander(f"📦 Hasil ekstraksi ({len(bucket['extraction'])} file)"):
                _render_extraction_results(bucket["extraction"])
        elif bucket["result"] is not None and pid in RESULT_RENDERERS:
            with st.expander("📦 Hasil tahap ini"):
                RESULT_RENDERERS[pid](bucket["result"]["payload"])

        # 🧠 Prompt & jawaban LLM
        if bucket["llm"]:
            with st.expander(f"🧠 Prompt & Jawaban LLM ({len(bucket['llm'])})"):
                _render_llm_traces(bucket["llm"])

# ── Auto refresh ──
if (
    auto_refresh
    and not st.session_state.get("_no_autorefresh")  # hook untuk AppTest
    and job_status in ("queued", "running")
):
    time.sleep(REFRESH_SECONDS)
    st.rerun()
