# ADR-0001: Modular monolith for the backend

## Status

Accepted. Recorded 2026-11-03. Implemented in `backend/app`.

## Context

Factory Sherlock has several distinct capabilities: catalog management (products, specifications, machines, material lots, defect types), manufacturing execution (production orders, production batches, production units), quality (inspections, defect classification), traceability and quarantine, a simulation engine, an investigation engine, dashboard analytics, and authentication. The project is delivered by a small team on a fixed academic timeline and must be runnable on one laptop with a single MySQL instance.

The main architectural question was whether to split these capabilities into separate services or keep them in one process with enforced internal boundaries.

## Decision

Build the backend as a single FastAPI application organised as a modular monolith:

- One deployable process (`uvicorn app.main:app`) and one database.
- Internal packages with fixed responsibilities and a one-way dependency direction: `api` to `services` to `domain`, `models`, `repositories`, `simulation`, and `investigation`, with `core` as a shared leaf. The rules are written down in [system-overview.md](../architecture/system-overview.md#module-boundaries).
- Subsystems that could plausibly become separate components later (simulation, investigation) are kept free of HTTP and persistence concerns: the simulation engine returns dataclasses and the investigation rules depend on a `QueryRunner` protocol rather than on a session.
- Cross-subsystem writes share one transaction through the request-scoped session (see `app/core/database.py`), which is only possible because everything runs in one process against one database.

## Consequences

Positive:

- A production batch, a simulation run, or an investigation is written atomically across many tables without distributed coordination.
- Local setup is one MySQL instance plus one Python environment; there is no service discovery, message broker, or network between components.
- Code navigation and refactoring stay simple; the whole backend is roughly 5,000 lines including SQL and migrations.
- The boundaries make the simulation and investigation engines unit-testable without a database.

Negative or accepted costs:

- Boundaries are enforced by convention and review, not by the build. Nothing stops a route from importing a repository directly; the module boundary table is the contract.
- The process scales as a unit. A long simulation run occupies a worker; there is no separate job runner. This is acceptable for the project's data volumes (hundreds of batches, thousands of inspections).
- If the investigation engine were ever to run against a separate analytical store, the `QueryRunner` protocol is the extraction seam, but the service that persists evidence would need to change.

## Alternatives considered

- Microservices (separate simulation, investigation, and core API services). Rejected: cross-service transactions would be needed for batch creation and evidence persistence, local development would require orchestration, and the team size does not justify the operational overhead.
- Unstructured monolith (routes calling the ORM directly). Rejected: business rules such as state transitions and measurement evaluation would be duplicated between the API and the simulator, and the investigation rules would be hard to test.
- Separate backend for the simulator as a batch job writing to the same database. Rejected for now: the simulator needs the same reference data, enums, and quality rules as the API, and sharing them in one package avoids drift. The engine's purity keeps this option open.
