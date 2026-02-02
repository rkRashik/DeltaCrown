"""
Management command to run development bootstrap smoke checks.

This command:
1. Prints sanitized database identity
2. Runs Django system check
3. Runs smoke tests to verify bootstrap success

Usage:
    python manage.py dev_bootstrap_smoke_check
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.test.utils import get_runner
from django.conf import settings
from urllib.parse import urlparse
import sys
import os


class Command(BaseCommand):
    help = "Run development bootstrap smoke checks (identity + check + smoke tests)"

    def handle(self, *args, **options):
        """Execute smoke check sequence."""
        self.stdout.write("=" * 80)
        self.stdout.write("DEVELOPMENT BOOTSTRAP SMOKE CHECK")
        self.stdout.write("=" * 80)
        
        exit_code = 0
        
        # Step 1: Database Identity
        try:
            self.stdout.write("\n" + self.style.WARNING("1. DATABASE IDENTITY"))
            self.stdout.write("-" * 80)
            self._print_database_identity()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] Database identity check failed: {e}"))
            exit_code = 1
        
        if exit_code != 0:
            sys.exit(exit_code)
        
        # Step 2: Django System Check
        try:
            self.stdout.write("\n" + self.style.WARNING("2. SYSTEM CHECK"))
            self.stdout.write("-" * 80)
            self._run_system_check()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] System check failed: {e}"))
            sys.exit(1)
        
        # Step 3: Smoke Tests
        try:
            self.stdout.write("\n" + self.style.WARNING("3. SMOKE TESTS"))
            self.stdout.write("-" * 80)
            self._run_smoke_tests()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] Smoke tests failed: {e}"))
            sys.exit(1)
        
        # Success
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("[OK] ALL SMOKE CHECKS PASSED"))
        self.stdout.write("=" * 80)
        self.stdout.write("\nDevelopment database is ready for use.")
        self.stdout.write("\n")
    
    def _print_database_identity(self):
        """Print sanitized database connection identity."""
        # Get database URL source
        using_dev = bool(os.getenv('DATABASE_URL_DEV'))
        db_url = os.getenv('DATABASE_URL_DEV') or os.getenv('DATABASE_URL', '')
        
        if not db_url:
            raise Exception("No DATABASE_URL set")
        
        parsed = urlparse(db_url)
        source = "[DEV]" if using_dev else "[PROD]"
        
        self.stdout.write(f"Source: {source}")
        self.stdout.write(f"Host: {parsed.hostname or 'unknown'}")
        self.stdout.write(f"Database: {parsed.path.lstrip('/') if parsed.path else 'unknown'}")
        
        # Verify live connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), version()")
            db_name, version = cursor.fetchone()
            
            self.stdout.write(f"\nLive Connection:")
            self.stdout.write(f"  Database: {db_name}")
            self.stdout.write(f"  PostgreSQL: {version.split(',')[0]}")
        
        # Warning if not using DEV
        if not using_dev:
            self.stdout.write(self.style.WARNING(
                "\n[WARNING] Not using DATABASE_URL_DEV - may be production database!"
            ))
        
        self.stdout.write(self.style.SUCCESS("\n[OK] Database identity verified"))
    
    def _run_system_check(self):
        """Run Django system check."""
        self.stdout.write("Running: python manage.py check")
        
        try:
            call_command('check', verbosity=0)
            self.stdout.write(self.style.SUCCESS("[OK] Django check passed"))
        except Exception as e:
            raise Exception(f"Django check failed: {e}")
    
    def _run_smoke_tests(self):
        """Run smoke tests."""
        self.stdout.write("Running smoke tests: apps.core.tests.test_smoke_dev_bootstrap")
        self.stdout.write("")
        
        # Use Django test runner
        TestRunner = get_runner(settings)
        test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)
        
        # Run only smoke tests
        failures = test_runner.run_tests([
            'apps.core.tests.test_smoke_dev_bootstrap.DevBootstrapSmokeTests'
        ])
        
        if failures:
            raise Exception(f"{failures} test(s) failed")
        
        self.stdout.write(self.style.SUCCESS("\n[OK] All smoke tests passed"))
