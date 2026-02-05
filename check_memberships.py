#!/usr/bin/env python
"""Check current team memberships."""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.organizations.models import TeamMembership, Team
from django.contrib.auth import get_user_model

User = get_user_model()

print("Current TeamMemberships:")
print("-" * 100)
print(f"{'ID':<6} {'User':<20} {'Team':<30} {'Game':<8} {'Org':<8} {'Status':<10}")
print("-" * 100)

for membership in TeamMembership.objects.select_related('team', 'user').all()[:20]:
    print(f"{membership.id:<6} {membership.user.username:<20} {membership.team.name[:28]:<30} {membership.game_id:<8} {membership.organization_id or 'None':<8} {membership.status:<10}")

print(f"\nTotal: {TeamMembership.objects.count()} memberships")
print(f"Active: {TeamMembership.objects.filter(status='ACTIVE').count()}")
print(f"Independent teams (org_id=None): {TeamMembership.objects.filter(organization_id__isnull=True).count()}")
print(f"Org teams: {TeamMembership.objects.filter(organization_id__isnull=False).count()}")
