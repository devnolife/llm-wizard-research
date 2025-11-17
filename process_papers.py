#!/usr/bin/env python3
"""
Proses Papers - Clear Step by Step
1. Scan PDF files
2. Convert to Vector DB
3. Run Analysis
"""

import os
import sys
from pathlib import Path
import time

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("\n" + "=" * 80)
    print("🧙 WIZARD RESEARCH - PAPER PROCESSING")
    print("=" * 80 + "\n")
    
    # ============================================================================
    # STEP 1: Scan PDF Files
    # ============================================================================
    print("📂 STEP 1: SCANNING PDF FILES")
    print("-" * 80)
    
    pdf_dir = Path("test_pdfs")
    if not pdf_dir.exists():
        print(f"❌ Folder {pdf_dir} tidak ditemukan!")
        return
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    print(f"✓ Found {len(pdf_files)} PDF files:\n")
    
    for i, pdf in enumerate(pdf_files, 1):
        size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"  {i}. {pdf.name} ({size_mb:.2f} MB)")
    
    if not pdf_files:
        print("❌ Tidak ada PDF files!")
        return
    
    print()
    
    # ============================================================================
    # STEP 2: Convert PDF to Vector DB
    # ============================================================================
    print("🔄 STEP 2: CONVERTING PDF TO VECTOR DATABASE")
    print("-" * 80)
    
    # Import yang dibutuhkan
    print("Loading modules...")
    try:
        from utils.config_loader import get_config
        from utils.document_processor import DocumentProcessor
        from retrieval.vector_store import VectorStore
        print("✓ Modules loaded\n")
    except Exception as e:
        print(f"❌ Import error: {e}")
        print("\nUsing API method instead...\n")
        use_api_method(pdf_files)
        return
    
    # Initialize components
    print("Initializing components...")
    config = get_config()
    doc_processor = DocumentProcessor()
    vector_store = VectorStore(config)
    print("✓ Components initialized\n")
    
    # Check existing data
    stats = vector_store.get_stats()
    print(f"Current database status:")
    print(f"  - Total documents: {stats.get('total_documents', 0)}")
    print(f"  - Embedding model: {stats.get('embedding_model', 'unknown')}")
    print()
    
    # Process each PDF
    total_chunks = 0
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"Processing [{i}/{len(pdf_files)}]: {pdf_path.name}")
        
        try:
            # Extract text
            print("  → Extracting text...", end=" ")
            documents = doc_processor.process_pdf(str(pdf_path))
            print(f"✓ {len(documents)} chunks")
            
            # Add to vector store
            print("  → Adding to vector database...", end=" ")
            for doc in documents:
                vector_store.add_document(
                    content=doc['content'],
                    metadata=doc.get('metadata', {})
                )
            print(f"✓ Done")
            
            total_chunks += len(documents)
            print()
            
        except Exception as e:
            print(f"✗ Error: {e}\n")
            continue
    
    print(f"✅ Successfully processed {len(pdf_files)} PDFs → {total_chunks} chunks\n")
    
    # Update stats
    stats = vector_store.get_stats()
    print(f"Updated database status:")
    print(f"  - Total documents: {stats.get('total_documents', 0)}")
    print()
    
    # ============================================================================
    # STEP 3: Run Analysis
    # ============================================================================
    print("🤖 STEP 3: RUNNING MODEL ANALYSIS")
    print("-" * 80)
    
    # Use API for analysis (simpler)
    print("Using API endpoints for analysis...\n")
    
    import requests
    
    api_url = "http://localhost:8000"
    
    # Check API
    try:
        resp = requests.get(f"{api_url}/api/stats", timeout=5)
        if resp.status_code != 200:
            print("❌ API not responding. Please start the server:")
            print("   uvicorn src.api.main:app --reload\n")
            return
    except:
        print("❌ API not running. Please start the server:")
        print("   uvicorn src.api.main:app --reload\n")
        return
    
    # 3a. Gap Detection
    print("📊 Analysis 1: Gap Detection")
    print("-" * 40)
    topic = "machine learning"
    print(f"Topic: {topic}\n")
    print("Analyzing... (this may take time)")
    
    try:
        resp = requests.post(f"{api_url}/api/gaps", json={"topic": topic}, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            gaps = result.get('gaps', [])
            print(f"✓ Found {len(gaps)} research gaps:\n")
            for i, gap in enumerate(gaps[:3], 1):
                print(f"  {i}. {gap.get('area', 'Unknown')}")
                print(f"     {gap.get('description', 'N/A')[:100]}...")
            print()
        else:
            print(f"✗ Error: {resp.status_code}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    # 3b. Recommendations
    print("📊 Analysis 2: Recommendations")
    print("-" * 40)
    query = "deep learning"
    print(f"Query: {query}\n")
    print("Generating recommendations...")
    
    try:
        resp = requests.post(f"{api_url}/api/recommend", json={"query": query}, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            recs = result.get('recommendations', [])
            print(f"✓ Found {len(recs)} recommendations\n")
            if recs:
                for i, rec in enumerate(recs[:3], 1):
                    print(f"  {i}. {rec.get('title', 'Unknown')}")
            else:
                print("  (No recommendations generated)\n")
        else:
            print(f"✗ Error: {resp.status_code}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    # 3c. Search Test
    print("📊 Analysis 3: Search Test")
    print("-" * 40)
    search_query = "neural networks"
    print(f"Query: {search_query}\n")
    
    try:
        resp = requests.post(f"{api_url}/api/search", json={"query": search_query, "top_k": 3}, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            results = result.get('results', [])
            print(f"✓ Found {len(results)} results\n")
            for i, res in enumerate(results, 1):
                print(f"  {i}. Score: {res.get('score', 0):.4f}")
                print(f"     {res.get('content', '')[:80]}...")
            print()
        else:
            print(f"✗ Error: {resp.status_code}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
    
    print("=" * 80)
    print("✅ ALL STEPS COMPLETED")
    print("=" * 80 + "\n")


def use_api_method(pdf_files):
    """Fallback: Use API method for ingestion"""
    import requests
    
    api_url = "http://localhost:8000"
    
    # Check API
    try:
        resp = requests.get(f"{api_url}/api/stats", timeout=5)
        if resp.status_code != 200:
            print("❌ API not responding. Please start the server:")
            print("   uvicorn src.api.main:app --reload\n")
            return
    except:
        print("❌ API not running. Please start the server:")
        print("   uvicorn src.api.main:app --reload\n")
        return
    
    print("Using API for PDF ingestion...\n")
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"Uploading [{i}/{len(pdf_files)}]: {pdf_path.name}")
        
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': (pdf_path.name, f, 'application/pdf')}
                resp = requests.post(f"{api_url}/api/ingest", files=files, timeout=60)
                
                if resp.status_code == 200:
                    result = resp.json()
                    print(f"  ✓ Chunks created: {result.get('chunks_created', 0)}\n")
                else:
                    print(f"  ✗ Error: {resp.status_code}\n")
        except Exception as e:
            print(f"  ✗ Error: {e}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
