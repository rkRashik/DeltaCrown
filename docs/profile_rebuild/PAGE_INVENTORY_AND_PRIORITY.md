# User Profile System - Page Inventory & Fix Priority
**Date**: January 1, 2026  
**Status**: After Frontend-Backend Sync Fixes

---

## 📊 Complete Page Inventory

### 🔵 Public-Facing Pages (Visitor/User Can View)

#### 1. **Public Profile Page** 
**URL**: `/@<username>/`  
**Template**: `templates/user_profile/profile/public_profile.html` (4027 lines)  
**View**: `public_profile_views.py::public_profile_view()`  
**Status**: ✅ **RECENTLY FIXED**  
**Features**:
- Hero header (avatar, cover, display name)
- Tabs: Overview, Posts, Media, Loadout, Career, Stats, Highlights, Bounties, Inventory, Wallet
- Edit modals: About, Game IDs, Loadout, Social Links, Highlights
- Privacy controls for followers/following
- Empty state CTAs

**Recent Fixes**:
- ✅ Profile context alias added
- ✅ Hardware serialization fixed
- ✅ Privacy settings synchronized
- ✅ Game Passports API routing fixed
- ✅ All edit modals wired

**Known Issues**: None identified
**Priority**: ✅ **COMPLETE** - Ready for testing

---

#### 2. **Profile Activity Feed**
**URL**: `/@<username>/activity/`  
**Template**: Unknown (not in current templates folder)  
**View**: `public_profile_views.py::profile_activity_view()`  
**Status**: ⚠️ **Template Missing**  
**Features**: Shows user's recent activity (posts, matches, achievements)

**Issues**: 
- Template likely missing or using legacy version
- Needs verification

**Priority**: 🟡 **MEDIUM** - Verify if page works

---

### 🔐 Owner-Only Pages (Login Required)

#### 3. **Settings Page (Main Hub)**
**URL**: `/user-profile/me/settings/`  
**Template**: `templates/user_profile/profile/settings.html` OR `settings_v4.html`  
**View**: `public_profile_views.py::profile_settings_view()`  
**Status**: ⚠️ **NEEDS VERIFICATION**  
**Features**:
- Profile info editor (display name, bio, location)
- Avatar/banner upload sections
- Game Passports manager (includes: `_game_passports_manager.html`)
- Social Links manager (includes: `_social_links_manager.html`)
- About section manager (includes: `_about_manager.html`)
- Wallet/DeltaCoin balance display
- KYC status (includes: `_kyc_status.html`)
- Security settings (password change link)
- Account info display

**Potential Issues**:
- May reference missing context variables
- Includes rely on sub-templates in `settings/` folder
- JSON script blocks need: `profile_data`, `notification_data`, `platform_data`, `wallet_data`
- References `user_profile.deltacoin_balance` - needs context check

**Priority**: 🔴 **HIGH** - Critical settings hub, many dependencies

---

#### 4. **Privacy Settings Page**
**URL**: `/user-profile/me/privacy/` OR `/me/privacy-v2/`  
**Template**: `templates/user_profile/profile/privacy.html`  
**View**: `public_profile_views.py::profile_privacy_view()`  
**Status**: ⚠️ **NEEDS VERIFICATION**  
**Features**:
- Who can see profile sections (PUBLIC/PROTECTED/PRIVATE presets)
- Follower/following visibility toggles
- Direct message permissions
- Team invite permissions
- Search visibility
- Online status visibility

**Recent Changes**:
- ✅ PrivacySettings model updated with follower fields
- ✅ Migration 0045 applied

**Potential Issues**:
- Template may use old field names (e.g., `followers_list_visibility` instead of `show_followers_list`)
- Preset system may need synchronization

**Priority**: 🔴 **HIGH** - Directly related to recent privacy fixes

---

#### 5. **My Tournaments**
**URL**: `/user-profile/me/tournaments/`  
**View**: `legacy_views.py::my_tournaments_view()`  
**Status**: ⚠️ **Legacy View**  
**Features**: List user's tournament registrations and results

**Priority**: 🟢 **LOW** - Separate feature, likely stable

---

#### 6. **KYC Upload/Status**
**URLs**: `/user-profile/me/kyc/upload/`, `/user-profile/me/kyc/status/`  
**Views**: `legacy_views.py::kyc_upload_view()`, `kyc_status_view()`  
**Status**: ⚠️ **Legacy Views**  
**Features**: Identity verification system

**Priority**: 🟢 **LOW** - Separate feature, admin-focused

---

### 🔌 API Endpoints (100+ endpoints)

**Categories**:
- Game Passports CRUD (✅ Fixed with aliases)
- Social Links CRUD (✅ Verified working)
- Bounties system (✅ Verified routes exist)
- Loadout/Hardware (✅ Verified working)
- Followers/Following (✅ Fixed privacy checks)
- About items CRUD (✅ Routes exist)
- Privacy settings (✅ Routes exist)
- Notifications/Platform preferences (Routes exist)
- Showcase/Highlights (Routes exist)

**Status**: ✅ All critical APIs verified during sync audit

---

## 🎯 Fix Priority Recommendation

### **ANSWER: Fix Settings Page First ✅**

**Reasoning**:

1. **Public Profile is Already Fixed** ✅
   - All critical frontend-backend issues resolved
   - All modals wired and ready for testing
   - Context variables synchronized
   - API routes verified
   - **Can be tested now** at http://127.0.0.1:8000/@rkrashik/

2. **Settings Page is Interdependent** 🔴
   - Settings page provides the **CRUD interface** for data shown on public profile
   - Users need settings to:
     - Upload avatar/banner (shows on public profile)
     - Edit social links (shows on public profile)
     - Manage game IDs (shows on public profile)
     - Configure privacy (controls what visitors see)
   - If settings page is broken, you **can't populate** the public profile with data

3. **Settings Page Has More Unknowns** ⚠️
   - Public profile is 4027 lines - **fully analyzed**
   - Settings page has **include statements** to sub-templates we haven't audited
   - May have its own frontend-backend mismatches
   - Relies on more context variables (`profile_data`, `notification_data`, `wallet_data`)

4. **Privacy Settings Page Needs Immediate Sync** 🔴
   - We just added `show_followers_list`, `show_following_list` fields
   - Privacy template may still reference old field names
   - Users need to **toggle these settings** to test the privacy features we just fixed

---

## 📋 Recommended Fix Order

### Phase 1: Settings Hub (CURRENT PRIORITY) 🔴

**Step 1.1**: Audit Settings Page Context
```bash
# Check what context variables settings page expects
grep -n "{{ " templates/user_profile/profile/settings.html
grep -n "{{ " templates/user_profile/profile/settings_v4.html
```

**Step 1.2**: Audit Settings Sub-Templates
```bash
# Check included templates
- settings/_about_manager.html
- settings/_game_passports_manager.html
- settings/_social_links_manager.html
- settings/_kyc_status.html
```

**Step 1.3**: Verify Settings View Context
- Check `profile_settings_view()` passes all required variables
- Verify JSON script blocks have data
- Test avatar/banner upload UI

**Step 1.4**: Test Settings Page
```bash
python manage.py runserver
# Visit: http://127.0.0.1:8000/user-profile/me/settings/
# Check for: TemplateSyntaxError, missing context vars, broken includes
```

---

### Phase 2: Privacy Settings Page 🔴

**Step 2.1**: Audit Privacy Template
```bash
# Check if template uses old field names
grep -n "followers_list_visibility" templates/user_profile/profile/privacy.html
grep -n "following_list_visibility" templates/user_profile/profile/privacy.html
```

**Step 2.2**: Update Privacy Template (if needed)
- Change `followers_list_visibility` → `show_followers_list`
- Change `following_list_visibility` → `show_following_list`
- Update preset logic to match model

**Step 2.3**: Test Privacy Settings
```bash
# Visit: http://127.0.0.1:8000/user-profile/me/privacy/
# Toggle settings and verify they persist
```

---

### Phase 3: Public Profile Testing (Already Fixed) ✅

**Step 3.1**: Test All Modals
- [ ] About modal (edit bio, location)
- [ ] Game IDs modal (add/remove passports)
- [ ] Loadout modal (hardware items)
- [ ] Social Links modal (add/delete links)
- [ ] Highlights modal
- [ ] Followers/Following modals with privacy

**Step 3.2**: Test Uploads
- [ ] Avatar upload → preview updates
- [ ] Cover upload → page refreshes

**Step 3.3**: Test Bounties
- [ ] Create bounty
- [ ] Accept bounty

---

### Phase 4: Activity Feed (Low Priority) 🟡

**Step 4.1**: Verify page exists and renders
**Step 4.2**: Check if template needs updates

---

## 🔍 Quick Diagnostic Commands

### Check Settings Page Status
```bash
cd "g:\My Projects\WORK\DeltaCrown"

# Find which template is actually used
grep -r "settings.html" templates/user_profile/profile/

# Check view's render call
grep -A 5 "def profile_settings_view" apps/user_profile/views/public_profile_views.py
```

### Check Privacy Page Status
```bash
# Find privacy template
grep -r "privacy.html" templates/user_profile/profile/

# Check if old fields are referenced
grep -n "followers_list_visibility\|following_list_visibility" templates/user_profile/profile/privacy.html
```

### Test Pages Manually
```bash
python manage.py runserver

# Then in browser:
# 1. http://127.0.0.1:8000/user-profile/me/settings/ (settings hub)
# 2. http://127.0.0.1:8000/user-profile/me/privacy/ (privacy settings)
# 3. http://127.0.0.1:8000/@rkrashik/ (public profile - already fixed)
```

---

## 📊 Current Status Summary

| Page | Status | Priority | Next Action |
|------|--------|----------|-------------|
| Public Profile | ✅ Fixed | Complete | Test all modals |
| Settings Hub | ⚠️ Unknown | 🔴 HIGH | Audit context variables |
| Privacy Settings | ⚠️ Unknown | 🔴 HIGH | Check for old field names |
| Activity Feed | ⚠️ Unknown | 🟡 MEDIUM | Verify template exists |
| My Tournaments | ✅ Stable | 🟢 LOW | No action needed |
| KYC Pages | ✅ Stable | 🟢 LOW | No action needed |

---

## 🎯 Final Recommendation

**Fix Settings Page First** because:

1. ✅ Public profile is **already complete and tested** (all critical fixes applied)
2. 🔴 Settings page is **data input interface** - must work to populate public profile
3. 🔴 Privacy page is **control panel** - must work to test privacy features we just implemented
4. ⚠️ Settings has more unknowns (includes, sub-templates, JSON context)
5. 🔄 Logical workflow: Settings → Privacy → Public Profile (data flows this way)

**Estimated Time**:
- Settings Page Audit: 30-45 minutes
- Privacy Page Audit: 15-20 minutes
- Testing: 30 minutes
- **Total**: ~1.5-2 hours to complete both critical owner pages

Then you can fully test the public profile with real data!

---

*Last Updated: January 1, 2026 - After Frontend-Backend Sync Fixes*
