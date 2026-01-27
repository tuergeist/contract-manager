.PHONY: help up down build logs clean test test-back test-front lint lint-back lint-front shell migrate makemigrations superuser health graphql-health

# Colors
GREEN := \033[0;32m
NC := \033[0m # No Color

help: ## Show this help
	@echo "Contract Manager - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Docker commands
up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

build: ## Build/rebuild images
	docker compose build

logs: ## Follow all logs
	docker compose logs -f

logs-back: ## Follow backend logs
	docker compose logs -f backend

logs-front: ## Follow frontend logs
	docker compose logs -f frontend

clean: ## Full reset (removes volumes)
	docker compose down -v --remove-orphans
	docker compose build --no-cache

restart: ## Restart all services
	docker compose restart

# Testing
test: test-back test-front ## Run all tests

test-back: ## Run backend tests
	docker compose exec backend pytest

test-front: ## Run frontend tests
	docker compose exec frontend npm test

# Linting
lint: lint-back lint-front ## Run all linters

lint-back: ## Run backend linters
	docker compose exec backend ruff check .
	docker compose exec backend ruff format --check .

lint-back-fix: ## Auto-fix backend lint issues
	docker compose exec backend ruff check --fix .
	docker compose exec backend ruff format .

lint-front: ## Run frontend linters
	docker compose exec frontend npm run lint

# Django commands
shell: ## Django shell
	docker compose exec backend python manage.py shell_plus

migrate: ## Run migrations
	docker compose exec backend python manage.py migrate

makemigrations: ## Create new migrations
	docker compose exec backend python manage.py makemigrations

superuser: ## Create superuser
	docker compose exec backend python manage.py createsuperuser

collectstatic: ## Collect static files
	docker compose exec backend python manage.py collectstatic --noinput

# Health checks
health: ## Check backend health endpoint
	@curl -s http://localhost:8001/api/health | jq .

graphql-health: ## Test GraphQL endpoint
	@curl -s -X POST http://localhost:8001/graphql \
		-H "Content-Type: application/json" \
		-d '{"query": "{ health }"}' | jq .

# Database
db-shell: ## PostgreSQL shell
	docker compose exec db psql -U contract_manager -d contract_manager

db-dump: ## Dump database
	docker compose exec db pg_dump -U contract_manager contract_manager > backup.sql

# Development
install-back: ## Install backend dependencies locally (for IDE)
	cd backend && uv pip install -e ".[dev]"

install-front: ## Install frontend dependencies locally (for IDE)
	cd frontend && npm install
