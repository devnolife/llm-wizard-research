"""
Quick test for embedding model selection feature
"""
import requests
import json

def test_embedding_model_selection():
    """Test the new embedding model parameter"""
    
    base_url = "http://localhost:8000"
    
    # Test dengan berbagai model
    models_to_test = [
        "all-MiniLM-L6-v2",
        "all-mpnet-base-v2",
        "nomic-embed-text"
    ]
    
    print("🧪 Testing Embedding Model Selection\n")
    print("=" * 60)
    
    for model in models_to_test:
        print(f"\n📊 Testing with model: {model}")
        print("-" * 60)
        
        payload = {
            "query": "machine learning",
            "max_results": 3,
            "sources": ["arxiv"],
            "deduplicate": True,
            "embedding_model": model
        }
        
        try:
            response = requests.post(
                f"{base_url}/api/papers/search",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"   Papers found: {data['total_results']}")
                print(f"   Embedding model used: {data.get('embedding_model', 'N/A')}")
                print(f"   Sources: {data['sources_searched']}")
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"   Error: {response.text[:200]}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("\n💡 Now open http://localhost:8000 and try:")
    print("   1. Select different embedding models from dropdown")
    print("   2. Search for papers")
    print("   3. See the model name displayed in results")


if __name__ == "__main__":
    test_embedding_model_selection()
