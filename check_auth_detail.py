import json, pathlib, traceback

outfile = pathlib.Path(r"C:\Users\ei\Projects\royaltyStatementValidator\swagger_auth_detail.txt")
try:
    data = json.loads(pathlib.Path(r"C:\Users\ei\Projects\royaltyStatementValidator\swagger_full.json").read_text())
    auth_paths = [k for k in data.get("paths", {}) if "/authenticate/" in k.lower()]
    lines = []
    for path in sorted(auth_paths):
        methods = data["paths"][path]
        for method_name, method_data in methods.items():
            if method_name.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                lines.append(f"\n{'='*60}")
                lines.append(f"{method_name.upper()} {path}")
                lines.append(f"Summary: {method_data.get('summary', 'N/A')}")
                lines.append(f"OperationId: {method_data.get('operationId', 'N/A')}")
                params = method_data.get("parameters", [])
                if params:
                    lines.append("Parameters:")
                    for p in params:
                        if p.get("name"):
                            lines.append(f"  - {p['name']} ({p.get('in')}): {p.get('type', '')} {p.get('description', '')[:100]}")
                        elif p.get("schema"):
                            ref = p["schema"].get("$ref", "")
                            if ref:
                                ref_name = ref.split("/")[-1]
                                defn = data.get("definitions", {}).get(ref_name, {})
                                lines.append(f"  Body schema ({ref_name}):")
                                for pn, pd in defn.get("properties", {}).items():
                                    lines.append(f"    - {pn}: {pd.get('type', pd.get('$ref', ''))}")
                responses = method_data.get("responses", {})
                for code, resp in responses.items():
                    ref = resp.get("schema", {}).get("$ref", "")
                    lines.append(f"Response {code}: {resp.get('description', '')[:100]}")
                    if ref:
                        ref_name = ref.split("/")[-1]
                        defn = data.get("definitions", {}).get(ref_name, {})
                        props = list(defn.get("properties", {}).keys())
                        if props:
                            lines.append(f"  Schema ({ref_name}): {props}")
    outfile.write_text("\n".join(lines))
except Exception:
    outfile.write_text(traceback.format_exc())
