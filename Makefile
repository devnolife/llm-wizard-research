# Wizard Research — Neuro-Symbolic Synthesis Gap Detection

.PHONY: help install dev test clean docker-up docker-down backend frontend experiment db-stats db-sources db-query papers-search papers-ingest experiment-ablation-nli experiment-breakdown experiment-calibration experiment-benchmark experiment-prf experiment-retrieval experiment-errors

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies (backend + frontend)
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ All dependencies installed!"

install-backend: ## Install backend dependencies only
	cd backend && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies only
	cd frontend && npm install

dev: ## Run both backend and frontend in development mode
	@echo "Starting development servers..."
	make -j2 backend frontend

backend: ## Run backend server
	./run_backend.sh

frontend: ## Run frontend development server
	cd frontend && npm run dev

test: ## Run all tests
	cd backend && pytest tests/

test-unit: ## Run unit tests only (core components)
	cd backend && pytest tests/test_fact_table.py tests/test_rule_engine.py tests/test_relation_classifier.py tests/test_fact_extractor.py tests/test_gap_analyzer.py

test-integration: ## Run integration tests only
	cd backend && pytest tests/test_integration.py

experiment-data: ## Download the 23-paper benchmark dataset from arXiv
	cd backend && python experiments/download_papers.py

experiment: ## Run the full neuro-symbolic experiment pipeline
	cd backend && python experiments/run_experiment.py --mode full --fresh-db

experiment-ablation: ## Run ablation runs (no-rule-engine + linear-baseline)
	cd backend && python experiments/run_experiment.py --mode no-rule-engine --skip-ingest
	cd backend && python experiments/run_experiment.py --mode linear-baseline --skip-ingest

experiment-compare: ## Aggregate experiment results into BAB IV tables
	cd backend && python experiments/compare_results.py

experiment-stats: ## Multi-run experiments with mean±std + Mann-Whitney U + effect size (H6/H7/H9)
	cd backend && python experiments/run_multi.py --runs 3

experiment-ablation-nli: ## H9 ablation: dedicated NLI cross-encoder vs LLM-only (run both modes)
	cd backend && python experiments/run_experiment.py --mode nli --skip-ingest
	cd backend && python experiments/run_experiment.py --mode no-nli --skip-ingest

experiment-breakdown: ## Breakdown EAR/conf by indicator type & detection method: make experiment-breakdown R=<results.json>
	cd backend && python experiments/breakdown_analysis.py --results $(or $(R),experiments/results/experiment_full_llama3.2_latest.json)

experiment-benchmark: ## Build a gold gap benchmark from corpus future-work (add NOLLM=1 to skip Ollama)
	cd backend && python experiments/build_gap_benchmark.py $(if $(NOLLM),--no-llm,)

experiment-prf: ## Gap Precision/Recall/F1 vs gold: make experiment-prf GOLD=<gold.json> R=<results.json>
	cd backend && python experiments/evaluate_gaps.py --gold $(GOLD) --results $(or $(R),experiments/results/experiment_full_llama3.2_latest.json) --per-topic

experiment-retrieval: ## Retrieval eval (nDCG/MRR/Recall@k) ± reranker, with ID/EN breakdown
	cd backend && python experiments/evaluate_retrieval.py --n 40 --k 10 --by-language

experiment-errors: ## False-discovery error taxonomy from expert form: make experiment-errors F=<form.xlsx> R=<results.json>
	cd backend && python experiments/error_taxonomy.py --forms $(F) $(if $(R),--results $(R),)

experiment-calibration: ## Confidence calibration (Brier/ECE) from a filled expert form: make experiment-calibration F=<form.xlsx>
	cd backend && python experiments/expert_eval/calibration.py --forms $(F)

experiment-annotate: ## Sample 50 SPO facts into an annotation sheet (precision)
	cd backend && python experiments/annotate_facts.py sample --results experiments/results/experiment_full_llama3.2_latest.json --n 50

lint: ## Run linters
	cd backend && pylint app/
	cd frontend && npm run lint

format: ## Format code
	cd backend && black app/
	cd frontend && npm run format

clean: ## Clean temporary files and caches
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	cd frontend && rm -rf node_modules/.vite

docker-up: ## Start all services with Docker Compose
	docker-compose up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-build: ## Build Docker images
	docker-compose build

docker-logs: ## View Docker logs
	docker-compose logs -f

init-db: ## Initialize database
	cd backend && python scripts/init_db.py

db-stats: ## Show vector store statistics (collection, doc count, model)
	cd backend && python scripts/vectorstore_cli.py stats

db-sources: ## List source documents and chunk counts in the vector store
	cd backend && python scripts/vectorstore_cli.py sources

db-query: ## Semantic search the vector store: make db-query Q="your query" [K=5]
	cd backend && python scripts/vectorstore_cli.py query "$(Q)" -k $(or $(K),5)

papers-search: ## Fetch external papers (no ingest): make papers-search Q="query" [K=10]
	cd backend && python scripts/papers_cli.py search "$(Q)" -k $(or $(K),10)

papers-ingest: ## Fetch papers and add them to the searchable corpus: make papers-ingest Q="query" [K=10]
	cd backend && python scripts/papers_cli.py ingest "$(Q)" -k $(or $(K),10)

setup: install ## Initial project setup
	@echo "Creating .env files from examples..."
	cp -n backend/.env.example backend/.env 2>/dev/null || true
	cp -n frontend/.env.example frontend/.env 2>/dev/null || true
	@echo "✅ Project setup complete!"
	@echo "Please edit .env files with your configuration"
