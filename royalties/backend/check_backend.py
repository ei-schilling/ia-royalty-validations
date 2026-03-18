"""Check backend status and test all auth endpoints."""
import subprocess
import sys
import time
import os

# First check if something is on port 8000
import socket

def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

print(f"Port 8000 in use: {port_in_use(8000)}")

# If port is in use, test it
if port_in_use(8000):
    import httpx
    client = httpx.Client(base_url="http://127.0.0.1:8000")
    
    # Check routes
    r = client.get("/openapi.json")
    routes = list(r.json()["paths"].keys())
    print(f"Routes: {routes}")
    
    if "/api/auth/register" in routes:
        print("✓ New auth endpoints present!")
        
        # Test register
        r = client.post("/api/auth/register", json={"nickname": "e2etest", "password": "testpass"})
        print(f"Register: {r.status_code} {r.json()}")
        
        # Test login
        r = client.post("/api/auth/login", json={"nickname": "e2etest", "password": "testpass"})
        print(f"Login: {r.status_code} {r.json()}")
        
        if r.status_code == 200:
            token = r.json()["access_token"]
            # Test me
            r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            print(f"Me: {r.status_code} {r.json()}")
    else:
        print("✗ Old auth endpoints — backend needs restart with new code!")
        print("  Starting fresh backend...")
        
        # The backend needs a restart. Let's do it properly.
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./dev.db"
        print("  Set DATABASE_URL for SQLite")
        print("  Please restart the backend manually or via docker compose rebuild")
else:
    print("Port 8000 not in use — backend not running")
    print("Starting backend with SQLite...")
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./dev.db"
    
    # Import and start
    sys.path.insert(0, os.path.dirname(__file__))
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
