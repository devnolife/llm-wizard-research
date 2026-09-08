"""Langkah 3 — indikator synthesis gap (neuro-symbolic) pada jurnal yang diunggah.

Menjalankan pipeline analisis 8 tahap yang dievaluasi tesis
(``POST /api/upload-and-analyze``) pada PDF yang sama, lalu memperlihatkan
keluaran tahap ``neuro_symbolic``: fakta SPO → graf pengetahuan → indikator
Cooper/Booth (fragmentasi, inkonsistensi, ketidaklengkapan kolektif, ditambah
ketiadaan dukungan bukti) → vonis Rule Engine → kalibrasi & abstain.
Hasil tampil begitu tahap itu selesai, meski job masih menyusun ringkasan,
usulan, dan roadmap (bahan langkah berikutnya). Polling oleh ``app.py``.
"""

from __future__ import annotations

import json
import re

import pandas as pd
import streamlit as st

from wl_common import (
    JOB_STATUS_BADGES,
    TERMINAL_STATUSES,
    cancel_job,
    job_artifacts,
    job_events,
    job_graph,
    job_status,
    render_reading_text,
    render_table_with_reader,
    render_view_switch,
    section_label,
    short_name,
    start_legacy_analysis,
)

# Urutan tahap pipeline legacy (api/auto_analysis.py). Tahap setelah
# neuro_symbolic tetap berjalan, tetapi hasilnya bahan langkah berikutnya.
PHASES = [
    ("ingestion", "Baca & chunk PDF (masuk vector store)"),
    ("topics", "Topik utama (LLM)"),
    ("paper_analysis", "Basis, persamaan & kekurangan tiap jurnal (LLM)"),
    ("neuro_symbolic", "Neuro-symbolic: fakta → graf → indikator → Rule Engine"),
    ("summary", "Ringkasan (bahan langkah berikutnya)"),
    ("gaps", "Normalisasi indikator"),
    ("proposal", "Usulan penelitian (bahan langkah berikutnya)"),
    ("roadmap", "Roadmap (bahan langkah berikutnya)"),
]
GAP_TYPE_BADGES = {
    "FRAGMENTATION": "🧩 Fragmentasi",
    "INCONSISTENCY": "⚡ Inkonsistensi",
    "INCOMPLETENESS": "🕳️ Ketidaklengkapan",
    "SUPPORT_GAP": "🔍 Ketiadaan dukungan bukti",
    "LLM_UNVALIDATED": "🤖 LLM (tanpa validasi)",
}
VERDICT_BADGES = {"PASS": "✅ PASS", "FLAG": "⚠️ FLAG", "REJECT": "⛔ REJECT"}
DETECTION_LABELS = {
    "topic_clustering": "klaster pendekatan (embedding; modularitas Q, silhouette)",
    "citation_isolation": "isolasi struktural di graf pengetahuan + kandidat jembatan",
    "fact_table_contradicts": "relasi CONTRADICTS di tabel fakta (diverifikasi classifier)",
    "nli_adjudicated": "kontradiksi klaim via model NLI (cross-encoder)",
    "claim_adjudication": "adjudikasi klaim (tanpa model NLI)",
    "llm_nli": "kontradiksi via LLM (pelengkap)",
    "aspect_coverage": "cakupan aspek: aspek yang diharapkan vs yang dibahas",
    "evidence_gap_map": "peta bukti: sel baris×kolom tanpa studi",
    "methodology_coverage": "keragaman metodologi (kata kunci)",
    "workflow_stage_mining": "tahapan metode: tahap yang tidak pernah divariasikan",
    "evidence_support": "dukungan bukti primer (leave-one-out)",
}
# Jenis pernyataan penulis yang dipakai sebagai bukti pendukung (bukan skor):
# dua dari telaah kekurangan per jurnal, tiga dari gap mining langkah 2.
AUTHOR_KIND_LABELS = {
    "tersurat": "kekurangan tersurat (kutipan terverifikasi)",
    "tersirat": "kekurangan tersirat (inferensi, tanpa kutipan)",
    "explicit_future_work": "future work eksplisit (gap mining)",
    "stated_limitation": "keterbatasan yang dinyatakan (gap mining)",
    "implicit_gap": "gap implisit (gap mining)",
}
# Label tahap workflow-stage mining (selaras core/gap_detection/workflow_stages.STAGES).
STAGE_LABELS = {
    "data_source": "Sumber data",
    "data_collection": "Pengumpulan data",
    "preprocessing": "Prapemrosesan",
    "representation_features": "Representasi/fitur",
    "method_model": "Metode/model",
    "evaluation_metrics": "Metrik evaluasi",
    "validation_design": "Desain validasi",
    "tools_environment": "Alat/lingkungan",
}
TRACE_LABELS = {
    "observe": "👁️ Observe — ambil passage, ekstrak fakta, bangun graf",
    "think": "🧠 Think — deteksi indikator, cek NLI",
    "act": "⚙️ Act — validasi Rule Engine, rekomendasi",
    "evaluate": "🔍 Evaluate — kritik-diri, putuskan revisi",
    "analyze": "Analisis domain (mode berurutan)",
    "detect_gaps": "Deteksi gap (mode berurutan)",
    "recommend": "Rekomendasi (mode berurutan)",
    "coordinator_fallback": "⚠️ Coordinator gagal → fallback LLM",
}
MODE_LABELS = {
    "langgraph": "LangGraph (Observe → Think → Act → Evaluate, dengan loop revisi)",
    "sequential": "berurutan (LangGraph tidak tersedia; tanpa loop revisi)",
    "llm_fallback": "fallback LLM (lapisan neuro-symbolic GAGAL dijalankan)",
}


def reset() -> None:
    for key in ("ns_job_id", "ns_cache"):
        st.session_state.pop(key, None)


def _gap_type(g: dict) -> str:
    return g.get("type") or g.get("indicator_type") or "?"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _find_quote(quote: str, chunks_by_id: dict):
    """Chunk langkah 1 yang memuat ``quote`` beserta potongan persisnya (untuk highlight)."""
    words = [re.escape(w) for w in (quote or "").split()[:40]]
    if len(words) < 3:
        return None, None
    pattern = re.compile(r"\s+".join(words), re.IGNORECASE)
    for chunk in chunks_by_id.values():
        m = pattern.search(chunk.get("text", ""))
        if m:
            return chunk, m.group(0)
    return None, None


# ── Progres ────────────────────────────────────────────────────────────────

def _phase_states(events: list) -> dict:
    states: dict = {}
    for e in events:
        kind, phase = e.get("type", ""), e.get("phase")
        if not phase or not kind.startswith("phase."):
            continue
        states[phase] = {"state": kind.split(".", 1)[1], "duration_ms": e.get("duration_ms")}
    return states


def _render_progress(api_base: str, job_id: str, status: dict, phases: dict) -> None:
    state = status.get("status", "queued")
    icon, label = JOB_STATUS_BADGES.get(state, ("❔", state))
    st.markdown(f"**Job `{job_id[:8]}…` — {icon} {label}**")
    if state not in TERMINAL_STATUSES:
        st.progress(min(100, int(status.get("progress") or 0)) / 100,
                    text=status.get("message") or "…")
    else:
        st.caption(status.get("message") or "")

    with st.expander("Tahapan pipeline", expanded=state not in TERMINAL_STATUSES):
        for key, text in PHASES:
            ph = phases.get(key)
            if not ph:
                mark, extra = "⬜", ""
            elif ph["state"] == "completed":
                mark = "✅"
                extra = f" · {ph['duration_ms'] / 1000:.0f} dtk" if ph.get("duration_ms") else ""
            elif ph["state"] == "failed":
                mark, extra = "❌", " · gagal, pipeline lanjut dengan fallback"
            else:
                mark, extra = "🔄", ""
            st.caption(f"{mark} {text}{extra}")

    b1, b2 = st.columns(2)
    if state not in TERMINAL_STATUSES:
        if b1.button("⏹️ Batalkan", key="ns-cancel", width="stretch"):
            cancel_job(api_base, job_id)
            st.rerun()
    if b2.button("🔁 Mulai dari awal", key="ns-reset", width="stretch"):
        reset()
        st.rerun()


# ── Pengambilan hasil ──────────────────────────────────────────────────────

def _facts_from_graph(graph: dict) -> list:
    nodes = {n.get("id"): n for n in graph.get("nodes") or []}

    def name(node_id):
        n = nodes.get(node_id) or {}
        return n.get("name") or node_id, n.get("entity_type") or "?"

    facts = []
    for e in graph.get("edges") or []:
        if not e.get("predicate"):
            continue
        s_name, s_type = name(e.get("source"))
        o_name, o_type = name(e.get("target"))
        facts.append({
            "subject": s_name, "subject_type": s_type,
            "predicate": e["predicate"],
            "object": o_name, "object_type": o_type,
            "confidence": e.get("confidence"),
            "source_paper": e.get("source_paper") or "",
            "source": e.get("source") or "",
            "is_inferred": bool(e.get("is_inferred")),
        })
    return facts


def _load(api_base: str, job_id: str, status: dict) -> dict | None:
    """Hasil tahap neuro-symbolic: dari ``results`` bila job selesai, dari artefak
    tahap bila job masih berjalan. Di-cache per (job, sumber)."""
    completed = status.get("status") == "completed"
    want = "results" if completed else "artifact"
    cache = st.session_state.get("ns_cache") or {}
    if cache.get("job_id") == job_id and cache.get("source") == want:
        return cache

    with st.spinner("Mengambil hasil…"):
        if completed:
            r = status.get("results") or {}
            indicators = r.get("gap_indicators") or []
            cache = {
                "job_id": job_id, "source": want,
                "indicators": indicators,
                # tanpa coordinator, results.gaps berisi gap buatan LLM (fallback)
                "fallback_gaps": [] if indicators else (r.get("gaps") or []),
                "sample_facts": r.get("sample_facts") or [],
                "stats": r.get("fact_table_stats") or {},
                "rule_report": r.get("rule_engine_report") or {},
                "trace": r.get("reasoning_trace") or [],
                "mode": r.get("execution_mode") or "?",
                "topics": r.get("topics") or [],
                "facts": None,
            }
            try:
                cache["facts"] = _facts_from_graph(job_graph(api_base, job_id))
            except Exception:
                cache["facts"] = None
        else:
            arts = job_artifacts(api_base, job_id, "neuro_symbolic")
            result = next((a.get("payload") or {} for a in reversed(arts)
                           if a.get("kind") == "result"), None)
            if result is None:
                return None
            cache = {
                "job_id": job_id, "source": want,
                "indicators": result.get("indicators") or [],
                "fallback_gaps": [],
                "sample_facts": result.get("sample_facts") or [],
                "stats": result.get("fact_table_stats") or {},
                "rule_report": result.get("rule_engine_report") or {},
                "trace": result.get("reasoning_trace") or [],
                "mode": result.get("mode") or "?",
                "topics": [],
                "facts": None,
            }
    st.session_state["ns_cache"] = cache
    return cache


# ── Hasil: indikator ───────────────────────────────────────────────────────

def _confidence_text(g: dict) -> str:
    raw = g.get("confidence")
    cal = g.get("calibrated_confidence")
    if raw is None:
        return "—"
    text = f"{float(raw):.2f}"
    if cal is not None and abs(float(cal) - float(raw)) >= 0.005:
        text += f" → terkalibrasi {float(cal):.2f}"
    return text


def _render_indicator_card(g: dict, chunks_by_id: dict) -> None:
    verdict = g.get("rule_engine_verdict")
    method = g.get("detection_method")
    with st.container(border=True):
        head = f"**{GAP_TYPE_BADGES.get(_gap_type(g), _gap_type(g))}**"
        if method:
            head += f" · {DETECTION_LABELS.get(method, method)}"
        head += f" · Rule Engine {VERDICT_BADGES.get(verdict, '— tanpa vonis')}"
        head += f" · keyakinan {_confidence_text(g)}"
        st.markdown(head)
        if g.get("needs_review"):
            st.warning("Perlu tinjauan peneliti — sistem menahan diri menyebut ini temuan: "
                       + "; ".join(g.get("abstention_reasons") or ["tanpa alasan tercatat"]))
        if g.get("title") and g["title"] not in (g.get("description") or ""):
            st.markdown(f"**{g['title']}**")
        render_reading_text(g.get("description", ""))

        evidence = g.get("evidence") or []
        if evidence:
            st.markdown("**Bukti / metrik**")
            for item in evidence:
                st.markdown(f"- {item}")

        quotes = g.get("supporting_quotes") or []
        if quotes:
            st.markdown("**Kutipan verbatim dari jurnal**")
            for i, q in enumerate(quotes):
                quote = q.get("quote", "")
                origin = ""
                if q.get("origin") == "author_stated":
                    origin = (" · ✍️ pernyataan penulis: "
                              + AUTHOR_KIND_LABELS.get(q.get("kind"), str(q.get("kind") or "")))
                elif q.get("origin") == "workflow_stage":
                    origin = f" · 🧪 tahap metode: {STAGE_LABELS.get(q.get('stage'), q.get('stage') or '')}"
                st.markdown(f"> {quote}\n>\n> — *{q.get('source_paper') or '?'}*"
                            + (f" · {q['context']}" if q.get("context") else "") + origin)
                chunk, span = _find_quote(quote, chunks_by_id)
                if chunk:
                    with st.expander(f"Lihat di chunk #{chunk['chunk_index']} · "
                                     f"{section_label(chunk['section_normalized'])} · "
                                     f"hal. {chunk.get('page_start') or '?'} · {chunk.get('source', '')}"):
                        render_reading_text(chunk["text"], highlight=span)
                else:
                    st.caption("Kutipan tidak ditemukan di chunk langkah 1 (teks passage dipotong "
                               "500 karakter oleh retriever, atau pembaca PDF berbeda).")

        related = [str(p) for p in (g.get("related_papers") or []) if str(p).strip()]
        if related:
            st.caption("Jurnal terkait: " + ", ".join(short_name(p, 40) for p in related[:12])
                       + (f" … (+{len(related) - 12})" if len(related) > 12 else ""))

        _render_coverage_map(g)
        _render_stage_matrix(g)
        _render_author_corroboration(g)

        directions = g.get("suggested_directions") or []
        if directions:
            st.markdown("**Arah yang disarankan (indikatif)**")
            for d in directions:
                st.markdown(f"- {d}")

        subgraph = g.get("evidence_subgraph") or []
        if subgraph:
            st.markdown("**Sub-graf bukti**")
            st.dataframe(
                [{"Dari": e.get("from_name") or e.get("from"), "Relasi": e.get("predicate"),
                  "Ke": e.get("to_name") or e.get("to"), "Jurnal": e.get("source_paper", "")}
                 for e in subgraph],
                width="stretch", hide_index=True,
            )

        prov = g.get("provenance") or {}
        if prov:
            if prov.get("complete"):
                st.caption("Provenans lengkap: klaim → jurnal terkutip → kutipan → validasi "
                           f"({prov.get('validation_outcome') or '—'}"
                           + (f"; {prov['validation_detail']}" if prov.get("validation_detail") else "")
                           + ").")
            else:
                st.caption("Provenans belum lengkap — mata rantai hilang: "
                           + ", ".join(prov.get("broken_links") or ["?"]) + ".")

        with st.expander("Detail mentah (JSON)"):
            st.json(g, expanded=False)


def _author_corroboration(g: dict) -> list:
    for sub in g.get("sub_indicators") or []:
        if isinstance(sub, dict) and sub.get("author_corroboration"):
            return list(sub["author_corroboration"])
    return []


def _stage_matrix(g: dict) -> dict:
    for sub in g.get("sub_indicators") or []:
        if isinstance(sub, dict) and isinstance(sub.get("stage_matrix"), dict):
            return sub["stage_matrix"]
    return {}


def _sub_dict(g: dict, key: str) -> dict:
    for sub in g.get("sub_indicators") or []:
        if isinstance(sub, dict) and isinstance(sub.get(key), dict):
            return sub[key]
    return {}


_AXES_SOURCE_LABELS = {
    "curated": "ontologi domain kurasi (YAML)",
    "llm_grounded": "usulan LLM yang lolos grounding korpus",
    "default": "kosakata bawaan (generik)",
}


def _render_coverage_map(g: dict) -> None:
    """Grid baris x kolom berisi jumlah studi; sel kosong = kandidat gap, bukan gap.
    Asal sumbu (kurasi / LLM grounded / bawaan) ditampilkan agar bisa diaudit."""
    matrix = _sub_dict(g, "coverage_matrix")
    grid = matrix.get("grid") or []
    if not grid:
        return
    axes = _sub_dict(g, "axes_spec")
    source = axes.get("source") or "default"
    with st.expander(
        f"🗺️ Peta bukti · {matrix.get('empty_cells', 0)} sel kosong dari "
        f"{len(matrix.get('rows') or [])}×{len(matrix.get('columns') or [])} · sumbu: "
        f"{_AXES_SOURCE_LABELS.get(source, source)}"
        + (f" ({axes['slug']}.yaml)" if axes.get("slug") else ""),
        expanded=False,
    ):
        st.dataframe([{"Baris \\ Kolom": r.get("row"), **{k: v for k, v in r.items() if k != "row"}}
                      for r in grid], width="stretch", hide_index=True)
        for n in axes.get("notes") or []:
            st.caption(n)
        if axes.get("dropped_ungrounded"):
            st.caption("Istilah usulan LLM yang dibuang karena tidak ada di korpus: "
                       + ", ".join(axes["dropped_ungrounded"][:8]))
        st.caption("Sel berisi JUMLAH studi (bukan skor). Sel kosong adalah kandidat untuk "
                   "dinilai peneliti — literatur tidak menetapkan aturan 'count < k'.")


def _render_stage_matrix(g: dict) -> None:
    """Tahap metode x jurnal (workflow-stage mining).

    HOMOGEN = satu varian pada >= min_papers jurnal yang menyatakan tahap itu;
    jurnal yang tidak menyatakan tahap tidak dihitung setuju. Tabel ini bukti
    indikator Ketidaklengkapan, bukan skor tambahan.
    """
    matrix = _stage_matrix(g)
    stages = matrix.get("stages") or []
    if not stages:
        return
    papers = [str(p) for p in matrix.get("papers") or []]
    homogeneous = [s for s in stages if s.get("homogeneous")]
    with st.expander(
        f"🧪 Matriks tahapan metode · {len(homogeneous)}/{len(stages)} tahap homogen pada "
        f"{len(papers)} jurnal · kutipan terverifikasi "
        f"{matrix.get('verified_quotes', 0)}/{matrix.get('total_quotes', 0)}",
        expanded=bool(homogeneous),
    ):
        rows = []
        for s in stages:
            row = {"Tahap": s.get("label") or s.get("stage"),
                   "Status": "HOMOGEN" if s.get("homogeneous") else
                   ("beragam" if s.get("variants") else "tidak dinyatakan")}
            value_by_paper = {}
            for v in s.get("variants") or []:
                for p in v.get("papers") or []:
                    value_by_paper[str(p)] = v.get("value", "")
            for p in papers:
                row[short_name(p, 24)] = value_by_paper.get(p, "—")
            rows.append(row)
        st.dataframe(rows, width="stretch", hide_index=True)
        st.caption(f"Pencocokan varian: {matrix.get('matcher', '?')} · ambang homogen: satu varian "
                   f"pada ≥ {matrix.get('min_papers', 3)} jurnal yang menyatakan tahap itu.")


def _render_author_corroboration(g: dict) -> None:
    """Pernyataan penulis (kekurangan / future work) yang sejalan dengan indikator.

    Ini bukti pendukung, bukan definisi gap: saran future work satu penulis
    tetap bukan synthesis gap (BAB II 2.2.2), tetapi menunjukkan indikator
    lintas-jurnal ini menamai masalah yang penulis sendiri akui.
    """
    hits = _author_corroboration(g)
    if not hits:
        return
    sources = {h.get("source") for h in hits if h.get("source")}
    st.markdown(f"**✍️ Dikuatkan pernyataan penulis** · {len(hits)} pernyataan dari "
                f"{len(sources)} jurnal — bukti pendukung, tidak mengubah keyakinan")
    for h in hits:
        label = AUTHOR_KIND_LABELS.get(h.get("kind"), str(h.get("kind") or ""))
        score = h.get("score")
        score_txt = f" · kemiripan {float(score):.2f} ({h.get('method', '')})" if score is not None else ""
        st.markdown(f"- *{short_name(str(h.get('source') or '?'), 40)}* — {label}{score_txt}"
                    f"  \n  {h.get('text', '')}"
                    + (f"  \n  ↳ cocok dengan: _{h['matched_term']}_" if h.get("matched_term") else ""))


def _render_indicators(indicators: list, chunks_by_id: dict) -> None:
    types = [t for t in GAP_TYPE_BADGES if any(_gap_type(g) == t for g in indicators)]
    types += sorted({_gap_type(g) for g in indicators} - set(types))
    f1, f2 = st.columns([3, 1])
    type_sel = f1.multiselect("Jenis indikator", types, default=types, key="ns-type",
                              format_func=lambda t: GAP_TYPE_BADGES.get(t, t))
    with_review = f2.toggle("Sertakan yang perlu tinjauan", value=True, key="ns-review")
    shown = [g for g in indicators
             if _gap_type(g) in type_sel and (with_review or not g.get("needs_review"))]

    def row(g: dict) -> dict:
        cal = g.get("calibrated_confidence")
        return {
            "Jenis": GAP_TYPE_BADGES.get(_gap_type(g), _gap_type(g)),
            "Metode": (g.get("detection_method") or "—").replace("_", " "),
            "Keyakinan": cal if cal is not None else g.get("confidence"),
            "Vonis": g.get("rule_engine_verdict") or "—",
            "Tinjauan": "⚠️" if g.get("needs_review") else "",
            "Jurnal": len(g.get("related_papers") or []),
            "Deskripsi": g.get("description", ""),
        }

    render_view_switch(
        shown, "ns-ind", row, lambda i: _render_indicator_card(shown[i], chunks_by_id),
        column_config={
            "Keyakinan": st.column_config.NumberColumn(format="%.2f", width="small"),
            "Deskripsi": st.column_config.TextColumn(width="large"),
        },
    )
    jsonl = "\n".join(json.dumps(g, ensure_ascii=False) for g in indicators)
    st.download_button("⬇️ Unduh indikator (.jsonl)", data=jsonl.encode("utf-8"),
                       file_name="indikator.jsonl", mime="application/x-ndjson", key="dl-ns-ind")


# ── Hasil: fakta & graf ────────────────────────────────────────────────────

def _render_fact_detail(f: dict, chunks_by_id: dict) -> None:
    with st.container(border=True):
        st.markdown(f"**{f.get('subject')}** ({f.get('subject_type')}) —"
                    f" *{f.get('predicate')}* → **{f.get('object')}** ({f.get('object_type')})")
        st.caption(f"keyakinan {float(f.get('confidence') or 0):.2f} · jurnal: {f.get('source_paper') or '—'}"
                   + (" · fakta hasil inferensi" if f.get("is_inferred") else ""))
        if f.get("source"):
            st.markdown("Kalimat sumber:")
            render_reading_text(f["source"])
            chunk, span = _find_quote(f["source"], chunks_by_id)
            if chunk:
                with st.expander(f"Lihat di chunk #{chunk['chunk_index']} · "
                                 f"{section_label(chunk['section_normalized'])} · {chunk.get('source', '')}"):
                    render_reading_text(chunk["text"], highlight=span)


def _render_facts(cache: dict, chunks_by_id: dict) -> None:
    stats = cache.get("stats") or {}
    m = st.columns(5)
    m[0].metric("Fakta (SPO)", stats.get("total_facts", 0))
    m[1].metric("Triple unik", stats.get("unique_triples", "—"))
    m[2].metric("Duplikat", stats.get("duplicate_facts", "—"))
    m[3].metric("Entitas", stats.get("total_entities", 0))
    m[4].metric("Jurnal berfakta", stats.get("papers_indexed", "—"))
    by_type = stats.get("entities_by_type") or {}
    by_pred = stats.get("facts_by_predicate") or {}
    if by_type or by_pred:
        c1, c2 = st.columns(2)
        if by_type:
            c1.caption("Entitas per tipe")
            c1.bar_chart(pd.DataFrame({"Entitas": by_type}), height=160)
        if by_pred:
            c2.caption("Fakta per predikat")
            c2.bar_chart(pd.DataFrame({"Fakta": by_pred}), height=160)

    facts = cache.get("facts")
    from_graph = facts is not None
    if facts is None:
        facts = cache.get("sample_facts") or []
        if facts:
            st.caption(f"Sampel {len(facts)} fakta pertama — tabel lengkap dan graf tersedia "
                       "setelah job selesai.")
    if not facts:
        st.info("Tidak ada fakta yang terekstrak." if stats.get("total_facts", 0) == 0
                else "Daftar fakta belum tersedia.")
        return

    def row(f: dict) -> dict:
        return {
            "Subjek": f.get("subject"), "Tipe S": f.get("subject_type"),
            "Predikat": f.get("predicate"),
            "Objek": f.get("object"), "Tipe O": f.get("object_type"),
            "Keyakinan": f.get("confidence"),
            "Jurnal": short_name(f.get("source_paper") or "—", 32),
        }

    total = stats.get("total_facts", 0)
    if from_graph and len(facts) < total:
        st.caption(f"{len(facts)} relasi dalam graf pengetahuan dari {total} fakta (graf menyimpan "
                   "satu relasi per pasangan entitas) — klik satu baris untuk membaca kalimat sumbernya.")
    else:
        st.caption(f"{len(facts)} fakta — klik satu baris untuk membaca kalimat sumbernya.")
    render_table_with_reader([row(f) for f in facts], lambda i: _render_fact_detail(facts[i], chunks_by_id),
                             "ns-facts", column_config={
                                 "Keyakinan": st.column_config.NumberColumn(format="%.2f", width="small")})
    jsonl = "\n".join(json.dumps(f, ensure_ascii=False) for f in facts)
    st.download_button("⬇️ Unduh fakta (.jsonl)", data=jsonl.encode("utf-8"),
                       file_name="fakta.jsonl", mime="application/x-ndjson", key="dl-ns-facts")


# ── Hasil: jejak penalaran ─────────────────────────────────────────────────

def _render_trace(trace: list) -> None:
    if not trace:
        st.info("Tidak ada jejak penalaran tersimpan.")
        return
    for entry in trace:
        phase = entry.get("phase", "?")
        label = TRACE_LABELS.get(phase, phase)
        if entry.get("iteration") is not None:
            label += f" · iterasi {entry['iteration']}"
        with st.container(border=True):
            st.markdown(f"**{label}**")
            for action in entry.get("actions") or []:
                st.markdown(f"- {action}")
            if entry.get("status"):
                st.caption(f"status: {entry['status']}")
            if entry.get("error"):
                st.error(entry["error"])


# ── Hasil ──────────────────────────────────────────────────────────────────

def _render_results(cache: dict, chunks_by_id: dict) -> list:
    mode = cache.get("mode")
    indicators = cache.get("indicators") or []
    fallback = cache.get("fallback_gaps") or []
    if mode == "llm_fallback" or (not indicators and fallback):
        st.error(
            "Lapisan neuro-symbolic **gagal dijalankan** (coordinator error). Gap di bawah "
            "dibuat LLM langsung lalu dicek Rule Engine — **bukan** hasil ekstraksi fakta/graf."
        )
        indicators = fallback
    elif mode == "sequential":
        st.info(f"Mode eksekusi: {MODE_LABELS['sequential']}.")
    else:
        st.caption(f"Mode eksekusi: {MODE_LABELS.get(mode, mode)}")

    counts = {t: sum(1 for g in indicators if _gap_type(g) == t) for t in GAP_TYPE_BADGES}
    rule = cache.get("rule_report") or {}
    stats = cache.get("stats") or {}
    m = st.columns(7)
    m[0].metric("Indikator", len(indicators))
    m[1].metric("Fragmentasi", counts["FRAGMENTATION"])
    m[2].metric("Inkonsistensi", counts["INCONSISTENCY"])
    m[3].metric("Ketidaklengkapan", counts["INCOMPLETENESS"])
    m[4].metric("Dukungan bukti", counts["SUPPORT_GAP"])
    m[5].metric("Rule Engine", f"{rule.get('passed', 0)}✅ {rule.get('flagged', 0)}⚠️ {rule.get('rejected', 0)}⛔",
                help="PASS / FLAG / REJECT. Indikator REJECT sudah dibuang sebelum tampil.")
    m[6].metric("Perlu tinjauan", sum(1 for g in indicators if g.get("needs_review")),
                help="Sistem abstain: keyakinan terkalibrasi di bawah ambang atau provenans belum lengkap.")
    if stats.get("total_facts", 0) == 0 and indicators:
        st.warning("Tabel fakta kosong (0 fakta SPO) — indikator di atas bertumpu pada klaster/"
                   "aspek, bukan pada graf pengetahuan. Cek layanan LLM (ekstraksi fakta gagal?).")

    tab_ind, tab_facts, tab_trace = st.tabs([
        f"🧩 Indikator ({len(indicators)})",
        f"🔗 Fakta & graf ({stats.get('total_facts', 0)})",
        "🧭 Jejak penalaran",
    ])
    with tab_ind:
        if indicators:
            _render_indicators(indicators, chunks_by_id)
        else:
            st.info("Tidak ada indikator yang lolos Rule Engine. Lihat jejak penalaran untuk "
                    "melihat apa yang dideteksi dan mengapa ditolak.")
    with tab_facts:
        _render_facts(cache, chunks_by_id)
    with tab_trace:
        _render_trace(cache.get("trace") or [])
    return indicators


# ── Entri ──────────────────────────────────────────────────────────────────

def render(api_base: str, uploads, backend_ok: bool, chunks_by_id: dict):
    """Gambar langkah 3. Mengembalikan ``(job_id, status)``; ``status`` None bila belum ada job."""
    st.header("Langkah 3 — indikator synthesis gap (neuro-symbolic)")
    st.write(
        "Berbeda dari langkah 2 yang mengutip kalimat gap **per jurnal**, langkah ini membandingkan "
        "jurnal-jurnal yang Anda unggah **satu sama lain** memakai kerangka Cooper (1998) / Booth "
        "dkk. (2012): **fragmentasi** (dibahas dari sudut berbeda tanpa integrasi), **inkonsistensi** "
        "(temuan bertentangan belum direkonsiliasi), **ketidaklengkapan kolektif** (aspek penting "
        "tak tercakup bersama), ditambah **ketiadaan dukungan bukti** (klaim diulang tanpa bukti primer)."
    )
    st.caption(
        "Alur: LLM mengekstrak fakta subjek–predikat–objek → tabel fakta & graf pengetahuan → "
        "analisis klaster/NLI/cakupan aspek → tiap indikator divalidasi Rule Engine (PASS/FLAG/REJECT) "
        "→ kalibrasi keyakinan; yang lemah ditandai *perlu tinjauan*, bukan disebut temuan. "
        "Catatan jujur: koordinator bekerja pada ≤10 passage paling relevan dengan topik utama "
        "(ekstraksi fakta pada ≤5 di antaranya), bukan seluruh teks jurnal."
    )

    job_id = st.session_state.get("ns_job_id")
    if not job_id:
        gap_job_id = st.session_state.get("gap_job_id")
        if st.button("🧠 Jalankan analisis neuro-symbolic", type="primary",
                     disabled=not uploads or not backend_ok, key="ns-start"):
            try:
                body = start_legacy_analysis(api_base, uploads, gap_job_id=gap_job_id)
                st.session_state["ns_job_id"] = body["job_id"]
                st.rerun()
            except Exception as exc:
                st.error(f"Gagal memulai: {exc}")
        else:
            st.caption("PDF yang sama dikirim ke pipeline analisis 8 tahap (puluhan panggilan LLM; "
                       "biasanya beberapa menit). Hasil tahap neuro-symbolic tampil lebih dulu."
                       + (" Gap per jurnal dari langkah 2 ikut dikirim sebagai bukti pendukung "
                          "indikator." if gap_job_id else
                          " Jalankan langkah 2 dulu bila ingin gap per jurnal ikut menjadi bukti "
                          "pendukung indikator."))
        return None, None

    try:
        status = job_status(api_base, job_id)
    except Exception as exc:
        st.error(f"Tidak bisa membaca status job: {exc}")
        if st.button("🔁 Mulai dari awal", key="ns-reset-err"):
            reset()
            st.rerun()
        return job_id, None

    try:
        phases = _phase_states(job_events(api_base, job_id))
    except Exception:
        phases = {}
    _render_progress(api_base, job_id, status, phases)

    state = status.get("status")
    neuro = phases.get("neuro_symbolic") or {}
    if state == "completed" or neuro.get("state") == "completed":
        cache = _load(api_base, job_id, status)
        if cache:
            if state != "completed":
                st.info("Tahap neuro-symbolic selesai — hasil di bawah sudah final untuk langkah ini. "
                        "Job masih menyusun ringkasan, usulan, dan roadmap (bahan langkah berikutnya).")
            _render_results(cache, chunks_by_id)
    elif neuro.get("state") == "failed":
        st.warning("Lapisan neuro-symbolic gagal; pipeline melanjutkan dengan fallback LLM. "
                   "Hasil fallback (bukan neuro-symbolic) tampil setelah job selesai.")
    elif state in TERMINAL_STATUSES:
        st.error(status.get("error") or status.get("message") or f"Job berakhir: {state}")
    return job_id, status
