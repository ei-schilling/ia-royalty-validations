"""Rule 1: Missing Titles — checks that every row has a product identifier."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue


class MissingTitlesRule(BaseRule):
    """Checks that every row has a non-empty product identifier (ISBN/Artnr/Titel)."""

    @property
    def rule_id(self) -> str:
        return "missing_titles"

    @property
    def description(self) -> str:
        return "Every row must have a product identifier (ISBN, Artnr, or Titel)"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []
        for row in statement_data:
            # Skip summary rows from PDF
            if row.get("_record_type") == "page_summary":
                continue

            row_num = row.get("_row_number")
            # Check standard CSV/JSON fields
            artnr = row.get("artnr", "").strip()
            titel = row.get("titel", "").strip()

            if not artnr and not titel:
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=row_num,
                    field="artnr/titel",
                    expected_value="non-empty product identifier",
                    actual_value="(empty)",
                    message="Missing product identifier — no Artnr or Titel found",
                    context={"aftale": row.get("aftale", ""), "kontonr": row.get("kontonr", "")},
                ))
                continue

            # Validate ISBN-13 checksum if the artnr looks like an ISBN
            if artnr and len(artnr.replace("-", "")) == 13 and artnr.replace("-", "").isdigit():
                if not _valid_isbn13(artnr):
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="artnr",
                        expected_value="valid ISBN-13 checksum",
                        actual_value=artnr,
                        message=f"ISBN-13 checksum is invalid: {artnr}",
                        context={"aftale": row.get("aftale", "")},
                    ))

        return issues


def _valid_isbn13(isbn: str) -> bool:
    """Validate an ISBN-13 check digit."""
    digits = isbn.replace("-", "")
    if len(digits) != 13 or not digits.isdigit():
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    check = (10 - total % 10) % 10
    return check == int(digits[12])
