"""
Query count verification for Tier-1 wiring.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test.utils import setup_test_environment
from django.db import connection, reset_queries
from django.conf import settings

# Enable query tracking
setup_test_environment()
settings.DEBUG = True

from apps.organizations.models import Team
from apps.accounts.models import User
from apps.organizations.services.team_detail_context import get_team_detail_context
from django.core.cache import cache

# Clear cache to force game lookup
cache.clear()

# Get test data
user = User.objects.first()
team = Team.objects.first()

if not team:
    print("No teams found. Please create a team first.")
    exit(1)

print(f"Testing with team: {team.slug}")
print(f"Viewer: {user.username if user else 'Anonymous'}")
print()

# Test query count without cache
reset_queries()
context = get_team_detail_context(team_slug=team.slug, viewer=user)
query_count = len(connection.queries)

print(f"✅ Query Count (without game cache): {query_count}")
print(f"   Target: ≤3 queries for Tier-1")
print()

# Show game context
game_ctx = context['team']['game']
print("Game Context:")
print(f"  - ID: {game_ctx.get('id')}")
print(f"  - Name: {game_ctx.get('name')}")
print(f"  - Slug: {game_ctx.get('slug')}")
print(f"  - Logo: {game_ctx.get('logo_url')}")
print(f"  - Color: {game_ctx.get('primary_color')}")
print()

# Test with cache
reset_queries()
context2 = get_team_detail_context(team_slug=team.slug, viewer=user)
query_count_cached = len(connection.queries)

print(f"✅ Query Count (with game cache): {query_count_cached}")
print(f"   Target: ≤2 queries (game cached)")
print()

# Show queries
print("Queries executed (first call):")
for i, q in enumerate(connection.queries[:5], 1):
    sql = q['sql'][:100] + '...' if len(q['sql']) > 100 else q['sql']
    print(f"  {i}. {sql}")
print()

if query_count <= 3:
    print("✅ PASSED: Query count within Tier-1 budget")
else:
    print(f"❌ FAILED: Query count {query_count} exceeds budget of 3")
