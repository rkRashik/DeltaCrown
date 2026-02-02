"""
Database migration reconciliation command.

Purpose: Safely reconcile physical database tables with Django's migration history
when tables exist but migration records are missing (common with external DB creation
or legacy migrations).

This command:
1. Diagnoses the current state (read-only)
2. Detects table/migration mismatches
3. Safely fakes missing migration records (with --apply-fake)

SAFETY GUARANTEES:
- Read-only by default (requires explicit --apply-fake flag)
- Never drops tables or deletes data
- Validates table existence before faking migrations
- Idempotent (safe to re-run)
- Requires --yes-i-know-the-database for production safety
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.conf import settings
from django.db.migrations.recorder import MigrationRecorder
from django.db import transaction
from datetime import datetime


class Command(BaseCommand):
    help = "Reconcile database tables with Django migration history (READ-ONLY unless --apply-fake)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply-fake',
            action='store_true',
            help='Actually fake the migrations (default is read-only diagnosis)',
        )
        parser.add_argument(
            '--yes-i-know-the-database',
            action='store_true',
            help='Required safety confirmation that you understand which database will be affected',
        )

    def handle(self, *args, **options):
        apply_fake = options['apply_fake']
        confirmed = options['yes_i_know_the_database']
        
        self.stdout.write("=" * 80)
        self.stdout.write("DATABASE MIGRATION RECONCILIATION")
        self.stdout.write(f"Timestamp: {datetime.now().isoformat()}")
        self.stdout.write("=" * 80)
        
        # Step 1: Database identification
        self.stdout.write(self.style.WARNING("\n1. DATABASE IDENTIFICATION"))
        self.stdout.write("-" * 80)
        
        db_settings = settings.DATABASES['default']
        db_host = db_settings.get('HOST', 'localhost')
        db_port = db_settings.get('PORT', '5432')
        db_name = db_settings.get('NAME', 'unknown')
        db_user = db_settings.get('USER', 'unknown')
        
        self.stdout.write(f"Host: {db_host}")
        self.stdout.write(f"Port: {db_port}")
        self.stdout.write(f"Database: {db_name}")
        self.stdout.write(f"User: {db_user}")
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user, current_schema()")
            runtime_db, runtime_user, runtime_schema = cursor.fetchone()
            self.stdout.write(f"Runtime DB: {runtime_db}")
            self.stdout.write(f"Runtime User: {runtime_user}")
            self.stdout.write(f"Runtime Schema: {runtime_schema}")
        
        # CRITICAL SAFETY CHECK: Test database requirement
        import os
        is_test_db = 'test' in runtime_db.lower()
        allow_nontest = os.getenv('ALLOW_NONTEST_MIGRATION_RECONCILE', '0') == '1'
        
        if apply_fake and not is_test_db and not allow_nontest:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.ERROR("SAFETY BLOCK: Cannot apply-fake on production database!"))
            self.stdout.write("=" * 80)
            self.stdout.write(f"\nCurrent database: {runtime_db}")
            self.stdout.write("This database name does NOT contain 'test'.")
            self.stdout.write("\nTo protect production data, --apply-fake is only allowed on test databases.")
            self.stdout.write("\n" + "-" * 80)
            self.stdout.write("RECOMMENDED ACTION:")
            self.stdout.write("-" * 80)
            self.stdout.write("\n1. Go to Neon Console: https://console.neon.tech")
            self.stdout.write("2. Create a new branch from your main database:")
            self.stdout.write("   - Click on your project")
            self.stdout.write("   - Go to 'Branches' tab")
            self.stdout.write("   - Click 'New Branch'")
            self.stdout.write("   - Name it: test_deltacrown")
            self.stdout.write("   - Base it on: main branch")
            self.stdout.write("\n3. Get the connection string for the new branch")
            self.stdout.write("\n4. Update your .env file:")
            self.stdout.write("   DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/test_deltacrown?sslmode=require")
            self.stdout.write("\n5. Run this command again")
            self.stdout.write("\n" + "-" * 80)
            self.stdout.write("ALTERNATIVE (Advanced users only):")
            self.stdout.write("-" * 80)
            self.stdout.write("\nIf you REALLY understand what you're doing and want to")
            self.stdout.write("apply-fake on the production database, set:")
            self.stdout.write("   $env:ALLOW_NONTEST_MIGRATION_RECONCILE=1")
            self.stdout.write("AND use --yes-i-know-the-database flag")
            self.stdout.write("\n" + "=" * 80)
            return
        
        # Step 2: Table inventory
        self.stdout.write(self.style.WARNING("\n2. TABLE INVENTORY"))
        self.stdout.write("-" * 80)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                  AND (tablename LIKE 'organizations_%' OR tablename LIKE 'teams_%')
                ORDER BY tablename
            """)
            tables = [row[0] for row in cursor.fetchall()]
        
        org_tables = [t for t in tables if t.startswith('organizations_')]
        teams_tables = [t for t in tables if t.startswith('teams_')]
        
        self.stdout.write(f"Organizations tables: {len(org_tables)}")
        self.stdout.write(f"Teams tables: {len(teams_tables)}")
        self.stdout.write(f"Total: {len(tables)}")
        
        # Step 3: Migration records inventory
        self.stdout.write(self.style.WARNING("\n3. MIGRATION RECORDS"))
        self.stdout.write("-" * 80)
        
        recorder = MigrationRecorder(connection)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT app, COUNT(*) 
                FROM django_migrations 
                WHERE app IN ('organizations', 'teams', 'competition')
                GROUP BY app
                ORDER BY app
            """)
            migration_counts = dict(cursor.fetchall())
        
        org_migration_count = migration_counts.get('organizations', 0)
        teams_migration_count = migration_counts.get('teams', 0)
        competition_migration_count = migration_counts.get('competition', 0)
        
        self.stdout.write(f"organizations app: {org_migration_count} migrations recorded")
        self.stdout.write(f"teams app: {teams_migration_count} migrations recorded")
        self.stdout.write(f"competition app: {competition_migration_count} migrations recorded")
        
        # Step 4: Detect mismatches
        self.stdout.write(self.style.WARNING("\n4. MISMATCH DETECTION"))
        self.stdout.write("-" * 80)
        
        # Organizations: Expected 12 migrations
        org_migrations_needed = [
            '0001_initial',
            '0002_add_team_tag_and_tagline',
            '0003_add_team_invite_model',
            '0004_create_organization_profile',
            '0005_add_org_uuid_and_public_id',
            '0006_backfill_org_identifiers',
            '0007_add_team_visibility',
            '0008_add_team_social_fields',
            '0009_fix_teaminvite_fk_reference',
            '0010_alter_teamranking_team_alter_teaminvite_team_and_more',
            '0011_add_team_colors',
            '0012_alter_membership_invite_team_fk',
        ]
        
        # Teams: Expected 5 migrations (0001, 0002, 0099, 0100, 0101)
        teams_migrations_needed = [
            '0001_initial',
            '0002_initial',
            '0099_fix_teamsponsor_fk_to_organizations_team',
            '0100_fix_teamjoinrequest_fk_to_organizations_team',
            '0101_alter_teamjoinrequest_team_alter_teamsponsor_team',
        ]
        
        # Check which are missing
        existing_org_migrations = set(
            recorder.migration_qs.filter(app='organizations').values_list('name', flat=True)
        )
        existing_teams_migrations = set(
            recorder.migration_qs.filter(app='teams').values_list('name', flat=True)
        )
        
        missing_org = [m for m in org_migrations_needed if m not in existing_org_migrations]
        missing_teams = [m for m in teams_migrations_needed if m not in existing_teams_migrations]
        
        org_has_tables = len(org_tables) > 0
        teams_has_tables = len(teams_tables) > 0
        org_missing_migrations = len(missing_org) > 0
        teams_missing_migrations = len(missing_teams) > 0
        
        mismatch_detected = False
        
        if org_has_tables and org_missing_migrations:
            self.stdout.write(self.style.ERROR(
                f"MISMATCH: {len(org_tables)} organizations tables exist but {len(missing_org)} migrations missing"
            ))
            mismatch_detected = True
            for m in missing_org[:5]:  # Show first 5
                self.stdout.write(f"  Missing: organizations.{m}")
            if len(missing_org) > 5:
                self.stdout.write(f"  ... and {len(missing_org) - 5} more")
        
        if teams_has_tables and teams_missing_migrations:
            self.stdout.write(self.style.ERROR(
                f"MISMATCH: {len(teams_tables)} teams tables exist but {len(missing_teams)} migrations missing"
            ))
            mismatch_detected = True
            for m in missing_teams:
                self.stdout.write(f"  Missing: teams.{m}")
        
        if not mismatch_detected:
            self.stdout.write(self.style.SUCCESS("No mismatches detected - migrations are in sync with tables"))
            return
        
        # Step 5: Sentinel table verification
        self.stdout.write(self.style.WARNING("\n5. CRITICAL TABLE VERIFICATION"))
        self.stdout.write("-" * 80)
        
        critical_checks = {
            'organizations_organization': 'organizations_organization' in tables,
            'teams_team': 'teams_team' in tables,
        }
        
        all_critical_present = all(critical_checks.values())
        
        for table, exists in critical_checks.items():
            status = self.style.SUCCESS("EXISTS") if exists else self.style.ERROR("MISSING")
            self.stdout.write(f"  {table}: {status}")
        
        if not all_critical_present:
            self.stdout.write(self.style.ERROR(
                "\nCRITICAL: Some essential tables are missing. Cannot safely fake migrations."
            ))
            self.stdout.write("Run migrations normally to create missing tables.")
            return
        
        # Step 6: Apply fake migrations (if requested)
        if not apply_fake:
            self.stdout.write(self.style.WARNING("\n6. RECOMMENDED ACTION"))
            self.stdout.write("-" * 80)
            self.stdout.write("Tables exist but migration records are missing.")
            self.stdout.write("\nTo fix this, run:")
            self.stdout.write(self.style.SUCCESS(
                "  python manage.py db_migration_reconcile --apply-fake --yes-i-know-the-database"
            ))
            self.stdout.write("\nThis will mark existing migrations as applied without executing SQL.")
            return
        
        # Safety check for apply
        if not confirmed:
            raise CommandError(
                "ERROR: --apply-fake requires --yes-i-know-the-database flag.\n"
                f"You are about to modify migration records in: {db_name} on {db_host}\n"
                "Please confirm you understand which database will be affected."
            )
        
        self.stdout.write(self.style.WARNING("\n6. APPLYING FAKE MIGRATIONS"))
        self.stdout.write("-" * 80)
        self.stdout.write(f"Database: {runtime_db}")
        self.stdout.write(f"Host: {db_host}")
        self.stdout.write("")
        
        total_faked = 0
        
        with transaction.atomic():
            # Fake organizations migrations
            if missing_org:
                self.stdout.write(f"\nFaking {len(missing_org)} organizations migrations...")
                for migration_name in org_migrations_needed:
                    if migration_name in missing_org:
                        recorder.record_applied('organizations', migration_name)
                        self.stdout.write(self.style.SUCCESS(f"  [OK] organizations.{migration_name}"))
                        total_faked += 1
            
            # Fake teams migrations
            if missing_teams:
                self.stdout.write(f"\nFaking {len(missing_teams)} teams migrations...")
                for migration_name in teams_migrations_needed:
                    if migration_name in missing_teams:
                        recorder.record_applied('teams', migration_name)
                        self.stdout.write(self.style.SUCCESS(f"  [OK] teams.{migration_name}"))
                        total_faked += 1
        
        # Step 7: Verification
        self.stdout.write(self.style.WARNING("\n7. VERIFICATION"))
        self.stdout.write("-" * 80)
        
        final_org_count = recorder.migration_qs.filter(app='organizations').count()
        final_teams_count = recorder.migration_qs.filter(app='teams').count()
        
        self.stdout.write(f"organizations migrations now: {final_org_count}/{len(org_migrations_needed)}")
        self.stdout.write(f"teams migrations now: {final_teams_count}/{len(teams_migrations_needed)}")
        
        if final_org_count == len(org_migrations_needed) and final_teams_count == len(teams_migrations_needed):
            self.stdout.write(self.style.SUCCESS(f"\n[SUCCESS] Faked {total_faked} migrations"))
            self.stdout.write("\nNext steps:")
            self.stdout.write("1. Run: python manage.py showmigrations organizations teams")
            self.stdout.write("2. Run: python manage.py migrate --check")
            self.stdout.write("3. Run: python manage.py migrate (to apply any remaining migrations)")
        else:
            self.stdout.write(self.style.ERROR("\nWARNING: Some migrations may still be missing"))
        
        self.stdout.write("\n" + "=" * 80)
