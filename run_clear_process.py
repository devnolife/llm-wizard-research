#!/usr/bin/env python3
"""
Clear step-by-step process:
1. Check PDFs available
2. Convert PDFs to vector DB
3. Run model analysis

No API needed - direct Python
"""

import sys
import os
from pathlib import Path
import time

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Now import after path is set - import langsung tanpa __init__.py
import chromadb
from sentence_transformers import SentenceTransformer
import PyPDF2
from typing import List, Dict, Any

def print_header(title):
    """Print nice header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def step1_check_pdfs():
    """Step 1: Check available PDFs"""
    print_header("STEP 1: CEK PDF YANG TERSEDIA")
    
    pdf_dir = Path("data/raw")
    if not pdf_dir.exists():
        print(f"\n❌ Folder {pdf_dir} tidak ditemukan!")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Folder {pdf_dir} sudah dibuat")
        return []
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"\n❌ Tidak ada file PDF di {pdf_dir}")
        print("\n💡 Silakan copy file PDF ke folder data/raw/")
        return []
    
    print(f"\n✅ Ditemukan {len(pdf_files)} file PDF:")
    for i, pdf in enumerate(pdf_files, 1):
        size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"   {i}. {pdf.name:40s} ({size_mb:.2f} MB)")
    
    return pdf_files

def step2_check_vector_db():
    """Step 2: Check current vector DB status"""
    print_header("STEP 2: CEK STATUS DATABASE VECTOR")
    
    try:
        # Initialize ChromaDB directly
        db_path = "./chroma_db"
        collection_name = "research_papers"
        
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        count = collection.count()
        
        print(f"\n📊 Status Database:")
        print(f"   Total dokumen: {count}")
        print(f"   Collection: {collection_name}")
        print(f"   Path: {db_path}")
        
        if count > 0:
            print(f"\n✅ Database sudah ada data ({count} chunks)")
            print(f"\n⚠️  Pilihan:")
            print(f"   1. Hapus data lama dan proses ulang")
            print(f"   2. Tambah data baru ke database existing")
            print(f"   3. Skip ingestion, langsung ke analysis")
            choice = input("\nPilih (1/2/3): ").strip()
            return client, collection, count, choice
        else:
            print(f"\n⚠️  Database kosong, perlu di-isi dulu")
            return client, collection, 0, "1"
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None, 0, "1"

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF"""
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    return text

def chunk_text(text: str, chunk_size=500, overlap=50) -> List[str]:
    """Split text into chunks"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    
    return chunks

def step3_process_pdfs(pdf_files, client, collection, mode="1"):
    """Step 3: Process PDFs to Vector DB"""
    print_header("STEP 3: CONVERT PDF → VECTOR DATABASE")
    
    if mode == "3":
        print("\n⏭️  Skip ingestion")
        return
    
    if mode == "1":
        print("\n🗑️  Menghapus data lama...")
        try:
            # Clear collection
            ids = collection.get()['ids']
            if ids:
                collection.delete(ids=ids)
            print("✅ Data lama sudah dihapus")
        except Exception as e:
            print(f"⚠️  Error clearing: {e}")
    
    print(f"\n📄 Memproses {len(pdf_files)} file PDF...")
    print(f"🔧 Loading embedding model...")
    
    # Load embedding model
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print(f"✅ Model loaded!\n")
    
    total_chunks = 0
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_path.name}")
        
        try:
            # Extract text
            print(f"    → Extracting text...")
            text = extract_text_from_pdf(pdf_path)
            print(f"    → Extracted {len(text)} characters")
            
            # Chunk text
            print(f"    → Chunking text...")
            chunks = chunk_text(text, chunk_size=500, overlap=50)
            print(f"    → Created {len(chunks)} chunks")
            
            # Generate embeddings
            print(f"    → Generating embeddings...")
            embeddings = model.encode(chunks, show_progress_bar=False)
            
            # Store to vector DB
            print(f"    → Storing to ChromaDB...")
            ids = [f"{pdf_path.stem}_{j}" for j in range(len(chunks))]
            metadatas = [
                {
                    "source": pdf_path.name,
                    "chunk_id": str(j),
                    "total_chunks": str(len(chunks))
                }
                for j in range(len(chunks))
            ]
            
            collection.add(
                ids=ids,
                embeddings=embeddings.tolist(),
                documents=chunks,
                metadatas=metadatas
            )
            
            total_chunks += len(chunks)
            print(f"    ✅ Done! ({len(chunks)} chunks stored)")
            print()
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n✅ TOTAL: {total_chunks} chunks dari {len(pdf_files)} PDF")
    
    # Verify
    final_count = collection.count()
    print(f"✅ Database sekarang ada {final_count} chunks")

def step4_run_analysis(collection):
    """Step 4: Run model analysis"""
    print_header("STEP 4: ANALISIS DENGAN MODEL")
    
    print("\n🔧 Loading embedding model...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print("✅ Model ready!\n")
    
    # Test 1: Search
    print("-" * 80)
    print("TEST 1: SEARCH VECTOR DB")
    print("-" * 80)
    
    query = "machine learning"
    print(f"\nQuery: '{query}'")
    
    # Generate query embedding
    query_embedding = model.encode([query])[0]
    
    # Search in ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=5
    )
    
    docs = results['documents'][0] if results['documents'] else []
    distances = results['distances'][0] if results['distances'] else []
    metadatas = results['metadatas'][0] if results['metadatas'] else []
    
    print(f"✅ Found {len(docs)} results:\n")
    
    for i, (doc, dist, meta) in enumerate(zip(docs, distances, metadatas), 1):
        similarity = 1 - dist  # Convert distance to similarity
        print(f"{i}. Similarity: {similarity:.4f}")
        print(f"   Source: {meta.get('source', 'unknown')}")
        print(f"   Content: {doc[:120]}...")
        print()
    
    # Test 2: Topic analysis
    print("-" * 80)
    print("TEST 2: TOPIC ANALYSIS")
    print("-" * 80)
    
    topics = ["deep learning", "neural networks", "machine learning"]
    
    for topic in topics:
        print(f"\n📊 Topic: '{topic}'")
        
        topic_embedding = model.encode([topic])[0]
        results = collection.query(
            query_embeddings=[topic_embedding.tolist()],
            n_results=3
        )
        
        count = len(results['documents'][0]) if results['documents'] else 0
        print(f"   → Found {count} relevant documents")
    
    print()
    
    # Test 3: Statistics
    print("-" * 80)
    print("TEST 3: DATABASE STATISTICS")
    print("-" * 80)
    
    total_docs = collection.count()
    
    print(f"\n📈 Statistics:")
    print(f"   Total chunks: {total_docs}")
    
    # Get all sources
    all_data = collection.get()
    sources = set()
    if all_data['metadatas']:
        for meta in all_data['metadatas']:
            sources.add(meta.get('source', 'unknown'))
    
    print(f"   Unique PDFs: {len(sources)}")
    print(f"\n📄 PDF files:")
    for i, source in enumerate(sorted(sources), 1):
        print(f"      {i}. {source}")
    
    print()

def main():
    """Main workflow"""
    print("\n" + "="*80)
    print("  🧙 WIZARD RESEARCH - CLEAR STEP BY STEP PROCESS")
    print("="*80)
    
    # Step 1: Check PDFs
    pdf_files = step1_check_pdfs()
    
    if not pdf_files:
        print("\n⚠️  Tidak ada PDF untuk diproses. Keluar.\n")
        return
    
    # Step 2: Check Vector DB
    client, collection, doc_count, choice = step2_check_vector_db()
    
    if client is None or collection is None:
        print("\n❌ Tidak bisa akses vector store. Keluar.\n")
        return
    
    # Step 3: Process PDFs
    if choice in ["1", "2"]:
        step3_process_pdfs(pdf_files, client, collection, mode=choice)
    
    # Wait a bit
    time.sleep(1)
    
    # Step 4: Analysis
    step4_run_analysis(collection)
    
    print("\n" + "="*80)
    print("  ✅ SEMUA PROSES SELESAI!")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proses dibatalkan oleh user\n")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
