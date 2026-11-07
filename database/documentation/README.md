# Database documentation index

This directory indexes the database documentation for Factory Sherlock and explains what each part of the `database/` tree is for. The documents themselves live under `docs/database/` so that they sit with the rest of the project documentation.

## Documents

| Document | What it covers |
|----------|----------------|
| [docs/database/database-design.md](../../docs/database/database-design.md) | Design goals, ER diagram, every table's keys, foreign key actions, constraints and indexes, business rules in MySQL versus services, transaction boundaries, indexing rationale and known gaps, and how the ORM maps to MySQL |
| [docs/database/data-dictionary.md](../../docs/database/data-dictionary.md) | Column-level reference: exact MySQL type, nullability, default, constraints, and meaning for all 17 tables |
| [docs/database/normalization.md](../../docs/database/normalization.md) | Functional dependencies, 1NF to BCNF analysis with concrete examples, and the derived values that are stored on purpose |
| [docs/database/queries.md](../../docs/database/queries.md) | The fourteen SQL files (ten under `queries/`, four under `queries/investigation/`): business question, techniques, parameters, callers, EXPLAIN notes, and real results from the seeded database |
| [docs/database/seed-data.md](../../docs/database/seed-data.md) | Reference seed contents, demo accounts, the demo scenario and the row counts it produces, and the reset procedure |
| [docs/media/diagrams/er-diagram.mmd](../../docs/media/diagrams/er-diagram.mmd) | Mermaid source of the ER diagram |

## The `database/` directory

```
database/
  documentation/   this index
  migrations are not here: see backend/migrations/versions/
  queries/         SQL files loaded by the backend at runtime
    investigation/ queries used only by the investigation rules
  schema/          schema.sql, a generated DDL snapshot
  seeds/           01_reference_data.sql, demo_scenario.json, sample_inspection_import.csv
```

### Migrations are authoritative

The schema is defined by the ORM models in `backend/app/models/` and created by the Alembic migrations in `backend/migrations/versions/`: `20261104_0106_create_manufacturing_schema.py` (revision `3a5e982c3679`, the 17 tables) and `20261107_2106_link_alerts_to_production_orders.py` (revision `383273c26ef7`, which adds `alerts.production_order_id` with the index `ix_alerts_production_order` and the named foreign key `fk_alerts_production_order`). `alembic upgrade head` is the only supported way to create or change tables. The `alembic_version` table in the database records the applied revision.

### `schema/schema.sql` is generated

`scripts/development/export_schema.sh` runs `mysqldump --no-data` against the migrated database and writes the result to `database/schema/schema.sql`, stripping `AUTO_INCREMENT` counters and client directives. It exists so the DDL can be read without running the application and so reviewers can see the exact MySQL types, ENUM lists, index names, and constraint names. Do not edit it by hand; rerun the script after a migration.

### `queries/` is loaded at runtime

`backend/app/repositories/sql_loader.py` reads every `*.sql` file under `database/queries/` once per process. The numeric prefix is stripped from the file name and subdirectories become dotted prefixes, so `01_machine_defect_rate_comparison.sql` is `machine_defect_rate_comparison` and `investigation/defect_onset.sql` is `investigation.defect_onset`. Each file starts with a comment header (business question, tables, techniques, parameters, result, callers, performance) that the SQL explorer endpoint returns as the query description. Parameters use SQLAlchemy `:name` placeholders and are always bound, never interpolated. Because the backend executes these files verbatim and stores their text on investigation evidence cards, the SQL on disk, the SQL executed, and the SQL shown to users are the same text.

### `seeds/`

- `01_reference_data.sql`: idempotent `INSERT ... ON DUPLICATE KEY UPDATE` statements for products, specifications, machines, defect types, and material lots. Executed by `backend/app/seed.py`.
- `demo_scenario.json`: the default simulation request that `python -m app.seed --demo` runs to populate production, quality, event, and alert data. The demo accounts are created by `seed.py` itself because their password hashes depend on `SEED_DEMO_PASSWORD`.
- `sample_inspection_import.csv`: a 16-row upload for `POST /api/v1/inspections/import` against the demo scenario. It is not applied by `seed.py`; see `docs/quality/inspection-import.md` and `docs/database/seed-data.md` section 4.

To rebuild everything from scratch: `cd backend && uv run python ../scripts/development/reset_database.py --demo`.
