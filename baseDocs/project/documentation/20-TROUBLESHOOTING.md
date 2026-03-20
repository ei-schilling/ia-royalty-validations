# 20 — Troubleshooting

## Common Issues

### Docker & Containers

#### Port 80 already in use
**Symptom**: Frontend container fails to start
**Fix**: Stop other web servers (IIS, Apache, nginx) or change the port:
```yaml
# docker-compose.yml
frontend:
  ports:
    - "3000:80"  # Changed from 80:80
```

#### Port 5432 already in use
**Symptom**: Database container fails to start
**Fix**: Stop local PostgreSQL or change the port mapping:
```yaml
db:
  ports:
    - "5433:5432"
```
Remember to update `DATABASE_URL` accordingly.

#### Backend keeps restarting
**Symptom**: `docker compose ps` shows backend in restart loop
**Fix**: Check logs for the actual error:
```bash
docker compose logs backend --tail 50
```
Common causes:
- Database not ready (wait a few seconds)
- Missing Python dependencies
- Syntax errors in code

#### "no space left on device" during build
**Fix**: Clean up Docker resources:
```bash
docker system prune -a
docker volume prune
```

#### AnythingLLM not connecting
**Fix**: Ensure the container is running and healthy:
```bash
docker compose logs anythingllm
```
The AnythingLLM API key is hardcoded — no key configuration needed.

---

### Backend

#### 500 Internal Server Error on any endpoint
**Diagnosis**:
```bash
docker compose logs backend --tail 100
```
**Common causes**:
- Database connection failed (check `db` container)
- File permission error on `uploads/` directory
- Missing environment variable

#### "Table already exists" warning on startup
**This is normal.** `create_all()` is idempotent — it skips existing tables.

#### File upload returns 400 "Unsupported file type"
**Check**: Verify the file extension is in `ALLOWED_EXTENSIONS` (default: `csv,xlsx,json,pdf,zip,tar,gz,rar`).

#### PDF parsing returns empty data
**Cause**: The PDF parser is Schilling-specific. Generic PDFs may not match the expected layout.
**Fix**: Ensure the PDF follows the Schilling "Royalty afregning" format.

#### Amount consistency warnings on valid data
**Cause**: The tolerance may be too tight for your data.
**Fix**: Increase `AMOUNT_TOLERANCE` (default: `0.01`):
```bash
export AMOUNT_TOLERANCE=0.05
```

#### Chat returns "No LLM available"
**Cause**: Neither OpenAI nor Docker Model Runner is accessible.
**Fix**:
1. Set `OPENAI_API_KEY` in environment
2. Or enable Docker Model Runner in Docker Desktop settings

---

### Frontend

#### Blank page after deployment
**Diagnosis**: Open browser DevTools → Console tab.
**Common causes**:
- JavaScript build error (check `docker compose logs frontend`)
- API proxy not configured (Nginx not routing `/api/` correctly)
- Missing `index.html` in the built output

#### Login fails with "Failed to fetch"
**Cause**: Backend is unreachable.
**Fix**:
1. Check backend is running: `docker compose ps`
2. Check Nginx proxy config in `nginx.conf`
3. Check CORS settings: `CORS_ORIGINS` must include the frontend origin

#### Chat messages not streaming (stuck on loading)
**Cause**: SSE not reaching the frontend.
**Fix**:
1. Check Nginx SSE config (buffering must be off):
```nginx
proxy_buffering off;
proxy_cache off;
```
2. Check backend logs for chat endpoint errors
3. Verify LLM configuration (OpenAI key or Docker Model Runner)

#### File upload progress stuck
**Cause**: SSE connection for batch progress may be blocked.
**Fix**:
1. Check browser DevTools → Network → EventSource connection
2. Verify the token is being passed as query parameter
3. Check backend logs for batch processing errors

#### Theme not persisting after refresh
**Fix**: Clear `localStorage` and re-select theme:
```javascript
localStorage.removeItem('rv-theme')
```

#### "TypeError: Failed to construct 'URL'" on PDF preview
**Cause**: Upload ID or file URL is invalid.
**Fix**: Check that the validation was run successfully and the upload still exists.

---

### Database

#### Can't connect to PostgreSQL
**From host machine**:
```bash
psql -h localhost -U validator -d validator -p 5432
# Password: validator
```

**From another container**:
```bash
docker compose exec db psql -U validator -d validator
```

#### Reset the database completely
```bash
docker compose down -v
docker compose up -d db
# Wait 5 seconds for PostgreSQL to initialize
docker compose up -d backend
```

#### View database contents
**Option 1: pgAdmin** — http://localhost:5050 (admin@admin.com / admin)
**Option 2: psql**:
```bash
docker compose exec db psql -U validator -d validator
\dt              -- List tables
SELECT * FROM users;
SELECT * FROM uploads ORDER BY uploaded_at DESC LIMIT 10;
SELECT * FROM validation_runs ORDER BY started_at DESC LIMIT 10;
SELECT COUNT(*) FROM validation_issues;
```

---

### Testing

#### Tests fail with "no module named app"
**Fix**: Install the package in development mode:
```bash
cd royalties/backend
pip install -e ".[dev]"
```

#### Tests fail with database errors
**Fix**: Tests should use in-memory SQLite. Check that `conftest.py` overrides the database URL:
```python
DATABASE_URL = "sqlite+aiosqlite://"
```

#### Tests pass locally but fail in CI
**Common causes**:
- Missing dev dependencies
- Different Python version
- File path differences (Windows vs Linux)

---

## Useful Debug Commands

### Check service status
```bash
docker compose ps
docker compose top
```

### Follow all logs
```bash
docker compose logs -f
```

### Shell into containers
```bash
docker compose exec backend bash
docker compose exec frontend sh
docker compose exec db bash
```

### Check backend health
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### Test API manually
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"nickname":"test","password":"test123"}'

# Upload a file
curl -X POST http://localhost:8000/api/uploads/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@path/to/statement.csv"
```

### Check resource usage
```bash
docker stats
```

---

## FAQ

**Q: Can I use MySQL instead of PostgreSQL?**
A: Not without changes. The application uses PostgreSQL-specific features via `asyncpg`. SQLite is supported for development/testing only.

**Q: Can I run without Docker?**
A: Yes. See the "Local Development" section in [03-GETTING-STARTED.md](./03-GETTING-STARTED.md). You'll need Python 3.12+ and Node.js 22+.

**Q: How do I add a new file format?**
A: Add a parser function in `backend/app/validation/parser.py` for your format, add the extension to `ALLOWED_EXTENSIONS`, and add tests.

**Q: How do I change the AI model?**
A: Modify the `OPENAI_MODEL` constant in `backend/app/api/chat.py`. Any OpenAI-compatible model should work.

**Q: Can I use this with non-Schilling royalty statements?**
A: The CSV, Excel, and JSON parsers work with any tabular data. The PDF parser is Schilling-specific. Some validation rules check for Schilling-specific field names and transaction types.

**Q: How do I backup the database?**
A:
```bash
docker compose exec db pg_dump -U validator validator > backup.sql
```

**Q: How do I restore a database backup?**
A:
```bash
docker compose exec -T db psql -U validator validator < backup.sql
```
