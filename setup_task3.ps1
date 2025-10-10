# Task 3 Setup Script
# Run this to complete the integration of the advanced team creation form

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Task 3: Advanced Team Creation Form - Setup" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Step 1: Install Django REST Framework
Write-Host "[Step 1] Installing Django REST Framework..." -ForegroundColor Yellow
pip install djangorestframework

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Django REST Framework installed successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to install Django REST Framework" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Check if Pillow is installed (for image handling)
Write-Host "[Step 2] Checking Pillow installation..." -ForegroundColor Yellow
python -c "import PIL" 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Pillow already installed" -ForegroundColor Green
} else {
    Write-Host "Installing Pillow..." -ForegroundColor Yellow
    pip install Pillow
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Pillow installed successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to install Pillow" -ForegroundColor Red
    }
}

Write-Host ""

# Step 3: Backup settings.py
Write-Host "[Step 3] Backing up settings.py..." -ForegroundColor Yellow
$settingsPath = "deltacrown\settings.py"
$backupPath = "deltacrown\settings.py.backup_task3"

if (Test-Path $settingsPath) {
    Copy-Item $settingsPath $backupPath
    Write-Host "✓ Settings backed up to $backupPath" -ForegroundColor Green
} else {
    Write-Host "✗ Could not find settings.py" -ForegroundColor Red
}

Write-Host ""

# Step 4: Instructions for manual settings update
Write-Host "[Step 4] Manual Configuration Required" -ForegroundColor Yellow
Write-Host ""
Write-Host "Please add the following to your deltacrown/settings.py:" -ForegroundColor White
Write-Host ""
Write-Host "# Add to INSTALLED_APPS" -ForegroundColor Cyan
Write-Host "INSTALLED_APPS = [" -ForegroundColor Gray
Write-Host "    ..." -ForegroundColor Gray
Write-Host "    'rest_framework'," -ForegroundColor Green
Write-Host "]" -ForegroundColor Gray
Write-Host ""
Write-Host "# Add REST Framework configuration" -ForegroundColor Cyan
Write-Host "REST_FRAMEWORK = {" -ForegroundColor Green
Write-Host "    'DEFAULT_PERMISSION_CLASSES': [" -ForegroundColor Green
Write-Host "        'rest_framework.permissions.IsAuthenticatedOrReadOnly'," -ForegroundColor Green
Write-Host "    ]," -ForegroundColor Green
Write-Host "    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination'," -ForegroundColor Green
Write-Host "    'PAGE_SIZE': 100" -ForegroundColor Green
Write-Host "}" -ForegroundColor Green
Write-Host ""

# Step 5: Check if migration is needed
Write-Host "[Step 5] Checking database migration status..." -ForegroundColor Yellow
python manage.py showmigrations teams | Select-String "0040" 

Write-Host ""
Write-Host "If migration 0040 shows [X], you're good. Otherwise run:" -ForegroundColor White
Write-Host "    python manage.py migrate teams" -ForegroundColor Cyan

Write-Host ""

# Step 6: Test API endpoints
Write-Host "[Step 6] Testing API availability..." -ForegroundColor Yellow
Write-Host "After updating settings.py, test with:" -ForegroundColor White
Write-Host "    python manage.py runserver" -ForegroundColor Cyan
Write-Host "    curl http://localhost:8000/teams/api/games/" -ForegroundColor Cyan

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Setup Instructions Complete!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Update deltacrown/settings.py (see instructions above)" -ForegroundColor White
Write-Host "2. Add create_team_advanced_view to apps/teams/views/public.py" -ForegroundColor White
Write-Host "3. Add URL pattern: path('create/advanced/', ...)" -ForegroundColor White
Write-Host "4. Test at: http://localhost:8000/teams/create/advanced/" -ForegroundColor White
Write-Host ""
Write-Host "See TASK3_IMPLEMENTATION_COMPLETE.md for full documentation." -ForegroundColor Cyan
Write-Host ""
