"""Tests for all 14 validation rules."""

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
from app.validation.rules.language_support import LanguageSupportRule

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

    def test_missing_artnr_titel_and_aftale(self):
        data = [{"artnr": "", "titel": "", "aftale": "", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR

    def test_missing_artnr_and_titel_but_has_aftale_passes(self):
        data = [{"artnr": "", "titel": "", "aftale": "AFT-2024-001", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_has_titel_no_artnr_passes(self):
        data = [{"artnr": "", "titel": "My Book", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_skips_summary_rows(self):
        data = [{"_record_type": "page_summary", "artnr": "", "titel": "", "aftale": ""}]
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
        # 1.2 = 120% as a fraction — exceeds the 100% threshold
        data = [{"stkafregnsats": "1.2", "_row_number": 2, "_source": "csv"}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "120.0%" in warnings[0].message

    def test_bad_rates_file(self, fixtures_dir: Path):
        data = parse_file(fixtures_dir / "bad_rates.csv", "csv")
        issues = self.rule.validate(data)
        # -0.05 → error (negative), 0 → error (zero), 1.2 → warning (120% > 100%)
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

    def test_csv_afgift_negative_passes(self):
        data = [{"transtype": "afgift", "aftale": "AFT-001", "beloeb": "-250.00", "_source": "csv", "_row_number": 5}]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_csv_afgift_positive_warns(self):
        data = [{"transtype": "afgift", "aftale": "AFT-001", "beloeb": "250.00", "_source": "csv", "_row_number": 5}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "positive" in warnings[0].message.lower()

    def test_csv_afgift_empty_beloeb_warns(self):
        data = [{"transtype": "afgift", "aftale": "AFT-001", "beloeb": "", "_source": "csv", "_row_number": 5}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1

    def test_csv_afgift_non_numeric_warns(self):
        data = [{"transtype": "AFGIFT", "aftale": "AFT-001", "beloeb": "N/A", "_source": "csv", "_row_number": 5}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1


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
            {"transtype": "garglobal", "aftale": "AFT-001", "beloeb": "5000", "_source": "csv"},
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

    def test_engine_has_all_12_rules(self):
        engine = ValidationEngine()
        rules = engine.get_active_rules(["all"])
        assert len(rules) == 13  # updated: 13 rules after adding unwanted_symbols

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


# ---------------------------------------------------------------------------
# Rule 12: Language Support
# ---------------------------------------------------------------------------
class TestLanguageSupportRule:
    """Tests for the LanguageSupportRule."""

    def setup_method(self):
        self.rule = LanguageSupportRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "language_support"

    def test_clean_data_no_issues(self):
        data = [
            {"artnr": "978-87-1234-567-1", "beloeb": "1234.56", "_row_number": 2, "_source": "csv"}
        ]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_replacement_char_error(self):
        data = [
            {"titel": "Min bog \uFFFD forfatter", "_row_number": 3, "_source": "csv"}
        ]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "replacement character" in errors[0].message

    def test_mojibake_oe_warning(self):
        data = [
            {"titel": "ForlÃ¦gger", "_row_number": 4, "_source": "csv"}
        ]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "mojibake" in warnings[0].message.lower()

    def test_danish_comma_number_warning(self):
        data = [
            {"beloeb": "4.570,59", "_row_number": 5, "_source": "csv"}
        ]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "Danish locale format" in warnings[0].message

    def test_internal_keys_skipped(self):
        data = [
            {"_source": "csv", "_row_number": 2, "_encoding": "utf-8-sig"}
        ]
        issues = self.rule.validate(data)
        assert len(issues) == 0

    def test_empty_value_skipped(self):
        data = [{"artnr": "", "beloeb": "", "_row_number": 2}]
        issues = self.rule.validate(data)
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Rule 13: Unwanted Symbols
# ---------------------------------------------------------------------------
from app.validation.rules.unwanted_symbols import UnwantedSymbolsRule  # noqa: E402


class TestUnwantedSymbolsRule:
    """Tests for the UnwantedSymbolsRule."""

    def setup_method(self):
        self.rule = UnwantedSymbolsRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "unwanted_symbols"

    def test_clean_data_no_issues(self):
        data = [{"artnr": "978-87-1234-567-1", "beloeb": "1234.56", "_row_number": 2, "_source": "csv"}]
        assert self.rule.validate(data) == []

    # --- ERROR: control characters ---
    def test_null_byte_error(self):
        data = [{"titel": "Min\x00bog", "_row_number": 3}]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "\\u0000" in errors[0].message or "control" in errors[0].message.lower()

    def test_control_char_error(self):
        data = [{"artnr": "97887\x0312", "_row_number": 4}]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1

    def test_tab_allowed(self):
        # Tab (\t) is an acceptable whitespace character
        data = [{"titel": "Bog\tmed tab", "_row_number": 5}]
        issues = [i for i in self.rule.validate(data) if i.severity == Severity.ERROR]
        assert len(issues) == 0

    # --- ERROR: zero-width characters ---
    def test_zero_width_space_error(self):
        data = [{"beloeb": "1234\u200B.56", "_row_number": 6}]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "\\u200B" in errors[0].message

    def test_mid_field_bom_error(self):
        data = [{"aftale": "AFT\uFEFF-001", "_row_number": 7}]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "\\uFEFF" in errors[0].message

    def test_zero_width_joiner_error(self):
        data = [{"kontonr": "AUTH\u200D0001", "_row_number": 8}]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1

    # --- WARNING: non-breaking space ---
    def test_nbsp_warning(self):
        data = [{"beloeb": "1\u00A0234.56", "_row_number": 9}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "non-breaking space" in warnings[0].message.lower()

    # --- WARNING: smart quotes ---
    def test_left_double_quote_warning(self):
        data = [{"titel": "\u201CMin bog\u201D", "_row_number": 10}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert any("quotation" in w.message for w in warnings)

    def test_curly_single_quote_warning(self):
        data = [{"titel": "Forfatterens\u2019 bog", "_row_number": 11}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1

    # --- WARNING: dashes ---
    def test_em_dash_warning(self):
        data = [{"periode": "01.01.20\u201431.12.20", "_row_number": 12}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "em-dash" in warnings[0].message

    def test_en_dash_warning(self):
        data = [{"artnr": "978\u201387-0000", "_row_number": 13}]
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "en-dash" in warnings[0].message

    # --- INFO: whitespace-only ---
    def test_whitespace_only_info(self):
        data = [{"artnr": "   ", "_row_number": 14}]
        issues = self.rule.validate(data)
        infos = [i for i in issues if i.severity == Severity.INFO]
        assert len(infos) == 1
        assert "whitespace" in infos[0].message.lower()

    # --- INFO: trailing whitespace in numeric field ---
    def test_trailing_whitespace_numeric_info(self):
        data = [{"beloeb": "1234.56  ", "_row_number": 15}]
        issues = self.rule.validate(data)
        infos = [i for i in issues if i.severity == Severity.INFO]
        assert len(infos) == 1
        assert "trailing whitespace" in infos[0].message.lower()

    def test_trailing_whitespace_non_numeric_not_flagged(self):
        # Trailing space on a text field is not flagged at INFO level
        data = [{"titel": "Min bog  ", "_row_number": 16}]
        infos = [i for i in self.rule.validate(data) if i.severity == Severity.INFO]
        assert len(infos) == 0

    # --- Internal keys always skipped ---
    def test_internal_keys_skipped(self):
        data = [{"_source": "csv\x00corrupt", "_row_number": 2, "_encoding": "utf-8"}]
        assert self.rule.validate(data) == []

    # --- Engine count ---
    def test_engine_has_all_13_rules(self):
        engine = ValidationEngine()
        assert len(engine.get_active_rules(["all"])) == 14  # updated: 14 rules after adding text_within_margins


# ---------------------------------------------------------------------------
# Rule 14: Text Within Margins
# ---------------------------------------------------------------------------
from app.validation.rules.text_within_margins import TextWithinMarginsRule  # noqa: E402


class TestTextWithinMarginsRule:
    """Tests for the TextWithinMarginsRule."""

    def setup_method(self):
        self.rule = TextWithinMarginsRule()

    def test_rule_id(self):
        assert self.rule.rule_id == "text_within_margins"

    def test_clean_data_no_issues(self):
        data = [{"artnr": "978-87-1234-567-1", "titel": "Min bog", "_row_number": 2, "_source": "csv"}]
        assert self.rule.validate(data) == []

    # --- ERROR: per-field limits (ID fields) ---
    def test_artnr_too_long_error(self):
        data = [{"artnr": "A" * 21, "_row_number": 3, "_source": "csv"}]
        issues = self.rule.validate(data)
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert errors[0].field == "artnr"
        assert "21" in errors[0].actual_value

    def test_aftale_too_long_error(self):
        data = [{"aftale": "X" * 21, "_row_number": 3, "_source": "csv"}]
        errors = [i for i in self.rule.validate(data) if i.severity == Severity.ERROR]
        assert len(errors) == 1

    def test_transtype_too_long_error(self):
        data = [{"transtype": "T" * 31, "_row_number": 4, "_source": "csv"}]
        errors = [i for i in self.rule.validate(data) if i.severity == Severity.ERROR]
        assert len(errors) == 1

    def test_artnr_at_limit_passes(self):
        data = [{"artnr": "A" * 20, "_row_number": 3, "_source": "csv"}]
        errors = [i for i in self.rule.validate(data) if i.severity == Severity.ERROR]
        assert len(errors) == 0

    # --- WARNING: per-field limits (text/numeric fields) ---
    def test_titel_too_long_warning(self):
        data = [{"titel": "T" * 201, "_row_number": 5, "_source": "csv"}]
        warnings = [i for i in self.rule.validate(data) if i.severity == Severity.WARNING]
        assert any(i.field == "titel" for i in warnings)

    def test_beloeb_too_long_warning(self):
        data = [{"beloeb": "1" * 21, "_row_number": 6, "_source": "csv"}]
        warnings = [i for i in self.rule.validate(data) if i.severity == Severity.WARNING]
        assert any(i.field == "beloeb" for i in warnings)

    # --- ERROR: absolute ceiling > 500 ---
    def test_absolute_max_error(self):
        data = [{"titel": "X" * 501, "_row_number": 7, "_source": "csv"}]
        errors = [i for i in self.rule.validate(data) if i.severity == Severity.ERROR]
        assert len(errors) == 1
        assert "500" in errors[0].message

    def test_absolute_max_does_not_double_report(self):
        # artnr > 500 chars: should produce exactly 1 issue (absolute), not also per-field
        data = [{"artnr": "A" * 501, "_row_number": 8, "_source": "csv"}]
        issues = self.rule.validate(data)
        field_issues = [i for i in issues if i.field == "artnr"]
        assert len(field_issues) == 1

    # --- WARNING: CSV cell > 255 ---
    def test_csv_cell_over_255_warning(self):
        data = [{"kanal": "K" * 256, "_row_number": 9, "_source": "csv"}]
        warnings = [i for i in self.rule.validate(data) if i.severity == Severity.WARNING]
        assert any("Excel cell limit" in w.message for w in warnings)

    def test_csv_cell_255_exact_no_warning(self):
        data = [{"kanal": "K" * 255, "_row_number": 9, "_source": "csv"}]
        warnings = [i for i in self.rule.validate(data) if "Excel cell limit" in (i.message or "")]
        assert len(warnings) == 0

    # --- WARNING: column header too long ---
    def test_long_header_warning(self):
        long_header = "verylongcolumnheaderthatexceedsfiftycharacterslimit"  # 51 chars
        data = [
            {long_header: "val", "_row_number": 2, "_source": "csv"},
            {long_header: "val2", "_row_number": 3, "_source": "csv"},
        ]
        warnings = [i for i in self.rule.validate(data) if i.field == long_header]
        # Should be reported only once regardless of row count
        assert len(warnings) == 1

    # --- WARNING: CSV row total > 2000 chars ---
    def test_row_total_too_long_warning(self):
        data = [{
            "titel": "T" * 500,
            "kanal": "K" * 500,
            "prisgruppe": "P" * 500,
            "bilagsnr": "B" * 501,
            "_row_number": 10,
            "_source": "csv",
        }]
        warnings = [i for i in self.rule.validate(data) if i.field is None and "total" in (i.message or "").lower()]
        assert len(warnings) == 1

    # --- WARNING: PDF multi-line field ---
    def test_pdf_multiline_titel_warning(self):
        data = [{
            "titel": "Linje 1\nLinje 2",
            "_row_number": 101,
            "_source": "pdf",
            "_record_type": "page_summary",
        }]
        warnings = [i for i in self.rule.validate(data) if i.severity == Severity.WARNING]
        assert any("multiple lines" in w.message for w in warnings)

    def test_pdf_single_line_titel_passes(self):
        data = [{
            "titel": "Min bog om royalty",
            "_row_number": 101,
            "_source": "pdf",
            "_record_type": "page_summary",
        }]
        assert self.rule.validate(data) == []

    # --- Internal keys skipped ---
    def test_internal_keys_not_measured(self):
        data = [{"_source": "csv", "_encoding": "utf-8-sig", "_row_number": 2}]
        assert self.rule.validate(data) == []

    # --- Engine count ---
    def test_engine_has_all_14_rules(self):
        engine = ValidationEngine()
        assert len(engine.get_active_rules(["all"])) == 14


# ---------------------------------------------------------------------------
# Transaction type additions (from Roy.h DB keys)
# ---------------------------------------------------------------------------
class TestTransactionTypesRuleExtended:
    """Tests for transaction types added from Roy.h authoritative DB key list."""

    def setup_method(self):
        self.rule = TransactionTypesRule()

    def test_garmethod_passes(self):
        """GarMethod is the Roy.h DB key for method guarantee — must be accepted."""
        data = [{"transtype": "GarMethod", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_garmethodmod_passes(self):
        data = [{"transtype": "GarMethodMod", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_antologi_passes(self):
        data = [{"transtype": "Antologi", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_salgtilb_passes(self):
        data = [{"transtype": "SalgTilb", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_returneret_passes(self):
        data = [{"transtype": "Returneret", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_erstatning_passes(self):
        data = [{"transtype": "Erstatning", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_pension_passes(self):
        data = [{"transtype": "Pension", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_ambi_passes(self):
        data = [{"transtype": "Ambi", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_engangshonor_passes(self):
        data = [{"transtype": "EngangsHonor", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_ovfbrutto_passes(self):
        data = [{"transtype": "OvfBrutto", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_prodroy_passes(self):
        data = [{"transtype": "ProdRoy", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_oplag_passes(self):
        data = [{"transtype": "Oplag", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_udbetalt_passes(self):
        """Udbetalt (Roy.h DB key) must be accepted alongside udbetaling."""
        data = [{"transtype": "Udbetalt", "_row_number": 1}]
        assert self.rule.validate(data) == []

    def test_grossamount_passes(self):
        data = [{"transtype": "GrossAmount", "_row_number": 1}]
        assert self.rule.validate(data) == []


# ---------------------------------------------------------------------------
# Engine: simulation row filtering
# ---------------------------------------------------------------------------
class TestSimulationRowFiltering:
    """The engine must skip DIM1='SIMUL' rows for all business-logic rules."""

    def test_unknown_transtype_in_simul_row_not_flagged(self):
        """A DIM1=SIMUL row with an unknown transtype must not produce errors."""
        engine = ValidationEngine()
        data = [
            {"transtype": "SimulFakeType", "dim1": "SIMUL", "_row_number": 1},
        ]
        issues = engine.run(data, ["transaction_types"])
        assert issues == []

    def test_real_row_still_validated(self):
        """A row without DIM1=SIMUL must still be checked by business rules."""
        engine = ValidationEngine()
        data = [
            {"transtype": "TotallyUnknown", "dim1": "", "_row_number": 1},
        ]
        errors = [i for i in engine.run(data, ["transaction_types"]) if i.severity == Severity.ERROR]
        assert len(errors) == 1

    def test_simul_case_insensitive(self):
        """DIM1='simul' (any case) must also be treated as a simulation row."""
        engine = ValidationEngine()
        data = [
            {"transtype": "FakeType", "dim1": "simul", "_row_number": 1},
        ]
        issues = engine.run(data, ["transaction_types"])
        assert issues == []

    def test_data_hygiene_rules_still_run_on_simul_rows(self):
        """language_support / unwanted_symbols / text_within_margins still process SIMUL rows."""
        engine = ValidationEngine()
        data = [
            {"titel": "A" * 600, "dim1": "SIMUL", "_row_number": 1},
        ]
        issues = engine.run(data, ["text_within_margins"])
        # The text_within_margins rule should still flag the oversized titel
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# Rule 15: Stock Balance
# ---------------------------------------------------------------------------
from app.validation.rules.stock_balance import StockBalanceRule  # noqa: E402


class TestStockBalanceRule:
    """Tests for the StockBalanceRule."""

    def setup_method(self):
        self.rule = StockBalanceRule()

    def _summary_row(self, **kwargs) -> dict:
        base = {
            "_record_type": "page_summary",
            "_source": "pdf",
            "_row_number": 199,
            "_page_number": "2",
        }
        base.update(kwargs)
        return base

    def test_rule_id(self):
        assert self.rule.rule_id == "stock_balance"

    def test_balanced_stock_passes(self):
        # 10000 - 0 - 0 - 0 + (-785) = 9215
        row = self._summary_row(
            total_oplag="10000",
            frieksemplarer="0",
            svind="0",
            makulatur="0",
            periodens_salg="-785",
            lagerbeholdning="9215",
        )
        assert self.rule.validate([row]) == []

    def test_balanced_with_tidligere_afregnet(self):
        # 10000 - 0 - 0 - 0 + (-1185) + (-20) = 8795  (the screenshot example)
        row = self._summary_row(
            total_oplag="10000",
            frieksemplarer="0",
            svind="0",
            makulatur="0",
            tidligere_afregnet="-1185",
            periodens_salg="-20",
            lagerbeholdning="8795",
        )
        assert self.rule.validate([row]) == []

    def test_balanced_with_auto_reguleret(self):
        # 0 - 0 - 0 - 0 + 1000 + (-1000) + 0 = 0  (the auto reguleret example)
        row = self._summary_row(
            total_oplag="0",
            frieksemplarer="0",
            svind="0",
            makulatur="0",
            auto_reguleret="1000",
            tidligere_afregnet="-1000",
            periodens_salg="0",
            lagerbeholdning="0",
        )
        assert self.rule.validate([row]) == []

    def test_imbalanced_stock_warns(self):
        # expected 9215 but PDF says 9000
        row = self._summary_row(
            total_oplag="10000",
            frieksemplarer="0",
            svind="0",
            makulatur="0",
            periodens_salg="-785",
            lagerbeholdning="9000",
        )
        issues = self.rule.validate([row])
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "lagerbeholdning" in warnings[0].field

    def test_with_frieks_svind_makulatur(self):
        # 10000 - 50 - 10 - 5 + (-200) = 9735
        row = self._summary_row(
            total_oplag="10000",
            frieksemplarer="50",
            svind="10",
            makulatur="5",
            periodens_salg="-200",
            lagerbeholdning="9735",
        )
        assert self.rule.validate([row]) == []

    def test_with_negative_frieks_svind_makulatur(self):
        # PDF may store reductions as negative: 10698 - 11 - 23 - 201 + 0 + (-146) + 0 = 10317
        row = self._summary_row(
            total_oplag="10698",
            frieksemplarer="-11",
            svind="-23",
            makulatur="-201",
            auto_reguleret="0",
            tidligere_afregnet="-146",
            periodens_salg="0",
            lagerbeholdning="10317",
        )
        assert self.rule.validate([row]) == []

    def test_missing_required_fields_skipped(self):
        # Without lagerbeholdning or total_oplag, rule skips silently
        row = self._summary_row(total_oplag="10000")
        assert self.rule.validate([row]) == []

    def test_non_pdf_row_skipped(self):
        row = self._summary_row(
            _source="csv",
            total_oplag="10000",
            periodens_salg="-785",
            lagerbeholdning="9000",
        )
        assert self.rule.validate([row]) == []

    def test_sales_row_skipped(self):
        row = {
            "_record_type": "sales_line",
            "_source": "pdf",
            "_row_number": 101,
            "total_oplag": "10000",
            "periodens_salg": "-785",
            "lagerbeholdning": "9000",
        }
        assert self.rule.validate([row]) == []

    def test_engine_count_now_15(self):
        engine = ValidationEngine()
        assert len(engine.get_active_rules(["all"])) == 16


# ---------------------------------------------------------------------------
# Rule 16: Missing Labels
# ---------------------------------------------------------------------------
from app.validation.rules.missing_labels import MissingLabelsRule  # noqa: E402


class TestMissingLabelsRule:
    """Tests for the MissingLabelsRule."""

    def setup_method(self):
        self.rule = MissingLabelsRule()

    def _page_rows(self, page: str, with_metadata: bool = True) -> list[dict]:
        summary = {
            "_record_type": "page_summary",
            "_source": "pdf",
            "_page_number": page,
            "_row_number": int(page) * 100 + 99,
        }
        if with_metadata:
            summary["aftale"] = "AFT-001"
            summary["kontonr"] = "ACC-001"
            summary["periode"] = "2026"
        sales = {
            "_record_type": "sales_line",
            "_source": "pdf",
            "_page_number": page,
            "_row_number": int(page) * 100 + 1,
            "royalty_amount": "500.00",
        }
        return [summary, sales]

    def test_rule_id(self):
        assert self.rule.rule_id == "missing_labels"

    def test_page_with_labels_passes(self):
        data = self._page_rows("1", with_metadata=True)
        assert self.rule.validate(data) == []

    def test_page_without_labels_warns(self):
        data = self._page_rows("2", with_metadata=False)
        issues = self.rule.validate(data)
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert "missing" in warnings[0].message.lower()
        assert warnings[0].context["page"] == "2"

    def test_page_without_sales_lines_skipped(self):
        # A summary-only page with no content flag should not trigger the warning
        summary = {
            "_record_type": "page_summary",
            "_source": "pdf",
            "_page_number": "3",
            "_row_number": 399,
        }
        assert self.rule.validate([summary]) == []

    def test_no_labels_detected_without_sales_is_sum_page(self):
        # _no_labels_detected + no sales lines = royalty sum/overview page;
        # these legitimately lack field labels — must NOT warn.
        summary = {
            "_record_type": "page_summary",
            "_source": "pdf",
            "_page_number": "4",
            "_row_number": 499,
            "_no_labels_detected": "true",
        }
        assert self.rule.validate([summary]) == []

    def test_no_labels_detected_with_sales_warns(self):
        # _no_labels_detected + sales lines = agreement page with missing labels — should warn
        summary = {
            "_record_type": "page_summary",
            "_source": "pdf",
            "_page_number": "5",
            "_row_number": 599,
            "_no_labels_detected": "true",
        }
        sales = {
            "_record_type": "sales_line",
            "_source": "pdf",
            "_page_number": "5",
            "_row_number": 501,
        }
        issues = self.rule.validate([summary, sales])
        warnings = [i for i in issues if i.severity == Severity.WARNING]
        assert len(warnings) == 1
        assert warnings[0].context["page"] == "5"

    def test_non_pdf_rows_skipped(self):
        row = {
            "_record_type": "page_summary",
            "_source": "csv",
            "_page_number": "1",
            "_row_number": 199,
        }
        assert self.rule.validate([row]) == []

    def test_partial_metadata_passes(self):
        # Having at least one label (e.g. just aftale) is enough
        data = self._page_rows("4", with_metadata=False)
        data[0]["aftale"] = "AFT-002"  # only aftale present
        assert self.rule.validate(data) == []

    def test_engine_count_now_16(self):
        engine = ValidationEngine()
        assert len(engine.get_active_rules(["all"])) == 16
