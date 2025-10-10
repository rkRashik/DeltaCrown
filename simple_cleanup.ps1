# ============================================================================
# DeltaCrown Teams App - Simple Cleanup Script
# ============================================================================
# Purpose: Fix critical issues and verify system health
# Date: October 9, 2025
# ============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "DeltaCrown Teams App - Quick Cleanup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Continue"

# Step 1: Verify Django system check
Write-Host "[1/4] Running Django system check..." -ForegroundColor Yellow
python manage.py check teams

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Status: PASSED" -ForegroundColor Green
} else {
    Write-Host "  Status: FAILED - Please review errors above" -ForegroundColor Red
}

# Step 2: Check migration status
Write-Host ""
Write-Host "[2/4] Checking migrations..." -ForegroundColor Yellow
Write-Host "  Current migration status for teams app:" -ForegroundColor Gray
python manage.py showmigrations teams

Write-Host ""
Write-Host "  Checking for pending migrations..." -ForegroundColor Gray
python manage.py makemigrations --dry-run teams

Write-Host ""
Write-Host "  Generate migrations if needed? (Y/N)" -ForegroundColor Cyan
$response = Read-Host

if ($response -eq "Y" -or $response -eq "y") {
    python manage.py makemigrations teams
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "  Apply migrations now? (Y/N)" -ForegroundColor Cyan
        $applyResponse = Read-Host
        
        if ($applyResponse -eq "Y" -or $applyResponse -eq "y") {
            python manage.py migrate teams
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Status: Migrations applied successfully" -ForegroundColor Green
            } else {
                Write-Host "  Status: Migration failed" -ForegroundColor Red
            }
        }
    }
}

# Step 3: Remove debug statements
Write-Host ""
Write-Host "[3/4] Checking for debug print statements..." -ForegroundColor Yellow

$socialFile = "apps\teams\views\social.py"
if (Test-Path $socialFile) {
    $content = Get-Content $socialFile -Raw
    
    if ($content -like '*print(f"DEBUG*') {
        Write-Host "  Found debug print statements" -ForegroundColor Yellow
        Write-Host "  Remove them? (Y/N)" -ForegroundColor Cyan
        $removeResponse = Read-Host
        
        if ($removeResponse -eq "Y" -or $removeResponse -eq "y") {
            # Backup
            $backupDir = "backup_pre_cleanup"
            if (-not (Test-Path $backupDir)) {
                New-Item -ItemType Directory -Path $backupDir | Out-Null
            }
            Copy-Item $socialFile "$backupDir\social.py.backup" -Force
            Write-Host "  Backed up original file" -ForegroundColor Green
            
            # Remove debug lines
            $lines = Get-Content $socialFile
            $cleanLines = $lines | Where-Object { $_ -notlike '*print(f"DEBUG*' }
            Set-Content -Path $socialFile -Value $cleanLines
            
            Write-Host "  Status: Debug statements removed" -ForegroundColor Green
        }
    } else {
        Write-Host "  Status: No debug statements found" -ForegroundColor Green
    }
} else {
    Write-Host "  Status: File not found" -ForegroundColor Red
}

# Step 4: Generate report
Write-Host ""
Write-Host "[4/4] Generating cleanup report..." -ForegroundColor Yellow

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$reportFile = "CLEANUP_EXECUTION_REPORT.txt"

$report = @"
DeltaCrown Teams App - Cleanup Report
======================================
Generated: $timestamp

COMPLETED CHECKS:
-----------------
1. Django system check
2. Migration status verification
3. Debug statement cleanup
4. Report generation

BACKUP CREATED:
---------------
backup_pre_cleanup/social.py.backup (if debug removal performed)

NEXT STEPS:
-----------
1. Review full audit: CLEANUP_REPORT.md
2. Run test suite: pytest tests/
3. Manual testing (see checklist in CLEANUP_REPORT.md)
4. If all tests pass, proceed to Task 6/7

STATUS: Cleanup completed
"@

Set-Content -Path $reportFile -Value $report
Write-Host "  Report saved: $reportFile" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cleanup Completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Review: CLEANUP_REPORT.md" -ForegroundColor Gray
Write-Host "  2. Review: $reportFile" -ForegroundColor Gray
Write-Host "  3. Test: python manage.py runserver" -ForegroundColor Gray
Write-Host "  4. Navigate to: http://127.0.0.1:8000/teams/" -ForegroundColor Gray
Write-Host ""

Write-Host "Open cleanup reports? (Y/N)" -ForegroundColor Cyan
$openResponse = Read-Host

if ($openResponse -eq "Y" -or $openResponse -eq "y") {
    code CLEANUP_REPORT.md
    code $reportFile
}

Write-Host ""
Write-Host "Cleanup script completed!" -ForegroundColor Green
Write-Host ""
