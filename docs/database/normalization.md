# Normalization analysis

This document records the functional dependencies in the Factory Sherlock schema and shows that every table is in third normal form (3NF) and, with the qualifications noted, in Boyce-Codd normal form (BCNF). It also lists the places where a derived or snapshot value is stored on purpose, with the reason. Column definitions are in [data-dictionary.md](data-dictionary.md).

Notation: `A -> B` means B is functionally determined by A. Surrogate keys are written `id`.

## 1. Functional dependencies by table

| Table | Candidate keys | Non-trivial dependencies |
|-------|----------------|--------------------------|
| users | `id`, `username`, `email` | `id -> username, email, password_hash, role, is_active, created_at`; `username -> id`; `email -> id` |
| products | `id`, `code` | `id -> code, name, description, created_at, updated_at`; `code -> id` |
| product_specifications | `id`, `(product_id, characteristic)` | `id -> product_id, characteristic, target_value, tolerance, unit`; `(product_id, characteristic) -> id` |
| machines | `id`, `code` | `id -> code, name, status, created_at, updated_at`; `code -> id` |
| machine_events | `id` | `id -> machine_id, event_type, previous_state, new_state, severity, description, occurred_at` |
| material_lots | `id`, `lot_number` | `id -> lot_number, material_name, supplier, quantity_received, status, received_at`; `lot_number -> id` |
| production_orders | `id`, `order_number` | `id -> order_number, product_id, machine_id, quantity_planned, quantity_completed, status, due_date, created_at, updated_at`; `order_number -> id` |
| production_batches | `id`, `batch_number` | `id -> batch_number, production_order_id, machine_id, quantity, status, started_at, completed_at, quarantine_reason`; `batch_number -> id` |
| batch_materials | `(batch_id, material_lot_id)` | `(batch_id, material_lot_id) -> quantity_used` |
| production_units | `id`, `serial_number`, `(batch_id, sequence_in_batch)` | `id -> batch_id, serial_number, sequence_in_batch, produced_at`; `serial_number -> id`; `(batch_id, sequence_in_batch) -> id` |
| defect_types | `id`, `code` | `id -> code, name, description`; `code -> id` |
| inspections | `id`, `(unit_id, specification_id)` | `id -> unit_id, specification_id, measured_value, result, inspected_at`; `(unit_id, specification_id) -> id` |
| inspection_defects | `(inspection_id, defect_type_id)` | none (all-key relation) |
| alerts | `id` | `id -> machine_id, production_order_id, alert_type, severity, message, created_at, acknowledged_at, acknowledged_by` |
| investigations | `id` | `id -> title, machine_id, product_id, window_start, window_end, status, summary, conclusion, opened_by, created_at, closed_at` |
| investigation_evidence | `id`, `(investigation_id, sequence)` | `id -> investigation_id, sequence, rule_code, title, narrative, query_name, query_sql, result_rows, created_at`; `(investigation_id, sequence) -> id` |
| investigation_batches | `(investigation_id, batch_id)` | `(investigation_id, batch_id) -> reason` |

Every candidate key other than the surrogate `id` is declared as a UNIQUE constraint in the schema, so the dependency analysis above is enforced, not merely assumed.

## 2. First normal form

Every column holds one atomic value of one type; there are no repeating groups and no comma-separated lists. Three design choices are worth spelling out because each avoided a 1NF violation:

**Product specifications are rows, not columns.** A product could have been modelled with columns such as `diameter_target`, `diameter_tolerance`, `length_target`, and so on. That design fails when a product needs a characteristic the table did not anticipate (the bracket has `hole_position` and `thickness`; the shaft has `diameter` and `length`). `product_specifications` holds one characteristic per row, and `uq_spec_product_characteristic` guarantees that a product does not list the same characteristic twice. The seed file creates six rows for three products without any schema change.

**Defects on an inspection are a junction, not a list.** A failed inspection can carry more than one classification (the simulation appends `SURFACE_DAMAGE` to a dimensional defect when a gross material defect is simulated). Storing codes in a delimited string column would prevent counting defects by type with `GROUP BY`. `inspection_defects` holds one row per (inspection, defect type), and query 03 counts them with a plain join.

**Material lots per batch are a junction.** Same reasoning: a batch can use several lots, and the quantity taken from each lot is an attribute of the pair, so it lives on `batch_materials.quantity_used`.

### The JSON column

`investigation_evidence.result_rows` is a MySQL `json` column holding an object with two arrays, `columns` (the column names in SQL order) and `rows` (one array of values per result row); the application writes it in `investigation_service.evidence_payload`. The object form is used because MySQL reorders the keys of JSON objects, which would scramble the column order of a stored list of row objects. Strictly, a JSON document is a non-atomic value. It is accepted here because:

- The rows are a frozen snapshot of what a query returned at a point in time, kept for audit. They are never queried by their contents, never updated, and never joined; the API rebuilds one ordered dictionary per row (`EvidenceRead`) and returns them to the user interface without changing the values.
- Each rule returns rows with a different shape (`defect_onset` returns hourly buckets, `shared_material_lots` returns lots), so a relational child table would need either one table per rule or an entity-attribute-value structure, both of which are worse for the only operation performed on the data, which is "show exactly what the engineer saw".
- The relational facts behind the snapshot still exist in normalized form in the base tables; `query_sql` on the same row documents how to recompute them.

`machine_events.previous_state` and `new_state` are NULL for non-state-change events. This is a nullable-attribute design rather than a subtype table (`state_change_events`); it keeps the event log one ordered table, which is what `ix_machine_events_machine_time` and the investigation queries rely on.

## 3. Second normal form

2NF concerns tables with composite keys, where a non-key attribute must depend on the whole key rather than part of it.

| Table | Composite key | Non-key attributes | Depends on the whole key? |
|-------|---------------|--------------------|---------------------------|
| batch_materials | (batch_id, material_lot_id) | quantity_used | Yes: the quantity taken from one lot for one batch is meaningless for either alone |
| inspection_defects | (inspection_id, defect_type_id) | none | Trivially |
| investigation_batches | (investigation_id, batch_id) | reason | Yes: why this batch was flagged by this investigation |

Tables with surrogate single-column keys and additional composite candidate keys (`product_specifications`, `production_units`, `inspections`, `investigation_evidence`) are also checked against their composite candidate key. For example in `inspections`, `measured_value`, `result`, and `inspected_at` depend on the pair (unit, specification), not on the unit alone (a unit has several measurements) or on the specification alone (a specification is measured on many units).

Attributes that would have violated 2NF were kept out of the junction tables: supplier and material name belong to the lot, not to `batch_materials`; defect name belongs to `defect_types`, not to `inspection_defects`.

## 4. Third normal form

3NF requires that no non-key attribute depends transitively on the key through another non-key attribute. The schema avoids the common transitive dependencies:

- `production_batches` stores `machine_id`, not the machine's code or name. Query 04 joins to `machines` to display `machine_code`.
- `production_orders` stores `product_id`; product name is obtained by joining. Query 07 groups by `p.name` after the join.
- `inspections` stores `specification_id`; the target and tolerance are read from `product_specifications` when the result is computed and are not copied onto the inspection.
- `production_units` stores `batch_id`; the machine, order, and product of a unit are found by traversing the chain (query 05), not copied onto the unit.
- `alerts` and `investigations` store `machine_id` and user ids rather than machine codes or usernames.

### Derived values that are stored on purpose

Three columns hold values that could be recomputed from other rows. Each is a deliberate, documented decision rather than an oversight.

| Column | Derivable from | Why stored |
|--------|----------------|------------|
| `inspections.result` | `measured_value` compared with the specification's `target_value` and `tolerance` | The result is a historical fact: the unit passed or failed at inspection time under the specification in force then. If an engineer later tightens a tolerance, past results must not silently flip. Storing the result also lets `ix_inspections_time_result` serve defect-rate queries without a join to `product_specifications`. `quality_service.record_inspection` is the only writer and always computes the value through `quality_rules.evaluate_measurement`. |
| `production_orders.quantity_completed` | `SUM(quantity)` over the order's `COMPLETED` batches | Needed for the CHECK constraint `quantity_completed <= quantity_planned`, which MySQL can only evaluate on columns of the same row, and read on every order list. Maintained by `complete_batch` and `simulation_service.persist` with an atomic `UPDATE ... SET quantity_completed = quantity_completed + n`, so concurrent completions cannot lose an increment. |
| `production_batches.machine_id` | `production_orders.machine_id` of the owning order | The order's machine is a planning assignment and is nullable (`ON DELETE SET NULL`); the batch's machine is the machine that actually ran it and is mandatory (`NOT NULL`, `ON DELETE RESTRICT`). Every analytical query joins batches to machines directly. In the current workflow the two values are always equal when the batch is created, because `create_batch` copies `order.machine_id` and orders cannot be edited after a batch exists. |

`product_specifications` rows are edited in place: changing a tolerance does not create a new version of the specification, which is the reason `inspections.result` is stored as a snapshot rather than recomputed. Versioned specifications (a `valid_from` column or a separate history table, so a past inspection can name the exact tolerance it was judged against) are listed as future work; until then an edited tolerance changes what future inspections are judged against without altering past results.

Two further stored values are snapshots rather than derived data: `investigation_evidence.result_rows` and `investigation_evidence.query_sql` (section 2), and `investigations.summary`, which is the rule engine's text at opening time and is kept alongside the engineer's later `conclusion` so the two can be compared.

`production_batches.quantity` equals the number of `production_units` rows created with the batch. It is the requested batch size and is validated by `ck_batch_quantity_positive` before the units are generated; the services create exactly that many units in the same transaction.

## 5. Boyce-Codd normal form

BCNF requires that every determinant be a candidate key. From the dependency table in section 1, every left-hand side is a candidate key: either the surrogate `id`, a declared UNIQUE natural key (`code`, `lot_number`, `order_number`, `batch_number`, `serial_number`, `username`, `email`), or a declared composite UNIQUE key. Strictly, three documented exceptions exist where a non-key attribute is determined by other non-key attributes, each kept on purpose and explained in section 4: in `inspections`, `(specification_id, measured_value) -> result`, because the stored result is a snapshot taken under the specification in force at inspection time; in `production_batches`, `machine_id` repeats `production_orders.machine_id` of the owning order, so `production_order_id -> machine_id` holds at creation time (the copy is mandatory and protected by `ON DELETE RESTRICT`, where the original is nullable); and the generated identifiers `production_units.serial_number` and `production_batches.batch_number` are derived by the services from `(batch_id, sequence_in_batch)` and from the order number plus batch position. None of these is a hidden dependency: the first has a single writer, the second is equal by construction, and the third is a naming convention rather than a schema rule, as the next paragraphs explain.

Two observations about keys that are not dependencies in the schema:

- `production_units.serial_number` is generated as `<batch_number>-U<sequence>` by the services, so in practice it is determined by `(batch_id, sequence_in_batch)`. The format is a convention of `production_service.create_batch` and `simulation_service.persist`, not a rule of the schema; the column is an independent candidate key so that units created by other means (for example a future import) can carry externally assigned serials. The UNIQUE key on `(batch_id, sequence_in_batch)` is what prevents duplicate positions.
- `production_batches.batch_number` is generated as `<order_number>-B<nn>`; the same reasoning applies.

Neither convention introduces a non-key determinant in the schema, so BCNF holds with the exceptions above documented rather than hidden.

## 6. What was deliberately not denormalized

The following shortcuts were considered and rejected because they would make the investigation queries unreliable or the data impossible to correct:

| Rejected shortcut | Why rejected |
|-------------------|--------------|
| A `defect_rate` column on `production_batches` or `machines` | The rate depends on the time window asked about; queries 01, 06, 08, and `defect_onset` each compute it for a different window from the inspection rows. A stored rate would be correct for one window only. |
| A `failed` flag on `production_units` | A unit fails when any of its inspections fails; query 09 computes this with `COUNT(DISTINCT CASE WHEN i.result = 'FAIL' THEN u.id END)`. Storing it would duplicate `inspections.result` and have to be maintained on every inspection insert. |
| Material lot numbers copied onto `production_units` | Lots attach to batches, not units; copying would multiply rows and break when a batch uses two lots. Backward traceability (query 05) reaches lots through `batch_materials` and returns one row per lot. |
| Machine code or product name on `production_batches` | Would permit a batch to disagree with its own order; the joins are cheap through primary keys (`eq_ref` in every plan). |
| Storing the investigation's affected batches as a JSON array on `investigations` | The link is queried relationally: query 08's `EXISTS` on `investigation_batches` reports whether a batch is already under investigation, and the junction's `ON DELETE RESTRICT` on `batch_id` means a flagged batch cannot be deleted out from under an investigation. |
| Separate per-event-type tables for `machine_events` | The investigation asks "what happened on this machine shortly before quality deteriorated" across all event types; one table with one composite index answers it in a single range scan. |
