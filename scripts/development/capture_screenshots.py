"""Capture the screenshots listed in docs/media/media-plan.md from the running app.

The script drives a real browser against the frontend dev server, signs in
with the demo engineer account, and saves one PNG per screen. Nothing is
synthesised: if a screen fails to load, the script exits non-zero instead of
writing a placeholder.

Prerequisites: the demo scenario is loaded (``make reset-demo``), the backend
(``make backend``) and the frontend (``make frontend``) are running, and the
Python ``playwright`` package is installed (``uv run --group docs``).

    cd backend && uv run --group docs python ../scripts/development/capture_screenshots.py

Environment: SEED_DEMO_PASSWORD (read from the repository .env), FRONTEND_URL
(default http://localhost:5173), SCREENSHOT_DIR (default docs/media/screenshots).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(os.environ.get("SCREENSHOT_DIR", REPO_ROOT / "docs" / "media" / "screenshots"))
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
VIEWPORT = {"width": 1600, "height": 1000}


def _demo_password() -> str:
    env_file = REPO_ROOT / ".env"
    for line in env_file.read_text().splitlines():
        if line.startswith("SEED_DEMO_PASSWORD="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("SEED_DEMO_PASSWORD not found in .env")


def _chrome_path() -> str | None:
    candidate = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    return str(candidate) if candidate.exists() else None


def _shot(page: Page, name: str) -> None:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(400)
    target = OUT_DIR / name
    page.screenshot(path=str(target), full_page=False)
    print(f"captured {target.relative_to(REPO_ROOT)}")


def _login(page: Page, password: str) -> None:
    page.goto(f"{FRONTEND_URL}/login")
    page.get_by_label("Username").fill("engineer")
    page.wait_for_timeout(200)
    _shot(page, "01-login.png")
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url(f"{FRONTEND_URL}/")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    password = _demo_password()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=_chrome_path())
        page = browser.new_page(viewport=VIEWPORT, color_scheme="light")
        _login(page, password)
        _shot(page, "02-overview-dashboard.png")

        page.goto(f"{FRONTEND_URL}/machines")
        page.get_by_role("button", name=re.compile("CNC-03")).first.click()
        _shot(page, "03-machines-events.png")

        page.goto(f"{FRONTEND_URL}/orders")
        _shot(page, "04-orders-and-batches.png")

        page.goto(f"{FRONTEND_URL}/quality")
        page.get_by_label("Result").select_option("FAIL")
        _shot(page, "05-quality-inspections.png")

        page.goto(f"{FRONTEND_URL}/investigations")
        page.wait_for_load_state("networkidle")
        first_case = page.locator("a[href^='/investigations/']").first
        if first_case.count() == 0:
            print("no investigation found; open one through the UI or the API first", file=sys.stderr)
            browser.close()
            return 1
        first_case.click()
        page.wait_for_load_state("networkidle")
        show_sql = page.get_by_role("button", name="Show the SQL").first
        show_sql.wait_for()
        show_sql.click()
        _shot(page, "06-investigation-case-board.png")

        page.goto(f"{FRONTEND_URL}/traceability")
        page.get_by_label("Lot number").fill("L203")
        page.get_by_role("button", name="Trace lot").click()
        page.wait_for_load_state("networkidle")
        page.get_by_label("Serial number").fill("SIM0001-CNC-03-03-B04-U0001")
        page.get_by_role("button", name="Trace unit").click()
        _shot(page, "07-traceability-and-quarantine.png")

        page.goto(f"{FRONTEND_URL}/analytics")
        _shot(page, "08-analytics-charts.png")
        page.get_by_label("Query").select_option("batches_requiring_review")
        page.get_by_role("button", name="Run query").click()
        page.wait_for_load_state("networkidle")
        page.get_by_role("heading", name="SQL Explorer").evaluate(
            "node => node.closest('section').scrollIntoView({block: 'start'})"
        )
        page.evaluate("window.scrollBy(0, -24)")
        _shot(page, "09-analytics-sql-explorer.png")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
