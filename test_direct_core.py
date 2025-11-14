"""
Direct CORE API test - bypass our wrapper to see raw response
"""
import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def test_direct_core_api():
    """Test CORE API directly"""
    
    api_key = os.getenv("CORE_API_KEY")
    
    if not api_key:
        print("❌ CORE_API_KEY not found in .env")
        return
    
    print("🔍 Direct CORE API Test")
    print("=" * 60)
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    base_url = "https://api.core.ac.uk/v3"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Test 1: Simple search
    print("\n1️⃣ Testing search endpoint...")
    print(f"   URL: {base_url}/search/works")
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(
                f"{base_url}/search/works",
                params={"q": "machine learning", "limit": 5},
                headers=headers
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Response keys: {list(data.keys())}")
                print(f"   Total hits: {data.get('totalHits', 'N/A')}")
                print(f"   Results count: {len(data.get('results', []))}")
                
                if data.get('results'):
                    first = data['results'][0]
                    print(f"\n   📄 First result:")
                    print(f"      ID: {first.get('id')}")
                    print(f"      Title: {first.get('title', '')[:60]}...")
                    print(f"      Year: {first.get('yearPublished')}")
                    
            elif response.status_code == 500:
                print(f"   ⚠️  500 Error but checking response...")
                try:
                    data = response.json()
                    print(f"   Response keys: {list(data.keys())}")
                    print(f"   Message: {data.get('message', '')[:200]}")
                    
                    # Check if there's partial data
                    if 'results' in data:
                        print(f"   Results available: {len(data['results'])}")
                except:
                    print(f"   Raw text: {response.text[:500]}")
            else:
                print(f"   ❌ Error: {response.text[:300]}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Test 2: Try different query
    print("\n2️⃣ Testing with simpler query...")
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(
                f"{base_url}/search/works",
                params={"q": "python", "limit": 3},
                headers=headers
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code in [200, 500]:
                try:
                    data = response.json()
                    results = data.get('results', [])
                    print(f"   Results: {len(results)}")
                    
                    if results:
                        print(f"   ✅ Got results!")
                        for i, paper in enumerate(results[:3], 1):
                            print(f"\n      {i}. {paper.get('title', 'No title')[:50]}...")
                            print(f"         ID: {paper.get('id')}")
                    else:
                        print(f"   ⚠️  No results in response")
                        print(f"   Response structure: {json.dumps(data, indent=2)[:500]}")
                except:
                    pass
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Test 3: Try to get specific paper
    print("\n3️⃣ Testing get specific paper (if we have ID)...")
    test_id = "286186774"  # A known CORE paper ID
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(
                f"{base_url}/works/{test_id}",
                headers=headers
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Paper found!")
                print(f"      Title: {data.get('title', '')[:60]}...")
                print(f"      Authors: {len(data.get('authors', []))}")
                print(f"      Year: {data.get('yearPublished')}")
            else:
                print(f"   Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"   Exception: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Direct API test complete")


if __name__ == "__main__":
    asyncio.run(test_direct_core_api())
