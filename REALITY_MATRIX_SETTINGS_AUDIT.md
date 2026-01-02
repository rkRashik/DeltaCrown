# Reality Matrix: Settings Control Deck Truth Reconciliation

**Date:** January 2, 2026  
**Purpose:** Audit current settings state vs backend reality before production wiring sprint

---

## Executive Summary

**Current State:**
- ✅ Platform Preferences System EXISTS (Phase 5A complete)
- ✅ Privacy Settings EXISTS with full backend
- ✅ Career/LFT Settings EXISTS (Phase 2A complete)
- ✅ Notifications Settings EXISTS (Phase 2B complete)
- ✅ Game Passports API EXISTS (full CRUD)
- ⚠️ Frontend template has placeholder/disabled sections
- ⚠️ Some backend features not wired to UI

**Key Finding:** Backend is MORE complete than the UI suggests. Most "coming soon" features are production-ready backend-wise.

---

## Reality Matrix Table

| Tab/Feature | Backend Exists? | Frontend Status | Source of Truth Models | Required Action |
|-------------|----------------|-----------------|------------------------|-----------------|
| **Identity** | ✅ YES | ✅ ENABLED | `UserProfile` (display_name, bio, avatar, banner) | WIRE gender field if exists |
| **Security & KYC** | ⚠️ PARTIAL | 🟡 PARTIAL | `VerificationRecord`, Django Auth | FIX password change, wire KYC upload |
| **Privacy & Visibility** | ✅ YES | ✅ ENABLED | `PrivacySettings` (14 fields + is_private_account) | EXPAND to show all fields |
| **Notifications** | ✅ YES | ✅ ENABLED | `UserProfile.system_settings` JSON | REMOVE quiet hours, WIRE categories |
| **Career & LFT** | ✅ YES | ✅ ENABLED | `UserProfile` (lft_status, roles, etc) | MAKE game-aware (11 games) |
| **Game Passports** | ✅ YES | 🟡 PARTIAL | `GameProfile` model + full CRUD API | WIRE real CRUD (placeholder buttons exist) |
| **Bounties & Match** | ✅ YES | ✅ ENABLED | `UserProfile.system_settings` JSON | VERIFY endpoints, remove hardcoding |
| **Pro Loadout** | ✅ YES | ✅ ENABLED | `HardwareGear`, `GameProfileConfig` | REDESIGN UI (category-based) |
| **Live Feed/Stream** | ✅ YES | ✅ ENABLED | `UserProfile` (stream_url, stream_platform) | ADD URL validation |
| **Inventory** | ✅ YES | ✅ ENABLED | `UserProfile.system_settings.inventory_visibility` | VERIFY privacy enforcement |
| **Wallet/Billing** | ✅ YES | ❌ BROKEN | `Wallet` model (apps/economy) | FIX missing templates |
| **Platform Prefs** | ✅ YES | ❌ NOT IN UI | `UserProfile` (preferred_language, timezone_pref, time_format, theme_preference) | ADD TAB + wire middleware |
| **Follow Requests** | ✅ YES | ❌ NOT IN UI | `FollowRequest` model (Phase 6A) | ADD management UI |
| **Danger Zone** | ⚠️ PARTIAL | ✅ ENABLED | Django User + soft delete | VERIFY deletion flow |

---

## Backend API Map (Verified Production-Ready)

### ✅ Fully Implemented APIs

#### 1. Platform Preferences (Phase 5A)
```
GET  /me/settings/platform-global/
POST /me/settings/platform-global/save/
```
- **Models:** `UserProfile.preferred_language`, `timezone_pref`, `time_format`, `theme_preference`
- **Middleware:** `UserPlatformPrefsMiddleware` (activates timezone + language per request)
- **Context Processor:** `user_platform_prefs` (injects prefs into all templates)
- **Template Filters:** `format_dt`, `format_money` (respects user prefs)
- **Status:** ✅ COMPLETE but not in UI tab

#### 2. Privacy Settings
```
GET  /me/settings/privacy/
POST /me/settings/privacy/save/
```
- **Models:** `PrivacySettings` (14 boolean fields + inventory_visibility + is_private_account)
- **Fields:** show_following_list, show_achievements, show_game_passports, show_social_links, etc.
- **Status:** ✅ COMPLETE, UI only shows subset

#### 3. Career & Matchmaking Settings (Phase 2A)
```
GET  /me/settings/career/
POST /me/settings/career/save/
GET  /me/settings/matchmaking/
POST /me/settings/matchmaking/save/
```
- **Models:** `UserProfile` (lft_status, preferred_roles, etc) + system_settings JSON
- **Status:** ✅ COMPLETE

#### 4. Notifications Settings (Phase 2B)
```
GET  /me/settings/notifications/
POST /me/settings/notifications/save/
```
- **Models:** `UserProfile.system_settings` JSON
- **Status:** ✅ COMPLETE

#### 5. Game Passports (GP-FE-MVP-01 + UP-PHASE15)
```
GET    /api/game-passports/
POST   /api/game-passports/create/
POST   /api/game-passports/update/
POST   /api/game-passports/delete/
POST   /api/passports/toggle-lft/
POST   /api/passports/pin/
POST   /api/passports/reorder/
```
- **Models:** `GameProfile` (first-class passport system with structured fields)
- **Status:** ✅ COMPLETE API, UI shows placeholders

#### 6. Follow Requests (Phase 6A)
```
POST /profiles/<username>/follow/
POST /profiles/<username>/follow/respond/
GET  /me/follow-requests/?status=...
```
- **Models:** `FollowRequest` (PENDING/APPROVED/REJECTED)
- **Status:** ✅ COMPLETE backend, Phase 6B added private wall, NO management UI

#### 7. Dynamic Content APIs (Phase 14B - Eliminates Hardcoding)
```
GET /api/games/
GET /api/games/<id>/metadata/
GET /api/social-links/platforms/
GET /api/privacy/presets/
```
- **Purpose:** NO HARDCODED DROPDOWNS, load from DB
- **Status:** ✅ COMPLETE

### ⚠️ Partially Implemented

#### 8. Wallet/Billing
```
GET /economy/wallet/
POST /economy/withdraw/request/
```
- **Models:** `Wallet`, `Transaction`, `WithdrawalRequest` (apps/economy)
- **Status:** ⚠️ Backend exists, MISSING TEMPLATES

#### 9. Security & KYC
```
POST /me/kyc/upload/
GET  /me/kyc/status/
```
- **Models:** `VerificationRecord`
- **Status:** ⚠️ Backend exists, UI shows placeholders

---

## Model Field Audit (Admin Parity)

### UserProfile Model (Excerpt)
```python
class UserProfile(models.Model):
    # Identity
    display_name = CharField(max_length=50)
    bio = TextField(max_length=500, blank=True)
    avatar = ImageField(upload_to='avatars/', blank=True)
    banner = ImageField(upload_to='banners/', blank=True)
    
    # Platform Preferences (Phase 6 Part C)
    preferred_language = CharField(max_length=10, default='en', choices=[('en', 'English'), ('bn', 'Bengali')])
    timezone_pref = CharField(max_length=50, default='Asia/Dhaka')
    time_format = CharField(max_length=3, default='12h', choices=[('12h', '12-hour'), ('24h', '24-hour')])
    theme_preference = CharField(max_length=10, default='dark', choices=[('light', 'Light'), ('dark', 'Dark'), ('system', 'System')])
    
    # Career/LFT
    lft_status = BooleanField(default=False)
    preferred_roles = JSONField(default=dict)
    
    # Streaming
    stream_url = URLField(max_length=500, blank=True)
    stream_platform = CharField(max_length=50, blank=True, choices=[('twitch', 'Twitch'), ('youtube', 'YouTube'), ...])
    
    # System settings (JSON catchall)
    system_settings = JSONField(default=dict)  # Contains: currency, notifications, inventory_visibility, etc
```

### PrivacySettings Model
```python
class PrivacySettings(models.Model):
    user_profile = OneToOneField(UserProfile, on_delete=CASCADE, related_name='privacy')
    
    # Visibility toggles (14 fields)
    show_following_list = BooleanField(default=True)
    show_achievements = BooleanField(default=True)
    show_game_passports = BooleanField(default=True)
    show_social_links = BooleanField(default=True)
    show_wallet = BooleanField(default=False)  # Admin: User can hide wallet
    show_match_history = BooleanField(default=True)
    show_teams = BooleanField(default=True)
    show_certificates = BooleanField(default=True)
    show_badges = BooleanField(default=True)
    show_tournaments = BooleanField(default=True)
    show_endorsements = BooleanField(default=True)
    show_real_name = BooleanField(default=False)
    show_email = BooleanField(default=False)
    
    # Inventory visibility (GP2A)
    inventory_visibility = CharField(max_length=20, default='FRIENDS_ONLY', choices=[('PRIVATE', ...), ('FRIENDS_ONLY', ...), ('PUBLIC', ...)])
    
    # Private Account (Phase 6A)
    is_private_account = BooleanField(default=False)
    
    # Legacy visibility preset (UP-PHASE12B)
    visibility_preset = CharField(max_length=20, default='PUBLIC', choices=[('PRIVATE', ...), ('PROTECTED', ...), ('PUBLIC', ...)])
```

### GameProfile Model (Game Passport)
```python
class GameProfile(models.Model):
    user_profile = ForeignKey(UserProfile, on_delete=CASCADE, related_name='game_profiles')
    game = ForeignKey(Game, on_delete=CASCADE)
    
    # Structured identity fields (GP-2A)
    in_game_name = CharField(max_length=100, blank=True)
    game_id = CharField(max_length=200, blank=True)  # Game-specific unique ID
    rank = CharField(max_length=100, blank=True)
    rank_tier = CharField(max_length=100, blank=True)
    region = ForeignKey(ServerRegion, on_delete=SET_NULL, null=True)
    
    # Visibility & LFT
    is_pinned = BooleanField(default=False)
    is_public = BooleanField(default=True)
    lft_status = BooleanField(default=False)
    
    # Metadata
    sort_order = IntegerField(default=0)
    stats_cache = JSONField(default=dict)
```

### HardwareGear Model (Loadout)
```python
class HardwareGear(models.Model):
    user_profile = ForeignKey(UserProfile, on_delete=CASCADE, related_name='hardware_gear')
    
    category = CharField(max_length=50, choices=[('MOUSE', 'Mouse'), ('KEYBOARD', 'Keyboard'), ('MONITOR', 'Monitor'), ...])
    brand = CharField(max_length=100)
    model_name = CharField(max_length=200)
    specs = TextField(blank=True)
```

---

## Contradictions Found

### 1. ❌ Platform Preferences Tab Missing
- **Backend:** FULLY IMPLEMENTED (Phase 5A complete)
- **Frontend:** NOT IN TAB NAVIGATION
- **Action:** ADD "Platform" tab between "Privacy" and "Notifications"

### 2. ❌ Game Passports CRUD Placeholders
- **Backend:** Full CRUD API exists (`/api/game-passports/` + create/update/delete)
- **Frontend:** Buttons show "coming soon" toasts
- **Action:** WIRE real API calls, remove placeholder toasts

### 3. ❌ Follow Requests Management Missing
- **Backend:** Phase 6A complete, Phase 6B added private wall
- **Frontend:** No UI to list/approve/reject incoming requests
- **Action:** ADD "Follow Requests" section to Privacy tab

### 4. ❌ Wallet Pages Broken
- **Backend:** `Wallet` model + APIs exist
- **Frontend:** Template paths broken (`economy/wallet_dashboard.html` missing)
- **Action:** CREATE missing templates + fix routing

### 5. ⚠️ Career & LFT Not Game-Aware
- **Backend:** Supports per-game LFT via GameProfile.lft_status
- **Frontend:** Shows single LFT toggle (not per-game)
- **Action:** REDESIGN to show per-game team status + LFT toggle

### 6. ⚠️ Privacy Settings Incomplete
- **Backend:** 14 privacy toggles exist
- **Frontend:** Only shows 3-4 toggles
- **Action:** EXPAND to show all privacy controls

### 7. ⚠️ Notifications "Quiet Hours" Not Desired
- **Backend:** Not implemented
- **Frontend:** Shows UI (disabled)
- **Action:** REMOVE from UI

---

## Admin vs Website Parity

### Models in Admin but NOT in Website UI:

1. **GameProfile (Full Model)**
   - Admin: Shows all fields (in_game_name, game_id, rank, rank_tier, region, lft_status, is_pinned, sort_order)
   - Website: Only shows basic display + placeholder buttons
   - **Action:** Wire full CRUD in settings

2. **HardwareGear**
   - Admin: Full CRUD (category, brand, model_name, specs)
   - Website: Form exists but could be improved
   - **Action:** Redesign as category-based editor

3. **PrivacySettings (14 fields)**
   - Admin: Shows all 14 toggles
   - Website: Only shows subset
   - **Action:** Expand UI to match admin

4. **Platform Preferences (4 fields)**
   - Admin: preferred_language, timezone_pref, time_format, theme_preference
   - Website: NOT IN UI
   - **Action:** Add Platform tab

5. **VerificationRecord (KYC)**
   - Admin: Full model (document_type, document_number, status, verified_at)
   - Website: Placeholder UI only
   - **Action:** Wire upload + status check

---

## Template Issues Found

### Disabled Sections
```html
<!-- Line 160: Disabled section style (gray out + no interaction) -->
.disabled-section {
    opacity: 0.5;
    pointer-events: none;
}
```

**Current Usage:**
- ❌ NO disabled-section classes found in template (already cleaned up in Phase 6B)

### "Coming Soon" Placeholders
```javascript
// Line 1753
showToast('⚠️ Game passport deletion coming soon', 'info');

// Line 1759
showToast('⚠️ Game linking wizard coming soon', 'info');
```

**Action:** REPLACE with real API calls to:
- `POST /api/game-passports/delete/` (backend ready)
- `POST /api/game-passports/create/` (backend ready)

---

## Missing Templates (Critical)

1. **economy/wallet_dashboard.html** - Referenced but doesn't exist
2. **economy/withdrawal_request.html** - Withdrawal flow broken
3. **economy/transaction_history.html** - History page missing

---

## Action Priority Matrix

### P0 (Critical - Blocks Production)
1. ✅ CREATE Platform Preferences tab (backend ready, just wire UI)
2. ✅ WIRE Game Passports CRUD (remove placeholders, use existing APIs)
3. ✅ FIX Wallet templates (create missing HTML files)
4. ✅ EXPAND Privacy Settings UI (show all 14 toggles)

### P1 (High - Production-Grade UX)
5. ✅ ADD Follow Requests management UI (list/approve/reject)
6. ✅ REDESIGN Career & LFT (make game-aware, show per-game teams)
7. ✅ REDESIGN Pro Loadout (category-based hardware editor)
8. ✅ WIRE KYC upload flow (backend exists, UI placeholder)

### P2 (Medium - Polish)
9. ✅ ADD Stream URL validation (client-side + backend)
10. ✅ REMOVE Notifications "Quiet Hours" (not desired)
11. ✅ VERIFY Danger Zone flow (account deletion scheduling)

### P3 (Low - Future Enhancement)
12. 🔜 ADD gender field (if backend supports)
13. 🔜 ADD language switcher (Bengali "Coming Soon")
14. 🔜 ADD pro presets for loadouts (requires seeded data)

---

## Verification Checklist

After implementation, verify:

### Settings → Profile Sync
- [ ] Change display_name in settings → Reflects on public profile instantly
- [ ] Toggle privacy setting → Profile page respects it immediately
- [ ] Enable private account → Non-followers blocked correctly
- [ ] Change inventory visibility → Inventory page enforces it
- [ ] Update passport → Profile passports section updates
- [ ] Change platform prefs → All timestamps/currency formatted correctly

### Admin Parity
- [ ] All fields in GameProfile admin are editable on website
- [ ] All privacy toggles in admin UI exist on website
- [ ] Platform preferences match admin fieldset
- [ ] HardwareGear CRUD possible on website

### No Hardcoded Values
- [ ] Game list loaded from `/api/games/` (no hardcoded array)
- [ ] Social platforms loaded from `/api/social-links/platforms/`
- [ ] Privacy presets from `/api/privacy/presets/`
- [ ] Timezone list from backend service
- [ ] Currency list from backend service

### Template Helpers Work
- [ ] `{% format_dt_context transaction.created_at %}` shows correct format (12h/24h)
- [ ] `{% format_money_context wallet.balance %}` shows correct currency symbol
- [ ] Timestamps respect user timezone (middleware activates it)

---

## Next Steps

1. **Implement Step 1:** Platform Wiring (add Platform tab, wire middleware, add template helpers)
2. **Implement Step 2:** Settings → Profile Sync (verify all changes reflect everywhere)
3. **Implement Steps 3-4:** Feature-by-feature rebuild (Game Passports, Career/LFT, Wallet, etc)
4. **Add Tests:** Comprehensive endpoint + template tests
5. **Manual QA:** Production checklist verification

---

## Conclusion

**Good News:**
- Backend is MORE complete than UI suggests
- Phase 5A (Platform Prefs) is production-ready
- Most APIs already exist and are tested

**Bad News:**
- UI shows placeholders for features that actually work
- Some templates are missing (wallet pages)
- Settings don't sync to profile instantly (need verification)

**Estimated Effort:**
- Platform Wiring (Step 1): 2-3 hours
- Settings Sync (Step 2): 1-2 hours
- Feature Rebuilds (Steps 3-4): 8-12 hours total
- Testing: 2-3 hours
- **Total: 13-20 hours for production-grade settings system**
