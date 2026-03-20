import json, pathlib

data = json.loads(pathlib.Path(r"C:\Users\ei\Projects\royaltyStatementValidator\swagger_full.json").read_text())

lines = []

# Search for login/auth/token/session endpoints
keywords = ["login", "auth", "token", "session", "logon", "credential", "apikey"]
for path in sorted(data.get("paths", {})):
    if any(w in path.lower() for w in keywords):
        methods = data["paths"][path]
        for method in methods:
            if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                summary = methods[method].get("summary", methods[method].get("operationId", ""))
                lines.append(f"{method.upper():6s} {path}")
                if summary:
                    lines.append(f"       -> {summary}")
                # Show parameters
                params = methods[method].get("parameters", [])
                for p in params:
                    lines.append(f"       param: {p.get('name')} ({p.get('in')}) - {p.get('description','')[:80]}")

# Also check security definitions
if "securityDefinitions" in data:
    lines.append("\n=== Security Definitions ===")
    for name, defn in data["securityDefinitions"].items():
        lines.append(f"{name}: {json.dumps(defn)[:200]}")

if "security" in data:
    lines.append(f"\n=== Global Security ===\n{json.dumps(data['security'])[:200]}")

if not lines:
    lines.append("NO login/auth/token endpoints found in swagger!")
    # Try broader search
    lines.append("\nAll unique path prefixes:")
    prefixes = set()
    for p in data.get("paths", {}):
        parts = p.split("/")
        if len(parts) > 4:
            prefixes.add("/".join(parts[:5]))
    for pf in sorted(prefixes):
        lines.append(f"  {pf}")

pathlib.Path(r"C:\Users\ei\Projects\royaltyStatementValidator\swagger_auth.txt").write_text("\n".join(lines))
