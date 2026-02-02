#!/usr/bin/env pwsh
# Test runner script for Windows PowerShell
# Loads .env.test and runs Phase 1 team creation API tests

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "`n=== DeltaCrown Phase 1 Test Runner ===" -ForegroundColor Cyan

# Load .env.test if it exists
$envTestFile = Join-Path (Join-Path $PSScriptRoot "..") ".env.test"
if (Test-Path $envTestFile) {
    Write-Host "Loading environment from .env.test..." -ForegroundColor Green
    Get-Content $envTestFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
            Write-Host "  Set $name" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "No .env.test file found at $envTestFile" -ForegroundColor Yellow
}

# Validate DATABASE_URL_TEST is set
if (-not $env:DATABASE_URL_TEST) {
    Write-Host "ERROR: DATABASE_URL_TEST environment variable is not set" -ForegroundColor Red
    Write-Host "Please create .env.test with DATABASE_URL_TEST or set it manually" -ForegroundColor Yellow
    exit 1
}

Write-Host "DATABASE_URL_TEST is set" -ForegroundColor Green

# Set Django settings module
$env:DJANGO_SETTINGS_MODULE = "deltacrown.settings_test"
Write-Host "Using settings module: deltacrown.settings_test" -ForegroundColor Gray

# Run Django system check
Write-Host "`nRunning Django system check..." -ForegroundColor Cyan
python manage.py check
if ($LASTEXITCODE -ne 0) {
    Write-Host "Django system check failed" -ForegroundColor Red
    exit $LASTEXITCODE
}

# Run pytest
Write-Host "`nRunning Phase 1 tests..." -ForegroundColor Cyan
pytest apps/organizations/tests/test_team_creation_api.py -v --tb=short --reuse-db

Write-Host "`n=== Test Run Complete ===" -ForegroundColor Cyan
exit $LASTEXITCODE
