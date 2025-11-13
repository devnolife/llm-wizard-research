"""
Test CORE API Integration
Run this after you add CORE_API_KEY to .env file
"""
import asyncio
import os
from dotenv import load_dotenv
from src.external.paper_apis import AggregatedPaperAPI

load_dotenv()

async def test_core_api():
    """Test CORE API with your API key"""
    
    print("="*70)
    print("🧪 Testing CORE API Integration")
    print("="*70)
    
    # Check if API key exists
    api_key = os.getenv("CORE_API_KEY")
    if not api_key:
        print("\n❌ CORE_API_KEY not found in .env file!")
        print("\n📝 To get CORE API key:")
        print("   1. Visit: https://core.ac.uk/services/api")
        print("   2. Sign up (free)")
        print("   3. Get API key (10,000 requests/day free)")
        print("   4. Add to .env: CORE_API_KEY=your_key_here")
        return
    
    print(f"\n✅ API Key found: {api_key[:10]}...{api_key[-5:]}")
    
    # Initialize API
    api = AggregatedPaperAPI(core_key=api_key)
    
    # Test queries
    test_queries = [
        "machine learning",
        "deep learning neural networks",
        "natural language processing"
    ]
    
    for query in test_queries:
        print(f"\n" + "-"*70)
        print(f"🔍 Query: '{query}'")
        print("-"*70)
        
        try:
            results = await api.core.search(query, max_results=5)
            
            if results:
                print(f"✅ Found {len(results)} papers from CORE")
                for i, paper in enumerate(results, 1):
                    print(f"\n{i}. {paper.title}")
                    print(f"   Authors: {', '.join(paper.authors[:3])}")
                    print(f"   Year: {paper.year}")
                    if paper.doi:
                        print(f"   DOI: {paper.doi}")
                    if paper.citation_count:
                        print(f"   Citations: {paper.citation_count}")
            else:
                print("⚠️  No results found")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test aggregated search
    print(f"\n" + "="*70)
    print("🔄 Testing Aggregated Search (CORE + arXiv + CrossRef)")
    print("="*70)
    
    try:
        results = await api.search_all(
            query="transformer neural networks",
            max_results_per_source=3,
            sources=["core", "arxiv", "crossref"]
        )
        
        for source, papers in results.items():
            print(f"\n📚 {source.upper()}: {len(papers)} papers")
            for paper in papers[:2]:
                print(f"   - {paper.title[:70]}...")
        
        # Deduplicate
        unique = api.deduplicate_papers(results)
        print(f"\n✨ After deduplication: {len(unique)} unique papers")
        
    except Exception as e:
        print(f"❌ Aggregated search error: {e}")
    
    print("\n" + "="*70)
    print("✅ CORE API Test Complete!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_core_api())
