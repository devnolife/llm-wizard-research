#!/usr/bin/env python3
"""
Papers CLI — fetch external research papers and (optionally) ingest them so
they show up in the project's search.

This is a command-line companion to the SearchPage feature. It calls the same
``AggregatedPaperAPI`` the backend uses (arXiv, Semantic Scholar, CrossRef,
PubMed, CORE, Europe PMC), so anything you can search in the UI you can also
fetch from the terminal — handy for scripting, debugging a source, or
pre-populating the corpus.

Usage (run from the ``backend/`` directory):

    # Fetch & display papers (no ingestion) — proves a source works
    python scripts/papers_cli.py search "synthesis gap detection"
    python scripts/papers_cli.py search "graph neural network" --sources europe_pmc arxiv -k 5
    python scripts/papers_cli.py search "transformer" --year-from 2018 --json

    # Fetch + add to the vector store so they appear in semantic search
    python scripts/papers_cli.py ingest "neuro-symbolic reasoning" --sources arxiv europe_pmc -k 10

Environment variables (optional, for higher rate limits) are read the same way
as the backend: SEMANTIC_SCHOLAR_API_KEY, PUBMED_API_KEY, CROSSREF_EMAIL,
PUBMED_EMAIL, CORE_API_KEY.
"""

import argparse
import asyncio
import json
import os
import sys

# Make the backend package importable when run as ``python scripts/...``
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.paper_apis import AggregatedPaperAPI  # noqa: E402

ALL_SOURCES = ["arxiv", "semantic_scholar", "crossref", "pubmed", "core", "europe_pmc", "sciencedirect"]
DEFAULT_SOURCES = ["arxiv", "europe_pmc", "crossref"]


def build_paper_api() -> AggregatedPaperAPI:
    """Construct the aggregator exactly like the backend dependency does."""
    return AggregatedPaperAPI(
        semantic_scholar_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
        pubmed_key=os.getenv("PUBMED_API_KEY"),
        crossref_email=os.getenv("CROSSREF_EMAIL"),
        pubmed_email=os.getenv("PUBMED_EMAIL"),
        core_key=os.getenv("CORE_API_KEY"),
    )


def clean_paper_metadata(paper) -> dict:
    """Mirror of routes/papers.py: drop None values for ChromaDB compatibility."""
    metadata = {
        "title": paper.title or "Unknown",
        "authors": ", ".join(paper.authors) if paper.authors else "Unknown",
        "source_api": paper.source_api or "unknown",
    }
    if paper.year is not None:
        metadata["year"] = int(paper.year)
    if paper.journal:
        metadata["journal"] = str(paper.journal)
    if paper.doi:
        metadata["doi"] = str(paper.doi)
    if paper.url:
        metadata["url"] = str(paper.url)
    if paper.keywords:
        metadata["keywords"] = ", ".join(paper.keywords)
    if paper.citation_count is not None:
        metadata["citation_count"] = int(paper.citation_count)
    return metadata


async def _fetch(args):
    """Search across sources, deduplicate, and return a flat list of papers."""
    api = build_paper_api()
    # Over-fetch per source then dedupe down to k. Dividing k evenly across
    # sources starves the result when some sources return nothing for the query
    # (e.g. Europe PMC is biomedical, so it yields 0 for a CS/Indonesian topic).
    # Requesting up to k from each source lets the productive sources backfill,
    # so `-k 10` reliably returns 10 when the papers exist anywhere.
    per_source = max(3, args.k)
    results = await api.search_all(
        query=args.query,
        max_results_per_source=per_source,
        sources=args.sources,
        year_from=args.year_from,
        year_to=args.year_to,
    )
    if args.deduplicate:
        papers = api.deduplicate_papers(results, query=args.query)
    else:
        papers = [p for source_papers in results.values() for p in source_papers]
    return papers[: args.k], {s: len(results.get(s, [])) for s in args.sources}


def _emit(data, as_json: bool, human):
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        human(data)


def cmd_search(args) -> None:
    papers, per_source = asyncio.run(_fetch(args))
    payload = {
        "query": args.query,
        "sources": args.sources,
        "per_source_counts": per_source,
        "returned": len(papers),
        "papers": [
            {
                "title": p.title,
                "authors": p.authors[:5] if p.authors else [],
                "year": p.year,
                "source": p.source_api,
                "doi": p.doi,
                "url": p.url,
                "citation_count": p.citation_count,
                "abstract": (p.abstract or "")[:300],
            }
            for p in papers
        ],
    }

    def human(d):
        counts = ", ".join(f"{s}={n}" for s, n in d["per_source_counts"].items())
        print(f"Query: {d['query']!r}   [{counts}]   -> {d['returned']} unique")
        print("=" * 72)
        for i, p in enumerate(d["papers"], 1):
            authors = ", ".join(p["authors"]) or "Unknown"
            print(f"#{i}  ({p['year']}) {p['title']}")
            print(f"     {authors}  ·  {p['source']}  ·  cites:{p['citation_count']}")
            if p["url"]:
                print(f"     {p['url']}")
            print()

    _emit(payload, args.json, human)


def cmd_ingest(args) -> None:
    # VectorStore is only needed for ingestion; import lazily to keep `search` fast.
    from app.core.retrieval.vector_store import VectorStore, Document
    from app.utils.config_loader import get_config

    papers, per_source = asyncio.run(_fetch(args))

    cfg = get_config().vector_db
    effective_collection = args.collection or cfg.collection_name
    effective_persist = args.persist_dir or cfg.persist_directory
    store = VectorStore(
        persist_directory=effective_persist,
        collection_name=effective_collection,
        embedding_model=cfg.embedding_model,
    )

    ingested, failed, ids = 0, 0, []
    for paper in papers:
        try:
            doc = Document(
                id=paper.paper_id,
                content=f"{paper.title or 'Untitled'}\n\n"
                        f"{paper.abstract or 'No abstract available'}",
                metadata=clean_paper_metadata(paper),
            )
            ids.append(store.add_document(doc))
            ingested += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  ! failed to ingest {paper.paper_id}: {exc}", file=sys.stderr)
            failed += 1

    payload = {
        "query": args.query,
        "sources": args.sources,
        "per_source_counts": per_source,
        "papers_found": len(papers),
        "papers_ingested": ingested,
        "papers_failed": failed,
        "collection": effective_collection,
        "persist_directory": effective_persist,
        "total_documents": store.count(),
    }

    def human(d):
        print(f"Ingested {d['papers_ingested']}/{d['papers_found']} papers "
              f"into '{d['collection']}' (failed: {d['papers_failed']})")
        print(f"Collection now holds {d['total_documents']} documents.")
        print("These papers are now searchable via `make db-query` / the app search.")

    _emit(payload, args.json, human)


def add_common_fetch_args(p) -> None:
    p.add_argument("query", help="Search query")
    p.add_argument("-k", "--k", type=int, default=10,
                   help="Total number of papers to return (default: 10)")
    p.add_argument("--sources", nargs="+", default=DEFAULT_SOURCES,
                   choices=ALL_SOURCES,
                   help=f"Sources to query (default: {' '.join(DEFAULT_SOURCES)})")
    p.add_argument("--year-from", type=int, default=None, help="Earliest publication year")
    p.add_argument("--year-to", type=int, default=None, help="Latest publication year")
    p.add_argument("--no-dedupe", dest="deduplicate", action="store_false",
                   help="Do not deduplicate across sources")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="papers_cli.py",
        description="Fetch external research papers and optionally ingest them "
                    "into the searchable vector store.",
    )
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON instead of human-readable output")
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Fetch and display papers (no ingestion)")
    add_common_fetch_args(s)

    g = sub.add_parser("ingest", help="Fetch papers and add them to the vector store")
    add_common_fetch_args(g)
    g.add_argument("--persist-dir", default=None,
                   help="Override the ChromaDB persist directory (default: from config)")
    g.add_argument("--collection", default=None,
                   help="Override the collection name (default: from config)")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    {"search": cmd_search, "ingest": cmd_ingest}[args.command](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
