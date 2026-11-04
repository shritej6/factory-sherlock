"""Forward and backward traceability plus quarantine decisions."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now
from app.core.exceptions import NotFoundError
from app.domain.state_machines import BATCH_TRANSITIONS, assert_transition
from app.models import (
    Alert,
    AlertType,
    BatchMaterial,
    BatchStatus,
    MaterialLot,
    MaterialLotStatus,
    ProductionBatch,
    Severity,
)
from app.repositories.query_runner import SqlQueryRunner
from app.services import catalog_service, production_service


def forward_trace(session: Session, lot_number: str) -> list[dict[str, Any]]:
    lot = session.scalar(select(MaterialLot).where(MaterialLot.lot_number == lot_number))
    if lot is None:
        raise NotFoundError(f"Material lot {lot_number} not found")
    return SqlQueryRunner(session).run("material_lot_forward_trace", {"lot_number": lot_number})


def backward_trace(session: Session, serial_number: str) -> list[dict[str, Any]]:
    rows = SqlQueryRunner(session).run("unit_backward_trace", {"serial_number": serial_number})
    if not rows:
        raise NotFoundError(f"Unit {serial_number} not found")
    return rows


def quarantine_batch(session: Session, batch_id: int, *, reason: str) -> ProductionBatch:
    batch = production_service.get_batch(session, batch_id)
    if batch.status is BatchStatus.QUARANTINED:
        # Repeating a quarantine is not an error; the first reason stands.
        return batch
    assert_transition(
        BATCH_TRANSITIONS,
        batch.status,
        BatchStatus.QUARANTINED,
        entity=f"Batch {batch.batch_number}",
    )
    batch.status = BatchStatus.QUARANTINED
    batch.quarantine_reason = reason
    session.add(
        Alert(
            machine_id=batch.machine_id,
            alert_type=AlertType.MATERIAL_QUARANTINE,
            severity=Severity.WARNING,
            message=f"Batch {batch.batch_number} quarantined: {reason}"[:255],
            created_at=now(),
        )
    )
    session.flush()
    return batch


def quarantine_lot(session: Session, lot_id: int, *, reason: str) -> list[ProductionBatch]:
    """Quarantine a material lot and every batch that consumed it.

    All rows change in one transaction, so a database error rolls back the
    lot's status change as well. Repeating the call is safe: batches that are
    already quarantined are left alone, and no second alert is raised when
    nothing new was quarantined. Returns the batches that were newly
    quarantined.
    """
    lot = catalog_service.get_material_lot(session, lot_id)
    already_quarantined = lot.status is MaterialLotStatus.QUARANTINED
    lot.status = MaterialLotStatus.QUARANTINED
    batches = session.scalars(
        select(ProductionBatch)
        .join(BatchMaterial, BatchMaterial.batch_id == ProductionBatch.id)
        .where(BatchMaterial.material_lot_id == lot.id)
        .where(ProductionBatch.status != BatchStatus.QUARANTINED)
    ).all()
    affected: list[ProductionBatch] = []
    for batch in batches:
        batch.status = BatchStatus.QUARANTINED
        batch.quarantine_reason = f"Material lot {lot.lot_number}: {reason}"[:255]
        affected.append(batch)
    if affected or not already_quarantined:
        session.add(
            Alert(
                machine_id=None,
                alert_type=AlertType.MATERIAL_QUARANTINE,
                severity=Severity.CRITICAL,
                message=f"Lot {lot.lot_number} quarantined ({len(affected)} batches): {reason}"[
                    :255
                ],
                created_at=now(),
            )
        )
    session.flush()
    return affected
