# Factory Sherlock data dictionary

One table per entity. MySQL types are copied from `database/schema/schema.sql`, the snapshot exported from the migrated database. "Default" is the database-level default; where the ORM supplies a value at insert time instead (`default=` in `backend/app/models/`), it is listed as "none (ORM: value)" because MySQL itself has no default for that column.

All tables use `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci`. The `alembic_version` table (`version_num varchar(32)`, primary key) records the latest applied migration and is not an application entity.

## users

Application accounts. Passwords are stored only as hashes.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| username | varchar(50) | NO | none | UNIQUE KEY `username` | Login name |
| email | varchar(255) | NO | none | UNIQUE KEY `email` | Contact address |
| password_hash | varchar(255) | NO | none | | Hash produced by `app.core.security.hash_password` |
| role | enum('ADMIN','ENGINEER','OPERATOR','VIEWER') | NO | none (ORM: VIEWER) | | Authorization role checked on every request |
| is_active | tinyint(1) | NO | none (ORM: 1) | | Inactive accounts cannot log in |
| created_at | datetime | NO | (now()) | | Row creation time |

## products

Catalogue of manufactured products.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| code | varchar(20) | NO | none | UNIQUE KEY `code` | Business identifier, for example `STEEL-SHAFT` |
| name | varchar(100) | NO | none | | Display name |
| description | text | YES | NULL | | Free text |
| created_at | datetime | NO | (now()) | | Row creation time |
| updated_at | datetime | NO | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | | Set on insert and refreshed by MySQL on every update, including raw SQL; the ORM also sets it on the updates it issues |

## product_specifications

One measurable characteristic per row.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| product_id | int | NO | none | FK `products.id` ON DELETE CASCADE; part of UNIQUE `uq_spec_product_characteristic` | Owning product |
| characteristic | varchar(50) | NO | none | part of UNIQUE `uq_spec_product_characteristic` | Name such as `diameter`, `hole_position` |
| target_value | decimal(10,3) | NO | none | | Nominal value |
| tolerance | decimal(10,3) | NO | none | CHECK `ck_spec_tolerance_positive` (`tolerance > 0`) | Allowed absolute deviation |
| unit | varchar(10) | NO | none (ORM: mm) | | Unit of measure |

## machines

Production machines.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| code | varchar(20) | NO | none | UNIQUE KEY `code` | Business identifier, for example `CNC-03` |
| name | varchar(100) | NO | none | | Display name |
| status | enum('IDLE','RUNNING','WARNING','STOPPED','FAULT') | NO | none (ORM: IDLE) | | Current state; transitions governed by `MACHINE_TRANSITIONS` |
| created_at | datetime | NO | (now()) | | Row creation time |
| updated_at | datetime | NO | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | | Set on insert and refreshed by MySQL on every update, including raw SQL; the ORM also sets it on the updates it issues |

## machine_events

Append-only log of state changes and simulated faults.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| machine_id | int | NO | none | FK `machines.id` ON DELETE RESTRICT; leading column of `ix_machine_events_machine_time` | Machine the event belongs to |
| event_type | enum('STATE_CHANGE','TOOL_WEAR','CALIBRATION_DRIFT','MATERIAL_ISSUE','DOWNTIME','MAINTENANCE') | NO | none | | Kind of event. `MAINTENANCE` is defined but not produced by current code |
| previous_state | enum('IDLE','RUNNING','WARNING','STOPPED','FAULT') | YES | NULL | | Populated for `STATE_CHANGE` only |
| new_state | enum('IDLE','RUNNING','WARNING','STOPPED','FAULT') | YES | NULL | CHECK `ck_event_state_pair` (`(event_type = 'STATE_CHANGE') = (new_state IS NOT NULL)`) | Populated for `STATE_CHANGE` only; the CHECK enforces the pairing |
| severity | enum('INFO','WARNING','CRITICAL') | NO | none (ORM: INFO) | | `CRITICAL` for transitions into `FAULT` and for `DOWNTIME` faults; `WARNING` for other simulated faults |
| description | varchar(255) | NO | none | | Human-readable reason |
| occurred_at | datetime | NO | none | second column of `ix_machine_events_machine_time` | Event time (not the insert time) |

## material_lots

Raw material received from suppliers.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| lot_number | varchar(30) | NO | none | UNIQUE KEY `lot_number` | Supplier lot identifier, for example `L201` |
| material_name | varchar(100) | NO | none | | Material description; the simulation matches products to lots by this value |
| supplier | varchar(100) | NO | none | | Supplier name |
| quantity_received | decimal(10,2) | NO | none | CHECK `ck_material_lot_quantity_non_negative` (`quantity_received >= 0`) | Quantity delivered |
| status | enum('AVAILABLE','QUARANTINED','CONSUMED') | NO | none (ORM: AVAILABLE) | | Only `AVAILABLE` lots can be consumed by a new batch |
| received_at | datetime | NO | none | | Delivery time |

## production_orders

A request to manufacture a quantity of one product.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| order_number | varchar(30) | NO | none | UNIQUE KEY `order_number` | Business identifier; simulation runs generate `SIM0001-CNC-03-01` |
| product_id | int | NO | none | FK `products.id` ON DELETE RESTRICT; implicit index `product_id` | Product to manufacture |
| machine_id | int | YES | NULL | FK `machines.id` ON DELETE SET NULL; implicit index `machine_id` | Planned machine; required before release |
| quantity_planned | int | NO | none | CHECK `ck_order_quantity_planned_positive` (`> 0`) | Units requested |
| quantity_completed | int | NO | none (ORM: 0) | CHECK `ck_order_quantity_completed_non_negative` (`>= 0`); CHECK `ck_order_completed_within_planned` (`<= quantity_planned`) | Units completed so far; maintained by `complete_batch` and simulation persistence |
| status | enum('PLANNED','RELEASED','IN_PROGRESS','COMPLETED','CANCELLED') | NO | none (ORM: PLANNED) | index `ix_production_orders_status` | Workflow state; transitions governed by `ORDER_TRANSITIONS` |
| due_date | date | YES | NULL | | Target completion date |
| created_at | datetime | NO | (now()) | leading column of `ix_production_orders_created_id (created_at, id)` | Row creation time (the simulation sets it explicitly to the simulated time); the index matches the `created_at DESC, id DESC` ordering of the order list |
| updated_at | datetime | NO | CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | | Set on insert and refreshed by MySQL on every update, including raw SQL; the ORM also sets it on the updates it issues |

## production_batches

A run of units for one order on one machine.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| batch_number | varchar(30) | NO | none | UNIQUE KEY `batch_number` | `<order_number>-B<nn>`, generated by the services |
| production_order_id | int | NO | none | FK `production_orders.id` ON DELETE RESTRICT; index `ix_production_batches_order` | Owning order |
| machine_id | int | NO | none | FK `machines.id` ON DELETE RESTRICT; leading column of `ix_production_batches_machine_time` | Machine that ran the batch |
| quantity | int | NO | none | CHECK `ck_batch_quantity_positive` (`> 0`) | Units in the batch; equals the number of `production_units` rows created with it |
| status | enum('IN_PROGRESS','COMPLETED','QUARANTINED') | NO | none (ORM: IN_PROGRESS) | CHECK `ck_batch_completed_has_time` (`status <> 'COMPLETED' OR completed_at IS NOT NULL`); CHECK `ck_batch_quarantine_reason` (`(status = 'QUARANTINED') = (quarantine_reason IS NOT NULL)`) | Transitions governed by `BATCH_TRANSITIONS` |
| started_at | datetime | NO | none | second column of `ix_production_batches_machine_time`; leading column of `ix_production_batches_started_id (started_at, id)` | Start time; the second index matches the `started_at DESC, id DESC` ordering of the batch list |
| completed_at | datetime | YES | NULL | CHECK `ck_batch_completed_after_start` (`completed_at IS NULL OR completed_at >= started_at`); see `ck_batch_completed_has_time` | Set when the batch completes; required for `COMPLETED` and kept when a completed batch is later quarantined |
| quarantine_reason | varchar(255) | YES | NULL | see `ck_batch_quarantine_reason` | Set when the batch is quarantined, directly or through a lot quarantine; present exactly when `status = 'QUARANTINED'` |

## batch_materials

Junction: material lots consumed by a batch.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| batch_id | int | NO | none | part of PRIMARY KEY; FK `production_batches.id` ON DELETE RESTRICT | Consuming batch; the link blocks deletion of the batch |
| material_lot_id | int | NO | none | part of PRIMARY KEY; FK `material_lots.id` ON DELETE RESTRICT; implicit index `material_lot_id` | Consumed lot |
| quantity_used | decimal(10,2) | NO | none | CHECK `ck_batch_material_quantity_positive` (`> 0`) | Quantity taken from the lot (the simulation records the unit count) |

## production_units

One manufactured component.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| batch_id | int | NO | none | FK `production_batches.id` ON DELETE RESTRICT; leading column of UNIQUE `uq_unit_batch_sequence`; second column of `ix_production_units_produced_at` | Owning batch; units block deletion of the batch |
| serial_number | varchar(40) | NO | none | UNIQUE KEY `serial_number` | `<batch_number>-U<nnnn>`, generated by the services |
| sequence_in_batch | int | NO | none | part of UNIQUE `uq_unit_batch_sequence`; CHECK `ck_unit_sequence_positive` (`> 0`) | Position within the batch, starting at 1 |
| produced_at | datetime | NO | none | leading column of `ix_production_units_produced_at` | Production time of the unit |

## defect_types

Reference list of defect classifications.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| code | varchar(30) | NO | none | UNIQUE KEY `code` | Identifier used by `quality_rules.py`, for example `OVERSIZE_DIAMETER` |
| name | varchar(100) | NO | none | | Display name |
| description | text | YES | NULL | | Free text |

## inspections

One measurement of one unit against one specification.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| unit_id | int | NO | none | FK `production_units.id` ON DELETE RESTRICT; leading column of UNIQUE `uq_inspection_unit_spec` | Inspected unit; inspections block deletion of the unit |
| specification_id | int | NO | none | FK `product_specifications.id` ON DELETE RESTRICT; part of UNIQUE `uq_inspection_unit_spec`; leading column of `ix_inspections_spec_time (specification_id, inspected_at)`, which also backs the foreign key (the implicit `specification_id` index was replaced by revision `6c1f0d2a9b47`) | Characteristic checked |
| measured_value | decimal(10,3) | NO | none | | Measured value in the specification's unit |
| result | enum('PASS','FAIL') | NO | none | second column of `ix_inspections_time_result` | Stored outcome computed from the specification at inspection time |
| inspected_at | datetime | NO | none | leading column of `ix_inspections_time_result` and of `ix_inspections_time_id (inspected_at, id)`; second column of `ix_inspections_spec_time` | Inspection time; `ix_inspections_time_id` matches the `inspected_at DESC, id DESC` ordering of the inspection list |

## inspection_defects

Junction: defect classifications of a failed inspection.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| inspection_id | int | NO | none | part of PRIMARY KEY; FK `inspections.id` ON DELETE CASCADE | Classified inspection |
| defect_type_id | int | NO | none | part of PRIMARY KEY; FK `defect_types.id` ON DELETE RESTRICT; implicit index `defect_type_id` | Defect classification |

## alerts

Notifications raised by the simulation, by quarantine actions, and by the overdue order check.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| machine_id | int | YES | NULL | FK `machines.id` ON DELETE SET NULL; implicit index `machine_id` | Machine concerned; NULL for lot quarantine alerts and for overdue alerts on orders without a machine |
| production_order_id | int | YES | NULL | FK `production_orders.id` ON DELETE SET NULL (`fk_alerts_production_order`); index `ix_alerts_production_order` | Order concerned; set only by the ORDER_OVERDUE check, which also uses it to find the open alert for an order. Added by revision `383273c26ef7` |
| alert_type | enum('HIGH_DEFECT_RATE','MACHINE_FAULT','MATERIAL_QUARANTINE','ORDER_OVERDUE') | NO | none | | Category. `ORDER_OVERDUE` is raised by `alert_service.raise_overdue_order_alerts` |
| severity | enum('INFO','WARNING','CRITICAL') | NO | none | | Severity |
| message | varchar(255) | NO | none | | Text; services truncate to 255 characters |
| created_at | datetime | NO | (now()) | leading column of `ix_alerts_created (created_at, id)` | Alert time (the simulation and the quarantine services set it explicitly; the overdue check stamps the check date: the server clock, or `--as-of` when the job replays a past check) |
| acknowledged_at | datetime | YES | NULL | | Set by `acknowledge_alert` |
| acknowledged_by | int | YES | NULL | FK `users.id` ON DELETE SET NULL; implicit index `acknowledged_by` | Acknowledging user |

## investigations

A quality investigation over a time window.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| title | varchar(150) | NO | none | | Title supplied by the engineer |
| machine_id | int | YES | NULL | FK `machines.id` ON DELETE SET NULL; implicit index `machine_id` | Machine in scope; NULL means fleet-wide |
| product_id | int | YES | NULL | FK `products.id` ON DELETE SET NULL; implicit index `product_id` | Product in scope; validated on creation, not used by the current rules |
| window_start | datetime | NO | none | CHECK `ck_investigation_window_order` (`window_end > window_start`) | Start of the analysed period |
| window_end | datetime | NO | none | see above | End of the analysed period (exclusive in the queries) |
| status | enum('OPEN','IN_REVIEW','CLOSED') | NO | none (ORM: OPEN) | CHECK `ck_investigation_closed` (`(status = 'CLOSED') = (closed_at IS NOT NULL)`) | Transitions governed by `INVESTIGATION_TRANSITIONS` |
| summary | text | YES | NULL | | Written by the rule engine at creation |
| conclusion | text | YES | NULL | | Written by an engineer; required to close |
| opened_by | int | YES | NULL | FK `users.id` ON DELETE SET NULL; implicit index `opened_by` | Creating user |
| created_at | datetime | NO | (now()) | leading column of `ix_investigations_created_id (created_at, id)` | Creation time; the index matches the `created_at DESC, id DESC` ordering of the investigation list |
| closed_at | datetime | YES | NULL | see `ck_investigation_closed` | Set when status becomes `CLOSED`; present exactly then |

## investigation_evidence

One evidence card per rule that fired.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| id | int | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate key |
| investigation_id | int | NO | none | FK `investigations.id` ON DELETE CASCADE; leading column of UNIQUE `uq_evidence_investigation_sequence` | Owning investigation |
| sequence | int | NO | none | part of UNIQUE `uq_evidence_investigation_sequence` | Display order, starting at 1 |
| rule_code | varchar(40) | NO | none | | `R1` to `R7` |
| title | varchar(150) | NO | none | | Card title |
| narrative | text | NO | none | | Plain-language finding |
| query_name | varchar(60) | NO | none | | Key in the SQL catalogue, for example `investigation.defect_onset` |
| query_sql | text | NO | none | | Exact SQL text that produced the rows |
| result_rows | json | NO | none | | Rows returned by the query at creation time (snapshot), stored as `{"columns": [...], "rows": [[...], ...]}` to preserve column order |
| created_at | datetime | NO | (now()) | | Creation time |

## investigation_batches

Junction: batches flagged by an investigation.

| Column | MySQL type | Null | Default | Constraints | Description |
|--------|------------|------|---------|-------------|-------------|
| investigation_id | int | NO | none | part of PRIMARY KEY; FK `investigations.id` ON DELETE CASCADE | Flagging investigation |
| batch_id | int | NO | none | part of PRIMARY KEY; FK `production_batches.id` ON DELETE RESTRICT; implicit index `batch_id` | Flagged batch; the link blocks deletion of the batch |
| reason | varchar(255) | NO | none | | Why the batch was flagged; the service writes "Defect rate above review threshold" |

## ENUM domains

| ENUM name (SQLAlchemy) | Values | Used by |
|------------------------|--------|---------|
| user_role | ADMIN, ENGINEER, OPERATOR, VIEWER | users.role |
| machine_status | IDLE, RUNNING, WARNING, STOPPED, FAULT | machines.status, machine_events.previous_state, machine_events.new_state |
| machine_event_type | STATE_CHANGE, TOOL_WEAR, CALIBRATION_DRIFT, MATERIAL_ISSUE, DOWNTIME, MAINTENANCE | machine_events.event_type |
| severity | INFO, WARNING, CRITICAL | machine_events.severity, alerts.severity |
| order_status | PLANNED, RELEASED, IN_PROGRESS, COMPLETED, CANCELLED | production_orders.status |
| batch_status | IN_PROGRESS, COMPLETED, QUARANTINED | production_batches.status |
| material_lot_status | AVAILABLE, QUARANTINED, CONSUMED | material_lots.status |
| inspection_result | PASS, FAIL | inspections.result |
| alert_type | HIGH_DEFECT_RATE, MACHINE_FAULT, MATERIAL_QUARANTINE, ORDER_OVERDUE | alerts.alert_type |
| investigation_status | OPEN, IN_REVIEW, CLOSED | investigations.status |

MySQL stores ENUM values as the listed strings; the SQLAlchemy `name=` is used by the models only, since MySQL has no named enum types.
