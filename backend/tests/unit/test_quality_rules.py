from decimal import Decimal

import pytest
from app.domain.quality_rules import (
    DEFECT_DIMENSIONAL,
    DEFECT_HOLE_POSITION,
    DEFECT_OVERSIZE,
    DEFECT_UNDERSIZE,
    defect_rate,
    evaluate_measurement,
)
from app.models.enums import InspectionResult

TARGET = Decimal("20.000")
TOL = Decimal("0.100")


@pytest.mark.parametrize("value", ["20.000", "20.040", "19.900", "20.100"])
def test_values_inside_tolerance_pass(value: str) -> None:
    result = evaluate_measurement(
        measured=Decimal(value), target=TARGET, tolerance=TOL, characteristic="diameter"
    )
    assert result.result is InspectionResult.PASS
    assert result.defect_code is None


@pytest.mark.parametrize(
    ("value", "code"),
    [("20.250", DEFECT_OVERSIZE), ("20.101", DEFECT_OVERSIZE), ("19.850", DEFECT_UNDERSIZE)],
)
def test_diameter_failures_are_classified_by_direction(value: str, code: str) -> None:
    result = evaluate_measurement(
        measured=Decimal(value), target=TARGET, tolerance=TOL, characteristic="diameter"
    )
    assert result.result is InspectionResult.FAIL
    assert result.defect_code == code


def test_other_characteristics_map_to_their_defect_types() -> None:
    hole = evaluate_measurement(
        measured=Decimal("50.5"),
        target=Decimal("50"),
        tolerance=Decimal("0.2"),
        characteristic="hole_position",
    )
    length = evaluate_measurement(
        measured=Decimal("151"),
        target=Decimal("150"),
        tolerance=Decimal("0.5"),
        characteristic="length",
    )
    assert hole.defect_code == DEFECT_HOLE_POSITION
    assert length.defect_code == DEFECT_DIMENSIONAL


def test_defect_rate_definition() -> None:
    assert defect_rate(0, 0) == 0.0
    assert defect_rate(3, 12) == 0.25
    assert defect_rate(1, 3) == 0.3333
