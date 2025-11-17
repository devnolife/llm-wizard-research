#!/usr/bin/env python3
"""
Pure Python - Tidak pakai API sama sekali
Direct import dan jalankan fungsi
"""

import os
import sys
from pathlib import Path

# Setup path
SCRIPT_DIR = Path(__file__).parent
SRC_DIR = SCRIPT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

print("\n" + "=" * 80)
print("🧙 WIZARD RESEARCH - PURE PYTHON (NO API)")
print("=" * 80 + "\n")

# ============================================================================
# STEP 1: Import semua yang dibutuhkan
# ============================================================================
print("📦 Step 1: Loading modules...")

# Import langsung tanpa lewat __init__.py untuk avoid relative import errors
try:
    import importlib.util
    
    # Load config
    spec = importlib.util.spec_from_file_location("config_loader", SRC_DIR / "utils" / "config_loader.py")
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    get_config = config_module.get_config
    
    # Load document processor
    spec = importlib.util.spec_from_file_location("document_processor", SRC_DIR / "utils" / "document_processor.py")
    doc_proc_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doc_proc_module)
    DocumentProcessor = doc_proc_module.DocumentProcessor
    
    # Load vector store
    spec = importlib.util.spec_from_file_location("vector_store", SRC_DIR / "retrieval" / "vector_store.py")
    vs_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vs_module)
    VectorStore = vs_module.VectorStore
    
    # Load LLM
    spec = importlib.util.spec_from_file_location("glm_interface", SRC_DIR / "llm" / "glm_interface.py")
    llm_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(llm_module)
    GLMInterface = llm_module.GLMInterface
    
    print("   ✓ Core modules loaded (config, document processor, vector store, LLM)")
    
except Exception as e:
    print(f"   ✗ Error loading basic modules: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Optional modules
RAGRetriever = None
GapDetectorAgent = None
RecommenderAgent = None

print("   ⚠ Advanced modules (RAG, Gap Detector, Recommender) skipped due to import complexity")

print()

# ============================================================================
# STEP 2: Initialize components
# ============================================================================
print("=" * 80)
print("🔧 Step 2: Initializing components...")
print("=" * 80)

config = get_config()
print(f"✓ Config loaded")

vector_store = VectorStore(
    persist_directory=config.vector_db.persist_directory,
    collection_name=config.vector_db.collection_name,
    embedding_model=config.vector_db.embedding_model,
    distance_metric=config.vector_db.distance_metric
)
print(f"✓ Vector store initialized")

# Initialize LLM with lightweight model
try:
    llm = GLMInterface()  # Uses config defaults (llama3.2:latest)
    print(f"✓ LLM initialized: {config.llm.model_name}")
except Exception as e:
    print(f"⚠ LLM initialization failed: {e}")
    llm = None

doc_processor = DocumentProcessor()
print(f"✓ Document processor initialized")

print()

# ============================================================================
# STEP 3: Check existing data
# ============================================================================
print("=" * 80)
print("📊 Step 3: Database status")
print("=" * 80)

stats = vector_store.get_stats()
print(f"Total documents: {stats.get('total_documents', 0)}")
print(f"Embedding model: {stats.get('embedding_model', 'unknown')}")
print(f"Collection: {stats.get('collection_name', 'unknown')}")
print()

# ============================================================================
# STEP 4: Process PDFs
# ============================================================================
print("=" * 80)
print("📄 Step 4: Process PDFs from test_pdfs/")
print("=" * 80)

pdf_dir = SCRIPT_DIR / "test_pdfs"
if not pdf_dir.exists():
    print(f"✗ Directory not found: {pdf_dir}")
    sys.exit(1)

pdf_files = sorted(pdf_dir.glob("*.pdf"))
print(f"Found {len(pdf_files)} PDF files:\n")

for i, pdf_path in enumerate(pdf_files, 1):
    print(f"{i}. {pdf_path.name}")

print()

# Process each PDF
total_chunks = 0
for i, pdf_path in enumerate(pdf_files, 1):
    print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
    
    try:
        # Extract text and create chunks
        print(f"    → Extracting text...")
        processed_doc = doc_processor.process_pdf(str(pdf_path))
        chunks = processed_doc.chunks  # Get chunks from ProcessedDocument
        print(f"    ✓ Created {len(chunks)} chunks")
        
        # Add to vector store
        print(f"    → Adding to vector store...")
        for chunk in chunks:
            vector_store.add_document(
                content=chunk.content,
                metadata=chunk.metadata
            )
        
        total_chunks += len(chunks)
        print(f"    ✓ Stored in database")
        
    except Exception as e:
        print(f"    ✗ Error: {e}")
        import traceback
        traceback.print_exc()

print(f"\n✅ Total chunks created: {total_chunks}")
print()

# Check updated stats
stats = vector_store.get_stats()
print(f"📊 Updated database: {stats.get('total_documents', 0)} total documents")
print()

# ============================================================================
# STEP 5: Test Search
# ============================================================================
print("=" * 80)
print("🔍 Step 5: Test Search")
print("=" * 80)

query = "machine learning"
print(f"Query: '{query}'")
print()

try:
    results = vector_store.search(query, top_k=5)
    print(f"✓ Found {len(results)} results:\n")
    
    for i, result in enumerate(results[:3], 1):
        print(f"{i}. Score: {result.score:.4f}")
        print(f"   Content: {result.document.content[:150]}...")
        print(f"   Source: {result.document.metadata.get('source', 'unknown')}")
        print()
        
except Exception as e:
    print(f"✗ Search error: {e}")
    import traceback
    traceback.print_exc()

print()

# ============================================================================
# STEP 6-8: Advanced features (RAG, Gap Detection, Recommendations)
# ============================================================================
print("=" * 80)
print("⚠️  SKIPPED: Advanced features (require LLM)")
print("=" * 80)
print("RAG Q&A, Gap Detection, and Recommendations require GLM which is currently")
print("having issues. Focus on core functionality: PDF → Vector DB → Search")
print()

# ============================================================================
# DONE
# ============================================================================
print("=" * 80)
print("✅ ALL STEPS COMPLETED")
print("=" * 80)
print()
