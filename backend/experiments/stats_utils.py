"""
Statistical helpers for the thesis experiments — effect sizes and confidence
intervals to complement the Mann-Whitney U p-values (H6/H7/H9).

p-values answer "is there a difference?"; effect sizes answer "how large?" and
confidence intervals quantify the uncertainty. Reviewers increasingly require
both. All functions are dependency-light (stdlib + optional scipy) and
non-parametric, matching the small-n, non-normal nature of multi-run LLM output.
"""

from __future__ import annotations

import random
import statistics
from typing import Callable, List, Optional, Tuple


def cliffs_delta(a: List[float], b: List[float]) -> Optional[Tuple[float, str]]:
    """
    Cliff's delta — non-parametric effect size for the dominance of `a` over `b`.

    delta = (#(a>b) - #(a<b)) / (na*nb), ranges [-1, 1].
    Returns (delta, magnitude) or None when a sample is empty.
    Magnitude thresholds (Romano et al., 2006): |d|<0.147 negligible,
    <0.33 small, <0.474 medium, else large.
    """
    if not a or not b:
        return None
    greater = sum(1 for x in a for y in b if x > y)
    less = sum(1 for x in a for y in b if x < y)
    delta = (greater - less) / (len(a) * len(b))
    ad = abs(delta)
    if ad < 0.147:
        mag = "negligible"
    elif ad < 0.33:
        mag = "small"
    elif ad < 0.474:
        mag = "medium"
    else:
        mag = "large"
    return round(delta, 3), mag


def rank_biserial_from_u(u: float, n1: int, n2: int) -> Optional[float]:
    """
    Rank-biserial correlation derived from the Mann-Whitney U statistic.

    r = 1 - 2U/(n1*n2), ranges [-1, 1]. A convenient effect size that pairs
    directly with the U test already computed in run_multi.py.
    """
    if n1 == 0 or n2 == 0:
        return None
    return round(1.0 - (2.0 * u) / (n1 * n2), 3)


def bootstrap_ci_diff(
    a: List[float],
    b: List[float],
    stat: Callable[[List[float]], float] = statistics.median,
    n_boot: int = 5000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Optional[Tuple[float, float, float]]:
    """
    Bootstrap CI for the difference stat(a) - stat(b).

    Returns (point_estimate, ci_low, ci_high) or None when data is insufficient.
    Uses percentile bootstrap; default statistic is the median (robust for the
    small, skewed samples typical of LLM runs).
    """
    if len(a) < 2 or len(b) < 2:
        return None
    rng = random.Random(seed)
    point = stat(a) - stat(b)
    diffs = []
    for _ in range(n_boot):
        ra = [a[rng.randrange(len(a))] for _ in a]
        rb = [b[rng.randrange(len(b))] for _ in b]
        try:
            diffs.append(stat(ra) - stat(rb))
        except statistics.StatisticsError:
            continue
    if not diffs:
        return None
    diffs.sort()
    lo = diffs[int((alpha / 2) * len(diffs))]
    hi = diffs[int((1 - alpha / 2) * len(diffs)) - 1]
    return round(point, 3), round(lo, 3), round(hi, 3)


def format_effect(
    a: List[float],
    b: List[float],
    u: Optional[float] = None,
) -> str:
    """Compact human-readable effect-size + CI string for a Markdown cell."""
    parts = []
    cd = cliffs_delta(a, b)
    if cd is not None:
        parts.append(f"δ={cd[0]} ({cd[1]})")
    if u is not None:
        rb = rank_biserial_from_u(u, len(a), len(b))
        if rb is not None:
            parts.append(f"r={rb}")
    ci = bootstrap_ci_diff(a, b)
    if ci is not None:
        parts.append(f"Δmed={ci[0]} [{ci[1]}, {ci[2]}]")
    return "; ".join(parts) if parts else "—"
