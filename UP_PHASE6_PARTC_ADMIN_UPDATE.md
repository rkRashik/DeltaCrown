# Phase 6 Part C - Admin Panel Documentation
**DeltaCrown Esports Platform | Admin Configuration Update**

> Last Updated: 2025-12-29  
> Status: Production Ready ✅  
> Access: Superuser only (`/admin/`)

---

## Overview

Phase 6 Part C adds **2 new admin models** and **updates UserProfileAdmin** with enhanced settings management capabilities. These changes enable platform administrators to manage user notification preferences, wallet configurations, and platform preferences directly from the Django admin interface.

---

## 1. NotificationPreferencesAdmin

**Model:** `NotificationPreferences`  
**Admin Class:** `NotificationPreferencesAdmin`  
**Location:** `apps/user_profile/admin.py`  
**Access URL:** `/admin/user_profile/notificationpreferences/`

### Features

#### List Display
Shows key fields in admin list view:
- **User Profile** (link to associated UserProfile)
- **Email: Tournament Reminders** (✓/✗ icon)
- **Email: Match Results** (✓/✗ icon)
- **Email: Team Invites** (✓/✗ icon)
- **Platform: Tournament Start** (✓/✗ icon)
- **Platform: Team Messages** (✓/✗ icon)

#### Search & Filtering
- **Search Fields:** User's username, display name
- **List Filters:** 
  - Email tournament reminders enabled/disabled
  - Email match results enabled/disabled
  - Platform tournament notifications enabled/disabled

#### Fieldsets

##### Email Notifications
- `email_tournament_reminders` - Send email before tournaments start
- `email_match_results` - Send email after matches complete
- `email_team_invites` - Send email for team invitations
- `email_achievements` - Send email for new achievements
- `email_platform_updates` - Send email for platform announcements

##### Platform Notifications
- `platform_tournament_start` - In-app notification when tournament begins
- `platform_team_messages` - In-app notification for team chat messages
- `platform_follows` - In-app notification for new followers
- `platform_achievements` - In-app notification for achievements

### Permissions
- **Add:** Superuser only (auto-created on user registration)
- **Change:** Superuser only
- **Delete:** Superuser only (not recommended - breaks OneToOne relationship)
- **View:** Superuser only

### Business Logic
- OneToOne relationship with UserProfile (one set of preferences per user)
- Defaults applied on model creation (see model definition)
- No custom save() override - standard Django admin behavior

### Example Admin Actions

**Bulk Enable Tournament Reminders:**
```python
# In admin.py, add custom action:
@admin.action(description='Enable tournament reminders for selected users')
def enable_tournament_reminders(modeladmin, request, queryset):
    queryset.update(email_tournament_reminders=True, platform_tournament_start=True)
    
# Register action in NotificationPreferencesAdmin:
actions = [enable_tournament_reminders]
```

---

## 2. WalletSettingsAdmin

**Model:** `WalletSettings`  
**Admin Class:** `WalletSettingsAdmin`  
**Location:** `apps/user_profile/admin.py`  
**Access URL:** `/admin/user_profile/walletsettings/`

### Features

#### List Display
Shows key financial configuration:
- **User Profile** (link to associated UserProfile)
- **bKash Enabled** (✓/✗ icon)
- **bKash Account** (masked: `017****5678`)
- **Nagad Enabled** (✓/✗ icon)
- **Rocket Enabled** (✓/✗ icon)
- **Auto-Withdrawal Threshold** (e.g., `1000 DC`)
- **Auto-Convert to USD** (✓/✗ icon)

#### Search & Filtering
- **Search Fields:** User's username, display name, bKash account number (full search for admins)
- **List Filters:**
  - bKash enabled/disabled
  - Nagad enabled/disabled
  - Rocket enabled/disabled
  - Auto-withdrawal enabled/disabled

#### Fieldsets

##### Mobile Banking Configuration
- `bkash_enabled` - Enable bKash withdrawals
- `bkash_account` - bKash mobile number (validated: 01[3-9]\d{8})
- `nagad_enabled` - Enable Nagad withdrawals
- `nagad_account` - Nagad mobile number (validated: 01[3-9]\d{8})
- `rocket_enabled` - Enable Rocket withdrawals
- `rocket_account` - Rocket mobile number (validated: 01[3-9]\d{8})

##### Withdrawal Preferences
- `auto_withdrawal_threshold` - Auto-withdraw when balance exceeds (DC)
- `auto_convert_to_usd` - Automatically convert DeltaCoin to USD

### Permissions
- **Add:** Superuser only (auto-created on user registration)
- **Change:** Superuser only
- **Delete:** Superuser only (not recommended - breaks OneToOne relationship)
- **View:** Superuser only

### Validation
- **Mobile Numbers:** RegexValidator ensures Bangladesh mobile number format
- **Pattern:** `01[3-9]\d{8}` (e.g., `01712345678`)
- **Admin Errors:** Django admin shows inline validation errors on save

### Security Considerations
- **PII Data:** Mobile numbers are sensitive - admin access logs should be monitored
- **Masked Display:** Consider implementing custom ModelAdmin to mask account numbers in list view
- **Audit Trail:** Recommend adding change logging for financial settings modifications

### Example Admin Actions

**Bulk Disable Auto-Withdrawals:**
```python
@admin.action(description='Disable auto-withdrawals for selected users')
def disable_auto_withdrawals(modeladmin, request, queryset):
    queryset.update(auto_withdrawal_threshold=0)

# Register action in WalletSettingsAdmin:
actions = [disable_auto_withdrawals]
```

---

## 3. UserProfileAdmin Updates

**Model:** `UserProfile`  
**Admin Class:** `UserProfileAdmin` (existing, now enhanced)  
**Location:** `apps/user_profile/admin.py`  
**Access URL:** `/admin/user_profile/userprofile/`

### New Fieldset: Platform Preferences

Added in Phase 6 Part C to manage user's interface preferences directly from admin.

#### Fields

| Field | Type | Choices | Default | Description |
|-------|------|---------|---------|-------------|
| `preferred_language` | CharField | `en`, `bn` | `en` | Interface language (Bengali coming soon) |
| `timezone_pref` | CharField | Any IANA timezone | `Asia/Dhaka` | User's timezone for timestamp display |
| `time_format` | CharField | `12h`, `24h` | `12h` | Time display format preference |
| `theme_preference` | CharField | `light`, `dark`, `system` | `dark` | UI theme preference |

#### Admin Display

**Fieldset Name:** "Platform Preferences"  
**Position:** After "Profile Settings" fieldset  
**Collapsible:** No (always visible)

**Layout:**
```python
{
    'fields': (
        ('preferred_language', 'timezone_pref'),
        ('time_format', 'theme_preference'),
    )
}
```

**Widgets:**
- `preferred_language`: Select dropdown (en/bn)
- `timezone_pref`: Text input with autocomplete (future: timezone picker widget)
- `time_format`: Radio buttons (12h/24h)
- `theme_preference`: Radio buttons (light/dark/system)

### New Inlines

#### NotificationPreferencesInline

**Type:** `StackedInline`  
**Model:** `NotificationPreferences`  
**Relationship:** OneToOne to UserProfile  
**Max Num:** 1 (enforced by OneToOne)

**Purpose:** Edit user's notification preferences directly from UserProfile admin page.

**Fields Shown:**
- Email Notifications (5 checkboxes)
- Platform Notifications (4 checkboxes)

**Extra:** 0 (no empty inline forms)

**Example:**
```
┌─ Notification Preferences ────────────────────────┐
│ ☑ Email: Tournament Reminders                     │
│ ☑ Email: Match Results                            │
│ ☑ Email: Team Invites                             │
│ ☐ Email: Achievements                             │
│ ☐ Email: Platform Updates                         │
│                                                    │
│ ☑ Platform: Tournament Start                      │
│ ☑ Platform: Team Messages                         │
│ ☐ Platform: Follows                               │
│ ☑ Platform: Achievements                          │
└────────────────────────────────────────────────────┘
```

#### WalletSettingsInline

**Type:** `StackedInline`  
**Model:** `WalletSettings`  
**Relationship:** OneToOne to UserProfile  
**Max Num:** 1 (enforced by OneToOne)

**Purpose:** Edit user's wallet configuration directly from UserProfile admin page.

**Fields Shown:**
- Mobile Banking (6 fields: 3 enabled checkboxes + 3 account inputs)
- Withdrawal Preferences (2 fields)

**Extra:** 0 (no empty inline forms)

**Example:**
```
┌─ Wallet Settings ──────────────────────────────────┐
│ ☑ bKash Enabled:  [01712345678_______________]     │
│ ☐ Nagad Enabled:  [_________________________]     │
│ ☐ Rocket Enabled: [_________________________]     │
│                                                    │
│ Auto-Withdrawal Threshold: [1000__] DC            │
│ ☐ Auto-Convert to USD                             │
└────────────────────────────────────────────────────┘
```

### Complete UserProfileAdmin Structure

**Updated Fieldsets:**
1. User Information (existing)
2. Profile Settings (existing)
3. **Platform Preferences** (NEW - Phase 6C)
4. Verification & Trust (existing)
5. Social Media (existing)
6. Gaming Stats (existing)

**Updated Inlines:**
1. GameProfileInline (existing)
2. **NotificationPreferencesInline** (NEW - Phase 6C)
3. **WalletSettingsInline** (NEW - Phase 6C)

**List Display:**
- Username
- Display Name
- Email (if verified)
- Level
- DeltaCoin Balance
- Is KYC Verified
- Date Joined

**Search Fields:**
- Username
- Display Name
- Email
- First Name
- Last Name

**List Filters:**
- Is KYC Verified
- Stream Status
- Preferred Language (NEW - Phase 6C)
- Theme Preference (NEW - Phase 6C)
- Date Joined

---

## 4. Admin Usage Guide

### Creating a New User Profile (with Settings)

1. Navigate to `/admin/user_profile/userprofile/add/`
2. Fill required fields (user, display name)
3. Scroll to **Platform Preferences** section → set language/timezone/theme
4. Scroll to **Notification Preferences** inline → check desired toggles
5. Scroll to **Wallet Settings** inline → enable payment methods if needed
6. Click **Save**

**Result:** UserProfile created with NotificationPreferences and WalletSettings auto-created via signals.

### Editing Existing User Settings

1. Navigate to `/admin/user_profile/userprofile/`
2. Search for user by username/email
3. Click user to edit
4. Modify:
   - **Platform Preferences** fieldset for language/timezone/theme
   - **Notification Preferences** inline for email/platform toggles
   - **Wallet Settings** inline for payment methods
5. Click **Save**

**Result:** All changes persisted immediately, user sees updates on next page refresh.

### Bulk Operations (Advanced)

**Enable Tournament Notifications for All Users:**
```python
# Django shell:
from apps.user_profile.models import NotificationPreferences
NotificationPreferences.objects.all().update(
    email_tournament_reminders=True,
    platform_tournament_start=True
)
```

**Change All Users to Dark Theme:**
```python
from apps.user_profile.models import UserProfile
UserProfile.objects.all().update(theme_preference='dark')
```

---

## 5. Database Schema Reference

### NotificationPreferences Table

**Table Name:** `user_profile_notificationpreferences`  
**Primary Key:** `id` (AutoField)  
**Foreign Key:** `user_profile_id` (OneToOne to UserProfile)

**Columns:**
- `id` (bigint, PK)
- `user_profile_id` (bigint, FK, unique)
- `email_tournament_reminders` (boolean, default: true)
- `email_match_results` (boolean, default: true)
- `email_team_invites` (boolean, default: true)
- `email_achievements` (boolean, default: false)
- `email_platform_updates` (boolean, default: false)
- `platform_tournament_start` (boolean, default: true)
- `platform_team_messages` (boolean, default: true)
- `platform_follows` (boolean, default: false)
- `platform_achievements` (boolean, default: true)

**Indexes:**
- PK on `id`
- Unique index on `user_profile_id`

---

### WalletSettings Table

**Table Name:** `user_profile_walletsettings`  
**Primary Key:** `id` (AutoField)  
**Foreign Key:** `user_profile_id` (OneToOne to UserProfile)

**Columns:**
- `id` (bigint, PK)
- `user_profile_id` (bigint, FK, unique)
- `bkash_enabled` (boolean, default: false)
- `bkash_account` (varchar(15), blank, validated)
- `nagad_enabled` (boolean, default: false)
- `nagad_account` (varchar(15), blank, validated)
- `rocket_enabled` (boolean, default: false)
- `rocket_account` (varchar(15), blank, validated)
- `auto_withdrawal_threshold` (integer, default: 1000)
- `auto_convert_to_usd` (boolean, default: false)

**Indexes:**
- PK on `id`
- Unique index on `user_profile_id`

**Constraints:**
- Mobile account numbers validated with regex: `^01[3-9]\d{8}$`

---

### UserProfile Table Updates

**New Columns (Phase 6C):**
- `preferred_language` (varchar(10), default: 'en', choices: en/bn)
- `timezone_pref` (varchar(50), default: 'Asia/Dhaka')
- `time_format` (varchar(5), default: '12h', choices: 12h/24h)
- `theme_preference` (varchar(10), default: 'dark', choices: light/dark/system)

**Migration:** `0030_phase6c_settings_models.py`

---

## 6. Troubleshooting

### Issue: Inline not showing in admin

**Symptom:** NotificationPreferencesInline or WalletSettingsInline not visible  
**Cause:** Model not created for user (signal failed or missing)  
**Solution:**
```python
# Django shell:
from apps.user_profile.models import UserProfile, NotificationPreferences, WalletSettings

profile = UserProfile.objects.get(user__username='username')

# Create missing preferences:
NotificationPreferences.objects.get_or_create(user_profile=profile)
WalletSettings.objects.get_or_create(user_profile=profile)
```

### Issue: Validation error on mobile number

**Symptom:** "Enter a valid value" error when saving bKash/Nagad/Rocket account  
**Cause:** Invalid Bangladesh mobile number format  
**Valid Format:** Must match `01[3-9]\d{8}` (e.g., `01712345678`)  
**Invalid Examples:**
- `1712345678` (missing leading 0)
- `01012345678` (invalid prefix - must be 013-019)
- `017123456` (too short - must be 11 digits)

### Issue: Platform preferences not syncing to frontend

**Symptom:** User changes theme in admin but doesn't see it on website  
**Cause:** Frontend template not reading UserProfile fields correctly  
**Solution:** Verify template context includes `user_profile.theme_preference` and CSS applies theme classes.

---

## 7. Best Practices

### Data Integrity
- **Never delete** NotificationPreferences or WalletSettings records directly - always delete through UserProfile cascade
- **Always create** preferences/wallet via signals or `get_or_create()` to avoid orphaned profiles

### Performance
- Use `select_related('user_profile')` when querying settings models to avoid N+1 queries
- Admin list queries automatically use `select_related` for foreign keys

### Security
- **Mobile numbers are PII** - restrict admin access, enable audit logging
- **Wallet settings are financial** - changes should require approval workflow in production
- **Never expose** raw account numbers in public APIs (use masked display)

### Monitoring
- Track admin changes to WalletSettings (consider adding Django Admin Log monitoring)
- Alert on bulk changes to NotificationPreferences (potential spam vector)
- Monitor timezone changes (can indicate compromised accounts)

---

## 8. Future Enhancements

### Planned Features
1. **Custom Admin Actions:**
   - Bulk enable/disable specific notification types
   - Export wallet settings for financial audit
   - Mass update timezone for all BD users

2. **Enhanced Validation:**
   - Real-time mobile number verification via SMS API
   - Duplicate account number detection across users
   - Timezone validation against IANA database

3. **Reporting:**
   - Notification preferences distribution chart
   - Wallet adoption metrics (% users with bKash enabled)
   - Theme preference analytics

4. **Permissions:**
   - Role-based access (support staff can view, only finance can edit wallet)
   - User-specific permission for self-editing via custom admin views

---

## Support

**Questions?** Contact platform team or check source code:
- Admin Configuration: `apps/user_profile/admin.py`
- Models: `apps/user_profile/models/settings.py`
- Migrations: `apps/user_profile/migrations/0030_phase6c_settings_models.py`

**Last Verified:** 2025-12-29  
**Django Version:** 5.x  
**Status:** Production ready, all admin features functional
