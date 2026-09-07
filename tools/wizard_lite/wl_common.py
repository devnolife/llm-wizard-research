"""Konstanta, klien backend, dan komponen tampilan yang dipakai semua langkah Wizard Lite."""

from __future__ import annotations

import html

import requests
import streamlit as st

DEFAULT_API = "http://127.0.0.1:8001"
TIMEOUT_SECONDS = 600  # OCR pada PDF hasil pindaian bisa lama

OCR_CHOICES = {
    "auto": "Otomatis — PyMuPDF lokal; ocrd hanya bila teks buruk (hasil pindaian)",
    "force": "Paksa ocrd — kirim PDF ke layanan OCR (lapisan teks / OCR GPU)",
}
VIEW_TABLE, VIEW_STACK, VIEW_FOCUS = "📋 Tabel + baca di bawah", "📖 Baca berurutan", "🎯 Fokus satu"
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
JOB_STATUS_BADGES = {
    "queued": ("🕓", "menunggu giliran worker"),
    "running": ("🔄", "berjalan"),
    "completed": ("✅", "selesai"),
    "failed": ("❌", "gagal"),
    "cancelled": ("🚫", "dibatalkan"),
    "interrupted": ("⚠️", "terputus"),
}
TERMINAL_STATUSES = {"completed", "failed", "cancelled", "interrupted"}


# ── Backend ────────────────────────────────────────────────────────────────

def _raise_for_status(resp: requests.Response) -> None:
    if resp.status_code < 400:
        return
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        detail = resp.text or resp.reason
    raise RuntimeError(f"HTTP {resp.status_code}: {detail}")


def backend_alive(api_base: str) -> bool:
    try:
        return requests.get(f"{api_base}/health", timeout=3).status_code == 200
    except requests.RequestException:
        return False


def _upload_files(uploads) -> list:
    return [("files", (u.name, u.getvalue(), "application/pdf")) for u in uploads]


def request_chunks(api_base: str, uploads, ocr_mode: str) -> dict:
    resp = requests.post(f"{api_base}/api/research/chunk-preview", files=_upload_files(uploads),
                         data={"ocr_mode": ocr_mode}, timeout=TIMEOUT_SECONDS)
    _raise_for_status(resp)
    return resp.json()


def start_research_job(api_base: str, uploads, ocr_mode: str, until: str) -> dict:
    resp = requests.post(f"{api_base}/api/research/start", files=_upload_files(uploads),
                         data={"ocr_mode": ocr_mode, "until": until}, timeout=TIMEOUT_SECONDS)
    _raise_for_status(resp)
    return resp.json()


def continue_research_job(api_base: str, job_id: str, until: str, novelty_limit: int = 0) -> dict:
    """Lanjutkan job yang selesai ke tahap berikutnya memakai keluaran yang sudah ada."""
    resp = requests.post(f"{api_base}/api/research/{job_id}/continue",
                         data={"until": until, "novelty_limit": str(novelty_limit)}, timeout=30)
    _raise_for_status(resp)
    return resp.json()


def job_status(api_base: str, job_id: str) -> dict:
    resp = requests.get(f"{api_base}/api/analysis-status/{job_id}", timeout=15)
    _raise_for_status(resp)
    return resp.json()


def job_events(api_base: str, job_id: str) -> list:
    resp = requests.get(f"{api_base}/api/analysis-status/{job_id}/events", timeout=15)
    _raise_for_status(resp)
    return resp.json().get("events", [])


def cancel_job(api_base: str, job_id: str) -> dict:
    resp = requests.post(f"{api_base}/api/analysis-status/{job_id}/cancel", timeout=15)
    _raise_for_status(resp)
    return resp.json()


def stage_records(api_base: str, job_id: str, phase: str) -> list:
    """Seluruh record satu koleksi (dipaginasi otomatis)."""
    records, offset, page = [], 0, 500
    while True:
        resp = requests.get(f"{api_base}/api/research/{job_id}/records/{phase}",
                            params={"offset": offset, "limit": page}, timeout=60)
        _raise_for_status(resp)
        body = resp.json()
        records.extend(body.get("records", []))
        offset += page
        if offset >= body.get("filtered", 0) or not body.get("records"):
            return records


# ── Komponen tampilan ──────────────────────────────────────────────────────

def section_label(key: str) -> str:
    return SECTION_LABELS.get(key, key or "—")


def render_reading_text(text: str, highlight: str | None = None) -> None:
    """Teks dalam tipografi baca (bukan monospace), aman dari markdown/HTML.

    ``highlight``: potongan yang ditandai (mis. kalimat gap verbatim di chunk sumbernya).
    """
    body = html.escape(text or "")
    if highlight and highlight.strip():
        needle = html.escape(highlight.strip())
        body = body.replace(needle, f"<mark>{needle}</mark>")
    st.markdown(
        "<div style='white-space:pre-wrap;font-size:1.05rem;line-height:1.7;'>"
        f"{body}</div>",
        unsafe_allow_html=True,
    )


def render_table_with_reader(rows: list, render_detail, key: str, height: int = 420,
                             column_config: dict | None = None) -> None:
    """Tabel ringkas di atas; klik satu baris → ``render_detail(index)`` di bawah."""
    import pandas as pd

    event = st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        height=min(height, 38 + 35 * max(1, len(rows))),
        on_select="rerun",
        selection_mode="single-row",
        key=f"table-{key}",
        column_config=column_config,
    )
    selected = (event.selection.rows if event and event.selection else []) or []
    if not selected:
        st.info("Klik satu baris di tabel untuk membaca isinya secara utuh di sini.")
        return
    render_detail(selected[0])


def render_focus(n: int, render_detail, key: str) -> None:
    """Satu item per layar dengan tombol maju/mundur; ``render_detail(index)``."""
    slider_key = f"slider-{key}"
    current = min(int(st.session_state.get(slider_key, 1)), n)

    b1, b2, b3 = st.columns([1, 3, 1])
    if b1.button("⬅️ Sebelumnya", key=f"prev-{key}", width="stretch"):
        current -= 1
    if b3.button("Berikutnya ➡️", key=f"next-{key}", width="stretch"):
        current += 1
    current = max(1, min(current, n))
    # widget state must be written before the slider is instantiated in this run
    st.session_state[slider_key] = current
    if n > 1:
        current = b2.slider("Ke-", 1, n, key=slider_key, label_visibility="collapsed")
    else:
        b2.caption("Hanya satu yang lolos filter")

    st.caption(f"{current} dari {n} yang lolos filter")
    render_detail(current - 1)


def render_view_switch(shown: list, key: str, rows_fn, render_detail, column_config=None) -> None:
    """Radio Tabel / Berurutan / Fokus untuk daftar item apa pun."""
    v1, v2 = st.columns([3, 1])
    view = v1.radio("Tampilan", [VIEW_TABLE, VIEW_STACK, VIEW_FOCUS], horizontal=True,
                    key=f"view-{key}", label_visibility="collapsed")
    v2.caption(f"{len(shown)} item")
    if not shown:
        st.warning("Tidak ada yang cocok dengan filter.")
    elif view == VIEW_TABLE:
        render_table_with_reader([rows_fn(x) for x in shown], render_detail, key,
                                 column_config=column_config)
    elif view == VIEW_STACK:
        for i in range(len(shown)):
            render_detail(i)
    else:
        render_focus(len(shown), render_detail, key)
