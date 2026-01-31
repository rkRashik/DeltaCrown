#!/usr/bin/env python
"""Compare field lists between old and new Team models."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.teams.models._legacy import Team as LegacyTeam
from apps.organizations.models import Team as NewTeam

print("=== LEGACY Team (_legacy.Team) ===")
legacy_fields = {f.name: f.__class__.__name__ for f in LegacyTeam._meta.get_fields()}
for name, ftype in sorted(legacy_fields.items()):
    print(f"  {name}: {ftype}")

print("\n=== NEW Team (organizations.Team) ===")
new_fields = {f.name: f.__class__.__name__ for f in NewTeam._meta.get_fields()}
for name, ftype in sorted(new_fields.items()):
    print(f"  {name}: {ftype}")

print("\n=== Fields in NEW but not in LEGACY ===")
missing_in_legacy = set(new_fields.keys()) - set(legacy_fields.keys())
for name in sorted(missing_in_legacy):
    print(f"  {name}: {new_fields[name]}")

print("\n=== Fields in LEGACY but not in NEW ===")
missing_in_new = set(legacy_fields.keys()) - set(new_fields.keys())
for name in sorted(missing_in_new):
    print(f"  {name}: {legacy_fields[name]}")
