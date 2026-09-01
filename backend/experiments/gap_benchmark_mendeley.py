"""Mendeley Research-Gap-Discovery benchmark for the gap extractor (TAHAP 2 B).

Dataset: Mendeley ``px9xd7tw8n`` — 3,326 arXiv papers with gold
``Limitation`` / ``Research Gap`` / ``Importance`` extracted from abstracts.
The CSV has no abstract text, so we fetch each sampled paper's abstract from the
arXiv API, run OUR extractor on it, and compare our gap to the gold gap via:

  * semantic similarity (sentence-transformers), and
  * an LLM-as-judge 1-5 rubric adapted from FutureGen (optional, --judge).

Usage (from ``backend``):
    python -m experiments.gap_benchmark_mendeley \
        --dataset ../data/benchmarks/mendeley_gaps.csv --sample 25 --judge
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from dotenv import load_dotenv

load_dotenv()

from app.core.gap_mining.extractor import extract_gaps_from_candidate
from app.services import copilot_client

_ARXIV_API = "http://export.arxiv.org/api/query"


def _fetch_abstract(arxiv_id: str, max_retries: int = 4) -> Optional[str]:
    """Fetch an abstract from the arXiv API with 429/backoff (strips version)."""
    base_id = re.sub(r"v\d+$", "", str(arxiv_id).strip())
    for attempt in range(max_retries + 1):
        try:
            r = requests.get(
                _ARXIV_API, params={"id_list": base_id, "max_results": 1}, timeout=40
            )
        except requests.RequestException:
            time.sleep(min(2 ** attempt, 20))
            continue
        if r.status_code == 200:
            m = re.search(r"<summary>(.*?)</summary>", r.text, re.DOTALL)
            if not m:
                return None
            return re.sub(r"\s+", " ", m.group(1)).strip()
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(2 ** attempt, 20))  # arXiv throttles shared IPs
            continue
        return None
    return None


def _similarity_model():
    from sentence_transformers import SentenceTransformer

    # Force CPU: the GPU may be occupied by the LLM service (avoids CUDA OOM).
    # Multilingual model so an Indonesian paraphrase can be compared fairly to an
    # English gold gap (the pipeline uses the same family for retrieval).
    return SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", device="cpu"
    )


def _cos(model, a: str, b: str) -> float:
    import numpy as np

    va, vb = model.encode([a, b])
    denom = (np.linalg.norm(va) * np.linalg.norm(vb)) or 1.0
    return float(np.dot(va, vb) / denom)


_JUDGE_PROMPT = """You compare a MACHINE-extracted research gap to a GROUND-TRUTH \
research gap for the same paper. Score 1-5 how well the machine gap captures the \
same unsolved problem (5=captures it fully/equivalently, 3=partially, 1=unrelated). \
Reply with ONLY the integer.

GROUND TRUTH: "{gold}"
MACHINE: "{machine}"
"""


def _judge(gold: str, machine: str) -> Optional[int]:
    res = copilot_client.generate(
        _JUDGE_PROMPT.format(gold=gold[:600], machine=machine[:600]),
        system="You are a strict evaluator. Reply with a single integer 1-5.",
    )
    if not res:
        return None
    m = re.search(r"[1-5]", res[0])
    return int(m.group(0)) if m else None


def run(dataset: str, sample: int, use_judge: bool, seed: int = 13, out_path=None):
    import pandas as pd

    df = pd.read_csv(dataset)
    df = df[df["Research Gap"].notna() & (df["Research Gap"].str.len() > 20)]
    df = df.sample(n=min(sample, len(df)), random_state=seed).reset_index(drop=True)
    logger.info(f"Benchmarking on {len(df)} Mendeley papers")

    model = _similarity_model()
    rows: List[Dict[str, Any]] = []
    for i, row in df.iterrows():
        gold_gap = str(row["Research Gap"])
        title = str(row["Title"])
        abstract = _fetch_abstract(row["Paper ID"])
        time.sleep(3.0)  # be polite to arXiv (shared IP is throttled)
        if not abstract:
            rows.append({"id": row["Paper ID"], "fetched": False})
            continue
        candidate = {"text": abstract, "paper_title": title, "year": None,
                     "doi": None, "source": str(row["Paper ID"]), "chunk_id": None}
        gaps = extract_gaps_from_candidate(candidate, abstract)
        if not gaps:
            rows.append({"id": row["Paper ID"], "fetched": True, "extracted": False})
            continue
        statement = gaps[0].get("gap_statement") or ""
        paraphrase = gaps[0].get("gap_paraphrase") or ""
        # Best of verbatim (same language as gold) and paraphrase (multilingual
        # model handles ID↔EN), so we do not penalise a good ID paraphrase.
        sim = max(
            _cos(model, gold_gap, statement) if statement else 0.0,
            _cos(model, gold_gap, paraphrase) if paraphrase else 0.0,
        )
        # Judge against the verbatim English statement (same language as gold).
        judge = _judge(gold_gap, statement or paraphrase) if use_judge else None
        rows.append({"id": row["Paper ID"], "fetched": True, "extracted": True,
                     "similarity": sim, "judge": judge})
        if (i + 1) % 5 == 0:
            logger.info(f"  {i + 1}/{len(df)} done")

    fetched = [r for r in rows if r.get("fetched")]
    extracted = [r for r in fetched if r.get("extracted")]
    sims = [r["similarity"] for r in extracted]
    judges = [r["judge"] for r in extracted if r.get("judge") is not None]

    summary = {
        "dataset": dataset,
        "sampled_papers": len(rows),
        "abstracts_fetched": len(fetched),
        "gap_extracted": len(extracted),
        "gap_extracted_pct": round(100 * len(extracted) / max(len(fetched), 1), 1),
        "mean_semantic_sim": round(sum(sims) / len(sims), 3) if sims else None,
        "sim_ge_0.5": sum(1 for s in sims if s >= 0.5) if sims else 0,
        "mean_llm_judge": round(sum(judges) / len(judges), 2) if judges else None,
        "judge_ge_3": sum(1 for j in judges if j >= 3) if judges else 0,
        "n_judged": len(judges),
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }

    print("\n" + "=" * 60)
    print("MENDELEY GAP-EXTRACTION BENCHMARK")
    print("=" * 60)
    print(f"sampled papers:        {summary['sampled_papers']}")
    print(f"abstracts fetched:     {summary['abstracts_fetched']}")
    print(f"gap extracted:         {summary['gap_extracted']}  "
          f"({summary['gap_extracted_pct']}% of fetched)")
    if sims:
        print(f"mean semantic sim:     {summary['mean_semantic_sim']}")
        print(f"  sim >= 0.5:          {summary['sim_ge_0.5']}/{len(sims)}")
    if judges:
        print(f"mean LLM-judge (1-5):  {summary['mean_llm_judge']}")
        print(f"  judge >= 3:          {summary['judge_ge_3']}/{len(judges)}")
    print("=" * 60)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump({"summary": summary, "rows": rows}, fh, ensure_ascii=False, indent=2)
        logger.info(f"Wrote benchmark result to {out_path}")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mendeley gap-extraction benchmark.")
    ap.add_argument("--dataset", required=True, help="Path to mendeley_gaps.csv")
    ap.add_argument("--sample", type=int, default=25)
    ap.add_argument("--judge", action="store_true", help="Also run LLM-as-judge.")
    ap.add_argument("--out", default=None, help="Optional JSON path to save results.")
    args = ap.parse_args(argv)
    run(args.dataset, args.sample, args.judge, out_path=args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
