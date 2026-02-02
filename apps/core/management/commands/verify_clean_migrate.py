"""
Management command to verify clean database migration.

This command:
1. Prints sanitized database identity
2. Runs Django migrations
3. Performs smoke checks
4. Exits with non-zero code if any step fails

Designed for fresh database setup/bootstrap scenarios.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection
from django.conf import settings
from urllib.parse import urlparse
import sys
import os


class Command(BaseCommand):
    help = "Verify clean database migration (identity + migrate + smoke checks)"

    def handle(self, *args, **options):
        """Execute the verification sequence."""
        self.stdout.write("=" * 80)
        self.stdout.write("CLEAN DATABASE MIGRATION VERIFICATION")
        self.stdout.write("=" * 80)
        
        exit_code = 0
        
        # Step 1: Database Identity
        try:
            self.stdout.write("\n" + self.style.WARNING("1. DATABASE IDENTITY"))
            self.stdout.write("-" * 80)
            self._verify_database_identity()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] Database identity check failed: {e}"))
            exit_code = 1
        
        if exit_code != 0:
            sys.exit(exit_code)
        
        # Step 2: Run Migrations
        try:
            self.stdout.write("\n" + self.style.WARNING("2. RUNNING MIGRATIONS"))
            self.stdout.write("-" * 80)
            self._run_migrations()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] Migrations failed: {e}"))
            sys.exit(1)
        
        # Step 3: Smoke Checks
        try:
            self.stdout.write("\n" + self.style.WARNING("3. SMOKE CHECKS"))
            self.stdout.write("-" * 80)
            self._run_smoke_checks()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] Smoke checks failed: {e}"))
            sys.exit(1)
        
        # Success
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("[OK] ALL CHECKS PASSED"))
        self.stdout.write("=" * 80)
        self.stdout.write("\nDatabase is ready for use.")
        self.stdout.write("\nNext steps:")
        self.stdout.write("  - Run setup commands (seed_game_ranking_configs, etc.)")
        self.stdout.write("  - Create superuser: python manage.py createsuperuser")
        self.stdout.write("  - Start server: python manage.py runserver")
        self.stdout.write("\n")
    
    def _verify_database_identity(self):
        """Verify and display database connection identity."""
        # Get database URL source
        using_dev = bool(os.getenv('DATABASE_URL_DEV'))
        db_url = os.getenv('DATABASE_URL_DEV') or os.getenv('DATABASE_URL', '')
        
        if not db_url:
            raise CommandError("No DATABASE_URL set")
        
        parsed = urlparse(db_url)
        source = "[DEV]" if using_dev else "[PROD]"
        
        self.stdout.write(f"Source: {source}")
        self.stdout.write(f"Host: {parsed.hostname or 'unknown'}")
        self.stdout.write(f"Port: {parsed.port or 5432}")
        self.stdout.write(f"Database: {parsed.path.lstrip('/') if parsed.path else 'unknown'}")
        self.stdout.write(f"User: {parsed.username or 'unknown'}")
        
        # Verify live connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user, version()")
            db_name, db_user, version = cursor.fetchone()
            
            self.stdout.write(f"\nLive Connection:")
            self.stdout.write(f"  current_database(): {db_name}")
            self.stdout.write(f"  current_user: {db_user}")
            self.stdout.write(f"  version: {version.split(',')[0]}")
        
        # Verify Neon connection if expected
        if 'neon.tech' in db_url:
            if 'neon.tech' not in (parsed.hostname or ''):
                raise CommandError("DATABASE_URL claims Neon but host doesn't match")
            self.stdout.write(self.style.SUCCESS("\n[OK] Connected to Neon cloud database"))
        
        self.stdout.write(self.style.SUCCESS("\n[OK] Database identity verified"))
    
    def _run_migrations(self):
        """Run Django migrations."""
        self.stdout.write("Running: python manage.py migrate")
        self.stdout.write("")
        
        # Run migrate with verbosity 1 (normal output)
        call_command('migrate', verbosity=1, interactive=False)
        
        self.stdout.write(self.style.SUCCESS("\n[OK] Migrations completed"))
    
    def _run_smoke_checks(self):
        """Run smoke checks to verify database state."""
        # Check 1: Django system check
        self.stdout.write("Running: python manage.py check")
        try:
            call_command('check', verbosity=0)
            self.stdout.write(self.style.SUCCESS("[OK] Django check passed"))
        except Exception as e:
            raise CommandError(f"Django check failed: {e}")
        
        # Check 2: Migration status
        self.stdout.write("\nChecking migration status...")
        from django.db.migrations.recorder import MigrationRecorder
        recorder = MigrationRecorder(connection)
        
        # Count applied migrations
        total_migrations = recorder.migration_qs.count()
        self.stdout.write(f"Total applied migrations: {total_migrations}")
        
        # Check key apps
        key_apps = ['organizations', 'teams', 'competition', 'tournaments']
        for app in key_apps:
            count = recorder.migration_qs.filter(app=app).count()
            if count > 0:
                self.stdout.write(f"  {app}: {count} migrations")
        
        self.stdout.write(self.style.SUCCESS("[OK] Migration status verified"))
        
        # Check 3: Critical tables exist
        self.stdout.write("\nVerifying critical tables...")
        critical_tables = [
            'django_content_type',
            'accounts_user',
            'organizations_organization',
            'teams_team',
        ]
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = ANY(%s)
            """, [critical_tables])
            existing_tables = [row[0] for row in cursor.fetchall()]
        
        for table in critical_tables:
            if table in existing_tables:
                self.stdout.write(f"[OK] {table}")
            else:
                raise CommandError(f"Critical table missing: {table}")
        
        self.stdout.write(self.style.SUCCESS("\n[OK] Critical tables verified"))
