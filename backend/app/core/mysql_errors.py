"""Read the MySQL error number out of a wrapped SQLAlchemy driver error.

pymysql attaches ``(errno, message)`` to the original exception; SQLAlchemy
keeps that object on ``exc.orig``. Services and the API error handlers both
need the number to tell a duplicate key apart from every other integrity
failure, so the helper lives here rather than in either layer.
"""

from __future__ import annotations

MYSQL_DUPLICATE_KEY = 1062


def driver_args(exc: Exception) -> tuple[object, ...]:
    """The (errno, message) pair pymysql attaches to the wrapped driver error."""
    orig = getattr(exc, "orig", None)
    args = getattr(orig, "args", ())
    return tuple(args) if isinstance(args, tuple) else ()


def mysql_error_code(exc: Exception) -> int | None:
    args = driver_args(exc)
    return args[0] if args and isinstance(args[0], int) else None
