"""
Management command to verify database and Redis connections.
Tests PostgreSQL extensions and Redis cache functionality.

Usage:
    python manage.py verify_connections
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = 'Verify database and Redis connections with PostgreSQL extensions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed connection information',
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Connection Verification ===\n'))

        # Test PostgreSQL connection
        self.stdout.write('Testing PostgreSQL connection...')
        try:
            with connection.cursor() as cursor:
                # Test basic connection
                cursor.execute('SELECT version();')
                pg_version = cursor.fetchone()[0]
                self.stdout.write(self.style.SUCCESS(f'✓ PostgreSQL connected: {pg_version.split(",")[0]}'))

                if verbose:
                    cursor.execute('SELECT current_database();')
                    db_name = cursor.fetchone()[0]
                    self.stdout.write(f'  Database: {db_name}')

                # Test uuid-ossp extension
                cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'uuid-ossp';")
                if cursor.fetchone():
                    self.stdout.write(self.style.SUCCESS('✓ Extension uuid-ossp is installed'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ Extension uuid-ossp is NOT installed'))

                # Test pg_trgm extension
                cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'pg_trgm';")
                if cursor.fetchone():
                    self.stdout.write(self.style.SUCCESS('✓ Extension pg_trgm is installed'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ Extension pg_trgm is NOT installed'))

                # Test unaccent extension
                cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'unaccent';")
                if cursor.fetchone():
                    self.stdout.write(self.style.SUCCESS('✓ Extension unaccent is installed'))
                else:
                    self.stdout.write(self.style.WARNING('⚠ Extension unaccent is NOT installed'))

                # Test connection pool
                if verbose:
                    cursor.execute('SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();')
                    active_connections = cursor.fetchone()[0]
                    self.stdout.write(f'  Active connections: {active_connections}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ PostgreSQL connection failed: {str(e)}'))
            return

        self.stdout.write('')

        # Test Redis connection
        self.stdout.write('Testing Redis connection...')
        try:
            # Test set/get
            test_key = 'deltacrown_verify_test'
            test_value = f'Connection verified at {timezone.now()}'
            cache.set(test_key, test_value, timeout=60)
            retrieved = cache.get(test_key)

            if retrieved == test_value:
                self.stdout.write(self.style.SUCCESS('✓ Redis connected and working'))
                self.stdout.write(self.style.SUCCESS('✓ Cache set/get operations successful'))
                
                # Clean up
                cache.delete(test_key)
                self.stdout.write(self.style.SUCCESS('✓ Cache delete operation successful'))

                if verbose:
                    # Try to get Redis info
                    try:
                        from django_redis import get_redis_connection
                        redis_conn = get_redis_connection("default")
                        info = redis_conn.info()
                        self.stdout.write(f'  Redis version: {info.get("redis_version", "unknown")}')
                        self.stdout.write(f'  Connected clients: {info.get("connected_clients", "unknown")}')
                        self.stdout.write(f'  Used memory: {info.get("used_memory_human", "unknown")}')
                    except Exception:
                        pass  # Silently skip if django-redis not available

            else:
                self.stdout.write(self.style.ERROR('✗ Redis cache verification failed: value mismatch'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Redis connection failed: {str(e)}'))
            self.stdout.write(self.style.WARNING('  Note: This is expected if Redis is not running'))

        self.stdout.write('')

        # Test session backend
        self.stdout.write('Checking session configuration...')
        from django.conf import settings
        session_engine = settings.SESSION_ENGINE
        self.stdout.write(f'  Session engine: {session_engine}')
        
        if 'cache' in session_engine:
            self.stdout.write(self.style.SUCCESS('✓ Sessions configured to use cache (Redis)'))
        else:
            self.stdout.write(self.style.WARNING(f'  Sessions using: {session_engine}'))

        self.stdout.write('\n' + self.style.MIGRATE_HEADING('=== Verification Complete ===\n'))
