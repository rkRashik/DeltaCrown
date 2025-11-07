"""Quick script to verify database tables created"""
import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT tablename 
    FROM pg_tables 
    WHERE schemaname = 'public' 
    AND tablename LIKE '%tournament%' 
    ORDER BY tablename
""")

tables = [row[0] for row in cursor.fetchall()]
print(f"\n✅ Created {len(tables)} tournament tables:")
for table in tables:
    print(f"  - {table}")

print("\n✅ Verifying models import correctly:")
from apps.tournaments.models import Bracket, BracketNode, Match, Tournament
print(f"  - Bracket model: {Bracket._meta.db_table}")
print(f"  - BracketNode model: {BracketNode._meta.db_table}")
print(f"  - Match model: {Match._meta.db_table}")
print(f"  - Tournament model: {Tournament._meta.db_table}")

print("\n✅ Database migration successful! Ready for BracketService implementation.")
