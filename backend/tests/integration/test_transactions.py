"""Database-level guarantees: rollback, foreign keys, check constraints."""

from datetime import datetime
from decimal import Decimal

import pytest
from app.core.database import SessionLocal, engine
from app.core.exceptions import ConflictError
from app.models import (
    Investigation,
    InvestigationEvidence,
    Machine,
    MachineEvent,
    MachineEventType,
    MaterialLot,
    OrderStatus,
    Product,
    ProductionBatch,
    ProductionOrder,
    ProductionUnit,
    Severity,
)
from app.services import production_service
from sqlalchemy import func, select, text
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from sqlalchemy.orm import Session


def test_session_rolls_back_partial_writes(db_session: Session) -> None:
    product_id = db_session.scalar(select(Product.id).where(Product.code == "GEAR"))
    with SessionLocal() as session:
        session.add(
            ProductionOrder(order_number="PO-RB-1", product_id=product_id, quantity_planned=5)
        )
        session.flush()
        with pytest.raises(IntegrityError):
            # Second insert violates the unique order number; the whole unit of work is discarded.
            session.add(
                ProductionOrder(order_number="PO-RB-1", product_id=product_id, quantity_planned=5)
            )
            session.flush()
        session.rollback()
    assert db_session.scalar(select(func.count(ProductionOrder.id))) == 0


def test_foreign_keys_are_enforced_by_mysql(db_session: Session) -> None:
    with pytest.raises(IntegrityError):
        db_session.add(ProductionOrder(order_number="PO-FK", product_id=999999, quantity_planned=1))
        db_session.flush()
    db_session.rollback()
    machine_id = db_session.scalar(select(Machine.id).where(Machine.code == "CNC-01"))
    db_session.add(
        MachineEvent(
            machine_id=machine_id,
            event_type=MachineEventType.MAINTENANCE,
            severity=Severity.INFO,
            description="x",
            occurred_at=datetime(2026, 1, 1),
        )
    )
    db_session.flush()
    with pytest.raises(IntegrityError):  # ON DELETE RESTRICT protects the event history
        db_session.execute(text("DELETE FROM machines WHERE id = :id"), {"id": machine_id})
    db_session.rollback()


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO production_orders (order_number, product_id, quantity_planned, quantity_completed, status)"
        " SELECT 'PO-CK', id, 0, 0, 'PLANNED' FROM products LIMIT 1",
        "INSERT INTO production_orders (order_number, product_id, quantity_planned, quantity_completed, status)"
        " SELECT 'PO-CK', id, 5, 6, 'PLANNED' FROM products LIMIT 1",
        "INSERT INTO product_specifications (product_id, characteristic, target_value, tolerance, unit)"
        " SELECT id, 'x', 1, 0, 'mm' FROM products LIMIT 1",
        "INSERT INTO production_orders (order_number, product_id, quantity_planned, quantity_completed, status)"
        " SELECT 'PO-EN', id, 5, 0, 'NOT_A_STATUS' FROM products LIMIT 1",
        # ck_event_state_pair: only STATE_CHANGE events carry a new state.
        "INSERT INTO machine_events (machine_id, event_type, new_state, severity, description, occurred_at)"
        " SELECT id, 'MAINTENANCE', 'IDLE', 'INFO', 'x', '2026-01-01' FROM machines LIMIT 1",
        # ck_investigation_closed: a CLOSED investigation must record when it closed.
        "INSERT INTO investigations (title, window_start, window_end, status, closed_at)"
        " VALUES ('x', '2026-01-01', '2026-01-02', 'CLOSED', NULL)",
    ],
)
def test_check_and_enum_constraints_reject_bad_rows(db_session: Session, statement: str) -> None:
    with pytest.raises((IntegrityError, OperationalError, DataError)):
        db_session.execute(text(statement))
    db_session.rollback()


def _in_progress_order(session: Session, order_number: str) -> ProductionOrder:
    order = ProductionOrder(
        order_number=order_number,
        product_id=session.scalar(select(Product.id).where(Product.code == "GEAR")),
        machine_id=session.scalar(select(Machine.id).where(Machine.code == "CNC-01")),
        quantity_planned=10,
        status=OrderStatus.IN_PROGRESS,
    )
    session.add(order)
    session.flush()
    return order


@pytest.mark.parametrize(
    "status, completed_at, quarantine_reason",
    [
        ("COMPLETED", None, None),  # ck_batch_completed_has_time
        ("COMPLETED", datetime(2026, 1, 1, 7), None),  # ck_batch_completed_after_start
        ("QUARANTINED", None, None),  # ck_batch_quarantine_reason: reason missing
        ("IN_PROGRESS", None, "Suspect lot"),  # ck_batch_quarantine_reason: reason without status
    ],
)
def test_batch_lifecycle_checks_reject_inconsistent_rows(
    db_session: Session, status: str, completed_at: datetime | None, quarantine_reason: str | None
) -> None:
    order = _in_progress_order(db_session, "PO-BCK")
    statement = text(
        "INSERT INTO production_batches (batch_number, production_order_id, machine_id, quantity,"
        " status, started_at, completed_at, quarantine_reason)"
        " VALUES ('PO-BCK-B01', :order_id, :machine_id, 2, :status, '2026-01-01 08:00:00',"
        " :completed_at, :quarantine_reason)"
    )
    params = {
        "order_id": order.id,
        "machine_id": order.machine_id,
        "status": status,
        "completed_at": completed_at,
        "quarantine_reason": quarantine_reason,
    }
    with pytest.raises((IntegrityError, OperationalError)):
        db_session.execute(statement, params)
    db_session.rollback()


def _batch_with_units(session: Session, order: ProductionOrder, quantity: int) -> ProductionBatch:
    started = datetime(2026, 1, 1, 8)
    batch = ProductionBatch(
        batch_number=f"{order.order_number}-B01",
        production_order_id=order.id,
        machine_id=order.machine_id,
        quantity=quantity,
        started_at=started,
    )
    batch.units = [
        ProductionUnit(
            serial_number=f"{batch.batch_number}-U{seq:04d}",
            sequence_in_batch=seq,
            produced_at=started,
        )
        for seq in range(1, quantity + 1)
    ]
    session.add(batch)
    session.flush()
    return batch


def test_batch_with_units_cannot_be_deleted(db_session: Session) -> None:
    """ON DELETE RESTRICT keeps traceability rows: units block the delete of their batch."""
    batch = _batch_with_units(db_session, _in_progress_order(db_session, "PO-RST"), 2)
    with pytest.raises(IntegrityError):
        db_session.execute(text("DELETE FROM production_batches WHERE id = :id"), {"id": batch.id})
    db_session.rollback()


def test_complete_batch_increments_quantity_atomically(db_session: Session) -> None:
    """A stale in-memory order must not overwrite a completion committed in between."""
    order = _in_progress_order(db_session, "PO-ATM")
    batch = _batch_with_units(db_session, order, 4)
    db_session.commit()
    with engine.begin() as conn:  # a concurrent request completes 2 units for the same order
        conn.execute(
            text(
                "UPDATE production_orders SET quantity_completed = quantity_completed + 2 WHERE id = :id"
            ),
            {"id": order.id},
        )
    assert order.quantity_completed == 0  # this session still holds the value it loaded

    production_service.complete_batch(db_session, batch.id)
    db_session.commit()

    assert order.quantity_completed == 6
    stored = db_session.scalar(
        select(ProductionOrder.quantity_completed).where(ProductionOrder.id == order.id)
    )
    assert stored == 6


def test_completing_a_batch_beyond_the_planned_quantity_is_a_conflict(db_session: Session) -> None:
    """The service refuses before ck_order_completed_within_planned would fire."""
    order = _in_progress_order(db_session, "PO-OVR")
    batch = _batch_with_units(db_session, order, 4)
    db_session.execute(
        text("UPDATE production_orders SET quantity_completed = 7 WHERE id = :id"), {"id": order.id}
    )
    db_session.commit()
    db_session.expire_all()  # a request would load the order fresh; 7 + 4 exceeds 10
    with pytest.raises(ConflictError, match="exceed the order's planned quantity"):
        production_service.complete_batch(db_session, batch.id)
    db_session.rollback()
    stored = db_session.execute(
        text("SELECT status, completed_at FROM production_batches WHERE id = :id"), {"id": batch.id}
    ).one()
    assert tuple(stored) == ("IN_PROGRESS", None)


@pytest.mark.parametrize(
    "statement",
    [
        # BR-01: usernames and emails are unique.
        "INSERT INTO users (username, email, password_hash, role, is_active) VALUES ('engineer', 'x@example.com', 'h', 'VIEWER', 1)",
        "INSERT INTO users (username, email, password_hash, role, is_active) VALUES ('someone', 'engineer@example.com', 'h', 'VIEWER', 1)",
        # BR-10: product, machine, and lot codes are unique.
        "INSERT INTO products (code, name) VALUES ('GEAR', 'again')",
        "INSERT INTO machines (code, name, status) VALUES ('CNC-01', 'again', 'IDLE')",
        "INSERT INTO material_lots (lot_number, material_name, supplier, quantity_received, status, received_at) VALUES ('L201', 'm', 's', 1, 'AVAILABLE', '2026-01-01')",
        # BR-11: one characteristic per product.
        "INSERT INTO product_specifications (product_id, characteristic, target_value, tolerance, unit) SELECT id, 'diameter', 1, 1, 'mm' FROM products WHERE code = 'STEEL-SHAFT'",
        # BR-16: defect type codes are unique.
        "INSERT INTO defect_types (code, name) VALUES ('SURFACE_DAMAGE', 'again')",
    ],
)
def test_reference_unique_constraints_reject_duplicates(
    db_session: Session, statement: str
) -> None:
    with pytest.raises(IntegrityError):
        db_session.execute(text(statement))
    db_session.rollback()


def test_unit_serials_sequences_evidence_and_lot_links_are_unique(db_session: Session) -> None:
    order = _in_progress_order(db_session, "PO-UNQ")
    batch = _batch_with_units(db_session, order, 2)
    lot_id = db_session.scalar(select(MaterialLot.id).where(MaterialLot.lot_number == "L401"))
    db_session.execute(
        text("INSERT INTO batch_materials VALUES (:b, :lot, 1.00)"), {"b": batch.id, "lot": lot_id}
    )
    investigation = Investigation(
        title="Unique", window_start=datetime(2026, 1, 1), window_end=datetime(2026, 1, 2)
    )
    investigation.evidence = [
        InvestigationEvidence(
            sequence=1,
            rule_code="R1",
            title="t",
            narrative="n",
            query_name="q",
            query_sql="SELECT 1",
            result_rows={"columns": [], "rows": []},
        )
    ]
    db_session.add(investigation)
    db_session.commit()
    duplicates = [
        # BR-54: serial numbers and the sequence within a batch are unique.
        f"INSERT INTO production_units (batch_id, serial_number, sequence_in_batch, produced_at) VALUES ({batch.id}, 'PO-UNQ-B01-U0001', 9, '2026-01-01')",
        f"INSERT INTO production_units (batch_id, serial_number, sequence_in_batch, produced_at) VALUES ({batch.id}, 'OTHER', 1, '2026-01-01')",
        # BR-80: one link per batch and lot pair.
        f"INSERT INTO batch_materials VALUES ({batch.id}, {lot_id}, 2.00)",
        # BR-72: evidence sequence is unique per investigation.
        f"INSERT INTO investigation_evidence (investigation_id, sequence, rule_code, title, narrative, query_name, query_sql, result_rows) VALUES ({investigation.id}, 1, 'R2', 't', 'n', 'q', 'SELECT 1', '{{}}')",
    ]
    for statement in duplicates:
        with pytest.raises(IntegrityError):
            db_session.execute(text(statement))
        db_session.rollback()


def test_decimal_precision_is_preserved(db_session: Session) -> None:
    value = db_session.scalar(
        select(func.sum(text("tolerance"))).select_from(text("product_specifications"))
    )
    assert isinstance(value, Decimal)
