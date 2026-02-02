"""Verify BracketService imports"""
import django
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.services.bracket_service import BracketService

print("✅ BracketService imported successfully\n")
print("Public methods:")
methods = [m for m in dir(BracketService) if not m.startswith('_') and callable(getattr(BracketService, m))]
for method in methods:
    print(f"  - {method}()")

print(f"\nTotal: {len(methods)} public methods")
