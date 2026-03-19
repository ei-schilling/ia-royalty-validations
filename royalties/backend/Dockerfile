# --- Build stage ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir build

# Copy project files
COPY pyproject.toml .
COPY app/ app/

# Install runtime dependencies
RUN pip install --no-cache-dir --target=/app/deps .

# --- Runtime stage ---
FROM python:3.12-slim

WORKDIR /app

# Install system tools for archive extraction
RUN apt-get update && apt-get install -y --no-install-recommends unrar-free && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r validator && useradd -r -g validator validator

# Copy installed deps and application code
COPY --from=builder /app/deps /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/app /app/app

# Create upload directory
RUN mkdir -p /app/uploads && chown -R validator:validator /app

USER validator

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
