"""Runs the simulation engine and persists its output in one transaction."""

import logging

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import Base
from app.core.exceptions import ValidationError
from app.domain.quality_rules import DEFECT_CODES
from app.models import (
    Alert,
    BatchMaterial,
    BatchStatus,
    DefectType,
    Inspection,
    InspectionDefect,
    InspectionResult,
    Machine,
    MachineEvent,
    MachineEventType,
    MaterialLot,
    MaterialLotStatus,
    OrderStatus,
    Product,
    ProductionBatch,
    ProductionOrder,
    ProductionUnit,
    Severity,
)
from app.schemas.simulation import SimulationRequest, SimulationResult
from app.simulation.config import (
    Catalog,
    FaultScenario,
    MachineRef,
    ProductRef,
    SimulationConfig,
    SpecRef,
)
from app.simulation.engine import SimulationEngine
from app.simulation.events import SimulatedBatch, SimulationOutput

logger = logging.getLogger(__name__)

# Which seeded material lots feed which product (by material name).
PRODUCT_MATERIALS = {
    "STEEL-SHAFT": "Steel bar stock 4140",
    "METAL-BRACKET": "Sheet steel 3 mm",
    "GEAR": "Alloy gear blank 8620",
}


def load_catalog(session: Session) -> Catalog:
    products = session.scalars(
        select(Product).options(selectinload(Product.specifications)).order_by(Product.code)
    ).all()
    machines = session.scalars(select(Machine).order_by(Machine.code)).all()
    lots = session.scalars(
        select(MaterialLot)
        .where(MaterialLot.status == MaterialLotStatus.AVAILABLE)
        .order_by(MaterialLot.lot_number)
    ).all()
    defect_ids = {d.code: d.id for d in session.scalars(select(DefectType))}
    missing = sorted(set(DEFECT_CODES) - set(defect_ids))
    if missing:
        raise ValidationError(
            "Defect catalogue is missing codes the simulator produces; run the reference seed",
            details={"missing": missing},
        )

    product_refs = []
    for product in products:
        material = PRODUCT_MATERIALS.get(product.code)
        lot_ids = tuple(lot.id for lot in lots if lot.material_name == material)
        if not lot_ids:
            raise ValidationError(f"No available material lots for product {product.code}")
        product_refs.append(
            ProductRef(
                product_id=product.id,
                code=product.code,
                specs=tuple(
                    SpecRef(s.id, s.characteristic, s.target_value, s.tolerance)
                    for s in product.specifications
                ),
                material_lot_ids=lot_ids,
            )
        )
    return Catalog(
        products=tuple(product_refs),
        machines=tuple(MachineRef(m.id, m.code, m.status) for m in machines),
        defect_type_ids=defect_ids,
    )


def to_config(request: SimulationRequest) -> SimulationConfig:
    faults = tuple(
        FaultScenario(f.machine_code, f.fault, f.start_batch_index) for f in request.faults
    )
    return SimulationConfig(
        seed=request.seed,
        start_time=request.start_time,
        batches_per_machine=request.batches_per_machine,
        units_per_batch=request.units_per_batch,
        minutes_per_batch=request.minutes_per_batch,
        faults=faults,
    )


def run_simulation(session: Session, request: SimulationRequest) -> SimulationResult:
    catalog = load_catalog(session)
    config = to_config(request)
    try:
        output = SimulationEngine(config, catalog).run()
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc
    result = persist(session, output, catalog, run_tag=_next_run_tag(session))
    logger.info(
        "simulation persisted",
        extra={"operation": "simulation", "request_id": f"seed-{request.seed}"},
    )
    return result


def _next_run_tag(session: Session) -> str:
    count = session.scalar(select(func.count(ProductionOrder.id))) or 0
    return f"SIM{count + 1:04d}"


BULK_CHUNK_SIZE = 1000

# A persisted batch paired with the engine record it came from.
BatchPair = tuple[SimulatedBatch, ProductionBatch]
Row = dict[str, object]


def persist(
    session: Session, output: SimulationOutput, catalog: Catalog, *, run_tag: str
) -> SimulationResult:
    """Write one simulation run inside the caller's transaction.

    Orders, batches, and alerts are few and go through the ORM. Units,
    inspections, inspection defects, and machine events can number in the
    thousands and are written with chunked multi-row INSERTs. MySQL returns no
    generated ids for multi-row inserts, so each bulk step selects the ids it
    needs back by natural key (serial number, then unit and specification).
    """
    orders = _persist_orders(session, output, catalog, run_tag)
    batches = _persist_batches(session, output, orders)
    _complete_orders(orders, batches)

    _bulk_insert(session, ProductionUnit, _unit_rows(batches))
    unit_ids = _unit_ids_by_serial(session, batches)
    inspection_rows, failed = _inspection_rows(batches, unit_ids)
    _bulk_insert(session, Inspection, inspection_rows)
    inspection_ids = _inspection_ids_by_unit_and_spec(session, batches)
    _bulk_insert(
        session, InspectionDefect, _defect_rows(batches, unit_ids, inspection_ids, catalog)
    )
    _bulk_insert(session, MachineEvent, _event_rows(output))

    _persist_alerts(session, output)
    for machine_id, status in output.final_states.items():
        session.get_one(Machine, machine_id).status = status
    session.flush()
    return SimulationResult(
        seed=output.seed,
        orders_created=len(output.orders),
        batches_created=len(output.batches),
        units_created=len(unit_ids),
        inspections_created=len(inspection_rows),
        failed_inspections=failed,
        events_created=len(output.state_changes) + len(output.fault_events),
        alerts_created=len(output.alerts),
    )


def _persist_orders(
    session: Session, output: SimulationOutput, catalog: Catalog, run_tag: str
) -> dict[tuple[int, int], ProductionOrder]:
    machine_codes = {m.machine_id: m.code for m in catalog.machines}
    orders: dict[tuple[int, int], ProductionOrder] = {}
    for sim_order in output.orders:
        code = machine_codes[sim_order.machine_id]
        order = ProductionOrder(
            order_number=f"{run_tag}-{code}-{sim_order.order_index + 1:02d}",
            product_id=sim_order.product_id,
            machine_id=sim_order.machine_id,
            quantity_planned=sim_order.quantity_planned,
            quantity_completed=0,
            status=OrderStatus.IN_PROGRESS,
            due_date=sim_order.due_date.date(),
            created_at=sim_order.created_at,
            updated_at=sim_order.created_at,
        )
        orders[(sim_order.machine_id, sim_order.order_index)] = order
        session.add(order)
    session.flush()
    return orders


def _persist_batches(
    session: Session, output: SimulationOutput, orders: dict[tuple[int, int], ProductionOrder]
) -> list[BatchPair]:
    """Batches go through the ORM so their ids are known before units are written."""
    batch_counter: dict[tuple[int, int], int] = {}
    pairs: list[BatchPair] = []
    for sim_batch in output.batches:
        key = (sim_batch.machine_id, sim_batch.order_index)
        order = orders[key]
        batch_counter[key] = batch_counter.get(key, 0) + 1
        batch = ProductionBatch(
            batch_number=f"{order.order_number}-B{batch_counter[key]:02d}",
            production_order_id=order.id,
            machine_id=sim_batch.machine_id,
            quantity=len(sim_batch.units),
            status=BatchStatus.COMPLETED,
            started_at=sim_batch.started_at,
            completed_at=sim_batch.completed_at,
        )
        batch.material_links = [
            BatchMaterial(material_lot_id=lot_id, quantity_used=len(sim_batch.units))
            for lot_id in sim_batch.material_lot_ids
        ]
        session.add(batch)
        pairs.append((sim_batch, batch))
    session.flush()
    return pairs


def _complete_orders(
    orders: dict[tuple[int, int], ProductionOrder], batches: list[BatchPair]
) -> None:
    """Orders were created in this transaction, so their counters can be set directly."""
    for sim_batch, batch in batches:
        order = orders[(sim_batch.machine_id, sim_batch.order_index)]
        order.quantity_completed += batch.quantity
        if order.quantity_completed >= order.quantity_planned:
            order.status = OrderStatus.COMPLETED


def _serial_number(batch: ProductionBatch, sequence: int) -> str:
    return f"{batch.batch_number}-U{sequence:04d}"


def _unit_rows(batches: list[BatchPair]) -> list[Row]:
    return [
        {
            "batch_id": batch.id,
            "serial_number": _serial_number(batch, sim_unit.sequence_in_batch),
            "sequence_in_batch": sim_unit.sequence_in_batch,
            "produced_at": sim_unit.produced_at,
        }
        for sim_batch, batch in batches
        for sim_unit in sim_batch.units
    ]


def _unit_ids_by_serial(session: Session, batches: list[BatchPair]) -> dict[str, int]:
    batch_ids = [batch.id for _, batch in batches]
    rows = session.execute(
        select(ProductionUnit.serial_number, ProductionUnit.id).where(
            ProductionUnit.batch_id.in_(batch_ids)
        )
    )
    return {serial: unit_id for serial, unit_id in rows}


def _inspection_rows(batches: list[BatchPair], unit_ids: dict[str, int]) -> tuple[list[Row], int]:
    rows: list[Row] = []
    failed = 0
    for sim_batch, batch in batches:
        for sim_unit in sim_batch.units:
            unit_id = unit_ids[_serial_number(batch, sim_unit.sequence_in_batch)]
            for sim_insp in sim_unit.inspections:
                rows.append(
                    {
                        "unit_id": unit_id,
                        "specification_id": sim_insp.specification_id,
                        "measured_value": sim_insp.measured_value,
                        "result": sim_insp.result,
                        "inspected_at": sim_insp.at,
                    }
                )
                failed += sim_insp.result is InspectionResult.FAIL
    return rows, failed


def _inspection_ids_by_unit_and_spec(
    session: Session, batches: list[BatchPair]
) -> dict[tuple[int, int], int]:
    batch_ids = [batch.id for _, batch in batches]
    rows = session.execute(
        select(Inspection.unit_id, Inspection.specification_id, Inspection.id)
        .join(ProductionUnit, ProductionUnit.id == Inspection.unit_id)
        .where(ProductionUnit.batch_id.in_(batch_ids))
    )
    return {(unit_id, spec_id): inspection_id for unit_id, spec_id, inspection_id in rows}


def _defect_rows(
    batches: list[BatchPair],
    unit_ids: dict[str, int],
    inspection_ids: dict[tuple[int, int], int],
    catalog: Catalog,
) -> list[Row]:
    rows: list[Row] = []
    for sim_batch, batch in batches:
        for sim_unit in sim_batch.units:
            unit_id = unit_ids[_serial_number(batch, sim_unit.sequence_in_batch)]
            for sim_insp in sim_unit.inspections:
                inspection_id = inspection_ids[(unit_id, sim_insp.specification_id)]
                rows.extend(
                    {
                        "inspection_id": inspection_id,
                        "defect_type_id": catalog.defect_type_ids[code],
                    }
                    for code in sim_insp.defect_codes
                )
    return rows


def _event_rows(output: SimulationOutput) -> list[Row]:
    """State changes and fault events share one table, so every row names every column."""
    rows: list[Row] = [
        {
            "machine_id": change.machine_id,
            "event_type": MachineEventType.STATE_CHANGE,
            "previous_state": change.previous,
            "new_state": change.new,
            "severity": Severity.CRITICAL if change.new.value == "FAULT" else Severity.INFO,
            "description": change.reason,
            "occurred_at": change.at,
        }
        for change in output.state_changes
    ]
    rows.extend(
        {
            "machine_id": event.machine_id,
            "event_type": event.event_type,
            "previous_state": None,
            "new_state": None,
            "severity": event.severity,
            "description": event.description,
            "occurred_at": event.at,
        }
        for event in output.fault_events
    )
    return rows


def _persist_alerts(session: Session, output: SimulationOutput) -> None:
    for alert in output.alerts:
        session.add(
            Alert(
                machine_id=alert.machine_id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                message=alert.message,
                created_at=alert.at,
            )
        )


def _bulk_insert(session: Session, model: type[Base], rows: list[Row]) -> None:
    """Multi-row INSERTs in chunks, inside the session's current transaction."""
    for start in range(0, len(rows), BULK_CHUNK_SIZE):
        session.execute(insert(model), rows[start : start + BULK_CHUNK_SIZE])
