"""Gabungkan gap dari beberapa run gap mining menjadi union beranotasi k/n.

Gap mining memakai LLM yang tidak deterministik: dua run pada chunk yang identik
hanya ~75% tumpang tindih, jadi angka satu run ("388 gap") adalah satu undian.
Skrip ini adalah PRODUSEN resmi ``gaps_union.jsonl``: ia memakai kunci gabungan
dan ambang stabil yang SAMA dengan tahap ``gap_mining`` di
``app.services.research_pipeline`` (``merge_gap_runs``), sehingga k/n dari CLI dan
dari job identik.

Tiap gap keluaran membawa ``run_hits`` (muncul di berapa run), ``run_total``,
``run_ids`` (1-based, urutan --inputs) dan ``stable`` (run_hits >= ambang).
Kolom lain diambil dari run PERTAMA yang memuat gap itu; ``grounding_score``
diambil maksimumnya.

Pakai (dari backend):
    python -m experiments.consensus_gaps \
        --inputs ../data/processed/gaps_v3.jsonl ../data/processed/gaps_v4.jsonl \
                 ../data/processed/gaps_d4eb6a1d.jsonl \
        --out ../data/processed/gaps_union.jsonl [--min-run-hits 2] [--stable-only]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Sequence

from app.core.pipeline.io import read_jsonl, write_jsonl
from app.services.research_pipeline import merge_gap_runs


def load_run(path: str) -> List[Dict[str, Any]]:
    return [g for g in read_jsonl(path) if g.get("record") != "meta" and g.get("gap_statement")]


def consensus_table(gaps: Sequence[Dict[str, Any]], runs: int) -> List[str]:
    """Baris teks distribusi k/n: berapa gap muncul di tepat k run."""
    dist = Counter(int(g.get("run_hits") or 0) for g in gaps)
    total = max(1, len(gaps))
    lines = [f"{'k (run)':>8} | {'gap':>6} | {'%':>6}"]
    lines.append("-" * 26)
    for k in range(runs, 0, -1):
        n = dist.get(k, 0)
        lines.append(f"{k:>5}/{runs:<2} | {n:>6} | {100 * n / total:>5.1f}%")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Union gap lintas run dengan frekuensi k/n.")
    ap.add_argument("--inputs", nargs="+", required=True,
                    help="Berkas gaps_*.jsonl, satu per run (urutan menentukan run_ids).")
    ap.add_argument("--out", required=True, help="gaps_union.jsonl keluaran.")
    ap.add_argument("--min-run-hits", type=int, default=0,
                    help="Ambang 'stabil'; 0 = bawaan ceil(2n/3) (3 run -> 2).")
    ap.add_argument("--stable-only", action="store_true",
                    help="Tulis hanya gap stabil (bawaan: semua gap, ditandai stable=true/false).")
    args = ap.parse_args(argv)

    runs = [load_run(p) for p in args.inputs]
    unique, consensus = merge_gap_runs(runs, min_run_hits=args.min_run_hits)
    written = [g for g in unique if g.get("stable")] if args.stable_only else unique

    meta = {
        "record": "meta",
        "diekspor_pada": datetime.now().isoformat(timespec="seconds"),
        "sumber_run": list(args.inputs),
        "jumlah_gap_per_run": [len(r) for r in runs],
        "jumlah_gap_union": len(unique),
        "jumlah_gap_stabil": consensus["stable"],
        "jumlah_jurnal_bergap": len({g.get("source") for g in unique}),
        "konsensus": consensus,
        "catatan": ("Union gap lintas run; run_hits/run_total = kemunculan, stable = "
                    f"run_hits >= {consensus['min_run_hits']}. Kunci gabungan = "
                    "(source, gap_statement.lower()) — sama dengan tahap gap_mining."),
    }
    write_jsonl(args.out, [meta] + written)

    print(f"Run        : {consensus['runs']} berkas, gap per run = {[len(r) for r in runs]}")
    print(f"Union      : {len(unique)} gap unik dari "
          f"{meta['jumlah_jurnal_bergap']} jurnal")
    print(f"Stabil     : {consensus['stable']} (>= {consensus['min_run_hits']} run) · "
          f"tidak stabil {consensus['unstable']}")
    print(f"Jaccard antar-run (rata-rata pasangan): {consensus['jaccard_between_runs']}")
    print()
    print("\n".join(consensus_table(unique, consensus["runs"])))
    print(f"\n[ditulis ke {args.out}: {len(written)} gap"
          + (" stabil saja" if args.stable_only else "") + "]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
