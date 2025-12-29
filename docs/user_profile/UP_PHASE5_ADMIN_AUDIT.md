# UP_PHASE5_ADMIN_AUDIT.md

**Phase:** 5A - Deep System Audit  
**Date:** December 28, 2025  
**Status:** 🔍 **ADMIN CONFIGURATION AUDIT COMPLETE**

---

## 🎯 MISSION

Audit Django Admin configuration to identify:
1. Duplicate controls (legacy fields + inlines for new models)
2. Confusing model names (Achievement vs Badge)
3. Orphaned inlines (SocialLink never used)
4. Unsafe actions that need safeguards
5. Missing computed fields for operators

---

## 📂 ADMIN INVENTORY

| Model | Admin Class | Status | Issues |
|-------|-------------|--------|--------|
| UserProfile | ✅ Registered | Active | Duplicate fields |
| PrivacySettings | ✅ Registered | Active | None |
| VerificationRecord | ✅ Registered | Active | None |
| Badge | ✅ Registered | Active | Confusing name |
| UserBadge | ✅ Registered | Active | None |
| SocialLink | ✅ Registered | ⚠️ Orphaned | Unused model |
| GameProfile | ✅ Registered | Active | Complex but working |
| GameProfileAlias | ✅ Registered | Active | None |
| GameProfileConfig | ✅ Registered | Active | None |
| Achievement | ✅ Registered | Active | Confusing name |
| Match | ✅ Registered | ⚠️ Placeholder | Unused fields |
| Certificate | ✅ Registered | Active | None |
| UserActivity | ✅ Registered | 🔴 Orphaned | No writes |
| UserProfileStats | ✅ Registered | 🔴 Orphaned | No reads |
| UserAuditEvent | ✅ Registered | Active | Working |

**Total Models:** 15  
**Active:** 10  
**Orphaned:** 3 (SocialLink, UserActivity, UserProfileStats)  
**Placeholder:** 1 (Match)

---

## 🚨 CRITICAL ISSUE #1: DUPLICATE PRIVACY CONTROLS

### **Location:** `UserProfileAdmin` Line 149-280

**Problem:** UserProfile admin shows **BOTH** legacy privacy fields **AND** PrivacySettings inline.

**Evidence:**

1. **Legacy fields in list_filter (Line 170):**
```python
list_filter = [
    'kyc_status',
    'region',
    'is_private',  # ❌ LEGACY FIELD (should not exist)
    'stream_status',
    'created_at',
]
```

2. **No fieldset for legacy privacy fields** (Good! They're hidden)

3. **But PrivacySettings inline exists (Line 273):**
```python
inlines = [
    PrivacySettingsInline,  # ✅ NEW SYSTEM (15 fields)
    SocialLinkInline,       # ❌ ORPHANED (no views use it)
    GameProfileInline,      # ✅ WORKING
    UserBadgeInline,        # ✅ WORKING
]
```

**Confusion:**
- Admin sees `is_private` in list filter
- Admin clicks profile → sees PrivacySettings inline with 15 granular fields
- **Which one is canonical?** Operator doesn't know!

**Fix Required:**
1. Remove `is_private` from `list_filter`
2. Add computed field `privacy_profile_visibility` (reads from PrivacySettings)
3. Keep PrivacySettings inline only

---

## 🚨 CRITICAL ISSUE #2: SOCIAL LINKS DUPLICATE SYSTEM

### **Location:** `UserProfileAdmin` Line 227-242

**Problem:** UserProfile admin has **"Legacy Social Links" fieldset** but also **SocialLink inline**.

**Evidence:**

1. **Legacy Social Links fieldset (Line 227-242):**
```python
('Legacy Social Links', {
    'description': 'Note: New social links use SocialLink model (see inline below)',
    'fields': [
        'youtube_link',   # ❌ Direct UserProfile field
        'twitch_link',    # ❌ Direct UserProfile field
        'discord_id',     # ❌ Direct UserProfile field
        'facebook',       # ❌ Direct UserProfile field
        'instagram',      # ❌ Direct UserProfile field
        'tiktok',         # ❌ Direct UserProfile field
        'twitter',        # ❌ Direct UserProfile field
        'stream_status',  # ❌ Direct UserProfile field
    ],
    'classes': ['collapse']  # Hidden by default (good)
}),
```

2. **SocialLink inline (Line 274):**
```python
SocialLinkInline,  # ❌ Points to SocialLink model (never used by views)
```

**Backend Reality (from UP_PHASE5_BACKEND_REALITY.md):**
- Settings form writes to UserProfile direct fields
- SocialLink model has NO view references (0 reads, 0 writes)
- Frontend reads UserProfile direct fields

**Operator Confusion:**
- Admin sees "Note: New social links use SocialLink model" 
- But settings form doesn't use SocialLink model!
- **Which should admin edit?**

**Fix Required:**
1. Delete SocialLink model (unused)
2. Remove SocialLinkInline
3. Rename fieldset to "Social Links" (remove "Legacy")
4. Keep UserProfile direct fields (they work)

---

## ⚠️ ISSUE #3: ACHIEVEMENT VS BADGE NAMING CONFUSION

### **Two Similar Models:**

| Model | Purpose | Admin | Evidence |
|-------|---------|-------|----------|
| Badge | System-defined achievements | BadgeAdmin | 622 lines |
| Achievement | User-specific achievements? | AchievementAdmin | 988 lines |

**Problem:** What's the difference?

**Badge Model:**
```python
class Badge(models.Model):
    name = models.CharField(max_length=100, unique=True)
    emoji = models.CharField(max_length=10, default="🏆")
    description = models.TextField()
    category = models.CharField(...)
    # System-defined, manually created in admin
```

**Achievement Model:**
```python
class Achievement(models.Model):
    user = models.ForeignKey(User, ...)
    title = models.CharField(max_length=200)
    description = models.TextField()
    earned_at = models.DateTimeField(auto_now_add=True)
    # User-specific accomplishment records
```

**UserBadge Model:**
```python
class UserBadge(models.Model):
    user = models.ForeignKey(User, ...)
    badge = models.ForeignKey(Badge, ...)  # Links to Badge, not Achievement
    earned_at = models.DateTimeField(auto_now_add=True)
    # Junction table for user ↔ badge
```

**Confusion:**
- Badge → system achievements (like "First Blood", "Champion")
- Achievement → user-specific records (like tournament wins, milestones)
- But naming is unclear: "Achievement" sounds like a template, "Badge" sounds like an instance

**Operator Impact:**
- "Should I create a Badge or Achievement for tournament winner?"
- "Why are there two achievement systems?"

**Fix Options:**

**Option A: Rename for Clarity**
- Badge → AchievementTemplate
- UserBadge → UserAchievement
- Achievement → Milestone

**Option B: Merge Models**
- Keep Badge only
- Merge Achievement into Badge with `is_system` flag

**Recommendation:** Option A (rename) - least disruptive.

---

## 🔴 ISSUE #4: ORPHANED ADMIN - UserActivity

### **Location:** Line 1083-1145

**Problem:** UserActivity admin exists but **NO VIEWS WRITE EVENTS**.

**Admin Features:**
- Read-only list view
- Event type filter
- Metadata preview
- `has_add_permission = False`
- `has_delete_permission = False`

**Backend Reality:**
- Model exists (apps/user_profile/models/activity.py, 168 lines)
- Event log design (profile_updated, passport_created, achievement_earned, etc.)
- **0 views call UserActivity.objects.create()**
- **0 signals emit events**

**Admin Impact:**
- Operator sees "User Activity" in sidebar
- Clicks → empty table (always)
- Confusion: "Is this broken? Why no events?"

**Fix Required:**
1. Delete UserActivity model
2. Unregister UserActivityAdmin
3. Remove from `admin.py` imports

---

## 🔴 ISSUE #5: ORPHANED ADMIN - UserProfileStats

### **Location:** Line 1146-1334

**Problem:** UserProfileStats admin exists but **NO VIEWS READ STATS**.

**Admin Features:**
- Read-only list view
- "Recompute Stats" action
- "Reconcile Economy" action
- Shows: deltacoin_balance, tournaments, matches, teams

**Backend Reality:**
- Model exists (apps/user_profile/models/stats.py, 273 lines)
- Derived projection (computed from other tables)
- **0 views query UserProfileStats**
- Profile page reads UserProfile.deltacoin_balance directly

**Admin Impact:**
- Operator sees "User Profile Stats" in sidebar
- Clicks → table exists but data might be stale
- **Recompute action doesn't help** (nothing reads this table)

**Fix Required:**
1. Delete UserProfileStats model
2. Unregister UserProfileStatsAdmin
3. Remove from `admin.py` imports
4. Keep stats computation logic in services (for future)

---

## ⚠️ ISSUE #6: MATCH ADMIN IS PLACEHOLDER

### **Location:** Line 1008-1038

**Problem:** Match model exists but fields are unused.

**Admin Shows:**
```python
list_display = [
    'user',
    'game',
    'result',
    'kills',
    'deaths',
    'played_at',
]
```

**Backend Reality:**
- UserProfile has `matches_played`, `matches_won` fields (placeholders)
- Match model is registered but **no tournament system writes to it**
- Fields exist but data is never populated

**Admin Impact:**
- Operator sees "Matches" in sidebar
- Clicks → empty table (no matches recorded)
- Confusion: "Where are the match results?"

**Fix Options:**

**Option A: Remove Match Admin (Recommended)**
- Keep model (for future)
- Unregister admin (hide from sidebar)
- Re-register when tournament system writes matches

**Option B: Delete Match Model**
- Remove completely
- Re-implement when needed

**Recommendation:** Option A (future-proofing).

---

## ⚠️ ISSUE #7: GAME PROFILES JSON DEPRECATION WARNING

### **Location:** Line 243-257

**Problem:** Admin shows "Legacy Game Profiles (JSON - DEPRECATED)" fieldset with scary warning.

**Evidence:**
```python
('Legacy Game Profiles (JSON - DEPRECATED)', {
    'description': '''
        ⚠️ <strong>TRANSITIONAL:</strong> Game data now managed via Game Passport system (GameProfile model).<br>
        This JSON field is deprecated and will be removed in Phase 4.<br>
        <strong>Use the Game Passport inline editor below instead.</strong>
    ''',
    'fields': ['game_profiles'],
    'classes': ['collapse']  # Hidden by default
}),
```

**Admin Impact:**
- Operator sees red warning
- **Confusion:** "Is game_profiles broken? Should I migrate data?"
- **Reality:** JSON field is still in DB but not used by frontend

**Fix Required:**
1. Remove `game_profiles` from fieldsets (don't show in admin)
2. Keep field in model for data safety (don't drop column yet)
3. Remove warning message
4. Migration in Phase 5D will drop column after verification

---

## ✅ WORKING ADMINS

### **GameProfile Admin (GP-0) - Excellent**

**Location:** Line 667-898

**Features:**
- Identity change tracking (GameProfileAlias inline)
- Cooldown enforcement (locked_until display)
- Pin management (is_pinned toggle)
- Privacy controls (visibility field)
- LFT badge (is_lft field)
- Audit integration (change history)

**Status:** ✅ **PRODUCTION-READY**

**Evidence:**
- Lock status display helper (Line 697-709)
- Identity key computed field (Line 711-716)
- Alias inline registered (Line 83-135)
- All CRUD operations audited

**No Issues Found.**

---

### **PrivacySettings Admin - Clean**

**Location:** Line 436-498

**Features:**
- 15 granular privacy fields
- User link helper
- Date filters

**Status:** ✅ **WORKING**

**No Issues Found.**

---

### **Badge Admin - Simple**

**Location:** Line 595-619

**Features:**
- List display with emoji + name
- Category filter
- Search by name

**Status:** ✅ **WORKING** (but see naming confusion Issue #3)

---

### **UserBadge Admin - Junction Table**

**Location:** Line 620-643

**Features:**
- Shows user ↔ badge relationships
- Earned date tracking
- Pin status

**Status:** ✅ **WORKING**

---

### **Certificate Admin - Working**

**Location:** Line 1039-1082

**Features:**
- Certificate management
- Thumbnail preview
- Download links

**Status:** ✅ **WORKING**

**No Issues Found.**

---

## 📊 ADMIN UX ISSUES

### **Issue 8: Sidebar Clutter**

**Problem:** 15 models in User Profile section = overwhelming sidebar.

**Current Sidebar:**
```
User Profile
├── User Profiles (UserProfile)
├── Privacy Settings (PrivacySettings)
├── Verification Records (VerificationRecord)
├── Badges (Badge)
├── User Badges (UserBadge)
├── Social Links (SocialLink) ← ORPHANED
├── Game Profiles (GameProfile)
├── Game Profile Aliases (GameProfileAlias)
├── Game Profile Configs (GameProfileConfig)
├── Achievements (Achievement) ← CONFUSING NAME
├── Matches (Match) ← PLACEHOLDER
├── Certificates (Certificate)
├── User Activities (UserActivity) ← ORPHANED
├── User Profile Stats (UserProfileStats) ← ORPHANED
└── User Audit Events (UserAuditEvent)
```

**Improvement:**
1. Remove 3 orphaned admins → 12 models
2. Hide Match admin → 11 models
3. Group related models with `Meta.verbose_name_plural`:
   - Core: UserProfile, PrivacySettings, VerificationRecord
   - Badges: Badge, UserBadge
   - Game Passports: GameProfile, GameProfileAlias, GameProfileConfig
   - Achievements: Achievement, Certificate
   - Audit: UserAuditEvent

---

### **Issue 9: Missing Computed Fields**

**Problem:** Admin list views don't show important computed data.

**Examples:**

| Field | Where Needed | Why |
|-------|--------------|-----|
| `can_change_identity` | GameProfile | Show if passport is locked |
| `privacy_summary` | UserProfile | Show "Private" / "Followers Only" / "Public" |
| `game_count` | UserProfile | Quick overview of games (**exists, but called `games_count`**) |
| `follower_count` | UserProfile | Quick social stats (**exists in model, but not in admin**) |
| `balance_drift` | UserProfile | Show if economy out of sync |

**Fix Required:**
- Add computed fields to UserProfile list_display
- Use colors for quick status checks (green = ok, red = issue)

---

## 🎯 SUMMARY OF ISSUES

| # | Issue | Severity | Model | Fix Complexity |
|---|-------|----------|-------|----------------|
| 1 | Duplicate privacy controls | 🔴 CRITICAL | UserProfile | Easy |
| 2 | Dual social links system | 🔴 CRITICAL | UserProfile | Medium |
| 3 | Achievement vs Badge naming | 🟡 HIGH | Badge/Achievement | Easy (rename) |
| 4 | Orphaned UserActivity admin | 🔴 CRITICAL | UserActivity | Easy (delete) |
| 5 | Orphaned UserProfileStats admin | 🔴 CRITICAL | UserProfileStats | Easy (delete) |
| 6 | Match admin is placeholder | 🟡 HIGH | Match | Easy (unregister) |
| 7 | Game profiles JSON deprecation | 🟢 LOW | UserProfile | Easy (remove fieldset) |
| 8 | Sidebar clutter | 🟡 HIGH | All | Medium |
| 9 | Missing computed fields | 🟢 LOW | UserProfile | Medium |

**Critical Issues:** 3 (Privacy duplicate, Social links duplicate, 2 orphaned admins)  
**High Priority:** 3 (Naming confusion, Match placeholder, Sidebar clutter)  
**Low Priority:** 2 (JSON warning, Missing computed fields)

---

## 🔥 IMMEDIATE ACTIONS REQUIRED

### **Priority 1: Remove Orphaned Admins**
1. Unregister UserActivityAdmin
2. Unregister UserProfileStatsAdmin
3. Remove from imports
4. (Keep models for now, delete in Phase 5D after backend cleanup)

### **Priority 2: Fix Duplicate Privacy Controls**
1. Remove `is_private` from UserProfileAdmin.list_filter
2. Add computed field `privacy_visibility()` reading from PrivacySettings
3. Keep PrivacySettings inline only

### **Priority 3: Fix Duplicate Social Links**
1. Remove SocialLinkInline from UserProfileAdmin.inlines
2. Rename "Legacy Social Links" → "Social Links"
3. (Delete SocialLink model in Phase 5D)

### **Priority 4: Hide Match Admin**
1. Unregister MatchAdmin (keep model)
2. Re-register when tournament system implemented

### **Priority 5: Clarify Badge/Achievement Naming**
1. Add help text to Badge admin: "System-wide achievement templates"
2. Add help text to Achievement admin: "User-specific milestone records"
3. (Optional: rename models in Phase 6)

---

**Status:** Admin audit complete. Next: Phase 5B Architecture Design.
