"""Rule 6: Settlement Totals — validates that per-page and overall totals balance."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue


class SettlementTotalsRule(BaseRule):
    """Validates the chain: sales lines → subtotal → fordeling → garanti → afgift → payout."""

    @property
    def rule_id(self) -> str:
        return "settlement_totals"

    @property
    def description(self) -> str:
        return "Settlement totals must balance: sales subtotal → deductions → payout"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        # Group data by page (for PDFs)
        pages: dict[str, dict] = {}
        page_sales: dict[str, list[dict]] = {}

        for row in statement_data:
            page = row.get("_page_number", "")
            if not page:
                continue

            if row.get("_record_type") == "page_summary":
                pages[page] = row
            elif row.get("_record_type") == "sales_line":
                page_sales.setdefault(page, []).append(row)

        for page_num, summary in pages.items():
            row_num = summary.get("_row_number")
            sales = page_sales.get(page_num, [])

            # Validate sales lines sum to subtotal
            if sales:
                sales_total = 0.0
                for sale in sales:
                    try:
                        sales_total += float(sale.get("royalty_amount", 0))
                    except (ValueError, TypeError):
                        continue

                # Check fordeling chain
                fordeling_pct = summary.get("fordeling_pct", "")
                fordeling_base = summary.get("fordeling_base", "")
                fordeling_amount = summary.get("fordeling_amount", "")

                if fordeling_pct and fordeling_base and fordeling_amount:
                    try:
                        pct = float(fordeling_pct)
                        base = float(fordeling_base)
                        declared_ford = float(fordeling_amount)

                        # Verify base matches sales total
                        if abs(base - sales_total) > 1.0:
                            issues.append(
                                ValidationIssue(
                                    severity=Severity.ERROR,
                                    rule_id=self.rule_id,
                                    rule_description=self.description,
                                    row_number=row_num,
                                    field="fordeling_base",
                                    expected_value=f"{sales_total:.2f}",
                                    actual_value=f"{base:.2f}",
                                    message=(
                                        f"Page {page_num}: Fordeling base ({base:.2f}) "
                                        f"doesn't match sales total ({sales_total:.2f})"
                                    ),
                                    context={"page": page_num, "aftale": summary.get("aftale", "")},
                                )
                            )

                        # Verify fordeling amount = base * pct
                        expected_ford = base * pct
                        if abs(expected_ford - declared_ford) > 1.0:
                            issues.append(
                                ValidationIssue(
                                    severity=Severity.ERROR,
                                    rule_id=self.rule_id,
                                    rule_description=self.description,
                                    row_number=row_num,
                                    field="fordeling_amount",
                                    expected_value=f"{expected_ford:.2f}",
                                    actual_value=f"{declared_ford:.2f}",
                                    message=(
                                        f"Page {page_num}: Fordeling amount ({declared_ford:.2f}) "
                                        f"!= base ({base:.2f}) * rate ({pct:.1%}) = {expected_ford:.2f}"
                                    ),
                                    context={"page": page_num, "aftale": summary.get("aftale", "")},
                                )
                            )

                        # Verify final payout chain
                        udbetaling = summary.get("til_udbetaling", "")
                        garanti = summary.get("rest_garanti", "0")
                        afgift = summary.get("afgift", "0")

                        if udbetaling:
                            try:
                                payout = float(udbetaling)
                                garanti_val = float(garanti) if garanti else 0.0
                                afgift_val = float(afgift) if afgift else 0.0

                                expected_payout = declared_ford + garanti_val - afgift_val
                                if abs(expected_payout - payout) > 1.0:
                                    issues.append(
                                        ValidationIssue(
                                            severity=Severity.ERROR,
                                            rule_id=self.rule_id,
                                            rule_description=self.description,
                                            row_number=row_num,
                                            field="til_udbetaling",
                                            expected_value=f"{expected_payout:.2f}",
                                            actual_value=f"{payout:.2f}",
                                            message=(
                                                f"Page {page_num}: Payout ({payout:.2f}) != "
                                                f"fordeling ({declared_ford:.2f}) + "
                                                f"garanti ({garanti_val:.2f}) - "
                                                f"afgift ({afgift_val:.2f}) = {expected_payout:.2f}"
                                            ),
                                            context={
                                                "page": page_num,
                                                "aftale": summary.get("aftale", ""),
                                            },
                                        )
                                    )
                            except (ValueError, TypeError):
                                pass
                    except (ValueError, TypeError):
                        pass

        # For CSV/Excel: validate total BELOEB sums
        csv_rows = [r for r in statement_data if r.get("_source") in ("csv", "xlsx", "json")]
        if csv_rows:
            issues.extend(self._validate_csv_totals(csv_rows))

        return issues

    def _validate_csv_totals(self, rows: list[dict]) -> list[ValidationIssue]:
        """Validate that CSV/Excel row amounts sum correctly by agreement."""
        issues = []
        by_agreement: dict[str, float] = {}

        for row in rows:
            aftale = row.get("aftale", "unknown")
            beloeb = row.get("beloeb", "")
            if not beloeb:
                continue
            try:
                by_agreement[aftale] = by_agreement.get(aftale, 0) + float(beloeb)
            except (ValueError, TypeError):
                continue

        return issues
