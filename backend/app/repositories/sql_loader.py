"""Loads the SQL files under database/queries so the backend runs the exact
text that the documentation describes and that the investigation case board
shows to users.

Files are keyed by their stem without the numeric prefix, for example
``01_machine_defect_rate_comparison.sql`` becomes ``machine_defect_rate_comparison``
and ``investigation/defect_onset.sql`` becomes ``investigation.defect_onset``.
"""

import re
from functools import lru_cache
from pathlib import Path

from sqlalchemy import TextClause, bindparam, text

from app.core.exceptions import NotFoundError

QUERIES_DIR = Path(__file__).resolve().parents[3] / "database" / "queries"
_PREFIX = re.compile(r"^\d+_")


class UnknownQueryError(NotFoundError):
    """Raised when no SQL file matches the requested query name."""


@lru_cache
def _catalog() -> dict[str, str]:
    catalog: dict[str, str] = {}
    for path in sorted(QUERIES_DIR.rglob("*.sql")):
        stem = _PREFIX.sub("", path.stem)
        relative = path.relative_to(QUERIES_DIR)
        key = ".".join([*relative.parts[:-1], stem])
        catalog[key] = path.read_text(encoding="utf-8")
    return catalog


def query_names() -> list[str]:
    return sorted(_catalog())


def load_sql(name: str) -> str:
    """Return the raw SQL text including its documentation header."""
    try:
        return _catalog()[name]
    except KeyError as exc:
        raise UnknownQueryError(name) from exc


def load_query(name: str, *, expanding: tuple[str, ...] = ()) -> TextClause:
    """Return an executable text clause.

    ``expanding`` names list-valued parameters that should be rendered as
    ``IN (?, ?, ...)``; SQLAlchemy needs to know about them up front.
    """
    clause = text(load_sql(name))
    if expanding:
        clause = clause.bindparams(*[bindparam(p, expanding=True) for p in expanding])
    return clause
