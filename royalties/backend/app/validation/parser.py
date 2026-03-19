"""File parser module — parses CSV, Excel, JSON, and PDF royalty statements
into a normalized list[dict] format for validation rules to consume.
"""

import json
import re
from pathlib import Path


from typing import Optional
import openpyxl
import pandas as pd
import pdfplumber

# Encodings tried in order when reading text files.
# Danish Schilling exports are typically UTF-8-BOM; older Windows environments
# use Windows-1252 (cp1252). latin-1 is a lossless last resort.
_ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "cp1252", "latin-1")

# Numeric field names (post-normalisation) where Danish comma-decimal format
# (e.g. "4.570,59") should be converted to a plain decimal string.
_NUMERIC_FIELDS = frozenset({
    "stkpris",
    "stkafregnpris",
    "stkafregnsats",
    "liniebeloeb",
    "beloeb",
    "linieskat",
    "linieafgift",
    "liniemoms",
    "skat",
    "antal",
})


def detect_encoding(file_path: Path) -> str:
    """Detect the encoding of a file by trying candidates in order.

    Returns the first encoding that decodes the file without error.
    Falls back to 'latin-1' (always succeeds, may produce garbled text).
    """
    raw_bytes = file_path.read_bytes()
    for enc in _ENCODING_CANDIDATES:
        try:
            raw_bytes.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue
    return "latin-1"


def parse_file(file_path: Path, file_format: str) -> list[dict]:
    """Auto-detect format and parse into a normalized list of row dicts.

    Each dict represents a royalty line with normalized field names.
    """
    parsers = {
        "csv": _parse_csv,
        "xlsx": _parse_excel,
        "json": _parse_json,
        "pdf": _parse_pdf,
    }
    parser = parsers.get(file_format)
    if not parser:
        raise ValueError(f"Unsupported file format: {file_format}")
    return parser(file_path)


# ---------------------------------------------------------------------------
# CSV parser — supports both Schilling native (semicolon) and standard (comma)
# ---------------------------------------------------------------------------


def _parse_csv(file_path: Path) -> list[dict]:
    """Parse a CSV file, auto-detecting encoding, delimiter, and number format."""
    encoding = detect_encoding(file_path)
    raw = file_path.read_text(encoding=encoding)

    # Detect delimiter: semicolon count vs. comma count in first line
    first_line = raw.split("\n", 1)[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

    df = pd.read_csv(file_path, sep=delimiter, encoding=encoding, dtype=str)
    df.columns = [c.strip().strip('"') for c in df.columns]

    rows = []
    for idx, row in df.iterrows():
        normalized = {}
        for col in df.columns:
            val = str(row[col]).strip().strip('"') if pd.notna(row[col]) else ""
            # Handle Schilling =N/100 formulas
            val = _resolve_formula(val)
            norm_key = _normalize_column_name(col)
            # Normalise Danish comma-decimal format on known numeric fields
            # (e.g. "4.570,59" → "4570.59"). Only triggered when a comma is
            # present so standard period-decimal values are never touched.
            if norm_key in _NUMERIC_FIELDS and "," in val:
                val = _danish_number_to_str(val)
            normalized[norm_key] = val
        normalized["_row_number"] = idx + 2  # 1-based, skip header
        normalized["_source"] = "csv"
        normalized["_encoding"] = encoding
        rows.append(normalized)
    return rows


def _resolve_formula(val: str) -> str:
    """Resolve Schilling =N/100 Excel formulas to plain numbers."""
    match = re.match(r"^=(-?\d+)/(\d+)$", val)
    if match:
        numerator = int(match.group(1))
        denominator = int(match.group(2))
        if denominator != 0:
            return str(numerator / denominator)
    return val


# ---------------------------------------------------------------------------
# Excel parser
# ---------------------------------------------------------------------------


def _parse_excel(file_path: Path) -> list[dict]:
    """Parse an Excel file, using the first worksheet with header row."""
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(next(rows_iter))]
    normalized_headers = [_normalize_column_name(h) for h in headers]

    rows = []
    for row_idx, row in enumerate(rows_iter, start=2):
        normalized = {}
        for col_idx, val in enumerate(row):
            key = (
                normalized_headers[col_idx]
                if col_idx < len(normalized_headers)
                else f"col_{col_idx}"
            )
            normalized[key] = str(val).strip() if val is not None else ""
        normalized["_row_number"] = row_idx
        normalized["_source"] = "xlsx"
        rows.append(normalized)
    wb.close()
    return rows


# ---------------------------------------------------------------------------
# JSON parser
# ---------------------------------------------------------------------------


def _parse_json(file_path: Path) -> list[dict]:
    """Parse a JSON file containing royalty statement data."""
    encoding = detect_encoding(file_path)
    data = json.loads(file_path.read_text(encoding=encoding))

    # Support both flat list and nested { "rows": [...] } format
    if isinstance(data, list):
        raw_rows = data
    elif isinstance(data, dict) and "rows" in data:
        raw_rows = data["rows"]
    else:
        raise ValueError("JSON must be a list of objects or contain a 'rows' array")

    rows = []
    for idx, raw in enumerate(raw_rows):
        normalized = {
            _normalize_column_name(k): str(v) if v is not None else "" for k, v in raw.items()
        }
        normalized["_row_number"] = idx + 1
        normalized["_source"] = "json"
        rows.append(normalized)
    return rows


# ---------------------------------------------------------------------------
# PDF parser — Schilling "Royalty afregning" specific
# ---------------------------------------------------------------------------


def _parse_pdf(file_path: Path) -> list[dict]:
    """Parse a Schilling Royalty afregning PDF into normalized rows.

    Each page represents one agreement. The parser extracts:
    - Metadata block (Titel, Kontonr, Aftale, Periode, etc.)
    - Sales table lines (Salgskanal, Prisgruppe, Sats, Antal, Pris, Royalty)
    - Summary/deduction lines (Royalty fordeling, Rest garanti, Afgift, Til udbetaling)
    """
    rows = []
    with pdfplumber.open(str(file_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            page_data = _parse_pdf_page(text, page_num)
            rows.extend(page_data)
    return rows


def _parse_pdf_page(text: str, page_num: int) -> list[dict]:
    """Parse a single PDF page into one or more row dicts."""
    rows = []

    # Extract metadata
    metadata = _extract_pdf_metadata(text)
    metadata["_page_number"] = str(page_num)
    metadata["_source"] = "pdf"

    # Flag pages where substantial text exists but no field labels were matched.
    # This indicates missing lead texts (font/rendering issue in the PDF).
    # Heuristic: page has >100 chars of text, contains at least one digit, yet
    # none of the key metadata fields could be extracted.
    # Only set this flag on pages that have agreement-page structural content
    # (stock block or sales table headers) — royalty sum/overview pages
    # legitimately use column layouts without field labels and must not be flagged.
    _LABEL_FIELDS = ("aftale", "kontonr", "periode", "afregning_nr",
                     "total_oplag", "periodens_salg", "lagerbeholdning")
    has_any_extracted = any(metadata.get(f) for f in _LABEL_FIELDS)
    has_content = len(text.strip()) > 100 and any(c.isdigit() for c in text)
    _AGREEMENT_PAGE_INDICATORS = ("total oplag", "salgskanal", "frieksemplar")
    looks_like_agreement_page = any(ind in text.lower() for ind in _AGREEMENT_PAGE_INDICATORS)
    if has_content and not has_any_extracted and looks_like_agreement_page:
        metadata["_no_labels_detected"] = "true"

    # Detect "last settlement" flag
    if "sidsteafregning" in text.lower().replace(" ", ""):
        metadata["is_final_settlement"] = "true"

    # Extract sales lines
    sales_lines = _extract_pdf_sales_lines(text)

    # Extract summary values
    summary = _extract_pdf_summary(text)

    if sales_lines:
        for idx, sale in enumerate(sales_lines):
            row = {**metadata, **sale}
            row["_row_number"] = page_num * 100 + idx + 1
            row["_record_type"] = "sales_line"
            rows.append(row)

    # Always add a summary row for the page
    summary_row = {**metadata, **summary}
    summary_row["_row_number"] = page_num * 100 + 99
    summary_row["_record_type"] = "page_summary"
    rows.append(summary_row)

    return rows


def _extract_pdf_metadata(text: str) -> dict:
    """Extract key-value metadata pairs from a PDF page."""
    metadata = {}

    # Titel and Aftalenavn are free-text single-line fields — match on original
    # text (newlines intact) so \n acts as a natural stop boundary.
    titel_match = re.search(r"Titel:\s*(.+)", text, re.IGNORECASE)
    if titel_match:
        metadata["titel"] = titel_match.group(1).strip()

    aftalenavn_match = re.search(r"Aftalenavn:\s*(.+)", text, re.IGNORECASE)
    if aftalenavn_match:
        metadata["aftalenavn"] = aftalenavn_match.group(1).strip()

    # All remaining fields use newline-collapsed text for robustness against
    # pdfplumber occasionally splitting a value across two lines.
    other_patterns = {
        # Account / agreement identifiers — "Aftalenr.:" and plain "Aftale:" hold
        # the agreement number/ID; "Aftalenavn:" holds the human-readable name which
        # can be arbitrarily long and must NOT be captured into the aftale ID field.
        "kontonr":      r"Kontonr\.?:\s*(\S+)",
        "aftale":       r"Aftalenr?\.?:\s*(\S+)",
        "periode":      r"(?:Periode|Til\s*dato):\s*(\S+)",
        "afregning_nr": r"Afregnings?\s*nr\.?:\s*(\d+)",
        # Stock / circulation block (top-left of the Schilling PDF layout)
        "total_oplag":      r"Total\s*oplag:\s*(-?[\d.,]+)",
        "frieksemplarer":   r"Frieksemplar(?:er)?:\s*(-?[\d.,]+)",
        "svind":            r"Svind:?\s+(-?[\d.,]+)",
        "makulatur":        r"Makul(?:atur|eret):?\s*(-?[\d.,]+)",
        "periodens_salg":   r"Periodens\s*salg:\s*(-?[\d.,]+)",
        "lagerbeholdning":  r"Lagerbeholdning:\s*(-?[\d.,]+)",
        "tidligere_afregnet": r"Tidligere\s*afregnet:\s*(-?[\d.,]+)",
        "auto_reguleret":     r"Auto\s*reguleret:\s*(-?[\d.,]+)",
        # Warehouse snapshot (used when explicit opening/closing stock is shown)
        "primo_lager":      r"Primolager:\s*(-?[\d.,]+)",
        "ultimo_lager":     r"Ultimolager:\s*(-?[\d.,]+)",
    }

    clean_text = text.replace("\n", " ")

    # Fields whose values are numeric quantities — normalise via _danish_number_to_str
    _numeric_metadata = {
        "total_oplag", "frieksemplarer", "svind", "makulatur",
        "periodens_salg", "lagerbeholdning", "primo_lager", "ultimo_lager",
        "tidligere_afregnet", "auto_reguleret",
    }

    for field, pattern in other_patterns.items():
        match = re.search(pattern, clean_text, re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            metadata[field] = _danish_number_to_str(raw) if field in _numeric_metadata else raw

    return metadata


def _extract_pdf_sales_lines(text: str) -> list[dict]:
    """Extract sales table rows from a PDF page.

    Sales lines appear after the column headers (Salgskanal:, Prisgruppe:, etc.)
    and before the summary section.
    """
    lines = text.split("\n")
    sales_lines = []
    in_sales_section = False

    for line in lines:
        stripped = line.strip()

        # Detect start of sales section by header row
        if "Salgskanal:" in stripped or "Prisgruppe:" in stripped:
            in_sales_section = True
            continue

        # Detect end of sales section
        if in_sales_section and (
            "Royaltyfordeling" in stripped.replace(" ", "")
            or "Tiludbetaling" in stripped.replace(" ", "")
            or "Tiln" in stripped.replace(" ", "")
            or "Overf" in stripped.replace(" ", "")
        ):
            in_sales_section = False
            continue

        if not in_sales_section:
            continue

        # Parse a sales line — format: Channel PriceGroup Rate Qty Price Royalty
        sale = _parse_sales_line(stripped)
        if sale:
            sales_lines.append(sale)

    return sales_lines


def _parse_sales_line(line: str) -> Optional[dict]:
    """Parse a single sales line from the PDF table.

    Expected format varies, but typically:
    "Retail Normalsale 50,000% 435 324,00 70.470,00"
    or fixed rate: "Retail Normalsale 500,000kr. 1.000 500,00 500.000,00"
    """
    # Match percentage rate lines
    pct_match = re.match(
        r"^(.+?)\s+"  # Channel
        r"(.+?)\s+"  # Price group
        r"(-?[\d.,]+)%\s+"  # Rate (percentage)
        r"(-?[\d.,]+)\s+"  # Quantity
        r"(-?[\d.,]+)\s+"  # Price basis
        r"(-?[\d.,]+)$",  # Royalty amount
        line.strip(),
    )
    if pct_match:
        sats_display, sats_fraction = _parse_rate_pct(pct_match.group(3))
        return {
            "salgskanal": pct_match.group(1).strip(),
            "prisgruppe": pct_match.group(2).strip(),
            "sats": sats_display,
            "sats_value": str(sats_fraction),
            "sats_type": "percentage",
            "antal": _danish_number_to_str(pct_match.group(4)),
            "prisgrundlag": _danish_number_to_str(pct_match.group(5)),
            "royalty_amount": _danish_number_to_str(pct_match.group(6)),
        }

    # Match fixed-rate (kr.) lines
    kr_match = re.match(
        r"^(.+?)\s+"  # Channel
        r"(.+?)\s+"  # Price group
        r"(-?[\d.,]+)kr\.\s+"  # Rate (fixed amount per unit)
        r"(-?[\d.,]+)\s+"  # Quantity
        r"(-?[\d.,]+)\s+"  # Price basis
        r"(-?[\d.,]+)$",  # Royalty amount
        line.strip(),
    )
    if kr_match:
        return {
            "salgskanal": kr_match.group(1).strip(),
            "prisgruppe": kr_match.group(2).strip(),
            "sats": kr_match.group(3).replace(".", "").replace(",", ".") + " kr.",
            "sats_value": _danish_number_to_str(kr_match.group(3)),
            "sats_type": "fixed",
            "antal": _danish_number_to_str(kr_match.group(4)),
            "prisgrundlag": _danish_number_to_str(kr_match.group(5)),
            "royalty_amount": _danish_number_to_str(kr_match.group(6)),
        }

    # Single-number line (subtotal line like "-780,00")
    subtotal_match = re.match(r"^(-?[\d.,]+)$", line.strip())
    if subtotal_match:
        return None  # Subtotals handled in summary extraction

    return None


def _extract_pdf_summary(text: str) -> dict:
    """Extract summary/deduction values from a PDF page."""
    summary = {}
    clean = text.replace("\n", " ")

    # Royalty fordeling: 10,000% af -780,00   => -78,00
    fordeling_match = re.search(
        r"Royaltyfordeling:\s*(-?[\d.,]+)%\s*af\s*(-?[\d.,]+)\s+(-?[\d.,]+)",
        clean.replace(" ", ""),
    )
    if not fordeling_match:
        fordeling_match = re.search(
            r"Royalty\s*fordeling:\s*(-?[\d.,]+)\s*%\s*af\s*(-?[\d.,]+)\s+(-?[\d.,]+)",
            clean,
        )
    if fordeling_match:
        _, fordeling_fraction = _parse_rate_pct(fordeling_match.group(1))
        summary["fordeling_pct"] = str(fordeling_fraction)
        summary["fordeling_base"] = _danish_number_to_str(fordeling_match.group(2))
        summary["fordeling_amount"] = _danish_number_to_str(fordeling_match.group(3))

    # Rest global garanti
    garanti_match = re.search(r"Restglobalgaranti:\s*(-?[\d.,]+)", clean.replace(" ", ""))
    if not garanti_match:
        garanti_match = re.search(r"Rest\s*global\s*garanti:\s*(-?[\d.,]+)", clean)
    if garanti_match:
        summary["rest_garanti"] = _danish_number_to_str(garanti_match.group(1))

    # Afgift (duty/tax)
    afgift_match = re.search(r"Afgift:\s*(-?[\d.,]+)", clean)
    if afgift_match:
        summary["afgift"] = _danish_number_to_str(afgift_match.group(1))

    # Til udbetaling (payout)
    udbetaling_match = re.search(r"Tiludbetaling:\s*(-?[\d.,]+)", clean.replace(" ", ""))
    if not udbetaling_match:
        udbetaling_match = re.search(r"Til\s*udbetaling:\s*(-?[\d.,]+)", clean)
    if udbetaling_match:
        summary["til_udbetaling"] = _danish_number_to_str(udbetaling_match.group(1))

    # Overført fra tidligere (amount carried forward FROM a previous settlement — adds to current base)
    overfort_match = re.search(r"Overf.rtfra.+?:\s*(-?[\d.,]+)", clean.replace(" ", ""))
    if overfort_match:
        summary["overfort"] = _danish_number_to_str(overfort_match.group(1))

    # Til næste afregning / Overført til næste (amount carried TO next settlement — reduces current payout)
    naeste_match = re.search(r"Tiln.steafregning:\s*(-?[\d.,]+)", clean.replace(" ", ""))
    if not naeste_match:
        naeste_match = re.search(r"Overf.rttilN.ste.+?:\s*(-?[\d.,]+)", clean.replace(" ", ""), re.IGNORECASE)
    if naeste_match:
        summary["til_naeste"] = _danish_number_to_str(naeste_match.group(1))
        # For compatibility with validation logic, also map to carry_forward
        summary["carry_forward"] = summary["til_naeste"]

    return summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_rate_pct(raw: str) -> tuple[str, float]:
    """Parse a percentage rate string to (display_str, fraction_value).

    Handles both Danish (dot=thousands, comma=decimal) and international
    (dot=decimal) formats.  Since royalty rates above 100% are impossible,
    a parsed value > 1.0 is used as a signal that the dot was the decimal
    separator rather than a thousands separator, and the string is re-parsed
    accordingly.

    Examples
    --------
    Danish:        '51,000' -> ('51.0%', 0.51)   # comma=decimal
    International: '51.000' -> ('51.0%', 0.51)   # dot=decimal (re-parsed)
    Danish:        '10,000' -> ('10.0%', 0.10)
    """
    # First try: Danish convention (dot=thousands, comma=decimal)
    danish = raw.replace(".", "").replace(",", ".")
    try:
        danish_val = float(danish) / 100
        if danish_val <= 1.0:  # <= 100 % — plausible royalty rate
            return danish + "%", danish_val
    except ValueError:
        pass

    # Fallback: international convention (dot=decimal, comma=thousands)
    intl = raw.replace(",", "")
    try:
        intl_val = float(intl) / 100
        return intl + "%", intl_val
    except ValueError:
        pass

    # Last resort — return Danish result even if implausible
    return danish + "%", float(danish) / 100


def _danish_number_to_str(val: str) -> str:
    """Convert a number string (Danish or international) to a plain decimal string.

    When both separators are present, whichever comes last is the decimal point —
    this is unambiguous regardless of locale:
      3,398.20  → period last → comma=thousands, period=decimal → 3398.20
      3.398,20  → comma last  → period=thousands, comma=decimal → 3398.20

    When only one separator is present, the digit-count heuristic applies:
      -1,005    → 3 digits after comma → thousands separator → -1005
      -780,00   → 2 digits after comma → decimal separator  → -780.00
      1.000     → 3 digits after period → thousands          → 1000
      149.95    → 2 digits after period → decimal            → 149.95
    """
    val = val.strip()
    has_comma = "," in val
    has_dot = "." in val

    if has_comma and has_dot:
        # Both separators: last one is the decimal point
        if val.rfind(".") > val.rfind(","):
            # e.g. 3,398.20 → remove commas (thousands), keep period (decimal)
            return val.replace(",", "")
        else:
            # e.g. 3.398,20 → remove periods (thousands), comma→period (decimal)
            return val.replace(".", "").replace(",", ".")

    if has_comma:
        after = val.rsplit(",", 1)[-1].lstrip("-")
        if len(after) == 3 and after.isdigit():
            # e.g. -1,005 → comma is thousands separator
            return val.replace(",", "")
        # e.g. -780,00 → comma is decimal separator
        return val.replace(",", ".")

    if has_dot:
        parts = val.split(".")
        if len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
            # e.g. 1.000 → period is thousands separator
            return val.replace(".", "")
        # e.g. 149.95 → period is decimal separator
        return val

    return val


def _normalize_column_name(name: str) -> str:
    """Normalize a column header name to a consistent lowercase form."""
    mapping = {
        "artnr": "artnr",
        "arttxt": "arttxt",
        "kontonr": "kontonr",
        "forfnavn": "forfnavn",
        "stkafregnsats": "stkafregnsats",
        "stkafregnpris": "stkafregnpris",
        "liniebeloeb": "liniebeloeb",
        "liniebelqb": "liniebeloeb",
        "linieskat": "linieskat",
        "linieafgift": "linieafgift",
        "liniemoms": "liniemoms",
        "linieantalw": "antal",
        "linieantas": "antal",
        "linieantat": "antal",
        "linieantel": "antal",
        "linieantal": "antal",
        "bildato": "bildato",
        "transnr": "transnr",
        "transtype": "transtype",
        "konto": "konto",
        "aftale": "aftale",
        "kanal": "kanal",
        "prisgruppe": "prisgruppe",
        "vilkar": "vilkar",
        "bilagsnr": "bilagsnr",
        "bilagsdato": "bilagsdato",
        "antal": "antal",
        "stkpris": "stkpris",
        "beloeb": "beloeb",
        "valuta": "valuta",
        "skat": "skat",
        "afregnbatch": "afregnbatch",
        "dim1": "dim1",
    }
    key = name.lower().strip().replace(" ", "").replace("_", "")
    return mapping.get(key, name.lower().strip())
