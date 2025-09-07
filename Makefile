# Panic System Platform - Development Commands

.PHONY: help install dev test lint format clean docker-build docker-up docker-down create-admin

help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies"
	@echo "  dev         - Run development server"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting"
	@echo "  format      - Format code"
	@echo "  clean       - Clean cache files"
	@echo "  docker-build - Build Docker images"
	@echo "  docker-up   - Start Docker services"
	@echo "  docker-down - Stop Docker services"
	@echo "  create-admin - Create super admin account"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --cov=app --cov-report=html

lint:
	flake8 app/
	isort --check-only app/
	black --check app/

format:
	isort app/
	black app/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

migrate:
	python scripts/run_migrations.py

migrate-alembic:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(name)"

db-reset:
	docker-compose down -v
	docker-compose up -d postgres redis
	sleep 5
	make migrate

create-admin:
	python3 scripts/create_super_admin.py