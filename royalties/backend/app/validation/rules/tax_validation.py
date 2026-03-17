"""Rule 4: Tax Validation — structural checks on tax/duty deductions."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue


class TaxValidationRule(BaseRule):
    """Checks structural validity of tax/duty (Afgift) deductions.

    v1: Can only verify that duty lines are present and are negative deductions.
    Full tax rate validation requires reference data (v2).
    """

    @property
    def rule_id(self) -> str:
        return "tax_validation"

    @property
    def description(self) -> str:
        return "Tax/duty (Afgift) lines must be present and structurally valid"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        for row in statement_data:
            if row.get("_record_type") != "page_summary":
                continue

            row_num = row.get("_row_number")
            afgift = row.get("afgift", "")

            if not afgift:
                # Afgift field not present — ok, many pages don't have it
                continue

            try:
                afgift_val = float(afgift)
            except (ValueError, TypeError):
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="afgift",
                        expected_value="numeric value",
                        actual_value=afgift,
                        message=f"Duty/tax amount is not numeric: '{afgift}'",
                        context={"aftale": row.get("aftale", "")},
                    )
                )
                continue

            # Duty should be zero or a negative deduction
            if afgift_val > 0:
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="afgift",
                        expected_value="<= 0 (deduction)",
                        actual_value=str(afgift_val),
                        message=f"Duty/tax amount is positive ({afgift_val}) — expected a deduction (negative or zero)",
                        context={"aftale": row.get("aftale", "")},
                    )
                )

        return issues
