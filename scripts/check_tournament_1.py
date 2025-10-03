#!/usr/bin/env python
"""Quick check of tournament ID 1."""
import os, sys, django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament

try:
    t = Tournament.objects.get(id=1)
    print(f"Tournament ID 1: {t.name}")
    print(f"Status: {t.status}")
    print(f"Slug: {t.slug}")
    print(f"\nAll fields:")
    for f in t._meta.fields:
        print(f"  - {f.name}: {getattr(t, f.name, 'N/A')}")
except Tournament.DoesNotExist:
    print("Tournament ID 1 does not exist")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
