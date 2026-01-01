# Settings Page UI/UX Design Specification
**Platform**: DeltaCrown Esports  
**Date**: January 1, 2026  
**Document Version**: 1.0  
**Purpose**: Complete audit and content specification for unified settings page design

---

## 📋 Executive Summary

This document provides a comprehensive analysis of all user profile settings, platform preferences, and configuration options available in DeltaCrown. It serves as the **single source of truth** for UI/UX designers creating the unified settings page.

### Scope
- **Personal Settings**: Identity, contact info, demographics
- **Privacy & Security**: Visibility controls, KYC verification
- **Esports Features**: Game passports, loadout, career management
- **Platform Preferences**: Notifications, language, theme
- **Economy**: Wallet, earnings, withdrawal methods
- **Social Features**: Following, social links, profile showcase

---

## 🎯 Design Goals

1. **Single Source of Truth**: All user configurations in one place
2. **Progressive Disclosure**: Complex settings hidden behind tabs/accordions
3. **Clear Hierarchy**: Organize by user intent (Account → Identity → Privacy → Esports → Economy)
4. **Mobile-First**: Responsive design for mobile gamers
5. **Instant Feedback**: Real-time validation and success/error messages
6. **Accessibility**: WCAG 2.1 AA compliance

---

## 📊 Database Schema Overview

### Core Models
```
UserProfile (apps/user_profile/models_main.py)
├── PrivacySettings (1:1)
├── NotificationPreferences (1:1)
├── WalletSettings (1:1)
├── DeltaCrownWallet (1:1) [apps/economy/models.py]
├── GameProfile (1:N) - Game Passports
├── SocialLink (1:N)
├── HardwareGear (1:N) [apps/user_profile/models/loadout.py]
├── GameConfig (1:N) [apps/user_profile/models/loadout.py]
├── Bounty (1:N) [apps/user_profile/models/bounties.py]
└── Follow (M:N via follower/following)
```

---

## 🗂️ Settings Menu Structure

```
┌─ ACCOUNT
│  ├─ Profile Information
│  ├─ Contact Details
│  └─ Demographics
│
├─ IDENTITY  
│  ├─ Display & Avatar
│  ├─ Legal Information (KYC)
│  └─ Location
│
├─ PRIVACY & VISIBILITY
│  ├─ Profile Visibility Preset
│  ├─ What Others Can See
│  ├─ Follower/Following Privacy
│  └─ Interaction Permissions
│
├─ SECURITY & KYC
│  ├─ Password & Authentication
│  ├─ KYC Verification Status
│  └─ Withdrawal PIN
│
├─ NOTIFICATIONS
│  ├─ Email Notifications
│  ├─ Platform Notifications
│  └─ Notification Digest
│
├─ ESPORTS
│  ├─ Career & LFT
│  ├─ Game Passports
│  ├─ Matchmaking & Bounties
│  └─ Loadout (Hardware & Configs)
│
├─ ASSETS & LIVE
│  ├─ Inventory & Cosmetics
│  ├─ Stream Configuration
│  └─ Wallet & Earnings
│
├─ PLATFORM PREFERENCES
│  ├─ Language & Region
│  ├─ Time Zone & Format
│  └─ Theme
│
└─ DANGER ZONE
   ├─ Deactivate Account
   └─ Delete Account
```

---

## 📖 Detailed Section Specifications

---

### 1. ACCOUNT

#### 1.1 Profile Information

**Purpose**: Core identity displayed publicly on profile

**Fields** (from `UserProfile` model):

| Field | Type | Required | Max Length | Help Text | Current Value Access |
|-------|------|----------|------------|-----------|---------------------|
| `display_name` | Text | ✅ | 80 chars | Public display name | `{{ profile.display_name }}` |
| `slug` | Slug | ❌ | 64 chars | Custom URL (deltacrown.com/u/legend) | `{{ profile.slug }}` |
| `bio` | Textarea | ❌ | Unlimited | Profile bio/headline | `{{ profile.bio }}` |
| `pronouns` | Text | ❌ | 50 chars | e.g., he/him, she/her, they/them | `{{ profile.pronouns }}` |

**Validation Rules**:
- `display_name`: Required, 3-80 characters, alphanumeric + spaces/underscores
- `slug`: Optional, lowercase letters/numbers/hyphens only, unique globally
- `bio`: Optional, max 500 characters recommended for UX

**UI Components**:
- Text input for display_name
- Text input for slug with real-time availability check
- Rich textarea for bio with character counter
- Dropdown for pronouns with custom option

---

#### 1.2 Contact Details

**Purpose**: Communication channels (private unless user chooses to show publicly)

**Fields** (from `UserProfile` model):

| Field | Type | Required | Max Length | Help Text | Privacy Control |
|-------|------|----------|------------|-----------|----------------|
| Email | Email | ✅ | - | Managed by auth system | `PrivacySettings.show_email` |
| `phone` | Text | ❌ | 20 chars | +8801XXXXXXXXX format | `PrivacySettings.show_phone` |
| `emergency_contact_name` | Text | ❌ | 200 chars | For LAN events | Never shown publicly |
| `emergency_contact_phone` | Text | ❌ | 20 chars | For LAN events | Never shown publicly |
| `emergency_contact_relation` | Text | ❌ | 50 chars | e.g., Parent, Spouse | Never shown publicly |

**Validation Rules**:
- Email: Django auth system validation
- Phone: International format (+country_code + number)
- Emergency contacts: Optional but recommended for LAN participants

**UI Components**:
- Email display (read-only, link to change via auth system)
- Phone input with country code dropdown
- Emergency contact section (collapsible accordion)

---

#### 1.3 Demographics

**Purpose**: Optional demographic data for analytics and gender-specific events

**Fields** (from `UserProfile` model):

| Field | Type | Required | Choices | Privacy Control |
|-------|------|----------|---------|----------------|
| `gender` | Select | ❌ | Male, Female, Other, Prefer not to say | `PrivacySettings.show_gender` |
| `date_of_birth` | Date | ❌ | - | `PrivacySettings.show_age` (shows age, not DOB) |

**Validation Rules**:
- DOB: Must be 13+ years old (COPPA compliance)
- Gender: Optional, no validation needed

**UI Components**:
- Gender dropdown
- Date picker for DOB with age calculator preview
- Privacy toggle for each field inline

---

### 2. IDENTITY

#### 2.1 Display & Avatar

**Purpose**: Visual identity on platform

**Fields** (from `UserProfile` model):

| Field | Type | Max Size | Format | Help Text |
|-------|------|----------|--------|-----------|
| `avatar` | ImageField | 5 MB | JPEG/PNG/WebP | Profile picture (min 100x100px) |
| `banner` | ImageField | 10 MB | JPEG/PNG/WebP | Profile cover image (min 1200x300px, 4:1 ratio) |

**Upload API**:
- Endpoint: `POST /user-profile/me/settings/media/`
- Parameters: `media_type` ('avatar' or 'banner'), `file`
- Response: `{success: true, url: '/media/...', preview_url: '/media/...'}`

**UI Components**:
- Avatar upload with circular crop preview
- Banner upload with aspect ratio guide (4:1)
- Drag-and-drop or click to upload
- Real-time preview before save
- Delete button for each media type

---

#### 2.2 Legal Information (KYC)

**Purpose**: Identity verification for prize payments and compliance

**Fields** (from `UserProfile` model):

| Field | Type | Required for KYC | Max Length | Locked After KYC |
|-------|------|------------------|------------|------------------|
| `real_full_name` | Text | ✅ | 200 chars | ✅ |
| `date_of_birth` | Date | ✅ | - | ✅ |
| `nationality` | Text | ✅ | 100 chars | ✅ |
| `kyc_status` | Status | Auto | - | Read-only |
| `kyc_verified_at` | DateTime | Auto | - | Read-only |

**KYC Status Values** (from `KYC_STATUS_CHOICES`):
- `unverified`: Not started
- `pending`: Under review
- `verified`: Approved ✅
- `rejected`: Denied (can resubmit)

**Validation Rules**:
- Real name: Must match government ID
- DOB: Must be 18+ for prize withdrawals
- Nationality: Free text, must match ID document

**UI Components**:
- Form fields (disabled if kyc_status = 'verified')
- Status badge (color-coded: green=verified, yellow=pending, red=rejected, gray=unverified)
- Link to KYC upload page (`/user-profile/me/kyc/upload/`)
- Warning banner: "These fields cannot be changed after verification"

**Related Model**: `VerificationRecord` (tracks KYC documents, admin review notes)

---

#### 2.3 Location

**Purpose**: Tournament eligibility, regional matchmaking, prize shipping

**Fields** (from `UserProfile` model):

| Field | Type | Required | Choices/Format | Privacy Control |
|-------|------|----------|----------------|----------------|
| `country` | Text | ❌ | Free text | `PrivacySettings.show_country` |
| `region` | Select | ✅ | BD, SA, AS, EU, NA | Never hidden (used for matchmaking) |
| `city` | Text | ❌ | Free text | Never shown publicly |
| `postal_code` | Text | ❌ | 20 chars | Never shown publicly |
| `address` | Textarea | ❌ | 300 chars | `PrivacySettings.show_address` |

**Region Choices** (from `REGION_CHOICES`):
```python
("BD", "Bangladesh")
("SA", "South Asia")
("AS", "Asia (Other)")
("EU", "Europe")
("NA", "North America")
```

**UI Components**:
- Country autocomplete (with flag icons)
- Region dropdown (required, affects tournament matchmaking)
- City/postal code inputs (for prize shipping)
- Address textarea (shows warning: "Required for physical prize shipping")

---

### 3. PRIVACY & VISIBILITY

**Model**: `PrivacySettings` (1:1 with UserProfile)

#### 3.1 Profile Visibility Preset

**Purpose**: Quick preset toggles for common privacy levels

**Fields** (from `PrivacySettings` model):

| Field | Type | Default | Choices |
|-------|------|---------|---------|
| `visibility_preset` | Select | PUBLIC | PUBLIC, PROTECTED, PRIVATE |

**Preset Behaviors**:

| Setting | PUBLIC | PROTECTED | PRIVATE |
|---------|--------|-----------|---------|
| Real name | ❌ | ❌ | ❌ |
| Contact info | ❌ | ❌ | ❌ |
| Gaming IDs | ✅ | ✅ | ❌ |
| Match history | ✅ | Followers only | ❌ |
| Teams | ✅ | ✅ | ❌ |
| Achievements | ✅ | ✅ | Followers only |
| Activity feed | ✅ | Followers only | ❌ |
| Social links | ✅ | ✅ | ❌ |
| Followers count | ✅ | ✅ | ❌ |
| Followers list | ✅ | Followers only | ❌ |

**UI Components**:
- Large radio buttons with preset names
- Expandable "What does this mean?" for each preset
- **Advanced Settings** button → expands granular toggles

---

#### 3.2 What Others Can See (Granular Toggles)

**Purpose**: Fine-tune what information is visible on public profile

**Personal Information Fields** (from `PrivacySettings` model):

| Toggle Field | Default | Controls Visibility Of |
|-------------|---------|----------------------|
| `show_real_name` | ❌ | Legal full name on profile |
| `show_phone` | ❌ | Phone number on profile |
| `show_email` | ❌ | Email address on profile |
| `show_age` | ✅ | Calculated age (not DOB) |
| `show_gender` | ❌ | Gender identity |
| `show_country` | ✅ | Country of residence |
| `show_address` | ❌ | Full address |

**Gaming & Activity Fields**:

| Toggle Field | Default | Controls Visibility Of |
|-------------|---------|----------------------|
| `show_game_ids` | ✅ | Gaming IDs (Riot ID, Steam, etc.) |
| `show_match_history` | ✅ | Tournament match history |
| `show_teams` | ✅ | Team memberships |
| `show_achievements` | ✅ | Badges and achievements |
| `show_activity_feed` | ✅ | Activity feed on profile |
| `show_tournaments` | ✅ | Tournament participation history |

**Economy & Inventory Fields**:

| Toggle Field | Default | Controls Visibility Of |
|-------------|---------|----------------------|
| `show_inventory_value` | ❌ | Total inventory/cosmetics value |
| `show_level_xp` | ✅ | Player level and XP |

**UI Components**:
- Toggle switches (iOS-style) for each setting
- Section headers (Personal Info, Gaming, Economy)
- Tooltips explaining what each toggle controls
- Preview link: "See what your profile looks like to others"

---

#### 3.3 Follower/Following Privacy

**Purpose**: Instagram-style follower privacy controls (NEW - Added Jan 1, 2026)

**Fields** (from `PrivacySettings` model):

| Toggle Field | Default | Controls |
|-------------|---------|----------|
| `show_followers_count` | ✅ | Display follower count on profile |
| `show_following_count` | ✅ | Display following count on profile |
| `show_followers_list` | ✅ | Allow viewing list of followers |
| `show_following_list` | ✅ | Allow viewing list of following |

**UI Components**:
- 4 separate toggles
- Icon: 🔒 when disabled, 👁️ when enabled
- Help text: "Hiding count/list only affects visitors; you can always see your own"

---

#### 3.4 Interaction Permissions

**Purpose**: Control who can contact/invite you

**Fields** (from `PrivacySettings` model):

| Toggle Field | Default | Controls |
|-------------|---------|----------|
| `allow_team_invites` | ✅ | Receive team invitations |
| `allow_friend_requests` | ✅ | Receive friend requests |
| `allow_direct_messages` | ✅ | Receive DMs from other users |

**UI Components**:
- Toggle switches
- Warning icon for "allow_direct_messages": "Disabling this may affect tournament communication"

---

### 4. SECURITY & KYC

#### 4.1 Password & Authentication

**Purpose**: Account security (delegated to Django auth)

**Actions**:
- Change password → Link to `/account/password_change/`
- Two-factor authentication (future)
- Active sessions (future)

**UI Components**:
- Button: "Change Password" → redirects to auth page
- Security recommendations panel
- Last login timestamp display

---

#### 4.2 KYC Verification Status

**Purpose**: Identity verification dashboard

**Fields** (from `UserProfile` model):

| Field | Display | Description |
|-------|---------|-------------|
| `kyc_status` | Badge | unverified/pending/verified/rejected |
| `kyc_verified_at` | DateTime | "Verified on [date]" |

**UI Components**:
- Large status card with color-coded badge
- **If unverified**: "Verify Identity" button → `/user-profile/me/kyc/upload/`
- **If pending**: "Under review, typically 24-48 hours"
- **If verified**: Checkmark icon + verified date
- **If rejected**: "Resubmit Documents" button + rejection reason

**Related Endpoint**: `/user-profile/me/kyc/status/`

---

#### 4.3 Withdrawal PIN

**Purpose**: Secure withdrawals (part of `DeltaCrownWallet` model)

**Fields** (from `DeltaCrownWallet` model):

| Field | Type | Description |
|-------|------|-------------|
| `pin_hash` | Hashed | 4-digit PIN for withdrawal verification |

**UI Components**:
- **If no PIN set**: "Set Withdrawal PIN" button → opens modal
- **If PIN set**: "Change Withdrawal PIN" button
- PIN input (4 digits, masked)
- Confirmation prompt: "You'll need this PIN to withdraw earnings"

---

### 5. NOTIFICATIONS

**Model**: `NotificationPreferences` (1:1 with UserProfile)  
**Plus**: `NotificationPreference` (from apps/notifications/models.py - per-event channel settings)

#### 5.1 Email Notifications

**Purpose**: Control what emails user receives

**Fields** (from `NotificationPreferences` model):

| Toggle Field | Default | Email Type |
|-------------|---------|------------|
| `email_tournament_reminders` | ✅ | Upcoming tournament reminders |
| `email_match_results` | ✅ | Match result notifications |
| `email_team_invites` | ✅ | Team invitation emails |
| `email_achievements` | ❌ | Achievement unlock emails |
| `email_platform_updates` | ✅ | Platform updates & announcements |

**UI Components**:
- Toggle switches with email icon
- Section header: "Email Notifications"
- Global opt-out: "Unsubscribe from all emails" (sets all to false)

---

#### 5.2 Platform Notifications (In-App)

**Purpose**: Browser/in-app notification popups

**Fields** (from `NotificationPreferences` model):

| Toggle Field | Default | Notification Type |
|-------------|---------|------------------|
| `notify_tournament_start` | ✅ | Tournament start alerts |
| `notify_team_messages` | ✅ | New team messages |
| `notify_follows` | ✅ | New follower alerts |
| `notify_achievements` | ✅ | Achievement unlock popups |

**UI Components**:
- Toggle switches with bell icon
- Section header: "Platform Notifications"
- Test notification button: "Send Test Notification"

---

#### 5.3 Notification Channels (Advanced)

**Purpose**: Per-event channel preferences (from `NotificationPreference` model in apps/notifications/)

**Event Types** (from `Notification.Type` choices):

| Event | Default Channels | Description |
|-------|-----------------|-------------|
| `invite_sent` | in_app, email | Team invite sent |
| `invite_accepted` | in_app, email | Team invite accepted |
| `roster_changed` | in_app | Team roster changed |
| `tournament_registered` | in_app, email | Tournament registration confirmed |
| `match_result` | in_app, email | Match result posted |
| `ranking_changed` | in_app | Team ranking changed |
| `sponsor_approved` | in_app, email | Sponsor approved |
| `payout_received` | in_app, email | Payout received |
| `achievement_earned` | in_app, email | Achievement unlocked |

**Channels Available**:
- `in_app`: Browser notification
- `email`: Email notification
- `discord`: Discord DM (future)

**UI Components**:
- Advanced accordion: "Customize Per-Event Channels"
- For each event: Multi-select checkboxes (in_app, email, discord)
- Global opt-outs:
  - `opt_out_email`: Disable all email notifications
  - `opt_out_in_app`: Disable all in-app notifications
  - `opt_out_discord`: Disable all Discord notifications

---

#### 5.4 Notification Digest

**Purpose**: Daily summary email instead of individual emails

**Fields** (from `NotificationPreference` model):

| Toggle Field | Default | Description |
|-------------|---------|-------------|
| `enable_daily_digest` | ✅ | Receive daily summary |
| `digest_time` | 08:00 | Time to send digest |

**UI Components**:
- Toggle: "Enable Daily Digest"
- Time picker: "Send at" (only shown if digest enabled)
- Preview: "You'll receive 1 email per day summarizing all activity"

---

### 6. ESPORTS

#### 6.1 Career & LFT

**Purpose**: Career settings and looking-for-team status

**Fields** (from `UserProfile` model and `GameProfile` model):

| Field | Type | Model | Description |
|-------|------|-------|-------------|
| `reputation_score` | Integer | UserProfile | Fair play karma (100 = default) |
| `skill_rating` | Integer | UserProfile | Platform ELO/MMR (1000 = default) |
| `is_lft` | Boolean | GameProfile | Looking for team (per-game) |

**UI Components**:
- **Reputation**: Read-only display with badge
- **Skill Rating**: Read-only display with rank icon
- **LFT Status**: Per-game toggles (shown as list of games with switches)
- Help text: "LFT status is per-game. Toggle on to show 'Looking for Team' badge on your profile"

**Related API**: 
- `POST /user-profile/api/passports/toggle-lft/` (toggles is_lft for a game passport)

---

#### 6.2 Game Passports

**Model**: `GameProfile` (1:N with UserProfile)

**Purpose**: Gaming identities across platforms (Riot ID, Steam ID, MLBB ID, etc.)

**Fields** (from `GameProfile` model):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `game` | ForeignKey | ✅ | Game from registry |
| `ign` | Text | ✅ | In-game name (e.g., Player123) |
| `discriminator` | Text | ❌ | Tag/Zone (e.g., #NA1, Zone ID) |
| `platform` | Text | ❌ | Platform (PC, PS5, Xbox) |
| `identity_key` | Text | Auto | Normalized unique key |
| `visibility` | Select | PUBLIC | PUBLIC/PROTECTED/PRIVATE |
| `is_pinned` | Boolean | ❌ | Show on profile (max 6) |
| `is_lft` | Boolean | ❌ | Looking for team |
| `rank_text` | Text | ❌ | Current rank (e.g., "Immortal 3") |
| `rank_icon_url` | URL | ❌ | Rank badge image |

**Validation Rules**:
- IGN: Required, 3-64 characters
- Discriminator: Optional, game-specific format
- Identity Key: Auto-generated from ign+discriminator+platform, enforces uniqueness
- Max 6 pinned passports per user

**UI Components**:
- **List View**: Card grid showing all game passports
- **Add Button**: "+ Add Game Passport" → opens modal
- **Modal Form**:
  - Game dropdown (from `Game` registry)
  - IGN text input
  - Discriminator text input (with game-specific placeholder)
  - Platform dropdown (if applicable to game)
  - Visibility dropdown
  - LFT toggle
  - Rank input (optional)
- **Card Actions**:
  - Edit button → reopens modal with data
  - Delete button → confirmation dialog
  - Pin/Unpin button → shows "Pinned" badge
- **Drag-and-drop reordering** for pinned passports

**Related APIs**:
- `GET /user-profile/api/game-passports/` - List user's passports
- `POST /user-profile/api/game-passports/create/` - Create passport
- `POST /user-profile/api/game-passports/update/` - Update passport
- `POST /user-profile/api/game-passports/delete/` - Delete passport
- `POST /user-profile/api/passports/pin/` - Pin/unpin passport
- `POST /user-profile/api/passports/reorder/` - Change display order

**Identity Change Cooldown**: `identity_change_cooldown` (from `GameProfile` model) - prevents frequent IGN changes

---

#### 6.3 Matchmaking & Bounties

**Model**: `Bounty` (1:N with UserProfile)

**Purpose**: Peer-to-peer challenges with escrow-backed stakes

**Fields** (from `Bounty` model):

| Field | Type | Description |
|-------|------|-------------|
| `title` | Text | Challenge title |
| `description` | Textarea | Challenge requirements |
| `game` | ForeignKey | Game for challenge |
| `stake_amount` | Integer | DeltaCoins locked in escrow |
| `status` | Select | OPEN/ACCEPTED/IN_PROGRESS/PENDING_RESULT/DISPUTED/COMPLETED/EXPIRED/CANCELLED |
| `target_user` | ForeignKey | Private challenge (optional) |

**Bounty Lifecycle**:
1. OPEN → Waiting for acceptor (72h expiry)
2. ACCEPTED → Match pending
3. IN_PROGRESS → Match started
4. PENDING_RESULT → Result submitted (24h dispute window)
5. COMPLETED → Winner paid (terminal)

**UI Components**:
- **List View**: Table showing active bounties (created + accepted)
- **Tabs**:
  - "Created by Me" (show `creator` = user)
  - "Accepted by Me" (show `acceptor` = user)
  - "Targeted at Me" (show `target_user` = user, status = OPEN)
- **Create Bounty Button**: Opens modal
- **Modal Form**:
  - Title input
  - Description textarea
  - Game dropdown
  - Stake amount input (must have balance)
  - Target user autocomplete (optional, for private challenges)
- **Bounty Card Actions**:
  - **If OPEN + creator**: Cancel button
  - **If OPEN + target**: Accept button
  - **If ACCEPTED**: "Start Match" button
  - **If IN_PROGRESS**: Submit result button
  - **If PENDING_RESULT**: Confirm/Dispute buttons

**Related APIs**:
- `POST /user-profile/api/bounties/create/` - Create bounty (locks stake)
- `POST /user-profile/api/bounties/<id>/accept/` - Accept bounty
- `POST /user-profile/api/bounties/<id>/start/` - Start match
- `POST /user-profile/api/bounties/<id>/submit-proof/` - Submit proof
- `POST /user-profile/api/bounties/<id>/confirm-result/` - Confirm result
- `POST /user-profile/api/bounties/<id>/dispute/` - Raise dispute

**Related Models**:
- `BountyAcceptance`: Records acceptances
- `BountyProof`: Stores proof submissions (screenshots/videos)
- `BountyDispute`: Tracks disputes

---

#### 6.4 Loadout (Hardware & Configs)

**Models**: 
- `HardwareGear` (1:N with User, max 1 per category)
- `GameConfig` (1:N with User, max 1 per game)

##### 6.4.1 Hardware Gear

**Purpose**: Pro player hardware setup (mouse, keyboard, headset, monitor, mousepad)

**Fields** (from `HardwareGear` model):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `category` | Select | ✅ | MOUSE/KEYBOARD/HEADSET/MONITOR/MOUSEPAD |
| `brand` | Text | ✅ | Brand name (e.g., Logitech, Razer) |
| `model` | Text | ✅ | Product model (e.g., G Pro X Superlight) |
| `specs` | JSON | ❌ | Specifications (DPI, polling rate, weight) |
| `purchase_url` | URL | ❌ | Optional affiliate link |
| `is_public` | Boolean | ✅ | Show on public profile |

**Hardware Categories**:
- MOUSE: DPI, polling rate, weight
- KEYBOARD: Switch type, layout
- HEADSET: Wired/wireless, surround sound
- MONITOR: Refresh rate, resolution, panel type
- MOUSEPAD: Size, surface type

**Validation Rules**:
- One hardware item per category per user
- Brand and model cannot be empty
- Specs stored as flexible JSON (different per category)

**UI Components**:
- **Card Grid**: 5 cards (one per category)
- **Empty State**: "Add [Category]" button
- **Filled State**: 
  - Brand + Model display
  - Specs badges (e.g., "800 DPI", "1000Hz")
  - Edit button
  - Delete button
  - Public/Private toggle
- **Modal Form**:
  - Category (disabled if editing)
  - Brand autocomplete (with popular brands)
  - Model text input
  - Specs builder:
    - Mouse: DPI, Polling Rate, Weight inputs
    - Keyboard: Switch Type dropdown, Layout dropdown
    - Headset: Connection Type dropdown
    - Monitor: Refresh Rate, Resolution, Panel Type
    - Mousepad: Size dropdown, Surface Type dropdown
  - Purchase URL (optional)
  - Public toggle

**Related APIs**:
- `POST /api/profile/loadout/hardware/` - Save hardware
- `DELETE /api/profile/loadout/hardware/<id>/` - Delete hardware

---

##### 6.4.2 Game Configurations

**Purpose**: Per-game settings (sensitivity, crosshair, keybinds, graphics)

**Fields** (from `GameConfig` model):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `game` | ForeignKey | ✅ | Game this config applies to |
| `settings` | JSON | ✅ | Game-specific configuration |
| `is_public` | Boolean | ✅ | Show on public profile |
| `notes` | Textarea | ❌ | Optional notes (max 500 chars) |

**Settings Structure** (examples):
- **Valorant**: `{sensitivity: 0.45, dpi: 800, crosshair_style: 'small_dot'}`
- **CS2**: `{sensitivity: 1.2, dpi: 800, viewmodel_fov: 68}`
- **PUBG**: `{sensitivity: 50, vehicle_controls: {...}}`

**Validation Rules**:
- One config per user per game
- Settings must be valid JSON dict
- Notes max 500 characters

**UI Components**:
- **List View**: Cards showing game configs
- **Add Button**: "+ Add Game Config" → opens modal
- **Modal Form**:
  - Game dropdown
  - **Dynamic settings builder** based on game schema:
    - Sensitivity slider (0.1-2.0)
    - DPI input (400-3200)
    - Crosshair style dropdown
    - Keybinds editor (advanced accordion)
  - Notes textarea
  - Public toggle
- **Card Actions**:
  - Edit button
  - Delete button
  - Copy config button (copy JSON to clipboard)

**Related APIs**:
- `POST /api/profile/loadout/game-config/` - Save config
- `DELETE /api/profile/loadout/game-config/<id>/` - Delete config

---

### 7. ASSETS & LIVE

#### 7.1 Inventory & Cosmetics

**Purpose**: Digital assets (profile frames, chat colors, emotes)

**Fields** (from `UserProfile` model):

| Field | Type | Description |
|-------|------|-------------|
| `inventory_items` | JSON | List of owned digital asset IDs |
| `pinned_badges` | JSON | List of pinned badge IDs (max 5) |

**UI Components**:
- **Inventory Grid**: Visual grid of owned items
- **Categories**: Profile Frames, Chat Colors, Emotes, Name Tags
- **Item Card**: Preview + "Equip" button
- **Equipped Items Section**: Shows currently active items

**Future Integration**: Shop system for purchasing cosmetics

---

#### 7.2 Stream Configuration

**Model**: `StreamConfig` (1:1 with UserProfile)

**Purpose**: Streaming setup and live status

**Fields** (from `UserProfile` model):

| Field | Type | Description |
|-------|------|-------------|
| `stream_status` | Boolean | Currently streaming (grants XP bonuses) |
| `twitch_link` | URL | Twitch channel URL |

**UI Components**:
- **Live Toggle**: "I'm Live" switch → sets `stream_status` = True
- **Stream URL**: Twitch/YouTube link input
- **Auto-detect**: API integration to auto-detect when user goes live (future)
- **XP Bonus Display**: Shows "+50% XP while streaming"

**Related**: `SocialLink` model for streaming platforms

---

#### 7.3 Wallet & Earnings

**Models**: 
- `DeltaCrownWallet` (1:1 with UserProfile)
- `DeltaCrownTransaction` (N:1 with Wallet)

**Purpose**: Virtual currency balance, earnings tracking, withdrawals

---

##### 7.3.1 Balance Overview

**Fields** (from `DeltaCrownWallet` model):

| Field | Type | Description |
|-------|------|-------------|
| `cached_balance` | Integer | Current DeltaCoin balance |
| `pending_balance` | Integer | Locked in pending withdrawals |
| `lifetime_earnings` | Integer | Total earned from prizes (all-time) |
| `last_withdrawal_at` | DateTime | Last successful withdrawal |

**Calculated Fields**:
- `available_balance` = `cached_balance` - `pending_balance`

**UI Components**:
- **Large Balance Card**:
  - Main balance (with DeltaCoin icon)
  - Available balance (green badge)
  - Pending balance (yellow badge)
- **Lifetime Earnings Badge**: "🏆 [amount] earned all-time"
- **Last Withdrawal**: "Last withdrawal: [date]"

---

##### 7.3.2 Withdrawal Methods (Bangladesh Mobile Banking)

**Fields** (from `DeltaCrownWallet` model):

| Payment Method | Field | Validation |
|---------------|-------|------------|
| bKash | `bkash_number` | 01[3-9]XXXXXXXXX (11 digits) |
| Nagad | `nagad_number` | 01[3-9]XXXXXXXXX (11 digits) |
| Rocket | `rocket_number` | 01[3-9]XXXXXXXXX (11 digits) |
| Bank Transfer | `bank_account_name`, `bank_account_number`, `bank_name`, `bank_branch` | Full details required |

**UI Components**:
- **Tab Selector**: bKash / Nagad / Rocket / Bank Transfer
- **bKash Tab**:
  - Phone number input with Bangladesh flag
  - Format helper: "01712345678"
  - Verification badge if verified
- **Bank Transfer Tab**:
  - Account holder name input
  - Account number input
  - Bank name dropdown (popular BD banks)
  - Branch name input
- **Save Button**: "Save Withdrawal Method"

---

##### 7.3.3 Withdrawal PIN

**Fields** (from `DeltaCrownWallet` model):

| Field | Type | Description |
|-------|------|-------------|
| `pin_hash` | Hashed | 4-digit PIN for withdrawal security |

**UI Components**:
- **If no PIN**: "Set Withdrawal PIN" button → modal
- **Modal**:
  - PIN input (4 digits, masked)
  - Confirm PIN input
  - Security warning: "Required for all withdrawals"
- **If PIN set**: "Change PIN" button

---

##### 7.3.4 Withdrawal Requests

**Model**: `WithdrawalRequest` (from apps/economy/models.py)

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `amount` | Integer | Amount to withdraw (DeltaCoins) |
| `method` | Select | bkash/nagad/rocket/bank |
| `status` | Select | pending/approved/rejected/completed |
| `requested_at` | DateTime | Request timestamp |

**Validation Rules**:
- Minimum withdrawal: 500 DeltaCoins
- Maximum withdrawal: 50,000 DeltaCoins per request
- KYC verification required
- Withdrawal method must be configured
- PIN verification required

**UI Components**:
- **Withdraw Button**: Opens withdrawal modal
- **Modal**:
  - Amount input (with min/max validation)
  - Method selector (shows saved methods)
  - Fee display: "5% platform fee = [amount]"
  - PIN verification input
  - Estimated processing: "24-48 hours"
- **Withdrawal History Table**:
  - Date, Amount, Method, Status, Reference ID

---

##### 7.3.5 Transaction History

**Model**: `DeltaCrownTransaction` (from apps/economy/models.py)

**Transaction Types**:
- `prize`: Tournament prize
- `deposit`: Manual admin credit
- `withdrawal`: Withdrawal request
- `bounty_stake`: Bounty stake lock
- `bounty_payout`: Bounty win
- `purchase`: Shop purchase
- `refund`: Refund

**UI Components**:
- **Transaction List**: Table with infinite scroll
- **Columns**: Date, Type, Amount (+/-), Balance After, Description
- **Filters**: Type dropdown, Date range picker
- **Export Button**: "Download CSV"

---

### 8. PLATFORM PREFERENCES

**Model**: `UserProfile` (system_settings JSON field)

#### 8.1 Language & Region

**Fields** (from `UserProfile` model):

| Field | Type | Choices | Default |
|-------|------|---------|---------|
| `preferred_language` | Select | en (English), bn (Bengali - Coming Soon) | en |
| `timezone_pref` | Text | IANA timezone | Asia/Dhaka |
| `time_format` | Select | 12h (3:00 PM), 24h (15:00) | 12h |

**UI Components**:
- Language dropdown with flag icons
- Timezone autocomplete (with popular Bangladesh timezones at top)
- Time format radio buttons

---

#### 8.2 Theme

**Fields** (from `UserProfile` model):

| Field | Type | Choices | Default |
|-------|------|---------|---------|
| `theme_preference` | Select | light, dark, system | dark |

**UI Components**:
- Theme selector with preview cards
- **Light**: Preview with light colors
- **Dark**: Preview with dark colors (current)
- **System**: "Match system settings"
- Apply instantly on change (no save button needed)

---

### 9. SOCIAL

#### 9.1 Social Links

**Model**: `SocialLink` (1:N with User)

**Purpose**: Connected social media and streaming platforms

**Supported Platforms** (from `PLATFORM_CHOICES`):

**Streaming**:
- Twitch
- YouTube
- Kick
- Facebook Gaming

**Social Media**:
- Twitter/X
- Discord
- Instagram
- TikTok
- Facebook

**Gaming**:
- Steam
- Riot Games

**Dev**:
- GitHub

**Fields** (from `SocialLink` model):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | Select | ✅ | Platform from choices above |
| `url` | URL | ✅ | Full URL to profile |
| `handle` | Text | ❌ | Display name/handle (optional) |
| `is_verified` | Boolean | Auto | Platform API verification |

**Validation Rules**:
- One link per platform per user (unique constraint)
- URL must contain platform domain:
  - Twitch: `twitch.tv/`
  - YouTube: `youtube.com/` or `youtu.be/`
  - Twitter: `twitter.com/` or `x.com/`
  - Discord: `discord.gg/`
  - Instagram: `instagram.com/`
  - TikTok: `tiktok.com/@`
  - Steam: `steamcommunity.com/`

**UI Components**:
- **List View**: Cards showing connected platforms
- **Add Button**: "+ Add Social Link" → modal
- **Modal**:
  - Platform dropdown (with icons)
  - URL input (with platform-specific placeholder)
  - Handle input (optional)
- **Card Actions**:
  - Edit button
  - Delete button
  - Verification badge if `is_verified` = True
- **Drag-and-drop reordering** for display order

**Related APIs**:
- `GET /user-profile/api/social-links/` - List user's social links
- `POST /user-profile/api/social-links/create/` - Add social link
- `POST /user-profile/api/social-links/update/` - Update social link
- `DELETE /user-profile/api/social-links/delete/` - Remove social link

---

#### 9.2 Following System

**Model**: `Follow` (M:N relationship via follower/following)

**Purpose**: Instagram-style follower/following system

**Statistics** (from context):
- `follower_count`: Number of users following this user
- `following_count`: Number of users this user follows

**Privacy Controls**: (from `PrivacySettings`)
- `show_followers_count`: Display count on profile
- `show_following_count`: Display count on profile
- `show_followers_list`: Allow viewing follower list
- `show_following_list`: Allow viewing following list

**UI Components** (Read-Only in Settings):
- **Statistics Display**:
  - Followers: [count]
  - Following: [count]
- **Link to Profile**: "Manage followers on your profile"
- **Privacy Toggles**: Link to Privacy section

**Related APIs**:
- `GET /user-profile/api/profile/<username>/followers/` - List followers
- `GET /user-profile/api/profile/<username>/following/` - List following
- `POST /user-profile/api/profile/<username>/follow/` - Follow user
- `POST /user-profile/api/profile/<username>/unfollow/` - Unfollow user

---

### 10. DANGER ZONE

**Purpose**: Irreversible account actions

#### 10.1 Deactivate Account

**Action**: Temporarily deactivate account (reversible)

**Effects**:
- Profile hidden from search
- Cannot participate in tournaments
- Cannot send/receive messages
- Wallet remains accessible
- Can reactivate anytime

**UI Components**:
- **Warning Card** (red background):
  - Title: "⚠️ Deactivate Account"
  - Description: "Your profile will be hidden. You can reactivate anytime."
  - Button: "Deactivate Account"
- **Confirmation Modal**:
  - Password verification
  - Reason dropdown (optional)
  - "Are you sure?" checkbox
  - "Deactivate" button (red)

---

#### 10.2 Delete Account

**Action**: Permanently delete account (irreversible after 30 days)

**Effects**:
- 30-day grace period (can cancel deletion)
- After 30 days: All data permanently deleted
- Wallet balance forfeited if not withdrawn
- Tournament history anonymized
- Game IDs released

**Legal Requirements**:
- GDPR Article 17 (Right to Erasure)
- Must withdraw wallet balance first
- Cannot delete if active tournament registrations

**UI Components**:
- **Danger Card** (dark red background):
  - Title: "🚨 Delete Account Permanently"
  - Description: "This action cannot be undone after 30 days."
  - Prerequisites checklist:
    - [ ] Wallet balance withdrawn
    - [ ] No active tournament registrations
    - [ ] Read data retention policy
  - Button: "Request Account Deletion" (disabled until checklist complete)
- **Confirmation Modal**:
  - Type "DELETE" to confirm
  - Password verification
  - Reason textarea (optional, for analytics)
  - "I understand this is permanent" checkbox
  - "Delete My Account" button (dark red)

---

## 🎨 UI/UX Design Guidelines

### Layout Structure

**Desktop (>1024px)**:
```
┌─────────────────────────────────────────────────┐
│ Header (Logo, User Menu)                        │
├──────────────┬──────────────────────────────────┤
│ Settings Nav │ Content Area                     │
│ (Sticky)     │                                  │
│              │                                  │
│ Account      │ [Active Section Content]        │
│ Identity     │                                  │
│ Privacy      │                                  │
│ Security     │                                  │
│ ...          │                                  │
│              │                                  │
└──────────────┴──────────────────────────────────┘
```

**Mobile (<768px)**:
```
┌─────────────────────────┐
│ Header                  │
├─────────────────────────┤
│ [Hamburger Menu]        │
│ Current Section Name    │
├─────────────────────────┤
│                         │
│ Content Area            │
│ (Full Width)            │
│                         │
│                         │
└─────────────────────────┘
```

---

### Visual Hierarchy

**Page Structure**:
1. **Settings Navigation** (Left Sidebar)
   - Section headers (uppercase, small, gray)
   - Active section (cyan accent)
   - Hover states
   
2. **Content Area** (Right)
   - Section title (large, white)
   - Section description (gray, smaller)
   - Setting cards/groups
   - Save buttons (bottom-right sticky)

**Card Components**:
```
┌─────────────────────────────────────────┐
│ Card Title                         [Icon]│
│ Description text in gray...              │
│                                          │
│ [Input Fields]                           │
│ [Toggle Switches]                        │
│                                          │
│                     [Cancel] [Save]      │
└─────────────────────────────────────────┘
```

---

### Component Library

#### Toggle Switch (iOS-style)
- Off: Gray background, white circle (left)
- On: Cyan background, white circle (right)
- Disabled: Gray background with reduced opacity

#### Input Fields
- Label (above input, small, gray)
- Input box (dark background, white text, cyan border on focus)
- Help text (below input, smaller, gray)
- Error state (red border, red help text)

#### Buttons
- **Primary**: Cyan background, white text
- **Secondary**: Transparent with cyan border, cyan text
- **Danger**: Red background, white text
- **Ghost**: Transparent, gray text (hover: white text)

#### Modals
- Dark overlay (80% opacity)
- White card (rounded corners, shadow)
- Close button (top-right)
- Actions at bottom (Cancel left, Confirm right)

#### Badges
- Status badges (green=verified, yellow=pending, red=rejected, gray=unverified)
- Count badges (small, pill-shaped, cyan background)
- Icon badges (circular, 24px, colored borders)

---

### Color Palette

**Primary Colors**:
- `--z-cyan`: #00D9FF (primary accent, links, buttons)
- `--z-purple`: #B066FF (secondary accent, premium features)
- `--z-gold`: #FFD700 (achievements, rewards)

**Background Colors**:
- `--z-bg`: #0A0E27 (main background)
- `--z-card-bg`: #1A1F3A (card background)
- `--z-hover-bg`: rgba(255,255,255,0.05) (hover states)

**Text Colors**:
- `--z-text-primary`: #FFFFFF (headings, primary text)
- `--z-text-secondary`: #94A3B8 (body text, descriptions)
- `--z-text-muted`: #64748B (help text, placeholders)

**Semantic Colors**:
- Success: #22C55E
- Warning: #F59E0B
- Error: #EF4444
- Info: #3B82F6

---

### Typography

**Font Family**:
- Display: "Orbitron" (headings, section titles)
- Body: "Inter" (paragraphs, inputs)

**Font Sizes**:
- `text-4xl`: 2.25rem (page titles)
- `text-2xl`: 1.5rem (section titles)
- `text-lg`: 1.125rem (card titles)
- `text-base`: 1rem (body text)
- `text-sm`: 0.875rem (help text)
- `text-xs`: 0.75rem (badges, labels)

---

### Spacing

**Padding/Margin**:
- `xs`: 0.25rem (4px)
- `sm`: 0.5rem (8px)
- `md`: 1rem (16px)
- `lg`: 1.5rem (24px)
- `xl`: 2rem (32px)
- `2xl`: 3rem (48px)

**Component Spacing**:
- Between sections: 3rem (48px)
- Between cards: 1.5rem (24px)
- Within cards: 1rem (16px)
- Between inputs: 1rem (16px)

---

### Animations

**Transitions**:
- Default: 150ms ease-in-out
- Hover states: 200ms ease-in-out
- Modal open/close: 300ms ease-in-out

**Micro-interactions**:
- Toggle switch: 200ms spring animation
- Button click: Scale(0.95) for 100ms
- Card hover: translateY(-2px) + shadow increase
- Save success: Green checkmark fade-in

---

## 🔗 API Endpoints Summary

### Account & Identity
- `POST /user-profile/me/settings/basic/` - Update display name, bio, pronouns
- `POST /user-profile/me/settings/media/` - Upload avatar/banner
- `POST /user-profile/me/settings/media/remove/` - Remove avatar/banner

### Privacy & Security
- `GET /user-profile/me/settings/privacy/` - Get privacy settings
- `POST /user-profile/me/settings/privacy/save/` - Update privacy settings

### Game Passports
- `GET /user-profile/api/game-passports/` - List passports
- `POST /user-profile/api/game-passports/create/` - Create passport
- `POST /user-profile/api/game-passports/update/` - Update passport
- `POST /user-profile/api/game-passports/delete/` - Delete passport
- `POST /user-profile/api/passports/pin/` - Pin/unpin passport
- `POST /user-profile/api/passports/toggle-lft/` - Toggle LFT status

### Social Links
- `GET /user-profile/api/social-links/` - List social links
- `POST /user-profile/api/social-links/create/` - Add social link
- `POST /user-profile/api/social-links/delete/` - Remove social link

### Loadout
- `POST /api/profile/loadout/hardware/` - Save hardware
- `DELETE /api/profile/loadout/hardware/<id>/` - Delete hardware
- `POST /api/profile/loadout/game-config/` - Save game config
- `DELETE /api/profile/loadout/game-config/<id>/` - Delete game config

### Bounties
- `POST /user-profile/api/bounties/create/` - Create bounty
- `POST /user-profile/api/bounties/<id>/accept/` - Accept bounty
- `POST /user-profile/api/bounties/<id>/start/` - Start match
- `POST /user-profile/api/bounties/<id>/submit-proof/` - Submit proof
- `POST /user-profile/api/bounties/<id>/confirm-result/` - Confirm result
- `POST /user-profile/api/bounties/<id>/dispute/` - Raise dispute

### Notifications
- `GET /api/settings/notifications/` - Get notification preferences
- `POST /user-profile/me/settings/notifications/` - Update preferences

### Wallet
- `GET /api/settings/wallet/` - Get wallet settings
- `POST /user-profile/me/settings/wallet/` - Update wallet settings

---

## 📱 Mobile Considerations

### Responsive Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1023px
- Desktop: ≥ 1024px

### Mobile-Specific Features
- **Collapsible Navigation**: Hamburger menu for settings nav
- **Bottom Sheet Modals**: Modal slides up from bottom on mobile
- **Touch Targets**: Minimum 44x44px for all interactive elements
- **Swipe Gestures**: Swipe right to open nav, swipe left to close
- **Reduced Motion**: Respect `prefers-reduced-motion` media query

---

## ✅ Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Create settings page layout (nav + content area)
- [ ] Implement routing (tab-based navigation)
- [ ] Build reusable components (Toggle, Input, Modal, Card)
- [ ] Set up form validation utilities

### Phase 2: Account & Identity (Week 2)
- [ ] Profile Information section
- [ ] Contact Details section
- [ ] Demographics section
- [ ] Avatar/Banner upload UI
- [ ] Legal Information (KYC) section
- [ ] Location section

### Phase 3: Privacy & Security (Week 3)
- [ ] Privacy preset selector
- [ ] Granular privacy toggles
- [ ] Follower/Following privacy
- [ ] Interaction permissions
- [ ] KYC verification dashboard
- [ ] Withdrawal PIN setup

### Phase 4: Esports (Week 4-5)
- [ ] Career & LFT section
- [ ] Game Passports manager (CRUD + drag-drop)
- [ ] Bounties dashboard
- [ ] Hardware Gear manager
- [ ] Game Config manager

### Phase 5: Notifications & Preferences (Week 6)
- [ ] Email notification toggles
- [ ] Platform notification toggles
- [ ] Per-event channel settings
- [ ] Notification digest settings
- [ ] Language & timezone selectors
- [ ] Theme switcher

### Phase 6: Wallet & Economy (Week 7)
- [ ] Balance overview
- [ ] Withdrawal method setup (bKash, Nagad, Rocket, Bank)
- [ ] Withdrawal request flow
- [ ] Transaction history table
- [ ] Export transactions

### Phase 7: Social & Danger Zone (Week 8)
- [ ] Social Links manager (CRUD)
- [ ] Following statistics display
- [ ] Deactivate account flow
- [ ] Delete account flow with confirmations

### Phase 8: Polish & Testing (Week 9-10)
- [ ] Mobile responsive testing
- [ ] Accessibility audit
- [ ] Cross-browser testing
- [ ] Performance optimization
- [ ] User acceptance testing

---

## 📚 Reference Documents

### Existing Code
- **Models**: `apps/user_profile/models_main.py`, `apps/user_profile/models/*.py`
- **Views**: `apps/user_profile/views/public_profile_views.py`, `apps/user_profile/views/settings_api.py`
- **URLs**: `apps/user_profile/urls.py`
- **Admin**: `apps/user_profile/admin.py`

### Design System
- **Tokens**: `static/css/design-tokens.css`
- **Components**: `templates/components/`

### API Documentation
- **Frontend-Backend Sync**: `docs/profile_rebuild/FRONTEND_BACKEND_SYNC_REPORT.md`
- **Page Inventory**: `docs/profile_rebuild/PAGE_INVENTORY_AND_PRIORITY.md`

---

## 🎯 Success Metrics

### UX Metrics
- **Settings Completion Rate**: % of users who save changes
- **Time to Complete**: Average time spent in settings
- **Error Rate**: % of form submissions with validation errors
- **Mobile Usage**: % of settings changes on mobile devices

### Business Metrics
- **KYC Verification Rate**: % of users completing KYC
- **Withdrawal Method Setup**: % of users configuring paymentmethods
- **Game Passport Creation**: Average passports per user
- **Privacy Control Usage**: % of users adjusting privacy settings

---

**End of Document**

*This specification serves as the complete reference for designers and developers implementing the DeltaCrown Settings Page. All model fields, validation rules, and UI components are documented for a unified, comprehensive settings experience.*
