"""Rule 8: Date Validation — checks settlement dates are within valid ranges."""

import re
from datetime import datetime

from app.validation.base_rule import BaseRule, Severity, ValidationIssue


class DateValidationRule(BaseRule):
    """Validates settlement period dates and voucher dates."""

    @property
    def rule_id(self) -> str:
        return "date_validation"

    @property
    def description(self) -> str:
        return "Dates must be within valid settlement period ranges"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        for row in statement_data:
            row_num = row.get("_row_number")
            source = row.get("_source", "")

            # PDF period validation
            periode = row.get("periode", "")
            if periode:
                parsed = _parse_period(periode)
                if parsed:
                    start, end = parsed
                    if start > end:
                        issues.append(ValidationIssue(
                            severity=Severity.ERROR,
                            rule_id=self.rule_id,
                            rule_description=self.description,
                            row_number=row_num,
                            field="periode",
                            expected_value="start <= end",
                            actual_value=periode,
                            message=f"Period start ({start}) is after end ({end})",
                            context={"aftale": row.get("aftale", "")},
                        ))

            # CSV/Excel voucher date validation
            bilagsdato = row.get("bilagsdato", "") or row.get("bildato", "")
            if bilagsdato:
                date = _parse_date(bilagsdato)
                if date is None:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="bilagsdato",
                        expected_value="valid date",
                        actual_value=bilagsdato,
                        message=f"Cannot parse voucher date: '{bilagsdato}'",
                        context={"aftale": row.get("aftale", "")},
                    ))
                elif date.year < 2000 or date.year > 2100:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="bilagsdato",
                        expected_value="2000–2100",
                        actual_value=str(date.year),
                        message=f"Voucher date year ({date.year}) is outside expected range",
                        context={"aftale": row.get("aftale", "")},
                    ))

        return issues


def _parse_period(period_str: str) -> tuple[datetime, datetime] | None:
    """Parse a Schilling period string like '01.01.20-31.12.20'."""
    match = re.match(r"(\d{2}\.\d{2}\.\d{2})-(\d{2}\.\d{2}\.\d{2})", period_str)
    if match:
        try:
            start = datetime.strptime(match.group(1), "%d.%m.%y")
            end = datetime.strptime(match.group(2), "%d.%m.%y")
            return start, end
        except ValueError:
            return None
    return None


def _parse_date(date_str: str) -> datetime | None:
    """Try multiple date formats common in Schilling exports."""
    formats = ["%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%y", "%d.%m.%y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None
