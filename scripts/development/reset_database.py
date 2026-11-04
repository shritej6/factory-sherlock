#!/usr/bin/env python3
"""Drops every table in the configured database and rebuilds it from migrations.

    cd backend && uv run python ../scripts/development/reset_database.py [--demo]

Use APP_ENV=test to reset the test database instead. Foreign key checks are
disabled during the drop so table order does not matter. This never touches
users, privileges, or other schemas.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from sqlalchemy import MetaData, create_engine, text

from app.core.config import get_settings

BACKEND = Path(__file__).resolve().parents[2] / "backend"


def drop_all_tables() -> int:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in metadata.tables.values():
            conn.execute(text(f"DROP TABLE IF EXISTS `{table.name}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    return len(metadata.tables)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="seed reference data and demo scenario")
    args = parser.parse_args()
    settings = get_settings()
    dropped = drop_all_tables()
    print(f"dropped {dropped} tables from {settings.effective_database}")
    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], cwd=BACKEND, check=True)
    seed_cmd = ["uv", "run", "python", "-m", "app.seed"] + (["--demo"] if args.demo else [])
    subprocess.run(seed_cmd, cwd=BACKEND, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
