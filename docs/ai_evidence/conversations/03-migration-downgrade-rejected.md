# Conversation 3: Rejected Alembic downgrade and the MySQL index rule

Project area: database migrations and tooling. Tool: Claude Code. Date: 2026-11-03.
Outcome: rejected and replaced.

## Sequence

1. Context: the initial migration was produced with `alembic revision --autogenerate`. The AI presented the generated file as ready to use.
2. Student action: ran `alembic downgrade base` to prove the migration is reversible, as the course requires.
3. Failure: MySQL rejected the downgrade partway through. The generated downgrade called `drop_index` on ix_production_batches_order before dropping the table, and MySQL will not drop an index that backs a foreign key while the constraint exists. Because MySQL DDL is not transactional, the schema was left half dropped.
4. Decision: the explicit `drop_index` calls were removed from the downgrade (dropping a table removes its indexes), and a reset script (scripts/development/reset_database.py) was added that disables foreign key checks, drops every table, and re-runs the migration, so a broken state can always be recovered.
5. A second AI suggestion in the same exchange, to use `alembic downgrade -q`, was also wrong: the flag does not exist. It was discarded after the command printed its usage text.

## Verification

- `alembic downgrade base` now completes and leaves only alembic_version; `alembic upgrade head` recreates all 17 tables (run twice in sequence on 2026-11-03).
- The reset script was used to rebuild the demo database before exporting database/schema/schema.sql.

## Student annotation

[Shritej: note why MySQL DDL not being transactional matters for the Week 10 defense and how you would demonstrate the rollback live.]
