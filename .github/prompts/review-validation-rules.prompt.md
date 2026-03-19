---
description: "Review the validation rules in the backend — check coverage, correctness, and gaps for each of the 11 rules"
name: "Review Validation Rules"
agent: "agent"
tools: [search, read_file, get_errors]
---

You are performing a structured review of the royalty statement validation rules in the backend.

## Scope

Rules live in [royalties/backend/app/validation/rules/](royalties/backend/app/validation/rules/).
They are registered in [royalties/backend/app/validation/engine.py](royalties/backend/app/validation/engine.py).
All rules extend `BaseRule` from [royalties/backend/app/validation/base_rule.py](royalties/backend/app/validation/base_rule.py).

## Review Checklist (repeat for each rule)

For each of the 11 rules below, evaluate:

1. **Correctness** — Does the logic match the rule's stated description?
2. **Field coverage** — Are all relevant normalized field names handled (CSV, Excel, JSON, PDF)?
3. **Edge cases** — Empty strings, non-numeric values, missing keys, `_source` variants?
4. **Severity** — Is the severity (`ERROR` / `WARNING` / `INFO`) appropriate?
5. **Test coverage** — Is the rule tested in [royalties/backend/tests/test_rules.py](royalties/backend/tests/test_rules.py)?
6. **Known gaps / TODOs** — Any commented-out logic or v2 stubs?

## Rules to Review

| # | Rule ID | File |
|---|---------|------|
| 1 | `missing_titles` | `rules/missing_titles.py` |
| 2 | `invalid_rates` | `rules/invalid_rates.py` |
| 3 | `amount_consistency` | `rules/amount_consistency.py` |
| 4 | `tax_validation` | `rules/tax_validation.py` |
| 5 | `guarantee_validation` | `rules/guarantee_validation.py` |
| 6 | `settlement_totals` | `rules/settlement_totals.py` |
| 7 | `duplicate_entries` | `rules/duplicate_entries.py` |
| 8 | `date_validation` | `rules/date_validation.py` |
| 9 | `advance_balance` | `rules/advance_balance.py` |
| 10 | `recipient_shares` | `rules/recipient_shares.py` |
| 11 | `transaction_types` | `rules/transaction_types.py` |

## Output Format

For each rule, produce a short section:

Rule N: <rule_id>
* Status: ✅ OK | ⚠️ Gaps | ❌ Issues
* Findings: <bullet list of observations>
* Recommended actions: <bullet list, or "None">

End with a **Summary Table** of all rules and a **Prioritized Action Plan** (P1 / P2 / P3).
