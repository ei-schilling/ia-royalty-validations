# Royalty Statement Validator — Documentation Index

> **Last updated**: March 2026

Welcome to the Royalty Statement Validator documentation. This index provides a roadmap to all available documentation for developers, contributors, and stakeholders.

---

## Quick Navigation

| # | Document | Description |
|---|----------|-------------|
| 01 | [Project Overview](./01-PROJECT-OVERVIEW.md) | What this project is, its purpose, and high-level summary |
| 02 | [Architecture](./02-ARCHITECTURE.md) | System architecture, service topology, data flow diagrams |
| 03 | [Getting Started](./03-GETTING-STARTED.md) | Setup, installation, first run — everything to go from zero to running |
| 04 | [Backend API Reference](./04-BACKEND-API.md) | Full REST API documentation with request/response schemas |
| 05 | [Backend Internals](./05-BACKEND-INTERNALS.md) | Services, validation engine, file parsing, rule plugins |
| 06 | [Frontend Guide](./06-FRONTEND-GUIDE.md) | React application, components, pages, state management |
| 07 | [Database Schema](./07-DATABASE-SCHEMA.md) | Tables, columns, relationships, migration strategy |
| 08 | [Authentication & Security](./08-AUTHENTICATION.md) | JWT auth flow, password hashing, token lifecycle |
| 09 | [AI Chat System](./09-AI-CHAT-SYSTEM.md) | RAG pipeline, LLM integration, SSE streaming, AG-UI protocol |
| 10 | [Validation Rules](./10-VALIDATION-RULES.md) | All 11 rules in detail — what they check, how they work |
| 11 | [File Parsing](./11-FILE-PARSING.md) | Multi-format parser — CSV, Excel, JSON, PDF (Schilling-specific) |
| 12 | [Docker & Infrastructure](./12-DOCKER-INFRASTRUCTURE.md) | docker-compose, Dockerfiles, nginx, volumes, networking |
| 13 | [Environment Variables](./13-ENVIRONMENT-VARIABLES.md) | Complete configuration reference |
| 14 | [Testing](./14-TESTING.md) | Test suite, fixtures, running tests, coverage |
| 15 | [Domain Glossary](./15-DOMAIN-GLOSSARY.md) | Schilling ERP terminology, Danish field names, business concepts |
| 16 | [Batch Upload & SSE](./16-BATCH-UPLOAD-SSE.md) | Multi-file upload flow, archive extraction, SSE progress events |
| 17 | [PDF Report Generation](./17-PDF-REPORTS.md) | Styled validation reports and annotated data PDFs |
| 18 | [Frontend Components](./18-FRONTEND-COMPONENTS.md) | Component catalog — shadcn/ui, custom components, design tokens |
| 19 | [Contributing](./19-CONTRIBUTING.md) | Code style, conventions, PR workflow, adding new rules |
| 20 | [Troubleshooting](./20-TROUBLESHOOTING.md) | Common issues, debugging tips, FAQ |

---

## For Different Audiences

### New Developer Onboarding
Start with: [01 → Project Overview](./01-PROJECT-OVERVIEW.md) → [03 → Getting Started](./03-GETTING-STARTED.md) → [02 → Architecture](./02-ARCHITECTURE.md)

### Backend Developer
Read: [05 → Backend Internals](./05-BACKEND-INTERNALS.md) → [04 → API Reference](./04-BACKEND-API.md) → [10 → Validation Rules](./10-VALIDATION-RULES.md) → [07 → Database](./07-DATABASE-SCHEMA.md)

### Frontend Developer
Read: [06 → Frontend Guide](./06-FRONTEND-GUIDE.md) → [18 → Components](./18-FRONTEND-COMPONENTS.md) → [09 → AI Chat](./09-AI-CHAT-SYSTEM.md)

### DevOps / Infrastructure
Read: [12 → Docker & Infrastructure](./12-DOCKER-INFRASTRUCTURE.md) → [13 → Environment Variables](./13-ENVIRONMENT-VARIABLES.md)

### Domain Expert / Business Analyst
Read: [01 → Project Overview](./01-PROJECT-OVERVIEW.md) → [15 → Domain Glossary](./15-DOMAIN-GLOSSARY.md) → [10 → Validation Rules](./10-VALIDATION-RULES.md)
