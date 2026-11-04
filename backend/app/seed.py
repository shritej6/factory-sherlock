"""Seed command.

    uv run python -m app.seed            # reference data + demo accounts
    uv run python -m app.seed --demo     # also run the default simulation scenario

Reference rows come from database/seeds/01_reference_data.sql so the SQL the
instructor reads is the SQL that actually runs. Demo accounts get the password
from SEED_DEMO_PASSWORD; the command refuses to run without it.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.models import User, UserRole
from app.schemas.simulation import SimulationRequest
from app.services import simulation_service

SEEDS_DIR = Path(__file__).resolve().parents[2] / "database" / "seeds"
DEMO_ACCOUNTS = (
    ("admin", "admin@example.com", UserRole.ADMIN),
    ("engineer", "engineer@example.com", UserRole.ENGINEER),
    ("operator", "operator@example.com", UserRole.OPERATOR),
    ("viewer", "viewer@example.com", UserRole.VIEWER),
)
logger = logging.getLogger("seed")


def apply_reference_sql(session: Session) -> None:
    raw = (SEEDS_DIR / "01_reference_data.sql").read_text(encoding="utf-8")
    # Drop comment lines first so a statement that follows a comment block is kept.
    sql = "\n".join(line for line in raw.splitlines() if not line.lstrip().startswith("--"))
    for statement in (s.strip() for s in sql.split(";")):
        if statement:
            session.execute(text(statement))
    logger.info("reference data applied", extra={"operation": "seed"})


def ensure_demo_users(session: Session, password: str) -> None:
    for username, email, role in DEMO_ACCOUNTS:
        existing = session.scalar(select(User).where(User.username == username))
        if existing is None:
            session.add(
                User(
                    username=username, email=email, role=role, password_hash=hash_password(password)
                )
            )
        else:
            existing.password_hash = hash_password(password)
    logger.info("demo accounts ready", extra={"operation": "seed"})


def run_demo_scenario(session: Session) -> None:
    payload = json.loads((SEEDS_DIR / "demo_scenario.json").read_text(encoding="utf-8"))
    payload.pop("description", None)
    result = simulation_service.run_simulation(session, SimulationRequest(**payload))
    logger.info(
        "demo scenario persisted: %s", result.model_dump_json(), extra={"operation": "seed"}
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the Factory Sherlock database")
    parser.add_argument("--demo", action="store_true", help="also run the default simulation")
    args = parser.parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)
    if not settings.seed_demo_password:
        print("SEED_DEMO_PASSWORD is not set; refusing to create accounts", file=sys.stderr)
        return 2
    with SessionLocal() as session:
        try:
            apply_reference_sql(session)
            ensure_demo_users(session, settings.seed_demo_password)
            if args.demo:
                run_demo_scenario(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
