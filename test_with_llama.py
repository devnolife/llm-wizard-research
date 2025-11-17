#!/usr/bin/env python3
"""
Test RAG, Gap Detection, dan Recommendations dengan Ollama (llama3.2)
Menggunakan API endpoint yang sudah jalan
"""

import requests
import json
from pathlib import Path

API_URL = "http://localhost:8000"

def test_search():
    """Test search functionality"""
    print("=" * 80)
    print("🔍 TEST 1: SEARCH")
    print("=" * 80)
    
    response = requests.post(
        f"{API_URL}/api/search",
        json={"query": "machine learning", "top_k": 3}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Found {result['total_results']} results\n")
        
        for i, res in enumerate(result['results'][:3], 1):
            print(f"{i}. {res['title']}")
            print(f"   Score: {res['score']:.4f}")
            print(f"   Content: {res['content'][:150]}...")
            print()
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
    
    print()

def test_rag_qa():
    """Test RAG Q&A"""
    print("=" * 80)
    print("💬 TEST 2: RAG Q&A")
    print("=" * 80)
    
    question = "What is machine learning and what are its main approaches?"
    print(f"Question: {question}\n")
    print("Generating answer with gpt-oss (13GB model)...\n")
    
    response = requests.post(
        f"{API_URL}/api/chat",
        json={"message": question, "use_history": False}
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Answer:")
        print("-" * 80)
        print(result.get('response', 'No answer'))
        print("-" * 80)
        print()
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        print()

def test_gap_detection():
    """Test gap detection"""
    print("=" * 80)
    print("🔍 TEST 3: GAP DETECTION")
    print("=" * 80)
    
    topic = "deep learning applications"
    print(f"Topic: {topic}\n")
    print("Analyzing research gaps with gpt-oss (13GB model)...\n")
    
    response = requests.post(
        f"{API_URL}/api/gaps",
        json={"topic": topic}
    )
    
    if response.status_code == 200:
        result = response.json()
        gaps = result.get('gaps', [])
        
        print(f"✓ Detected {len(gaps)} research gaps:\n")
        
        for i, gap in enumerate(gaps[:5], 1):
            print(f"{i}. {gap.get('area', 'Unknown')}")
            print(f"   Description: {gap.get('description', 'N/A')[:200]}")
            print(f"   Confidence: {gap.get('confidence', 0):.2f}")
            print()
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        print()

def test_recommendations():
    """Test recommendations"""
    print("=" * 80)
    print("💡 TEST 4: RECOMMENDATIONS")
    print("=" * 80)
    
    query = "neural networks for image classification"
    print(f"Query: {query}\n")
    print("Generating recommendations with gpt-oss (13GB model)...\n")
    
    response = requests.post(
        f"{API_URL}/api/recommend",
        json={"query": query, "max_recommendations": 5}
    )
    
    if response.status_code == 200:
        result = response.json()
        
        recommendations = result.get('recommendations', [])
        themes = result.get('themes', [])
        methodologies = result.get('methodologies', [])
        
        if isinstance(recommendations, list):
            print(f"✓ Generated {len(recommendations)} recommendations:\n")
            
            for i, rec in enumerate(recommendations[:5], 1):
                if isinstance(rec, dict):
                    print(f"{i}. {rec.get('title', 'Unknown')}")
                    print(f"   Relevance: {rec.get('relevance_score', 0):.2f}")
                    print(f"   Reason: {rec.get('reason', 'N/A')[:150]}")
                else:
                    print(f"{i}. {rec}")
                print()
        else:
            print("   (No recommendations generated)")
            print()
        
        if themes:
            print(f"🎯 Key Themes ({len(themes)}):")
            for theme in themes[:5]:
                print(f"   • {theme}")
            print()
        
        if methodologies:
            print(f"🔬 Methodologies ({len(methodologies)}):")
            for method in methodologies[:5]:
                print(f"   • {method}")
            print()
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        print()

def main():
    print("\n" + "=" * 80)
    print("🧙 WIZARD RESEARCH - TEST WITH LLAMA3.2")
    print("=" * 80 + "\n")
    
    # Check API status
    try:
        response = requests.get(f"{API_URL}/api/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"📊 Database: {stats.get('total_documents', 0)} documents")
            print(f"🤖 Model: gpt-oss:latest (13GB - better quality)")
            print()
        else:
            print("❌ API not responding. Make sure server is running:")
            print("   uvicorn src.api.main:app --reload")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Make sure server is running: uvicorn src.api.main:app --reload")
        return
    
    # Run tests
    test_search()
    test_rag_qa()
    test_gap_detection()
    test_recommendations()
    
    print("=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
