#!/usr/bin/env python3
"""
Main process - Jalankan semua proses utama sistem wizard-research
Menggunakan API endpoints untuk menghindari import issues
"""

import requests
import json
from pathlib import Path
from typing import List, Dict, Any


class WizardResearchSystem:
    """Main system untuk menjalankan semua proses via API"""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        print("🔧 Initializing Wizard Research System...")
        self.api_url = api_url
        
        # Check if API is running
        try:
            response = requests.get(f"{self.api_url}/api/stats")
            if response.status_code == 200:
                print("✅ API connection OK!\n")
            else:
                print("⚠️  API responded with non-200 status\n")
        except Exception as e:
            print(f"❌ Cannot connect to API at {api_url}")
            print(f"   Error: {e}")
            print("   Make sure the API is running: uvicorn src.api.main:app --reload\n")
            raise
    
    def check_database_status(self) -> bool:
        """Check status database"""
        print("=" * 80)
        print("📊 DATABASE STATUS")
        print("=" * 80)
        
        try:
            response = requests.get(f"{self.api_url}/api/stats")
            response.raise_for_status()
            stats = response.json()
            
            print(f"Total documents: {stats.get('total_documents', 0)}")
            print(f"Embedding model: {stats.get('embedding_model', 'unknown')}")
            print(f"Dimensions: {stats.get('embedding_dimensions', 'unknown')}")
            print()
            
            return stats.get('total_documents', 0) > 0
        except Exception as e:
            print(f"❌ Error getting stats: {e}\n")
            return False
    
    def ingest_pdfs(self, pdf_paths: List[str]):
        """Proses 1: Ingest PDF files via API"""
        print("=" * 80)
        print("📄 PROCESS 1: PDF INGESTION")
        print("=" * 80)
        
        for pdf_path in pdf_paths:
            if not Path(pdf_path).exists():
                print(f"❌ File not found: {pdf_path}")
                continue
            
            print(f"\nProcessing: {pdf_path}")
            
            try:
                with open(pdf_path, 'rb') as f:
                    files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
                    response = requests.post(
                        f"{self.api_url}/api/ingest",
                        files=files
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    print(f"  ✓ Chunks created: {result.get('chunks_created', 0)}")
                    print(f"  ✓ Status: {result.get('message', 'OK')}")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print("\n✅ Ingestion complete!\n")
    
    def detect_gaps(self, topic: str) -> Dict[str, Any]:
        """Proses 2: Gap Detection via API"""
        print("=" * 80)
        print("🔍 PROCESS 2: GAP DETECTION")
        print("=" * 80)
        print(f"Topic: {topic}\n")
        
        print("Analyzing research gaps (this may take a while)...")
        
        try:
            response = requests.post(
                f"{self.api_url}/api/gaps",
                json={"topic": topic}
            )
            response.raise_for_status()
            result = response.json()
            
            gaps = result.get('gaps', [])
            print(f"\n✅ Detected {len(gaps)} research gaps:\n")
            
            for i, gap in enumerate(gaps, 1):
                print(f"{i}. {gap.get('area', 'Unknown Area')}")
                print(f"   Description: {gap.get('description', 'N/A')}")
                print(f"   Confidence: {gap.get('confidence', 0):.2f}")
                if gap.get('suggestions'):
                    print(f"   Suggestions: {gap.get('suggestions')}")
                print()
            
            return result
            
        except Exception as e:
            print(f"❌ Error in gap detection: {e}")
            return None
    
    def generate_recommendations(self, query: str) -> Dict[str, Any]:
        """Proses 3: Generate Recommendations via API"""
        print("=" * 80)
        print("💡 PROCESS 3: RECOMMENDATIONS")
        print("=" * 80)
        print(f"Query: {query}\n")
        
        print("Generating recommendations...")
        
        try:
            response = requests.post(
                f"{self.api_url}/api/recommend",
                json={"query": query}
            )
            response.raise_for_status()
            result = response.json()
            
            # Display recommendations
            recommendations = result.get('recommendations', [])
            print(f"\n✅ Generated {len(recommendations)} recommendations:\n")
            
            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    print(f"{i}. {rec.get('title', 'Unknown')}")
                    print(f"   Relevance: {rec.get('relevance_score', 0):.2f}")
                    print(f"   Reason: {rec.get('reason', 'N/A')}")
                    print()
            else:
                print("   (No recommendations found)\n")
            
            # Display themes
            themes = result.get('themes', [])
            if themes:
                print(f"🎯 Key Themes ({len(themes)}):")
                for theme in themes:
                    print(f"   • {theme}")
                print()
            
            # Display methodologies
            methodologies = result.get('methodologies', [])
            if methodologies:
                print(f"🔬 Methodologies ({len(methodologies)}):")
                for method in methodologies:
                    print(f"   • {method}")
                print()
            
            return result
            
        except Exception as e:
            print(f"❌ Error in recommendations: {e}")
            return None
    
    def rag_query(self, question: str) -> str:
        """Proses 4: RAG Q&A via API"""
        print("=" * 80)
        print("💬 PROCESS 4: RAG Q&A")
        print("=" * 80)
        print(f"Question: {question}\n")
        
        print("Retrieving context and generating answer...")
        
        try:
            response = requests.post(
                f"{self.api_url}/api/chat",
                json={"query": question}
            )
            response.raise_for_status()
            result = response.json()
            
            answer = result.get('answer', 'No answer generated')
            sources = result.get('sources', [])
            
            print(f"\n✅ Answer:\n")
            print(answer)
            print()
            
            if sources:
                print(f"📚 Sources ({len(sources)}):")
                for i, source in enumerate(sources[:3], 1):
                    print(f"   {i}. {source.get('metadata', {}).get('source', 'Unknown')}")
                print()
            
            return answer
            
        except Exception as e:
            print(f"❌ Error in RAG: {e}")
            return None
    
    def search_papers(self, query: str, top_k: int = 5) -> List[Dict]:
        """Bonus: Search papers in database"""
        print("=" * 80)
        print("🔎 BONUS: SEARCH PAPERS")
        print("=" * 80)
        print(f"Query: {query}\n")
        
        try:
            response = requests.post(
                f"{self.api_url}/api/search",
                json={"query": query, "top_k": top_k}
            )
            response.raise_for_status()
            result = response.json()
            
            results = result.get('results', [])
            print(f"\n✅ Found {len(results)} results:\n")
            
            for i, res in enumerate(results, 1):
                print(f"{i}. Score: {res.get('score', 0):.4f}")
                print(f"   Source: {res.get('metadata', {}).get('source', 'Unknown')}")
                print(f"   Content: {res.get('content', '')[:150]}...")
                print()
            
            return results
            
        except Exception as e:
            print(f"❌ Error in search: {e}")
            return []


def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("🧙 WIZARD RESEARCH SYSTEM - MAIN PROCESS")
    print("=" * 80 + "\n")
    
    try:
        # Initialize system (connect to API)
        system = WizardResearchSystem()
        
        # Check database status
        has_data = system.check_database_status()
        
        if not has_data:
            print("⚠️  Database kosong. Perlu ingest PDF dulu.\n")
            
            # Example: Ingest PDFs from data/raw/
            pdf_dir = Path("data/raw")
            if pdf_dir.exists():
                pdf_files = list(pdf_dir.glob("*.pdf"))
                if pdf_files:
                    print(f"Found {len(pdf_files)} PDFs in {pdf_dir}")
                    print("Ingest PDFs? (y/n): ", end='')
                    response = input()
                    if response.lower() == 'y':
                        system.ingest_pdfs([str(p) for p in pdf_files[:3]])  # Limit to 3
                        has_data = True
            
            if not has_data:
                print("❌ No data to process. Exiting.")
                return
        
        # Main processes
        print("\n🚀 Starting main processes...\n")
        
        # 1. Search test
        print("Testing search functionality first...\n")
        system.search_papers("machine learning", top_k=3)
        
        # 2. Gap Detection
        topic = "machine learning"
        gaps = system.detect_gaps(topic)
        
        # 3. Recommendations
        query = "deep learning applications"
        recommendations = system.generate_recommendations(query)
        
        # 4. RAG Q&A
        question = "What are the main challenges in deep learning research?"
        answer = system.rag_query(question)
        
        print("=" * 80)
        print("✅ ALL PROCESSES COMPLETED")
        print("=" * 80)
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure the API server is running:")
        print("  uvicorn src.api.main:app --reload")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
