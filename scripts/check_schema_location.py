"""
Schema Location Validation Script
==================================

Detects tables that exist outside the public schema for critical Django apps.

PURPOSE:
    Prevents recurrence of Phase 15 schema drift (Jan 2026) where migrations
    created tables in test_schema instead of public, causing ORM failures.

USAGE:
    python scripts/check_schema_location.py

    Returns:
        Exit code 0: All tables in correct schema (PASS)
        Exit code 1: Tables found outside public schema (FAIL)

WHAT IT CHECKS:
    - user_profile_* tables
    - teams_* tables
    - accounts_* tables (excluding auth shadow tables)
    - tournament_* tables
    - games_* tables

    Any of these found in schemas other than 'public' triggers a FAIL.

INTEGRATION:
    Can be added to CI/CD pipeline:
        - Pre-deployment check
        - Post-migration validation
        - Nightly health check

NO AUTO-FIXING:
    This script only detects issues. It does NOT modify the database.
    Manual intervention required if failures detected.

DEPENDENCIES:
    - Django (uses settings and database connection)
    - PostgreSQL (queries information_schema)

OUTPUT:
    - PASS: Green checkmark, exit 0
    - FAIL: Red X, lists problematic tables, exit 1
"""

import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection


def check_schema_location():
    """
    Verify critical tables are in public schema.
    
    Returns:
        bool: True if all tables in correct location, False otherwise
    """
    # Critical prefixes to check
    critical_prefixes = [
        'user_profile_',
        'teams_',
        'accounts_user',  # Main user table only (exclude shadow)
        'tournament_',
        'games_',
    ]
    
    with connection.cursor() as cursor:
        # Find all tables not in public schema with critical prefixes
        cursor.execute("""
            SELECT 
                schemaname,
                tablename
            FROM pg_tables
            WHERE schemaname != 'public'
              AND schemaname NOT IN ('pg_catalog', 'information_schema')
              AND (
                  tablename LIKE 'user_profile_%%'
                  OR tablename LIKE 'teams_%%'
                  OR tablename = 'accounts_user'
                  OR tablename LIKE 'tournament_%%'
                  OR tablename LIKE 'games_%%'
              )
            ORDER BY schemaname, tablename;
        """)
        
        misplaced_tables = cursor.fetchall()
        
        # Print header
        print("\n" + "="*70)
        print("SCHEMA LOCATION VALIDATION")
        print("="*70)
        
        if not misplaced_tables:
            print("\n✅ PASS: All critical tables are in public schema")
            print("="*70 + "\n")
            return True
        
        # Failure - report details
        print("\n❌ FAIL: Tables found outside public schema\n")
        print(f"{'Schema':<20} {'Table':<40}")
        print("-"*70)
        
        for schema, table in misplaced_tables:
            print(f"{schema:<20} {table:<40}")
        
        print("\n" + "="*70)
        print("ACTION REQUIRED:")
        print("  1. Identify why tables are in wrong schema")
        print("  2. Review recent migrations")
        print("  3. Move tables to public schema if needed:")
        print("     ALTER TABLE <schema>.<table> SET SCHEMA public;")
        print("  4. See docs/migrations/PHASE15_SCHEMA_DRIFT_FINAL_REPORT.md")
        print("="*70 + "\n")
        
        return False


def main():
    """Main entry point."""
    try:
        passed = check_schema_location()
        sys.exit(0 if passed else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
