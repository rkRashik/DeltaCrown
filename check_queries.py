#!/usr/bin/env python
"""Check query count for team detail context with stats."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test.utils import setup_test_environment
from django.db import connection, reset_queries
from apps.organizations.services.team_detail_context import get_team_detail_context
from apps.organizations.models import Team

setup_test_environment()

# Find an existing team with ranking (from tests)
team = Team.objects.filter(ranking__isnull=False).first()

if not team:
    print('❌ No teams with ranking found. Run tests first.')
    exit(1)

print(f'🔍 Testing with team: {team.slug} (has ranking: {hasattr(team, "ranking")})\n')

# Reset and count queries
reset_queries()
context = get_team_detail_context(team.slug, None)

print(f'✅ Total queries: {len(connection.queries)}')
print('\nQuery breakdown:')
for i, q in enumerate(connection.queries, 1):
    sql = q['sql']
    if 'SELECT' in sql:
        # Shorten long queries
        if len(sql) > 150:
            print(f'{i}. {sql[:150]}...')
        else:
            print(f'{i}. {sql}')

print(f'\n📊 Stats context returned:')
for key, value in context["stats"].items():
    print(f'  - {key}: {value}')
    
print(f'\n✅ Query budget status: {len(connection.queries)}/6 ({"PASS" if len(connection.queries) <= 6 else "FAIL"})')
