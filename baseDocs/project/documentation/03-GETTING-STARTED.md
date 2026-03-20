# 03 — Getting Started

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Docker** | 20.10+ | Docker Desktop recommended on Windows/Mac |
| **Docker Compose** | v2+ | Included with Docker Desktop |
| **Git** | Any | For cloning the repository |
| **Node.js** | 22+ | Only for local frontend development |
| **Python** | 3.12+ | Only for local backend development |

---

## Quick Start (Docker — Recommended)

### 1. Clone the Repository

```bash
git clone <repo-url>
cd royaltyStatementValidator
```

### 2. Set Environment Variables

Create a `.env` file in `royalties/` (next to `docker-compose.yml`):

```env
# Required for AI chat
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional overrides
JWT_SECRET=your-production-secret-here
```

> **Note**: The AI chat works without `OPENAI_API_KEY` if Docker Model Runner is available (falls back to Qwen 2.5 locally).

### 3. Start All Services

```bash
cd royalties
docker compose up --build -d
```

This builds and starts five containers: PostgreSQL, FastAPI backend, Nginx frontend, AnythingLLM, and pgAdmin.

### 4. Verify Everything Is Running

```bash
docker compose ps
```

Expected output:
```
NAME                    SERVICE      STATUS
royalties-backend-1     backend      Up
royalties-db-1          db           Up
royalties-frontend-1    frontend     Up
royalties-pgadmin-1     pgadmin      Up
royalties-anythingllm-1 anythingllm  Up
```

### 5. Seed the Knowledge Base (Optional)

For RAG-powered AI chat answers about royalty business rules:

```bash
bash seed_royalty_docs.sh
```

### 6. Open the Application

| Service | URL |
|---------|-----|
| **Web Application** | http://localhost |
| **API Swagger UI** | http://localhost:8000/docs |
| **API ReDoc** | http://localhost:8000/redoc |
| **Health Check** | http://localhost:8000/health |
| **pgAdmin** | http://localhost:5050 |
| **AnythingLLM** | http://localhost:3001 |

### 7. First Steps

1. Open http://localhost
2. Click "Register" → enter a nickname and password
3. Navigate to "Upload" → drag-and-drop a royalty statement file (CSV, Excel, JSON, or PDF)
4. View the validation results dashboard
5. Try the AI assistant at http://localhost/help

---

## Stop / Restart Services

```bash
# Stop containers (keep data)
docker compose down

# Stop containers and delete all data (full reset)
docker compose down -v

# Rebuild a single service after code changes
docker compose up --build -d backend

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart a specific service
docker compose restart backend
```

---

## Local Development (Without Docker)

### Backend (Python)

```bash
cd royalties/backend

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"
```

**Option A: Use SQLite for local dev** (no PostgreSQL needed):

```bash
set DATABASE_URL=sqlite+aiosqlite:///./dev.db   # Windows
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"  # Linux/Mac

python -m uvicorn app.main:app --reload --port 8000
```

**Option B: Use the Dockerized PostgreSQL**:

```bash
# Start only the database
cd ../
docker compose up -d db

# Back to backend
cd backend
set DATABASE_URL=postgresql+asyncpg://validator:validator@localhost:5432/validator

python -m uvicorn app.main:app --reload --port 8000
```

The API will be available at http://localhost:8000 with auto-reload on file changes.

### Frontend (React)

```bash
cd royalties/frontend

# Install dependencies
npm install

# Start dev server (with API proxy to localhost:8000)
npm run dev
```

The dev server starts at http://localhost:5173 with hot module replacement. API calls are proxied to the backend via Vite's built-in proxy.

### Running Both Together

1. Terminal 1: Start backend (`uvicorn` on `:8000`)
2. Terminal 2: Start frontend (`npm run dev` on `:5173`)
3. Open http://localhost:5173

The Vite dev server proxies all `/api/*` requests to `http://localhost:8000`.

---

## Project Structure

```
royaltyStatementValidator/
│
├── baseDocs/                          # Reference documentation
│   ├── project/
│   │   ├── RoyaltySettlementSystem.md # Schilling ERP system reference
│   │   ├── RoyaltyStatementValidatorPlan.md
│   │   └── documentation/             # This documentation set
│   └── royaltyBase/
│       ├── csv/                        # Sample CSV statement files
│       ├── pdf/                        # Sample PDF statement files
│       ├── json/                       # Sample JSON files
│       └── xlxs/                       # Sample Excel files
│
├── royalties/                          # Application code
│   ├── docker-compose.yml
│   ├── seed_royalty_docs.sh
│   ├── backend/
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── app/                        # FastAPI application
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── api/                    # Route handlers
│   │   │   ├── db/                     # Database config
│   │   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── schemas/                # Pydantic schemas
│   │   │   ├── services/               # Business logic
│   │   │   └── validation/             # Engine + rules
│   │   ├── tests/                      # Test suite
│   │   └── uploads/                    # File storage (Docker volume)
│   └── frontend/
│       ├── Dockerfile
│       ├── nginx.conf
│       ├── package.json
│       ├── vite.config.ts
│       └── src/                        # React application
│           ├── api.ts                  # API client
│           ├── types.ts                # TypeScript types
│           ├── components/             # Shared UI components
│           ├── pages/                  # Route pages
│           └── features/              # Feature modules
│               ├── ai-chat/           # Chat components & hooks
│               └── uploads/           # Batch upload system
│
├── README.md
├── generate_royalty_base.py            # Test data generator
└── test_*.py                           # Integration test scripts
```

---

## Useful Commands

| Command | Purpose |
|---------|---------|
| `docker compose up --build -d` | Build and start all services |
| `docker compose down` | Stop services |
| `docker compose down -v` | Stop services + delete volumes |
| `docker compose logs -f backend` | Follow backend logs |
| `docker compose exec backend bash` | Shell into backend container |
| `docker compose exec db psql -U validator` | PostgreSQL shell |
| `npm run dev` | Start frontend dev server |
| `npm run build` | Production frontend build |
| `python -m pytest tests/ -v` | Run backend tests |
| `python -m pytest tests/ --cov=app` | Tests with coverage |

---

## Troubleshooting First Setup

| Problem | Solution |
|---------|----------|
| Port 80 already in use | Stop other web servers or change the frontend port in `docker-compose.yml` |
| Port 5432 already in use | Stop local PostgreSQL or change the db port mapping |
| `OPENAI_API_KEY` not set | AI chat will fallback to Docker Model Runner; set the key for full functionality |
| Frontend shows blank page | Check `docker compose logs frontend` for build errors |
| Backend returns 500 errors | Check `docker compose logs backend` for Python tracebacks |
| Database connection refused | Ensure the `db` container is healthy: `docker compose ps` |
| Uploads fail (permission denied) | Ensure the `uploads` volume is writable in the container |
