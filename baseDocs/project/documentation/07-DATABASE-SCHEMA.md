# 07 — Database Schema

## Overview

The application uses **PostgreSQL 16** as its primary data store, accessed via **SQLAlchemy 2.0 async** with the `asyncpg` driver.

Tables are auto-created on application startup via `Base.metadata.create_all()`. Alembic is installed for migration management but is not currently used in the auto-creation flow.

---

## Entity Relationship Diagram

```
┌─────────────┐       ┌──────────────┐       ┌──────────────────┐       ┌───────────────────┐
│   users     │       │   uploads    │       │ validation_runs  │       │ validation_issues │
├─────────────┤       ├──────────────┤       ├──────────────────┤       ├───────────────────┤
│ id (PK)     │──1:N─▶│ id (PK)      │──1:N─▶│ id (PK)          │──1:N─▶│ id (PK)           │
│ nickname    │       │ user_id (FK) │       │ upload_id (FK)   │       │ validation_run_id │
│ password_hash│      │ filename     │       │ status           │       │ severity          │
│ created_at  │       │ file_path    │       │ rules_executed   │       │ rule_id           │
└─────────────┘       │ file_format  │       │ passed_count     │       │ rule_description  │
                      │ row_count    │       │ warning_count    │       │ row_number        │
                      │ uploaded_at  │       │ error_count      │       │ field             │
                      └──────────────┘       │ info_count       │       │ expected_value    │
                                             │ started_at       │       │ actual_value      │
                                             │ completed_at     │       │ message           │
                                             └──────────────────┘       │ context (JSON)    │
                                                                        └───────────────────┘
```

---

## Tables

### `users`

Stores user accounts.

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | `UUID` | PRIMARY KEY | `uuid4()` | Unique user identifier |
| `nickname` | `VARCHAR(100)` | UNIQUE, NOT NULL, INDEXED | — | Display name / login identifier |
| `password_hash` | `VARCHAR(128)` | NOT NULL | — | bcrypt-hashed password |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Account creation timestamp |

**Relationships**:
- `uploads` → one-to-many → `Upload`

**SQLAlchemy model**: `app/models/user.py`

---

### `uploads`

Stores uploaded file records.

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | `UUID` | PRIMARY KEY | `uuid4()` | Unique upload identifier |
| `user_id` | `UUID` | FOREIGN KEY → `users.id`, NOT NULL | — | Owning user |
| `filename` | `VARCHAR(500)` | NOT NULL | — | Original filename |
| `file_path` | `VARCHAR(1000)` | NOT NULL | — | Absolute path on disk |
| `file_format` | `VARCHAR(10)` | NOT NULL | — | File format: `csv`, `xlsx`, `json`, `pdf` |
| `row_count` | `INTEGER` | NULLABLE | — | Number of data rows parsed |
| `uploaded_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | Upload timestamp |

**Relationships**:
- `user` → many-to-one → `User`
- `validation_runs` → one-to-many → `ValidationRun`

**SQLAlchemy model**: `app/models/upload.py`

---

### `validation_runs`

Stores validation execution records.

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | `UUID` | PRIMARY KEY | `uuid4()` | Unique validation run identifier |
| `upload_id` | `UUID` | FOREIGN KEY → `uploads.id`, NOT NULL | — | The file being validated |
| `status` | `VARCHAR(20)` | NOT NULL | `'pending'` | Run state: `pending` → `running` → `completed` \| `failed` |
| `rules_executed` | `INTEGER` | NOT NULL | `0` | Number of rules that ran |
| `passed_count` | `INTEGER` | NOT NULL | `0` | Rules that found no issues |
| `warning_count` | `INTEGER` | NOT NULL | `0` | Warning-level issues found |
| `error_count` | `INTEGER` | NOT NULL | `0` | Error-level issues found |
| `info_count` | `INTEGER` | NOT NULL | `0` | Info-level issues found |
| `started_at` | `TIMESTAMPTZ` | NULLABLE | — | When the run started |
| `completed_at` | `TIMESTAMPTZ` | NULLABLE | — | When the run finished |

**Relationships**:
- `upload` → many-to-one → `Upload`
- `issues` → one-to-many → `ValidationIssue`

**Status lifecycle**:
```
pending → running → completed
                  → failed
```

**SQLAlchemy model**: `app/models/validation_result.py`

---

### `validation_issues`

Stores individual validation issues/findings.

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `id` | `UUID` | PRIMARY KEY | `uuid4()` | Unique issue identifier |
| `validation_run_id` | `UUID` | FOREIGN KEY → `validation_runs.id`, NOT NULL | — | Parent validation run |
| `severity` | `VARCHAR(10)` | NOT NULL | — | `error`, `warning`, or `info` |
| `rule_id` | `VARCHAR(50)` | NOT NULL | — | Rule identifier (e.g. `missing_titles`) |
| `rule_description` | `TEXT` | NOT NULL | — | Human-readable rule description |
| `row_number` | `INTEGER` | NULLABLE | — | Source row where issue was found (1-based) |
| `field` | `VARCHAR(100)` | NULLABLE | — | Column/field name with the issue |
| `expected_value` | `VARCHAR(200)` | NULLABLE | — | What the value should be |
| `actual_value` | `VARCHAR(200)` | NULLABLE | — | What the value actually was |
| `message` | `TEXT` | NOT NULL | — | Detailed issue description |
| `context` | `JSON` | NULLABLE | — | Extra metadata (agreement, product, etc.) |

**SQLAlchemy model**: `app/models/validation_result.py`

---

## Connection Configuration

```python
# Async SQLAlchemy engine
engine = create_async_engine(settings.database_url, echo=False)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

**Connection string format**: `postgresql+asyncpg://user:password@host:port/database`

**Default**: `postgresql+asyncpg://validator:validator@db:5432/validator` (Docker)

---

## Session Management

The `get_db()` dependency provides a transactional session per request:

```python
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- **Auto-commit on success**: If the request handler completes without error, the session is committed.
- **Auto-rollback on error**: If any exception occurs, the session is rolled back.
- **No manual commit needed**: Route handlers operate within the session and trust the commit/rollback lifecycle.

---

## Migration Strategy

Alembic is included as a dependency but **tables are currently auto-created** at startup:

```python
# In main.py lifespan
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

For production, consider switching to Alembic migrations:

```bash
# Initialize Alembic (once)
alembic init alembic

# Generate migration from model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

---

## Indexes

| Table | Column | Index Type | Notes |
|-------|--------|-----------|-------|
| `users` | `nickname` | UNIQUE | Fast lookup for login |
| `uploads` | `user_id` | FK (implicit) | Filter uploads by user |
| `validation_runs` | `upload_id` | FK (implicit) | Link runs to uploads |
| `validation_issues` | `validation_run_id` | FK (implicit) | Link issues to runs |

---

## Data Volume Estimates

| Entity | Typical Volume | Notes |
|--------|---------------|-------|
| Users | 10-100 | Small team tool |
| Uploads | 100-1000 per user | Royalty statement files |
| Validation Runs | 1-3 per upload | Usually 1: initial validation |
| Validation Issues | 0-500 per run | Depends on file quality |
