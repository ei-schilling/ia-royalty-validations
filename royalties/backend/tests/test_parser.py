"""Tests for the multi-format file parser module."""

from pathlib import Path

import pytest

from app.validation.parser import (
    _danish_number_to_str,
    _normalize_column_name,
    _resolve_formula,
    detect_encoding,
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
    """Tests for Danish/international number format conversion."""

    def test_danish_thousands_and_decimal(self):
        # 1.234,56 → period is thousands sep, comma is decimal (comma last)
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

    def test_international_comma_thousands(self):
        # -1,005 → comma followed by exactly 3 digits → thousands separator
        assert _danish_number_to_str("-1,005") == "-1005"

    def test_international_comma_thousands_2000(self):
        # -2,000 → same rule
        assert _danish_number_to_str("-2,000") == "-2000"

    def test_danish_comma_decimal(self):
        # -780,00 → comma followed by 2 digits → decimal separator
        assert _danish_number_to_str("-780,00") == "-780.00"

    def test_danish_comma_decimal_small(self):
        # 0,50 → 2 digits after comma → decimal
        assert _danish_number_to_str("0,50") == "0.50"

    def test_international_both_separators(self):
        # 3,398.20 → period comes last → period=decimal, comma=thousands
        assert _danish_number_to_str("3,398.20") == "3398.20"

    def test_danish_both_separators(self):
        # 3.398,20 → comma comes last → comma=decimal, period=thousands
        assert _danish_number_to_str("3.398,20") == "3398.20"

    def test_large_international_amount(self):
        # 70,470.00 → period last → comma=thousands, period=decimal
        assert _danish_number_to_str("70,470.00") == "70470.00"


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


class TestDetectEncoding:
    """Tests for file encoding detection."""

    def test_utf8_bom_detected(self, tmp_path: Path):
        f = tmp_path / "bom.csv"
        f.write_bytes(b"\xef\xbb\xbfTRANSNR;BELOEB\n1;100.00\n")
        assert detect_encoding(f) == "utf-8-sig"

    def test_plain_utf8_detected(self, tmp_path: Path):
        f = tmp_path / "utf8.csv"
        f.write_text("TRANSNR;BELOEB\n1;100.00\n", encoding="utf-8")
        # utf-8-sig succeeds on plain utf-8 too (BOM becomes optional)
        assert detect_encoding(f) in ("utf-8-sig", "utf-8")

    def test_cp1252_detected(self, tmp_path: Path):
        f = tmp_path / "cp1252.csv"
        # Write a line with ø (U+00F8) encoded as Windows-1252 (0xF8)
        f.write_bytes(b"TITEL;BELOEB\nForl\xf8gger;500.00\n")
        assert detect_encoding(f) == "cp1252"

    def test_csv_encoding_stored_in_rows(self, tmp_path: Path):
        f = tmp_path / "enc.csv"
        f.write_text("TRANSNR,BELOEB\n1,100.00\n", encoding="utf-8")
        rows = parse_file(f, "csv")
        assert "_encoding" in rows[0]
        assert rows[0]["_encoding"] in ("utf-8-sig", "utf-8")


class TestDanishCSVNormalisation:
    """Tests for Danish comma-decimal auto-normalisation in the CSV parser."""

    def test_comma_decimal_in_beloeb_normalised(self, tmp_path: Path):
        f = tmp_path / "danish.csv"
        f.write_text(
            "TRANSNR;TRANSTYPE;ARTNR;BELOEB\n"
            '1;Salg;978-87-0000-000-0;"4.570,59"\n',
            encoding="utf-8",
        )
        rows = parse_file(f, "csv")
        assert rows[0]["beloeb"] == "4570.59"

    def test_period_decimal_unchanged(self, tmp_path: Path):
        f = tmp_path / "period.csv"
        f.write_text(
            "TRANSNR;TRANSTYPE;ARTNR;BELOEB\n"
            "1;Salg;978-87-0000-000-0;4570.59\n",
            encoding="utf-8",
        )
        rows = parse_file(f, "csv")
        assert rows[0]["beloeb"] == "4570.59"

    def test_non_numeric_field_with_comma_unchanged(self, tmp_path: Path):
        """Commas inside text fields (e.g. KANAL) must not be mangled."""
        f = tmp_path / "text_comma.csv"
        f.write_text(
            "TRANSNR;TRANSTYPE;KANAL;BELOEB\n"
            "1;Salg;Bog, Audio;100.00\n",
            encoding="utf-8",
        )
        rows = parse_file(f, "csv")
        # kanal is not a numeric field — comma should be preserved
        assert rows[0]["kanal"] == "Bog, Audio"
        assert rows[0]["beloeb"] == "100.00"
