"""Start dev backend and run E2E auth checks."""
import os, sys, time, socket, subprocess, threading

BACKEND_DIR = r"C:\Users\ei\Projects\royaltyStatementValidator\royalties\backend"
PYTHON = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
RESULTS_FILE = os.path.join(BACKEND_DIR, "e2e_results.txt")

def port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0

results = []
def log(msg):
    results.append(msg)
    print(msg)

# Check if old server is on 8000
if port_open(8000):
    log("Port 8000 is already in use — checking if it has new routes...")
    import httpx
    try:
        r = httpx.get("http://127.0.0.1:8000/openapi.json", timeout=5)
        routes = list(r.json()["paths"].keys())
        if "/api/auth/register" in routes:
            log("Backend already has new auth endpoints!")
        else:
            log(f"Backend has OLD routes: {routes}")
            log("Need to restart backend. Trying to kill port 8000...")
            # Try to kill it
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", 
                 "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | "
                 "Where-Object {$_.OwningProcess -ne 0 -and $_.OwningProcess -ne 4} | "
                 "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"],
                timeout=10
            )
            time.sleep(3)
            if port_open(8000):
                log("ERROR: Could not free port 8000!")
                log("Please manually stop Docker or any process on port 8000")
            else:
                log("Port 8000 freed!")
    except Exception as e:
        log(f"Error checking backend: {e}")

# Start backend if port is free
if not port_open(8000):
    log("Starting backend on port 8000 with SQLite...")
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite+aiosqlite:///./dev.db"
    proc = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    
    # Wait for startup
    for i in range(20):
        time.sleep(1)
        if port_open(8000):
            log(f"Backend started after {i+1}s")
            break
    else:
        out = proc.stdout.read(2000).decode() if proc.stdout else ""
        log(f"ERROR: Backend didn't start in 20s. Output: {out}")
        with open(RESULTS_FILE, "w") as f:
            f.write("\n".join(results))
        sys.exit(1)

# Now test
import httpx
client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=10)

# Verify routes
r = client.get("/openapi.json")
routes = list(r.json()["paths"].keys())
log(f"Routes: {routes}")

# Test register
log("\n--- Testing Register ---")
r = client.post("/api/auth/register", json={"nickname": "e2e_user", "password": "testpass123"})
log(f"Register: {r.status_code} -> {r.text[:200]}")

if r.status_code == 201:
    token = r.json()["access_token"]
    user = r.json()["user"]
    log(f"  Token received: {token[:20]}...")
    log(f"  User: {user}")
    
    # Test login
    log("\n--- Testing Login ---")
    r = client.post("/api/auth/login", json={"nickname": "e2e_user", "password": "testpass123"})
    log(f"Login: {r.status_code} -> {r.text[:200]}")
    
    # Test wrong password
    r = client.post("/api/auth/login", json={"nickname": "e2e_user", "password": "wrongpass"})
    log(f"Login wrong pw: {r.status_code} (expected 401)")
    
    # Test /me
    log("\n--- Testing /me ---")
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    log(f"Me: {r.status_code} -> {r.text[:200]}")
    
    # Test /me without token
    r = client.get("/api/auth/me")
    log(f"Me no token: {r.status_code} (expected 401)")
    
    # Test protected upload endpoint without token
    log("\n--- Testing Protected Upload ---")
    r = client.post("/api/uploads/", files={"file": ("test.csv", b"a,b\n1,2")})
    log(f"Upload no token: {r.status_code} (expected 401)")
    
    # Test duplicate register
    log("\n--- Testing Duplicate Register ---")
    r = client.post("/api/auth/register", json={"nickname": "e2e_user", "password": "other"})
    log(f"Duplicate register: {r.status_code} (expected 409)")
else:
    log(f"ERROR: Register failed! Response: {r.text}")

log("\n--- DONE ---")
with open(RESULTS_FILE, "w") as f:
    f.write("\n".join(results))
