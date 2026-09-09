"""🧭 Wizard — alur bertahap di atas pipeline penelitian, fokus pada jurnal yang diunggah.

Langkah 1: unggah PDF → lihat chunk (``POST /api/research/chunk-preview``; tanpa job/LLM).
Langkah 2: cari research gap dengan LLM (job pipeline ``until=gap_mining``).
Langkah 3: indikator synthesis gap neuro-symbolic antar jurnal yang diunggah
           (job pipeline 8 tahap ``POST /api/upload-and-analyze``).
Langkah 4: rekomendasi topik & judul siap-pakai — job langkah 2 dilanjutkan ke tahap
           ``recommendation`` (``POST /api/research/{job}/continue``; gap mining tidak diulang).

Pencarian ke literatur luar (OpenAlex) bukan bagian proposal; bila tahap kebaruan
aktif di server, langkah 4 memberi tahu dan membolehkan membatasi jumlah gap yang dicek.

Halaman ini dulunya aplikasi terpisah ``tools/wizard_lite`` (:8502); sejak 9 Sep 2026
menjadi halaman pembuka aplikasi tunggal ``tools/process_monitor`` (:8501).
"""

from __future__ import annotations

import io
import json
import time

import pandas as pd
import streamlit as st

import step2_gaps
import step3_neuro
import step4_titles
from common import api_base
from wl_common import (
    METHOD_LABELS,
    OCR_CHOICES,
    QUALITY_BADGES,
    SECTION_ORDER,
    TERMINAL_STATUSES,
    backend_alive,
    render_reading_text,
    render_view_switch,
    request_chunks,
    section_label,
)

POLL_SECONDS = 2

# Sidebar utama menyimpan "…/api"; klien wizard membangun path /api/… sendiri.
API = api_base().removesuffix("/api")
st.session_state.setdefault("preview", None)
st.session_state.setdefault("ocr_mode", "auto")


class _StoredUpload:
    """Salinan berkas unggahan yang bertahan saat pindah halaman (widget uploader
    kosong lagi setiap kembali ke halaman ini)."""

    def __init__(self, name: str, data: bytes):
        self.name, self._data = name, data

    def getvalue(self) -> bytes:
        return self._data


def _remember_uploads(files) -> list:
    """Pakai berkas dari widget bila ada (dan simpan); kalau tidak, berkas tersimpan."""
    if files:
        st.session_state["wizard_uploads"] = [_StoredUpload(f.name, f.getvalue()) for f in files]
        return list(files)
    return list(st.session_state.get("wizard_uploads") or [])


# ── Langkah 1: tampilan ────────────────────────────────────────────────────

def render_summary(item: dict) -> None:
    meta = item.get("meta") or {}
    st.subheader(meta.get("paper_title") or item["source"])
    bits = []
    if meta.get("year"):
        bits.append(str(meta["year"]))
    if meta.get("authors"):
        bits.append(", ".join(meta["authors"][:3]) + (" dkk." if len(meta["authors"]) > 3 else ""))
    if meta.get("doi"):
        bits.append(f"DOI {meta['doi']}")
    if meta.get("language"):
        bits.append(f"bahasa: {meta['language']}")
    st.caption(" · ".join(bits) if bits else item["source"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Halaman", item.get("pages", 0))
    c2.metric("Chunk", item["num_chunks"])
    c3.metric("Token total", item["token_total"])
    avg = round(item["token_total"] / item["num_chunks"]) if item["num_chunks"] else 0
    c4.metric("Token / chunk", avg)
    c5.metric("Kualitas ekstraksi", QUALITY_BADGES.get(meta.get("extraction_quality"), "—"))
    method = item.get("extraction_method")
    st.caption(
        f"Metode ekstraksi: **{METHOD_LABELS.get(method, method)}**"
        + (" · struktur IMRaD dari GROBID" if item.get("grobid_used") else "")
        + f" · metadata: {meta.get('metadata_source', '—')}"
    )

    sections = item.get("sections") or {}
    if sections:
        order = [s for s in SECTION_ORDER if s in sections] + \
                [s for s in sections if s not in SECTION_ORDER]
        chart = pd.DataFrame(
            {"Bagian": [section_label(s) for s in order], "Chunk": [sections[s] for s in order]}
        ).set_index("Bagian")
        st.caption("Sebaran chunk per bagian")
        st.bar_chart(chart, height=180)


def chunk_heading(c: dict) -> str:
    head = (f"#{c['chunk_index']} · {section_label(c['section_normalized'])}"
            f" · hal. {c.get('page_start') or '?'} · {c['token_count']} token")
    if c.get("section_raw"):
        head += f" · judul asli: {c['section_raw']}"
    return head


def render_chunk_card(c: dict) -> None:
    with st.container(border=True):
        st.markdown(f"**{chunk_heading(c)}**")
        render_reading_text(c["text"])


def render_chunks(item: dict, key: str) -> None:
    chunks = item["chunks"]
    present = [s for s in SECTION_ORDER if any(c["section_normalized"] == s for c in chunks)]
    present += sorted({c["section_normalized"] for c in chunks} - set(present))

    f1, f2, f3 = st.columns([2, 2, 1])
    chosen = f1.multiselect("Bagian", present, default=present, key=f"sec-{key}",
                            format_func=section_label)
    needle = f2.text_input("Cari teks", key=f"q-{key}", placeholder="kata kunci…").strip().lower()
    show_ref = f3.toggle("Ikutkan chunk berlabel referensi", value=False, key=f"ref-{key}",
                         help="Chunk daftar pustaka atau yang padat sitasi (is_reference) "
                              "disembunyikan karena tidak dipakai analisis.")

    shown = [
        c for c in chunks
        if c["section_normalized"] in chosen
        and (show_ref or not c.get("is_reference"))
        and (not needle or needle in c["text"].lower())
    ]
    st.caption(f"{len(shown)} dari {len(chunks)} chunk")

    def row(c: dict) -> dict:
        return {"#": c["chunk_index"], "Bagian": section_label(c["section_normalized"]),
                "Hal.": c.get("page_start"), "Token": c["token_count"], "Teks": c["text"]}

    render_view_switch(shown, key, row, lambda i: render_chunk_card(shown[i]),
                       column_config={"Teks": st.column_config.TextColumn(width="large")})

    jsonl = "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks)
    st.download_button("⬇️ Unduh semua chunk (.jsonl)", data=jsonl.encode("utf-8"),
                       file_name=f"{item['source']}.chunks.jsonl", mime="application/x-ndjson",
                       key=f"dl-{key}")


# ── Halaman ────────────────────────────────────────────────────────────────

with st.sidebar:
    alive = backend_alive(API)
    st.markdown("Backend: " + ("🟢 hidup" if alive else "🔴 tidak terjangkau"))
    if not alive:
        st.code("./run_backend.sh", language="bash")
    st.radio("Pembaca PDF", list(OCR_CHOICES), key="ocr_mode",
             format_func=OCR_CHOICES.get,
             help="Metode yang benar-benar terpakai tampil di ringkasan tiap jurnal.")

st.title("🧭 Wizard — dari PDF ke judul penelitian")
st.caption("1 chunk → 2 research gap → 3 indikator synthesis gap → 4 rekomendasi & judul · "
           "seluruh bukti berasal dari jurnal yang Anda unggah. Detail teknis tiap tahap ada di "
           "menu **Detail teknis** (kiri).")

st.header("Langkah 1 — unggah jurnal, lihat hasil chunk")
st.write(
    "PDF dibaca, dibersihkan, dideteksi bagiannya (Pendahuluan, Metode, …), lalu "
    "dipotong menjadi chunk berukuran token yang seragam. Inilah teks yang akan "
    "dipakai tahap analisis berikutnya."
)

widget_uploads = st.file_uploader("PDF jurnal (boleh lebih dari satu)", type=["pdf"],
                                  accept_multiple_files=True)
uploads = _remember_uploads(widget_uploads)
if uploads and not widget_uploads:
    st.caption(f"Memakai {len(uploads)} berkas yang diunggah sebelumnya: "
               + ", ".join(u.name for u in uploads))
run = st.button("🔪 Proses chunk", type="primary", disabled=not uploads or not alive)

if run:
    with st.spinner(f"Memproses {len(uploads)} PDF…"):
        try:
            st.session_state["preview"] = request_chunks(API, uploads, st.session_state["ocr_mode"])
            step2_gaps.reset()  # chunk baru → hasil gap lama tidak lagi relevan
            step3_neuro.reset()
            step4_titles.reset()
        except Exception as exc:
            st.session_state["preview"] = None
            st.error(f"Gagal memproses: {exc}")

preview = st.session_state.get("preview")
if not preview:
    st.info("Pilih satu atau beberapa PDF, lalu klik **Proses chunk**.")
    st.stop()

params = preview.get("params") or {}
st.caption(
    f"Parameter chunking: target {params.get('target_tokens')} token, "
    f"maks {params.get('max_tokens')} token, tumpang-tindih {params.get('overlap_ratio')}"
    f" · pembaca PDF: {'paksa ocrd' if params.get('ocr_mode') == 'force' else 'otomatis'}"
)

items = preview.get("files") or []
ok_items = [i for i in items if not i.get("error")]
for item in items:
    if item.get("error"):
        st.error(f"**{item['source']}** — {item['error']}")

if len(ok_items) > 1:
    st.caption("Ringkasan semua berkas")
    st.dataframe(
        [
            {
                "Berkas": i["source"],
                "Judul": (i.get("meta") or {}).get("paper_title") or "—",
                "Tahun": (i.get("meta") or {}).get("year"),
                "Halaman": i.get("pages"),
                "Chunk": i["num_chunks"],
                "Token": i["token_total"],
                "Kualitas": QUALITY_BADGES.get((i.get("meta") or {}).get("extraction_quality"), "—"),
            }
            for i in ok_items
        ],
        width="stretch",
        hide_index=True,
    )

tabs = st.tabs([i["source"] for i in ok_items]) if len(ok_items) > 1 else [st.container()]
for tab, item in zip(tabs, ok_items):
    with tab:
        render_summary(item)
        render_chunks(item, key=item["source"])

if len(ok_items) > 1:
    buf = io.StringIO()
    for i in ok_items:
        for c in i["chunks"]:
            buf.write(json.dumps(c, ensure_ascii=False) + "\n")
    st.download_button("⬇️ Unduh chunk semua berkas (.jsonl)", data=buf.getvalue().encode("utf-8"),
                       file_name="chunks.jsonl", mime="application/x-ndjson")

# ── Langkah 2, 3 & 4 ─────────────────────────────────────────────────────────────────

st.divider()
chunks_by_id = {c["chunk_id"]: c for i in ok_items for c in i["chunks"]}
job_id, job_state, gaps = step2_gaps.render(
    api_base=API,
    uploads=uploads,
    ocr_mode=st.session_state["ocr_mode"],
    backend_ok=alive,
    chunks_by_id=chunks_by_id,
)

st.divider()
ns_job_id, ns_state = step3_neuro.render(
    api_base=API,
    uploads=uploads,
    backend_ok=alive,
    chunks_by_id=chunks_by_id,
)

st.divider()
step4_titles.render(api_base=API, gap_job_id=job_id, gap_status=job_state, backend_ok=alive)

# Satu polling untuk semua langkah: rerun selama ada job yang belum berakhir
# (langkah 4 melanjutkan job langkah 2, jadi statusnya sudah tercakup job_state).
if any(s and s.get("status") not in TERMINAL_STATUSES for s in (job_state, ns_state)):
    time.sleep(POLL_SECONDS)
    st.rerun()
