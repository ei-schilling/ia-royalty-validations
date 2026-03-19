"""Rule 12: Language Support — flags encoding corruption and locale issues."""

import re

from app.validation.base_rule import BaseRule, Severity, ValidationIssue

# The Unicode replacement character inserted when a byte sequence cannot be
# decoded — a definitive sign of the wrong encoding having been used.
_REPLACEMENT_CHAR = "\uFFFD"

# Patterns that indicate UTF-8 bytes were misread as Windows-1252 (mojibake).
# Each tuple is (readable label, compiled pattern).
_MOJIBAKE_PATTERNS = [
    ("ø/Ø (UTF-8 read as cp1252)", re.compile(r"Ã¸|Ã˜")),
    ("æ/Æ (UTF-8 read as cp1252)", re.compile(r"Ã¦|Ã†")),
    ("å/Å (UTF-8 read as cp1252)", re.compile(r"Ã¥|Ã…")),
]

# Fields where Danish comma-decimal values should have been normalised.
# If a comma still appears here after parsing, normalisation was skipped.
_NUMERIC_FIELDS = frozenset({
    "stkpris",
    "stkafregnpris",
    "stkafregnsats",
    "liniebeloeb",
    "beloeb",
    "skat",
    "antal",
})

# Internal metadata keys injected by the parser — not real data fields.
_INTERNAL_KEYS = frozenset({
    "_row_number", "_source", "_encoding", "_record_type",
    "_page_number", "_page_num",
})


class LanguageSupportRule(BaseRule):
    """Flags encoding corruption and locale issues in royalty statement data.

    Checks three categories:
    - Encoding corruption: U+FFFD replacement character in any field value.
    - Mojibake: UTF-8 Danish characters (æ/ø/å) misread as Windows-1252.
    - Unnormalised numbers: numeric fields that still contain a comma after
      parsing (Danish comma-decimal format that was not converted).
    """

    @property
    def rule_id(self) -> str:
        return "language_support"

    @property
    def description(self) -> str:
        return "Field values must not contain encoding corruption or unnormalised Danish number formats"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        for row in statement_data:
            row_num = row.get("_row_number")

            for field, value in row.items():
                if field in _INTERNAL_KEYS or not isinstance(value, str) or not value:
                    continue

                # 1 — Replacement character: definitive encoding failure.
                if _REPLACEMENT_CHAR in value:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field=field,
                        expected_value="valid UTF-8 text",
                        actual_value=repr(value[:60]),
                        message=(
                            f"Field '{field}' contains the Unicode replacement character "
                            f"(\uFFFD) — the file was read with the wrong encoding"
                        ),
                        context={"encoding": row.get("_encoding", "unknown")},
                    ))

                # 2 — Mojibake: UTF-8 bytes misinterpreted as Windows-1252.
                for label, pattern in _MOJIBAKE_PATTERNS:
                    if pattern.search(value):
                        issues.append(ValidationIssue(
                            severity=Severity.WARNING,
                            rule_id=self.rule_id,
                            rule_description=self.description,
                            row_number=row_num,
                            field=field,
                            expected_value="correctly encoded Danish characters",
                            actual_value=repr(value[:60]),
                            message=(
                                f"Field '{field}' appears to contain mojibake for {label}: "
                                f"the file may have been encoded as UTF-8 but read as Windows-1252"
                            ),
                            context={"pattern": label},
                        ))
                        break  # One report per field is enough

                # 3 — Unnormalised Danish number: comma still present in numeric field.
                if field in _NUMERIC_FIELDS and re.search(r"\d,\d", value):
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field=field,
                        expected_value="period-decimal number (e.g. 1234.56)",
                        actual_value=value,
                        message=(
                            f"Numeric field '{field}' contains a comma: "
                            f"'{value}' looks like Danish locale format (1.234,56). "
                            f"This may cause calculation errors."
                        ),
                        context={},
                    ))

        return issues
