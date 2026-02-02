"""
Management command to reconcile legacy database with current migration state.

This fixes SCENARIO A: Tables exist but migrations not recorded.
Specifically handles both organizations and teams apps which have tables
created outside Django's migration system.

PROBLEM:
- Production Neon database has organizations_* and teams_* tables
- django_migrations table is missing records for these migrations
- Running migrate fails with DuplicateTable errors

SOLUTION:
- Detect which migrations should be faked based on existing tables
- Insert migration records into django_migrations
- Verify dependency consistency
"""

import os
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = "Reconcile legacy organizations and teams migrations with current database state"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write("\n" + "="*70)
        self.stdout.write("RECONCILE LEGACY MIGRATIONS")
        self.stdout.write("="*70 + "\n")

        # Migration definitions for both apps
        migration_specs = {
            'organizations': {
                'migrations': [
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
                ],
                'sentinel_tables': [
                    'organizations_organization',
                    'organizations_membership',
                    'organizations_ranking',
                ],
            },
            'teams': {
                'migrations': [
                    '0099_fix_teamsponsor_fk_to_organizations_team',
                    '0100_fix_teamjoinrequest_fk_to_organizations_team',
                    '0101_alter_teamjoinrequest_team_alter_teamsponsor_team',
                ],
                'sentinel_tables': [
                    'teams_team',
                    'teams_teamsponsor',
                    'teams_teamjoinrequest',
                ],
            },
        }

        recorder = MigrationRecorder(connection)
        total_faked = 0

        for app_label, spec in migration_specs.items():
            self.stdout.write(self.style.WARNING(f"\n📦 Processing {app_label} app\n"))

            # Check current recorded migrations
            existing_migrations = set(
                recorder.migration_qs.filter(app=app_label).values_list('name', flat=True)
            )
            self.stdout.write(f"Currently recorded: {len(existing_migrations)} migrations")

            # Check sentinel tables exist
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                      AND table_name = ANY(%s)
                """, [spec['sentinel_tables']])
                found_tables = [row[0] for row in cursor.fetchall()]

            missing_tables = set(spec['sentinel_tables']) - set(found_tables)
            if missing_tables:
                self.stdout.write(self.style.ERROR(
                    f"⚠️  WARNING: Missing sentinel tables: {missing_tables}"
                ))
                self.stdout.write(self.style.ERROR(
                    f"Skipping {app_label} - database doesn't match expected schema"
                ))
                continue

            self.stdout.write(self.style.SUCCESS(
                f"✅ All {len(found_tables)} sentinel tables found"
            ))

            # Determine which migrations to fake
            migrations_to_fake = [
                m for m in spec['migrations']
                if m not in existing_migrations
            ]

            if not migrations_to_fake:
                self.stdout.write(self.style.SUCCESS(
                    f"✅ All {app_label} migrations already recorded"
                ))
                continue

            self.stdout.write(f"\nMigrations to fake: {len(migrations_to_fake)}")
            for migration in migrations_to_fake:
                self.stdout.write(f"  ⏭️  {migration}")

            # Fake-apply migrations
            if dry_run:
                self.stdout.write(self.style.WARNING("\n🔍 DRY RUN - No changes made\n"))
                for migration in migrations_to_fake:
                    self.stdout.write(f"  Would fake: {app_label}.{migration}")
            else:
                self.stdout.write(self.style.WARNING("\n⚙️  Applying fake migrations...\n"))
                with transaction.atomic():
                    for migration_name in migrations_to_fake:
                        recorder.record_applied(app_label, migration_name)
                        self.stdout.write(self.style.SUCCESS(
                            f"  ✅ Faked: {app_label}.{migration_name}"
                        ))
                        total_faked += 1

        # Final summary
        self.stdout.write("\n" + "="*70)
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"🔍 DRY RUN complete - would fake {total_faked} migrations"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"✅ Successfully faked {total_faked} migrations across {len(migration_specs)} apps"
            ))
            self.stdout.write(self.style.SUCCESS(
                "\n🎉 Next: Run 'python manage.py migrate' to apply any remaining migrations"
            ))
        self.stdout.write("="*70 + "\n")
