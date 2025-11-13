"""
Test Full Workflow - RAG-LLM Research Recommendation System
Using llama3.2:latest model
"""
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
load_dotenv()

print("=" * 70)
print("🚀 RAG-LLM Research Recommendation System - Full Workflow Test")
print("=" * 70)
print(f"📍 Model: {os.getenv('OLLAMA_MODEL', 'llama3.2:latest')}")
print(f"📍 Ollama URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
print()

async def test_full_workflow():
    """Test complete workflow from LLM to RAG to Agents"""
    
    # ==============================================
    # 1. Test LLM Interface
    # ==============================================
    print("\n" + "="*70)
    print("📝 [1/6] Testing LLM Interface")
    print("="*70)
    
    try:
        from src.llm.glm_interface import GLMInterface
        
        llm = GLMInterface()
        health = await llm.health_check()
        
        if health["status"] == "healthy":
            print(f"✅ LLM initialized: {health['model']}")
            
            # Quick generation test
            response = llm.generate(
                prompt="What is deep learning? Answer in 20 words.",
                max_tokens=50,
                temperature=0.3
            )
            print(f"💬 LLM Response: {response[:100]}...")
        else:
            print(f"❌ LLM health check failed: {health}")
            return False
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ==============================================
    # 2. Test Vector Store
    # ==============================================
    print("\n" + "="*70)
    print("📚 [2/6] Testing Vector Store (ChromaDB)")
    print("="*70)
    
    try:
        from src.retrieval.vector_store import VectorStore, Document
        
        vector_store = VectorStore()
        
        # Add sample documents
        sample_docs = [
            Document(
                id="doc1",
                content="Transformers are neural network architectures that use self-attention mechanisms for sequence processing.",
                metadata={
                    "title": "Attention Is All You Need",
                    "authors": "Vaswani et al.",
                    "year": 2017,
                    "keywords": "transformers, attention, neural networks"
                }
            ),
            Document(
                id="doc2",
                content="BERT is a bidirectional encoder that learns contextualized word representations using masked language modeling.",
                metadata={
                    "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                    "authors": "Devlin et al.",
                    "year": 2018,
                    "keywords": "BERT, pre-training, language models"
                }
            ),
            Document(
                id="doc3",
                content="GPT models use autoregressive transformers for text generation and few-shot learning.",
                metadata={
                    "title": "Language Models are Few-Shot Learners",
                    "authors": "Brown et al.",
                    "year": 2020,
                    "keywords": "GPT, few-shot learning, generation"
                }
            )
        ]
        
        print(f"📝 Adding {len(sample_docs)} sample documents...")
        for doc in sample_docs:
            vector_store.add_document(doc)
        
        # Test search
        query = "What are transformer models?"
        print(f"\n🔍 Testing search: '{query}'")
        results = vector_store.search(query, top_k=2)
        
        print(f"✅ Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            title = result.document.metadata.get('title', 'N/A') if result.document.metadata else 'N/A'
            print(f"   {i}. {title} (score: {result.score:.3f})")
            print(f"      Content: {result.document.content[:80]}...")
        
    except Exception as e:
        print(f"❌ Vector Store test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ==============================================
    # 3. Test RAG Retriever
    # ==============================================
    print("\n" + "="*70)
    print("🔎 [3/6] Testing RAG Retriever")
    print("="*70)
    
    try:
        from src.retrieval.rag_retriever import RAGRetriever
        
        retriever = RAGRetriever(vector_store=vector_store)
        
        query = "How does BERT differ from GPT?"
        print(f"🔍 Query: '{query}'")
        
        results = retriever.retrieve(query, top_k=2)
        print(f"✅ Retrieved {len(results)} documents")
        
        for i, result in enumerate(results, 1):
            title = result.document.metadata.get('title', 'N/A') if result.document.metadata else 'N/A'
            print(f"   {i}. {title}")
        
    except Exception as e:
        print(f"❌ RAG Retriever test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ==============================================
    # 4. Test Knowledge Graph
    # ==============================================
    print("\n" + "="*70)
    print("🕸️  [4/6] Testing Knowledge Graph")
    print("="*70)
    
    try:
        from src.knowledge_graph.graph_builder import KnowledgeGraphBuilder
        
        kg = KnowledgeGraphBuilder()
        
        # Add papers
        from src.knowledge_graph.graph_builder import PaperNode
        
        papers = [
            PaperNode(paper_id="paper1", title="Attention Is All You Need", authors=["Vaswani"], year=2017),
            PaperNode(paper_id="paper2", title="BERT", authors=["Devlin"], year=2018),
            PaperNode(paper_id="paper3", title="GPT-3", authors=["Brown"], year=2020)
        ]
        
        for paper in papers:
            kg.add_paper(paper)
        
        # Add citations
        kg.add_citation("paper2", "paper1")  # BERT cites Transformers
        kg.add_citation("paper3", "paper1")  # GPT-3 cites Transformers
        
        # Get stats
        stats = kg.get_stats()
        print(f"✅ Graph created:")
        print(f"   📄 Papers: {stats['num_papers']}")
        print(f"   🔗 Citations: {stats['num_citations']}")
        
        # Find influential papers
        influential = kg.get_most_influential_papers(top_k=2)
        print(f"   🌟 Most influential: {[p[0] for p in influential]}")
        
    except Exception as e:
        print(f"❌ Knowledge Graph test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ==============================================
    # 5. Test Research Analyzer Agent
    # ==============================================
    print("\n" + "="*70)
    print("🤖 [5/6] Testing Research Analyzer Agent")
    print("="*70)
    
    try:
        from src.agents.research_analyzer import ResearchAnalyzerAgent
        
        analyzer = ResearchAnalyzerAgent(llm=llm, retriever=retriever)
        
        query = "transformer architectures in NLP"
        print(f"🔍 Analyzing: '{query}'")
        
        analysis = analyzer.analyze(query)
        
        print(f"✅ Analysis completed:")
        print(f"   📊 Themes: {len(analysis.get('themes', []))} found")
        print(f"   🔬 Methodologies: {len(analysis.get('methodologies', []))} found")
        if analysis.get('summary'):
            print(f"   📝 Summary: {analysis['summary'][:100]}...")
        
    except Exception as e:
        print(f"❌ Research Analyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ==============================================
    # 6. Test Recommendation Engine
    # ==============================================
    print("\n" + "="*70)
    print("💡 [6/6] Testing Recommendation Engine")
    print("="*70)
    
    try:
        from src.recommendation.engine import RecommendationEngine
        from src.gap_detection.analyzer import GapAnalyzer
        
        gap_analyzer = GapAnalyzer(
            vector_store=vector_store,
            knowledge_graph=kg,
            llm=llm
        )
        
        rec_engine = RecommendationEngine(
            retriever=retriever,
            knowledge_graph=kg,
            gap_analyzer=gap_analyzer
        )
        
        query = "attention mechanisms"
        print(f"🔍 Getting recommendations for: '{query}'")
        
        recommendations = rec_engine.recommend(
            query=query,
            strategy="hybrid",
            top_k=3
        )
        
        print(f"✅ Generated {len(recommendations)} recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. Score: {rec.score:.3f}")
            print(f"      Reason: {rec.reason}")
        
    except Exception as e:
        print(f"❌ Recommendation Engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ==============================================
    # Summary
    # ==============================================
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED! System is ready!")
    print("="*70)
    print("\n📊 System Components Status:")
    print("   ✅ LLM Interface (llama3.2:latest)")
    print("   ✅ Vector Store (ChromaDB)")
    print("   ✅ RAG Retriever")
    print("   ✅ Knowledge Graph")
    print("   ✅ Research Analyzer Agent")
    print("   ✅ Recommendation Engine")
    print("\n🚀 Next Steps:")
    print("   1. Start API server: uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
    print("   2. Upload PDF papers to data/raw/")
    print("   3. Ingest papers: POST /api/ingest")
    print("   4. Try search: GET /api/search?query=your_query")
    print("   5. Get recommendations: GET /api/recommend?query=your_topic")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_full_workflow())
    exit(0 if success else 1)
