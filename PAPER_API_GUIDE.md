# 📚 External Paper API Integration Guide

## Overview

Sistem ini terintegrasi dengan 4 API akademik utama untuk mengambil paper/jurnal:

| API | Deskripsi | API Key Required | Rate Limit |
|-----|-----------|------------------|------------|
| **arXiv** | Preprint papers (CS, Physics, Math) | ❌ No | 3 req/sec |
| **Semantic Scholar** | Multi-disciplinary papers | ⚠️  Optional | 100/5min (free)<br>5000/5min (with key) |
| **CrossRef** | Published journals with DOI | ⚠️  Optional email | Faster with email |
| **PubMed** | Medical/Life sciences | ⚠️  Optional | 3 req/sec (free)<br>10 req/sec (with key) |

## 🔑 Setup API Keys (Optional)

### 1. **Semantic Scholar API Key** (Recommended)
**Keuntungan:** Rate limit lebih tinggi (5000 requests/5 min)

1. Daftar di: https://www.semanticscholar.org/product/api
2. Dapatkan API key gratis
3. Tambahkan ke `.env`:
```bash
SEMANTIC_SCHOLAR_API_KEY=your_key_here
```

### 2. **PubMed API Key** (Optional)
**Keuntungan:** Rate limit 10 req/sec vs 3 req/sec

1. Daftar akun NCBI: https://www.ncbi.nlm.nih.gov/account/
2. Generate API key
3. Tambahkan ke `.env`:
```bash
PUBMED_API_KEY=your_key_here
PUBMED_EMAIL=your_email@example.com
```

### 3. **CrossRef Polite Pool** (Optional)
**Keuntungan:** Response lebih cepat dari "polite pool"

Tambahkan email Anda ke `.env`:
```bash
CROSSREF_EMAIL=your_email@example.com
```

## 📖 Cara Penggunaan

### A. Via Python Code

#### 1. **Search Single Source**

```python
import asyncio
from src.external.paper_apis import ArXivAPI, SemanticScholarAPI

async def search_arxiv():
    arxiv = ArXivAPI()
    
    # Search papers
    papers = await arxiv.search(
        query="transformer neural networks",
        max_results=10
    )
    
    for paper in papers:
        print(f"Title: {paper.title}")
        print(f"Authors: {', '.join(paper.authors)}")
        print(f"Year: {paper.year}")
        print(f"PDF: {paper.pdf_url}")
        print("-" * 80)

asyncio.run(search_arxiv())
```

#### 2. **Search Multiple Sources**

```python
from src.external.paper_apis import AggregatedPaperAPI

async def search_all_sources():
    api = AggregatedPaperAPI()
    
    # Search across all sources
    results = await api.search_all(
        query="attention mechanisms",
        max_results_per_source=10,
        sources=["arxiv", "semantic_scholar", "crossref"]
    )
    
    # Show results by source
    for source, papers in results.items():
        print(f"\n{source}: {len(papers)} papers")
        for paper in papers[:3]:
            print(f"  - {paper.title[:60]}...")
    
    # Deduplicate across sources
    unique_papers = api.deduplicate_papers(results)
    print(f"\nTotal unique papers: {len(unique_papers)}")

asyncio.run(search_all_sources())
```

#### 3. **Get Specific Paper Details**

```python
async def get_paper_details():
    api = AggregatedPaperAPI()
    
    # Get paper from Semantic Scholar by ID
    paper = await api.semantic_scholar.get_paper_details("649def34f8be52c8b66281af98ae884c09aef38b")
    
    if paper:
        print(f"Title: {paper.title}")
        print(f"Abstract: {paper.abstract[:200]}...")
        print(f"Citations: {paper.citation_count}")

asyncio.run(get_paper_details())
```

### B. Via REST API

#### 1. **Search Papers**

```bash
# Search across all sources
curl -X POST "http://localhost:8000/api/papers/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "transformer neural networks",
    "max_results": 10,
    "sources": ["arxiv", "semantic_scholar"],
    "deduplicate": true
  }'
```

**Response:**
```json
{
  "query": "transformer neural networks",
  "total_results": 18,
  "sources_searched": ["arxiv", "semantic_scholar"],
  "papers": [
    {
      "paper_id": "2010.11929",
      "title": "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale",
      "authors": ["Alexey Dosovitskiy", "Lucas Beyer", "..."],
      "abstract": "While the Transformer architecture has become...",
      "year": 2020,
      "journal": "arXiv",
      "doi": null,
      "url": "http://arxiv.org/abs/2010.11929",
      "pdf_url": "http://arxiv.org/pdf/2010.11929",
      "citation_count": 0,
      "keywords": ["cs.CV", "cs.AI"],
      "source_api": "arxiv"
    }
  ]
}
```

#### 2. **Ingest Single Paper**

```bash
# Fetch and add paper to vector store
curl -X POST "http://localhost:8000/api/papers/ingest-external?paper_id=2010.11929&source=arxiv"
```

#### 3. **Batch Ingest Papers**

```bash
# Search and automatically ingest multiple papers
curl -X POST "http://localhost:8000/api/papers/batch-ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "attention mechanisms in NLP",
    "max_results": 20,
    "sources": ["arxiv", "semantic_scholar"]
  }'
```

**Response:**
```json
{
  "success": true,
  "query": "attention mechanisms in NLP",
  "papers_found": 20,
  "papers_ingested": 18,
  "papers_failed": 2,
  "ingested_ids": ["doc1", "doc2", "..."],
  "message": "Successfully ingested 18 papers"
}
```

## 🔍 Advanced Search Queries

### arXiv Search Syntax

```python
# Search by field
await arxiv.search("ti:transformer")  # Title
await arxiv.search("au:Vaswani")      # Author
await arxiv.search("abs:attention")   # Abstract

# Combined queries
await arxiv.search("ti:transformer AND au:Vaswani")

# Category filter
await arxiv.search("cat:cs.AI")       # AI papers
```

### Semantic Scholar Search

```python
# Specific fields
papers = await ss.search(
    query="deep learning",
    fields=["paperId", "title", "abstract", "year", "authors", "citationCount"]
)

# Get paper by DOI
paper = await ss.get_paper_details("DOI:10.1038/nature14539")
```

### CrossRef Filters

```python
# Journal articles only
papers = await crossref.search(
    query="neural networks",
    filter_params={"type": "journal-article"}
)

# Recent papers
papers = await crossref.search(
    query="transformers",
    filter_params={
        "from-pub-date": "2020",
        "type": "journal-article"
    }
)
```

### PubMed Search Syntax

```python
# Medical Subject Headings (MeSH)
await pubmed.search("diabetes[MeSH Terms]")

# Publication date range
await pubmed.search("cancer AND 2020:2023[PDAT]")

# Author search
await pubmed.search("Smith J[Author]")
```

## 📊 Complete Workflow Example

```python
"""
Complete workflow: Search → Filter → Ingest → Analyze
"""

import asyncio
from src.external.paper_apis import AggregatedPaperAPI
from src.retrieval.vector_store import VectorStore, Document

async def complete_workflow():
    # 1. Initialize
    api = AggregatedPaperAPI()
    vector_store = VectorStore()
    
    # 2. Search papers
    print("🔍 Searching papers...")
    results = await api.search_all(
        query="transformer attention mechanisms",
        max_results_per_source=10,
        sources=["arxiv", "semantic_scholar"]
    )
    
    # 3. Deduplicate
    papers = api.deduplicate_papers(results)
    print(f"📚 Found {len(papers)} unique papers")
    
    # 4. Filter by year and citations
    recent_papers = [
        p for p in papers
        if p.year and p.year >= 2020 and p.citation_count > 10
    ]
    print(f"✅ Filtered to {len(recent_papers)} recent high-impact papers")
    
    # 5. Ingest to vector store
    ingested = 0
    for paper in recent_papers:
        try:
            doc = Document(
                id=paper.paper_id,
                content=f"{paper.title}\n\n{paper.abstract}",
                metadata={
                    "title": paper.title,
                    "authors": ", ".join(paper.authors),
                    "year": paper.year,
                    "citation_count": paper.citation_count,
                    "source": paper.source_api
                }
            )
            vector_store.add_document(doc)
            ingested += 1
        except Exception as e:
            print(f"⚠️  Failed to ingest {paper.title[:50]}: {e}")
    
    print(f"✨ Successfully ingested {ingested} papers")
    
    # 6. Search similar papers
    similar = vector_store.search("attention mechanisms", top_k=5)
    print(f"\n📖 Most relevant papers:")
    for i, result in enumerate(similar, 1):
        title = result.document.metadata.get('title', 'N/A')
        print(f"{i}. {title}")

asyncio.run(complete_workflow())
```

## 🚀 Quick Start

### 1. **Tanpa API Key (Gratis)**

```bash
# Start server
uvicorn src.api.main:app --reload

# Test search
curl -X POST "http://localhost:8000/api/papers/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "deep learning", "max_results": 5}'
```

### 2. **Dengan API Key (Recommended)**

Edit `.env`:
```bash
SEMANTIC_SCHOLAR_API_KEY=your_key_here
CROSSREF_EMAIL=your_email@example.com
```

Restart server dan test:
```bash
curl -X POST "http://localhost:8000/api/papers/batch-ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "attention mechanisms",
    "max_results": 50,
    "sources": ["arxiv", "semantic_scholar", "crossref"]
  }'
```

## 📝 Notes

- **Rate Limits:** Semantic Scholar tanpa key = 100 req/5min, dengan key = 5000 req/5min
- **Best Practice:** Gunakan batch ingest untuk populate database awal
- **Caching:** Paper yang sudah di-ingest tidak akan di-fetch ulang
- **Deduplication:** Sistem otomatis detect duplicate berdasarkan DOI dan title similarity

## 🐛 Troubleshooting

### Error: "Rate limit exceeded"
**Solution:** 
- Tambahkan API key untuk Semantic Scholar atau PubMed
- Kurangi `max_results_per_source`
- Tambahkan delay antara requests

### Error: "Connection timeout"
**Solution:**
- Check internet connection
- Beberapa API mungkin down, coba source lain
- Increase timeout di aiohttp session

### No results found
**Solution:**
- Coba query yang lebih general
- Check spelling
- Gunakan syntax yang sesuai untuk masing-masing API

## 🔗 API Documentation Links

- arXiv API: https://arxiv.org/help/api/
- Semantic Scholar: https://www.semanticscholar.org/product/api
- CrossRef API: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- PubMed E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25501/
