"""Offset pagination for ORM list queries.

List endpoints over growing tables (orders, batches, inspections, events,
alerts, investigations) return one page at a time. The count runs as a
separate statement over the same filters so ``total`` is independent of the
requested window, and the ordering must end in a unique column so pages do
not overlap or skip rows.
"""

from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class PageParams:
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class PageResult[T]:
    items: list[T]
    total: int


def paginate[T](session: Session, stmt: Select[T], paging: PageParams) -> PageResult[T]:
    """Run ``stmt`` twice: once for the total count and once for the requested window."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.scalar(count_stmt) or 0
    items = list(session.scalars(stmt.limit(paging.limit).offset(paging.offset)))
    return PageResult(items=items, total=total)
