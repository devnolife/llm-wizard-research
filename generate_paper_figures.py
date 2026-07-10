#!/usr/bin/env python3
"""Generate publication-quality figures for the IEEE paper & thesis (BAB IV).

Reads multi-run experiment JSONs from backend/experiments/results/ and writes
300-dpi PNG + PDF figures to paper_figures/.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "backend" / "experiments" / "results"
OUT = ROOT / "paper_figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.titlesize": 9,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "figure.dpi": 300,
})

MODES = ["full", "no-rule-engine", "linear-baseline", "nli", "no-nli"]
MODEL = "llama3.2_latest"


def load_runs(mode):
    runs = []
    for i in (1, 2, 3):
        p = RESULTS / f"experiment_{mode}_{MODEL}.run{i}.json"
        if p.exists():
            runs.append(json.load(open(p)))
    return runs


def indicators_of(run):
    ph3 = run.get("phase3_gap_detection", {})
    topics = ph3.get("topics", [])
    if isinstance(topics, dict):
        topics = list(topics.values())
    out = []
    for t in topics:
        out.extend(t.get("indicators", t.get("gap_indicators", [])))
    return out or ph3.get("gap_indicators", [])


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", dpi=300)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}.png / .pdf")


# ── Fig 1: System architecture block diagram ─────────────────────────
def fig1_architecture():
    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    ax.axis("off")

    def box(x, y, w, h, label, fc="#f0f0f0", fontsize=8, weight="normal"):
        r = plt.Rectangle((x, y), w, h, fc=fc, ec="black", lw=0.8, zorder=2)
        ax.add_patch(r)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
                fontsize=fontsize, weight=weight, zorder=3, wrap=True)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", lw=0.9))

    # Phase pipeline (top row)
    phases = [
        ("Phase 1\nIngestion\n(PDF \u2192 chunks \u2192\nChromaDB)", "#e8eef7"),
        ("Phase 2\nFact Extraction\n(LLM + patterns \u2192\nSPO Fact Table)", "#e8f7ec"),
        ("Phase 3\nAgentic Analysis\n(LangGraph loop)", "#fdf3e3"),
        ("Phase 4\nLogical Validation\n(Rule Engine\nF1\u2013F3, C1\u2013C3, K1\u2013K3)", "#f7e8e8"),
    ]
    x = 0.02
    for label, color in phases:
        box(x, 0.55, 0.21, 0.38, label, fc=color, fontsize=7.5)
        if x > 0.02:
            arrow(x - 0.025, 0.74, x, 0.74)
        x += 0.235

    # Agentic loop (bottom)
    loop = ["Observe", "Think", "Act", "Evaluate"]
    lx = 0.28
    for i, step in enumerate(loop):
        box(lx, 0.08, 0.1, 0.16, step, fc="#fff8dc", fontsize=8)
        if i < 3:
            arrow(lx + 0.1, 0.16, lx + 0.13, 0.16)
        lx += 0.13
    # loop-back arrow evaluate -> think (arc below the boxes)
    ax.annotate("", xy=(0.46, 0.06), xytext=(0.72, 0.06),
                arrowprops=dict(arrowstyle="->", lw=0.8,
                                connectionstyle="arc3,rad=-0.3"))
    ax.text(0.59, -0.08, "revise (max 3 iterations)", ha="center", fontsize=7, style="italic")
    # connect loop to phase 3
    arrow(0.545, 0.28, 0.545, 0.52)

    # Output box
    box(0.79, 0.08, 0.19, 0.3, "Gap indicators\n+ verdicts (PASS/\nFLAG/REJECT)\n+ reasoning trace", fc="#eee6f5", fontsize=7.5)
    arrow(0.955, 0.52, 0.9, 0.4)

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.14, 1)
    save(fig, "fig1_architecture")


# ── Fig 2: Ablation — indicators per mode (mean ± std) ───────────────
def fig2_ablation():
    means, stds, rerr_m, rerr_s = [], [], [], []
    for mode in MODES:
        runs = load_runs(mode)
        counts = [len(indicators_of(r)) for r in runs]
        means.append(np.mean(counts))
        stds.append(np.std(counts, ddof=1) if len(counts) > 1 else 0)
        rerrs = []
        for r in runs:
            rr = r.get("phase4_rule_engine", {}).get("summary", {})
            tot = rr.get("total_evaluated", rr.get("total_validated", rr.get("total", 0)))
            bad = rr.get("flagged", 0) + rr.get("rejected", 0)
            rerrs.append(100 * bad / tot if tot else 0)
        rerr_m.append(np.mean(rerrs) if rerrs else 0)
        rerr_s.append(np.std(rerrs, ddof=1) if len(rerrs) > 1 else 0)

    labels = ["Full", "No rule\nengine", "Linear\nbaseline", "NLI", "No NLI"]
    x = np.arange(len(MODES))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.6))

    ax1.bar(x, means, yerr=stds, capsize=3, color="#7a9cc4", edgecolor="black", lw=0.6)
    ax1.set_xticks(x, labels)
    ax1.set_ylabel("Gap indicators per run")
    ax1.set_title("(a) Detected indicators (mean \u00b1 SD, n=3)")

    ax2.bar(x, rerr_m, yerr=[np.minimum(rerr_m, rerr_s), rerr_s], capsize=3,
            color="#c48a7a", edgecolor="black", lw=0.6)
    ax2.set_xticks(x, labels)
    ax2.set_ylabel("RERR (%)")
    ax2.set_ylim(bottom=0)
    ax2.set_title("(b) Rule-engine rejection rate")

    fig.tight_layout()
    save(fig, "fig2_ablation")


# ── Fig 3: H9 — NLI vs no-NLI ────────────────────────────────────────
def fig3_h9():
    data = {}
    for mode in ("nli", "no-nli"):
        runs = load_runs(mode)
        counts = [len(indicators_of(r)) for r in runs]
        confs = []
        for r in runs:
            gis = indicators_of(r)
            cs = [g.get("confidence", 0) for g in gis]
            confs.append(np.mean(cs) if cs else 0)
        data[mode] = (counts, confs)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.0, 2.5))
    labels = ["With NLI", "LLM-only\n(no NLI)"]
    colors = ["#7a9cc4", "#c4b57a"]

    for ax, idx, ylabel, title in (
        (ax1, 0, "Indicators per run", "(a) Indicator count"),
        (ax2, 1, "Mean confidence", "(b) Confidence"),
    ):
        vals = [data["nli"][idx], data["no-nli"][idx]]
        m = [np.mean(v) for v in vals]
        s = [np.std(v, ddof=1) for v in vals]
        ax.bar([0, 1], m, yerr=s, capsize=3, color=colors, edgecolor="black", lw=0.6, width=0.55)
        for i, v in enumerate(vals):
            ax.scatter([i] * len(v), v, color="black", s=8, zorder=3)
        ax.set_xticks([0, 1], labels)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
    ax2.set_ylim(0.7, 0.8)

    fig.tight_layout()
    save(fig, "fig3_h9_nli")


# ── Fig 4: Adversarial validation — confidence before/after ─────────
def fig4_adversarial():
    run = json.load(open(RESULTS / f"experiment_full_{MODEL}.run1.json"))
    adv = run.get("phase5_adversarial", {})
    cases = adv.get("cases", [])
    ids = [c["case_id"] for c in cases]
    before = [c["original_confidence"] for c in cases]
    after = [c["adjusted_confidence"] for c in cases]
    verdicts = [c["actual_verdict"] for c in cases]

    x = np.arange(len(ids))
    w = 0.35
    fig, ax = plt.subplots(figsize=(5.5, 2.6))
    ax.bar(x - w / 2, before, w, label="Before validation", color="#b0b0b0", edgecolor="black", lw=0.6)
    vc = {"REJECT": "#c0504d", "FLAG": "#e8b84b", "PASS": "#77a86e"}
    ax.bar(x + w / 2, after, w, label="After validation",
           color=[vc[v] for v in verdicts], edgecolor="black", lw=0.6)
    for i, v in enumerate(verdicts):
        ax.text(i + w / 2, after[i] + 0.02, v, ha="center", fontsize=6.5, rotation=0)
    ax.set_xticks(x, ids, fontsize=7.5)
    ax.set_ylabel("Confidence")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right")
    fig.tight_layout()
    save(fig, "fig4_adversarial")


# ── Fig 5: Gap type distribution (full mode, 3 runs pooled) ─────────
def fig5_gap_types():
    counts = {"FRAGMENTATION": 0, "INCONSISTENCY": 0, "INCOMPLETENESS": 0}
    for r in load_runs("full"):
        for gi in indicators_of(r):
            t = str(gi.get("indicator_type", gi.get("type", ""))).upper()
            for k in counts:
                if k in t:
                    counts[k] += 1
    labels = ["Fragmentation", "Inconsistency", "Incompleteness"]
    vals = [counts["FRAGMENTATION"], counts["INCONSISTENCY"], counts["INCOMPLETENESS"]]
    fig, ax = plt.subplots(figsize=(3.4, 2.8))
    wedges, _, autotexts = ax.pie(
        vals, labels=labels, autopct=lambda p: f"{p:.1f}%\n(n={int(round(p*sum(vals)/100))})",
        colors=["#7a9cc4", "#e8b84b", "#c0504d"],
        wedgeprops=dict(edgecolor="black", lw=0.6), textprops=dict(fontsize=8))
    fig.tight_layout()
    save(fig, "fig5_gap_types")


if __name__ == "__main__":
    print(f"Reading results from {RESULTS}")
    fig1_architecture()
    fig2_ablation()
    fig3_h9()
    fig4_adversarial()
    fig5_gap_types()
    print(f"Done. Figures in {OUT}/")
