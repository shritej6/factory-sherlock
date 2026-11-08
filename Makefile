# Factory Sherlock development commands.
#
# Every target wraps a command that can also be run by hand; see
# docs/development/setup-guide.md for the full walkthrough. Targets that touch
# the database read connection settings from .env at the repository root.

SHELL := /bin/bash
.DEFAULT_GOAL := help

BACKEND_DIR := backend
FRONTEND_DIR := frontend
UV := uv
PNPM := pnpm

.PHONY: help db-init db-start db-stop migrate seed seed-demo reset-demo backend frontend \
	test-backend test-frontend benchmark-sim lint format export-schema export-openapi render-diagrams render-figures check-docs \
	check-overdue screenshots videos

help: ## List available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk -F ':.*## ' '{ printf "  %-16s %s\n", $$1, $$2 }'

db-init: ## Create the local MySQL data directory, databases, and application user (one time)
	bash scripts/development/local_mysql.sh init

db-start: ## Start the local MySQL server
	bash scripts/development/local_mysql.sh start

db-stop: ## Stop the local MySQL server
	bash scripts/development/local_mysql.sh stop

migrate: ## Apply Alembic migrations to the configured database
	cd $(BACKEND_DIR) && $(UV) run alembic upgrade head

seed: ## Load reference data and demo accounts
	cd $(BACKEND_DIR) && $(UV) run python -m app.seed

seed-demo: ## Load reference data, demo accounts, and run the demo simulation scenario
	cd $(BACKEND_DIR) && $(UV) run python -m app.seed --demo

reset-demo: ## Drop all tables, re-run migrations, and seed the demo scenario
	cd $(BACKEND_DIR) && $(UV) run python ../scripts/development/reset_database.py --demo

# Exits 0 after committing (counts logged as one JSON line) and 1 after rolling back on
# any error (logged with the traceback). Add -- --as-of <ISO 8601> only to replay a past check.
check-overdue: ## Raise ORDER_OVERDUE alerts for open production orders past their due date
	cd $(BACKEND_DIR) && $(UV) run python -m app.jobs.check_overdue_orders

backend: ## Run the FastAPI server with reload
	cd $(BACKEND_DIR) && $(UV) run uvicorn app.main:app --reload --no-proxy-headers

frontend: ## Run the Vite dev server
	cd $(FRONTEND_DIR) && $(PNPM) dev

test-backend: ## Run the backend test suite (integration tests need MySQL)
	cd $(BACKEND_DIR) && $(UV) run pytest

test-frontend: ## Run the frontend test suite
	cd $(FRONTEND_DIR) && $(PNPM) test

benchmark-sim: ## Time simulation persistence for two request shapes against the configured database (rolled back)
	cd $(BACKEND_DIR) && $(UV) run python ../scripts/development/benchmark_simulation.py

lint: ## Ruff check, Ruff format check, mypy, and frontend lint and typecheck when present
	cd $(BACKEND_DIR) && $(UV) run ruff check . && $(UV) run ruff format --check . && $(UV) run mypy app
	@if [ -f $(FRONTEND_DIR)/package.json ]; then \
		cd $(FRONTEND_DIR) && $(PNPM) lint && $(PNPM) typecheck; \
	else \
		echo "skipping frontend lint: $(FRONTEND_DIR)/package.json not found"; \
	fi

format: ## Apply Ruff formatting and import fixes, and Prettier when the frontend is present
	cd $(BACKEND_DIR) && $(UV) run ruff format . && $(UV) run ruff check --fix .
	@if [ -f $(FRONTEND_DIR)/package.json ]; then \
		cd $(FRONTEND_DIR) && $(PNPM) format; \
	else \
		echo "skipping frontend format: $(FRONTEND_DIR)/package.json not found"; \
	fi

export-schema: ## Write the migrated MySQL DDL to database/schema/schema.sql
	bash scripts/development/export_schema.sh

render-diagrams: ## Render docs/media/diagrams/*.mmd to SVG with Playwright (installed Chrome on macOS, else bundled Chromium)
	cd $(BACKEND_DIR) && $(UV) run --group docs python ../scripts/development/render_diagrams.py

render-figures: ## Render the Mermaid blocks in docs/milestones/*.md to PNG figures for the DOCX and PDF builds
	cd $(BACKEND_DIR) && $(UV) run --group docs python ../scripts/development/render_milestone_figures.py

screenshots: ## Re-capture docs/media/screenshots/*.png from the running app with Playwright (see docs/media/media-plan.md for the required state)
	cd $(BACKEND_DIR) && $(UV) run --group docs python ../scripts/development/capture_screenshots.py

videos: ## Record the silent walkthrough videos into docs/media/videos with Playwright and ffmpeg (writes to the database)
	cd $(BACKEND_DIR) && $(UV) run --group docs python ../scripts/development/record_walkthroughs.py

export-openapi: ## Write the OpenAPI document to docs/api/openapi.json
	cd $(BACKEND_DIR) && $(UV) run python ../scripts/development/export_openapi.py

check-docs: ## Fail if any Markdown file contains an em dash, en dash, or emoji
	@matches="$$(find . -type f -name '*.md' \
		-not -path '*/node_modules/*' -not -path '*/.venv/*' \
		-not -path './.git/*' -not -path './.local/*' -print0 \
		| xargs -0 perl -CSD -ne 'print "$$ARGV:$$.: $$_" if /[\x{2013}\x{2014}]|[\x{1F000}-\x{1FAFF}]|[\x{2600}-\x{27BF}]|[\x{2B00}-\x{2BFF}]|\x{FE0F}/; close ARGV if eof')"; \
	if [ -n "$$matches" ]; then \
		echo "Forbidden characters found (em dash, en dash, or emoji):"; \
		printf '%s\n' "$$matches"; \
		exit 1; \
	fi; \
	echo "No forbidden characters found in Markdown files."
