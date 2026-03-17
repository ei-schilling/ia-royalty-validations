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
from app.validation.rules.transaction_types import TransactionTypesRule


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
        ]

    def get_active_rules(self, rules_filter: list[str]) -> list[BaseRule]:
        """Get rules matching the filter. 'all' returns all rules."""
        if "all" in rules_filter:
            return self._rules
        return [r for r in self._rules if r.rule_id in rules_filter]

    def run(self, statement_data: list[dict], rules_filter: list[str]) -> list[ValidationIssue]:
        """Run all matching rules against the statement data and collect issues."""
        active_rules = self.get_active_rules(rules_filter)
        all_issues: list[ValidationIssue] = []
        for rule in active_rules:
            issues = rule.validate(statement_data)
            all_issues.extend(issues)
        return all_issues
