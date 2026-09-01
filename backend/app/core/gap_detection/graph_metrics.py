"""
Graph-based fragmentation metrics (LeapSpace P6).

The original fragmentation detector had two structural weaknesses:

1. `_cluster_approaches` was not clustering at all — a greedy single pass over
   keyword Jaccard with a hard 0.3 cutoff, so cluster count depended on paper
   ordering and embeddings were never used.
2. `_compute_isolation_score` reduced connectivity to a binary
   "is there any path" ratio, discarding path length, community structure and
   any notion of which *bridge* is worth proposing.

This module supplies the pieces the P6 review identifies as standard practice:
embedding clustering with modularity/silhouette reporting, the classical
literature-based-discovery link-prediction scores, betweenness-based broker
detection, and false-bridge filters.

Formulas (P6):
    CN(x,y)      = |Gamma(x) INTERSECT Gamma(y)|
    Jaccard(x,y) = |Gamma(x) INTERSECT Gamma(y)| / |Gamma(x) UNION Gamma(y)|
    AA(x,y)      = SUM over z of 1 / log(k_z)
    RA(x,y)      = SUM over z of 1 / k_z
    PA(x,y)      = k_x * k_y

Reference interpretation points cited by the report: modularity Q = 0.42 with
24 subclusters over 75 papers and inter-cluster overlap below 15 % was read as
fragmented; Q = 0.93 with silhouette 0.97 was read as cohesive.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from loguru import logger

# Interpretation bands from the P6 reference studies.
Q_FRAGMENTED_MAX = 0.42          # at or below this, structure reads as fragmented
Q_COHESIVE_MIN = 0.75            # above this, structure reads as cohesive
OVERLAP_FRAGMENTED_MAX = 0.15    # inter-cluster vocabulary overlap below 15 %

# Cosine similarity above which two papers join the same cluster.
CLUSTER_SIMILARITY_THRESHOLD = 0.45

# Entities appearing in more than this fraction of papers are "generic" and are
# suppressed as bridge intermediates (rarity filter).
GENERIC_ENTITY_MAX_RATIO = 0.6


@dataclass
class ClusterResult:
    """Clustering outcome plus the structural quality metrics."""

    clusters: Dict[int, List[str]]
    modularity: float = 0.0
    silhouette: float = 0.0
    inter_cluster_overlap: float = 0.0
    method: str = "lexical"

    @property
    def n_clusters(self) -> int:
        return len(self.clusters)

    @property
    def interpretation(self) -> str:
        """Map the metrics onto the bands cited in the P6 report."""
        if self.n_clusters < 2:
            return "single cluster — no fragmentation signal"
        if self.modularity >= Q_COHESIVE_MIN and self.silhouette >= 0.5:
            return (
                f"cohesive (Q={self.modularity:.2f}, silhouette={self.silhouette:.2f}) "
                f"— comparable to the cohesive reference corpus (Q=0.93)"
            )
        if (self.modularity <= Q_FRAGMENTED_MAX
                and self.inter_cluster_overlap <= OVERLAP_FRAGMENTED_MAX):
            return (
                f"fragmented (Q={self.modularity:.2f}, inter-cluster overlap "
                f"{self.inter_cluster_overlap:.0%}) — matches the fragmented "
                f"reference pattern (Q=0.42, overlap <15%)"
            )
        return (
            f"intermediate structure (Q={self.modularity:.2f}, silhouette="
            f"{self.silhouette:.2f}, overlap {self.inter_cluster_overlap:.0%})"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_clusters": self.n_clusters,
            "modularity_q": round(self.modularity, 3),
            "silhouette": round(self.silhouette, 3),
            "inter_cluster_overlap": round(self.inter_cluster_overlap, 3),
            "method": self.method,
            "interpretation": self.interpretation,
        }


@dataclass
class BridgeCandidate:
    """A ranked candidate connection between two disconnected literature nodes."""

    source: str
    target: str
    source_name: str = ""
    target_name: str = ""
    common_neighbors: int = 0
    jaccard: float = 0.0
    adamic_adar: float = 0.0
    resource_allocation: float = 0.0
    preferential_attachment: float = 0.0
    betweenness_broker: str = ""
    filtered_reason: str = ""
    intermediates: List[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Blended ranking score.

        Adamic-Adar and resource allocation dominate because both discount
        hub intermediates, which is exactly the false-bridge failure mode the
        report warns about; preferential attachment is included with a small
        weight only, since on its own it merely rewards popularity.
        """
        return round(
            0.40 * _squash(self.adamic_adar)
            + 0.30 * _squash(self.resource_allocation)
            + 0.20 * self.jaccard
            + 0.10 * _squash(math.log1p(self.preferential_attachment)),
            4,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_name or self.source,
            "target": self.target_name or self.target,
            "common_neighbors": self.common_neighbors,
            "jaccard": round(self.jaccard, 3),
            "adamic_adar": round(self.adamic_adar, 3),
            "resource_allocation": round(self.resource_allocation, 3),
            "preferential_attachment": self.preferential_attachment,
            "score": self.score,
            "broker": self.betweenness_broker,
            "intermediates": self.intermediates[:5],
            "filtered_reason": self.filtered_reason,
        }


def _squash(value: float) -> float:
    """Map an unbounded non-negative score into [0, 1)."""
    return value / (1.0 + value) if value > 0 else 0.0


# ---------------------------------------------------------------------------
# Clustering with quality metrics
# ---------------------------------------------------------------------------

def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


def _jaccard_sets(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _build_similarity_matrix(
    items: List[str],
    features: Dict[str, List[str]],
    embedder=None,
) -> Tuple[List[List[float]], str]:
    """Pairwise similarity, embedding-based when an encoder is available."""
    vectors = None
    method = "lexical"
    if embedder is not None:
        texts = [" ".join(features.get(i, [])) or i for i in items]
        try:
            vectors = embedder.encode(texts, normalize_embeddings=True)
            method = "embedding"
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Cluster embedding failed, using lexical overlap: {exc}")
            vectors = None

    n = len(items)
    matrix = [[0.0] * n for _ in range(n)]
    sets = {i: {f.lower() for f in features.get(i, [])} for i in items}
    for i in range(n):
        matrix[i][i] = 1.0
        for j in range(i + 1, n):
            if vectors is not None:
                sim = max(0.0, min(1.0, _cosine(vectors[i], vectors[j])))
            else:
                sim = _jaccard_sets(sets[items[i]], sets[items[j]])
            matrix[i][j] = matrix[j][i] = sim
    return matrix, method


def _connected_components(
    items: List[str], matrix: List[List[float]], threshold: float
) -> Dict[int, List[str]]:
    """Order-independent grouping: threshold the graph, take components.

    Unlike the previous greedy single pass, the result does not depend on the
    order in which papers arrive.
    """
    n = len(items)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][j] >= threshold:
                union(i, j)

    groups: Dict[int, List[str]] = {}
    for idx, item in enumerate(items):
        groups.setdefault(find(idx), []).append(item)
    return {new_id: members for new_id, members in enumerate(groups.values())}


def compute_modularity(
    items: List[str],
    matrix: List[List[float]],
    clusters: Dict[int, List[str]],
    threshold: float,
) -> float:
    """Newman modularity Q on the thresholded similarity graph.

        Q = (1 / 2m) * SUM_ij [ A_ij - k_i*k_j / 2m ] * delta(c_i, c_j)
    """
    index = {item: i for i, item in enumerate(items)}
    n = len(items)
    adjacency = [[matrix[i][j] if i != j and matrix[i][j] >= threshold else 0.0
                  for j in range(n)] for i in range(n)]
    degrees = [sum(row) for row in adjacency]
    two_m = sum(degrees)
    if two_m <= 0:
        return 0.0
    membership = {}
    for cid, members in clusters.items():
        for member in members:
            membership[member] = cid

    q = 0.0
    for i in range(n):
        for j in range(n):
            if membership.get(items[i]) != membership.get(items[j]):
                continue
            q += adjacency[i][j] - degrees[i] * degrees[j] / two_m
    return round(q / two_m, 4)


def compute_silhouette(
    items: List[str],
    matrix: List[List[float]],
    clusters: Dict[int, List[str]],
) -> float:
    """Mean silhouette width using (1 - similarity) as the distance."""
    if len(clusters) < 2:
        return 0.0
    index = {item: i for i, item in enumerate(items)}
    membership = {m: cid for cid, members in clusters.items() for m in members}
    scores: List[float] = []
    for item in items:
        own = membership[item]
        same = [o for o in clusters[own] if o != item]
        if not same:
            scores.append(0.0)
            continue
        a = sum(1.0 - matrix[index[item]][index[o]] for o in same) / len(same)
        b_values = []
        for cid, members in clusters.items():
            if cid == own or not members:
                continue
            b_values.append(
                sum(1.0 - matrix[index[item]][index[o]] for o in members) / len(members)
            )
        if not b_values:
            scores.append(0.0)
            continue
        b = min(b_values)
        denominator = max(a, b)
        scores.append(0.0 if denominator == 0 else (b - a) / denominator)
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def compute_inter_cluster_overlap(
    clusters: Dict[int, List[str]], features: Dict[str, List[str]]
) -> float:
    """Mean pairwise Jaccard of cluster vocabularies.

    The P6 fragmented reference had inter-cluster overlap below 15 %.
    """
    vocabularies: List[Set[str]] = []
    for members in clusters.values():
        vocabulary: Set[str] = set()
        for member in members:
            vocabulary.update(f.lower() for f in features.get(member, []))
        vocabularies.append(vocabulary)
    overlaps = [
        _jaccard_sets(vocabularies[i], vocabularies[j])
        for i in range(len(vocabularies))
        for j in range(i + 1, len(vocabularies))
    ]
    return round(sum(overlaps) / len(overlaps), 4) if overlaps else 0.0


def cluster_papers(
    features: Dict[str, List[str]],
    embedder=None,
    threshold: float = CLUSTER_SIMILARITY_THRESHOLD,
) -> ClusterResult:
    """Cluster papers by approach vocabulary and report structural quality."""
    items = list(features.keys())
    if len(items) < 2:
        return ClusterResult(clusters={0: items}, method="trivial")

    matrix, method = _build_similarity_matrix(items, features, embedder)
    clusters = _connected_components(items, matrix, threshold)
    return ClusterResult(
        clusters=clusters,
        modularity=compute_modularity(items, matrix, clusters, threshold),
        silhouette=compute_silhouette(items, matrix, clusters),
        inter_cluster_overlap=compute_inter_cluster_overlap(clusters, features),
        method=method,
    )


# ---------------------------------------------------------------------------
# Entropy gating / centroid reassignment (P5)
# ---------------------------------------------------------------------------

@dataclass
class GatingResult:
    """Coverage before/after rescuing singleton clusters."""

    clusters: Dict[int, List[str]]
    reassigned: Dict[str, int] = field(default_factory=dict)
    ambiguous: List[str] = field(default_factory=list)
    coverage_before: float = 0.0
    coverage_after: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reassigned": dict(self.reassigned),
            "ambiguous": list(self.ambiguous),
            "coverage_before": round(self.coverage_before, 3),
            "coverage_after": round(self.coverage_after, 3),
        }


def _entropy(weights: Sequence[float]) -> float:
    """Normalized Shannon entropy of a similarity distribution."""
    total = sum(w for w in weights if w > 0)
    if total <= 0 or len(weights) < 2:
        return 1.0
    probabilities = [w / total for w in weights if w > 0]
    raw = -sum(p * math.log(p) for p in probabilities)
    return raw / math.log(len(probabilities)) if len(probabilities) > 1 else 1.0


def rescue_singletons(
    features: Dict[str, List[str]],
    result: ClusterResult,
    embedder=None,
    entropy_threshold: float = 0.9,
) -> GatingResult:
    """Reassign singleton papers to their nearest cluster centroid (P5).

    Papers whose similarity is spread evenly across clusters (high entropy)
    are left ambiguous instead of being forced into a cluster; the report
    routes exactly those cases to an LLM. Reference effect: topic coverage
    improved from 75.5 % to 95.7 %.
    """
    items = list(features.keys())
    multi = {cid: m for cid, m in result.clusters.items() if len(m) > 1}
    singles = [m[0] for cid, m in result.clusters.items() if len(m) == 1]
    coverage_before = (
        sum(len(m) for m in multi.values()) / len(items) if items else 0.0
    )
    if not multi or not singles:
        return GatingResult(
            clusters=result.clusters,
            coverage_before=coverage_before,
            coverage_after=coverage_before,
        )

    matrix, _ = _build_similarity_matrix(items, features, embedder)
    index = {item: i for i, item in enumerate(items)}
    clusters = {cid: list(members) for cid, members in result.clusters.items()}

    reassigned: Dict[str, int] = {}
    ambiguous: List[str] = []
    for single in singles:
        similarities = {
            cid: sum(matrix[index[single]][index[m]] for m in members) / len(members)
            for cid, members in multi.items()
        }
        if not similarities:
            continue
        if _entropy(list(similarities.values())) > entropy_threshold:
            ambiguous.append(single)
            continue
        best_cid = max(similarities, key=similarities.get)
        if similarities[best_cid] <= 0:
            ambiguous.append(single)
            continue
        reassigned[single] = best_cid
        clusters[best_cid].append(single)
        clusters = {cid: [m for m in members if not (m == single and cid != best_cid)]
                    for cid, members in clusters.items()}

    clusters = {cid: members for cid, members in clusters.items() if members}
    clusters = {new_id: members for new_id, members in enumerate(clusters.values())}
    covered = sum(len(m) for m in clusters.values() if len(m) > 1)
    return GatingResult(
        clusters=clusters,
        reassigned=reassigned,
        ambiguous=ambiguous,
        coverage_before=coverage_before,
        coverage_after=covered / len(items) if items else 0.0,
    )


# ---------------------------------------------------------------------------
# Link prediction & bridge ranking
# ---------------------------------------------------------------------------

def link_prediction_scores(
    graph, node_a: str, node_b: str
) -> Dict[str, float]:
    """All five classical link-prediction scores for one node pair."""
    neighbors_a = set(graph.neighbors(node_a)) if node_a in graph else set()
    neighbors_b = set(graph.neighbors(node_b)) if node_b in graph else set()
    common = neighbors_a & neighbors_b
    union = neighbors_a | neighbors_b

    adamic_adar = 0.0
    resource_allocation = 0.0
    for z in common:
        degree = graph.degree(z)
        if degree > 1:
            adamic_adar += 1.0 / math.log(degree)
        if degree > 0:
            resource_allocation += 1.0 / degree

    return {
        "common_neighbors": len(common),
        "jaccard": len(common) / len(union) if union else 0.0,
        "adamic_adar": adamic_adar,
        "resource_allocation": resource_allocation,
        "preferential_attachment": float(len(neighbors_a) * len(neighbors_b)),
        "intermediates": sorted(common),
    }


def _generic_nodes(graph, max_ratio: float = GENERIC_ENTITY_MAX_RATIO) -> Set[str]:
    """Rarity filter: nodes connected to most of the graph carry no meaning."""
    n = graph.number_of_nodes()
    if n < 4:
        return set()
    cutoff = max(2, int(max_ratio * (n - 1)))
    return {node for node, degree in graph.degree() if degree >= cutoff}


def rank_bridges(
    graph,
    candidate_pairs: Iterable[Tuple[str, str]],
    node_names: Optional[Dict[str, str]] = None,
    node_types: Optional[Dict[str, str]] = None,
    node_years: Optional[Dict[str, int]] = None,
    top_k: int = 10,
) -> Tuple[List[BridgeCandidate], List[BridgeCandidate]]:
    """Score and filter candidate bridges between disconnected literature.

    False-bridge filters applied (P6):
      * rarity — intermediates that are generic hubs are discarded
      * semantic type constraints — a bridge between two nodes of the same
        narrow type (e.g. two datasets) is not a research bridge
      * temporal plausibility — the later node cannot inform the earlier one
      * deduplication — a pair is scored once, order-independent

    Returns (kept, filtered) so the rejected candidates remain inspectable.
    """
    node_names = node_names or {}
    node_types = node_types or {}
    node_years = node_years or {}
    generic = _generic_nodes(graph)

    try:
        import networkx as nx
        betweenness = nx.betweenness_centrality(graph) if graph.number_of_nodes() > 2 else {}
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.debug(f"Betweenness unavailable: {exc}")
        betweenness = {}

    kept: List[BridgeCandidate] = []
    filtered: List[BridgeCandidate] = []
    seen: Set[Tuple[str, str]] = set()

    for node_a, node_b in candidate_pairs:
        if node_a == node_b:
            continue
        key = tuple(sorted((node_a, node_b)))
        if key in seen:
            continue
        seen.add(key)
        if node_a not in graph or node_b not in graph:
            continue

        scores = link_prediction_scores(graph, node_a, node_b)
        intermediates = [z for z in scores["intermediates"] if z not in generic]
        candidate = BridgeCandidate(
            source=node_a,
            target=node_b,
            source_name=node_names.get(node_a, ""),
            target_name=node_names.get(node_b, ""),
            common_neighbors=len(intermediates),
            jaccard=scores["jaccard"],
            adamic_adar=scores["adamic_adar"],
            resource_allocation=scores["resource_allocation"],
            preferential_attachment=scores["preferential_attachment"],
            intermediates=intermediates,
        )
        if intermediates:
            broker = max(intermediates, key=lambda z: betweenness.get(z, 0.0))
            candidate.betweenness_broker = node_names.get(broker, broker)

        # Filter 1 — rarity: every intermediate was a generic hub.
        if scores["common_neighbors"] and not intermediates:
            candidate.filtered_reason = "all intermediates are generic hub entities"
            filtered.append(candidate)
            continue
        # Filter 2 — semantic type constraint.
        type_a, type_b = node_types.get(node_a), node_types.get(node_b)
        if type_a and type_b and type_a == type_b and type_a.upper() in {"DATASET", "METRIC"}:
            candidate.filtered_reason = f"both endpoints are {type_a} nodes — not a research bridge"
            filtered.append(candidate)
            continue
        # Filter 3 — temporal plausibility.
        year_a, year_b = node_years.get(node_a), node_years.get(node_b)
        if year_a and year_b and abs(year_a - year_b) > 25:
            candidate.filtered_reason = (
                f"implausible temporal distance ({year_a} vs {year_b})"
            )
            filtered.append(candidate)
            continue
        # Filter 4 — no shared context at all is not a bridge, it is noise.
        if not intermediates:
            candidate.filtered_reason = "no shared intermediate entity"
            filtered.append(candidate)
            continue

        kept.append(candidate)

    kept.sort(key=lambda c: c.score, reverse=True)
    return kept[:top_k], filtered[:top_k]
