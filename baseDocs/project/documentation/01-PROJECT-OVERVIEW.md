# 01 — Project Overview

## What Is the Royalty Statement Validator?

The Royalty Statement Validator is a **standalone web application** that validates royalty statement files exported from the **Schilling ERP** system — a Danish publishing-industry royalty settlement platform written in C++ with Oracle SQL.

The validator catches inconsistencies, missing data, and calculation errors **before** statements are processed or shared with authors. It analyzes files in multiple formats (CSV, Excel, JSON, PDF) and applies 11 business-rule checks derived from the same logic the Schilling engine enforces.

### What It Does

- Accepts royalty statement files via drag-and-drop or file picker
- Parses CSV, Excel, JSON, and Schilling-specific PDF formats
- Runs 11 validation rules covering titles, rates, amounts, taxes, guarantees, totals, duplicates, dates, advances, shares, and transaction types
- Presents results in a dashboard with severity-coded issues (error / warning / info)
- Generates PDF validation reports (styled summary + annotated source data)
- Provides an AI-powered assistant for explaining results and Danish royalty terminology
- Supports batch upload of multiple files (including ZIP/TAR/RAR archives)

### What It Is NOT

- **Not** a replacement for the Schilling ERP settlement engine
- **Not** connected to the Oracle database in real-time
- **Not** a full settlement calculation system
- It works **exclusively** on exported/generated files

---

## Target Users

| User | Use Case |
|------|----------|
| **Publishers** | Validate statements before sending to authors |
| **Royalty Administrators** | Quality-check exported data for errors |
| **Finance Teams** | Verify calculation integrity before processing payments |
| **Developers** | Test and debug Schilling export data |

---

## Key Features

### File Upload & Parsing
- Drag-and-drop batch upload with real-time progress
- Archive extraction (ZIP, TAR, GZ, RAR) — automatically validates all files inside
- Smart parsing of Schilling-specific PDF statements (metadata blocks, sales tables, summary lines)
- Column name normalization and Danish number format conversion

### Validation Engine
- Plugin architecture — 11 independent rule classes
- Each rule returns issues tagged with severity, row number, field, expected/actual values
- Configurable tolerances (amount rounding, rate thresholds)
- Results persisted to database for history and re-review

### Results Dashboard
- Summary cards: passed checks, warnings, errors, info
- Filterable, paginated issue list with severity badges
- Document preview (table view, raw text, PDF iframe)
- Downloadable PDF reports (styled summary + annotated data)

### AI Assistant
- Two modes: Document Assistant (sidebar, context-aware) and Royalty Assistant (full page, RAG/SQL agent)
- Powered by OpenAI GPT-4o-mini with AnythingLLM RAG context
- Fallback to Docker Model Runner (Qwen 2.5) when OpenAI is unavailable
- SSE streaming with AG-UI protocol for real-time token delivery
- File upload support for ad-hoc document analysis

### Authentication
- JWT-based with bcrypt password hashing
- 8-hour token lifetime
- Simple nickname + password registration

---

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12+ · FastAPI · SQLAlchemy 2.0 (async) · Pydantic |
| **Database** | PostgreSQL 16 |
| **Frontend** | React 19 · TypeScript · Vite 8 · Tailwind CSS 3 · shadcn/ui |
| **AI/Chat** | OpenAI GPT-4o-mini · AnythingLLM (RAG) · Docker Model Runner (fallback) |
| **Infrastructure** | Docker Compose · Nginx · pgAdmin |
| **Testing** | pytest · pytest-asyncio · aiosqlite (in-memory) |

---

## Repository Structure (Top-Level)

```
royaltyStatementValidator/
├── baseDocs/                    # Domain documentation & reference data
│   ├── project/                 # Project plans, system docs, this documentation
│   └── royaltyBase/             # Sample royalty statement files (CSV, PDF, JSON, XLSX)
├── royalties/                   # Application source code
│   ├── docker-compose.yml       # Service orchestration
│   ├── backend/                 # Python FastAPI backend
│   ├── frontend/                # React TypeScript frontend
│   ├── seed_royalty_docs.sh     # Knowledge base seeding script
│   └── pgadmin-servers.json     # pgAdmin auto-config
├── README.md                    # Top-level readme
├── generate_royalty_base.py     # Test data generator
└── test_*.py                    # Integration/smoke test scripts
```
