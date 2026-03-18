"""Rule 5: Guarantee Validation — checks guarantee deductions within the file."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue


class GuaranteeValidationRule(BaseRule):
    """Validates guarantee balance deductions within the uploaded file.

    For PDFs: checks that 'Rest global garanti' deductions are negative and
    don't make the payout negative (impossible state).
    For CSV/Excel: checks paired guarantee/offset matching.
    """

    @property
    def rule_id(self) -> str:
        return "guarantee_validation"

    @property
    def description(self) -> str:
        return "Guarantee deductions must be valid and balance within the file"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        # PDF summary rows
        for row in statement_data:
            if row.get("_record_type") != "page_summary":
                continue

            row_num = row.get("_row_number")
            garanti = row.get("rest_garanti", "")
            udbetaling = row.get("til_udbetaling", "")

            if not garanti:
                continue

            try:
                garanti_val = float(garanti)
            except (ValueError, TypeError):
                continue

            # Guarantee should be a negative deduction (or zero)
            if garanti_val > 0:
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="rest_garanti",
                        expected_value="<= 0",
                        actual_value=str(garanti_val),
                        message=f"Global guarantee is positive ({garanti_val}) — expected a deduction",
                        context={"aftale": row.get("aftale", "")},
                    )
                )

            # Check if payout went negative (impossible state)
            if udbetaling:
                try:
                    payout = float(udbetaling)
                    if payout < 0:
                        issues.append(
                            ValidationIssue(
                                severity=Severity.ERROR,
                                rule_id=self.rule_id,
                                rule_description=self.description,
                                row_number=row_num,
                                field="til_udbetaling",
                                expected_value=">= 0",
                                actual_value=str(payout),
                                message="Payout is negative after guarantee deduction — impossible state",
                                context={
                                    "aftale": row.get("aftale", ""),
                                    "rest_garanti": str(garanti_val),
                                },
                            )
                        )
                except (ValueError, TypeError):
                    pass

        # CSV/Excel paired guarantee check
        guarantees: dict[str, float] = {}
        offsets: dict[str, float] = {}
        for row in statement_data:
            transtype = row.get("transtype", "").lower()
            aftale = row.get("aftale", "")
            beloeb = row.get("beloeb", "")
            if not transtype or not aftale or not beloeb:
                continue
            try:
                amount = float(beloeb)
            except (ValueError, TypeError):
                continue

            if "garanti" in transtype and "mod" not in transtype:
                guarantees[aftale] = guarantees.get(aftale, 0) + amount
            elif "garanti" in transtype and "mod" in transtype:
                offsets[aftale] = offsets.get(aftale, 0) + amount

        for aftale, guar_amount in guarantees.items():
            if aftale not in offsets:
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=None,
                        field="guarantee/offset",
                        expected_value="matching offset",
                        actual_value="no offset found",
                        message=(
                            f"Guarantee for agreement {aftale} ({guar_amount:.2f}) "
                            "has no matching offset in this file — may exist in prior settlements"
                        ),
                        context={"aftale": aftale},
                    )
                )

        return issues
