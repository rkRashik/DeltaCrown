"""
Quick script to check GameProfile columns in DB vs model
"""
import django
django.setup()

from django.db import connection
from apps.user_profile.models import GameProfile

print("=" * 80)
print("GameProfile Model Fields (from Django ORM):")
print("=" * 80)
for field in GameProfile._meta.get_fields():
    if hasattr(field, 'get_internal_type'):
        print(f"  {field.name:30} {field.get_internal_type():20} {'NULL' if field.null else 'NOT NULL'}")

print("\n" + "=" * 80)
print("GameProfile Database Columns (from PostgreSQL):")
print("=" * 80)
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'user_profile_gameprofile' 
        ORDER BY ordinal_position
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]:30} {row[1]:20} {row[2]}")

print("\n" + "=" * 80)
print("Checking for GP-2A structured identity columns:")
print("=" * 80)
required_columns = ['ign', 'discriminator', 'platform', 'region']
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns 
        WHERE table_name = 'user_profile_gameprofile'
    """)
    existing_columns = {row[0] for row in cursor.fetchall()}
    
for col in required_columns:
    status = "✅ EXISTS" if col in existing_columns else "❌ MISSING"
    print(f"  {col:20} {status}")
