#!/usr/bin/env python3
"""
Gap-detection Precision / Recall / F1 against a gold-standard benchmark.

The expert-evaluation metric EAR is precision-like: it tells you how many of the
*produced* indicators are genuine, but NOT how many real gaps were *missed*.
This evaluator closes that gap. Given a curated gold set of gaps, it matches the
system's detected indicators to the gold gaps by semantic similarity (the
project's own embedding model) and reports Precision, Recall, and F1 — and,
crucially, lets you compare modes (full vs linear-baseline vs no-rule-engine vs
nli/no-nli) on the SAME gold set.

Gold format (JSON) — see build_gap_benchmark.py:
    {"gold_gaps": [
        {"id": "g1", "statement": "...", "topic_key": "T1", "verified": true},
        ...
    ]}
Only entries with verified == true are scored.

Usage (from backend/):
    python experiments/evaluate_gaps.py \
        --gold experiments/gap_benchmark.json \
        --results experiments/results/experiment_full_llama3.2_latest.json \
        --results experiments/results/experiment_linear-baseline_llama3.2_latest.json \
        --threshold 0.5
"""

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BACKEND_DIR / "experiments" / "results"
for _p in (str(BACKEND_DIR), str(BACKEND_DIR / "experiments")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gap_matching import evaluate as evaluate_emb, prf  # noqa: E402


def load_gold(path: Path):
    data = json.loads(path.read_text())
    gaps = [g for g in data.get("gold_gaps", []) if g.get("verified")]
    return gaps


def load_detected(path: Path):
    """Flatten detected indicators with topic, from an experiment result JSON."""
    report = json.loads(path.read_text())
    out = []
    for topic in report.get("phase3_gap_detection", {}).get("topics", []):
        tkey = topic.get("topic_key", topic.get("topic", "?"))
        for ind in topic.get("indicators", []):
            text = ind.get("description", "")
            if text:
                out.append({"text": text, "topic_key": tkey})
    info = report.get("experiment_info", {})
    label = info.get("mode", path.stem)
    return out, label


def get_embedder(model_name: str):
    """Return a function text->vector using sentence-transformers."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)
    return lambda texts: [v.tolist() for v in model.encode(texts, show_progress_bar=False)]


def score(detected, gold, embed, threshold, per_topic):
    """Compute overall (and optional per-topic) PRF for one result set."""
    det_texts = [d["text"] for d in detected]
    gold_texts = [g["statement"] for g in gold]
    det_emb = embed(det_texts) if det_texts else []
    gold_emb = embed(gold_texts) if gold_texts else []

    overall, _ = evaluate_emb(det_emb, gold_emb, threshold)
    result = {"overall": overall.to_dict()}

    if per_topic:
        topics = sorted({g.get("topic_key") for g in gold if g.get("topic_key")})
        per = {}
        for tk in topics:
            d_idx = [i for i, d in enumerate(detected) if d["topic_key"] == tk]
            g_idx = [i for i, g in enumerate(gold) if g.get("topic_key") == tk]
            de = [det_emb[i] for i in d_idx]
            ge = [gold_emb[i] for i in g_idx]
            p, _ = evaluate_emb(de, ge, threshold)
            per[tk] = p.to_dict()
        result["per_topic"] = per
    return result


def render(all_scores, threshold, n_gold) -> str:
    lines = [
        "# Evaluasi Gap vs Gold Standard — Precision / Recall / F1",
        f"\nThreshold kemiripan: **{threshold}** · Gold gaps (verified): **{n_gold}**\n",
        "| Mode/Result | Precision | Recall | F1 | TP | FP | FN | #Detected | #Gold |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for label, sc in all_scores:
        o = sc["overall"]
        lines.append(
            f"| `{label}` | {o['precision']} | **{o['recall']}** | **{o['f1']}** "
            f"| {o['tp']} | {o['fp']} | {o['fn']} | {o['n_detected']} | {o['n_gold']} |"
        )
    lines += [
        "",
        "_**Recall** = berapa banyak gap yang BENAR-BENAR ada (gold) berhasil "
        "terdeteksi — metrik yang tidak bisa diberikan EAR. Precision = berapa "
        "banyak indikator terdeteksi yang cocok dengan gap gold. Pencocokan: "
        "kemiripan kosinus embedding ≥ threshold, greedy satu-ke-satu._",
    ]

    # Per-topic detail (if present)
    if all_scores and "per_topic" in all_scores[0][1]:
        lines += ["", "## Per Topik"]
        for label, sc in all_scores:
            if "per_topic" not in sc:
                continue
            lines += [f"\n### `{label}`", "",
                      "| Topik | Precision | Recall | F1 | TP | FP | FN |",
                      "|---|---|---|---|---|---|---|"]
            for tk, o in sc["per_topic"].items():
                lines.append(f"| {tk} | {o['precision']} | {o['recall']} | {o['f1']} "
                             f"| {o['tp']} | {o['fp']} | {o['fn']} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gap Precision/Recall/F1 vs gold benchmark.")
    parser.add_argument("--gold", required=True, help="Gold benchmark JSON")
    parser.add_argument("--results", action="append", required=True,
                        help="Experiment result JSON (repeatable to compare modes)")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Cosine similarity match threshold (default 0.5)")
    parser.add_argument("--model", default=None, help="Embedding model (default: project config)")
    parser.add_argument("--per-topic", action="store_true", help="Also report per-topic PRF")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    gold = load_gold(Path(args.gold))
    if not gold:
        print("No verified gold gaps found (need entries with \"verified\": true).")
        return 1

    if args.model is None:
        from app.utils.config_loader import get_config
        args.model = get_config().vector_db.embedding_model
    embed = get_embedder(args.model)

    all_scores = []
    for r in args.results:
        rp = Path(r)
        if not rp.exists():
            rp = RESULTS_DIR / rp.name
        detected, label = load_detected(rp)
        all_scores.append((label, score(detected, gold, embed, args.threshold, args.per_topic)))

    md = render(all_scores, args.threshold, len(gold))
    out = Path(args.output) if args.output else RESULTS_DIR / "gap_prf_evaluation.md"
    out.write_text(md)
    out.with_suffix(".json").write_text(json.dumps(
        {"threshold": args.threshold, "n_gold": len(gold),
         "scores": {label: sc for label, sc in all_scores}}, indent=2))
    print(f"Evaluasi tersimpan: {out}\n")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
