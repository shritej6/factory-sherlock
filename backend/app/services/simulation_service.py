"""Runs the simulation engine and persists its output in one transaction."""

import logging

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

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
from app.simulation.events import SimulationOutput

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


def persist(
    session: Session, output: SimulationOutput, catalog: Catalog, *, run_tag: str
) -> SimulationResult:
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

    units_created = inspections_created = failed = 0
    batch_counter: dict[int, int] = {}
    for sim_batch in output.batches:
        order = orders[(sim_batch.machine_id, sim_batch.order_index)]
        batch_counter[order.id] = batch_counter.get(order.id, 0) + 1
        batch = ProductionBatch(
            batch_number=f"{order.order_number}-B{batch_counter[order.id]:02d}",
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
        session.flush()
        for sim_unit in sim_batch.units:
            unit = ProductionUnit(
                batch_id=batch.id,
                serial_number=f"{batch.batch_number}-U{sim_unit.sequence_in_batch:04d}",
                sequence_in_batch=sim_unit.sequence_in_batch,
                produced_at=sim_unit.produced_at,
            )
            for sim_insp in sim_unit.inspections:
                inspection = Inspection(
                    specification_id=sim_insp.specification_id,
                    measured_value=sim_insp.measured_value,
                    result=sim_insp.result,
                    inspected_at=sim_insp.at,
                )
                inspection.defect_links = [
                    InspectionDefect(defect_type_id=catalog.defect_type_ids[code])
                    for code in sim_insp.defect_codes
                ]
                unit.inspections.append(inspection)
                inspections_created += 1
                failed += sim_insp.result is InspectionResult.FAIL
            session.add(unit)
            units_created += 1
        session.execute(
            update(ProductionOrder)
            .where(ProductionOrder.id == order.id)
            .values(quantity_completed=ProductionOrder.quantity_completed + len(sim_batch.units))
        )
        session.refresh(order)
        if order.quantity_completed >= order.quantity_planned:
            order.status = OrderStatus.COMPLETED

    for change in output.state_changes:
        session.add(
            MachineEvent(
                machine_id=change.machine_id,
                event_type=MachineEventType.STATE_CHANGE,
                previous_state=change.previous,
                new_state=change.new,
                severity=Severity.CRITICAL if change.new.value == "FAULT" else Severity.INFO,
                description=change.reason,
                occurred_at=change.at,
            )
        )
    for event in output.fault_events:
        session.add(
            MachineEvent(
                machine_id=event.machine_id,
                event_type=event.event_type,
                severity=event.severity,
                description=event.description,
                occurred_at=event.at,
            )
        )
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
    for machine_id, status in output.final_states.items():
        session.get_one(Machine, machine_id).status = status
    session.flush()
    return SimulationResult(
        seed=output.seed,
        orders_created=len(output.orders),
        batches_created=len(output.batches),
        units_created=units_created,
        inspections_created=inspections_created,
        failed_inspections=failed,
        events_created=len(output.state_changes) + len(output.fault_events),
        alerts_created=len(output.alerts),
    )
