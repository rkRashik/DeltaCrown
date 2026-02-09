<#
.SYNOPSIS
    DeltaCrown Development Launcher
.DESCRIPTION
    Launches Django (0.0.0.0:8000), Celery, and Discord bot.
#>

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot

# ── 1. Auto-Detect Virtual Environment ────────────────────────────────────
if (Test-Path "$ProjectRoot\.venv\Scripts\python.exe") {
    $PyExe = "$ProjectRoot\.venv\Scripts\python.exe"
    $CeleryExe = "$ProjectRoot\.venv\Scripts\celery.exe"
    Write-Host "✅ Found Python in: .venv" -ForegroundColor Green
}
elseif (Test-Path "$ProjectRoot\venv\Scripts\python.exe") {
    $PyExe = "$ProjectRoot\venv\Scripts\python.exe"
    $CeleryExe = "$ProjectRoot\venv\Scripts\celery.exe"
    Write-Host "✅ Found Python in: venv" -ForegroundColor Green
}
else {
    Write-Host "❌ CRITICAL ERROR: Could not find python.exe." -ForegroundColor Red
    Write-Host "   Please ensure you have created the virtual environment."
    exit 1
}

Write-Host "------------------------------------------------" -ForegroundColor Cyan
Write-Host "   DeltaCrown - Dev Launcher" -ForegroundColor Cyan
Write-Host "------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

# ── 2. Django Server (Wi-Fi Enabled) ──────────────────────────────────────
# Updated to run on 0.0.0.0:8000 so you can access via Phone/LAN
Write-Host "Starting Django Server (0.0.0.0:8000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    '-NoExit', '-Command',
    "Set-Location '$ProjectRoot'; & '$PyExe' manage.py runserver 0.0.0.0:8000"
) -WindowStyle Normal

# ── 3. Celery Worker ──────────────────────────────────────────────────────
Write-Host "Starting Celery Worker..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    '-NoExit', '-Command',
    "Set-Location '$ProjectRoot'; & '$CeleryExe' -A deltacrown worker --pool=solo --loglevel=info"
) -WindowStyle Normal

# ── 4. Discord Bot ────────────────────────────────────────────────────────
Write-Host "Starting Discord Bot..." -ForegroundColor Magenta
Start-Process powershell -ArgumentList @(
    '-NoExit', '-Command',
    "Set-Location '$ProjectRoot'; & '$PyExe' manage.py run_discord_bot"
) -WindowStyle Normal

Write-Host ""
Write-Host "DONE: All 3 processes launched." -ForegroundColor Green
Write-Host "Info: Access via phone using http://YOUR_PC_IP:8000" -ForegroundColor Gray
Write-Host ""