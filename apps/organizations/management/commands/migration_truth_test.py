"""
Management command to establish TRUTH about fresh DB migration failure.

This command:
1. Creates a fresh ephemeral Postgres database
2. Runs migrations with full verbosity
3. Captures exact failure mode and stack trace
4. Introspects DB state at failure point
5. Generates comprehensive evidence report

Usage:
    python manage.py migration_truth_test
"""
import sys
import traceback
from io import StringIO
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection, connections
from django.conf import settings
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class Command(BaseCommand):
    help = "Run fresh DB migration test and capture comprehensive evidence"

    def add_arguments(self, parser):
        parser.add_argument(
            '--keep-db',
            action='store_true',
            help='Keep test database after run for manual inspection'
        )
        parser.add_argument(
            '--db-name',
            type=str,
            default='deltacrown_truth_test',
            help='Name for test database (default: deltacrown_truth_test)'
        )

    def handle(self, *args, **options):
        keep_db = options['keep_db']
        test_db_name = options['db_name']
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.WARNING("MIGRATION TRUTH TEST - STEP 1: ESTABLISH FACTS"))
        self.stdout.write("=" * 80)
        
        # Store original DB connection info
        original_db = settings.DATABASES['default']['NAME']
        original_conn = connection
        
        # Get superuser connection for DB creation
        db_config = settings.DATABASES['default']
        
        self.stdout.write(f"\n📋 Database Configuration:")
        self.stdout.write(f"   Original DB: {original_db}")
        self.stdout.write(f"   Test DB: {test_db_name}")
        self.stdout.write(f"   Host: {db_config['HOST']}")
        self.stdout.write(f"   User: {db_config['USER']}")
        
        # Step 1: Create fresh database
        self.stdout.write(f"\n🔨 Step 1: Creating fresh database '{test_db_name}'...")
        
        try:
            # Connect to postgres DB to create new database
            conn = psycopg2.connect(
                dbname='postgres',
                user=db_config['USER'],
                password=db_config['PASSWORD'],
                host=db_config['HOST'],
                port=db_config['PORT']
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Drop existing test DB if exists
            self.stdout.write(f"   Dropping existing '{test_db_name}' if exists...")
            cursor.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
            
            # Create fresh test DB
            self.stdout.write(f"   Creating fresh '{test_db_name}'...")
            cursor.execute(f"CREATE DATABASE {test_db_name}")
            
            cursor.close()
            conn.close()
            
            self.stdout.write(self.style.SUCCESS(f"   ✅ Fresh database '{test_db_name}' created"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Failed to create database: {e}"))
            return
        
        # Step 2: Switch Django to use test database
        self.stdout.write(f"\n🔀 Step 2: Switching Django connection to '{test_db_name}'...")
        
        # Close existing connections
        connections.close_all()
        
        # Update settings to point to test DB
        settings.DATABASES['default']['NAME'] = test_db_name
        
        # Force Django to create new connection
        from django.db import connection as new_connection
        new_connection.ensure_connection()
        
        self.stdout.write(self.style.SUCCESS(f"   ✅ Connected to '{test_db_name}'"))
        
        # Step 3: Verify DB is empty
        self.stdout.write(f"\n🔍 Step 3: Verifying database is empty...")
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT count(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            
            self.stdout.write(f"   Tables in public schema: {table_count}")
            
            if table_count > 0:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                self.stdout.write(f"   Existing tables: {', '.join(tables)}")
                self.stdout.write(self.style.WARNING("   ⚠️  Database not empty!"))
            else:
                self.stdout.write(self.style.SUCCESS("   ✅ Database is empty"))
        
        # Step 4: Run migrations with full verbosity
        self.stdout.write(f"\n🚀 Step 4: Running migrations with full verbosity...")
        self.stdout.write("-" * 80)
        
        # Capture stdout and stderr
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        migration_success = False
        migration_error = None
        migration_traceback = None
        
        try:
            # Run migrate with verbosity 3 (maximum detail)
            call_command(
                'migrate',
                verbosity=3,
                interactive=False,
                stdout=stdout_capture,
                stderr=stderr_capture
            )
            migration_success = True
            self.stdout.write(self.style.SUCCESS("\n✅ Migrations completed successfully!"))
            
        except Exception as e:
            migration_error = str(e)
            migration_traceback = traceback.format_exc()
            self.stdout.write(self.style.ERROR(f"\n❌ Migration failed: {type(e).__name__}: {e}"))
        
        # Print captured output
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        
        if stdout_output:
            self.stdout.write("\n📝 Migration stdout:")
            self.stdout.write(stdout_output)
        
        if stderr_output:
            self.stdout.write("\n📝 Migration stderr:")
            self.stdout.write(stderr_output)
        
        if migration_traceback:
            self.stdout.write("\n📝 Full traceback:")
            self.stdout.write(migration_traceback)
        
        # Step 5: Introspect DB state after migration attempt
        self.stdout.write(f"\n🔍 Step 5: Introspecting database state after migration...")
        self.stdout.write("-" * 80)
        
        db_state = self._introspect_db_state()
        
        self.stdout.write(f"\n📊 Database State:")
        self.stdout.write(f"   Total tables: {db_state['table_count']}")
        self.stdout.write(f"   django_migrations exists: {db_state['has_django_migrations']}")
        self.stdout.write(f"   organizations_organization exists: {db_state['has_organizations_organization']}")
        
        if db_state['table_count'] > 0:
            self.stdout.write(f"\n   All tables ({db_state['table_count']}):")
            for table in db_state['tables']:
                self.stdout.write(f"      - {table}")
        
        if db_state['has_django_migrations']:
            self.stdout.write(f"\n   Applied migrations: {db_state['migration_count']}")
            if db_state['migrations']:
                self.stdout.write("   Last 10 migrations:")
                for app, name in db_state['migrations'][-10:]:
                    self.stdout.write(f"      - {app}.{name}")
        
        # Step 6: Detailed error analysis
        if not migration_success:
            self.stdout.write(f"\n🔬 Step 6: Error Analysis")
            self.stdout.write("-" * 80)
            
            error_type = self._classify_error(migration_error, migration_traceback)
            self.stdout.write(f"   Error Type: {error_type}")
            
            if error_type == "DuplicateTable":
                self._analyze_duplicate_table_error(migration_traceback, db_state)
            elif error_type == "NotNullViolation":
                self._analyze_not_null_error(migration_traceback, db_state)
            else:
                self.stdout.write(f"   Raw error: {migration_error}")
        
        # Step 7: Cleanup
        self.stdout.write(f"\n🧹 Step 7: Cleanup")
        self.stdout.write("-" * 80)
        
        # Restore original database connection
        connections.close_all()
        settings.DATABASES['default']['NAME'] = original_db
        
        if not keep_db:
            self.stdout.write(f"   Dropping test database '{test_db_name}'...")
            try:
                conn = psycopg2.connect(
                    dbname='postgres',
                    user=db_config['USER'],
                    password=db_config['PASSWORD'],
                    host=db_config['HOST'],
                    port=db_config['PORT']
                )
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cursor = conn.cursor()
                cursor.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
                cursor.close()
                conn.close()
                self.stdout.write(self.style.SUCCESS(f"   ✅ Test database dropped"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Failed to drop database: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"   ⚠️  Keeping test database '{test_db_name}' for inspection"))
        
        # Final summary
        self.stdout.write(f"\n" + "=" * 80)
        self.stdout.write(self.style.WARNING("SUMMARY"))
        self.stdout.write("=" * 80)
        
        if migration_success:
            self.stdout.write(self.style.SUCCESS("✅ Migrations completed successfully on fresh database"))
            self.stdout.write(f"   Tables created: {db_state['table_count']}")
            self.stdout.write(f"   Migrations applied: {db_state['migration_count']}")
        else:
            self.stdout.write(self.style.ERROR("❌ Migration failed on fresh database"))
            self.stdout.write(f"   Error: {migration_error}")
            self.stdout.write(f"   Tables created before failure: {db_state['table_count']}")
            self.stdout.write(f"   Migrations applied before failure: {db_state['migration_count']}")
        
        self.stdout.write("=" * 80)
    
    def _introspect_db_state(self):
        """Introspect current database state."""
        state = {
            'table_count': 0,
            'tables': [],
            'has_django_migrations': False,
            'has_organizations_organization': False,
            'migration_count': 0,
            'migrations': []
        }
        
        with connection.cursor() as cursor:
            # Get all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            state['tables'] = [row[0] for row in cursor.fetchall()]
            state['table_count'] = len(state['tables'])
            
            # Check for django_migrations
            state['has_django_migrations'] = 'django_migrations' in state['tables']
            
            # Check for organizations_organization
            state['has_organizations_organization'] = 'organizations_organization' in state['tables']
            
            # Get applied migrations if table exists
            if state['has_django_migrations']:
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                state['migration_count'] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT app, name 
                    FROM django_migrations 
                    ORDER BY applied
                """)
                state['migrations'] = cursor.fetchall()
        
        return state
    
    def _classify_error(self, error_msg, traceback_str):
        """Classify the type of migration error."""
        if not error_msg:
            return "Unknown"
        
        error_lower = error_msg.lower()
        traceback_lower = traceback_str.lower() if traceback_str else ""
        
        if 'already exists' in error_lower or 'duplicate' in error_lower:
            return "DuplicateTable"
        elif 'not null' in error_lower or 'violates not-null' in error_lower:
            return "NotNullViolation"
        elif 'foreign key' in error_lower:
            return "ForeignKeyViolation"
        else:
            return "Unknown"
    
    def _analyze_duplicate_table_error(self, traceback_str, db_state):
        """Analyze DuplicateTable error in detail."""
        self.stdout.write("\n   🔬 DuplicateTable Error Analysis:")
        
        # Extract table name from error
        lines = traceback_str.split('\n')
        for line in lines:
            if 'already exists' in line.lower():
                self.stdout.write(f"      Error line: {line.strip()}")
        
        # Check if table actually exists
        if db_state['has_organizations_organization']:
            self.stdout.write("      ⚠️  organizations_organization table EXISTS in database")
            self.stdout.write("      This confirms duplicate CREATE TABLE attempt")
            
            # Try to find which migration created it
            if db_state['has_django_migrations']:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT app, name, applied 
                        FROM django_migrations 
                        WHERE app = 'organizations'
                        ORDER BY applied
                    """)
                    org_migrations = cursor.fetchall()
                    if org_migrations:
                        self.stdout.write(f"\n      Organizations migrations applied ({len(org_migrations)}):")
                        for app, name, applied in org_migrations:
                            self.stdout.write(f"         - {app}.{name} at {applied}")
        else:
            self.stdout.write("      ⚠️  organizations_organization table DOES NOT exist")
            self.stdout.write("      This is unexpected - error claims duplicate but table missing")
    
    def _analyze_not_null_error(self, traceback_str, db_state):
        """Analyze NotNullViolation error in detail."""
        self.stdout.write("\n   🔬 NotNullViolation Error Analysis:")
        
        # Extract column/table from error
        lines = traceback_str.split('\n')
        for line in lines:
            if 'not null' in line.lower() or 'violates' in line.lower():
                self.stdout.write(f"      Error line: {line.strip()}")
        
        self.stdout.write("\n      Likely cause: AddField with null=False on existing table")
        self.stdout.write("      Solution: Split into phases:")
        self.stdout.write("         1. AddField with null=True")
        self.stdout.write("         2. Data migration to populate values")
        self.stdout.write("         3. AlterField to null=False")
