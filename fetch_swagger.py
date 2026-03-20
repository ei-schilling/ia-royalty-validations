"""Fetch Schilling swagger.json and extract document management endpoints."""
import urllib.request, ssl, json, pathlib

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://sch-test.local.schilling.dk/docs/swagger.json"
print(f"Fetching {url} ...")
req = urllib.request.Request(url)
with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
    data = json.loads(resp.read().decode())

# Save full swagger for reference
pathlib.Path("swagger_full.json").write_text(json.dumps(data, indent=2))

# Extract document management paths
dm_paths = {k: v for k, v in data.get("paths", {}).items() if "document" in k.lower()}
print(f"\nFound {len(dm_paths)} document-related paths:\n")
for path, methods in sorted(dm_paths.items()):
    for method in methods:
        if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            summary = methods[method].get("summary", methods[method].get("operationId", ""))
            print(f"  {method.upper():6s} {path}")
            if summary:
                print(f"         -> {summary}")
