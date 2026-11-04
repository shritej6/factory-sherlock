# Changelog

All notable changes to Factory Sherlock are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers will follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once the first release is tagged. No release has been tagged yet, so there is only an Unreleased section.

## [Unreleased]

### Added

- Repository foundation: MIT license, `.editorconfig`, `.gitignore`, `.env.example`, `docker-compose.yml` for an optional MySQL 8.4 service, and `scripts/development/local_mysql.sh` for running MySQL without Docker.
- MySQL schema with 17 tables covering users, products and specifications, machines and machine events, material lots, production orders, batches, and units, inspections and defects, alerts, and investigations with their evidence, created by a single Alembic revision (`backend/migrations/versions/20261104_0106_create_manufacturing_schema.py`) with a matching downgrade. A generated DDL snapshot is kept at `database/schema/schema.sql`.
- Database setup script `scripts/setup/init_databases.sh` that creates the application and test databases and a least-privilege application user.
- FastAPI backend under `backend/app` exposing 31 API paths (40 HTTP operations) across auth, catalog, production, quality, traceability, analytics, simulation, investigations, and health, with JWT authentication, role-based authorization, Pydantic validation, and safe error responses carrying request ids. The OpenAPI document is exported to `docs/api/openapi.json`.
- Simulation engine (`backend/app/simulation`) that models machine state, fault injection, and measurement generation to produce production and inspection data.
- Investigation engine (`backend/app/investigation`) with rules for defect onset detection, machine events before onset, and shared material lots, producing a summary for each investigation.
- Twelve documented SQL queries under `database/queries/`: nine reporting and traceability queries and three investigation queries executed by the engine through bound parameters.
- Seed command `python -m app.seed` that loads reference data from `database/seeds/01_reference_data.sql`, creates the demo accounts, and optionally runs the demo scenario from `database/seeds/demo_scenario.json`; reset script `scripts/development/reset_database.py` that drops all tables and rebuilds from migrations.
- Developer scripts to export the schema (`scripts/development/export_schema.sh`) and the OpenAPI document (`scripts/development/export_openapi.py`).
- Documentation set under `docs/` with the architecture overview and directories reserved for requirements, database design, simulation, investigation, testing, decisions, milestones, and AI evidence.
- Governance and CI: GitHub Actions workflows for the backend, frontend, and documentation checks; pull request and issue templates; `CONTRIBUTING.md`; `SECURITY.md`; and a root `Makefile` wrapping the development commands.

### In progress

- Frontend under `frontend/` (React, Vite, TypeScript, Vitest) is being built. Its CI workflow runs only when `frontend/package.json` is present.
- Backend test suites under `backend/tests/` (unit, API, integration) are being completed; coverage figures will be recorded once the suite is stable.
