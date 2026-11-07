"""Inspections and quality metrics."""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.clock import now
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.quality_rules import defect_rate, evaluate_measurement
from app.models import (
    DefectType,
    Inspection,
    InspectionDefect,
    InspectionResult,
    ProductionBatch,
    ProductionUnit,
    ProductSpecification,
)
from app.repositories.pagination import PageParams, PageResult, paginate
from app.schemas.quality import InspectionCreate, InspectionRead, QualitySummary
from app.services.catalog_service import _flush_or_conflict


def record_inspection(session: Session, data: InspectionCreate) -> Inspection:
    """Record a manual measurement; pass/fail is decided by the specification."""
    unit = session.get(ProductionUnit, data.unit_id)
    if unit is None:
        raise NotFoundError(f"Production unit {data.unit_id} not found")
    spec = session.get(ProductSpecification, data.specification_id)
    if spec is None:
        raise NotFoundError(f"Specification {data.specification_id} not found")
    if spec.product_id != unit.batch.order.product_id:
        raise ValidationError("Specification does not belong to the unit's product")

    evaluation = evaluate_measurement(
        measured=data.measured_value,
        target=spec.target_value,
        tolerance=spec.tolerance,
        characteristic=spec.characteristic,
    )
    codes = set(data.defect_type_codes)
    if evaluation.result is InspectionResult.FAIL and evaluation.defect_code:
        codes.add(evaluation.defect_code)
    if evaluation.result is InspectionResult.PASS and codes:
        raise ValidationError("Defect codes cannot be attached to a passing inspection")

    inspection = Inspection(
        unit_id=unit.id,
        specification_id=spec.id,
        measured_value=data.measured_value,
        result=evaluation.result,
        inspected_at=data.inspected_at or now(),
    )
    if codes:
        found = {
            d.code: d for d in session.scalars(select(DefectType).where(DefectType.code.in_(codes)))
        }
        missing = codes - found.keys()
        if missing:
            raise ValidationError(f"Unknown defect codes: {sorted(missing)}")
        inspection.defect_links = [InspectionDefect(defect_type=found[c]) for c in sorted(codes)]
    session.add(inspection)
    _flush_or_conflict(session, "Inspection for this unit and specification")
    return inspection


def to_read(inspection: Inspection) -> InspectionRead:
    return InspectionRead(
        id=inspection.id,
        unit_id=inspection.unit_id,
        specification_id=inspection.specification_id,
        measured_value=inspection.measured_value,
        result=inspection.result,
        inspected_at=inspection.inspected_at,
        defect_codes=sorted(link.defect_type.code for link in inspection.defect_links),
    )


def list_inspections(
    session: Session,
    paging: PageParams,
    *,
    batch_id: int | None = None,
    result: InspectionResult | None = None,
) -> PageResult[Inspection]:
    stmt = (
        select(Inspection)
        .options(selectinload(Inspection.defect_links).selectinload(InspectionDefect.defect_type))
        .order_by(Inspection.inspected_at.desc(), Inspection.id.desc())
    )
    if batch_id is not None:
        stmt = stmt.join(ProductionUnit).where(ProductionUnit.batch_id == batch_id)
    if result is not None:
        stmt = stmt.where(Inspection.result == result)
    return paginate(session, stmt, paging)


def quality_summary(
    session: Session, *, machine_id: int | None = None, batch_id: int | None = None
) -> QualitySummary:
    units_stmt = select(func.count(ProductionUnit.id)).join(ProductionBatch)
    insp_stmt = (
        select(
            func.count(Inspection.id),
            func.coalesce(
                func.sum(case((Inspection.result == InspectionResult.FAIL, 1), else_=0)), 0
            ),
        )
        .join(ProductionUnit)
        .join(ProductionBatch)
    )
    if machine_id is not None:
        units_stmt = units_stmt.where(ProductionBatch.machine_id == machine_id)
        insp_stmt = insp_stmt.where(ProductionBatch.machine_id == machine_id)
    if batch_id is not None:
        units_stmt = units_stmt.where(ProductionBatch.id == batch_id)
        insp_stmt = insp_stmt.where(ProductionBatch.id == batch_id)
    produced = session.scalar(units_stmt) or 0
    inspected, failed = session.execute(insp_stmt).one()
    inspected, failed = int(inspected or 0), int(failed or 0)
    return QualitySummary(
        total_produced=produced,
        total_inspected=inspected,
        passed=inspected - failed,
        failed=failed,
        defect_rate=defect_rate(failed, inspected),
    )
