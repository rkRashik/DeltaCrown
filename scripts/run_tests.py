"""Run pytest in a clean subprocess and write results to file."""
import subprocess
import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_FILE = os.path.join(BASE_DIR, 'test_results.txt')

try:
    os.environ['DATABASE_URL_TEST'] = 'postgresql://dcadmin:dcpass123@localhost:5432/deltacrown_test'

    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-W', 'ignore', '--no-header', '--tb=short', '-q',
         '-p', 'no:warnings', '--create-db', 'tests/tournaments/'],
        capture_output=True,
        text=True,
        timeout=1800,
        cwd=BASE_DIR
    )

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        lines = result.stdout.strip().split('\n')
        f.write(f"RETURN_CODE={result.returncode}\n")
        f.write(f"TOTAL_LINES={len(lines)}\n\n")
        # All output (clean, no-header, tb=line, q mode is compact)
        for line in lines:
            f.write(line + '\n')
        if result.stderr:
            stderr_lines = result.stderr.strip().split('\n')
            f.write(f"\n=== STDERR (last 20) ===\n")
            for line in stderr_lines[-20:]:
                f.write(line + '\n')

except Exception as e:
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"EXCEPTION: {e}\n")
        f.write(traceback.format_exc())

print(f"Done. Results in {OUT_FILE}")
