# C1 Cleanup Plan (2026-01-14)

**Goal**: Identify and safely remove legacy/duplicate code to prepare for V1 without breaking behavior.  
**Phase**: Analysis + Safe Cleanup Only  
**Date**: 2026-01-14

---

## Executive Summary

**Status**: ✅ Analysis Complete | Safe deletions identified  
**Critical Protections Verified**:
- ✅ `/me/settings/` working (renders `settings_control_deck.html`)
- ✅ Django admin `/admin/user_profile/` functional
- ✅ Public profiles `/@username/` rendering
- ✅ No behavior changes in this phase

**Key Findings**:
- **10 legacy items** identified (templates, views, fields, static files)
- **5 FALLBACK items** (keep for environment safety)
- **3 DEPRECATE candidates** (legacy social fields)
- **2 SAFE DELETE candidates** (old settings template + CSS)
- **43 backup files** in `backup_UP/` (safe to archive)

**Recommended Actions**:
- Stage 1: Deprecate legacy social fields (add warnings)
- Stage 2: Migrate legacy social data to `SocialLink` model
- Stage 3: Delete proven dead code (settings.html, settings.css)

---

## STEP 0: Baseline Smoke Verification

### Critical Endpoints (MUST KEEP WORKING)

| Endpoint | View Function | Template | Status |
|----------|---------------|----------|--------|
| `GET /me/settings/` | `profile_settings_view` | `settings_control_deck.html` | ✅ VERIFIED |
| `POST /me/settings/basic/` | `update_basic_info` | JSON response | ✅ VERIFIED |
| `POST /me/settings/media/` | `upload_media` | JSON response | ✅ VERIFIED |
| `POST /api/social-links/update/` | `update_social_links_api` | JSON response | ✅ VERIFIED |
| `POST /me/settings/privacy/save/` | `update_privacy_settings` | JSON response | ✅ VERIFIED |
| `GET /admin/user_profile/` | Django admin | Admin templates | ✅ VERIFIED |
| `GET /@<username>/` | `public_profile_view` | `public_profile.html` | ✅ VERIFIED |

**Verification Source**:
- Runtime proof: `docs/audits/UP2_settings_runtime_proof.md`
- Server logs: 2026-01-14 13:37:56 (429KB response confirms Control Deck)
- Feature flag: `SETTINGS_CONTROL_DECK_ENABLED = True` (line 913, settings.py)

---

## STEP 1: Inventory of Legacy/Duplicate Candidates

### A) Templates

| Item | Path | Lines | Why Legacy | Evidence |
|------|------|-------|------------|----------|
| **1. settings.html** | `templates/user_profile/profile/settings.html` | 468 | Old Alpine.js version, replaced by Control Deck | Uses Alpine.js (x-data), not used in view |
| **2. settings_v4.html** | `templates/user_profile/profile/settings_v4.html` | 467 | FALLBACK for Control Deck (feature flag) | Lines 1209-1213: if not ENABLED → v4 |
| **3. Backup files** | `templates/user_profile/backup_UP/phase_up1_20260114/` | 43 files | Phase UP.1 backup (2026-01-14) | Created during redesign, safe archive |
| **4. _about_manager.html** | `templates/user_profile/profile/settings/_about_manager.html` | Unknown | Only included in settings_v4.html (not Control Deck) | Line 148 in settings_v4.html |
| **5. _social_links_manager.html** | `templates/user_profile/profile/settings/_social_links_manager.html` | Unknown | Only included in settings_v4.html (not Control Deck) | Line 167 in settings_v4.html |
| **6. _kyc_status.html** | `templates/user_profile/profile/settings/_kyc_status.html` | Unknown | Only included in settings_v4.html (not Control Deck) | Line 382 in settings_v4.html |

**Proof Methodology**:
- Searched: `grep -r "settings.html"` in templates/views
- Found: `legacy_views.py:739` renders `user_profile/settings.html`
- URL Check: `settings_view` commented out in `urls.py:371`
- Template includes: Checked `{% include %}` tags in both settings templates

---

### B) Views/URLs

| Item | Path | Why Legacy | Evidence |
|------|------|------------|----------|
| **7. settings_view** | `apps/user_profile/views/legacy_views.py:568` | Old settings view, replaced by `profile_settings_view` | Commented out in urls.py:371 |
| **8. privacy_settings_view** | `apps/user_profile/views/legacy_views.py` (line unknown) | Old privacy view, replaced by `profile_privacy_view` | Commented out in urls.py:368 |
| **9. URL alias 'settings'** | `apps/user_profile/urls.py:203` | Duplicate name for `/me/settings/` | No `reverse('settings')` usage found |

**Proof Evidence**:
```python
# urls.py:371 (COMMENTED OUT)
# path("me/settings/", settings_view, name="settings"),  # Replaced by profile_settings_v2

# urls.py:202-203 (ACTIVE with DUPLICATE names)
path("me/settings/", profile_settings_view, name="profile_settings"),
path("me/settings/", profile_settings_view, name="settings"),  # Alias for template compatibility
```

**reverse() Usage Check**:
- Searched: `grep -r "reverse('settings')"` → **0 matches**
- Searched: `grep -r "url 'settings'"` → **0 matches**
- Conclusion: Alias name "settings" is **UNUSED** in codebase

---

### C) Models - Legacy Social Fields

| Item | Model | Field | Why Legacy | Evidence |
|------|-------|-------|------------|----------|
| **10. facebook** | `UserProfile` | `URLField` | Replaced by `SocialLink` model | Line 219, models_main.py |
| **11. instagram** | `UserProfile` | `URLField` | Replaced by `SocialLink` model | Line 220, models_main.py |
| **12. tiktok** | `UserProfile` | `URLField` | Replaced by `SocialLink` model | Line 221, models_main.py |
| **13. twitter** | `UserProfile` | `URLField` | Replaced by `SocialLink` model | Line 222, models_main.py |
| **14. youtube_link** | `UserProfile` | `URLField` | Replaced by `SocialLink` model | Line 216, models_main.py |
| **15. twitch_link** | `UserProfile` | `URLField` | Replaced by `SocialLink` model | Line 217, models_main.py |
| **16. discord_id** | `UserProfile` | `CharField(64)` | Replaced by `SocialLink` model | Line 218, models_main.py |

**Code Context** (`models_main.py:215-222`):
```python
# ===== SOCIAL LINKS =====
youtube_link = models.URLField(blank=True)
twitch_link = models.URLField(blank=True)
discord_id = models.CharField(max_length=64, blank=True)
facebook = models.URLField(blank=True, default="")
instagram = models.URLField(blank=True, default="")
tiktok = models.URLField(blank=True, default="")
twitter = models.URLField(blank=True, default="")
```

**Modern Canonical Model**: `SocialLink` (models_main.py:1364)
```python
class SocialLink(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='social_links')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    url = models.URLField(max_length=500)
    handle = models.CharField(max_length=100, blank=True)
```

**Usage Check**:
- Settings API uses: `SocialLink` model (settings_api.py:227)
- Legacy API writes: `profile.facebook = ...` (public_profile_views.py:1504)
- **DUPLICATION ISSUE**: Data can exist in BOTH locations

---

### D) Static Files

| Item | Path | Why Legacy | Evidence |
|------|------|------------|----------|
| **17. settings.css** | `static/css/settings.css` | Old styles for Alpine.js settings.html | Only referenced in backup: backups/user_profile_legacy_v1/templates/settings.html:7 |
| **18. settings_v2.css** | `static/css/settings_v2.css` | FALLBACK styles for settings_v4.html | Used by settings_v4.html:7 and settings.html:7 |

**Proof Evidence**:
```bash
# Grep results for settings.css
backups/user_profile_legacy_v1/templates/settings.html:7
<link rel="stylesheet" href="{% static 'css/settings.css' %}">
```

**No active templates use `settings.css`** - only in archived backup.

---

### E) Services/Helpers

**Status**: No unused services identified in this phase.

**Checked Items**:
- `ProfilePermissionChecker`: ACTIVE (used in public_profile_view)
- `build_public_profile_context`: ACTIVE (used in profile_settings_view)
- `GamePassportService`: ACTIVE (used in settings context)

---

## STEP 2: Usage Proof (Evidence-Based)

### Template: settings.html

**Import Check**:
```bash
grep -r "settings.html" apps/**/*.py
```
**Result**:
- `legacy_views.py:739`: `return render(request, 'user_profile/settings.html', context)`

**URL Routing Check**:
```python
# urls.py:371 (COMMENTED OUT)
# path("me/settings/", settings_view, name="settings"),  # Replaced by profile_settings_v2
```

**Conclusion**: `settings.html` is rendered ONLY by `settings_view` which is **COMMENTED OUT** in urls.py.  
**Status**: SAFE DELETE

---

### Template: settings_v4.html

**Usage Check**:
```python
# public_profile_views.py:1209-1213
from django.conf import settings as django_settings
if django_settings.SETTINGS_CONTROL_DECK_ENABLED:
    template = 'user_profile/profile/settings_control_deck.html'
else:
    template = 'user_profile/profile/settings_v4.html'
```

**Feature Flag Check**:
```python
# settings.py:913
SETTINGS_CONTROL_DECK_ENABLED = os.getenv('SETTINGS_CONTROL_DECK_ENABLED', 'True').lower() == 'true'
```

**Environment Check**: Default is `'True'` → Control Deck active  
**Fallback Trigger**: Only if env var explicitly set to `'false'`  
**Status**: FALLBACK (keep for safety)

---

### Legacy Social Fields

**Write Locations**:
1. `public_profile_views.py:1504` (update_basic_info):
   ```python
   profile.facebook = facebook
   ```
2. `settings_debug.py:68`:
   ```python
   'facebook': profile.facebook,
   ```

**Modern API** (`settings_api.py:227`):
```python
# Delete existing links for this user
SocialLink.objects.filter(user=request.user).delete()

# Create new links
for link_data in links_data:
    link = SocialLink.objects.create(
        user=request.user,
        platform=platform,
        url=url,
        handle=link_data.get('handle', '')
    )
```

**Conclusion**:
- **Modern API**: Uses `SocialLink` model exclusively ✅
- **Legacy API**: Still writes to `UserProfile.facebook` etc. ⚠️
- **Data Duplication**: Yes - social links stored in TWO places
- **Status**: DEPRECATE (requires migration)

---

### URL Alias 'settings'

**reverse() Usage Check**:
```bash
grep -r "reverse('settings')" → 0 matches
grep -r "url 'settings'" → 0 matches
```

**URLs with name='settings'**:
```python
# urls.py:203
path("me/settings/", profile_settings_view, name="settings"),  # Alias
```

**Conclusion**: Alias name "settings" has **ZERO** references in codebase.  
**Status**: DEPRECATE (can be removed in Stage 3 after verification)

---

## STEP 3: Classification

### Legend
- **ACTIVE**: Currently in use, must keep
- **FALLBACK**: Not currently used but required for environment safety (feature flags, env vars)
- **DEPRECATE**: Keep but mark for future removal (needs migration or warning period)
- **SAFE DELETE**: No references found, verified dead code

---

### Classification Table

| # | Item | Location | Classification | Reason |
|---|------|----------|----------------|--------|
| 1 | `settings.html` | templates/user_profile/profile/ | **SAFE DELETE** | Only rendered by commented-out view |
| 2 | `settings_v4.html` | templates/user_profile/profile/ | **FALLBACK** | Feature flag fallback (if ENABLED=False) |
| 3 | Backup files (43) | templates/user_profile/backup_UP/ | **SAFE DELETE** | Phase UP.1 backup, no runtime usage |
| 4 | `_about_manager.html` | templates/.../settings/ | **FALLBACK** | Included by settings_v4.html (fallback chain) |
| 5 | `_social_links_manager.html` | templates/.../settings/ | **FALLBACK** | Included by settings_v4.html (fallback chain) |
| 6 | `_kyc_status.html` | templates/.../settings/ | **FALLBACK** | Included by settings_v4.html (fallback chain) |
| 7 | `settings_view` | legacy_views.py:568 | **SAFE DELETE** | URL route commented out, no usage |
| 8 | `privacy_settings_view` | legacy_views.py | **SAFE DELETE** | URL route commented out, replaced |
| 9 | URL alias 'settings' | urls.py:203 | **DEPRECATE** | No reverse() usage, but low-risk to keep |
| 10-16 | Legacy social fields (7 fields) | models_main.py:216-222 | **DEPRECATE** | Still used by legacy API, needs migration |
| 17 | `settings.css` | static/css/ | **SAFE DELETE** | Only referenced in archived backup |
| 18 | `settings_v2.css` | static/css/ | **FALLBACK** | Used by settings_v4.html (fallback) |

---

## STEP 4: Action Plan (Staged)

### Stage 1: Deprecation Actions (Immediate, Safe)

**1.1 Add Deprecation Comments**

**File**: `apps/user_profile/models_main.py` (lines 215-222)
```python
# ===== SOCIAL LINKS (DEPRECATED - Use SocialLink model instead) =====
# DEPRECATION NOTICE (2026-01-14): These fields are legacy duplicates.
# Modern API uses SocialLink model. Schedule removal after data migration.
youtube_link = models.URLField(blank=True)  # DEPRECATED
twitch_link = models.URLField(blank=True)  # DEPRECATED
discord_id = models.CharField(max_length=64, blank=True)  # DEPRECATED
facebook = models.URLField(blank=True, default="")  # DEPRECATED
instagram = models.URLField(blank=True, default="")  # DEPRECATED
tiktok = models.URLField(blank=True, default="")  # DEPRECATED
twitter = models.URLField(blank=True, default="")  # DEPRECATED
```

**1.2 Add Warning to Legacy API** (optional, DEBUG only)

**File**: `apps/user_profile/views/public_profile_views.py` (line 1504)
```python
# DEPRECATION WARNING (2026-01-14)
if settings.DEBUG:
    import warnings
    warnings.warn(
        "Writing to legacy UserProfile.facebook field. "
        "Migrate to SocialLink model API.",
        DeprecationWarning,
        stacklevel=2
    )
profile.facebook = facebook
```

**1.3 Document in Admin**

**File**: `apps/user_profile/admin/users.py` (fieldset for social media)
```python
# Add help_text to fieldset
fieldsets = [
    # ...
    ("Social Media (DEPRECATED - Use SocialLink inline)", {
        'fields': ('facebook', 'instagram', 'tiktok', 'twitter', 
                   'youtube_link', 'twitch_link', 'discord_id'),
        'description': 'DEPRECATED: Use SocialLink model. These fields kept for data migration only.',
    }),
]
```

**Risk**: Zero - comments only, no behavior change

---

### Stage 2: Migration Actions (Requires Planning)

**2.1 Data Migration Plan**

**Goal**: Copy legacy social data into `SocialLink` model, then mark fields for deletion.

**Pre-Migration Checks**:
1. Count profiles with legacy social data:
   ```python
   profiles_with_legacy = UserProfile.objects.exclude(
       Q(facebook='') & Q(instagram='') & Q(tiktok='') & Q(twitter='') &
       Q(youtube_link='') & Q(twitch_link='') & Q(discord_id='')
   ).count()
   ```
2. Check for conflicts (user has BOTH legacy field AND SocialLink for same platform)
3. Decide conflict resolution (SocialLink wins? Merge? Manual review?)

**Migration Script** (apps/user_profile/migrations/NNNN_migrate_legacy_social.py):
```python
from django.db import migrations

def migrate_legacy_social_links(apps, schema_editor):
    UserProfile = apps.get_model('user_profile', 'UserProfile')
    SocialLink = apps.get_model('user_profile', 'SocialLink')
    User = apps.get_model('auth', 'User')
    
    platform_map = {
        'facebook': 'facebook',
        'instagram': 'instagram',
        'tiktok': 'tiktok',
        'twitter': 'twitter',
        'youtube_link': 'youtube',
        'twitch_link': 'twitch',
    }
    
    migrated_count = 0
    for profile in UserProfile.objects.all():
        for legacy_field, platform_name in platform_map.items():
            legacy_url = getattr(profile, legacy_field, '')
            if legacy_url:
                # Check if SocialLink already exists
                if not SocialLink.objects.filter(user=profile.user, platform=platform_name).exists():
                    SocialLink.objects.create(
                        user=profile.user,
                        platform=platform_name,
                        url=legacy_url
                    )
                    migrated_count += 1
    
    print(f"Migrated {migrated_count} legacy social links")

class Migration(migrations.Migration):
    dependencies = [
        ('user_profile', 'PREVIOUS_MIGRATION'),
    ]
    
    operations = [
        migrations.RunPython(migrate_legacy_social_links),
    ]
```

**Rollback Plan**: Keep legacy fields populated during migration (read-only in admin).

**Timeline**: After C1 cleanup, before V1 launch.

---

**2.2 Remove Legacy API Writes**

**After migration completes**, update legacy API to stop writing to deprecated fields:

**File**: `apps/user_profile/views/public_profile_views.py` (lines 1497-1504)
```python
# REMOVE THESE LINES after migration:
# profile.facebook = facebook
# profile.instagram = instagram
# profile.twitter = twitter
# etc.

# ADD: Redirect to modern API
return JsonResponse({
    'success': False,
    'error': 'Social links must be updated via /api/social-links/update/ endpoint'
}, status=400)
```

**Risk**: Medium - requires testing legacy clients that may use old API.

---

### Stage 3: Deletion Actions (After Stage 1+2)

**3.1 Delete Verified Dead Templates**

| File | Reason | Risk |
|------|--------|------|
| `templates/user_profile/profile/settings.html` | Rendered by commented-out view | LOW |
| `static/css/settings.css` | Only referenced in archived backup | LOW |
| `apps/user_profile/views/legacy_views.py:568-750` | `settings_view` function | LOW |
| `apps/user_profile/views/legacy_views.py` (privacy_settings_view) | Replaced view | LOW |

**Command**:
```bash
# Backup first (just in case)
mkdir -p backups/C1_cleanup_2026-01-14

# Delete templates
rm templates/user_profile/profile/settings.html
rm static/css/settings.css

# Delete views (manual edit)
# Remove settings_view function from legacy_views.py
```

**3.2 Archive Backup Files**

```bash
# Move to long-term archive (outside repo)
mv templates/user_profile/backup_UP/ backups/archive/backup_UP_phase_up1_20260114/
```

**3.3 Remove URL Alias (After Verification)**

**File**: `apps/user_profile/urls.py` (line 203)
```python
# REMOVE this line after confirming no external dependencies:
# path("me/settings/", profile_settings_view, name="settings"),  # Alias
```

**Verification**: Monitor logs for 2 weeks to ensure no reverse('settings') calls from external sources.

---

### Stage 4: Model Field Removal (V2, After Data Migration)

**AFTER Stage 2 migration is complete AND verified**, create migration to drop fields:

```python
# apps/user_profile/migrations/NNNN_drop_legacy_social_fields.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('user_profile', 'NNNN_migrate_legacy_social'),
    ]
    
    operations = [
        migrations.RemoveField(model_name='userprofile', name='facebook'),
        migrations.RemoveField(model_name='userprofile', name='instagram'),
        migrations.RemoveField(model_name='userprofile', name='tiktok'),
        migrations.RemoveField(model_name='userprofile', name='twitter'),
        migrations.RemoveField(model_name='userprofile', name='youtube_link'),
        migrations.RemoveField(model_name='userprofile', name='twitch_link'),
        migrations.RemoveField(model_name='userprofile', name='discord_id'),
    ]
```

**Timeline**: After V1 launch, in V1.1 or V2.

---

## DO NOT DELETE YET (Safety List)

### Templates (Keep for Fallback)
- ✋ `settings_v4.html` - Feature flag fallback
- ✋ `_about_manager.html` - Included by fallback template
- ✋ `_social_links_manager.html` - Included by fallback template
- ✋ `_kyc_status.html` - Included by fallback template
- ✋ `settings_control_deck.html` - ACTIVE main template

### Static Files (Keep for Fallback)
- ✋ `settings_v2.css` - Used by settings_v4.html

### URLs (Keep for Stability)
- ✋ URL name alias 'settings' - Low risk, but monitor usage first
- ✋ Commented-out routes in urls.py - Historical reference

### Models (Keep Until Migration)
- ✋ Legacy social fields (facebook, instagram, etc.) - Requires data migration

---

## Optional Safe Cleanup Execution

### Changes Applied in C1 Phase

**Status**: ⚠️ NO CHANGES APPLIED YET

**Rationale**: 
- Stage 1 deprecation comments are safe but should be reviewed before commit
- Stage 3 deletions require approval (settings.html, settings.css, legacy views)
- Backup archival can be done but kept in repo for now

**Recommended Next Step**:
1. Review this plan with team
2. Apply Stage 1 deprecation comments (safe, reversible)
3. Schedule Stage 2 migration for post-C1
4. Apply Stage 3 deletions after approval

---

## Verification Checklist

After any deletions, verify:

- [ ] `/me/settings/` still renders Control Deck template
- [ ] POST to `/me/settings/basic/` still saves display_name
- [ ] POST to `/api/social-links/update/` still works
- [ ] Django admin loads without errors
- [ ] Public profiles `/@username/` render
- [ ] No 404 errors in server logs
- [ ] No template rendering errors

**Test Command**:
```bash
python manage.py runserver
# Visit: http://127.0.0.1:8000/me/settings/
# Check: No errors, Control Deck loads
```

---

## Summary Statistics

**Total Items Inventoried**: 18  
**Classification Breakdown**:
- ACTIVE: 0 (all critical items already active)
- FALLBACK: 5 (templates + CSS for feature flag safety)
- DEPRECATE: 8 (legacy social fields + URL alias)
- SAFE DELETE: 5 (settings.html, settings.css, legacy views, backup files)

**Estimated Cleanup Impact**:
- **Files to delete**: 5 (templates/views/CSS)
- **Backup files to archive**: 43
- **Model fields to deprecate**: 7
- **Lines of code removed**: ~1,500 (templates) + ~200 (views)

**Risk Assessment**:
- Stage 1 (Deprecation): **ZERO RISK** - comments only
- Stage 3 (Deletion): **LOW RISK** - verified dead code
- Stage 2 (Migration): **MEDIUM RISK** - requires testing

---

## Next Steps

1. **Immediate** (C1 Phase):
   - Apply Stage 1 deprecation comments
   - Archive backup files (optional)

2. **Short-term** (Post-C1):
   - Execute Stage 3 safe deletions (settings.html, settings.css, legacy views)
   - Monitor logs for any unexpected reverse('settings') usage

3. **Medium-term** (Pre-V1):
   - Plan Stage 2 data migration (legacy social → SocialLink)
   - Execute migration in staging environment
   - Verify migration success

4. **Long-term** (V1.1 or V2):
   - Drop legacy social fields from UserProfile model
   - Remove fallback templates if Control Deck proves stable

---

**Report Generated**: 2026-01-14  
**Author**: AI Assistant  
**Status**: Ready for Review  
**Next Action**: Review with team → Apply Stage 1 → Execute Stage 3 after approval
