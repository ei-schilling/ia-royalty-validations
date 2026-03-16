"""Rule 11: Transaction Types — validates against the known Schilling type set."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue

# The 40 known transaction types from Roy.h → RoyTransTypeTekst[]
KNOWN_TRANSACTION_TYPES = {
    "salg", "retur", "frieksp", "makulatur", "svind",
    "tilgang", "overforsel", "korrektion", "efterreg",
    "afgift", "skat", "moms", "forskud", "forskudmod",
    "garglobal", "garglobalmod", "garlokal", "garlokalmod",
    "garmetode", "garmetodemod",
    "royalty", "royaltymod", "speciel", "specielmod",
    "bonus", "bonusmod", "afskrivning", "afskrivningmod",
    "udbetaling", "udbetalingmod", "indbetaling", "indbetalingmod",
    "overfort", "overfortmod", "rente", "rentemod",
    "diverse", "diversemod", "rabat", "rabatmod",
}

# Deprecated types that still work but should be flagged
DEPRECATED_TYPES = {
    "speciel", "specielmod",
}


class TransactionTypesRule(BaseRule):
    """Validates that every transaction type code is from the known Schilling set."""

    @property
    def rule_id(self) -> str:
        return "transaction_types"

    @property
    def description(self) -> str:
        return "Transaction type must be a recognized Schilling type"

    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]:
        issues = []

        for row in statement_data:
            transtype = row.get("transtype", "").strip()
            if not transtype:
                continue

            row_num = row.get("_row_number")
            normalized = transtype.lower().replace(" ", "").replace("_", "")

            if normalized not in KNOWN_TRANSACTION_TYPES:
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=row_num,
                    field="transtype",
                    expected_value=f"one of {len(KNOWN_TRANSACTION_TYPES)} known types",
                    actual_value=transtype,
                    message=f"Unknown transaction type: '{transtype}'",
                    context={"aftale": row.get("aftale", ""), "artnr": row.get("artnr", "")},
                ))
            elif normalized in DEPRECATED_TYPES:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=row_num,
                    field="transtype",
                    expected_value="non-deprecated type",
                    actual_value=transtype,
                    message=f"Deprecated transaction type: '{transtype}'",
                    context={"aftale": row.get("aftale", ""), "artnr": row.get("artnr", "")},
                ))

        return issues
