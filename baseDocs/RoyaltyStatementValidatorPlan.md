# Royalty Statement Validator — Project Plan

## 1. Project Overview

Build a standalone web application that lets users **upload a royalty statement file** and **validates its content** against the business rules used in the Schilling ERP royalty settlement system. The goal is to catch inconsistencies and errors — missing titles, incorrect rates, calculation mismatches — **before** the statement is processed further or shared with authors.

### What This App Is

A lightweight, independent validation tool. It does **not** replace the Schilling settlement engine. Instead, it reads exported/generated royalty statement files and applies a set of validation checks derived from the same business rules that the Schilling C++ engine enforces (documented in [RoyaltySettlementSystem.md](RoyaltySettlementSystem.md)).

### What This App Is Not

- Not a full settlement calculation engine
- Not a replacement for the Schilling ERP module
- Not connected to the Oracle database in real-time (it works on exported files)

---

## 2. Requirements (from Acceptance Criteria)

### 2.1 User Access

| Requirement | Detail |
|-------------|--------|
| User can enter a nickname or user ID | Simple identification — no heavy auth needed for v1 |
| User can access the royalty statement validator | Browser-based, no install required |

### 2.2 File Upload

| Requirement | Detail |
|-------------|--------|
| User can upload a royalty statement file | Drag-and-drop or file picker; supported formats: CSV, Excel (.xlsx), JSON, PDF |
| System validates that a file has been uploaded before processing | Frontend + backend guard |
| System stores the uploaded file or file reference | Server-side storage with unique ID per upload |

### 2.3 Statement Validation

| Requirement | Detail |
|-------------|--------|
| System validates the content of the royalty statement | Parse → validate → report |
| Missing titles | Detect rows where product/ISBN (Artnr) is blank or not found in reference data |
| Missing or invalid royalty rates | Detect rows where the royalty rate is zero, negative, or outside expected bounds |
| Inconsistent amounts | Detect rows where `quantity × unit_price × rate ≠ reported_amount` (within tolerance) |
| Calculation errors | Detect incorrect tax/VAT calculations, guarantee offset mismatches, settlement total discrepancies |
| System flags any validation issues found | Each issue tagged with severity: error, warning, or info |

### 2.4 Result Presentation

| Requirement | Detail |
|-------------|--------|
| Structured result view | Grouped by: passed checks, warnings, errors |
| User can see passed checks, warnings, errors | Summary counts + detailed list |
| User can review details of each issue | Expandable rows showing: line number, field, expected vs. actual, rule description |

---

## 3. Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Backend** | Python 3.12+ | Required by spec; rich ecosystem for data parsing/validation |
| **REST API** | FastAPI | Async, auto-generated OpenAPI docs, type-safe with Pydantic |
| **File parsing** | openpyxl (Excel), pdfplumber (PDF table extraction), pandas (CSV/data manipulation) | Robust parsing of tabular royalty data |
| **Database** | PostgreSQL 16 | Production-grade from day one; stores uploads, validation runs, results; runs in Docker for local dev |
| **ORM** | SQLAlchemy 2.0 | Async support, migrations via Alembic |
| **Frontend** | React 19 + TypeScript | Modern SPA; matches existing React knowledge in the Schilling codebase |
| **UI framework** | Tailwind CSS + shadcn/ui | Clean, professional look with minimal custom CSS |
| **Build tool** | Vite | Fast dev server and builds |
| **Testing** | pytest (backend), Vitest + Playwright (frontend) | Full coverage: unit + integration + E2E |
| **Containerization** | Docker + docker-compose | One-command local setup |

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (React SPA)                  │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Login /  │  │  File Upload │  │  Results Viewer   │  │
│  │  Identify │  │  Component   │  │  (pass/warn/err)  │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │ REST API (JSON)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                          │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Auth /   │  │  Upload      │  │  Validation       │  │
│  │  User     │  │  Service     │  │  Engine           │  │
│  │  Service  │  │              │  │                   │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
│                                           │              │
│                                    ┌──────┴──────┐       │
│                                    │ Rule Plugins│       │
│                                    │ (one per    │       │
│                                    │  check)     │       │
│                                    └─────────────┘       │
│                         │                                │
│                    ┌────┴────┐                            │
│                    │PostgreSQL│                           │
│                    └─────────┘                            │
└─────────────────────────────────────────────────────────┘
```

### 4.1 Backend Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings (env-driven)
│   ├── models/                  # SQLAlchemy models
│   │   ├── user.py
│   │   ├── upload.py
│   │   └── validation_result.py
│   ├── schemas/                 # Pydantic request/response models
│   │   ├── user.py
│   │   ├── upload.py
│   │   └── validation.py
│   ├── api/                     # Route handlers
│   │   ├── auth.py              # POST /api/auth/identify
│   │   ├── uploads.py           # POST /api/uploads, GET /api/uploads/{id}
│   │   └── validations.py       # POST /api/validations/{upload_id}, GET results
│   ├── services/                # Business logic
│   │   ├── upload_service.py
│   │   └── validation_service.py
│   ├── validation/              # Validation engine + rule plugins
│   │   ├── engine.py            # Orchestrates all rules
│   │   ├── base_rule.py         # Abstract base class for rules
│   │   ├── parser.py            # File parsing (CSV, Excel, JSON, PDF)
│   │   └── rules/               # One file per validation rule
│   │       ├── missing_titles.py
│   │       ├── invalid_rates.py
│   │       ├── amount_consistency.py
│   │       ├── calculation_errors.py
│   │       ├── tax_validation.py
│   │       ├── guarantee_offsets.py
│   │       ├── settlement_totals.py
│   │       ├── duplicate_entries.py
│   │       └── date_validation.py
│   └── db/                      # Database setup
│       ├── database.py
│       └── migrations/
├── tests/
│   ├── test_parser.py
│   ├── test_rules/
│   │   ├── test_missing_titles.py
│   │   ├── test_invalid_rates.py
│   │   ├── test_amount_consistency.py
│   │   └── ...
│   ├── test_api/
│   │   ├── test_uploads.py
│   │   └── test_validations.py
│   └── fixtures/                # Sample royalty statement files
│       ├── valid_statement.csv
│       ├── valid_statement.pdf
│       ├── missing_titles.csv
│       ├── bad_rates.xlsx
│       └── calculation_errors.json
├── requirements.txt
├── Dockerfile
└── pyproject.toml
```

### 4.2 Frontend Structure

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/                     # API client (fetch wrappers)
│   │   └── client.ts
│   ├── pages/
│   │   ├── LoginPage.tsx        # Nickname/ID entry
│   │   ├── UploadPage.tsx       # File upload with drag-and-drop
│   │   └── ResultsPage.tsx      # Validation results viewer
│   ├── components/
│   │   ├── FileDropzone.tsx     # Drag-and-drop file upload area
│   │   ├── ValidationSummary.tsx# Pass/warn/error counts
│   │   ├── ValidationDetail.tsx # Expandable issue rows
│   │   ├── StatusBadge.tsx      # Error/Warning/Pass badge
│   │   └── Layout.tsx           # App shell, navigation
│   ├── types/
│   │   └── index.ts             # TypeScript interfaces
│   └── hooks/
│       ├── useUpload.ts
│       └── useValidation.ts
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── package.json
└── Dockerfile
```

---

## 5. API Design

### 5.1 Endpoints

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| `POST` | `/api/auth/identify` | Register/identify user | `{ "nickname": "string" }` | `{ "user_id": "uuid", "nickname": "string" }` |
| `POST` | `/api/uploads` | Upload a statement file | `multipart/form-data` (file + user_id) | `{ "upload_id": "uuid", "filename": "string", "status": "uploaded" }` |
| `GET` | `/api/uploads/{upload_id}` | Get upload details | — | `{ "upload_id", "filename", "uploaded_at", "row_count", "status" }` |
| `POST` | `/api/validations/{upload_id}/run` | Trigger validation | `{ "rules": ["all"] }` (optional filter) | `{ "validation_id": "uuid", "status": "running" }` |
| `GET` | `/api/validations/{validation_id}` | Get validation results | — | `ValidationResultResponse` (see below) |
| `GET` | `/api/validations/{validation_id}/issues` | Get detailed issues | `?severity=error&page=1&size=50` | Paginated issue list |

### 5.2 Validation Result Response

```json
{
  "validation_id": "uuid",
  "upload_id": "uuid",
  "status": "completed",
  "started_at": "2026-03-16T10:00:00Z",
  "completed_at": "2026-03-16T10:00:03Z",
  "summary": {
    "total_rows": 1250,
    "passed_checks": 18,
    "warnings": 3,
    "errors": 2,
    "rules_executed": 9
  },
  "issues": [
    {
      "id": "uuid",
      "severity": "error",
      "rule": "amount_consistency",
      "rule_description": "Quantity × Unit Price × Rate must equal the reported amount",
      "row_number": 47,
      "field": "BELOEB",
      "expected_value": "1250.00",
      "actual_value": "1350.00",
      "difference": "100.00",
      "context": {
        "agreement": "AFT-2024-001",
        "product": "978-87-1234-567-8",
        "recipient": "AUTH-0042"
      }
    }
  ]
}
```

---

## 6. Validation Rules — Mapped from Schilling ERP

Each rule is implemented as a plugin class inheriting from `BaseRule`. This makes it easy to add new rules without modifying the engine.

### 6.1 Rule Plugin Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationIssue:
    severity: Severity
    rule_id: str
    rule_description: str
    row_number: int | None
    field: str | None
    expected_value: str | None
    actual_value: str | None
    message: str
    context: dict

class BaseRule(ABC):
    @property
    @abstractmethod
    def rule_id(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def validate(self, statement_data: list[dict]) -> list[ValidationIssue]: ...
```

### 6.2 Rules Catalogue

The validation rules are derived from the business logic documented in [RoyaltySettlementSystem.md](RoyaltySettlementSystem.md).

#### Rule 1: Missing Titles (`missing_titles`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | `ROYPOST.ARTNR` — every posting must have a product/ISBN |
| **What it checks** | Every row in the statement has a non-empty product identifier (ISBN/Artnr) |
| **Severity** | ERROR if blank; WARNING if format is invalid (bad ISBN checksum) |
| **Schilling parallel** | The `IndTrans` import and `CoupledTransaction` coupling both require a valid `ARTNR` |

#### Rule 2: Missing or Invalid Royalty Rates (`invalid_rates`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | `ROYAFTALEKANALPRIS.STKAFREGNSATS` and `RoySharesLadder` staircase rates |
| **What it checks** | Rate is present, non-negative, and within a reasonable range (0%–100% for percentage, or > 0 for per-unit) |
| **Severity** | ERROR if rate is 0 or negative; WARNING if rate exceeds typical bounds (e.g., > 50%) |
| **Schilling parallel** | `Gem.cpp` applies the rate from `ROYAFTALEKANALPRIS`; rate of 0 produces zero royalty — likely an error |

#### Rule 3: Amount Consistency (`amount_consistency`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | Core calculation in `Gem.cpp`: `royalty = quantity × unit_price × rate` (simplified) |
| **What it checks** | For each sales line: validates that `antal_solgte × prisgrundlag × sats ≈ royalty_amount` within tolerance. For **percentage rates** (`50,000%`): `435 × 324.00 × 0.50 = 70,470.00`. For **fixed-amount rates** (`500,000 kr.`): `1000 × 500.00 = 500,000.00`. Tolerance: ±1.00 for rounding |
| **Severity** | ERROR if difference > 1.00; WARNING if difference is 0.01–1.00 |
| **Schilling parallel** | The `SalgArray` in `Afregn.cpp` computes each line's amount; `KompRoypost` uses 0.01 tolerance for compression matching |
| **Known limitation** | This rule applies the simple formula. Staircase/ladder rates (`RoySharesLadder`), depreciation, minimum royalty floors, and FIFO/LIFO return matching produce amounts that won't match the simple formula — these cases generate an INFO instead of ERROR. See Section 17: Known Limitations |

#### Rule 4: Calculation Errors — Tax/Withholding (`tax_validation`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | `TaxCalculation.hpp` — `GenerateIntermediateCalculations()`, `GetTaxAmount()` |
| **What it checks** | In v1 (without reference data): checks that if an "Afgift" (duty) line is present in the PDF summary, its amount is non-zero and negative (a deduction). In v2 (with reference data): tax amount = gross amount × configured tax rate; pension/AMBI deductions match configured rates |
| **Severity** | WARNING if duty line is present but amount is zero or missing; ERROR (v2 only) if tax amount diverges from configured rate |
| **Schilling parallel** | `TaxCalculation` object computes multi-level deductions; `CheckCombination()` in `DivRut.cpp` validates VAT code/TIN pairing |
| **Known limitation** | Full tax validation requires recipient-specific tax codes and rates as reference data. Without it, only structural checks are possible. See Section 17: Known Limitations |

#### Rule 5: Guarantee Balance Validation (`guarantee_validation`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | `Afregn.cpp` → `RoySkrivGaranti()`; guarantee types: local, global, method |
| **What it checks** | In the PDF: when a "Rest global garanti" (remaining global guarantee) line appears, validates it is a negative value (deduction from payout). Cross-checks that `author_share − rest_garanti − afgift = til_udbetaling`. In CSV/Excel: paired guarantee/offset matching (`GarGlobal` ↔ `GarGlobalMod`) with matching absolute amounts |
| **Severity** | ERROR if the guarantee deduction makes payout negative (impossible state); WARNING if guarantee reference found without matching amount in the same file (may exist in prior settlements) |
| **Schilling parallel** | `RoyHentGlobGaranti2()` and `RoyHentGaranti()` load guarantees; offsets are posted as paired `*Mod` transactions |
| **Known limitation** | Global guarantees span multiple agreements and settlements. A single file may show only the offset without the original. The rule only validates within-file consistency. See Section 17: Known Limitations |

#### Rule 6: Settlement Total Consistency (`settlement_totals`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | `GenUdskriv.cpp` sum pages; `PaymentVoucherReport` |
| **What it checks** | Per page/agreement: sum of sales line royalties = royalty subtotal; `royalty_subtotal × royalty_fordeling_pct = author_share`; `author_share − garanti − afgift = til_udbetaling`. Across all pages: total payout is the sum of each page's `til_udbetaling` |
| **Severity** | ERROR if totals diverge |
| **Schilling parallel** | Settlement statements have sum pages that must balance; `ROYUDBETALT` (paid out) should equal the net of all other postings |
| **PDF-specific** | From the real Schilling PDF: validates the chain `sales lines → subtotal → royalty fordeling → rest garanti → afgift → til udbetaling` |

#### Rule 7: Duplicate Entries (`duplicate_entries`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | `ROYPOST.TRANSNR` is unique; `KompRoypost` compression groups by key dimensions |
| **What it checks** | No two rows share the same `(agreement, product, channel, price_group, transaction_type, voucher_number)` unless they are legitimate compression groups |
| **Severity** | WARNING — duplicates may be intentional (multiple terms) but should be reviewed |

#### Rule 8: Date Validation (`date_validation`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | `ROY_AFRDAT_MAX/MIN`, `FORF_AC_AFRDAT`, `ROY_AFREGNESFORAFREGNET` |
| **What it checks** | Settlement date is within the stated period; voucher date is not before settlement date; no future-dated transactions beyond settlement date |
| **Severity** | ERROR if voucher date < settlement date; WARNING if dates are at period boundaries |
| **Schilling parallel** | `SettlementCriteria.cpp` validates `SettlementDateFrom`; error code `FORF_AC_AFRDAT` blocks voucher dates before settlement |

#### Rule 9: Advance/Offset Balance (`advance_balance`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | `ROYFORSKUD` / `ROYFORSKUDMOD` pairing; `IAdvance` in Rights module |
| **What it checks** | Total advance offsets do not exceed original advance amounts per agreement |
| **Severity** | ERROR if offset > advance (over-recouped); WARNING if advance has zero offset (never recouped) in a final settlement |

#### Rule 10: Recipient Share Validation (`recipient_shares`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | `Arv.cpp`, `IRoyDistribution`, error code `RIG_AUTSHA_TH` |
| **What it checks** | When multiple recipients exist for one agreement, their percentage shares sum to ≤ 100% |
| **Severity** | ERROR if sum > 100%; WARNING if sum < 100% (unclaimed share) |

#### Rule 11: Transaction Type Validation (`transaction_types`)

| Aspect | Detail |
|--------|--------|
| **Schilling source** | 40 transaction types in `Roy.h` / `RoyTransTypeTekst[]` |
| **What it checks** | Every `TRANSTYPE` in the file is a recognized type from the known set |
| **Severity** | ERROR if unknown type; WARNING if deprecated type |

---

## 7. Expected Statement File Format

The validator must support the main export formats from Schilling. The parser auto-detects format.

### 7.1 CSV Format

The `RoySkyldListe` export from Schilling uses **semicolon-delimited CSV** with double-quote enclosure and Danish number formatting. Numeric values may appear as Excel formulas (`=12345/100`).

**Schilling native format (semicolon-delimited):**
```csv
"ArtNr";"ArtTxt";"Kontonr";"ForfNavn";"Dim1";"StkAfregnpris";"StkAfregnsats";"LinieBelqb";"LinieSkat";"LinieAfgift";"LinieMoms";"LinieAntal";"BilDato"
"978-87-1234-567-8";"Lunch";"654321";"Johannes B. Hreinsson";"";=1495000/100;=1200/100;=899700/100;=0/100;=0/100;=0/100;=500/1;"15-01-2026"
```

**Standardized CSV** (also accepted — comma-delimited, plain numbers):
```csv
TRANSNR,TRANSTYPE,KONTO,AFTALE,ARTNR,KANAL,PRISGRUPPE,VILKAR,BILAGSNR,BILAGSDATO,ANTAL,STKPRIS,STKAFREGNSATS,BELOEB,VALUTA,SKAT,AFREGNBATCH
10001,Salg,AUTH-0042,AFT-2024-001,978-87-1234-567-8,Boghandel,Standard,A,50001,2026-01-15,500,149.95,0.12,8997.00,DKK,0.00,1001
```

The parser auto-detects the format variant:

| Feature | Schilling native | Standardized |
|---------|-----------------|---------------|
| Delimiter | Semicolon (`;`) | Comma (`,`) |
| Quoting | Double-quote | Optional |
| Numbers | `=N/100` Excel formulas | Plain decimals |
| Decimal separator | Comma (`,`) | Period (`.`) |
| Thousands separator | Period (`.`) | None or comma |

### 7.2 Excel Format

Same columns as either CSV variant, in the first worksheet. Header row required. Numeric values are plain numbers (no `=N/100` formulas).

The parser also supports the `IndTrans` import format, where **column positions are configurable** per Schilling installation. To handle this, the parser matches columns by **header name**, not by position. If headers are missing but the number of columns matches a known layout, the parser prompts the user to confirm the column mapping.

### 7.3 PDF Format (Schilling "Royalty afregning" PDF)

The primary input format. Schilling generates settlement PDFs via Apache FOP (XSL-FO → PDF). The parser uses **pdfplumber** to extract structured data from these specific PDFs.

#### Real PDF Structure (from `10564_Royaltyafregning.pdf`)

Each PDF contains **one page per agreement** for a given recipient. Each page follows this layout:

```
┌─────────────────────────────────────────────────────────┐
│  Recipient Header          Publisher Header             │
│  C: Johannes B. Hreinsson  Schilling A/S                │
│  Baldersbækvej 24-26       Baldersbækvej 24-26          │
│  2635 Ishøj                DK-2635 Ishøj                │
│                            Tel 70 27 99 00              │
│                            CVR nr. 12345678             │
├─────────────────────────────────────────────────────────┤
│                   Royalty afregning                      │
├─────────────────────────────────────────────────────────┤
│  METADATA BLOCK (key-value pairs):                      │
│  Primo lager:        0 stk.    Titel: <book title>      │
│  Periodens tilgang:  0 stk.    Kontonr: 654321          │
│  Frieksemplarer:     0 stk.    Aftale: 9788701021968    │
│  Periodens svind:    0 stk.    Periode: 01.01.20-31.12.20│
│  Makulatur:          0 stk.    Afregning nr: 2          │
│  Ultimo lager:     792 stk.                             │
├─────────────────────────────────────────────────────────┤
│  SALES TABLE (if sales exist):                          │
│  Salgskanal  Prisgruppe   Sats     Antal solgte  Pris   Royalty │
│  Retail      Normal sale  50,000%  435           324,00  70.470,00│
│  Retail      Normal sale  50,000%  50            150,00   3.750,00│
│  Retail      Normal sale  50,000% -1.500         100,00 -75.000,00│
│                                                    -780,00│
├─────────────────────────────────────────────────────────┤
│  DEDUCTIONS / SUMMARY:                                  │
│  Royalty fordeling: 10,000% af -780,00          -78,00  │
│  Rest global garanti:                        -6.048,52  │
│  Afgift:                                                │
│  Til udbetaling:                             72.512,48  │
├─────────────────────────────────────────────────────────┤
│  Footer / Signature block                               │
└─────────────────────────────────────────────────────────┘
```

#### Extracted Data Fields per Page

| Section | Field | Example | Maps to |
|---------|-------|---------|---------|
| **Metadata** | Titel (Title) | "Silent regard of slow things" | Product name |
| **Metadata** | Kontonr (Account) | 654321 | Recipient account |
| **Metadata** | Aftale (Agreement) | 9788701021968 | Agreement number (often ISBN) |
| **Metadata** | Periode (Period) | 01.01.20-31.12.20 | Settlement period |
| **Metadata** | Afregning nr (Settlement #) | 2 | Settlement sequence number |
| **Metadata** | Primo lager | 0 stk. | Opening stock |
| **Metadata** | Ultimo lager | 792 stk. | Closing stock |
| **Metadata** | Frieksemplarer | 0 stk. | Free copies |
| **Metadata** | Periodens svind | 0 stk. | Period shrinkage |
| **Metadata** | Makulatur | 0 stk. | Pulped copies |
| **Sales line** | Salgskanal | Retail | Sales channel |
| **Sales line** | Prisgruppe | Normal sale | Price group |
| **Sales line** | Sats | 50,000% or 500,000 kr. | Royalty rate (% or fixed amount) |
| **Sales line** | Antal solgte | 435 | Quantity sold |
| **Sales line** | Prisgrundlag | 324,00 | Price basis (unit price) |
| **Sales line** | Royalty | 70.470,00 | Calculated royalty amount |
| **Summary** | Royalty total | -780,00 | Sum of sales line royalties |
| **Summary** | Royalty fordeling | 10,000% af -780,00 = -78,00 | Author's share of royalty |
| **Summary** | Overført til næste | -78,00 | Carried to next settlement |
| **Summary** | Rest global garanti | -6.048,52 | Remaining global guarantee |
| **Summary** | Afgift | (amount) | Duty/levy deduction |
| **Summary** | Til udbetaling | 72.512,48 | Net payout amount |

#### PDF Parsing Strategy

1. **Text extraction** via `pdfplumber.page.extract_text()` — the Schilling PDFs use embedded Helvetica fonts (not scanned images), so text extraction works reliably
2. **Page-by-page processing**: Each page = one agreement. Parse metadata block first, then detect sales table rows, then summary/deduction lines
3. **Regex-based field extraction** for the metadata block (key-value pairs like `Titel:`, `Kontonr:`, `Aftale:`, `Periode:`)
4. **Table detection** for the sales grid using `pdfplumber.page.extract_tables()` or positional text parsing between the column headers (`Salgskanal:`, `Prisgruppe:`, `Sats:`, etc.) and the summary section
5. **Danish number format handling**: Thousands separator = `.`, decimal separator = `,` (e.g., `70.470,00` = 70470.00). The parser must convert Danish number formats to floats
6. **Rate type detection**: Rates can be percentage (`50,000%`) or fixed amount per copy (`500,000 kr.`). The parser checks for `%` or `kr.` suffix
7. **Parse confidence score**: Each extracted page gets a confidence score (0–100%) based on how many expected fields were found. Pages below 80% trigger a WARNING

#### Known PDF Variants

| Variant | Characteristics | Parser Handling |
|---------|----------------|-----------------|
| **No sales** (Page 1 in sample) | Only metadata + "Til udbetaling: 0,00", no sales table | Valid — skip sales table extraction |
| **With sales** (Page 2, 3, 4) | Full metadata + sales table + summary | Standard parsing path |
| **With guarantee** (Page 4) | Summary includes "Rest global garanti" line | Extract as guarantee_balance field |
| **With duty/tax** (Page 4) | Summary includes "Afgift:" line | Extract as duty_amount field |
| **Last settlement note** (Page 3) | Contains "Bemærk! Dette er sidste afregning" | Flag as `is_final_settlement = true` |
| **Fixed-rate royalty** (Page 4) | Rate shown as "500,000 kr." instead of percentage | Parse as per-unit fixed amount |

### 7.4 JSON Format

```json
{
  "settlement_date": "2026-01-15",
  "batch_id": 1001,
  "rows": [
    {
      "transnr": 10001,
      "transtype": "Salg",
      "konto": "AUTH-0042",
      "aftale": "AFT-2024-001",
      "artnr": "978-87-1234-567-8",
      "kanal": "Boghandel",
      "prisgruppe": "Standard",
      "antal": 500,
      "stkpris": 149.95,
      "stkafregnsats": 0.12,
      "beloeb": 8997.00,
      "valuta": "DKK",
      "skat": 0.00
    }
  ]
}
```

---

## 8. Data Model (New App)

```mermaid
erDiagram
    USERS ||--o{ UPLOADS : "creates"
    UPLOADS ||--o{ VALIDATION_RUNS : "validated by"
    VALIDATION_RUNS ||--o{ VALIDATION_ISSUES : "produces"

    USERS {
        uuid id PK
        string nickname
        datetime created_at
    }

    UPLOADS {
        uuid id PK
        uuid user_id FK
        string filename
        string file_path
        string file_format "csv | xlsx | json | pdf"
        int row_count
        datetime uploaded_at
    }

    VALIDATION_RUNS {
        uuid id PK
        uuid upload_id FK
        string status "pending | running | completed | failed"
        int rules_executed
        int passed_count
        int warning_count
        int error_count
        datetime started_at
        datetime completed_at
    }

    VALIDATION_ISSUES {
        uuid id PK
        uuid validation_run_id FK
        string severity "error | warning | info"
        string rule_id
        string rule_description
        int row_number
        string field
        string expected_value
        string actual_value
        string message
        json context
    }
```

---

## 9. User Flow

```mermaid
flowchart TD
    A[User opens app in browser] --> B[Enter nickname / user ID]
    B --> C[Upload royalty statement file]
    C --> D{File uploaded?}
    D -->|No| C
    D -->|Yes| E[Backend parses file]
    E --> F{Parse OK?}
    F -->|No| G[Show parse errors]
    G --> C
    F -->|Yes| H[Show file summary: rows, columns, format]
    H --> I[User clicks 'Validate']
    I --> J[Backend runs all validation rules]
    J --> K[Results returned]
    K --> L[Show summary: ✓ passed, ⚠ warnings, ✗ errors]
    L --> M{User wants details?}
    M -->|Yes| N[Expand issue → see line number, field, expected vs actual]
    M -->|No| O[Done / Upload another file]

    style D fill:#fff3e0
    style F fill:#fff3e0
    style L fill:#e8f5e9
```

---

## 10. Implementation Plan

### Phase 1 — Foundation (Week 1–2)

| Task | Details |
|------|---------|
| **Project scaffolding** | Set up monorepo: `backend/` (FastAPI) + `frontend/` (React + Vite) + `docker-compose.yml` |
| **Backend: database + models** | PostgreSQL via docker-compose; SQLAlchemy models for Users, Uploads, ValidationRuns, ValidationIssues; Alembic migrations |
| **Backend: user identification** | `POST /api/auth/identify` — create or find by nickname, return user_id |
| **Backend: file upload** | `POST /api/uploads` — accept multipart file, store on disk, record in DB |
| **Frontend: login page** | Simple nickname entry form → stores user_id in state/localStorage |
| **Frontend: upload page** | `FileDropzone` component with drag-and-drop + file picker |
| **Docker setup** | Dockerfiles for backend + frontend + PostgreSQL; docker-compose with shared network, persistent volume for DB |

### Phase 2 — Parser + First Rules (Week 3–4)

| Task | Details |
|------|---------|
| **PDF parser** | Schilling "Royalty afregning" PDF parser: page-by-page metadata extraction, sales table parsing, Danish number format conversion, rate type detection (% vs. kr.) |
| **Other parsers** | CSV (semicolon-delimited with `=N/100` formula support), Excel, JSON — normalize to common `list[dict]` structure |
| **Validation engine** | `Engine.run(rules, data)` → collects `ValidationIssue` from each rule |
| **Rule: missing_titles** | Check `artnr` column; optional ISBN checksum validation |
| **Rule: invalid_rates** | Check `stkafregnsats` > 0 and within bounds |
| **Rule: amount_consistency** | `antal × stkpris × stkafregnsats ≈ beloeb` |
| **Rule: transaction_types** | Validate against known `RoyTransTypeTekst` set |
| **API: trigger + retrieve** | `POST /api/validations/{upload_id}/run` + `GET /api/validations/{id}` |
| **Tests** | pytest for each rule with fixture files |

### Phase 3 — Advanced Rules (Week 5–6)

| Task | Details |
|------|---------|
| **Rule: tax_validation** | Tax amount vs. gross × rate |
| **Rule: guarantee_offsets** | Paired guarantee/offset matching |
| **Rule: settlement_totals** | Net payout = sales − returns − guarantees − advances − tax |
| **Rule: date_validation** | Voucher date vs. settlement date checks |
| **Rule: advance_balance** | Offset ≤ advance per agreement |
| **Rule: recipient_shares** | Share percentages sum ≤ 100% |
| **Rule: duplicate_entries** | Detect duplicate key tuples |
| **Tests** | Full rule coverage with edge cases |

### Phase 4 — Frontend Results + Polish (Week 7–8)

| Task | Details |
|------|---------|
| **Results page** | Summary cards (pass/warn/error counts) + sortable/filterable issue table |
| **Detail view** | Expandable rows with: line number, field, expected vs. actual, context (agreement, product, recipient) |
| **Export** | Download validation report as CSV or PDF |
| **Error handling** | Graceful error states for: unparseable files, server errors, empty files |
| **Responsive design** | Works on desktop + tablet |
| **E2E tests** | Playwright tests covering full upload → validate → review flow |

### Phase 5 — Hardening + Deployment (Week 9–10)

| Task | Details |
|------|---------|
| **Security** | File upload size limits, allowed file types only, input sanitization, CORS config |
| **Performance** | Async validation for large files; progress indicator |
| **Logging** | Structured logging (JSON) for all API calls and validation runs |
| **Documentation** | API docs (auto-generated by FastAPI), user guide, developer README |
| **CI/CD** | GitHub Actions: lint + test + build + docker push |
| **Deploy** | Docker Compose or Kubernetes manifest for production |

---

## 11. Validation Rule → Schilling Source Mapping

This table provides the complete traceability from each new validation rule back to the original Schilling ERP source code and business rules.

| New Rule | Schilling Source File | Schilling Function / Constant | Business Rule |
|----------|----------------------|-------------------------------|---------------|
| `missing_titles` | `Royalty/Batch/IndTrans/IndTrans.cpp` | `OpretRoypost()` requires `ARTNR` | Every royalty post must have a product |
| `invalid_rates` | `Royalty/Lib/Roy.h`, `Royalty/Objects/RoySharesLadder/` | `STKAFREGNSATS` in `ROYAFTALEKANALPRIS` | Rate must be defined in agreement terms |
| `amount_consistency` | `Royalty/Lib/Gem.cpp`, `Royalty/Lib/Afregn.cpp` | `SalgArray` — qty × price × rate | Core calculation in settlement engine |
| `tax_validation` | `Royalty/Objects/TaxCalculation/TaxCalculation.hpp` | `GetTaxAmount()`, `GetResult()` | Tax = gross × configured rate |
| `guarantee_validation` | `Royalty/Lib/Afregn.cpp` | `RoySkrivGaranti()` → guarantee balance check | Guarantee deductions must balance with payout |
| `settlement_totals` | `Royalty/Lib/GenUdskriv.cpp` | Sum pages in `PaymentVoucherReport` | Statement must balance |
| `duplicate_entries` | `Royalty/Trans/KompRoypost/KompRoypost.cpp` | Compression key uniqueness | No unintended duplicate postings |
| `date_validation` | `Royalty/Objects/SettlementRun/SettlementCriteria.cpp` | `ValidateSettlementDateFrom()`, `FORF_AC_AFRDAT` | Dates must be within valid settlement period |
| `advance_balance` | `Royalty/Lib/Afregn.cpp` | `ROYFORSKUD` / `ROYFORSKUDMOD` | Cannot recoup more than advanced |
| `recipient_shares` | `Royalty/Lib/Arv.cpp` | `ROYMEDFORFATTER` shares, `RIG_AUTSHA_TH` | Shares must not exceed 100% |
| `transaction_types` | `Royalty/Lib/Roy.h` | `RoyTransTypeTekst[]` (40 types) | Only known transaction types are valid |

---

## 12. Sample Test Scenarios

### Happy Path — PDF
1. Upload the sample `10564_Royaltyafregning.pdf` (4 pages, 4 agreements)
2. All amounts consistent, rates valid, totals balance
3. → 0 errors, 0 warnings, 11 passed checks

### Happy Path — CSV
1. Upload a correctly formatted semicolon-delimited CSV with 100 rows
2. All rates present, amounts consistent, dates valid
3. → 0 errors, 0 warnings, 11 passed checks

### Missing Title in PDF
1. Upload PDF where page 1 has missing `Titel:` field
2. → 1 error: `missing_titles` on page 1, "Title field is empty"

### Calculation Mismatch in PDF
1. Upload PDF where page 2 has sales line: `Retail, Normal sale, 50,000%, 435, 324,00, 50.000,00`
2. Expected: `435 × 324.00 × 0.50 = 70,470.00` but actual is `50,000.00`
3. → 1 error: `amount_consistency` on page 2, line 3, expected 70470.00, actual 50000.00

### Settlement Total Mismatch in PDF
1. Upload PDF where page 4 shows sales royalty total = 500.000,00, royalty fordeling = 25% of 500.000 = 125.000,00, rest garanti = -6.048,52, but "Til udbetaling" = 200.000,00 (doesn't balance)
2. → 1 error: `settlement_totals` on page 4, "Payout 200000.00 ≠ expected 118951.48 (125000.00 − 6048.52)"

### Fixed-Rate Royalty Validation
1. Upload PDF where page 4 has rate `500,000 kr.` with 1000 copies
2. Parser detects fixed-rate, validates: `1000 × 500.00 = 500,000.00` ✓
3. → 0 errors

### Missing Titles in CSV
1. Upload CSV where rows 15, 42 have blank `ARTNR`
2. → 2 errors: `missing_titles` at rows 15 and 42

### Incorrect Rate
1. Upload CSV where row 30 has `STKAFREGNSATS = -0.05`
2. → 1 error: `invalid_rates` at row 30, "Rate is negative"

### Calculation Mismatch
1. Upload CSV where row 8 has `500 × 149.95 × 0.12 = 8997.00` but `BELOEB = 9500.00`
2. → 1 error: `amount_consistency` at row 8, expected 8997.00, actual 9500.00, diff 503.00

### Unmatched Guarantee Offset
1. Upload CSV with `GarGlobal` at row 20 (5000.00) but no corresponding `GarGlobalMod`
2. → 1 error: `guarantee_offsets` at row 20, "No matching offset for global guarantee"

### Over-Recouped Advance
1. Upload CSV with advance of 10000.00 and offsets totaling 12000.00
2. → 1 error: `advance_balance`, "Advance offset (12000.00) exceeds original advance (10000.00)"

---

## 13. Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://validator:validator@localhost:5432/validator` | PostgreSQL connection string |
| `UPLOAD_DIR` | `./uploads` | Directory for stored files |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum file upload size |
| `ALLOWED_EXTENSIONS` | `csv,xlsx,json,pdf` | Accepted file types |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `AMOUNT_TOLERANCE` | `0.01` | Rounding tolerance for amount checks (from Schilling `KompRoypost`) |
| `MAX_RATE_THRESHOLD` | `0.50` | Rates above this trigger a warning |

### Reference Data (Optional Enhancement)

For more advanced validation, the app can load:
- **Known product list** (ISBNs) — CSV upload or API endpoint, to validate `ARTNR` against actual catalogue
- **Agreement terms** — export from Schilling `ROYAFTALEKANALPRIS`, to validate rates match contract
- **Recipient list** — export from `ROYFORFATTER`, to verify recipient codes exist

This is optional for v1 but enables much richer validation in v2.

---

## 14. Future Enhancements (v2+)

| Enhancement | Description |
|-------------|-------------|
| **Reference data upload** | Upload agreement/product/recipient master data for cross-referencing |
| **Historical comparison** | Compare current statement against previous period's statement |
| **Schilling DB connector** | Optional direct read from Oracle for live validation against master data |
| **Batch processing** | Upload multiple statements at once, validate in parallel |
| **Email notifications** | Send validation summary to stakeholders |
| **Role-based access** | Admin can manage reference data; users can only upload and validate |
| **Audit trail** | Full history of who uploaded what and which issues were found |
| **Custom rules** | UI for defining additional validation rules without code changes |
| **Settlement simulation** | Re-calculate royalty from raw data (mini settlement engine in Python) |

---

## 15. Getting Started (Dev Setup)

```bash
# Clone the repo
git clone <repo-url>
cd royaltyStatementValidator

# Start everything with Docker (includes PostgreSQL)
docker-compose up --build

# Backend: http://localhost:8000 (API docs at /docs)
# Frontend: http://localhost:5173
# PostgreSQL: localhost:5432 (user: validator, password: validator, db: validator)
```

### docker-compose.yml (key services)

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: validator
      POSTGRES_PASSWORD: validator
      POSTGRES_DB: validator
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://validator:validator@db:5432/validator
    depends_on:
      - db
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"

volumes:
  pgdata:
```

### Without Docker

```bash
# Prerequisites: PostgreSQL 16 running locally
# Create database:
# psql -U postgres -c "CREATE USER validator WITH PASSWORD 'validator';"
# psql -U postgres -c "CREATE DATABASE validator OWNER validator;"

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head           # Run database migrations
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## 16. Key Decisions

| Decision | Rationale |
|----------|-----------|
| **FastAPI over Flask/Django** | Async support, automatic OpenAPI docs, Pydantic validation — best fit for a REST API with file processing |
| **PostgreSQL from day one** | Production-grade; supports concurrent access, JSON columns, full-text search; runs in Docker for local dev with zero friction |
| **Plugin-based rules** | Each rule is a separate class/file — easy to add, test, enable/disable without touching the engine |
| **0.01 tolerance** | Matches the Schilling `KompRoypost` compression tolerance — proven in production |
| **File-based storage** | Statement files stored on disk with UUID filenames — simple, auditable, no binary DB blobs |
| **No auth system for v1** | Nickname-based identification — sufficient for an internal tool; add proper auth in v2 if needed |
| **Danish field names preserved** | Using `BELOEB`, `ANTAL`, `STKPRIS`, etc. in the file format — matches Schilling exports and avoids translation errors |
| **PDF as primary input** | The Schilling "Royalty afregning" PDF is the most common file users will upload — the parser is purpose-built for this specific format, not a generic PDF table extractor |

---

## 17. Known Limitations & Blind Spots

This section documents the gaps between what the validator can check with an uploaded file alone vs. what the full Schilling ERP settlement engine checks with access to the Oracle database. These are not bugs — they are inherent to a file-based validation approach.

### 17.1 Critical Limitations

#### Amount Consistency and Staircase Rates

The `amount_consistency` rule uses the simple formula `quantity × price × rate = royalty`. In Schilling, the actual calculation involves:

| Factor | Schilling Source | Impact on Validation |
|--------|-----------------|---------------------|
| **Staircase/ladder rates** (`RoySharesLadder`) | Different rates for different quantity tiers, blended via `RoyFordelSalgMgd()` | Amount will NOT match simple formula for large runs crossing tier boundaries |
| **Depreciation** | `LoadDepreciationPerCent()` reduces rates over time | Older editions will have lower effective rates |
| **Minimum royalty floors** | `MINROYALTY` in `ROYAFTALEKANALPRIS` | Amount may be higher than formula predicts |
| **FIFO/LIFO return matching** | Returns matched against specific sales at their original rate | Return amounts may not match current rate |
| **Currency conversion** | Multi-currency with exchange rates in `Gem.cpp` | Converted amounts include FX rounding |
| **Binding deduction** | `BindingDeductionRate` on agreement | Reduces base amount before rate application |

**Mitigation**: When a line fails the simple formula, the validator emits an INFO (not ERROR) with the message "Amount may use staircase rates, depreciation, or other adjustments — verify manually."

#### Tax Validation Without Reference Data

Full tax validation is **not possible** in v1 without knowing each recipient's configured tax code, rate, and exemptions. The Schilling `TaxCalculation` object uses multi-level intermediate calculations (`GenerateIntermediateCalculations()`) with per-recipient configuration.

**v1 capability**: Structural checks only (duty line present and non-zero, amounts are negative deductions).
**v2 with reference data**: Full rate-based validation.

#### Cross-Settlement References

Several business rules span multiple settlement periods:

| Scenario | Why It's a Problem |
|----------|-------------------|
| **Global guarantees** | Posted in period 1, offset in period 5 — single file shows only one side |
| **Advance recoupment** | Advances recoup across many settlements — cannot verify total without history |
| **Settlement sequence** | `ROY_AFREGNESFORAFREGNET` requires knowing the previous settlement date |

**Mitigation**: Rules only validate within-file consistency. Cross-file checks are flagged as INFO ("Reference not found in this file — may exist in prior settlements").

### 17.2 Moderate Limitations

#### No Multi-Currency Validation

The Schilling system handles DKK, EUR, NOK, SEK with exchange rate conversions. The validator does not check:
- Currency consistency within a settlement
- Exchange rate reasonableness
- Mismatched currency between amount and rate

**Planned for v2** with reference data support.

#### No Settlement Batch Consistency Check

All rows in a single settlement should share the same `AFREGNBATCH`. For CSV/Excel uploads, there is no rule to verify the file represents a coherent batch vs. a mix of unrelated settlements. For PDFs, this is naturally enforced (the PDF is one settlement run).

#### Compressed vs. Uncompressed Data

The `KompRoypost` compression merges ROYPOST rows into summaries. If a CSV/Excel file contains compressed data, the `duplicate_entries` rule may not apply correctly, and `amount_consistency` may fail on aggregated amounts.

#### Configurable CSV Column Layout

The `IndTrans` CSV import in Schilling uses column positions from a `.layout` file stored in the FGOPL database — **there is no fixed column order**. The parser mitigates this by matching on column header names, not positions. If headers are missing, the user must confirm the mapping.

### 17.3 PDF-Specific Limitations

| Limitation | Detail |
|-----------|--------|
| **pdfplumber extracts text without spaces** | The Schilling PDF uses tight character spacing — `pdfplumber` may merge words (e.g., `SchillingA/S` instead of `Schilling A/S`). The parser applies heuristic space-insertion |
| **Danish encoding** | Characters like `æ`, `ø`, `å` are present in the PDF. `pdfplumber` handles these via WinAnsiEncoding (confirmed in the sample PDF's font definitions) |
| **Non-standard PDFs** | If a customer's Schilling installation uses a customized XSL-FO template (`SettlementForm` systab override), the page layout may differ. The parser is built for the standard `XSLRoyAfr3`/`XSLRoyAfr4` templates |
| **Scanned PDFs** | PDFs generated by Schilling use embedded fonts (Helvetica), so text extraction works. Scanned/photocopied PDFs are NOT supported in v1 |

### 17.4 Validation Coverage Matrix

Which rules work with which file formats:

| Rule | PDF | CSV (native) | CSV (standard) | Excel | JSON |
|------|-----|-------------|----------------|-------|------|
| `missing_titles` | ✓ (Titel field) | ✓ (ArtNr column) | ✓ | ✓ | ✓ |
| `invalid_rates` | ✓ (Sats column) | ✓ (StkAfregnsats) | ✓ | ✓ | ✓ |
| `amount_consistency` | ✓ (per sales line) | ✓ | ✓ | ✓ | ✓ |
| `tax_validation` | ✓ (Afgift line) | ✓ | ✓ | ✓ | ✓ |
| `guarantee_validation` | ✓ (Rest garanti line) | Partial (needs pairing) | Partial | Partial | Partial |
| `settlement_totals` | ✓ (full chain) | ✓ | ✓ | ✓ | ✓ |
| `duplicate_entries` | N/A (1 per page) | ✓ | ✓ | ✓ | ✓ |
| `date_validation` | ✓ (Periode field) | ✓ | ✓ | ✓ | ✓ |
| `advance_balance` | Partial (if shown) | ✓ (needs pairing) | ✓ | ✓ | ✓ |
| `recipient_shares` | ✓ (fordeling %) | N/A (single rows) | N/A | N/A | N/A |
| `transaction_types` | N/A (no type codes) | ✓ | ✓ | ✓ | ✓ |
