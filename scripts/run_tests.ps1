# DeltaCrown Test Runner with Dockerized PostgreSQL
# Usage: .\scripts\run_tests.ps1 [test_path]
# Example: .\scripts\run_tests.ps1 tests/test_team_creation_regression.py

param(
    [string]$TestPath = "tests/",
    [switch]$NoBuild,
    [switch]$KeepAlive
)

$ErrorActionPreference = "Stop"

Write-Host "=== DeltaCrown Test Runner ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker availability
Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
try {
    docker version | Out-Null
} catch {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Docker is available" -ForegroundColor Green

# Step 2: Start test database container
Write-Host "[2/6] Starting test database container..." -ForegroundColor Yellow
Push-Location "$PSScriptRoot\..\ops"
try {
    if ($NoBuild) {
        docker-compose -f docker-compose.test.yml up -d
    } else {
        docker-compose -f docker-compose.test.yml up -d --build
    }
} catch {
    Write-Host "ERROR: Failed to start test database container" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location

# Step 3: Wait for database to be ready
Write-Host "[3/6] Waiting for database to be ready..." -ForegroundColor Yellow
$maxRetries = 30
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    $health = docker inspect --format='{{.State.Health.Status}}' deltacrown_test_db 2>$null
    if ($health -eq "healthy") {
        Write-Host "  ✓ Database is ready" -ForegroundColor Green
        break
    }
    $retryCount++
    Write-Host "  . Waiting for database (attempt $retryCount/$maxRetries)..." -ForegroundColor Gray
    Start-Sleep -Seconds 1
}

if ($retryCount -eq $maxRetries) {
    Write-Host "ERROR: Database failed to become ready" -ForegroundColor Red
    docker logs deltacrown_test_db
    exit 1
}

# Step 4: Set database URL
Write-Host "[4/6] Configuring test database connection..." -ForegroundColor Yellow
$env:DATABASE_URL_TEST = "postgresql://dcadmin:dcpass123@localhost:54329/deltacrown_test"
Write-Host "  ✓ DATABASE_URL_TEST set" -ForegroundColor Green

# Step 5: Run migrations
Write-Host "[5/6] Running database migrations..." -ForegroundColor Yellow
try {
    python manage.py migrate --settings=deltacrown.settings_test --no-input
    Write-Host "  ✓ Migrations completed" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Migrations failed" -ForegroundColor Red
    exit 1
}

# Step 6: Run tests
Write-Host "[6/6] Running tests: $TestPath" -ForegroundColor Yellow
Write-Host ""
pytest $TestPath -v --tb=short

$testExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "=== Test Run Complete ===" -ForegroundColor Cyan

# Cleanup
if (-not $KeepAlive) {
    Write-Host ""
    Write-Host "Stopping test database container..." -ForegroundColor Yellow
    Push-Location "$PSScriptRoot\..\ops"
    docker-compose -f docker-compose.test.yml down
    Pop-Location
    Write-Host "  ✓ Container stopped" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Test database container is still running (--KeepAlive flag)" -ForegroundColor Yellow
    Write-Host "To stop: docker-compose -f ops/docker-compose.test.yml down" -ForegroundColor Gray
}

exit $testExitCode

Write-Host "`n=== Test Run Complete ===" -ForegroundColor Cyan
exit $LASTEXITCODE
