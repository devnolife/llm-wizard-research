#!/usr/bin/env python3
"""
Graph Seed Builder — Wizard Research

Builds knowledge-graph seed data for the /api/graph endpoint WITHOUT the LLM,
using FactExtractor's pattern-based fallback (regex entities + linguistic
marker relations) over the already-ingested experiment chunks.

Useful for demoing the VOSviewer-style graph page instantly; LLM-extracted
facts from full experiment runs (richer) supersede this automatically once
available (the endpoint picks the newest result file containing all_facts).

Usage:
    cd backend
    python experiments/build_graph_seed.py
"""

import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from loguru import logger

from app.core.knowledge.fact_extractor import FactExtractor
from app.core.knowledge.fact_table import FactTable
from app.core.retrieval.vector_store import VectorStore
from app.utils.config_loader import get_config

RESULTS_DIR = BACKEND_DIR / "experiments" / "results"
OUTPUT = RESULTS_DIR / "experiment_graph_seed.json"
MANIFEST = PROJECT_DIR / "research_papers" / "papers_manifest.json"


def main():
    config = get_config()
    vs = VectorStore(
        persist_directory=str(PROJECT_DIR / "chroma_db_experiment"),
        collection_name="experiment_papers",
        embedding_model=config.vector_db.embedding_model,
    )
    count = vs.count()
    if count == 0:
        print("ERROR: experiment vector store kosong — jalankan eksperimen dgn ingest dulu.")
        sys.exit(1)
    logger.info(f"Experiment store: {count} chunks")

    # Group chunks per source paper (first N chars each, like phase 2)
    raw = vs.collection.get(include=["documents", "metadatas"])
    per_paper = defaultdict(list)
    for doc, meta in zip(raw["documents"], raw["metadatas"]):
        src = (meta or {}).get("source", "unknown")
        idx = (meta or {}).get("chunk_index", 0)
        per_paper[src].append((idx, doc))

    titles = {}
    if MANIFEST.exists():
        manifest = json.loads(MANIFEST.read_text())
        titles = {p["file"]: p["title"] for p in manifest.get("papers", [])}

    ft = FactTable()
    fe = FactExtractor(llm_interface=None)  # pattern-based only — no LLM
    start = time.time()

    entities_per_paper = {}
    for paper_file, chunks in sorted(per_paper.items()):
        chunks.sort(key=lambda x: x[0])
        text = " ".join(c for _, c in chunks)[:8000]
        stats = fe.extract_from_text(text, paper_id=paper_file, fact_table=ft, max_text_length=8000)
        entities_per_paper[paper_file] = ft.find_entities(source_paper=paper_file)
        logger.info(f"  {Path(paper_file).name}: {stats['entities_extracted']} entities, {stats['total_facts']} facts")

    # Co-occurrence edges (the actual VOSviewer model): entities appearing in
    # the same paper are linked. Dedup by entity NAME to merge regex repeats.
    from app.core.knowledge.fact_table import Fact, PredicateType

    cooccur_added = 0
    for paper_file, ents in entities_per_paper.items():
        by_name = {}
        for e in ents:
            by_name.setdefault(e.name.lower(), e)
        uniq = list(by_name.values())[:20]  # cap pairs per paper
        for i, a in enumerate(uniq):
            for b in uniq[i + 1:]:
                if a.entity_id == b.entity_id:
                    continue
                ft.add_fact(Fact(
                    subject_id=a.entity_id,
                    predicate=PredicateType.DISCUSSES,
                    object_id=b.entity_id,
                    source="co-occurrence (same paper)",
                    source_paper=paper_file,
                    confidence=0.5,
                    metadata={"extraction_method": "cooccurrence"},
                ))
                cooccur_added += 1
    logger.info(f"Co-occurrence facts added: {cooccur_added}")

    # Resolve to the all_facts shape used by the graph endpoint
    all_facts = []
    for fact in ft.query():
        subj = ft.get_entity(fact.subject_id)
        obj = ft.get_entity(fact.object_id)
        all_facts.append({
            "fact_id": fact.fact_id,
            "subject": subj.name if subj else fact.subject_id,
            "subject_type": subj.entity_type.value if subj else "CONCEPT",
            "predicate": fact.predicate.value,
            "object": obj.name if obj else fact.object_id,
            "object_type": obj.entity_type.value if obj else "CONCEPT",
            "confidence": float(fact.confidence),
            "source_paper": titles.get(fact.source_paper, fact.source_paper),
            "evidence": fact.source[:200],
            "extraction_method": fact.metadata.get("extraction_method", "pattern"),
        })

    report = {
        "experiment_info": {
            "timestamp": datetime.now().isoformat(),
            "model": "pattern-only (no LLM)",
            "mode": "graph-seed",
            "system": "Wizard Research — pattern-based KG seed",
        },
        "phase2_fact_extraction": {
            "all_facts": all_facts,
            "total_facts": len(all_facts),
            "fact_table_stats": ft.get_statistics(),
        },
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    elapsed = time.time() - start
    print(f"\nSeed tersimpan : {OUTPUT}")
    print(f"Papers          : {len(per_paper)}")
    print(f"Facts           : {len(all_facts)}")
    print(f"Waktu           : {elapsed:.1f}s")


if __name__ == "__main__":
    main()
