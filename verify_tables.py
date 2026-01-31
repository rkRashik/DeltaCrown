import psycopg2

conn = psycopg2.connect(dbname='deltacrown', user='dc_user', password='Rashik0001', host='localhost', port=5432)
cur = conn.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename LIMIT 50")
tables = [row[0] for row in cur.fetchall()]
print(f"✅ Found {len(tables)} total tables in public schema:")
for t in tables:
    if 'org' in t.lower() or 'team' in t.lower():
        print(f"  • {t} ⭐")
    else:
        print(f"  • {t}")
