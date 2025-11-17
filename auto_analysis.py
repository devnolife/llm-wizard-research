#!/usr/bin/env python3
"""
Auto Analysis - Extract topics dari PDF dan generate insights otomatis
Tidak perlu input manual query/keywords
"""

import sys
import os
os.chdir('/home/devnolife/wizard-research')
sys.path.insert(0, '/home/devnolife/wizard-research')

print("\n" + "=" * 80)
print("🧙 AUTO ANALYSIS - Ekstrak Topics & Generate Insights Otomatis")
print("=" * 80 + "\n")

# Import modules
from src.utils.config_loader import get_config
from src.retrieval.vector_store import VectorStore
from src.llm.glm_interface import GLMInterface

# Initialize
config = get_config()
print(f"✓ Config loaded: {config.llm.model_name}")

vector_store = VectorStore(
    persist_directory=config.vector_db.persist_directory,
    collection_name=config.vector_db.collection_name,
    embedding_model=config.vector_db.embedding_model,
    distance_metric=config.vector_db.distance_metric
)
print(f"✓ Vector store: {vector_store.collection.count()} documents")

llm = GLMInterface()
print(f"✓ LLM initialized\n")

# ============================================================================
# STEP 1: Auto-Extract Topics dari Database
# ============================================================================
print("=" * 80)
print("📚 STEP 1: AUTO-EXTRACT TOPICS FROM DATABASE")
print("=" * 80)
print()

# Sample documents from database
print("→ Sampling documents from database...")
all_docs = vector_store.collection.get(limit=50)  # Get 50 random docs

# Combine content
sample_contents = []
for i, content in enumerate(all_docs['documents'][:20]):  # Use first 20
    sample_contents.append(content[:300])  # First 300 chars

combined_sample = "\n\n".join(sample_contents)

# Extract topics with LLM
print("→ Analyzing content with LLM to extract main topics...\n")

topic_prompt = f"""Analyze the following research document excerpts and extract the 5 main research topics/areas being discussed.

Document excerpts:
{combined_sample}

List only the topic names, one per line, without numbering or explanation.
Format: Just the topic name

Topics:"""

topics_response = llm.generate(topic_prompt, max_tokens=200)
topics = [t.strip() for t in topics_response.strip().split('\n') if t.strip() and len(t.strip()) > 3]

print("✓ Extracted Topics:")
print("-" * 80)
for i, topic in enumerate(topics[:5], 1):
    print(f"{i}. {topic}")
print("-" * 80)
print()

# ============================================================================
# STEP 2: Auto-Generate Research Summary
# ============================================================================
print("=" * 80)
print("📊 STEP 2: AUTO-GENERATE RESEARCH SUMMARY")
print("=" * 80)
print()

if topics:
    main_topic = topics[0]
    print(f"→ Analyzing main topic: '{main_topic}'...\n")
    
    # Get documents about main topic
    topic_docs = vector_store.search(main_topic, top_k=15)
    
    # Build summary
    doc_contents = "\n\n".join([f"Document {i+1}:\n{d.document.content[:400]}" 
                                for i, d in enumerate(topic_docs[:8])])
    
    summary_prompt = f"""Based on these research documents about {main_topic}, provide a comprehensive summary of:
1. Current state of research
2. Main methodologies being used
3. Key findings or trends

Documents:
{doc_contents}

Summary:"""
    
    print(f"→ Generating summary with {config.llm.model_name}...\n")
    summary = llm.generate(summary_prompt, max_tokens=500)
    
    print("✓ Research Summary:")
    print("-" * 80)
    print(summary)
    print("-" * 80)
    print()

# ============================================================================
# STEP 3: Auto-Detect Research Gaps
# ============================================================================
print("=" * 80)
print("🔍 STEP 3: AUTO-DETECT RESEARCH GAPS")
print("=" * 80)
print()

for i, topic in enumerate(topics[:3], 1):  # Analyze top 3 topics
    print(f"[{i}/{min(3, len(topics))}] Topic: '{topic}'")
    print()
    
    # Get documents about this topic
    topic_docs = vector_store.search(topic, top_k=10)
    
    if not topic_docs:
        print(f"  ⚠ No documents found for '{topic}'\n")
        continue
    
    # Analyze gaps
    doc_contents = "\n\n".join([d.document.content[:250] for d in topic_docs[:5]])
    
    gap_prompt = f"""Analyze research about {topic} and identify 2 specific research gaps.

Documents:
{doc_contents}

Format:
Gap 1: [Specific unexplored area]
Gap 2: [Specific unexplored area]

Research Gaps:"""
    
    gaps = llm.generate(gap_prompt, max_tokens=250)
    
    print("  Research Gaps:")
    for line in gaps.strip().split('\n'):
        if line.strip():
            print(f"  • {line.strip()}")
    print()

# ============================================================================
# STEP 4: Auto-Generate Research Recommendations
# ============================================================================
print("=" * 80)
print("💡 STEP 4: AUTO-GENERATE RECOMMENDATIONS")
print("=" * 80)
print()

if topics:
    # Combine multiple topics for broader recommendations
    combined_topics = ", ".join(topics[:3])
    print(f"→ Based on topics: {combined_topics}\n")
    
    # Get diverse set of documents
    all_related_docs = []
    for topic in topics[:3]:
        docs = vector_store.search(topic, top_k=5)
        all_related_docs.extend(docs)
    
    # Build context from diverse documents
    diverse_contents = "\n\n".join([
        f"{d.document.metadata.get('title', 'Unknown')}: {d.document.content[:200]}"
        for d in all_related_docs[:10]
    ])
    
    rec_prompt = f"""Based on current research in: {combined_topics}

Current Research:
{diverse_contents}

Provide 5 specific, actionable research recommendations that:
1. Build on current work
2. Address important gaps
3. Have practical impact

Format: Just list the recommendations, one per line

Recommendations:"""
    
    print(f"→ Generating recommendations with {config.llm.model_name}...\n")
    recommendations = llm.generate(rec_prompt, max_tokens=400)
    
    print("✓ Research Recommendations:")
    print("-" * 80)
    for line in recommendations.strip().split('\n'):
        if line.strip() and len(line.strip()) > 10:
            print(f"• {line.strip()}")
    print("-" * 80)
    print()

# ============================================================================
# STEP 5: Generate Research Roadmap
# ============================================================================
print("=" * 80)
print("🗺️  STEP 5: AUTO-GENERATE RESEARCH ROADMAP")
print("=" * 80)
print()

if topics and len(topics) >= 2:
    roadmap_prompt = f"""Based on current research in these areas: {', '.join(topics[:3])}

Create a brief research roadmap with 3 phases:
- Phase 1 (Short-term): Immediate next steps
- Phase 2 (Medium-term): Building on foundations
- Phase 3 (Long-term): Ambitious goals

Keep it concise and specific.

Research Roadmap:"""
    
    print(f"→ Creating roadmap with {config.llm.model_name}...\n")
    roadmap = llm.generate(roadmap_prompt, max_tokens=400)
    
    print("✓ Research Roadmap:")
    print("-" * 80)
    print(roadmap)
    print("-" * 80)
    print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("✅ AUTO ANALYSIS COMPLETED")
print("=" * 80)
print()
print("Summary:")
print(f"  • Extracted {len(topics)} main topics from database")
print(f"  • Analyzed {min(3, len(topics))} topics for research gaps")
print(f"  • Generated comprehensive recommendations")
print(f"  • Created research roadmap")
print()
print("All insights generated automatically from PDF content!")
print()
