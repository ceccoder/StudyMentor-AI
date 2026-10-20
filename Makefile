# StudyMentor AI - Development Makefile

.PHONY: help install dev test lint format migrate-up migrate-down migrate-create docker-up docker-down docker-logs clean

help:
	@echo "StudyMentor AI - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install backend dependencies"
	@echo "  make dev            Start development server"
	@echo ""
	@echo "Database:"
	@echo "  make migrate-up     Run database migrations"
	@echo "  make migrate-down   Rollback last migration"
	@echo "  make migrate-create Create new migration (usage: make migrate-create msg='add new table')"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test           Run tests with coverage"
	@echo "  make lint           Run linter (ruff)"
	@echo "  make format         Format code (ruff format)"
	@echo "  make typecheck      Run type checker (mypy)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      Start all services with docker-compose"
	@echo "  make docker-down    Stop all services"
	@echo "  make docker-logs    View docker logs"
	@echo "  make docker-build   Build docker images"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          Remove cache and build artifacts"
	@echo "  make shell          Open backend container shell"

# Backend setup
install:
	cd backend && pip install -e ".[dev]"

# Development server
dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Database migrations
migrate-up:
	cd backend && alembic upgrade head

migrate-down:
	cd backend && alembic downgrade -1

migrate-create:
	cd backend && alembic revision --autogenerate -m "$(msg)"

# Testing
test:
	cd backend && pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

test-watch:
	cd backend && pytest tests/ -v --watch

# Code quality
lint:
	cd backend && ruff check .

format:
	cd backend && ruff format .

typecheck:
	cd backend && mypy app/

# Docker
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build --no-cache

docker-shell:
	docker-compose exec backend bash

# Clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	rm -rf backend/.coverage backend/htmlcov 2>/dev/null || true