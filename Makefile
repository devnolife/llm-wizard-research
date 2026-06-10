# Wizard Research — Neuro-Symbolic Synthesis Gap Detection

.PHONY: help install dev test clean docker-up docker-down backend frontend experiment

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

experiment-stats: ## Multi-run experiments with mean±std + Mann-Whitney U (H6/H7)
	cd backend && python experiments/run_multi.py --runs 3

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

setup: install ## Initial project setup
	@echo "Creating .env files from examples..."
	cp -n backend/.env.example backend/.env 2>/dev/null || true
	cp -n frontend/.env.example frontend/.env 2>/dev/null || true
	@echo "✅ Project setup complete!"
	@echo "Please edit .env files with your configuration"
