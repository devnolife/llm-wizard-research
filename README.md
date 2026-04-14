# Wizard Research

**Neuro-Symbolic Agentic System for Synthesis Gap Detection in Scientific Literature**

A research prototype that combines LLM-based reasoning with rule-based validation to detect indicators of synthesis gaps (fragmentation, inconsistency, incompleteness) in academic papers. Built as a thesis project for the Master's program in Informatics Engineering at Universitas Hasanuddin.

> **Thesis:** *Pendekatan Neuro-Symbolic Agentic untuk Deteksi Indikator Synthesis Gap pada Literatur Ilmiah*
> **Author:** Andi Agung Dwi Arya B (D082251054)

---

## Architecture

The system implements a **Neuro-Symbolic Agentic** architecture with 4 processing phases:

```
Phase 1: INGESTION          PDF → Parse → Chunk → Embed → Vector Store (ChromaDB)
Phase 2: FACT EXTRACTION     Entity Extraction → Relation Extraction → SPO Triples → Knowledge Graph
Phase 3: AGENTIC ANALYSIS    Plan → Act → Observe → Reflect → Repeat/Stop (LangGraph)
Phase 4: VALIDATION          Rule Engine (9 rules) → PASS / FLAG / REJECT
```

### Key Components

| Component | Description | Location |
|-----------|-------------|----------|
| **Gap Analyzer** | Detects 3 Cooper (1998) indicators: Fragmentation, Inconsistency, Incompleteness | `backend/app/core/gap_detection/` |
| **Rule Engine** | 9 rules in 3 categories (Feasibility, Causality, Consistency) with PASS/FLAG/REJECT verdicts | `backend/app/core/validation/rule_engine.py` |
| **Knowledge Graph** | SPO Fact Base with 8 entity types and 12 predicates for deductive reasoning | `backend/app/core/knowledge/` |
| **3-Layer Discriminator** | Semantic Filtering → Evidence Extraction → Rule-Based Validation | `backend/app/core/validation/relation_classifier.py` |
| **Agent Coordinator** | LangGraph-based multi-step reasoning with tool selection | `backend/app/core/agents/coordinator.py` |
| **RAG Pipeline** | SciBERT embeddings + ChromaDB vector retrieval | `backend/app/core/retrieval/` |

---

## Project Structure

```
wizard-research/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # FastAPI endpoints (analysis, documents, papers, health)
│   │   ├── core/
│   │   │   ├── agents/          # LangGraph coordinator + 4 specialized agents
│   │   │   │   └── tools/       # RAG, KG querier, NLI checker, paper analyzer, self-critic
│   │   │   ├── gap_detection/   # Synthesis gap analyzer (3 indicators)
│   │   │   ├── knowledge/       # Fact table + fact extractor (SPO triples)
│   │   │   ├── knowledge_graph/ # Graph builder
│   │   │   ├── recommendation/  # Research recommendation engine
│   │   │   ├── retrieval/       # Vector store + RAG retriever
│   │   │   └── validation/      # Rule engine + relation classifier (3-layer)
│   │   ├── services/            # LLM service (Ollama) + external paper APIs
│   │   └── utils/               # Config loader, document processor
│   ├── experiments/             # Evaluation experiment runner
│   ├── tests/                   # Unit + integration tests
│   ├── config.yaml
│   └── requirements.txt
│
├── frontend/                    # React 19 + Vite + TailwindCSS (shadcn/ui style)
│   └── src/
│       ├── components/
│       │   ├── pages/           # Upload, Results, Search, Chat, Documents, Revisi
│       │   ├── layout/          # Navbar
│       │   └── common/          # Badge, EmptyState, ErrorBoundary, LoadingSpinner
│       ├── contexts/            # DarkMode, Toast
│       ├── hooks/               # useApi
│       └── services/            # API clients
│
├── drafts/                      # Proposal chapter drafts (BAB I–V)
├── RINGKASAN_REVISI.md          # Comprehensive revision summary
├── Makefile
└── docker-compose.yml
```

---

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- [Ollama](https://ollama.ai) with `llama3.2:latest` (or any compatible model)

### Installation

```bash
git clone https://github.com/devnolife/wizard-research.git
cd wizard-research
make setup
```

### Start Ollama

```bash
ollama serve
ollama pull llama3.2
```

### Run Development Servers

```bash
# Terminal 1 — Backend (port 8000)
make backend

# Terminal 2 — Frontend (port 5173)
make frontend
```

- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8000/docs

---

## Usage

1. **Upload Papers** — Drag & drop 3–10 PDF papers on the upload page
2. **Auto-Analysis** — System extracts facts, builds KG, runs agentic analysis
3. **View Results** — Dashboard with 5 tabs: Overview, Topics, Gaps, Recommendations, Roadmap
4. **Search** — Query external APIs (arXiv, Semantic Scholar, CORE, PubMed, CrossRef)
5. **Chat** — Interactive Q&A about your research corpus

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload-and-analyze` | Upload PDFs and run full analysis pipeline |
| `GET` | `/api/analysis-status/{job_id}` | Check analysis progress |
| `POST` | `/api/recommend` | Get research recommendations |
| `POST` | `/api/gaps` | Detect synthesis gap indicators |
| `POST` | `/api/chat` | Chat with research assistant |
| `POST` | `/api/ingest` | Ingest a single PDF |
| `POST` | `/api/search` | Semantic search across documents |
| `POST` | `/api/papers/search` | Search external paper APIs |
| `GET` | `/health` | Health check |

---

## Testing

```bash
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
```

---

## Docker

```bash
docker-compose up -d    # Start all services
docker-compose down     # Stop services
docker-compose logs -f  # View logs
```

---

## External API Keys (Optional)

Add to `backend/.env` for enhanced paper search:

```bash
SEMANTIC_SCHOLAR_API_KEY=your_key
CORE_API_KEY=your_key
PUBMED_API_KEY=your_key
CROSSREF_EMAIL=your_email
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python, FastAPI, LangGraph, ChromaDB, SciSpaCy |
| **Frontend** | React 19, Vite 5, TailwindCSS 3.4 (shadcn/ui style) |
| **LLM** | Ollama (llama3.2 / configurable) |
| **Vector DB** | ChromaDB |
| **APIs** | arXiv, Semantic Scholar, CORE, PubMed, CrossRef |

---

## License

MIT License

---

Made with ❤️ by [devnolife](https://github.com/devnolife)
