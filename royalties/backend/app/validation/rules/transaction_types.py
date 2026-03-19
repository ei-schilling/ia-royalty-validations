"""Rule 11: Transaction Types — validates against the known Schilling type set."""

from app.validation.base_rule import BaseRule, Severity, ValidationIssue

# Known transaction types: original 40 observed types + all DB keys from Roy.h
# (Roy.h RoyTransTypeTekst[] lists the authoritative DB keys; additional types
# come from real export files in the wild.)
KNOWN_TRANSACTION_TYPES = {
    # ── Sales / inventory ──────────────────────────────────────────────────────
    "salg",           # Sales
    "salgtilb",       # Sales returns (credit note) — Roy.h: SalgTilb
    "retur",          # Returns (physical) — observed in exports
    "returneret",     # Returns — Roy.h: Returneret
    "oplag",          # Print-run / stock quantity — Roy.h: Oplag
    "frieks",         # Free copies — Roy.h: Frieks
    "frieksp",        # Free copies (variant observed in exports)
    "makulatur",      # Write-off / scrapped stock — observed in exports
    "svind",          # Shrinkage / waste — Roy.h: Svind
    "tilgang",        # Inventory receipt — observed in exports
    # ── Royalty calculations ───────────────────────────────────────────────────
    "royalty",        # Standard royalty
    "royaltymod",     # Royalty offset/reversal
    "prodroy",        # Production royalty — Roy.h: ProdRoy
    "prodroyarv",     # Inherited production royalty — Roy.h: ProdRoyArv
    "grossamount",    # Gross amount before taxes/VAT — Roy.h: GrossAmount
    "antologi",       # Anthology royalty — Roy.h: Antologi
    "antologimod",    # Anthology royalty offset — Roy.h: AntologiMod
    "erstatning",     # Compensation / damages — Roy.h: Erstatning
    # ── Guarantees ────────────────────────────────────────────────────────────
    "garglobal",      # Global guarantee deduction
    "garglobalmod",   # Global guarantee offset
    "garlokal",       # Local guarantee deduction
    "garlokalmod",    # Local guarantee offset
    "garmetode",      # Method guarantee deduction (Danish variant)
    "garmetodemod",   # Method guarantee offset (Danish variant)
    "garmethod",      # Method guarantee deduction — Roy.h: GarMethod
    "garmethodmod",   # Method guarantee offset — Roy.h: GarMethodMod
    # ── Advances ──────────────────────────────────────────────────────────────
    "forskud",        # Advance payment
    "forskudmod",     # Advance offset / recoupment
    # ── Tax and levies ────────────────────────────────────────────────────────
    "afgift",         # Duty / social levy
    "skat",           # Withholding tax
    "moms",           # VAT
    "ambi",           # Labour market contribution — Roy.h: Ambi
    "pension",        # Pension deduction — Roy.h: Pension
    # ── Payments and adjustments ──────────────────────────────────────────────
    "udbetaling",     # Disbursement (observed in exports)
    "udbetalingmod",  # Disbursement reversal
    "udbetalt",       # Paid out — Roy.h: Udbetalt
    "indbetaling",    # Receipt
    "indbetalingmod", # Receipt reversal
    "engangshonor",   # One-off fee — Roy.h: EngangsHonorar (hidden on statement)
    "ovfbrutto",      # Gross carry-over / balance adjustment — Roy.h: OvfBrutto
    "afregnnjust",    # Settlement adjustment — Roy.h: AfregnjJust
    "overforsel",     # Transfer (observed in exports)
    "overfort",       # Transferred amount
    "overfortmod",    # Transfer reversal
    # ── Interest and misc ─────────────────────────────────────────────────────
    "rente",          # Interest
    "rentemod",       # Interest reversal
    "diverse",        # Miscellaneous
    "diversemod",     # Miscellaneous reversal
    "bonus",          # Bonus
    "bonusmod",       # Bonus reversal
    "rabat",          # Discount
    "rabatmod",       # Discount reversal
    "speciel",        # Special (deprecated)
    "specielmod",     # Special reversal (deprecated)
    "afskrivning",    # Write-down
    "afskrivningmod", # Write-down reversal
    "korrektion",     # Correction — observed in exports
    "efterreg",       # Subsequent adjustment — observed in exports
}

# Deprecated types that still work but should be flagged
DEPRECATED_TYPES = {
    "speciel",
    "specielmod",
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
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="transtype",
                        expected_value=f"one of {len(KNOWN_TRANSACTION_TYPES)} known types",
                        actual_value=transtype,
                        message=f"Unknown transaction type: '{transtype}'",
                        context={"aftale": row.get("aftale", ""), "artnr": row.get("artnr", "")},
                    )
                )
            elif normalized in DEPRECATED_TYPES:
                issues.append(
                    ValidationIssue(
                        severity=Severity.WARNING,
                        rule_id=self.rule_id,
                        rule_description=self.description,
                        row_number=row_num,
                        field="transtype",
                        expected_value="non-deprecated type",
                        actual_value=transtype,
                        message=f"Deprecated transaction type: '{transtype}'",
                        context={"aftale": row.get("aftale", ""), "artnr": row.get("artnr", "")},
                    )
                )

        return issues
