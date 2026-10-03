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

e2e: ## End-to-end tests against the live deploy (override HACKBENCH_E2E_URL to target another)
	HACKBENCH_E2E_URL=$${HACKBENCH_E2E_URL:-https://thismay52--hackbench-web.modal.run} uv run pytest -q tests/e2e

qc: ## Run the reference QC pipeline on HACKBENCH_DATA_DIR (writes results/, git-ignored)
	uv run python -m hackbench.polaron --out results

validate: lint typecheck test ## Full local gate (run before pushing)

run: ## Serve the app locally on :8000
	uv run fastapi dev src/hackbench/api.py --factory

deploy: ## Deploy to Modal (needs `modal token new` once); stamps the git commit
	HACKBENCH_COMMIT=$${HACKBENCH_COMMIT:-$$(git rev-parse HEAD)} uv run modal deploy src/hackbench/deploy.py

.PHONY: help install test lint typecheck audit e2e qc validate run deploy
