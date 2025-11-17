#!/usr/bin/env python3
"""
Test sistem langsung tanpa API - langsung pakai fungsi internal
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from retrieval.vector_store import VectorStore
from retrieval.rag_retriever import RAGRetriever
from gap_detection.analyzer import GapAnalyzer
from recommendation.engine import RecommendationEngine
from utils.config_loader import load_config

def test_vector_store():
    """Test apakah vector store punya data"""
    print("=" * 60)
    print("TEST 1: Vector Store Status")
    print("=" * 60)
    
    config = load_config()
    vector_store = VectorStore(config)
    
    # Cek jumlah dokumen
    stats = vector_store.get_stats()
    print(f"✓ Total documents: {stats.get('total_documents', 0)}")
    print(f"✓ Model: {stats.get('embedding_model', 'unknown')}")
    print(f"✓ Dimensions: {stats.get('dimensions', 'unknown')}")
    print()

def test_search():
    """Test search langsung di vector store"""
    print("=" * 60)
    print("TEST 2: Search Functionality")
    print("=" * 60)
    
    config = load_config()
    vector_store = VectorStore(config)
    
    query = "machine learning"
    print(f"Query: '{query}'")
    print()
    
    results = vector_store.search(query, top_k=5)
    print(f"Found {len(results)} results:")
    print()
    
    for i, result in enumerate(results, 1):
        print(f"{i}. Distance: {result.get('distance', 'N/A'):.4f}")
        print(f"   Title: {result.get('metadata', {}).get('title', 'No title')}")
        print(f"   Content: {result.get('content', '')[:150]}...")
        print()

def test_rag_retriever():
    """Test RAG retriever"""
    print("=" * 60)
    print("TEST 3: RAG Retriever")
    print("=" * 60)
    
    config = load_config()
    retriever = RAGRetriever(config)
    
    query = "deep learning applications"
    print(f"Query: '{query}'")
    print()
    
    results = retriever.retrieve(query, top_k=3)
    print(f"Retrieved {len(results)} documents:")
    print()
    
    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result.get('score', 'N/A')}")
        print(f"   Title: {result.get('metadata', {}).get('title', 'No title')}")
        print(f"   Content: {result.get('content', '')[:200]}...")
        print()

def test_gap_detection():
    """Test gap detection langsung"""
    print("=" * 60)
    print("TEST 4: Gap Detection")
    print("=" * 60)
    
    config = load_config()
    gap_analyzer = GapAnalyzer(config)
    
    topic = "machine learning"
    print(f"Topic: '{topic}'")
    print()
    
    try:
        gaps = gap_analyzer.detect_gaps(topic)
        print(f"✓ Found {len(gaps)} gaps:")
        print()
        
        for i, gap in enumerate(gaps, 1):
            print(f"{i}. {gap.get('title', 'No title')}")
            print(f"   Confidence: {gap.get('confidence', 0):.2f}")
            print(f"   Description: {gap.get('description', 'N/A')[:150]}...")
            print()
    except Exception as e:
        print(f"✗ Error: {e}")
        print()

def test_recommendations():
    """Test recommendation engine langsung"""
    print("=" * 60)
    print("TEST 5: Recommendations")
    print("=" * 60)
    
    config = load_config()
    rec_engine = RecommendationEngine(config)
    
    query = "deep learning research"
    print(f"Query: '{query}'")
    print()
    
    try:
        recommendations = rec_engine.get_recommendations(query)
        print(f"✓ Generated recommendations:")
        print()
        
        # Recommendations
        if recommendations.get('recommendations'):
            print(f"  Papers: {len(recommendations['recommendations'])} recommendations")
            for i, rec in enumerate(recommendations['recommendations'][:3], 1):
                print(f"    {i}. {rec.get('title', 'No title')}")
                print(f"       Reason: {rec.get('reason', 'N/A')[:100]}...")
        else:
            print("  ✗ No recommendations found")
        
        print()
        
        # Themes
        if recommendations.get('themes'):
            print(f"  Themes: {len(recommendations['themes'])} themes found")
            for theme in recommendations['themes'][:3]:
                print(f"    - {theme}")
        else:
            print("  ✗ No themes found")
        
        print()
        
        # Methodologies
        if recommendations.get('methodologies'):
            print(f"  Methodologies: {len(recommendations['methodologies'])} found")
            for method in recommendations['methodologies'][:3]:
                print(f"    - {method}")
        else:
            print("  ✗ No methodologies found")
        
        print()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        print()

def main():
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "TEST SISTEM LANGSUNG (NO API)" + " " * 17 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    try:
        test_vector_store()
        test_search()
        test_rag_retriever()
        test_gap_detection()
        test_recommendations()
        
        print("=" * 60)
        print("✓ ALL TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
