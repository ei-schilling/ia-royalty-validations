"""Rule 9: Advance Balance — checks that advance offsets don't exceed originals."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue


class AdvanceBalanceRule(BaseRule):
    """Validates that advance recoupment offsets do not exceed the original advance."""

    @property
    def rule_id(self) -> str:
        return "advance_balance"

    @property
    def description(self) -> str:
        return "Advance offsets must not exceed the original advance amount"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        # Collect advances and offsets per agreement
        advances: dict[str, float] = {}
        offsets: dict[str, float] = {}

        for row in statement_data:
            transtype = row.get("transtype", "").lower()
            aftale = row.get("aftale", "")
            beloeb = row.get("beloeb", "")

            if not transtype or not aftale or not beloeb:
                continue

            try:
                amount = abs(float(beloeb))
            except (ValueError, TypeError):
                continue

            if "forskud" in transtype and "mod" not in transtype:
                advances[aftale] = advances.get(aftale, 0) + amount
            elif "forskud" in transtype and "mod" in transtype:
                offsets[aftale] = offsets.get(aftale, 0) + amount

        for aftale, offset_total in offsets.items():
            advance_total = advances.get(aftale, 0)
            if offset_total > advance_total and advance_total > 0:
                # advance_total == 0 means the original advance was paid in a prior
                # settlement file that is not present in this upload. We cannot
                # determine over-recoupment without the original amount, so we skip
                # rather than raising a false positive.
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=None,
                        field="advance/offset",
                        expected_value=f"<= {advance_total:.2f}",
                        actual_value=f"{offset_total:.2f}",
                        message=(
                            f"Advance offset ({offset_total:.2f}) exceeds original advance "
                            f"({advance_total:.2f}) for agreement {aftale}"
                        ),
                        context={"aftale": aftale},
                    )
                )

        return issues
