import pytest
from app.core.exceptions import InvalidTransitionError
from app.domain.state_machines import (
    BATCH_TRANSITIONS,
    INVESTIGATION_TRANSITIONS,
    MACHINE_TRANSITIONS,
    ORDER_TRANSITIONS,
    assert_transition,
)
from app.models.enums import BatchStatus, InvestigationStatus, MachineStatus, OrderStatus

ALL_MACHINE_EDGES = [(c, t) for c in MachineStatus for t in MachineStatus]
ALL_ORDER_EDGES = [(c, t) for c in OrderStatus for t in OrderStatus]
ALL_BATCH_EDGES = [(c, t) for c in BatchStatus for t in BatchStatus]
ALL_INVESTIGATION_EDGES = [(c, t) for c in InvestigationStatus for t in InvestigationStatus]

# The tables as written in docs/requirements/business-rules.md (BR-20, BR-34, BR-56, BR-74).
DOCUMENTED_MACHINE_EDGES = {
    MachineStatus.IDLE: {MachineStatus.RUNNING, MachineStatus.STOPPED},
    MachineStatus.RUNNING: {
        MachineStatus.WARNING,
        MachineStatus.STOPPED,
        MachineStatus.FAULT,
        MachineStatus.IDLE,
    },
    MachineStatus.WARNING: {MachineStatus.RUNNING, MachineStatus.STOPPED, MachineStatus.FAULT},
    MachineStatus.FAULT: {MachineStatus.STOPPED},
    MachineStatus.STOPPED: {MachineStatus.IDLE},
}
DOCUMENTED_ORDER_EDGES = {
    OrderStatus.PLANNED: {OrderStatus.RELEASED, OrderStatus.CANCELLED},
    OrderStatus.RELEASED: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED},
    OrderStatus.IN_PROGRESS: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}
DOCUMENTED_BATCH_EDGES = {
    BatchStatus.IN_PROGRESS: {BatchStatus.COMPLETED, BatchStatus.QUARANTINED},
    BatchStatus.COMPLETED: {BatchStatus.QUARANTINED},
    BatchStatus.QUARANTINED: set(),
}
DOCUMENTED_INVESTIGATION_EDGES = {
    InvestigationStatus.OPEN: {InvestigationStatus.IN_REVIEW, InvestigationStatus.CLOSED},
    InvestigationStatus.IN_REVIEW: {InvestigationStatus.CLOSED, InvestigationStatus.OPEN},
    InvestigationStatus.CLOSED: set(),
}


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (OrderStatus.PLANNED, OrderStatus.RELEASED),
        (OrderStatus.RELEASED, OrderStatus.IN_PROGRESS),
        (OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED),
        (OrderStatus.PLANNED, OrderStatus.CANCELLED),
    ],
)
def test_legal_order_transitions(current: OrderStatus, target: OrderStatus) -> None:
    assert_transition(ORDER_TRANSITIONS, current, target, entity="Order")


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (OrderStatus.CANCELLED, OrderStatus.IN_PROGRESS),  # cancelled orders cannot start
        (OrderStatus.COMPLETED, OrderStatus.IN_PROGRESS),  # completed orders are terminal
        (OrderStatus.PLANNED, OrderStatus.COMPLETED),  # cannot skip production
        (OrderStatus.PLANNED, OrderStatus.PLANNED),  # no self transitions
    ],
)
def test_illegal_order_transitions_are_rejected(current: OrderStatus, target: OrderStatus) -> None:
    with pytest.raises(InvalidTransitionError) as exc:
        assert_transition(ORDER_TRANSITIONS, current, target, entity="Order")
    assert exc.value.details["current"] == str(current)
    assert "allowed" in exc.value.details


def test_fault_must_go_through_stopped() -> None:
    assert MACHINE_TRANSITIONS[MachineStatus.FAULT] == frozenset({MachineStatus.STOPPED})
    with pytest.raises(InvalidTransitionError):
        assert_transition(
            MACHINE_TRANSITIONS, MachineStatus.FAULT, MachineStatus.RUNNING, entity="M"
        )


def test_every_machine_state_has_a_row() -> None:
    assert set(MACHINE_TRANSITIONS) == set(MachineStatus)
    assert set(ORDER_TRANSITIONS) == set(OrderStatus)
    assert set(BATCH_TRANSITIONS) == set(BatchStatus)
    assert set(INVESTIGATION_TRANSITIONS) == set(InvestigationStatus)


def _check_edge[S](table: dict[S, frozenset[S]], current: S, target: S, *, allowed: bool) -> None:
    if allowed:
        assert_transition(table, current, target, entity="E")
        return
    with pytest.raises(InvalidTransitionError) as exc:
        assert_transition(table, current, target, entity="E")
    assert exc.value.status_code == 422
    assert exc.value.details == {
        "current": str(current),
        "target": str(target),
        "allowed": sorted(map(str, table[current])),
    }


@pytest.mark.parametrize(("current", "target"), ALL_MACHINE_EDGES)
def test_every_machine_edge_matches_the_documented_table(
    current: MachineStatus, target: MachineStatus
) -> None:
    allowed = target in DOCUMENTED_MACHINE_EDGES[current]
    _check_edge(MACHINE_TRANSITIONS, current, target, allowed=allowed)


@pytest.mark.parametrize(("current", "target"), ALL_ORDER_EDGES)
def test_every_order_edge_matches_the_documented_table(
    current: OrderStatus, target: OrderStatus
) -> None:
    allowed = target in DOCUMENTED_ORDER_EDGES[current]
    _check_edge(ORDER_TRANSITIONS, current, target, allowed=allowed)


@pytest.mark.parametrize(("current", "target"), ALL_BATCH_EDGES)
def test_every_batch_edge_matches_the_documented_table(
    current: BatchStatus, target: BatchStatus
) -> None:
    allowed = target in DOCUMENTED_BATCH_EDGES[current]
    _check_edge(BATCH_TRANSITIONS, current, target, allowed=allowed)


@pytest.mark.parametrize(("current", "target"), ALL_INVESTIGATION_EDGES)
def test_every_investigation_edge_matches_the_documented_table(
    current: InvestigationStatus, target: InvestigationStatus
) -> None:
    allowed = target in DOCUMENTED_INVESTIGATION_EDGES[current]
    _check_edge(INVESTIGATION_TRANSITIONS, current, target, allowed=allowed)


def test_terminal_states_reject_every_target() -> None:
    assert ORDER_TRANSITIONS[OrderStatus.COMPLETED] == frozenset()
    assert ORDER_TRANSITIONS[OrderStatus.CANCELLED] == frozenset()
    assert BATCH_TRANSITIONS[BatchStatus.QUARANTINED] == frozenset()
    assert INVESTIGATION_TRANSITIONS[InvestigationStatus.CLOSED] == frozenset()
