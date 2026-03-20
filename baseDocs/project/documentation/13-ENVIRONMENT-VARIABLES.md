# 13 — Environment Variables

## Overview

All backend configuration is managed via environment variables using `pydantic-settings`. Variables can be set in:

1. The `environment` section of `docker-compose.yml`
2. A `.env` file in the `royalties/` directory
3. System environment variables
4. Directly in the shell before starting the backend

---

## Backend Configuration

### Database

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://validator:validator@localhost:5432/validator` | Yes | PostgreSQL connection string. Use `sqlite+aiosqlite:///./dev.db` for local dev without Postgres. |

### File Storage

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `UPLOAD_DIR` | `./uploads` | No | Directory where uploaded files are stored |
| `MAX_UPLOAD_SIZE_MB` | `50` | No | Maximum upload file size in megabytes |
| `ALLOWED_EXTENSIONS` | `csv,xlsx,json,pdf,zip,tar,gz,rar` | No | Comma-separated list of accepted file extensions |

### Authentication

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `JWT_SECRET` | `change-me-in-production` | **Yes (production)** | Secret key for JWT signing. **Must be changed in production.** |
| `JWT_ALGORITHM` | `HS256` | No | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | `480` | No | Token lifetime in minutes (default: 8 hours) |

### CORS

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `CORS_ORIGINS` | `["http://localhost:5173"]` | No | JSON array of allowed CORS origins |

### Validation Thresholds

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `AMOUNT_TOLERANCE` | `0.01` | No | Maximum rounding difference before flagging amount inconsistency |
| `MAX_RATE_THRESHOLD` | `1.00` | No | Maximum valid royalty rate (1.00 = 100%). Values above this trigger warnings. |

### AI Chat / LLM

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `OPENAI_API_KEY` | (none) | No | OpenAI API key for GPT-4o-mini. Without this, falls back to Docker Model Runner. |
| `DMR_BASE` | `http://model-runner.docker.internal/engines/llama.cpp/v1` | No | Docker Model Runner base URL (fallback LLM) |

### Logging

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `LOG_LEVEL` | `INFO` | No | Python logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Docker Compose Environment

### PostgreSQL (`db`)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `validator` | Database user |
| `POSTGRES_PASSWORD` | `validator` | Database password |
| `POSTGRES_DB` | `validator` | Database name |

### pgAdmin (`pgadmin`)

| Variable | Default | Description |
|----------|---------|-------------|
| `PGADMIN_DEFAULT_EMAIL` | `admin@admin.com` | Login email |
| `PGADMIN_DEFAULT_PASSWORD` | `admin` | Login password |

### AnythingLLM (`anythingllm`)

AnythingLLM configuration is managed through its own `.env` file or through its web UI at `:3001`. See `royalties/anythingllm.env` for reference.

---

## Frontend Configuration

The frontend has no runtime environment variables. All configuration is baked in at build time via Vite.

### Build-Time Configuration (`vite.config.ts`)

| Setting | Value | Description |
|---------|-------|-------------|
| Dev server port | `5173` | Vite dev server port |
| API proxy target | `http://localhost:8000` | Backend URL for dev proxy |
| Path alias `@` | `./src` | Import alias |

### Runtime Constants

| Constant | Location | Value | Description |
|----------|----------|-------|-------------|
| `BASE` | `api.ts` | `/api` | API base path |
| `rsv_token` | `AuthContext.tsx` | localStorage key | Token storage key |
| `rsv_nickname` | `AuthContext.tsx` | localStorage key | Nickname cache key |
| `rv-theme` | `ThemeProvider.tsx` | localStorage key | Theme preference key |

---

## Example `.env` File

Create this file at `royalties/.env`:

```env
# Required for production
JWT_SECRET=your-very-long-random-secret-key-here-at-least-32-chars

# OpenAI (optional — enables primary LLM)
OPENAI_API_KEY=sk-your-openai-api-key

# Database (override if not using default Docker credentials)
# POSTGRES_USER=validator
# POSTGRES_PASSWORD=secure-password
# POSTGRES_DB=validator

# Backend overrides
# MAX_UPLOAD_SIZE_MB=100
# AMOUNT_TOLERANCE=0.02
# MAX_RATE_THRESHOLD=0.50
# JWT_EXPIRE_MINUTES=240
# LOG_LEVEL=DEBUG
```

---

## Environment by Context

### Docker (Production-like)

```yaml
# docker-compose.yml
backend:
  environment:
    DATABASE_URL: postgresql+asyncpg://validator:validator@db:5432/validator
    UPLOAD_DIR: /app/uploads
    CORS_ORIGINS: '["http://localhost:5173","http://localhost"]'
    DMR_BASE: http://model-runner.docker.internal/engines/llama.cpp/v1
    OPENAI_API_KEY: ${OPENAI_API_KEY}
    JWT_SECRET: ${JWT_SECRET:-change-me-in-production}
```

### Local Development (SQLite)

```bash
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
export UPLOAD_DIR="./uploads"
export CORS_ORIGINS='["http://localhost:5173"]'
export JWT_SECRET="dev-secret-not-for-production"
```

### Local Development (Docker DB only)

```bash
export DATABASE_URL="postgresql+asyncpg://validator:validator@localhost:5432/validator"
export UPLOAD_DIR="./uploads"
```

### Testing

Tests override the database URL to use in-memory SQLite:

```python
DATABASE_URL = "sqlite+aiosqlite://"  # In-memory
```

No other environment variables are needed for testing.
