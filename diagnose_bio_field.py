import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.user_profile.models import UserProfile
from django.db import connection

print("="*80)
print("DJANGO MODEL FIELDS CHECK")
print("="*80)

# Check what fields Django thinks UserProfile has
print("\nDjango ORM sees these fields in UserProfile:")
from django.db.models import NOT_PROVIDED
for field in UserProfile._meta.get_fields():
    if hasattr(field, 'column'):
        print(f"  Field: {field.name:30} -> Column: {field.column:30} Type: {field.get_internal_type()}")
        if hasattr(field, 'default') and field.default != NOT_PROVIDED:
            print(f"       Default: {repr(field.default)}")
    elif hasattr(field, 'name'):
        print(f"  Field: {field.name:30} (relation)")

print("\n" + "="*80)
print("CHECK FOR BIO/ABOUT_BIO FIELDS")
print("="*80)

bio_fields = [f for f in UserProfile._meta.get_fields() if 'bio' in f.name.lower() or 'about' in f.name.lower()]
print(f"\nFound {len(bio_fields)} fields with 'bio' or 'about' in name:")
from django.db.models import NOT_PROVIDED
for field in bio_fields:
    print(f"  - {field.name}")
    if hasattr(field, 'column'):
        print(f"    Column: {field.column}")
        print(f"    Type: {field.get_internal_type()}")
        print(f"    Null: {field.null}")
        print(f"    Blank: {field.blank}")
        if hasattr(field, 'default'):
            print(f"    Default: {repr(field.default) if field.default != NOT_PROVIDED else 'NOT_PROVIDED'}")

print("\n" + "="*80)
print("DATABASE COLUMNS CHECK")
print("="*80)

cursor = connection.cursor()
cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'user_profile_userprofile'
    AND (column_name LIKE '%bio%' OR column_name LIKE '%about%')
    ORDER BY column_name
""")

db_cols = cursor.fetchall()
print(f"\nDatabase has {len(db_cols)} columns with 'bio' or 'about' in name:")
for col in db_cols:
    print(f"  - {col[0]}")
    print(f"    Type: {col[1]}")
    print(f"    Nullable: {col[2]}")
    print(f"    Default: {col[3]}")

print("\n" + "="*80)
print("MISMATCH CHECK")
print("="*80)

# Check for mismatches
field_names = {f.column for f in UserProfile._meta.get_fields() if hasattr(f, 'column')}
db_col_names = {col[0] for col in cursor.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'user_profile_userprofile'
""").fetchall()}

print(f"\nFields in model but not in database:")
for name in field_names - db_col_names:
    print(f"  - {name}")

print(f"\nColumns in database but not in model:")
for name in db_col_names - field_names:
    if name not in ['id']:  # Skip auto fields
        print(f"  - {name}")
