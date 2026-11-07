"""The driver-error table in app.api.errors, exercised with pymysql-style errors."""

import logging

import pymysql
import pytest
from app.api.errors import (
    ErrorMapping,
    classify_data,
    classify_integrity,
    classify_operational,
    mysql_error_code,
)
from sqlalchemy.exc import DataError, IntegrityError, OperationalError, TimeoutError

STATEMENT = "INSERT INTO inspections (unit_id) VALUES (1)"


def _operational(code: int, message: str = "driver text") -> OperationalError:
    return OperationalError(STATEMENT, {}, pymysql.err.OperationalError(code, message))


def _data(code: int, message: str = "driver text") -> DataError:
    return DataError(STATEMENT, {}, pymysql.err.DataError(code, message))


def _integrity(code: int, message: str = "driver text") -> IntegrityError:
    return IntegrityError(STATEMENT, {}, pymysql.err.IntegrityError(code, message))


def test_check_constraint_violation_is_a_422_naming_the_constraint() -> None:
    exc = _operational(3819, "Check constraint 'chk_inspections_measured' is violated.")
    mapping = classify_operational(exc)
    assert mapping == ErrorMapping(
        422,
        "ValidationError",
        "A database check constraint rejected the change",
        {"constraint": "chk_inspections_measured"},
        logging.WARNING,
        "check constraint violation",
    )


def test_check_constraint_violation_without_a_parseable_name_has_empty_details() -> None:
    mapping = classify_operational(_operational(3819, "constraint failed"))
    assert (mapping.status, mapping.details) == (422, {})


@pytest.mark.parametrize("code", [2002, 2003, 2006, 2013])
def test_connection_errors_are_503_not_reachable(code: int) -> None:
    mapping = classify_operational(_operational(code, "Can't connect to MySQL server"))
    assert (mapping.status, mapping.error) == (503, "DatabaseUnavailable")
    assert mapping.message == "The database is not reachable"
    assert mapping.details == {}


def test_pool_timeout_is_503_not_reachable() -> None:
    mapping = classify_operational(TimeoutError("QueuePool limit reached"))
    assert (mapping.status, mapping.message) == (503, "The database is not reachable")


@pytest.mark.parametrize("code", [1040, 1129, 1226, 3024])
def test_other_operational_errors_are_503_unavailable(code: int) -> None:
    mapping = classify_operational(_operational(code))
    assert (mapping.status, mapping.error) == (503, "DatabaseUnavailable")
    assert mapping.message == "The database is unavailable"


@pytest.mark.parametrize("code", [1205, 1213])
def test_lock_contention_stays_a_retryable_409(code: int) -> None:
    mapping = classify_operational(_operational(code, "Deadlock found"))
    assert (mapping.status, mapping.error) == (409, "ConflictError")


def test_data_too_long_is_a_422() -> None:
    mapping = classify_data(_data(1406, "Data too long for column 'serial_number' at row 1"))
    assert (mapping.status, mapping.error) == (422, "ValidationError")
    assert mapping.message == "A value is too long for its column"
    assert mapping.log_level == logging.WARNING


@pytest.mark.parametrize("code", [1264, 1292, 1366])
def test_other_data_errors_are_generic_500s(code: int) -> None:
    mapping = classify_data(_data(code))
    assert (mapping.status, mapping.error) == (500, "InternalError")
    assert mapping.message == "An unexpected error occurred"
    assert mapping.log_level == logging.ERROR


def test_integrity_table_is_unchanged() -> None:
    assert classify_integrity(_integrity(1062)).status == 409
    assert classify_integrity(_integrity(1452)).status == 422
    assert classify_integrity(_integrity(1048)).status == 500


def test_error_code_is_read_only_from_an_integer_first_argument() -> None:
    assert mysql_error_code(_operational(2013)) == 2013
    assert mysql_error_code(OperationalError(STATEMENT, {}, RuntimeError("no args"))) is None
    assert mysql_error_code(TimeoutError("pool")) is None
