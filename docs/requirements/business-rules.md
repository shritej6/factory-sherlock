# Business rules

Every rule the system enforces, with the layer that enforces it. Enforcement layers:

- MySQL constraint: declared in the Alembic migrations under `backend/migrations/versions/` and visible in `database/schema/schema.sql`. Holds even for rows written outside the application.
- Domain state machine: transition tables in `backend/app/domain/state_machines.py`, applied through `assert_transition`, which raises `InvalidTransitionError` (HTTP 422).
- Service check: Python logic in `backend/app/services/*.py` that raises `ValidationError` (422), `NotFoundError` (404), or `ConflictError` (409).
- Schema validation: Pydantic models in `backend/app/schemas/*.py`; failures return 422 with per-field messages.
- Domain function: pure computation in `backend/app/domain/quality_rules.py`.

Where a rule is enforced at more than one layer, all layers are listed; the first is the one a client normally hits.

## Identity and access

| ID | Rule | Enforced by |
|----|------|-------------|
| BR-01 | Usernames and emails are unique. | MySQL constraint (`users.username`, `users.email` UNIQUE) |
| BR-02 | Only active users can log in or use a token. | Service check (`auth_service.authenticate`, `get_active_user`) |
| BR-03 | Login failures return one generic message regardless of cause. | Service check (`auth_service.authenticate`) |
| BR-04 | A token expires after `JWT_ACCESS_TOKEN_MINUTES`. | Service check (`core/security.decode_access_token`) |
| BR-05 | Reads require any authenticated user; writes require the role on the route: OPERATOR set (ADMIN, ENGINEER, OPERATOR) for machine status, order status, batch start and completion, inspections, alert acknowledgement; ENGINEER set (ADMIN, ENGINEER) for products, machines, material lots, order creation and edit, quarantine, investigations, simulation. | Service check (`api/deps.py::require_roles`) |
| BR-06 | The role in the token is informational; the database row decides. | Service check (`api/deps.py::get_current_user`) |

## Reference data

| ID | Rule | Enforced by |
|----|------|-------------|
| BR-10 | Product, machine, and material lot codes are unique and match `^[A-Z0-9][A-Z0-9_-]{1,29}$`. | Schema validation (`CODE_PATTERN`); MySQL constraint (UNIQUE `code`, `lot_number`); service check converts duplicate-key to 409 (`_flush_or_conflict`) |
| BR-11 | A product's characteristic names are unique within the product. | MySQL constraint (`uq_spec_product_characteristic`) |
| BR-12 | Specification target and tolerance are positive with at most three decimals. | Schema validation (`SpecificationCreate`, `gt=0`, `decimal_places=3`); MySQL constraint (`ck_spec_tolerance_positive`, `NUMERIC(10,3)`) |
| BR-13 | Deleting a product cascades to its specifications; a product referenced by an order or a specification referenced by an inspection cannot be deleted. | MySQL constraint (`product_specifications.product_id` CASCADE; `production_orders.product_id` RESTRICT; `inspections.specification_id` RESTRICT) |
| BR-14 | A material lot's received quantity is non-negative with two decimals. | Schema validation (`MaterialLotCreate`, `ge=0`); MySQL constraint (`ck_material_lot_quantity_non_negative`) |
| BR-15 | A material lot that has been used by a batch cannot be deleted. | MySQL constraint (`batch_materials.material_lot_id` RESTRICT) |
| BR-16 | Defect type codes are unique and a defect type in use cannot be deleted. | MySQL constraint (`defect_types.code` UNIQUE; `inspection_defects.defect_type_id` RESTRICT) |
| BR-17 | Status columns accept only the enumerated values. | MySQL constraint (ENUM columns for user role, machine status, event type, severity, order status, batch status, lot status, inspection result, alert type, investigation status); schema validation (enum types) |

## Machines

| ID | Rule | Enforced by |
|----|------|-------------|
| BR-20 | Machine status transitions: IDLE to RUNNING or STOPPED; RUNNING to WARNING, STOPPED, FAULT, or IDLE; WARNING to RUNNING, STOPPED, or FAULT; FAULT to STOPPED only; STOPPED to IDLE only. | Domain state machine (`MACHINE_TRANSITIONS`) via `catalog_service.change_machine_status` and `simulation/machine_state.py` |
| BR-21 | A machine in FAULT must be stopped before it can run again. | Domain state machine (no FAULT to RUNNING edge) |
| BR-22 | Every status change is recorded as a STATE_CHANGE machine event with previous and new state, in the same transaction; a change to FAULT has CRITICAL severity. | Service check (`catalog_service.change_machine_status`, `simulation_service.persist`) |
| BR-23 | A status change requires a reason of 1 to 255 characters. | Schema validation (`MachineStatusChange`) |
| BR-24 | A machine with events, batches, or orders cannot be deleted; deleting a machine clears its reference on alerts and investigations. | MySQL constraint (`machine_events.machine_id`, `production_batches.machine_id` RESTRICT; `production_orders.machine_id`, `alerts.machine_id`, `investigations.machine_id` SET NULL) |

## Production orders

| ID | Rule | Enforced by |
|----|------|-------------|
| BR-30 | Order numbers are unique and match `^[A-Z0-9][A-Z0-9_-]{1,29}$`. | Schema validation (`ProductionOrderCreate`); MySQL constraint (UNIQUE `order_number`); service check (409 on duplicate) |
| BR-31 | Planned quantity is between 1 and 100000. | Schema validation (`gt=0, le=100_000`); MySQL constraint (`ck_order_quantity_planned_positive`) |
| BR-32 | An order references an existing product and, if given, an existing machine. | Service check (`create_order`, `update_order` call `get_product`, `get_machine`; 404); MySQL constraint (foreign keys) |
| BR-33 | Completed quantity is never negative and never exceeds planned quantity. | MySQL constraint (`ck_order_quantity_completed_non_negative`, `ck_order_completed_within_planned`); service check (`complete_batch` returns 409 before the constraint would fire) |
| BR-34 | Order status transitions: PLANNED to RELEASED or CANCELLED; RELEASED to IN_PROGRESS or CANCELLED; IN_PROGRESS to COMPLETED or CANCELLED; COMPLETED and CANCELLED are terminal. | Domain state machine (`ORDER_TRANSITIONS`) via `production_service.change_order_status` |
| BR-35 | A cancelled order cannot start production and a completed order cannot be reopened. | Domain state machine (terminal states) |
| BR-36 | An order must have a machine before it can be released. | Service check (`change_order_status`) |
| BR-37 | An order can be marked COMPLETED only when completed quantity is at least planned quantity. | Service check (`change_order_status`) |
| BR-38 | An order can be edited (machine, planned quantity, due date) only while PLANNED or RELEASED. | Service check (`update_order`, `EDITABLE_ORDER_STATES`) |
| BR-39 | An order with batches cannot be deleted. | MySQL constraint (`production_batches.production_order_id` RESTRICT) |
| BR-40 | Starting a batch on a RELEASED order moves it to IN_PROGRESS; completing the batch that reaches the planned quantity moves the order to COMPLETED. | Service check (`create_batch`, `complete_batch`) |

## Production batches and units

| ID | Rule | Enforced by |
|----|------|-------------|
| BR-50 | A batch can be started only for an order that is RELEASED or IN_PROGRESS and has a machine. | Service check (`create_batch`, `PRODUCIBLE_ORDER_STATES`) |
| BR-51 | Batch quantity is between 1 and 10000 and must not exceed the order's remaining quantity minus the quantity of batches still IN_PROGRESS. | Schema validation (`ProductionBatchCreate`); service check (`create_batch`); MySQL constraint (`ck_batch_quantity_positive`) |
| BR-52 | A batch consumes at least one material lot; each lot is listed once; each lot must be AVAILABLE; each `quantity_used` is positive with two decimals. | Schema validation (`min_length=1`, `gt=0`, `decimal_places=2`); service check (duplicates, status); MySQL constraint (`ck_batch_material_quantity_positive`, composite primary key) |
| BR-53 | Batch numbers are unique and derived as `<order_number>-Bnn`; the batch inherits the order's machine. | Service check (`next_batch_number`); MySQL constraint (UNIQUE `batch_number`) |
| BR-54 | Starting a batch creates one unit per quantity with serial `<batch_number>-Unnnn` and a unique, positive sequence within the batch. | Service check (`create_batch`); MySQL constraint (UNIQUE `serial_number`, `uq_unit_batch_sequence`, `ck_unit_sequence_positive`) |
| BR-55 | Order status change, batch, material links, and units are written atomically. | Service check plus request transaction (`core/database.get_db_session`) |
| BR-56 | Batch status transitions: IN_PROGRESS to COMPLETED or QUARANTINED; COMPLETED to QUARANTINED; QUARANTINED is terminal. | Domain state machine (`BATCH_TRANSITIONS`) via `complete_batch`, `quarantine_batch` |
| BR-57 | Completing a batch sets `completed_at` and adds its quantity to the order; it is refused if that would exceed the planned quantity. | Service check (`complete_batch`, 409); MySQL constraint (`ck_order_completed_within_planned`) |
| BR-58 | Deleting a batch removes its units, material links, and investigation links; a batch cannot be deleted while referenced otherwise (no delete endpoint exists). | MySQL constraint (CASCADE on `production_units`, `batch_materials`, `investigation_batches`) |

## Quality

| ID | Rule | Enforced by |
|----|------|-------------|
| BR-60 | A measurement passes when `abs(measured - target) <= tolerance`; otherwise it fails. | Domain function (`evaluate_measurement`) used by `quality_service.record_inspection` and the simulator |
| BR-61 | A failed measurement is classified by characteristic: diameter characteristics (`diameter`, `outer_diameter`, `bore_diameter`) to OVERSIZE_DIAMETER or UNDERSIZE_DIAMETER by sign; `hole_position` to HOLE_POSITION_DEVIATION; others to DIMENSIONAL_DEVIATION. | Domain function (`classify_defect`) |
| BR-62 | The specification must belong to the product of the unit's order. | Service check (`record_inspection`) |
| BR-63 | The computed defect code is always attached to a failed inspection; additional codes supplied by the operator must exist; a passing inspection cannot carry defect codes. | Service check (`record_inspection`) |
| BR-64 | A unit has at most one inspection per specification. | MySQL constraint (`uq_inspection_unit_spec`); service check (409 via `_flush_or_conflict`) |
| BR-65 | Measured values have at most three decimals. | Schema validation (`InspectionCreate`, `decimal_places=3`); MySQL constraint (`NUMERIC(10,3)`) |
| BR-66 | The stored PASS/FAIL result is not recomputed when a specification changes. | Service check (result persisted at inspection time; model docstring) |
| BR-67 | Defect rate is `failed / inspected` rounded to four decimals, and 0 when nothing was inspected. | Domain function (`defect_rate`), mirrored in SQL with `NULLIF` and `ROUND(..., 4)` |
| BR-68 | A simulated batch whose defect rate reaches 0.15 raises a HIGH_DEFECT_RATE alert, once per consecutive run above the threshold. | Service check (`simulation/engine.py`) |
| BR-69 | An alert is acknowledged at most once; later calls do not change the acknowledgement. | Service check (`analytics_service.acknowledge_alert`); the route requires the Operator role set |

## Investigations

| ID | Rule | Enforced by |
|----|------|-------------|
| BR-70 | The window end must be after the window start. | Service check (`open_investigation`); MySQL constraint (`ck_investigation_window_order`) |
| BR-71 | Title is 3 to 150 characters; conclusion at most 4000 characters; machine and product ids, if given, must exist. | Schema validation (`InvestigationCreate`, `InvestigationStatusChange`); service check (404) |
| BR-72 | Evidence cards are numbered uniquely per investigation and store the query SQL and rows. | Service check (`open_investigation`); MySQL constraint (`uq_evidence_investigation_sequence`) |
| BR-73 | Every batch returned by rule R5 is linked to the investigation with the reason "Defect rate above review threshold". | Service check (`open_investigation`) |
| BR-74 | Investigation status transitions: OPEN to IN_REVIEW or CLOSED; IN_REVIEW to CLOSED or OPEN; CLOSED is terminal. | Domain state machine (`INVESTIGATION_TRANSITIONS`) via `change_status` |
| BR-75 | Closing requires a conclusion and sets `closed_at`. | Service check (`change_status`) |
| BR-76 | Rule narratives and the summary never assert causation. | Service check by convention (`rules.py`, `summary.py` wording); reviewed in code review |
| BR-77 | A machine is "elevated" when its defect rate is at least 0.05 and at least twice the fleet rate (or the fleet rate is zero); the onset is the first hourly bucket at or above 0.10; batches at or above 0.10 that are not quarantined require review; events are searched 6 hours before onset. | Service check (`RuleThresholds`) |
| BR-78 | Deleting an investigation removes its evidence and batch links; deleting its machine, product, or opener clears the reference. | MySQL constraint (CASCADE on evidence and links; SET NULL on `machine_id`, `product_id`, `opened_by`) |

## Traceability and quarantine

| ID | Rule | Enforced by |
|----|------|-------------|
| BR-80 | A batch to lot link is unique per pair. | MySQL constraint (composite primary key on `batch_materials`) |
| BR-81 | Forward trace requires an existing lot; backward trace requires an existing serial. | Service check (404) |
| BR-82 | Quarantining a batch requires a reason of 5 to 255 characters, is allowed from IN_PROGRESS or COMPLETED, and records a MATERIAL_QUARANTINE alert of WARNING severity. | Schema validation (`QuarantineRequest`); domain state machine; service check (`quarantine_batch`) |
| BR-83 | Quarantining a lot sets the lot to QUARANTINED, quarantines every linked batch that is not already quarantined with reason "Material lot <lot>: <reason>", records one CRITICAL alert, and does all of it in one transaction. | Service check (`quarantine_lot`) plus request transaction |
| BR-84 | A lot that is not AVAILABLE cannot be used for a new batch. | Service check (`create_batch`); simulator ignores such lots (`load_catalog`) |
| BR-85 | Quarantine is not reversible through the API. | Domain state machine (`QUARANTINED` terminal); no lot release endpoint |

## Simulation

| ID | Rule | Enforced by |
|----|------|-------------|
| BR-90 | Seed is non-negative; batches per machine 1 to 200; units per batch 1 to 500; minutes per batch 1 to 600; fault start index at least 0; unknown request fields are rejected. | Schema validation (`SimulationRequest`, `FaultScenario`) |
| BR-91 | Fault kind must be one of the five `FaultKind` values; the machine code must exist. | Service check (`to_config` 422; engine `ValueError` mapped to 422) |
| BR-92 | Every product must have at least one AVAILABLE lot of its material. | Service check (`load_catalog`) |
| BR-93 | The engine's config and catalog invariants hold (sizes at least 1; at least one product and one machine; every product has specifications and lots). | Service check (`SimulationConfig.__post_init__`, `Catalog.__post_init__`) |
| BR-94 | Simulated state transitions obey `MACHINE_TRANSITIONS`. | Domain state machine (`MachineStateTracker.transition`) |
| BR-95 | All simulated rows are written in one transaction. | Service check plus request transaction |

## Overdue order alerts

The check runs on demand through `POST /api/v1/analytics/alerts/checks/overdue-orders` (Operator role set) and through `uv run python -m app.jobs.check_overdue_orders` (`make check-overdue`). Both call `alert_service.raise_overdue_order_alerts`.

| ID | Rule | Enforced by |
|----|------|-------------|
| BR-100 | An order is overdue when its `due_date` is before the check date (`as_of`, default the server clock) and its status is PLANNED, RELEASED, or IN_PROGRESS. COMPLETED and CANCELLED orders and orders without a due date are never overdue; an order due on the check date is not yet overdue. | Service check (`alert_service.overdue_orders`, `OPEN_ORDER_STATES`, `days_late`) |
| BR-101 | Each overdue order gets one ORDER_OVERDUE alert linked through `alerts.production_order_id`, carrying the order's `machine_id` when it has one and `created_at` equal to `as_of`. | Service check (`raise_overdue_order_alerts`); MySQL constraint (`fk_alerts_production_order`) |
| BR-102 | Severity is WARNING when the order is 1 to 2 days late and CRITICAL from the third day. The message is `Order <order_number> is <n> day(s) overdue (due <due_date>)`. | Service check (`overdue_severity`, `CRITICAL_AFTER_DAYS`, `overdue_message`) |
| BR-103 | The check is idempotent: an order that already has an unacknowledged ORDER_OVERDUE alert gets no new one, however often the check runs. After that alert is acknowledged, the next check raises a fresh alert (with the current days late and severity) if the order is still overdue. | Service check (`_orders_with_open_alert`) |
| BR-104 | Deleting an order keeps its alerts and clears the link; the alert text still names the order number. | MySQL constraint (`alerts.production_order_id` ON DELETE SET NULL) |

## Rules stated in the brief but not enforced in code

- Material consumption is not reconciled: `quantity_used` may exceed `quantity_received`, and lots are never marked CONSUMED.
- Two simulation faults on the same machine and batch index are not rejected; the last one listed wins.
- Order `due_date` does not block anything: nothing prevents completing an order late. Overdue orders are reported by the ORDER_OVERDUE check (BR-100 to BR-104) and labelled by the `production_performance` query; neither changes the order.
