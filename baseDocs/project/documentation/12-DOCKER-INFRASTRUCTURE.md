# 12 — Docker & Infrastructure

## Overview

The application runs as a multi-container Docker Compose setup with five services.

**File**: `royalties/docker-compose.yml`

---

## Services

### Frontend (`frontend`)

| Property | Value |
|----------|-------|
| **Build context** | `./frontend` |
| **Base image** | Node 22 (build) → Nginx Alpine (runtime) |
| **Port** | `80:80` |
| **Role** | Serves React SPA + proxies API requests |

**Dockerfile** (two-stage build):
```dockerfile
# Stage 1: Build
FROM node:22-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Backend (`backend`)

| Property | Value |
|----------|-------|
| **Build context** | `./backend` |
| **Base image** | Python 3.12 |
| **Port** | `8000:8000` |
| **Role** | FastAPI REST API, validation engine, AI chat |
| **Depends on** | `db` |

**Key environment variables**:
```yaml
environment:
  DATABASE_URL: postgresql+asyncpg://validator:validator@db:5432/validator
  UPLOAD_DIR: /app/uploads
  CORS_ORIGINS: '["http://localhost:5173","http://localhost"]'
  DMR_BASE: http://model-runner.docker.internal/engines/llama.cpp/v1
  OPENAI_API_KEY: ${OPENAI_API_KEY}
```

**Volumes**: `uploads:/app/uploads` (shared with AnythingLLM)

### Database (`db`)

| Property | Value |
|----------|-------|
| **Image** | `postgres:16-alpine` |
| **Port** | `5432:5432` |
| **Role** | Primary data store |

**Credentials**:
```yaml
environment:
  POSTGRES_USER: validator
  POSTGRES_PASSWORD: validator
  POSTGRES_DB: validator
```

**Volume**: `pgdata:/var/lib/postgresql/data`

### pgAdmin (`pgadmin`)

| Property | Value |
|----------|-------|
| **Image** | `dpage/pgadmin4` |
| **Port** | `5050:80` |
| **Role** | Database administration UI |

**Credentials**:
```yaml
environment:
  PGADMIN_DEFAULT_EMAIL: admin@admin.com
  PGADMIN_DEFAULT_PASSWORD: admin
```

Auto-configured with `pgadmin-servers.json` to connect to the `db` service.

### AnythingLLM (`anythingllm`)

| Property | Value |
|----------|-------|
| **Image** | `mintplexlabs/anythingllm` |
| **Port** | `3001:3001` |
| **Role** | Vector database for RAG |

**Volumes**:
- `anythingllm_storage:/app/server/storage` — Vector DB data
- `uploads:/app/server/storage/hotdir/royalty-docs:ro` — Read-only access to uploaded files for indexing

---

## Nginx Configuration

**File**: `royalties/frontend/nginx.conf`

| Location | Behavior | Cache |
|----------|----------|-------|
| `/` | SPA fallback: `try_files $uri /index.html` | `no-cache` |
| `/assets/` | Static assets (JS, CSS, images) | `1 year` (immutable hashes) |
| `/api/` | Proxy to `http://backend:8000` | None |
| `/api/chat/stream` | SSE-optimized proxy | Buffering off, 300s timeout |
| `/health` | Proxy to backend | None |

### SSE Configuration

Critical settings for Server-Sent Events to work correctly:

```nginx
location /api/chat/stream {
    proxy_pass http://backend:8000;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    chunked_transfer_encoding off;
}
```

### Upload Size Limit

```nginx
location /api/ {
    client_max_body_size 50m;
    proxy_pass http://backend:8000;
}
```

---

## Volumes

| Volume | Type | Containers | Purpose |
|--------|------|------------|---------|
| `pgdata` | Named | db | PostgreSQL data persistence |
| `uploads` | Named | backend, anythingllm | Uploaded files (shared RW/RO) |
| `anythingllm_storage` | Named | anythingllm | Vector DB and config |
| `pgadmin_data` | Named | pgadmin | pgAdmin session/config data |

---

## Networking

All services are on the default Docker Compose bridge network.

### Internal DNS

| Hostname | Service | Port |
|----------|---------|------|
| `db` | PostgreSQL | 5432 |
| `backend` | FastAPI | 8000 |
| `frontend` | Nginx | 80 |
| `anythingllm` | AnythingLLM | 3001 |
| `pgadmin` | pgAdmin | 80 (mapped to 5050) |

### External Access

| Port | Service | URL |
|------|---------|-----|
| `80` | Frontend (Nginx) | http://localhost |
| `8000` | Backend API | http://localhost:8000 |
| `5432` | PostgreSQL | `postgresql://validator:validator@localhost:5432/validator` |
| `5050` | pgAdmin | http://localhost:5050 |
| `3001` | AnythingLLM | http://localhost:3001 |

---

## Docker Model Runner

The backend can use Docker Model Runner as a fallback LLM. This is a Docker Desktop feature that runs LLMs locally.

**Connection**: `http://model-runner.docker.internal/engines/llama.cpp/v1`

This hostname is automatically available inside Docker containers when Docker Model Runner is enabled in Docker Desktop.

**Model**: `docker.io/ai/qwen2.5:3B-Q4_K_M`

---

## Common Operations

### Build and start all services
```bash
cd royalties
docker compose up --build -d
```

### Rebuild only the backend
```bash
docker compose up --build -d backend
```

### View logs
```bash
docker compose logs -f             # All services
docker compose logs -f backend     # Backend only
docker compose logs -f frontend    # Frontend only
```

### Shell into a container
```bash
docker compose exec backend bash
docker compose exec db psql -U validator
```

### Reset everything
```bash
docker compose down -v    # Stop + delete all volumes
docker compose up --build -d
```

### Check container health
```bash
docker compose ps
docker compose top
```

### Copy files into a container
```bash
docker cp local_file.py royalties-backend-1:/tmp/
docker compose exec backend python /tmp/local_file.py
```

---

## Seed Script (`seed_royalty_docs.sh`)

Seeds the AnythingLLM knowledge base with royalty reference documents:

```bash
# From the royalties/ directory
bash seed_royalty_docs.sh
```

This script:
1. Copies files from `baseDocs/royaltyBase/` into the backend container
2. The files land in `/app/uploads/royalty-knowledge-base/`
3. This path is bind-mounted into AnythingLLM's hotdir
4. AnythingLLM automatically indexes new files for RAG

---

## Production Considerations

| Concern | Current State | Recommendation |
|---------|--------------|----------------|
| **HTTPS** | Not configured | Add Let's Encrypt or terminate TLS at a reverse proxy |
| **JWT Secret** | Default value | Override `JWT_SECRET` with a strong random value |
| **Database** | Default credentials | Change `POSTGRES_USER` and `POSTGRES_PASSWORD` |
| **Volumes** | Docker volumes | Consider bind mounts to specific host directories for backups |
| **Resource limits** | None | Add `deploy.resources.limits` in docker-compose.yml |
| **Health checks** | Not configured in compose | Add `healthcheck` sections for each service |
| **Logging** | stdout | Configure log drivers (e.g., json-file with rotation) |
| **Backups** | None | Schedule `pg_dump` for database backups |
