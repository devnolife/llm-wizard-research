"""
Knowledge Graph API — VOSviewer-style network data.

Serves the SPO Fact Base as a network graph (nodes + links) with community
clusters, for the frontend graph visualization page.

Data sources (priority):
    1. Persisted snapshot for the requested/completed analysis job
    2. Latest full-mode experiment result JSON (all_facts dump)
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx
from fastapi import APIRouter, Query
from loguru import logger

from ...utils.job_store import get_job_graph, get_latest_completed_job

router = APIRouter()

BACKEND_DIR = Path(__file__).resolve().parents[3]
RESULTS_DIR = BACKEND_DIR / "experiments" / "results"


def _facts_from_job(job_id: str | None) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """Load facts captured with a completed, isolated analysis job."""
    if not job_id:
        latest = get_latest_completed_job()
        job_id = latest.get("job_id") if latest else None
    snapshot = get_job_graph(job_id) if job_id else None
    if not snapshot:
        return [], None
    facts = snapshot.get("facts", [])
    return (facts if isinstance(facts, list) else []), job_id


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
    job_id: Optional[str] = Query(None, description="Completed analysis job ID (defaults to latest)"),
    min_degree: int = Query(1, ge=1, description="Hide nodes with fewer connections"),
    max_nodes: int = Query(300, ge=10, le=2000),
):
    """
    Knowledge graph as a VOSviewer-style network.

    Returns nodes (id, label, type, cluster, weight) and links
    (source, target, predicate, weight), plus cluster/stat metadata.
    """
    requested_job_id = job_id
    source = "job_snapshot"
    try:
        facts, selected_job_id = _facts_from_job(job_id)
    except Exception as e:
        logger.warning(f"Persisted analysis graph unavailable: {e}")
        facts = []
        selected_job_id = None

    if not facts and requested_job_id:
        return {
            "source": "job_snapshot_empty",
            "job_id": requested_job_id,
            "nodes": [],
            "links": [],
            "clusters": [],
            "stats": {"nodes": 0, "links": 0, "facts": 0},
        }

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
        "job_id": selected_job_id,
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
