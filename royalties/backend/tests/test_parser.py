"""Tests for the multi-format file parser module."""

from pathlib import Path

import pytest

from app.validation.parser import (
    _danish_number_to_str,
    _normalize_column_name,
    _resolve_formula,
    parse_file,
)


class TestResolveFormula:
    """Tests for the =N/D formula resolver used in Schilling native CSV."""

    def test_simple_division(self):
        assert _resolve_formula("=1495000/100") == "14950.0"

    def test_negative_numerator(self):
        assert _resolve_formula("=-5000/100") == "-50.0"

    def test_divide_by_one(self):
        assert _resolve_formula("=500/1") == "500.0"

    def test_non_formula_passthrough(self):
        assert _resolve_formula("149.95") == "149.95"
        assert _resolve_formula("hello") == "hello"
        assert _resolve_formula("") == ""

    def test_zero_numerator(self):
        assert _resolve_formula("=0/100") == "0.0"


class TestDanishNumberToStr:
    """Tests for Danish number format conversion (1.234,56 → 1234.56)."""

    def test_danish_thousands_and_decimal(self):
        # 1.234,56 → period is thousands sep, comma is decimal
        assert _danish_number_to_str("1.234,56") == "1234.56"

    def test_plain_integer(self):
        assert _danish_number_to_str("500") == "500"

    def test_negative_danish(self):
        assert _danish_number_to_str("-1.234,56") == "-1234.56"

    def test_us_style_decimal(self):
        # No comma, period with 2 decimal digits → keep as-is
        assert _danish_number_to_str("149.95") == "149.95"

    def test_thousands_only(self):
        # 1.000 → period followed by 3 digits, no comma → treat as thousands
        assert _danish_number_to_str("1.000") == "1000"


class TestNormalizeColumnName:
    """Tests for column name normalization mapping."""

    def test_known_mappings(self):
        assert _normalize_column_name("ArtNr") == "artnr"
        assert _normalize_column_name("StkAfregnsats") == "stkafregnsats"
        assert _normalize_column_name("LinieBelqb") == "liniebeloeb"  # ø→q mapping
        assert _normalize_column_name("BilDato") == "bildato"

    def test_standard_csv_columns(self):
        assert _normalize_column_name("TRANSNR") == "transnr"
        assert _normalize_column_name("TRANSTYPE") == "transtype"
        assert _normalize_column_name("BELOEB") == "beloeb"
        assert _normalize_column_name("ANTAL") == "antal"

    def test_unknown_column_lowered(self):
        assert _normalize_column_name("CustomField") == "customfield"


class TestParseCSV:
    """Tests for standard comma-delimited CSV parsing."""

    def test_valid_csv(self, fixtures_dir: Path):
        rows = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        assert len(rows) == 3
        assert rows[0]["_source"] == "csv"
        assert rows[0]["_row_number"] == 2
        assert rows[0]["transtype"] == "Salg"
        assert rows[0]["artnr"] == "978-87-1234-567-1"
        assert rows[0]["stkafregnsats"] == "0.12"
        assert rows[0]["beloeb"] == "8997.00"

    def test_retur_row(self, fixtures_dir: Path):
        rows = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        retur = rows[2]
        assert retur["transtype"] == "Retur"
        assert retur["antal"] == "-50"

    def test_schilling_native_csv(self, fixtures_dir: Path):
        """Semicolon-delimited with =N/100 formulas."""
        rows = parse_file(fixtures_dir / "schilling_native.csv", "csv")
        assert len(rows) == 2
        # Formula =1495000/100 should resolve to 14950.0
        assert rows[0]["stkafregnpris"] == "14950.0"
        # Formula =1200/100 should resolve to 12.0
        assert rows[0]["stkafregnsats"] == "12.0"
        # Formula =899700/100 should resolve to 8997.0
        assert rows[0]["liniebeloeb"] == "8997.0"
        # =500/1 resolves to 500.0
        assert rows[0]["antal"] == "500.0"

    def test_missing_titles_csv(self, fixtures_dir: Path):
        rows = parse_file(fixtures_dir / "missing_titles.csv", "csv")
        assert len(rows) == 3
        # First row has empty artnr
        assert rows[0]["artnr"] == ""
        # Second row has a valid ISBN
        assert rows[1]["artnr"] == "978-87-1234-567-1"

    def test_row_numbers_start_at_2(self, fixtures_dir: Path):
        """Row numbers start at 2 (1 is header)."""
        rows = parse_file(fixtures_dir / "valid_statement.csv", "csv")
        assert rows[0]["_row_number"] == 2
        assert rows[1]["_row_number"] == 3
        assert rows[2]["_row_number"] == 4


class TestParseJSON:
    """Tests for JSON file parsing."""

    def test_valid_json(self, fixtures_dir: Path):
        rows = parse_file(fixtures_dir / "valid_statement.json", "json")
        assert len(rows) == 2
        assert rows[0]["_source"] == "json"
        assert rows[0]["_row_number"] == 1
        assert rows[0]["transnr"] == "10001"
        assert rows[0]["transtype"] == "Salg"
        assert rows[0]["beloeb"] == "8997.00"

    def test_json_column_normalization(self, fixtures_dir: Path):
        rows = parse_file(fixtures_dir / "valid_statement.json", "json")
        # JSON keys like "STKAFREGNSATS" should normalize
        assert "stkafregnsats" in rows[0]


class TestUnsupportedFormat:
    """Tests for unsupported file formats."""

    def test_unsupported_raises(self, tmp_path: Path):
        dummy = tmp_path / "test.txt"
        dummy.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file format"):
            parse_file(dummy, "txt")
