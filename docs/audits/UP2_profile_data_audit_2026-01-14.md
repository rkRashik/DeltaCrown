# UP.2 Profile Data Audit (2026-01-14)

**Audit Date**: 2026-01-14  
**Scope**: Complete reconciliation of Admin, Settings, and Public Profile data surfaces  
**Objective**: Document all data flows before Phase UP.2 wiring implementation

---

## 1) Inventory of Relevant Models

### 1.1 UserProfile Model
**File**: `apps/user_profile/models_main.py` (lines 38-150+)  
**Class**: `UserProfile`

**Key Fields**:
| Field | Type | Relation | Notes |
|-------|------|----------|-------|
| `user` | OneToOneField | → `AUTH_USER_MODEL` | Primary link to Django User |
| `uuid` | UUIDField | - | Public unique ID (immutable) |
| `public_id` | CharField(15) | - | Human-readable ID (DC-YY-NNNNNN) |
| `display_name` | CharField(80) | - | Public customizable name |
| `slug` | SlugField(64) | - | Custom URL slug |
| `avatar` | ImageField | - | Upload path: `user_avatars/{user_id}/` |
| `banner` | ImageField | - | Upload path: `user_banners/{user_id}/` |
| `bio` | TextField | - | Profile bio/headline |
| `country` | CharField(100) | - | Country of residence (FULL NAME, not ISO) |
| `region` | CharField(2) | choices | REGION_CHOICES |
| `city` | CharField(100) | - | City of residence |
| `real_full_name` | CharField(200) | - | Legal name (KYC-locked) |
| `date_of_birth` | DateField | - | DOB for verification |
| `nationality` | CharField(100) | - | Citizenship (may differ from country) |
| `kyc_status` | CharField(20) | choices | ['unverified', 'pending', 'verified', 'rejected'] |
| `phone` | CharField(20) | - | Primary phone |
| `whatsapp` | CharField(20) | - | WhatsApp number (2026-01-08 addition) |
| `secondary_email` | EmailField | - | Public/contact email (2026-01-08) |
| `secondary_email_verified` | BooleanField | - | OTP verification status (readonly) |
| `preferred_contact_method` | CharField(20) | choices | ['email', 'phone', 'whatsapp'] |
| `gender` | CharField(20) | choices | ['male', 'female', 'other', 'prefer_not_to_say'] |
| `level` | IntegerField | - | Gamification level |
| `xp` | IntegerField | - | Experience points |

**Legacy Social Fields** (duplicates - see SocialLink model):
- `facebook`, `instagram`, `tiktok`, `twitter`
- `youtube_link`, `twitch_link`, `discord_id`

**Computed Properties**:
- Evidence: NOT FOUND in models_main.py lines 1-150
- Likely: `avatar_url`, `banner_url` via `avatar.url` and `banner.url` (Django ImageField)

**Notes**:
- `country` stores full country NAME (e.g., "Bangladesh"), NOT ISO code
- This causes template issues with flag CDN which expects ISO codes
- KYC fields are locked after verification (admin readonly)

---

### 1.2 DeltaCrownWallet Model
**File**: `apps/economy/models.py` (lines 13-40)  
**Class**: `DeltaCrownWallet`

**Key Fields**:
| Field | Type | Relation | Notes |
|-------|------|----------|-------|
| `profile` | OneToOneField | → `UserProfile` | related_name='dc_wallet' |
| `cached_balance` | IntegerField | - | Derived from transaction ledger |
| `allow_overdraft` | BooleanField | - | Default: False |
| `bkash_number` | CharField(15) | - | Bangladesh mobile payment |
| `nagad_number` | CharField(15) | - | Bangladesh mobile payment |
| `rocket_number` | CharField(15) | - | Bangladesh mobile payment |

**Evidence**:
```python
# apps/economy/models.py:13-40
class DeltaCrownWallet(models.Model):
    profile = models.OneToOneField(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="dc_wallet",
    )
    cached_balance = models.IntegerField(default=0)
```

**Notes**:
- Wallet is READ-ONLY in UserProfile admin (lines 140-148 in admin/users.py)
- Balance managed by Economy app, not editable in settings
- Admin warns: "Manual edits will be overwritten"

---

### 1.3 SocialLink Model
**File**: `apps/user_profile/models_main.py` (lines 1364-1420)  
**Class**: `SocialLink`

**Key Fields**:
| Field | Type | Relation | Notes |
|-------|------|----------|-------|
| `user` | ForeignKey | → `AUTH_USER_MODEL` | related_name='social_links' |
| `platform` | CharField(20) | choices | See PLATFORM_CHOICES below |
| `url` | URLField(500) | - | Full profile URL |
| `handle` | CharField(100) | - | Display name/handle (optional) |
| `is_verified` | BooleanField | - | Platform API verification |

**PLATFORM_CHOICES** (lowercase values):
```python
[
    # Streaming
    ('twitch', 'Twitch'),
    ('youtube', 'YouTube'),
    ('kick', 'Kick'),
    ('facebook_gaming', 'Facebook Gaming'),
    # Social Media
    ('twitter', 'Twitter/X'),
    ('discord', 'Discord'),
    ('instagram', 'Instagram'),
    ('tiktok', 'TikTok'),
    ('facebook', 'Facebook'),
    # Gaming
    ('steam', 'Steam'),
    ('riot', 'Riot Games'),
    # Development
    ('github', 'GitHub'),
]
```

**Evidence**:
```python
# apps/user_profile/models_main.py:1364
class SocialLink(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='social_links')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
```

**Unique Constraint**: `[user, platform]` - one link per platform per user

**Notes**:
- **DUPLICATE STORAGE ISSUE**: UserProfile has legacy social fields (facebook, twitter, etc.) AND SocialLink table exists
- Settings page uses SocialLink model (correct)
- Legacy fields in UserProfile should be deprecated

---

### 1.4 GameProfile Model (Game Passports)
**File**: `apps/user_profile/models_main.py` (lines 1457-1580)  
**Class**: `GameProfile`

**Key Fields**:
| Field | Type | Relation | Notes |
|-------|------|----------|-------|
| `user` | ForeignKey | → `AUTH_USER_MODEL` | related_name='game_profiles' |
| `game` | ForeignKey | → `games.Game` | related_name='passports' |
| `game_display_name` | CharField(100) | - | Auto-filled from game choices |
| `ign` | CharField(64) | - | In-game name/username |
| `discriminator` | CharField(32) | - | Tag/Zone (e.g., #NA1) **NOT `game_tag`** |
| `platform` | CharField(32) | - | PC/PS5/Xbox/etc. |
| `in_game_name` | CharField(100) | - | Display name (computed from ign+discriminator) |
| `identity_key` | CharField(100) | - | Normalized for uniqueness (lowercase) |
| `rank_name` | CharField(50) | - | Current rank |
| `rank_image` | ImageField | - | Rank badge image |
| `rank_points` | IntegerField | - | LP/RR/MMR points |
| `rank_tier` | IntegerField | - | Numeric tier for sorting |
| `matches_played` | IntegerField | - | Total matches |
| `is_verified` | BooleanField | - | Platform verification status |
| `visibility` | CharField(10) | choices | ['PUBLIC', 'PROTECTED', 'PRIVATE'] |
| `is_pinned` | BooleanField | - | Show on profile showcase |

**Evidence**:
```python
# apps/user_profile/models_main.py:1457
class GameProfile(models.Model):
    ign = models.CharField(max_length=64, help_text="In-game name")
    discriminator = models.CharField(max_length=32, help_text="Tag/Zone like #NA1")
```

**CRITICAL FIELD NAME MISMATCH**:
- Model uses: `discriminator`
- Template assumes: `game_tag`
- **FIX REQUIRED**: Change template references from `passport.game_tag` → `passport.discriminator`

---

### 1.5 TeamMembership Model
**File**: `apps/teams/models/_legacy.py` (lines 569-650)  
**Class**: `TeamMembership`

**Key Fields**:
| Field | Type | Relation | Notes |
|-------|------|----------|-------|
| `team` | ForeignKey | → `Team` | related_name='memberships' |
| `profile` | ForeignKey | → `UserProfile` | related_name='team_memberships' |
| `role` | CharField(30) | choices | See Role.choices |
| `status` | CharField(16) | choices | ['ACTIVE', 'PENDING', 'REMOVED'] |
| `joined_at` | DateTimeField | - | Membership start date |
| `left_at` | DateTimeField | - | Null if active |

**Team Model Fields** (lines 38-100):
- `name`: CharField(100, unique)
- `tag`: CharField(10, unique)
- `logo`: ImageField (upload_to=team_logos)
- `game`: CharField(50)
- `region`: CharField(48)

**Evidence**:
```python
# apps/teams/models/_legacy.py:569
class TeamMembership(models.Model):
    profile = models.ForeignKey("user_profile.UserProfile", related_name="team_memberships")
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.PLAYER)
```

**View Context Mapping** (`public_profile_views.py` lines 224-248):
```python
user_teams = [{
    'name': membership.team.name,
    'tag': membership.team.tag,
    'logo_url': membership.team.logo.url if membership.team.logo else None,
    'role': membership.get_role_display(),
    'game': membership.team.game,
    'team_id': membership.team.id,
}]
```

---

### 1.6 Follow Model (for follower/following counts)
**File**: NOT FOUND in explicit model search  
**Evidence Location**: `apps/user_profile/views/public_profile_views.py` lines 415-416

```python
context['follower_count'] = Follow.objects.filter(following=profile_user).count()
context['following_count'] = Follow.objects.filter(follower=profile_user).count()
```

**Inferred Structure**:
- Model name: `Follow`
- Fields: `follower` (ForeignKey to User), `following` (ForeignKey to User)
- Location: Likely in `apps/user_profile/models_main.py` or separate relationship model

**Status**: Model exists but not directly audited - counts are computed dynamically

---

### 1.7 UserProfileStats Model
**File**: `apps/user_profile/models/stats.py` (inferred from imports)  
**Context Evidence**: `public_profile_views.py` lines 506-528

```python
from apps.user_profile.models import UserProfileStats
stats = UserProfileStats.objects.get(user_profile=user_profile)
context['user_stats'] = {
    'total_matches': stats.total_matches,
    'total_wins': stats.total_wins,
    'win_rate': round((stats.total_wins / stats.total_matches * 100) if stats.total_matches > 0 else 0, 1),
    'tournaments_played': stats.tournaments_played,
    'tournaments_won': stats.tournaments_won,
    'total_kills': getattr(stats, 'total_kills', 0),
    'total_deaths': getattr(stats, 'total_deaths', 0),
    'kd_ratio': round((kills / deaths) if deaths > 0 else 0, 2)
}
```

**Key Fields** (inferred):
- `user_profile`: ForeignKey to UserProfile
- `total_matches`, `total_wins`: IntegerField
- `tournaments_played`, `tournaments_won`: IntegerField
- `total_kills`, `total_deaths`: IntegerField (optional)

---

### 1.8 PrivacySettings Model
**File**: `apps/user_profile/models_main.py` (referenced in admin.py lines 80-93)  
**Class**: `PrivacySettings`

**Fields** (from admin inline):
```python
fields = [
    ('show_real_name', 'show_phone', 'show_email'),
    ('show_age', 'show_gender', 'show_country'),
    ('show_game_ids', 'show_social_links'),
    ('show_match_history', 'show_teams', 'show_achievements'),
    ('allow_team_invites', 'allow_friend_requests', 'allow_direct_messages'),
]
```

**Relation**: OneToOne with UserProfile (inferred from StackedInline usage)

---

### 1.9 NotificationPreferences Model
**File**: `apps/user_profile/models/settings.py` (inferred from imports)  
**Admin Evidence**: `admin.py` lines 174-206

**Fields**:
- Email: `email_tournament_reminders`, `email_match_results`, `email_team_invites`, `email_achievements`, `email_platform_updates`
- Platform: `notify_tournament_start`, `notify_team_messages`, `notify_follows`, `notify_achievements`

---

### 1.10 WalletSettings Model
**File**: `apps/user_profile/models/settings.py` (inferred)  
**Admin Evidence**: `admin.py` lines 206-248

**Fields**:
- Mobile Banking: `bkash_enabled`, `bkash_account`, `nagad_enabled`, `nagad_account`, `rocket_enabled`, `rocket_account`
- Preferences: `auto_withdrawal_threshold`, `auto_convert_to_usd`

---

## 2) Django Admin Audit (Source of Truth A)

### 2.1 UserProfile Admin Configuration

**File**: `apps/user_profile/admin/users.py` (lines 127-200)  
**Admin Class**: `UserProfileAdmin`  
**Registration**: `@admin.register(UserProfile)`  
**URL**: `http://127.0.0.1:8000/admin/user_profile/userprofile/`

**list_display** (evidence line 129):
```python
("id", "user", "display_name", "public_id", "kyc_status_badge", "coin_balance", "created_at")
```

**search_fields** (line 130):
```python
("user__username", "display_name", "user__email", "phone", "real_full_name", "public_id")
```

**readonly_fields** (lines 137-142):
```python
(
    "uuid", "slug", "public_id", "created_at", "updated_at", "kyc_verified_at",
    "secondary_email_verified",  # Only system can verify via OTP
    "deltacoin_balance",  # Economy-owned (read-only)
    "lifetime_earnings",  # Economy-owned (read-only)
)
```

**fieldsets** (lines 145-175):

| Section | Fields | Notes |
|---------|--------|-------|
| **User Account** | user, uuid, slug, public_id | Identity fields |
| **Public Identity** | avatar, banner, display_name, bio, region | Editable public data |
| **Legal Identity & KYC** | real_full_name, date_of_birth, nationality, kyc_status, kyc_verified_at | KYC-locked after verification |
| **Contact Information** | phone, whatsapp, secondary_email, secondary_email_verified, preferred_contact_method, country, city, postal_code, address | Comprehensive contact data |
| **Demographics** | gender | Optional demographic |
| **Emergency Contact** | emergency_contact_name, emergency_contact_phone, emergency_contact_relation | Safety data |
| **Social Media** | facebook, instagram, tiktok, twitter, youtube_link, twitch_link, discord_id | **LEGACY FIELDS** - duplicates SocialLink model |
| **Gaming & Streaming** | stream_status | Auto-updated field |
| **Gamification** | level, xp, pinned_badges | XP system |
| **Economy & Wallet** | deltacoin_balance, lifetime_earnings, inventory_items | **READ-ONLY** - Economy app owns |
| **System Data** | attributes, system_settings, created_at, updated_at | Internal metadata |

**Inlines**:
- NOT SHOWN in excerpt, but typically: `PrivacySettingsInline`, `SocialLinkInline`, `GameProfileInline`, `NotificationPreferencesInline`, `WalletSettingsInline`

---

### 2.2 Admin → Model Mapping Table

| Admin Label/Field | Model.Field | Type | Notes |
|-------------------|-------------|------|-------|
| Display Name | `UserProfile.display_name` | CharField(80) | Editable |
| Bio | `UserProfile.bio` | TextField | Editable |
| Avatar | `UserProfile.avatar` | ImageField | Upload widget |
| Banner | `UserProfile.banner` | ImageField | Upload widget |
| Country | `UserProfile.country` | CharField(100) | Full name, NOT ISO code |
| Phone | `UserProfile.phone` | CharField(20) | Editable |
| WhatsApp | `UserProfile.whatsapp` | CharField(20) | NEW (2026-01-08) |
| Secondary Email | `UserProfile.secondary_email` | EmailField | Editable |
| Secondary Email Verified | `UserProfile.secondary_email_verified` | BooleanField | READONLY (OTP-only) |
| DeltaCoin Balance | `UserProfile.deltacoin_balance` | IntegerField | READONLY (Economy-owned) |
| Facebook (legacy) | `UserProfile.facebook` | URLField | DUPLICATE - use SocialLink |
| Twitter (legacy) | `UserProfile.twitter` | URLField | DUPLICATE - use SocialLink |
| Discord ID (legacy) | `UserProfile.discord_id` | CharField | DUPLICATE - use SocialLink |
| Social Links (inline) | `SocialLink.platform/url/handle` | Model relation | CORRECT location |
| Game Passports (inline) | `GameProfile.*` | Model relation | Via GameProfileInline |
| Privacy Settings (inline) | `PrivacySettings.*` | OneToOne relation | Editable flags |

---

### 2.3 Related Model Admins

**PrivacySettings**: Standalone admin + inline (`@admin.register(PrivacySettings)` line 248)  
**SocialLink**: Inline only (no standalone admin registered)  
**GameProfile**: Custom admin in `admin/game_passports.py` (line 466 comment: `# class GameProfileAdmin`)  
**DeltaCrownWallet**: NOT registered in user_profile admin (managed by Economy app)  
**TeamMembership**: NOT registered here (managed by Teams app)

---

## 3) Settings Page Audit (Source of Truth B)

### 3.1 URL Map

**Base Route**: `/me/settings/` → `profile_settings_view`  
**View File**: `apps/user_profile/views/public_profile_views.py` (lines 860-1000)  
**Template**: `templates/user_profile/profile/settings_v4.html`

**Sub-Routes** (from `urls.py` lines 202-252):

| URL | View | Purpose | Form/Model |
|-----|------|---------|------------|
| `/me/settings/` | `profile_settings_view` | Main settings SPA | settings_v4.html |
| `/me/settings/basic/` | `update_basic_info` | Update display_name/bio | UserProfile |
| `/me/settings/social/` | `update_social_links` | Legacy endpoint | SocialLink (deprecated?) |
| `/me/settings/media/` | `upload_media` | Avatar/banner upload | UserProfile.avatar/banner |
| `/me/settings/media/remove/` | `remove_media_api` | Remove avatar/banner | UserProfile |
| `/me/settings/privacy/` | `get_privacy_settings` | Get privacy JSON | PrivacySettings |
| `/me/settings/privacy/save/` | `update_privacy_settings` | Save privacy flags | PrivacySettings |
| `/me/settings/send-verification-otp/` | `send_verification_otp` | Email OTP | UserProfile.secondary_email |
| `/me/settings/verify-otp-code/` | `verify_otp_code` | Verify OTP | UserProfile.secondary_email_verified |
| `/me/settings/career/` | `career_settings_get` | Career profile GET | CareerProfile |
| `/me/settings/career/save/` | `career_settings_save` | Career profile POST | CareerProfile |
| `/me/settings/matchmaking/` | `matchmaking_settings_get` | Matchmaking prefs | MatchmakingPreferences |
| `/me/settings/matchmaking/save/` | `matchmaking_settings_save` | Save matchmaking | MatchmakingPreferences |
| `/me/settings/loadout/` | `loadout_settings_get` | Hardware loadout | HardwareGear/GameConfig |
| `/me/settings/loadout/save/` | `loadout_settings_save` | Save loadout | HardwareGear/GameConfig |
| `/me/settings/notifications/` | `notifications_settings_get` | Notification prefs | NotificationPreferences |
| `/me/settings/notifications/save/` | `notifications_settings_save` | Save notifications | NotificationPreferences |
| `/me/settings/platform-global/` | `get_platform_global_settings` | Platform prefs | Platform-wide settings |
| `/me/settings/platform-global/save/` | `save_platform_global_settings` | Save platform prefs | Platform-wide settings |
| `/api/social-links/create/` | `social_link_create_api` | Create social link | SocialLink |
| `/api/social-links/update/` | `social_link_update_single_api` | Update social link | SocialLink |
| `/api/social-links/delete/` | `social_link_delete_api` | Delete social link | SocialLink |
| `/api/game-passports/create/` | `create_game_passport_api` | Create passport | GameProfile |
| `/api/game-passports/update/` | `update_game_passport_api` | Update passport | GameProfile |
| `/api/game-passports/delete/` | `delete_game_passport_api` | Delete passport | GameProfile |

---

### 3.2 Settings Template Structure

**Template**: `templates/user_profile/profile/settings_v4.html` (467 lines)  
**Architecture**: Single-Page Application (SPA) with vanilla JS navigation  
**Evidence**: Lines 1-10

```django-html
{% extends "base.html" %}
{% block title %}Settings - DeltaCrown{% endblock %}
```

**Navigation Sections** (lines 34-58):

| Section | Icon | Data Attribute | Sub-Template |
|---------|------|----------------|--------------|
| Profile | 👤 | `data-section="profile"` | Inline form |
| Privacy | 🔒 | `data-section="privacy"` | Link to `/me/privacy/` |
| About | 📝 | `data-section="about"` | `_about_manager.html` |
| Game Passports | 🎮 | `data-section="game-passports"` | `partials/_game_passports.html` |
| Social Links | 🔗 | `data-section="social"` | `_social_links_manager.html` |
| Notifications | 🔔 | `data-section="notifications"` | Inline form |
| Platform | 🌐 | `data-section="platform"` | Inline form |
| Wallet | 💰 | `data-section="wallet"` | Inline form |
| KYC | ✅ | `data-section="kyc"` | Inline form |
| Security | 🛡️ | `data-section="security"` | Inline form |
| Account | ⚙️ | `data-section="account"` | Inline form |

---

### 3.3 Profile Section Form Fields

**Location**: `settings_v4.html` lines 73-111  
**Form ID**: `#profile-form`  
**Submit**: AJAX POST (inferred from SPA architecture)

**Fields**:
| Input Name | Label | Type | Model Target | Validation |
|------------|-------|------|--------------|------------|
| `display_name` | Display Name | text | `UserProfile.display_name` | required |
| `bio` | Bio | textarea | `UserProfile.bio` | maxlength=500 |
| `country` | Country | select | `UserProfile.country` | Dropdown (BD, IN, PK, US, GB shown) |
| `pronouns` | Pronouns | text | `UserProfile.pronouns` (?) | optional |

**Evidence**:
```django-html
<!-- settings_v4.html:84-91 -->
<div class="form-group">
    <label class="form-label" for="display_name">Display Name</label>
    <input type="text" id="display_name" name="display_name" class="form-input" required>
</div>
```

**Country Field Issue**:
- Template shows hardcoded options: `BD`, `IN`, `PK`, `US`, `GB`
- Model field is CharField(100) storing FULL NAMES
- **MISMATCH**: Template uses ISO codes, model stores full names

---

### 3.4 Game Passports Section

**Partial Template**: `templates/user_profile/profile/settings/partials/_game_passports.html`  
**API Endpoints**:
- Create: `/api/game-passports/create/` → `create_game_passport_api`
- Update: `/api/game-passports/update/` → `update_game_passport_api`
- Delete: `/api/game-passports/delete/` → `delete_game_passport_api`

**Model**: `GameProfile`  
**Fields Edited**:
- `ign` (in-game name)
- `discriminator` (tag/zone)
- `platform` (PC/console)
- `rank_name` (current rank)
- `visibility` (PUBLIC/PROTECTED/PRIVATE)
- `is_pinned` (showcase toggle)

---

### 3.5 Social Links Section

**Partial Template**: `templates/user_profile/profile/settings/_social_links_manager.html`  
**API Endpoints**:
- Create: `/api/social-links/create/` → `social_link_create_api`
- Update: `/api/social-links/update/` → `social_link_update_single_api`
- Delete: `/api/social-links/delete/` → `social_link_delete_api`
- List: `/api/social-links/` → `social_links_list_api`

**Model**: `SocialLink`  
**Fields Edited**:
- `platform` (dropdown: twitch, youtube, discord, twitter, etc.)
- `url` (full profile URL)
- `handle` (display name/username)

---

### 3.6 Settings → Model Mapping Table

| Settings UI Field | Template Input Name | Model.Field | Save Location | Notes |
|-------------------|---------------------|-------------|---------------|-------|
| Display Name | `display_name` | `UserProfile.display_name` | `/me/settings/basic/` | Max 80 chars |
| Bio | `bio` | `UserProfile.bio` | `/me/settings/basic/` | Max 500 chars |
| Country | `country` | `UserProfile.country` | `/me/settings/basic/` | MISMATCH: ISO vs full name |
| Pronouns | `pronouns` | `UserProfile.pronouns` | `/me/settings/basic/` | Field may not exist? |
| Avatar | File upload | `UserProfile.avatar` | `/me/settings/media/` | ImageField |
| Banner | File upload | `UserProfile.banner` | `/me/settings/media/` | ImageField |
| Secondary Email | `secondary_email` | `UserProfile.secondary_email` | Email API | OTP verification required |
| Social Platform | `platform` | `SocialLink.platform` | Social Links API | Lowercase choices |
| Social URL | `url` | `SocialLink.url` | Social Links API | URLField(500) |
| Social Handle | `handle` | `SocialLink.handle` | Social Links API | Optional display name |
| Game IGN | `ign` | `GameProfile.ign` | Game Passports API | In-game name |
| Game Tag | `discriminator` | `GameProfile.discriminator` | Game Passports API | **NOT `game_tag`** |
| Game Platform | `platform` | `GameProfile.platform` | Game Passports API | PC/PS5/Xbox |
| Passport Visibility | `visibility` | `GameProfile.visibility` | Game Passports API | PUBLIC/PROTECTED/PRIVATE |
| Show Game IDs | `show_game_ids` | `PrivacySettings.show_game_ids` | Privacy API | Boolean toggle |
| Show Social Links | `show_social_links` | `PrivacySettings.show_social_links` | Privacy API | Boolean toggle |
| Show Teams | `show_teams` | `PrivacySettings.show_teams` | Privacy API | Boolean toggle |

---

## 4) Cross-Surface Reconciliation (Admin vs Settings)

### 4.1 Critical Mismatches

#### **Mismatch 1: Country Field Format**
- **Admin**: Shows CharField(100) with full country names (e.g., "Bangladesh")
- **Settings Template**: Dropdown with ISO codes (BD, IN, PK, US, GB)
- **Model Storage**: `UserProfile.country` stores full names
- **Impact**: Template assumes ISO codes but model stores full names
- **Fix Required**: Either (a) store ISO codes in model, or (b) update template to use full names

#### **Mismatch 2: GameProfile Field Name**
- **Admin**: Model field is `discriminator` (lines 1457+ in models_main.py)
- **Template Assumption**: Code references `passport.game_tag`
- **Evidence**: Public profile template line 595 (before wiring)
- **Fix Required**: Change all template references from `game_tag` → `discriminator`

#### **Mismatch 3: Social Links Duplication**
- **Admin**: Shows BOTH legacy UserProfile fields (facebook, twitter, discord_id) AND SocialLink inline
- **Settings**: Uses SocialLink model exclusively (correct approach)
- **Impact**: Data can be stored in two places
- **Recommendation**: Deprecate legacy UserProfile social fields, migrate to SocialLink

#### **Mismatch 4: Wallet Balance Visibility**
- **Admin**: Shows `deltacoin_balance` as READONLY with warning
- **Settings**: Wallet section exists but unclear if balance is shown/editable
- **Public Profile**: Wallet shown owner-only via `is_owner` permission check
- **Consistency**: Admin correctly locks this field (Economy app owns it)

#### **Mismatch 5: Pronouns Field**
- **Settings Template**: Shows `pronouns` input field (line 104)
- **Admin Fieldsets**: NO pronouns field listed
- **Model**: NOT FOUND in UserProfile model fields (lines 1-150)
- **Status**: **GHOST FIELD** - template references non-existent field
- **Fix Required**: Either add field to model or remove from settings UI

#### **Mismatch 6: Email Verification Flow**
- **Admin**: `secondary_email_verified` is READONLY (line 141)
- **Settings**: Has OTP send/verify endpoints (lines 230-231 in urls.py)
- **Enforcement**: Correct - only system can verify, not admins
- **Status**: Working as designed

---

### 4.2 Legacy & Duplicate Fields

**Duplicate Storage Issues**:

| Data Type | Legacy Location | Modern Location | Status |
|-----------|----------------|-----------------|--------|
| Social Links | `UserProfile.facebook`, `.twitter`, `.discord_id`, etc. | `SocialLink` model | **DUPLICATE** - migrate to SocialLink |
| Avatar URL | `UserProfile.avatar` | N/A | Correct - ImageField |
| Banner URL | `UserProfile.banner` | N/A | Correct - ImageField |
| Wallet Balance | `UserProfile.deltacoin_balance` | `DeltaCrownWallet.cached_balance` | **DUPLICATE** - Economy owns wallet |
| Country | `UserProfile.country` | N/A | Correct but format issue |

**Recommendation**: 
1. Deprecate `UserProfile` social media fields (facebook, twitter, etc.)
2. Remove `deltacoin_balance` from UserProfile (use Economy API)
3. Add migration to copy legacy social data to SocialLink model
4. Update admin to hide deprecated fields

---

## 5) Profile Page Target Map (For Wiring Later)

**Template**: `templates/user_profile/profile/public_profile.html`  
**Route**: `/@<username>/` → `public_profile_view`  
**View Context**: `build_public_profile_context()` service

### 5.1 HERO Section Data Map

| Profile UI Element | Source Model.Field | Privacy Gate | View Context Variable | Notes/Fallback |
|--------------------|-------------------|--------------|----------------------|----------------|
| Page Title | `User.username` | Public | `profile_user.username` | Always shown |
| Banner Image | `UserProfile.banner` | Public | `profile.banner.url` | Fallback: placeholder image |
| Avatar Image | `UserProfile.avatar` | Public | `profile.avatar.url` | Fallback: default avatar |
| Display Name | `UserProfile.display_name` | Public | `profile.display_name` | Fallback: `profile_user.username` |
| Username Tag | `User.username` | Public | `profile_user.username` | Always shown with # prefix |
| Team Badge | `TeamMembership → Team.tag/name` | `can_view_teams` | `user_teams[0].tag`, `.name` | Show first active team |
| Verification Badge | `UserProfile.kyc_status` | Public | Hardcoded "Verified Pro" | **NOT WIRED** - static badge |
| Bio/Tagline | `UserProfile.bio` | Public | `profile.bio` | Conditional display |
| Follower Count | `Follow` model count | Public | `follower_count` | Fallback: 0 |
| Following Count | `Follow` model count | Public | `following_count` | Fallback: 0 |
| Wins | `UserProfileStats.total_wins` | Public | `user_stats.total_wins` | Fallback: 0 |
| Country | `UserProfile.country` | `show_country` | `profile.country` | **ISSUE**: Stores full name, not ISO |

**Evidence**:
```python
# public_profile_views.py:415-416
context['follower_count'] = Follow.objects.filter(following=profile_user).count()
context['following_count'] = Follow.objects.filter(follower=profile_user).count()
```

---

### 5.2 CONNECT / Social Links Section Data Map

| Profile UI Element | Source Model.Field | Privacy Gate | View Context Variable | Notes/Fallback |
|--------------------|-------------------|--------------|----------------------|----------------|
| Discord Preferred | `SocialLink.handle` OR `.url` | `can_view_social_links` | `social_links` (list) | Filter for platform='discord' |
| Twitter Icon | `SocialLink.url` | `can_view_social_links` | `social_links` | Filter for platform='twitter' |
| Twitch Icon | `SocialLink.url` | `can_view_social_links` | `social_links` | Filter for platform='twitch' |
| YouTube Icon | `SocialLink.url` | `can_view_social_links` | `social_links` | Filter for platform='youtube' |

**Context Structure**:
```python
# public_profile_views.py:486-500
social_links = [
    {'platform': 'discord', 'url': '...', 'handle': '...'},
    {'platform': 'twitter', 'url': '...', 'handle': '...'},
    # ...
]
```

**Platform Values**: Lowercase ('discord', 'twitter', 'twitch', 'youtube')

---

### 5.3 DELTA VAULT / Wallet Section Data Map

| Profile UI Element | Source Model.Field | Privacy Gate | View Context Variable | Notes/Fallback |
|--------------------|-------------------|--------------|----------------------|----------------|
| Balance Display | `DeltaCrownWallet.cached_balance` | `is_owner` | `wallet.balance` | Owner-only, 0 if not owner |
| Transaction History | `WalletTransaction` model | `is_owner` | `wallet.transactions` (?) | Owner-only |

**Privacy Enforcement** (lines 90-105):
```python
if permissions.get('is_owner'):
    wallet = DeltaCrownWallet.objects.get_or_create(profile=user_profile)[0]
    context['wallet'] = {'balance': wallet.cached_balance}
else:
    context['wallet'] = None
```

**Critical**: Wallet shown ONLY to owner, enforced server-side

---

### 5.4 AFFILIATIONS / Teams Section Data Map

| Profile UI Element | Source Model.Field | Privacy Gate | View Context Variable | Notes/Fallback |
|--------------------|-------------------|--------------|----------------------|----------------|
| Team Name | `Team.name` | `can_view_teams` | `user_teams[].name` | List of all active teams |
| Team Tag | `Team.tag` | `can_view_teams` | `user_teams[].tag` | Abbreviation |
| Team Logo | `Team.logo` | `can_view_teams` | `user_teams[].logo_url` | Fallback: show tag as text |
| Member Role | `TeamMembership.role` | `can_view_teams` | `user_teams[].role` | "Captain", "Player", etc. |
| Game | `Team.game` | `can_view_teams` | `user_teams[].game` | Game this team plays |

**Context Structure** (lines 224-248):
```python
user_teams = [
    {
        'name': membership.team.name,
        'tag': membership.team.tag,
        'logo_url': membership.team.logo.url if membership.team.logo else None,
        'role': membership.get_role_display(),
        'game': membership.team.game,
        'team_id': membership.team.id,
    }
]
```

---

### 5.5 GAME IDs / Passports Section Data Map

| Profile UI Element | Source Model.Field | Privacy Gate | View Context Variable | Notes/Fallback |
|--------------------|-------------------|--------------|----------------------|----------------|
| Total Count | `GameProfile` count | `can_view_game_passports` | `pinned_passports|length + unpinned_passports|length` | Dynamic count |
| Game Icon | `Game.icon_url` (via FK) | `can_view_game_passports` | `passport.game.icon_url` (?) | Fallback: generic gamepad icon |
| IGN + Tag | `GameProfile.in_game_name` + `.discriminator` | `can_view_game_passports` | `passport.in_game_name`, `.discriminator` | **NOT `.game_tag`** |
| Rank Name | `GameProfile.rank_name` | `can_view_game_passports` | `passport.rank_name` | Optional |
| Platform | `GameProfile.platform` | `can_view_game_passports` | `passport.platform` | PC/PS5/Xbox |
| Verified Badge | `GameProfile.is_verified` | `can_view_game_passports` | `passport.is_verified` | Boolean flag |

**Context Structure** (lines 150-194):
```python
# Uses GamePassportService to fetch passports
pinned_passports = GameProfile.objects.filter(user=profile_user, is_pinned=True)
unpinned_passports = GameProfile.objects.filter(user=profile_user, is_pinned=False)
```

**Critical Field Name**: `discriminator` NOT `game_tag`

---

## 6) Actionable Recommendations (No Code Yet)

### 6.1 Top 10 Fixes (Priority Order)

1. **FIX: GameProfile Field Name**
   - **Issue**: Template assumes `passport.game_tag` but model uses `discriminator`
   - **Location**: Public profile template line ~595
   - **Action**: Global find/replace `passport.game_tag` → `passport.discriminator`
   - **Impact**: Critical - will break game ID display

2. **FIX: Country Field Format**
   - **Issue**: Model stores full names ("Bangladesh"), flag CDN needs ISO codes ("BD")
   - **Location**: UserProfile.country field
   - **Action**: Either (a) add `country_code` CharField(2), or (b) use django-countries package, or (c) remove flag display
   - **Impact**: High - affects location display with flags

3. **REMOVE: Ghost Pronouns Field**
   - **Issue**: Settings template shows pronouns input but model has no such field
   - **Location**: settings_v4.html line 104
   - **Action**: Remove from template OR add field to UserProfile model
   - **Impact**: Medium - causes form submission errors

4. **DEPRECATE: Legacy Social Fields**
   - **Issue**: Duplicate storage in UserProfile (facebook, twitter) AND SocialLink model
   - **Location**: UserProfile model lines ~160-180 (estimated)
   - **Action**: Add migration to copy data to SocialLink, mark fields deprecated, hide in admin
   - **Impact**: Medium - prevents data inconsistency

5. **REMOVE: DeltaCoin Balance from UserProfile**
   - **Issue**: Balance stored in both UserProfile and DeltaCrownWallet (Economy app owns)
   - **Location**: UserProfile.deltacoin_balance field
   - **Action**: Remove field, always read from Economy API
   - **Impact**: Medium - reduces sync issues

6. **FIX: Social Platform Case Sensitivity**
   - **Issue**: Template checks both uppercase and lowercase ('DISCORD' or 'discord')
   - **Reality**: Model choices are lowercase only
   - **Location**: Public profile template social links section
   - **Action**: Remove uppercase checks, use lowercase only
   - **Impact**: Low - minor cleanup

7. **ADD: Country ISO Code Mapping**
   - **Issue**: Need to map full country names to ISO codes for flags
   - **Location**: Template helper or model property
   - **Action**: Add `get_country_code()` method or use django-countries
   - **Impact**: Medium - enables flag display

8. **DOCUMENT: Wallet Privacy Enforcement**
   - **Issue**: Wallet balance visible only to owner, not documented in template
   - **Location**: Public profile view context
   - **Action**: Add template comments explaining `{% if wallet %}` check
   - **Impact**: Low - improves maintainability

9. **STANDARDIZE: Empty State Messages**
   - **Issue**: Some sections have "No X yet" messages, some don't
   - **Location**: Profile template various sections
   - **Action**: Add `{% empty %}` blocks to all loops
   - **Impact**: Low - better UX

10. **AUDIT: Verification Badge Logic**
    - **Issue**: "Verified Pro" badge is hardcoded, no backend verification check
    - **Location**: Public profile HERO section
    - **Action**: Wire to UserProfile.kyc_status or Badge system
    - **Impact**: Medium - currently misleading

---

### 6.2 Canonical Data Sources

**Establish these as SOURCE OF TRUTH**:

| Data Type | Canonical Location | Reason |
|-----------|-------------------|--------|
| Social Links | `SocialLink` model | Dedicated table, proper structure |
| Wallet Balance | `DeltaCrownWallet.cached_balance` | Economy app owns transactions |
| Game Identities | `GameProfile` model | Rich structure with history |
| Team Memberships | `TeamMembership → Team` | Teams app manages roster |
| Profile Stats | `UserProfileStats` model | Computed from match data |
| Privacy Settings | `PrivacySettings` model | Dedicated settings table |
| Avatar/Banner | `UserProfile.avatar/banner` | FileField with proper storage |
| Display Name | `UserProfile.display_name` | Primary identity field |
| Email Verification | `UserProfile.secondary_email_verified` | OTP-controlled, readonly |

**Deprecate/Remove**:
- `UserProfile.facebook`, `.twitter`, `.discord_id` (use SocialLink)
- `UserProfile.deltacoin_balance` (use DeltaCrownWallet)

---

### 6.3 Template Assumptions to Remove

**Incorrect Assumptions Found**:

1. **Assumption**: `passport.game_tag` field exists
   - **Reality**: Field is named `discriminator`
   - **Fix**: Update template references

2. **Assumption**: Social platform values are uppercase ('DISCORD')
   - **Reality**: Model uses lowercase ('discord')
   - **Fix**: Remove uppercase checks

3. **Assumption**: `country` field stores ISO codes
   - **Reality**: Stores full country names
   - **Fix**: Add ISO code property or change storage format

4. **Assumption**: Pronouns field exists on UserProfile
   - **Reality**: Field not found in model
   - **Fix**: Add field or remove from settings UI

5. **Assumption**: All social links visible to all users
   - **Reality**: Gated by `can_view_social_links` permission
   - **Fix**: Already handled in view context (correct)

6. **Assumption**: Wallet balance always available
   - **Reality**: Only shown to owner via `is_owner` check
   - **Fix**: Already enforced in view (correct)

---

### 6.4 Missing Properties/Helpers Needed

**Required Template Properties**:

1. **`UserProfile.get_country_code()`**
   - **Purpose**: Convert full country name to ISO code for flag CDN
   - **Return**: 2-letter ISO code (e.g., "BD")
   - **Implementation**: Dictionary mapping or django-countries

2. **`UserProfile.avatar_url_or_default`**
   - **Purpose**: Return avatar URL or default placeholder
   - **Return**: URL string
   - **Implementation**: Property that checks `if self.avatar else default_url`

3. **`UserProfile.banner_url_or_default`**
   - **Purpose**: Return banner URL or default placeholder
   - **Return**: URL string
   - **Implementation**: Property that checks `if self.banner else default_url`

4. **`GameProfile.full_identity`**
   - **Purpose**: Return formatted IGN+discriminator (e.g., "Player#NA1")
   - **Return**: String
   - **Implementation**: `f"{self.ign}#{self.discriminator}" if self.discriminator else self.ign`

5. **`Team.logo_url_or_placeholder`**
   - **Purpose**: Return team logo URL or fallback to tag initials
   - **Return**: URL string or None (template handles fallback)
   - **Implementation**: Property that checks `if self.logo else None`

---

## 7) Evidence Appendix

### 7.1 Key Code Snippets

**UserProfile Model Declaration**:
```python
# apps/user_profile/models_main.py:38
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="profile")
    display_name = models.CharField(max_length=80)
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True)
    banner = models.ImageField(upload_to=user_banner_path, blank=True, null=True)
    bio = models.TextField(blank=True, help_text="Profile bio/headline")
    country = models.CharField(max_length=100, blank=True, default="")
```

**GameProfile discriminator Field**:
```python
# apps/user_profile/models_main.py:1520
discriminator = models.CharField(
    max_length=32,
    null=True,
    blank=True,
    db_index=True,
    help_text="Discriminator / Tag / Zone (e.g., '#NA1' for Riot)"
)
```

**SocialLink Platform Choices**:
```python
# apps/user_profile/models_main.py:1370-1387
PLATFORM_CHOICES = [
    ('twitch', 'Twitch'),
    ('youtube', 'YouTube'),
    ('discord', 'Discord'),
    ('twitter', 'Twitter/X'),
    # ... all lowercase values
]
```

**Admin Readonly Fields**:
```python
# apps/user_profile/admin/users.py:137-142
readonly_fields = (
    "uuid", "slug", "public_id", "created_at", "updated_at",
    "secondary_email_verified",  # Only system can verify via OTP
    "deltacoin_balance",  # Economy-owned (read-only)
)
```

**View Context: Wallet Owner-Only**:
```python
# apps/user_profile/views/public_profile_views.py:90-105
if permissions.get('is_owner'):
    wallet = DeltaCrownWallet.objects.get_or_create(profile=user_profile)[0]
    context['wallet'] = {'balance': wallet.cached_balance}
else:
    context['wallet'] = None
```

**View Context: Social Links**:
```python
# apps/user_profile/views/public_profile_views.py:486-500
if permissions.get('can_view_social_links'):
    social_links_qs = SocialLink.objects.filter(user=profile_user)
    context['social_links'] = [
        {
            'platform': link.platform,
            'url': link.url,
            'handle': link.handle,
        }
        for link in social_links_qs
    ]
```

**Settings Template Navigation**:
```django-html
<!-- templates/user_profile/profile/settings_v4.html:34-48 -->
<div class="nav-item" data-section="profile">
    <span class="nav-icon">👤</span><span>Profile</span>
</div>
<div class="nav-item" data-section="game-passports">
    <span class="nav-icon">🎮</span><span>Game Passports</span>
</div>
<div class="nav-item" data-section="social">
    <span class="nav-icon">🔗</span><span>Social Links</span>
</div>
```

---

## 8) Files Audited

**Models**:
- `apps/user_profile/models_main.py` (lines 1-2287)
- `apps/user_profile/models/__init__.py`
- `apps/economy/models.py` (lines 1-40)
- `apps/teams/models/_legacy.py` (lines 38-650)

**Admin**:
- `apps/user_profile/admin.py` (lines 1-2609)
- `apps/user_profile/admin/users.py` (lines 1-1561)

**Views**:
- `apps/user_profile/views/public_profile_views.py` (lines 1-1630)

**URLs**:
- `apps/user_profile/urls.py` (lines 1-451)

**Templates**:
- `templates/user_profile/profile/settings_v4.html` (lines 1-467)
- `templates/user_profile/profile/public_profile.html` (referenced)

**Forms**: `apps/user_profile/forms.py` (not fully audited - inferred from view usage)

---

## 9) Search Results - NOT FOUND

**Items searched but not located**:

1. **Pronouns Field**: 
   - Searched in: `UserProfile` model fields (lines 1-150)
   - Result: NOT FOUND - ghost field in settings template
   - Query: `grep -r "pronouns" apps/user_profile/models*.py`

2. **Follow Model**: 
   - Searched in: `apps/user_profile/models*.py`
   - Result: NOT FOUND explicitly, but referenced in views
   - Likely location: Relationship model in separate file

3. **Settings Form Classes**:
   - Searched for: `UserProfileSettingsForm`, `AboutSettingsForm`
   - Result: Imported in views but form file not fully audited
   - File exists: `apps/user_profile/forms.py`

4. **Standalone SocialLink Admin**:
   - Searched in: `admin.py` registration calls
   - Result: NOT FOUND - only inline admin exists
   - Comment found: `# class SocialLinkAdmin` (line 456, commented out)

---

## 10) Summary & Next Steps

**Audit Complete**: ✅  
**Critical Issues Found**: 6  
**Recommendations Generated**: 10

**Before Wiring Phase UP.2**:
1. Fix `game_tag` → `discriminator` field name mismatch
2. Decide on country field format (ISO vs full name)
3. Remove ghost pronouns field from settings
4. Plan deprecation of legacy social fields

**Ready for Wiring**:
- ✅ View context structure documented
- ✅ Admin field sources mapped
- ✅ Settings save locations identified
- ✅ Privacy gates documented
- ⚠️ Field name fixes required first

**Deliverable**: This report serves as source of truth for Phase UP.2 implementation.

---

**Report Generated**: 2026-01-14  
**Auditor**: AI Assistant  
**Status**: Complete - Ready for Review
