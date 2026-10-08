.DEFAULT_GOAL := help

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

install: ## Install dependencies (incl. dev + extras)
	uv sync --all-extras

test: ## Run tests
	uv run pytest -q

lint: ## Lint (incl. security rules) and format-check
	uv run ruff check . && uv run ruff format --check .

typecheck: ## Strict type check
	uv run mypy

audit: ## Scan dependencies for known vulnerabilities
	uv run pip-audit --skip-editable

e2e: ## End-to-end tests against the live site (override HACKBENCH_E2E_URL to target another)
	HACKBENCH_E2E_URL=$${HACKBENCH_E2E_URL:-https://qte77.github.io/2026-10-03-london-ai-science-hack} uv run pytest -q tests/e2e

qc: ## Run the reference QC pipeline on HACKBENCH_DATA_DIR (writes results/, git-ignored)
	uv run python -m hackbench.polaron --out results

qc-suite: ## Build the synthetic drift suite from the baseline, run it, score vs known truth
	uv run python -m hackbench.polaron --suite --out results

agent-smoke: ## ONE live Haiku session on Batch_3 (needs ANTHROPIC_API_KEY; ~$0.1, capped at $1.50)
	uv run --env-file .env python -m hackbench.polaron --agent $${AGENT:-haiku-4-5/neutral} --candidate $${CANDIDATE:-Batch_3} --out results

cycle: ## End-to-end cycle on local derived results (PARALLAX=dir of their decision briefs) -> results/cycle/
	uv run python -m hackbench.cycle --inputs results --out results/cycle $${PARALLAX:+--parallax $$PARALLAX}

validate: lint typecheck test ## Full local gate (run before pushing)

run: ## Serve the app locally on :8000
	uv run fastapi dev src/hackbench/api.py --factory

site: ## Pre-render the app into _site/ for GitHub Pages (set HACKBENCH_BASE_URL to the public URL)
	uv run python -m hackbench.static_site --out _site

.PHONY: help install test lint typecheck audit e2e qc qc-suite agent-smoke cycle validate run site
