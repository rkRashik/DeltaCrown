"""
Audit all applied migrations to find schema gaps.
Checks if tables and critical columns created by migrations actually exist in database.
"""
import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

# Key migrations that create tables/columns we want to verify
CRITICAL_CHECKS = [
    {
        'migration': '0001_initial',
        'table': 'user_profile_userprofile',
        'columns': ['user_id', 'bio', 'avatar'],
    },
    {
        'migration': '0005_badge_userbadge',
        'table': 'user_profile_badge',
        'columns': ['id', 'name', 'description'],
    },
    {
        'migration': '0007_userprofile_pronouns_achievement_certificate_and_more',
        'table': 'user_profile_achievement',
        'columns': ['id', 'user_id'],
    },
    {
        'migration': '0013_add_public_id_system',
        'table': 'user_profile_userprofile',
        'columns': ['public_id'],
    },
    {
        'migration': '0016_restore_publicidcounter',
        'table': 'user_profile_publicidcounter',
        'columns': ['year', 'counter'],
    },
    {
        'migration': '0020_gp0_game_passport_rebuild',
        'table': 'user_profile_gameprofile',
        'columns': ['id', 'user_id'],
    },
    {
        'migration': '0030_phase6c_settings_models',
        'table': 'user_profile_privacysettings',
        'columns': ['user_id'],
    },
    {
        'migration': '0031_add_profile_showcase_model',
        'table': 'user_profile_profileshowcase',
        'columns': ['user_id'],
    },
    {
        'migration': '0034_p0_media_models',
        'table': 'user_profile_highlight',
        'columns': ['id', 'user_id'],
    },
    {
        'migration': '0035_p0_loadout_models',
        'table': 'user_profile_hardwareloadout',
        'columns': ['user_id'],
    },
    {
        'migration': '0036_p0_trophy_showcase',
        'table': 'user_profile_trophyshowcase',
        'columns': ['user_id'],
    },
    {
        'migration': '0046_careerprofile_matchmakingpreferences',
        'table': 'user_profile_careerprofile',
        'columns': ['user_id'],
    },
    {
        'migration': '0048_phase6a_private_account_and_follow_requests',
        'table': 'user_profile_followrequest',
        'columns': ['id', 'from_user_id', 'to_user_id'],
    },
    {
        'migration': '0055_phase4_add_about_fields_and_hardware_loadout',
        'table': 'user_profile_userprofile',
        'columns': ['device_platform', 'active_hours', 'main_role'],
    },
]

def check_table_exists(table_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, [table_name])
        return cursor.fetchone()[0]

def check_column_exists(table_name, column_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = %s 
                AND column_name = %s
            );
        """, [table_name, column_name])
        return cursor.fetchone()[0]

def audit_migrations():
    # Get all applied migrations
    applied_migrations = set(
        f"{app}_{name}" 
        for app, name in MigrationRecorder.Migration.objects.filter(
            app='user_profile'
        ).values_list('app', 'name')
    )
    
    print("=" * 80)
    print("MIGRATION INTEGRITY AUDIT")
    print("=" * 80)
    print(f"Database: {connection.settings_dict['NAME']}")
    print(f"Applied user_profile migrations: {len(applied_migrations)}")
    print()
    
    issues = []
    checks_passed = 0
    checks_failed = 0
    
    for check in CRITICAL_CHECKS:
        migration = check['migration']
        table = check['table']
        columns = check['columns']
        
        # Check if migration is applied
        if f"user_profile_{migration}" not in applied_migrations:
            print(f"[SKIP] {migration} - not applied")
            continue
        
        # Check table exists
        table_exists = check_table_exists(table)
        if not table_exists:
            issues.append(f"Migration {migration}: Table {table} MISSING")
            checks_failed += 1
            print(f"[FAIL] {migration}")
            print(f"       Table: {table} - MISSING")
            continue
        
        # Check columns exist
        missing_columns = []
        for column in columns:
            if not check_column_exists(table, column):
                missing_columns.append(column)
        
        if missing_columns:
            issues.append(f"Migration {migration}: Columns {missing_columns} MISSING from {table}")
            checks_failed += 1
            print(f"[FAIL] {migration}")
            print(f"       Table: {table} - EXISTS")
            print(f"       Missing columns: {', '.join(missing_columns)}")
        else:
            checks_passed += 1
            print(f"[PASS] {migration}")
            print(f"       Table: {table} with {len(columns)} columns")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Checks passed: {checks_passed}")
    print(f"Checks failed: {checks_failed}")
    
    if issues:
        print("\nISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("\nNo schema integrity issues found.")
        return True

if __name__ == '__main__':
    success = audit_migrations()
    sys.exit(0 if success else 1)
