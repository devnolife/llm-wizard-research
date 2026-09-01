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
Phase 3: AGENTIC ANALYSIS    Observe → Think → Act → Evaluate (self-critique) → Repeat/Stop (LangGraph)
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
| **RAG Pipeline** | Two-stage retrieval: multilingual Sentence-Transformers (paraphrase-multilingual-MiniLM-L12-v2) bi-encoder + ChromaDB, then a cross-encoder reranker (ms-marco-MiniLM) for precision. Section-aware chunking tags chunks by section. | `backend/app/core/retrieval/` |

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
- Optional: [copilotd](https://github.com/devnolife/copilot-sdk-go) — when `COPILOTD_URL` is set (with `LLM_ENGINE=copilot`), all text generation runs on GitHub Copilot (`COPILOTD_MODEL`, default `claude-opus-4.8-fast`); Ollama then only serves as fallback (`COPILOT_STRICT=0`) or for embeddings

### Installation

```bash
git clone https://github.com/devnolife/wizard-research.git
cd wizard-research
make setup
```

For a reproducible CPU-safe backend environment, install [uv](https://docs.astral.sh/uv/)
and run `make install-backend-locked`; the lock is refreshed with
`make lock-backend`. The standard `make install` remains available for existing
GPU/local environments.

### Start Ollama

```bash
ollama serve
ollama pull llama3.2
```

### Run Development Servers

```bash
# Terminal 1 — Backend (port 8001)
make backend

# Terminal 2 — Frontend (port 5173)
make frontend
```

- **Frontend:** http://localhost:5173
- **API Docs:** http://localhost:8001/docs

---

## Usage

1. **Upload Papers** — Drag & drop 3–10 PDF papers on the upload page
2. **Auto-Analysis** — System extracts facts, builds KG, runs agentic analysis
3. **View Results** — Dashboard with 5 tabs: Overview, Topics, Gaps, Recommendations, Roadmap
4. **Search** — Query external APIs (arXiv, Semantic Scholar, CORE, PubMed, CrossRef, Europe PMC, ScienceDirect)
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

## Document OCR (ocrd service)

PDFs are read **ocrd-first**: every ingested PDF is sent to
[ocrd](../ocr-service/) — a standalone GPU OCR service (VLM-based, built on
Baidu Unlimited-OCR) installed at `~/ocr-service` and managed as a systemd
user service on port `8792`.

- **Digital PDFs** (with a text layer) are answered from the text layer in
  milliseconds without touching the GPU (`extraction_method="ocrd_text_layer"`).
- **Scanned / image-only PDFs** go through GPU OCR and come back as structured
  Markdown (`extraction_method="ocr"` / `ocr_used=true`).
- If the service is down or fails, ingestion **falls back to `pypdf`**
  (`extraction_method="pypdf"`) and never breaks.

```bash
# Service management (systemd user service, auto-starts on boot)
systemctl --user status ocrd
journalctl --user -u ocrd -f

# Health / readiness (model takes ~2 min to load after start)
curl -s http://127.0.0.1:8792/health

# Probe from the backend side
python backend/scripts/runtime_doctor.py --check-ocr
```

Configuration lives under the `OCR_*` env vars (see `.env`): `OCR_ENABLED`,
`OCR_SERVICE_URL` (default `http://127.0.0.1:8792`), `OCR_API_KEY`,
`OCR_IMAGE_MODE` (`gundam`/`base`), `OCR_DPI` (0 = server default),
`OCR_TIMEOUT`, and `OCR_PREFER_TEXT_LAYER`.

> **Note:** the legacy `ocr_service/` folder (raw SGLang setup on port 10000)
> is **deprecated** — ocrd manages its own GPU runtime. The folder is kept
> only until you decide to delete it.

---

## Testing

```bash
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-api          # Mocked FastAPI contract tests (no Ollama/OCR required)
```

## Analysis jobs and runtime diagnostics

Uploaded analysis inputs are stored per job and processed by a local SQLite
queue (maximum two concurrent jobs). Each job has its own FactTable, Knowledge
Graph, agent state, and retrieval scope; only its uploaded PDFs contribute to
its result. Jobs can be cancelled or retried from the result page and recover
after a backend restart while their retained inputs remain within the configured
retention window.

Inspect the effective, redacted configuration with:

```bash
make runtime-doctor
make runtime-doctor OCR=1  # additionally probe OCR when enabled
```

Operational telemetry stores only metadata such as job phase, duration, status,
and counts. It intentionally excludes PDF text, prompts, raw queries, chat
messages, and credentials.

---

## Inspecting the Vector Store

Inspect and query the ingested ChromaDB corpus directly from the CLI. These
commands use the project's own `VectorStore` (same multilingual
`paraphrase-multilingual-MiniLM-L12-v2` embeddings as the backend), so semantic search works against the client-side
embeddings produced during ingestion:

```bash
make db-stats                              # Collection name, document count, model, dimension
make db-sources                            # Source PDFs with per-document chunk counts
make db-query Q="synthesis gap detection"  # Semantic search (optional: K=5)
```

Under the hood these call `backend/scripts/vectorstore_cli.py`, which also
supports `--json` output and a `--source <file.pdf>` filter for agent/automation use:

```bash
cd backend
python scripts/vectorstore_cli.py --json query "transformer attention" -k 3
```

### Re-indexing to a new embedding model

The corpus is embedded with a **multilingual** bi-encoder
(`paraphrase-multilingual-MiniLM-L12-v2`) for mixed Indonesian/English papers.
To migrate an existing collection to a different embedding model **without
re-uploading PDFs** (ChromaDB stores the text, so documents are re-embedded
losslessly — preserving papers whose source PDFs are gone):

```bash
cd backend
python scripts/reindex_corpus.py --dry-run   # preview (counts + sources)
python scripts/reindex_corpus.py             # research_papers -> research_papers_ml
```

The original collection is kept as a backup; point the app at the new one via
`vector_db.collection_name` / `vector_db.embedding_model` in `config.yaml` (or
`CHROMA_COLLECTION_NAME` / `EMBEDDING_MODEL` env vars).

---

## Fetching Papers (CLI)

Fetch external research papers from the command line and optionally ingest them
into the searchable corpus so they show up in the app's search. Uses the same
`AggregatedPaperAPI` as the backend (arXiv, Semantic Scholar, CrossRef, PubMed,
CORE, **Europe PMC**):

```bash
make papers-search Q="synthesis gap detection"   # Fetch & display (no ingest), optional K=10
make papers-ingest Q="neuro-symbolic reasoning"  # Fetch + add to vector store (searchable)
```

The underlying `backend/scripts/papers_cli.py` exposes more options:

```bash
cd backend
# Pick sources, year range, and JSON output
python scripts/papers_cli.py search "graph neural network" \
    --sources europe_pmc arxiv -k 5 --year-from 2020 --json

# Ingest into a scratch collection (keeps the main corpus untouched)
python scripts/papers_cli.py ingest "knowledge graph" --sources europe_pmc \
    -k 10 --persist-dir /tmp/scratch_db --collection scratch
```

Available sources: `arxiv`, `semantic_scholar`, `crossref`, `pubmed`, `core`,
`europe_pmc`, `sciencedirect` (default: `arxiv europe_pmc crossref`). API keys
are optional and read from `backend/.env` — see
[External API Keys](#external-api-keys-optional).

---

## Experiments (Thesis Evaluation)

Reproducible experiment pipeline with ablation modes for hypothesis testing:

```bash
cd backend

# 1. Download the benchmark dataset (23 papers, 4 topics, from arXiv)
python experiments/download_papers.py

# 2. Full neuro-symbolic pipeline (+ adversarial rule engine validation)
python experiments/run_experiment.py --mode full --fresh-db

# 3. Ablation H7 — without the Rule Engine validation layer
python experiments/run_experiment.py --mode no-rule-engine --skip-ingest

# 4. Ablation H6 — linear RAG+LLM baseline (single prompt, no agentic loop)
python experiments/run_experiment.py --mode linear-baseline --skip-ingest

# 4b. Ablation H9 — dedicated cross-encoder NLI vs LLM-only contradiction
python experiments/run_experiment.py --mode nli --skip-ingest      # NLI enabled
python experiments/run_experiment.py --mode no-nli --skip-ingest   # NLI disabled

# 5. Model comparison (e.g., 3B vs 13B)
python experiments/run_experiment.py --mode full --model gpt-oss:latest --skip-ingest

# 6. Multi-run statistics — mean ± std + Mann-Whitney U + effect size (Cliff's δ,
#    rank-biserial) + bootstrap 95% CI, for H6 / H7 / H9
python experiments/run_multi.py --model llama3.2:latest --runs 3 \
    --seed 42 --modes full,no-rule-engine,linear-baseline,nli,no-nli

# 7. Negative control — topic absent from the corpus (sanity check)
python experiments/run_experiment.py --mode full --skip-ingest \
    --topics NONE --custom-topic "TC:quantum biology in marine ecosystems" \
    --output experiment_negative_control.json

# 8. SPO extraction precision — sample 50 facts for manual annotation
python experiments/annotate_facts.py sample \
    --results experiments/results/experiment_full_llama3.2_latest.json --n 50
# ... annotate the XLSX, then:
python experiments/annotate_facts.py score \
    --sheet experiments/results/fact_annotation.xlsx

# 9. Breakdown — EAR/confidence by indicator type & detection method
#    (shows which neuro-symbolic components carry the load; add --expert-form
#    <xlsx> for per-type/method EAR & LCS, e.g. NLI vs LLM-only for H9)
python experiments/breakdown_analysis.py \
    --results experiments/results/experiment_full_llama3.2_latest.json

# 10. Gold-standard benchmark + Precision/Recall/F1 (recall is what EAR cannot
#     give). Build a benchmark from authors' own stated future-work/limitations,
#     curate it (set verified=yes), then score — comparing modes on one gold set.
python experiments/build_gap_benchmark.py            # or --no-llm (no Ollama)
#   → curate experiments/gap_benchmark.xlsx, mark genuine gaps verified=yes,
#     then re-save the verified rows into gap_benchmark.json, and:
python experiments/evaluate_gaps.py \
    --gold experiments/gap_benchmark.json \
    --results experiments/results/experiment_full_llama3.2_latest.json \
    --results experiments/results/experiment_linear-baseline_llama3.2_latest.json \
    --threshold 0.5 --per-topic

# 11. Retrieval quality (nDCG/MRR/Recall@k) — bi-encoder vs + cross-encoder
#     reranker, automatic known-item protocol; --by-language splits ID vs EN
#     to test cross-lingual generalization of the multilingual embedding.
python experiments/evaluate_retrieval.py --n 40 --k 10 --by-language

# 12. False-discovery error taxonomy (from a filled expert form) — categorizes
#     Trivial/Illogical/Already-addressed errors × indicator type × method.
python experiments/error_taxonomy.py \
    --forms experiments/expert_eval/expert_form_filled.xlsx \
    --results experiments/results/experiment_full_llama3.2_latest.json
```

Optional: add `--nli` to any run to enable the dedicated cross-encoder NLI
model (independent contradiction signal, decoupled from the generative LLM).
The `nli` / `no-nli` modes are dedicated H9 ablation runs that fix this toggle.

Results are written to `backend/experiments/results/experiment_<mode>_<model>.json`.

### Expert Evaluation (EAR, LCS, AS, FDR, SHG, REP)

```bash
# Generate the XLSX assessment form from experiment results
python experiments/expert_eval/generate_form.py \
    --results experiments/results/experiment_full_llama3.2_latest.json

# After the expert fills the form, compute metrics + hypothesis tests (H4, H5)
python experiments/expert_eval/compute_metrics.py \
    --forms experiments/expert_eval/expert_form_filled.xlsx

# Confidence calibration (Brier score + ECE + reliability diagram) from the
# filled form — is a 0.8-confidence indicator genuine ~80% of the time?
python experiments/expert_eval/calibration.py \
    --forms experiments/expert_eval/expert_form_filled.xlsx
# add --use-adjusted to evaluate the post-Rule-Engine confidence instead
```

See [backend/experiments/expert_eval/README.md](backend/experiments/expert_eval/README.md) for details.

---

## Gap Discovery Pipeline (PDF → chunks → gaps → novelty)

An upgraded, reproducible pipeline that turns a folder of journal PDFs into
verified research-gap candidates. It fixes 10 measurable extraction/chunking
defects, mines research gaps with an LLM (grounded to verbatim quotes), and
verifies each gap's novelty against recent literature.

Shared core: `backend/app/core/pipeline/` (extraction, cleaning, metadata,
token-aware chunking) and `backend/app/core/gap_mining/` (candidates, LLM
extraction, verbatim verification, novelty). The same core powers the FastAPI
ingestion path, so uploaded PDFs get the new schema automatically.

```bash
cd backend

# TAHAP 1 — extract + clean + section + token-chunk 35 PDFs → new-schema JSONL
python -m scripts.run_pipeline --input ../data/raw/analysis_jobs/<jobid> \
    --out ../data/processed/chunks_<jobid>.jsonl
# legacy baseline for before/after comparison:
python -m scripts.run_pipeline --input <dir> --out ../data/processed/chunks_old.jsonl --legacy

# Audit all 10 defects + bagian-E validation gate (exit 1 on failure with --gate)
python -m experiments.audit_chunks ../data/processed/chunks_<jobid>.jsonl \
    --baseline ../data/processed/chunks_old.jsonl --gate

# TAHAP 2 — mine research gaps (L1 section/phrase candidates → L2 Copilot LLM,
# every gap_statement verified verbatim against its source chunk)
python -m scripts.mine_gaps --chunks ../data/processed/chunks_<jobid>.jsonl \
    --out ../data/processed/gaps_<jobid>.jsonl
# verify 100% verbatim grounding + count gaps the old regex-only approach missed
python -m experiments.verify_gaps --gaps ../data/processed/gaps_<jobid>.jsonl \
    --chunks ../data/processed/chunks_<jobid>.jsonl

# Benchmark extraction quality against the Mendeley Research-Gap dataset
# (semantic similarity + optional LLM-as-judge 1–5 rubric)
python -m experiments.gap_benchmark_mendeley \
    --dataset ../data/benchmarks/mendeley_gaps.csv --sample 25 --judge

# TAHAP 3 — novelty check each gap vs recent (≥2024) papers (OpenAlex, cached)
python -m scripts.check_novelty --gaps ../data/processed/gaps_<jobid>.jsonl \
    --out ../data/processed/gaps_<jobid>_novelty.jsonl

# Final single report: chunking before/after + open gaps per topic + title ideas
python -m experiments.final_report \
    --chunks-new ../data/processed/chunks_<jobid>.jsonl \
    --chunks-old ../data/processed/chunks_old.jsonl \
    --gaps ../data/processed/gaps_<jobid>_novelty.jsonl \
    --out ../data/processed/final_report.md
```

Optional **GROBID** (higher-quality title/authors/year/DOI + IMRaD sections):
`docker compose --profile grobid up -d grobid`, then set
`GROBID_URL=http://localhost:8070` in `backend/.env`. Without it the pipeline
falls back to pymupdf + regex-DOI + CrossRef/OpenAlex, so no server is required.

New per-chunk JSONL schema adds: `doi`, `paper_title`, `authors`, `year`,
`language`, `section_raw`, `section_normalized`, `is_reference`, `page_start`,
`token_count`, `chunk_id`, and `extraction_quality`.

---

## Docker

Docker setup is currently a template, not the primary supported path; for
development, run the backend and frontend with `make backend` / `make frontend`.

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
ELSEVIER_API_KEY=your_key        # ScienceDirect (Elsevier)
ELSEVIER_INSTTOKEN=your_token    # optional, for off-campus full-text
```

> **Note on CORE:** without `CORE_API_KEY`, CORE requests are heavily
> rate-limited (HTTP 429) and often return no results — the client retries with
> backoff but may still come up empty. Get a free key (10,000 requests/day) at
> <https://core.ac.uk/services/api>. arXiv, CrossRef, and Europe PMC work
> without any key.

> **Note on ScienceDirect (Elsevier):** the API does **not** use your
> ScienceDirect login (username/password). Get a free API key at
> <https://dev.elsevier.com/> and set `ELSEVIER_API_KEY`. Metadata + abstracts
> (used for search and ingestion) work with the key alone. Full-text of content
> your institution subscribes to additionally requires either running from the
> **UNHAS campus network / VPN** (IP-based entitlement) or an institutional
> token (`ELSEVIER_INSTTOKEN`) issued by the UNHAS library.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python, FastAPI, LangGraph, ChromaDB |
| **Frontend** | React 19, Vite 5, TailwindCSS 3.4 (shadcn/ui style) |
| **LLM** | GitHub Copilot via copilotd (`claude-opus-4.8-fast` default) with Ollama (llama3.2 / gpt-oss) as local engine or fallback |
| **Embeddings** | Multilingual Sentence-Transformers (paraphrase-multilingual-MiniLM-L12-v2) bi-encoder + cross-encoder reranker (ms-marco-MiniLM) |
| **Vector DB** | ChromaDB |
| **APIs** | arXiv, Semantic Scholar, CORE, PubMed, CrossRef, Europe PMC, ScienceDirect |

---

## License

MIT License

---

Made with ❤️ by [devnolife](https://github.com/devnolife)
