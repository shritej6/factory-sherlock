#!/usr/bin/env python3
"""Times simulation persistence against the configured development database.

    cd backend && uv run python ../scripts/development/benchmark_simulation.py

Two request shapes are run through ``simulation_service.run_simulation``, the
same function the API route and ``app.seed --demo`` call. Every run is wrapped
in a session that is rolled back, so no rows are left behind (InnoDB
auto-increment counters still advance; that is the only trace). Each shape is
repeated three times and the median is reported, together with the time the
pure engine needs on its own so the persistence share is visible.

Rows per second counts production units plus inspections over the median total
time of the service call.
"""

import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.schemas.simulation import FaultScenario, SimulationRequest
from app.services import simulation_service
from app.simulation.engine import SimulationEngine

REPEATS = 3
START = datetime(2026, 11, 2, 6, 0, 0)
SHAPES = {
    "demo (3 x 12 x 20)": SimulationRequest(
        seed=42,
        start_time=START,
        batches_per_machine=12,
        units_per_batch=20,
        minutes_per_batch=30,
        faults=[
            FaultScenario(machine_code="CNC-03", fault="TOOL_WEAR", start_batch_index=4),
            FaultScenario(machine_code="CNC-02", fault="DOWNTIME", start_batch_index=6),
        ],
    ),
    "large (3 x 40 x 50)": SimulationRequest(
        seed=42,
        start_time=START,
        batches_per_machine=40,
        units_per_batch=50,
        minutes_per_batch=30,
        faults=[FaultScenario(machine_code="CNC-03", fault="TOOL_WEAR", start_batch_index=20)],
    ),
}


@dataclass(frozen=True)
class Timing:
    shape: str
    units: int
    inspections: int
    total_seconds: float
    engine_seconds: float

    @property
    def rows_per_second(self) -> float:
        return (self.units + self.inspections) / self.total_seconds


def time_engine(request: SimulationRequest) -> float:
    """Engine only, so the persistence share of the total can be read off."""
    with SessionLocal() as session:
        catalog = simulation_service.load_catalog(session)
        session.rollback()
    config = simulation_service.to_config(request)
    started = time.perf_counter()
    SimulationEngine(config, catalog).run()
    return time.perf_counter() - started


def time_service_path(shape: str, request: SimulationRequest) -> Timing:
    with SessionLocal() as session:
        started = time.perf_counter()
        result = simulation_service.run_simulation(session, request)
        elapsed = time.perf_counter() - started
        session.rollback()
    return Timing(
        shape=shape,
        units=result.units_created,
        inspections=result.inspections_created,
        total_seconds=elapsed,
        engine_seconds=time_engine(request),
    )


def median_timing(shape: str, request: SimulationRequest) -> Timing:
    runs = [time_service_path(shape, request) for _ in range(REPEATS)]
    return Timing(
        shape=shape,
        units=runs[0].units,
        inspections=runs[0].inspections,
        total_seconds=statistics.median(r.total_seconds for r in runs),
        engine_seconds=statistics.median(r.engine_seconds for r in runs),
    )


def print_table(timings: list[Timing]) -> None:
    columns = [("shape", "<22"), ("units", ">8"), ("inspections", ">13")]
    columns += [("median s", ">10"), ("engine s", ">10"), ("rows/s", ">9")]
    header = "".join(format(name, spec) for name, spec in columns)
    print(header)
    print("-" * len(header))
    for t in timings:
        print(
            f"{t.shape:<22}{t.units:>8}{t.inspections:>13}"
            f"{t.total_seconds:>10.2f}{t.engine_seconds:>10.2f}{t.rows_per_second:>9.0f}"
        )


def main() -> int:
    settings = get_settings()
    if settings.app_env == "production":
        print("refusing to benchmark against a production database", file=sys.stderr)
        return 2
    print(f"database: {settings.effective_database}, repeats per shape: {REPEATS}")
    print_table([median_timing(shape, request) for shape, request in SHAPES.items()])
    return 0


if __name__ == "__main__":
    sys.exit(main())
