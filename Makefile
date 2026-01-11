.PHONY: help dev lint test migrate docker-up docker-down clean install

# Default target
help:
	@echo "AcuCare Pathways - Available Commands"
	@echo "======================================"
	@echo "make install    - Install dependencies"
	@echo "make dev        - Run development server"
	@echo "make lint       - Run linting (ruff)"
	@echo "make typecheck  - Run type checking (mypy)"
	@echo "make test       - Run tests"
	@echo "make migrate    - Run database migrations"
	@echo "make docker-up  - Start docker compose"
	@echo "make docker-down- Stop docker compose"
	@echo "make clean      - Clean cache files"

# Install dependencies
install:
	pip install -e ".[dev]"

# Run development server
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run linting
lint:
	ruff check app tests
	ruff format --check app tests

# Format code
format:
	ruff check --fix app tests
	ruff format app tests

# Run type checking
typecheck:
	mypy app

# Run tests
test:
	pytest -v tests/

# Run tests with coverage
test-cov:
	pytest -v --cov=app --cov-report=term-missing tests/

# Run database migrations
migrate:
	alembic upgrade head

# Create a new migration
migration:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

# Docker commands
docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api

# Clean cache and temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f *.db 2>/dev/null || true
