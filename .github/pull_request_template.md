## Summary

<!-- One or two sentences on what this change does and why it is needed. Link the design note or decision record if one exists. -->

## Type of change

- [ ] Feature
- [ ] Bug fix
- [ ] Refactor (no behaviour change)
- [ ] Database schema or migration
- [ ] Documentation
- [ ] Build, CI, or tooling
- [ ] Other (describe below)

## Linked issue

Closes #

## How it was tested

<!-- Paste the exact commands you ran and summarise their results. Do not list commands you did not run. -->

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run mypy app
uv run pytest
```

Results:

- 

## Database changes

- [ ] No schema change
- [ ] Alembic migration added under `backend/migrations/versions/`
- [ ] `downgrade()` reverses the change and was run locally (`uv run alembic downgrade -1` then `upgrade head`)
- [ ] `database/schema/schema.sql` regenerated with `make export-schema`
- [ ] ERD and `docs/database/` updated to match

## Security checklist

- [ ] No secrets, credentials, or real connection strings in the diff
- [ ] SQL uses bound parameters only (SQLAlchemy `text()` with `:name` binds or ORM); no string concatenation of user input
- [ ] Request bodies and query parameters are validated by Pydantic schemas
- [ ] Every new or changed mutating endpoint declares its required role (`Operator`, `Engineer`, or `Admin`)
- [ ] Error responses do not expose SQL text, stack traces, or driver messages
- [ ] Logs do not include passwords, tokens, or request bodies

## Documentation

- [ ] Relevant files under `docs/` updated
- [ ] `docs/api/openapi.json` regenerated with `make export-openapi` if routes or schemas changed
- [ ] `CHANGELOG.md` Unreleased section updated
- [ ] No em dashes, en dashes, or emoji in any Markdown (`make check-docs` passes)

## AI assistance disclosure

<!-- Course requirement. Fill in every item, even if the answer is "none". -->

- Tools used:
- What the AI proposed:
- What was accepted as proposed:
- What was revised before merging, and why:
- What was rejected, and why:
- How the final result was verified by a person (tests run, queries executed, documentation read against the code):
