"""Render every Mermaid source under docs/media/diagrams to SVG.

Uses Playwright with the Mermaid library loaded from a CDN, so no Node toolchain
is required. Run from the repository root:

    make render-diagrams

which runs ``cd backend && uv run --group docs python
../scripts/development/render_diagrams.py``.

The browser is an installed Google Chrome when one exists at the macOS
location, otherwise Playwright's bundled Chromium (install it once with
``uv run --group docs playwright install chromium`` from ``backend/``).

Each ``<name>.mmd`` produces ``<name>.svg`` next to it. Existing SVGs are
overwritten so the rendered output always matches the source.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import Browser, Playwright, sync_playwright
from playwright.sync_api import Error as PlaywrightError

DIAGRAM_DIR = Path(__file__).resolve().parents[2] / "docs" / "media" / "diagrams"
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"
MACOS_CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
INSTALL_HINT = (
    "No browser available for Playwright. Install the bundled Chromium with:\n"
    "    cd backend && uv run --group docs playwright install chromium"
)

PAGE = """<!doctype html><html><body><div id="out"></div>
<script src="{cdn}"></script>
<script>
mermaid.initialize({{startOnLoad: false, theme: "neutral", securityLevel: "loose"}});
async function render(source) {{
  const {{ svg }} = await mermaid.render("diagram", source);
  return svg;
}}
</script></body></html>"""


class BrowserUnavailableError(RuntimeError):
    """Raised when neither an installed Chrome nor the bundled Chromium can start."""


def _launch(playwright: Playwright) -> Browser:
    """Prefer the macOS Chrome install, else Playwright's own Chromium."""
    if MACOS_CHROME.exists():
        return playwright.chromium.launch(executable_path=str(MACOS_CHROME))
    try:
        return playwright.chromium.launch()
    except PlaywrightError as exc:
        detail = str(exc).splitlines()[0]
        raise BrowserUnavailableError(f"{INSTALL_HINT}\n\nPlaywright said: {detail}") from exc


def _render_all(browser: Browser, sources: list[Path]) -> int:
    """Render each source to SVG; return the number of failures."""
    page = browser.new_page()
    page.set_content(PAGE.format(cdn=MERMAID_CDN))
    page.wait_for_function("typeof mermaid !== 'undefined'")
    failures = 0
    for source in sources:
        try:
            svg = page.evaluate("render(" + json.dumps(source.read_text()) + ")")
        except Exception as exc:  # report every diagram, then fail
            failures += 1
            print(f"FAILED {source.name}: {str(exc).splitlines()[0]}", file=sys.stderr)
            continue
        target = source.with_suffix(".svg")
        target.write_text(svg)
        print(f"rendered {target.relative_to(DIAGRAM_DIR.parents[2])}")
    return failures


def main() -> int:
    sources = sorted(DIAGRAM_DIR.glob("*.mmd"))
    if not sources:
        print(f"No .mmd files found in {DIAGRAM_DIR}", file=sys.stderr)
        return 1
    with sync_playwright() as playwright:
        try:
            browser = _launch(playwright)
        except BrowserUnavailableError as exc:
            print(exc, file=sys.stderr)
            return 1
        try:
            failures = _render_all(browser, sources)
        finally:
            browser.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
