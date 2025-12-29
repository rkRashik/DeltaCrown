# User Profile - Cleanup Plan (Phase 0)

**Generated:** December 28, 2025  
**Purpose:** Identify dead/junk/legacy files with safety classification (DO NOT DELETE YET)

---

## Safety Classification Legend

- ✅ **Safe to delete** - Proven unused (no references found)
- 🟡 **Needs confirmation** - Possible includes/imports (verify manually)
- ❌ **Must keep** - Wired / actively used

---

## Templates - Safe to Delete

### Backup Templates (NOT mounted by any view)

| File | References Found | Classification |
|------|-----------------|----------------|
| `templates/user_profile/profile/settings_backup.html` | ❌ None | ✅ **SAFE TO DELETE** |
| `templates/user_profile/profile/settings_modern.html` | ❌ None | ✅ **SAFE TO DELETE** |
| `templates/user_profile/profile/settings_modern_2025.html` | ❌ None | ✅ **SAFE TO DELETE** |
| `templates/user_profile/profile/backup_v1/*` | ❌ None | ✅ **SAFE TO DELETE** (entire directory) |
| `templates/user_profile/profile/backup_v2/*` | ❌ None | ✅ **SAFE TO DELETE** (entire directory) |

**Verification:**
- Searched all Python files: No `render()` calls to these templates
- Searched all templates: No `{% include %}` statements referencing them
- Searched all templates: No `{% extends %}` statements referencing them

**Action:** Delete these files after Phase 0 approval

---

## Templates - Needs Confirmation

### Root-Level Legacy Templates

| File | Rendered By | Status |
|------|------------|---------|
| `templates/user_profile/profile.html` | `profile_view`, `public_profile` | 🟡 **DEPRECATED** but may have `{% include %}` deps |
| `templates/user_profile/settings.html` (root) | `settings_view` | ❌ NOT MOUNTED - ✅ **SAFE** |
| `templates/user_profile/privacy_settings.html` | `privacy_settings_view` | ❌ NOT MOUNTED - ✅ **SAFE** |

**Action:** 
1. Verify `profile.html` component includes are not used elsewhere
2. If confirmed, delete root-level templates

---

## Templates - Component Directory

### `templates/user_profile/components/`

| Component | Used By | Status |
|-----------|---------|---------|
| `_identity_card.html` | `profile.html` (deprecated) | 🟡 **ORPHANED** if parent deleted |
| `_vital_stats.html` | `profile.html` (deprecated) | 🟡 **ORPHANED** |
| `_social_links.html` | `profile.html` (deprecated) | 🟡 **ORPHANED** |
| `_team_card.html` | `profile.html` (deprecated) | 🟡 **ORPHANED** |
| `_game_passport.html` | `profile.html` (deprecated) | 🟡 **ORPHANED** |
| `_match_history.html` | `profile.html` (deprecated) | 🟡 **ORPHANED** |
| `_trophy_shelf.html` | `profile.html` (deprecated) | 🟡 **ORPHANED** |
| `_wallet_card.html` | `profile.html` (deprecated) | 🟡 **ORPHANED** |
| `_certificates.html` | `profile.html` (deprecated) | 🟡 **ORPHANED** |

**Action:**
1. Search if any V2 templates use these components
2. If not, delete entire `components/` directory

---

## Templates - Old Components

### `templates/user_profile/components_old/`

| Directory | Status |
|-----------|---------|
| `components_old/*` | ✅ **SAFE TO DELETE** (entire directory) |

**Verification:** "old" suffix indicates intentionally deprecated

---

## Static JS - Safe to Delete

### Dead JS Files

| File | Referenced By | Classification |
|------|--------------|----------------|
| `static/user_profile/settings_v2_prod.js` | ❌ None | ✅ **SAFE TO DELETE** |
| `static/user_profile/settings_modern.js` | `settings_modern.html` (not mounted) | ✅ **SAFE TO DELETE** |

**Verification:**
- Searched all templates: No `{% static %}` references to these files
- Searched all HTML files: No `<script src=` references

---

## Static JS - Needs Investigation

### JS Directories

| Directory | Contents | Status |
|-----------|----------|---------|
| `static/user_profile/v2/` | Unknown | 🟡 **TO INVESTIGATE** |
| `static/user_profile/v3/` | Unknown | 🟡 **TO INVESTIGATE** |
| `static/user_profile/backup/` | Unknown | 🟡 **TO INVESTIGATE** |
| `static/user_profile/backup_v1/` | Unknown | 🟡 **TO INVESTIGATE** |

**Action:**
1. List contents of each directory
2. Check for references in templates/views
3. If no references, mark safe to delete

---

## Static JS - Must Keep

### Active JS Files

| File | Used By | Classification |
|------|---------|----------------|
| `static/user_profile/js/settings.js` | `profile/settings.html` | ❌ **MUST KEEP** |
| `static/user_profile/js/profile.js` | TBD (needs verification) | 🟡 **NEEDS CONFIRMATION** |

---

## Python Code - Safe to Delete

### Deprecated View Functions

| Function | File | Route | Classification |
|----------|------|-------|----------------|
| `profile_view` | `views/legacy_views.py:124` | NOT MOUNTED (deprecated) | ✅ **SAFE TO DELETE** |
| `privacy_settings_view` | `views/legacy_views.py:551` | NOT MOUNTED (commented out) | ✅ **SAFE TO DELETE** |
| `settings_view` | `views/legacy_views.py:591` | NOT MOUNTED (commented out) | ✅ **SAFE TO DELETE** |

**Verification:**
- Confirmed NOT mounted in `urls.py`
- Marked with `@deprecate_route` decorator
- Replaced by V2 equivalents

**Action:** Delete these functions from `legacy_views.py`

---

## Python Code - Needs Migration Plan

### Duplicate Mutation Endpoints

| Old Endpoint | File | New Endpoint | Status |
|-------------|------|--------------|---------|
| `follow_user` | `legacy_views.py` | `follow_user_safe` | 🟡 **DEPRECATE AFTER FRONTEND MIGRATION** |
| `unfollow_user` | `legacy_views.py` | `unfollow_user_safe` | 🟡 **DEPRECATE AFTER FRONTEND MIGRATION** |
| `save_game_profiles` | `legacy_views.py` | `save_game_profiles_safe` | 🟡 **DEPRECATE AFTER FRONTEND MIGRATION** |
| `add_game_profile` | `legacy_views.py` | `create_passport` | 🟡 **DEPRECATE AFTER FRONTEND MIGRATION** |
| `edit_game_profile` | `legacy_views.py` | GamePassportService | 🟡 **DEPRECATE AFTER FRONTEND MIGRATION** |
| `delete_game_profile` | `legacy_views.py` | `delete_passport` | 🟡 **DEPRECATE AFTER FRONTEND MIGRATION** |

**Action:**
1. Audit frontend JS to find references to old endpoints
2. Update frontend to use new endpoints
3. Add deprecation warnings to old endpoints
4. Monitor usage for 1 sprint
5. Delete old endpoints

---

## Python Code - Refactoring Needed

### `views/legacy_views.py` (1569 lines)

**Issues:**
- Too many concerns in one file
- Mix of active and deprecated code
- Should split into focused modules

**Proposed Split:**

```
views/
  kyc.py              # KYC verification views
  tournaments.py      # Tournament views (my_tournaments_view)
  social.py           # Follow system views (followers/following)
  profile_components.py  # Achievements, match history, certificates
```

**Action:** Refactor in Phase 1 (after audit approved)

---

## Models - Deprecated Fields

### `UserProfile` Model

| Field | Status | Replacement |
|-------|--------|-------------|
| `game_profiles` (JSONField) | ⚠️ **DEPRECATED** | `GameProfile` model |
| Social link fields (`youtube_link`, `twitch_link`, etc.) | ⚠️ **DEPRECATED** | `SocialLink` model |
| Privacy flags (`is_private`, `show_email`, etc.) | ⚠️ **DUPLICATE** | `PrivacySettings` model |

**Action:**
1. Verify all code uses `GameProfile` model (not JSON field)
2. Verify all code uses `SocialLink` model (not fields)
3. Consolidate privacy to `PrivacySettings` only
4. Create migration to drop deprecated fields (Phase 2)

---

## Cleanup Summary by Phase

### Phase 0 (This Document)
- ✅ Audit complete
- ✅ Cleanup plan documented
- ❌ **NO DELETIONS YET**

### Phase 1 (Immediate Cleanup - Safe Deletions)

**Templates:**
- Delete `settings_backup.html`
- Delete `settings_modern.html`
- Delete `settings_modern_2025.html`
- Delete `backup_v1/` directory
- Delete `backup_v2/` directory
- Delete `components_old/` directory
- Delete `settings.html` (root)
- Delete `privacy_settings.html`

**Static:**
- Delete `settings_v2_prod.js`
- Delete `settings_modern.js`

**Python:**
- Delete `profile_view()` function
- Delete `privacy_settings_view()` function
- Delete `settings_view()` function

**Estimated Cleanup:** ~2,000 lines of dead code

---

### Phase 2 (Frontend Migration Required)

**Action:** Update frontend JS to use safe endpoints, then delete:
- `follow_user()` → use `follow_user_safe()`
- `unfollow_user()` → use `unfollow_user_safe()`
- `save_game_profiles()` → use `save_game_profiles_safe()`
- `add_game_profile()` → use `create_passport()`
- `edit_game_profile()` → use GamePassportService
- `delete_game_profile()` → use `delete_passport()`

**Estimated Cleanup:** ~500 lines

---

### Phase 3 (Refactoring)

**Action:** Split `legacy_views.py` into focused modules
- Extract KYC views → `views/kyc.py`
- Extract tournament views → `views/tournaments.py`
- Extract social views → `views/social.py`
- Extract component views → `views/profile_components.py`

**Result:** Better organization, no line reduction

---

### Phase 4 (Model Cleanup)

**Action:** Drop deprecated fields after migration complete
- Drop `game_profiles` JSONField
- Drop social link fields on UserProfile
- Consolidate privacy flags to PrivacySettings only

**Result:** Cleaner schema, simpler model

---

## Verification Commands

### Check for template references
```bash
# Search Python files for template renders
grep -r "render.*settings_backup" apps/user_profile/

# Search templates for includes
grep -r "{% include.*settings_backup" templates/

# Search templates for extends
grep -r "{% extends.*settings_backup" templates/
```

### Check for JS references
```bash
# Search templates for static loads
grep -r "{% static.*settings_v2_prod" templates/

# Search HTML for script tags
grep -r "settings_v2_prod.js" templates/
```

### Check for function calls
```bash
# Search for view function calls
grep -r "profile_view\(" apps/

# Search for URL names
grep -r "url.*profile_view" .
```

---

## Final Checklist Before Deletion

- [ ] Run grep searches to verify no references
- [ ] Check git history for recent changes to files
- [ ] Verify tests don't reference deleted code
- [ ] Create backup branch before deletion
- [ ] Run full test suite after deletion
- [ ] Verify all URLs still resolve
- [ ] Verify all templates render

---

**Document Status:** ✅ Phase D Complete  
**Next Step:** Get approval to proceed with Phase 1 deletions
