from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from app.api.deps import CurrentUser, DbSession, Operator, Paging
from app.models.enums import InspectionResult
from app.schemas.common import Page
from app.schemas.quality import (
    InspectionCreate,
    InspectionImportResult,
    InspectionRead,
    QualitySummary,
)
from app.services import inspection_import, quality_service
from app.services.inspection_csv import MAX_FILE_BYTES

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


@router.post(
    "/inspections/import",
    response_model=InspectionImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="Import inspections from a CSV file",
    description=(
        "Multipart upload with one field named `file`: UTF-8 CSV, header row, columns "
        "`serial_number`, `characteristic`, `measured_value`, optional `inspected_at` and "
        "`defect_type_codes` (separated by `|`). At most 1 MiB and 5000 data rows. Every row "
        "is validated first; one invalid row rejects the whole file with 422 and no inspection "
        "is written."
    ),
)
def import_inspections(
    session: DbSession, _: Operator, file: Annotated[UploadFile, File()]
) -> InspectionImportResult:
    # Read one byte past the limit so the size check cannot be fooled by a larger body.
    content = file.file.read(MAX_FILE_BYTES + 1)
    return inspection_import.import_csv(
        session, content, content_type=file.content_type, filename=file.filename
    )


@router.get("/quality/summary", response_model=QualitySummary)
def quality_summary(
    session: DbSession,
    _: CurrentUser,
    machine_id: int | None = Query(None, gt=0),
    batch_id: int | None = Query(None, gt=0),
) -> QualitySummary:
    return quality_service.quality_summary(session, machine_id=machine_id, batch_id=batch_id)
