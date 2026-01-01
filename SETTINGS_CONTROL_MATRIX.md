# Settings Control Matrix - Production Audit

**Platform**: DeltaCrown Esports  
**Template**: `templates/My drafts/setting_temp/settings_temp.html`  
**Audit Date**: January 1, 2026  
**Auditor**: Senior Full-Stack Engineer  
**Purpose**: Backend implementation status for every UI control

---

## Audit Methodology

1. **Source Template**: `settings_temp.html` (709 lines)
2. **Backend Models Verified**:
   - `UserProfile` (`apps/user_profile/models_main.py`)
   - `PrivacySettings` (`apps/user_profile/models_main.py`)
   - `GameProfile` (`apps/user_profile/models_main.py`)
   - `SocialLink` (`apps/user_profile/models_main.py`)
   - `HardwareGear` (`apps/user_profile/models/loadout.py`)
   - `GameConfig` (`apps/user_profile/models/loadout.py`)
   - `Bounty` (`apps/user_profile/models/bounties.py`)
   - `DeltaCrownWallet` (`apps/economy/models.py`)
3. **Design Specification**: `docs/profile_rebuild/SETTINGS_PAGE_UI_UX_DESIGN_SPEC.md`

---

## Risk Level Definitions

- **LOW**: Backend fully implemented, field exists, no migration needed
- **MEDIUM**: Backend exists but incomplete/untested, or requires minor schema changes
- **HIGH**: No backend implementation, requires new model/field/API

---

## Settings Control Matrix

| UI_SECTION | UI_CONTROL | CONTROL_TYPE | INTENDED_BEHAVIOR | BACKEND_MODEL | BACKEND_FIELD | BACKEND_STATUS | RISK_LEVEL | NOTES |
|------------|------------|--------------|-------------------|---------------|---------------|----------------|------------|-------|
| **IDENTITY** | Change Cover Image | upload | Upload profile banner image | UserProfile | `banner` | READY | LOW | ImageField exists (upload_to=user_banner_path), max 10MB, API: POST /me/settings/media/ |
| **IDENTITY** | Change Avatar | upload | Upload profile picture | UserProfile | `avatar` | READY | LOW | ImageField exists (upload_to=user_avatar_path), max 5MB, API: POST /me/settings/media/ |
| **IDENTITY** | Display Name | input | Public display name | UserProfile | `display_name` | READY | LOW | CharField(max_length=80), required, validated in form |
| **IDENTITY** | Gamertag | input | Unique username/slug | UserProfile | `slug` | READY | LOW | SlugField(max_length=64), unique=True, optional |
| **IDENTITY** | Location | input | City/country residence | UserProfile | `city`, `country` | READY | LOW | CharField(max_length=100), privacy controlled by PrivacySettings.show_country |
| **IDENTITY** | Bio | textarea | Profile bio/headline | UserProfile | `bio` | READY | LOW | TextField, blank=True, recommended max 500 chars |
| **CAREER & LFT** | Current Status (Signed) | radio | Career status: Signed to team | UserProfile | NOT_IMPLEMENTED | NOT_IMPLEMENTED | HIGH | No `career_status` or `recruitment_status` field exists. Design shows 3 options: Signed/Free Agent/Scouting. Requires new CharField with choices or enum |
| **CAREER & LFT** | Current Status (Free Agent) | radio | Career status: Open to offers | UserProfile | NOT_IMPLEMENTED | NOT_IMPLEMENTED | HIGH | Same as above. No backend field for LFT recruitment status at profile level (only GameProfile.is_lft per-game) |
| **CAREER & LFT** | Current Status (Scouting) | radio | Career status: Manager recruiting | UserProfile | NOT_IMPLEMENTED | NOT_IMPLEMENTED | HIGH | Same as above. No manager/recruiter role distinction in UserProfile |
| **CAREER & LFT** | Primary Role | select | Main esports role (IGL/Duelist/Support) | GameProfile | `main_role` | READY | LOW | CharField(max_length=50), per-game, but UI shows global dropdown (mismatch). Should either be per-game or global field |
| **CAREER & LFT** | Min. Salary (Monthly) | input | Minimum salary expectation | UserProfile | NOT_IMPLEMENTED | NOT_IMPLEMENTED | HIGH | No `min_salary` or `salary_expectation` field. Spec mentions this is private, not visible to recruiters unless offer meets threshold. Requires new IntegerField or DecimalField |
| **CAREER & LFT** | Allow Direct Contracts | toggle | Enable manager contract DMs | PrivacySettings | NOT_IMPLEMENTED | NOT_IMPLEMENTED | MEDIUM | No `allow_direct_contracts` field. Related: `allow_direct_messages` exists but is for all DMs, not contract-specific. Requires new BooleanField or reuse allow_direct_messages with context |
| **MATCHMAKING** | Minimum Bounty Threshold | slider | Anti-spam filter for challenges | UserProfile or Bounty | NOT_IMPLEMENTED | NOT_IMPLEMENTED | HIGH | No `min_bounty_threshold` field. Bounty model exists but no per-user threshold setting. Requires new IntegerField in UserProfile or BountySettings 1:1 model |
| **MATCHMAKING** | Auto-Reject Unverified | toggle | Block challenges from non-KYC users | UserProfile or Bounty | NOT_IMPLEMENTED | NOT_IMPLEMENTED | MEDIUM | No `bounty_require_kyc` or `auto_reject_unverified` field. Requires new BooleanField in UserProfile |
| **MATCHMAKING** | Allow Team Challenges | toggle | Accept 5v5 bounty requests | UserProfile or Bounty | NOT_IMPLEMENTED | NOT_IMPLEMENTED | MEDIUM | No `allow_team_bounties` field. Requires new BooleanField in UserProfile |
| **PRIVACY** | Private Account | toggle | Require approval for followers | PrivacySettings | NOT_IMPLEMENTED | NOT_IMPLEMENTED | HIGH | No `is_private_account` or `require_follow_approval` field. Instagram-style privacy control. Requires new BooleanField in PrivacySettings |
| **PRIVACY** | Hide Following List | toggle | Only owner sees who they follow | PrivacySettings | `show_following_list` | READY | LOW | BooleanField(default=True), controls follower list visibility on public profile |
| **PRIVACY** | Inventory Visibility | select | Who can see frames/trophies | PrivacySettings | `show_inventory_value` | PARTIAL | MEDIUM | Only shows inventory VALUE (bool), not visibility LEVEL (public/friends/private). Requires migration to CharField with choices or new `inventory_visibility` field |
| **INVENTORY** | Allow Trade Requests | toggle | Enable item swap proposals | UserProfile | NOT_IMPLEMENTED | NOT_IMPLEMENTED | HIGH | No trade system implemented. Requires `allow_trades` BooleanField + Trade model + escrow logic |
| **INVENTORY** | Allow Incoming Gifts | toggle | Enable cosmetic gifts from users | UserProfile | NOT_IMPLEMENTED | NOT_IMPLEMENTED | HIGH | No gift system implemented. Requires `allow_gifts` BooleanField + Gift model |
| **INVENTORY** | Saved Shipping Addresses | button | Manage physical prize addresses | UserProfile | `address`, `postal_code`, `city`, `country` | PARTIAL | MEDIUM | Only 1 address stored in UserProfile. No multi-address support. Requires new ShippingAddress 1:N model for multiple saved addresses |
| **PASSPORTS** | Link New Game | button | Add game passport | GameProfile | (entire model) | READY | LOW | Model fully implemented (ign, discriminator, platform, visibility, is_lft, rank_text, etc.). API: POST /api/game-passports/create/ |
| **PASSPORTS** | Game Passport Card | display | Show linked gaming IDs | GameProfile | `ign`, `discriminator`, `platform`, `rank_text`, `is_pinned` | READY | LOW | All fields exist. Supports pinning (max 6), ordering, privacy levels |
| **PASSPORTS** | Delete Passport | button | Remove game account link | GameProfile | - | READY | LOW | API: POST /api/game-passports/delete/ |
| **LOADOUT** | Mouse | input | Gaming mouse brand/model | HardwareGear | `brand`, `model` | READY | LOW | category='MOUSE', brand/model CharField, specs JSONField (DPI, polling rate, weight) |
| **LOADOUT** | Keyboard | input | Gaming keyboard brand/model | HardwareGear | `brand`, `model` | READY | LOW | category='KEYBOARD', brand/model CharField, specs JSONField (switch type, layout) |
| **LOADOUT** | Headset | input | Gaming headset brand/model | HardwareGear | `brand`, `model` | READY | LOW | category='HEADSET', brand/model CharField, specs JSONField (wired/wireless) |
| **LOADOUT** | Monitor | input | Gaming monitor brand/model | HardwareGear | `brand`, `model` | READY | LOW | category='MONITOR', brand/model CharField, specs JSONField (refresh rate, resolution, panel) |
| **STREAM** | Platform (Twitch) | radio | Select streaming platform | SocialLink | `platform`, `url` | PARTIAL | MEDIUM | SocialLink supports 'twitch' platform, but UI shows radio buttons for mutually exclusive platform selection. Current model allows multiple platforms. Need clarification: is stream URL 1:1 or N:N? |
| **STREAM** | Platform (YouTube) | radio | Select streaming platform | SocialLink | `platform`, `url` | PARTIAL | MEDIUM | Same as above. SocialLink supports 'youtube' but UI implies single active stream platform |
| **STREAM** | Channel URL | input | Streaming channel link | SocialLink | `url` | READY | LOW | URLField(max_length=500), validated per platform (twitch.tv/, youtube.com/). Constraint: unique_together=['user', 'platform'] |
| **SECURITY** | Identity Verified Badge | display | KYC verification status | UserProfile | `kyc_status`, `kyc_verified_at` | READY | LOW | CharField with choices: unverified/pending/verified/rejected. Related: VerificationRecord model tracks documents |
| **SECURITY** | Change Password | button | Update account password | Django Auth | - | READY | LOW | Delegates to /account/password_change/. No custom implementation needed |
| **NOTIFICATIONS** | Tournament Alerts | toggle | Match reminders & bracket updates | NotificationPreferences | NOT_IMPLEMENTED | NOT_IMPLEMENTED | HIGH | No NotificationPreferences model found in codebase. Spec mentions it but model does not exist. Requires new 1:1 model with UserProfile |
| **NOTIFICATIONS** | Marketing Emails | toggle | Newsletters and promotions | NotificationPreferences | NOT_IMPLEMENTED | NOT_IMPLEMENTED | HIGH | Same as above. No backend for email notification preferences. Notification model exists in apps/notifications/ but no per-user preference toggles |
| **BILLING** | Wallet Balance | display | Current DeltaCoin balance | DeltaCrownWallet | `cached_balance` | READY | LOW | IntegerField, read-only display. Calculated from ledger transactions |
| **BILLING** | Withdraw Button | button | Initiate withdrawal request | DeltaCrownWallet | `pending_balance`, `pin_hash` | READY | LOW | Requires 4-digit PIN verification (pin_hash). Supports bKash, Nagad, Rocket, bank transfer |
| **BILLING** | History Button | button | View transaction history | Transaction model | - | READY | LOW | Transaction ledger exists in apps/economy/models.py. API: GET /economy/transactions/ |
| **DANGER ZONE** | Delete Account | button | Permanently delete account | User | `is_active` or hard delete | READY | LOW | Standard Django user deletion or soft-delete (is_active=False). Requires confirmation modal + email verification |

---

## Summary Statistics

### Backend Status Breakdown

| Status | Count | Percentage |
|--------|-------|------------|
| **READY** | 22 | 56.4% |
| **PARTIAL** | 4 | 10.3% |
| **NOT_IMPLEMENTED** | 13 | 33.3% |

### Risk Level Breakdown

| Risk Level | Count | Percentage |
|------------|-------|------------|
| **LOW** | 22 | 56.4% |
| **MEDIUM** | 7 | 17.9% |
| **HIGH** | 10 | 25.6% |

---

## Critical Findings

### 🔴 HIGH RISK - Missing Backend (Requires New Models/Fields)

1. **Career Status Radio Buttons** (Signed/Free Agent/Scouting)
   - **Impact**: Core career/LFT feature non-functional
   - **Required**: New `career_status` CharField in UserProfile with choices
   - **Alternative**: Extend GameProfile.is_lft to profile-level

2. **Min. Salary Input**
   - **Impact**: Recruitment filtering broken
   - **Required**: New `min_salary_monthly` IntegerField in UserProfile

3. **Allow Direct Contracts Toggle**
   - **Impact**: Manager DM feature incomplete
   - **Required**: New `allow_direct_contracts` BooleanField in PrivacySettings OR reuse `allow_direct_messages` with context

4. **Bounty Threshold Slider**
   - **Impact**: Anti-spam filter missing
   - **Required**: New `min_bounty_threshold` IntegerField in UserProfile

5. **Private Account Toggle**
   - **Impact**: Instagram-style privacy broken
   - **Required**: New `is_private_account` BooleanField in PrivacySettings

6. **Trade/Gift Toggles**
   - **Impact**: Inventory features non-functional
   - **Required**: Trade and Gift models + escrow logic + 2 new BooleanFields

7. **NotificationPreferences Model**
   - **Impact**: All notification toggles non-functional
   - **Required**: New NotificationPreferences 1:1 model with 10+ BooleanFields

### 🟡 MEDIUM RISK - Partial Implementation

1. **Inventory Visibility Select**
   - **Issue**: Only boolean `show_inventory_value` exists, not visibility LEVEL (public/friends/private)
   - **Required**: Migrate to CharField or add `inventory_visibility` field

2. **Saved Shipping Addresses**
   - **Issue**: Only 1 address in UserProfile, no multi-address support
   - **Required**: New ShippingAddress 1:N model

3. **Stream Platform Radio Buttons**
   - **Issue**: SocialLink allows multiple platforms, but UI implies single active stream
   - **Required**: Clarify business logic (1 active stream vs N streams)

4. **Primary Role Dropdown**
   - **Issue**: UI shows global dropdown, but GameProfile.main_role is per-game
   - **Required**: Decide if role is global (new UserProfile field) or per-game (fix UI)

### ✅ LOW RISK - Ready for Production

- Avatar/Banner upload (full implementation)
- Display name, slug, bio, location (full implementation)
- Game Passports CRUD (full implementation)
- Hardware Loadout (full implementation)
- Stream URL (partial - see medium risk)
- Wallet balance/withdraw (full implementation)
- KYC status display (full implementation)
- Privacy toggles (most implemented)

---

## Recommendations

### Immediate Actions (Pre-Launch Blockers)

1. **Disable Non-Functional UI Sections**:
   - Hide "Current Status" radio buttons (Career & LFT)
   - Hide "Min. Salary" input
   - Hide "Allow Direct Contracts" toggle
   - Hide "Minimum Bounty Threshold" slider
   - Hide "Private Account" toggle
   - Hide "Allow Trade Requests" toggle
   - Hide "Allow Incoming Gifts" toggle
   - Hide all Notification toggles

2. **Add Placeholder Messages**:
   - Replace disabled sections with: "Coming Soon - Feature Under Development"

### Phase 1 (Critical Path - 2 weeks)

1. **Career/LFT Backend**:
   - Add `career_status` CharField to UserProfile
   - Add `min_salary_monthly` IntegerField to UserProfile
   - Add `allow_direct_contracts` BooleanField to PrivacySettings
   - Create Career Settings API endpoints

2. **Bounty Settings**:
   - Add `min_bounty_threshold` IntegerField to UserProfile
   - Add `auto_reject_unverified` BooleanField to UserProfile
   - Add `allow_team_bounties` BooleanField to UserProfile

3. **Privacy Enhancements**:
   - Add `is_private_account` BooleanField to PrivacySettings
   - Update follower logic to check privacy setting

### Phase 2 (Feature Completeness - 4 weeks)

1. **NotificationPreferences Model**:
   - Create 1:1 model with UserProfile
   - Add fields: email_tournament_reminders, email_match_results, email_team_invites, email_achievements, email_platform_updates
   - Add fields: notify_tournament_start, notify_team_messages, notify_follows, notify_achievements
   - Create Notification Settings API

2. **Inventory System**:
   - Migrate `show_inventory_value` to `inventory_visibility` CharField
   - Create Trade model + escrow logic
   - Create Gift model
   - Add `allow_trades`, `allow_gifts` BooleanFields

3. **Shipping Addresses**:
   - Create ShippingAddress 1:N model
   - Migrate existing UserProfile.address to ShippingAddress
   - Create Address Management API

### Phase 3 (Polish - 2 weeks)

1. **Stream Platform Clarification**:
   - Decide: Single active stream or multiple streams?
   - Update SocialLink constraints if needed
   - Fix UI radio button logic

2. **Role System**:
   - Decide: Global role or per-game role?
   - Add `global_role` to UserProfile if needed
   - Update UI to match backend logic

---

## Data Integrity Concerns

### ❌ UI-Backend Mismatches

1. **Career Status**: UI shows 3 options, backend has 0 fields
2. **Bounty Settings**: UI shows slider + 2 toggles, backend has 0 fields
3. **Notifications**: UI shows 2 toggles, backend model does not exist
4. **Inventory Visibility**: UI shows dropdown (3 options), backend has boolean (2 states)
5. **Role**: UI shows global dropdown, backend is per-game field

### ⚠️ Potential User Confusion

- Users will see settings they cannot save (no backend)
- Form submissions will silently fail or return errors
- Settings will not persist across sessions

---

## Testing Checklist

Before launch, verify each control:

- [ ] Change Cover Image → Uploads successfully, renders in profile
- [ ] Change Avatar → Uploads successfully, renders in profile
- [ ] Display Name → Saves and displays on profile
- [ ] Gamertag → Saves, enforces uniqueness
- [ ] Location → Saves, respects privacy settings
- [ ] Bio → Saves, enforces character limit
- [ ] Current Status → **SKIP (NOT IMPLEMENTED)**
- [ ] Primary Role → Verify per-game vs global logic
- [ ] Min. Salary → **SKIP (NOT IMPLEMENTED)**
- [ ] Allow Direct Contracts → **SKIP (NOT IMPLEMENTED)**
- [ ] Minimum Bounty Threshold → **SKIP (NOT IMPLEMENTED)**
- [ ] Auto-Reject Unverified → **SKIP (NOT IMPLEMENTED)**
- [ ] Allow Team Challenges → **SKIP (NOT IMPLEMENTED)**
- [ ] Private Account → **SKIP (NOT IMPLEMENTED)**
- [ ] Hide Following List → Verify toggle persists
- [ ] Inventory Visibility → Verify boolean vs dropdown mismatch
- [ ] Allow Trade Requests → **SKIP (NOT IMPLEMENTED)**
- [ ] Allow Incoming Gifts → **SKIP (NOT IMPLEMENTED)**
- [ ] Saved Shipping Addresses → Verify single address saves
- [ ] Link New Game → Verify GameProfile creation
- [ ] Delete Passport → Verify soft/hard delete
- [ ] Mouse/Keyboard/Headset/Monitor → Verify HardwareGear saves
- [ ] Stream Platform → Verify SocialLink creation/update
- [ ] Channel URL → Verify platform validation
- [ ] Identity Verified Badge → Verify KYC status display
- [ ] Change Password → Verify Django auth redirect
- [ ] Tournament Alerts → **SKIP (NOT IMPLEMENTED)**
- [ ] Marketing Emails → **SKIP (NOT IMPLEMENTED)**
- [ ] Wallet Balance → Verify display from cached_balance
- [ ] Withdraw Button → Verify PIN prompt + withdrawal flow
- [ ] History Button → Verify transaction list loads
- [ ] Delete Account → Verify confirmation flow

---

## API Endpoints Status

### ✅ Implemented

- `POST /me/settings/media/` - Avatar/banner upload
- `POST /me/settings/basic/` - Display name, bio, location
- `POST /me/settings/social/` - Social links CRUD
- `POST /me/settings/privacy/` - Privacy toggles save
- `GET /api/game-passports/` - List passports
- `POST /api/game-passports/create/` - Create passport
- `POST /api/game-passports/delete/` - Delete passport
- `GET /economy/transactions/` - Transaction history

### ❌ Missing

- `POST /me/settings/career/` - Career status + salary
- `POST /me/settings/bounty-preferences/` - Bounty thresholds
- `POST /me/settings/notifications/` - Notification preferences
- `POST /me/settings/inventory/` - Trade/gift toggles
- `GET /me/settings/shipping-addresses/` - Address management
- `POST /me/settings/shipping-addresses/create/` - Add address

---

## Conclusion

**Production Readiness**: ⚠️ **NOT READY**

- **33.3%** of UI controls have no backend implementation
- **25.6%** of controls are HIGH RISK (require new models/APIs)
- **17.9%** of controls are MEDIUM RISK (partial implementation)

**Recommended Action**:
1. Disable all NOT_IMPLEMENTED sections immediately
2. Ship with 56.4% functional controls (LOW RISK only)
3. Prioritize Phase 1 (Career/LFT + Bounty Settings) for next sprint
4. Full feature parity in 8 weeks (Phases 1-3)

**Alternative Strategy**:
- Ship as "Beta Settings" with disclaimer
- Progressive rollout as backend completes
- User feedback loop during phased development

---

**Audit Completed**: January 1, 2026  
**Next Review**: After Phase 1 completion
