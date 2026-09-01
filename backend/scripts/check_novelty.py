"""CLI: novelty-check mined gaps against recent literature (TAHAP 3).

Reads gaps_<jobid>.jsonl, queries OpenAlex (>=2024) for each gap, attaches
``novelty_status`` / ``related_recent_papers`` / ``checked_at``, and writes an
enriched gaps file. Responses are cached so re-runs are cheap.

Usage (from ``backend``):
    python -m scripts.check_novelty --gaps ../data/processed/gaps_d4eb6a1d.jsonl \
        --out ../data/processed/gaps_d4eb6a1d_novelty.jsonl
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from datetime import datetime

from loguru import logger

from dotenv import load_dotenv

load_dotenv()

from app.core.gap_mining.novelty import annotate_gaps
from app.core.pipeline.io import read_jsonl, write_jsonl


def main(argv=None):
    ap = argparse.ArgumentParser(description="Novelty-check mined gaps.")
    ap.add_argument("--gaps", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--from-date", default="2024-01-01")
    ap.add_argument("--min-interval", type=float, default=1.0,
                    help="Seconds between OpenAlex requests (raise to avoid 429).")
    ap.add_argument("--max-retries", type=int, default=4,
                    help="Retry budget per query on 429/5xx (lower = fail fast).")
    args = ap.parse_args(argv)

    records = read_jsonl(args.gaps)
    meta = next((r for r in records if r.get("record") == "meta"), None)
    gaps = [r for r in records if r.get("record") != "meta"]
    logger.info(f"novelty-checking {len(gaps)} gaps (recent = from {args.from_date})")

    t0 = time.time()
    enriched = annotate_gaps(gaps, from_date=args.from_date,
                             min_interval=args.min_interval, max_retries=args.max_retries)
    status_counts = Counter(g["novelty_status"] for g in enriched)

    out_meta = dict(meta or {"record": "meta"})
    out_meta.update({
        "novelty_checked_at": datetime.now().isoformat(timespec="seconds"),
        "novelty_from_date": args.from_date,
        "novelty_status_counts": dict(status_counts),
    })
    write_jsonl(args.out, [out_meta] + enriched)
    logger.info(
        f"Wrote {len(enriched)} novelty-checked gaps to {args.out} "
        f"in {time.time() - t0:.1f}s | status={dict(status_counts)}"
    )
    # 100% coverage check (TAHAP 3 kriteria #1).
    missing = sum(1 for g in enriched if not g.get("novelty_status"))
    if missing:
        logger.error(f"{missing} gaps missing novelty_status!")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
