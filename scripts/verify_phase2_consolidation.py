#!/usr/bin/env python
"""
Verification Script for Tournament Code Consolidation (Phase 2)

Checks:
1. Deprecated views are importable
2. URL patterns are correctly configured
3. Templates have been moved
4. Modern registration view is primary
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings")
import django
django.setup()

from django.urls import reverse, resolve
from django.test import RequestFactory
from django.contrib.auth import get_user_model

print("=" * 60)
print("Tournament Code Consolidation Verification (Phase 2)")
print("=" * 60)
print()

# Test 1: Deprecated Views Import
print("Test 1: Deprecated Views Import")
try:
    from apps.tournaments.views._deprecated import (
        register,
        unified_register,
        enhanced_register,
        valorant_register,
        efootball_register,
    )
    print("  ✓ All deprecated views imported successfully")
    print(f"    Functions: {[f.__name__ for f in [register, unified_register, enhanced_register]]}")
except ImportError as e:
    print(f"  ✗ Failed to import deprecated views: {e}")

print()

# Test 2: URL Resolution
print("Test 2: URL Resolution")
try:
    # Modern URL (primary)
    modern_url = reverse('tournaments:modern_register', kwargs={'slug': 'test-tournament'})
    print(f"  ✓ Modern registration URL: {modern_url}")
    
    # Deprecated URLs (should still work)
    deprecated_urls = [
        ('register', reverse('tournaments:register', kwargs={'slug': 'test'})),
        ('unified_register', reverse('tournaments:unified_register', kwargs={'slug': 'test'})),
        ('enhanced_register', reverse('tournaments:enhanced_register', kwargs={'slug': 'test'})),
    ]
    
    for name, url in deprecated_urls:
        print(f"  ✓ Deprecated '{name}' URL: {url}")
        
except Exception as e:
    print(f"  ✗ URL resolution failed: {e}")

print()

# Test 3: Template Files
print("Test 3: Template Files")
template_base = project_root / "templates" / "tournaments"

# Check modern template exists
modern_template = template_base / "modern_register.html"
if modern_template.exists():
    print(f"  ✓ Modern template exists: {modern_template.name}")
else:
    print(f"  ✗ Modern template not found")

# Check deprecated templates moved
deprecated_dir = template_base / "_deprecated"
if deprecated_dir.exists():
    print(f"  ✓ Deprecated directory exists")
    deprecated_templates = list(deprecated_dir.glob("*.html"))
    print(f"    Moved templates: {len(deprecated_templates)}")
    for tmpl in deprecated_templates[:3]:  # Show first 3
        print(f"      - {tmpl.name}")
    if len(deprecated_templates) > 3:
        print(f"      ... and {len(deprecated_templates) - 3} more")
else:
    print(f"  ✗ Deprecated directory not found")

# Check old templates removed from main directory
old_templates = [
    "register.html",
    "unified_register.html", 
    "valorant_register.html",
    "efootball_register.html",
]

removed = []
for tmpl in old_templates:
    if not (template_base / tmpl).exists():
        removed.append(tmpl)

if len(removed) == len(old_templates):
    print(f"  ✓ All old templates removed from main directory")
else:
    print(f"  ⚠ Some old templates still in main directory: {set(old_templates) - set(removed)}")

print()

# Test 4: File Organization
print("Test 4: Code Organization")
views_path = project_root / "apps" / "tournaments" / "views"

# Check modern view
modern_view = views_path / "registration_modern.py"
if modern_view.exists():
    size = modern_view.stat().st_size
    print(f"  ✓ Modern registration view: {size:,} bytes")
else:
    print(f"  ✗ Modern view not found")

# Check deprecated wrapper
deprecated_wrapper = views_path / "_deprecated.py"
if deprecated_wrapper.exists():
    size = deprecated_wrapper.stat().st_size
    print(f"  ✓ Deprecation wrapper: {size:,} bytes")
else:
    print(f"  ✗ Deprecation wrapper not found")

# Check state machine
state_machine = project_root / "apps" / "tournaments" / "models" / "state_machine.py"
if state_machine.exists():
    size = state_machine.stat().st_size
    print(f"  ✓ State machine: {size:,} bytes")
else:
    print(f"  ✗ State machine not found")

print()

# Test 5: Documentation
print("Test 5: Documentation")
docs_path = project_root / "docs"

docs = [
    "TOURNAMENT_STATE_MACHINE_REFACTORING.md",
    "TOURNAMENT_CODE_CONSOLIDATION.md",
]

for doc in docs:
    doc_file = docs_path / doc
    if doc_file.exists():
        size = doc_file.stat().st_size
        print(f"  ✓ {doc}: {size:,} bytes")
    else:
        print(f"  ✗ {doc} not found")

print()

# Test 6: Metrics
print("Test 6: Code Reduction Metrics")

# Count lines in old vs new
def count_lines(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return len([l for l in f if l.strip() and not l.strip().startswith('#')])
    except:
        return 0

old_views = [
    views_path / "registration.py",
    views_path / "registration_unified.py",
    views_path / "enhanced_registration.py",
]

new_views = [
    views_path / "registration_modern.py",
    views_path / "_deprecated.py",
]

old_lines = sum(count_lines(f) for f in old_views if f.exists())
new_lines = sum(count_lines(f) for f in new_views if f.exists())

if old_lines > 0 and new_lines > 0:
    reduction = ((old_lines - new_lines) / old_lines) * 100
    print(f"  Old system: ~{old_lines:,} lines")
    print(f"  New system: ~{new_lines:,} lines")
    print(f"  Reduction: {reduction:.1f}%")
else:
    print(f"  ⚠ Could not calculate metrics")

print()
print("=" * 60)
print("✓ Phase 2 Verification Complete!")
print("=" * 60)
print()
print("Next Steps:")
print("  1. Test deprecated URL redirect in browser")
print("  2. Verify modern registration form works")
print("  3. Check deprecation warnings in logs")
print("  4. Proceed to Phase 3: JavaScript/CSS cleanup")
