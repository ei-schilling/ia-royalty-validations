"""Rule 7: Duplicate Entries — detects duplicate rows based on key dimensions."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue


class DuplicateEntriesRule(BaseRule):
    """Detects duplicate rows sharing the same key dimension tuple."""

    @property
    def rule_id(self) -> str:
        return "duplicate_entries"

    @property
    def description(self) -> str:
        return "No two rows should share the same key dimensions unless intentional"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        # Only check CSV/Excel/JSON rows (PDF has one agreement per page)
        rows = [r for r in statement_data if r.get("_source") in ("csv", "xlsx", "json")]
        if not rows:
            return issues

        seen: dict[tuple, list[int]] = {}
        key_fields = ("aftale", "artnr", "kanal", "prisgruppe", "transtype", "bilagsnr")

        for row in rows:
            key = tuple(row.get(f, "") for f in key_fields)
            # Skip if all key fields are empty
            if all(v == "" for v in key):
                continue
            row_num = row.get("_row_number", 0)
            seen.setdefault(key, []).append(row_num)

        for key, row_nums in seen.items():
            if len(row_nums) > 1:
                key_dict = dict(zip(key_fields, key))
                for row_num in row_nums[1:]:  # Report all but the first occurrence
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field=None,
                        expected_value="unique row",
                        actual_value=f"duplicate (first at row {row_nums[0]})",
                        message=(
                            f"Duplicate entry: same key dimensions as row {row_nums[0]} — "
                            "may be intentional (compression) or an error"
                        ),
                        context=key_dict,
                    ))

        return issues
