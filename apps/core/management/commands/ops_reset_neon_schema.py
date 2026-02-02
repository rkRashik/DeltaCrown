"""
Management command to reset Neon database schema and re-bootstrap.

SAFETY:
- Only runs on Neon databases (checks for neon.tech in host)
- Refuses to run on databases with 'prod' in name unless FORCE=1
- Requires explicit confirmation or CONFIRM=1 env var

USAGE:
    # Interactive (prompts for confirmation)
    python manage.py ops_reset_neon_schema

    # Non-interactive (for automation)
    CONFIRM=1 python manage.py ops_reset_neon_schema

    # Force on production-named DB (dangerous!)
    FORCE=1 CONFIRM=1 python manage.py ops_reset_neon_schema
"""
import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection
from urllib.parse import urlparse


class Command(BaseCommand):
    help = "Reset Neon database schema and re-bootstrap with seeds"

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-seed',
            action='store_true',
            help='Skip seeding after migration'
        )

    def handle(self, *args, **options):
        # Get database URL and parse
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            raise CommandError("❌ DATABASE_URL not set")

        parsed = urlparse(db_url)
        db_host = parsed.hostname or ''
        db_name = parsed.path.lstrip('/') or ''

        # Safety check 1: Must be Neon
        if 'neon.tech' not in db_host and not os.getenv('FORCE'):
            raise CommandError(
                f"❌ Safety: This command only runs on Neon databases.\n"
                f"   Current host: {db_host}\n"
                f"   Set FORCE=1 to override (dangerous!)"
            )

        # Safety check 2: Refuse production-named databases
        if 'prod' in db_name.lower() and not os.getenv('FORCE'):
            raise CommandError(
                f"❌ Safety: Database name contains 'prod': {db_name}\n"
                f"   Set FORCE=1 to override (very dangerous!)"
            )

        # Confirmation
        if not os.getenv('CONFIRM'):
            self.stdout.write(self.style.WARNING(
                f"\n⚠️  WARNING: This will DELETE ALL DATA in database:\n"
                f"   Host: {db_host}\n"
                f"   Database: {db_name}\n"
            ))
            response = input("\nType 'RESET' to confirm: ")
            if response != 'RESET':
                self.stdout.write(self.style.ERROR("❌ Aborted"))
                return

        # Execute reset
        self.stdout.write(self.style.WARNING("\n🗑️  Dropping schema..."))
        try:
            with connection.cursor() as cursor:
                cursor.execute("DROP SCHEMA public CASCADE;")
                cursor.execute("CREATE SCHEMA public;")
                cursor.execute("GRANT ALL ON SCHEMA public TO neondb_owner;")
                cursor.execute("GRANT ALL ON SCHEMA public TO public;")
        except Exception as e:
            raise CommandError(f"❌ Schema reset failed: {e}")

        self.stdout.write(self.style.SUCCESS("✅ Schema reset complete\n"))

        # Run migrations
        self.stdout.write("📦 Running migrations...")
        try:
            call_command('migrate', '--noinput', verbosity=0)
            
            # Count applied migrations
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM django_migrations;")
                migration_count = cursor.fetchone()[0]
            
            self.stdout.write(self.style.SUCCESS(f"✅ Applied {migration_count} migrations\n"))
        except Exception as e:
            raise CommandError(f"❌ Migrations failed: {e}")

        # Seed data
        if options['no_seed']:
            self.stdout.write(self.style.WARNING("⏭️  Skipping seed (--no-seed)\n"))
        else:
            self._seed_data()

        # Final summary
        self._print_summary()

    def _seed_data(self):
        """Seed core data in correct order."""
        self.stdout.write("🌱 Seeding data...\n")

        # 1. Seed games
        self.stdout.write("  1/3 Seeding games...")
        try:
            call_command('seed_games', verbosity=0)
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM games_game;")
                game_count = cursor.fetchone()[0]
            self.stdout.write(self.style.SUCCESS(f"      ✅ {game_count} games"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Failed: {e}"))

        # 2. Seed passport schemas
        self.stdout.write("  2/3 Seeding passport schemas...")
        try:
            call_command('seed_game_passport_schemas', verbosity=0)
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM user_profile_gamepassportschema;")
                schema_count = cursor.fetchone()[0]
            self.stdout.write(self.style.SUCCESS(f"      ✅ {schema_count} schemas"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"      ❌ Failed: {e}"))

        # 3. Seed competition configs (optional)
        if os.getenv('COMPETITION_APP_ENABLED') == '1':
            self.stdout.write("  3/3 Seeding competition configs...")
            try:
                call_command('seed_game_ranking_configs', verbosity=0)
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM competition_gamerankingconfig;")
                    config_count = cursor.fetchone()[0]
                self.stdout.write(self.style.SUCCESS(f"      ✅ {config_count} configs"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"      ❌ Failed: {e}"))
        else:
            self.stdout.write("  3/3 Skipping competition configs (COMPETITION_APP_ENABLED not set)")

        self.stdout.write()

    def _print_summary(self):
        """Print final summary."""
        db_url = os.getenv('DATABASE_URL', '')
        parsed = urlparse(db_url)
        
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("✅ RESET COMPLETE"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"\n📍 Database: {parsed.hostname}:{parsed.port or 5432}/{parsed.path.lstrip('/')}")
        self.stdout.write("\n📋 Next steps:")
        self.stdout.write("   1. Create superuser: python manage.py createsuperuser")
        self.stdout.write("   2. Start server: python manage.py runserver")
        self.stdout.write("   3. Visit: http://localhost:8000/admin/\n")
