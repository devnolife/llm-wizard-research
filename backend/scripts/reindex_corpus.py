#!/usr/bin/env python3
"""
Re-index the corpus into a new embedding space (lossless migration).

Why: the original collection was embedded with the English-centric
``all-MiniLM-L6-v2`` bi-encoder. Switching to a multilingual model
(``paraphrase-multilingual-MiniLM-L12-v2``) improves retrieval for the mixed
Indonesian/English corpus. Because changing the embedding model invalidates the
stored vectors, the documents must be re-embedded.

This migration is **lossless**: ChromaDB stores the document *text*, so we read
every chunk (text + metadata) from the source collection and re-embed it into a
*new* collection with the target model. The original collection is left
untouched as a backup — critically, this preserves app-uploaded papers whose
source PDFs are no longer on disk (e.g. the Indonesian journals).

Usage (run from the ``backend/`` directory):

    # Dry run — report what would happen, no writes
    python scripts/reindex_corpus.py --dry-run

    # Migrate research_papers (all-MiniLM) -> research_papers_ml (multilingual)
    python scripts/reindex_corpus.py

    # Custom source/target/model
    python scripts/reindex_corpus.py \
        --source-collection research_papers \
        --target-collection research_papers_ml \
        --target-model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

After a successful run, point the app at the new space by setting in
``backend/config.yaml`` (or env): vector_db.collection_name and
vector_db.embedding_model — see the printed next-steps.
"""

import argparse
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.retrieval.vector_store import VectorStore, Document  # noqa: E402
from app.utils.config_loader import get_config  # noqa: E402

DEFAULT_TARGET_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main() -> int:
    cfg = get_config().vector_db
    parser = argparse.ArgumentParser(description="Lossless corpus re-index migration.")
    parser.add_argument("--persist-dir", default=cfg.persist_directory)
    parser.add_argument("--source-collection", default=cfg.collection_name)
    parser.add_argument("--source-model", default=cfg.embedding_model)
    parser.add_argument("--target-collection", default=f"{cfg.collection_name}_ml")
    parser.add_argument("--target-model", default=DEFAULT_TARGET_MODEL)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--dry-run", action="store_true",
                        help="Report counts only; do not write the new collection")
    args = parser.parse_args()

    print(f"Source: {args.source_collection} ({args.source_model})")
    print(f"Target: {args.target_collection} ({args.target_model})")
    print(f"Persist dir: {args.persist_dir}")
    print("-" * 60)

    # 1. Open the source collection and read every document (text + metadata).
    source = VectorStore(
        persist_directory=args.persist_dir,
        collection_name=args.source_collection,
        embedding_model=args.source_model,
    )
    docs = source.get_all_documents()
    print(f"Read {len(docs)} documents from '{args.source_collection}'.")

    # Distinct sources — useful sanity check that nothing is silently lost.
    sources = sorted({(d.metadata or {}).get("source", "<unknown>") for d in docs})
    print(f"Distinct sources: {len(sources)}")

    if args.dry_run:
        print("\n[dry-run] No data written. Re-run without --dry-run to migrate.")
        return 0

    if not docs:
        print("Nothing to migrate (source is empty).")
        return 1

    # 2. Create the target collection with the new model and re-embed.
    target = VectorStore(
        persist_directory=args.persist_dir,
        collection_name=args.target_collection,
        embedding_model=args.target_model,
    )
    existing = target.count()
    if existing > 0:
        print(f"WARNING: target '{args.target_collection}' already has "
              f"{existing} documents. Clearing it for a clean rebuild.")
        target.clear_collection()

    # Preserve original chunk IDs so cross-references stay valid.
    to_add = [
        Document(id=d.id, content=d.content, metadata=d.metadata or {})
        for d in docs
    ]
    target.add_documents(to_add, batch_size=args.batch_size)

    migrated = target.count()
    print("-" * 60)
    print(f"Migrated {migrated}/{len(docs)} documents into "
          f"'{args.target_collection}'.")
    ok = migrated == len(docs)
    print("Result:", "OK ✅" if ok else "MISMATCH ⚠️")

    print("\nNext steps — point the app at the new embedding space:")
    print("  In backend/config.yaml under vector_db:")
    print(f"    collection_name: {args.target_collection}")
    print(f"    embedding_model: {args.target_model}")
    print("  (or set CHROMA_COLLECTION_NAME / EMBEDDING_MODEL env vars).")
    print(f"\nThe original '{args.source_collection}' collection is kept as a backup.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
