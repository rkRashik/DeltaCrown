"""
READ-ONLY incident assessment command.
NO destructive operations - diagnostics only.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import json
from datetime import datetime


class Command(BaseCommand):
    help = "READ-ONLY assessment of database state after incident"
    
    def handle(self, *args, **options):
        report = []
        
        report.append("="*80)
        report.append("INCIDENT ASSESSMENT - READ-ONLY DIAGNOSTICS")
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("="*80)
        
        # 1. Database connection info
        report.append("\n1. DATABASE CONNECTION DETAILS")
        report.append("-" * 80)
        
        db_settings = settings.DATABASES['default']
        report.append(f"Host: {db_settings.get('HOST', 'N/A')}")
        report.append(f"Port: {db_settings.get('PORT', 'N/A')}")
        report.append(f"Database Name: {db_settings.get('NAME', 'N/A')}")
        report.append(f"User: {db_settings.get('USER', 'N/A')}")
        report.append(f"SSL Mode: {db_settings.get('OPTIONS', {}).get('sslmode', 'N/A')}")
        
        with connection.cursor() as cursor:
            # Current database runtime info
            cursor.execute("SELECT current_database()")
            current_db = cursor.fetchone()[0]
            report.append(f"Current Database (runtime): {current_db}")
            
            cursor.execute("SELECT current_user")
            current_user = cursor.fetchone()[0]
            report.append(f"Current User (runtime): {current_user}")
            
            cursor.execute("SELECT current_schema()")
            current_schema = cursor.fetchone()[0]
            report.append(f"Current Schema (runtime): {current_schema}")
            
            cursor.execute("SHOW search_path")
            search_path = cursor.fetchone()[0]
            report.append(f"Search Path: {search_path}")
            
            cursor.execute("SELECT inet_server_addr(), inet_server_port()")
            server_info = cursor.fetchone()
            report.append(f"Server Address: {server_info[0]}")
            report.append(f"Server Port: {server_info[1]}")
        
        # 2. Table inventory
        report.append("\n2. TABLE INVENTORY (organizations_* and teams_*)")
        report.append("-" * 80)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE tablename LIKE 'organizations_%' OR tablename LIKE 'teams_%'
                ORDER BY schemaname, tablename
            """)
            tables = cursor.fetchall()
            
            if tables:
                report.append(f"Found {len(tables)} tables:")
                for schema, table in tables:
                    report.append(f"  {schema}.{table}")
            else:
                report.append("*** WARNING: NO organizations_* or teams_* tables found ***")
        
        # 3. All tables in public schema
        report.append("\n3. ALL TABLES IN PUBLIC SCHEMA")
        report.append("-" * 80)
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            all_tables = [row[0] for row in cursor.fetchall()]
            report.append(f"Total tables in public schema: {len(all_tables)}")
            
            # Check for specific critical tables
            critical_tables = [
                'django_migrations',
                'organizations_organization',
                'organizations_team',
                'teams_team',
            ]
            
            report.append("\nCritical table check:")
            for table in critical_tables:
                exists = table in all_tables
                status = "EXISTS" if exists else "MISSING"
                report.append(f"  {table}: {status}")
        
        # 4. Migration records
        report.append("\n4. MIGRATION RECORDS")
        report.append("-" * 80)
        
        with connection.cursor() as cursor:
            # Check if django_migrations exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename = 'django_migrations'
                )
            """)
            migrations_table_exists = cursor.fetchone()[0]
            
            if not migrations_table_exists:
                report.append("*** ERROR: django_migrations table does not exist ***")
            else:
                report.append("django_migrations table: EXISTS")
                
                # Count by app
                cursor.execute("""
                    SELECT app, COUNT(*) 
                    FROM django_migrations 
                    WHERE app IN ('organizations', 'teams')
                    GROUP BY app
                    ORDER BY app
                """)
                app_counts = cursor.fetchall()
                
                if app_counts:
                    report.append("\nMigration counts:")
                    for app, count in app_counts:
                        report.append(f"  {app}: {count} migrations")
                else:
                    report.append("\n*** WARNING: No migration records for organizations or teams ***")
                
                # Latest 10 for organizations
                cursor.execute("""
                    SELECT id, app, name, applied 
                    FROM django_migrations 
                    WHERE app = 'organizations'
                    ORDER BY applied DESC
                    LIMIT 10
                """)
                org_migrations = cursor.fetchall()
                
                if org_migrations:
                    report.append("\nLatest organizations migrations (up to 10):")
                    for mid, app, name, applied in org_migrations:
                        report.append(f"  [{mid}] {app}.{name} - {applied}")
                else:
                    report.append("\nNo organizations migration records found")
                
                # Latest 10 for teams
                cursor.execute("""
                    SELECT id, app, name, applied 
                    FROM django_migrations 
                    WHERE app = 'teams'
                    ORDER BY applied DESC
                    LIMIT 10
                """)
                teams_migrations = cursor.fetchall()
                
                if teams_migrations:
                    report.append("\nLatest teams migrations (up to 10):")
                    for mid, app, name, applied in teams_migrations:
                        report.append(f"  [{mid}] {app}.{name} - {applied}")
                else:
                    report.append("\nNo teams migration records found")
                
                # Total migration count
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                total_migrations = cursor.fetchone()[0]
                report.append(f"\nTotal migration records in database: {total_migrations}")
        
        # 5. Recent DDL activity (if available)
        report.append("\n5. RECENT DATABASE ACTIVITY")
        report.append("-" * 80)
        
        with connection.cursor() as cursor:
            # Check for pg_stat_activity
            cursor.execute("""
                SELECT query, state, query_start, state_change
                FROM pg_stat_activity
                WHERE query ILIKE '%organizations_%' OR query ILIKE '%teams_%'
                ORDER BY query_start DESC
                LIMIT 5
            """)
            recent_queries = cursor.fetchall()
            
            if recent_queries:
                report.append("Recent queries mentioning organizations/teams:")
                for query, state, query_start, state_change in recent_queries:
                    report.append(f"  [{query_start}] {state}")
                    report.append(f"    {query[:200]}...")
            else:
                report.append("No recent queries found in pg_stat_activity")
        
        # 6. Damage assessment
        report.append("\n6. DAMAGE ASSESSMENT")
        report.append("-" * 80)
        
        orgs_tables_exist = len([t for s, t in tables if t.startswith('organizations_')]) > 0
        teams_tables_exist = len([t for s, t in tables if t.startswith('teams_')]) > 0
        orgs_migrations_exist = len([a for a, c in app_counts if a == 'organizations']) > 0 if app_counts else False
        teams_migrations_exist = len([a for a, c in app_counts if a == 'teams']) > 0 if app_counts else False
        
        if not orgs_tables_exist and orgs_migrations_exist:
            report.append("*** CRITICAL: organizations tables MISSING but migration records EXIST ***")
            report.append("This indicates tables were dropped after migrations were recorded.")
            report.append("Likely data loss scenario.")
        elif not orgs_tables_exist and not orgs_migrations_exist:
            report.append("INFO: organizations tables and migrations both missing (consistent state)")
        elif orgs_tables_exist and not orgs_migrations_exist:
            report.append("INFO: organizations tables exist but no migration records")
        else:
            report.append("OK: organizations tables and migrations both present")
        
        if not teams_tables_exist and teams_migrations_exist:
            report.append("*** CRITICAL: teams tables MISSING but migration records EXIST ***")
            report.append("This indicates tables were dropped after migrations were recorded.")
        elif not teams_tables_exist and not teams_migrations_exist:
            report.append("INFO: teams tables and migrations both missing (consistent state)")
        elif teams_tables_exist and not teams_migrations_exist:
            report.append("INFO: teams tables exist but no migration records")
        else:
            report.append("OK: teams tables and migrations both present")
        
        # Output report
        report.append("\n" + "="*80)
        report.append("END OF ASSESSMENT")
        report.append("="*80)
        
        for line in report:
            self.stdout.write(line)
        
        # Save to file
        output_file = "INCIDENT_ASSESSMENT_RAW_DATA.txt"
        with open(output_file, 'w') as f:
            f.write('\n'.join(report))
        
        self.stdout.write(f"\n\nReport saved to: {output_file}")
