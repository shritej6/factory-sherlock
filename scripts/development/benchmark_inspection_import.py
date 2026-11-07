#!/usr/bin/env python3
"""Times the CSV inspection import at its 5000-row maximum.

    cd backend && uv run python ../scripts/development/benchmark_inspection_import.py

The script builds one STEEL-SHAFT batch of 2500 units through the production
service (two specifications per unit give 5000 rows), renders the CSV the way
a gauge export would, and times ``inspection_import.import_csv`` inside a
savepoint that is rolled back, so no rows are left behind (InnoDB
auto-increment counters still advance). Reference data is applied when the
database has no products. Each run is repeated three times and the median
wall time and SQL statement count are reported.
"""

import statistics
import sys
import time
from dataclasses import dataclass
from decimal import Decimal

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models import Machine, MaterialLot, OrderStatus, Product
from app.schemas.production import (
    BatchMaterialInput,
    ProductionBatchCreate,
    ProductionOrderCreate,
)
from app.seed import apply_reference_sql
from app.services import inspection_import, production_service
from app.services.inspection_csv import MAX_DATA_ROWS
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

REPEATS = 3
UNITS = MAX_DATA_ROWS // 2  # STEEL-SHAFT has two specifications
HEADER = "serial_number,characteristic,measured_value,inspected_at,defect_type_codes\n"
# Every tenth unit fails its diameter and carries an explicit code so the
# defect path is exercised; the length value varies within tolerance.
FAILING_EVERY = 10


@dataclass(frozen=True)
class Timing:
    seconds: float
    statements: int
    imported: int
    failed: int


class StatementCounter:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self, *args: object) -> None:
        self.count += 1


def build_batch(session: Session) -> str:
    """One released order and one batch; returns the batch number."""
    if (session.scalar(select(func.count(Product.id))) or 0) == 0:
        apply_reference_sql(session)
    product_id = session.scalar(select(Product.id).where(Product.code == "STEEL-SHAFT"))
    lot_id = session.scalar(select(MaterialLot.id).where(MaterialLot.lot_number == "L201"))
    machine_id = session.scalar(select(Machine.id).where(Machine.code == "CNC-01"))
    assert product_id and lot_id and machine_id, "reference data is missing"
    order = production_service.create_order(
        session,
        ProductionOrderCreate(
            order_number=f"BENCH-{int(time.time()) % 1_000_000:06d}",
            product_id=product_id,
            machine_id=machine_id,
            quantity_planned=UNITS,
        ),
    )
    production_service.change_order_status(session, order.id, OrderStatus.RELEASED)
    batch = production_service.create_batch(
        session,
        ProductionBatchCreate(
            production_order_id=order.id,
            quantity=UNITS,
            materials=[BatchMaterialInput(material_lot_id=lot_id, quantity_used=Decimal("1"))],
        ),
    )
    return batch.batch_number


def render_csv(batch_number: str) -> bytes:
    lines = [HEADER]
    for seq in range(1, UNITS + 1):
        serial = f"{batch_number}-U{seq:04d}"
        diameter = "20.250" if seq % FAILING_EVERY == 0 else f"20.{seq % 90:03d}"
        codes = "SURFACE_DAMAGE" if seq % FAILING_EVERY == 0 else ""
        lines.append(f"{serial},diameter,{diameter},2026-11-02T08:{seq % 60:02d}:00,{codes}\n")
        lines.append(f"{serial},length,150.{seq % 400:03d},,\n")
    return "".join(lines).encode("utf-8")


def time_import(session: Session, content: bytes) -> Timing:
    counter = StatementCounter()
    event.listen(engine, "before_cursor_execute", counter)
    savepoint = session.begin_nested()
    started = time.perf_counter()
    try:
        result = inspection_import.import_csv(
            session, content, content_type="text/csv", filename="benchmark.csv"
        )
        elapsed = time.perf_counter() - started
    finally:
        savepoint.rollback()
        event.remove(engine, "before_cursor_execute", counter)
    return Timing(elapsed, counter.count, result.imported, result.failed_inspections)


def main() -> int:
    settings = get_settings()
    if settings.app_env == "production":
        print("refusing to benchmark against a production database", file=sys.stderr)
        return 2
    print(f"database: {settings.effective_database}, repeats: {REPEATS}")
    with SessionLocal() as session:
        batch_number = build_batch(session)
        content = render_csv(batch_number)
        runs = [time_import(session, content) for _ in range(REPEATS)]
        session.rollback()
    first = runs[0]
    median = statistics.median(r.seconds for r in runs)
    print(f"rows: {first.imported} imported, {first.failed} failed, {len(content)} bytes")
    print(f"statements per run: {first.statements}")
    print(f"median seconds: {median:.2f} ({first.imported / median:.0f} rows/s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
