"""_flush_or_conflict only turns duplicate keys into 409s."""

from __future__ import annotations

import pytest
from app.core.exceptions import ConflictError
from app.services.catalog_service import _flush_or_conflict
from sqlalchemy.exc import IntegrityError


class _FailingSession:
    def __init__(self, errno: int) -> None:
        self._errno = errno

    def flush(self) -> None:
        raise IntegrityError("INSERT", {}, RuntimeError(self._errno, "driver message"))


def test_duplicate_key_becomes_a_conflict() -> None:
    with pytest.raises(ConflictError, match="Machine CNC-09 already exists"):
        _flush_or_conflict(_FailingSession(1062), "Machine CNC-09")  # type: ignore[arg-type]


def test_other_integrity_errors_are_left_to_the_api_handlers() -> None:
    with pytest.raises(IntegrityError):
        _flush_or_conflict(_FailingSession(1452), "Machine CNC-09")  # type: ignore[arg-type]
