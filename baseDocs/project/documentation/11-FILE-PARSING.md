# 11 — File Parsing

## Overview

The multi-format parser converts uploaded files into a normalized `list[dict]` representation. This is the common data format consumed by all validation rules.

**File**: `backend/app/validation/parser.py`

---

## Supported Formats

| Format | Extension | Library | Max Size |
|--------|-----------|---------|----------|
| CSV | `.csv` | pandas | 50 MB |
| Excel | `.xlsx` | openpyxl | 50 MB |
| JSON | `.json` | stdlib json | 50 MB |
| PDF | `.pdf` | pdfplumber | 50 MB |
| ZIP | `.zip` | zipfile | 50 MB |
| TAR/GZ | `.tar`, `.gz` | tarfile | 50 MB |
| RAR | `.rar` | rarfile | 50 MB |

Archives (ZIP/TAR/GZ/RAR) are extracted first, then each inner file is parsed individually.

---

## Normalized Output Format

Every format is converted to `list[dict]` where each dict is a row with string keys and mixed-type values.

### Reserved Keys

These keys are added to every row by the parser:

| Key | Type | Description |
|-----|------|-------------|
| `_row_number` | int | Original row index (1-based) |
| `_source` | str | Source filename |
| `_record_type` | str | Type identifier (`sale`, `summary`, `metadata`, etc.) |
| `_page_number` | int | PDF page number (PDF only) |

---

## CSV Parsing

**Library**: pandas

### Behavior

1. **Delimiter detection**: Auto-detects `;` (Schilling standard) vs `,` (generic CSV)
2. **Column normalization**: Column names are lowercased and stripped of whitespace
3. **Formula resolution**: Schilling exports sometimes contain Excel-style formulas like `=N/100`. The parser evaluates these to numeric values.
4. **Encoding**: UTF-8 with fallback to latin-1

### Schilling CSV Format

Typical Schilling export columns:

```csv
TRANSNR;TRANSTYPE;KONTO;AFTALE;ARTNR;KANAL;PRISGRUPPE;VILKAR;BILAGSNR;BILAGSDATO;ANTAL;STKPRIS;STKAFREGNSATS;BELOEB;VALUTA;SKAT;AFREGNBATCH
1001;Salg;AUTH-0042;AFT-001;978-87-1234;DK;PG1;V1;5001;2024-01-15;100;249.95;=10/100;2499.50;DKK;0;0
```

### Formula Handling

```python
# Input:  =10/100
# Output: 0.10

# Input:  =15/100
# Output: 0.15
```

The `=N/100` pattern is common in Schilling exports for representing royalty rates as percentage fractions.

---

## Excel Parsing

**Library**: openpyxl

### Behavior

1. Reads the **first worksheet** only
2. **First row** is treated as headers
3. Column names are normalized (lowercase, strip)
4. Empty rows are skipped
5. Read-only mode for performance

---

## JSON Parsing

**Library**: stdlib `json`

### Accepted Formats

**Flat array**:
```json
[
  {"TRANSNR": 1001, "TRANSTYPE": "Salg", ...},
  {"TRANSNR": 1002, "TRANSTYPE": "SalgTilb", ...}
]
```

**Wrapped object**:
```json
{
  "rows": [
    {"TRANSNR": 1001, "TRANSTYPE": "Salg", ...},
    {"TRANSNR": 1002, "TRANSTYPE": "SalgTilb", ...}
  ]
}
```

Both formats produce the same `list[dict]` output.

---

## PDF Parsing (Schilling-Specific)

**Library**: pdfplumber

This is a custom parser designed specifically for Schilling "Royalty afregning" PDF statements. It extracts structured data from the visual layout of the PDF.

### PDF Structure (Per Page)

```
┌─────────────────────────────────────────┐
│  HEADER: "Royalty afregning"            │
│                                          │
│  METADATA BLOCK:                         │
│  ├── Titel: <book title>                │
│  ├── Kontonr: <account>                 │
│  ├── Aftale: <agreement>                │
│  ├── Periode: <from> - <to>             │
│  └── Afregning nr: <number>             │
│                                          │
│  STOCK SECTION:                          │
│  ├── Primo lager: <opening stock>       │
│  └── Ultimo lager: <closing stock>      │
│                                          │
│  SALES TABLE:                            │
│  ┌──────────┬──────────┬─────┬─────────┐│
│  │Salgskanal│Prisgruppe│ Sats│  Antal   ││
│  │          │          │     │Pris │Roy ││
│  ├──────────┼──────────┼─────┼─────────┤│
│  │ DK       │ PG1      │ 10% │100│249  ││
│  │ Online   │ PG2      │ 15% │ 50│ 75  ││
│  └──────────┴──────────┴─────┴─────────┘│
│                                          │
│  SUMMARY SECTION:                        │
│  ├── Fordeling: <amount> (<pct>%)       │
│  ├── Rest garanti: <amount>             │
│  ├── Afgift: <amount>                   │
│  └── Til udbetaling: <payout amount>   │
└─────────────────────────────────────────┘
```

### Extracted Fields

**Metadata (per page)**:

| Field | Key | Description |
|-------|-----|-------------|
| Book title | `titel` | The work being settled |
| Account | `kontonr` | Recipient account number |
| Agreement | `aftale` | Agreement number |
| Period | `periode` | Settlement period (from–to) |
| Settlement number | `afregning_nr` | Unique settlement number |
| Opening stock | `primo_lager` | Beginning inventory |
| Closing stock | `ultimo_lager` | Ending inventory |

**Sales lines (per row)**:

| Field | Key | Description |
|-------|-----|-------------|
| Sales channel | `salgskanal` | DK, Online, Export, etc. |
| Price group | `prisgruppe` | PG1, PG2, etc. |
| Rate | `sats` | Royalty percentage |
| Quantity | `antal` | Number of units |
| Price | `pris` | Unit price or total price |
| Royalty | `royalty` | Calculated royalty amount |

**Summary lines (per page)**:

| Field | Key | Description |
|-------|-----|-------------|
| Distribution | `fordeling` | Total royalty before deductions |
| Distribution % | `fordeling_pct` | Author's share percentage |
| Guarantee remainder | `rest_garanti` | Guarantee deduction |
| Duty | `afgift` | Social duty deduction |
| Payout | `til_udbetaling` | Net payout amount |

### Danish Number Format Conversion

Schilling PDFs use Danish number formatting:

```
70.470,00 → 70470.00
1.250,50  → 1250.50
-500,00   → -500.00
```

The parser handles:
- Period as thousands separator
- Comma as decimal separator
- Negative numbers with leading minus

---

## Archive Extraction

**File**: `backend/app/services/archive_service.py`

### Supported Archives

| Format | Library | Extension |
|--------|---------|-----------|
| ZIP | `zipfile` | `.zip` |
| TAR | `tarfile` | `.tar`, `.tar.gz`, `.tgz` |
| GZ | `tarfile` + `gzip` | `.gz` |
| RAR | `rarfile` | `.rar` |

### Extraction Process

1. Open archive and list contents
2. Filter to allowed extensions: `csv`, `xlsx`, `json`, `pdf`
3. Skip junk files: `__MACOSX/`, `.DS_Store`, `Thumbs.db`
4. Extract each file to `{UPLOAD_DIR}/{uuid}.{ext}`
5. Return list of `(original_filename, stored_path, format)`

### Nested Archives

Currently, nested archives (archive within archive) are **not** extracted recursively.

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Unsupported file extension | 400 error before parsing |
| File too large | 400 error before parsing |
| CSV with wrong encoding | Falls back to latin-1 |
| Malformed JSON | 400 error with parse error message |
| Password-protected PDF | 400 error |
| Corrupted archive | 400 error with extraction failure message |
| Empty file | Parsed successfully with 0 rows |
| Excel with no sheets | 400 error |
