"""Column mixins reused across models."""

from datetime import datetime

from sqlalchemy import DateTime, FetchedValue, func, text
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Insert and update timestamps maintained by MySQL.

    ``updated_at`` carries MySQL's ``ON UPDATE CURRENT_TIMESTAMP`` clause so a
    row changed by raw SQL is refreshed as well as one changed through the ORM.
    SQLAlchemy's ``server_onupdate`` does not render that clause, so it is part
    of the server default text; ``FetchedValue`` tells the ORM to reload it.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        server_onupdate=FetchedValue(),
        onupdate=func.now(),
        nullable=False,
    )
