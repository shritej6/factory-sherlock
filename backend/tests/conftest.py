"""Shared fixtures.

APP_ENV is forced to "test" before any application module is imported so the
cached settings point at the ``factory_sherlock_test`` schema. Database tests
(marked ``integration``) migrate that schema once per session and truncate
every table before each test, so tests never depend on one another.
"""

import os

os.environ["APP_ENV"] = "test"

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.seed import apply_reference_sql, ensure_demo_users
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_PASSWORD = "test-password-123"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Everything under tests/api and tests/integration needs MySQL."""
    for item in items:
        path = str(item.fspath)
        if "/tests/api/" in path or "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def migrated_database() -> None:
    assert get_settings().effective_database.endswith("_test"), "refusing to run on non-test DB"
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")


@pytest.fixture
def db_session(migrated_database: None) -> Iterator[Session]:
    """Clean schema plus reference data and demo users for each test."""
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"TRUNCATE TABLE `{table.name}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    with SessionLocal() as session:
        apply_reference_sql(session)
        ensure_demo_users(session, TEST_PASSWORD)
        session.commit()
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client(db_session: Session) -> TestClient:
    return TestClient(app)


def _login(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def engineer(client: TestClient) -> dict[str, str]:
    return _login(client, "engineer")


@pytest.fixture
def operator(client: TestClient) -> dict[str, str]:
    return _login(client, "operator")


@pytest.fixture
def viewer(client: TestClient) -> dict[str, str]:
    return _login(client, "viewer")


@pytest.fixture
def ids(client: TestClient, engineer: dict[str, str]) -> dict[str, dict[str, int]]:
    """Look up reference ids by code so tests never hardcode auto-increment values."""
    return {
        "machines": {
            m["code"]: m["id"] for m in client.get("/api/v1/machines", headers=engineer).json()
        },
        "products": {
            p["code"]: p["id"] for p in client.get("/api/v1/products", headers=engineer).json()
        },
        "lots": {
            m["lot_number"]: m["id"]
            for m in client.get("/api/v1/material-lots", headers=engineer).json()
        },
    }


@pytest.fixture
def simulated(client: TestClient, engineer: dict[str, str]) -> dict[str, object]:
    """Persist the small deterministic scenario used by investigation and query tests."""
    body = {
        "seed": 7,
        "start_time": "2026-11-02T06:00:00",
        "batches_per_machine": 8,
        "units_per_batch": 30,
        "minutes_per_batch": 30,
        "faults": [{"machine_code": "CNC-03", "fault": "TOOL_WEAR", "start_batch_index": 2}],
    }
    response = client.post("/api/v1/simulation/runs", json=body, headers=engineer)
    assert response.status_code == 201, response.text
    return response.json()
