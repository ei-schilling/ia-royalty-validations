"""Annotated PDF — renders the uploaded data as a table with highlighted issues.

Reads the original file, renders every row as a styled table, and
colour-codes the cells that triggered validation issues.  A legend and
per-row annotations make it easy to spot and understand each problem.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.validation.parser import parse_file

# ── Palette ──────────────────────────────────────────────────────────────────

BG_DARK = HexColor("#111118")
BG_CARD = HexColor("#18181f")
BG_ROW_EVEN = HexColor("#16161d")
BG_ROW_ODD = HexColor("#1c1c25")
BORDER = HexColor("#2a2a35")
TEXT = HexColor("#f0f0f5")
TEXT_DIM = HexColor("#8b8b9e")
TEXT_MUTED = HexColor("#5a5a6e")

AMBER = HexColor("#e8a230")
EMERALD = HexColor("#34d399")
RED = HexColor("#f87171")
SKY = HexColor("#38bdf8")

# Highlight backgrounds (translucent-ish via lighter tones)
HL_ERROR = HexColor("#3d1818")
HL_WARNING = HexColor("#3d3018")
HL_INFO = HexColor("#182a3d")
HL_OK = None  # no highlight

SEVERITY_COLORS = {
    "error": (RED, HL_ERROR, "E"),
    "warning": (AMBER, HL_WARNING, "W"),
    "info": (SKY, HL_INFO, "I"),
}

# ── Typography ───────────────────────────────────────────────────────────────

def _s(name: str, **kw) -> ParagraphStyle:
    kw.setdefault("fontName", "Helvetica")
    kw.setdefault("textColor", TEXT)
    return ParagraphStyle(name, **kw)


S_TITLE = _s("at_title", fontSize=16, leading=20, fontName="Helvetica-Bold")
S_SUBTITLE = _s("at_sub", fontSize=9, leading=12, textColor=TEXT_DIM)
S_HEADER = _s("at_hdr", fontSize=6.5, leading=8, fontName="Helvetica-Bold", textColor=TEXT_DIM)
S_CELL = _s("at_cell", fontSize=6.5, leading=8)
S_CELL_ERR = _s("at_cell_e", fontSize=6.5, leading=8, textColor=RED)
S_CELL_WARN = _s("at_cell_w", fontSize=6.5, leading=8, textColor=AMBER)
S_CELL_INFO = _s("at_cell_i", fontSize=6.5, leading=8, textColor=SKY)
S_ANNOT = _s("at_ann", fontSize=6, leading=8, textColor=TEXT_DIM)
S_LEGEND = _s("at_leg", fontSize=7, leading=10)
S_FOOTER = _s("at_foot", fontSize=6, leading=8, textColor=TEXT_MUTED, alignment=TA_CENTER)
S_SECTION = _s("at_sec", fontSize=10, leading=14, fontName="Helvetica-Bold")

CELL_STYLE_MAP = {
    "error": S_CELL_ERR,
    "warning": S_CELL_WARN,
    "info": S_CELL_INFO,
}

PAGE_W, PAGE_H = landscape(A4)
MARGIN = 12 * mm


# ── Page background ──────────────────────────────────────────────────────────

def _bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG_DARK)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Top accent
    canvas.setFillColor(AMBER)
    canvas.rect(0, PAGE_H - 2 * mm, PAGE_W, 2 * mm, fill=1, stroke=0)

    # Footer
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 10 * mm, PAGE_W - MARGIN, 10 * mm)
    canvas.setFont("Helvetica", 5.5)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawCentredString(PAGE_W / 2, 6 * mm, f"Annotated Validation Report — Page {doc.page}")
    canvas.drawRightString(
        PAGE_W - MARGIN, 6 * mm,
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
    )
    canvas.restoreState()


# ── Build issue index ────────────────────────────────────────────────────────

def _build_issue_index(
    issues: list[dict],
) -> tuple[dict[int, list[dict]], dict[tuple[int, str], str]]:
    """Build two indexes:
    - row_issues: row_number → [issue, ...]
    - cell_severity: (row_number, field) → worst severity
    """
    row_issues: dict[int, list[dict]] = {}
    cell_severity: dict[tuple[int, str], str] = {}

    severity_rank = {"error": 0, "warning": 1, "info": 2}

    for iss in issues:
        rn = iss.get("row_number")
        if rn is None:
            continue
        row_issues.setdefault(rn, []).append(iss)

        field = iss.get("field")
        if field:
            key = (rn, field.lower().strip())
            existing = cell_severity.get(key)
            if existing is None or severity_rank.get(iss["severity"], 9) < severity_rank.get(existing, 9):
                cell_severity[key] = iss["severity"]

    return row_issues, cell_severity


# ── Column selection ─────────────────────────────────────────────────────────

# For CSV/Excel: show the most relevant columns (skip internal ones)
CSV_DISPLAY_COLS = [
    "transnr", "transtype", "aftale", "artnr", "kanal", "prisgruppe",
    "antal", "stkpris", "stkafregnsats", "beloeb", "bilagsdato", "valuta",
]

PDF_DISPLAY_COLS = [
    "titel", "kontonr", "aftale", "salgskanal", "prisgruppe",
    "sats", "antal", "prisgrundlag", "royalty_amount",
    "fordeling_amount", "afgift", "til_udbetaling",
]


def _pick_columns(rows: list[dict], source: str) -> list[str]:
    """Choose which columns to display based on source type."""
    preferred = PDF_DISPLAY_COLS if source == "pdf" else CSV_DISPLAY_COLS

    # Only keep columns that actually have data
    available = set()
    for r in rows[:50]:  # sample first 50 rows
        for k, v in r.items():
            if not k.startswith("_") and v:
                available.add(k)

    cols = [c for c in preferred if c in available]

    # Add any remaining non-internal columns not in the preferred list
    for key in sorted(available):
        if key not in cols and not key.startswith("_"):
            cols.append(key)

    return cols[:14]  # Cap at 14 columns to fit the page


def _col_label(col: str) -> str:
    """Human-readable column header."""
    return col.replace("_", " ").title()


# ── Main function ────────────────────────────────────────────────────────────

def generate_annotated_pdf(
    *,
    file_path: str,
    file_format: str,
    filename: str,
    validation_id: str,
    total_rows: int,
    issues: list[dict],
) -> bytes:
    """Render the original data as a table PDF with issue highlights."""
    buf = io.BytesIO()

    frame = Frame(MARGIN, 13 * mm, PAGE_W - 2 * MARGIN, PAGE_H - 20 * mm, id="main")
    tmpl = PageTemplate(id="main", frames=[frame], onPage=_bg)
    doc = BaseDocTemplate(buf, pagesize=landscape(A4), pageTemplates=[tmpl])

    story: list = []
    usable_w = PAGE_W - 2 * MARGIN

    # Parse the original file
    rows = parse_file(Path(file_path), file_format)
    if not rows:
        story.append(Paragraph("No data rows found in the uploaded file.", S_SUBTITLE))
        doc.build(story)
        return buf.getvalue()

    source = rows[0].get("_source", "csv")
    columns = _pick_columns(rows, source)

    # Build issue indexes
    row_issues, cell_severity = _build_issue_index(issues)

    issue_count = len(issues)
    affected_rows = len(row_issues)

    # ── Title ────────────────────────────────────────────────────────────
    story.append(Paragraph("Annotated Validation Report", S_TITLE))
    story.append(Spacer(1, 1.5 * mm))
    story.append(Paragraph(
        f"<b>{filename}</b> &nbsp;·&nbsp; {len(rows)} rows &nbsp;·&nbsp; "
        f"{issue_count} issues across {affected_rows} rows",
        S_SUBTITLE,
    ))
    story.append(Spacer(1, 3 * mm))

    # ── Legend ────────────────────────────────────────────────────────────
    red_hex = RED.hexval()[2:]
    amber_hex = AMBER.hexval()[2:]
    sky_hex = SKY.hexval()[2:]
    emerald_hex = EMERALD.hexval()[2:]
    legend_text = (
        f'<font color="#{red_hex}">■</font> Error &nbsp;&nbsp;'
        f'<font color="#{amber_hex}">■</font> Warning &nbsp;&nbsp;'
        f'<font color="#{sky_hex}">■</font> Info &nbsp;&nbsp;'
        f'<font color="#{emerald_hex}">■</font> OK'
    )
    story.append(Paragraph(legend_text, S_LEGEND))
    story.append(Spacer(1, 3 * mm))

    # ── Column widths ────────────────────────────────────────────────────
    n_cols = len(columns)
    # Reserve space for row number column + annotation column
    row_num_w = 22
    annot_w = min(120, usable_w * 0.18)
    data_w = usable_w - row_num_w - annot_w
    col_w = data_w / max(n_cols, 1)
    col_widths = [row_num_w] + [col_w] * n_cols + [annot_w]

    # ── Header row ───────────────────────────────────────────────────────
    header = [Paragraph("#", S_HEADER)]
    for c in columns:
        header.append(Paragraph(_col_label(c), S_HEADER))
    header.append(Paragraph("Issues", S_HEADER))

    # ── Data rows ────────────────────────────────────────────────────────
    CHUNK = 40  # rows per page/table to avoid memory issues
    all_table_data = [header]
    style_cmds: list[tuple] = [
        # Header styling
        ("BACKGROUND", (0, 0), (-1, 0), BG_CARD),
        ("TEXTCOLOR", (0, 0), (-1, 0), TEXT_DIM),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, BORDER),
        # Global
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
    ]

    for idx, row_data in enumerate(rows):
        rn = row_data.get("_row_number", idx + 1)
        table_row_idx = len(all_table_data)  # 1-based after header

        # Determine if this row has issues
        row_iss = row_issues.get(rn, [])
        has_issues = len(row_iss) > 0

        # Row background (alternating)
        row_bg = BG_ROW_ODD if idx % 2 else BG_ROW_EVEN
        if has_issues:
            # Use the worst severity colour for the row indicator
            worst = min(row_iss, key=lambda i: {"error": 0, "warning": 1, "info": 2}.get(i["severity"], 9))
            _, row_hl, _ = SEVERITY_COLORS[worst["severity"]]
            row_bg = row_hl

        style_cmds.append(("BACKGROUND", (0, table_row_idx), (-1, table_row_idx), row_bg))

        # Row number cell
        rn_style = S_CELL
        if has_issues:
            worst_sev = min(row_iss, key=lambda i: {"error": 0, "warning": 1, "info": 2}.get(i["severity"], 9))["severity"]
            color, _, marker = SEVERITY_COLORS[worst_sev]
            rn_hex = color.hexval()[2:]
            cells = [Paragraph(f'<font color="#{rn_hex}"><b>{rn}</b></font>', S_CELL)]
        else:
            cells = [Paragraph(str(rn), _s(f"rn_{idx}", fontSize=6.5, leading=8, textColor=TEXT_MUTED))]

        # Data cells
        for col in columns:
            val = row_data.get(col, "")
            if len(str(val)) > 30:
                val = str(val)[:28] + "…"

            cell_key = (rn, col.lower().strip())
            sev = cell_severity.get(cell_key)
            if sev:
                cell_style = CELL_STYLE_MAP[sev]
                color_obj, hl_bg, _ = SEVERITY_COLORS[sev]
                # Highlight this specific cell
                col_idx = columns.index(col) + 1  # +1 for row number col
                style_cmds.append(("BACKGROUND", (col_idx, table_row_idx), (col_idx, table_row_idx), hl_bg))
            else:
                cell_style = S_CELL

            cells.append(Paragraph(str(val), cell_style))

        # Annotation cell — compact issue descriptions
        if row_iss:
            annotations = []
            for iss in row_iss[:3]:  # max 3 per row to save space
                sev = iss["severity"]
                color_obj, _, marker = SEVERITY_COLORS[sev]
                c_hex = color_obj.hexval()[2:]
                field_str = f" [{iss['field']}]" if iss.get("field") else ""
                msg = iss["message"]
                if len(msg) > 60:
                    msg = msg[:58] + "…"
                annotations.append(
                    f'<font color="#{c_hex}"><b>{marker}</b></font> {msg}{field_str}'
                )
            if len(row_iss) > 3:
                annotations.append(f"… +{len(row_iss) - 3} more")
            cells.append(Paragraph("<br/>".join(annotations), S_ANNOT))
        else:
            cells.append(Paragraph("", S_ANNOT))

        all_table_data.append(cells)

        # Emit table in chunks to avoid oversized single tables
        if len(all_table_data) > CHUNK:
            t = Table(all_table_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle(style_cmds))
            story.append(t)
            story.append(PageBreak())
            # Reset for next chunk
            all_table_data = [header]
            style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), BG_CARD),
                ("TEXTCOLOR", (0, 0), (-1, 0), TEXT_DIM),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
            ]

    # Emit remaining rows
    if len(all_table_data) > 1:
        t = Table(all_table_data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle(style_cmds))
        story.append(t)

    # ── Build ────────────────────────────────────────────────────────────
    doc.build(story)
    return buf.getvalue()
