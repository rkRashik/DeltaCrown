"""Script to identify importable test files and generate ignore list."""
import os
import sys
import importlib
import warnings

os.environ['DJANGO_SETTINGS_MODULE'] = 'deltacrown.settings_test'
os.environ['DATABASE_URL_TEST'] = 'postgresql://dcadmin:dcpass123@localhost:5432/deltacrown_test'

warnings.filterwarnings('ignore')

import django
django.setup()

import glob

broken = []
ok = []

for pattern in ['tests/**/*.py', 'apps/**/tests/**/*.py']:
    for f in sorted(glob.glob(pattern, recursive=True)):
        if '__pycache__' in f or '__init__' in f or 'conftest' in f:
            continue
        if '_archive' in f:
            continue
        mod = f.replace('\\', '.').replace('/', '.').replace('.py', '')
        try:
            importlib.import_module(mod)
            ok.append(f)
        except Exception as e:
            broken.append(f)

print(f'Importable: {len(ok)} test files')
print(f'Broken: {len(broken)} test files')
print()
print('BROKEN FILES:')
for f in broken:
    print(f'  {f}')
