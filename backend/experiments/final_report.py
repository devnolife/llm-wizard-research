"""Final single report (kriteria keseluruhan): chunking before/after + open gaps
per topic (with citations) + example research-title candidates per topic.

Usage (from ``backend``):
    python -m experiments.final_report \
        --chunks-new ../data/processed/chunks_new.jsonl \
        --chunks-old ../data/processed/chunks_old.jsonl \
        --gaps ../data/processed/gaps_d4eb6a1d_novelty.jsonl \
        --out ../data/processed/final_report.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

from app.core.pipeline.io import read_jsonl
from experiments.audit_chunks import audit, gate

_ROWS = [
    ("mid-sentence prose cut %", "m1_midsentence_pct", "%"),
    ("clean terminal end %", "clean_terminal_pct", "%"),
    ("overlap %", "m2_overlap_pct", "%"),
    ("bad title (journals)", "m3_bad_title", ""),
    ("null year (journals)", "m4_null_year", ""),
    ("section 'other' %", "m5_other_pct", "%"),
    ("distinct sections", "m5_distinct_sections", ""),
    ("reference chunks", "m6_reference_chunks", ""),
    ("extraction-artifact chunks", "m7_artifact_chunks", ""),
    ("header/footer chunks", "m8_headerfooter_chunks", ""),
    ("duplicate chunks", "m9_duplicates", ""),
    ("poor-quality chunks", "m10_poor_chunks", ""),
]


def _fmt(v, unit):
    return f"{v:.1f}{unit}" if isinstance(v, float) else f"{v}{unit}"


def _chunking_section(new: Dict, old: Optional[Dict]) -> List[str]:
    lines = ["## TAHAP 1 — Chunking metrics (before / after)", ""]
    if old:
        lines += ["| metric | BEFORE | AFTER |", "|---|---:|---:|",
                  f"| journals | {old['journals']} | {new['journals']} |",
                  f"| chunks | {old['chunks']} | {new['chunks']} |"]
        for label, key, unit in _ROWS:
            lines.append(f"| {label} | {_fmt(old[key], unit)} | {_fmt(new[key], unit)} |")
    else:
        lines += ["| metric | value |", "|---|---:|",
                  f"| journals | {new['journals']} |", f"| chunks | {new['chunks']} |"]
        for label, key, unit in _ROWS:
            lines.append(f"| {label} | {_fmt(new[key], unit)} |")
    fails = gate(new)
    lines += ["", f"**Validation gate (bagian E):** {'PASS' if not fails else 'FAIL — ' + '; '.join(fails)}", ""]
    return lines


def _gaps_section(gaps: List[Dict]) -> List[str]:
    total = len(gaps)
    journals = len({g.get("source") for g in gaps})
    by_type = Counter(g.get("gap_type") for g in gaps)
    by_topic = Counter(g.get("topic") for g in gaps)
    grounded = sum(1 for g in gaps if (g.get("grounding_score") or 0) >= 0.82)
    lines = ["## TAHAP 2 — Research gaps extracted", "",
             f"- Total gaps: **{total}** from **{journals}** journals",
             f"- Verbatim-grounded: **{grounded}/{total}** "
             f"({100 * grounded / max(total, 1):.0f}%)",
             f"- By type: {dict(by_type)}",
             f"- By topic: {dict(by_topic)}", ""]
    return lines


def _novelty_section(gaps: List[Dict]) -> List[str]:
    have_novelty = [g for g in gaps if g.get("novelty_status")]
    counts = Counter(g.get("novelty_status") for g in have_novelty)
    lines = ["## TAHAP 3 — Novelty check", "",
             f"- Gaps with novelty_status: **{len(have_novelty)}/{len(gaps)}**",
             f"- Status: {dict(counts)}", ""]
    return lines


def _open_gaps_per_topic(gaps: List[Dict]) -> List[str]:
    open_gaps = [g for g in gaps if g.get("novelty_status") == "open"]
    by_topic: Dict[str, List[Dict]] = defaultdict(list)
    for g in open_gaps:
        by_topic[g.get("topic")].append(g)
    lines = ["## OPEN gaps per topic = safe research-title candidates", "",
             f"{len(open_gaps)} open gaps across {len(by_topic)} topics.", ""]
    for topic in sorted(by_topic):
        gs = by_topic[topic]
        lines.append(f"### {topic} ({len(gs)} open gaps)")
        for g in gs[:8]:
            cites = g.get("related_recent_papers") or []
            cite_str = "; ".join(
                f"{c.get('title', '')[:50]} ({c.get('year')})" for c in cites[:2]
            ) or "no recent match"
            lines.append(f"- **{(g.get('gap_paraphrase') or g.get('gap_statement'))[:150]}**")
            lines.append(f"  - _{g.get('source')}_ ({g.get('year')}) — recent: {cite_str}")
        lines.append("")
    return lines, by_topic


def _candidate_titles(by_topic: Dict[str, List[Dict]], use_llm: bool) -> List[str]:
    lines = ["## Example research-title candidates per topic", ""]
    if not use_llm:
        lines.append("_(LLM title generation skipped.)_")
        return lines
    from app.services import copilot_client
    if not copilot_client.is_configured():
        lines.append("_(Copilot not configured; skipping title generation.)_")
        return lines
    for topic in sorted(by_topic):
        gs = by_topic[topic][:10]
        paraphrases = "\n".join(f"- {g.get('gap_paraphrase') or g.get('gap_statement')}" for g in gs)
        prompt = (
            "Berdasarkan daftar research gap (yang BELUM terjawab literatur terbaru) "
            f"pada topik '{topic}' berikut, usulkan 3 judul penelitian dalam Bahasa "
            "Indonesia yang spesifik dan layak. Jawab sebagai daftar bernomor singkat.\n\n"
            f"{paraphrases}"
        )
        res = copilot_client.generate(prompt, system="Anda pakar metodologi penelitian.")
        titles = res[0] if res else "(tidak tersedia)"
        lines += [f"### {topic}", titles, ""]
    return lines


def _mendeley_section(path: Optional[str]) -> List[str]:
    """Include the Mendeley benchmark summary if a result JSON is available."""
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            s = json.load(fh).get("summary", {})
    except Exception:
        return []
    lines = ["## TAHAP 2 — Benchmark kualitas ekstraksi (Mendeley px9xd7tw8n)", "",
             f"- Paper sampel: {s.get('sampled_papers')} · abstrak ter-fetch: {s.get('abstracts_fetched')}",
             f"- Gap ter-ekstrak: {s.get('gap_extracted')} ({s.get('gap_extracted_pct')}% dari yang ter-fetch)",
             f"- Rata-rata semantic similarity (multilingual): **{s.get('mean_semantic_sim')}** "
             f"(≥0.5: {s.get('sim_ge_0.5')})",
             f"- LLM-as-judge (1–5, rubrik FutureGen): **{s.get('mean_llm_judge')}** "
             f"(≥3: {s.get('judge_ge_3')}/{s.get('n_judged')})", ""]
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the final single report.")
    ap.add_argument("--chunks-new", required=True)
    ap.add_argument("--chunks-old", default=None)
    ap.add_argument("--gaps", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mendeley", default=None, help="Mendeley benchmark result JSON.")
    ap.add_argument("--no-llm", action="store_true", help="Skip LLM title generation.")
    args = ap.parse_args(argv)

    new = audit(args.chunks_new)
    old = audit(args.chunks_old) if args.chunks_old else None
    gaps = [g for g in read_jsonl(args.gaps) if g.get("record") != "meta"]

    lines = [
        f"# Laporan Akhir — Pipeline Gap Penelitian",
        f"_Dibuat: {datetime.now().isoformat(timespec='seconds')}_", "",
    ]
    lines += _chunking_section(new, old)
    lines += _gaps_section(gaps)
    lines += _mendeley_section(args.mendeley)
    lines += _novelty_section(gaps)
    open_lines, by_topic = _open_gaps_per_topic(gaps)
    lines += open_lines
    lines += _candidate_titles(by_topic, use_llm=not args.no_llm)

    report = "\n".join(lines)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(report)
    print(f"\n[written to {args.out}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
