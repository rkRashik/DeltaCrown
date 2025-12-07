import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings")
django.setup()

from django.db import connection
from apps.teams.models import TeamMembership

# Get Django model fields
model_fields = {f.name for f in TeamMembership._meta.fields}
print(f"\n Django Model Fields ({len(model_fields)}):")
for fname in sorted(model_fields):
    print(f"  {fname}")

# Get database columns
cursor = connection.cursor()
cursor.execute("""
    SELECT column_name, is_nullable, data_type, column_default 
    FROM information_schema.columns 
    WHERE table_name = 'teams_teammembership'
    ORDER BY column_name
""")

db_columns = {}
for row in cursor.fetchall():
    db_columns[row[0]] = {"nullable": row[1], "type": row[2], "default": row[3]}

print(f"\n Database Columns ({len(db_columns)}):")
for col_name in sorted(db_columns.keys()):
    info = db_columns[col_name]
    print(f"  {col_name}: {info['type']}, nullable={info['nullable']}, default={info['default']}")

# Find missing fields
missing_in_model = set(db_columns.keys()) - model_fields
print(f"\n❌ Missing in Django Model ({len(missing_in_model)}):")
for col in sorted(missing_in_model):
    info = db_columns[col]
    print(f"  {col}: {info['type']}, nullable={info['nullable']}, default={info['default']}")

missing_in_db = model_fields - set(db_columns.keys())
print(f"\n⚠️ Missing in Database ({len(missing_in_db)}):")
for field in sorted(missing_in_db):
    print(f"  {field}")
