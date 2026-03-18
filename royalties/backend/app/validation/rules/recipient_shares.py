"""Rule 10: Recipient Shares — validates that co-author shares sum to ≤ 100%."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue


from typing import Optional

class RecipientSharesRule(BaseRule):
    """Validates that recipient percentage shares sum to at most 100%."""

    @property
    def rule_id(self) -> str:
        return "recipient_shares"

    @property
    def description(self) -> str:
        return "Co-author/recipient percentage shares must sum to ≤ 100%"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        # Collect fordeling percentages per agreement (PDF data)
        shares: dict[str, list[tuple[float, Optional[int]]]] = {}

        for row in statement_data:
            if row.get("_record_type") != "page_summary":
                continue

            aftale = row.get("aftale", "")
            fordeling_pct = row.get("fordeling_pct", "")
            row_num = row.get("_row_number")

            if not aftale or not fordeling_pct:
                continue

            try:
                pct = float(fordeling_pct)
            except (ValueError, TypeError):
                continue

            shares.setdefault(aftale, []).append((pct, row_num))

        for aftale, pct_list in shares.items():
            total = sum(p for p, _ in pct_list)
            if total > 1.0 + 0.001:  # Small tolerance for floating point
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=pct_list[0][1],
                        field="fordeling_pct",
                        expected_value="<= 100%",
                        actual_value=f"{total:.1%}",
                        message=(
                            f"Recipient shares for agreement {aftale} sum to {total:.1%} "
                            f"(exceeds 100%)"
                        ),
                        context={"aftale": aftale, "shares": [p for p, _ in pct_list]},
                    )
                )
            elif total < 1.0 - 0.001:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=pct_list[0][1],
                    field="fordeling_pct",
                    expected_value="100%",
                    actual_value=f"{total:.1%}",
                    message=(
                        f"Recipient shares for agreement {aftale} sum to only {total:.1%}. "
                        f"Other recipients or the publisher may receive the remaining share, "
                        f"which may not be present in this file."
                    ),
                    context={"aftale": aftale, "shares": [p for p, _ in pct_list]},
                ))

        return issues
