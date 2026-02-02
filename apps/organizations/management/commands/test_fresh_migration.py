"""
Test fresh database migration to diagnose DuplicateTable error.
"""
import psycopg2
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Test fresh database migration'

    def handle(self, *args, **options):
        db_config = settings.DATABASES['default']
        
        # Create fresh test database
        test_db_name = 'deltacrown_migration_test'
        
        self.stdout.write(f"Creating fresh database: {test_db_name}")
        
        try:
            # Connect to postgres database to create test database
            conn = psycopg2.connect(
                dbname='postgres',
                user=db_config['USER'],
                password=db_config['PASSWORD'],
                host=db_config['HOST'],
                port=db_config.get('PORT', '5432')
            )
            conn.autocommit = True
            cur = conn.cursor()
            
            # Drop and recreate test database
            cur.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
            cur.execute(f"CREATE DATABASE {test_db_name} OWNER {db_config['USER']}")
            
            self.stdout.write(self.style.SUCCESS(f"✓ Created fresh database: {test_db_name}"))
            
            # Close connection
            cur.close()
            conn.close()
            
            # Update Django connection to use test database
            connection.close()
            connection.settings_dict['NAME'] = test_db_name
            connection.ensure_connection()
            
            self.stdout.write("Running migrations on fresh database...")
            
            # Run migrations with verbose output
            call_command('migrate', '--verbosity=2', '--traceback')
            
            self.stdout.write(self.style.SUCCESS("✓ Migrations completed successfully"))
            
            # Check what tables were created
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname='public' AND tablename LIKE 'organizations_%'
                    ORDER BY tablename
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                self.stdout.write(f"\nOrganizations tables created ({len(tables)}):")
                for table in tables:
                    self.stdout.write(f"  - {table}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error: {e}"))
            import traceback
            traceback.print_exc()
        
        finally:
            # Restore original database connection
            connection.close()
            connection.settings_dict['NAME'] = db_config['NAME']
            self.stdout.write(f"\nRestored connection to: {db_config['NAME']}")
