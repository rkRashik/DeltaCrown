"""Verify admin_bracket module"""
import django
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.admin_bracket import BracketAdmin, BracketNodeAdmin

print("✅ Admin classes imported successfully\n")
print(f"BracketAdmin:")
print(f"  - Actions: {len(BracketAdmin.actions)} ({', '.join(BracketAdmin.actions)})")
print(f"  - List display: {len(BracketAdmin.list_display)} fields")
print(f"  - List filters: {len(BracketAdmin.list_filter)} filters")
print(f"  - Inlines: {len(BracketAdmin.inlines)} inline(s)")

print(f"\nBracketNodeAdmin:")
print(f"  - List display: {len(BracketNodeAdmin.list_display)} fields")
print(f"  - List filters: {len(BracketNodeAdmin.list_filter)} filters")
print(f"  - Readonly fields: {len(BracketNodeAdmin.readonly_fields)} fields")

print("\n✅ Admin interfaces ready for Django admin!")
