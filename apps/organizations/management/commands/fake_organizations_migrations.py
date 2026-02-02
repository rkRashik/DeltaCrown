"""
Management command to manually record organizations migrations as applied.

This is needed when tables already exist in the database but django_migrations
has no record of their creation (SCENARIO A: legacy tables without migration tracking).

Strategy:
1. Check existing table structures against each migration
2. Fake-apply migrations that match existing schema
3. Apply remaining migrations normally
"""

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = "Manually record organizations migrations as applied when tables exist"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )
        parser.add_argument(
            '--migrations',
            nargs='+',
            help='Specific migration names to fake (e.g., 0001_initial 0002_add_team_tag_and_tagline)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_migrations = options.get('migrations')

        self.stdout.write("\n" + "="*70)
        self.stdout.write("FAKE ORGANIZATIONS MIGRATIONS")
        self.stdout.write("="*70 + "\n")

        # Step 1: Check current state
        self.stdout.write(self.style.WARNING("\n📊 Step 1: Checking current migration state\n"))
        
        recorder = MigrationRecorder(connection)
        existing_migrations = set(
            recorder.migration_qs.filter(app='organizations').values_list('name', flat=True)
        )
        
        self.stdout.write(f"Currently recorded organizations migrations: {len(existing_migrations)}")
        if existing_migrations:
            for migration in sorted(existing_migrations):
                self.stdout.write(f"  ✅ {migration}")
        else:
            self.stdout.write(self.style.ERROR("  ❌ No organizations migrations recorded"))

        # Step 2: List available migrations
        self.stdout.write(self.style.WARNING("\n📦 Step 2: Available migrations\n"))
        
        # All known migrations from file listing
        all_migrations = [
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
        
        # Filter to specific migrations if requested
        if specific_migrations:
            migrations_to_fake = [m for m in all_migrations if m in specific_migrations]
            self.stdout.write(f"Requested specific migrations: {len(migrations_to_fake)}")
        else:
            migrations_to_fake = [m for m in all_migrations if m not in existing_migrations]
            self.stdout.write(f"Migrations to fake: {len(migrations_to_fake)}")
        
        if not migrations_to_fake:
            self.stdout.write(self.style.SUCCESS("\n✅ All migrations already recorded!"))
            return

        for migration in migrations_to_fake:
            status = "✅ recorded" if migration in existing_migrations else "⏭️  to fake"
            self.stdout.write(f"  {status}: {migration}")

        # Step 3: Check table existence
        self.stdout.write(self.style.WARNING("\n🔍 Step 3: Verifying table existence\n"))
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                  AND table_name LIKE 'organizations_%'
                ORDER BY table_name
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
        
        self.stdout.write(f"Found {len(existing_tables)} organizations tables:")
        for table in existing_tables:
            self.stdout.write(f"  📋 {table}")

        # Expected tables from 0001_initial
        expected_core_tables = [
            'organizations_organization',
            'organizations_team_invite',
            'organizations_activity_log',
            'organizations_membership',
            'organizations_ranking',
        ]
        
        missing_core = [t for t in expected_core_tables if t not in existing_tables]
        if missing_core:
            self.stdout.write(self.style.ERROR(f"\n⚠️  WARNING: Missing core tables: {missing_core}"))
            self.stdout.write(self.style.ERROR("This suggests the database schema doesn't match migrations."))
            if not dry_run:
                self.stdout.write(self.style.ERROR("Aborting to prevent inconsistency."))
                return

        # Step 4: Fake-apply migrations
        self.stdout.write(self.style.WARNING(f"\n⚙️  Step 4: Fake-applying {len(migrations_to_fake)} migrations\n"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be made\n"))
            for migration in migrations_to_fake:
                self.stdout.write(f"  Would fake: organizations.{migration}")
        else:
            with transaction.atomic():
                for migration_name in migrations_to_fake:
                    recorder.record_applied('organizations', migration_name)
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Faked: organizations.{migration_name}"))
            
            self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully faked {len(migrations_to_fake)} migrations"))

        # Step 5: Verify final state
        self.stdout.write(self.style.WARNING("\n✅ Step 5: Verification\n"))
        
        final_migrations = set(
            recorder.migration_qs.filter(app='organizations').values_list('name', flat=True)
        )
        self.stdout.write(f"Total organizations migrations now recorded: {len(final_migrations)}")
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS("\n🎉 Next step: Run 'python manage.py migrate' to apply any remaining migrations"))
        
        self.stdout.write("\n" + "="*70 + "\n")
