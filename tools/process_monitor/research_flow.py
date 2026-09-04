"""Peta proses: apa yang dikerjakan tiap tahap, live maupun setelah selesai.

Sumber kebenarannya ``substeps`` dari ``/api/research/stages``; modul ini hanya
menggambar. Dua tampilan memakai data yang sama:

* ``render_live_map`` — Langkah 2: st.status per tahap, checklist sub-langkah
  yang berpindah ✅ mengikuti event ``substep.*``, plus log aktivitas awam.
* ``render_stage_flow`` — Langkah 3: corong angka masuk → keluar per sub-langkah
  dengan contoh data yang lolos DAN yang dibuang.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from common import fetch_events, fmt_datetime, fmt_duration
from research_common import (
    fetch_records,
    fetch_stages,
    render_metrics_grid,
    render_records_tab,
    render_source_tab,
    render_stage_extras,
    research_jobs,
    stage_result_payload,
    stage_states,
    substep_states,
)
from research_vocab import (
    ENUM_LABELS,
    enum_label,
    help_of,
    label,
    mode_teknis,
    render_glossary,
)

_SUB_ICON = {"pending": "⚪", "running": "⏳", "done": "✅", "error": "❌", "skipped": "⏭️"}
_STATUS_STATE = {"running": "running", "done": "complete", "failed": "error",
                 "cancelled": "error", "pending": "running"}

# Contoh per sub-langkah: kolom mana yang ditampilkan sebagai teks utama.
_SAMPLE_TEXT_FIELDS = ("gap_statement", "text", "label", "file")


# ── helper angka ───────────────────────────────────────────────────────────

def stage_constants(stage_key: str) -> dict:
    """Ambang/bobot tahap dari backend; {} bila backend lama tanpa field itu."""
    stage = next((s for s in fetch_stages() if s["key"] == stage_key), None)
    return (stage or {}).get("constants") or {}


def _num(metrics: dict, key: str | None):
    if not key:
        return None
    return metrics.get(key)


def _funnel_line(sub: dict, metrics: dict, live: dict | None = None) -> str:
    """'343 → 115 (dibuang 228)' dari metrik hasil, atau dari event live.

    Sub-langkah berjenis "periksa" tidak menyaring apa pun: ``keluar`` adalah
    jumlah yang ditandai, jadi ditulis 'diperiksa 10 · ditandai 1', bukan '10 → 1'.
    """
    src = live if live else {}
    masuk = src.get("masuk", _num(metrics, sub["in_metric"]))
    keluar = src.get("keluar", _num(metrics, sub["out_metric"]))
    dibuang = src.get("dibuang", _num(metrics, sub["drop_metric"]))
    if sub.get("jenis") == "periksa":
        parts = []
        if masuk is not None:
            parts.append(f"diperiksa **{masuk}**")
        if keluar is not None:
            parts.append(f"ditandai **{keluar}**")
        return " · ".join(parts)
    parts = []
    if masuk is not None:
        parts.append(f"**{masuk}**")
    if keluar is not None:
        parts.append(f"→ **{keluar}**")
    if dibuang not in (None, 0):
        parts.append(f"(dibuang {dibuang})")
    return " ".join(parts)


def _sub_title(sub: dict) -> str:
    return sub["label_teknis"] if mode_teknis() else sub["label"]


# ── Langkah 2: live ────────────────────────────────────────────────────────

def render_live_map(job_id: str, events: list[dict], status: dict) -> None:
    """Empat tahap sebagai st.status; tahap aktif terbuka dan menunjukkan
    sub-langkah mana yang sedang berjalan."""
    stages = fetch_stages()
    states = stage_states(job_id, events)
    message = status.get("message") or ""
    message_at = float(status.get("updated_at") or 0)
    for stage in stages:
        key = stage["key"]
        state = states.get(key, {}).get("state", "pending")
        dur = states.get(key, {}).get("duration_ms")
        title = f"{stage['icon']} {stage['title']}"
        if state == "done":
            title += f" — selesai {fmt_duration(dur)}" if dur else " — selesai"
        elif state == "pending":
            title += " — menunggu"
        # Keluar dari blok `with` selalu memaksa state "running" → "complete",
        # sehingga tahap yang masih menunggu tampak sudah selesai. Kembalikan
        # state yang benar sesudahnya; menunggu digambarkan sebagai spinner.
        wanted = _STATUS_STATE.get(state, "running")
        box = st.status(title, state=wanted, expanded=(state == "running"))
        with box:
            _render_substep_checklist(stage, state, substep_states(events, key),
                                      message, message_at)
        if wanted == "running":
            box.update(state="running")


def _render_substep_checklist(stage: dict, stage_state: str, subs: dict[str, dict],
                              message: str, message_at: float = 0.0) -> None:
    subs_def = stage.get("substeps") or []
    for sub in subs_def:
        parent = sub.get("inside")
        if parent:
            # Bersarang: mewarisi status induk; tidak punya event sendiri.
            p_state = subs.get(parent, {}).get("state", "pending")
            icon = _SUB_ICON["done" if p_state == "done" else
                             "running" if p_state == "running" else "pending"]
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} {_sub_title(sub)}",
                        unsafe_allow_html=True)
            continue
        info = subs.get(sub["key"], {})
        state = info.get("state", "pending")
        if state == "pending" and stage_state == "done":
            state = "skipped"
        line = f"{_SUB_ICON[state]} **{_sub_title(sub)}**"
        if state in ("done", "error"):
            nums = _funnel_line(sub, {}, info)
            if nums:
                line += f" · {nums}"
            if info.get("duration_ms"):
                line += f" · {fmt_duration(info['duration_ms'])}"
        elif state == "running" and message:
            # Pesan progres yang lebih tua dari sub-langkah ini milik tahap
            # sebelumnya ("Chunking 10/10" saat LLM baru mulai) — jangan ditempel.
            if message_at >= float(info.get("started_at") or 0):
                line += f" · _{message}_"
            else:
                line += " · _sedang berjalan…_"
        st.markdown(line)
        if state == "error":
            st.caption(f"❌ {info.get('error')}")


def render_activity_log(events: list[dict], status: dict, stages: list[dict],
                        limit: int = 15) -> None:
    """Event terakhir diterjemahkan ke bahasa awam, terbaru di atas."""
    titles = {s["key"]: s["title"] for s in stages}
    sub_labels = {(s["key"], sub["key"]): sub["label"]
                  for s in stages for sub in (s.get("substeps") or [])}
    lines: list[str] = []
    for ev in reversed(events):
        text = _describe_event(ev, titles, sub_labels)
        if text:
            lines.append(f"`{_clock(ev.get('created_at'))}` {text}")
        if len(lines) >= limit:
            break
    with st.expander(f"🧾 Log aktivitas ({len(events)} event)", expanded=False):
        if status.get("message"):
            st.markdown(f"**Sekarang:** {status['message']}")
        for line in lines:
            st.markdown(line)
        if mode_teknis() and events:
            st.dataframe(pd.DataFrame([
                {"type": e.get("type"), "phase": e.get("phase"),
                 "data": str(e.get("data") or "")[:120]} for e in events[-limit:]
            ]), width="stretch", hide_index=True)


def _clock(epoch) -> str:
    return datetime.fromtimestamp(epoch).strftime("%H:%M:%S") if epoch else "—"


def _describe_event(ev: dict, titles: dict, sub_labels: dict) -> str | None:
    kind, phase, d = ev.get("type"), ev.get("phase"), ev.get("data") or {}
    if kind == "job.created":
        return f"🚀 Analisis dibuat untuk {d.get('file_count', '?')} berkas"
    if kind == "phase.started":
        return f"▶️ Mulai tahap **{titles.get(phase, phase)}**"
    if kind == "phase.completed":
        return f"🏁 **{titles.get(phase, phase)}** selesai ({fmt_duration(ev.get('duration_ms'))})"
    if kind == "phase.failed":
        return f"❌ **{titles.get(phase, phase)}** gagal: {d.get('error', '')[:120]}"
    if kind == "phase.cancelled":
        return f"🚫 **{titles.get(phase, phase)}** dibatalkan"
    if kind == "file.started":
        return f"📄 Membaca {d.get('file')} ({d.get('index')}/{d.get('of')})"
    if kind == "file.completed":
        return f"✔ {d.get('file')}: {d.get('chunks')} chunk"
    if kind == "file.failed":
        return f"⚠️ {d.get('file')} gagal dibaca: {d.get('error', '')[:100]}"
    if kind == "substep.started":
        return f"  ▹ {sub_labels.get((phase, d.get('substep')), d.get('substep'))}…"
    if kind == "substep.completed":
        name = sub_labels.get((phase, d.get("substep")), d.get("substep"))
        nums = []
        if d.get("masuk") is not None:
            nums.append(str(d["masuk"]))
        if d.get("keluar") is not None:
            nums.append(f"→ {d['keluar']}")
        if d.get("dibuang"):
            nums.append(f"(dibuang {d['dibuang']})")
        tail = f": {' '.join(nums)}" if nums else ""
        return f"  ✔ {name}{tail}"
    return None


# ── Estimasi durasi dari riwayat ───────────────────────────────────────────

@st.cache_data(ttl=300)
def estimate_stage_durations(api_base: str, max_jobs: int = 5) -> dict[str, int]:
    """Rata-rata durasi tiap tahap dari job penelitian yang sudah selesai.

    ``api_base`` ikut jadi kunci cache agar ganti backend tidak memakai angka
    lama. Kosong bila belum ada riwayat.
    """
    totals: dict[str, list[int]] = {}
    done_jobs = [j for j in research_jobs(limit=40) if j.get("status") == "completed"]
    for job in done_jobs[:max_jobs]:
        payload = fetch_events(job["job_id"])
        if not isinstance(payload, dict):
            continue
        for ev in payload.get("events") or []:
            if ev.get("type") == "phase.completed" and ev.get("duration_ms"):
                totals.setdefault(ev["phase"], []).append(int(ev["duration_ms"]))
    return {k: int(sum(v) / len(v)) for k, v in totals.items() if v}


# ── Langkah 3: isi satu tab tahap ──────────────────────────────────────────

def render_stage_body(job_id: str, stage: dict, events: list[dict]) -> None:
    """Tiga tab: alur & angka (corong + contoh), data lengkap (+ jejak), kode."""
    key = stage["key"]
    info = stage_states(job_id, events).get(key, {})
    state = info.get("state", "pending")
    if state == "pending":
        st.info("Tahap ini belum berjalan.")
        return
    if state == "running":
        st.warning("Tahap ini sedang berjalan — hasil detail muncul setelah selesai.")
    if state == "failed":
        st.error(f"Tahap gagal: {info.get('error', 'tidak diketahui')}")
    if state == "cancelled":
        st.warning("Tahap ini dihentikan oleh pembatalan; datanya tidak lengkap.")

    arts, payload = stage_result_payload(job_id, key)
    tab_alur, tab_data, tab_kode = st.tabs(
        ["🧭 Alur & angka", "🗂️ Data lengkap", "💻 Kode & rumus"])
    with tab_alur:
        if not payload:
            st.info("Belum ada hasil detail untuk tahap ini.")
        else:
            if payload.get("duration_ms") is not None:
                st.caption(f"⏱️ Durasi tahap: **{fmt_duration(payload['duration_ms'])}**")
            st.markdown("**Apa yang dikerjakan, berurutan:**")
            render_stage_flow(job_id, stage, payload, events)
            if payload.get("metrics"):
                st.markdown("**Semua angka tahap ini**")
                render_metrics_grid(payload["metrics"])
            render_stage_extras(arts, payload)
        render_glossary(key)
    with tab_data:
        render_records_tab(job_id, key, trace=render_record_trace)
        render_glossary(key)
    with tab_kode:
        render_source_tab(key, stage.get("substeps"))


# ── Langkah 3: corong per tahap ────────────────────────────────────────────

def render_stage_flow(job_id: str, stage: dict, payload: dict, events: list[dict]) -> None:
    """Sub-langkah berurutan dengan angka masuk → keluar dan contoh datanya."""
    metrics = payload.get("metrics") or {}
    samples = payload.get("substep_samples")
    subs = substep_states(events, stage["key"])
    recorded = samples is not None  # job lama tidak punya kunci ini sama sekali

    for sub in stage.get("substeps") or []:
        nested = bool(sub.get("inside"))
        info = subs.get(sub["key"], {})
        state = info.get("state", "done")
        out_val = _num(metrics, sub["out_metric"])
        if out_val == "tidak dicek":
            state = "skipped"
        icon = _SUB_ICON.get(state, "✅")
        indent = "&nbsp;" * 8 if nested else ""
        nums = "" if nested else _funnel_line(sub, metrics, info if info else None)
        head = f"{indent}{icon} **{_sub_title(sub)}**"
        if nums:
            head += f" &nbsp;·&nbsp; {nums}"
        if info.get("duration_ms") and not nested:
            head += f" &nbsp;·&nbsp; {fmt_duration(info['duration_ms'])}"
        st.markdown(head, unsafe_allow_html=True)
        st.caption(f"{indent}{sub['penjelasan']}", unsafe_allow_html=True)
        if state == "skipped":
            st.caption(f"{indent}⏭️ Dilewati pada analisis ini.", unsafe_allow_html=True)

        if sub.get("sample_key"):
            _render_substep_samples(sub, samples or {}, recorded, metrics)

    consts = stage.get("constants") or {}
    if consts:
        with st.expander("⚙️ Ambang & bobot yang dipakai", expanded=False):
            st.caption("Diimpor dari modul yang menjalankan tahap ini, bukan disalin.")
            st.dataframe(pd.DataFrame([{"parameter": k, "nilai": str(v)}
                                       for k, v in consts.items()]),
                         width="stretch", hide_index=True)


def _render_substep_samples(sub: dict, samples: dict, recorded: bool, metrics: dict) -> None:
    key = sub["sample_key"]
    drop = _num(metrics, sub["drop_metric"])
    title = {
        "verifikasi_gugur": "Contoh kalimat yang DIBUANG karena tak ditemukan di jurnal",
        "dedup_dibuang": "Contoh duplikat yang dibuang",
        "contoh_addressed": "Contoh gap yang sudah dijawab literatur (dan siapa yang menjawab)",
        "dibuang_bukan_open": "Contoh gap yang disisihkan karena sudah ada yang mengerjakan",
        "tema_terbesar": "Tema terbesar dan anggotanya",
        "pdf_gagal": "PDF yang gagal dibaca",
        "chunk_kecil": "Contoh chunk terkecil (biasanya sisa judul palsu/tabel)",
    }.get(key, f"Contoh {key.replace('_', ' ')}")
    rows = samples.get(key)
    with st.expander(f"🔎 {title}", expanded=False):
        if not recorded:
            st.caption("Contoh tidak direkam pada analisis ini — fitur ini ada sejak "
                       "pembaruan; jalankan analisis baru untuk melihatnya.")
            return
        if not rows:
            what = "yang dibuang" if sub["drop_metric"] else "yang tercatat"
            st.caption(f"Tidak ada {what}" + (f" ({drop})" if drop is not None else "") + ".")
            return
        for row in rows:
            _render_sample_row(row)


def _render_sample_row(row: dict) -> None:
    text_field = next((f for f in _SAMPLE_TEXT_FIELDS if row.get(f)), None)
    if text_field:
        st.markdown(f"> {row[text_field]}")
    meta = []
    for k, v in row.items():
        if k == text_field or v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            if k == "anggota":
                meta.append(f"{label(k)}: " + "; ".join(
                    f"{m.get('source')} — {m.get('title')}" for m in v))
            elif k in ("literatur_2024plus", "paper_penjawab"):
                items = [f"{p.get('title')} ({p.get('year')}, cocok {p.get('match_score')})"
                         if isinstance(p, dict) else str(p) for p in v]
                meta.append(f"{label(k) if k in ('literatur_2024plus',) else 'paper penjawab'}: "
                            + "; ".join(items))
            else:
                meta.append(f"{label(k)}: {', '.join(map(str, v))}")
        elif k in ENUM_LABELS:
            meta.append(f"{label(k)}: {enum_label(k, v)}")
        else:
            meta.append(f"{label(k)}: {v}")
    if meta:
        st.caption(" · ".join(meta))
    st.divider()


# ── Jejak per record (tab Data lengkap) ────────────────────────────────────

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-!<>~|])")


def _md_escape(text: str) -> str:
    return _MD_SPECIAL.sub(r"\\\1", text)


def _highlight(haystack: str, needle: str) -> tuple[str, bool]:
    """Sorot ``needle`` di ``haystack`` bila muncul persis (abaikan kapital)."""
    if not needle:
        return _md_escape(haystack), False
    idx = haystack.lower().find(needle.lower())
    if idx < 0:
        return _md_escape(haystack), False
    before, hit, after = haystack[:idx], haystack[idx:idx + len(needle)], haystack[idx + len(needle):]
    return f"{_md_escape(before)}:orange-background[{_md_escape(hit)}]{_md_escape(after)}", True


def _find_chunk(job_id: str, chunk_id: str) -> dict | None:
    data = fetch_records(job_id, "chunking", q=chunk_id, limit=5)
    for rec in data.get("records") or []:
        if rec.get("chunk_id") == chunk_id:
            return rec
    return None


def render_record_trace(rec: dict, phase: str, job_id: str) -> None:
    """Bagian 'dari mana angka/kalimat ini berasal' di bawah satu record."""
    if phase in ("gap_mining", "novelty", "recommendation"):
        _render_evidence(rec, job_id, phase)
    if phase == "novelty":
        _render_novelty_verdict(rec)
    if phase == "recommendation":
        _render_score_breakdown(rec)


def _render_evidence(rec: dict, job_id: str, phase: str) -> None:
    statement = rec.get("gap_statement") or rec.get("description") or ""
    chunk_ids = rec.get("evidence_chunk_ids") or []
    with st.expander("🔗 Lihat kalimat ini di chunk sumbernya", expanded=False):
        if rec.get("candidate_reason"):
            st.caption(f"Kenapa bagian ini dibaca LLM: `{rec['candidate_reason']}`")
        chunk = _find_chunk(job_id, chunk_ids[0]) if chunk_ids else None
        if chunk is None and statement:
            # Proposal tidak menyimpan chunk_id; cari lewat awal kalimatnya.
            data = fetch_records(job_id, "chunking", q=statement[:60],
                                 filters={"source": rec.get("source")}, limit=1)
            chunk = (data.get("records") or [None])[0]
        if chunk is None:
            st.caption("Chunk sumber tidak ditemukan di berkas chunking job ini.")
            return
        body, exact = _highlight(chunk.get("text") or "", statement)
        st.caption(f"`{chunk.get('chunk_id')}` · {label('section_normalized')}: "
                   f"{chunk.get('section_normalized')} · hlm {chunk.get('page_start')}")
        st.markdown(body)
        if not exact:
            score = rec.get("grounding_score")
            st.caption("Kalimat tidak muncul persis (spasi/tanda baca berbeda) — dicocokkan "
                       f"secara fuzzy, skor {score}." if score is not None else
                       "Kalimat tidak muncul persis; dicocokkan secara fuzzy.")


def _render_novelty_verdict(rec: dict) -> None:
    papers = rec.get("related_recent_papers") or []
    status = rec.get("novelty_status")
    c = stage_constants("novelty")
    strong_thr = c.get("strong_match_threshold", 0.5)
    with st.expander("🔭 Bagaimana status kebaruan ini ditentukan", expanded=False):
        st.markdown(f"**Kata kunci dicari:** `{rec.get('novelty_query') or '—'}`")
        strong = [p for p in papers if (p.get("match_score") or 0) >= strong_thr]
        if papers:
            st.dataframe(pd.DataFrame([{
                "judul": p.get("title"), "tahun": p.get("year"),
                "DOI": p.get("doi") or "", "skor cocok": p.get("match_score"),
                "kuat?": "✔" if (p.get("match_score") or 0) >= strong_thr else "",
            } for p in papers]), width="stretch", hide_index=True)
        else:
            st.caption("OpenAlex tidak mengembalikan paper — bisa benar-benar baru, bisa "
                       "juga permintaan sedang dibatasi (throttle).")
        verdict = {
            "open": f"tidak ada paper dengan kecocokan ≥{strong_thr} → "
                    f"**{enum_label('novelty_status', status)}**",
            "partially_addressed": f"{len(strong)} paper cocok kuat (1–2) → "
                                   f"**{enum_label('novelty_status', status)}**",
            "addressed": f"{len(strong)} paper cocok kuat (≥3) → "
                         f"**{enum_label('novelty_status', status)}**",
        }.get(status, f"status: {status}")
        st.markdown(f"**Putusan:** {verdict}")


def _render_score_breakdown(rec: dict) -> None:
    gc, nc, act = rec.get("gap_confidence"), rec.get("novelty_credit"), rec.get("actionability")
    c = stage_constants("recommendation")
    w_gap, w_nov, w_act = c.get("w_gap", 0.5), c.get("w_novelty", 0.3), c.get("w_actionability", 0.2)
    with st.expander("🧮 Dari mana skor prioritas ini", expanded=False):
        if gc is None or nc is None:
            st.caption("Rincian suku rumus tidak tersimpan pada analisis ini (job lama). "
                       "Jalankan analisis baru untuk melihat perhitungannya.")
            return
        act = act or 0
        rows = [
            {"suku": label("gap_confidence"), "bobot": w_gap, "nilai": gc,
             "kontribusi": round(w_gap * gc, 4), "arti": help_of("gap_confidence")},
            {"suku": label("novelty_credit"), "bobot": w_nov, "nilai": nc,
             "kontribusi": round(w_nov * nc, 4),
             "arti": f"kebaruan {rec.get('novelty')} → {enum_label('band', rec.get('band'))}"},
            {"suku": label("actionability"), "bobot": w_act, "nilai": act,
             "kontribusi": round(w_act * act, 4), "arti": help_of("actionability")},
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        total = round(w_gap * gc + w_nov * nc + w_act * act, 4)
        st.markdown(f"**Jumlah = {total}** (tersimpan: {rec.get('priority_score')})")
        if rec.get("nearest_paper"):
            st.caption(f"Jurnal paling mirip di korpus: {rec['nearest_paper']} "
                       f"(kemiripan {rec.get('nearest_similarity')})")
        for note in rec.get("score_notes") or []:
            st.caption(f"• {note}")
