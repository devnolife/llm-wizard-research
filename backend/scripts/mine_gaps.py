"""CLI: mine research gaps from a chunks JSONL -> gaps_<jobid>.jsonl (TAHAP 2).

Pipeline: L1 section+phrase candidates -> L2 LLM structured extraction (Copilot)
-> verbatim verification -> dedup -> write gaps JSONL.

Usage (from ``backend``):
    python -m scripts.mine_gaps --chunks ../data/processed/chunks_new.jsonl \
        --out ../data/processed/gaps_d4eb6a1d.jsonl

    python -m scripts.mine_gaps --chunks new.jsonl --out gaps.jsonl --limit 20
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

from dotenv import load_dotenv

load_dotenv()  # pick up COPILOTD_URL etc. for the CLI process

from app.core.gap_mining.candidates import matched_phrases, select_candidates, with_context
from app.core.gap_mining.extractor import extract_gaps_from_candidate
from app.core.gap_mining.verify import verify_gaps
from app.core.pipeline.io import read_jsonl, write_jsonl


def _dedup_gaps(gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for g in gaps:
        key = (g.get("source"), g.get("gap_statement", "").strip().lower())
        h = hashlib.sha1(str(key).encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        out.append(g)
    return out


def _regex_baseline(chunks: List[Dict[str, Any]]) -> int:
    """Count chunks the OLD regex-only approach would flag (for comparison)."""
    return sum(1 for c in chunks if not c.get("is_reference") and matched_phrases(c.get("text", "")))


def mine(chunks_path: str, out_path: str, job_id: str, limit: int = 0, workers: int = 4):
    chunks = [c for c in read_jsonl(chunks_path) if c.get("record") == "chunk"]
    by_source: Dict[str, List[Dict]] = defaultdict(list)
    for c in chunks:
        by_source[c.get("source")].append(c)

    candidates = select_candidates(chunks)
    if limit:
        candidates = candidates[:limit]
    logger.info(
        f"{len(chunks)} chunks -> {len(candidates)} candidates "
        f"(regex-only baseline would flag {_regex_baseline(chunks)} chunks)"
    )

    t0 = time.time()
    all_gaps: List[Dict[str, Any]] = []

    def _work(cand):
        ctx = with_context(cand, by_source)
        return extract_gaps_from_candidate(cand, ctx)

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_work, c): c for c in candidates}
        for fut in as_completed(futures):
            done += 1
            try:
                gaps = fut.result()
            except Exception as e:
                logger.warning(f"candidate failed: {e}")
                gaps = []
            all_gaps.extend(gaps)
            if done % 20 == 0 or done == len(candidates):
                logger.info(f"  extracted {done}/{len(candidates)} candidates, {len(all_gaps)} raw gaps")

    # Verify verbatim grounding, then dedup.
    raw_path = out_path + ".raw.jsonl"
    write_jsonl(raw_path, all_gaps)  # cache raw gaps for cheap re-verification
    grounded = verify_gaps(all_gaps, by_source)
    logger.info(f"grounding: {len(grounded)}/{len(all_gaps)} gaps verbatim-verified")
    gaps = _dedup_gaps(grounded)

    journals_with_gaps = len({g["source"] for g in gaps})
    meta = {
        "record": "meta", "job_id": job_id,
        "diekspor_pada": datetime.now().isoformat(timespec="seconds"),
        "jumlah_gap": len(gaps), "jumlah_jurnal_bergap": journals_with_gaps,
        "jumlah_kandidat": len(candidates),
        "catatan": "Gap terstruktur; gap_statement diverifikasi verbatim di chunk sumber.",
    }
    write_jsonl(out_path, [meta] + gaps)
    logger.info(
        f"Wrote {len(gaps)} gaps from {journals_with_gaps} journals to {out_path} "
        f"in {time.time() - t0:.1f}s"
    )
    return {"gaps": len(gaps), "journals": journals_with_gaps, "candidates": len(candidates)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mine research gaps from chunks JSONL.")
    ap.add_argument("--chunks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--job-id", default=None)
    ap.add_argument("--limit", type=int, default=0, help="Cap candidates (for a quick run).")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)

    job_id = args.job_id or "job"
    mine(args.chunks, args.out, job_id, limit=args.limit, workers=args.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
