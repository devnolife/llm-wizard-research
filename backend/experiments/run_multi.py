#!/usr/bin/env python3
"""
Multi-Run Statistical Experiment Wrapper — Wizard Research

Runs each experiment configuration N times (LLM output is stochastic even at
temperature 0.3) and reports mean ± std plus significance tests, addressing
the "is the difference significant?" examiner question for H6/H7.

Statistics:
    - Per-config: mean ± std of indicator count, avg confidence, RERR
    - H7: full vs no-rule-engine   (Mann-Whitney U, per-run indicator counts
          and mean confidences)
    - H6: full vs linear-baseline  (same tests)

Usage:
    cd backend
    python experiments/run_multi.py --model llama3.2:latest --runs 3
    python experiments/run_multi.py --model llama3.2:latest --runs 3 --skip-runs   # aggregate only
"""

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

from scipy.stats import mannwhitneyu

BACKEND_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BACKEND_DIR / "experiments" / "results"
MODES = ["full", "no-rule-engine", "linear-baseline"]


def run_name(mode: str, model: str, run_idx: int) -> str:
    slug = model.replace(":", "_").replace("/", "_")
    return f"experiment_{mode}_{slug}.run{run_idx}.json"


def execute_runs(model: str, runs: int, modes: list):
    """Execute run_experiment.py for each mode × run index."""
    for mode in modes:
        for i in range(1, runs + 1):
            out = run_name(mode, model, i)
            if (RESULTS_DIR / out).exists():
                print(f"[skip] {out} already exists")
                continue
            print(f"[run ] mode={mode} run={i}/{runs} → {out}")
            cmd = [
                sys.executable, "experiments/run_experiment.py",
                "--mode", mode, "--model", model,
                "--skip-ingest", "--output", out,
            ]
            result = subprocess.run(cmd, cwd=BACKEND_DIR)
            if result.returncode != 0:
                print(f"[FAIL] mode={mode} run={i} exited {result.returncode}")
                sys.exit(1)


def collect_metrics(model: str, runs: int, modes: list) -> dict:
    """Load per-run metrics for each mode."""
    data = {}
    for mode in modes:
        per_run = []
        for i in range(1, runs + 1):
            path = RESULTS_DIR / run_name(mode, model, i)
            if not path.exists():
                continue
            report = json.loads(path.read_text())
            m = report.get("overall_metrics", {})
            topics = report.get("phase3_gap_detection", {}).get("topics", [])
            confidences = []
            for t in topics:
                confidences.extend(t.get("confidence_scores", []))
            per_run.append({
                "indicators": m.get("total_gap_indicators", 0),
                "avg_confidence": m.get("avg_confidence", 0),
                "facts": m.get("total_facts_extracted", 0),
                "rerr": m.get("rule_engine_rejection_rate_RERR"),
                "confidences": confidences,
            })
        data[mode] = per_run
    return data


def mean_std(values: list) -> str:
    if not values:
        return "—"
    if len(values) == 1:
        return f"{values[0]:.3g}"
    return f"{statistics.mean(values):.3g} ± {statistics.stdev(values):.2g}"


def mwu(sample_a: list, sample_b: list):
    """Mann-Whitney U; returns (U, p) or None when insufficient data."""
    if len(sample_a) < 2 or len(sample_b) < 2:
        return None
    if len(set(sample_a + sample_b)) == 1:  # identical values → undefined
        return None
    u, p = mannwhitneyu(sample_a, sample_b, alternative="two-sided")
    return float(u), float(p)


def aggregate(model: str, data: dict) -> str:
    lines = [f"## Statistik Multi-Run — model {model}", ""]

    # Per-config summary
    lines += [
        "| Mode | n run | Indikator (mean±std) | Avg Conf (mean±std) | Fakta SPO (mean±std) | RERR % (mean±std) |",
        "|---|---|---|---|---|---|",
    ]
    for mode, runs in data.items():
        if not runs:
            lines.append(f"| {mode} | 0 | — | — | — | — |")
            continue
        lines.append(
            f"| {mode} | {len(runs)} "
            f"| {mean_std([r['indicators'] for r in runs])} "
            f"| {mean_std([r['avg_confidence'] for r in runs])} "
            f"| {mean_std([r['facts'] for r in runs])} "
            f"| {mean_std([r['rerr'] for r in runs if r['rerr'] is not None])} |"
        )

    # Hypothesis tests on pooled per-indicator confidences
    lines += ["", "### Uji Signifikansi (Mann-Whitney U, two-sided)", ""]
    lines += ["| Perbandingan | Hipotesis | Variabel | U | p-value | Signifikan (α=0.05) |",
              "|---|---|---|---|---|---|"]

    comparisons = [
        ("full", "no-rule-engine", "H7"),
        ("full", "linear-baseline", "H6"),
    ]
    for mode_a, mode_b, hyp in comparisons:
        runs_a, runs_b = data.get(mode_a, []), data.get(mode_b, [])
        # Variable 1: per-run indicator counts
        counts = mwu([r["indicators"] for r in runs_a], [r["indicators"] for r in runs_b])
        # Variable 2: pooled per-indicator confidences
        conf_a = [c for r in runs_a for c in r["confidences"]]
        conf_b = [c for r in runs_b for c in r["confidences"]]
        confs = mwu(conf_a, conf_b)

        for label, res in [("jumlah indikator/run", counts), ("confidence per indikator", confs)]:
            if res is None:
                lines.append(f"| {mode_a} vs {mode_b} | {hyp} | {label} | — | — | data tidak cukup |")
            else:
                u, p = res
                sig = "ya" if p < 0.05 else "tidak"
                lines.append(f"| {mode_a} vs {mode_b} | {hyp} | {label} | {u:.1f} | {p:.4f} | {sig} |")

    lines += ["", "_Catatan: n run kecil (≈3–5) membatasi power statistik; "
              "p ≥ 0.05 berarti 'belum ada bukti perbedaan', bukan 'terbukti sama'._"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Multi-run experiment wrapper with statistics")
    parser.add_argument("--model", default="llama3.2:latest")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--modes", default=",".join(MODES),
                        help=f"Comma-separated modes (default: {','.join(MODES)})")
    parser.add_argument("--skip-runs", action="store_true",
                        help="Skip execution; aggregate existing run files only")
    args = parser.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    if not args.skip_runs:
        execute_runs(args.model, args.runs, modes)

    data = collect_metrics(args.model, args.runs, modes)
    report_md = aggregate(args.model, data)

    slug = args.model.replace(":", "_").replace("/", "_")
    out = RESULTS_DIR / f"multirun_stats_{slug}.md"
    out.write_text(report_md)
    print(f"\nStatistik tersimpan: {out}\n")
    print(report_md)


if __name__ == "__main__":
    main()
