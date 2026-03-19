"""Rule 16: Missing Labels — detects PDF pages where field/column lead texts are absent."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue

# Metadata fields that are only extractable when their label prefix is present
# in the PDF text (e.g. "Aftale:", "Kontonr:", "Periode:").  If ALL of these
# are absent on a page that has sales lines, the lead texts are missing.
_EXPECTED_METADATA = ("aftale", "kontonr", "periode", "afregning_nr")


class MissingLabelsRule(BaseRule):
    """Detects PDF pages where structural label texts are missing.

    Schilling PDFs contain field labels such as "Aftalenavn:", "Kontonr.:",
    "Periode:", "ISBN:", "Titel:" etc.  When these lead texts are absent
    (e.g. due to a font rendering issue), the data values are still visible
    but unidentifiable.  The parser relies on these labels to extract metadata,
    so their absence leaves a page_summary row with no aftale/kontonr/periode
    despite the page containing sales line data.
    """

    @property
    def rule_id(self) -> str:
        return "missing_labels"

    @property
    def description(self) -> str:
        return "PDF page is missing field/column label texts (lead texts)"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        # Group PDF rows by page number
        summaries: dict[str, dict] = {}
        sales_by_page: dict[str, list] = {}

        for row in statement_data:
            if row.get("_source") != "pdf":
                continue
            page = row.get("_page_number", "")
            if not page:
                continue
            if row.get("_record_type") == "page_summary":
                summaries[page] = row
            elif row.get("_record_type") == "sales_line":
                sales_by_page.setdefault(page, []).append(row)

        for page_num, summary in summaries.items():
            sales = sales_by_page.get(page_num, [])

            # Two detection paths:
            # 1. Page has sales lines but none of the metadata fields extracted
            #    (labels missing from the agreement/metadata block only).
            # 2. Parser set _no_labels_detected flag: page has substantial text
            #    and digits but zero field labels matched anywhere on the page
            #    (all labels absent — including stock section labels).
            #    Requires sales lines to be present: royalty sum/overview pages
            #    legitimately lack field labels (they use column layouts) but
            #    also have no individual sales line rows.
            no_labels_flag = summary.get("_no_labels_detected") == "true" and bool(sales)
            has_sales_no_meta = bool(sales) and not any(
                summary.get(f) for f in _EXPECTED_METADATA
            )

            if not (no_labels_flag or has_sales_no_meta):
                continue

            row_num = summary.get("_row_number")
            issues.append(
                ValidationIssue(
                    severity=Severity.WARNING,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=row_num,
                    field="aftale/kontonr/periode",
                    expected_value="field labels present in PDF text",
                    actual_value="no labels found",
                    message=(
                        f"Page {page_num}: Field label texts appear to be missing "
                        f"(aftale, kontonr, periode not extractable). "
                        f"The PDF may have a font or rendering issue — "
                        f"data values are present but field labels are absent."
                    ),
                    context={"page": page_num, "sales_line_count": str(len(sales))},
                )
            )

        return issues
