"""
Test CORE API ingest via HTTP endpoint
Run this AFTER server is started
"""
import requests
import json

def test_core_ingest_http():
    """Test ingesting CORE papers via HTTP"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing CORE API Ingest via HTTP")
    print("=" * 60)
    
    # Test papers from our earlier search
    test_papers = [
        {"id": "51392183", "title": "Pytrec_eval: An Extremely Fast Python Interface"},
        {"id": "286186774", "title": "Validation of the GPR model"},
    ]
    
    print("\n📋 Will test ingesting these papers:")
    for i, paper in enumerate(test_papers, 1):
        print(f"   {i}. ID: {paper['id']} - {paper['title'][:50]}...")
    
    results = {"success": [], "failed": []}
    
    for paper in test_papers:
        paper_id = paper['id']
        print(f"\n{'='*60}")
        print(f"📥 Ingesting paper ID: {paper_id}")
        print(f"   Title: {paper['title']}")
        print("-" * 60)
        
        try:
            response = requests.post(
                f"{base_url}/api/papers/ingest-external",
                params={
                    "paper_id": paper_id,
                    "source": "core"
                },
                timeout=60
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS!")
                print(f"      Doc ID: {data.get('doc_id')}")
                print(f"      Title: {data.get('title', '')[:60]}...")
                print(f"      Message: {data.get('message')}")
                results["success"].append(paper_id)
            else:
                print(f"   ❌ FAILED")
                print(f"      Error: {response.text[:200]}")
                results["failed"].append(paper_id)
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ ERROR: Cannot connect to server")
            print(f"      Make sure server is running: python -m uvicorn src.api.main:app --reload")
            return
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results["failed"].append(paper_id)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"   Total tested: {len(test_papers)}")
    print(f"   ✅ Success: {len(results['success'])}")
    print(f"   ❌ Failed: {len(results['failed'])}")
    
    if results["success"]:
        print(f"\n   Successfully ingested papers:")
        for pid in results["success"]:
            print(f"      • {pid}")
    
    if results["failed"]:
        print(f"\n   Failed to ingest:")
        for pid in results["failed"]:
            print(f"      • {pid}")
    
    # Test retrieval
    if results["success"]:
        print(f"\n{'='*60}")
        print(f"🔍 Testing Vector Store Retrieval")
        print(f"{'='*60}")
        
        try:
            response = requests.get(f"{base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "components" in data:
                    print(f"   Vector Store Status: {data['components'].get('vector_store', 'Unknown')}")
        except:
            pass
    
    print(f"\n✅ Test Complete!")
    print(f"\n💡 Next steps:")
    print(f"   1. Search for papers in frontend")
    print(f"   2. Click '➕ Add to Collection' button")
    print(f"   3. Papers will be ingested automatically!")


if __name__ == "__main__":
    test_core_ingest_http()
