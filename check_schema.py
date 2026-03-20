import json, pathlib

data = json.loads(pathlib.Path("swagger_full.json").read_text())

lines = []

# Document-related paths
doc_paths = sorted([k for k in data.get("paths", {}) if "ocument" in k])
lines.append(f"=== {len(doc_paths)} Document paths in Swagger ===")
for p in doc_paths:
    lines.append(p)

# Check what our service is using vs swagger
lines.append("\n=== Our service URLs vs Swagger ===")
our_meta = "/schilling/documentmanagement/Document/{id}"
our_download = "/schilling/documentmanagement/Document/{id}/Download"
swagger_meta = "/ws/{company}/schilling/documentmanagement/Document/{Id}"
swagger_download = "/ws/{company}/schilling/documentmanagement/Document/{Id}/Download"
lines.append(f"Our metadata:  {{base_url}}{our_meta}")
lines.append(f"Swagger meta:  {swagger_meta}")
lines.append(f"Our download:  {{base_url}}{our_download}")
lines.append(f"Swagger down:  {swagger_download}")

# Get Document schema fields
for p in doc_paths:
    if p.endswith("/{Id}"):
        get_op = data["paths"][p].get("get", {})
        resp = get_op.get("responses", {}).get("200", {})
        schema_ref = resp.get("schema", {}).get("$ref", "")
        if schema_ref:
            ref_name = schema_ref.split("/")[-1]
            defn = data.get("definitions", {}).get(ref_name, {})
            props = list(defn.get("properties", {}).keys())
            lines.append(f"\n=== Document schema fields ({ref_name}) ===")
            for f in props[:40]:
                lines.append(f"  {f}")

pathlib.Path("swagger_analysis.txt").write_text("\n".join(lines))
