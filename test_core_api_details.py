"""
Simple test for CORE API get_paper_details
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_core_api_only():
    """Test CORE API get_paper_details without vector store dependency"""
    from src.external.paper_apis import CoreAPI
    
    print("🧪 Testing CORE API - Get Paper Details")
    print("=" * 60)
    
    # Initialize CORE API
    core_api = CoreAPI()
    print(f"✅ CORE API initialized")
    print(f"   API Key present: {bool(core_api.api_key)}")
    
    # Test 1: Search for papers first
    print("\n1️⃣ Searching for papers to get valid IDs...")
    papers = await core_api.search("artificial intelligence", max_results=5)
    
    if not papers:
        print("❌ No papers found in search")
        print("   Trying with year filter...")
        papers = await core_api.search("machine learning", max_results=5, year_from=2020)
    
    if not papers:
        print("❌ Still no papers found")
        return
    
    print(f"✅ Found {len(papers)} papers")
    
    # Display all found papers
    for i, paper in enumerate(papers, 1):
        print(f"\n   📄 Paper {i}:")
        print(f"      ID: {paper.paper_id}")
        print(f"      Title: {paper.title[:80]}...")
        print(f"      Year: {paper.year}")
        print(f"      Authors: {', '.join(paper.authors[:2])}")
        print(f"      Citations: {paper.citation_count}")
        print(f"      Has Abstract: {'Yes' if paper.abstract else 'No'} ({len(paper.abstract)} chars)")
    
    # Test 2: Get details of each paper
    print("\n2️⃣ Testing get_paper_details for each paper...")
    print("-" * 60)
    
    successful = 0
    failed = 0
    
    for i, paper in enumerate(papers, 1):
        print(f"\n   Testing paper {i} (ID: {paper.paper_id})...")
        
        detailed = await core_api.get_paper_details(paper.paper_id)
        
        if detailed:
            successful += 1
            print(f"   ✅ SUCCESS")
            print(f"      Title: {detailed.title[:60]}...")
            print(f"      Authors: {len(detailed.authors)} authors")
            print(f"      Year: {detailed.year}")
            print(f"      DOI: {detailed.doi or 'N/A'}")
            print(f"      Abstract length: {len(detailed.abstract)} chars")
            print(f"      PDF URL: {'Available' if detailed.pdf_url else 'N/A'}")
            print(f"      Keywords: {len(detailed.keywords or [])} keywords")
            
            # Check if content is suitable for ingestion
            content_length = len(f"{detailed.title}\n\n{detailed.abstract}")
            print(f"      📊 Content for ingestion: {content_length} chars")
            
            if content_length > 100:
                print(f"      ✅ Suitable for vector store ingestion")
            else:
                print(f"      ⚠️  Content too short for meaningful ingestion")
        else:
            failed += 1
            print(f"   ❌ FAILED to get details")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 SUMMARY:")
    print(f"   Total papers tested: {len(papers)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Success rate: {(successful/len(papers)*100):.1f}%")
    
    if successful > 0:
        print("\n✅ CORE API get_paper_details is working!")
        print("\n💡 Next steps:")
        print("   1. Start the server: python -m uvicorn src.api.main:app --reload")
        print("   2. Test ingest endpoint:")
        print(f"      curl -X POST 'http://localhost:8000/api/papers/ingest-external?paper_id={papers[0].paper_id}&source=core'")
        print("   3. Or use the frontend 'Add to Collection' button")
    else:
        print("\n❌ All get_paper_details calls failed")
        print("   Check CORE API key and endpoint")


if __name__ == "__main__":
    asyncio.run(test_core_api_only())
