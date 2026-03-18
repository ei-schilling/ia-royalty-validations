"""Run E2E auth tests and save output to a file."""
import subprocess
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
PYTHON = os.path.join(BACKEND, ".venv", "Scripts", "python.exe")
OUTPUT = os.path.join(HERE, "e2e_output.txt")

result = subprocess.run(
    [PYTHON, "-m", "pytest", os.path.join(HERE, "test_e2e_auth.py"), "-v", "--tb=short"],
    capture_output=True,
    text=True,
    cwd=BACKEND,
)

output = result.stdout + "\n" + result.stderr
with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(output)

# Also print
print(output)
sys.exit(result.returncode)
