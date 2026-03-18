"""PDF report generation for validation runs.

Produces a polished, professional PDF summarizing validation results
with a dark-themed design, colour-coded severity sections, and clear metrics.
"""

from __future__ import annotations

import io
import math
from datetime import datetime

from reportlab.graphics.shapes import Circle, Drawing, Group, Line, String
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── Colour palette (matches the dark UI) ────────────────────────────────────

BG_DARK = HexColor("#111118")
BG_CARD = HexColor("#18181f")
BG_CARD_ALT = HexColor("#1e1e27")
BORDER_SUBTLE = HexColor("#2a2a35")
TEXT_PRIMARY = HexColor("#f0f0f5")
TEXT_SECONDARY = HexColor("#8b8b9e")
TEXT_MUTED = HexColor("#5a5a6e")

AMBER = HexColor("#e8a230")
EMERALD = HexColor("#34d399")
RED = HexColor("#f87171")
SKY = HexColor("#38bdf8")
AMBER_BG = HexColor("#2a2215")
EMERALD_BG = HexColor("#12261e")
RED_BG = HexColor("#2a1515")
SKY_BG = HexColor("#121e2a")

# ── Typography ───────────────────────────────────────────────────────────────

_BASE_FONT = "Helvetica"
_BASE_COLOR = TEXT_PRIMARY


def _style(name: str, **kw) -> ParagraphStyle:
    """Create a ParagraphStyle with sensible defaults."""
    kw.setdefault("fontName", _BASE_FONT)
    kw.setdefault("textColor", _BASE_COLOR)
    return ParagraphStyle(name, **kw)


STYLES = {
    "title": _style("title", fontSize=22, leading=28, alignment=TA_LEFT),
    "subtitle": _style("subtitle", fontSize=10, leading=14, textColor=TEXT_SECONDARY),
    "heading": _style("heading", fontSize=13, leading=18, fontName="Helvetica-Bold"),
    "body": _style("body", fontSize=9, leading=13),
    "body_muted": _style("body_muted", fontSize=8, leading=11, textColor=TEXT_SECONDARY),
    "metric_value": _style("metric_value", fontSize=26, leading=30, fontName="Helvetica-Bold", alignment=TA_CENTER),
    "metric_label": _style("metric_label", fontSize=8, leading=11, textColor=TEXT_SECONDARY, alignment=TA_CENTER),
    "small_mono": _style("small_mono", fontSize=7, leading=10, fontName="Courier", textColor=TEXT_MUTED),
    "section_title": _style("section_title", fontSize=11, leading=15, fontName="Helvetica-Bold"),
    "footer": _style("footer", fontSize=7, leading=10, textColor=TEXT_MUTED, alignment=TA_CENTER),
    "cell": _style("cell", fontSize=8, leading=11),
    "cell_bold": _style("cell_bold", fontSize=8, leading=11, fontName="Helvetica-Bold"),
}

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm

# ── All known rules (mirrors frontend) ──────────────────────────────────────

ALL_RULES: list[dict[str, str]] = [
    {"rule_id": "missing_titles", "description": "Every row must have a product identifier (ISBN, Artnr, or Titel)"},
    {"rule_id": "invalid_rates", "description": "Royalty rate must be present, non-negative, and within reasonable bounds"},
    {"rule_id": "amount_consistency", "description": "Quantity × Unit Price × Rate must equal the reported royalty amount"},
    {"rule_id": "tax_validation", "description": "Tax/duty (Afgift) lines must be present and structurally valid"},
    {"rule_id": "guarantee_validation", "description": "Guarantee deductions must be valid and balance within the file"},
    {"rule_id": "settlement_totals", "description": "Settlement totals must balance: sales subtotal → deductions → payout"},
    {"rule_id": "duplicate_entries", "description": "No two rows should share the same key dimensions unless intentional"},
    {"rule_id": "date_validation", "description": "Dates must be within valid settlement period ranges"},
    {"rule_id": "advance_balance", "description": "Advance offsets must not exceed the original advance amount"},
    {"rule_id": "recipient_shares", "description": "Co-author/recipient percentage shares must sum to ≤ 100%"},
    {"rule_id": "transaction_types", "description": "Transaction type must be a recognized Schilling type"},
]


def _format_rule_id(rule_id: str) -> str:
    return " ".join(w.capitalize() for w in rule_id.split("_"))


# ── Drawing helpers ──────────────────────────────────────────────────────────

def _pass_rate_ring(rate: int, size: float = 62) -> Drawing:
    """Create a circular pass-rate gauge."""
    d = Drawing(size, size)
    cx, cy, r = size / 2, size / 2, size / 2 - 4

    # Background ring
    d.add(Circle(cx, cy, r, strokeColor=BORDER_SUBTLE, strokeWidth=5, fillColor=None))

    # Foreground arc (approximated with line segments)
    color = EMERALD if rate == 100 else AMBER
    segments = max(1, int(rate / 100 * 60))
    g = Group()
    for i in range(segments):
        angle_start = math.radians(90 - (i * 360 * rate / 100 / 60))
        angle_end = math.radians(90 - ((i + 1) * 360 * rate / 100 / 60))
        x1 = cx + r * math.cos(angle_start)
        y1 = cy + r * math.sin(angle_start)
        x2 = cx + r * math.cos(angle_end)
        y2 = cy + r * math.sin(angle_end)
        g.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=5, strokeLineCap=1))
    d.add(g)

    # Centre text
    d.add(String(cx, cy + 4, f"{rate}%", fontSize=16, fontName="Helvetica-Bold",
                 fillColor=TEXT_PRIMARY, textAnchor="middle"))
    d.add(String(cx, cy - 8, "PASS RATE", fontSize=5, fontName="Helvetica",
                 fillColor=TEXT_SECONDARY, textAnchor="middle"))
    return d


def _severity_dot(color: Color, size: float = 6) -> Drawing:
    """Tiny coloured dot for severity indicators."""
    d = Drawing(size, size)
    d.add(Circle(size / 2, size / 2, size / 2, fillColor=color, strokeColor=None))
    return d


# ── Page backgrounds ─────────────────────────────────────────────────────────

def _draw_page_bg(canvas, doc):
    """Dark background with subtle header accent and footer."""
    canvas.saveState()

    # Full-page dark background
    canvas.setFillColor(BG_DARK)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Top accent bar
    canvas.setFillColor(AMBER)
    canvas.rect(0, PAGE_H - 3 * mm, PAGE_W, 3 * mm, fill=1, stroke=0)

    # Subtle gradient band at top
    for i in range(20):
        opacity = 0.03 * (1 - i / 20)
        canvas.setFillColor(Color(0.91, 0.64, 0.19, opacity))
        canvas.rect(0, PAGE_H - 3 * mm - (i + 1) * 2 * mm, PAGE_W, 2 * mm, fill=1, stroke=0)

    # Footer line
    canvas.setStrokeColor(BORDER_SUBTLE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 14 * mm, PAGE_W - MARGIN, 14 * mm)

    # Footer text
    canvas.setFont("Helvetica", 6)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawCentredString(PAGE_W / 2, 9 * mm, f"Royalty Statement Validator — Page {doc.page}")
    canvas.drawRightString(
        PAGE_W - MARGIN, 9 * mm,
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
    )

    canvas.restoreState()


# ── Card helper ──────────────────────────────────────────────────────────────

def _card_table(data, col_widths, bg=BG_CARD, extra_style=None):
    """Wrap content in a card-like table with styling."""
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_PRIMARY),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDER_SUBTLE),
    ]
    if extra_style:
        style_cmds.extend(extra_style)
    t = Table(data, colWidths=col_widths, repeatRows=0)
    t.setStyle(TableStyle(style_cmds))
    return t


def _metric_cell(value: str, label: str, color: Color) -> list:
    """Two-line metric for the summary strip."""
    return [
        Paragraph(f'<font color="#{color.hexval()[2:]}">{value}</font>', STYLES["metric_value"]),
        Paragraph(label, STYLES["metric_label"]),
    ]


# ── Main generation function ─────────────────────────────────────────────────

def generate_validation_pdf(
    *,
    filename: str,
    validation_id: str,
    started_at: datetime | None,
    completed_at: datetime | None,
    total_rows: int,
    rules_executed: int,
    passed_checks: int,
    errors: int,
    warnings: int,
    infos: int,
    issues: list[dict],
) -> bytes:
    """Build a full validation report PDF and return its bytes."""
    buf = io.BytesIO()

    frame = Frame(MARGIN, 18 * mm, PAGE_W - 2 * MARGIN, PAGE_H - 40 * mm, id="main")
    template = PageTemplate(id="main", frames=[frame], onPage=_draw_page_bg)
    doc = BaseDocTemplate(buf, pagesize=A4, pageTemplates=[template])

    story: list = []
    usable_w = PAGE_W - 2 * MARGIN

    # ── Header ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Validation Report", STYLES["title"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"File: <b>{filename}</b>", STYLES["subtitle"]))

    meta_parts = []
    if started_at:
        meta_parts.append(f"Run: {started_at.strftime('%Y-%m-%d %H:%M')}")
    meta_parts.append(f"{rules_executed} rules · {total_rows} rows")
    story.append(Paragraph(" &nbsp;|&nbsp; ".join(meta_parts), STYLES["body_muted"]))
    story.append(Spacer(1, 6 * mm))

    # ── Pass rate + metrics strip ────────────────────────────────────────────
    pass_rate = round(passed_checks / rules_executed * 100) if rules_executed > 0 else 100

    # Build as simple paragraphs instead of a complex table-with-drawings
    rate_color = EMERALD if pass_rate == 100 else AMBER
    rate_hex = rate_color.hexval()[2:]
    emerald_hex = EMERALD.hexval()[2:]
    red_hex = RED.hexval()[2:]
    amber_hex = AMBER.hexval()[2:]
    sky_hex = SKY.hexval()[2:]
    muted_hex = TEXT_SECONDARY.hexval()[2:]

    metrics_row = [[
        Paragraph(
            f'<font size="22" color="#{rate_hex}"><b>{pass_rate}%</b></font>'
            f'<br/><font size="7" color="#{muted_hex}">PASS RATE</font>',
            _style("m0", alignment=TA_CENTER),
        ),
        Paragraph(
            f'<font size="20" color="#{emerald_hex}"><b>{passed_checks}</b></font>'
            f'<br/><font size="7" color="#{muted_hex}">Passed</font>',
            _style("m1", alignment=TA_CENTER),
        ),
        Paragraph(
            f'<font size="20" color="#{red_hex}"><b>{errors}</b></font>'
            f'<br/><font size="7" color="#{muted_hex}">Errors</font>',
            _style("m2", alignment=TA_CENTER),
        ),
        Paragraph(
            f'<font size="20" color="#{amber_hex}"><b>{warnings}</b></font>'
            f'<br/><font size="7" color="#{muted_hex}">Warnings</font>',
            _style("m3", alignment=TA_CENTER),
        ),
        Paragraph(
            f'<font size="20" color="#{sky_hex}"><b>{infos}</b></font>'
            f'<br/><font size="7" color="#{muted_hex}">Info</font>',
            _style("m4", alignment=TA_CENTER),
        ),
    ]]
    m_col = usable_w / 5
    metrics_table = Table(metrics_row, colWidths=[m_col] * 5)
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_CARD),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.5, BORDER_SUBTLE),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 6 * mm))

    # ── Separator ────────────────────────────────────────────────────────────
    sep = Table([[""]], colWidths=[usable_w])
    sep.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDER_SUBTLE),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(sep)
    story.append(Spacer(1, 4 * mm))

    # ── Severity sections ────────────────────────────────────────────────────
    severity_cfg = {
        "error": {"label": "Errors", "color": RED, "bg": RED_BG, "count": errors},
        "warning": {"label": "Warnings", "color": AMBER, "bg": AMBER_BG, "count": warnings},
        "info": {"label": "Informational", "color": SKY, "bg": SKY_BG, "count": infos},
    }

    for sev_key, cfg in severity_cfg.items():
        sev_issues = [i for i in issues if i["severity"] == sev_key]
        color_hex = cfg["color"].hexval()[2:]

        # Section header
        header_text = (
            f'<font color="#{color_hex}">●</font> &nbsp;'
            f'<b>{cfg["label"]}</b> &nbsp;'
            f'<font size="8" color="#{color_hex}">{len(sev_issues)}</font>'
        )
        story.append(Paragraph(header_text, STYLES["section_title"]))
        story.append(Spacer(1, 2 * mm))

        if not sev_issues:
            story.append(Paragraph(
                f'<font color="#{TEXT_SECONDARY.hexval()[2:]}">No {cfg["label"].lower()} for this document.</font>',
                STYLES["body"],
            ))
            story.append(Spacer(1, 4 * mm))
            continue

        # Group by rule_id
        groups: dict[str, list[dict]] = {}
        for issue in sev_issues:
            groups.setdefault(issue["rule_id"], []).append(issue)

        for rule_id, rule_issues in groups.items():
            # Rule sub-header
            desc = rule_issues[0].get("rule_description", rule_id)
            rule_label = _format_rule_id(rule_id)
            story.append(Paragraph(
                f'<font color="#{color_hex}">▸</font> &nbsp;'
                f'<b>{desc}</b> &nbsp;'
                f'<font size="7" color="#{TEXT_MUTED.hexval()[2:]}">{rule_label} · {len(rule_issues)} occurrence{"s" if len(rule_issues) != 1 else ""}</font>',
                STYLES["body"],
            ))
            story.append(Spacer(1, 1.5 * mm))

            # Issue rows as a mini-table
            rows = []
            for iss in rule_issues:
                row_info = f"Row {iss['row_number']}" if iss.get("row_number") else "—"
                field = iss.get("field") or ""
                msg = iss.get("message", "")
                exp = iss.get("expected_value") or ""
                act = iss.get("actual_value") or ""
                detail = msg
                if exp:
                    detail += f"  (expected: {exp})"
                if act:
                    detail += f"  (actual: {act})"
                rows.append([
                    Paragraph(row_info, STYLES["cell_bold"]),
                    Paragraph(field, STYLES["cell"]),
                    Paragraph(detail, STYLES["cell"]),
                ])

            if rows:
                # Header row
                hdr = [
                    Paragraph('<b>Row</b>', STYLES["cell_bold"]),
                    Paragraph('<b>Field</b>', STYLES["cell_bold"]),
                    Paragraph('<b>Detail</b>', STYLES["cell_bold"]),
                ]
                t_data = [hdr] + rows
                detail_w = usable_w - 50 - 80
                t = _card_table(
                    t_data,
                    [50, 80, detail_w],
                    bg=cfg["bg"],
                    extra_style=[
                        ("BACKGROUND", (0, 0), (-1, 0), BG_CARD),
                        ("TEXTCOLOR", (0, 0), (-1, 0), TEXT_SECONDARY),
                        ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ],
                )
                story.append(t)

            story.append(Spacer(1, 3 * mm))

        story.append(Spacer(1, 2 * mm))

    # ── Passed rules ─────────────────────────────────────────────────────────
    error_rule_ids = {i["rule_id"] for i in issues if i["severity"] == "error"}
    passed_rules = [r for r in ALL_RULES if r["rule_id"] not in error_rule_ids]

    emerald_hex = EMERALD.hexval()[2:]
    story.append(Paragraph(
        f'<font color="#{emerald_hex}">●</font> &nbsp;'
        f'<b>Passed Rules</b> &nbsp;'
        f'<font size="8" color="#{emerald_hex}">{len(passed_rules)}</font>',
        STYLES["section_title"],
    ))
    story.append(Spacer(1, 2 * mm))

    if passed_rules:
        rows = []
        for r in passed_rules:
            rows.append([
                Paragraph(f'<font color="#{emerald_hex}">✓</font>', STYLES["cell"]),
                Paragraph(f'<b>{r["description"]}</b>', STYLES["cell"]),
                Paragraph(_format_rule_id(r["rule_id"]), STYLES["small_mono"]),
            ])
        t = _card_table(rows, [20, usable_w - 140, 120], bg=EMERALD_BG)
        story.append(t)
    else:
        story.append(Paragraph(
            f'<font color="#{TEXT_SECONDARY.hexval()[2:]}">No rules passed without errors.</font>',
            STYLES["body"],
        ))

    story.append(Spacer(1, 10 * mm))

    # ── Build ────────────────────────────────────────────────────────────────
    doc.build(story)
    return buf.getvalue()
