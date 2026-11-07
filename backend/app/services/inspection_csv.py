"""CSV parsing for the inspection import.

Turns the decoded upload into typed rows and collects every structural
problem before the database is consulted. The module never opens a session,
so it is unit tested without MySQL. Error messages name the row, the column,
and the rule that failed; they never repeat free text from the file, and
nothing here is logged.
"""

import csv
import io
import re
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.core.exceptions import ValidationError
from app.schemas.catalog import CODE_PATTERN

REQUIRED_COLUMNS = ("serial_number", "characteristic", "measured_value")
OPTIONAL_COLUMNS = ("inspected_at", "defect_type_codes")
KNOWN_COLUMNS = frozenset(REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
MAX_FILE_BYTES = 1024 * 1024
MAX_DATA_ROWS = 5000
MAX_DEFECT_CODES = 10
SERIAL_MAX_LENGTH = 40
CHARACTERISTIC_MAX_LENGTH = 50
# inspections.measured_value is NUMERIC(10, 3): seven integer digits, three decimals.
MEASURED_MAX_ABS = Decimal("10000000")
_THREE_PLACES = Decimal("0.001")
_CODE_RE = re.compile(CODE_PATTERN)


@dataclass(frozen=True)
class RowError:
    """One problem in the upload.

    ``row`` is the 1-based position below the header (blank lines count, so it
    equals the line number minus one) and is None for header and file-level
    problems. ``field`` is the column name, or None when the problem spans
    columns, or "file" for file-level problems.
    """

    row: int | None
    field: str | None
    message: str


@dataclass(frozen=True)
class ImportRow:
    row: int
    serial_number: str
    characteristic: str
    measured_value: Decimal
    inspected_at: datetime | None
    defect_type_codes: tuple[str, ...]


class FieldError(Exception):
    """Raised by a field parser; converted to a ``RowError`` by the caller."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def import_error(message: str, errors: list[RowError]) -> ValidationError:
    """The 422 body: ``details.errors`` is a list of ``{row, field, message}``."""
    return ValidationError(message, details={"errors": [asdict(e) for e in errors]})


def file_error(message: str) -> ValidationError:
    return import_error(message, [RowError(None, "file", message)])


def parse_csv(text: str) -> tuple[list[ImportRow], list[RowError]]:
    """Parse the decoded file into typed rows plus every row-level error.

    Header problems and the row limit raise immediately because the rest of
    the file cannot be interpreted; row problems are collected so one upload
    reports everything at once.
    """
    reader = csv.reader(io.StringIO(text, newline=""))
    columns = _read_header(reader)
    rows: list[ImportRow] = []
    errors: list[RowError] = []
    first_seen: dict[tuple[str, str], int] = {}
    data_rows = 0
    for record in reader:
        if _is_blank(record):
            continue
        data_rows += 1
        if data_rows > MAX_DATA_ROWS:
            raise file_error(f"The file has more than {MAX_DATA_ROWS} data rows")
        row_number = reader.line_num - 1
        parsed, row_errors = _parse_record(record, columns, row_number)
        errors.extend(row_errors)
        if parsed is None:
            continue
        duplicate = _duplicate_error(parsed, first_seen)
        if duplicate is not None:
            errors.append(duplicate)
        else:
            rows.append(parsed)
    if data_rows == 0:
        raise file_error("The file has no data rows")
    return rows, errors


def _read_header(reader: Iterator[list[str]]) -> dict[str, int]:
    header = next(reader, None)
    if header is None or _is_blank(header):
        raise file_error("The file has no header row")
    names = [name.strip().lower() for name in header]
    errors: list[RowError] = []
    for name in names:
        if name not in KNOWN_COLUMNS:
            errors.append(RowError(None, name or None, "Unknown column"))
        elif names.count(name) > 1:
            errors.append(RowError(None, name, "Column appears more than once"))
    for required in REQUIRED_COLUMNS:
        if required not in names:
            errors.append(RowError(None, required, "Required column is missing"))
    if errors:
        raise import_error("The CSV header is invalid", _unique(errors))
    return {name: index for index, name in enumerate(names)}


def _unique(errors: list[RowError]) -> list[RowError]:
    return list(dict.fromkeys(errors))


def _is_blank(record: list[str]) -> bool:
    return all(value.strip() == "" for value in record)


def _parse_record(
    record: list[str], columns: dict[str, int], row: int
) -> tuple[ImportRow | None, list[RowError]]:
    if len(record) != len(columns):
        message = f"Expected {len(columns)} values but found {len(record)}"
        return None, [RowError(row, None, message)]
    values = {name: record[index].strip() for name, index in columns.items()}
    errors: list[RowError] = []

    def field[T](name: str, parse: Callable[[str], T]) -> T | None:
        try:
            return parse(values.get(name, ""))
        except FieldError as exc:
            errors.append(RowError(row, name, exc.message))
            return None

    serial = field("serial_number", lambda v: _required_text(v, SERIAL_MAX_LENGTH))
    characteristic = field("characteristic", lambda v: _required_text(v, CHARACTERISTIC_MAX_LENGTH))
    measured = field("measured_value", _parse_measured)
    inspected_at = field("inspected_at", _parse_timestamp)
    codes = field("defect_type_codes", _parse_codes)
    if errors or serial is None or characteristic is None or measured is None or codes is None:
        return None, errors
    return ImportRow(row, serial, characteristic, measured, inspected_at, codes), []


def _duplicate_error(row: ImportRow, first_seen: dict[tuple[str, str], int]) -> RowError | None:
    key = (row.serial_number, row.characteristic.lower())
    earlier = first_seen.setdefault(key, row.row)
    if earlier == row.row:
        return None
    return RowError(
        row.row, None, f"Same serial number and characteristic as row {earlier} of this file"
    )


def _required_text(value: str, max_length: int) -> str:
    if not value:
        raise FieldError("Value is required")
    if len(value) > max_length:
        raise FieldError(f"Value is longer than {max_length} characters")
    return value


def _parse_measured(value: str) -> Decimal:
    if not value:
        raise FieldError("Value is required")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise FieldError("Must be a decimal number such as 20.040") from exc
    if not number.is_finite():
        raise FieldError("Must be a decimal number such as 20.040")
    if abs(number) >= MEASURED_MAX_ABS:
        raise FieldError(f"Must be smaller than {MEASURED_MAX_ABS} in absolute value")
    quantized = number.quantize(_THREE_PLACES)
    if quantized != number:
        raise FieldError("Must have at most 3 decimal places")
    return quantized


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FieldError("Must be an ISO 8601 timestamp such as 2026-11-02T08:15:00") from exc
    if parsed.tzinfo is not None:
        raise FieldError("Must not carry a UTC offset; timestamps are server local time")
    # MySQL DATETIME has no fractional seconds; truncating keeps stored and returned values equal.
    return parsed.replace(microsecond=0)


def _parse_codes(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    codes = [code.strip() for code in value.split("|") if code.strip()]
    if any(_CODE_RE.fullmatch(code) is None for code in codes):
        raise FieldError(
            "Codes use upper case letters, digits, '_' or '-' and are separated by '|'"
        )
    unique = tuple(dict.fromkeys(codes))
    if len(unique) > MAX_DEFECT_CODES:
        raise FieldError(f"At most {MAX_DEFECT_CODES} defect codes per row")
    return unique
