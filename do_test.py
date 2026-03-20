import urllib.request, urllib.error, json, sys

# 1) Health check
try:
    req = urllib.request.Request("http://localhost:8000/api/health")
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read().decode()
        print(f"HEALTH: {resp.status} {body}")
except Exception as e:
    print(f"HEALTH ERROR: {e}")

# 2) Test validate-document with real Schilling credentials
print("\n--- Testing validate-document ---")
try:
    payload = json.dumps({
        "document_id": 22858,
        "schilling_token": "000001f4KDMB1e/0QqS0j+gIZns33g",
        "company_id": 4,
        "schilling_api_url": "https://sch-test.local.schilling.dk/ws/company4"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "http://localhost:8000/api/validations/validate-document",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"STATUS: {resp.status}")
        for line in resp:
            print(line.decode().rstrip())
            sys.stdout.flush()
except urllib.error.HTTPError as e:
    print(f"HTTP ERROR: {e.code}")
    print(e.read().decode())
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
