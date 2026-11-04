from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Operator
from app.models.enums import InspectionResult
from app.schemas.quality import InspectionCreate, InspectionRead, QualitySummary
from app.services import quality_service

router = APIRouter(tags=["quality"])


@router.get("/inspections", response_model=list[InspectionRead])
def list_inspections(
    session: DbSession,
    _: CurrentUser,
    batch_id: int | None = Query(None, gt=0),
    result: InspectionResult | None = None,
    limit: int = Query(200, ge=1, le=1000),
) -> list[InspectionRead]:
    rows = quality_service.list_inspections(session, batch_id=batch_id, result=result, limit=limit)
    return [quality_service.to_read(i) for i in rows]


@router.post("/inspections", response_model=InspectionRead, status_code=status.HTTP_201_CREATED)
def record_inspection(session: DbSession, _: Operator, body: InspectionCreate) -> InspectionRead:
    inspection = quality_service.record_inspection(session, body)
    return quality_service.to_read(inspection)


@router.get("/quality/summary", response_model=QualitySummary)
def quality_summary(
    session: DbSession,
    _: CurrentUser,
    machine_id: int | None = Query(None, gt=0),
    batch_id: int | None = Query(None, gt=0),
) -> QualitySummary:
    return quality_service.quality_summary(session, machine_id=machine_id, batch_id=batch_id)
