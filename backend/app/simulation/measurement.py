"""Measurement generation.

Normal production is modelled as a normal distribution centred on the target
with a standard deviation of one third of the tolerance, which yields roughly
0.3 percent natural failures. Faults shift the mean or widen the spread.
"""

import random
from decimal import ROUND_HALF_UP, Decimal

from app.simulation.config import SpecRef
from app.simulation.faults import MeasurementEffect

NATURAL_SIGMA_FRACTION = Decimal("1") / Decimal("3")
_QUANT = Decimal("0.001")


class MeasurementGenerator:
    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def generate(self, spec: SpecRef, effect: MeasurementEffect) -> tuple[Decimal, bool]:
        """Return (measured_value, gross_defect_flag)."""
        sigma = float(spec.tolerance * NATURAL_SIGMA_FRACTION * effect.sigma_multiplier)
        value = Decimal(str(self._rng.gauss(0.0, sigma)))
        value += spec.tolerance * effect.offset_fraction
        gross = False
        if effect.gross_defect_probability and self._rng.random() < effect.gross_defect_probability:
            # Material problems show up as a large deviation in either direction.
            direction = 1 if self._rng.random() < 0.5 else -1
            value += spec.tolerance * Decimal(str(1.0 + self._rng.random())) * direction
            gross = True
        measured = (spec.target + value).quantize(_QUANT, rounding=ROUND_HALF_UP)
        return measured, gross
