#!/usr/bin/env python3
"""
Retrieval-quality evaluation (#6) + cross-lingual breakdown (#7).

Justifies the two-stage retrieval design empirically: it measures whether the
cross-encoder reranker improves ranking over the bi-encoder alone, using an
automatic *known-item* protocol that needs no human labels — a query derived
from one chunk should retrieve other chunks of the SAME source paper.

Metrics (binary relevance, relevant = same source paper): MRR, nDCG@k,
Recall@k, P@k. With --by-language, results are split by the query paper's
language (Indonesian vs English) to test whether the multilingual embedding
generalizes cross-lingually.

Usage (from backend/):
    python experiments/evaluate_retrieval.py --n 40 --k 10 --by-language
"""

import argparse
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
for _p in (str(BACKEND_DIR), str(BACKEND_DIR / "experiments")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from retrieval_metrics import (  # noqa: E402
    reciprocal_rank, recall_at_k, precision_at_k, ndcg_at_k, aggregate,
)

# Minimal stop-word sets for a dependency-free ID/EN language guess.
_ID_WORDS = {"yang", "dan", "dengan", "untuk", "pada", "dari", "ini", "itu",
             "adalah", "tidak", "dalam", "akan", "atau", "sebagai", "oleh",
             "penelitian", "metode", "hasil", "data", "menggunakan", "dapat"}
_EN_WORDS = {"the", "and", "for", "with", "this", "that", "from", "are", "was",
             "which", "have", "using", "based", "results", "method", "model",
             "between", "such", "these", "their", "where"}


def detect_language(text: str) -> str:
    """Heuristic ID/EN detection by stop-word frequency."""
    tokens = re.findall(r"[a-zA-Z]+", (text or "").lower())
    if not tokens:
        return "unknown"
    id_hits = sum(1 for t in tokens if t in _ID_WORDS)
    en_hits = sum(1 for t in tokens if t in _EN_WORDS)
    if id_hits == en_hits == 0:
        return "unknown"
    return "id" if id_hits > en_hits else "en"


def build_queries(store, n: int, seed: int):
    """Known-item queries: (query_text, query_chunk_id, source, n_relevant, lang)."""
    docs = store.get_all_documents()
    by_source = defaultdict(list)
    for d in docs:
        src = (d.metadata or {}).get("source", "?")
        by_source[src].append(d)
    # Only sources with >=2 chunks can have a "relevant" set beyond the query.
    eligible = {s: ds for s, ds in by_source.items() if len(ds) >= 3}
    rng = random.Random(seed)
    sources = list(eligible)
    rng.shuffle(sources)

    queries = []
    for src in sources:
        chunks = eligible[src]
        qd = rng.choice(chunks)
        # Query = a leading slice of the chunk (a realistic short query).
        qtext = re.sub(r"\s+", " ", qd.content)[:160].strip()
        if len(qtext) < 30:
            continue
        n_rel = len(chunks) - 1  # other chunks of same source
        queries.append({
            "text": qtext, "id": qd.id, "source": src,
            "n_relevant": n_rel, "lang": detect_language(qd.content),
        })
        if len(queries) >= n:
            break
    return queries


def relevances(results, query, k):
    """Binary relevance list (same source), excluding the query chunk itself."""
    rels = []
    for r in results:
        if r.document.id == query["id"]:
            continue
        same = (r.document.metadata or {}).get("source") == query["source"]
        rels.append(1 if same else 0)
        if len(rels) >= k:
            break
    return rels


def per_query_metrics(rels, n_relevant, k):
    return {
        "mrr": reciprocal_rank(rels),
        f"ndcg@{k}": ndcg_at_k(rels, n_relevant, k),
        f"recall@{k}": recall_at_k(rels, n_relevant, k),
        f"p@{k}": precision_at_k(rels, k),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieval eval (nDCG/MRR/Recall@k) ± reranker.")
    parser.add_argument("--n", type=int, default=40, help="Number of known-item queries")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--pool", type=int, default=50, help="Bi-encoder candidate pool before rerank")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--by-language", action="store_true", help="Split metrics by query language (ID/EN)")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    from app.api.dependencies import get_vector_store, get_reranker
    store = get_vector_store()
    reranker = get_reranker()

    queries = build_queries(store, args.n, args.seed)
    if not queries:
        print("No eligible queries (need sources with >=3 chunks).")
        return 1

    bi_rows, re_rows = [], []
    lang_rows = defaultdict(lambda: {"bi": [], "re": []})

    for q in queries:
        # Bi-encoder ranking
        results = store.search(q["text"], top_k=args.pool)
        bi_rels = relevances(results, q, args.k)
        bi_m = per_query_metrics(bi_rels, q["n_relevant"], args.k)
        bi_rows.append(bi_m)

        # Reranked ranking (cross-encoder over the same candidate pool)
        if reranker is not None and getattr(reranker, "available", False) and results:
            cand = [r for r in results if r.document.id != q["id"]]
            ranked = reranker.rerank(q["text"], [r.document.content for r in cand])
            if ranked is not None:
                reordered = [cand[i] for i, _ in ranked]
                re_rels = relevances(reordered, q, args.k)
            else:
                re_rels = bi_rels
        else:
            re_rels = bi_rels
        re_m = per_query_metrics(re_rels, q["n_relevant"], args.k)
        re_rows.append(re_m)

        if args.by_language:
            lang_rows[q["lang"]]["bi"].append(bi_m)
            lang_rows[q["lang"]]["re"].append(re_m)

    bi_agg, re_agg = aggregate(bi_rows), aggregate(re_rows)
    metric_keys = list(bi_agg.keys())

    lines = [
        "# Evaluasi Retrieval — Bi-encoder vs + Cross-encoder Reranker",
        f"\nProtokol known-item (relevan = chunk dari paper sumber yang sama) · "
        f"queries: {len(queries)} · k={args.k} · pool={args.pool}\n",
        "| Sistem | " + " | ".join(metric_keys) + " |",
        "|---|" + "---|" * len(metric_keys),
        "| Bi-encoder | " + " | ".join(str(bi_agg[m]) for m in metric_keys) + " |",
        "| + Reranker | " + " | ".join(f"**{re_agg[m]}**" for m in metric_keys) + " |",
        "",
        "_Reranker membantu jika nilai (terutama nDCG@k & MRR) naik dibanding "
        "bi-encoder saja — pembenaran empiris two-stage retrieval._",
    ]

    if args.by_language:
        lines += ["", "## Per Bahasa (cross-lingual generalization)"]
        for lang, rows in sorted(lang_rows.items()):
            n_q = len(rows["bi"])
            ba, ra = aggregate(rows["bi"]), aggregate(rows["re"])
            lines += [f"\n### `{lang}` ({n_q} queries)", "",
                      "| Sistem | " + " | ".join(metric_keys) + " |",
                      "|---|" + "---|" * len(metric_keys),
                      "| Bi-encoder | " + " | ".join(str(ba[m]) for m in metric_keys) + " |",
                      "| + Reranker | " + " | ".join(str(ra[m]) for m in metric_keys) + " |"]
        lines += ["", "_Metrik ID yang sebanding dengan EN menunjukkan embedding "
                  "multilingual menggeneralisasi lintas bahasa._"]

    md = "\n".join(lines)
    out = Path(args.output) if args.output else BACKEND_DIR / "experiments" / "results" / "retrieval_eval.md"
    out.write_text(md)
    print(f"Evaluasi retrieval tersimpan: {out}\n")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
