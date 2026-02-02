import os, sys, django
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'deltacrown.settings'
django.setup()
from django.db import connection

c = connection.cursor()

# Check test_schema specifically
c.execute("""
    SELECT table_schema, column_name
    FROM information_schema.columns
    WHERE column_name = 'left_at'
    AND table_name = 'teams_teammembership'
""")

results = c.fetchall()
if results:
    for r in results:
        print(f"[FOUND] {r[0]}.teams_teammembership.{r[1]}")
else:
    print("[NOT FOUND] left_at not in any schema")

# Check if teams_teammembership exists in test_schema
c.execute("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_name = 'teams_teammembership'
""")
tables = c.fetchall()
print(f"\nteams_teammembership found in: {[t[0] for t in tables]}")
