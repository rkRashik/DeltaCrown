"""Quick script to analyze test run results."""
import sys
from collections import Counter

filename = sys.argv[1] if len(sys.argv) > 1 else 'test_results13.txt'

fails = Counter()
errors = Counter()
with open(filename) as f:
    for line in f:
        line = line.strip()
        if line.startswith('FAILED '):
            path = line[7:].rsplit('::', 1)[0]
            fails[path] += 1
        elif line.startswith('ERROR '):
            path = line[6:].rsplit('::', 1)[0]
            errors[path] += 1

print('=== TOP 25 FAILING ===')
for path, count in fails.most_common(25):
    print(f'{count:3d}  {path}')
print(f'Total: {len(fails)} files, {sum(fails.values())} F')
print()
print('=== TOP 15 ERRORS ===')
for path, count in errors.most_common(15):
    print(f'{count:3d}  {path}')
print(f'Total: {len(errors)} files, {sum(errors.values())} E')
