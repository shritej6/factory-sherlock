"""Products, specifications, machines, material lots, and defect types."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.clock import now
from app.core.exceptions import ConflictError, NotFoundError
from app.domain.state_machines import MACHINE_TRANSITIONS, assert_transition
from app.models import (
    DefectType,
    Machine,
    MachineEvent,
    MachineEventType,
    MachineStatus,
    MaterialLot,
    Product,
    ProductSpecification,
    Severity,
)
from app.schemas.catalog import MachineCreate, MaterialLotCreate, ProductCreate, ProductUpdate


def _flush_or_conflict(session: Session, what: str) -> None:
    """Translate a duplicate-key error into a 409 instead of a 500.

    The unique constraint is the real guard against duplicates (two concurrent
    requests cannot both succeed); this just turns its failure into a clean
    client error.
    """
    try:
        session.flush()
    except IntegrityError as exc:
        raise ConflictError(f"{what} already exists") from exc


# Products


def list_products(session: Session) -> list[Product]:
    stmt = select(Product).options(selectinload(Product.specifications)).order_by(Product.code)
    return list(session.scalars(stmt))


def get_product(session: Session, product_id: int) -> Product:
    product = session.get(Product, product_id, options=[selectinload(Product.specifications)])
    if product is None:
        raise NotFoundError(f"Product {product_id} not found")
    return product


def create_product(session: Session, data: ProductCreate) -> Product:
    product = Product(code=data.code, name=data.name, description=data.description)
    product.specifications = [
        ProductSpecification(**spec.model_dump()) for spec in data.specifications
    ]
    session.add(product)
    _flush_or_conflict(session, f"Product {data.code}")
    return product


def update_product(session: Session, product_id: int, data: ProductUpdate) -> Product:
    product = get_product(session, product_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    session.flush()
    return product


def list_specifications(session: Session) -> list[ProductSpecification]:
    """Every specification with its product loaded, ordered by product code then characteristic."""
    stmt = (
        select(ProductSpecification)
        .join(ProductSpecification.product)
        .options(joinedload(ProductSpecification.product))
        .order_by(Product.code, ProductSpecification.characteristic)
    )
    return list(session.scalars(stmt))


# Machines


def list_machines(session: Session) -> list[Machine]:
    return list(session.scalars(select(Machine).order_by(Machine.code)))


def get_machine(session: Session, machine_id: int) -> Machine:
    machine = session.get(Machine, machine_id)
    if machine is None:
        raise NotFoundError(f"Machine {machine_id} not found")
    return machine


def create_machine(session: Session, data: MachineCreate) -> Machine:
    machine = Machine(code=data.code, name=data.name)
    session.add(machine)
    _flush_or_conflict(session, f"Machine {data.code}")
    return machine


def change_machine_status(
    session: Session, machine_id: int, *, target: MachineStatus, reason: str
) -> Machine:
    """Move a machine to a new state and record the change as an event.

    Both writes happen in the caller's transaction so a rejected event insert
    also reverts the status change.
    """
    machine = get_machine(session, machine_id)
    assert_transition(MACHINE_TRANSITIONS, machine.status, target, entity=f"Machine {machine.code}")
    severity = Severity.CRITICAL if target is MachineStatus.FAULT else Severity.INFO
    session.add(
        MachineEvent(
            machine_id=machine.id,
            event_type=MachineEventType.STATE_CHANGE,
            previous_state=machine.status,
            new_state=target,
            severity=severity,
            description=reason,
            occurred_at=now(),
        )
    )
    machine.status = target
    session.flush()
    return machine


def list_machine_events(
    session: Session, machine_id: int, *, limit: int = 100
) -> list[MachineEvent]:
    get_machine(session, machine_id)
    stmt = (
        select(MachineEvent)
        .where(MachineEvent.machine_id == machine_id)
        .order_by(MachineEvent.occurred_at.desc(), MachineEvent.id.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


# Material lots and defect types


def list_material_lots(session: Session) -> list[MaterialLot]:
    return list(session.scalars(select(MaterialLot).order_by(MaterialLot.lot_number)))


def get_material_lot(session: Session, lot_id: int) -> MaterialLot:
    lot = session.get(MaterialLot, lot_id)
    if lot is None:
        raise NotFoundError(f"Material lot {lot_id} not found")
    return lot


def create_material_lot(session: Session, data: MaterialLotCreate) -> MaterialLot:
    lot = MaterialLot(**data.model_dump())
    session.add(lot)
    _flush_or_conflict(session, f"Material lot {data.lot_number}")
    return lot


def list_defect_types(session: Session) -> list[DefectType]:
    return list(session.scalars(select(DefectType).order_by(DefectType.code)))
