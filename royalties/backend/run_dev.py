"""Launch dev backend with SQLite."""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./dev.db"

# Ensure we can import app
sys.path.insert(0, os.path.dirname(__file__))

import uvicorn
uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
