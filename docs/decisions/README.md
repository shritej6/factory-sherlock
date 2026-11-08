# Architecture decision records

This directory holds the architecture decision records (ADRs) for Factory Sherlock. Each record captures one decision that shapes the codebase, the situation that led to it, what was decided, the consequences accepted, and the alternatives that were considered. Records are numbered in the order they were written and are not edited after acceptance except to change their status or add an amendment that points to a superseding record.

Every ADR follows the same sections: Status, Context, Decision, Consequences, Alternatives considered. Status values used: Accepted, Proposed, Superseded by ADR-nnnn, Deprecated. An ADR whose decision is only partly implemented says so in its status line.

## Index

| ID | Title | Status | Main code |
|----|-------|--------|-----------|
| [ADR-0001](ADR-0001-modular-monolith.md) | Modular monolith for the backend | Accepted | `backend/app` |
| [ADR-0002](ADR-0002-mysql-as-system-of-record.md) | MySQL 8 as the single system of record | Accepted | `backend/migrations`, `backend/app/models`, `database/` |
| [ADR-0003](ADR-0003-alembic-single-migration-system.md) | Alembic as the single schema migration system | Accepted | `backend/alembic.ini`, `backend/migrations`, `scripts/development/export_schema.sh` |
| [ADR-0004](ADR-0004-sql-files-as-runtime-and-documentation-source.md) | SQL files as both runtime artefact and documentation source | Accepted | `database/queries`, `backend/app/repositories` |
| [ADR-0005](ADR-0005-rule-based-investigation-before-ml.md) | Rule-based investigation engine before any machine learning | Accepted | `backend/app/investigation` |
| [ADR-0006](ADR-0006-deterministic-simulation-engine.md) | Deterministic, persistence-free simulation engine | Accepted | `backend/app/simulation`, `backend/app/services/simulation_service.py` |
| [ADR-0007](ADR-0007-jwt-roles-and-least-privilege-db-user.md) | JWT authentication with four roles and a least-privilege database user | Accepted | `backend/app/core/security.py`, `backend/app/api/deps.py`, `scripts/setup/init_databases.sh` |
| [ADR-0008](ADR-0008-uv-and-pnpm-toolchains.md) | uv for the Python backend and pnpm for the frontend | Accepted | `backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`, `frontend/pnpm-lock.yaml` |
| [ADR-0009](ADR-0009-cusum-onset-rule.md) | CUSUM onset detection as a seventh rule, not a model | Accepted | `backend/app/investigation/rules.py`, `database/queries/investigation/hourly_defect_rates.sql` |
| [ADR-0010](ADR-0010-commit-short-walkthrough-videos.md) | Commit short silent walkthrough videos | Accepted | `scripts/development/record_walkthroughs.py`, `docs/media/videos/` |
| [ADR-0011](ADR-0011-industrial-control-panel-interface.md) | Black industrial control panel interface | Accepted | `frontend/src/styles/index.css`, `frontend/src/app/StatusBand.tsx`, `frontend/src/app/SoftKeyBar.tsx` |

## Writing a new record

1. Copy the section structure from an existing record and take the next number.
2. Describe the context in terms of the forces at play (constraints, requirements, team situation), not the solution.
3. State the decision in the present tense and point at the code or configuration that implements it.
4. List consequences honestly, including costs and follow-ups, and distinguish what is implemented from what is planned.
5. Add the record to the index above.

Related documents: [system overview](../architecture/system-overview.md), [component design](../architecture/component-design.md), [data flow](../architecture/data-flow.md), [repository structure](../architecture/repository-structure.md).
