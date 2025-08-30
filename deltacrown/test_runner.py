# test_runner.py
from django.test.runner import DiscoverRunner
from django.db import connections


class CustomTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        # First, make sure the test database is completely gone
        test_db_name = 'test_deltacrown'

        try:
            with connections['default'].cursor() as cursor:
                # Terminate any active connections to the test database
                cursor.execute("""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = %s
                    AND pid <> pg_backend_pid()
                """, [test_db_name])
        except Exception:
            pass

        try:
            with connections['default'].cursor() as cursor:
                # Drop the database if it exists - without quotes around name
                cursor.execute("DROP DATABASE IF EXISTS test_deltacrown")
        except Exception:
            pass

        # Now let Django handle the test database creation
        return super().setup_databases(**kwargs)