"""
Utility script to drop all tournament-related database tables.
Run this to reset the database for clean migration.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

def drop_all_tournament_tables():
    with connection.cursor() as cursor:
        # Get all tournament tables
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE tablename LIKE 'tournaments_%' OR tablename LIKE 'tournament_engine_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(tables)} tournament tables:")
        for table in tables:
            print(f"  - {table}")
        
        if tables:
            # Drop all tables
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"✅ Dropped {table}")
            
            print(f"\n✅ Successfully dropped {len(tables)} tournament tables")
        else:
            print("No tournament tables found")

if __name__ == '__main__':
    drop_all_tournament_tables()
