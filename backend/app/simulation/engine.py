"""Virtual factory engine.

Runs every machine through a fixed number of batches, generating units,
measurements, inspections, machine events, and alerts. Deterministic for a
given (config, catalog) pair because all randomness flows through one
``random.Random`` seeded from the config.

Simplifications (documented in docs/simulation/simulation-design.md):
machines run in parallel on a shared clock, each batch takes exactly
``minutes_per_batch``, and every unit is inspected on every characteristic.
"""

import random
from datetime import datetime, timedelta

from app.domain.quality_rules import DEFECT_SURFACE, defect_rate, evaluate_measurement
from app.models.enums import AlertType, InspectionResult, MachineEventType, MachineStatus, Severity
from app.simulation.config import (
    Catalog,
    FaultKind,
    FaultScenario,
    MachineRef,
    ProductRef,
    SimulationConfig,
    SpecRef,
)
from app.simulation.events import (
    FaultEvent,
    SimulatedAlert,
    SimulatedBatch,
    SimulatedInspection,
    SimulatedOrder,
    SimulatedUnit,
    SimulationOutput,
)
from app.simulation.faults import ActiveFault, combined_effect
from app.simulation.machine_state import MachineStateTracker
from app.simulation.measurement import MeasurementGenerator

_FAULT_EVENT_TYPES = {
    FaultKind.TOOL_WEAR: MachineEventType.TOOL_WEAR,
    FaultKind.CALIBRATION_DRIFT: MachineEventType.CALIBRATION_DRIFT,
    FaultKind.VARIATION: MachineEventType.CALIBRATION_DRIFT,
    FaultKind.MATERIAL_ISSUE: MachineEventType.MATERIAL_ISSUE,
    FaultKind.DOWNTIME: MachineEventType.DOWNTIME,
}
_FAULT_DESCRIPTIONS = {
    FaultKind.TOOL_WEAR: "Simulated cutting tool wear: dimensions drift upward over time",
    FaultKind.CALIBRATION_DRIFT: "Simulated calibration error: constant undersize bias",
    FaultKind.VARIATION: "Simulated spindle instability: measurement spread increased",
    FaultKind.MATERIAL_ISSUE: "Simulated material defect: intermittent gross deviations",
    FaultKind.DOWNTIME: "Simulated unplanned downtime: machine faulted and was restarted",
}


class SimulationEngine:
    def __init__(self, config: SimulationConfig, catalog: Catalog) -> None:
        self._config = config
        self._catalog = catalog
        self._rng = random.Random(config.seed)
        self._measure = MeasurementGenerator(self._rng)
        self._machine_codes = {m.code for m in catalog.machines}
        for fault in config.faults:
            if fault.machine_code not in self._machine_codes:
                raise ValueError(f"fault references unknown machine {fault.machine_code}")

    def run(self) -> SimulationOutput:
        output = SimulationOutput(seed=self._config.seed)
        for machine_index, machine in enumerate(self._catalog.machines):
            self._run_machine(machine_index, machine, output)
        return output

    def _run_machine(self, machine_index: int, machine: MachineRef, out: SimulationOutput) -> None:
        cfg = self._config
        tracker = MachineStateTracker(machine.machine_id, machine.code, machine.status)
        clock = cfg.start_time
        active: list[ActiveFault] = []
        faults_by_batch = {
            f.start_batch_index: f for f in cfg.faults if f.machine_code == machine.code
        }
        tracker.start_running(clock, "Simulation started")
        previous_batch_alerted = False

        for batch_index in range(cfg.batches_per_machine):
            order_index = batch_index // cfg.batches_per_order
            if batch_index % cfg.batches_per_order == 0:
                out.orders.append(self._make_order(machine_index, machine, order_index, clock))
            product = self._product_for(machine_index, order_index)

            fault = faults_by_batch.get(batch_index)
            if fault is not None:
                clock = self._inject_fault(fault, tracker, active, clock, out)
                if fault.kind is FaultKind.DOWNTIME:
                    # The batch slot is lost to downtime; production resumes with the next one.
                    continue

            batch = self._produce_batch(machine, product, order_index, batch_index, clock, active)
            out.batches.append(batch)
            clock = batch.completed_at

            rate = defect_rate(batch.failed, batch.inspected)
            if rate >= cfg.alert_defect_rate and not previous_batch_alerted:
                out.alerts.append(
                    SimulatedAlert(
                        machine.machine_id,
                        AlertType.HIGH_DEFECT_RATE,
                        Severity.WARNING,
                        f"Batch {batch_index + 1} on {machine.code} failed {rate:.0%}"
                        " of inspections",
                        clock,
                    )
                )
            previous_batch_alerted = rate >= cfg.alert_defect_rate

        # A machine with an unresolved fault stays in WARNING so the dashboard
        # reflects it; a healthy machine returns to IDLE.
        if tracker.status is MachineStatus.RUNNING:
            tracker.transition(MachineStatus.IDLE, clock, "Simulation finished")
        out.state_changes.extend(tracker.history)
        out.final_states[machine.machine_id] = tracker.status

    def _make_order(
        self, machine_index: int, machine: MachineRef, order_index: int, at: datetime
    ) -> SimulatedOrder:
        cfg = self._config
        remaining = cfg.batches_per_machine - order_index * cfg.batches_per_order
        batches_in_order = min(cfg.batches_per_order, remaining)
        product = self._product_for(machine_index, order_index)
        return SimulatedOrder(
            order_index=order_index,
            machine_id=machine.machine_id,
            product_id=product.product_id,
            quantity_planned=batches_in_order * cfg.units_per_batch,
            created_at=at,
            due_date=at + timedelta(minutes=cfg.minutes_per_batch * batches_in_order + 60),
        )

    def _product_for(self, machine_index: int, order_index: int) -> ProductRef:
        """Each machine is dedicated to one product, as in a real cell layout.

        When there are more products than machines the remaining products
        rotate through the machines order by order.
        """
        products = self._catalog.products
        extra = (
            order_index * len(self._catalog.machines)
            if len(products) > len(self._catalog.machines)
            else 0
        )
        return products[(machine_index + extra) % len(products)]

    def _inject_fault(
        self,
        fault: FaultScenario,
        tracker: MachineStateTracker,
        active: list[ActiveFault],
        clock: datetime,
        out: SimulationOutput,
    ) -> datetime:
        severity = Severity.CRITICAL if fault.kind is FaultKind.DOWNTIME else Severity.WARNING
        out.fault_events.append(
            FaultEvent(
                tracker.machine_id,
                _FAULT_EVENT_TYPES[fault.kind],
                severity,
                _FAULT_DESCRIPTIONS[fault.kind],
                clock,
            )
        )
        if fault.kind is FaultKind.DOWNTIME:
            tracker.transition(MachineStatus.FAULT, clock, "Unplanned downtime")
            out.alerts.append(
                SimulatedAlert(
                    tracker.machine_id,
                    AlertType.MACHINE_FAULT,
                    Severity.CRITICAL,
                    f"{tracker.code} entered FAULT during simulated downtime",
                    clock,
                )
            )
            clock += timedelta(minutes=self._config.minutes_per_batch)
            tracker.transition(MachineStatus.STOPPED, clock, "Fault acknowledged")
            tracker.transition(MachineStatus.IDLE, clock, "Reset after downtime")
            tracker.transition(MachineStatus.RUNNING, clock, "Production resumed")
            if active:
                tracker.transition(
                    MachineStatus.WARNING, clock, "Earlier fault still active after restart"
                )
            return clock
        if tracker.status is MachineStatus.RUNNING:
            tracker.transition(MachineStatus.WARNING, clock, _FAULT_DESCRIPTIONS[fault.kind])
        active.append(ActiveFault(fault.kind))
        return clock

    def _produce_batch(
        self,
        machine: MachineRef,
        product: ProductRef,
        order_index: int,
        batch_index: int,
        started_at: datetime,
        active: list[ActiveFault],
    ) -> SimulatedBatch:
        cfg = self._config
        step = timedelta(minutes=cfg.minutes_per_batch) / cfg.units_per_batch
        units = []
        for seq in range(1, cfg.units_per_batch + 1):
            produced_at = started_at + step * seq
            inspections = tuple(
                self._inspect(spec, is_primary=(idx == 0), active=active, at=produced_at)
                for idx, spec in enumerate(product.specs)
            )
            units.append(SimulatedUnit(seq, produced_at, inspections))
            for fault in active:
                fault.advance()
        lots = product.material_lot_ids
        # Consecutive batches share a lot so that traceability has something to find.
        lot_ids: tuple[int, ...] = (lots[(batch_index // 2) % len(lots)],)
        if len(lots) > 1 and batch_index % 3 == 2:
            lot_ids = (*lot_ids, lots[(batch_index // 2 + 1) % len(lots)])
        return SimulatedBatch(
            machine_id=machine.machine_id,
            order_index=order_index,
            batch_index=batch_index,
            material_lot_ids=tuple(dict.fromkeys(lot_ids)),
            started_at=started_at,
            completed_at=started_at + timedelta(minutes=cfg.minutes_per_batch),
            units=tuple(units),
        )

    def _inspect(
        self, spec: SpecRef, *, is_primary: bool, active: list[ActiveFault], at: datetime
    ) -> SimulatedInspection:
        effect = combined_effect(active, primary_characteristic=is_primary)
        measured, gross = self._measure.generate(spec, effect)
        evaluation = evaluate_measurement(
            measured=measured,
            target=spec.target,
            tolerance=spec.tolerance,
            characteristic=spec.characteristic,
        )
        codes: tuple[str, ...] = ()
        if evaluation.result is InspectionResult.FAIL:
            codes = (evaluation.defect_code,) if evaluation.defect_code else ()
            if gross:
                codes = (*codes, DEFECT_SURFACE)
        return SimulatedInspection(spec.specification_id, measured, evaluation.result, codes, at)
