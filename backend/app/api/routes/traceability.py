from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, Engineer
from app.schemas.catalog import MaterialLotRead
from app.schemas.production import ProductionBatchRead, QuarantineRequest
from app.schemas.traceability import (
    BackwardTraceRead,
    BackwardTraceRow,
    ForwardTraceRead,
    ForwardTraceRow,
    LotQuarantineRead,
)
from app.services import catalog_service, traceability_service

router = APIRouter(prefix="/traceability", tags=["traceability"])


@router.get("/forward/{lot_number}", response_model=ForwardTraceRead)
def forward_trace(session: DbSession, _: CurrentUser, lot_number: str) -> ForwardTraceRead:
    rows = traceability_service.forward_trace(session, lot_number)
    return ForwardTraceRead(
        lot_number=lot_number, batches=[ForwardTraceRow.model_validate(r) for r in rows]
    )


@router.get("/backward/{serial_number}", response_model=BackwardTraceRead)
def backward_trace(session: DbSession, _: CurrentUser, serial_number: str) -> BackwardTraceRead:
    rows = traceability_service.backward_trace(session, serial_number)
    return BackwardTraceRead(
        serial_number=serial_number, lineage=[BackwardTraceRow.model_validate(r) for r in rows]
    )


@router.post("/material-lots/{lot_id}/quarantine", response_model=LotQuarantineRead)
def quarantine_lot(
    session: DbSession, _: Engineer, lot_id: int, body: QuarantineRequest
) -> LotQuarantineRead:
    batches = traceability_service.quarantine_lot(session, lot_id, reason=body.reason)
    lot = catalog_service.get_material_lot(session, lot_id)
    return LotQuarantineRead(
        lot=MaterialLotRead.model_validate(lot),
        quarantined_batches=[ProductionBatchRead.model_validate(b) for b in batches],
    )
