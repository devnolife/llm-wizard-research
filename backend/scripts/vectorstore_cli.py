#!/usr/bin/env python3
"""
Vector Store CLI — inspect and query the project's ChromaDB knowledge base.

A lightweight command-line harness over the project's own ``VectorStore`` (the
same ChromaDB collection + ``all-MiniLM-L6-v2`` embedding function used by the
backend). Unlike a generic ChromaDB HTTP CLI, this talks to the embedded
``PersistentClient`` directly, so semantic search works with the client-side
embeddings the ingestion pipeline produced.

Usage (run from the ``backend/`` directory):

    python scripts/vectorstore_cli.py stats
    python scripts/vectorstore_cli.py sources
    python scripts/vectorstore_cli.py query "synthesis gap detection" -k 5
    python scripts/vectorstore_cli.py query "transformer attention" --source attention_is_all_you_need.pdf

Add ``--json`` to any command for machine-readable output (handy for agents).
"""

import argparse
import json
import os
import sys
from collections import Counter

# Make the backend package importable when run as ``python scripts/...``
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.retrieval.vector_store import VectorStore  # noqa: E402
from app.utils.config_loader import get_config  # noqa: E402


def _build_store() -> VectorStore:
    """Instantiate the VectorStore from the project's config (config.yaml)."""
    cfg = get_config().vector_db
    return VectorStore(
        persist_directory=cfg.persist_directory,
        collection_name=cfg.collection_name,
        embedding_model=cfg.embedding_model,
    )


def _print(data, as_json: bool, human):
    """Emit either JSON or a human-readable rendering."""
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        human(data)


def cmd_stats(store: VectorStore, args) -> None:
    stats = store.get_stats()

    def human(d):
        print("Vector store statistics")
        print("-" * 40)
        for key, value in d.items():
            print(f"  {key:20s}: {value}")

    _print(stats, args.json, human)


def cmd_sources(store: VectorStore, args) -> None:
    docs = store.get_all_documents()
    counts = Counter()
    for doc in docs:
        source = (doc.metadata or {}).get("source", "<unknown>")
        counts[source] += 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    payload = {
        "total_chunks": len(docs),
        "distinct_sources": len(ranked),
        "sources": [{"source": s, "chunks": n} for s, n in ranked],
    }

    def human(d):
        print(f"{d['distinct_sources']} source documents, "
              f"{d['total_chunks']} chunks total")
        print("-" * 60)
        for item in d["sources"]:
            print(f"  {item['chunks']:5d}  {item['source']}")

    _print(payload, args.json, human)


def cmd_query(store: VectorStore, args) -> None:
    where = {"source": args.source} if args.source else None
    results = store.search(
        query=args.text,
        top_k=args.k,
        filter_metadata=where,
        min_score=args.min_score,
    )
    payload = {
        "query": args.text,
        "top_k": args.k,
        "results": [
            {
                "rank": r.rank,
                "score": round(r.score, 4),
                "source": (r.document.metadata or {}).get("source"),
                "title": (r.document.metadata or {}).get("title"),
                "preview": (r.document.content or "")[:240].replace("\n", " "),
            }
            for r in results
        ],
    }

    def human(d):
        print(f"Query: {d['query']!r}  (top {d['top_k']})")
        print("=" * 70)
        if not d["results"]:
            print("  No results.")
            return
        for item in d["results"]:
            print(f"#{item['rank']}  score={item['score']:.4f}  "
                  f"source={item['source']}")
            print(f"     {item['preview']}")
            print()

    _print(payload, args.json, human)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vectorstore_cli.py",
        description="Inspect and query the project's ChromaDB vector store.",
    )
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON instead of human-readable output")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats", help="Show collection statistics")
    sub.add_parser("sources", help="List source documents and chunk counts")

    q = sub.add_parser("query", help="Semantic search over the corpus")
    q.add_argument("text", help="Query text")
    q.add_argument("-k", "--k", type=int, default=5,
                   help="Number of results (default: 5)")
    q.add_argument("--source", default=None,
                   help="Restrict results to a single source document")
    q.add_argument("--min-score", type=float, default=None,
                   help="Minimum cosine similarity score")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    store = _build_store()
    handlers = {
        "stats": cmd_stats,
        "sources": cmd_sources,
        "query": cmd_query,
    }
    handlers[args.command](store, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
