# Coding standards

These standards describe how code in this repository is written and checked. The tool configuration is the authority; this document explains it and adds the conventions that tools cannot enforce.

## Backend (Python)

### Tooling

Configured in `backend/pyproject.toml`:

- `ruff` for linting and formatting. Rule sets: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort), `B` (bugbear), `UP` (pyupgrade), `N` (pep8-naming), `SIM` (simplify), `RUF` (ruff-specific). `B008` is ignored because FastAPI dependency injection uses call defaults by design. Line length 100, target `py312`, sources `app` and `tests`.
- `mypy --strict` with the `pydantic.mypy` plugin on `app`; `ignore_missing_imports = true` for untyped third-party packages (`types-pymysql` is installed for the driver).
- `pytest` with `testpaths = ["tests"]`, the `integration` marker, and `-ra` summary output.

Commands, run from `backend/`:

```bash
uv run ruff check .
uv run ruff format .          # or --check in CI
uv run mypy app
APP_ENV=test uv run pytest
```

All three checks must pass before a pull request is opened. The post-edit lint hook in the development environment runs ruff automatically on saved files; treat its output as blocking.

### Formatting

`ruff format` (Black-compatible) decides layout; do not hand-format. Double quotes, trailing commas in multi-line collections, 100-column lines. `.editorconfig` sets four-space indentation for Python, two spaces for everything else, LF line endings, and a final newline.

### Naming

- Modules, functions, variables: `snake_case`. Private helpers start with one underscore (`_flush_or_conflict`, `_jsonable`, `_pct`).
- Classes: `PascalCase`. Pydantic request models end in `Create`, `Update`, or a verb noun (`StatusChange`, `QuarantineRequest`); response models end in `Read`; simulation records start with `Simulated`.
- Constants: `UPPER_SNAKE_CASE` at module level (`TOOL_WEAR_RATE`, `MACHINE_TRANSITIONS`, `DASHBOARD_QUERIES`).
- Enumerations: `enum.StrEnum` with `UPPER_SNAKE_CASE` members whose values equal their names, so the same string is used in Python, MySQL `ENUM` columns, JSON, and the frontend.
- Database identifiers: `snake_case` table and column names; constraint names prefixed `ck_` (check), `uq_` (unique), `ix_` (index) followed by table and purpose (`ck_order_completed_within_planned`, `uq_inspection_unit_spec`, `ix_inspections_time_result`).
- SQL query files: two-digit numeric prefix and `snake_case` stem for dashboard queries (`08_batches_requiring_review.sql`); investigation queries live in `investigation/` without a prefix. The stem is the query name used in code.
- Typed errors: suffix `Error` and subclass `AppError` with a class-level `status_code`.

### Docstrings and comments

Docstrings explain intent and the reason behind a decision, not what the code syntactically does. Module docstrings state the module's role and its boundaries (for example "The engine never touches SQLAlchemy"). Function docstrings are written when the behaviour is not obvious from the signature: `defect_rate` documents the zero case and that it is the single definition shared by three subsystems; `quarantine_lot` documents the transactional guarantee. Comments are reserved for non-obvious choices (why `pool_pre_ping`, why bcrypt directly rather than passlib, why the same login error for unknown users).

Rules: no commented-out code; no `TODO` without an issue reference; no comments that restate the next line.

### Structure and size

- Layers depend downward only: `api` to `services` to `domain`, `models`, `repositories`, `simulation`, `investigation`; `core` is a shared leaf. The full table is in `docs/architecture/system-overview.md`.
- Services receive a `Session` and never commit; routes call one service function and convert to a response model.
- Raw SQL lives only in `database/queries/`; Python refers to it by name.
- Configuration is read only through `get_settings()`.
- Functions should stay under 40 lines and modules under 500 lines. Current exceptions, which are acceptable because each is a single linear persistence or validation sequence and splitting would scatter a transaction, are `simulation_service.persist` (about 117 lines), `production_service.create_batch` (57), `investigation_service.open_investigation` (49), `SimulationEngine._run_machine` (48), and `quality_service.record_inspection` (41). The generated Alembic migration is exempt. New code should not add to this list without a reason stated in the pull request.
- Prefer frozen dataclasses for value objects (`SimulationConfig`, `Evidence`, `SpecRef`) and plain dictionaries only at the JSON boundary.
- Prefer composition and protocols (`QueryRunner`) to inheritance; the only inheritance is the ORM base, the Pydantic bases, and the error hierarchy.

### Errors

Services raise `NotFoundError`, `ConflictError`, `ValidationError`, `InvalidTransitionError`, `AuthenticationError`, or `AuthorizationError` with a message safe for clients and optional `details`. Never raise `HTTPException` outside `app/api`. Never catch an exception without re-raising or converting it to a typed error; `_flush_or_conflict` and `verify_password` are the model for narrow conversions. Log with `extra={"request_id": ..., "user_id": ..., "operation": ...}` and never log request bodies, passwords, or tokens.

### SQL files

Each file begins with a comment header: query number or purpose, business question, tables, techniques, parameters, result shape, and, for dashboard queries, which screen or rule uses it and a performance note. Use named bind parameters (`:window_start`), half-open time intervals (`>= start AND < end`), `NULLIF` for divisions, and `ROUND(..., 4)` for rates so SQL and Python agree. Keep the header accurate when a rule stops using a file.

### Tests

Test names read as sentences: `test_fault_to_running_is_rejected`, `test_same_seed_produces_identical_output`. Unit tests do not open database sessions. Assertions on simulated data must hold for any seed or pin a seed and derive the expectation from the formulas. Mark database tests with `@pytest.mark.integration`.

## Frontend (TypeScript and React)

Configured in `frontend/eslint.config.js`, `.prettierrc`, `tsconfig.app.json`, and `vite.config.ts`:

- TypeScript `strict`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`, `verbatimModuleSyntax`, `isolatedModules`; `@/*` maps to `src/*`.
- ESLint: `@eslint/js` recommended, `typescript-eslint` recommended, `react-hooks` recommended, `react-refresh/only-export-components` (warning, constant exports allowed), `consistent-type-imports` (error), `no-unused-vars` with `_`-prefixed arguments allowed; Prettier conflicts disabled through `eslint-config-prettier`.
- Prettier: single quotes, semicolons, trailing commas everywhere, 100-column lines.
- Vitest with jsdom, globals, Testing Library, and `tests/setup.ts` (jest-dom matchers, cleanup, mock restoration, and `localStorage` clearing after each test; a `ResizeObserver` stub for Recharts).

Conventions: `const` over `let`, never `var`; `async`/`await` with every rejection handled; discriminated unions for request state; feature folders under `src/features/<feature>/` with components, hooks, and tests co-located; shared UI in `src/components/ui`, charts in `src/components/charts`, API client code in `src/services`, response types in `src/types/api.ts` kept in step with `docs/api/openapi.json`. Components are function components in `PascalCase.tsx`; hooks start with `use`.

Commands, run from `frontend/`: `pnpm lint`, `pnpm typecheck`, `pnpm format:check`, `pnpm test`.

## Documentation

Markdown under `docs/` uses GitHub-flavoured Markdown, Mermaid fenced blocks for diagrams (with the source also kept under `docs/media/diagrams/`), and tables only where they aid comparison. Terminology is fixed: production order, production batch, production unit, material lot, inspection, defect type, investigation, evidence card. Documentation states what the code does; unimplemented behaviour is labelled Planned.

## Commits and branches

Commit messages follow Conventional Commits: `<type>(<scope>): <imperative summary>`, with types `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `build`, `ci`, `perf` and scopes such as `backend`, `frontend`, `db`, `sim`, `investigation`, `docs`. The body explains why the change is made, not what the diff shows; a `BREAKING CHANGE:` footer marks incompatible API or schema changes.

Branch names: `feature/<short-description>`, `fix/<short-description>`, `refactor/<short-description>`, `hotfix/<short-description>`, `docs/<short-description>`. Work is merged through pull requests; nothing is pushed directly to the default branch and the default branch is never force-pushed. Pull requests stay under about 400 changed lines where practical, include tests for new behaviour, and pass ruff, mypy, pytest, ESLint, tsc, and Vitest before review.

## Security checklist for every change

- Validate input at the boundary (Pydantic with `extra="forbid"`); trust internal calls.
- Parameterised queries only; never interpolate user input into SQL.
- No secrets in code, tests, fixtures, or documentation; `.env` stays ignored.
- Every new endpoint declares its role dependency and is reachable only with a bearer token (except `GET /health`).
- Error responses never contain SQL, driver messages, or stack traces.
