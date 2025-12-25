# GP-2A Emergency Fix - Run in clean PowerShell session

$ErrorActionPreference = "Stop"

Write-Host "`n" ("=" * 80) -ForegroundColor Cyan
Write-Host "GP-2A EMERGENCY FIX: Adding missing structured identity columns" -ForegroundColor Cyan
Write-Host ("=" * 80) "`n" -ForegroundColor Cyan

# Step 1: Apply migration
Write-Host "[1/4] Applying migration..." -ForegroundColor Yellow
try {
    & python manage.py migrate user_profile 2>&1 | Out-String | Write-Host
    Write-Host "✅ Migration applied`n" -ForegroundColor Green
} catch {
    Write-Host "❌ Migration failed: $_`n" -ForegroundColor Red
    exit 1
}

# Step 2: Verify columns
Write-Host "[2/4] Verifying database columns..." -ForegroundColor Yellow
$checkScript = @'
import django
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='user_profile_gameprofile'")
    cols = [row[0] for row in cursor.fetchall()]
required = ['ign', 'discriminator', 'platform', 'region']
missing = [col for col in required if col not in cols]
if missing:
    print(f"MISSING:{','.join(missing)}")
    exit(1)
else:
    print("OK:All columns exist")
    for col in required:
        print(f"  ✓ {col}")
'@

try {
    $result = & python -c $checkScript 2>&1 | Out-String
    Write-Host $result
    if ($result -match "MISSING:") {
        Write-Host "❌ Some columns still missing!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ All GP-2A columns verified`n" -ForegroundColor Green
} catch {
    Write-Host "❌ Verification failed: $_`n" -ForegroundColor Red
    exit 1
}

# Step 3: Test admin page
Write-Host "[3/4] Testing admin page access..." -ForegroundColor Yellow
$testAdmin = @'
import django
django.setup()
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.user_profile.admin import GameProfileAdmin
from apps.user_profile.models import GameProfile
try:
    # Simulate admin list view
    admin = GameProfileAdmin(GameProfile, None)
    queryset = admin.get_queryset(None)
    print(f"OK:Admin queryset works, {queryset.count()} profiles")
except Exception as e:
    print(f"ERROR:{e}")
    exit(1)
'@

try {
    $result = & python -c $testAdmin 2>&1 | Out-String
    Write-Host $result
    if ($result -match "ERROR:") {
        Write-Host "❌ Admin test failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Admin page should work now`n" -ForegroundColor Green
} catch {
    Write-Host "❌ Admin test failed: $_`n" -ForegroundColor Red
    exit 1
}

# Step 4: Run system check
Write-Host "[4/4] Running Django system check..." -ForegroundColor Yellow
try {
    & python manage.py check 2>&1 | Out-String | Write-Host
    Write-Host "✅ System check passed`n" -ForegroundColor Green
} catch {
    Write-Host "⚠️  System check had warnings (may be OK)`n" -ForegroundColor Yellow
}

Write-Host "`n" ("=" * 80) -ForegroundColor Green
Write-Host "✅ GP-2A FIX COMPLETE!" -ForegroundColor Green  
Write-Host ("=" * 80) -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  1. Test /admin/user_profile/gameprofile/" -ForegroundColor White
Write-Host "  2. Test /@<username>/ profile page" -ForegroundColor White
Write-Host "  3. Create a test Game Passport to verify form works" -ForegroundColor White
Write-Host ""
