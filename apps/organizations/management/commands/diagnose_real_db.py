"""
Diagnose the REAL database state where migrate fails.
No ephemeral DBs - use actual settings.DATABASES['default'].
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = "Diagnose real database state for migration issues"

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.WARNING("REAL DATABASE DIAGNOSIS"))
        self.stdout.write("=" * 80)
        
        # Step 1: Show Django database settings
        self.stdout.write("\n📋 Step 1: Django Database Settings")
        self.stdout.write("-" * 80)
        
        db_settings = settings.DATABASES['default']
        self.stdout.write(f"ENGINE: {db_settings['ENGINE']}")
        self.stdout.write(f"NAME: {db_settings['NAME']}")
        self.stdout.write(f"HOST: {db_settings['HOST']}")
        self.stdout.write(f"PORT: {db_settings.get('PORT', 5432)}")
        self.stdout.write(f"USER: {db_settings['USER']}")
        self.stdout.write(f"PASSWORD: {'*' * 8} (redacted)")
        
        options_dict = db_settings.get('OPTIONS', {})
        if options_dict:
            self.stdout.write(f"OPTIONS: {options_dict}")
        else:
            self.stdout.write("OPTIONS: (none)")
        
        # Step 2: Actual connection info from PostgreSQL
        self.stdout.write("\n🔌 Step 2: Actual PostgreSQL Connection Info")
        self.stdout.write("-" * 80)
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            current_db = cursor.fetchone()[0]
            self.stdout.write(f"Current database: {current_db}")
            
            cursor.execute("SELECT current_user")
            current_user = cursor.fetchone()[0]
            self.stdout.write(f"Current user: {current_user}")
            
            cursor.execute("SELECT current_schema()")
            current_schema = cursor.fetchone()[0]
            self.stdout.write(f"Current schema: {current_schema}")
            
            cursor.execute("SHOW search_path")
            search_path = cursor.fetchone()[0]
            self.stdout.write(f"Search path: {search_path}")
            
            # Try to get server address
            try:
                cursor.execute("SELECT inet_server_addr(), inet_server_port()")
                result = cursor.fetchone()
                if result and result[0]:
                    self.stdout.write(f"Server address: {result[0]}:{result[1]}")
                else:
                    self.stdout.write("Server address: localhost (Unix socket)")
            except Exception as e:
                self.stdout.write(f"Server address: (could not determine: {e})")
        
        # Step 3: Find organizations_organization table across ALL schemas
        self.stdout.write("\n🔍 Step 3: Searching for organizations_organization table")
        self.stdout.write("-" * 80)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_name = 'organizations_organization'
                ORDER BY table_schema
            """)
            
            tables = cursor.fetchall()
            if tables:
                self.stdout.write(self.style.WARNING(f"Found {len(tables)} occurrence(s):"))
                for schema, name, ttype in tables:
                    self.stdout.write(f"  - Schema: {schema}, Table: {name}, Type: {ttype}")
            else:
                self.stdout.write(self.style.SUCCESS("Table organizations_organization NOT FOUND in any schema"))
        
        # Step 4: Check django_migrations table existence
        self.stdout.write("\n📝 Step 4: Django Migrations Table State")
        self.stdout.write("-" * 80)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'django_migrations'
            """)
            
            has_migrations_table = cursor.fetchone()[0] > 0
            
            if has_migrations_table:
                self.stdout.write(self.style.SUCCESS("✓ django_migrations table EXISTS"))
                
                # Check for organizations migrations
                cursor.execute("""
                    SELECT app, name, applied
                    FROM django_migrations
                    WHERE app = 'organizations'
                    ORDER BY applied
                """)
                
                org_migrations = cursor.fetchall()
                if org_migrations:
                    self.stdout.write(f"\nFound {len(org_migrations)} organizations migration(s) recorded:")
                    for app, name, applied in org_migrations:
                        self.stdout.write(f"  - {app}.{name} applied at {applied}")
                else:
                    self.stdout.write(self.style.WARNING("\n⚠️  NO organizations migrations recorded in django_migrations"))
                
                # Count total migrations
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                total_count = cursor.fetchone()[0]
                self.stdout.write(f"\nTotal migrations recorded: {total_count}")
                
            else:
                self.stdout.write(self.style.ERROR("✗ django_migrations table DOES NOT EXIST"))
                self.stdout.write("  This means migrations have never been run on this database")
        
        # Step 5: Check ALL tables in public schema
        self.stdout.write("\n📊 Step 5: All Tables in Public Schema")
        self.stdout.write("-" * 80)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            all_tables = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f"Total tables in public schema: {len(all_tables)}")
            
            if all_tables:
                # Show first 20 and last 20
                if len(all_tables) <= 40:
                    self.stdout.write("\nAll tables:")
                    for table in all_tables:
                        self.stdout.write(f"  - {table}")
                else:
                    self.stdout.write("\nFirst 20 tables:")
                    for table in all_tables[:20]:
                        self.stdout.write(f"  - {table}")
                    self.stdout.write(f"\n  ... ({len(all_tables) - 40} more) ...")
                    self.stdout.write("\nLast 20 tables:")
                    for table in all_tables[-20:]:
                        self.stdout.write(f"  - {table}")
                
                # Check for specific org tables
                org_tables = [t for t in all_tables if 'organization' in t.lower()]
                if org_tables:
                    self.stdout.write(f"\nOrganization-related tables ({len(org_tables)}):")
                    for table in org_tables:
                        self.stdout.write(f"  - {table}")
        
        # Step 6: Scenario determination
        self.stdout.write("\n🎯 Step 6: Scenario Determination")
        self.stdout.write("-" * 80)
        
        with connection.cursor() as cursor:
            # Check if django_migrations exists
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'django_migrations'
            """)
            has_migrations_table = cursor.fetchone()[0] > 0
            
            # Check if organizations_organization exists
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'organizations_organization'
            """)
            has_org_table = cursor.fetchone()[0] > 0
            
            # Check if organizations.0001_initial is recorded
            has_org_migration = False
            if has_migrations_table:
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM django_migrations
                    WHERE app = 'organizations'
                    AND name = '0001_initial'
                """)
                has_org_migration = cursor.fetchone()[0] > 0
            
            self.stdout.write(f"django_migrations table exists: {has_migrations_table}")
            self.stdout.write(f"organizations_organization table exists: {has_org_table}")
            self.stdout.write(f"organizations.0001_initial recorded: {has_org_migration}")
            
            if has_org_table and not has_org_migration:
                self.stdout.write("\n" + self.style.ERROR("SCENARIO A: Table exists but migration not recorded"))
                self.stdout.write("Fix: Use --fake-initial flag or insert migration record")
            elif has_org_table and has_org_migration:
                self.stdout.write("\n" + self.style.WARNING("UNEXPECTED: Both table and migration exist"))
                self.stdout.write("This shouldn't cause DuplicateTable error")
            elif not has_org_table and not has_org_migration:
                self.stdout.write("\n" + self.style.SUCCESS("CLEAN STATE: Ready for fresh migration"))
            else:
                self.stdout.write("\n" + self.style.WARNING("Migration recorded but table missing - unusual state"))
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("DIAGNOSIS COMPLETE"))
        self.stdout.write("=" * 80)
