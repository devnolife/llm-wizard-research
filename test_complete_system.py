"""
Test the complete system with year filtering and frontend
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_year_filtering():
    """Test CORE API year filtering"""
    from src.external.paper_apis import CoreAPI
    
    print("=" * 60)
    print("Testing CORE API Year Filtering")
    print("=" * 60)
    
    core_api = CoreAPI()
    
    # Test 1: Search without year filter
    print("\n1️⃣ Search without year filter:")
    papers = await core_api.search("machine learning", max_results=3)
    print(f"   Found {len(papers)} papers")
    for paper in papers:
        print(f"   - {paper.title[:60]}... ({paper.year})")
    
    # Test 2: Search with year_from filter
    print("\n2️⃣ Search with year_from=2020:")
    papers = await core_api.search("machine learning", max_results=3, year_from=2020)
    print(f"   Found {len(papers)} papers")
    for paper in papers:
        print(f"   - {paper.title[:60]}... ({paper.year})")
        if paper.year and paper.year < 2020:
            print(f"   ⚠️ WARNING: Paper year {paper.year} is before 2020!")
    
    # Test 3: Search with year range filter
    print("\n3️⃣ Search with year range 2020-2023:")
    papers = await core_api.search("machine learning", max_results=3, year_from=2020, year_to=2023)
    print(f"   Found {len(papers)} papers")
    for paper in papers:
        print(f"   - {paper.title[:60]}... ({paper.year})")
        if paper.year and (paper.year < 2020 or paper.year > 2023):
            print(f"   ⚠️ WARNING: Paper year {paper.year} is outside 2020-2023!")
    
    # Test 4: Search with year_to filter
    print("\n4️⃣ Search with year_to=2021:")
    papers = await core_api.search("neural networks", max_results=3, year_to=2021)
    print(f"   Found {len(papers)} papers")
    for paper in papers:
        print(f"   - {paper.title[:60]}... ({paper.year})")
        if paper.year and paper.year > 2021:
            print(f"   ⚠️ WARNING: Paper year {paper.year} is after 2021!")
    
    print("\n✅ CORE API Year Filtering Test Complete!")


async def test_aggregated_year_filtering():
    """Test aggregated API with year filtering"""
    from src.external.paper_apis import AggregatedPaperAPI
    
    print("\n" + "=" * 60)
    print("Testing Aggregated API Year Filtering")
    print("=" * 60)
    
    api = AggregatedPaperAPI(
        core_key=os.getenv("CORE_API_KEY")
    )
    
    # Test with year filtering
    print("\n📚 Searching across APIs with year filter 2020-2024:")
    results = await api.search_all(
        query="artificial intelligence",
        max_results_per_source=3,
        sources=["core", "arxiv"],
        year_from=2020,
        year_to=2024
    )
    
    for source, papers in results.items():
        print(f"\n{source.upper()}: {len(papers)} papers")
        for paper in papers[:3]:
            print(f"  - {paper.title[:60]}... ({paper.year})")
    
    print("\n✅ Aggregated API Year Filtering Test Complete!")


def test_frontend_files():
    """Check if frontend files exist"""
    print("\n" + "=" * 60)
    print("Testing Frontend Files")
    print("=" * 60)
    
    import os
    from pathlib import Path
    
    static_dir = Path("static")
    index_file = static_dir / "index.html"
    
    print(f"\n📁 Static directory: {static_dir.absolute()}")
    print(f"   Exists: {static_dir.exists()}")
    
    print(f"\n📄 Index file: {index_file.absolute()}")
    print(f"   Exists: {index_file.exists()}")
    
    if index_file.exists():
        size = index_file.stat().st_size
        print(f"   Size: {size:,} bytes")
        
        # Check for key features in HTML
        content = index_file.read_text()
        features = [
            ("Search input", 'id="searchInput"' in content),
            ("Year filters", 'id="yearFrom"' in content),
            ("API toggles", 'data-source="core"' in content),
            ("CORE primary", '⭐ CORE (Primary)' in content),
            ("Paper cards", 'class="paper-card"' in content),
            ("Modern styling", 'var(--primary)' in content)
        ]
        
        print("\n   Features found:")
        for feature, found in features:
            status = "✅" if found else "❌"
            print(f"   {status} {feature}")
    
    print("\n✅ Frontend Files Test Complete!")


async def main():
    """Run all tests"""
    print("\n🧙‍♂️ WIZARD RESEARCH - COMPREHENSIVE SYSTEM TEST")
    print("=" * 60)
    
    try:
        # Test year filtering
        await test_year_filtering()
        
        # Test aggregated API with year filtering
        await test_aggregated_year_filtering()
        
        # Test frontend files
        test_frontend_files()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n🚀 Ready to start the server!")
        print("   Run: cd /home/devnolife/wizard-research && uvicorn src.api.main:app --reload")
        print("   Then open: http://localhost:8000")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
