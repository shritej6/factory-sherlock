"""Production orders and batches: the manufacturing execution workflow."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.clock import now
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.state_machines import BATCH_TRANSITIONS, ORDER_TRANSITIONS, assert_transition
from app.models import (
    BatchMaterial,
    BatchStatus,
    MaterialLotStatus,
    OrderStatus,
    ProductionBatch,
    ProductionOrder,
    ProductionUnit,
)
from app.schemas.production import (
    ProductionBatchCreate,
    ProductionOrderCreate,
    ProductionOrderUpdate,
)
from app.services import catalog_service
from app.services.catalog_service import _flush_or_conflict

EDITABLE_ORDER_STATES = frozenset({OrderStatus.PLANNED, OrderStatus.RELEASED})
PRODUCIBLE_ORDER_STATES = frozenset({OrderStatus.RELEASED, OrderStatus.IN_PROGRESS})


# Orders


def list_orders(session: Session, *, status: OrderStatus | None = None) -> list[ProductionOrder]:
    stmt = select(ProductionOrder).order_by(
        ProductionOrder.created_at.desc(), ProductionOrder.id.desc()
    )
    if status is not None:
        stmt = stmt.where(ProductionOrder.status == status)
    return list(session.scalars(stmt))


def get_order(session: Session, order_id: int) -> ProductionOrder:
    order = session.get(ProductionOrder, order_id)
    if order is None:
        raise NotFoundError(f"Production order {order_id} not found")
    return order


def create_order(session: Session, data: ProductionOrderCreate) -> ProductionOrder:
    catalog_service.get_product(session, data.product_id)
    if data.machine_id is not None:
        catalog_service.get_machine(session, data.machine_id)
    order = ProductionOrder(**data.model_dump())
    session.add(order)
    _flush_or_conflict(session, f"Production order {data.order_number}")
    return order


def update_order(session: Session, order_id: int, data: ProductionOrderUpdate) -> ProductionOrder:
    order = get_order(session, order_id)
    if order.status not in EDITABLE_ORDER_STATES:
        raise ValidationError(
            f"Order {order.order_number} is {order.status} and can no longer be edited"
        )
    changes = data.model_dump(exclude_unset=True)
    if "machine_id" in changes:
        if changes["machine_id"] is None and order.status is OrderStatus.RELEASED:
            raise ValidationError("A released order must keep a machine assignment")
        if changes["machine_id"] is not None:
            catalog_service.get_machine(session, changes["machine_id"])
    for field, value in changes.items():
        setattr(order, field, value)
    session.flush()
    return order


def change_order_status(session: Session, order_id: int, target: OrderStatus) -> ProductionOrder:
    order = get_order(session, order_id)
    assert_transition(ORDER_TRANSITIONS, order.status, target, entity=f"Order {order.order_number}")
    if target is OrderStatus.RELEASED and order.machine_id is None:
        raise ValidationError("An order must be assigned to a machine before release")
    if target is OrderStatus.COMPLETED and order.quantity_completed < order.quantity_planned:
        raise ValidationError(
            "Order cannot be completed: "
            f"{order.quantity_completed} of {order.quantity_planned} units produced"
        )
    order.status = target
    session.flush()
    return order


# Batches


def list_batches(
    session: Session, *, order_id: int | None = None, machine_id: int | None = None
) -> list[ProductionBatch]:
    stmt = (
        select(ProductionBatch)
        .options(selectinload(ProductionBatch.material_links))
        .order_by(ProductionBatch.started_at.desc(), ProductionBatch.id.desc())
    )
    if order_id is not None:
        stmt = stmt.where(ProductionBatch.production_order_id == order_id)
    if machine_id is not None:
        stmt = stmt.where(ProductionBatch.machine_id == machine_id)
    return list(session.scalars(stmt))


def get_batch(session: Session, batch_id: int) -> ProductionBatch:
    batch = session.get(
        ProductionBatch, batch_id, options=[selectinload(ProductionBatch.material_links)]
    )
    if batch is None:
        raise NotFoundError(f"Production batch {batch_id} not found")
    return batch


def next_batch_number(session: Session, order: ProductionOrder) -> str:
    count = session.scalar(
        select(func.count(ProductionBatch.id)).where(
            ProductionBatch.production_order_id == order.id
        )
    )
    return f"{order.order_number}-B{(count or 0) + 1:02d}"


def create_batch(session: Session, data: ProductionBatchCreate) -> ProductionBatch:
    """Start a batch: validates the order, consumes material lots, creates units.

    This is the workflow that must succeed or fail as a whole. The order status
    change, the batch row, its junction rows, and its units are all written in
    the request transaction; any validation error below leaves nothing behind.
    """
    order = get_order(session, data.production_order_id)
    if order.status not in PRODUCIBLE_ORDER_STATES:
        raise ValidationError(f"Order {order.order_number} is {order.status}; release it first")
    if order.machine_id is None:
        raise ValidationError("Order has no machine assigned")
    remaining = order.quantity_planned - order.quantity_completed
    in_progress = session.scalar(
        select(func.coalesce(func.sum(ProductionBatch.quantity), 0)).where(
            ProductionBatch.production_order_id == order.id,
            ProductionBatch.status == BatchStatus.IN_PROGRESS,
        )
    )
    if data.quantity > remaining - int(in_progress or 0):
        raise ValidationError(
            f"Batch of {data.quantity} exceeds the {remaining - int(in_progress or 0)} units "
            "still to be produced for this order"
        )

    lot_ids = [m.material_lot_id for m in data.materials]
    if len(set(lot_ids)) != len(lot_ids):
        raise ValidationError("The same material lot is listed more than once")
    for material in data.materials:
        lot = catalog_service.get_material_lot(session, material.material_lot_id)
        if lot.status is not MaterialLotStatus.AVAILABLE:
            raise ValidationError(
                f"Material lot {lot.lot_number} is {lot.status} and cannot be used"
            )

    if order.status is OrderStatus.RELEASED:
        order.status = OrderStatus.IN_PROGRESS
    started_at = now()
    batch = ProductionBatch(
        batch_number=next_batch_number(session, order),
        production_order_id=order.id,
        machine_id=order.machine_id,
        quantity=data.quantity,
        started_at=started_at,
    )
    batch.material_links = [BatchMaterial(**m.model_dump()) for m in data.materials]
    batch.units = [
        ProductionUnit(
            serial_number=f"{batch.batch_number}-U{seq:04d}",
            sequence_in_batch=seq,
            produced_at=started_at,
        )
        for seq in range(1, data.quantity + 1)
    ]
    session.add(batch)
    _flush_or_conflict(session, f"Batch {batch.batch_number}")
    return batch


def complete_batch(session: Session, batch_id: int) -> ProductionBatch:
    batch = get_batch(session, batch_id)
    assert_transition(
        BATCH_TRANSITIONS, batch.status, BatchStatus.COMPLETED, entity=f"Batch {batch.batch_number}"
    )
    order = batch.order
    if order.status is not OrderStatus.IN_PROGRESS:
        raise ValidationError(
            f"Order {order.order_number} is {order.status}; only IN_PROGRESS orders accept "
            "completed batches"
        )
    if order.quantity_completed + batch.quantity > order.quantity_planned:
        # The CHECK constraint would reject this too; failing here gives a clearer message.
        raise ConflictError("Completing this batch would exceed the order's planned quantity")
    batch.status = BatchStatus.COMPLETED
    batch.completed_at = now()
    # Increment in SQL so two batches completing at once cannot lose an update;
    # ck_order_completed_within_planned is the final guard against overshoot.
    session.execute(
        update(ProductionOrder)
        .where(ProductionOrder.id == order.id)
        .values(quantity_completed=ProductionOrder.quantity_completed + batch.quantity)
    )
    session.refresh(order)
    if order.quantity_completed == order.quantity_planned:
        assert_transition(
            ORDER_TRANSITIONS, order.status, OrderStatus.COMPLETED, entity=order.order_number
        )
        order.status = OrderStatus.COMPLETED
    session.flush()
    return batch
