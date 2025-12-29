# Phase 6 Part C: Settings Page Redesign - Architecture Plan

**Start Date:** December 29, 2025  
**Status:** 🚧 Planning Complete - Ready for Implementation

---

## 🎯 OBJECTIVES

Transform settings from a 2000-line monolithic page into a **production-grade, enterprise-level settings system** matching:
- Epic Games Account Settings
- Google Account Settings
- Steam Profile Settings
- Riot Account Management

**Success Criteria:**
1. Every setting persists correctly to backend
2. Settings influence real platform behavior
3. Modern, intuitive UX with clear information architecture
4. No fake toggles or placeholder logic
5. Mobile-responsive with proper navigation
6. Admin panel reflects new structure

---

## 📊 CURRENT STATE ANALYSIS

### Existing Settings Page
- **File:** `templates/user_profile/profile/settings.html`
- **Size:** 1,993 lines, 101KB
- **View:** `views.fe_v2.profile_settings_v2`
- **Route:** `/me/settings/`

### Current Sections (11 total)
1. **Profile & Media** - Avatar, banner, display name, bio
2. **Game Passports** - IGN, rank, region per game
3. **Social Links** - Platform links (twitter, twitch, discord, etc.)
4. **Privacy** - Duplicates privacy page (redundant)
5. **KYC** - Legal name, ID verification
6. **Contact** - Email, phone
7. **Demographics** - Age, gender, pronouns
8. **Emergency** - Emergency contact info
9. **Platform** - Language, timezone, theme
10. **Security** - Password change, 2FA
11. **Danger Zone** - Account deletion

### Problems Identified
1. ❌ **Redundant Privacy Section** - Already have `/me/privacy/` page
2. ❌ **Poor Information Architecture** - KYC/Emergency shouldn't be in settings
3. ❌ **Missing Wallet Section** - Earnings/withdrawals not integrated
4. ❌ **Monolithic Template** - 2000 lines makes maintenance impossible
5. ❌ **Inconsistent Persistence** - Some sections save, some don't
6. ❌ **No Notifications Section** - Email/platform notifications scattered

---

## 🏗️ NEW ARCHITECTURE

### 1. SETTINGS SECTIONS (6 Core + 1 Meta)

#### **1. Profile** (Public Identity)
**Purpose:** Control how you appear to others

**Fields:**
- Avatar upload (image file)
- Banner upload (image file)
- Display name (text, 3-30 chars)
- Bio (textarea, max 500 chars)
- Location (country dropdown)
- Pronouns (text, optional)

**Persistence:**
- Model: `UserProfile`
- Endpoint: `/me/settings/basic/` (existing)
- Method: POST with multipart/form-data

**Backend Status:** ✅ Fully wired (`update_basic_info` view)

---

#### **2. Privacy** (Visibility Controls)
**Purpose:** Control what others can see

**NOTE:** This should **link to** `/me/privacy/` page, NOT duplicate it.

**UI in Settings:**
- Card showing current privacy level:
  - "Your profile is **Public**" (with icon)
  - "Your profile is **Friends Only**"
  - "Your profile is **Private**"
- Button: "Manage Privacy Settings" → links to `/me/privacy/`
- Quick summary: "X of Y sections visible"

**Rationale:** Privacy is complex enough to deserve its own page. Settings should have a summary card + link only.

**Backend Status:** ✅ Fully wired (`PrivacySettings` model, `profile_privacy_v2` view)

---

#### **3. Notifications** (Communication Preferences)
**Purpose:** Control how platform contacts you

**Fields:**
- **Email Notifications**
  - Tournament reminders (toggle)
  - Match results (toggle)
  - Team invites (toggle)
  - Achievement unlocks (toggle)
  - Platform updates (toggle)
  
- **Platform Notifications** (in-app)
  - Tournament start alerts (toggle)
  - Team messages (toggle)
  - Follow notifications (toggle)
  - Achievement popups (toggle)

**Persistence:**
- Model: `NotificationPreferences` (NEW - needs creation)
- Endpoint: `/me/settings/notifications/` (NEW)
- Method: POST JSON

**Backend Status:** ❌ **NEEDS CREATION**

**Migration Required:**
```python
# apps/user_profile/models.py
class NotificationPreferences(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='notification_prefs')
    
    # Email notifications
    email_tournament_reminders = models.BooleanField(default=True)
    email_match_results = models.BooleanField(default=True)
    email_team_invites = models.BooleanField(default=True)
    email_achievements = models.BooleanField(default=False)
    email_platform_updates = models.BooleanField(default=True)
    
    # Platform notifications (in-app)
    notify_tournament_start = models.BooleanField(default=True)
    notify_team_messages = models.BooleanField(default=True)
    notify_follows = models.BooleanField(default=True)
    notify_achievements = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_notification_preferences'
        verbose_name = 'Notification Preferences'
        verbose_name_plural = 'Notification Preferences'
```

---

#### **4. Platform Preferences** (User Experience)
**Purpose:** Customize how platform works for you

**Fields:**
- **Language** (dropdown)
  - Options: English (only for now)
  - Badge: "Coming Soon" for other languages
  - **Must persist** (even though only English works)
  - Field: `preferred_language` on `UserProfile` (already exists)
  
- **Timezone** (dropdown)
  - Options: All world timezones
  - Used for: Tournament times, match schedules, activity timestamps
  - Field: `timezone` on `UserProfile` (already exists)
  
- **Time Format** (radio)
  - Options: 12-hour (3:00 PM) / 24-hour (15:00)
  - Field: `time_format` on `UserProfile` (NEW)
  
- **Theme** (radio)
  - Options: Light / Dark / System
  - Field: `theme_preference` on `UserProfile` (NEW)
  - Default: 'dark'

**Persistence:**
- Model: `UserProfile` (extend existing)
- Endpoint: `/me/settings/platform/` (NEW)
- Method: POST JSON

**Backend Status:** ⚠️ **PARTIAL** (timezone/language exist, time_format/theme need fields)

**Migration Required:**
```python
# Add to UserProfile model
time_format = models.CharField(
    max_length=10,
    choices=[('12h', '12-hour'), ('24h', '24-hour')],
    default='12h'
)
theme_preference = models.CharField(
    max_length=10,
    choices=[('light', 'Light'), ('dark', 'Dark'), ('system', 'System')],
    default='dark'
)
```

---

#### **5. Wallet** (Earnings & Withdrawals)
**Purpose:** Manage tournament earnings and cash-outs

**Fields:**
- **Balance Display** (read-only)
  - Deltacoin balance: `{{ profile.deltacoin_balance }}` DC
  - USD equivalent: `${{ profile.deltacoin_balance_usd }}`
  - Last updated: timestamp
  
- **Withdrawal Methods**
  - bKash (toggle + account number input)
  - Nagad (toggle + account number input)
  - Rocket (toggle + account number input)
  - **No fake methods** - only Bangladesh mobile banking for now
  
- **Withdrawal Preferences**
  - Minimum threshold before auto-withdrawal (dropdown: 100 DC, 500 DC, 1000 DC, Manual only)
  - Auto-convert to USD (toggle)
  
- **Transaction History Link**
  - Button: "View Transaction History" → `/me/wallet/transactions/`

**Persistence:**
- Model: `WalletSettings` (NEW)
- Endpoint: `/me/settings/wallet/` (NEW)
- Method: POST JSON

**Backend Status:** ❌ **NEEDS CREATION**

**Migration Required:**
```python
# apps/user_profile/models.py
class WalletSettings(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='wallet_settings')
    
    # Withdrawal methods (Bangladesh mobile banking)
    bkash_enabled = models.BooleanField(default=False)
    bkash_account = models.CharField(max_length=20, blank=True)
    
    nagad_enabled = models.BooleanField(default=False)
    nagad_account = models.CharField(max_length=20, blank=True)
    
    rocket_enabled = models.BooleanField(default=False)
    rocket_account = models.CharField(max_length=20, blank=True)
    
    # Withdrawal preferences
    auto_withdrawal_threshold = models.IntegerField(default=0)  # 0 = manual only
    auto_convert_to_usd = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_wallet_settings'
        verbose_name = 'Wallet Settings'
        verbose_name_plural = 'Wallet Settings'
```

---

#### **6. Account** (Security & Danger Zone)
**Purpose:** Critical account management

**Subsections:**

**A. Security**
- Change password (form: current, new, confirm)
- Enable 2FA (toggle + QR code modal)
- Active sessions (list + "Logout All" button)
- Login history (last 10 logins with IP/device)

**B. Danger Zone**
- Account deletion request
- Export data (GDPR compliance)
- Deactivate account (temporary)

**Persistence:**
- Password change: Django auth backend
- 2FA: `django-otp` or custom implementation
- Sessions: Django session framework
- Account deletion: Soft delete flag on User model

**Backend Status:** ⚠️ **PARTIAL** (password change exists, 2FA needs implementation)

---

#### **7. Game Passports** (Meta Section)
**Purpose:** This should be a **separate page** `/me/settings/passports/` linked from settings, NOT embedded.

**Rationale:** 
- Game passports are complex (schema per game, validation, region/rank dropdowns)
- Already have dedicated UI in current settings
- Should be its own route for deep linking (e.g., "Add passport" CTA from profile)

**UI in Settings:**
- Card showing passport count: "You have X game passports"
- Button: "Manage Game Passports" → links to `/me/settings/passports/`

---

### 2. INFORMATION ARCHITECTURE

#### Removed from Settings (Not User-Facing)
1. **KYC/Legal** - Should be admin-only or payment flow, not settings
2. **Emergency Contact** - Should be admin-only or registration flow
3. **Demographics** - Should be optional profile wizard, not settings

#### Why Remove These?
- Epic Games: No KYC in account settings (handled in payment flow)
- Google Account: No emergency contact (privacy liability)
- Steam: No demographics in settings (optional community features)

**Professional platforms hide compliance fields from settings.**

---

### 3. NAVIGATION STRUCTURE

#### Desktop Layout
```
┌─────────────────────────────────────────────┐
│ [Settings Header with "Preview Profile"]    │
├───────────────┬─────────────────────────────┤
│ Left Nav      │ Content Area                │
│ (300px fixed) │ (flexible)                  │
│               │                             │
│ 👤 Profile    │ [Active Section Content]    │
│ 🔒 Privacy    │                             │
│ 🔔 Notifs     │ [Forms, toggles, inputs]    │
│ ⚙️ Platform   │                             │
│ 💰 Wallet     │ [Save buttons per section]  │
│ 🛡️ Account    │                             │
│               │ [Success/error feedback]    │
└───────────────┴─────────────────────────────┘
```

#### Mobile Layout
```
┌─────────────────────┐
│ [Header]            │
├─────────────────────┤
│ [Hamburger Menu]    │  ← Toggles nav drawer
├─────────────────────┤
│                     │
│ [Active Section]    │
│                     │
│ [Content stacks]    │
│                     │
└─────────────────────┘
```

---

### 4. TECHNICAL IMPLEMENTATION PLAN

#### Phase C.1: Backend Preparation
1. ✅ Verify existing endpoints work
2. ❌ Create `NotificationPreferences` model + migration
3. ❌ Create `WalletSettings` model + migration
4. ❌ Add `time_format`, `theme_preference` to `UserProfile`
5. ❌ Create `/me/settings/notifications/` endpoint
6. ❌ Create `/me/settings/wallet/` endpoint
7. ❌ Create `/me/settings/platform/` endpoint
8. ✅ Verify privacy settings endpoint works

#### Phase C.2: Frontend Redesign
1. ❌ Create new settings template (modular, <500 lines)
2. ❌ Create section components (profile, notifications, platform, wallet, account)
3. ❌ Implement left navigation (desktop + mobile)
4. ❌ Wire all forms to endpoints
5. ❌ Add success/error feedback per section
6. ❌ Implement unsaved changes warning
7. ❌ Add loading states for async saves

#### Phase C.3: Admin Panel Cleanup
1. ❌ Update `UserProfile` admin (add new fields)
2. ❌ Create `NotificationPreferences` admin
3. ❌ Create `WalletSettings` admin
4. ❌ Remove deprecated fields from admin
5. ❌ Add inline admins where appropriate
6. ❌ Improve field grouping and help text

#### Phase C.4: Testing & Verification
1. ❌ Manual test all settings persist correctly
2. ❌ Verify timezone affects timestamps
3. ❌ Verify theme changes work
4. ❌ Verify notification preferences save
5. ❌ Verify wallet settings save
6. ❌ Test mobile navigation
7. ❌ Test unsaved changes warning

#### Phase C.5: Documentation
1. ❌ Create `UP_PHASE6_PARTC_API_MAP.md` (all endpoints)
2. ❌ Create `UP_PHASE6_PARTC_ADMIN_UPDATE.md` (admin changes)
3. ❌ Create `UP_PHASE6_PARTC_COMPLETION_REPORT.md` (summary)

---

## 🔌 API ENDPOINT MAP

### Existing Endpoints ✅
| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/me/settings/basic/` | POST | Update display name, bio, country | ✅ Working |
| `/me/settings/media/` | POST | Upload avatar/banner | ✅ Working |
| `/me/settings/media/remove/` | POST | Remove avatar/banner | ✅ Working |
| `/me/settings/social/` | POST | Update social links | ✅ Working |
| `/me/settings/privacy/` | GET | Get privacy settings | ✅ Working |
| `/me/settings/privacy/save/` | POST | Update privacy settings | ✅ Working |

### New Endpoints Required ❌
| Endpoint | Method | Purpose | Payload | Response |
|----------|--------|---------|---------|----------|
| `/me/settings/notifications/` | POST | Update notification prefs | `{email_tournament_reminders: bool, ...}` | `{success: bool, message: str}` |
| `/me/settings/platform/` | POST | Update platform prefs | `{language: str, timezone: str, time_format: str, theme: str}` | `{success: bool, message: str}` |
| `/me/settings/wallet/` | POST | Update wallet settings | `{bkash_enabled: bool, bkash_account: str, ...}` | `{success: bool, message: str}` |
| `/me/settings/account/password/` | POST | Change password | `{current_password: str, new_password: str}` | `{success: bool, message: str}` |

---

## 🎨 UX/UI PRINCIPLES

### 1. Glassmorphism Design
- All sections in glass cards
- Subtle gradients for visual hierarchy
- Consistent border colors (slate-700/50)
- Backdrop blur for depth

### 2. Clear Information Hierarchy
- Section titles: 1.5rem, font-bold
- Subsection titles: 1.25rem, font-semibold
- Labels: 0.875rem, uppercase, tracking-wide, text-slate-400
- Help text: 0.75rem, text-slate-500

### 3. Interaction Feedback
- Save buttons: Gradient background, hover scale
- Success states: Green checkmark icon + message (fade out after 3s)
- Error states: Red X icon + message (persist until dismissed)
- Loading states: Spinner animation on button

### 4. Form Validation
- Client-side validation (HTML5 + custom JS)
- Server-side validation (Django forms)
- Inline error messages below fields
- Highlight invalid fields with red border

### 5. Mobile Responsiveness
- Left nav collapses to hamburger < 1024px
- Form inputs stack vertically < 640px
- Touch-friendly targets (min 44px)
- Swipe gestures for section navigation

---

## 🚧 IMPLEMENTATION CONSTRAINTS

### Must Follow
1. ✅ NO fake saves - every toggle/input persists
2. ✅ NO placeholder logic (except "Coming Soon" for language)
3. ✅ NO backend rewrites outside settings scope
4. ✅ NO UI that doesn't persist data
5. ✅ NO regressions to Phase 6 Part B (profile page)

### Can Modify
1. ✅ Create new models (NotificationPreferences, WalletSettings)
2. ✅ Add fields to existing models (UserProfile)
3. ✅ Create new endpoints (notifications, platform, wallet)
4. ✅ Restructure settings template (from 2000 lines → modular)
5. ✅ Update admin panel (reflect new structure)

---

## 📈 SUCCESS METRICS

### Functional Requirements
- [ ] All 6 core sections render correctly
- [ ] All forms submit successfully
- [ ] All settings persist to database
- [ ] Settings influence platform behavior (timezone, theme, notifications)
- [ ] Privacy page linked (not duplicated)
- [ ] Game passports linked (not embedded)

### UX Requirements
- [ ] Settings page < 800 lines (modular components)
- [ ] Navigation intuitive (no confusion)
- [ ] Mobile navigation works smoothly
- [ ] Success/error feedback clear
- [ ] Unsaved changes warning works
- [ ] Loading states prevent double-submit

### Admin Requirements
- [ ] All new models in admin
- [ ] Field grouping logical
- [ ] Help text clear
- [ ] No deprecated fields visible
- [ ] Inline admins where appropriate

---

## 🎯 NEXT STEPS

1. **Start with Backend (C.1)**
   - Create migrations for new models
   - Create API endpoints
   - Write endpoint tests
   
2. **Then Frontend (C.2)**
   - Redesign settings template
   - Wire all forms
   - Add feedback mechanisms
   
3. **Then Admin (C.3)**
   - Update admin registrations
   - Improve field organization
   
4. **Then Testing (C.4)**
   - Manual verification
   - Edge case testing
   
5. **Finally Documentation (C.5)**
   - API map
   - Admin update notes
   - Completion report

---

**Architecture Complete ✅**  
**Ready for Implementation 🚀**  
**Last Updated:** December 29, 2025
