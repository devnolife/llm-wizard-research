"""
Test CORE API integration in paper_apis.py
"""
import asyncio
import os
from dotenv import load_dotenv
from src.external.paper_apis import CoreAPI, AggregatedPaperAPI

load_dotenv()

async def test_core_api():
    print("=" * 70)
    print("Testing CORE API Integration")
    print("=" * 70)
    
    # Test 1: Basic search
    print("\n1. Testing basic CORE API search...")
    core = CoreAPI()
    papers = await core.search("machine learning", max_results=5)
    
    print(f"   ✅ Found {len(papers)} papers")
    if papers:
        print(f"\n   Example paper:")
        print(f"   Title: {papers[0].title[:80]}...")
        print(f"   Authors: {', '.join(papers[0].authors[:3])}")
        print(f"   Year: {papers[0].year}")
        print(f"   DOI: {papers[0].doi}")
    
    # Test 2: Search with year filter
    print("\n2. Testing search with year filter...")
    papers_filtered = await core.search(
        "deep learning",
        max_results=5,
        year_from=2020,
        year_to=2023
    )
    
    print(f"   ✅ Found {len(papers_filtered)} papers (2020-2023)")
    if papers_filtered:
        years = [p.year for p in papers_filtered if p.year]
        print(f"   Years: {years}")
    
    # Test 3: Aggregated search (including CORE)
    print("\n3. Testing aggregated search with CORE...")
    aggregated = AggregatedPaperAPI()
    all_results = await aggregated.search_all(
        "transformer neural networks",
        max_results_per_source=3,
        sources=["core", "arxiv"]  # Test only CORE and arXiv
    )
    
    for source, papers in all_results.items():
        print(f"   {source}: {len(papers)} papers")
    
    total = sum(len(papers) for papers in all_results.values())
    print(f"   ✅ Total: {total} papers retrieved")
    
    # Test 4: Get specific paper details
    if papers and papers[0].paper_id:
        print(f"\n4. Testing get_paper_details...")
        paper_id = papers[0].paper_id
        print(f"   Fetching details for paper ID: {paper_id}")
        
        paper_details = await core.get_paper_details(paper_id)
        if paper_details:
            print(f"   ✅ Successfully retrieved paper details")
            print(f"   Title: {paper_details.title[:80]}...")
        else:
            print(f"   ⚠️  Could not retrieve paper details")
    
    print("\n" + "=" * 70)
    print("✨ All CORE API tests completed!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_core_api())
