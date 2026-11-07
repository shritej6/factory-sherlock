"""Import inspections from a CSV upload in one transaction.

Rows are parsed by ``inspection_csv``, resolved against production units,
product specifications, defect types, and existing inspections, and only when
every row is valid are they recorded through
``quality_service.record_inspection``. Routing each row through the same
function as manual entry keeps the pass/fail rule and the defect
classification identical for both entry points. The caller's session owns the
transaction; nothing here commits, so a failure anywhere leaves no rows behind.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import now
from app.domain.quality_rules import evaluate_measurement
from app.models import (
    DefectType,
    Inspection,
    InspectionResult,
    ProductionBatch,
    ProductionOrder,
    ProductionUnit,
    ProductSpecification,
)
from app.schemas.quality import InspectionCreate, InspectionImportResult
from app.services.inspection_csv import (
    MAX_FILE_BYTES,
    ImportRow,
    RowError,
    file_error,
    import_error,
    parse_csv,
)
from app.services.quality_service import record_inspection

logger = logging.getLogger(__name__)

# Browsers on Windows label .csv files as application/vnd.ms-excel; curl and
# some gauge software send application/octet-stream, accepted only with a .csv name.
ACCEPTED_CONTENT_TYPES = frozenset({"text/csv", "application/csv", "application/vnd.ms-excel"})


@dataclass(frozen=True)
class _Lookups:
    """Reference rows the file refers to, loaded with one query per table."""

    units: dict[str, tuple[int, int]]  # serial number -> (unit id, product id)
    specs: dict[tuple[int, str], ProductSpecification]  # (product id, lower characteristic)
    defect_codes: frozenset[str]
    inspected_pairs: frozenset[tuple[int, int]]  # (unit id, specification id)


def import_csv(
    session: Session, content: bytes, *, content_type: str | None, filename: str | None
) -> InspectionImportResult:
    """Validate the whole file, then record every row or nothing."""
    text = decode_upload(content, content_type=content_type, filename=filename)
    rows, errors = parse_csv(text)
    creates, resolve_errors = _resolve_rows(session, rows, default_time=now())
    errors.extend(resolve_errors)
    if errors:
        errors.sort(key=lambda e: (e.row or 0, e.field or ""))
        raise import_error("The file was not imported because some rows are invalid", errors)
    inspections = [record_inspection(session, create) for create in creates]
    failed = sum(1 for i in inspections if i.result is InspectionResult.FAIL)
    logger.info(
        "inspections imported: %d rows, %d failed",
        len(inspections),
        failed,
        extra={"operation": "inspections.import"},
    )
    return InspectionImportResult(
        imported=len(inspections),
        failed_inspections=failed,
        inspection_ids=[i.id for i in inspections],
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
) -> tuple[list[InspectionCreate], list[RowError]]:
    if not rows:
        return [], []
    lookups = _load_lookups(session, rows)
    creates: list[InspectionCreate] = []
    errors: list[RowError] = []
    for row in rows:
        create, row_errors = _resolve_row(row, lookups, default_time)
        errors.extend(row_errors)
        if create is not None:
            creates.append(create)
    return creates, errors


def _load_lookups(session: Session, rows: list[ImportRow]) -> _Lookups:
    serials = {row.serial_number for row in rows}
    unit_stmt = (
        select(ProductionUnit.id, ProductionUnit.serial_number, ProductionOrder.product_id)
        .join(ProductionUnit.batch)
        .join(ProductionBatch.order)
        .where(ProductionUnit.serial_number.in_(serials))
    )
    units = {
        serial: (unit_id, product_id)
        for unit_id, serial, product_id in session.execute(unit_stmt).all()
    }
    specs = {
        (spec.product_id, spec.characteristic.lower()): spec
        for spec in session.scalars(select(ProductSpecification))
    }
    codes = frozenset(session.scalars(select(DefectType.code)))
    unit_ids = [unit_id for unit_id, _ in units.values()]
    pair_stmt = select(Inspection.unit_id, Inspection.specification_id).where(
        Inspection.unit_id.in_(unit_ids)
    )
    pairs: frozenset[tuple[int, int]] = frozenset()
    if unit_ids:
        pairs = frozenset((u, s) for u, s in session.execute(pair_stmt).all())
    return _Lookups(units=units, specs=specs, defect_codes=codes, inspected_pairs=pairs)


def _resolve_row(
    row: ImportRow, lookups: _Lookups, default_time: datetime
) -> tuple[InspectionCreate | None, list[RowError]]:
    unit = lookups.units.get(row.serial_number)
    if unit is None:
        message = "No production unit has this serial number"
        return None, [RowError(row.row, "serial_number", message)]
    unit_id, product_id = unit
    spec = lookups.specs.get((product_id, row.characteristic.lower()))
    if spec is None:
        message = "The unit's product has no specification with this characteristic"
        return None, [RowError(row.row, "characteristic", message)]
    errors = _rule_errors(row, unit_id, spec, lookups)
    if errors:
        return None, errors
    create = InspectionCreate(
        unit_id=unit_id,
        specification_id=spec.id,
        measured_value=row.measured_value,
        inspected_at=row.inspected_at or default_time,
        defect_type_codes=list(row.defect_type_codes),
    )
    return create, []


def _rule_errors(
    row: ImportRow, unit_id: int, spec: ProductSpecification, lookups: _Lookups
) -> list[RowError]:
    """Mirror the checks ``record_inspection`` applies, with the row attached."""
    errors: list[RowError] = []
    if (unit_id, spec.id) in lookups.inspected_pairs:
        message = "This unit already has an inspection for this characteristic"
        errors.append(RowError(row.row, None, message))
    unknown = [code for code in row.defect_type_codes if code not in lookups.defect_codes]
    if unknown:
        errors.append(
            RowError(row.row, "defect_type_codes", f"Unknown defect codes: {', '.join(unknown)}")
        )
    if row.defect_type_codes:
        evaluation = evaluate_measurement(
            measured=row.measured_value,
            target=spec.target_value,
            tolerance=spec.tolerance,
            characteristic=spec.characteristic,
        )
        if evaluation.result is InspectionResult.PASS:
            message = "Defect codes cannot be attached to a passing measurement"
            errors.append(RowError(row.row, "defect_type_codes", message))
    return errors
