# Royalty Statement Validator

A standalone web application that validates royalty statement files against business rules from the **Schilling ERP** royalty settlement system. It catches inconsistencies — missing titles, incorrect rates, calculation mismatches, duplicate entries — **before** statements are processed or shared with authors. This is **not** a settlement engine; it works on exported files only.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Services & URLs](#services--urls)
- [API Reference](#api-reference)
- [Authentication](#authentication)
- [Validation Engine](#validation-engine)
- [Supported File Formats](#supported-file-formats)
- [Database Schema](#database-schema)
- [Frontend](#frontend)
- [Testing](#testing)
- [Configuration](#configuration)
- [Project Structure](#project-structure)

---

## Architecture Overview

```mermaid
graph TB
    subgraph Client
        Browser["Browser (React SPA)"]
    end

    subgraph Docker["Docker Compose"]
        subgraph FE["Frontend Container :80"]
            Nginx["Nginx<br/>SPA + Reverse Proxy"]
        end

        subgraph BE["Backend Container :8000"]
            FastAPI["FastAPI App"]
            Auth["Auth Module<br/>JWT + bcrypt"]
            Parser["Multi-Format Parser<br/>CSV · Excel · JSON · PDF"]
            Engine["Validation Engine<br/>11 Rules"]
        end

        subgraph DB["Database Container :5432"]
            Postgres["PostgreSQL 16"]
        end
    end

    Browser -->|HTTP :80| Nginx
    Nginx -->|/api/* proxy| FastAPI
    Nginx -->|static assets| Browser
    FastAPI --> Auth
    FastAPI --> Parser
    FastAPI --> Engine
    FastAPI -->|SQLAlchemy async| Postgres
```

### Request Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (React)
    participant Nginx
    participant API as FastAPI Backend
    participant DB as PostgreSQL

    User->>FE: Register / Login
    FE->>Nginx: POST /api/auth/register
    Nginx->>API: Proxy request
    API->>DB: Create user (bcrypt hash)
    DB-->>API: User record
    API-->>FE: JWT token + user

    User->>FE: Upload file
    FE->>Nginx: POST /api/uploads/ (multipart + Bearer)
    Nginx->>API: Proxy request
    API->>API: Validate extension & size
    API->>API: Parse file → count rows
    API->>DB: Save Upload record
    API-->>FE: UploadResponse

    User->>FE: View results (auto-triggered)
    FE->>Nginx: POST /api/validations/{id}/run (Bearer)
    Nginx->>API: Proxy request
    API->>API: Parse file → run 11 rules
    API->>DB: Save ValidationRun + Issues
    API-->>FE: ValidationRunResponse

    FE->>FE: Render summary + issue list
```

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **Backend** | Python + FastAPI | 3.12+ / ≥ 0.115 |
| **ORM** | SQLAlchemy (async) | ≥ 2.0.36 |
| **Database** | PostgreSQL | 16-alpine |
| **Auth** | JWT via python-jose + bcrypt | HS256 |
| **File Parsing** | pandas, openpyxl, pdfplumber | — |
| **Frontend** | React + TypeScript | React 19, Vite 8 |
| **UI** | Tailwind CSS + shadcn/ui (Radix) | Tailwind 3.4 |
| **State** | TanStack React Query | ≥ 5.90 |
| **Containerization** | Docker + docker-compose | Multi-stage builds |

---

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- Git

### 1. Clone the repository

```bash
git clone <repo-url>
cd royaltyStatementValidator
```

### 2. Start all services

```bash
cd royalties
docker compose up --build -d
```

This builds and starts three containers: PostgreSQL, the FastAPI backend, and the Nginx-served frontend.

### 3. Verify

```bash
docker compose ps
```

All three containers should show `Up` status. Open your browser:

| Service | URL |
|---|---|
| **Application** | http://localhost |
| **API** | http://localhost:8000 |
| **Swagger UI** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |
| **Health Check** | http://localhost:8000/health |

### 4. Stop services

```bash
docker compose down       # Stop containers, keep data
docker compose down -v    # Stop containers, delete volumes (reset DB)
```

### Local Development (without Docker)

<details>
<summary>Backend</summary>

```bash
cd royalties/backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -e ".[dev]"

# Set env vars for SQLite (dev mode)
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"

python -m uvicorn app.main:app --reload --port 8000
```

</details>

<details>
<summary>Frontend</summary>

```bash
cd royalties/frontend
npm install
npm run dev    # Starts Vite dev server on http://localhost:5173
```

</details>

---

## Services & URLs

```mermaid
graph LR
    subgraph Exposed["Exposed Ports"]
        P80[":80 — Frontend"]
        P8000[":8000 — Backend API"]
        P5432[":5432 — PostgreSQL"]
    end

    subgraph URLs["Available URLs"]
        A["http://localhost → Web App"]
        B["http://localhost:8000/docs → Swagger UI"]
        C["http://localhost:8000/redoc → ReDoc"]
        D["http://localhost:8000/health → Health Check"]
    end

    P80 --> A
    P8000 --> B
    P8000 --> C
    P8000 --> D
```

| Service | Container | Port | URL | Description |
|---|---|---|---|---|
| **Frontend** | `royalties-frontend-1` | 80 | http://localhost | React SPA served by Nginx |
| **Backend API** | `royalties-backend-1` | 8000 | http://localhost:8000 | FastAPI REST API |
| **Swagger UI** | — | 8000 | http://localhost:8000/docs | Interactive API documentation |
| **ReDoc** | — | 8000 | http://localhost:8000/redoc | Alternative API documentation |
| **Health Check** | — | 8000 | http://localhost:8000/health | Returns `{"status": "ok"}` |
| **PostgreSQL** | `royalties-db-1` | 5432 | `postgresql://validator:validator@localhost:5432/validator` | Database |

---

## API Reference

### Auth — `/api/auth`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | — | Create a new account |
| `POST` | `/api/auth/login` | — | Login, receive JWT |
| `GET` | `/api/auth/me` | Bearer | Get current user |

### Uploads — `/api/uploads`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/uploads/` | Bearer | Upload a royalty statement file |
| `GET` | `/api/uploads/{upload_id}` | Bearer | Get upload details |

### Validations — `/api/validations`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/validations/{upload_id}/run` | Bearer | Run validation on an upload |
| `GET` | `/api/validations/{validation_id}` | Bearer | Get full validation results |
| `GET` | `/api/validations/{validation_id}/issues` | Bearer | Paginated issues (filter by severity) |

### Health

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Service health check |

> Full interactive documentation available at http://localhost:8000/docs

---

## Authentication

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant DB as PostgreSQL

    Note over Client,DB: Registration
    Client->>API: POST /api/auth/register {nickname, password}
    API->>API: bcrypt.hash(password)
    API->>DB: INSERT user (nickname, password_hash)
    API->>API: Create JWT (user_id, exp=8h)
    API-->>Client: {access_token, token_type, user}

    Note over Client,DB: Login
    Client->>API: POST /api/auth/login {nickname, password}
    API->>DB: SELECT user WHERE nickname
    API->>API: bcrypt.verify(password, hash)
    API->>API: Create JWT (user_id, exp=8h)
    API-->>Client: {access_token, token_type, user}

    Note over Client,DB: Authenticated Request
    Client->>API: GET /api/uploads/ [Authorization: Bearer <token>]
    API->>API: Decode JWT → extract user_id
    API->>DB: SELECT user WHERE id = user_id
    API-->>Client: Response data
```

- **Algorithm**: HS256
- **Token lifetime**: 8 hours (configurable)
- **Password hashing**: bcrypt
- **Token storage**: `localStorage` (frontend)
- **Public endpoints**: `/health`, `/api/auth/register`, `/api/auth/login`
- **Protected endpoints**: All others (require `Authorization: Bearer <token>` header)

---

## Validation Engine

The engine follows a plugin architecture. Each rule implements a `validate()` method that receives parsed statement data and returns a list of issues.

```mermaid
graph TD
    File["Uploaded File"] --> Parser["Multi-Format Parser"]
    Parser --> Data["Normalized Row Data<br/>list of dict"]
    Data --> Engine["Validation Engine"]

    Engine --> R1["missing_titles"]
    Engine --> R2["invalid_rates"]
    Engine --> R3["amount_consistency"]
    Engine --> R4["tax_validation"]
    Engine --> R5["guarantee_validation"]
    Engine --> R6["settlement_totals"]
    Engine --> R7["duplicate_entries"]
    Engine --> R8["date_validation"]
    Engine --> R9["advance_balance"]
    Engine --> R10["recipient_shares"]
    Engine --> R11["transaction_types"]

    R1 --> Issues["Aggregated Issues"]
    R2 --> Issues
    R3 --> Issues
    R4 --> Issues
    R5 --> Issues
    R6 --> Issues
    R7 --> Issues
    R8 --> Issues
    R9 --> Issues
    R10 --> Issues
    R11 --> Issues

    Issues --> DB["Persist to DB"]
    Issues --> Response["API Response"]
```

### 11 Validation Rules

| # | Rule ID | Description | Severity |
|---|---|---|---|
| 1 | `missing_titles` | Every row must have a product identifier (Artnr or Titel). Validates ISBN-13 checksums. | ERROR / WARNING |
| 2 | `invalid_rates` | Royalty rate must be present, numeric, non-negative, non-zero, and ≤ 50%. | ERROR / WARNING |
| 3 | `amount_consistency` | Calculated amount (`qty × price × rate`) must match reported amount within tolerance. | WARNING / INFO |
| 4 | `tax_validation` | Tax/duty (Afgift) values must be numeric and non-positive (deductions ≤ 0). | WARNING |
| 5 | `guarantee_validation` | Guarantee deductions must be negative; payout must not go negative after deduction. | ERROR / WARNING |
| 6 | `settlement_totals` | Chain integrity: sales → base → fordeling → deductions → payout. | ERROR |
| 7 | `duplicate_entries` | Detects duplicate rows sharing the same key tuple (aftale, artnr, kanal, etc.). | WARNING |
| 8 | `date_validation` | Period start ≤ end. Voucher dates are parseable and within range (2000–2100). | ERROR / WARNING |
| 9 | `advance_balance` | Advance offsets must not exceed original advance amounts per agreement. | ERROR |
| 10 | `recipient_shares` | Co-author fordeling percentages must sum to ≤ 100% per agreement. | ERROR / WARNING |
| 11 | `transaction_types` | Every transaction type must be from the 40 known Schilling types. Flags deprecated types. | ERROR / WARNING |

### Severity Levels

| Level | Meaning |
|---|---|
| **ERROR** | Data integrity violation — must be corrected before processing |
| **WARNING** | Potential issue — review recommended |
| **INFO** | Informational — may be expected behavior (e.g., staircase rates) |

---

## Supported File Formats

```mermaid
graph LR
    CSV["📄 CSV"] --> Parser
    Excel["📊 Excel (.xlsx)"] --> Parser
    JSON["📋 JSON"] --> Parser
    PDF["📕 PDF"] --> Parser

    Parser["Multi-Format<br/>Parser"] --> Normalized["Normalized Data<br/>list[dict]"]

    style CSV fill:#22c55e,color:#fff
    style Excel fill:#3b82f6,color:#fff
    style JSON fill:#f59e0b,color:#fff
    style PDF fill:#ef4444,color:#fff
```

| Format | Extension | Parser Details |
|---|---|---|
| **CSV** | `.csv` | Auto-detects delimiter (`;` vs `,`). Handles Schilling `=N/100` formulas. Normalizes column names. |
| **Excel** | `.xlsx` | Uses openpyxl read-only mode. First worksheet, first row as headers. |
| **JSON** | `.json` | Supports flat `[{...}]` or nested `{"rows": [{...}]}` format. |
| **PDF** | `.pdf` | Schilling "Royalty afregning" specific. Extracts metadata, sales table lines, and summary/deduction values per page. Converts Danish number format (`70.470,00` → `70470.00`). |

**Max upload size**: 50 MB (configurable)

---

## Database Schema

```mermaid
erDiagram
    users ||--o{ uploads : "has many"
    uploads ||--o{ validation_runs : "has many"
    validation_runs ||--o{ validation_issues : "has many"

    users {
        UUID id PK
        String nickname UK
        String password_hash
        DateTime created_at
    }

    uploads {
        UUID id PK
        UUID user_id FK
        String filename
        String file_path
        String file_format
        Integer row_count
        DateTime uploaded_at
    }

    validation_runs {
        UUID id PK
        UUID upload_id FK
        String status
        Integer rules_executed
        Integer passed_count
        Integer warning_count
        Integer error_count
        Integer info_count
        DateTime started_at
        DateTime completed_at
    }

    validation_issues {
        UUID id PK
        UUID validation_run_id FK
        String severity
        String rule_id
        Text rule_description
        Integer row_number
        String field
        String expected_value
        String actual_value
        Text message
        JSON context
    }
```

---

## Frontend

### User Flow

```mermaid
stateDiagram-v2
    [*] --> Login
    Login --> Register: Create account
    Register --> Login: Already have account

    Login --> Upload: Authenticated
    Upload --> Results: File validated

    Results --> Upload: Validate another

    Upload --> Login: Logout
    Results --> Login: Logout
```

### Pages

| Page | Route | Auth | Description |
|---|---|---|---|
| **Login** | `/login` | Public | Nickname + password login form |
| **Register** | `/register` | Public | Account creation with password confirmation |
| **Upload** | `/upload` | Protected | Drag-and-drop file upload, auto-triggers validation |
| **Results** | `/results/:validationId` | Protected | Summary cards + filterable issue list with severity badges |

### Component Architecture

```mermaid
graph TD
    App["App (Router)"]
    App --> AuthProvider["AuthProvider (Context)"]
    AuthProvider --> PublicRoutes["Public Routes"]
    AuthProvider --> ProtectedRoute["ProtectedRoute (Guard)"]

    PublicRoutes --> Login["LoginPage"]
    PublicRoutes --> Register["RegisterPage"]

    ProtectedRoute --> Layout["Layout (Shell)"]
    Layout --> Upload["UploadPage"]
    Layout --> Results["ResultsPage"]

    Layout --> Header["Header (Logo + Logout)"]
    Layout --> Footer["Footer"]

    Upload --> FileUpload["File Upload Zone"]
    Results --> SummaryCards["Summary Cards"]
    Results --> IssueList["Issue List (Filterable)"]

    subgraph UI["shadcn/ui Components"]
        Button
        Card
        Badge
        Input
        Spinner
    end

    Login --> UI
    Register --> UI
    Upload --> UI
    Results --> UI
```

---

## Testing

**136 tests** — all passing.

| Test File | Count | Coverage |
|---|---|---|
| `test_api.py` | 22 | API endpoints, auth flow, protected routes, error responses |
| `test_e2e_auth.py` | 25 | End-to-end auth: register, login, me, multi-user isolation, full flows |
| `test_parser.py` | 21 | File parsing for all formats, edge cases |
| `test_rules.py` | 68 | All 11 validation rules with valid and invalid fixtures |

### Running Tests

```bash
cd royalties/backend

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_rules.py -v

# Run specific marker
python -m pytest tests/ -m e2e -v
```

Tests use **in-memory SQLite** (aiosqlite) — no running database required.

### Test Fixtures

Sample statement files are in `backend/tests/fixtures/`:

| Fixture | Purpose |
|---|---|
| `valid_statement.csv` | Fully valid statement |
| `schilling_native.csv` | Native Schilling export format |
| `missing_titles.csv` | Rows missing product identifiers |
| `bad_rates.csv` | Invalid royalty rates |
| `calculation_errors.csv` | Mismatched calculated amounts |
| `duplicate_rows.csv` | Duplicate entries |
| `mixed_issues.csv` | Multiple issue types combined |
| `advances_guarantees.csv` | Advance and guarantee scenarios |
| `valid_statement.json` | Valid JSON format statement |

---

## Configuration

All backend settings are managed via environment variables or the `Settings` class in `app/config.py`:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://validator:validator@localhost:5432/validator` | Database connection string |
| `UPLOAD_DIR` | `./uploads` | File storage path |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum upload file size |
| `ALLOWED_EXTENSIONS` | `csv,xlsx,json,pdf` | Accepted file types |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | CORS allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `AMOUNT_TOLERANCE` | `0.01` | Rounding tolerance for amount checks |
| `MAX_RATE_THRESHOLD` | `0.50` | Warn if royalty rate exceeds this |
| `JWT_SECRET` | `change-me-in-production` | JWT signing secret (**change in production**) |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | `480` | Token lifetime (8 hours) |

---

## Project Structure

```
royaltyStatementValidator/
├── baseDocs/                          # Domain documentation
│   ├── RoyaltySettlementSystem.md     # Schilling ERP system reference
│   └── RoyaltyStatementValidatorPlan.md
│
└── royalties/
    ├── docker-compose.yml             # Service orchestration
    │
    ├── backend/
    │   ├── Dockerfile                 # Multi-stage Python build
    │   ├── pyproject.toml             # Dependencies & project metadata
    │   │
    │   ├── app/
    │   │   ├── main.py                # FastAPI app, lifespan, routers
    │   │   ├── config.py              # Settings (env vars, defaults)
    │   │   │
    │   │   ├── api/
    │   │   │   ├── auth.py            # Register, login, me + JWT helpers
    │   │   │   ├── uploads.py         # File upload + retrieval
    │   │   │   └── validations.py     # Run validation, get results
    │   │   │
    │   │   ├── db/
    │   │   │   └── session.py         # Async SQLAlchemy engine & session
    │   │   │
    │   │   ├── models/
    │   │   │   ├── base.py            # Declarative base
    │   │   │   ├── user.py            # User model
    │   │   │   ├── upload.py          # Upload model
    │   │   │   ├── validation_run.py  # ValidationRun model
    │   │   │   └── validation_issue.py# ValidationIssue model
    │   │   │
    │   │   ├── schemas/
    │   │   │   ├── user.py            # Auth request/response schemas
    │   │   │   ├── upload.py          # Upload schemas
    │   │   │   └── validation.py      # Validation schemas
    │   │   │
    │   │   ├── services/
    │   │   │   ├── upload_service.py   # File handling + parsing on upload
    │   │   │   └── validation_service.py # Orchestrates engine + persistence
    │   │   │
    │   │   └── validation/
    │   │       ├── engine.py           # ValidationEngine orchestrator
    │   │       ├── parser.py           # Multi-format parser (CSV/Excel/JSON/PDF)
    │   │       └── rules/
    │   │           ├── base_rule.py    # Abstract base + Severity enum
    │   │           ├── missing_titles.py
    │   │           ├── invalid_rates.py
    │   │           ├── amount_consistency.py
    │   │           ├── tax_validation.py
    │   │           ├── guarantee_validation.py
    │   │           ├── settlement_totals.py
    │   │           ├── duplicate_entries.py
    │   │           ├── date_validation.py
    │   │           ├── advance_balance.py
    │   │           ├── recipient_shares.py
    │   │           └── transaction_types.py
    │   │
    │   └── tests/
    │       ├── conftest.py            # Fixtures (async client, auth client)
    │       ├── test_api.py            # API endpoint tests
    │       ├── test_e2e_auth.py       # E2E auth flow tests
    │       ├── test_parser.py         # File parser tests
    │       ├── test_rules.py          # Validation rule tests
    │       └── fixtures/              # Sample statement files
    │
    └── frontend/
        ├── Dockerfile                 # Multi-stage Node → Nginx build
        ├── nginx.conf                 # SPA routing + API proxy
        ├── package.json
        ├── vite.config.ts
        ├── tailwind.config.js
        ├── components.json            # shadcn/ui configuration
        │
        └── src/
            ├── main.tsx               # App entry (AuthProvider wrap)
            ├── App.tsx                # Router (public + protected routes)
            ├── api.ts                 # Typed fetch client + auth headers
            ├── types.ts               # TypeScript interfaces
            │
            ├── components/
            │   ├── AuthContext.tsx     # JWT auth context + provider
            │   ├── Layout.tsx         # App shell (header, footer, logout)
            │   ├── ProtectedRoute.tsx # Route guard (redirect if unauth)
            │   └── ui/               # shadcn/ui components
            │       ├── badge.tsx
            │       ├── button.tsx
            │       ├── card.tsx
            │       ├── input.tsx
            │       └── spinner.tsx
            │
            └── pages/
                ├── LoginPage.tsx
                ├── RegisterPage.tsx
                ├── UploadPage.tsx
                └── ResultsPage.tsx
```

---

## Domain Context

This application validates against business rules from the **Schilling ERP Royalty Settlement System** — a C++/Oracle-based publishing royalty engine used in the Danish publishing industry. Key domain concepts:

- **ROYPOST**: Central royalty ledger with 40+ transaction types (Sale, Return, Advance, Guarantee, etc.)
- **ROYAFTALE**: Agreement master data linking products to recipients via channels and price groups
- **Settlement flow**: 10-step pipeline from sales import to statement generation
- **Guarantee types**: Local, Global, and Method — each with offset tracking
- **Tax types**: Skat, Afgift, Moms, Pension, Ambi, GrossAmount

---

## License

This project is proprietary. All rights reserved.
