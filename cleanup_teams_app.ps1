# Teams App Cleanup Script - Automated Execution
# Date: October 9, 2025
# Based on comprehensive audit findings
# 
# This script safely removes verified unused/dead files from the Teams app
# All files are backed up before deletion for easy rollback

[CmdletBinding()]
param(
    [switch]$DryRun = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Success { param($msg) Write-Host $msg -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host $msg -ForegroundColor Yellow }
function Write-Info { param($msg) Write-Host $msg -ForegroundColor Cyan }
function Write-Error { param($msg) Write-Host $msg -ForegroundColor Red }

# Banner
Write-Host ""
Write-Info "═══════════════════════════════════════════════════════════"
Write-Info "   Teams App Cleanup Script - DeltaCrown Project"
Write-Info "═══════════════════════════════════════════════════════════"
Write-Host ""

# Verify we're in the right directory
$BasePath = "g:\My Projects\WORK\DeltaCrown"
if (-not (Test-Path "$BasePath\manage.py")) {
    Write-Error "Error: Not in DeltaCrown project root!"
    Write-Host "Expected: $BasePath"
    exit 1
}

Set-Location $BasePath
Write-Success "✓ Project root verified: $BasePath"

# Create backup folder
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$BackupPath = "$BasePath\CLEANUP_BACKUP_$Timestamp"

if (-not $DryRun) {
    New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
    Write-Success "✓ Backup folder created: $BackupPath"
} else {
    Write-Warning "DRY RUN MODE - No files will be deleted"
    Write-Host ""
}

# Statistics
$FilesBackedUp = 0
$FilesDeleted = 0
$FilesNotFound = 0
$FoldersDeleted = 0

# Function to backup and delete file
function Remove-WithBackup {
    param(
        [string]$FilePath,
        [string]$Description
    )
    
    $RelativePath = $FilePath.Replace($BasePath + "\", "")
    
    if (Test-Path $FilePath) {
        Write-Host "  → $Description" -ForegroundColor White
        Write-Host "    Path: $RelativePath" -ForegroundColor DarkGray
        
        if (-not $DryRun) {
            # Backup
            $BackupFilePath = Join-Path $BackupPath $RelativePath
            $BackupDir = Split-Path $BackupFilePath -Parent
            
            if (-not (Test-Path $BackupDir)) {
                New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
            }
            
            Copy-Item $FilePath $BackupFilePath -Force
            Write-Host "    ✓ Backed up" -ForegroundColor Green
            
            # Delete
            Remove-Item $FilePath -Force
            Write-Host "    ✓ Deleted" -ForegroundColor Yellow
            
            $script:FilesBackedUp++
            $script:FilesDeleted++
        } else {
            Write-Host "    [DRY RUN] Would backup and delete" -ForegroundColor Magenta
        }
    } else {
        Write-Host "  → $Description" -ForegroundColor DarkGray
        Write-Host "    Path: $RelativePath" -ForegroundColor DarkGray
        Write-Host "    ⊗ Not found (already deleted?)" -ForegroundColor DarkGray
        $script:FilesNotFound++
    }
    
    Write-Host ""
}

# Confirmation prompt
if (-not $Force -and -not $DryRun) {
    Write-Host ""
    Write-Warning "⚠️  This script will delete the following:"
    Write-Host "   • 2 dead template files" -ForegroundColor White
    Write-Host "   • 2 empty management commands" -ForegroundColor White
    Write-Host "   • 1 empty signals file" -ForegroundColor White
    Write-Host "   • 2 unused CSS/JS files" -ForegroundColor White
    Write-Host "   • 1 unused static folder (modern/)" -ForegroundColor White
    Write-Host "   • 1 orphaned view file (manage_console.py)" -ForegroundColor White
    Write-Host ""
    Write-Warning "All files will be backed up to: $BackupPath"
    Write-Host ""
    
    $Response = Read-Host "Continue with cleanup? (yes/no)"
    if ($Response -ne "yes") {
        Write-Host "Cleanup cancelled by user." -ForegroundColor Yellow
        exit 0
    }
    Write-Host ""
}

# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP PHASE 1: Dead Templates
# ═══════════════════════════════════════════════════════════════════════════
Write-Info "┌─────────────────────────────────────────────────────────┐"
Write-Info "│ Phase 1/5: Removing Dead Templates                     │"
Write-Info "└─────────────────────────────────────────────────────────┘"
Write-Host ""

Remove-WithBackup `
    "$BasePath\templates\teams\team_public.html" `
    "Dead template (not rendered by any view)"

Remove-WithBackup `
    "$BasePath\templates\teams\ranking_badge.html" `
    "Dead template (not included anywhere)"

# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP PHASE 2: Empty Management Commands
# ═══════════════════════════════════════════════════════════════════════════
Write-Info "┌─────────────────────────────────────────────────────────┐"
Write-Info "│ Phase 2/5: Removing Empty Management Commands          │"
Write-Info "└─────────────────────────────────────────────────────────┘"
Write-Host ""

Remove-WithBackup `
    "$BasePath\apps\teams\management\commands\init_team_rankings.py" `
    "Empty management command stub"

Remove-WithBackup `
    "$BasePath\apps\teams\management\commands\initialize_ranking.py" `
    "Empty management command stub"

# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP PHASE 3: Empty Signals File
# ═══════════════════════════════════════════════════════════════════════════
Write-Info "┌─────────────────────────────────────────────────────────┐"
Write-Info "│ Phase 3/5: Removing Empty Signals File                 │"
Write-Info "└─────────────────────────────────────────────────────────┘"
Write-Host ""

Remove-WithBackup `
    "$BasePath\apps\teams\signals\ranking_signals.py" `
    "Empty signals file (duplicate of signals.py)"

# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP PHASE 4: Unused Static Assets
# ═══════════════════════════════════════════════════════════════════════════
Write-Info "┌─────────────────────────────────────────────────────────┐"
Write-Info "│ Phase 4/5: Removing Unused Static Assets               │"
Write-Info "└─────────────────────────────────────────────────────────┘"
Write-Host ""

Remove-WithBackup `
    "$BasePath\static\teams\css\team-detail.css" `
    "Unused CSS file (not referenced in templates)"

Remove-WithBackup `
    "$BasePath\static\teams\js\team-detail.js" `
    "Unused JS file (not referenced in templates)"

# Remove modern theme folder (contains unused files)
$ModernPath = "$BasePath\static\teams\modern"
if (Test-Path $ModernPath) {
    Write-Host "  → Unused modern theme folder" -ForegroundColor White
    Write-Host "    Path: static\teams\modern\" -ForegroundColor DarkGray
    
    if (-not $DryRun) {
        # Backup all files in modern folder
        $ModernFiles = Get-ChildItem $ModernPath -Recurse -File
        foreach ($File in $ModernFiles) {
            $RelPath = $File.FullName.Replace($BasePath + "\", "")
            $BackupFilePath = Join-Path $BackupPath $RelPath
            $BackupDir = Split-Path $BackupFilePath -Parent
            
            if (-not (Test-Path $BackupDir)) {
                New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
            }
            
            Copy-Item $File.FullName $BackupFilePath -Force
            $script:FilesBackedUp++
        }
        
        Write-Host "    ✓ Backed up $($ModernFiles.Count) files" -ForegroundColor Green
        
        # Delete folder
        Remove-Item $ModernPath -Recurse -Force
        Write-Host "    ✓ Deleted entire folder" -ForegroundColor Yellow
        
        $script:FoldersDeleted++
        $script:FilesDeleted += $ModernFiles.Count
    } else {
        $ModernFiles = Get-ChildItem $ModernPath -Recurse -File
        Write-Host "    [DRY RUN] Would backup $($ModernFiles.Count) files and delete folder" -ForegroundColor Magenta
    }
} else {
    Write-Host "  → Unused modern theme folder" -ForegroundColor DarkGray
    Write-Host "    Path: static\teams\modern\" -ForegroundColor DarkGray
    Write-Host "    ⊗ Not found (already deleted?)" -ForegroundColor DarkGray
    $script:FilesNotFound++
}

Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP PHASE 5: Orphaned View File
# ═══════════════════════════════════════════════════════════════════════════
Write-Info "┌─────────────────────────────────────────────────────────┐"
Write-Info "│ Phase 5/5: Removing Orphaned View File                 │"
Write-Info "└─────────────────────────────────────────────────────────┘"
Write-Host ""

Remove-WithBackup `
    "$BasePath\apps\teams\views\manage_console.py" `
    "Orphaned view (not in URLs, references missing template)"

# ═══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
Write-Host ""
Write-Info "═══════════════════════════════════════════════════════════"
Write-Info "   Cleanup Complete!"
Write-Info "═══════════════════════════════════════════════════════════"
Write-Host ""

if (-not $DryRun) {
    Write-Success "✓ Files backed up: $FilesBackedUp"
    Write-Success "✓ Files deleted: $FilesDeleted"
    Write-Success "✓ Folders deleted: $FoldersDeleted"
    if ($FilesNotFound -gt 0) {
        Write-Host "  Files not found: $FilesNotFound (already cleaned?)" -ForegroundColor DarkGray
    }
    Write-Host ""
    Write-Warning "Backup location: $BackupPath"
} else {
    Write-Warning "DRY RUN COMPLETED - No files were actually deleted"
    Write-Host "  Files that would be deleted: $($FilesDeleted + $FilesNotFound)" -ForegroundColor White
}

Write-Host ""
Write-Info "═══════════════════════════════════════════════════════════"
Write-Info "   Next Steps:"
Write-Info "═══════════════════════════════════════════════════════════"
Write-Host ""
Write-Host "1. Run Django checks:" -ForegroundColor White
Write-Host "   python manage.py check" -ForegroundColor DarkGray
Write-Host ""
Write-Host "2. Test team features:" -ForegroundColor White
Write-Host "   • Create team" -ForegroundColor DarkGray
Write-Host "   • Edit team" -ForegroundColor DarkGray
Write-Host "   • View team detail" -ForegroundColor DarkGray
Write-Host "   • Manage team settings" -ForegroundColor DarkGray
Write-Host ""
Write-Host "3. If issues occur, restore from backup:" -ForegroundColor White
Write-Host "   Copy-Item '$BackupPath\*' -Destination '$BasePath' -Recurse -Force" -ForegroundColor DarkGray
Write-Host ""
Write-Host "4. If all looks good, delete backup folder:" -ForegroundColor White
Write-Host "   Remove-Item '$BackupPath' -Recurse -Force" -ForegroundColor DarkGray
Write-Host ""
Write-Success "✓ Cleanup script finished successfully!"
Write-Host ""
