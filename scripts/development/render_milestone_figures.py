"""Render the Mermaid blocks inside docs/milestones/*.md to PNG figures.

docs/milestones/build_documents.py embeds these PNGs in the DOCX and PDF
versions of each milestone document, so the proposal PDF carries the draft ERD
instead of a note pointing at the Markdown source. Figures are written to
docs/milestones/figures/<document>-<n>.png, numbered by the order of the
Mermaid blocks in the Markdown file.

Run from the backend directory with the docs dependency group:

    cd backend && uv run --group docs python ../scripts/development/render_milestone_figures.py

The script reuses the browser launch and Mermaid page from render_diagrams.py.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import Browser, sync_playwright
from render_diagrams import MERMAID_CDN, BrowserUnavailableError, _launch

REPO_ROOT = Path(__file__).resolve().parents[2]
MILESTONE_DIR = REPO_ROOT / "docs" / "milestones"
FIGURE_DIR = MILESTONE_DIR / "figures"
FENCE = re.compile(r"^```mermaid\s*$(.*?)^```\s*$", re.MULTILINE | re.DOTALL)
SCALE = 4
PAGE = """<!doctype html><html><body style="margin:0;background:#fff"><div id="figure"
style="display:inline-block;padding:8px"></div>
<script src="{cdn}"></script>
<script>
mermaid.initialize({{startOnLoad: false, theme: "neutral", securityLevel: "loose",
  er: {{fontSize: 34, entityPadding: 14, minEntityWidth: 150, minEntityHeight: 60,
       useMaxWidth: false}}}});
async function render(source) {{
  const {{ svg }} = await mermaid.render("diagram", source);
  document.getElementById("figure").innerHTML = svg;
  return svg;
}}
</script></body></html>"""


def mermaid_blocks(markdown_path: Path) -> list[str]:
    return [match.group(1).strip() for match in FENCE.finditer(markdown_path.read_text())]


def _render_png(browser: Browser, source: str, target: Path) -> None:
    page = browser.new_page(device_scale_factor=SCALE)
    try:
        page.set_content(PAGE.format(cdn=MERMAID_CDN))
        page.wait_for_function("typeof mermaid !== 'undefined'")
        page.evaluate("render(" + json.dumps(source) + ")")
        page.locator("#figure").screenshot(path=str(target))
    finally:
        page.close()


def render_all(browser: Browser) -> int:
    FIGURE_DIR.mkdir(exist_ok=True)
    failures = 0
    for markdown_path in sorted(MILESTONE_DIR.glob("*.md")):
        for index, source in enumerate(mermaid_blocks(markdown_path), start=1):
            target = FIGURE_DIR / f"{markdown_path.stem}-{index}.png"
            try:
                _render_png(browser, source, target)
            except Exception as exc:  # report every figure, then fail
                failures += 1
                print(f"FAILED {target.name}: {str(exc).splitlines()[0]}", file=sys.stderr)
                continue
            print(f"rendered {target.relative_to(REPO_ROOT)}")
    return failures


def main() -> int:
    with sync_playwright() as playwright:
        try:
            browser = _launch(playwright)
        except BrowserUnavailableError as exc:
            print(exc, file=sys.stderr)
            return 1
        try:
            failures = render_all(browser)
        finally:
            browser.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
