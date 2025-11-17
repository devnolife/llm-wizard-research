#!/usr/bin/env python3
"""
Pure Python - Run directly from src/ to avoid import issues
NO API, NO HTTP calls, just direct function calls
"""

import sys
import os

# Set working directory to project root
os.chdir('/home/devnolife/wizard-research')
sys.path.insert(0, '/home/devnolife/wizard-research')

print("\n" + "=" * 80)
print("🧙 WIZARD RESEARCH - PURE PYTHON NO API")
print("=" * 80 + "\n")

# Import everything we need
print("📦 Loading modules...")
from src.utils.config_loader import get_config
from src.utils.document_processor import DocumentProcessor
from src.retrieval.vector_store import VectorStore
from src.llm.glm_interface import GLMInterface
print("✓ Modules loaded\n")

# Initialize
print("🔧 Initializing components...")
config = get_config()
print(f"✓ Config: {config.llm.model_name}")

vector_store = VectorStore(
    persist_directory=config.vector_db.persist_directory,
    collection_name=config.vector_db.collection_name,
    embedding_model=config.vector_db.embedding_model,
    distance_metric=config.vector_db.distance_metric
)
print(f"✓ Vector store: {vector_store.collection.count()} documents")

llm = GLMInterface()
print(f"✓ LLM: {config.llm.model_name}")
print()

# ============================================================================
# TEST 1: Database Status
# ============================================================================
print("=" * 80)
print("📊 TEST 1: DATABASE STATUS")
print("=" * 80)

stats = vector_store.get_stats()
print(f"Total documents: {stats['total_documents']}")
print(f"Embedding model: {stats['embedding_model']}")
print(f"Collection: {stats['collection_name']}")
print()

# ============================================================================
# TEST 2: Search
# ============================================================================
print("=" * 80)
print("🔍 TEST 2: SEARCH")
print("=" * 80)

query = "machine learning"
print(f"Query: '{query}'\n")

results = vector_store.search(query, top_k=5)
print(f"✓ Found {len(results)} results:\n")

for i, result in enumerate(results[:3], 1):
    print(f"{i}. Score: {result.score:.4f}")
    print(f"   Content: {result.document.content[:150]}...")
    print(f"   Source: {result.document.metadata.get('file_name', 'unknown')}")
    print()

# ============================================================================
# TEST 3: RAG Q&A (with LLM)
# ============================================================================
print("=" * 80)
print("💬 TEST 3: RAG Q&A")
print("=" * 80)

question = "What is deep learning and how does it differ from traditional machine learning?"
print(f"Question: {question}\n")

# Step 1: Retrieve relevant documents
print("→ Retrieving relevant documents...")
search_results = vector_store.search(question, top_k=5)
print(f"  Found {len(search_results)} documents\n")

# Step 2: Build context
context_parts = []
for i, res in enumerate(search_results[:3], 1):
    context_parts.append(f"[Document {i}]\n{res.document.content[:500]}\n")

context = "\n".join(context_parts)

# Step 3: Generate answer with LLM
print(f"→ Generating answer with {config.llm.model_name}...\n")

prompt = f"""Based on the following research documents, please answer the question.

Context:
{context}

Question: {question}

Answer:"""

try:
    answer = llm.generate(prompt, max_tokens=500)
    print("✓ Answer:")
    print("-" * 80)
    print(answer)
    print("-" * 80)
    print()
except Exception as e:
    print(f"✗ Error generating answer: {e}")
    print()

# ============================================================================
# TEST 4: Simple Gap Detection (without complex agents)
# ============================================================================
print("=" * 80)
print("🔍 TEST 4: GAP DETECTION")
print("=" * 80)

topic = "neural networks"
print(f"Topic: '{topic}'\n")

# Retrieve documents about the topic
print(f"→ Analyzing research on {topic}...")
docs = vector_store.search(topic, top_k=10)
print(f"  Found {len(docs)} related documents\n")

# Analyze with LLM
doc_contents = "\n\n".join([d.document.content[:300] for d in docs[:5]])

gap_prompt = f"""Analyze the following research documents about {topic} and identify 3 specific research gaps or unexplored areas.

Documents:
{doc_contents}

Identify 3 research gaps in this format:
1. [Gap Area]: [Description]
2. [Gap Area]: [Description]
3. [Gap Area]: [Description]

Gaps:"""

try:
    print(f"→ Analyzing with {config.llm.model_name}...\n")
    gaps_response = llm.generate(gap_prompt, max_tokens=400)
    print("✓ Research Gaps:")
    print("-" * 80)
    print(gaps_response)
    print("-" * 80)
    print()
except Exception as e:
    print(f"✗ Error detecting gaps: {e}")
    print()

# ============================================================================
# TEST 5: Simple Recommendations
# ============================================================================
print("=" * 80)
print("💡 TEST 5: RECOMMENDATIONS")
print("=" * 80)

interest = "computer vision applications"
print(f"Research Interest: '{interest}'\n")

# Find related papers
print(f"→ Finding papers related to {interest}...")
papers = vector_store.search(interest, top_k=8)
print(f"  Found {len(papers)} papers\n")

# Get recommendations from LLM
papers_summary = "\n".join([
    f"{i+1}. Score: {p.score:.3f} | {p.document.content[:200]}..."
    for i, p in enumerate(papers[:5])
])

rec_prompt = f"""Based on these research papers about {interest}, recommend 3 specific research directions or paper topics that would be valuable to explore.

Papers:
{papers_summary}

Provide 3 recommendations in this format:
1. [Topic]: [Why it's valuable]
2. [Topic]: [Why it's valuable]
3. [Topic]: [Why it's valuable]

Recommendations:"""

try:
    print(f"→ Generating recommendations with {config.llm.model_name}...\n")
    recommendations = llm.generate(rec_prompt, max_tokens=400)
    print("✓ Recommendations:")
    print("-" * 80)
    print(recommendations)
    print("-" * 80)
    print()
except Exception as e:
    print(f"✗ Error generating recommendations: {e}")
    print()

# ============================================================================
# DONE
# ============================================================================
print("=" * 80)
print("✅ ALL TESTS COMPLETED - NO API USED!")
print("=" * 80)
print()
