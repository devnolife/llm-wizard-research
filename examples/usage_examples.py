"""
Example usage script demonstrating the RAG-LLM system
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.glm_interface import GLMInterface, ModelConfig
from src.retrieval.vector_store import VectorStore, Document
from src.retrieval.rag_retriever import RAGRetriever
from src.agents.coordinator import CoordinatorAgent
from src.agents.research_analyzer import ResearchAnalyzerAgent
from src.agents.gap_detector import GapDetectorAgent
from src.agents.recommender import RecommenderAgent
from src.utils.config_loader import get_config

from loguru import logger


def example_basic_search():
    """Example: Basic semantic search"""
    print("\n" + "="*70)
    print("Example 1: Basic Semantic Search")
    print("="*70)
    
    # Initialize components
    config = get_config()
    vector_store = VectorStore(
        persist_directory=config.vector_db.persist_directory,
        collection_name=config.vector_db.collection_name
    )
    
    # Search
    query = "transformer attention mechanisms"
    results = vector_store.search(query, top_k=3)
    
    print(f"\n🔍 Query: {query}")
    print(f"📊 Found {len(results)} results:\n")
    
    for result in results:
        print(f"{result.rank}. {result.document.metadata.get('title', 'Untitled')}")
        print(f"   Score: {result.score:.3f}")
        print(f"   Content: {result.document.content[:150]}...")
        print()


def example_rag_retrieval():
    """Example: RAG retrieval with context"""
    print("\n" + "="*70)
    print("Example 2: RAG Retrieval with Context")
    print("="*70)
    
    # Initialize components
    config = get_config()
    vector_store = VectorStore(
        persist_directory=config.vector_db.persist_directory,
        collection_name=config.vector_db.collection_name
    )
    retriever = RAGRetriever(vector_store, top_k=3)
    
    # Retrieve with context
    query = "recent advances in language models"
    context, results = retriever.get_context_for_generation(query, max_tokens=1000)
    
    print(f"\n🔍 Query: {query}")
    print(f"📄 Generated context length: {len(context)} characters")
    print(f"📚 Retrieved {len(results)} documents\n")
    
    for result in results:
        print(f"{result.rank}. {result.document.metadata.get('title')}")
        print(f"   Relevance: {result.score:.3f}")


def example_multi_agent():
    """Example: Multi-agent research analysis"""
    print("\n" + "="*70)
    print("Example 3: Multi-Agent Research Analysis")
    print("="*70)
    
    # Initialize components
    config = get_config()
    vector_store = VectorStore(
        persist_directory=config.vector_db.persist_directory,
        collection_name=config.vector_db.collection_name
    )
    retriever = RAGRetriever(vector_store)
    
    # Initialize agents
    research_analyzer = ResearchAnalyzerAgent(retriever=retriever)
    gap_detector = GapDetectorAgent(retriever=retriever)
    recommender = RecommenderAgent(retriever=retriever)
    
    coordinator = CoordinatorAgent(
        research_analyzer=research_analyzer,
        gap_detector=gap_detector,
        recommender=recommender
    )
    
    # Process research query
    query = "graph neural networks for molecular property prediction"
    print(f"\n🔬 Research Query: {query}\n")
    
    results = coordinator.process_research_query(query)
    
    print("📊 Analysis Results:")
    if results.get("analysis"):
        analysis = results["analysis"]
        print(f"   Themes: {analysis.get('themes', [])}")
        print(f"   Key Papers: {len(analysis.get('key_papers', []))}")
    
    print("\n🔍 Detected Gaps:")
    if results.get("gaps"):
        gaps = results["gaps"]
        print(f"   Unexplored Areas: {len(gaps.get('unexplored_areas', []))}")
        print(f"   Methodological Gaps: {len(gaps.get('methodological_gaps', []))}")
    
    print("\n💡 Recommendations:")
    if results.get("recommendations"):
        recs = results["recommendations"].get("recommendations", [])
        for rec in recs[:3]:
            print(f"   {rec.get('rank')}. {rec.get('title')}")
            print(f"      Score: {rec.get('relevance_score', 0):.3f}")


def example_with_llm():
    """Example: Using GLM-4.6 for analysis"""
    print("\n" + "="*70)
    print("Example 4: LLM-Powered Analysis (Requires Ollama)")
    print("="*70)
    
    try:
        # Initialize GLM
        glm = GLMInterface()
        
        # Health check
        if not glm.health_check():
            print("⚠️  GLM-4.6 not available. Please ensure Ollama is running.")
            return
        
        print("✅ GLM-4.6 is available\n")
        
        # Analyze research
        paper_content = """
        Graph Neural Networks (GNNs) have emerged as a powerful tool for 
        learning on graph-structured data. They extend deep learning to 
        non-Euclidean domains by aggregating information from neighboring nodes.
        """
        
        print("📝 Analyzing paper content...\n")
        analysis = glm.analyze_research(paper_content)
        
        print("🤖 GLM-4.6 Analysis:")
        print(analysis[:500] + "..." if len(analysis) > 500 else analysis)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure Ollama is installed and running with GLM-4.6 model")


def main():
    """Run all examples"""
    logger.add("logs/examples.log")
    
    print("\n" + "="*70)
    print("RAG-LLM Research Recommendation System - Usage Examples")
    print("="*70)
    
    try:
        # Run examples
        example_basic_search()
        example_rag_retrieval()
        example_multi_agent()
        example_with_llm()
        
        print("\n" + "="*70)
        print("✅ All examples completed!")
        print("="*70)
        
        print("\n💡 Next Steps:")
        print("1. Try the API: python -m uvicorn src.api.main:app --reload")
        print("2. Visit docs: http://localhost:8000/docs")
        print("3. Ingest your papers: POST /api/ingest")
        print("4. Get recommendations: POST /api/recommend")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("- Ensure database is initialized: python scripts/init_db.py")
        print("- Check Ollama is running: ollama list")
        print("- Verify configuration: cat configs/config.yaml")


if __name__ == "__main__":
    main()
