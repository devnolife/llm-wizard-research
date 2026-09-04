"""⚖️ Bandingkan dua analisis — angka per tahap berdampingan dan tumpang-tindih gap.

Penambangan gap tidak reproducible penuh (dua run pada chunk identik ~75%
tumpang tindih), jadi angka satu run bukan angka stabil. Halaman ini membuat
variasi itu terlihat: gap mana yang muncul di kedua run, mana yang hanya di
salah satu — per jurnal.
"""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from common import JOB_STATUS_BADGES, fmt_datetime, fmt_duration
from research_common import (
    fetch_all_records,
    fetch_stages,
    job_events,
    research_jobs,
    stage_result_payload,
    stage_states,
)
from research_vocab import enum_label, label

st.title("⚖️ Bandingkan Dua Analisis")
st.caption("Untuk melihat seberapa stabil hasil antar run, atau membandingkan dua kumpulan jurnal.")

jobs = [j for j in research_jobs(limit=50) if j.get("status") in ("completed", "cancelled")]
if len(jobs) < 2:
    st.info("Butuh minimal dua analisis yang selesai. Jalankan analisis lagi dari "
            "**🔬 Analisis Penelitian**.")
    st.stop()


def _label(j: dict) -> str:
    icon, lab, _ = JOB_STATUS_BADGES.get(j.get("status", ""), ("❔", "?", "gray"))
    return (f"{icon} {j['job_id'][:8]}… · {fmt_datetime(j.get('created_at'))} · "
            f"{len(j.get('files') or [])} berkas · {lab}")


ids = [j["job_id"] for j in jobs]
by_id = {j["job_id"]: j for j in jobs}
c1, c2 = st.columns(2)
a = c1.selectbox("Analisis A", ids, index=0, format_func=lambda i: _label(by_id[i]), key="cmp_a")
b = c2.selectbox("Analisis B", ids, index=min(1, len(ids) - 1),
                 format_func=lambda i: _label(by_id[i]), key="cmp_b")
if a == b:
    st.warning("Pilih dua analisis yang berbeda.")
    st.stop()

stages = fetch_stages()
ev_a, ev_b = job_events(a), job_events(b)

# ── berkas masukan ──
# Nama berkas job diawali indeks unggahan (00_, 01_, …) yang berbeda antar job;
# dibuang agar PDF yang sama dikenali sama. Ini juga yang dilakukan source_name().
_IDX = re.compile(r"^\d+_")
files_a = {_IDX.sub("", str(f).split("/")[-1]) for f in (by_id[a].get("files") or [])}
files_b = {_IDX.sub("", str(f).split("/")[-1]) for f in (by_id[b].get("files") or [])}
same_input = files_a == files_b and bool(files_a)
if same_input:
    st.success(f"Kedua analisis memakai **{len(files_a)} PDF yang sama** → perbedaan angka di "
               "bawah murni variasi sistem (LLM non-deterministik, throttle OpenAlex).")
else:
    st.warning(f"Masukan berbeda: A {len(files_a)} berkas, B {len(files_b)} berkas, "
               f"sama {len(files_a & files_b)}. Perbedaan angka mencakup perbedaan korpus, "
               "bukan hanya variasi sistem.")

# ── metrik per tahap berdampingan ──
st.subheader("Angka per tahap")
rows = []
durs = []
for stage in stages:
    key = stage["key"]
    _, pa = stage_result_payload(a, key)
    _, pb = stage_result_payload(b, key)
    ma, mb = pa.get("metrics") or {}, pb.get("metrics") or {}
    seen = {r["kunci"] for r in rows}
    for sub in stage.get("substeps") or []:
        for field in ("in_metric", "out_metric", "drop_metric"):
            mk = sub.get(field)
            if not mk or mk in seen:
                continue
            va, vb = ma.get(mk), mb.get(mk)
            if isinstance(va, (int, float)) or isinstance(vb, (int, float)):
                seen.add(mk)
                va_n = va if isinstance(va, (int, float)) else None
                vb_n = vb if isinstance(vb, (int, float)) else None
                rows.append({"tahap": stage["title"], "kunci": mk, "ukuran": label(mk),
                             "A": va_n, "B": vb_n,
                             "B − A": (vb_n - va_n) if va_n is not None and vb_n is not None
                             else None})
    da = stage_states(a, ev_a).get(key, {}).get("duration_ms")
    db = stage_states(b, ev_b).get(key, {}).get("duration_ms")
    durs.append({"tahap": stage["title"],
                 "A": fmt_duration(da) if da else "—", "B": fmt_duration(db) if db else "—",
                 "selisih": fmt_duration(abs(db - da)) if da and db else "—"})
# Angka dan durasi dipisah: satu kolom campur int & teks membuat Arrow menolak tabel.
mdf = pd.DataFrame(rows)[["tahap", "ukuran", "A", "B", "B − A"]]
st.dataframe(mdf, width="stretch", hide_index=True, height=min(600, 38 + 35 * len(mdf)))
st.caption("Durasi tiap tahap")
st.dataframe(pd.DataFrame(durs), width="stretch", hide_index=True)

# ── tumpang-tindih gap ──
st.subheader("Gap yang sama dan yang berbeda")
_WS = re.compile(r"\s+")


def _norm(s: str | None) -> str:
    return _WS.sub(" ", (s or "").strip().lower())


def _gap_set(job_id: str) -> dict[tuple[str, str], dict]:
    return {(g.get("source"), _norm(g.get("gap_statement"))): g
            for g in fetch_all_records(job_id, "gap_mining")}


ga, gb = _gap_set(a), _gap_set(b)
common = set(ga) & set(gb)
only_a, only_b = set(ga) - set(gb), set(gb) - set(ga)
union = len(ga | gb) if (ga or gb) else 0
jacc = len(common) / union if union else 0.0

k = st.columns(5)
k[0].metric("gap A", len(ga))
k[1].metric("gap B", len(gb))
k[2].metric("sama di keduanya", len(common))
k[3].metric("hanya A / hanya B", f"{len(only_a)} / {len(only_b)}")
k[4].metric("Jaccard", f"{jacc:.2f}", help="|A∩B| / |A∪B|; 1,0 = identik. Dua run pada "
                                            "chunk identik biasanya ~0,6.")
if same_input and union:
    st.caption(f"Pada masukan identik, **{len(common)} dari {union}** gap unik gabungan muncul "
               f"di kedua run ({100 * len(common) / union:.0f}%). Sisanya hanya muncul di satu "
               "run — itulah sebabnya skripsi perlu melaporkan frekuensi kemunculan k/n dari "
               "beberapa run, bukan angka satu run.")

# per jurnal
sources = sorted({s for s, _ in ga} | {s for s, _ in gb})
per = []
for s in sources:
    sa = {kk for kk in ga if kk[0] == s}
    sb = {kk for kk in gb if kk[0] == s}
    per.append({"jurnal": s, "gap A": len(sa), "gap B": len(sb), "sama": len(sa & sb),
                "hanya A": len(sa - sb), "hanya B": len(sb - sa)})
if per:
    st.dataframe(pd.DataFrame(per), width="stretch", hide_index=True)

tab_c, tab_a, tab_b = st.tabs([f"✅ Sama ({len(common)})", f"🅰️ Hanya A ({len(only_a)})",
                               f"🅱️ Hanya B ({len(only_b)})"])


def _list(keys, pool):
    for kk in sorted(keys):
        g = pool[kk]
        st.markdown(f"- **{g.get('source')}** · {enum_label('gap_type', g.get('gap_type'))} — "
                    f"{g.get('gap_statement')}")


with tab_c:
    _list(common, ga) if common else st.caption("Tidak ada gap yang sama.")
with tab_a:
    _list(only_a, ga) if only_a else st.caption("—")
with tab_b:
    _list(only_b, gb) if only_b else st.caption("—")

# ── status kebaruan gap yang sama ──
if common:
    st.subheader("Status kebaruan gap yang sama di keduanya")
    na = {(g.get("source"), _norm(g.get("gap_statement"))): g.get("novelty_status")
          for g in fetch_all_records(a, "novelty")}
    nb = {(g.get("source"), _norm(g.get("gap_statement"))): g.get("novelty_status")
          for g in fetch_all_records(b, "novelty")}
    agree = sum(1 for kk in common if na.get(kk) and na.get(kk) == nb.get(kk))
    flips = [{"jurnal": kk[0], "gap": ga[kk].get("gap_statement", "")[:110],
              "A": enum_label("novelty_status", na.get(kk)),
              "B": enum_label("novelty_status", nb.get(kk))}
             for kk in sorted(common) if na.get(kk) != nb.get(kk)]
    st.caption(f"Status sama pada **{agree}/{len(common)}** gap. Perbedaan status pada gap yang "
               "identik berasal dari OpenAlex (hasil pencarian/throttle berbeda antar waktu), "
               "bukan dari LLM.")
    if flips:
        st.dataframe(pd.DataFrame(flips), width="stretch", hide_index=True)
