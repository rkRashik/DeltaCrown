"""One-time script to setup test database."""
import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, user='dc_user', password='Rashik0001', dbname='postgres')
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
print('Databases:', [r[0] for r in cur.fetchall()])

cur.execute("SELECT 1 FROM pg_database WHERE datname = 'deltacrown_test'")
if not cur.fetchone():
    cur.execute('CREATE DATABASE deltacrown_test')
    print('Created deltacrown_test')
else:
    print('deltacrown_test already exists')

# Also create dcadmin role if it doesn't exist
cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'dcadmin'")
if not cur.fetchone():
    cur.execute("CREATE ROLE dcadmin WITH LOGIN PASSWORD 'dcpass123' SUPERUSER")
    print('Created dcadmin role')
else:
    print('dcadmin role already exists')

# Grant privileges
cur.execute("GRANT ALL PRIVILEGES ON DATABASE deltacrown_test TO dcadmin")
print('Granted privileges to dcadmin')

conn.close()
print('Done')
