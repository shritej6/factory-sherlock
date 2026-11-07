"""Creates investigations by running the engine and persisting its evidence."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.clock import now
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.state_machines import INVESTIGATION_TRANSITIONS, assert_transition
from app.investigation.engine import investigate
from app.investigation.rules import InvestigationContext
from app.models import (
    Investigation,
    InvestigationBatch,
    InvestigationEvidence,
    InvestigationStatus,
)
from app.repositories.pagination import PageParams, PageResult, paginate
from app.repositories.query_runner import SqlQueryRunner
from app.schemas.investigation import InvestigationCreate
from app.services import catalog_service

_LOAD = (
    selectinload(Investigation.evidence),
    selectinload(Investigation.batch_links),
)


def list_investigations(session: Session, paging: PageParams) -> PageResult[Investigation]:
    stmt = (
        select(Investigation)
        .options(*_LOAD)
        .order_by(Investigation.created_at.desc(), Investigation.id.desc())
    )
    return paginate(session, stmt, paging)


def get_investigation(session: Session, investigation_id: int) -> Investigation:
    inv = session.get(Investigation, investigation_id, options=list(_LOAD))
    if inv is None:
        raise NotFoundError(f"Investigation {investigation_id} not found")
    return inv


def open_investigation(
    session: Session, data: InvestigationCreate, *, user_id: int | None
) -> Investigation:
    """Run the rules and store the investigation, evidence, and batch links together."""
    machine_code = None
    if data.machine_id is not None:
        machine_code = catalog_service.get_machine(session, data.machine_id).code
    if data.product_id is not None:
        catalog_service.get_product(session, data.product_id)

    ctx = InvestigationContext(
        machine_id=data.machine_id,
        machine_code=machine_code,
        window_start=data.window_start,
        window_end=data.window_end,
    )
    report = investigate(ctx, SqlQueryRunner(session))

    investigation = Investigation(
        title=data.title,
        machine_id=data.machine_id,
        product_id=data.product_id,
        window_start=data.window_start,
        window_end=data.window_end,
        summary=report.summary,
        opened_by=user_id,
        created_at=now(),
    )
    investigation.evidence = [
        InvestigationEvidence(
            sequence=index,
            rule_code=card.rule_code,
            title=card.title,
            narrative=card.narrative,
            query_name=card.query_name,
            query_sql=card.query_sql,
            result_rows=evidence_payload(card.rows),
        )
        for index, card in enumerate(report.evidence, start=1)
    ]
    investigation.batch_links = [
        InvestigationBatch(batch_id=batch_id, reason="Defect rate above review threshold")
        for batch_id in report.affected_batch_ids
    ]
    session.add(investigation)
    session.flush()
    return get_investigation(session, investigation.id)


def evidence_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Store rows as a column list plus value arrays.

    MySQL normalises JSON object keys into its own order, which would scramble
    the column order of stored evidence; JSON arrays keep their order.
    """
    columns = list(rows[0].keys()) if rows else []
    return {"columns": columns, "rows": [[row[c] for c in columns] for row in rows]}


def change_status(
    session: Session,
    investigation_id: int,
    *,
    target: InvestigationStatus,
    conclusion: str | None,
) -> Investigation:
    inv = get_investigation(session, investigation_id)
    assert_transition(INVESTIGATION_TRANSITIONS, inv.status, target, entity="Investigation")
    if target is InvestigationStatus.CLOSED:
        if not conclusion:
            raise ValidationError("A conclusion is required to close an investigation")
        inv.conclusion = conclusion
        inv.closed_at = now()
    elif conclusion:
        inv.conclusion = conclusion
    inv.status = target
    session.flush()
    return inv
