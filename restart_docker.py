"""Restart Docker services and write status to a file."""
import subprocess
import sys
import os

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "royalties"))
status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docker_status.txt")

with open(status_file, "w") as f:
    f.write("=== Starting docker compose up --build -d ===\n")
    f.flush()

    result = subprocess.run(
        ["docker", "compose", "up", "--build", "-d"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)
    f.write(f"\n=== EXIT CODE: {result.returncode} ===\n")

    # Check container status
    ps = subprocess.run(
        ["docker", "compose", "ps"],
        capture_output=True,
        text=True,
    )
    f.write("\n=== CONTAINER STATUS ===\n")
    f.write(ps.stdout)
