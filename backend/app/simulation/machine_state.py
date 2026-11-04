"""In-memory machine state tracker that obeys the shared transition table."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

from app.domain.state_machines import MACHINE_TRANSITIONS, assert_transition
from app.models.enums import MachineStatus
from app.simulation.events import StateChange


@dataclass
class MachineStateTracker:
    machine_id: int
    code: str
    status: MachineStatus = MachineStatus.IDLE
    history: list[StateChange] = field(default_factory=list)

    # Legal path back to RUNNING from every state, so a simulation can start on a
    # machine that was left stopped or faulted without bypassing the state machine.
    _RESTART_PATH: ClassVar[dict[MachineStatus, tuple[MachineStatus, ...]]] = {
        MachineStatus.FAULT: (MachineStatus.STOPPED, MachineStatus.IDLE, MachineStatus.RUNNING),
        MachineStatus.STOPPED: (MachineStatus.IDLE, MachineStatus.RUNNING),
        MachineStatus.IDLE: (MachineStatus.RUNNING,),
        MachineStatus.WARNING: (MachineStatus.RUNNING,),
        MachineStatus.RUNNING: (),
    }

    def start_running(self, at: datetime, reason: str) -> None:
        for target in self._RESTART_PATH[self.status]:
            self.transition(target, at, reason)

    def transition(self, target: MachineStatus, at: datetime, reason: str) -> None:
        assert_transition(MACHINE_TRANSITIONS, self.status, target, entity=f"Machine {self.code}")
        self.history.append(StateChange(self.machine_id, self.status, target, at, reason))
        self.status = target
