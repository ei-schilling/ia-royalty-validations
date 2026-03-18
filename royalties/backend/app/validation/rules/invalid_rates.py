"""Rule 2: Invalid Rates — checks that royalty rates are present and reasonable."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue
from app.config import settings


class InvalidRatesRule(BaseRule):
    """Checks that royalty rates are present, non-negative, and within expected bounds."""

    @property
    def rule_id(self) -> str:
        return "invalid_rates"

    @property
    def description(self) -> str:
        return "Royalty rate must be present, non-negative, and within reasonable bounds"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []
        for row in statement_data:
            if row.get("_record_type") == "page_summary":
                continue

            row_num = row.get("_row_number")
            source = row.get("_source", "")

            # Get rate value from the appropriate field
            rate_str = row.get("stkafregnsats", "") or row.get("sats_value", "")
            if not rate_str:
                # Skip rows that don't have rate info (metadata rows, etc.)
                continue

            try:
                rate = float(rate_str)
            except (ValueError, TypeError):
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=row_num,
                    field="stkafregnsats",
                    expected_value="numeric value",
                    actual_value=rate_str,
                    message=f"Royalty rate is not a valid number: '{rate_str}'",
                    context={"aftale": row.get("aftale", ""), "artnr": row.get("artnr", "")},
                ))
                continue

            sats_type = row.get("sats_type", "percentage")

            if sats_type == "percentage":
                rate_fraction = rate / 100.0
                if rate < 0:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="stkafregnsats",
                        expected_value=">= 0",
                        actual_value=str(rate),
                        message=f"Royalty rate is negative: {rate}",
                        context={"aftale": row.get("aftale", ""), "artnr": row.get("artnr", "")},
                    ))
                elif rate == 0:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="stkafregnsats",
                        expected_value="> 0",
                        actual_value="0",
                        message="Royalty rate is zero — likely a configuration error",
                        context={"aftale": row.get("aftale", ""), "artnr": row.get("artnr", "")},
                    ))
                elif rate > settings.max_rate_threshold:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="stkafregnsats",
                        expected_value=f"<= {settings.max_rate_threshold}",
                        actual_value=str(rate),
                        message=f"Royalty rate {rate:.1f}% exceeds typical threshold "
                                f"({settings.max_rate_threshold:.0f}%)",
                        context={"aftale": row.get("aftale", ""), "artnr": row.get("artnr", "")},
                    ))
                # Use rate_fraction for any downstream calculations if needed
            else:
                # Fixed-rate (kr.) — just check it's positive
                if rate <= 0:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="stkafregnsats",
                        expected_value="> 0",
                        actual_value=str(rate),
                        message=f"Fixed royalty rate must be positive, got: {rate}",
                        context={"aftale": row.get("aftale", ""), "artnr": row.get("artnr", "")},
                    ))

        return issues
