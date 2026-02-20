"""Reset test database to clean state."""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

conn = psycopg2.connect('postgresql://dcadmin:dcpass123@localhost:5432/postgres')
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# Terminate existing connections
cur.execute("""
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = 'deltacrown_test'
    AND pid != pg_backend_pid()
""")

cur.execute('DROP DATABASE IF EXISTS deltacrown_test')
cur.execute('CREATE DATABASE deltacrown_test OWNER dcadmin')
print('Recreated deltacrown_test database (clean state)')
cur.close()
conn.close()
