from datetime import UTC, date, datetime

import pytest
from app.models.enums import OrderStatus, Severity
from app.services.alert_service import (
    CRITICAL_AFTER_DAYS,
    OPEN_ORDER_STATES,
    days_late,
    overdue_message,
    overdue_severity,
)

CHECK = datetime(2026, 11, 7, 8, 30)


@pytest.mark.parametrize(
    ("due", "expected"),
    [
        (date(2026, 11, 7), 0),  # due today: not late until tomorrow
        (date(2026, 11, 8), -1),
        (date(2026, 11, 6), 1),
        (date(2026, 10, 31), 7),
    ],
)
def test_days_late_counts_whole_calendar_days(due: date, expected: int) -> None:
    assert days_late(due, CHECK) == expected


def test_days_late_ignores_the_time_of_day() -> None:
    late_evening = datetime(2026, 11, 7, 23, 59, 59)
    early_morning = datetime(2026, 11, 7, 0, 0, 0)
    assert days_late(date(2026, 11, 6), late_evening) == days_late(date(2026, 11, 6), early_morning)
    aware = datetime(2026, 11, 7, 8, 30, tzinfo=UTC)
    assert days_late(date(2026, 11, 6), aware) == 1


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (1, Severity.WARNING),
        (CRITICAL_AFTER_DAYS, Severity.WARNING),
        (CRITICAL_AFTER_DAYS + 1, Severity.CRITICAL),
        (30, Severity.CRITICAL),
    ],
)
def test_severity_is_warning_then_critical(days: int, expected: Severity) -> None:
    assert overdue_severity(days) is expected


def test_message_names_order_due_date_and_days_late() -> None:
    assert (
        overdue_message("PO-1001", date(2026, 11, 6), 1)
        == "Order PO-1001 is 1 day overdue (due 2026-11-06)"
    )
    assert (
        overdue_message("PO-1001", date(2026, 11, 1), 6)
        == "Order PO-1001 is 6 days overdue (due 2026-11-01)"
    )
    assert len(overdue_message("A" * 30, date(2026, 1, 1), 10**6)) <= 255


def test_terminal_order_states_are_never_overdue() -> None:
    assert OrderStatus.COMPLETED not in OPEN_ORDER_STATES
    assert OrderStatus.CANCELLED not in OPEN_ORDER_STATES
    assert {
        OrderStatus.PLANNED,
        OrderStatus.RELEASED,
        OrderStatus.IN_PROGRESS,
    } == OPEN_ORDER_STATES
