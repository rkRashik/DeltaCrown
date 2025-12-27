import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

print("Adding available_ranks column to games_game table...")

try:
    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE games_game 
            ADD COLUMN IF NOT EXISTS available_ranks JSONB DEFAULT '[]'::jsonb NOT NULL;
        """)
    print("✅ Column added successfully!")
except Exception as e:
    print(f"Note: {e}")
    print("This is OK if column already exists")

print("\nVerifying column exists...")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'games_game' AND column_name = 'available_ranks';
    """)
    result = cursor.fetchone()
    if result:
        print(f"✅ Column exists: {result[0]} ({result[1]})")
    else:
        print("❌ Column not found!")
