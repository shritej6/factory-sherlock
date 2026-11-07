"""Bulk persistence of simulation output: chunking and id mapping.

The service writes units, inspections, and defects with multi-row INSERTs and
then selects generated ids back by natural key. These tests check that the
rows written match the engine output row for row, including runs that span
more than one insert chunk.
"""

from dataclasses import replace
from datetime import datetime

from app.core.database import Base
from app.models import Inspection, InspectionDefect, ProductionBatch, ProductionUnit
from app.schemas.simulation import FaultScenario, SimulationRequest
from app.services import simulation_service
from app.simulation.config import SimulationConfig
from app.simulation.engine import SimulationEngine
from app.simulation.events import SimulatedBatch, SimulationOutput
from sqlalchemy import func, select
from sqlalchemy.orm import Session

START = datetime(2026, 11, 2, 6, 0)


def _count(session: Session, model: type[Base]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _defect_rows_in(output: SimulationOutput) -> int:
    return sum(len(i.defect_codes) for b in output.batches for u in b.units for i in u.inspections)


def test_run_spanning_several_chunks_persists_exact_counts(db_session: Session) -> None:
    """Two batches of 1200 units: each batch alone exceeds BULK_CHUNK_SIZE."""
    assert simulation_service.BULK_CHUNK_SIZE == 1000
    catalog = simulation_service.load_catalog(db_session)
    two_machines = replace(catalog, machines=catalog.machines[:2])
    config = SimulationConfig(
        seed=11, start_time=START, batches_per_machine=1, units_per_batch=1200
    )
    output = SimulationEngine(config, two_machines).run()
    assert len(output.batches) == 2

    result = simulation_service.persist(db_session, output, two_machines, run_tag="SIM0001")
    db_session.commit()

    expected_inspections = sum(b.inspected for b in output.batches)
    assert result.units_created == 2400
    assert result.inspections_created == expected_inspections
    assert result.failed_inspections == sum(b.failed for b in output.batches)
    assert _count(db_session, ProductionBatch) == 2
    assert _count(db_session, ProductionUnit) == 2400
    assert _count(db_session, Inspection) == expected_inspections
    assert _count(db_session, InspectionDefect) == _defect_rows_in(output)


def _persisted_batch(session: Session, sim_batch: SimulatedBatch) -> ProductionBatch:
    return session.scalars(
        select(ProductionBatch).where(
            ProductionBatch.machine_id == sim_batch.machine_id,
            ProductionBatch.started_at == sim_batch.started_at,
        )
    ).one()


def test_inspections_point_at_the_unit_with_the_matching_serial(db_session: Session) -> None:
    """Sample units from every batch and compare their stored inspections with the engine's."""
    request = SimulationRequest(
        seed=5,
        start_time=START,
        batches_per_machine=3,
        units_per_batch=25,
        faults=[FaultScenario(machine_code="CNC-01", fault="MATERIAL_ISSUE", start_batch_index=0)],
    )
    catalog = simulation_service.load_catalog(db_session)
    output = SimulationEngine(simulation_service.to_config(request), catalog).run()
    simulation_service.run_simulation(db_session, request)
    db_session.commit()

    checked = 0
    for sim_batch in output.batches:
        batch = _persisted_batch(db_session, sim_batch)
        for sim_unit in (sim_batch.units[0], sim_batch.units[12], sim_batch.units[-1]):
            serial = f"{batch.batch_number}-U{sim_unit.sequence_in_batch:04d}"
            unit = db_session.scalars(
                select(ProductionUnit).where(ProductionUnit.serial_number == serial)
            ).one()
            stored = {
                (i.specification_id, i.measured_value, i.result): {
                    d.defect_type_id for d in i.defect_links
                }
                for i in unit.inspections
            }
            expected = {
                (i.specification_id, i.measured_value, i.result): {
                    catalog.defect_type_ids[code] for code in i.defect_codes
                }
                for i in sim_unit.inspections
            }
            assert stored == expected, serial
            checked += 1
    assert checked == 3 * len(output.batches)
