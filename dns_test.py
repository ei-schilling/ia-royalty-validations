import socket, subprocess, pathlib

out = []
hostname = "sch-test.local.schilling.dk"

# 1. Host DNS
try:
    result = socket.getaddrinfo(hostname, 443)
    ip = result[0][4][0]
    out.append(f"HOST_DNS: {hostname} -> {ip}")
except socket.gaierror as e:
    out.append(f"HOST_DNS_FAIL: {e}")

# 2. Container DNS
try:
    r = subprocess.run(
        ["docker", "exec", "royalties-backend-1", "python", "-c",
         f"import socket; r=socket.getaddrinfo('{hostname}',443); print(r[0][4][0])"],
        capture_output=True, text=True, timeout=15
    )
    if r.returncode == 0:
        out.append(f"CONTAINER_DNS: {hostname} -> {r.stdout.strip()}")
    else:
        out.append(f"CONTAINER_DNS_FAIL: {r.stderr.strip()}")
except Exception as e:
    out.append(f"CONTAINER_DNS_ERROR: {e}")

# 3. Quick connectivity test from container
try:
    r = subprocess.run(
        ["docker", "exec", "royalties-backend-1", "python", "-c",
         "import httpx; r=httpx.get('https://sch-test.local.schilling.dk/ws/company4/schilling/documentmanagement/document/22858',headers={'X-Schilling-Token':'000001f4KDMB1e/0QqS0j+gIZns33g','X-Schilling-Language':'da','Accept':'application/json;enums=expand'},verify=False,timeout=10); print(f'HTTP {r.status_code}'); print(r.text[:200])"],
        capture_output=True, text=True, timeout=20
    )
    out.append(f"SCHILLING_TEST: {r.stdout.strip()}")
    if r.stderr.strip():
        out.append(f"SCHILLING_STDERR: {r.stderr.strip()[-200:]}")
except Exception as e:
    out.append(f"SCHILLING_TEST_ERROR: {e}")

pathlib.Path("dns_result.txt").write_text("\n".join(out))
