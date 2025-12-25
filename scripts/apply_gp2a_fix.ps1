# GP-2A Fix Script: Apply migration and verify

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "GP-2A Fix: Applying migration to add missing columns" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Apply migration
Write-Host "Step 1: Applying migration 0027_gp2a_fix_missing_columns..." -ForegroundColor Yellow
python manage.py migrate user_profile

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Verification: Checking columns in database" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

# Check columns
python -c @"
import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute(\"\"\"
        SELECT column_name
        FROM information_schema.columns 
        WHERE table_name = 'user_profile_gameprofile'
        ORDER BY ordinal_position
    \"\"\")
    cols = [row[0] for row in cursor.fetchall()]
    
print('\nDatabase columns in user_profile_gameprofile:')
for col in cols:
    print(f'  ✓ {col}')

required = ['ign', 'discriminator', 'platform', 'region']
print('\nGP-2A Required Columns Status:')
missing = []
for col in required:
    if col in cols:
        print(f'  ✅ {col}: EXISTS')
    else:
        print(f'  ❌ {col}: MISSING')
        missing.append(col)

if missing:
    print(f'\n❌ ERROR: Missing columns: {missing}')
    exit(1)
else:
    print('\n✅ SUCCESS: All GP-2A columns exist!')
"@

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Green
Write-Host "Migration complete!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Green
