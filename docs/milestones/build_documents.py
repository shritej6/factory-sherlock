#!/usr/bin/env python3
"""Build DOCX and PDF versions of the milestone documents from their Markdown sources.

Usage (run from any directory):

    python3 docs/milestones/build_documents.py              # every *.md here except README.md
    python3 docs/milestones/build_documents.py week08-proposal.md
    python3 docs/milestones/build_documents.py --no-pdf     # DOCX only
    python3 docs/milestones/build_documents.py /path/to/other.md   # any Markdown file

Requirements: python-docx, pypdf, reportlab, and Pillow (pip install python-docx
pypdf reportlab pillow). LibreOffice (soffice on PATH) is optional. The script:

1. parses the Markdown subset used by these documents (headings, paragraphs,
   bullet and numbered lists, pipe tables, fenced code, bold and inline code);
2. writes <name>.docx next to the Markdown with python-docx;
3. writes <name>.pdf: prints styled HTML with Chrome through Playwright when the
   playwright package is importable (run from backend/ with the docs group), else
   converts the DOCX with soffice --headless when a working LibreOffice is installed,
   otherwise renders the parsed content directly with reportlab;
4. prints the PDF page count, the method used, and the number of bracketed
   prompts that still need to be replaced.

Mermaid fences are embedded as figures when scripts/development/render_milestone_figures.py
has produced docs/milestones/figures/<document>-<n>.png for them (n counts the Mermaid
blocks in the file). Without a rendered figure the fence is replaced by a note that
points to the Mermaid source in the Markdown file and to docs/database/database-design.md.
Generated files are overwritten on every run.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).resolve().parent
BODY_FONT = "Calibri"
MONO_FONT = "Consolas"
BODY_SIZE = Pt(10)
TABLE_SIZE = Pt(8.5)
MERMAID_NOTE = (
    "The entity relationship diagram is written in Mermaid. The diagram source is in "
    "the Markdown version of this document and in docs/database/database-design.md, "
    "where it renders in the repository viewer."
)
FIGURE_DIR = HERE / "figures"
CURRENT_SOURCE_DIR = HERE
FIGURE_WIDTH_INCHES = 6.9
HEADING_RESERVE_INCHES = 1.1
FORBIDDEN_DASHES = (chr(0x2013), chr(0x2014))
INLINE_PATTERN = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")
IMAGE_PATTERN = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")


@dataclass
class Block:
    kind: str
    lines: list[str] = field(default_factory=list)
    language: str = ""
    figure: Path | None = None


def attach_figures(markdown_path: Path, blocks: list[Block]) -> None:
    """Point each Mermaid block at the PNG that render_milestone_figures.py produced, if any."""
    global CURRENT_SOURCE_DIR
    CURRENT_SOURCE_DIR = markdown_path.parent
    index = 0
    for block in blocks:
        if block.kind == "image" and not Path(block.language).is_absolute():
            block.language = str((markdown_path.parent / block.language).resolve())
        if block.kind == "code" and block.language == "mermaid":
            index += 1
            candidate = FIGURE_DIR / f"{markdown_path.stem}-{index}.png"
            block.figure = candidate if candidate.exists() else None


def parse_markdown(text: str) -> list[Block]:
    """Split Markdown into blocks: heading, para, bullet, number, table, code, rule."""
    blocks: list[Block] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            index = _consume_fence(lines, index, blocks)
            continue
        if not line.strip():
            index += 1
            continue
        if line.startswith("#"):
            blocks.append(Block("heading", [line]))
        elif IMAGE_PATTERN.match(line.strip()):
            match = IMAGE_PATTERN.match(line.strip())
            blocks.append(Block("image", [match.group(1)], language=match.group(2)))
        elif line.startswith("|"):
            index = _consume_while(lines, index, blocks, "table", lambda s: s.startswith("|"))
            continue
        elif re.match(r"^- ", line):
            blocks.append(Block("bullet", [line[2:].strip()]))
        elif re.match(r"^\d+\. ", line):
            blocks.append(Block("number", [re.sub(r"^\d+\. ", "", line).strip()]))
        elif line.strip() == "---":
            blocks.append(Block("rule"))
        else:
            index = _consume_while(lines, index, blocks, "para", _is_plain_line)
            continue
        index += 1
    return blocks


def _is_plain_line(line: str) -> bool:
    if not line.strip() or line.startswith(("#", "|", "```", "![")):
        return False
    return not re.match(r"^(- |\d+\. )", line)


def _consume_while(lines: list[str], index: int, blocks: list[Block], kind: str, test) -> int:
    block = Block(kind)
    while index < len(lines) and test(lines[index]):
        block.lines.append(lines[index])
        index += 1
    blocks.append(block)
    return index


def _consume_fence(lines: list[str], index: int, blocks: list[Block]) -> int:
    language = lines[index][3:].strip()
    block = Block("code", language=language)
    index += 1
    while index < len(lines) and not lines[index].startswith("```"):
        block.lines.append(lines[index])
        index += 1
    blocks.append(block)
    return index + 1


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(0.7))
    normal = document.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = BODY_SIZE
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.line_spacing = 1.05
    for name, size, before in (("Title", 15, 0), ("Heading 1", 12, 8), ("Heading 2", 10.5, 6)):
        style = document.styles[name]
        style.font.name = BODY_FONT
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(3)
        style.paragraph_format.keep_with_next = True


def add_inline_runs(paragraph, text: str, size=None) -> None:
    """Add runs to a paragraph, honouring **bold** and `code` spans."""
    for piece in INLINE_PATTERN.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            run = paragraph.add_run(piece[2:-2])
            run.bold = True
        elif piece.startswith("`") and piece.endswith("`"):
            run = paragraph.add_run(piece[1:-1])
            run.font.name = MONO_FONT
        else:
            run = paragraph.add_run(piece)
        if size is not None:
            run.font.size = size


def render_heading(document: Document, line: str) -> None:
    level = len(line) - len(line.lstrip("#"))
    text = line[level:].strip()
    if level == 1:
        paragraph = document.add_paragraph(style="Title")
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        add_inline_runs(paragraph, text)
        return
    style = "Heading 1" if level == 2 else "Heading 2"
    add_inline_runs(document.add_paragraph(style=style), text)


def render_paragraph(document: Document, lines: list[str]) -> None:
    is_metadata = all(line.startswith("**") and ":**" in line for line in lines)
    if is_metadata:
        for line in lines:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_after = Pt(0)
            add_inline_runs(paragraph, line)
        document.paragraphs[-1].paragraph_format.space_after = Pt(6)
        return
    add_inline_runs(document.add_paragraph(), " ".join(line.strip() for line in lines))


def render_list_item(document: Document, text: str, kind: str) -> None:
    style = "List Bullet" if kind == "bullet" else "List Number"
    paragraph = document.add_paragraph(style=style)
    paragraph.paragraph_format.space_after = Pt(2)
    add_inline_runs(paragraph, text)


def render_code(document: Document, block: Block) -> None:
    if block.language == "mermaid":
        if block.figure is not None:
            document.add_picture(str(block.figure), width=Inches(FIGURE_WIDTH_INCHES))
            document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            return
        paragraph = document.add_paragraph()
        run = paragraph.add_run(MERMAID_NOTE)
        run.italic = True
        return
    for line in block.lines:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(line)
        run.font.name = MONO_FONT
        run.font.size = Pt(9)


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render_table(document: Document, lines: list[str]) -> None:
    rows = [_split_row(line) for line in lines if not re.match(r"^\|\s*-", line)]
    if not rows:
        return
    width = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=width)
    table.style = "Table Grid"
    for row_index, row in enumerate(rows):
        for col_index in range(width):
            cell = table.cell(row_index, col_index)
            text = row[col_index] if col_index < len(row) else ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            add_inline_runs(paragraph, text, size=TABLE_SIZE)
            if row_index == 0:
                _style_header_cell(cell)
    document.add_paragraph().paragraph_format.space_after = Pt(2)


def _style_header_cell(cell) -> None:
    for run in cell.paragraphs[0].runs:
        run.bold = True
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), "E7EBF3")
    cell._tc.get_or_add_tcPr().append(shading)


def render_blocks(document: Document, blocks: list[Block]) -> None:
    for block in blocks:
        if block.kind == "heading":
            render_heading(document, block.lines[0])
        elif block.kind == "para":
            render_paragraph(document, block.lines)
        elif block.kind in ("bullet", "number"):
            render_list_item(document, block.lines[0], block.kind)
        elif block.kind == "table":
            render_table(document, block.lines)
        elif block.kind == "code":
            render_code(document, block)
        elif block.kind == "image":
            render_image(document, block)


def render_image(document: Document, block: Block) -> None:
    path = Path(block.language)
    if not path.is_absolute():
        path = CURRENT_SOURCE_DIR / path
    document.add_picture(str(path), width=Inches(FIGURE_WIDTH_INCHES))
    document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if block.lines[0]:
        caption = document.add_paragraph()
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = caption.add_run(block.lines[0])
        run.italic = True
        run.font.size = Pt(9)


def build_docx(markdown_path: Path, blocks: list[Block]) -> Path:
    document = Document()
    configure_document(document)
    render_blocks(document, blocks)
    target = markdown_path.with_suffix(".docx")
    document.save(target)
    return target


def soffice_available() -> str | None:
    """Return the soffice path only when it actually runs (a dangling shim exits 127)."""
    soffice = shutil.which("soffice")
    if soffice is None:
        return None
    try:
        probe = subprocess.run([soffice, "--version"], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return soffice if probe.returncode == 0 else None


def chrome_available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    from html_pdf import chrome_path

    return chrome_path() is not None


def build_pdf(docx_path: Path, blocks: list[Block]) -> tuple[Path, str]:
    """Print styled HTML with Chrome when Playwright imports; else LibreOffice; else reportlab."""
    pdf_path = docx_path.with_suffix(".pdf")
    if chrome_available():
        from html_pdf import print_pdf, render_html

        title = document_title(blocks)
        print_pdf(render_html(blocks, title, MERMAID_NOTE), pdf_path, title)
        return pdf_path, "chrome"
    soffice = soffice_available()
    if soffice is None:
        render_pdf_reportlab(blocks, pdf_path)
        return pdf_path, "reportlab"
    with tempfile.TemporaryDirectory() as profile:
        command = [
            soffice,
            f"-env:UserInstallation=file://{profile}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(docx_path.parent),
            str(docx_path),
        ]
        subprocess.run(command, check=True, capture_output=True, timeout=180)
    return pdf_path, "soffice"


# --- reportlab fallback -----------------------------------------------------


def _pdf_styles() -> dict:
    from reportlab.lib.styles import ParagraphStyle

    base = {"fontName": "Helvetica", "fontSize": 10, "leading": 11.7, "spaceAfter": 3}
    heading = {"fontName": "Helvetica-Bold", "textColor": "#1F2A44"}
    return {
        "body": ParagraphStyle("body", **base),
        "meta": ParagraphStyle("meta", **{**base, "spaceAfter": 0}),
        "title": ParagraphStyle(
            "title", **{**heading, "fontSize": 15, "leading": 18, "spaceAfter": 6}
        ),
        "h1": ParagraphStyle(
            "h1", **{**heading, "fontSize": 12, "leading": 14, "spaceBefore": 6, "spaceAfter": 3}
        ),
        "h2": ParagraphStyle(
            "h2", **{**heading, "fontSize": 10.5, "leading": 13, "spaceBefore": 6, "spaceAfter": 3}
        ),
        "bullet": ParagraphStyle(
            "bullet", **{**base, "leftIndent": 14, "bulletIndent": 3, "spaceAfter": 2}
        ),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5, leading=10.2),
        "head": ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=8.5, leading=10.2),
        "note": ParagraphStyle("note", **{**base, "fontName": "Helvetica-Oblique"}),
    }


def _markup(text: str) -> str:
    """Convert the Markdown inline subset to reportlab paragraph markup."""
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    return re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', escaped)


def _pdf_heading(line: str, styles: dict):
    from reportlab.platypus import Paragraph

    level = len(line) - len(line.lstrip("#"))
    style = {1: styles["title"], 2: styles["h1"]}.get(level, styles["h2"])
    return Paragraph(_markup(line[level:].strip()), style)


def _pdf_paragraphs(lines: list[str], styles: dict) -> list:
    from reportlab.platypus import Paragraph, Spacer

    if all(line.startswith("**") and ":**" in line for line in lines):
        flow = [Paragraph(_markup(line), styles["meta"]) for line in lines]
        return [*flow, Spacer(1, 6)]
    return [Paragraph(_markup(" ".join(line.strip() for line in lines)), styles["body"])]


def _column_widths(rows: list[list[str]], total_width: float) -> list[float]:
    """Share the width by content length, but never narrower than a column's longest word."""
    columns = range(len(rows[0]))
    weights = [max(12, max(len(row[col]) for row in rows)) ** 0.6 for col in columns]
    widths = [total_width * weight / sum(weights) for weight in weights]
    minimums = [
        5.3 * max(len(word) for row in rows for word in (row[col].split() or [""])) + 8
        for col in columns
    ]
    fixed = {col for col in columns if widths[col] < minimums[col]}
    remaining = total_width - sum(minimums[col] for col in fixed)
    flexible_total = sum(weights[col] for col in columns if col not in fixed) or 1
    return [
        minimums[col] if col in fixed else remaining * weights[col] / flexible_total
        for col in columns
    ]


def _pdf_table(lines: list[str], styles: dict):
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, Table, TableStyle

    rows = [_split_row(line) for line in lines if not re.match(r"^\|\s*-", line)]
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    col_widths = _column_widths(rows, 7.1 * inch)
    data = [
        [Paragraph(_markup(cell), styles["head"] if r == 0 else styles["cell"]) for cell in row]
        for r, row in enumerate(rows)
    ]
    table = Table(data, colWidths=col_widths, repeatRows=1, spaceAfter=6)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA3B2")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EBF3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _pdf_figure(figure: Path):
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image

    pixel_width, pixel_height = ImageReader(str(figure)).getSize()
    width = FIGURE_WIDTH_INCHES * inch
    height = width * pixel_height / pixel_width
    return Image(str(figure), width=width, height=height, hAlign="CENTER")


def _pdf_code(block: Block, styles: dict):
    from reportlab.platypus import Paragraph, Preformatted

    if block.language == "mermaid":
        if block.figure is not None:
            return _pdf_figure(block.figure)
        return Paragraph(MERMAID_NOTE, styles["note"])
    code_style = styles["cell"].clone("code", fontName="Courier", fontSize=8.5, leading=10)
    return Preformatted("\n".join(block.lines), code_style)


def _pdf_flowables(blocks: list[Block], styles: dict) -> list:
    from reportlab.lib.units import inch
    from reportlab.platypus import CondPageBreak, KeepTogether, Paragraph

    flow: list = []
    number = 0
    for block in blocks:
        number = number + 1 if block.kind == "number" else 0
        if block.kind == "heading":
            flow.append(CondPageBreak(HEADING_RESERVE_INCHES * inch))
            flow.append(_pdf_heading(block.lines[0], styles))
        elif block.kind == "para":
            flow.extend(_pdf_paragraphs(block.lines, styles))
        elif block.kind == "bullet":
            flow.append(Paragraph(_markup(block.lines[0]), styles["bullet"], bulletText="-"))
        elif block.kind == "number":
            flow.append(
                Paragraph(_markup(block.lines[0]), styles["bullet"], bulletText=f"{number}.")
            )
        elif block.kind == "table":
            flow.append(_pdf_table(block.lines, styles))
        elif block.kind == "code" and block.figure is not None and _ends_with_heading(flow):
            flow.append(KeepTogether([flow.pop(), _pdf_code(block, styles)]))
        elif block.kind == "code":
            flow.append(_pdf_code(block, styles))
        elif block.kind == "image":
            flow.append(_pdf_figure(Path(block.language)))
    return flow


def _ends_with_heading(flow: list) -> bool:
    from reportlab.platypus import Paragraph

    return bool(flow) and isinstance(flow[-1], Paragraph) and flow[-1].style.name in ("h1", "h2")


def render_pdf_reportlab(blocks: list[Block], pdf_path: Path) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate

    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=pdf_path.stem,
    )
    document.build(_pdf_flowables(blocks, _pdf_styles()))


def document_title(blocks: list[Block]) -> str:
    for block in blocks:
        if block.kind == "heading" and block.lines[0].startswith("# "):
            return block.lines[0][2:].strip()
    return "Document"


def page_count(pdf_path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(pdf_path)).pages)


def lint_markdown(markdown_path: Path) -> None:
    text = markdown_path.read_text(encoding="utf-8")
    for dash in FORBIDDEN_DASHES:
        if dash in text:
            print(
                f"  warning: {markdown_path.name} contains U+{ord(dash):04X} dash", file=sys.stderr
            )
    prompts = len(re.findall(r"\[[^\]]+\]", text))
    if prompts:
        print(f"  note: {prompts} bracketed prompt(s) remain to be replaced by the student")


def select_sources(names: list[str]) -> list[Path]:
    if names:
        return [Path(name) if "/" in name else HERE / name for name in names]
    return sorted(p for p in HERE.glob("*.md") if p.name != "README.md")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sources", nargs="*", help="Markdown file names inside docs/milestones")
    parser.add_argument("--no-pdf", action="store_true", help="build DOCX only")
    args = parser.parse_args()
    for source in select_sources(args.sources):
        if not source.exists():
            print(f"missing: {source}", file=sys.stderr)
            return 1
        print(source.name)
        lint_markdown(source)
        blocks = parse_markdown(source.read_text(encoding="utf-8"))
        attach_figures(source, blocks)
        docx_path = build_docx(source, blocks)
        print(f"  wrote {docx_path.name}")
        if args.no_pdf:
            continue
        pdf_path, method = build_pdf(docx_path, blocks)
        print(f"  wrote {pdf_path.name} via {method} ({page_count(pdf_path)} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
