"""Quality evaluation: compare a measurement with a specification.

A unit passes a characteristic when ``abs(measured - target) <= tolerance``.
Defect classification depends on the characteristic name so that an oversize
shaft and an off-position bracket hole are reported as different problems.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import InspectionResult

# Defect type codes are seeded in database/seeds/01_reference_data.sql.
DEFECT_OVERSIZE = "OVERSIZE_DIAMETER"
DEFECT_UNDERSIZE = "UNDERSIZE_DIAMETER"
DEFECT_HOLE_POSITION = "HOLE_POSITION_DEVIATION"
DEFECT_DIMENSIONAL = "DIMENSIONAL_DEVIATION"
DEFECT_SURFACE = "SURFACE_DAMAGE"
# Every code the evaluator or simulator can attach; the reference seed must define them all.
DEFECT_CODES = (
    DEFECT_OVERSIZE,
    DEFECT_UNDERSIZE,
    DEFECT_HOLE_POSITION,
    DEFECT_DIMENSIONAL,
    DEFECT_SURFACE,
)

DIAMETER_CHARACTERISTICS = frozenset({"diameter", "outer_diameter", "bore_diameter"})


@dataclass(frozen=True)
class Evaluation:
    result: InspectionResult
    deviation: Decimal
    defect_code: str | None


def evaluate_measurement(
    *, measured: Decimal, target: Decimal, tolerance: Decimal, characteristic: str
) -> Evaluation:
    deviation = measured - target
    if abs(deviation) <= tolerance:
        return Evaluation(InspectionResult.PASS, deviation, None)
    return Evaluation(InspectionResult.FAIL, deviation, classify_defect(characteristic, deviation))


def classify_defect(characteristic: str, deviation: Decimal) -> str:
    if characteristic in DIAMETER_CHARACTERISTICS:
        return DEFECT_OVERSIZE if deviation > 0 else DEFECT_UNDERSIZE
    if characteristic == "hole_position":
        return DEFECT_HOLE_POSITION
    return DEFECT_DIMENSIONAL


def defect_rate(failed: int, inspected: int) -> float:
    """failed / inspected, defined as 0.0 when nothing was inspected.

    This is the single definition used by the API, the simulator, and the
    investigation engine so every screen reports the same number.
    """
    return 0.0 if inspected == 0 else round(failed / inspected, 4)
