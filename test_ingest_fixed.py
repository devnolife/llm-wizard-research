"""
Test paper ingestion after metadata cleaning fix
"""
import requests
import json
import time

def test_ingest_with_different_sources():
    """Test ingesting papers from different sources"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Paper Ingest - After Metadata Fix")
    print("=" * 70)
    
    # Test cases with different sources
    test_cases = [
        {
            "source": "arxiv",
            "paper_id": "2306.04338",  # arXiv paper
            "description": "arXiv paper (transformer models)"
        },
        {
            "source": "core",
            "paper_id": "51392183",  # CORE paper
            "description": "CORE paper (Python interface)"
        },
        {
            "source": "arxiv",
            "paper_id": "1706.03762",  # Famous "Attention is All You Need"
            "description": "arXiv paper (Attention mechanism)"
        }
    ]
    
    results = {"success": [], "failed": []}
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}/{len(test_cases)}: {test['description']}")
        print(f"Source: {test['source']}, Paper ID: {test['paper_id']}")
        print("-" * 70)
        
        try:
            response = requests.post(
                f"{base_url}/api/papers/ingest-external",
                params={
                    "paper_id": test['paper_id'],
                    "source": test['source']
                },
                timeout=60
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS!")
                print(f"   Doc ID: {data.get('doc_id')}")
                print(f"   Title: {data.get('title', 'N/A')[:60]}...")
                print(f"   Message: {data.get('message')}")
                results["success"].append(test)
            else:
                print(f"❌ FAILED")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('detail', response.text[:200])}")
                except:
                    print(f"   Error: {response.text[:200]}")
                results["failed"].append(test)
                
        except requests.exceptions.ConnectionError:
            print(f"❌ ERROR: Cannot connect to server at {base_url}")
            print(f"   Make sure server is running:")
            print(f"   python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
            return
        except Exception as e:
            print(f"❌ Exception: {e}")
            results["failed"].append(test)
        
        # Small delay between requests
        if i < len(test_cases):
            time.sleep(1)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"Total Tests: {len(test_cases)}")
    print(f"✅ Passed: {len(results['success'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"Success Rate: {len(results['success'])/len(test_cases)*100:.1f}%")
    
    if results["success"]:
        print(f"\n✅ Successfully ingested papers:")
        for test in results["success"]:
            print(f"   • [{test['source']}] {test['paper_id']} - {test['description']}")
    
    if results["failed"]:
        print(f"\n❌ Failed to ingest:")
        for test in results["failed"]:
            print(f"   • [{test['source']}] {test['paper_id']} - {test['description']}")
    
    # Check vector store
    if results["success"]:
        print(f"\n{'='*70}")
        print(f"🔍 Verifying Vector Store")
        print(f"{'='*70}")
        
        try:
            response = requests.get(f"{base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"System Status: {data.get('status')}")
                if "components" in data:
                    components = data['components']
                    print(f"\nComponent Status:")
                    for component, status in components.items():
                        symbol = "✅" if status else "❌"
                        print(f"   {symbol} {component}: {status}")
        except Exception as e:
            print(f"Could not check health: {e}")
    
    print(f"\n{'='*70}")
    print(f"✅ Test Complete!")
    print(f"\n💡 Next: Use frontend to search and click 'Add to Collection'")


if __name__ == "__main__":
    test_ingest_with_different_sources()
