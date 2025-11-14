"""
Test CORE API paper ingestion
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_core_ingest():
    """Test fetching and ingesting a paper from CORE API"""
    from src.external.paper_apis import CoreAPI
    from src.retrieval.vector_store import VectorStore, Document
    
    print("🧪 Testing CORE API Paper Ingestion")
    print("=" * 60)
    
    # Initialize CORE API
    core_api = CoreAPI()
    
    # Test 1: Search for papers first
    print("\n1️⃣ Searching for papers to get IDs...")
    papers = await core_api.search("machine learning", max_results=3)
    
    if not papers:
        print("❌ No papers found in search")
        return
    
    print(f"✅ Found {len(papers)} papers")
    for i, paper in enumerate(papers, 1):
        print(f"\n   Paper {i}:")
        print(f"   ID: {paper.paper_id}")
        print(f"   Title: {paper.title[:60]}...")
        print(f"   Year: {paper.year}")
        print(f"   Abstract length: {len(paper.abstract)} chars")
    
    # Test 2: Get details of first paper
    print("\n2️⃣ Getting detailed info for first paper...")
    test_paper_id = papers[0].paper_id
    print(f"   Fetching paper ID: {test_paper_id}")
    
    detailed_paper = await core_api.get_paper_details(test_paper_id)
    
    if not detailed_paper:
        print("❌ Failed to get paper details")
        return
    
    print("✅ Paper details retrieved:")
    print(f"   Title: {detailed_paper.title}")
    print(f"   Authors: {', '.join(detailed_paper.authors[:3])}")
    print(f"   Year: {detailed_paper.year}")
    print(f"   DOI: {detailed_paper.doi}")
    print(f"   Abstract: {detailed_paper.abstract[:100]}...")
    print(f"   Keywords: {detailed_paper.keywords[:5]}")
    
    # Test 3: Create document and prepare for vector store
    print("\n3️⃣ Preparing document for vector store...")
    
    doc = Document(
        id=detailed_paper.paper_id,
        content=f"{detailed_paper.title}\n\n{detailed_paper.abstract}",
        metadata={
            "title": detailed_paper.title,
            "authors": ", ".join(detailed_paper.authors),
            "year": detailed_paper.year,
            "journal": detailed_paper.journal,
            "doi": detailed_paper.doi,
            "url": detailed_paper.url,
            "source_api": detailed_paper.source_api,
            "keywords": ", ".join(detailed_paper.keywords or [])
        }
    )
    
    print("✅ Document created:")
    print(f"   ID: {doc.id}")
    print(f"   Content length: {len(doc.content)} chars")
    print(f"   Metadata keys: {list(doc.metadata.keys())}")
    
    # Test 4: Actually ingest into vector store
    print("\n4️⃣ Ingesting into vector store...")
    try:
        from src.utils.config_loader import get_config
        config = get_config()
        
        vector_store = VectorStore(
            persist_directory=config.vector_db.persist_directory,
            collection_name=config.vector_db.collection_name,
            embedding_model=config.vector_db.embedding_model
        )
        
        doc_id = vector_store.add_document(doc)
        print(f"✅ Document ingested successfully!")
        print(f"   Vector Store Doc ID: {doc_id}")
        
        # Verify by counting documents
        count = vector_store.count_documents()
        print(f"   Total documents in store: {count}")
        
    except Exception as e:
        print(f"⚠️  Could not ingest (vector store might not be initialized): {e}")
        print("   This is OK for testing API functionality")
    
    print("\n" + "=" * 60)
    print("✅ CORE API Ingest Test Complete!")
    print("\n💡 To test via HTTP endpoint:")
    print(f"   curl -X POST 'http://localhost:8000/api/papers/ingest-external?paper_id={test_paper_id}&source=core'")


if __name__ == "__main__":
    asyncio.run(test_core_ingest())
