"""Wizard Lite — langkah 1: unggah PDF jurnal, lihat hasil chunk.

UI sengaja kecil dan bertahap. Langkah ini hanya memakai TAHAP 1 pipeline
(``POST /api/research/chunk-preview``): tidak ada job, LLM, atau vector store.

Jalankan:  bash tools/wizard_lite/run.sh   (backend harus hidup di :8001)
"""

from __future__ import annotations

import io
import json

import pandas as pd
import requests
import streamlit as st

DEFAULT_API = "http://127.0.0.1:8001"
TIMEOUT_SECONDS = 600  # OCR pada PDF hasil pindaian bisa lama

# Urutan tampil mengikuti struktur artikel, bukan abjad.
SECTION_ORDER = ["abstract", "introduction", "related_work", "methods", "results",
                 "discussion", "conclusion", "references", "other"]
SECTION_LABELS = {
    "abstract": "Abstrak",
    "introduction": "Pendahuluan",
    "related_work": "Kajian Terkait",
    "methods": "Metode",
    "results": "Hasil",
    "discussion": "Pembahasan",
    "conclusion": "Kesimpulan",
    "references": "Referensi",
    "other": "Lainnya",
}
METHOD_LABELS = {
    "pymupdf_layout": "PyMuPDF (layout/font)",
    "pymupdf": "PyMuPDF",
    "pypdf": "pypdf",
    "ocrd_text_layer": "ocrd — lapisan teks",
    "ocrd_ocr": "ocrd — OCR GPU",
}
QUALITY_BADGES = {"good": "🟢 baik", "fair": "🟡 cukup", "poor": "🔴 buruk"}

st.set_page_config(page_title="Wizard Lite — Chunk", page_icon="📄", layout="wide")
st.session_state.setdefault("api_base", DEFAULT_API)
st.session_state.setdefault("preview", None)


# ── Backend ────────────────────────────────────────────────────────────────

def backend_alive(api_base: str) -> bool:
    try:
        return requests.get(f"{api_base}/health", timeout=3).status_code == 200
    except requests.RequestException:
        return False


def request_chunks(api_base: str, uploads) -> dict:
    files = [("files", (u.name, u.getvalue(), "application/pdf")) for u in uploads]
    resp = requests.post(f"{api_base}/api/research/chunk-preview", files=files,
                         timeout=TIMEOUT_SECONDS)
    if resp.status_code != 200:
        detail = resp.json().get("detail", resp.text) if resp.content else resp.reason
        raise RuntimeError(f"HTTP {resp.status_code}: {detail}")
    return resp.json()


# ── Tampilan ───────────────────────────────────────────────────────────────

def section_label(key: str) -> str:
    return SECTION_LABELS.get(key, key or "—")


def render_summary(item: dict) -> None:
    meta = item.get("meta") or {}
    title = meta.get("paper_title") or item["source"]
    st.subheader(title)
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
    st.caption(
        f"Metode ekstraksi: **{METHOD_LABELS.get(item.get('extraction_method'), item.get('extraction_method'))}**"
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

    st.dataframe(
        [
            {
                "#": c["chunk_index"],
                "Bagian": section_label(c["section_normalized"]),
                "Hal.": c.get("page_start"),
                "Token": c["token_count"],
                "Teks": c["text"],
            }
            for c in shown
        ],
        width="stretch",
        hide_index=True,
        column_config={"Teks": st.column_config.TextColumn(width="large")},
    )

    with st.expander("Baca chunk satu per satu", expanded=False):
        for c in shown:
            head = (f"#{c['chunk_index']} · {section_label(c['section_normalized'])}"
                    f" · hal. {c.get('page_start') or '?'} · {c['token_count']} token")
            if c.get("section_raw"):
                head += f" · judul asli: {c['section_raw']}"
            st.markdown(f"**{head}**")
            st.text(c["text"])
            st.divider()

    jsonl = "\n".join(json.dumps(c, ensure_ascii=False) for c in chunks)
    st.download_button("⬇️ Unduh semua chunk (.jsonl)", data=jsonl.encode("utf-8"),
                       file_name=f"{item['source']}.chunks.jsonl", mime="application/x-ndjson",
                       key=f"dl-{key}")


# ── Halaman ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📄 Wizard Lite")
    st.caption("Langkah 1 — unggah PDF, lihat chunk")
    st.text_input("Alamat backend", key="api_base")
    alive = backend_alive(st.session_state["api_base"])
    st.markdown("Backend: " + ("🟢 hidup" if alive else "🔴 tidak terjangkau"))
    if not alive:
        st.code("./run_backend.sh", language="bash")

st.title("Unggah jurnal → lihat hasil chunk")
st.write(
    "PDF dibaca, dibersihkan, dideteksi bagiannya (Pendahuluan, Metode, …), lalu "
    "dipotong menjadi chunk berukuran token yang seragam. Inilah teks yang akan "
    "dipakai tahap analisis berikutnya."
)

uploads = st.file_uploader("PDF jurnal (boleh lebih dari satu)", type=["pdf"],
                           accept_multiple_files=True)
run = st.button("🔪 Proses chunk", type="primary", disabled=not uploads or not alive)

if run:
    with st.spinner(f"Memproses {len(uploads)} PDF…"):
        try:
            st.session_state["preview"] = request_chunks(st.session_state["api_base"], uploads)
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
