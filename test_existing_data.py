#!/usr/bin/env python3
"""
Test sistem langsung dengan data yang sudah ada di ChromaDB
Tidak perlu upload, tidak perlu API eksternal
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from retrieval.vector_store import VectorStore
from retrieval.rag_retriever import RAGRetriever
from agents.gap_detector import GapDetector
from agents.recommender import Recommender
from llm.glm_interface import GLMInterface
from utils.config_loader import load_config

def main():
    print("=" * 80)
    print("TEST SISTEM DENGAN DATA YANG SUDAH ADA")
    print("=" * 80)
    
    # Load config
    config = load_config()
    
    # Initialize components
    print("\n1. Initializing Vector Store...")
    vector_store = VectorStore(config)
    
    # Check data
    stats = vector_store.get_stats()
    print(f"   ✓ Total documents: {stats['total_documents']}")
    print(f"   ✓ Embedding model: {stats['embedding_model']}")
    print(f"   ✓ Dimensions: {stats['embedding_dimensions']}")
    
    if stats['total_documents'] == 0:
        print("\n❌ Database kosong! Tidak ada data untuk ditest.")
        return
    
    # Initialize LLM
    print("\n2. Initializing LLM (GLM-4)...")
    llm = GLMInterface(config)
    
    # Initialize RAG Retriever
    print("\n3. Initializing RAG Retriever...")
    retriever = RAGRetriever(vector_store, llm, config)
    
    # Test 1: Search/Retrieval
    print("\n" + "=" * 80)
    print("TEST 1: SEARCH & RETRIEVAL")
    print("=" * 80)
    query = "machine learning"
    print(f"\nQuery: '{query}'")
    
    search_results = vector_store.search(query, k=5)
    print(f"\n✓ Found {len(search_results)} results:")
    for i, result in enumerate(search_results[:3], 1):
        print(f"\n{i}. Similarity: {result.get('similarity', 0):.4f}")
        print(f"   Content: {result['content'][:150]}...")
        if 'metadata' in result:
            print(f"   Source: {result['metadata'].get('source', 'unknown')}")
    
    # Test 2: Gap Detection
    print("\n" + "=" * 80)
    print("TEST 2: GAP DETECTION")
    print("=" * 80)
    
    print("\n3. Initializing Gap Detector...")
    gap_detector = GapDetector(retriever, llm, config)
    
    topic = "deep learning applications"
    print(f"\nTopic: '{topic}'")
    print("\nAnalyzing gaps (ini akan memakan waktu karena LLM analysis)...")
    
    gaps = gap_detector.detect_gaps(topic)
    print(f"\n✓ Detected {len(gaps.get('gaps', []))} gaps:")
    for i, gap in enumerate(gaps.get('gaps', [])[:3], 1):
        print(f"\n{i}. {gap.get('area', 'Unknown')}")
        print(f"   Description: {gap.get('description', 'N/A')[:150]}...")
        print(f"   Confidence: {gap.get('confidence', 0):.2f}")
    
    # Test 3: Recommendations
    print("\n" + "=" * 80)
    print("TEST 3: RECOMMENDATIONS")
    print("=" * 80)
    
    print("\n4. Initializing Recommender...")
    recommender = Recommender(retriever, llm, config)
    
    query_rec = "neural networks"
    print(f"\nQuery: '{query_rec}'")
    print("\nGenerating recommendations...")
    
    recommendations = recommender.recommend(query_rec)
    print(f"\n✓ Generated recommendations:")
    print(f"   Papers: {len(recommendations.get('recommendations', []))}")
    print(f"   Themes: {len(recommendations.get('themes', []))}")
    print(f"   Methodologies: {len(recommendations.get('methodologies', []))}")
    
    if recommendations.get('recommendations'):
        print("\nTop 3 recommendations:")
        for i, rec in enumerate(recommendations['recommendations'][:3], 1):
            print(f"\n{i}. {rec.get('title', 'Unknown')}")
            print(f"   Relevance: {rec.get('relevance_score', 0):.2f}")
            print(f"   Reason: {rec.get('reason', 'N/A')[:100]}...")
    
    if recommendations.get('themes'):
        print("\nKey themes:")
        for theme in recommendations['themes'][:3]:
            print(f"   • {theme}")
    
    # Test 4: RAG Query
    print("\n" + "=" * 80)
    print("TEST 4: RAG Q&A")
    print("=" * 80)
    
    question = "What are the main approaches in deep learning?"
    print(f"\nQuestion: '{question}'")
    print("\nGenerating answer...")
    
    answer = retriever.retrieve_and_generate(question)
    print(f"\n✓ Answer:\n{answer[:500]}...")
    
    print("\n" + "=" * 80)
    print("TEST SELESAI")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
