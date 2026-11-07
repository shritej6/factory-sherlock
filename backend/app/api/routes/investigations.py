from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Engineer, Paging
from app.models.enums import InvestigationStatus
from app.schemas.common import Page
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationRead,
    InvestigationStatusChange,
)
from app.services import investigation_service

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.get("", response_model=Page[InvestigationRead])
def list_investigations(
    session: DbSession,
    _: CurrentUser,
    paging: Paging,
    status_filter: list[InvestigationStatus] | None = Query(None, alias="status"),
) -> Page[InvestigationRead]:
    result = investigation_service.list_investigations(session, paging, statuses=status_filter)
    return Page[InvestigationRead].from_result(result, paging, InvestigationRead.model_validate)


@router.post("", response_model=InvestigationRead, status_code=status.HTTP_201_CREATED)
def open_investigation(
    session: DbSession, user: Engineer, body: InvestigationCreate
) -> InvestigationRead:
    inv = investigation_service.open_investigation(session, body, user_id=user.id)
    return InvestigationRead.model_validate(inv)


@router.get("/{investigation_id}", response_model=InvestigationRead)
def get_investigation(
    session: DbSession, _: CurrentUser, investigation_id: int
) -> InvestigationRead:
    return InvestigationRead.model_validate(
        investigation_service.get_investigation(session, investigation_id)
    )


@router.post("/{investigation_id}/status", response_model=InvestigationRead)
def change_status(
    session: DbSession, _: Engineer, investigation_id: int, body: InvestigationStatusChange
) -> InvestigationRead:
    inv = investigation_service.change_status(
        session, investigation_id, target=body.status, conclusion=body.conclusion
    )
    return InvestigationRead.model_validate(inv)
