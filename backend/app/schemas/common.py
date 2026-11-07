from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from app.repositories.pagination import PageParams, PageResult


class ApiModel(BaseModel):
    """Base for response models: reads ORM attributes and forbids unknown fields on input."""

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Shape of every error body produced by ``app.api.errors``."""

    error: str
    message: str
    details: dict[str, object] = {}
    request_id: str


class Page[T](BaseModel):
    """Envelope for paginated list endpoints.

    ``total`` counts every row matching the filters, ignoring ``limit`` and
    ``offset``, so clients can compute page numbers without a second request.
    """

    items: list[T]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_result[S](
        cls, result: PageResult[S], paging: PageParams, convert: Callable[[S], T]
    ) -> "Page[T]":
        return cls(
            items=[convert(item) for item in result.items],
            total=result.total,
            limit=paging.limit,
            offset=paging.offset,
        )
