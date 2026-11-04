# Factory Sherlock backend

FastAPI service that owns the MySQL schema, the manufacturing business rules,
the virtual factory simulator, and the investigation engine.

See the repository root README for setup and `docs/architecture/` for design.

Quick commands (run from this directory):

```bash
uv sync                      # install dependencies into .venv
uv run alembic upgrade head  # apply migrations to the configured database
uv run python -m app.seed    # load reference data and demo accounts
uv run uvicorn app.main:app --reload
uv run pytest                # unit, API, and integration tests (API and integration tests need the MySQL test database)
uv run ruff check . && uv run ruff format --check . && uv run mypy app
```
