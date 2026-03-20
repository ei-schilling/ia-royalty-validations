# 02 — Architecture

## System Overview

The Royalty Statement Validator is a containerized, full-stack web application composed of five Docker services communicating over an internal Docker network.

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Docker Compose                              │
│                                                                      │
│  ┌────────────┐   ┌──────────────┐   ┌────────────┐                │
│  │  Frontend   │   │   Backend    │   │  Database   │                │
│  │  (Nginx)    │──▶│  (FastAPI)   │──▶│ (Postgres)  │                │
│  │   :80       │   │   :8000      │   │   :5432     │                │
│  └────────────┘   └──────┬───────┘   └────────────┘                │
│                          │                                           │
│              ┌───────────┼───────────┐                               │
│              ▼                       ▼                               │
│  ┌────────────────┐    ┌──────────────────┐                         │
│  │  AnythingLLM   │    │  Docker Model    │                         │
│  │  (RAG Vector)  │    │  Runner (LLM)    │                         │
│  │   :3001        │    │  host.docker     │                         │
│  └────────────────┘    └──────────────────┘                         │
│                                                                      │
│  ┌────────────┐                                                      │
│  │  pgAdmin   │                                                      │
│  │   :5050    │                                                      │
│  └────────────┘                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Service Topology

| Service | Image | Port | Role |
|---------|-------|------|------|
| **frontend** | Custom (Node build → Nginx) | `:80` | Serves React SPA, proxies `/api/*` to backend |
| **backend** | Custom (Python 3.12) | `:8000` | FastAPI REST API, validation engine, AI chat |
| **db** | `postgres:16-alpine` | `:5432` | Primary data store |
| **pgadmin** | `dpage/pgadmin4` | `:5050` | Database administration UI |
| **anythingllm** | `mintplexlabs/anythingllm` | `:3001` | Vector database for RAG (retrieval-augmented generation) |

---

## Request Flow

### Standard Request (Upload → Validate → View Results)

```
Browser
  │
  ├─ GET / ──────────────▶ Nginx ──▶ index.html (SPA)
  │
  ├─ POST /api/uploads/ ─▶ Nginx ──▶ FastAPI ──▶ Parse file
  │                                      │         ──▶ Save to /app/uploads/
  │                                      │         ──▶ INSERT uploads table
  │                                      ◀─────────── UploadResponse (JSON)
  │
  ├─ POST /api/validations/{id}/run
  │                        ──▶ Nginx ──▶ FastAPI ──▶ Parse file → list[dict]
  │                                      │         ──▶ Run 11 rules
  │                                      │         ──▶ INSERT validation_runs + issues
  │                                      ◀─────────── ValidationRunResponse
  │
  └─ GET /api/validations/{id}
                           ──▶ Nginx ──▶ FastAPI ──▶ SELECT from DB
                                         ◀─────────── Full results + issues
```

### AI Chat Request (SSE Streaming)

```
Browser (TanStack AI)
  │
  ├─ POST /api/chat/stream?mode=query
  │      ──▶ Nginx (proxy_buffering off)
  │      ──▶ FastAPI
  │           │
  │           ├─ Fetch RAG context from AnythingLLM (/api/v1/workspace/...)
  │           │
  │           ├─ Build system prompt + user messages + RAG context
  │           │
  │           ├─ Stream to OpenAI GPT-4o-mini (primary)
  │           │   └─ or Docker Model Runner Qwen 2.5 (fallback)
  │           │
  │           └─ SSE Response (AG-UI protocol):
  │                RUN_STARTED → TEXT_MESSAGE_START →
  │                TEXT_MESSAGE_CONTENT (per token) →
  │                TEXT_MESSAGE_END → RUN_FINISHED
  │
  └─ Browser renders tokens in real-time
```

### Batch Upload Flow (SSE Progress)

```
Browser
  │
  ├─ POST /api/uploads/ (repeated for each file)
  │      ──▶ Returns upload_ids[]
  │
  ├─ POST /api/validations/batch {upload_ids}
  │      ──▶ Returns {batch_id}
  │
  └─ GET /api/validations/batch/{batch_id}/progress (EventSource)
         ──▶ SSE events:
              file_start → file_complete → ... → batch_complete
```

---

## Backend Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │                   API Layer                       │   │
│  │  auth.py │ uploads.py │ validations.py │ chat.py  │   │
│  └──────────────────┬───────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────┴───────────────────────────────┐   │
│  │               Service Layer                       │   │
│  │  upload_service │ validation_service │ pdf_service │   │
│  │  archive_service │ batch_service │ annotated_pdf  │   │
│  └──────────────────┬───────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────┴───────────────────────────────┐   │
│  │             Validation Engine                     │   │
│  │  engine.py → discovers + runs 11 rule plugins     │   │
│  │                                                    │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐            │   │
│  │  │ Rule 1  │ │ Rule 2  │ │ Rule 3  │  ...        │   │
│  │  │ missing │ │ invalid │ │ amount  │  (11 total) │   │
│  │  │ titles  │ │ rates   │ │ consist │             │   │
│  │  └─────────┘ └─────────┘ └─────────┘            │   │
│  └──────────────────────────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────┴───────────────────────────────┐   │
│  │              Data Layer                           │   │
│  │  SQLAlchemy async │ asyncpg │ PostgreSQL 16       │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Files | Responsibility |
|-------|-------|----------------|
| **API** | `api/auth.py`, `api/uploads.py`, `api/validations.py`, `api/chat.py` | HTTP routing, request validation, response serialization |
| **Schemas** | `schemas/user.py`, `schemas/upload.py`, `schemas/validation.py` | Pydantic models for request/response contracts |
| **Services** | `services/*.py` | Business logic, file processing, report generation |
| **Validation** | `validation/engine.py`, `validation/parser.py`, `validation/rules/*.py` | File parsing and rule execution |
| **Models** | `models/user.py`, `models/upload.py`, `models/validation_result.py` | SQLAlchemy ORM table definitions |
| **Database** | `db/database.py` | Async engine, session factory, connection management |
| **Config** | `config.py` | Environment-driven settings via pydantic-settings |

---

## Frontend Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Application                     │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              App.tsx (Router)                      │   │
│  │  BrowserRouter → Routes → Layout → Pages          │   │
│  └──────────────────┬───────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────┴───────────────────────────────┐   │
│  │              Context Providers                     │   │
│  │  AuthContext │ ThemeProvider                       │   │
│  └──────────────────┬───────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────┴───────────────────────────────┐   │
│  │                  Pages                            │   │
│  │  LoginPage │ RegisterPage │ UploadPage            │   │
│  │  ResultsPage │ HelpPage                           │   │
│  └──────────────────┬───────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────┴───────────────────────────────┐   │
│  │             Feature Modules                       │   │
│  │                                                    │   │
│  │  features/ai-chat/     features/uploads/           │   │
│  │  ├── components/       ├── components/             │   │
│  │  ├── hooks/            ├── hooks/                  │   │
│  │  └── types.ts          ├── api/                    │   │
│  │                        ├── utils/                  │   │
│  │                        └── types.ts                │   │
│  └──────────────────────────────────────────────────┘   │
│                     │                                    │
│  ┌──────────────────┴───────────────────────────────┐   │
│  │           UI Component Library                    │   │
│  │  shadcn/ui (Radix) │ Tailwind CSS │ Lucide icons  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### State Management Strategy

The application uses **no global store** (no Redux, no Zustand). State is managed through:

| Concern | Strategy |
|---------|----------|
| Authentication | React Context (`AuthContext`) |
| Theme | React Context (`ThemeProvider`) |
| File upload queue | Local hook state (`useFileQueue`) |
| Upload progress | SSE subscription (`useUploadProgress`) |
| Chat messages | TanStack AI (`useChat`) |
| Validation results | Local `useState` per page |

---

## Data Flow Diagram

```
                 ┌──────────────┐
                 │  User uploads │
                 │  a file       │
                 └──────┬───────┘
                        │
                        ▼
              ┌─────────────────┐
              │  File Parsing   │
              │  CSV/XLSX/JSON/ │
              │  PDF → list[dict]│
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐     ┌──────────────────┐
              │  Validation     │     │  Upload record    │
              │  Engine         │────▶│  saved to DB      │
              │  (11 rules)     │     └──────────────────┘
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐     ┌──────────────────┐
              │  Issues         │     │  ValidationRun    │
              │  collected      │────▶│  + Issues         │
              │  per rule       │     │  saved to DB      │
              └────────┬────────┘     └──────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Result sent    │
              │  to frontend    │
              │  as JSON        │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Dashboard      │
              │  renders:       │
              │  • Summary cards│
              │  • Issue list   │
              │  • PDF reports  │
              │  • AI chat      │
              └─────────────────┘
```

---

## Networking

All services communicate over a Docker bridge network created by docker-compose.

| Source | Destination | Protocol | Port |
|--------|-------------|----------|------|
| Browser | Nginx (frontend) | HTTP | 80 |
| Nginx | FastAPI (backend) | HTTP | 8000 |
| FastAPI | PostgreSQL (db) | TCP | 5432 |
| FastAPI | AnythingLLM | HTTP | 3001 |
| FastAPI | Docker Model Runner | HTTP | host network |
| FastAPI | OpenAI API | HTTPS | 443 |
| pgAdmin | PostgreSQL (db) | TCP | 5432 |

---

## Shared Volumes

| Volume | Containers | Purpose |
|--------|------------|---------|
| `pgdata` | db | PostgreSQL data persistence |
| `uploads` | backend, anythingllm | Uploaded files shared for RAG indexing |
| `anythingllm_storage` | anythingllm | Vector DB and configuration |
| `pgadmin_data` | pgadmin | pgAdmin session data |
