from datetime import datetime
from decimal import Decimal

import pytest
from app.core.exceptions import ValidationError
from app.services.inspection_csv import MAX_DATA_ROWS, MEASURED_FORMAT, RowError, parse_csv

HEADER = "serial_number,characteristic,measured_value,inspected_at,defect_type_codes\n"


def _errors(exc: ValidationError) -> list[dict[str, object]]:
    errors = exc.details["errors"]
    assert isinstance(errors, list)
    return errors


def test_columns_may_appear_in_any_order_and_optional_ones_may_be_absent() -> None:
    rows, errors = parse_csv(
        "measured_value,characteristic,serial_number\n20.040,Diameter,PO-1-B01-U0001\n"
    )
    assert errors == []
    assert len(rows) == 1
    row = rows[0]
    assert (row.row, row.serial_number, row.characteristic) == (1, "PO-1-B01-U0001", "Diameter")
    assert row.measured_value == Decimal("20.040")
    assert row.inspected_at is None and row.defect_type_codes == ()


def test_optional_columns_are_parsed() -> None:
    rows, errors = parse_csv(
        HEADER
        + "S1,diameter,20.3,2026-11-02T08:15:00,OVERSIZE_DIAMETER|SURFACE_DAMAGE|OVERSIZE_DIAMETER\n"
    )
    assert errors == []
    assert rows[0].inspected_at == datetime(2026, 11, 2, 8, 15)
    assert rows[0].defect_type_codes == ("OVERSIZE_DIAMETER", "SURFACE_DAMAGE")
    assert rows[0].measured_value == Decimal("20.300")


def test_missing_required_column_is_a_header_error() -> None:
    with pytest.raises(ValidationError) as info:
        parse_csv("serial_number,measured_value\nS1,20.0\n")
    assert _errors(info.value) == [
        {"row": None, "field": "characteristic", "message": "Required column is missing"}
    ]


def test_unknown_and_duplicate_columns_are_header_errors() -> None:
    with pytest.raises(ValidationError) as info:
        parse_csv(
            "serial_number,characteristic,measured_value,operator,serial_number\nS1,d,1,x,S1\n"
        )
    assert _errors(info.value) == [
        {"row": None, "field": "serial_number", "message": "Column appears more than once"},
        {"row": None, "field": "operator", "message": "Unknown column"},
    ]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("twenty", MEASURED_FORMAT),
        ("", "Value is required"),
        ("20.0005", "Must have at most 3 decimal places"),
        ("20.0400", "Must have at most 3 decimal places"),
        ("NaN", MEASURED_FORMAT),
        ("1_000", MEASURED_FORMAT),
        ("2.004e1", MEASURED_FORMAT),
        ("Infinity", MEASURED_FORMAT),
        ("20.", MEASURED_FORMAT),
        (".5", MEASURED_FORMAT),
        ("\u0662\u0660.\u0660\u0664", MEASURED_FORMAT),
        ("12345678", "Must be smaller than 10000000 in absolute value"),
    ],
)
def test_bad_measured_values_name_the_row_and_field(value: str, message: str) -> None:
    rows, errors = parse_csv(HEADER + f"S1,diameter,{value},,\n")
    assert rows == []
    assert errors == [RowError(1, "measured_value", message)]


@pytest.mark.parametrize(
    ("value", "stored"), [("20.04", "20.040"), ("+7", "7.000"), ("-0.5", "-0.500")]
)
def test_accepted_decimals_are_stored_with_three_places(value: str, stored: str) -> None:
    rows, errors = parse_csv(HEADER + f"S1,diameter,{value},,\n")
    assert errors == [] and rows[0].measured_value == Decimal(stored)


@pytest.mark.parametrize("value", ["yesterday", "2026-11-02T08:15:00+00:00", "2026-13-01"])
def test_bad_timestamps_are_rejected(value: str) -> None:
    rows, errors = parse_csv(HEADER + f"S1,diameter,20.0,{value},\n")
    assert rows == [] and len(errors) == 1
    assert (errors[0].row, errors[0].field) == (1, "inspected_at")


def test_timestamps_lose_microseconds_like_the_clock() -> None:
    rows, _ = parse_csv(HEADER + "S1,diameter,20.0,2026-11-02 08:15:00.250,\n")
    assert rows[0].inspected_at == datetime(2026, 11, 2, 8, 15, 0)


def test_defect_codes_must_match_the_code_pattern() -> None:
    rows, errors = parse_csv(HEADER + "S1,diameter,20.0,,oversize diameter\n")
    assert rows == [] and errors[0].field == "defect_type_codes" and errors[0].row == 1


def test_every_problem_in_a_row_is_reported_and_rows_keep_their_position() -> None:
    text = HEADER + "\n,diameter,abc,,\n   \nS2,diameter,20.0,,\n"
    rows, errors = parse_csv(text)
    assert [r.row for r in rows] == [4]
    assert errors == [
        RowError(2, "serial_number", "Value is required"),
        RowError(2, "measured_value", MEASURED_FORMAT),
    ]


def test_wrong_number_of_values_is_reported() -> None:
    rows, errors = parse_csv(HEADER + "S1,diameter,20.0\n")
    assert rows == [] and errors == [RowError(1, None, "Expected 5 values but found 3")]


def test_duplicate_serial_and_characteristic_pair_names_the_earlier_row() -> None:
    text = HEADER + "S1,diameter,20.0,,\nS1,length,150.0,,\nS1,DIAMETER,20.1,,\n"
    rows, errors = parse_csv(text)
    assert [r.row for r in rows] == [1, 2]
    assert errors == [
        RowError(3, None, "Same serial number and characteristic as row 1 of this file")
    ]


def test_row_limit_is_enforced_before_any_lookup() -> None:
    text = HEADER + "".join(f"S{i},diameter,20.0,,\n" for i in range(MAX_DATA_ROWS + 1))
    with pytest.raises(ValidationError) as info:
        parse_csv(text)
    assert _errors(info.value) == [
        {
            "row": None,
            "field": "file",
            "message": f"The file has more than {MAX_DATA_ROWS} data rows",
        }
    ]
    rows, errors = parse_csv(
        HEADER + "".join(f"S{i},diameter,20.0,,\n" for i in range(MAX_DATA_ROWS))
    )
    assert len(rows) == MAX_DATA_ROWS and errors == []


def test_header_only_and_empty_text_are_rejected() -> None:
    with pytest.raises(ValidationError, match="no data rows"):
        parse_csv(HEADER + "\n\n")
    with pytest.raises(ValidationError, match="no header row"):
        parse_csv("")


def test_serial_numbers_are_upper_cased_so_case_variants_are_the_same_unit() -> None:
    rows, errors = parse_csv(
        HEADER + "po-1-b01-u0001,diameter,20.0,,\nPO-1-B01-U0001,Diameter,20.1,,\n"
    )
    assert [r.serial_number for r in rows] == ["PO-1-B01-U0001"]
    assert errors == [
        RowError(2, None, "Same serial number and characteristic as row 1 of this file")
    ]


def test_quoted_field_spanning_lines_does_not_shift_row_numbers() -> None:
    text = HEADER + 'S1,"dia\nmeter",20.0,,\nS2,diameter,abc,,\n'
    rows, errors = parse_csv(text)
    assert [(r.row, r.characteristic) for r in rows] == [(1, "dia\nmeter")]
    assert errors == [RowError(2, "measured_value", MEASURED_FORMAT)]


@pytest.mark.parametrize(
    "text",
    [
        HEADER + "S1,diameter," + "9" * 131_073 + ",,\n",
        HEADER + 'S1,"diameter"x,20.0,,\n',
        HEADER + 'S1,"diameter,20.0,,\n',
    ],
)
def test_broken_csv_structure_is_a_file_error_not_a_crash(text: str) -> None:
    with pytest.raises(ValidationError) as info:
        parse_csv(text)
    assert _errors(info.value) == [
        {"row": None, "field": "file", "message": "The CSV structure is invalid"}
    ]


def test_unknown_header_names_are_echoed_truncated_and_blank_cells_are_labelled() -> None:
    long_name = "x" * 80
    with pytest.raises(ValidationError) as info:
        parse_csv(f"serial_number,characteristic,measured_value,{long_name},,\nS1,d,1,a,b,c\n")
    assert _errors(info.value) == [
        {"row": None, "field": "x" * 50, "message": "Unknown column"},
        {"row": None, "field": "(blank column 5)", "message": "Unknown column"},
        {"row": None, "field": "(blank column 6)", "message": "Unknown column"},
    ]
