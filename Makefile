.DEFAULT_GOAL := help

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

install: ## Install dependencies (incl. dev + deploy)
	uv sync --all-extras

test: ## Run tests
	uv run pytest -q

lint: ## Lint (incl. security rules) and format-check
	uv run ruff check . && uv run ruff format --check .

typecheck: ## Strict type check
	uv run mypy

audit: ## Scan dependencies for known vulnerabilities
	uv run pip-audit --skip-editable

validate: lint typecheck test ## Full local gate (run before pushing)

run: ## Serve the app locally on :8000
	uv run fastapi dev src/hackbench/api.py --factory

deploy: ## Deploy to Modal (needs `modal token new` once)
	uv run modal deploy src/hackbench/deploy.py

.PHONY: help install test lint typecheck audit validate run deploy
