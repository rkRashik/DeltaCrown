@echo off
REM Script to check GameProfile DB columns

echo Checking GameProfile model vs database columns...
echo.

python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT column_name FROM information_schema.columns WHERE table_name=%%27user_profile_gameprofile%%27 ORDER BY ordinal_position'); cols = [row[0] for row in cursor.fetchall()]; print('DB Columns:'); [print(f'  - {col}') for col in cols]; print(); required = ['ign', 'discriminator', 'platform', 'region']; print('GP-2A Required Columns:'); [print(f'  {col}: {%%27EXISTS%%27 if col in cols else %%27MISSING%%27}') for col in required]"
