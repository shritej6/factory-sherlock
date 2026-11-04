# Contributing to Factory Sherlock

Factory Sherlock is a MySQL-backed manufacturing simulation and quality investigation platform. It is a solo university project held to professional standards, so the process below is deliberately strict even though the contributor count is small. Every change goes through a branch, a pull request, and the CI checks described here.

## Development workflow

1. Open or pick an issue. Use the templates under `.github/ISSUE_TEMPLATE/`. Schema changes need a database change proposal before any migration is written.
2. Create a branch from `main` using the naming scheme below.
3. Make the change in small, reviewable commits using the conventional commit format.
4. Run the quality gates locally (see below) before opening the pull request.
5. Open a pull request. The template in `.github/pull_request_template.md` is mandatory, including the AI assistance disclosure section required by the course.
6. Wait for the CI workflows (`Backend CI`, `Frontend CI`, `Docs Lint`) to pass. Fix failures on the branch; do not merge around them.
7. Merge with a merge commit or squash, then delete the branch.

Direct pushes to `main` are not part of the workflow.

## Branch naming

| Prefix      | Use for                                                        | Example                              |
| ----------- | -------------------------------------------------------------- | ------------------------------------ |
| `feature/`  | New functionality                                              | `feature/inspection-review-endpoint` |
| `fix/`      | Bug fixes                                                      | `fix/defect-rate-division-by-zero`   |
| `refactor/` | Internal restructuring with no behaviour change                | `refactor/split-simulation-engine`   |
| `docs/`     | Documentation only                                             | `docs/traceability-query-notes`      |
| `chore/`    | Build, CI, dependency, and tooling changes                     | `chore/pin-ruff-version`             |

Use lowercase words separated by hyphens after the prefix.

## Commit messages

Commits follow the Conventional Commits format: `type(scope): summary`, written in the imperative mood, with a body that explains why the change was made when the summary is not enough.

Types in use: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `db`, `perf`.

Scopes in use: `api`, `db`, `simulation`, `investigation`, `queries`, `seed`, `frontend`, `docs`, `ci`.

Examples:

```text
feat(api): add batch review endpoint for engineers

Engineers need to clear batches flagged by query 08 without editing rows by
hand. The endpoint requires the engineer role and records who reviewed the
batch and when.
```

```text
fix(simulation): clamp measurement noise to the gauge range

Negative diameters were produced when the fault multiplier exceeded the
nominal value. Measurements are now clamped and the clamp is logged.
```

```text
db(schema): index material_lot_id on batch_materials

Forward trace (query 04) joins on this column. Adds a non-unique index in a
new Alembic revision with a matching downgrade.
```

```text
docs(investigation): describe the defect onset rule inputs
```

A commit should contain one logical change. Do not mix a formatting pass with a behaviour change.

## Pull request size

Aim for fewer than 400 changed lines excluding generated files (`docs/api/openapi.json`, `database/schema/schema.sql`, lockfiles). If a change is larger, split it into independently mergeable pull requests: schema first, then service and endpoint, then frontend. State in the summary when a pull request is deliberately large and why.

## Quality gates

A pull request is ready for review only when all of the following hold. CI enforces most of them; the rest are checked in review.

| Gate                      | How it is checked                                                                      |
| ------------------------- | -------------------------------------------------------------------------------------- |
| Tests pass                | `uv run pytest` in `backend/`, including tests marked `integration` against MySQL      |
| New code is tested        | Unit tests for rules and services, API tests for endpoints, integration tests for SQL  |
| Lint passes               | `uv run ruff check .` and `uv run ruff format --check .` in `backend/`                 |
| Type check                | `uv run mypy app` in `backend/` (blocking in CI)                                        |
| Frontend checks           | `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build` in `frontend/`                |
| No secrets                | `.env` is ignored by Git; nothing in the diff contains credentials or tokens            |
| Migrations are reversible | Every revision has a working `downgrade()`, tested with `alembic downgrade -1`          |
| Documentation checked     | `make check-docs` passes; affected files under `docs/` updated                          |

The `Makefile` wraps these commands: `make lint`, `make test-backend`, `make test-frontend`, `make check-docs`.

## Running the project

Setup instructions live in `docs/development/setup-guide.md` and are not repeated here. In short: copy `.env.example` to `.env`, start MySQL with `make db-init` and `make db-start` (or `docker compose up -d mysql`, which has not been executed on the maintainer's machine because Docker is not installed there), then run `make migrate`, `make seed-demo`, `make backend`, and `make frontend`. Run `make help` to list every target.

## Coding standards

- Python 3.12, formatted and linted by Ruff with a 100 character line limit. Mypy runs in strict mode.
- Configuration is read only through `app.core.config.get_settings()`. Do not read `os.environ` elsewhere.
- SQL that the course reviews lives in `database/queries/` as files and is executed through `app.repositories.query_runner` with bound parameters. Do not build SQL strings from user input.
- Every mutating endpoint declares its required role through the `Operator` or `Engineer` dependencies in `app.api.deps`. ADMIN is a member of both role sets; no route is admin-only.
- Request and response models are Pydantic schemas. Input schemas set `extra="forbid"`.
- Errors raised inside services are subclasses of `AppError` and are mapped to safe HTTP responses in `app.api.errors`. Do not return raw exception text to clients.
- Alembic is the only way the schema changes. `database/schema/schema.sql` is a generated snapshot, not a source.
- Functions stay under 40 lines and files under 500 lines unless there is a documented reason.
- No commented-out code, no dead code, and no `TODO` without an issue reference.
- TypeScript in `frontend/` runs in strict mode; use `const` by default and discriminated unions for state.

## Documentation writing rules

All Markdown in this repository, including issue and pull request text, follows these rules. `Docs Lint` enforces the character rules in CI.

- No emoji.
- No em dashes (U+2014) or en dashes (U+2013). Use commas, colons, parentheses, or separate sentences. Use a plain hyphen for ranges and compound words.
- No promotional language. Describe what the system does, not how impressive it is.
- No unverified claims. Numbers, counts, and test results must come from running the code or the queries. If something has not been measured, say so.
- Prefer precise nouns over generic ones: name the table, the endpoint, the query file, or the rule.
- Use GitHub Markdown. Code, commands, file names, and identifiers go in backticks.
- Diagrams are Mermaid sources under `docs/media/diagrams/` so they can be reviewed as text.

## AI assistance

The course requires disclosure of AI assistance. Every pull request must state what an AI tool proposed, what was accepted, what was revised, what was rejected, and how the final result was verified by a person. Generated code is held to the same tests and review as hand-written code.
