"""
Knowledge Graph API — VOSviewer-style network data.

Serves the SPO Fact Base as a network graph (nodes + links) with community
clusters, for the frontend graph visualization page.

Data sources (priority):
    1. Live FactTable singleton (populated by upload-and-analyze sessions)
    2. Latest full-mode experiment result JSON (all_facts dump)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

router = APIRouter()

BACKEND_DIR = Path(__file__).resolve().parents[3]
RESULTS_DIR = BACKEND_DIR / "experiments" / "results"


def _facts_from_live_table() -> List[Dict[str, Any]]:
    """Read facts from the in-memory FactTable (entity names resolved)."""
    from ..dependencies import get_fact_table

    ft = get_fact_table()
    facts = []
    for fact in ft.query():
        subj = ft.get_entity(fact.subject_id)
        obj = ft.get_entity(fact.object_id)
        facts.append({
            "subject": subj.name if subj else fact.subject_id,
            "subject_type": subj.entity_type.value if subj else "CONCEPT",
            "predicate": fact.predicate.value,
            "object": obj.name if obj else fact.object_id,
            "object_type": obj.entity_type.value if obj else "CONCEPT",
            "confidence": float(fact.confidence),
            "source_paper": fact.source_paper,
        })
    return facts


def _facts_from_experiment() -> tuple[List[Dict[str, Any]], Optional[str]]:
    """Fallback: load all_facts from the newest full-mode experiment result."""
    candidates = sorted(
        RESULTS_DIR.glob("experiment_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        facts = data.get("phase2_fact_extraction", {}).get("all_facts", [])
        if facts:
            return facts, path.name
    return [], None


@router.get("/graph")
async def get_knowledge_graph(
    min_degree: int = Query(1, ge=1, description="Hide nodes with fewer connections"),
    max_nodes: int = Query(300, ge=10, le=2000),
):
    """
    Knowledge graph as a VOSviewer-style network.

    Returns nodes (id, label, type, cluster, weight) and links
    (source, target, predicate, weight), plus cluster/stat metadata.
    """
    source = "live_fact_table"
    try:
        facts = _facts_from_live_table()
    except Exception as e:
        logger.warning(f"Live fact table unavailable: {e}")
        facts = []

    if not facts:
        facts, result_file = _facts_from_experiment()
        source = f"experiment:{result_file}" if result_file else "empty"

    if not facts:
        return {
            "source": "empty", "nodes": [], "links": [], "clusters": [],
            "stats": {"nodes": 0, "links": 0, "facts": 0},
        }

    # --- Build graph ---
    g = nx.Graph()
    link_index: Dict[tuple, Dict[str, Any]] = {}

    for fact in facts:
        s, o = fact["subject"].strip(), fact["object"].strip()
        if not s or not o or s.lower() == o.lower():
            continue
        if not g.has_node(s):
            g.add_node(s, type=fact.get("subject_type", "CONCEPT"))
        if not g.has_node(o):
            g.add_node(o, type=fact.get("object_type", "CONCEPT"))

        key = tuple(sorted((s, o)))
        if key in link_index:
            link_index[key]["weight"] += 1
            link_index[key]["predicates"].add(fact["predicate"])
        else:
            link_index[key] = {
                "source": s, "target": o, "weight": 1,
                "predicates": {fact["predicate"]},
                "confidence": fact.get("confidence", 0.7),
            }
            g.add_edge(s, o)

    # Filter by degree, cap node count by total degree ranking
    degrees = dict(g.degree())
    keep = {n for n, d in degrees.items() if d >= min_degree}
    if len(keep) > max_nodes:
        keep = set(sorted(keep, key=lambda n: degrees[n], reverse=True)[:max_nodes])
    g = g.subgraph(keep).copy()

    if g.number_of_nodes() == 0:
        return {
            "source": source, "nodes": [], "links": [], "clusters": [],
            "stats": {"nodes": 0, "links": 0, "facts": len(facts)},
        }

    # --- Community detection (VOSviewer-style clusters) ---
    try:
        communities = nx.community.greedy_modularity_communities(g)
    except Exception:
        communities = [set(g.nodes())]
    cluster_of = {}
    for idx, members in enumerate(communities):
        for node in members:
            cluster_of[node] = idx

    nodes = [
        {
            "id": n,
            "label": n,
            "type": g.nodes[n].get("type", "CONCEPT"),
            "cluster": cluster_of.get(n, 0),
            "weight": degrees.get(n, 1),
        }
        for n in g.nodes()
    ]
    links = [
        {
            "source": meta["source"],
            "target": meta["target"],
            "weight": meta["weight"],
            "predicates": sorted(meta["predicates"]),
            "confidence": meta["confidence"],
        }
        for key, meta in link_index.items()
        if g.has_node(meta["source"]) and g.has_node(meta["target"])
    ]

    cluster_summary = []
    for idx, members in enumerate(communities):
        kept = [m for m in members if m in keep]
        if not kept:
            continue
        top = sorted(kept, key=lambda n: degrees.get(n, 0), reverse=True)[:3]
        cluster_summary.append({"id": idx, "size": len(kept), "top_terms": top})

    return {
        "source": source,
        "nodes": nodes,
        "links": links,
        "clusters": cluster_summary,
        "stats": {
            "nodes": len(nodes),
            "links": len(links),
            "facts": len(facts),
            "clusters": len(cluster_summary),
        },
    }
