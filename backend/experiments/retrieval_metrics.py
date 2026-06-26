"""
Pure ranking-quality metrics for retrieval evaluation (#6).

Dependency-free so they are unit-testable in isolation. Each function takes a
ranked list of relevance labels (1 = relevant, 0 = not) in the order the items
were retrieved, plus the total number of relevant items where needed.
"""

from __future__ import annotations

import math
from typing import List, Sequence


def reciprocal_rank(rels: Sequence[int]) -> float:
    """RR = 1 / rank of the first relevant item (0 if none retrieved)."""
    for i, r in enumerate(rels, start=1):
        if r:
            return 1.0 / i
    return 0.0


def recall_at_k(rels: Sequence[int], total_relevant: int, k: int) -> float:
    """Fraction of all relevant items that appear in the top-k."""
    if total_relevant <= 0:
        return 0.0
    return sum(1 for r in rels[:k] if r) / total_relevant


def precision_at_k(rels: Sequence[int], k: int) -> float:
    """Fraction of the top-k that are relevant."""
    if k <= 0:
        return 0.0
    topk = rels[:k]
    return sum(1 for r in topk if r) / min(k, len(topk)) if topk else 0.0


def dcg_at_k(rels: Sequence[int], k: int) -> float:
    """Discounted Cumulative Gain with binary relevance."""
    return sum(r / math.log2(i + 1) for i, r in enumerate(rels[:k], start=1))


def ndcg_at_k(rels: Sequence[int], total_relevant: int, k: int) -> float:
    """
    Normalized DCG@k (binary relevance).

    IDCG is the DCG of the ideal ranking (min(total_relevant, k) ones first).
    """
    dcg = dcg_at_k(rels, k)
    ideal_ones = min(total_relevant, k)
    idcg = dcg_at_k([1] * ideal_ones, k)
    return dcg / idcg if idcg > 0 else 0.0


def aggregate(per_query: List[dict]) -> dict:
    """Mean of each metric across a list of per-query metric dicts."""
    if not per_query:
        return {}
    keys = per_query[0].keys()
    return {k: round(sum(q[k] for q in per_query) / len(per_query), 4) for k in keys}
