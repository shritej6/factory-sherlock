from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Operator, Paging
from app.models.enums import InspectionResult
from app.schemas.common import Page
from app.schemas.quality import InspectionCreate, InspectionRead, QualitySummary
from app.services import quality_service

router = APIRouter(tags=["quality"])


@router.get("/inspections", response_model=Page[InspectionRead])
def list_inspections(
    session: DbSession,
    _: CurrentUser,
    paging: Paging,
    batch_id: int | None = Query(None, gt=0),
    result: InspectionResult | None = None,
) -> Page[InspectionRead]:
    page = quality_service.list_inspections(session, paging, batch_id=batch_id, result=result)
    return Page[InspectionRead].from_result(page, paging, quality_service.to_read)


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
