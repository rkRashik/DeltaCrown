#!/usr/bin/env python3
"""Scan vNext modules for team.owner violations.

Usage:
    cd <project_root>
    python scripts/ops/scan_owner_violations.py
"""
import re
from pathlib import Path

# Navigate to project root (2 levels up from scripts/ops/)
project_root = Path(__file__).parent.parent.parent

# Target vNext modules only
vnext_modules = [
    'apps/organizations/services',
    'apps/organizations/views',
    'apps/organizations/api',
    'apps/competition/services',
    'apps/competition/views',
]

print('Scanning vNext modules for team.owner violations...\n')

total_violations = 0

for module_path in vnext_modules:
    module_dir = project_root / module_path
    if not module_dir.exists():
        continue
    
    py_files = list(module_dir.glob('**/*.py'))
    
    for file_path in py_files:
        violations = []
        in_docstring = False
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                stripped = line.strip()
                
                # Track docstring state
                if '"""' in stripped or "'''" in stripped:
                    in_docstring = not in_docstring
                    continue
                
                # Skip comments and docstrings
                if stripped.startswith('#') or in_docstring:
                    continue
                
                # Check for team.owner pattern in actual code
                if re.search(r'team\.owner\b', line):
                    violations.append((line_num, line.strip()[:100]))
        
        if violations:
            rel_path = file_path.relative_to(project_root)
            print(f'❌ {rel_path}')
            for ln, content in violations:
                print(f'   L{ln}: {content}')
                total_violations += 1
            print()

if total_violations == 0:
    print('✅ All vNext modules clean - no team.owner violations found')
else:
    print(f'\n❌ Total violations: {total_violations}')
