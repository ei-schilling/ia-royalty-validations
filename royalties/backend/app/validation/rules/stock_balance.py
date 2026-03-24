"""Rule 15: Stock Balance — validates the circulation / inventory balance on PDF pages."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue

# Tolerance in units: allow for rounding in the PDF display (e.g. 0 units)
_TOLERANCE = 0


class StockBalanceRule(BaseRule):
    """Validates the stock balance identity on each PDF settlement page.

    The Schilling PDF header block shows:

        Total oplag       (cumulative print run)
        Frieksemplar      (free copies — positive value, already deducted in print run)
        Svind             (shrinkage / waste)
        Makulatur         (scrapped copies)
        Periodens salg    (net sales this period — negative = sold/returned)
        Lagerbeholdning   (closing stock balance)

    Every field is printed in the PDF with its correct sign.  The balance
    identity is therefore a plain sum:

        Lagerbeholdning = Total oplag
                        + Frieksemplar        (positive as printed)
                        + Svind               (positive as printed)
                        + Makulatur           (positive as printed)
                        + Auto reguleret      (positive = adds stock)
                        + Tidligere afregnet  (negative — previously settled copies)
                        + Periodens salg      (negative — sold this period)
    """

    @property
    def rule_id(self) -> str:
        return "stock_balance"

    @property
    def description(self) -> str:
        return "Stock balance: closing stock must equal opening stock adjusted for movements"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        for row in statement_data:
            if row.get("_record_type") != "page_summary":
                continue
            if row.get("_source") != "pdf":
                continue

            row_num = row.get("_row_number")
            page_num = row.get("_page_number", "?")

            closing = row.get("lagerbeholdning", "")
            total_oplag = row.get("total_oplag", "")
            frieks = row.get("frieksemplarer", "")
            svind = row.get("svind", "")
            makulatur = row.get("makulatur", "")
            periodens_salg = row.get("periodens_salg", "")
            tidligere = row.get("tidligere_afregnet", "")
            auto_reg = row.get("auto_reguleret", "")

            # Need at minimum closing stock + total oplag + periodens salg to verify
            if not closing or not total_oplag or not periodens_salg:
                continue

            try:
                closing_val = float(closing)
                oplag_val = float(total_oplag)
                # All fields are taken at face value — the PDF already carries the
                # correct sign for each item (e.g. Tidligere afregnet is printed as
                # -55, Periodens salg as -20).  A plain sum must equal Lagerbeholdning.
                frieks_val = float(frieks) if frieks else 0.0
                svind_val = float(svind) if svind else 0.0
                mak_val = float(makulatur) if makulatur else 0.0
                salg_val = float(periodens_salg)
                tidligere_val = float(tidligere) if tidligere else 0.0
                auto_reg_val = float(auto_reg) if auto_reg else 0.0
            except (ValueError, TypeError):
                continue

            expected = oplag_val + frieks_val + svind_val + mak_val + auto_reg_val + tidligere_val + salg_val

            if abs(expected - closing_val) > _TOLERANCE:
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="lagerbeholdning",
                        expected_value=str(int(expected)),
                        actual_value=str(int(closing_val)),
                        message=(
                            f"Page {page_num}: Stock balance mismatch — "
                            f"oplag ({oplag_val:g}) "
                            f"+ frieks ({frieks_val:g}) "
                            f"+ svind ({svind_val:g}) "
                            f"+ makulatur ({mak_val:g}) "
                            f"+ auto reguleret ({auto_reg_val:g}) "
                            f"+ tidligere afregnet ({tidligere_val:g}) "
                            f"+ periodens salg ({salg_val:g}) "
                            f"= {expected:g}, "
                            f"but lagerbeholdning is {closing_val:g}"
                        ),
                        context={
                            "total_oplag": str(oplag_val),
                            "frieksemplarer": str(frieks_val),
                            "svind": str(svind_val),
                            "makulatur": str(mak_val),
                            "auto_reguleret": str(auto_reg_val),
                            "tidligere_afregnet": str(tidligere_val),
                            "periodens_salg": str(salg_val),
                            "lagerbeholdning": str(closing_val),
                            "expected": str(expected),
                        },
                    )
                )

        return issues
