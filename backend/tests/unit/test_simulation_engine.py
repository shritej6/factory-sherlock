from datetime import datetime
from decimal import Decimal

import pytest
from app.domain.quality_rules import defect_rate
from app.models.enums import InspectionResult, MachineEventType, MachineStatus
from app.simulation.config import (
    Catalog,
    FaultKind,
    FaultScenario,
    MachineRef,
    ProductRef,
    SimulationConfig,
    SpecRef,
)
from app.simulation.engine import SimulationEngine

START = datetime(2026, 11, 2, 6, 0)


def catalog() -> Catalog:
    shaft = ProductRef(
        1,
        "STEEL-SHAFT",
        (
            SpecRef(1, "diameter", Decimal("20.000"), Decimal("0.100")),
            SpecRef(2, "length", Decimal("150.000"), Decimal("0.500")),
        ),
        (1, 2, 3),
    )
    gear = ProductRef(
        2, "GEAR", (SpecRef(3, "outer_diameter", Decimal("60.000"), Decimal("0.150")),), (4, 5)
    )
    return Catalog(
        products=(shaft, gear), machines=(MachineRef(1, "CNC-01"), MachineRef(2, "CNC-02"))
    )


def run(seed: int = 1, *, units: int = 10, faults: tuple[FaultScenario, ...] = ()):  # type: ignore[no-untyped-def]
    config = SimulationConfig(
        seed=seed, start_time=START, batches_per_machine=6, units_per_batch=units, faults=faults
    )
    return SimulationEngine(config, catalog()).run()


def test_same_seed_same_history() -> None:
    assert run(seed=5) == run(seed=5)


def test_different_seed_different_measurements() -> None:
    a = run(seed=5).batches[0].units[0].inspections[0].measured_value
    b = run(seed=6).batches[0].units[0].inspections[0].measured_value
    assert a != b


def test_counts_follow_configuration() -> None:
    out = run()
    assert len(out.batches) == 12
    assert all(len(b.units) == 10 for b in out.batches)
    assert len(out.orders) == 4  # 6 batches per machine / 4 per order -> 2 orders per machine
    assert out.final_states == {1: MachineStatus.IDLE, 2: MachineStatus.IDLE}


def test_normal_production_has_low_failure_rate() -> None:
    out = run()
    inspections = [i for b in out.batches for u in b.units for i in u.inspections]
    failed = sum(i.result is InspectionResult.FAIL for i in inspections)
    assert failed / len(inspections) < 0.02


def test_tool_wear_raises_failures_and_leaves_machine_in_warning() -> None:
    fault = FaultScenario("CNC-01", FaultKind.TOOL_WEAR, 1)
    # 40 units per batch: by the last batch the offset exceeds the tolerance.
    out = run(units=40, faults=(fault,))
    cnc1 = [b for b in out.batches if b.machine_id == 1]
    assert cnc1[0].failed <= 1
    assert cnc1[-1].failed > cnc1[2].failed > cnc1[0].failed
    assert cnc1[-1].failed > 20
    assert out.final_states[1] is MachineStatus.WARNING
    assert [e.event_type for e in out.fault_events] == [MachineEventType.TOOL_WEAR]
    assert any(a.alert_type.value == "HIGH_DEFECT_RATE" for a in out.alerts)


def test_downtime_skips_a_batch_and_cycles_states() -> None:
    fault = FaultScenario("CNC-02", FaultKind.DOWNTIME, 3)
    out = run(faults=(fault,))
    assert len([b for b in out.batches if b.machine_id == 2]) == 5
    states = [c.new for c in out.state_changes if c.machine_id == 2]
    assert states[:5] == [
        MachineStatus.RUNNING,
        MachineStatus.FAULT,
        MachineStatus.STOPPED,
        MachineStatus.IDLE,
        MachineStatus.RUNNING,
    ]


def test_unknown_fault_machine_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown machine"):
        run(faults=(FaultScenario("CNC-99", FaultKind.TOOL_WEAR, 0),))


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ValueError):
        SimulationConfig(seed=1, start_time=START, batches_per_machine=0)


def test_simulation_starts_from_the_machine_stored_state() -> None:
    faulted = Catalog(
        products=catalog().products,
        machines=(MachineRef(1, "CNC-01", MachineStatus.FAULT), MachineRef(2, "CNC-02")),
    )
    config = SimulationConfig(seed=1, start_time=START, batches_per_machine=2, units_per_batch=5)
    out = SimulationEngine(config, faulted).run()
    path = [(c.previous, c.new) for c in out.state_changes if c.machine_id == 1][:3]
    assert path == [
        (MachineStatus.FAULT, MachineStatus.STOPPED),
        (MachineStatus.STOPPED, MachineStatus.IDLE),
        (MachineStatus.IDLE, MachineStatus.RUNNING),
    ]


def test_downtime_after_tool_wear_returns_to_warning() -> None:
    faults = (
        FaultScenario("CNC-01", FaultKind.TOOL_WEAR, 1),
        FaultScenario("CNC-01", FaultKind.DOWNTIME, 3),
    )
    out = run(faults=faults)
    states = [c.new for c in out.state_changes if c.machine_id == 1]
    assert states[-1] is MachineStatus.WARNING
    assert out.final_states[1] is MachineStatus.WARNING


def test_high_defect_rate_alert_is_raised_once_per_consecutive_run() -> None:
    """Once a batch reaches 0.15 the alert fires; later batches in the same run stay silent."""
    fault = FaultScenario("CNC-01", FaultKind.TOOL_WEAR, 1)
    out = run(units=40, faults=(fault,))
    cnc1 = [b for b in out.batches if b.machine_id == 1]
    rates = [defect_rate(b.failed, b.inspected) for b in cnc1]
    first_bad = next(i for i, r in enumerate(rates) if r >= 0.15)
    assert all(r >= 0.15 for r in rates[first_bad:]), rates  # tool wear only gets worse
    alerts = [a for a in out.alerts if a.alert_type.value == "HIGH_DEFECT_RATE"]
    assert [a.machine_id for a in alerts] == [1]
    assert alerts[0].message.startswith(f"Batch {first_bad + 1} on CNC-01 failed")
    assert alerts[0].at == cnc1[first_bad].completed_at


def test_catalog_and_config_invariants_are_enforced() -> None:
    machines = (MachineRef(1, "CNC-01"),)
    with pytest.raises(ValueError, match="at least one product and one machine"):
        Catalog(products=(), machines=machines)
    with pytest.raises(ValueError, match="at least one product and one machine"):
        Catalog(products=catalog().products, machines=())
    no_lots = ProductRef(9, "BARE", catalog().products[0].specs, ())
    with pytest.raises(ValueError, match="BARE needs specifications and material lots"):
        Catalog(products=(no_lots,), machines=machines)
    no_specs = ProductRef(9, "BARE", (), (1,))
    with pytest.raises(ValueError, match="BARE needs specifications and material lots"):
        Catalog(products=(no_specs,), machines=machines)
    with pytest.raises(ValueError, match="minutes_per_batch"):
        SimulationConfig(seed=1, start_time=START, minutes_per_batch=0)
    with pytest.raises(ValueError, match="units_per_batch"):
        SimulationConfig(seed=1, start_time=START, units_per_batch=0)
