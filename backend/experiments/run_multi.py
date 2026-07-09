#!/usr/bin/env python3
"""
Multi-Run Statistical Experiment Wrapper — Wizard Research

Runs each experiment configuration N times (LLM output is stochastic even at
temperature 0.3) and reports mean ± std plus significance tests, addressing
the "is the difference significant?" examiner question for H6/H7.

Statistics:
    - Per-config: mean ± std of indicator count, avg confidence, RERR
    - Primary tests: Mann-Whitney U on per-run summaries (indicator count/run
      and mean confidence/run) for H6/H7/H9, with Holm-Bonferroni correction.
    - Exploratory tests: pooled per-indicator confidence, reported separately
      with a pseudo-replication caveat for continuity with earlier thesis text.

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
MODES = ["full", "no-rule-engine", "linear-baseline", "nli", "no-nli"]

# Effect-size + CI helpers (complement the Mann-Whitney p-values).
sys.path.insert(0, str(BACKEND_DIR / "experiments"))
from stats_utils import format_effect, holm_bonferroni, per_run_mean_confidences  # noqa: E402


def run_name(mode: str, model: str, run_idx: int) -> str:
    slug = model.replace(":", "_").replace("/", "_")
    return f"experiment_{mode}_{slug}.run{run_idx}.json"


def execute_runs(model: str, runs: int, modes: list, base_seed: int):
    """Execute run_experiment.py for each mode × run index."""
    for mode in modes:
        for i in range(1, runs + 1):
            out = run_name(mode, model, i)
            if (RESULTS_DIR / out).exists():
                print(f"[skip] {out} already exists")
                continue
            seed = base_seed + i
            print(f"[run ] mode={mode} run={i}/{runs} seed={seed} → {out}")
            cmd = [
                sys.executable, "experiments/run_experiment.py",
                "--mode", mode, "--model", model,
                "--skip-ingest", "--output", out,
                "--seed", str(seed),
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
            info = report.get("experiment_info", {})
            m = report.get("overall_metrics", {})
            topics = report.get("phase3_gap_detection", {}).get("topics", [])
            confidences = []
            for t in topics:
                confidences.extend(t.get("confidence_scores", []))
            per_run.append({
                "run_index": i,
                "seed": info.get("seed"),
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


def _comparison_rows(data: dict, exploratory: bool = False) -> list:
    rows = []
    comparisons = [
        ("full", "no-rule-engine", "H7"),
        ("full", "linear-baseline", "H6"),
        ("nli", "no-nli", "H9"),
    ]
    for mode_a, mode_b, hyp in comparisons:
        runs_a, runs_b = data.get(mode_a, []), data.get(mode_b, [])
        if not runs_a or not runs_b:
            continue
        variables = []
        if exploratory:
            variables = [(
                "confidence per indikator (pooled; eksploratori)",
                [c for r in runs_a for c in r["confidences"]],
                [c for r in runs_b for c in r["confidences"]],
            )]
        else:
            variables = [
                ("jumlah indikator/run", [r["indicators"] for r in runs_a], [r["indicators"] for r in runs_b]),
                ("mean confidence/run", per_run_mean_confidences(runs_a), per_run_mean_confidences(runs_b)),
            ]

        for label, sample_a, sample_b in variables:
            res = mwu(sample_a, sample_b)
            u, p = (res if res is not None else (None, None))
            rows.append({
                "comparison": f"{mode_a} vs {mode_b}",
                "hypothesis": hyp,
                "variable": label,
                "u": u,
                "p": p,
                "p_adjusted": None,
                "sample_a": sample_a,
                "sample_b": sample_b,
            })

    adjusted = holm_bonferroni([row["p"] for row in rows])
    for row, p_adj in zip(rows, adjusted):
        row["p_adjusted"] = p_adj
    return rows


def _format_test_rows(rows: list) -> list:
    lines = [
        "| Perbandingan | Hipotesis | Variabel | U | p-value | p Holm | Sig Holm (α=0.05) | Effect size & 95% CI |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        effect = format_effect(row["sample_a"], row["sample_b"], u=row["u"])
        if row["p"] is None:
            lines.append(
                f"| {row['comparison']} | {row['hypothesis']} | {row['variable']} "
                f"| — | — | — | data tidak cukup | {effect} |"
            )
            continue
        sig = "ya" if row["p_adjusted"] is not None and row["p_adjusted"] < 0.05 else "tidak"
        lines.append(
            f"| {row['comparison']} | {row['hypothesis']} | {row['variable']} "
            f"| {row['u']:.1f} | {row['p']:.4f} | {row['p_adjusted']:.4f} | {sig} | {effect} |"
        )
    return lines


def aggregate(model: str, data: dict) -> str:
    lines = [f"## Statistik Multi-Run — model {model}", ""]

    # Per-config summary
    lines += [
        "| Mode | n run | Seeds | Indikator (mean±std) | Avg Conf (mean±std) | Fakta SPO (mean±std) | RERR % (mean±std) |",
        "|---|---|---|---|---|---|---|",
    ]
    for mode, runs in data.items():
        if not runs:
            lines.append(f"| {mode} | 0 | — | — | — | — | — |")
            continue
        seeds = [str(r["seed"]) for r in runs if r.get("seed") is not None]
        lines.append(
            f"| {mode} | {len(runs)} "
            f"| {', '.join(seeds) if seeds else '—'} "
            f"| {mean_std([r['indicators'] for r in runs])} "
            f"| {mean_std([r['avg_confidence'] for r in runs])} "
            f"| {mean_std([r['facts'] for r in runs])} "
            f"| {mean_std([r['rerr'] for r in runs if r['rerr'] is not None])} |"
        )

    primary_rows = _comparison_rows(data, exploratory=False)
    exploratory_rows = _comparison_rows(data, exploratory=True)

    lines += ["", "### Uji Signifikansi Primer — per-run summaries", ""]
    lines += _format_test_rows(primary_rows) if primary_rows else ["_Tidak ada perbandingan dengan data lengkap._"]

    lines += [
        "",
        "### Uji Eksploratori — pooled confidence per indikator",
        "",
        "_Caveat: confidence indikator dipool lintas topik/run hanya untuk kontinuitas analisis; "
        "ini berisiko pseudo-replication karena indikator dari run yang sama tidak independen._",
        "",
    ]
    lines += _format_test_rows(exploratory_rows) if exploratory_rows else ["_Tidak ada perbandingan dengan data lengkap._"]

    lines += ["", "_Effect size: Cliff's δ (negligible/small/medium/large), rank-biserial r, "
              "dan selisih median dengan 95% CI bootstrap. Uji primer memakai satu observasi per run; "
              "n run kecil (default 3) membatasi power, sehingga p ≥ 0.05 berarti 'belum ada bukti perbedaan', "
              "bukan 'terbukti sama'. Holm-Bonferroni diterapkan per tabel pada keluarga perbandingan ablation._"]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Multi-run experiment wrapper with statistics")
    parser.add_argument("--model", default="llama3.2:latest")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42,
                        help="Base seed; per-run seed = base seed + run index")
    parser.add_argument("--modes", default=",".join(MODES),
                        help=f"Comma-separated modes (default: {','.join(MODES)})")
    parser.add_argument("--skip-runs", action="store_true",
                        help="Skip execution; aggregate existing run files only")
    args = parser.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    if not args.skip_runs:
        execute_runs(args.model, args.runs, modes, args.seed)

    data = collect_metrics(args.model, args.runs, modes)
    report_md = aggregate(args.model, data)

    slug = args.model.replace(":", "_").replace("/", "_")
    out = RESULTS_DIR / f"multirun_stats_{slug}.md"
    out.write_text(report_md)
    print(f"\nStatistik tersimpan: {out}\n")
    print(report_md)


if __name__ == "__main__":
    main()
