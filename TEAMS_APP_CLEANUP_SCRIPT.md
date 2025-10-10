# Teams App Cleanup Script
**Based on Audit Completed:** October 9, 2025

## ✅ VERIFIED FINDINGS - Safe to Delete

### Investigation Results:
1. ✅ `team_public.html` - **NOT REFERENCED** anywhere (DEAD)
2. ✅ `ranking_badge.html` - **NOT REFERENCED** anywhere (DEAD)  
3. ✅ `manage_console.html` - **REFERENCED** but file **DOESN'T EXIST** (view will break!)
4. ✅ `team-detail.css` - **NOT REFERENCED** in templates (unused)
5. ✅ `team-detail.js` - **NOT REFERENCED** in templates (unused)
6. ✅ `static/teams/modern/` - Has CSS/JS but **NOT REFERENCED** in templates
7. ✅ Empty management commands confirmed
8. ✅ Empty signals file confirmed

---

## 🗑️ FILES TO DELETE - SAFE REMOVAL

### Category 1: Dead Templates (No References)
```powershell
# Dead template files - not rendered by any view or included anywhere
Remove-Item "g:\My Projects\WORK\DeltaCrown\templates\teams\team_public.html"
Remove-Item "g:\My Projects\WORK\DeltaCrown\templates\teams\ranking_badge.html"
```

### Category 2: Empty/Stub Python Files
```powershell
# Empty management commands
Remove-Item "g:\My Projects\WORK\DeltaCrown\apps\teams\management\commands\init_team_rankings.py"
Remove-Item "g:\My Projects\WORK\DeltaCrown\apps\teams\management\commands\initialize_ranking.py"

# Empty signals file (duplicate of signals.py)
Remove-Item "g:\My Projects\WORK\DeltaCrown\apps\teams\signals\ranking_signals.py"

# Empty utils init (but keep the package directory)
# Note: Keep the __init__.py even if empty as it makes utils/ a valid Python package
```

### Category 3: Unused Static Assets
```powershell
# CSS/JS files not referenced in any template
Remove-Item "g:\My Projects\WORK\DeltaCrown\static\teams\css\team-detail.css"
Remove-Item "g:\My Projects\WORK\DeltaCrown\static\teams\js\team-detail.js"

# Modern theme assets that are not referenced
Remove-Item -Recurse "g:\My Projects\WORK\DeltaCrown\static\teams\modern\"
```

---

## 🔧 FILES THAT NEED FIXING (Not Deletion)

### CRITICAL: Missing Template
```powershell
# Issue: manage_console.py line 35 references "teams/manage_console.html" but it doesn't exist
# This will cause a TemplateDoesNotExist error if that view is accessed

# OPTIONS:
# 1. Create the missing template, OR
# 2. Update manage_console.py to use existing template, OR
# 3. Delete manage_console.py if the feature is abandoned

# Recommended: Check if manage_console.py is actually used
```

**Check usage:**
```powershell
cd "g:\My Projects\WORK\DeltaCrown"
Select-String -Pattern "manage_console" -Path "apps\teams\urls.py"
Select-String -Pattern "manage_console" -Path "apps\teams\urls\*.py"
```

If **not in URLs**, then:
```powershell
# Delete the orphaned view file
Remove-Item "g:\My Projects\WORK\DeltaCrown\apps\teams\views\manage_console.py"
```

---

## 📝 COMPLETE CLEANUP POWERSHELL SCRIPT

```powershell
# Teams App Cleanup Script
# Run from project root: g:\My Projects\WORK\DeltaCrown

Write-Host "Starting Teams App Cleanup..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Set base path
$BasePath = "g:\My Projects\WORK\DeltaCrown"
Set-Location $BasePath

# Create backup folder
$BackupPath = "$BasePath\CLEANUP_BACKUP_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
Write-Host "Backup folder created: $BackupPath" -ForegroundColor Green

# Function to backup and delete
function Remove-WithBackup {
    param([string]$FilePath)
    
    if (Test-Path $FilePath) {
        $RelativePath = $FilePath.Replace($BasePath, "")
        $BackupFilePath = Join-Path $BackupPath $RelativePath
        $BackupDir = Split-Path $BackupFilePath -Parent
        
        # Create backup directory structure
        if (-not (Test-Path $BackupDir)) {
            New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        }
        
        # Copy to backup
        Copy-Item $FilePath $BackupFilePath -Force
        Write-Host "  Backed up: $RelativePath" -ForegroundColor Yellow
        
        # Delete original
        Remove-Item $FilePath -Force
        Write-Host "  Deleted: $RelativePath" -ForegroundColor Red
    } else {
        Write-Host "  Not found (skipped): $FilePath" -ForegroundColor DarkGray
    }
}

# 1. Delete Dead Templates
Write-Host "`n[1/4] Removing dead templates..." -ForegroundColor Cyan
Remove-WithBackup "$BasePath\templates\teams\team_public.html"
Remove-WithBackup "$BasePath\templates\teams\ranking_badge.html"

# 2. Delete Empty Management Commands
Write-Host "`n[2/4] Removing empty management commands..." -ForegroundColor Cyan
Remove-WithBackup "$BasePath\apps\teams\management\commands\init_team_rankings.py"
Remove-WithBackup "$BasePath\apps\teams\management\commands\initialize_ranking.py"

# 3. Delete Empty Signals File
Write-Host "`n[3/4] Removing empty signals file..." -ForegroundColor Cyan
Remove-WithBackup "$BasePath\apps\teams\signals\ranking_signals.py"

# 4. Delete Unused Static Assets
Write-Host "`n[4/4] Removing unused static assets..." -ForegroundColor Cyan
Remove-WithBackup "$BasePath\static\teams\css\team-detail.css"
Remove-WithBackup "$BasePath\static\teams\js\team-detail.js"

# Remove modern theme folder
if (Test-Path "$BasePath\static\teams\modern") {
    $ModernFiles = Get-ChildItem "$BasePath\static\teams\modern" -Recurse -File
    foreach ($File in $ModernFiles) {
        Remove-WithBackup $File.FullName
    }
    Remove-Item "$BasePath\static\teams\modern" -Recurse -Force
    Write-Host "  Deleted: static\teams\modern\ (entire folder)" -ForegroundColor Red
}

# Summary
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "Cleanup Complete!" -ForegroundColor Green
Write-Host "Backup location: $BackupPath" -ForegroundColor Yellow
Write-Host "`nFiles removed:" -ForegroundColor Cyan
Write-Host "  - 2 dead templates" -ForegroundColor White
Write-Host "  - 2 empty management commands" -ForegroundColor White
Write-Host "  - 1 empty signals file" -ForegroundColor White
Write-Host "  - 2 unused CSS/JS files" -ForegroundColor White
Write-Host "  - 1 unused static folder (modern/)" -ForegroundColor White
Write-Host "`nTotal: ~7-10 files removed" -ForegroundColor Green

Write-Host "`n⚠️  NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Check if manage_console.py is used (see report)" -ForegroundColor White
Write-Host "2. Run tests to verify nothing broke" -ForegroundColor White
Write-Host "3. Test team creation/management features" -ForegroundColor White
Write-Host "4. If issues occur, restore from: $BackupPath" -ForegroundColor White
```

---

## 🔍 POST-CLEANUP VERIFICATION

### Step 1: Check for Broken References
```powershell
# Check if any Python files reference deleted templates
cd "g:\My Projects\WORK\DeltaCrown"
Select-String -Pattern "team_public\.html" -Path "apps\teams\**\*.py" -Recurse
Select-String -Pattern "ranking_badge\.html" -Path "apps\teams\**\*.py" -Recurse

# Should return NO RESULTS (confirmed already)
```

### Step 2: Check manage_console.py Usage
```powershell
# Is it imported anywhere?
Select-String -Pattern "manage_console" -Path "apps\teams\**\*.py" -Recurse

# Is it in URLs?
Select-String -Pattern "manage_console" -Path "apps\teams\urls*.py"
```

### Step 3: Run Django Checks
```powershell
python manage.py check
python manage.py check --deploy
```

### Step 4: Test Team Features
```powershell
# Start dev server
python manage.py runserver

# Manually test:
# - Create team
# - Edit team
# - Invite member
# - View team detail
# - Access team settings
```

---

## 🚨 ROLLBACK PROCEDURE (If Something Breaks)

If cleanup causes issues:

```powershell
# Find your backup folder
$BackupPath = "g:\My Projects\WORK\DeltaCrown\CLEANUP_BACKUP_20251009_*"
$BackupFolder = Get-Item $BackupPath | Sort-Object LastWriteTime -Descending | Select-Object -First 1

# Restore all files
Write-Host "Restoring from: $($BackupFolder.FullName)" -ForegroundColor Yellow
Copy-Item "$($BackupFolder.FullName)\*" -Destination "g:\My Projects\WORK\DeltaCrown\" -Recurse -Force

Write-Host "Restore complete!" -ForegroundColor Green
```

---

## 📊 CLEANUP IMPACT SUMMARY

### Before Cleanup:
- **Templates:** 26 files
- **Management Commands:** 9 files  
- **Static Assets:** Multiple CSS/JS + modern/ folder
- **Signal Files:** 2 locations (1 empty)

### After Cleanup:
- **Templates:** 24 files (-2 dead templates)
- **Management Commands:** 7 files (-2 empty stubs)
- **Static Assets:** Minimal active files only (-3 unused)
- **Signal Files:** 1 active location (-1 empty)

### Storage Saved: ~15-20 KB (negligible but improves code clarity)
### Maintenance Burden Reduced: 🟢 MEDIUM (fewer confusing files)
### Risk Level: 🟢 VERY LOW (all deletions verified as unused)

---

## ⚠️ WHAT WE'RE **NOT** DELETING (And Why)

### Migrations (ALL KEPT)
- **Reason:** Deleting applied migrations breaks Django's migration history
- **Even broken/duplicate migrations MUST stay** if applied to database
- **Future:** Can squash on fresh database only

### Model Files (ALL KEPT)
- `models/team.py` - Wrapper pattern (valid architecture)
- `models/_legacy.py` - Actual source (required)
- All other model files - Actively used

### Utils Package (KEPT)
- `utils/` directory - Contains active ranking utilities
- `utils/__init__.py` - Makes it a valid package (needed)
- `utils.py` - Top-level utilities (actively imported)

### Signals (KEPT)
- `signals.py` - Active comprehensive signals (166 lines)
- `signals/__init__.py` - Package marker (may be needed)

### Templates (Most KEPT)
- Only deleting 2 verified-dead templates
- All others are actively rendered by views

---

## 📋 FINAL CHECKLIST

Before running cleanup script:

- [ ] Read full audit report
- [ ] Backup database (`python manage.py dumpdata > backup.json`)
- [ ] Commit current code to git
- [ ] Review files to be deleted one more time
- [ ] Run cleanup script
- [ ] Run `python manage.py check`
- [ ] Test team features manually
- [ ] Run test suite if available
- [ ] Commit cleanup changes

**If any issues:**
- [ ] Use rollback procedure
- [ ] Document what broke in audit report
- [ ] Investigate before retrying

---

## 🎯 CONCLUSION

**Total Files to Delete:** ~7-10 files
**Risk Level:** 🟢 **VERY LOW** (all verified as unused)
**Time Required:** ~5 minutes
**Testing Required:** ~15 minutes
**Recommended:** ✅ **SAFE TO PROCEED**

This cleanup removes only genuinely unused files while preserving all active code, migrations, and architecture patterns. The backup script ensures easy rollback if needed.

---

**Prepared by:** GitHub Copilot  
**Date:** October 9, 2025  
**Status:** ✅ Ready for Execution
