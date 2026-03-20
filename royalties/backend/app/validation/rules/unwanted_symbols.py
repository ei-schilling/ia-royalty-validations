"""Rule 13: Unwanted Symbols — detects illegal characters and problematic symbols."""

import re
import unicodedata

from app.validation.base_rule import BaseRule, Severity, ValidationIssue

# Internal parser metadata keys — never inspect these.
_INTERNAL_KEYS = frozenset({
    "_row_number", "_source", "_encoding", "_record_type",
    "_page_number", "_page_num",
})

# Numeric fields where non-breaking spaces and trailing whitespace are harmful.
_NUMERIC_FIELDS = frozenset({
    "antal", "stkpris", "stkafregnpris", "stkafregnsats",
    "beloeb", "liniebeloeb", "fordeling_pct", "afgift",
})

# Key/ID fields where any unexpected symbol breaks lookups or imports.
_KEY_FIELDS = frozenset({
    "artnr", "aftale", "kontonr", "transtype", "bilagsnr",
})

# Zero-width and invisible Unicode characters that corrupt parsing silently.
_ZERO_WIDTH_CHARS = {
    "\u200B": "zero-width space",
    "\u200C": "zero-width non-joiner",
    "\u200D": "zero-width joiner",
    "\uFEFF": "zero-width no-break space (mid-field BOM)",
}

# Smart/curly quote characters that look like plain quotes but aren't.
_SMART_QUOTES = {
    "\u201C": "left double quotation mark (\u201C)",
    "\u201D": "right double quotation mark (\u201D)",
    "\u2018": "left single quotation mark (\u2018)",
    "\u2019": "right single quotation mark (\u2019)",
}

# Dash characters that should be plain hyphen-minus in period strings and IDs.
_DASHES = {
    "\u2014": "em-dash (\u2014)",
    "\u2013": "en-dash (\u2013)",
}

# Regex for ASCII control characters excluding safe whitespace (\t, \n, \r).
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

# Regex for trailing whitespace in a value.
_TRAILING_WHITESPACE_RE = re.compile(r"\s+$")


def _unicode_escape(ch: str) -> str:
    """Return the \\uXXXX representation of a character."""
    return f"\\u{ord(ch):04X}"


class UnwantedSymbolsRule(BaseRule):
    """Detects illegal characters and problematic symbols in field values.

    Checks (in order of severity):
    - ERROR: ASCII control characters (except \\t, \\n, \\r), null bytes,
      zero-width Unicode characters.
    - WARNING: Non-breaking space (\\u00A0), smart/curly quotes, em/en-dashes,
      non-printable Unicode categories Cc/Cf.
    - INFO: Whitespace-only field values, trailing whitespace in numeric fields.
    """

    @property
    def rule_id(self) -> str:
        return "unwanted_symbols"

    @property
    def description(self) -> str:
        return "Field values must not contain illegal characters or problematic symbols"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        for row in statement_data:
            row_num = row.get("_row_number")

            for field, value in row.items():
                if field in _INTERNAL_KEYS or not isinstance(value, str):
                    continue

                # --- ERROR: ASCII control characters ---
                ctrl_match = _CONTROL_CHAR_RE.search(value)
                if ctrl_match:
                    ch = ctrl_match.group(0)
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field=field,
                        expected_value="printable text",
                        actual_value=repr(value[:60]),
                        message=(
                            f"Field '{field}' contains an ASCII control character "
                            f"{_unicode_escape(ch)} — strip before import"
                        ),
                        context={"char": _unicode_escape(ch), "fix": "strip control characters"},
                    ))

                # --- ERROR: zero-width / invisible Unicode ---
                for ch, label in _ZERO_WIDTH_CHARS.items():
                    if ch in value:
                        issues.append(ValidationIssue(
                            severity=Severity.ERROR,
                            rule_id=self.rule_id,
                            rule_description=self.description,
                            row_number=row_num,
                            field=field,
                            expected_value="no invisible characters",
                            actual_value=repr(value[:60]),
                            message=(
                                f"Field '{field}' contains a {label} "
                                f"({_unicode_escape(ch)}) — strip before import"
                            ),
                            context={"char": _unicode_escape(ch), "fix": f"strip {_unicode_escape(ch)}"},
                        ))

                # --- WARNING: non-breaking space in numeric fields ---
                if "\u00A0" in value:
                    sev = Severity.WARNING
                    issues.append(ValidationIssue(
                        severity=sev,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field=field,
                        expected_value="regular space or no space",
                        actual_value=repr(value[:60]),
                        message=(
                            f"Field '{field}' contains a non-breaking space (\\u00A0) — "
                            f"replace with a regular space or strip"
                        ),
                        context={"char": "\\u00A0", "fix": "replace \\u00A0 with space"},
                    ))

                # --- WARNING: smart/curly quotes ---
                for ch, label in _SMART_QUOTES.items():
                    if ch in value:
                        issues.append(ValidationIssue(
                            severity=Severity.WARNING,
                            rule_id=self.rule_id,
                            rule_description=self.description,
                            row_number=row_num,
                            field=field,
                            expected_value="plain ASCII quotes",
                            actual_value=repr(value[:60]),
                            message=(
                                f"Field '{field}' contains a {label} — "
                                f"replace with plain ASCII quote"
                            ),
                            context={"char": _unicode_escape(ch), "fix": "replace with \" or '"},
                        ))

                # --- WARNING: em/en-dash in key or period fields ---
                for ch, label in _DASHES.items():
                    if ch in value:
                        issues.append(ValidationIssue(
                            severity=Severity.WARNING,
                            rule_id=self.rule_id,
                            rule_description=self.description,
                            row_number=row_num,
                            field=field,
                            expected_value="hyphen-minus (-)",
                            actual_value=repr(value[:60]),
                            message=(
                                f"Field '{field}' contains a {label} — "
                                f"replace with a plain hyphen-minus (-)"
                            ),
                            context={"char": _unicode_escape(ch), "fix": "replace with -"},
                        ))

                # --- WARNING: other non-printable Unicode (Cc/Cf) not already caught ---
                for ch in value:
                    cat = unicodedata.category(ch)
                    if cat in ("Cc", "Cf") and ch not in _ZERO_WIDTH_CHARS and ch not in ("\t", "\n", "\r", "\u00A0"):
                        issues.append(ValidationIssue(
                            severity=Severity.WARNING,
                            rule_id=self.rule_id,
                            rule_description=self.description,
                            row_number=row_num,
                            field=field,
                            expected_value="printable text",
                            actual_value=repr(value[:60]),
                            message=(
                                f"Field '{field}' contains a non-printable Unicode character "
                                f"{_unicode_escape(ch)} (category {cat})"
                            ),
                            context={"char": _unicode_escape(ch), "fix": "strip non-printable characters"},
                        ))
                        break  # One report per field for this category

                # --- INFO: whitespace-only value ---
                if value and not value.strip():
                    issues.append(ValidationIssue(
                        severity=Severity.INFO,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field=field,
                        expected_value="non-empty value or empty string",
                        actual_value=repr(value),
                        message=(
                            f"Field '{field}' contains only whitespace — "
                            f"treat as empty or strip"
                        ),
                        context={"fix": "strip or treat as empty"},
                    ))

                # --- INFO: trailing whitespace in numeric fields ---
                elif field in _NUMERIC_FIELDS and _TRAILING_WHITESPACE_RE.search(value):
                    issues.append(ValidationIssue(
                        severity=Severity.INFO,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field=field,
                        expected_value="trimmed numeric value",
                        actual_value=repr(value),
                        message=(
                            f"Numeric field '{field}' has trailing whitespace — strip before parsing"
                        ),
                        context={"fix": "strip trailing whitespace"},
                    ))

        return issues
