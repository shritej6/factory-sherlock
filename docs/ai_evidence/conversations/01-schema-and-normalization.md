# Conversation 1: Schema design and normalization

Project area: database design. Tool: Claude Code. Date: 2026-11-03.
Outcome: accepted after review, with one element deliberately kept as a documented exception.

## Sequence

1. Student prompt (paraphrased): design the smallest normalized MySQL schema that supports products, machines, production orders, batches, material lots, inspections, defects, investigations, and traceability, with at least one many-to-many relationship.
2. AI proposal: seventeen tables. Products and product_specifications separated; three junction tables (batch_materials, inspection_defects, investigation_batches); machine_events as an append-only log; investigation_evidence storing the SQL text and result rows for each finding.
3. Student check against course concepts:
   - Each table has a single-column surrogate primary key except the junction tables, which use composite primary keys.
   - Every foreign key has an explicit ON DELETE rule (RESTRICT for history, CASCADE for owned children, SET NULL for optional references).
   - CHECK constraints cover quantities and tolerances; ENUM columns restrict states.
   - Functional dependencies were listed for production_orders, production_batches, and inspections to confirm 3NF.
4. Point of discussion: inspections store the pass or fail result even though it can be recomputed from the measurement and the specification. The AI argued this keeps history stable if a tolerance changes later. The student accepted this as a documented snapshot, not a normalization violation, because the stored value depends on the specification as it was at inspection time.
5. Decision: accepted. The migration was generated with Alembic and applied to MySQL 8.4; the DDL snapshot is in database/schema/schema.sql.

## Verification

- `uv run alembic upgrade head` created all tables; `SHOW TABLES` listed 17 plus alembic_version.
- Constraint behaviour is covered by backend/tests/integration/test_transactions.py (foreign key rejection, CHECK rejection, ENUM rejection).

## Student annotation

[Shritej: add two or three sentences on what you would have done differently without the AI proposal, and which part of the ER diagram you want to defend in the Week 10 lab.]
