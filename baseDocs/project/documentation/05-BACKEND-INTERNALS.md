# 05 — Backend Internals

## Application Entry Point

**File**: `backend/app/main.py`

The FastAPI application is created with:
- A `lifespan` context manager that initializes the database on startup (`Base.metadata.create_all`)
- CORS middleware configured from `settings.cors_origins`
- Four API routers mounted under `/api/`
- A `/health` endpoint

```python
# Router registration
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(uploads_router, prefix="/api/uploads", tags=["uploads"])
app.include_router(validations_router, prefix="/api/validations", tags=["validations"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
```

---

## Configuration (`config.py`)

Uses `pydantic-settings` to load configuration from environment variables with sensible defaults:

```python
class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://validator:validator@localhost:5432/validator"
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    allowed_extensions: str = "csv,xlsx,json,pdf,zip,tar,gz,rar"
    cors_origins: list[str] = ["http://localhost:5173"]
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    amount_tolerance: float = 0.01
    max_rate_threshold: float = 1.00
```

All settings are overridable via environment variables (case-insensitive).

---

## Service Layer

### `upload_service.py`

Handles file processing after upload:

1. Validates file extension against `ALLOWED_EXTENSIONS`
2. Checks file size against `MAX_UPLOAD_SIZE_MB`
3. Saves file to disk at `{UPLOAD_DIR}/{uuid}.{ext}`
4. Calls the parser to count rows
5. Returns `(file_path, row_count, file_format)`

For archive files (ZIP/TAR/GZ/RAR), delegates to `archive_service.py` for extraction.

### `validation_service.py`

Orchestrates a validation run:

1. Creates a `ValidationRun` record in DB (status: `pending`)
2. Parses the uploaded file using `parser.py` → `list[dict]`
3. Passes data to `ValidationEngine.run()` → list of `ValidationIssue`
4. Creates `ValidationIssue` records in DB
5. Updates `ValidationRun` with counts (passed, warning, error, info)
6. Sets status to `completed` (or `failed` on exception)

### `archive_service.py`

Extracts files from ZIP, TAR, GZ, and RAR archives:

- Filters extracted files to allowed extensions (csv, xlsx, json, pdf)
- Skips macOS junk files (`__MACOSX/`, `.DS_Store`)
- Assigns new UUID filenames to extracted files
- Returns a list of `(filename, file_path, file_format)` tuples

### `batch_service.py`

Manages multi-file batch validation with SSE progress:

1. Accepts a list of `upload_ids`
2. Creates a `batch_id` (UUID)
3. For each file: emits `file_start` → runs validation → emits `file_complete` or `file_error`
4. Finally emits `batch_complete`
5. Progress is streamed via Server-Sent Events

### `pdf_service.py`

Generates a styled PDF validation report using ReportLab:

- Header section: filename, validation date, summary counts
- Per-rule sections: pass/fail indicator, rule description
- Issue table: severity badge, row number, field, expected vs actual, message
- Color-coded severity indicators (red = error, amber = warning, blue = info)

### `annotated_pdf_service.py`

Generates an annotated data PDF:

- Renders the full source data as a table
- Highlights cells that triggered validation issues
- Color-codes cells by severity
- Includes a legend and issue summary

---

## Validation Engine

### `validation/engine.py`

The `ValidationEngine` class:

1. Auto-discovers all rule classes in `validation/rules/`
2. Instantiates each rule
3. Runs all rules against the parsed data
4. Collects and returns all issues

```python
class ValidationEngine:
    def __init__(self, settings: Settings):
        self.rules = self._discover_rules()
        self.settings = settings

    def run(self, data: list[dict]) -> list[ValidationIssue]:
        issues = []
        for rule in self.rules:
            issues.extend(rule.validate(data))
        return issues
```

### `validation/base_rule.py`

Abstract base class for all rules:

```python
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
    context: dict | None = None

class BaseRule(ABC):
    @property
    @abstractmethod
    def rule_id(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def validate(self, data: list[dict]) -> list[ValidationIssue]: ...
```

### `validation/parser.py`

Multi-format parser that normalizes all file types to `list[dict]`:

| Format | Library | Key Behavior |
|--------|---------|-------------|
| **CSV** | `pandas` | Auto-detects `;` vs `,` delimiter. Resolves Schilling `=N/100` formulas. Normalizes column names (lowercase, strip whitespace). |
| **XLSX** | `openpyxl` | Reads first worksheet, first row as headers. |
| **JSON** | stdlib | Accepts `list[dict]` or `{"rows": [...]}`. |
| **PDF** | `pdfplumber` | Schilling-specific: extracts metadata, sales lines, summary rows per page. |

**Reserved keys** added to every row:
- `_row_number`: Original row index (1-based)
- `_source`: Source filename
- `_record_type`: Type identifier (e.g., `sale`, `summary`, `metadata`)
- `_page_number`: PDF page number (PDF only)

---

## API Route Handlers

### `api/auth.py`

- `register()`: Hash password with bcrypt → create user → generate JWT → return token
- `login()`: Lookup user by nickname → verify bcrypt hash → generate JWT → return token
- `me()`: Decode JWT → fetch user from DB → return user profile
- `get_current_user()`: FastAPI dependency that extracts and validates the JWT from the Authorization header

### `api/uploads.py`

- `upload_file()`: Accept multipart file → validate → save to disk → parse → create Upload record → return response
- `list_uploads()`: Query all uploads for current user with nested validation runs, ordered by newest first (limit 50)
- `get_upload()`: Fetch single upload by ID (ownership check)
- `get_upload_content()`: Parse and return file preview (up to 50K rows / 500 KB)

### `api/validations.py`

- `run_validation()`: Create ValidationRun → parse file → execute engine → persist issues → return results
- `get_validation()`: Fetch full ValidationRun with all issues
- `get_issues()`: Paginated, severity-filtered issue list
- `get_validation_pdf()`: Generate and stream styled PDF report
- `get_annotated_pdf()`: Generate and stream annotated data PDF
- `create_batch()`: Accept upload IDs → create batch → return batch_id
- `batch_progress()`: SSE endpoint streaming validation progress events

### `api/chat.py`

- `chat_stream()`: Accept messages → fetch RAG context from AnythingLLM → stream LLM response via SSE
- `chat_upload()`: Accept file → extract text/data → return document content for chat context injection

---

## Dependency Injection

FastAPI dependency injection is used throughout:

```python
# Database session
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Current authenticated user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Decode JWT → fetch user → return or 401

# Type alias for convenience
CurrentUser = Annotated[User, Depends(get_current_user)]
```

Usage in routes:
```python
@router.post("/")
async def upload_file(
    file: UploadFile,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    ...
```
