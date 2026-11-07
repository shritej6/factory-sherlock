import json
import logging
import sys

from app.core.logging import LOGGED_FIELDS, JsonFormatter


def _format(**extra: object) -> dict[str, object]:
    record = logging.LogRecord(
        "app.test", logging.WARNING, __file__, 1, "login throttled", (), None
    )
    for key, value in extra.items():
        setattr(record, key, value)
    payload = json.loads(JsonFormatter().format(record))
    assert isinstance(payload, dict)
    return payload


def test_allowlisted_fields_reach_the_output() -> None:
    payload = _format(
        request_id="abc123",
        user_id=4,
        operation="login",
        error="RateLimitedError",
        status=429,
        retry_after_seconds=900,
    )
    assert payload["message"] == "login throttled"
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "app.test"
    for key in LOGGED_FIELDS:
        assert key in payload, key
    assert payload["status"] == 429
    assert payload["error"] == "RateLimitedError"
    assert payload["retry_after_seconds"] == 900


def test_fields_outside_the_allowlist_are_dropped() -> None:
    payload = _format(operation="login", password="hunter2", username="admin", body={"x": 1})
    assert payload["operation"] == "login"
    for key in ("password", "username", "body"):
        assert key not in payload
    assert set(payload) == {"timestamp", "level", "logger", "message", "operation"}


def test_none_values_are_omitted_and_exceptions_are_rendered() -> None:
    record = logging.LogRecord("app.test", logging.ERROR, __file__, 1, "boom", (), None)
    record.request_id = None
    try:
        raise ValueError("secret-detail")
    except ValueError:
        record.exc_info = sys.exc_info()
    payload = json.loads(JsonFormatter().format(record))
    assert "request_id" not in payload
    assert "ValueError: secret-detail" in payload["exception"]
