"""Rule 14: Text Within Margins — checks field lengths and row/column size limits."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue

# Internal parser metadata keys — never measured.
_INTERNAL_KEYS = frozenset({
    "_row_number", "_source", "_encoding", "_record_type",
    "_page_number", "_page_num",
})

# Per-field character length limits: (max_length, severity).
_FIELD_LIMITS: dict[str, tuple[int, Severity]] = {
    # Key/ID fields — errors: Schilling ERP truncates silently at import.
    "artnr":      (20,  Severity.ERROR),
    "aftale":     (20,  Severity.ERROR),
    "kontonr":    (20,  Severity.ERROR),
    "transtype":  (30,  Severity.ERROR),
    # Text/label fields — warnings: display may be clipped but import survives.
    "titel":      (200, Severity.WARNING),
    "aftalenavn": (50,  Severity.WARNING),
    "bilagsnr":   (30,  Severity.WARNING),
    "kanal":      (50,  Severity.WARNING),
    "prisgruppe": (50,  Severity.WARNING),
    # Numeric fields — warnings: long values suggest formatting issues.
    "beloeb":          (20, Severity.WARNING),
    "liniebeloeb":     (20, Severity.WARNING),
    "antal":           (20, Severity.WARNING),
    "stkpris":         (20, Severity.WARNING),
    "stkafregnpris":   (20, Severity.WARNING),
    "stkafregnsats":   (20, Severity.WARNING),
    "fordeling_pct":   (20, Severity.WARNING),
    "afgift":          (20, Severity.WARNING),
}

# Hard ceiling for any field — beyond this, truncation is certain.
_ABSOLUTE_MAX = 500

# CSV/Excel limits.
_CSV_CELL_MAX = 255       # Excel cell limit for many import operations
_CSV_ROW_TOTAL_MAX = 2000 # total chars across all fields in one row
_CSV_HEADER_MAX = 50      # column header length

# PDF sales-line column count limit.

# PDF fields expected on a single line (value must not contain a newline).
_PDF_SINGLE_LINE_FIELDS = frozenset({
    "titel", "kontonr", "aftale", "periode",
    "fordeling_amount", "til_udbetaling", "rest_garanti",
})


class TextWithinMarginsRule(BaseRule):
    """Checks that field values and rows stay within defined character limits.

    Three categories of checks:
    - Per-field length limits (see _FIELD_LIMITS).
    - Absolute maximum of 500 chars for any single field value.
    - CSV/Excel: cell values >255 chars, row totals >2000 chars, header >50 chars.
    - PDF: sales-line column count >6, multi-line values in single-line fields.
    """

    @property
    def rule_id(self) -> str:
        return "text_within_margins"

    @property
    def description(self) -> str:
        return "Field values must stay within defined character length limits"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        # Track which column headers have already been flagged (once per run).
        flagged_headers: set[str] = set()

        for row in statement_data:
            row_num = row.get("_row_number")
            source = row.get("_source", "")
            record_type = row.get("_record_type", "")

            row_total_chars = 0
            data_fields = {k: v for k, v in row.items() if k not in _INTERNAL_KEYS and isinstance(v, str)}

            for field, value in data_fields.items():
                length = len(value)
                row_total_chars += length

                # --- Absolute ceiling: any field > 500 chars ---
                if length > _ABSOLUTE_MAX:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field=field,
                        expected_value=f"<= {_ABSOLUTE_MAX} chars",
                        actual_value=str(length),
                        message=(
                            f"Field '{field}' is {length} chars — exceeds absolute maximum "
                            f"of {_ABSOLUTE_MAX} chars (truncation risk at import)"
                        ),
                        context={"preview": value[:40], "limit": _ABSOLUTE_MAX},
                    ))
                    continue  # absolute max already reported; skip per-field check

                # --- Per-field limits ---
                if field in _FIELD_LIMITS:
                    limit, sev = _FIELD_LIMITS[field]
                    if length > limit:
                        issues.append(ValidationIssue(
                            severity=sev,
                            rule_id=self.rule_id,
                            rule_description=self.description,
                            row_number=row_num,
                            field=field,
                            expected_value=f"<= {limit} chars",
                            actual_value=str(length),
                            message=(
                                f"Field '{field}' is {length} chars — exceeds limit of {limit}"
                            ),
                            context={"preview": value[:40], "limit": limit},
                        ))

                # --- CSV/Excel: cell value > 255 chars ---
                if source in ("csv", "xlsx") and length > _CSV_CELL_MAX:
                    # Only report if not already caught by per-field or absolute check.
                    limit_already_reported = (
                        field in _FIELD_LIMITS and _FIELD_LIMITS[field][0] <= _CSV_CELL_MAX
                    ) or length > _ABSOLUTE_MAX
                    if not limit_already_reported:
                        issues.append(ValidationIssue(
                            severity=Severity.WARNING,
                            rule_id=self.rule_id,
                            rule_description=self.description,
                            row_number=row_num,
                            field=field,
                            expected_value=f"<= {_CSV_CELL_MAX} chars",
                            actual_value=str(length),
                            message=(
                                f"Field '{field}' is {length} chars — exceeds Excel cell limit "
                                f"of {_CSV_CELL_MAX} chars"
                            ),
                            context={"preview": value[:40], "limit": _CSV_CELL_MAX},
                        ))

                # --- CSV/Excel: column header too long (flag once per header name) ---
                if source in ("csv", "xlsx") and field not in flagged_headers and len(field) > _CSV_HEADER_MAX:
                    flagged_headers.add(field)
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=None,
                        field=field,
                        expected_value=f"header <= {_CSV_HEADER_MAX} chars",
                        actual_value=str(len(field)),
                        message=(
                            f"Column header '{field}' is {len(field)} chars — "
                            f"exceeds {_CSV_HEADER_MAX}-char import mapping limit"
                        ),
                        context={"limit": _CSV_HEADER_MAX},
                    ))

                # --- PDF: single-line fields must not contain newlines ---
                if source == "pdf" and field in _PDF_SINGLE_LINE_FIELDS and "\n" in value:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field=field,
                        expected_value="single-line value",
                        actual_value=repr(value[:60]),
                        message=(
                            f"PDF field '{field}' spans multiple lines — "
                            f"expected a single-line value"
                        ),
                        context={"preview": value[:40]},
                    ))

            # --- CSV/Excel: row total > 2000 chars ---
            if source in ("csv", "xlsx") and row_total_chars > _CSV_ROW_TOTAL_MAX:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=row_num,
                    field=None,
                    expected_value=f"<= {_CSV_ROW_TOTAL_MAX} total chars per row",
                    actual_value=str(row_total_chars),
                    message=(
                        f"Row {row_num} total character length is {row_total_chars} — "
                        f"exceeds {_CSV_ROW_TOTAL_MAX}-char row limit"
                    ),
                    context={"total_chars": row_total_chars, "limit": _CSV_ROW_TOTAL_MAX},
                ))

        return issues
