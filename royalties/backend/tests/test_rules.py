"""Tests for all 11 validation rules."""

from pathlib import Path

from app.validation.base_rule import Severity
from app.validation.engine import ValidationEngine
from app.validation.parser import parse_file
from app.validation.rules.advance_balance import AdvanceBalanceRule
from app.validation.rules.amount_consistency import AmountConsistencyRule
from app.validation.rules.date_validation import DateValidationRule
from app.validation.rules.duplicate_entries import DuplicateEntriesRule
from app.validation.rules.guarantee_validation import GuaranteeValidationRule
from app.validation.rules.invalid_rates import InvalidRatesRule

# Import rule classes directly for isolated testing
from app.validation.rules.missing_titles import MissingTitlesRule, _valid_isbn13
from app.validation.rules.recipient_shares import RecipientSharesRule
from app.validation.rules.settlement_totals import SettlementTotalsRule
from app.validation.rules.tax_validation import TaxValidationRule
from app.validation.rules.transaction_types import TransactionTypesRule


# ---------------------------------------------------------------------------
# Rule 1: Missing Titles
# ---------------------------------------------------------------------------
class TestMissingTitlesRule:
    """Tests for the MissingTitlesRule."""

    def setup_method(self):
        self.rule = MissingTitlesRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "missing_titles"

    def test_valid_rows_no_issues(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_missing_artnr_detected(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "missing_titles.csv", "csv")
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 2  # rows 1 and 3 have empty artnr

    def test_isbn13_valid(self):
        assert _valid_isbn13("978-87-1234-567-1") is True

    def test_isbn13_invalid_checksum(self):
        assert _valid_isbn13("978-87-1234-567-0") is False

    def test_isbn13_too_short(self):
        assert _valid_isbn13("978-87-123") is False

    def test_missing_both_artnr_and_titel(self):
        data = [{"artnr": "", "titel": "", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    def test_has_titel_no_artnr_passes(self):
        data = [{"artnr": "", "titel": "My Book", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_skips_summary_rows(self):
        data = [{"_record_type": "page_summary", "artnr": "", "titel": ""}]
        issues = self.rule.validate(data)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Rule 2: Invalid Rates
# ---------------------------------------------------------------------------
class TestInvalidRatesRule:
    """Tests for the InvalidRatesRule."""

    def setup_method(self):
        self.rule = InvalidRatesRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "invalid_rates"

    def test_valid_rates_no_issues(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_negative_rate_error(self):
        data = [{"stkafregnsats": "-5", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "negative" in errors[0].message.lower()

    def test_zero_rate_error(self):
        data = [{"stkafregnsats": "0", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "zero" in errors[0].message.lower()

    def test_high_rate_warning(self):
        data = [{"stkafregnsats": "60", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "exceeds" in warnings[0].message.lower()

    def test_bad_rates_file(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "bad_rates.csv", "csv")
        issues = self.rule.validate(data)
        # -5 → error, 0 → error, 60 → warning
        errors = [i for i in issues if i.severity == Severity.ERROR]
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(errors) == 2
        assert len(warnings) == 1

    def test_non_numeric_rate_error(self):
        data = [{"stkafregnsats": "abc", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "not a valid number" in errors[0].message.lower()

    def test_missing_rate_skipped(self):
        data = [{"_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_skips_summary_rows(self):
        data = [{"_record_type": "page_summary", "stkafregnsats": "0"}]
        issues = self.rule.validate(data)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Rule 3: Amount Consistency
# ---------------------------------------------------------------------------
class TestAmountConsistencyRule:
    """Tests for the AmountConsistencyRule."""

    def setup_method(self):
        self.rule = AmountConsistencyRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "amount_consistency"

    def test_consistent_amounts_no_issues(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_calculation_mismatch_detected(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "calculation_errors.csv", "csv")
        issues = self.rule.validate(data)
        # Row 1: 500 x 149.95 x 0.12 = 8997.0, but reported 9000.0 (diff=3.0 -> INFO)
        # Row 2: 200 x 99.50 x 0.10 = 1990.0, but reported 2500.0 (diff=510 -> INFO)
        assert len(issues) >= 2

    def test_exact_amount_passes(self):
        data = [
            {
                "antal": "100",
                "stkpris": "200.00",
                "stkafregnsats": "10",
                "beloeb": "2000.00",
                "_row_number": 2,
                "_source": "csv",
            }
        ]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_missing_fields_skipped(self):
        data = [{"antal": "100", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_zero_quantity_skipped(self):
        data = [
            {
                "antal": "0",
                "stkpris": "100",
                "stkafregnsats": "10",
                "beloeb": "0",
                "_row_number": 2,
                "_source": "csv",
            }
        ]
        issues = self.rule.validate(data)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Rule 4: Tax Validation
# ---------------------------------------------------------------------------
class TestTaxValidationRule:
    """Tests for the TaxValidationRule."""

    def setup_method(self):
        self.rule = TaxValidationRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "tax_validation"

    def test_negative_afgift_passes(self):
        data = [{"_record_type": "page_summary", "afgift": "-150.00", "_row_number": 199}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_zero_afgift_passes(self):
        data = [{"_record_type": "page_summary", "afgift": "0", "_row_number": 199}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_positive_afgift_warning(self):
        data = [{"_record_type": "page_summary", "afgift": "250.00", "_row_number": 199}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "positive" in warnings[0].message.lower()

    def test_non_numeric_afgift_warning(self):
        data = [{"_record_type": "page_summary", "afgift": "N/A", "_row_number": 199}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1

    def test_no_afgift_skipped(self):
        data = [{"_record_type": "page_summary", "_row_number": 199}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_non_summary_row_skipped(self):
        data = [{"_record_type": "sales_line", "afgift": "500.00", "_row_number": 101}]
        issues = self.rule.validate(data)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Rule 5: Guarantee Validation
# ---------------------------------------------------------------------------
class TestGuaranteeValidationRule:
    """Tests for the GuaranteeValidationRule."""

    def setup_method(self):
        self.rule = GuaranteeValidationRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "guarantee_validation"

    def test_negative_garanti_passes(self):
        data = [
            {
                "_record_type": "page_summary",
                "rest_garanti": "-5000.00",
                "til_udbetaling": "3000.00",
                "_row_number": 199,
            }
        ]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_positive_garanti_warning(self):
        data = [
            {
                "_record_type": "page_summary",
                "rest_garanti": "5000.00",
                "_row_number": 199,
            }
        ]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1

    def test_negative_payout_error(self):
        data = [
            {
                "_record_type": "page_summary",
                "rest_garanti": "-20000.00",
                "til_udbetaling": "-5000.00",
                "_row_number": 199,
            }
        ]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "negative" in errors[0].message.lower()

    def test_csv_guarantee_without_offset_warns(self):
        data = [
            {"transtype": "Garanti", "aftale": "AFT-001", "beloeb": "-5000", "_source": "csv"},
        ]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1


# ---------------------------------------------------------------------------
# Rule 6: Settlement Totals
# ---------------------------------------------------------------------------
class TestSettlementTotalsRule:
    """Tests for the SettlementTotalsRule."""

    def setup_method(self):
        self.rule = SettlementTotalsRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "settlement_totals"

    def test_matching_totals_pass(self):
        data = [
            {
                "_record_type": "sales_line",
                "_page_number": "1",
                "royalty_amount": "1000.00",
            },
            {
                "_record_type": "sales_line",
                "_page_number": "1",
                "royalty_amount": "2000.00",
            },
            {
                "_record_type": "page_summary",
                "_page_number": "1",
                "fordeling_pct": "1.0",
                "fordeling_base": "3000.00",
                "fordeling_amount": "3000.00",
                "_row_number": 199,
            },
        ]
        issues = self.rule.validate(data)
        # fordeling_base (3000) matches sales sum (3000), pct * base = amount
        assert len(issues) == 0

    def test_mismatched_base_error(self):
        data = [
            {
                "_record_type": "sales_line",
                "_page_number": "1",
                "royalty_amount": "1000.00",
            },
            {
                "_record_type": "page_summary",
                "_page_number": "1",
                "fordeling_pct": "1.0",
                "fordeling_base": "5000.00",
                "fordeling_amount": "5000.00",
                "_row_number": 199,
            },
        ]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert any("Fordeling base" in e.message for e in errors)

    def test_no_pdf_data_no_issues(self):
        data = [{"transtype": "Salg", "_source": "csv", "_row_number": 2}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_payout_with_carry_forward(self):
        data = [
            {
                "_record_type": "sales_line", "_page_number": "1",
                "royalty_amount": "1000.00",
            },
            {
                "_record_type": "sales_line", "_page_number": "1",
                "royalty_amount": "2000.00",
            },
            {
                "_record_type": "page_summary", "_page_number": "1",
                "fordeling_pct": "1.0", "fordeling_base": "3000.00",
                "fordeling_amount": "3000.00", "rest_garanti": "0.00",
                "afgift": "0.00", "carry_forward": "500.00",
                "til_udbetaling": "2500.00", "_row_number": 199,
            },
        ]
        issues = self.rule.validate(data)
        # payout = 3000 + 0 - 0 - 500 = 2500, matches til_udbetaling
        assert len(issues) == 0

    def test_payout_with_carry_forward_error(self):
        data = [
            {
                "_record_type": "sales_line", "_page_number": "1",
                "royalty_amount": "1000.00",
            },
            {
                "_record_type": "sales_line", "_page_number": "1",
                "royalty_amount": "2000.00",
            },
            {
                "_record_type": "page_summary", "_page_number": "1",
                "fordeling_pct": "1.0", "fordeling_base": "3000.00",
                "fordeling_amount": "3000.00", "rest_garanti": "0.00",
                "afgift": "0.00", "carry_forward": "500.00",
                "til_udbetaling": "2000.00", "_row_number": 199,
            },
        ]
        issues = self.rule.validate(data)
        # payout should be 2500, but is 2000, so error expected
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "carry_forward" in errors[0].message

    def test_payout_mismatch_without_garanti_is_warning(self):
        data = [
            {
                "_record_type": "sales_line", "_page_number": "1",
                "royalty_amount": "3000.00",
            },
            {
                "_record_type": "page_summary", "_page_number": "1",
                "fordeling_pct": "1.0", "fordeling_base": "3000.00",
                "fordeling_amount": "3000.00",
                # rest_garanti intentionally absent
                "afgift": "0.00", "carry_forward": "0.00",
                "til_udbetaling": "2500.00", "_row_number": 199,
            },
        ]
        issues = self.rule.validate(data)
        # Mismatch but garanti missing → WARNING not ERROR
        errors = [i for i in issues if i.severity == Severity.ERROR]
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(errors) == 0
        assert len(warnings) == 1
        assert "not present in file" in warnings[0].message

    def test_payout_with_afgift_percentage(self):
        data = [
            {
                "_record_type": "sales_line", "_page_number": "1",
                "royalty_amount": "1000.00",
            },
            {
                "_record_type": "sales_line", "_page_number": "1",
                "royalty_amount": "2000.00",
            },
            {
                "_record_type": "page_summary", "_page_number": "1",
                "fordeling_pct": "1.0", "fordeling_base": "3000.00",
                "fordeling_amount": "3000.00", "rest_garanti": "200.00",
                "afgift": "10.0", "carry_forward": "100.00",
                "til_udbetaling": "2790.00", "_row_number": 199,
            },
        ]
        # afgift base = 3000 + 200 - 100 = 3100, afgift = 3100 * 0.10 = 310, payout = 3100 - 310 = 2790
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_payout_with_afgift_percentage_error(self):
        data = [
            {
                "_record_type": "sales_line", "_page_number": "1",
                "royalty_amount": "1000.00",
            },
            {
                "_record_type": "sales_line", "_page_number": "1",
                "royalty_amount": "2000.00",
            },
            {
                "_record_type": "page_summary", "_page_number": "1",
                "fordeling_pct": "1.0", "fordeling_base": "3000.00",
                "fordeling_amount": "3000.00", "rest_garanti": "200.00",
                "afgift": "10.0", "carry_forward": "100.00",
                "til_udbetaling": "2500.00", "_row_number": 199,
            },
        ]
        # payout should be 2790, but is 2500, so error expected
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "afgift" in errors[0].message


# ---------------------------------------------------------------------------
# Rule 7: Duplicate Entries
# ---------------------------------------------------------------------------
class TestDuplicateEntriesRule:
    """Tests for the DuplicateEntriesRule."""

    def setup_method(self):
        self.rule = DuplicateEntriesRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "duplicate_entries"

    def test_unique_rows_no_issues(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_duplicate_detected(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "duplicate_rows.csv", "csv")
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        # Rows 1 and 2 share the same key dimensions
        assert len(warnings) >= 1
        assert "duplicate" in warnings[0].message.lower()

    def test_pdf_rows_skipped(self):
        data = [
            {"aftale": "A", "artnr": "X", "_source": "pdf", "_row_number": 101},
            {"aftale": "A", "artnr": "X", "_source": "pdf", "_row_number": 102},
        ]
        issues = self.rule.validate(data)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Rule 8: Date Validation
# ---------------------------------------------------------------------------
class TestDateValidationRule:
    """Tests for the DateValidationRule."""

    def setup_method(self):
        self.rule = DateValidationRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "date_validation"

    def test_valid_dates_no_issues(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_unparseable_date_warning(self):
        data = [{"bilagsdato": "32-13-2026", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "cannot parse" in warnings[0].message.lower()

    def test_out_of_range_year_warning(self):
        data = [{"bilagsdato": "15-01-1990", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "outside expected range" in warnings[0].message.lower()

    def test_valid_danish_date(self):
        data = [{"bilagsdato": "15-01-2026", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Rule 9: Advance Balance
# ---------------------------------------------------------------------------
class TestAdvanceBalanceRule:
    """Tests for the AdvanceBalanceRule."""

    def setup_method(self):
        self.rule = AdvanceBalanceRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "advance_balance"

    def test_balanced_advances_no_issues(self):
        data = [
            {
                "transtype": "Forskud",
                "aftale": "AFT-001",
                "beloeb": "10000.00",
                "_row_number": 2,
                "_source": "csv",
            },
            {
                "transtype": "ForskudMod",
                "aftale": "AFT-001",
                "beloeb": "-8000.00",
                "_row_number": 3,
                "_source": "csv",
            },
        ]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_offset_exceeds_advance_error(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "advances_guarantees.csv", "csv")
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        # ForskudMod (12000) > Forskud (10000)
        assert len(errors) == 1
        assert "exceeds" in errors[0].message.lower()

    def test_no_advances_no_issues(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        issues = self.rule.validate(data)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Rule 10: Recipient Shares
# ---------------------------------------------------------------------------
class TestRecipientSharesRule:
    """Tests for the RecipientSharesRule."""

    def setup_method(self):
        self.rule = RecipientSharesRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "recipient_shares"

    def test_100_percent_passes(self):
        data = [
            {
                "_record_type": "page_summary",
                "aftale": "AFT-001",
                "fordeling_pct": "0.5",
                "_row_number": 199,
            },
            {
                "_record_type": "page_summary",
                "aftale": "AFT-001",
                "fordeling_pct": "0.5",
                "_row_number": 299,
            },
        ]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_over_100_percent_error(self):
        data = [
            {
                "_record_type": "page_summary",
                "aftale": "AFT-001",
                "fordeling_pct": "0.6",
                "_row_number": 199,
            },
            {
                "_record_type": "page_summary",
                "aftale": "AFT-001",
                "fordeling_pct": "0.6",
                "_row_number": 299,
            },
        ]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "exceeds 100%" in errors[0].message

    def test_under_100_percent_warning(self):
        data = [
            {
                "_record_type": "page_summary",
                "aftale": "AFT-001",
                "fordeling_pct": "0.3",
                "_row_number": 199,
            },
        ]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "unclaimed" in warnings[0].message

    def test_no_pdf_data_no_issues(self):
        data = [{"transtype": "Salg", "_source": "csv", "_row_number": 2}]
        issues = self.rule.validate(data)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Rule 11: Transaction Types
# ---------------------------------------------------------------------------
class TestTransactionTypesRule:
    """Tests for the TransactionTypesRule."""

    def setup_method(self):
        self.rule = TransactionTypesRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "transaction_types"

    def test_known_types_pass(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_unknown_type_error(self):
        data = [{"transtype": "FakeType", "_row_number": 2}]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "unknown" in errors[0].message.lower()

    def test_deprecated_type_warning(self):
        data = [{"transtype": "Speciel", "_row_number": 2}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "deprecated" in warnings[0].message.lower()

    def test_case_insensitive(self):
        data = [{"transtype": "SALG", "_row_number": 2}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_empty_type_skipped(self):
        data = [{"transtype": "", "_row_number": 2}]
        issues = self.rule.validate(data)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Engine tests
# ---------------------------------------------------------------------------
class TestValidationEngine:
    """Integration tests for the validation engine orchestration."""

    def test_engine_has_all_11_rules(self):
        engine = ValidationEngine()
        rules = engine.get_active_rules(["all"])
        assert len(rules) == 11

    def test_filter_specific_rules(self):
        engine = ValidationEngine()
        rules = engine.get_active_rules(["missing_titles", "invalid_rates"])
        assert len(rules) == 2
        rule_ids = {r.rule_id for r in rules}
        assert rule_ids == {"missing_titles", "invalid_rates"}

    def test_run_on_valid_data(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        engine = ValidationEngine()
        issues = engine.run(data, ["all"])
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_run_catches_mixed_issues(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "mixed_issues.csv", "csv")
        engine = ValidationEngine()
        issues = engine.run(data, ["all"])
        # Should have errors from unknown type + unparseable date
        assert len(issues) > 0
        rule_ids = {i.rule_id for i in issues}
        assert "transaction_types" in rule_ids
        assert "date_validation" in rule_ids
