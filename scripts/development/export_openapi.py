#!/usr/bin/env python3
"""Writes the OpenAPI document to docs/api/openapi.json.

Run from the backend directory: uv run python ../scripts/development/export_openapi.py
The file is generated; edit the FastAPI routes and schemas, not the JSON.
"""

import json
from pathlib import Path

from app.main import app

target = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.json"
target.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"wrote {target} ({len(app.openapi()['paths'])} paths)")
