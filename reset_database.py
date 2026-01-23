#!/usr/bin/env python
"""
Reset Neon Database - Drops all tables and recreates from migrations
"""
import os
import sys
import psycopg2
from urllib.parse import urlparse

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def reset_database():
    """Drop all tables and recreate the database schema"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables!")
        sys.exit(1)
    
    # Parse the DATABASE_URL
    parsed = urlparse(database_url)
    
    print("🔗 Connecting to Neon database...")
    print(f"   Host: {parsed.hostname}")
    print(f"   Database: {parsed.path[1:]}")
    
    # Connect to the database
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("\n🗑️  Dropping all tables...")
        
        # Get all table names
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = cursor.fetchall()
        
        print(f"   Found {len(tables)} tables to drop...")
        
        # Drop all tables with CASCADE
        for (table_name,) in tables:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')
                print(f"   ✓ Dropped {table_name}")
            except Exception as e:
                print(f"   ⚠ Warning dropping {table_name}: {e}")
        
        # Drop all sequences
        cursor.execute("""
            SELECT sequence_name FROM information_schema.sequences 
            WHERE sequence_schema = 'public';
        """)
        sequences = cursor.fetchall()
        
        if sequences:
            print(f"\n   Dropping {len(sequences)} sequences...")
            for (seq_name,) in sequences:
                try:
                    cursor.execute(f'DROP SEQUENCE IF EXISTS "{seq_name}" CASCADE;')
                except Exception as e:
                    print(f"   ⚠ Warning dropping sequence {seq_name}: {e}")
        
        print("✅ All tables dropped successfully!")
        
        cursor.close()
        conn.close()
        
        print("\n📦 Running migrations to recreate database schema...")
        os.system("python manage.py migrate")
        
        print("\n✅ Database reset complete!")
        print("\nNext steps:")
        print("  1. Create a superuser: python manage.py createsuperuser")
        print("  2. Load fixtures if you have any")
        print("  3. Start your server: python manage.py runserver")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("  NEON DATABASE RESET")
    print("=" * 60)
    print("\n⚠️  WARNING: This will DELETE ALL DATA in your database!")
    print("   Database: Neon PostgreSQL Cloud")
    
    response = input("\n   Type 'RESET' to confirm: ")
    
    if response == "RESET":
        reset_database()
    else:
        print("\n❌ Reset cancelled.")
        sys.exit(0)
