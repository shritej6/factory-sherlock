import pytest
from app.core.exceptions import InvalidTransitionError
from app.domain.state_machines import (
    MACHINE_TRANSITIONS,
    ORDER_TRANSITIONS,
    assert_transition,
)
from app.models.enums import MachineStatus, OrderStatus


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
