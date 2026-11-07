"""Render parsed milestone Markdown blocks to styled HTML and print it to PDF with Chrome.

Used by build_documents.py when the Python ``playwright`` package can be imported
(``cd backend && uv run --group docs python ../docs/milestones/build_documents.py``).
The page is Letter size with 0.8 inch margins, a running footer with the document
title and page number, and typography chosen for printed review: a sans-serif body
at 10.5 pt with 1.4 line spacing, navy headings, shaded table headers, and figures
scaled to the text width.
"""

from __future__ import annotations

import base64
import html
import re
from pathlib import Path

NAVY = "#1F2A44"
ACCENT = "#2B5797"
RULE = "#C9D0DC"
HEAD_FILL = "#E9EDF4"
ZEBRA = "#F7F8FB"

CSS = f"""
@page {{ size: Letter; margin: 0.8in 0.8in 0.9in 0.8in; }}
html {{ font-size: 10.5pt; }}
body {{
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  color: #1A1A1A; line-height: 1.4; margin: 0;
}}
h1 {{
  font-size: 20pt; line-height: 1.2; color: {NAVY}; margin: 0 0 6pt 0;
  padding-bottom: 8pt; border-bottom: 2.5pt solid {ACCENT};
}}
.meta {{ margin: 8pt 0 16pt 0; padding: 0; }}
.meta div {{ margin: 0; line-height: 1.5; display: grid; grid-template-columns: 110pt 1fr; }}
.meta b {{ color: {NAVY}; font-weight: 600; }}
h2 {{
  font-size: 13.5pt; color: {NAVY}; margin: 18pt 0 6pt 0; padding-bottom: 3pt;
  border-bottom: 0.75pt solid {RULE}; break-after: avoid; page-break-after: avoid;
}}
h3 {{
  font-size: 11.5pt; color: {NAVY}; margin: 12pt 0 4pt 0;
  break-after: avoid; page-break-after: avoid;
}}
p {{ margin: 0 0 7pt 0; text-align: left; orphans: 3; widows: 3; }}
ul, ol {{ margin: 0 0 7pt 0; padding-left: 18pt; }}
li {{ margin: 0 0 3pt 0; }}
table {{
  border-collapse: collapse; width: 100%; margin: 4pt 0 10pt 0; font-size: 9pt; line-height: 1.3;
}}
thead {{ display: table-header-group; }}
th {{
  background: {HEAD_FILL}; color: {NAVY}; text-align: left; font-weight: 600;
  padding: 4pt 5pt; border: 0.5pt solid {RULE}; vertical-align: bottom;
}}
td {{ padding: 3.5pt 5pt; border: 0.5pt solid {RULE}; vertical-align: top; }}
th, td {{ overflow-wrap: anywhere; min-width: 3.2em; }}
tbody tr:nth-child(even) td {{ background: {ZEBRA}; }}
tr {{ break-inside: avoid; page-break-inside: avoid; }}
code {{ font-family: Menlo, Consolas, monospace; font-size: 0.92em; }}
pre {{
  font-family: Menlo, Consolas, monospace; font-size: 8.5pt; line-height: 1.35;
  background: {ZEBRA}; border: 0.5pt solid {RULE}; padding: 6pt 8pt; margin: 4pt 0 10pt 0;
  white-space: pre-wrap; word-wrap: break-word;
}}
figure {{
  margin: 6pt 0 12pt 0; text-align: center; break-inside: avoid; page-break-inside: avoid;
}}
figure img {{ max-width: 100%; height: auto; }}
figcaption {{ font-size: 9pt; color: #4A5568; margin-top: 4pt; }}
figure.shot img {{ max-width: 80%; border: 0.5pt solid {RULE}; }}
p.caption {{
  font-weight: 600; font-size: 9.5pt; color: {NAVY}; margin: 8pt 0 3pt 0;
  break-after: avoid; page-break-after: avoid;
}}
p.lead {{ margin-bottom: 4pt; break-after: avoid; page-break-after: avoid; }}
.note {{ font-style: italic; color: #4A5568; }}
hr {{ border: 0; border-top: 0.75pt solid {RULE}; margin: 12pt 0; }}
a {{ color: {ACCENT}; text-decoration: none; }}
"""

COMPACT_CSS = """
@page { size: Letter; margin: 0.65in 0.7in 0.75in 0.7in; }
html { font-size: 9.75pt; }
body { line-height: 1.3; }
h1 { font-size: 17pt; margin-bottom: 4pt; padding-bottom: 6pt; }
.meta { margin: 6pt 0 10pt 0; }
.meta div { line-height: 1.35; }
h2 { font-size: 12pt; margin: 11pt 0 4pt 0; }
p { margin-bottom: 5pt; }
li { margin-bottom: 2pt; }
table { font-size: 8.25pt; line-height: 1.25; margin: 3pt 0 7pt 0; }
th, td { padding: 2.5pt 4pt; }
figure { margin: 4pt 0 8pt 0; }
figure img { max-width: 62%; }
"""

FOOTER_TEMPLATE = """
<div style="width:100%; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:8pt;
            color:#4A5568; padding:0 0.8in; display:flex; justify-content:space-between;">
  <span>{title}</span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>
"""

_INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


def markup(text: str) -> str:
    """Convert the Markdown inline subset (bold, code, links) to HTML."""
    parts: list[str] = []
    for piece in _INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            parts.append(f"<b>{html.escape(piece[2:-2])}</b>")
        elif piece.startswith("`") and piece.endswith("`"):
            parts.append(f"<code>{html.escape(piece[1:-1])}</code>")
        elif piece.startswith("[") and "](" in piece:
            label, url = piece[1:-1].split("](", 1)
            parts.append(f'<a href="{html.escape(url)}">{html.escape(label)}</a>')
        else:
            parts.append(html.escape(piece))
    return "".join(parts)


def _heading(line: str) -> str:
    level = len(line) - len(line.lstrip("#"))
    text = markup(line[level:].strip())
    tag = "h1" if level == 1 else "h2" if level == 2 else "h3"
    return f"<{tag}>{text}</{tag}>"


def _paragraph(lines: list[str]) -> str:
    if all(line.startswith("**") and ":**" in line for line in lines):
        rows = "".join(f"<div>{markup(line)}</div>" for line in lines)
        return f'<div class="meta">{rows}</div>'
    text = " ".join(line.strip() for line in lines)
    if re.match(r"^Table \d+(\.\d+)?:", text):
        return f'<p class="caption">{markup(text)}</p>'
    if text.endswith(":") and len(text) < 120:
        return f'<p class="lead">{markup(text)}</p>'
    return f"<p>{markup(text)}</p>"


def _table(lines: list[str]) -> str:
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in lines
        if not re.match(r"^\|\s*-", line)
    ]
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    head = "".join(f"<th>{markup(cell)}</th>" for cell in rows[0])
    body = "".join(
        "<tr>" + "".join(f"<td>{markup(cell)}</td>" for cell in row) + "</tr>" for row in rows[1:]
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _data_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _figure(path: Path, caption: str, css_class: str = "") -> str:
    cap = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
    cls = f' class="{css_class}"' if css_class else ""
    return f'<figure{cls}><img src="{_data_uri(path)}" alt="{html.escape(caption)}">{cap}</figure>'


def _code(block, note: str) -> str:
    if block.language == "mermaid":
        if block.figure is not None:
            return _figure(block.figure, "")
        return f'<p class="note">{html.escape(note)}</p>'
    return f"<pre>{html.escape(chr(10).join(block.lines))}</pre>"


def _list(kind: str, items: list[str]) -> str:
    tag = "ul" if kind == "bullet" else "ol"
    return f"<{tag}>" + "".join(f"<li>{markup(item)}</li>" for item in items) + f"</{tag}>"


def render_html(blocks: list, title: str, mermaid_note: str, compact: bool = False) -> str:
    """Return a complete HTML document for the parsed blocks.

    ``compact`` appends the denser page layout used for length-limited submissions.
    """
    out: list[str] = []
    pending_kind = ""
    pending_items: list[str] = []

    def flush() -> None:
        nonlocal pending_kind, pending_items
        if pending_items:
            out.append(_list(pending_kind, pending_items))
        pending_kind, pending_items = "", []

    for block in blocks:
        if block.kind in ("bullet", "number"):
            if pending_kind and pending_kind != block.kind:
                flush()
            pending_kind = block.kind
            pending_items.append(block.lines[0])
            continue
        flush()
        if block.kind == "heading":
            out.append(_heading(block.lines[0]))
        elif block.kind == "para":
            out.append(_paragraph(block.lines))
        elif block.kind == "table":
            out.append(_table(block.lines))
        elif block.kind == "code":
            out.append(_code(block, mermaid_note))
        elif block.kind == "image":
            path = Path(block.language)
            css_class = "" if "erd" in path.name.lower() else "shot"
            out.append(_figure(path, block.lines[0], css_class))
        elif block.kind == "rule":
            out.append("<hr>")
    flush()
    body = "\n".join(out)
    css = CSS + COMPACT_CSS if compact else CSS
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><style>{css}</style></head>"
        f"<body>{body}</body></html>"
    )


def chrome_path() -> str | None:
    candidate = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    return str(candidate) if candidate.exists() else None


def print_pdf(html_text: str, pdf_path: Path, title: str) -> None:
    """Print the HTML to PDF through Playwright: installed Chrome, else bundled Chromium."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        executable = chrome_path()
        browser = (
            playwright.chromium.launch(executable_path=executable)
            if executable
            else playwright.chromium.launch()
        )
        try:
            page = browser.new_page()
            page.set_content(html_text, wait_until="load")
            page.emulate_media(media="print")
            page.pdf(
                path=str(pdf_path),
                format="Letter",
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=FOOTER_TEMPLATE.format(title=html.escape(title)),
            )
        finally:
            browser.close()
