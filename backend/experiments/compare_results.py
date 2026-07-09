#!/usr/bin/env python3
"""
Results Comparator — Wizard Research Experiments

Aggregates experiment result JSONs (from run_experiment.py) into the
comparison tables used in BAB IV:

    Tabel A  Ablation study  — full vs no-rule-engine vs linear-baseline (H6, H7)
    Tabel B  Model comparison — llama3.2 (3B) vs gpt-oss (13B)
    Tabel C  Adversarial rule engine validation (per case)
    Tabel D  Per-topic indicator detail (full mode)

Usage:
    cd backend
    python experiments/compare_results.py                  # all JSONs in results/
    python experiments/compare_results.py --format markdown
"""

import argparse
import json
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
MODES = ["full", "no-rule-engine", "linear-baseline", "nli", "no-nli"]


def load_reports(results_dir: Path) -> list:
    reports = []
    for path in sorted(results_dir.glob("experiment_*.json")):
        name = path.name
        # Skip non-primary results: backups, multi-run replicas, graph seeds
        if any(tag in name for tag in ("backup", ".run", "graph_seed")):
            continue
        try:
            data = json.loads(path.read_text())
            info = data.get("experiment_info", {})
            if info.get("mode") not in MODES:
                continue
            reports.append({"file": path.name, "data": data})
        except (json.JSONDecodeError, OSError):
            continue
    return reports


def fmt(value, suffix=""):
    if value is None:
        return "—"
    return f"{value}{suffix}"


def table_ablation(reports, model_filter=None):
    """Tabel A: ablation per mode (optionally one model)."""
    by_model_mode = {
        (r["data"]["experiment_info"].get("model"), r["data"]["experiment_info"].get("mode")): r
        for r in reports
    }
    models = sorted({r["data"]["experiment_info"].get("model") for r in reports if r["data"]["experiment_info"].get("model")})
    if model_filter:
        models = [m for m in models if m == model_filter]

    rows = []
    for model in models:
        for mode in MODES:
            r = by_model_mode.get((model, mode))
            if not r:
                rows.append({"mode": mode, "model": model, "available": False})
                continue
            info = r["data"]["experiment_info"]
            m = r["data"].get("overall_metrics", {})
            p3 = r["data"].get("phase3_gap_detection", {})
            rows.append({
                "mode": info.get("mode"),
                "model": info.get("model"),
                "available": True,
                "indicators": m.get("total_gap_indicators", 0),
                "facts": m.get("total_facts_extracted", 0),
                "avg_conf": m.get("avg_confidence", 0),
                "avg_adj_conf": m.get("avg_adjusted_confidence", 0),
                "pass": m.get("rule_engine_pass_rate"),
                "rerr": m.get("rule_engine_rejection_rate_RERR"),
                "time_s": round(p3.get("total_time", 0), 1),
            })

    lines = [
        "| Mode | Model | Indikator | Fakta SPO | Avg Conf | Avg Adj Conf | PASS % | RERR % | Waktu Fase-3 (s) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for x in rows:
        if not x["available"]:
            lines.append(
                f"| {x['mode']} | {x['model']} | not available | not available "
                f"| not available | not available | not available | not available | not available |"
            )
            continue
        lines.append(
            f"| {x['mode']} | {x['model']} | {x['indicators']} | {x['facts']} "
            f"| {fmt(x['avg_conf'])} | {fmt(x['avg_adj_conf'])} "
            f"| {fmt(x['pass'])} | {fmt(x['rerr'])} | {x['time_s']} |"
        )
    return "\n".join(lines)


def table_model_comparison(reports):
    """Tabel B: model × full-mode head-to-head."""
    full = [r for r in reports if r["data"]["experiment_info"].get("mode") == "full"]
    lines = [
        "| Metrik | " + " | ".join(r["data"]["experiment_info"]["model"] for r in full) + " |",
        "|---|" + "---|" * len(full),
    ]
    metrics = [
        ("Fakta SPO terekstrak", "total_facts_extracted", ""),
        ("Indikator gap", "total_gap_indicators", ""),
        ("Rata-rata confidence", "avg_confidence", ""),
        ("Rule Engine PASS", "rule_engine_pass_rate", "%"),
        ("RERR (FLAG+REJECT)", "rule_engine_rejection_rate_RERR", "%"),
        ("Akurasi adversarial", "adversarial_accuracy", "%"),
        ("Total waktu pipeline", "total_pipeline_time_seconds", " s"),
    ]
    for label, key, suffix in metrics:
        vals = [fmt(r["data"]["overall_metrics"].get(key), suffix) for r in full]
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    return "\n".join(lines)


def table_adversarial(reports):
    """Tabel C: adversarial cases from the first full-mode report."""
    for r in reports:
        adv = r["data"].get("phase5_adversarial", {})
        cases = adv.get("cases", [])
        if cases:
            lines = [
                f"_Sumber: {r['file']} — akurasi {adv.get('summary', {}).get('accuracy')}%_",
                "",
                "| Kasus | Aturan Diuji | Verdict Diharapkan | Verdict Aktual | Conf Awal → Akhir | Sesuai |",
                "|---|---|---|---|---|---|",
            ]
            for c in cases:
                lines.append(
                    f"| {c['case_id']} | {c['rule_tested']} | {c['expected_verdict']} "
                    f"| {c['actual_verdict']} | {c['original_confidence']:.2f} → "
                    f"{c['adjusted_confidence']:.2f} | {'✓' if c['match'] else '✗'} |"
                )
            return "\n".join(lines)
    return "_Tidak ada data adversarial_"


def table_topic_detail(reports, model=None):
    """Tabel D: per-topic indicators from full mode."""
    target = None
    for r in reports:
        info = r["data"]["experiment_info"]
        if info.get("mode") == "full" and (model is None or info.get("model") == model):
            target = r
            break
    if not target:
        return "_Tidak ada data full mode_"

    lines = [
        f"_Sumber: {target['file']}_",
        "",
        "| Topik | Indikator | Fragmentasi | Inkonsistensi | Ketidaklengkapan | PASS | FLAG | REJECT | Avg Conf |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t in target["data"].get("phase3_gap_detection", {}).get("topics", []):
        if "error" in t:
            continue
        d = t.get("distribution", {})
        v = t.get("verdicts", {})
        lines.append(
            f"| {t.get('topic_key', '?')} | {t.get('total_indicators', 0)} "
            f"| {d.get('FRAGMENTATION', 0)} | {d.get('INCONSISTENCY', 0)} "
            f"| {d.get('INCOMPLETENESS', 0)} | {v.get('PASS', 0)} | {v.get('FLAG', 0)} "
            f"| {v.get('REJECT', 0)} | {fmt(t.get('avg_confidence'))} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare experiment results")
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    args = parser.parse_args()

    reports = load_reports(Path(args.results_dir))
    if not reports:
        print("Tidak ada file hasil eksperimen (experiment_*.json dengan field mode).")
        return

    print(f"Ditemukan {len(reports)} hasil eksperimen:\n")
    for r in reports:
        info = r["data"]["experiment_info"]
        print(f"  - {r['file']}  (mode={info.get('mode')}, model={info.get('model')})")

    print("\n\n## Tabel A — Ablation Study (H6, H7)\n")
    print(table_ablation(reports))

    print("\n\n## Tabel B — Komparasi Model (mode full)\n")
    print(table_model_comparison(reports))

    print("\n\n## Tabel C — Validasi Adversarial Rule Engine\n")
    print(table_adversarial(reports))

    print("\n\n## Tabel D — Detail per Topik (mode full)\n")
    print(table_topic_detail(reports))


if __name__ == "__main__":
    main()
