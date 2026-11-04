"""Database engine and session management.

One engine per process, one session per request. Services receive a session
through FastAPI dependency injection and never create their own, which keeps
transaction boundaries in one place (see ``get_db_session``).
"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def build_engine() -> Engine:
    settings = get_settings()
    # pool_pre_ping detects connections closed by MySQL's wait_timeout instead of
    # failing the first query after an idle period.
    return create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Request-scoped session.

    The session is committed when the request handler returns normally and
    rolled back when it raises, so a handler that fails halfway through a
    multi-table write leaves no partial rows behind.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
