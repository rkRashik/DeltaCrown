# Tournament System Removal - Migration Plan

**Date:** November 2, 2025  
**Operation:** Move tournament and game apps to backup_legacy folder  
**Goal:** Clean system for new tournament engine while keeping other apps functional

---

## ⚠️ CRITICAL WARNING

This operation will:
1. **DISABLE tournament functionality** completely
2. **BREAK dependencies** in teams, dashboard, notifications, user_profile apps
3. **REMOVE database tables** for tournaments and games
4. System will RUN but tournament-related features will be BROKEN

---

## 📋 Step-by-Step Migration Plan

### Phase 1: Create Backup (SAFE - Reversible)
1. Create `backup_legacy/` folder
2. Move apps to backup:
   - `apps/tournaments/` → `backup_legacy/tournaments/`
   - `apps/game_valorant/` → `backup_legacy/game_valorant/`
   - `apps/game_efootball/` → `backup_legacy/game_efootball/`
3. Move templates:
   - `templates/tournaments/` → `backup_legacy/templates/tournaments/`
4. Move static files:
   - `static/tournaments/` → `backup_legacy/static/tournaments/`

### Phase 2: Remove from INSTALLED_APPS (System will still run)
Update `deltacrown/settings.py`:
```python
# Remove these lines:
# "apps.tournaments.apps.TournamentsConfig",
# "apps.game_valorant",
# "apps.game_efootball",
```

### Phase 3: Remove URL Routes (Breaks tournament URLs)
Update `deltacrown/urls.py`:
```python
# Comment out:
# path("tournaments/", include(...)),
# path("api/tournaments/", include(...)),
```

### Phase 4: Fix Dependent Apps (CRITICAL)
Apps that reference tournaments:

#### A. **apps/teams/** (MANY REFERENCES)
- Remove tournament registration imports
- Comment out tournament-related views
- Keep team core functionality

#### B. **apps/dashboard/** (Safe - Uses lazy imports)
- Already uses `_get_model()` for optional imports
- Will gracefully fail if tournaments not found

#### C. **apps/notifications/** (DATABASE ISSUE)
- Has foreign keys to Tournament and Match models
- **BREAKING:** migrations reference tournaments.Tournament
- **Options:**
  1. Keep old migrations, drop tables manually
  2. Create new migration to remove FKs
  3. Keep notification tournament fields NULL

#### D. **apps/user_profile/** (Minimal impact)
- Remove tournament-related views/imports
- Keep profile core functionality

#### E. **apps/economy/** (Check coin awards)
- May have tournament participation rewards
- Keep if no tournament dependencies

### Phase 5: Database Cleanup (DESTRUCTIVE)
```sql
-- Drop tournament tables (manual SQL)
DROP TABLE IF EXISTS tournaments_registration CASCADE;
DROP TABLE IF EXISTS tournaments_match CASCADE;
DROP TABLE IF EXISTS tournaments_bracket CASCADE;
DROP TABLE IF EXISTS tournaments_tournament CASCADE;
-- ... (20+ more tables)

DROP TABLE IF EXISTS game_valorant_valorantconfig CASCADE;
DROP TABLE IF EXISTS game_efootball_efootballconfig CASCADE;
```

---

## 🚨 Problems This Will Cause

### 1. **Notification App** (CRITICAL)
```python
# apps/notifications/models.py has:
tournament = ForeignKey('tournaments.Tournament')  # BREAKS
match = ForeignKey('tournaments.Match')  # BREAKS
```

**Impact:** Notification app won't migrate, existing notifications broken

**Solutions:**
- **Option A:** Make FKs nullable, keep old data
- **Option B:** Drop notification tables, start fresh
- **Option C:** Keep notifications but remove tournament FKs

### 2. **Teams App** (HIGH)
Multiple files import from tournaments:
- `teams/views/public.py` - Registration display
- `teams/tasks.py` - Tournament notifications
- `teams/services/tournament_registration.py` - ENTIRE FILE
- `teams/api_views.py` - Tournament team queries

**Impact:** Some team views will crash

**Solutions:**
- Wrap imports in try/except
- Remove tournament-specific views temporarily
- Comment out tournament task functions

### 3. **Dashboard App** (MEDIUM - Already handled)
Uses lazy imports via `_get_model()`:
```python
Match = _get_model("tournaments.Match")
if Match:  # Safe - returns None if not found
    # use Match
```

**Impact:** Dashboard will work, but tournament sections empty

### 4. **User Profile** (LOW)
Few references:
- `user_profile/views_public.py` - Match history display

**Impact:** Profile match history will be empty

---

## ✅ Recommended Approach

### Conservative Approach (RECOMMENDED)
**Keep system running with minimal breakage:**

1. **Move apps to backup_legacy/** ✅ Safe
2. **Comment out from INSTALLED_APPS** ✅ Safe
3. **Comment out URL routes** ✅ Breaks tournament URLs only
4. **Wrap imports in try/except blocks** ✅ Graceful degradation
5. **DON'T drop database tables yet** ✅ Reversible
6. **Test system** ✅ Verify other apps work

### Aggressive Approach (NOT RECOMMENDED)
**Complete cleanup:**

1. Move apps ❌ Risk
2. Drop database tables ❌ IRREVERSIBLE
3. Remove all imports ❌ Time-consuming
4. Fix all dependent code ❌ Complex

---

## 🔧 Implementation Steps

### Step 1: Backup Everything
```powershell
# Create backup directory
New-Item -ItemType Directory -Path "G:\My Projects\WORK\DeltaCrown\backup_legacy"

# Copy (don't move yet) for safety
Copy-Item -Recurse "apps/tournaments" "backup_legacy/"
Copy-Item -Recurse "apps/game_valorant" "backup_legacy/"
Copy-Item -Recurse "apps/game_efootball" "backup_legacy/"
Copy-Item -Recurse "templates/tournaments" "backup_legacy/templates/" -ErrorAction SilentlyContinue
Copy-Item -Recurse "static/tournaments" "backup_legacy/static/" -ErrorAction SilentlyContinue
```

### Step 2: Database Backup
```powershell
# Backup PostgreSQL database
pg_dump -U dc_user -h localhost deltacrown > backup_legacy/deltacrown_backup_$(Get-Date -Format "yyyyMMdd_HHmmss").sql
```

### Step 3: Comment Out in Settings
Edit `deltacrown/settings.py` - comment out tournament apps

### Step 4: Test
```powershell
python manage.py check
python manage.py runserver
# Visit: http://localhost:8000/
# Test: Teams, Dashboard, Profile (NOT tournaments)
```

### Step 5: If Tests Pass, Move Apps
```powershell
Move-Item "apps/tournaments" "backup_legacy/"
Move-Item "apps/game_valorant" "backup_legacy/"
Move-Item "apps/game_efootball" "backup_legacy/"
```

---

## 🎯 Expected Result

### ✅ Will Work:
- User authentication (accounts)
- User profiles (user_profile)
- Team management (teams core features)
- Dashboard (with empty tournament sections)
- Notifications (with null tournament references)
- Economy (DeltaCoins)
- E-commerce
- Site UI

### ❌ Will Break:
- All tournament URLs (/tournaments/*)
- Tournament registration
- Match management
- Tournament admin
- Game-specific configurations
- Tournament notifications
- Team tournament integration

### ⚠️ Partial Functionality:
- Teams (core works, tournament features fail)
- Dashboard (displays, but no tournament data)
- Notifications (works, but tournament notifs fail)

---

## 🔄 Rollback Plan

If something breaks:

```powershell
# 1. Restore apps
Move-Item "backup_legacy/tournaments" "apps/"
Move-Item "backup_legacy/game_valorant" "apps/"
Move-Item "backup_legacy/game_efootball" "apps/"

# 2. Uncomment in settings.py

# 3. Restart server
python manage.py runserver
```

---

## 📝 Recommendation

**I STRONGLY RECOMMEND:**

1. **Do NOT drop database tables** - Keep data for reference
2. **Do NOT remove imports aggressively** - Wrap in try/except instead
3. **Test thoroughly** after each step
4. **Keep backup_legacy/** indefinitely for reference

**Better Approach:**
- Build new tournament engine alongside old one
- Gradually migrate features
- Deprecate old system when new one is ready
- Then cleanup

**Reason:**
- Removing tournament system will break many integrations
- Fixing all dependencies is time-consuming and risky
- Better to build new system first, then remove old one

---

## ❓ Your Decision Needed

**Option 1: Conservative (Recommended)**
- Move apps to backup_legacy
- Comment out from settings
- Wrap imports in try/except
- Keep database tables
- **Result:** System runs, tournament features disabled

**Option 2: Aggressive (Risky)**
- Move apps to backup_legacy
- Drop all database tables
- Remove all imports
- Fix all dependent code
- **Result:** Clean system, but may break unexpectedly

**Which approach should I proceed with?**
