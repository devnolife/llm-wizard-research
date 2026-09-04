"""🔬 Analisis Penelitian — satu halaman berpanduan dari unggah sampai hasil.

Langkah ditentukan dari status job, bukan dari klik pengguna, supaya tidak ada
layar yang muncul sebelum datanya siap. Saat berjalan, bagian live diperbarui
lewat ``st.fragment(run_every=...)`` — bukan ``time.sleep + st.rerun`` yang
memblokir seluruh halaman.
"""

import streamlit as st

from common import (
    JOB_STATUS_BADGES,
    api_base,
    cancel_job,
    fetch_status,
    fmt_datetime,
    fmt_duration,
)
from research_common import (
    fetch_stages,
    job_events,
    render_timeline,
    research_jobs,
    set_active_job,
    stage_result_payload,
    start_research,
)
from research_charts import render_overview_charts
from research_explorer import render_theme_browser
from research_flow import (
    estimate_stage_durations,
    render_activity_log,
    render_live_map,
    render_stage_body,
)
from research_journals import render_journal_crosstab
from research_vocab import mode_teknis

LANGKAH = ["1 · Unggah jurnal", "2 · Pipeline berjalan", "3 · Baca hasil"]
REFRESH_EVERY = "3s"

_FLOW_DIAGRAM = """
digraph G {
  rankdir=LR;
  node [shape=box, style="rounded,filled", fillcolor="#f4f6fa", fontname="Helvetica", fontsize=11];
  edge [fontname="Helvetica", fontsize=9, color="#7a869a"];
  pdf    [label="PDF jurnal"];
  chunk  [label="potongan teks\\n(chunk)"];
  kand   [label="kandidat\\n(kesimpulan, diskusi, pola kata)"];
  mentah [label="gap mentah\\n(dari LLM)"];
  verif  [label="gap terverifikasi\\n(ada di teks asli)"];
  unik   [label="gap unik"];
  status [label="open / partially /\\naddressed", fillcolor="#fff4e0"];
  rank   [label="proposal berperingkat\\n(skor prioritas)"];
  tema   [label="tema lintas-jurnal", fillcolor="#e8f5e9"];
  pdf -> chunk     [label="1. ekstraksi"];
  chunk -> kand    [label="2a. pilih"];
  kand -> mentah   [label="2b. LLM"];
  mentah -> verif  [label="2c. cek verbatim"];
  verif -> unik    [label="2d. dedup"];
  unik -> status   [label="3. OpenAlex 2024+"];
  status -> rank   [label="4a. hanya open"];
  rank -> tema     [label="4b. kelompokkan"];
}
"""


def _label(job_id: str, jobs: list[dict]) -> str:
    job = next((j for j in jobs if j["job_id"] == job_id), None)
    if not job:
        return f"{job_id[:8]}…"
    icon, label, _ = JOB_STATUS_BADGES.get(job.get("status", ""), ("❔", "?", "gray"))
    return (f"{icon} {job_id[:8]}… · {fmt_datetime(job.get('created_at'))} · "
            f"{len(job.get('files') or [])} berkas · {label}")


st.title("🔬 Analisis Penelitian")

if err := st.session_state.pop("last_error", None):
    st.error(err)

jobs = research_jobs(limit=30)
active = st.session_state.get("research_job_id") or st.query_params.get("job", "")
status = fetch_status(active) if active else {}
status = status if isinstance(status, dict) else {}
state = status.get("status", "")

if not active or state not in ("queued", "running", "completed", "failed", "cancelled"):
    langkah = 1
elif state in ("queued", "running"):
    langkah = 2
else:
    langkah = 3

# ── Penunjuk langkah ──
for col, (i, label) in zip(st.columns(3), enumerate(LANGKAH, 1)):
    if i < langkah:
        col.success(f"✅ {label}")
    elif i == langkah:
        col.info(f"➡️ **{label}**")
    else:
        col.caption(f"⚪ {label}")

st.divider()
stages = fetch_stages()


# ── LANGKAH 1 ──────────────────────────────────────────────────────────────
if langkah == 1:
    st.subheader("Langkah 1 — Unggah jurnal PDF")
    st.markdown(
        "Pilih beberapa PDF jurnal sekaligus, lalu tekan **Jalankan**. "
        "Sistem mengerjakan empat tahap ini otomatis tanpa perlu kamu klik lagi:")

    durations = estimate_stage_durations(api_base())
    for i, stage in enumerate(stages, 1):
        est = (f" · biasanya {fmt_duration(durations[stage['key']])}"
               if stage["key"] in durations else "")
        st.markdown(f"&nbsp;&nbsp;**{i}. {stage['icon']} {stage['title']}** — "
                    f"{stage['description']}{est}", unsafe_allow_html=True)

    with st.expander("🧭 Bagaimana sistem bekerja — peta alur & yang terjadi di tiap tahap",
                     expanded=False):
        st.graphviz_chart(_FLOW_DIAGRAM, width="stretch")
        for stage in stages:
            st.markdown(f"**{stage['icon']} {stage['title']}**")
            for sub in stage.get("substeps") or []:
                indent = "&nbsp;" * (8 if sub.get("inside") else 2)
                title = sub["label_teknis"] if mode_teknis() else sub["label"]
                st.markdown(f"{indent}• **{title}** — {sub['penjelasan']}",
                            unsafe_allow_html=True)

    if durations:
        total = sum(durations.values())
        st.info(f"Perkiraan waktu dari analisis sebelumnya: sekitar "
                f"**{fmt_duration(total)}**. Penambangan gap paling lama karena memanggil "
                "LLM per kandidat; verifikasi kebaruan dibatasi ~1 permintaan/detik oleh "
                "OpenAlex.")
    else:
        st.info("Perkiraan waktu: sekitar **4–5 menit untuk 14 jurnal**. "
                "Tahap penambangan gap memakan ~90% waktu karena memanggil LLM per kandidat.")

    uploads = st.file_uploader("PDF jurnal (bisa pilih banyak sekaligus)",
                               type="pdf", accept_multiple_files=True)
    if uploads:
        st.caption(f"{len(uploads)} berkas siap diproses.")
    if st.button("🚀 Jalankan analisis", disabled=not uploads, type="primary",
                 width="stretch"):
        job_id = start_research(uploads)
        if job_id:
            set_active_job(job_id)
            st.toast("Analisis dimulai — halaman berpindah ke Langkah 2 otomatis.", icon="🚀")
            st.rerun()

    if jobs:
        st.divider()
        st.subheader("…atau buka analisis sebelumnya")
        pilihan = st.selectbox(
            "Analisis yang tersimpan", [j["job_id"] for j in jobs],
            format_func=lambda jid: _label(jid, jobs), key="pilih_lama")
        if st.button("📂 Buka analisis ini", width="stretch"):
            set_active_job(pilihan)
            st.rerun()


# ── LANGKAH 2 ──────────────────────────────────────────────────────────────
elif langkah == 2:
    st.subheader("Langkah 2 — Sedang diproses")
    if state == "queued":
        st.info("Job **menunggu giliran worker** (maksimal dua analisis berjalan "
                "bersamaan). Ia mulai otomatis; biarkan halaman ini terbuka.")
    else:
        st.info("**Tidak ada yang perlu kamu lakukan.** Bagian di bawah memperbarui "
                "diri sendiri; begitu keempat tahap selesai, halaman berpindah ke hasil.")

    every = REFRESH_EVERY if st.session_state.get("auto_refresh", True) else None

    @st.fragment(run_every=every)
    def _live(job_id: str) -> None:
        now = fetch_status(job_id)
        now = now if isinstance(now, dict) else {}
        if now.get("status") not in ("queued", "running"):
            # Selesai/gagal/dibatalkan: rerun seluruh halaman agar pindah ke Langkah 3.
            st.rerun(scope="app")
        events = job_events(job_id)
        progress = float(now.get("progress") or 0)
        st.progress(min(1.0, progress / 100), text=now.get("message") or "—")
        render_live_map(job_id, events, now)
        render_activity_log(events, now, stages)
        st.caption("Diperbarui otomatis tiap 3 detik." if every else
                   "Auto-refresh mati — tekan Segarkan untuk memperbarui.")

    _live(active)

    col_refresh, col_cancel = st.columns([3, 1])
    if col_refresh.button("🔄 Segarkan sekarang", width="stretch"):
        st.rerun()
    with col_cancel.popover("⏹️ Batalkan", width="stretch"):
        st.markdown("Hentikan analisis ini? Job antre berhenti seketika; job berjalan "
                    "berhenti di batas tahap berikutnya. Tahap yang sudah rampung tetap "
                    "bisa dibaca.")
        if st.button("✅ Ya, batalkan", type="primary", key="cancel_research"):
            if cancel_job(active):
                st.toast("Pembatalan diminta", icon="⏹️")
            st.rerun()


# ── LANGKAH 3 ──────────────────────────────────────────────────────────────
else:
    if state == "failed":
        st.error(f"Analisis gagal: {status.get('error') or status.get('message')}")
    elif state == "cancelled":
        st.warning(f"Analisis dibatalkan: {status.get('message') or '—'}. Tahap yang "
                   "sudah rampung tetap bisa dibaca di tab bawah.")
    else:
        st.subheader("Langkah 3 — Hasil siap dibaca")
    st.caption(f"Analisis `{active[:8]}…` · {fmt_datetime(status.get('created_at'))}")
    render_timeline(active)

    st.markdown("**Tiga tab pertama merangkum seluruh analisis**: *Ikhtisar* (corong angka & "
                "waktu), *Per jurnal* (apa yang terjadi pada tiap PDF dari awal sampai akhir), "
                "*Tema* (gap serupa lintas jurnal). **Empat tab berikutnya menelusuri tiap "
                "tahap**: *Alur & angka*, *Grafik*, *Data lengkap* dengan jejak ke sumber, dan "
                "*Kode & rumus*. Tahap penambangan gap punya *Jejak per kandidat*: chunk → "
                "LLM → gap → verifikasi.")

    events = job_events(active)
    tab_names = ["📊 Ikhtisar", "📚 Per jurnal", "🧩 Tema"] + \
                [f"{s['icon']} {s['title']}" for s in stages]
    tabs = st.tabs(tab_names)
    with tabs[0]:
        payloads = {s["key"]: stage_result_payload(active, s["key"])[1] for s in stages}
        render_overview_charts(stages, payloads, events)
    with tabs[1]:
        render_journal_crosstab(active)
    with tabs[2]:
        render_theme_browser(active)
    for tab, stage in zip(tabs[3:], stages):
        with tab:
            render_stage_body(active, stage, events)

    st.divider()
    if st.button("🔁 Mulai analisis baru", width="stretch"):
        st.session_state.pop("research_job_id", None)
        st.query_params.clear()
        st.rerun()
    st.caption("Ingin membaca teks jurnal apa adanya? Buka **📖 Teks Sumber Jurnal** "
               "di sidebar.")
