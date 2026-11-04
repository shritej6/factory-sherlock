"""State machines for machines and production orders.

The transition tables are the authoritative definition of the business rules
"a cancelled order cannot start production", "a completed order cannot be
reopened", and "a machine in FAULT must be stopped before it can run again".
They are plain data so they can be unit tested without a database and shown
in documentation without paraphrasing.
"""

from app.core.exceptions import InvalidTransitionError
from app.models.enums import BatchStatus, InvestigationStatus, MachineStatus, OrderStatus

MACHINE_TRANSITIONS: dict[MachineStatus, frozenset[MachineStatus]] = {
    MachineStatus.IDLE: frozenset({MachineStatus.RUNNING, MachineStatus.STOPPED}),
    MachineStatus.RUNNING: frozenset(
        {MachineStatus.WARNING, MachineStatus.STOPPED, MachineStatus.FAULT, MachineStatus.IDLE}
    ),
    MachineStatus.WARNING: frozenset(
        {MachineStatus.RUNNING, MachineStatus.STOPPED, MachineStatus.FAULT}
    ),
    # A fault must be acknowledged by stopping the machine; it cannot jump back to RUNNING.
    MachineStatus.FAULT: frozenset({MachineStatus.STOPPED}),
    MachineStatus.STOPPED: frozenset({MachineStatus.IDLE}),
}

ORDER_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PLANNED: frozenset({OrderStatus.RELEASED, OrderStatus.CANCELLED}),
    OrderStatus.RELEASED: frozenset({OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED}),
    OrderStatus.IN_PROGRESS: frozenset({OrderStatus.COMPLETED, OrderStatus.CANCELLED}),
    # Terminal states.
    OrderStatus.COMPLETED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

BATCH_TRANSITIONS: dict[BatchStatus, frozenset[BatchStatus]] = {
    BatchStatus.IN_PROGRESS: frozenset({BatchStatus.COMPLETED, BatchStatus.QUARANTINED}),
    BatchStatus.COMPLETED: frozenset({BatchStatus.QUARANTINED}),
    # Quarantine is terminal. Material that passes re-inspection is released by
    # creating a new batch so that the quarantine record and its reason survive.
    BatchStatus.QUARANTINED: frozenset(),
}

INVESTIGATION_TRANSITIONS: dict[InvestigationStatus, frozenset[InvestigationStatus]] = {
    InvestigationStatus.OPEN: frozenset(
        {InvestigationStatus.IN_REVIEW, InvestigationStatus.CLOSED}
    ),
    InvestigationStatus.IN_REVIEW: frozenset(
        {InvestigationStatus.CLOSED, InvestigationStatus.OPEN}
    ),
    InvestigationStatus.CLOSED: frozenset(),
}


def assert_transition[S](
    table: dict[S, frozenset[S]], current: S, target: S, *, entity: str
) -> None:
    """Raise ``InvalidTransitionError`` unless ``current -> target`` is allowed."""
    allowed = table.get(current, frozenset())
    if target not in allowed:
        raise InvalidTransitionError(
            f"{entity} cannot move from {current} to {target}",
            details={
                "current": str(current),
                "target": str(target),
                "allowed": sorted(map(str, allowed)),
            },
        )
