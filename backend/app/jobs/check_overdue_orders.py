"""Overdue order check.

    uv run python -m app.jobs.check_overdue_orders
    uv run python -m app.jobs.check_overdue_orders --as-of 2026-11-07T08:00:00

Raises one ORDER_OVERDUE alert per open order past its due date that has no
open overdue alert yet (see ``alert_service.raise_overdue_order_alerts``) and
logs the counts as one JSON line.

Exit codes:

* 0: the check committed; the log line carries ``checked``, ``raised``, and
  ``alert_ids``.
* 1: the check failed; the transaction was rolled back, nothing was written,
  and the error with its traceback is logged under
  ``operation=check_overdue_orders``.

``--as-of`` exists for replaying a past check (and for tests); the HTTP
endpoint always uses the server clock.
"""

import argparse
import json
import logging
import sys
from datetime import datetime

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.services import alert_service

logger = logging.getLogger("jobs.check_overdue_orders")
OPERATION = {"operation": "check_overdue_orders"}


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Raise ORDER_OVERDUE alerts for late orders")
    parser.add_argument(
        "--as-of",
        type=datetime.fromisoformat,
        default=None,
        help=(
            "ISO 8601 moment to judge due dates against and to stamp on new alerts "
            "(default: now). Exists for replaying a past check."
        ),
    )
    return parser.parse_args(argv)


def run_check(as_of: datetime | None) -> dict[str, object]:
    """Run one check in its own transaction and return the counts to log."""
    with SessionLocal() as session:
        try:
            result = alert_service.raise_overdue_order_alerts(session, as_of=as_of)
            session.commit()
        except Exception:
            session.rollback()
            raise
    return {
        "checked": result.checked,
        "raised": result.raised,
        "alert_ids": [alert.id for alert in result.alerts],
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(get_settings().log_level)
    try:
        counts = run_check(args.as_of)
    except Exception:
        logger.exception("overdue order check failed; nothing was written", extra=OPERATION)
        return 1
    logger.info("overdue order check finished: %s", json.dumps(counts), extra=OPERATION)
    return 0


if __name__ == "__main__":
    sys.exit(main())
