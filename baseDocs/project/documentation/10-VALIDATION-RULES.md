# 10 — Validation Rules

## Overview

The validation engine runs **11 independent rule plugins** against parsed statement data. Each rule extends `BaseRule` and returns a list of `ValidationIssue` objects with severity, location, and description.

Rules are auto-discovered from the `validation/rules/` directory — no registration required.

---

## Severity Levels

| Level | Color | Meaning | Action Required |
|-------|-------|---------|-----------------|
| **ERROR** | 🔴 Red | Data integrity violation | Must be corrected before processing |
| **WARNING** | 🟡 Amber | Potential problem | Review recommended |
| **INFO** | 🔵 Blue | Informational finding | May be expected behavior |

---

## Rule 1: Missing Titles (`missing_titles`)

**Class**: `MissingTitlesRule`
**File**: `validation/rules/missing_titles.py`

### What It Checks

- Every row must have a non-empty product identifier (`artnr` or `titel`)
- If an `artnr` looks like an ISBN-13, validates the check digit

### Issue Types

| Severity | Condition |
|----------|-----------|
| ERROR | Row has no `artnr` AND no `titel` (completely unidentifiable) |
| WARNING | `artnr` appears to be an ISBN-13 but has an invalid check digit |

### Example Issue

```json
{
  "severity": "error",
  "rule_id": "missing_titles",
  "row_number": 47,
  "field": "artnr",
  "message": "Row has no product identifier (artnr or titel is blank)"
}
```

---

## Rule 2: Invalid Rates (`invalid_rates`)

**Class**: `InvalidRatesRule`
**File**: `validation/rules/invalid_rates.py`

### What It Checks

- `stkafregnsats` (settlement rate) or `sats_value` must be present
- Value must be numeric
- Value must be non-negative
- Value must be non-zero (warning, not error)
- Value must not exceed `max_rate_threshold` (default: 100% = 1.00)

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_RATE_THRESHOLD` | `1.00` | Maximum valid royalty rate |

### Issue Types

| Severity | Condition |
|----------|-----------|
| ERROR | Rate is negative or non-numeric |
| WARNING | Rate is zero or exceeds threshold |

---

## Rule 3: Amount Consistency (`amount_consistency`)

**Class**: `AmountConsistencyRule`
**File**: `validation/rules/amount_consistency.py`

### What It Checks

Validates that `quantity × unit_price × rate ≈ reported_amount`:

```
ANTAL × STKPRIS × STKAFREGNSATS ≈ BELOEB
```

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `AMOUNT_TOLERANCE` | `0.01` | Maximum allowed difference for WARNING |
| `INFO_THRESHOLD` | `1.00` | Difference above this triggers INFO instead of WARNING |

### Issue Types

| Severity | Condition |
|----------|-----------|
| WARNING | Difference exceeds `AMOUNT_TOLERANCE` but ≤ `INFO_THRESHOLD` |
| INFO | Difference exceeds `INFO_THRESHOLD` (likely intentional, e.g., staircase rates) |

### Example Issue

```json
{
  "severity": "warning",
  "rule_id": "amount_consistency",
  "row_number": 23,
  "field": "BELOEB",
  "expected_value": "1250.00",
  "actual_value": "1350.00",
  "message": "Amount mismatch: expected 1250.00, got 1350.00 (diff: 100.00)"
}
```

---

## Rule 4: Tax Validation (`tax_validation`)

**Class**: `TaxValidationRule`
**File**: `validation/rules/tax_validation.py`

### What It Checks

- Rows with `_record_type` containing "afgift" (duty/levy) are structurally valid
- Afgift values should be numeric
- Afgift amounts should be negative or zero (they are deductions)

### Issue Types

| Severity | Condition |
|----------|-----------|
| WARNING | Afgift value is positive (unusual — deductions should be ≤ 0) |
| WARNING | Afgift value is non-numeric |

---

## Rule 5: Guarantee Validation (`guarantee_validation`)

**Class**: `GuaranteeValidationRule`
**File**: `validation/rules/guarantee_validation.py`

### What It Checks

- Guarantee deduction rows (`rest_garanti`, `garanti`) are valid
- Deduction amounts should be negative (they reduce the payout)
- The payout after deduction should not go below zero

### Issue Types

| Severity | Condition |
|----------|-----------|
| ERROR | Payout goes negative after guarantee deduction |
| WARNING | Guarantee deduction is positive (should be negative) |

---

## Rule 6: Settlement Totals (`settlement_totals`)

**Class**: `SettlementTotalsRule`
**File**: `validation/rules/settlement_totals.py`

### What It Checks

Validates the chain integrity of settlement math on PDF pages:

```
Sales lines → Fordeling base
Fordeling base × fordeling_pct → Fordeling amount
Fordeling − garanti − afgift → Til udbetaling (payout)
```

For each page in a PDF statement:
1. Sum all sales line royalty amounts = expected fordeling base
2. Fordeling base × author percentage = expected fordeling amount
3. Fordeling − deductions (garanti, afgift) = expected payout

### Issue Types

| Severity | Condition |
|----------|-----------|
| ERROR | Fordeling amount doesn't match `base × percentage` |
| ERROR | Payout doesn't match `fordeling − deductions` |

---

## Rule 7: Duplicate Entries (`duplicate_entries`)

**Class**: `DuplicateEntriesRule`
**File**: `validation/rules/duplicate_entries.py`

### What It Checks

Detects rows sharing the same key dimensions (potential accidental duplicates):

**Key tuple**: `(aftale, artnr, kanal, prisgruppe, transtype, bilagsnr, antal, beloeb)`

### Issue Types

| Severity | Condition |
|----------|-----------|
| WARNING | Two or more rows share the exact same key tuple |

### Notes

Some duplicates may be intentional (e.g., split transactions). The rule flags them for manual review.

---

## Rule 8: Date Validation (`date_validation`)

**Class**: `DateValidationRule`
**File**: `validation/rules/date_validation.py`

### What It Checks

- `bilagsdato` (voucher date) is parseable as a date
- Period start date ≤ period end date
- All dates fall within a reasonable range (2000–2100)

### Issue Types

| Severity | Condition |
|----------|-----------|
| ERROR | Date is unparseable or clearly invalid |
| WARNING | Date is outside the 2000–2100 range |
| WARNING | Period start > period end |

---

## Rule 9: Advance Balance (`advance_balance`)

**Class**: `AdvanceBalanceRule`
**File**: `validation/rules/advance_balance.py`

### What It Checks

- Advance offset amounts (`ForskudMod`) must not exceed the original advance (`Forskud`) per agreement
- Prevents paying back more than was advanced

### Issue Types

| Severity | Condition |
|----------|-----------|
| ERROR | Advance offset exceeds the original advance amount |

---

## Rule 10: Recipient Shares (`recipient_shares`)

**Class**: `RecipientSharesRule`
**File**: `validation/rules/recipient_shares.py`

### What It Checks

- Co-author/recipient fordeling (distribution) percentages per agreement
- All shares for a given agreement must sum to ≤ 100%

### Issue Types

| Severity | Condition |
|----------|-----------|
| ERROR | Shares sum exceeds 100% for an agreement |
| WARNING | Shares sum is significantly less than 100% (possible missing recipient) |

---

## Rule 11: Transaction Types (`transaction_types`)

**Class**: `TransactionTypesRule`
**File**: `validation/rules/transaction_types.py`

### What It Checks

- Every `TRANSTYPE` value must be a recognized Schilling transaction type
- Flags deprecated or unusual types

### Known Transaction Types (40)

| Code | Danish | English |
|------|--------|---------|
| `Salg` | Salg | Sales |
| `SalgTilb` | Salg tilbageført | Sales returns (credit) |
| `Returneret` | Returneret | Returns |
| `Svind` | Svind | Wastage/shrinkage |
| `Oplag` | Oplag | Stock/print-run |
| `Frieks` | Frieksemplarer | Free copies |
| `Udbetalt` | Udbetalt | Paid out |
| `Skat` | Skat | Tax withheld |
| `Afgift` | Afgift | Social duties |
| `Moms` | Moms | VAT |
| `GarLokal` | Garanti lokal | Local guarantee |
| `GarLokalMod` | Garanti lokal modpost | Local guarantee offset |
| `GarGlobal` | Garanti global | Global guarantee |
| `GarGlobalMod` | Garanti global modpost | Global guarantee offset |
| `Forskud` | Forskud | Advance |
| `ForskudMod` | Forskud modpost | Advance offset |
| `Antologi` | Antologi | Anthology |
| `AntologiMod` | Antologi modpost | Anthology offset |
| `Erstatning` | Erstatning | Compensation |
| `AfregnjJust` | Afregningsjustering | Settlement adjustment |
| `ProdRoy` | Produktionsroyalty | Production royalty |
| `ProdRoyArv` | Produktionsroyalty arv | Production royalty (inherited) |
| `Pension` | Pension | Pension deduction |
| `Ambi` | AM-bidrag | Labour market contribution |
| `EngangsHonorar` | Engangshonorar | One-off fee |
| `Rente` | Rente | Interest withheld |
| `OvfBrutto` | Overført brutto | Gross carry-over |
| `GarMethod` | Garanti metode | Method guarantee |
| `GarMethodMod` | Garanti metode modpost | Method guarantee offset |
| `GrossAmount` | Bruttobeløb | Gross amount |

### Issue Types

| Severity | Condition |
|----------|-----------|
| ERROR | Transaction type is completely unrecognized |
| WARNING | Transaction type is deprecated or unusual |

---

## Adding a New Rule

To add a new validation rule:

1. Create a new file in `validation/rules/`:

```python
# validation/rules/my_new_rule.py
from app.validation.base_rule import BaseRule, ValidationIssue, Severity

class MyNewRule(BaseRule):
    @property
    def rule_id(self) -> str:
        return "my_new_rule"

    @property
    def description(self) -> str:
        return "Description of what this rule checks"

    def validate(self, data: list[dict]) -> list[ValidationIssue]:
        issues = []
        for row in data:
            # Check logic here
            if something_wrong:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    rule_id=self.rule_id,
                    rule_description=self.description,
                    row_number=row.get("_row_number"),
                    field="field_name",
                    expected_value="what it should be",
                    actual_value="what it actually is",
                    message="Human-readable message",
                ))
        return issues
```

2. The engine auto-discovers it — **no registration needed**. The `ValidationEngine` scans all modules in `validation/rules/` for classes that extend `BaseRule`.

3. Add tests in `tests/test_rules.py`.
