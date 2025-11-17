#!/usr/bin/env python3
"""
Clean start - Ingest ONLY 3 main papers
"""

import sys
import os
os.chdir('/home/devnolife/wizard-research')
sys.path.insert(0, '/home/devnolife/wizard-research')

from pathlib import Path

print("\n" + "=" * 80)
print("🧙 CLEAN START - Ingest 3 Jurnal Utama Saja")
print("=" * 80 + "\n")

# Import
from src.utils.config_loader import get_config
from src.utils.document_processor import DocumentProcessor
from src.retrieval.vector_store import VectorStore

# Initialize
config = get_config()
print(f"✓ Config loaded")

vector_store = VectorStore(
    persist_directory=config.vector_db.persist_directory,
    collection_name=config.vector_db.collection_name,
    embedding_model=config.vector_db.embedding_model,
    distance_metric=config.vector_db.distance_metric
)
print(f"✓ Vector store initialized (fresh/empty)")

doc_processor = DocumentProcessor()
print(f"✓ Document processor ready\n")

# ============================================================================
# Ingest 3 JURNAL UTAMA
# ============================================================================
print("=" * 80)
print("📄 INGESTING 3 MAIN PAPERS")
print("=" * 80)
print()

# HANYA 3 jurnal ini
main_papers = [
    "test_pdfs/test.pdf",
    "test_pdfs/test-2.pdf", 
    "test_pdfs/test-3.pdf"
]

total_chunks = 0

for i, pdf_path in enumerate(main_papers, 1):
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        print(f"[{i}/3] ✗ Not found: {pdf_file.name}")
        continue
    
    print(f"[{i}/3] Processing: {pdf_file.name}")
    
    try:
        # Process PDF
        print(f"    → Extracting text and creating chunks...")
        processed_doc = doc_processor.process_pdf(str(pdf_file))
        chunks = processed_doc.chunks
        print(f"    ✓ Created {len(chunks)} chunks")
        print(f"    ✓ Title: {processed_doc.title}")
        
        # Add to vector store
        print(f"    → Storing in vector database...")
        for chunk in chunks:
            vector_store.add_document(
                content=chunk.content,
                metadata=chunk.metadata
            )
        
        total_chunks += len(chunks)
        print(f"    ✓ Stored successfully\n")
        
    except Exception as e:
        print(f"    ✗ Error: {e}\n")

# Check final stats
print("=" * 80)
print("📊 FINAL DATABASE STATUS")
print("=" * 80)

stats = vector_store.get_stats()
print(f"✓ Total chunks ingested: {total_chunks}")
print(f"✓ Total documents in DB: {stats['total_documents']}")
print(f"✓ Collection: {stats['collection_name']}")
print(f"✓ Embedding model: {stats['embedding_model']}")
print()

# Quick verification - search test
print("=" * 80)
print("🔍 VERIFICATION - Quick Search Test")
print("=" * 80)
print()

test_query = "deep learning"
print(f"Query: '{test_query}'")

results = vector_store.search(test_query, top_k=3)
print(f"✓ Found {len(results)} results:\n")

for i, result in enumerate(results, 1):
    print(f"{i}. Score: {result.score:.4f}")
    print(f"   Source: {result.document.metadata.get('file_name', 'unknown')}")
    print(f"   Content: {result.document.content[:120]}...")
    print()

print("=" * 80)
print("✅ CLEAN DATABASE READY!")
print("=" * 80)
print(f"\nDatabase berisi HANYA 3 jurnal utama: {total_chunks} chunks total")
print("Sekarang bisa jalankan: python auto_analysis.py")
print()
