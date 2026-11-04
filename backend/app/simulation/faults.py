"""Fault models: how each simulated fault distorts measurements.

These are deliberately simple, documented in docs/simulation/fault-models.md,
and tuned so that an investigation can see the effect within a few batches.
All effects are expressed relative to the specification tolerance so they
scale across products with different units.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.simulation.config import FaultKind

# Fraction of tolerance added per unit produced since tool wear started.
TOOL_WEAR_RATE = Decimal("0.008")
# Constant bias as a fraction of tolerance for a miscalibrated machine.
CALIBRATION_OFFSET = Decimal("-0.80")
# Standard deviation multiplier for the increased-variation fault.
VARIATION_MULTIPLIER = Decimal("3.0")
# Probability that a unit made from problematic material shows a gross defect.
MATERIAL_ISSUE_PROBABILITY = 0.15


@dataclass
class ActiveFault:
    kind: FaultKind
    units_since_start: int = 0

    def advance(self) -> None:
        self.units_since_start += 1


@dataclass(frozen=True)
class MeasurementEffect:
    offset_fraction: Decimal = Decimal("0")
    sigma_multiplier: Decimal = Decimal("1")
    gross_defect_probability: float = 0.0


def combined_effect(
    active: list[ActiveFault], *, primary_characteristic: bool
) -> MeasurementEffect:
    """Sum the effects of every active fault for one measurement.

    Tool wear only affects the primary (first) characteristic because a worn
    cutting tool changes the dimension it cuts, not every dimension of the
    part. The other faults affect all characteristics.
    """
    offset = Decimal("0")
    sigma = Decimal("1")
    gross = 0.0
    for fault in active:
        if fault.kind is FaultKind.TOOL_WEAR and primary_characteristic:
            offset += TOOL_WEAR_RATE * fault.units_since_start
        elif fault.kind is FaultKind.CALIBRATION_DRIFT:
            offset += CALIBRATION_OFFSET
        elif fault.kind is FaultKind.VARIATION:
            sigma *= VARIATION_MULTIPLIER
        elif fault.kind is FaultKind.MATERIAL_ISSUE:
            gross = max(gross, MATERIAL_ISSUE_PROBABILITY)
    return MeasurementEffect(offset, sigma, gross)
