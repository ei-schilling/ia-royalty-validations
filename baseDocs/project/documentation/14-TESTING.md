# 14 — Testing

## Overview

The backend test suite contains **136 tests** covering API endpoints, authentication flows, file parsing, and all 11 validation rules.

Tests use **in-memory SQLite** (via `aiosqlite`) — no running database or Docker required.

---

## Test Structure

```
backend/tests/
├── conftest.py           # Shared fixtures (app, client, DB, auth helpers)
├── test_api.py           # API endpoint tests (22 tests)
├── test_e2e_auth.py      # End-to-end auth flow tests (25 tests)
├── test_parser.py        # File parsing tests (21 tests)
├── test_rules.py         # Validation rule tests (68 tests)
└── fixtures/             # Sample statement files
    ├── valid_statement.csv
    ├── schilling_native.csv
    ├── missing_titles.csv
    ├── bad_rates.csv
    ├── calculation_errors.csv
    ├── duplicate_rows.csv
    ├── mixed_issues.csv
    ├── advances_guarantees.csv
    ├── valid_statement.json
    └── ...
```

---

## Running Tests

### Prerequisites

```bash
cd royalties/backend
python -m venv .venv

# Windows:
.venv\Scripts\Activate.ps1

# Linux/Mac:
source .venv/bin/activate

pip install -e ".[dev]"
```

### Run All Tests

```bash
python -m pytest tests/ -v
```

### Run with Coverage

```bash
python -m pytest tests/ --cov=app --cov-report=term-missing
```

### Run Specific Test File

```bash
python -m pytest tests/test_rules.py -v
python -m pytest tests/test_api.py -v
python -m pytest tests/test_parser.py -v
python -m pytest tests/test_e2e_auth.py -v
```

### Run Specific Test

```bash
python -m pytest tests/test_rules.py::test_missing_titles_valid -v
```

### Run by Marker

```bash
python -m pytest tests/ -m e2e -v
```

### Using the Test Runner Script

```bash
python run_tests.py
```

This script runs the full suite and generates a report in `test_results.txt`.

---

## Test Categories

### API Tests (`test_api.py`) — 22 tests

Tests HTTP endpoints, request validation, and response shapes.

| Test Area | What's Tested |
|-----------|---------------|
| Health check | `GET /health` returns 200 |
| File upload | Upload CSV, XLSX, JSON, PDF files |
| Upload validation | Reject oversized files, unsupported types |
| Validation run | Trigger and retrieve validation results |
| Issue pagination | `GET /issues` with page, size, severity filters |
| PDF download | `GET /pdf` returns PDF binary |
| Error handling | 404 for missing resources, 422 for bad input |
| Auth protection | Protected endpoints reject unauthenticated requests |

### Auth E2E Tests (`test_e2e_auth.py`) — 25 tests

Full end-to-end authentication flow testing.

| Test Area | What's Tested |
|-----------|---------------|
| Registration | Create account, receive JWT, duplicate nickname rejection |
| Login | Valid login, wrong password, non-existent user |
| Token validation | `GET /me` with valid/expired/malformed tokens |
| Full flow | Register → upload → validate → view results |
| Multi-user isolation | User A cannot see User B's uploads |
| Token expiry | Expired tokens are rejected |
| Password validation | Short passwords, empty passwords |
| Nickname validation | Short nicknames, empty nicknames |

### Parser Tests (`test_parser.py`) — 21 tests

Tests file parsing for all supported formats.

| Test Area | What's Tested |
|-----------|---------------|
| CSV parsing | Standard CSV, semicolon-delimited, formula resolution |
| Excel parsing | .xlsx files with headers |
| JSON parsing | Flat array and wrapped object formats |
| PDF parsing | Schilling PDF metadata, sales lines, summary rows |
| Column normalization | Lowercase, whitespace stripping |
| Danish numbers | `70.470,00` → `70470.00` conversion |
| Edge cases | Empty files, single row, Unicode content |
| Row numbering | `_row_number` is correctly assigned |

### Rule Tests (`test_rules.py`) — 68 tests

Tests each validation rule with both valid and invalid data.

| Rule | Tests | What's Tested |
|------|-------|---------------|
| `missing_titles` | 8 | Valid titles, missing artnr, missing titel, ISBN-13 checksum |
| `invalid_rates` | 7 | Valid rates, zero rates, negative rates, exceeding threshold |
| `amount_consistency` | 8 | Matching amounts, rounding tolerance, large differences |
| `tax_validation` | 5 | Valid afgift, positive afgift (unusual), non-numeric |
| `guarantee_validation` | 6 | Valid guarantees, positive deduction, negative payout |
| `settlement_totals` | 6 | Valid chain, broken fordeling, broken payout |
| `duplicate_entries` | 5 | No duplicates, exact duplicates, near-duplicates |
| `date_validation` | 8 | Valid dates, unparseable, out-of-range, period inversion |
| `advance_balance` | 5 | Valid advances, offset exceeding advance |
| `recipient_shares` | 5 | Valid shares, exceeding 100%, partial shares |
| `transaction_types` | 5 | Known types, unknown types, deprecated types |

---

## Test Fixtures

### Database Fixture

Tests use in-memory SQLite with auto-created tables:

```python
@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        yield session
```

### HTTP Client Fixture

Uses `httpx.AsyncClient` with the FastAPI `TestClient`:

```python
@pytest.fixture
async def client(app):
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
```

### Auth Helper

Utility to register a user and get a JWT for authenticated tests:

```python
async def get_auth_token(client, nickname="testuser", password="testpass"):
    resp = await client.post("/api/auth/register", json={
        "nickname": nickname,
        "password": password
    })
    return resp.json()["access_token"]
```

### Sample Files

Located in `tests/fixtures/`. Each file is a minimal royalty statement designed to trigger specific rules:

| Fixture | Purpose |
|---------|---------|
| `valid_statement.csv` | All checks pass — no issues expected |
| `schilling_native.csv` | Real Schilling export format with semicolons and formulas |
| `missing_titles.csv` | Rows with blank artnr and titel fields |
| `bad_rates.csv` | Zero, negative, and excessive royalty rates |
| `calculation_errors.csv` | Amount mismatches between calculated and reported values |
| `duplicate_rows.csv` | Intentional duplicate key tuples |
| `mixed_issues.csv` | Multiple issue types in one file |
| `advances_guarantees.csv` | Advance and guarantee scenarios |
| `valid_statement.json` | Valid data in JSON format |

---

## Testing Best Practices

### Do

- Test both valid and invalid inputs for each rule
- Test edge cases: empty files, single rows, Unicode
- Use the in-memory SQLite fixture for fast tests
- Test API error responses (400, 401, 404, 422)
- Use descriptive test names: `test_missing_titles_isbn_checksum_valid`

### Don't

- Don't require Docker or a running database for tests
- Don't test implementation details — test behavior
- Don't share state between tests (each test gets a fresh DB)
- Don't skip auth tests — they're critical for security

---

## Dev Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-asyncio` | Async test support |
| `pytest-cov` | Coverage reports |
| `httpx` | Async HTTP client for API tests |
| `aiosqlite` | In-memory SQLite for async tests |
| `ruff` | Linter (not test-specific but used in CI) |
