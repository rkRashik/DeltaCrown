"""
Script to completely reset the database and run migrations fresh.
This resolves the corrupted migration state issue.
"""
import subprocess
import sys

print("=" * 80)
print("DELTACROWN DATABASE RESET & MIGRATION")
print("=" * 80)

# Step 1: Reset database using psql
print("\n[1/2] Resetting database...")
try:
    # Drop and recreate database
    subprocess.run([
        "psql",
        "-U", "postgres",
        "-h", "localhost",
        "-p", "5432",
        "-c", "DROP DATABASE IF EXISTS deltacrown;"
    ], check=True, capture_output=True, text=True)
    
    subprocess.run([
        "psql",
        "-U", "postgres",
        "-h", "localhost",
        "-p", "5432",
        "-c", "CREATE DATABASE deltacrown OWNER dc_user;"
    ], check=True, capture_output=True, text=True)
    
    print("✅ Database recreated successfully")
except subprocess.CalledProcessError as e:
    print(f"❌ Database reset failed: {e}")
    print(f"   stdout: {e.stdout}")
    print(f"   stderr: {e.stderr}")
    sys.exit(1)

# Step 2: Run all migrations
print("\n[2/2] Running migrations...")
try:
    result = subprocess.run([
        "python", "manage.py", "migrate"
    ], check=True, capture_output=True, text=True)
    
    print(result.stdout)
    print("✅ Migrations completed successfully")
except subprocess.CalledProcessError as e:
    print(f"❌ Migrations failed: {e}")
    print(f"   stdout: {e.stdout}")
    print(f"   stderr: {e.stderr}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ DATABASE RESET COMPLETE")
print("=" * 80)
