"""Overdue order check.

    uv run python -m app.jobs.check_overdue_orders
    uv run python -m app.jobs.check_overdue_orders --as-of 2026-11-07T08:00:00

Raises one ORDER_OVERDUE alert per open order past its due date that has no
open overdue alert yet (see ``alert_service.raise_overdue_order_alerts``), then
logs the counts as one JSON line and exits 0.
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Raise ORDER_OVERDUE alerts for late orders")
    parser.add_argument(
        "--as-of",
        type=datetime.fromisoformat,
        default=None,
        help="ISO 8601 moment to judge due dates against (default: now)",
    )
    args = parser.parse_args(argv)
    configure_logging(get_settings().log_level)
    with SessionLocal() as session:
        try:
            result = alert_service.raise_overdue_order_alerts(session, as_of=args.as_of)
            session.commit()
        except Exception:
            session.rollback()
            raise
    counts = {
        "checked": result.checked,
        "raised": result.raised,
        "alert_ids": [alert.id for alert in result.alerts],
    }
    logger.info(
        "overdue order check finished: %s",
        json.dumps(counts),
        extra={"operation": "check_overdue_orders"},
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
