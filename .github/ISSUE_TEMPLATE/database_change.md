---
name: Database change proposal
about: Propose a schema change with its ERD impact, migration plan, and rollback
title: "db: "
labels: database
assignees: ""
---

## Motivation

<!-- Which feature, query, or constraint requires this change? Link the issue. -->

## Proposed schema change

<!-- Tables, columns, types, nullability, defaults, constraints, and indexes. Write the intended DDL or the Alembic operations. -->

```sql

```

## ERD impact

- Tables added:
- Tables modified:
- Relationships added, changed, or removed (name the foreign keys and their `ON DELETE` behaviour):
- Does the change alter any entity in `docs/database/`? If yes, list the diagrams and documents to update.

## Data impact

- Existing rows affected (count or estimate, and how they are migrated):
- Seed data under `database/seeds/` that must change:
- Queries under `database/queries/` that must change:

## Migration plan

- [ ] Alembic revision generated with `uv run alembic revision --autogenerate -m "<slug>"` and reviewed by hand
- [ ] `upgrade()` applies cleanly on an empty database and on a database seeded with `make seed-demo`
- [ ] New foreign key columns are indexed
- [ ] Drop and add are not combined in one revision when data must be preserved
- [ ] `database/schema/schema.sql` regenerated with `make export-schema`

## Rollback plan

- [ ] `downgrade()` restores the previous schema
- [ ] Data lost on downgrade (if any) is listed here:
- [ ] Downgrade tested locally with `uv run alembic downgrade -1` followed by `uv run alembic upgrade head`

## Verification

<!-- Tests, queries, or API calls that prove the change works. Paste the commands you will run. -->

```bash

```
