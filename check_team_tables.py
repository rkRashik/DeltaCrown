import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT tablename 
    FROM pg_tables 
    WHERE schemaname='public' AND tablename LIKE '%team%' 
    ORDER BY tablename
""")

print("=== TEAM-RELATED TABLES IN DATABASE ===")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

# Also check the Team model's expected table
from apps.organizations.models import Team as VNextTeam
print(f"\n=== VNEXT TEAM MODEL EXPECTS ===")
print(f"  db_table: {VNextTeam._meta.db_table}")
print(f"  Model: {VNextTeam.__module__}.{VNextTeam.__name__}")

# Check if table exists
cursor.execute("""
    SELECT EXISTS (
        SELECT FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename = %s
    )
""", [VNextTeam._meta.db_table])
exists = cursor.fetchone()[0]
print(f"  Table exists: {exists}")

# Also check legacy Team
try:
    from apps.teams.models import Team as LegacyTeam
    print(f"\n=== LEGACY TEAM MODEL ===")
    print(f"  db_table: {LegacyTeam._meta.db_table}")
    print(f"  Model: {LegacyTeam.__module__}.{LegacyTeam.__name__}")
    
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename = %s
        )
    """, [LegacyTeam._meta.db_table])
    exists = cursor.fetchone()[0]
    print(f"  Table exists: {exists}")
except ImportError:
    print("\n=== LEGACY TEAM MODEL ===")
    print("  Not found (apps.teams.models.Team)")
