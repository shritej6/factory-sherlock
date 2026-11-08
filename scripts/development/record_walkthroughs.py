"""Record the silent walkthrough videos listed in docs/media/media-plan.md.

Each video is one Playwright browser context with ``record_video_dir`` set, driven
slowly enough for a viewer to follow, then converted to H.264 MP4 with ffmpeg. Sign-in
stores the API token in localStorage (the key ``AuthProvider`` reads), so no password
is typed on camera. Video 1 needs slides and narration and is skipped. Prerequisites:
``make reset-demo``, batch ``SIM0001-CNC-02-02-B04`` started and the sample CSV imported
(docs/quality/inspection-import.md), backend and frontend running, ``ffmpeg`` and
``ffprobe`` on PATH. The sequences write to the database, so reset the demo scenario
before recording again. Run with ``make videos``. Environment: SEED_DEMO_PASSWORD (from
the repository .env), FRONTEND_URL (default http://localhost:5173), VIDEO_DIR (default
docs/media/videos), VIDEOS (comma separated numbers to record, default 2,3,4,5,6).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Locator, Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(os.environ.get("VIDEO_DIR", REPO_ROOT / "docs" / "media" / "videos"))
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
API_URL = f"{FRONTEND_URL}/api/v1"
TOKEN_KEY = "factory-sherlock.token"
SIZE = {"width": 1280, "height": 800}
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
CNC03_WINDOW = ("2026-11-02T06:00", "2026-11-02T12:00")
SIZE_LIMIT_BYTES = 10 * 1024 * 1024
ENCODINGS = (["-crf", "28"], ["-crf", "30"], ["-crf", "30", "-r", "15"])


def _demo_password() -> str:
    for line in (REPO_ROOT / ".env").read_text().splitlines():
        if line.startswith("SEED_DEMO_PASSWORD="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("SEED_DEMO_PASSWORD not found in .env")


class Api:
    def __init__(self, password: str) -> None:
        self._password = password
        self._tokens: dict[str, str] = {}

    def token(self, account: str) -> str:
        if account not in self._tokens:
            body = {"username": account, "password": self._password}
            status, result = self.call("POST", "/auth/login", body=body)
            if status != 200:
                raise SystemExit(f"login as {account} returned {status}: {result}")
            self._tokens[account] = result["access_token"]
        return self._tokens[account]

    def call(
        self, method: str, path: str, account: str | None = None, body: Any = None
    ) -> tuple[int, Any]:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(f"{API_URL}{path}", data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if account is not None:
            request.add_header("Authorization", f"Bearer {self.token(account)}")
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, json.loads(response.read() or b"null")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"null")

    def get(self, path: str, account: str = "engineer") -> Any:
        status, result = self.call("GET", path, account)
        if status != 200:
            raise SystemExit(f"GET {path} returned {status}: {result}")
        return result

    def find_id(self, path: str, key: str, value: str) -> int:
        """Id of the first list item at ``path`` whose ``key`` equals ``value``."""
        for item in self.get(f"{path}?limit=200")["items"]:
            if item[key] == value:
                return int(item["id"])
        raise SystemExit(f"{path}: no item with {key} {value}")

    def batch_id(self, batch_number: str) -> int:
        return self.find_id("/production-batches", "batch_number", batch_number)

    def order_id(self, order_number: str) -> int:
        return self.find_id("/production-orders", "order_number", order_number)

    def first_unit_id(self, batch_id: int) -> int:
        rows = self.get(f"/inspections?batch_id={batch_id}&limit=200")["items"]
        if not rows:
            raise SystemExit(f"batch {batch_id} has no inspections to derive unit ids from")
        return min(int(row["unit_id"]) for row in rows)


def _label(text: str) -> re.Pattern[str]:
    return re.compile(rf"^{re.escape(text)}( \*)?$")


class Walk:
    """Slow, visible UI driving: every action ends in a pause so a viewer can follow."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def pause(self, seconds: float) -> None:
        self.page.wait_for_timeout(int(seconds * 1000))

    def settle(self, seconds: float = 2.0) -> None:
        self.page.wait_for_load_state("networkidle")
        self.pause(seconds)

    def go(self, nav_label: str, seconds: float = 3.0) -> None:
        self.page.get_by_role("link", name=nav_label, exact=True).click()
        self.settle(seconds)

    def click(self, locator: Locator, seconds: float = 2.0) -> None:
        locator.scroll_into_view_if_needed()
        locator.click()
        self.settle(seconds)

    def button(self, name: str, seconds: float = 2.0, exact: bool = True) -> None:
        self.click(self.page.get_by_role("button", name=name, exact=exact), seconds)

    def type(self, label: str, text: str, seconds: float = 1.0, nth: int = 0) -> None:
        field = self.page.get_by_label(_label(label)).nth(nth)
        field.click()
        field.press_sequentially(text, delay=45)
        self.pause(seconds)

    def fill(self, label: str, value: str, seconds: float = 1.0, nth: int = 0) -> None:
        self.page.get_by_label(_label(label)).nth(nth).fill(value)
        self.pause(seconds)

    def select(self, field: str, seconds: float = 1.5, nth: int = 0, **option: Any) -> None:
        self.page.get_by_label(_label(field)).nth(nth).select_option(**option)
        self.settle(seconds)

    def scroll(self, pixels: int, steps: int = 8, seconds: float = 0.3, then: float = 0) -> None:
        for _ in range(steps):
            self.page.mouse.wheel(0, pixels / steps)
            self.pause(seconds)
        self.pause(then)

    def show(self, locator: Locator, seconds: float = 3.0) -> None:
        locator.first.scroll_into_view_if_needed()
        self.pause(seconds)

    def text(self, pattern: str) -> Locator:
        return self.page.get_by_text(re.compile(pattern))


def _sign_in(browser: Browser, token: str, record_dir: Path) -> Page:
    context = browser.new_context(
        viewport=SIZE,
        color_scheme="dark",
        record_video_dir=str(record_dir),
        record_video_size=SIZE,
    )
    page = context.new_page()
    page.goto(f"{FRONTEND_URL}/login")
    page.evaluate("([key, value]) => window.localStorage.setItem(key, value)", [TOKEN_KEY, token])
    page.goto(f"{FRONTEND_URL}/")
    page.get_by_role("heading", name="Factory Overview").wait_for()
    return page


def video_02_virtual_factory(walk: Walk, api: Api) -> None:
    """Simulation request with a fault, the result, and the generated history."""
    walk.go("Simulation", 6)
    walk.fill("Seed", "7", 2)
    walk.fill("Start time", "2026-11-03T06:00", 2)
    walk.fill("Batches per machine", "6", 2)
    walk.button("Add fault", 3)
    walk.select("Machine 1", 2, label="CNC-01")
    walk.select("Fault", 2, value="CALIBRATION_DRIFT")
    walk.fill("Start batch index", "3", 3)
    walk.button("Run simulation", 1)
    walk.text(r"^Machine events$").wait_for()
    walk.settle(12)
    walk.go("Factory Overview", 8)
    walk.go("Machine Monitoring", 3)
    walk.click(walk.page.get_by_role("button", name=re.compile("CNC-01")).first, 6)
    walk.show(walk.page.get_by_role("list", name="Machine events"), 8)
    walk.go("Production Orders", 5)
    walk.scroll(400, seconds=0.5, then=5)
    walk.go("Production Batches", 3)
    walk.select("Machine", 5, label="CNC-01")
    walk.scroll(500, seconds=0.5, then=6)
    walk.go("Quality Inspection", 4)
    walk.select("Result", 5, value="FAIL")
    walk.scroll(500, seconds=0.5, then=6)
    walk.go("Analytics and Reports", 10)
    walk.go("Factory Overview", 6)


def _quality_filters(walk: Walk, api: Api) -> None:
    early = api.batch_id("SIM0001-CNC-03-01-B01")
    late = api.batch_id("SIM0001-CNC-03-03-B04")
    walk.go("Quality Inspection", 6)
    walk.scroll(300, seconds=0.4, then=4)
    walk.type("Batch id", str(early), 6)
    walk.scroll(300, seconds=0.4, then=3)
    walk.select("Result", 6, value="FAIL")
    walk.fill("Batch id", "", 1)
    walk.type("Batch id", str(late), 6)
    walk.scroll(400, seconds=0.5, then=6)
    walk.fill("Batch id", "", 1)
    walk.select("Result", 2, value="")
    walk.scroll(-1200, steps=4, seconds=0.2)


def _record_inspections(walk: Walk, api: Api) -> None:
    first_unit = api.first_unit_id(api.batch_id("SIM0001-CNC-02-02-B04"))
    walk.button("Record inspection", 4)
    walk.type("Unit id", str(first_unit + 8), 1.5)
    walk.select("Specification", 1.5, value="3")
    walk.type("Measured value", "50.050", 1.5)
    walk.button("Record inspection", 1)
    walk.text(r"recorded as PASS").wait_for()
    walk.pause(7)
    walk.fill("Unit id", str(first_unit + 9), 1.5)
    walk.type("Measured value", "50.500", 1.5)
    walk.button("Record inspection", 1)
    walk.text(r"recorded as FAIL").wait_for()
    walk.pause(7)
    walk.fill("Unit id", str(first_unit + 8), 1.5)
    walk.select("Specification", 1.5, value="5")
    walk.type("Measured value", "20.000", 1.5)
    walk.button("Record inspection", 1)
    walk.page.get_by_role("alert").first.wait_for()
    walk.pause(8)
    walk.button("Close", 3)


def video_03_quality_inspection(walk: Walk, api: Api) -> None:
    """Filters by batch and result, manual entry (pass, fail, wrong product), alerts."""
    _quality_filters(walk, api)
    _record_inspections(walk, api)
    walk.scroll(500, seconds=0.5, then=5)
    walk.go("Factory Overview", 6)
    high_defect = walk.page.locator("li", has_text="High Defect Rate").first
    walk.show(high_defect, 4)
    walk.click(high_defect.get_by_role("button", name=re.compile("^Acknowledge")), 8)


def _open_case(walk: Walk, title: str, machine_id: str, start: str, end: str) -> None:
    walk.button("Open investigation", 3)
    walk.type("Title", title, 1)
    walk.select("Machine", 1.5, value=machine_id)
    walk.fill("Window start", start, 1)
    walk.fill("Window end", end, 1.5)
    walk.button("Run the rules and open the case", 1)
    walk.page.get_by_role("heading", name=title).wait_for()
    walk.settle(8)


def _evidence_card(walk: Walk, code: str) -> Locator:
    cards = walk.page.locator("article[data-testid='evidence-card']")
    return cards.filter(has_text=re.compile(rf"^{code}(?!\d)"))


def _read_evidence(walk: Walk, sql_cards: tuple[str, ...]) -> None:
    for code in sql_cards:
        card = _evidence_card(walk, code)
        walk.show(card, 4)
        walk.click(card.get_by_role("button", name="Show the SQL"), 1)
        walk.scroll(300, steps=4, seconds=0.4)
        walk.pause(6)
    for code in ("R5", "R6", "R7"):
        card = _evidence_card(walk, code)
        if card.count():
            walk.show(card, 5)


def _quarantine_flagged_batch(walk: Walk, batch_number: str) -> None:
    walk.click(walk.page.get_by_role("link", name=f"Review and quarantine {batch_number}"), 4)
    walk.button(f"Quarantine batch {batch_number}", 2)
    walk.type("Reason", "Tool wear confirmed on CNC-03; hold pending re-measurement", 1.5)
    walk.button(f"Confirm quarantine of batch {batch_number}", 5)


def video_04_defect_investigation(walk: Walk, api: Api) -> None:
    """Open a case for CNC-03, read the evidence, review, quarantine, and close it."""
    walk.show(walk.page.get_by_text("Defect rate", exact=True), 4)
    walk.go("Investigations", 4)
    _open_case(walk, "CNC-03 defect rate climb, walkthrough", "3", *CNC03_WINDOW)
    case_url = walk.page.url
    _read_evidence(walk, ("R1", "R3", "R4"))
    walk.show(walk.page.get_by_text("Case status", exact=True), 2)
    walk.button("Mark in review", 4)
    _quarantine_flagged_batch(walk, "SIM0001-CNC-03-03-B04")
    walk.page.goto(case_url)
    walk.settle(4)
    walk.button("Close with conclusion", 2)
    conclusion = (
        "Tool wear on CNC-03 from 08:00 explains the diameter drift. Batch B04 quarantined."
    )
    walk.type("Conclusion", conclusion, 2)
    walk.button("Close case", 6)
    walk.show(walk.page.get_by_text("cannot be reopened"), 5)


def video_05_material_traceability(walk: Walk, api: Api) -> None:
    """Forward and backward traces, then the quarantine cascade from a lot to its batches."""
    walk.pause(6)
    walk.go("Material Traceability", 6)
    walk.type("Lot number", "L203", 1)
    walk.button("Trace lot", 12)
    walk.scroll(400, seconds=0.5, then=6)
    walk.type("Serial number", "SIM0001-CNC-03-03-B04-U0001", 1)
    walk.button("Trace unit", 4)
    walk.show(walk.page.get_by_text("Inspection summary", exact=True), 10)
    walk.scroll(300, steps=6, seconds=0.5, then=6)
    walk.scroll(-1500, steps=4, seconds=0.2)
    walk.select("Material lot", 3, value="2")
    walk.type("Reason", "Supplier certificate withdrawn for lot L202", 1.5)
    walk.button("Quarantine lot and its batches", 1)
    walk.text(r"^Lot L\d+ is quarantined").wait_for()
    walk.pause(12)
    walk.fill("Lot number", "L202", 1)
    walk.button("Trace lot", 14)
    walk.go("Production Batches", 3)
    walk.select("Status", 10, value="QUARANTINED")
    walk.scroll(300, steps=4, then=6)
    walk.go("Factory Overview", 3)
    walk.show(walk.page.get_by_text("Material Quarantine").first, 14)


def _manufacture(walk: Walk, api: Api) -> int:
    """Create and release an order, start a batch with two lots; returns the batch id."""
    walk.go("Production Orders", 3)
    walk.button("New order", 2)
    walk.type("Order number", "WALK-1001", 1)
    walk.select("Product", 1, value="1")
    walk.select("Machine", 1, value="1")
    walk.fill("Quantity planned", "10", 1)
    walk.fill("Due date", "2026-11-14", 1.5)
    walk.button("Create order", 6)
    transitions = walk.page.get_by_role("group", name="Transitions for WALK-1001")
    walk.click(transitions.get_by_role("button", name="Release"), 6)
    walk.go("Production Batches", 3)
    walk.button("Start batch", 2)
    walk.select("Production order", 1.5, value=str(api.order_id("WALK-1001")))
    walk.fill("Quantity", "10", 1)
    walk.select("Lot 1", 1, value="1")
    walk.fill("Quantity used", "5", 1)
    walk.button("Add lot", 1)
    walk.select("Lot 2", 1, value="3")
    walk.fill("Quantity used", "5", 1.5, nth=1)
    walk.button("Start batch", 8)
    return api.batch_id("WALK-1001-B01")


def _inspect_and_complete(walk: Walk, api: Api, batch_id: int, first_unit: int) -> None:
    walk.go("Quality Inspection", 3)
    walk.button("Record inspection", 2)
    walk.type("Unit id", str(first_unit), 1)
    walk.select("Specification", 1, value="5")
    walk.type("Measured value", "20.020", 1)
    walk.button("Record inspection", 1)
    walk.text(r"recorded as PASS").wait_for()
    walk.pause(6)
    walk.fill("Unit id", str(first_unit + 1), 1)
    walk.select("Specification", 1, value="6")
    walk.type("Measured value", "150.900", 1)
    walk.button("Record inspection", 1)
    walk.text(r"recorded as FAIL").wait_for()
    walk.pause(6)
    walk.button("Close", 2)
    walk.go("Production Batches", 3)
    walk.select("Order", 3, value=str(api.order_id("WALK-1001")))
    walk.button("Complete batch WALK-1001-B01", 7)
    walk.go("Production Orders", 7)


def _simulate_and_investigate(walk: Walk) -> None:
    walk.go("Simulation", 3)
    walk.fill("Seed", "11", 1)
    walk.fill("Start time", "2026-11-04T06:00", 1)
    walk.fill("Batches per machine", "6", 1)
    walk.button("Add fault", 1.5)
    walk.select("Machine 1", 1, label="CNC-02")
    walk.fill("Start batch index", "3", 1.5)
    walk.button("Run simulation", 1)
    walk.text(r"^Machine events$").wait_for()
    walk.settle(10)
    walk.go("Factory Overview", 8)
    walk.scroll(300, steps=4, then=6)
    walk.go("Investigations", 3)
    _open_case(walk, "CNC-02 tool wear on 2026-11-04", "2", "2026-11-04T06:00", "2026-11-04T12:00")
    _read_evidence(walk, ("R4",))
    walk.show(walk.page.get_by_text("Case status", exact=True), 2)
    walk.button("Close with conclusion", 2)
    walk.type("Conclusion", "Simulated tool wear on CNC-02 reproduced; no action needed.", 1.5)
    walk.button("Close case", 8)


def _quarantine_and_report(walk: Walk) -> None:
    walk.go("Material Traceability", 3)
    walk.select("Material lot", 1.5, value="8")
    walk.type("Reason", "Alloy certificate mismatch on lot L402", 1.5)
    walk.button("Quarantine lot and its batches", 1)
    walk.text(r"^Lot L\d+ is quarantined").wait_for()
    walk.pause(8)
    walk.go("Production Batches", 3)
    walk.select("Status", 8, value="QUARANTINED")
    walk.go("Analytics and Reports", 5)
    walk.scroll(700, steps=10, seconds=0.4, then=3)
    chart = walk.page.locator("section[aria-label='Control chart']")
    walk.show(chart, 2)
    chart.get_by_label("Specification").select_option(label="STEEL-SHAFT diameter (mm)")
    chart.get_by_label("Machine").select_option(label="CNC-03")
    walk.settle(10)
    explorer = walk.page.locator("section[aria-label='SQL explorer']")
    walk.show(explorer, 2)
    walk.select("Query", 3, value="batches_requiring_review")
    walk.button("Run query", 1)
    walk.text(r"returned \d+ row").wait_for()
    walk.show(explorer.locator("tbody tr").last, 10)
    walk.go("Factory Overview", 10)


def video_06_complete_walkthrough(walk: Walk, api: Api) -> None:
    """Manufacturing, simulation, investigation, traceability, analytics, as admin."""
    walk.pause(5)
    units_before = int(api.get("/quality/summary")["total_produced"])
    batch_id = _manufacture(walk, api)
    _inspect_and_complete(walk, api, batch_id, units_before + 1)
    recorded = api.get(f"/inspections?batch_id={batch_id}&limit=10")["items"]
    if len(recorded) != 2:
        raise SystemExit(f"expected 2 inspections on batch {batch_id}, found {len(recorded)}")
    _simulate_and_investigate(walk)
    _quarantine_and_report(walk)


VIDEOS: dict[int, tuple[str, Callable[[Walk, Api], None], str]] = {
    2: ("engineer", video_02_virtual_factory, "02-virtual-factory-demonstration.mp4"),
    3: ("engineer", video_03_quality_inspection, "03-quality-inspection-demonstration.mp4"),
    4: ("engineer", video_04_defect_investigation, "04-defect-investigation-demonstration.mp4"),
    5: ("engineer", video_05_material_traceability, "05-material-traceability-demonstration.mp4"),
    6: ("admin", video_06_complete_walkthrough, "06-complete-system-walkthrough.mp4"),
}


def _encode(source: Path, target: Path) -> None:
    for options in ENCODINGS:
        command = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source), "-c:v", "libx264"]
        command += ["-preset", "slow", *options, "-pix_fmt", "yuv420p"]
        command += ["-movflags", "+faststart", str(target)]
        subprocess.run(command, check=True)
        if target.stat().st_size <= SIZE_LIMIT_BYTES:
            return
    print(f"warning: {target.name} is over 10 MB after every encoding option", file=sys.stderr)


def _record(browser: Browser, api: Api, number: int) -> None:
    account, sequence, file_name = VIDEOS[number]
    target = OUT_DIR / file_name
    with tempfile.TemporaryDirectory(prefix="walkthrough-") as temp:
        page = _sign_in(browser, api.token(account), Path(temp))
        try:
            sequence(Walk(page), api)
        finally:
            video = page.video
            page.context.close()
        _encode(Path(video.path()), target)
    probe = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0"]
    seconds = float(subprocess.run([*probe, str(target)], capture_output=True, text=True).stdout)
    size = target.stat().st_size / 1e6
    print(f"recorded {target.relative_to(REPO_ROOT)} {seconds:.0f} s {size:.1f} MB")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    selected = [int(n) for n in os.environ.get("VIDEOS", "2,3,4,5,6").split(",") if n.strip()]
    api = Api(_demo_password())
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(CHROME) if CHROME.exists() else None
        )
        for number in selected:
            _record(browser, api, number)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
