"""Validation engine — discovers and orchestrates all validation rule plugins."""

from app.validation.base_rule import BaseRule, ValidationIssue
from app.validation.rules.advance_balance import AdvanceBalanceRule
from app.validation.rules.amount_consistency import AmountConsistencyRule
from app.validation.rules.date_validation import DateValidationRule
from app.validation.rules.duplicate_entries import DuplicateEntriesRule
from app.validation.rules.guarantee_validation import GuaranteeValidationRule
from app.validation.rules.invalid_rates import InvalidRatesRule
from app.validation.rules.missing_titles import MissingTitlesRule
from app.validation.rules.recipient_shares import RecipientSharesRule
from app.validation.rules.settlement_totals import SettlementTotalsRule
from app.validation.rules.tax_validation import TaxValidationRule
from app.validation.rules.language_support import LanguageSupportRule
from app.validation.rules.transaction_types import TransactionTypesRule
from app.validation.rules.unwanted_symbols import UnwantedSymbolsRule
from app.validation.rules.text_within_margins import TextWithinMarginsRule
from app.validation.rules.stock_balance import StockBalanceRule
from app.validation.rules.missing_labels import MissingLabelsRule

# Rules that inspect raw data hygiene should still run on simulation rows.
# All other (business-logic) rules skip rows with DIM1 = 'SIMUL'.
_DATA_HYGIENE_RULES = {"language_support", "unwanted_symbols", "text_within_margins"}


def _is_simulation_row(row: dict) -> bool:
    """Return True for rows that are simulation postings (DIM1 = 'SIMUL').

    The Schilling settlement engine writes simulated postings to ROYPOST with
    DIM1 = 'SIMUL' (see RoySimulering.cpp).  These must not be treated as real
    settlement transactions by business-logic validation rules.
    """
    return row.get("dim1", "").strip().upper() == "SIMUL"


class ValidationEngine:
    """Orchestrates validation rules and collects issues."""

    def __init__(self) -> None:
        self._rules: list[BaseRule] = [
            MissingTitlesRule(),
            InvalidRatesRule(),
            AmountConsistencyRule(),
            TaxValidationRule(),
            GuaranteeValidationRule(),
            SettlementTotalsRule(),
            DuplicateEntriesRule(),
            DateValidationRule(),
            AdvanceBalanceRule(),
            RecipientSharesRule(),
            TransactionTypesRule(),
            LanguageSupportRule(),
            UnwantedSymbolsRule(),
            TextWithinMarginsRule(),
            StockBalanceRule(),
            MissingLabelsRule(),
        ]

    def get_active_rules(self, rules_filter: list[str]) -> list[BaseRule]:
        """Get rules matching the filter. 'all' returns all rules."""
        if "all" in rules_filter:
            return self._rules
        return [r for r in self._rules if r.rule_id in rules_filter]

    def run(self, statement_data: list[dict], rules_filter: list[str]) -> list[ValidationIssue]:
        """Run all matching rules against the statement data and collect issues."""
        active_rules = self.get_active_rules(rules_filter)
        real_rows = [r for r in statement_data if not _is_simulation_row(r)]
        all_issues: list[ValidationIssue] = []
        for rule in active_rules:
            rows = statement_data if rule.rule_id in _DATA_HYGIENE_RULES else real_rows
            issues = rule.validate(rows)
            all_issues.extend(issues)
        return all_issues
