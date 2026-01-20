import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT column_name, ordinal_position
    FROM information_schema.columns
    WHERE table_name = 'user_profile_userprofile'
    ORDER BY ordinal_position
""")

cols = cursor.fetchall()
print('All columns in user_profile_userprofile (in database order):')
print('='*80)
for col_name, pos in cols:
    marker = ' <--- BIO/ABOUT' if 'about' in col_name.lower() or 'bio' in col_name.lower() else ''
    print(f'{pos:3}. {col_name}{marker}')

print(f'\nTotal: {len(cols)} columns')
