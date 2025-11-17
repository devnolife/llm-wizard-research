# Wizard Research - RAG-LLM Research Recommendation System

.PHONY: help install dev test clean docker-up docker-down backend frontend

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
	cd backend && python -m app.main

frontend: ## Run frontend development server
	cd frontend && npm run dev

test: ## Run all tests
	cd backend && pytest tests/

test-unit: ## Run unit tests only
	cd backend && pytest tests/unit/

test-integration: ## Run integration tests only
	cd backend && pytest tests/integration/

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
