"""Automated check: 100% of gap_statements are verbatim in their source chunks.

TAHAP 2 kriteria selesai #2. Exits non-zero if any gap is not verbatim-grounded,
and reports how many explicit gaps the old regex-only approach would have missed
(kriteria #3).

Usage (from ``backend``):
    python -m experiments.verify_gaps --gaps ../data/processed/gaps_d4eb6a1d.jsonl \
        --chunks ../data/processed/chunks_new.jsonl
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from typing import Dict, List

from app.core.gap_mining.candidates import matched_phrases
from app.core.gap_mining.verify import verify_gap_statement
from app.core.gap_detection.quote_grounding import QUOTE_MATCH_THRESHOLD
from app.core.pipeline.io import read_jsonl


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verify gap_statements are verbatim.")
    ap.add_argument("--gaps", required=True)
    ap.add_argument("--chunks", required=True)
    ap.add_argument("--threshold", type=float, default=QUOTE_MATCH_THRESHOLD)
    args = ap.parse_args(argv)

    chunks = [c for c in read_jsonl(args.chunks) if c.get("record") == "chunk"]
    by_id: Dict[str, Dict] = {c["chunk_id"]: c for c in chunks if c.get("chunk_id")}
    by_source: Dict[str, List[Dict]] = defaultdict(list)
    for c in chunks:
        by_source[c.get("source")].append(c)

    gaps = [g for g in read_jsonl(args.gaps) if g.get("record") != "meta"]
    if not gaps:
        print("No gaps to verify.")
        return 1

    failures = []
    for g in gaps:
        ev = g.get("evidence_chunk_ids") or []
        texts = [by_id[i]["text"] for i in ev if i in by_id]
        if not texts:
            texts = [c.get("text", "") for c in by_source.get(g.get("source"), [])]
        score = verify_gap_statement(g.get("gap_statement", ""), "\n".join(texts))
        if score < args.threshold:
            failures.append((g.get("source"), score, g.get("gap_statement", "")[:60]))

    verified = len(gaps) - len(failures)
    pct = 100.0 * verified / len(gaps)
    print("=" * 66)
    print(f"GAP VERBATIM VERIFICATION  (threshold {args.threshold})")
    print("=" * 66)
    print(f"gaps:                 {len(gaps)}")
    print(f"journals with gaps:   {len({g.get('source') for g in gaps})}")
    print(f"verbatim-verified:    {verified}/{len(gaps)}  ({pct:.1f}%)")

    # kriteria #3: explicit gaps the old regex-only approach would miss.
    explicit = [g for g in gaps if g.get("gap_type") == "explicit_future_work"]
    missed_by_regex = [
        g for g in explicit
        if not matched_phrases(g.get("gap_statement", ""))
    ]
    print(f"explicit gaps:        {len(explicit)}")
    print(f"  ...missed by regex: {len(missed_by_regex)} (found only via LLM/section targeting)")
    print("=" * 66)

    if failures:
        print("FAIL — ungrounded gaps:")
        for src, score, stmt in failures[:10]:
            print(f"   [{src}] score={score:.2f} :: {stmt}...")
        return 1
    print("PASS — 100% of gap_statements are verbatim in source chunks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
