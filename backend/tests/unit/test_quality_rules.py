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


@pytest.mark.parametrize(
    ("characteristic", "measured", "target", "tolerance", "code"),
    [
        ("bore_diameter", "11.800", "12.000", "0.050", DEFECT_UNDERSIZE),
        ("outer_diameter", "60.200", "60.000", "0.150", DEFECT_OVERSIZE),
        ("length", "149.000", "150.000", "0.500", DEFECT_DIMENSIONAL),
        ("hole_position", "49.500", "50.000", "0.200", DEFECT_HOLE_POSITION),
        ("thickness", "5.101", "5.000", "0.100", DEFECT_DIMENSIONAL),
    ],
)
def test_classification_covers_every_characteristic_and_sign(
    characteristic: str, measured: str, target: str, tolerance: str, code: str
) -> None:
    result = evaluate_measurement(
        measured=Decimal(measured),
        target=Decimal(target),
        tolerance=Decimal(tolerance),
        characteristic=characteristic,
    )
    assert result.result is InspectionResult.FAIL
    assert result.defect_code == code


def test_tolerance_boundary_is_inclusive_on_both_sides() -> None:
    low = evaluate_measurement(
        measured=Decimal("19.900"), target=TARGET, tolerance=TOL, characteristic="diameter"
    )
    below = evaluate_measurement(
        measured=Decimal("19.899"), target=TARGET, tolerance=TOL, characteristic="diameter"
    )
    assert low.result is InspectionResult.PASS and low.defect_code is None
    assert below.result is InspectionResult.FAIL and below.defect_code == DEFECT_UNDERSIZE
