"""Import inspections from a CSV upload in one transaction.

Rows are parsed by ``inspection_csv``, resolved against production units,
product specifications, defect types, and existing inspections, and evaluated
in memory with ``domain.quality_rules.evaluate_measurement``, the same rule
``quality_service.record_inspection`` applies to manual entry, so pass/fail
and the automatic defect code cannot drift between the two entry points. Only
when every row is valid are the inspections written, with chunked multi-row
INSERTs the way ``simulation_service.persist`` does; MySQL returns no ids for
those, so the new ids are selected back by (unit, specification). The
caller's session owns the transaction; nothing here commits, so a failure
anywhere leaves no rows behind.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import now
from app.core.database import Base
from app.core.exceptions import ValidationError
from app.core.mysql_errors import MYSQL_DUPLICATE_KEY, mysql_error_code
from app.domain.quality_rules import Evaluation, evaluate_measurement
from app.models import (
    DefectType,
    Inspection,
    InspectionDefect,
    InspectionResult,
    ProductionBatch,
    ProductionOrder,
    ProductionUnit,
    ProductSpecification,
)
from app.schemas.quality import InspectionImportResult
from app.services.inspection_csv import (
    MAX_FILE_BYTES,
    ImportRow,
    RowError,
    file_error,
    import_error,
    parse_csv,
)

logger = logging.getLogger(__name__)

# Browsers on Windows label .csv files as application/vnd.ms-excel; curl and
# some gauge software send application/octet-stream, accepted only with a .csv name.
ACCEPTED_CONTENT_TYPES = frozenset({"text/csv", "application/csv", "application/vnd.ms-excel"})
BULK_CHUNK_SIZE = 1000
INVALID_ROWS_MESSAGE = "The file was not imported because some rows are invalid"
RACE_MESSAGE = "Another import recorded this unit and characteristic first"

Row = dict[str, object]


@dataclass(frozen=True)
class _Lookups:
    """Reference rows the file refers to, loaded with one query per table."""

    units: dict[str, tuple[int, int]]  # upper case serial number -> (unit id, product id)
    specs: dict[tuple[int, str], ProductSpecification]  # (product id, lower characteristic)
    defect_type_ids: dict[str, int]
    inspected_pairs: frozenset[tuple[int, int]]  # (unit id, specification id)


@dataclass(frozen=True)
class _Planned:
    """One valid row, evaluated in memory and ready to insert."""

    row: int
    unit_id: int
    specification_id: int
    measured_value: Decimal
    result: InspectionResult
    inspected_at: datetime
    defect_type_ids: tuple[int, ...]


def import_csv(
    session: Session, content: bytes, *, content_type: str | None, filename: str | None
) -> InspectionImportResult:
    """Validate the whole file, then record every row or nothing."""
    text = decode_upload(content, content_type=content_type, filename=filename)
    rows, errors = parse_csv(text)
    plans, resolve_errors = _resolve_rows(session, rows, default_time=now())
    errors.extend(resolve_errors)
    if errors:
        errors.sort(key=lambda e: (e.row or 0, e.field or ""))
        raise import_error(INVALID_ROWS_MESSAGE, errors)
    inspection_ids = _write_inspections(session, plans)
    failed = sum(1 for plan in plans if plan.result is InspectionResult.FAIL)
    logger.info(
        "inspections imported: %d rows, %d failed",
        len(plans),
        failed,
        extra={"operation": "inspections.import"},
    )
    return InspectionImportResult(
        imported=len(plans), failed_inspections=failed, inspection_ids=inspection_ids
    )


def decode_upload(content: bytes, *, content_type: str | None, filename: str | None) -> str:
    if not _is_csv_upload(content_type, filename):
        raise file_error("Upload a CSV file with content type text/csv")
    if not content:
        raise file_error("The file is empty")
    if len(content) > MAX_FILE_BYTES:
        raise file_error(f"The file is larger than {MAX_FILE_BYTES // 1024} KiB")
    try:
        # utf-8-sig drops the byte order mark that spreadsheet exports prepend.
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise file_error("The file is not valid UTF-8") from exc


def _is_csv_upload(content_type: str | None, filename: str | None) -> bool:
    media_type = (content_type or "").split(";")[0].strip().lower()
    if media_type in ACCEPTED_CONTENT_TYPES:
        return True
    return media_type == "application/octet-stream" and (filename or "").lower().endswith(".csv")


def _resolve_rows(
    session: Session, rows: list[ImportRow], *, default_time: datetime
) -> tuple[list[_Planned], list[RowError]]:
    if not rows:
        return [], []
    lookups = _load_lookups(session, rows)
    plans: list[_Planned] = []
    errors: list[RowError] = []
    for row in rows:
        plan, row_errors = _resolve_row(row, lookups, default_time)
        errors.extend(row_errors)
        if plan is not None:
            plans.append(plan)
    return plans, errors


def _load_lookups(session: Session, rows: list[ImportRow]) -> _Lookups:
    serials = {row.serial_number for row in rows}
    unit_stmt = (
        select(ProductionUnit.id, ProductionUnit.serial_number, ProductionOrder.product_id)
        .join(ProductionUnit.batch)
        .join(ProductionBatch.order)
        .where(ProductionUnit.serial_number.in_(serials))
    )
    units = {
        serial.upper(): (unit_id, product_id)
        for unit_id, serial, product_id in session.execute(unit_stmt).all()
    }
    specs = {
        (spec.product_id, spec.characteristic.lower()): spec
        for spec in session.scalars(select(ProductSpecification))
    }
    defect_type_ids = {
        code: type_id for type_id, code in session.execute(select(DefectType.id, DefectType.code))
    }
    unit_ids = [unit_id for unit_id, _ in units.values()]
    pairs: frozenset[tuple[int, int]] = frozenset()
    if unit_ids:
        pairs = frozenset(_existing_pairs(session, unit_ids))
    return _Lookups(units, specs, defect_type_ids, pairs)


def _existing_pairs(
    session: Session, unit_ids: list[int], *, locking: bool = False
) -> list[tuple[int, int]]:
    """(unit, specification) pairs that already have an inspection.

    A locking read sees rows other transactions committed after this
    transaction's snapshot was taken, which a plain SELECT under REPEATABLE
    READ does not.
    """
    stmt = select(Inspection.unit_id, Inspection.specification_id).where(
        Inspection.unit_id.in_(unit_ids)
    )
    if locking:
        stmt = stmt.with_for_update(read=True)
    return [(unit_id, spec_id) for unit_id, spec_id in session.execute(stmt).all()]


def _resolve_row(
    row: ImportRow, lookups: _Lookups, default_time: datetime
) -> tuple[_Planned | None, list[RowError]]:
    unit = lookups.units.get(row.serial_number)
    if unit is None:
        message = "No production unit has this serial number"
        return None, [RowError(row.row, "serial_number", message)]
    unit_id, product_id = unit
    spec = lookups.specs.get((product_id, row.characteristic.lower()))
    if spec is None:
        message = "The unit's product has no specification with this characteristic"
        return None, [RowError(row.row, "characteristic", message)]
    evaluation = evaluate_measurement(
        measured=row.measured_value,
        target=spec.target_value,
        tolerance=spec.tolerance,
        characteristic=spec.characteristic,
    )
    codes = _defect_codes(row, evaluation)
    errors = _rule_errors(row, unit_id, spec.id, codes, evaluation, lookups)
    if errors:
        return None, errors
    plan = _Planned(
        row=row.row,
        unit_id=unit_id,
        specification_id=spec.id,
        measured_value=row.measured_value,
        result=evaluation.result,
        inspected_at=row.inspected_at or default_time,
        defect_type_ids=tuple(lookups.defect_type_ids[code] for code in codes),
    )
    return plan, []


def _defect_codes(row: ImportRow, evaluation: Evaluation) -> list[str]:
    """Explicit codes plus the one the rule derives on failure, as ``record_inspection`` does."""
    codes = set(row.defect_type_codes)
    if evaluation.result is InspectionResult.FAIL and evaluation.defect_code:
        codes.add(evaluation.defect_code)
    return sorted(codes)


def _rule_errors(
    row: ImportRow,
    unit_id: int,
    specification_id: int,
    codes: list[str],
    evaluation: Evaluation,
    lookups: _Lookups,
) -> list[RowError]:
    """Mirror the checks ``record_inspection`` applies, with the row attached."""
    errors: list[RowError] = []
    if (unit_id, specification_id) in lookups.inspected_pairs:
        message = "This unit already has an inspection for this characteristic"
        errors.append(RowError(row.row, None, message))
    unknown = [code for code in codes if code not in lookups.defect_type_ids]
    if unknown:
        errors.append(
            RowError(row.row, "defect_type_codes", f"Unknown defect codes: {', '.join(unknown)}")
        )
    if row.defect_type_codes and evaluation.result is InspectionResult.PASS:
        message = "Defect codes cannot be attached to a passing measurement"
        errors.append(RowError(row.row, "defect_type_codes", message))
    return errors


def _write_inspections(session: Session, plans: list[_Planned]) -> list[int]:
    """Bulk insert the planned rows; returns the new inspection ids in file order.

    The inserts run inside a savepoint so that, when another transaction
    recorded one of the pairs between validation and write, the partial chunk
    is undone before the conflicting rows are looked up and reported as 422.
    Every other integrity error is re-raised for the generic handler.
    """
    if not plans:
        return []
    try:
        with session.begin_nested():
            return _insert_plans(session, plans)
    except IntegrityError as exc:
        if mysql_error_code(exc) != MYSQL_DUPLICATE_KEY:
            raise
        race = _race_error(session, plans)
        if race is None:
            raise
        raise race from exc


def _insert_plans(session: Session, plans: list[_Planned]) -> list[int]:
    _bulk_insert(session, Inspection, [_inspection_row(plan) for plan in plans])
    unit_ids = sorted({plan.unit_id for plan in plans})
    stmt = select(Inspection.unit_id, Inspection.specification_id, Inspection.id).where(
        Inspection.unit_id.in_(unit_ids)
    )
    ids = {(unit_id, spec_id): insp_id for unit_id, spec_id, insp_id in session.execute(stmt)}
    defect_rows: list[Row] = [
        {"inspection_id": ids[(plan.unit_id, plan.specification_id)], "defect_type_id": type_id}
        for plan in plans
        for type_id in plan.defect_type_ids
    ]
    _bulk_insert(session, InspectionDefect, defect_rows)
    return [ids[(plan.unit_id, plan.specification_id)] for plan in plans]


def _inspection_row(plan: _Planned) -> Row:
    return {
        "unit_id": plan.unit_id,
        "specification_id": plan.specification_id,
        "measured_value": plan.measured_value,
        "result": plan.result,
        "inspected_at": plan.inspected_at,
    }


def _bulk_insert(session: Session, model: type[Base], rows: list[Row]) -> None:
    """Multi-row INSERTs in chunks, inside the session's current transaction."""
    for start in range(0, len(rows), BULK_CHUNK_SIZE):
        session.execute(insert(model), rows[start : start + BULK_CHUNK_SIZE])


def _race_error(session: Session, plans: list[_Planned]) -> ValidationError | None:
    """Name the rows another transaction recorded first, or None if the duplicate is unexplained."""
    taken = set(_existing_pairs(session, sorted({p.unit_id for p in plans}), locking=True))
    errors = [
        RowError(plan.row, None, RACE_MESSAGE)
        for plan in plans
        if (plan.unit_id, plan.specification_id) in taken
    ]
    if not errors:
        return None
    return import_error(INVALID_ROWS_MESSAGE, errors)
