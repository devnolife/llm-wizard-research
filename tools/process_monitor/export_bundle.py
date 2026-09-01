"""Ekspor satu run analisis menjadi SATU berkas Markdown yang ramah agen AI.

Tujuan berkas keluaran: sebuah agen AI (atau pembaca manusia) cukup membaca
satu berkas untuk memahami seluruh hasil analisis — korpus, indikator gap,
rantai bukti, usulan, sampai keterbatasannya — tanpa perlu memanggil API.

Prinsip penyusunan:
- Front-matter YAML di atas supaya bagian metadata bisa diurai mesin.
- Judul berjenjang dan stabil supaya agen bisa merujuk bagian tertentu.
- Angka disajikan apa adanya, termasuk yang nol dan yang belum tersedia,
  supaya agen tidak menyimpulkan lebih dari yang sistem klaim.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

INDICATOR_LABELS = {
    "FRAGMENTATION": "Fragmentasi",
    "INCONSISTENCY": "Inkonsistensi",
    "INCOMPLETENESS": "Ketidaklengkapan",
    "SUPPORT_GAP": "Ketiadaan Dukungan Bukti",
}

BAND_LABELS = {
    "sweet_spot": "kebaruan sehat",
    "derivative": "mirip literatur yang ada",
    "off_topic": "jauh dari korpus",
}


def _txt(value: Any) -> str:
    """Rapikan teks bebas jadi satu baris tanpa spasi ganda."""
    return " ".join(str(value or "").split())


def _block(value: Any) -> str:
    """Teks multi-paragraf: buang spasi berlebih tapi pertahankan baris baru."""
    raw = str(value or "").replace("\r\n", "\n").strip()
    return "\n".join(line.rstrip() for line in raw.split("\n"))


def _cell(value: Any) -> str:
    """Teks aman untuk sel tabel Markdown.

    Judul yang diekstrak dari PDF kerap memuat `|` (mis. "ISSN: 2181-3191
    VOLUME 2 | ISSUE 1"). Bila tidak di-escape, pipa itu dibaca sebagai
    pembatas kolom sehingga barisnya rusak dan tabel gagal diurai agen.
    """
    return _txt(value).replace("\\", "\\\\").replace("|", "\\|")


def _demote_headings(text: str, min_level: int) -> str:
    """Turunkan level heading teks sisipan agar tidak bertabrakan dengan
    penomoran bagian dokumen.

    Ringkasan dari LLM sering membawa headingnya sendiri (`# Ringkasan`,
    `## 1. Definisi`). Bila ditempel apa adanya, `## 1.` akan terbaca sebagai
    Bagian 1 dokumen ini dan merusak hierarki bagi pembaca maupun agen.
    """
    if not text:
        return text
    out: list[str] = []
    in_fence = False
    shift: int | None = None
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        hashes = len(stripped) - len(stripped.lstrip("#"))
        if hashes and stripped[hashes:hashes + 1] in (" ", "\t"):
            if shift is None:
                shift = max(0, min_level - hashes)
            new_level = min(6, hashes + shift)
            out.append("#" * new_level + stripped[hashes:])
        else:
            out.append(line)
    return "\n".join(out)


def _yaml_str(value: Any) -> str:
    return json.dumps(_txt(value), ensure_ascii=False)


def _pct(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "—"


def _num(value: Any, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def _ts(value: Any) -> str:
    try:
        return datetime.fromtimestamp(float(value)).isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError):
        return ""


def _duration(status: dict) -> str:
    try:
        secs = float(status["completed_at"]) - float(status["created_at"])
    except (KeyError, TypeError, ValueError):
        return ""
    m, s = divmod(int(secs), 60)
    return f"{m} menit {s} detik" if m else f"{s} detik"


def _indicator_counts(gaps: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for g in gaps:
        key = str(g.get("type") or g.get("indicator_type") or "").upper()
        if key:
            counts[key] = counts.get(key, 0) + 1
    return counts


def _front_matter(job_id: str, status: dict, results: dict) -> list[str]:
    gaps = results.get("gaps") or []
    recs = results.get("recommendations") or []
    prov_known = [g for g in gaps if g.get("provenance")]
    counts = _indicator_counts(gaps)
    calib = next((g.get("calibration") for g in gaps if g.get("calibration")), {}) or {}

    lines = [
        "---",
        f"dokumen: {_yaml_str('Hasil analisis gap penelitian — Wizard Research')}",
        f"job_id: {_yaml_str(job_id)}",
        f"dibuat_pada: {_yaml_str(_ts(status.get('created_at')))}",
        f"selesai_pada: {_yaml_str(_ts(status.get('completed_at')))}",
        f"diekspor_pada: {_yaml_str(datetime.now().isoformat(timespec='seconds'))}",
        f"jumlah_jurnal: {int(results.get('files_processed') or len(results.get('papers_info') or []))}",
        f"jumlah_chunk: {int(results.get('total_chunks') or 0)}",
        f"jumlah_topik: {len(results.get('topics') or [])}",
        f"jumlah_indikator_gap: {len(gaps)}",
        f"jumlah_usulan: {len(recs)}",
    ]
    if counts:
        lines.append("indikator_per_tipe:")
        for key in INDICATOR_LABELS:
            lines.append(f"  {key}: {counts.get(key, 0)}")
    if prov_known:
        complete = sum(1 for g in prov_known if (g.get("provenance") or {}).get("complete"))
        lines += [
            f"provenans_lengkap: {complete}",
            f"provenans_total: {len(prov_known)}",
            f"ditahan_untuk_telaah: {sum(1 for g in gaps if g.get('needs_review'))}",
        ]
    if calib:
        lines += [
            f"kalibrator_terlatih: {str(bool(calib.get('calibrator_fitted'))).lower()}",
            f"jumlah_label_pakar: {int(calib.get('calibration_labels') or 0)}",
        ]
    model = (results.get("llm_info") or {}).get("model")
    if model:
        lines.append(f"model_llm: {_yaml_str(model)}")
    if results.get("execution_mode"):
        lines.append(f"mode_eksekusi: {_yaml_str(results['execution_mode'])}")
    lines.append("---")
    return lines


def _how_to_read(results: dict) -> list[str]:
    gaps = results.get("gaps") or []
    has_layers = any(g.get("provenance") or g.get("calibration") for g in gaps)
    lines = [
        "",
        "## 0. Cara membaca berkas ini",
        "",
        "Berkas ini adalah keluaran lengkap **satu kali analisis** korpus jurnal "
        "oleh sistem neuro-simbolik pendeteksi *synthesis gap*. Urutan bagiannya "
        "mengikuti alur kerja sistem: korpus → topik → indikator gap → bukti → "
        "usulan → peta jalan.",
        "",
        "Istilah kunci:",
        "",
        "- **Synthesis gap** — kesenjangan yang baru terlihat setelah beberapa "
        "jurnal disintesis, bukan kekurangan satu jurnal. Kekurangan per jurnal "
        "ada di Bagian 8 sebagai bahan mentahnya.",
        "- **Empat indikator** — Fragmentasi, Inkonsistensi, Ketidaklengkapan, dan "
        "Ketiadaan Dukungan Bukti. Indikator yang **tidak terdeteksi tetap "
        "dicantumkan bernilai 0**; itu informasi, bukan kekosongan data.",
        "- **Keyakinan mentah vs terkalibrasi** — angka mentah berasal dari "
        "detektor; angka terkalibrasi sudah melewati Rule Engine dan lapisan "
        "kalibrasi. Pakai angka terkalibrasi bila keduanya ada.",
        "- **Provenans** — rantai `klaim → jurnal terkutip → kutipan verbatim → "
        "hasil validasi`. Bila rantai putus, sistem menandai gap itu perlu "
        "telaah manusia alih-alih mengklaimnya.",
        "- **Kebaruan (novelty)** — hanya **pengurut prioritas usulan**, bukan "
        "definisi gap. Usulan yang baru tapi tidak berpijak pada gap justru "
        "diberi prioritas rendah.",
        "",
        "Peringatan penggunaan bagi agen AI:",
        "",
        "- Jangan menaikkan derajat klaim. Bila suatu gap ditandai "
        "*perlu telaah*, sampaikan status itu, jangan disajikan sebagai temuan.",
        "- Jangan menghitung ulang metrik yang sengaja tidak dilaporkan "
        "(lihat Bagian 11); ketiadaannya disengaja, bukan terlewat.",
        "- Kutipan pada Bagian 4 dan 8 adalah teks verbatim dari PDF sumber; "
        "jangan diparafrase bila dipakai sebagai bukti.",
    ]
    if not has_layers:
        lines += [
            "",
            "> **Catatan:** run ini dibuat sebelum lapisan kalibrasi dan provenans "
            "ditambahkan, sehingga Bagian 3 dan rantai bukti pada Bagian 4 tidak "
            "tersedia.",
        ]
    return lines


def _corpus_section(results: dict) -> list[str]:
    papers = results.get("papers_info") or []
    lines = ["", "## 1. Korpus yang dianalisis", ""]
    stats = [
        f"- Jurnal diproses: **{results.get('files_processed') or len(papers)}**",
        f"- Total chunk teks: **{results.get('total_chunks') or 0}**",
    ]
    if results.get("new_papers") is not None:
        stats.append(
            f"- Jurnal baru: **{results.get('new_papers')}** · "
            f"duplikat terdeteksi: **{results.get('duplicate_papers') or 0}**"
        )
    lines += stats
    if not papers:
        return lines
    lines += [
        "",
        "| # | Judul | Berkas | Tahun | Chunk |",
        "|---|---|---|---|---|",
    ]
    for i, p in enumerate(papers, start=1):
        title = _txt(p.get("title"))[:110]
        lines.append(
            f"| {i} | {_cell(title) or '—'} | `{_cell(p.get('source'))}` | "
            f"{p.get('year') or '—'} | {p.get('num_chunks') or '—'} |"
        )
    return lines


def _summary_section(results: dict) -> list[str]:
    lines = ["", "## 2. Ringkasan eksekutif", ""]
    body = _block(results.get("summary"))
    lines.append(_demote_headings(body, 3) if body else "_(ringkasan kosong)_")
    topics = results.get("topics") or []
    if topics:
        lines += ["", "### 2.1 Topik yang teridentifikasi", ""]
        lines += [f"{i}. {_txt(t)}" for i, t in enumerate(topics, start=1)]
    return lines


def _method_status_section(results: dict) -> list[str]:
    gaps = results.get("gaps") or []
    recs = results.get("recommendations") or []
    counts = _indicator_counts(gaps)
    prov_known = [g for g in gaps if g.get("provenance")]
    calib = next((g.get("calibration") for g in gaps if g.get("calibration")), {}) or {}

    lines = ["", "## 3. Status lapisan metode pada run ini", ""]
    lines += [
        "| Lapisan | Hasil |",
        "|---|---|",
        f"| Indikator gap lolos | {len(gaps)} |",
    ]
    if prov_known:
        complete = sum(1 for g in prov_known if (g.get("provenance") or {}).get("complete"))
        held = sum(1 for g in gaps if g.get("needs_review"))
        lines += [
            f"| Provenans lengkap | {complete}/{len(prov_known)} |",
            f"| Ditahan untuk telaah manusia | {held}/{len(gaps)} |",
        ]
    else:
        lines += [
            "| Provenans lengkap | tidak tersedia pada run ini |",
            "| Ditahan untuk telaah manusia | tidak tersedia pada run ini |",
        ]
    if calib:
        temp = calib.get("temperature")
        lines.append(f"| Suhu kalibrasi (T) | {_num(temp, 2)} |")
        lines.append(
            f"| Kalibrator terlatih | "
            f"{'ya' if calib.get('calibrator_fitted') else 'belum'} "
            f"({int(calib.get('calibration_labels') or 0)} label pakar) |"
        )
    report = results.get("rule_engine_report") or {}
    if report:
        lines.append(
            f"| Rule Engine | {report.get('passed', 0)} lolos · "
            f"{report.get('flagged', 0)} ditandai · {report.get('rejected', 0)} ditolak |"
        )

    lines += ["", "### 3.1 Sebaran empat indikator", "", "| Indikator | Jumlah |", "|---|---|"]
    for key, label in INDICATOR_LABELS.items():
        lines.append(f"| {label} (`{key}`) | {counts.get(key, 0)} |")
    absent = [INDICATOR_LABELS[k] for k in INDICATOR_LABELS if not counts.get(k)]
    if absent:
        lines += [
            "",
            f"Indikator yang **tidak terdeteksi** pada korpus ini: {', '.join(absent)}. "
            "Nol berarti pola tersebut memang tidak ditemukan, bukan berarti "
            "indikatornya tidak diuji.",
        ]

    novs = [r.get("novelty") for r in recs if r.get("novelty")]
    if novs:
        lines += ["", "### 3.2 Skor kebaruan usulan", ""]
        try:
            vals = [float(n.get("novelty", 0)) for n in novs]
            bands: dict[str, int] = {}
            for n in novs:
                b = str(n.get("band") or "?")
                bands[b] = bands.get(b, 0) + 1
            band_txt = ", ".join(
                f"{v} {BAND_LABELS.get(k, k)}" for k, v in bands.items()
            )
            lines.append(
                f"Rentang kebaruan {len(novs)} usulan: **{min(vals):.0%}–{max(vals):.0%}** "
                f"({band_txt})."
            )
        except (TypeError, ValueError):
            lines.append("_(skor kebaruan tidak dapat dibaca)_")
        lines.append(
            "Skor ini **mengurutkan prioritas**, bukan mendefinisikan gap."
        )
    elif recs:
        lines += [
            "",
            "### 3.2 Skor kebaruan usulan",
            "",
            "_Tidak tersedia pada run ini._",
        ]
    return lines


def _gap_section(results: dict) -> list[str]:
    gaps = results.get("gaps") or []
    lines = ["", "## 4. Indikator gap kolektif", ""]
    if not gaps:
        lines.append("_Tidak ada gap terdeteksi pada run ini._")
        return lines
    lines.append(
        "Setiap gap di bawah disintesis dari kekurangan lintas jurnal "
        "(bahan mentah per jurnal ada di Bagian 8)."
    )

    for i, gap in enumerate(gaps, start=1):
        gtype = str(gap.get("type") or "").upper()
        label = INDICATOR_LABELS.get(gtype, gtype or "—")
        title = _txt(gap.get("title"))
        lines += ["", f"### 4.{i} {label}" + (f" — {title}" if title else ""), ""]
        lines.append(f"- **Tipe indikator:** `{gtype or '—'}`")

        calib = gap.get("calibration") or {}
        raw = gap.get("confidence", calib.get("raw_confidence"))
        cal = gap.get("calibrated_confidence", calib.get("calibrated_confidence"))
        if raw is not None:
            lines.append(f"- **Keyakinan mentah:** {_pct(raw)}")
        if cal is not None:
            lines.append(f"- **Keyakinan terkalibrasi:** {_pct(cal)}")
        verdict = gap.get("rule_engine_verdict") or calib.get("rule_verdict")
        if verdict:
            lines.append(f"- **Putusan Rule Engine:** {verdict}")

        if gap.get("needs_review"):
            reasons = [_txt(r) for r in (gap.get("abstention_reasons") or []) if _txt(r)]
            lines.append(
                "- **Status klaim:** ⚠️ DITAHAN — sistem tidak mengklaim temuan ini "
                "tanpa telaah manusia."
                + (f" Alasan: {'; '.join(reasons)}." if reasons else "")
            )
        elif gap.get("provenance"):
            lines.append("- **Status klaim:** diklaim (lolos pemeriksaan provenans)")

        desc = _block(gap.get("description"))
        if desc:
            lines += ["", "**Deskripsi:**", "", _demote_headings(desc, 4)]

        prov = gap.get("provenance") or {}
        if prov:
            lines += ["", "**Rantai provenans:**", ""]
            cited = [_txt(c) for c in (prov.get("cited_records") or []) if _txt(c)]
            passages = prov.get("retrieved_passages") or []
            lines.append(
                f"- Kelengkapan: {'lengkap' if prov.get('complete') else 'PUTUS'}"
                + (
                    f" (mata rantai hilang: {', '.join(prov.get('broken_links') or [])})"
                    if not prov.get("complete")
                    else ""
                )
            )
            if prov.get("validation_outcome"):
                lines.append(
                    f"- Validasi: {prov['validation_outcome']}"
                    + (f" — {_txt(prov.get('validation_detail'))}" if prov.get("validation_detail") else "")
                )
            if cited:
                lines.append(f"- Jurnal terkutip ({len(cited)}):")
                lines += [f"  - `{c}`" for c in cited]
            if passages:
                lines += ["", f"- Kutipan verbatim pendukung ({len(passages)}):"]
                for p in passages:
                    quote = _txt(p.get("quote"))
                    if not quote:
                        continue
                    src = _txt(p.get("source_paper"))
                    tail = f" — sumber: `{src}`" if src and src != "?" else ""
                    score = p.get("match_score")
                    if score is not None:
                        tail += f" (skor kecocokan {_num(score, 2)})"
                    lines += ["", f"  > {quote}{tail}"]

        evidence = [_txt(e) for e in (gap.get("evidence") or []) if _txt(e)]
        if evidence:
            lines += ["", "**Bukti pendukung:**", ""]
            lines += [f"- {e}" for e in evidence]

        related = [_txt(r) for r in (gap.get("related_papers") or []) if _txt(r)]
        if related:
            lines += ["", f"**Jurnal yang terlibat ({len(related)}):**", ""]
            lines += [f"- {r}" for r in related]

        directions = [_txt(d) for d in (gap.get("suggested_directions") or []) if _txt(d)]
        if directions:
            lines += ["", "**Arah riset yang disarankan:**", ""]
            lines += [f"- {d}" for d in directions]
    return lines


def _recommendation_section(results: dict) -> list[str]:
    recs = results.get("recommendations") or []
    lines = ["", "## 5. Usulan penelitian", ""]
    if results.get("proposal_intro"):
        lines += [f"> {_txt(results['proposal_intro'])}", ""]
    if not recs:
        lines.append("_Tidak ada usulan pada run ini._")
        return lines
    lines.append(
        "Usulan diurutkan mengikuti skor prioritas bila tersedia. Skor prioritas "
        "menggabungkan keyakinan gap, kelayakan eksekusi, dan kebaruan — dengan "
        "keyakinan gap sebagai faktor penentu."
    )
    for i, rec in enumerate(recs, start=1):
        gtype = str(rec.get("gap_type") or "").upper()
        lines += ["", f"### 5.{i} {_txt(rec.get('title')) or '(tanpa judul)'}", ""]
        lines.append(
            f"- **Menjawab indikator:** {INDICATOR_LABELS.get(gtype, gtype or '—')} "
            f"(`{gtype or '—'}`)"
        )
        if rec.get("priority"):
            lines.append(f"- **Prioritas:** {rec['priority']}")
        nov = rec.get("novelty") or {}
        if nov:
            lines += [
                f"- **Skor prioritas:** {_num(nov.get('priority_score'), 4)}",
                f"- **Kebaruan:** {_pct(nov.get('novelty'))} "
                f"({BAND_LABELS.get(str(nov.get('band')), _txt(nov.get('band')) or '—')})",
                f"- **Kelayakan eksekusi:** {_pct(nov.get('actionability'))}",
                f"- **Keyakinan gap yang mendasari:** {_pct(nov.get('gap_confidence'))}",
            ]
            if nov.get("nearest_paper"):
                lines.append(
                    f"- **Jurnal terdekat di korpus:** `{_txt(nov['nearest_paper'])}` "
                    f"(kemiripan {_pct(nov.get('nearest_similarity'))})"
                )
            notes = [_txt(n) for n in (nov.get("notes") or []) if _txt(n)]
            if notes:
                lines.append(f"- **Catatan kebaruan:** {'; '.join(notes)}")
        desc = _block(rec.get("description"))
        if desc:
            lines += ["", _demote_headings(desc, 4)]
        if rec.get("why"):
            lines += ["", f"**Mengapa penting:** {_txt(rec['why'])}"]
        if rec.get("how"):
            lines += ["", f"**Bagaimana dikerjakan:** {_txt(rec['how'])}"]

    refs = results.get("related_paper_refs") or []
    if refs:
        lines += ["", "### Rujukan jurnal terkait (pelengkap)", ""]
        for ref in refs:
            lines.append(f"- **{_txt(ref.get('title'))}** — {_txt(ref.get('reason'))}")
    return lines


def _roadmap_section(results: dict) -> list[str]:
    roadmap = results.get("roadmap") or []
    lines = ["", "## 6. Peta jalan penelitian", ""]
    if not roadmap:
        lines.append("_Tidak tersedia._")
        return lines
    for phase in roadmap:
        lines += ["", f"### {_txt(phase.get('phase'))}", ""]
        lines += [f"- {_txt(item)}" for item in (phase.get("items") or [])]
    return lines


def _knowledge_section(results: dict) -> list[str]:
    lines = ["", "## 7. Basis pengetahuan (fakta SPO)", ""]
    stats = results.get("fact_table_stats") or {}
    if stats:
        lines += [f"- `{k}`: {v}" for k, v in stats.items()]
    facts = results.get("sample_facts") or []
    if facts:
        lines += ["", "Contoh fakta terekstraksi:", ""]
        for f in facts:
            if isinstance(f, dict):
                trip = " → ".join(
                    _txt(f.get(k)) for k in ("subject", "predicate", "object") if f.get(k)
                )
                lines.append(f"- {trip or _txt(json.dumps(f, ensure_ascii=False))}")
            else:
                lines.append(f"- {_txt(f)}")
    if not stats and not facts:
        lines.append("_Tidak tersedia._")
    return lines


def _weakness_section(results: dict) -> list[str]:
    weaknesses = results.get("paper_weaknesses") or []
    lines = ["", "## 8. Kekurangan per jurnal (bahan mentah sintesis)", ""]
    if not weaknesses:
        lines.append("_Tidak tersedia._")
        return lines
    total = sum(
        len(w.get("tersurat") or []) + len(w.get("tersirat") or []) for w in weaknesses
    )
    lines.append(
        f"Total **{total} butir kekurangan** dari {len(weaknesses)} jurnal. "
        "*Tersurat* = dinyatakan penulis sendiri (ada kutipan). "
        "*Tersirat* = disimpulkan sistem dari isi jurnal."
    )
    for i, w in enumerate(weaknesses, start=1):
        tersurat = w.get("tersurat") or []
        tersirat = w.get("tersirat") or []
        lines += [
            "",
            f"### 8.{i} {_txt(w.get('title'))[:110] or _txt(w.get('source'))}",
            "",
            f"Berkas: `{_txt(w.get('source'))}`",
        ]
        if not tersurat and not tersirat:
            lines += ["", "_Tidak ada kekurangan tercatat untuk jurnal ini._"]
            continue
        for kind, items in (("Tersurat", tersurat), ("Tersirat", tersirat)):
            if not items:
                continue
            lines += ["", f"**{kind} ({len(items)}):**", ""]
            for it in items:
                poin = _txt(it.get("poin"))
                meta = []
                if it.get("verification_status"):
                    meta.append(_txt(it["verification_status"]))
                if it.get("confidence") is not None:
                    meta.append(f"keyakinan {_pct(it.get('confidence'))}")
                suffix = f" _({' · '.join(meta)})_" if meta else ""
                lines.append(f"- {poin}{suffix}")
                if it.get("dasar"):
                    lines.append(f"  - Dasar: {_txt(it['dasar'])}")
                if it.get("kutipan"):
                    lines.append(f"  - Kutipan: \"{_txt(it['kutipan'])}\"")
    return lines


def _metrics_section(results: dict) -> list[str]:
    lines = ["", "## 9. Metrik evaluasi pipeline", ""]
    metrics = results.get("eval_metrics") or {}
    if metrics:
        lines += ["| Metrik | Nilai |", "|---|---|"]
        for k, v in metrics.items():
            lines.append(f"| `{_cell(k)}` | {_cell(v)} |")
    else:
        lines.append("_Tidak tersedia._")
    return lines


def _trace_section(results: dict) -> list[str]:
    trace = results.get("reasoning_trace") or []
    lines = ["", "## 10. Jejak penalaran agen", ""]
    if not trace:
        lines.append("_Tidak tersedia._")
        return lines
    for step in trace:
        lines += ["", f"**Fase `{_txt(step.get('phase'))}`** ({_txt(step.get('timestamp'))})", ""]
        lines += [f"- {_txt(a)}" for a in (step.get("actions") or [])]
    skills = results.get("skills_used") or []
    if skills:
        lines += ["", f"Skill riset yang dipakai: {', '.join(f'`{s}`' for s in skills)}"]
    return lines


def _limitations_section(results: dict) -> list[str]:
    gaps = results.get("gaps") or []
    calib = next((g.get("calibration") for g in gaps if g.get("calibration")), {}) or {}
    lines = [
        "",
        "## 11. Keterbatasan yang harus ikut dibaca",
        "",
        "Bagian ini sengaja disertakan agar agen AI tidak melaporkan hasil di atas "
        "sebagai lebih pasti daripada yang sebenarnya diklaim sistem.",
        "",
    ]
    items = []
    if calib and not calib.get("calibrator_fitted"):
        items.append(
            f"**Kalibrator belum terlatih** ({int(calib.get('calibration_labels') or 0)} "
            "label pakar). Suhu kalibrasi masih T=1,00 sehingga pemetaannya identitas: "
            "angka \"terkalibrasi\" berasal dari penyesuaian Rule Engine, bukan "
            "*temperature scaling* terlatih. Karena itu **ECE, Brier score, dan AURC "
            "sengaja tidak dilaporkan** — melaporkannya tanpa label pakar akan "
            "menyesatkan."
        )
    if calib.get("conformal_cutoff") is None and calib:
        items.append(
            "**Ambang konformal belum tersedia**, sehingga penahanan klaim "
            "(abstensi) bersandar pada kelengkapan provenans dan putusan Rule "
            "Engine, bukan jaminan cakupan statistik."
        )
    counts = _indicator_counts(gaps)
    absent = [INDICATOR_LABELS[k] for k in INDICATOR_LABELS if not counts.get(k)]
    if absent:
        items.append(
            f"**Indikator {', '.join(absent)} tidak terdeteksi** pada korpus ini. "
            "Ini temuan negatif untuk korpus tersebut, bukan bukti bahwa indikator "
            "itu tidak berfungsi."
        )
    items.append(
        "**Kekurangan *tersirat* pada Bagian 8 adalah inferensi LLM**, bukan "
        "pernyataan penulis jurnal. Hanya butir *tersurat* yang punya kutipan "
        "verbatim sebagai dasar."
    )
    items.append(
        "**Kebaruan bukan definisi gap.** Kombinasi metode-domain yang belum "
        "pernah dicoba tidak dihitung sebagai *synthesis gap*; skor kebaruan hanya "
        "mengurutkan prioritas usulan yang sudah berpijak pada gap."
    )
    lines += [f"{i}. {t}" for i, t in enumerate(items, start=1)]
    return lines


def build_agent_bundle_md(job_id: str, status: dict, results: dict) -> str:
    """Rakit seluruh hasil satu run jadi satu dokumen Markdown."""
    parts: list[str] = []
    parts += _front_matter(job_id, status, results)
    parts += [
        "",
        "# Hasil Analisis Gap Penelitian",
        "",
        f"Job `{job_id}` · {results.get('files_processed') or len(results.get('papers_info') or [])} "
        f"jurnal · {results.get('total_chunks') or 0} chunk"
        + (f" · durasi {_duration(status)}" if _duration(status) else ""),
    ]
    parts += _how_to_read(results)
    parts += _corpus_section(results)
    parts += _summary_section(results)
    parts += _method_status_section(results)
    parts += _gap_section(results)
    parts += _recommendation_section(results)
    parts += _roadmap_section(results)
    parts += _knowledge_section(results)
    parts += _weakness_section(results)
    parts += _metrics_section(results)
    parts += _trace_section(results)
    parts += _limitations_section(results)
    parts += [
        "",
        "---",
        "",
        f"_Dibangkitkan otomatis oleh Wizard Research Monitor pada "
        f"{datetime.now().strftime('%d %B %Y %H:%M')} dari job `{job_id}`._",
        "",
    ]
    return "\n".join(parts)


def _cli() -> int:
    """Bangkitkan bundle langsung dari terminal (cadangan bila UI tak terjangkau).

    Contoh:
        python export_bundle.py                 # job terbaru → stdout ringkas + file
        python export_bundle.py 977fdd5a        # job tertentu
        python export_bundle.py --list          # lihat daftar job
    """
    import argparse
    import urllib.request

    api = os.environ.get("MONITOR_API", "http://127.0.0.1:8001/api")

    def _get(path: str) -> dict:
        with urllib.request.urlopen(f"{api}{path}", timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))

    ap = argparse.ArgumentParser(description="Ekspor hasil analisis jadi satu berkas Markdown.")
    ap.add_argument("job_id", nargs="?", help="ID job (boleh 8 karakter awal). Kosong = terbaru.")
    ap.add_argument("-o", "--output", help="Nama berkas keluaran.")
    ap.add_argument("--list", action="store_true", help="Tampilkan daftar job lalu keluar.")
    args = ap.parse_args()

    try:
        payload = _get("/analysis-jobs")
    except Exception as exc:
        print(f"Gagal menghubungi backend di {api} — apakah sudah jalan?\n  {exc}")
        return 1
    jobs = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    done = [j for j in jobs if j.get("status") == "completed"]

    if args.list:
        for j in done:
            print(f"{j.get('job_id', '')[:8]}  {j.get('files_processed') or '?'} jurnal")
        return 0
    if not done:
        print("Belum ada job yang selesai.")
        return 1

    if args.job_id:
        match = [j for j in done if str(j.get("job_id", "")).startswith(args.job_id)]
        if not match:
            print(f"Job '{args.job_id}' tidak ditemukan / belum selesai. Coba --list.")
            return 1
        job = match[0]
    else:
        job = done[0]

    job_id = job["job_id"]
    status = _get(f"/analysis-status/{job_id}")
    results = status.get("results") or {}
    if not results:
        print(f"Job {job_id[:8]} belum punya hasil.")
        return 1

    md = build_agent_bundle_md(job_id, status, results)
    n = results.get("files_processed") or len(results.get("paper_weaknesses") or [])
    out = args.output or f"analisis_gap_{n}jurnal_{job_id[:8]}.md"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"✔ {out}  ({len(md) / 1024:.1f} KB · {n} jurnal · job {job_id[:8]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
