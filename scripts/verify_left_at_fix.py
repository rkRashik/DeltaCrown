"""Verify left_at column fix by testing TeamMembership queries."""
import django
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.teams.models import TeamMembership
from django.db import connection

print("=" * 70)
print("VERIFYING teams_teammembership.left_at FIX")
print("=" * 70)

# Test 1: Column exists in schema
cursor = connection.cursor()
cursor.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'teams_teammembership'
    AND column_name = 'left_at'
""")
result = cursor.fetchone()
if result:
    print(f"✓ Column exists: {result[0]} ({result[1]}, nullable={result[2]})")
else:
    print("✗ Column missing")
    sys.exit(1)

# Test 2: ORM can access the field
try:
    # This will fail if column doesn't exist
    count = TeamMembership.objects.filter(left_at__isnull=True).count()
    print(f"✓ ORM query successful: {count} memberships with left_at=NULL")
except Exception as e:
    print(f"✗ ORM query failed: {e}")
    sys.exit(1)

# Test 3: Index exists
cursor.execute("""
    SELECT indexname
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename = 'teams_teammembership'
    AND indexname = 'teams_member_left_at_idx'
""")
result = cursor.fetchone()
if result:
    print(f"✓ Index exists: {result[0]}")
else:
    print("✗ Index missing (non-critical)")

print("\n" + "=" * 70)
print("VERIFICATION: PASS")
print("=" * 70)
