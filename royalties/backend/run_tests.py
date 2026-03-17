"""Run all tests and write results to a file."""
import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "--tb=short", "--no-header", "-q"],
    capture_output=True,
    text=True,
)

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results.txt")
with open(output_path, "w") as f:
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)
    f.write(f"\n=== EXIT CODE: {result.returncode} ===\n")
