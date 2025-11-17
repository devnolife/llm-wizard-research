#!/usr/bin/env python3
"""
Complete Upload Test Script
Tests bulk PDF upload functionality with various scenarios
"""

import requests
import time
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_health():
    """Test server health"""
    print("🏥 Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server healthy: {data}")
            return True
        else:
            print(f"❌ Server unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not reachable: {e}")
        return False

def test_single_upload(pdf_path, title=None, authors=None, year=None):
    """Test single PDF upload"""
    print(f"\n📤 Uploading: {Path(pdf_path).name}")
    
    files = {'file': open(pdf_path, 'rb')}
    data = {}
    
    if title:
        data['title'] = title
    if authors:
        data['authors'] = authors
    if year:
        data['year'] = year
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ingest",
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success!")
            print(f"   📄 Doc ID: {result['doc_id']}")
            print(f"   📦 Chunks: {result['chunks_created']}")
            print(f"   💬 Message: {result['message']}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Error: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        files['file'].close()

def test_bulk_upload(pdf_dir):
    """Test bulk upload from directory"""
    print(f"\n📁 Bulk upload from: {pdf_dir}")
    
    pdf_files = list(Path(pdf_dir).glob("*.pdf"))
    if not pdf_files:
        print("⚠️  No PDF files found")
        return
    
    print(f"📊 Found {len(pdf_files)} PDF files")
    
    success_count = 0
    fail_count = 0
    
    for pdf_path in pdf_files:
        if test_single_upload(str(pdf_path)):
            success_count += 1
        else:
            fail_count += 1
        time.sleep(0.5)  # Rate limiting
    
    print(f"\n{'='*50}")
    print(f"📊 Bulk Upload Summary")
    print(f"{'='*50}")
    print(f"✅ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📁 Total: {len(pdf_files)}")

def test_stats():
    """Test stats endpoint"""
    print(f"\n📊 Fetching system stats...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Vector Store Stats:")
            print(f"   Collection: {stats['vector_store']['collection_name']}")
            print(f"   Documents: {stats['vector_store']['total_documents']}")
            print(f"   Model: {stats['vector_store']['embedding_model']}")
            print(f"   Dimension: {stats['vector_store']['embedding_dimension']}")
        else:
            print(f"❌ Failed to get stats: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_search(query="deep learning"):
    """Test search after upload"""
    print(f"\n🔍 Testing search: '{query}'")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/search",
            json={"query": query, "top_k": 3},
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Found {results['total_results']} results")
            for i, result in enumerate(results['results'][:3], 1):
                print(f"\n   {i}. {result['metadata'].get('title', 'No title')}")
                print(f"      Score: {result['score']:.3f}")
                print(f"      Preview: {result['content'][:100]}...")
        else:
            print(f"❌ Search failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("="*60)
    print("🧪 Wizard Research - Upload Test Suite")
    print("="*60)
    
    # Test 1: Server health
    if not test_health():
        print("\n❌ Server not available. Please start the server first:")
        print("   uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
        return
    
    # Test 2: Single upload with metadata
    test_single_upload(
        "test_pdfs/paper_1.pdf",
        title="Deep Learning Research",
        authors="John Doe, Jane Smith",
        year=2024
    )
    
    # Test 3: Bulk upload
    if os.path.exists("test_pdfs"):
        test_bulk_upload("test_pdfs")
    
    # Test 4: Check stats
    test_stats()
    
    # Test 5: Search uploaded papers
    test_search("deep learning")
    test_search("transformer")
    
    print("\n" + "="*60)
    print("✨ Test suite completed!")
    print("="*60)

if __name__ == "__main__":
    main()
