#!/usr/bin/env python3
"""Repo Hygiene Guard - Enforce file placement rules.

Usage:
    python scripts/ops/check_repo_hygiene.py

Exits with code 1 if violations found.
"""
import sys
from pathlib import Path

# Navigate to project root (2 levels up from scripts/ops/)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Allowed root files (baseline + standard project files)
ALLOWED_ROOT_FILES = {
    # Python project standard
    'manage.py',
    'pyproject.toml',
    'pytest.ini',
    'Makefile',
    'schema.yml',
    
    # Documentation standard
    'README.md',
    'README_TECHNICAL.md',
    
    # Configuration standard
    '.env',
    '.env.example',
    '.env.test.template',
    '.flake8',
    '.gitignore',
    '.gitleaks.toml',
    '.pre-commit-config.yaml',
    
    # Docker
    'Dockerfile',
    'docker-compose.yml',
    'docker-compose.staging.yml',
    'docker-compose.test.yml',
}

# File patterns that should NOT be in root
FORBIDDEN_ROOT_PATTERNS = [
    ('*.md', 'Markdown docs (except README*.md)'),
    ('test_*.py', 'Test files'),
    ('*_test.py', 'Test files'),
    ('scan_*.py', 'Scanning scripts'),
    ('check_*.py', 'Check scripts'),
    ('fix_*.py', 'Fix scripts'),
    ('add_*.py', 'Addition scripts'),
    ('delete_*.py', 'Deletion scripts'),
    ('create_*.py', 'Creation scripts'),
    ('drop_*.py', 'Drop scripts'),
    ('list_*.py', 'List scripts'),
    ('verify_*.py', 'Verification scripts'),
    ('validate_*.py', 'Validation scripts'),
    ('reset_*.py', 'Reset scripts'),
    ('show_*.py', 'Show scripts'),
    ('compare_*.py', 'Comparison scripts'),
    ('*.sql', 'SQL files'),
    ('*.sqlite3', 'SQLite databases'),
    ('*.db', 'Database files'),
]

def check_root_hygiene():
    """Check for unauthorized files in project root."""
    violations = []
    
    # Get all files in root (not directories)
    root_files = [f for f in PROJECT_ROOT.iterdir() if f.is_file() and not f.name.startswith('.')]
    
    for file_path in root_files:
        filename = file_path.name
        
        # Check if allowed
        if filename in ALLOWED_ROOT_FILES:
            continue
        
        # Check forbidden patterns
        for pattern, description in FORBIDDEN_ROOT_PATTERNS:
            from fnmatch import fnmatch
            if fnmatch(filename, pattern):
                violations.append({
                    'file': filename,
                    'reason': description,
                    'suggest': get_suggested_location(filename)
                })
                break
        else:
            # File doesn't match allowed or forbidden - flag for review
            if not filename.startswith('.'):  # Ignore hidden files
                violations.append({
                    'file': filename,
                    'reason': 'Not in allowed root files list',
                    'suggest': 'Review and add to allowed list or move'
                })
    
    return violations

def get_suggested_location(filename):
    """Suggest proper location for misplaced file."""
    if filename.endswith('.md'):
        if 'PHASE' in filename or 'TRACKER' in filename or 'VNEXT' in filename:
            return 'docs/vnext/'
        elif 'OPS' in filename or 'ERADICATION' in filename or 'FIX' in filename:
            return 'docs/ops/'
        else:
            return 'docs/'
    
    if filename.startswith('test_') or filename.endswith('_test.py'):
        return 'tests/'
    
    if any(prefix in filename.lower() for prefix in ['scan', 'check', 'fix', 'add', 'delete', 'create', 'drop', 'list', 'verify', 'validate', 'reset', 'show', 'compare']):
        return 'scripts/ops/'
    
    if filename.endswith('.sql'):
        return 'scripts/ops/ or docs/ops/'
    
    if filename.endswith(('.sqlite3', '.db')):
        return 'DELETE (test artifacts)'
    
    return 'docs/ or scripts/ops/'

def main():
    """Main entry point."""
    print("🔍 Checking repo hygiene...\n")
    
    violations = check_root_hygiene()
    
    if not violations:
        print("✅ Root folder clean - no hygiene violations found")
        return 0
    
    print(f"❌ Found {len(violations)} hygiene violation(s):\n")
    
    for v in violations:
        print(f"  File: {v['file']}")
        print(f"  Reason: {v['reason']}")
        print(f"  Suggested location: {v['suggest']}")
        print()
    
    print("---")
    print("Repo Hygiene Rules:")
    print("  • Documentation: docs/vnext/, docs/ops/")
    print("  • Tests: tests/")
    print("  • Scripts: scripts/ops/")
    print("  • Only standard project files allowed in root")
    print()
    print("Fix violations by moving files to proper locations.")
    
    return 1

if __name__ == '__main__':
    sys.exit(main())
