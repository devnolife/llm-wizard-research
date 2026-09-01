"""Group gap-anchored proposals into cross-journal themes.

Ranking a flat proposal list lets the most verbose paper dominate: on the
35-journal corpus a single source supplied 5 of the top 15 entries, simply
because it stated the most limitations. A theme backed by several journals is
stronger evidence than several restatements from one journal.

Themes are ordered by how many DISTINCT journals support them, with the
project's own composite ``priority_score`` as the tie-breaker. No new composite
formula is invented here — journal coverage and priority stay separate,
reported numbers so the ranking remains auditable.

KNOWN LIMITATION — large themes are not trustworthy yet
-------------------------------------------------------
``cluster_papers`` groups by single-linkage connected components, so one
borderline pair chains two groups together. On the 35-journal corpus the top
theme claimed 7 journals / 33 gaps under a label about legal frameworks, but its
members actually spanned 5 topics: legal statements sat next to "adopt more
advanced tools", "techniques fail error-rate criteria" and "training programmes
are needed". That is a blob of loosely related practice gaps, not one theme, and
its ``journal_support`` therefore overstates the real agreement.

Small themes (2 journals) inspected so far are coherent. Treat this as an
exploration aid: ``journal_support`` on a large theme is an upper bound, not
evidence that N journals stated the same gap. Fixing it means moving off
single-linkage (complete/average linkage) or confining a theme to one topic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ..gap_detection.graph_metrics import cluster_papers

# Calibrated on the 35-journal corpus (358 open proposals, multilingual MiniLM).
# ``cluster_papers`` uses single-linkage components, which chain badly on short
# restatements: 0.60 collapsed 278 of 358 proposals into one blob, while 0.80
# fragmented almost everything into singletons. 0.75 keeps the largest theme at
# 33 members and still surfaces cross-journal ones.
THEME_SIMILARITY_THRESHOLD = 0.75

_TOKEN_RE = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
_STOPWORDS = {
    "yang", "dan", "untuk", "dengan", "pada", "dari", "dalam", "tidak", "adanya",
    "dapat", "akan", "atau", "oleh", "sebagai", "ini", "itu", "the", "and", "for",
    "with", "that", "this", "are", "not", "has", "have", "been", "which", "such",
}


def _terms(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")
            if t.lower() not in _STOPWORDS]


@dataclass
class Theme:
    """A cluster of proposals that restate the same underlying gap."""

    theme_id: int
    label: str
    members: List[Dict[str, Any]] = field(default_factory=list)
    journals: List[str] = field(default_factory=list)
    priority: float = 0.0
    top_priority: float = 0.0
    run_support: float = 0.0
    topics: List[str] = field(default_factory=list)

    @property
    def journal_support(self) -> int:
        return len(self.journals)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "label": self.label,
            "journal_support": self.journal_support,
            "journals": self.journals,
            "size": len(self.members),
            "priority": round(self.priority, 4),
            "top_priority": round(self.top_priority, 4),
            "run_support": round(self.run_support, 2),
            "topics": self.topics,
        }


def _priority_of(proposal: Dict[str, Any]) -> float:
    block = proposal.get("novelty") or {}
    return float(block.get("priority_score") or 0.0)


def build_themes(
    proposals: Sequence[Dict[str, Any]],
    embedder=None,
    threshold: float = THEME_SIMILARITY_THRESHOLD,
) -> List[Theme]:
    """Cluster ranked proposals into themes, ordered by journal coverage.

    ``proposals`` are the output of ``rank_proposals`` (each carrying a
    ``novelty.priority_score``). Returns themes sorted by distinct-journal
    support, then by mean priority.
    """
    if not proposals:
        return []

    keys = [f"p{i}" for i in range(len(proposals))]
    by_key = dict(zip(keys, proposals))
    features = {
        k: _terms(" ".join(str(by_key[k].get(f, "")) for f in ("title", "description")))
        for k in keys
    }
    clusters = cluster_papers(features, embedder=embedder, threshold=threshold).clusters

    themes: List[Theme] = []
    for cid, members in clusters.items():
        items = [by_key[k] for k in members]
        items.sort(key=_priority_of, reverse=True)
        priorities = [_priority_of(p) for p in items]
        journals = sorted({p.get("source") for p in items if p.get("source")})
        supports = [float(p["run_support"]) for p in items if p.get("run_support") is not None]
        topics = sorted({p.get("topic") for p in items if p.get("topic")})
        themes.append(Theme(
            theme_id=cid,
            label=str(items[0].get("title") or "")[:200],
            members=items,
            journals=journals,
            priority=sum(priorities) / len(priorities) if priorities else 0.0,
            top_priority=priorities[0] if priorities else 0.0,
            run_support=sum(supports) / len(supports) if supports else 0.0,
            topics=topics,
        ))

    themes.sort(key=lambda t: (t.journal_support, t.priority), reverse=True)
    for rank, theme in enumerate(themes):
        theme.theme_id = rank
    return themes
