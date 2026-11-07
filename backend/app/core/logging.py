"""Structured logging configuration.

Logs are emitted as single-line JSON so they can be shipped to any log
aggregator later. Passwords and tokens never reach the logger because the
settings object marks those fields ``repr=False`` and handlers log only
identifiers, never request bodies.
"""

import json
import logging
import sys
from datetime import UTC, datetime

# Only these ``extra`` fields reach the output. Anything else attached to a
# record is dropped, so a stray request body or header can never be logged.
LOGGED_FIELDS = (
    "request_id",
    "user_id",
    "operation",
    "error",
    "status",
    "retry_after_seconds",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in LOGGED_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # uvicorn installs its own handlers; route them through the JSON formatter too.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).handlers = [handler]
