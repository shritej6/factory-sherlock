"""Every ON DELETE behaviour declared in the schema migration, exercised with raw SQL.

The deletes run as plain statements so the test observes MySQL, not the ORM
cascade configuration. RESTRICT paths must raise IntegrityError, CASCADE paths
must remove the owned rows, SET NULL paths must clear the column.
"""

from datetime import datetime
from decimal import Decimal

import pytest
from app.core.database import SessionLocal
from app.models import (
    Alert,
    AlertType,
    DefectType,
    Inspection,
    InspectionDefect,
    InspectionResult,
    Investigation,
    InvestigationBatch,
    InvestigationEvidence,
    Machine,
    MaterialLot,
    MaterialLotStatus,
    OrderStatus,
    Product,
    ProductionBatch,
    ProductionOrder,
    ProductionUnit,
    ProductSpecification,
    Severity,
    User,
    UserRole,
)
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

AT = datetime(2026, 1, 1, 8)


def _delete(session: Session, table: str, row_id: int) -> None:
    session.execute(text(f"DELETE FROM {table} WHERE id = :id"), {"id": row_id})


def _assert_restricted(session: Session, table: str, row_id: int) -> None:
    session.commit()
    with pytest.raises(IntegrityError):
        _delete(session, table, row_id)
    session.rollback()
    with SessionLocal() as fresh:
        count = fresh.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE id = :id"), {"id": row_id}
        ).scalar()
        assert count == 1


def _rows_for_investigation(session: Session, investigation_id: int) -> tuple[int, int]:
    evidence = session.scalar(
        select(func.count(InvestigationEvidence.id)).where(
            InvestigationEvidence.investigation_id == investigation_id
        )
    )
    links = session.scalar(
        select(func.count(InvestigationBatch.batch_id)).where(
            InvestigationBatch.investigation_id == investigation_id
        )
    )
    return int(evidence or 0), int(links or 0)


def _order_with_batch(session: Session, number: str) -> tuple[ProductionOrder, ProductionBatch]:
    order = ProductionOrder(
        order_number=number,
        product_id=session.scalar(select(Product.id).where(Product.code == "STEEL-SHAFT")),
        machine_id=session.scalar(select(Machine.id).where(Machine.code == "CNC-02")),
        quantity_planned=3,
        status=OrderStatus.IN_PROGRESS,
    )
    session.add(order)
    session.flush()
    batch = ProductionBatch(
        batch_number=f"{number}-B01",
        production_order_id=order.id,
        machine_id=order.machine_id,
        quantity=3,
        started_at=AT,
    )
    batch.units = [
        ProductionUnit(
            serial_number=f"{number}-B01-U{seq:04d}", sequence_in_batch=seq, produced_at=AT
        )
        for seq in range(1, 4)
    ]
    session.add(batch)
    session.flush()
    return order, batch


def _inspection(session: Session, unit: ProductionUnit, *, with_defect: bool) -> Inspection:
    spec_id = session.scalar(
        select(ProductSpecification.id).where(ProductSpecification.characteristic == "diameter")
    )
    inspection = Inspection(
        unit_id=unit.id,
        specification_id=spec_id,
        measured_value=Decimal("20.300"),
        result=InspectionResult.FAIL,
        inspected_at=AT,
    )
    if with_defect:
        defect = session.scalar(select(DefectType).where(DefectType.code == "OVERSIZE_DIAMETER"))
        inspection.defect_links = [InspectionDefect(defect_type=defect)]
    session.add(inspection)
    session.flush()
    return inspection


# RESTRICT paths


def test_an_inspection_cannot_reference_a_missing_specification(db_session: Session) -> None:
    _, batch = _order_with_batch(db_session, "PO-FK-SPEC")
    db_session.add(
        Inspection(
            unit_id=batch.units[0].id,
            specification_id=999999,
            measured_value=Decimal("20.000"),
            result=InspectionResult.PASS,
            inspected_at=AT,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_a_product_with_orders_cannot_be_deleted(db_session: Session) -> None:
    order, _ = _order_with_batch(db_session, "PO-FK-PROD")
    _assert_restricted(db_session, "products", order.product_id)


def test_a_material_lot_used_by_a_batch_cannot_be_deleted(db_session: Session) -> None:
    _, batch = _order_with_batch(db_session, "PO-FK-LOT")
    lot_id = db_session.scalar(select(MaterialLot.id).where(MaterialLot.lot_number == "L201"))
    db_session.execute(
        text("INSERT INTO batch_materials VALUES (:batch_id, :lot_id, 3.00)"),
        {"batch_id": batch.id, "lot_id": lot_id},
    )
    assert lot_id is not None
    _assert_restricted(db_session, "material_lots", lot_id)


def test_a_machine_with_batches_cannot_be_deleted(db_session: Session) -> None:
    _, batch = _order_with_batch(db_session, "PO-FK-MACH")
    _assert_restricted(db_session, "machines", batch.machine_id)


def test_an_order_with_batches_cannot_be_deleted(db_session: Session) -> None:
    order, _ = _order_with_batch(db_session, "PO-FK-ORD")
    _assert_restricted(db_session, "production_orders", order.id)


def test_a_batch_with_material_links_or_investigation_links_cannot_be_deleted(
    db_session: Session,
) -> None:
    """Units, material links, and investigation links all RESTRICT the batch delete."""
    _, batch = _order_with_batch(db_session, "PO-FK-BATCH")
    _assert_restricted(db_session, "production_batches", batch.id)  # units
    db_session.execute(text("DELETE FROM production_units WHERE batch_id = :b"), {"b": batch.id})
    lot_id = db_session.scalar(select(MaterialLot.id).where(MaterialLot.lot_number == "L202"))
    db_session.execute(
        text("INSERT INTO batch_materials VALUES (:batch_id, :lot_id, 3.00)"),
        {"batch_id": batch.id, "lot_id": lot_id},
    )
    _assert_restricted(db_session, "production_batches", batch.id)  # material links
    db_session.execute(text("DELETE FROM batch_materials WHERE batch_id = :b"), {"b": batch.id})
    investigation = Investigation(title="Link", window_start=AT, window_end=datetime(2026, 1, 2))
    investigation.batch_links = [InvestigationBatch(batch_id=batch.id, reason="review")]
    db_session.add(investigation)
    _assert_restricted(db_session, "production_batches", batch.id)  # investigation links


def test_a_defect_type_in_use_and_an_inspected_unit_cannot_be_deleted(db_session: Session) -> None:
    _, batch = _order_with_batch(db_session, "PO-FK-DEF")
    inspection = _inspection(db_session, batch.units[0], with_defect=True)
    _assert_restricted(db_session, "defect_types", inspection.defect_links[0].defect_type_id)
    _assert_restricted(db_session, "production_units", inspection.unit_id)


# CASCADE paths


def test_deleting_a_product_without_orders_removes_its_specifications(db_session: Session) -> None:
    product = Product(code="SCRATCH", name="Scratch product")
    product.specifications = [
        ProductSpecification(
            characteristic="width", target_value=Decimal("5"), tolerance=Decimal("0.1")
        )
    ]
    db_session.add(product)
    db_session.commit()
    spec_id = product.specifications[0].id
    _delete(db_session, "products", product.id)
    db_session.commit()
    remaining = select(ProductSpecification.id).where(ProductSpecification.id == spec_id)
    assert db_session.scalar(remaining) is None


def test_deleting_an_inspection_removes_its_defect_links(db_session: Session) -> None:
    _, batch = _order_with_batch(db_session, "PO-FK-INSP")
    inspection = _inspection(db_session, batch.units[0], with_defect=True)
    defect_type_id = inspection.defect_links[0].defect_type_id
    db_session.commit()
    links = (
        select(func.count())
        .select_from(InspectionDefect)
        .where(InspectionDefect.inspection_id == inspection.id)
    )
    assert db_session.scalar(links) == 1
    _delete(db_session, "inspections", inspection.id)
    db_session.commit()
    assert db_session.scalar(links) == 0
    assert db_session.get(DefectType, defect_type_id) is not None  # the defect type survives


def test_deleting_an_investigation_removes_evidence_and_batch_links(db_session: Session) -> None:
    _, batch = _order_with_batch(db_session, "PO-FK-INV")
    investigation = Investigation(title="Cascade", window_start=AT, window_end=datetime(2026, 1, 2))
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
    investigation.batch_links = [InvestigationBatch(batch_id=batch.id, reason="review")]
    db_session.add(investigation)
    db_session.commit()
    assert _rows_for_investigation(db_session, investigation.id) == (1, 1)
    _delete(db_session, "investigations", investigation.id)
    db_session.commit()
    assert _rows_for_investigation(db_session, investigation.id) == (0, 0)
    assert db_session.get(ProductionBatch, batch.id) is not None  # the batch is not touched


# SET NULL paths


def _scratch_machine(session: Session) -> Machine:
    machine = Machine(code="SCRATCH-01", name="Scratch machine")
    session.add(machine)
    session.flush()
    return machine


def test_deleting_a_machine_clears_it_on_alerts_investigations_and_orders(
    db_session: Session,
) -> None:
    machine = _scratch_machine(db_session)
    alert = Alert(
        machine_id=machine.id,
        alert_type=AlertType.MACHINE_FAULT,
        severity=Severity.CRITICAL,
        message="scratch",
    )
    investigation = Investigation(
        title="Scratch", machine_id=machine.id, window_start=AT, window_end=datetime(2026, 1, 2)
    )
    order = ProductionOrder(
        order_number="PO-FK-NULL",
        product_id=db_session.scalar(select(Product.id).where(Product.code == "GEAR")),
        machine_id=machine.id,
        quantity_planned=1,
    )
    db_session.add_all([alert, investigation, order])
    db_session.commit()
    _delete(db_session, "machines", machine.id)
    db_session.commit()
    db_session.expire_all()
    assert alert.machine_id is None
    assert investigation.machine_id is None
    assert order.machine_id is None


def test_deleting_a_user_clears_acknowledgements_and_openers(db_session: Session) -> None:
    user = User(
        username="scratch", email="scratch@example.com", password_hash="x", role=UserRole.OPERATOR
    )
    db_session.add(user)
    db_session.flush()
    alert = Alert(
        alert_type=AlertType.MATERIAL_QUARANTINE,
        severity=Severity.WARNING,
        message="scratch",
        acknowledged_at=AT,
        acknowledged_by=user.id,
    )
    investigation = Investigation(
        title="Opened", opened_by=user.id, window_start=AT, window_end=datetime(2026, 1, 2)
    )
    db_session.add_all([alert, investigation])
    db_session.commit()
    _delete(db_session, "users", user.id)
    db_session.commit()
    db_session.expire_all()
    assert alert.acknowledged_by is None
    assert alert.acknowledged_at == AT  # only the reference is cleared
    assert investigation.opened_by is None


def test_deleting_a_product_clears_the_investigation_label(db_session: Session) -> None:
    product = Product(code="SCRATCH-P", name="Scratch")
    db_session.add(product)
    db_session.flush()
    investigation = Investigation(
        title="Labelled", product_id=product.id, window_start=AT, window_end=datetime(2026, 1, 2)
    )
    db_session.add(investigation)
    db_session.commit()
    _delete(db_session, "products", product.id)
    db_session.commit()
    db_session.expire_all()
    assert investigation.product_id is None


def test_an_unused_material_lot_can_be_deleted(db_session: Session) -> None:
    lot = MaterialLot(
        lot_number="L999",
        material_name="Scratch",
        supplier="Scratch",
        quantity_received=Decimal("1.00"),
        status=MaterialLotStatus.AVAILABLE,
        received_at=AT,
    )
    db_session.add(lot)
    db_session.commit()
    _delete(db_session, "material_lots", lot.id)
    db_session.commit()
    assert db_session.scalar(select(MaterialLot.id).where(MaterialLot.id == lot.id)) is None
