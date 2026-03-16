"""Rule 3: Amount Consistency — validates quantity × price × rate ≈ reported amount."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue
from app.config import settings


class AmountConsistencyRule(BaseRule):
    """Validates that quantity × price × rate equals the reported royalty amount."""

    @property
    def rule_id(self) -> str:
        return "amount_consistency"

    @property
    def description(self) -> str:
        return "Quantity × Unit Price × Rate must equal the reported royalty amount"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []
        for row in statement_data:
            if row.get("_record_type") == "page_summary":
                continue

            row_num = row.get("_row_number")
            source = row.get("_source", "")

            # Get values depending on source format
            if source == "pdf":
                qty_str = row.get("antal", "")
                price_str = row.get("prisgrundlag", "")
                rate_str = row.get("sats_value", "")
                amount_str = row.get("royalty_amount", "")
                sats_type = row.get("sats_type", "percentage")
            else:
                qty_str = row.get("antal", "")
                price_str = row.get("stkpris", "") or row.get("stkafregnpris", "")
                rate_str = row.get("stkafregnsats", "")
                amount_str = row.get("beloeb", "") or row.get("liniebeloeb", "")
                sats_type = "percentage"  # CSV/Excel rates are always fractional

            # Skip rows missing required fields
            if not all([qty_str, price_str, rate_str, amount_str]):
                continue

            try:
                qty = float(qty_str)
                price = float(price_str)
                rate = float(rate_str)
                actual_amount = float(amount_str)
            except (ValueError, TypeError):
                continue  # Non-numeric values caught by other rules

            # Skip zero-quantity rows (no calculation to verify)
            if qty == 0:
                continue

            # Calculate expected amount
            if sats_type == "fixed":
                expected = qty * rate
            else:
                expected = qty * price * rate

            diff = abs(expected - actual_amount)
            tolerance = max(settings.amount_tolerance, abs(expected) * 0.001)

            if diff > 1.0:
                # Large divergence — could be staircase rates or other adjustments
                issues.append(ValidationIssue(
                    severity=Severity.INFO,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=row_num,
                    field="beloeb",
                    expected_value=f"{expected:.2f}",
                    actual_value=f"{actual_amount:.2f}",
                    message=(
                        f"Amount differs by {diff:.2f}. "
                        "May use staircase rates, depreciation, or other adjustments — verify manually"
                    ),
                    context={
                        "qty": str(qty),
                        "price": str(price),
                        "rate": str(rate),
                        "sats_type": sats_type,
                        "aftale": row.get("aftale", ""),
                        "artnr": row.get("artnr", ""),
                    },
                ))
            elif diff > settings.amount_tolerance:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=row_num,
                    field="beloeb",
                    expected_value=f"{expected:.2f}",
                    actual_value=f"{actual_amount:.2f}",
                    message=f"Minor rounding difference: {diff:.2f}",
                    context={
                        "qty": str(qty),
                        "price": str(price),
                        "rate": str(rate),
                        "aftale": row.get("aftale", ""),
                    },
                ))

        return issues
