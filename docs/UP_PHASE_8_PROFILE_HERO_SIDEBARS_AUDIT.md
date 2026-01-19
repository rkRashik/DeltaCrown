# UP PHASE 8 — PROFILE HERO + SIDEBARS + OVERVIEW AUDIT
**Audit Date:** January 20, 2026  
**Scope:** Hero section, Left/Right sidebars, Overview tab widgets  
**Status:** 🔍 PRE-IMPLEMENTATION AUDIT

---

## 🎯 AUDIT OBJECTIVES

This audit documents the current state of the public profile page before implementing Phase 8 improvements:
1. Hero section (Follow system + Recruit widget)
2. Left sidebar (Profile Status, Connect, Gear)
3. Right sidebar (Live section)
4. Overview tab widgets (Career, Game Passports)

**Critical Rule:** Preserve existing design language. No global refactors. Scoped changes only.

---

## 📁 FILE STRUCTURE

### Primary Template
**File:** [templates/user_profile/profile/public_profile.html](templates/user_profile/profile/public_profile.html) (815 lines)

**Structure:**
```
Lines 1-203: Base template + CSS (Tailwind config, glass styles)
Lines 207-332: HERO SECTION (banner, avatar, bio, stats, action buttons)
Lines 337-515: LEFT SIDEBAR (Profile Status, Connect, Gear, Wallet)
Lines 518-562: CENTER COLUMN (Tab navigation)
Lines 567-686: RIGHT SIDEBAR (Live, Affiliations, Trophies, Bounty)
Lines 689-815: Mobile nav + JavaScript
```

### Tab Partials
- [templates/user_profile/profile/tabs/_tab_overview.html](templates/user_profile/profile/tabs/_tab_overview.html) (135 lines)
- [templates/user_profile/profile/tabs/_tab_career.html](templates/user_profile/profile/tabs/_tab_career.html)
- [templates/user_profile/profile/tabs/_tab_posts.html](templates/user_profile/profile/tabs/_tab_posts.html)
- [templates/user_profile/profile/tabs/_tab_highlights.html](templates/user_profile/profile/tabs/_tab_highlights.html)
- [templates/user_profile/profile/tabs/_tab_economy.html](templates/user_profile/profile/tabs/_tab_economy.html)
- [templates/user_profile/profile/tabs/_tab_bounty.html](templates/user_profile/profile/tabs/_tab_bounty.html)
- [templates/user_profile/profile/tabs/_tab_inventory.html](templates/user_profile/profile/tabs/_tab_inventory.html)

### About Section Partial
- [templates/user_profile/profile/partials/_about_tactical_v4.html](templates/user_profile/profile/partials/_about_tactical_v4.html)

### Views
**File:** [apps/user_profile/views/public_profile_views.py](apps/user_profile/views/public_profile_views.py) (2939 lines)

**Key Function:** `public_profile_view(request, username)` (Lines 84-250+)

---

## 🧩 CURRENT IMPLEMENTATION STATUS

### 1. HERO SECTION (Lines 207-332)

#### ✅ ALREADY EXISTS
- **Banner image** with gradient overlay
- **Avatar** with level badge
- **Team affiliation** badge (if member)
- **KYC verification** badge
- **Display name** + username
- **Bio** text with purple border accent
- **Stats row**: Followers, Following, Wins counts
- **Country flag** display

#### ❌ MISSING / NEEDS WORK
- **Follow/Unfollow functionality** (Lines 303-318):
  - Buttons exist but link to `{{ follow_url }}` and `{{ unfollow_url }}` (not wired)
  - No AJAX handling (full page refresh)
  - Follow request system partially implemented (shows "Requested" state)
  - Context keys: `relationship_ctx.can_follow`, `relationship_ctx.is_following`, `relationship_ctx.follow_requested`

- **Recruit button** (Lines 319-323):
  - Exists visually with condition `relationship_ctx.can_recruit`
  - **NOT LINKED** to Career tab (no deep link logic)
  - **Logic unclear**: What determines `can_recruit`?

- **Follower/Following counts** (Lines 276-285):
  - Display exists: `{{ follower_count }}`, `{{ following_count }}`
  - **Not clickable** (no modal/list view)
  - **Privacy not enforced**: Shown regardless of settings

**Context Keys Used:**
```python
relationship_ctx.show_edit_button  # Owner check
relationship_ctx.can_follow        # Can show Follow button
relationship_ctx.is_following      # Following state
relationship_ctx.follow_requested  # Pending follow request
relationship_ctx.can_recruit       # Recruit eligibility
relationship_ctx.is_private_account  # Private profile flag
follower_count                     # Follower count
following_count                    # Following count
```

---

### 2. LEFT SIDEBAR

#### 2A. Profile Status Widget (Lines 339-358)

**Current State:**
- Widget exists with hardcoded "85%" completion
- Shows fake progress bar
- Button says "Complete Now" (no functionality)
- **COMPLETELY FAKE** — Not connected to real data

**Missing:**
- Link to Settings completion logic
- Real completion percentage calculation
- Dynamic checklist items
- Proper CTA routing to Settings sections

**Visibility:** Currently shows to everyone (should be owner-only)

---

#### 2B. Connect Widget (Lines 360-450)

**Current State: ✅ MOSTLY GOOD**
- Shows Discord (special row with copy button)
- Shows other platforms in 3-column grid (Twitch, Twitter, YouTube, Facebook, Instagram, TikTok, Kick, Steam, GitHub)
- Privacy-aware: `{% if is_owner or permissions.can_view_social_links %}`
- Links to SocialLink model

**Data Source:**
```python
# From view (lines 198-228 in public_profile_views.py)
social_links = SocialLink.objects.filter(user=profile_user)
discord_handle = ...  # Extracted separately
discord_url = ...
social_links_renderable = [...]  # Filtered list with URLs
```

**Privacy Rule:**
- Owner always sees
- Visitors see if `permissions.can_view_social_links` (from `PrivacySettings.show_social_links`)

**Needs:** Make public as requested (currently private by default)

---

#### 2C. Gear Widget (Lines 452-491)

**Current State: ✅ EXISTS**
- Displays hardware gear from `HardwareGear` model
- Shows category icons (mouse, keyboard, headset, monitor, mousepad)
- Shows brand + model

**Data Source:**
```python
# From view (lines 231-242 in public_profile_views.py)
hardware_gears = HardwareGear.objects.filter(
    user=profile_user,
    is_public=True
).order_by('category')
```

**Privacy Rule:**
- Owner always sees
- Visitors see if `permissions.can_view_profile` (no specific gear privacy setting)

**Needs:** UI polish only (spacing, typography, empty state)

---

#### 2D. Wallet Widget (Lines 493-515)

**Current State:** Owner-only, functional
- Shows `wallet_balance` from context
- "Top Up" and "History" buttons (not wired)
- Lock icon for non-owners

**No changes needed** for Phase 8 (out of scope)

---

### 3. RIGHT SIDEBAR

#### 3A. Live Section (Lines 567-602)

**Current State: ⚠️ HARDCODED FAKE DATA**
- Shows fake live match ("TL vs SEN")
- "Watch Stream" button (no functionality)
- No connection to Settings → Stream Settings

**What's Missing:**
- Connection to streaming platform data (Twitch/YouTube/Facebook)
- Real live status detection
- Link to stream URL
- Privacy settings for public streaming

**Required:**
- Wire to Settings stream fields (Twitch/YouTube links from SocialLink model)
- Show "Offline" state when not streaming
- Respect privacy (owner always sees, visitors only if public)

---

#### 3B. Affiliations Widget (Lines 604-630)

**Current State: ✅ FUNCTIONAL**
- Shows teams from `user_teams` context
- Displays logo, name, role, game
- Clickable cards (hover states)

**Data Source:**
```python
# From context
user_teams = [...]  # Teams where user is member
```

**Needs:** Add Recruit button visibility here (as mentioned in requirements)

---

#### 3C. Trophies Widget (Lines 632-644)

**Current State:** Hardcoded emoji trophies
**No changes needed** for Phase 8

---

#### 3D. Active Bounty Widget (Lines 646-686)

**Current State:** Fake bounty challenge
**No changes needed** for Phase 8

---

### 4. OVERVIEW TAB WIDGETS

#### 4A. Performance Analytics (Lines 4-42 in _tab_overview.html)

**Current State: ✅ FUNCTIONAL**
- Shows K/D Ratio, Win Rate, Matches, Tournaments
- Uses `stats_ctx` context

**No changes needed** for Phase 8

---

#### 4B. Career Widget (Lines 46-79 in _tab_overview.html)

**Current State: ⚠️ HARDCODED FAKE DATA**
- Shows "Team Liquid" and "G2 Esports" (fake)
- Not connected to real Career model
- Says "Active in 2 Games" (fake)

**What's Missing:**
- Real career history data
- Limit to 2 most recent teams
- "View all" link to Career tab
- Proper data model integration

---

#### 4C. Game Passports Widget (Lines 81-135 in _tab_overview.html)

**Current State: ✅ PARTIALLY FUNCTIONAL**
- Shows pinned/unpinned game passports
- Uses real `GameProfile` model
- Context keys: `pinned_passports`, `unpinned_passports`
- Privacy-aware: `{% if is_owner or permissions.can_view_game_passports %}`

**Needs:**
- Limit display to 2 passports (currently shows all)
- "View all" link to Career tab
- Better empty state if no passports

---

## 🗄️ DATABASE MODELS

### Follow System

**Model:** `Follow` [apps/user_profile/models_main.py](apps/user_profile/models_main.py#L2291)
```python
class Follow(models.Model):
    follower = models.ForeignKey(User, related_name='following')
    followee = models.ForeignKey(User, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['follower', 'followee']]
```

**Model:** `FollowRequest` [apps/user_profile/models_main.py](apps/user_profile/models_main.py#L2432)
```python
class FollowRequest(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_ACCEPTED = 'ACCEPTED'
    STATUS_REJECTED = 'REJECTED'
    
    requester = models.ForeignKey(User, related_name='follow_requests_sent')
    target = models.ForeignKey(User, related_name='follow_requests_received')
    status = models.CharField(max_length=20, choices=...)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Service:** `FollowService` [apps/user_profile/services/follow_service.py](apps/user_profile/services/follow_service.py#L32)
```python
class FollowService:
    @staticmethod
    def is_following(follower_user, followee_user) -> bool: ...
    
    @staticmethod
    def has_pending_follow_request(requester_user, target_user) -> bool: ...
    
    @staticmethod
    def follow(follower_user, followee_user): ...
    
    @staticmethod
    def unfollow(follower_user, followee_user): ...
    
    @staticmethod
    def send_follow_request(requester_user, target_user): ...
    
    @staticmethod
    def accept_follow_request(request_id, target_user): ...
    
    @staticmethod
    def reject_follow_request(request_id, target_user): ...
```

---

### Privacy Settings

**Model:** `PrivacySettings` [apps/user_profile/models_main.py](apps/user_profile/models_main.py#L931)
```python
class PrivacySettings(models.Model):
    user_profile = models.OneToOneField(UserProfile, related_name='privacy_settings')
    
    # Visibility Preset
    visibility_preset = models.CharField(max_length=20, choices=..., default='PUBLIC')
    
    # Social Privacy
    show_social_links = models.BooleanField(default=True)
    show_followers_count = models.BooleanField(default=True)
    show_following_count = models.BooleanField(default=True)
    show_followers_list = models.BooleanField(default=True)
    show_following_list = models.BooleanField(default=True)
    
    # Private Account (Phase 6A)
    is_private_account = models.BooleanField(default=False)
    
    # Other fields...
    show_game_ids = models.BooleanField(default=True)
    show_teams = models.BooleanField(default=True)
    show_achievements = models.BooleanField(default=True)
    show_preferred_contact = models.BooleanField(default=False)
    # ...
```

**Service:** `ProfilePermissionChecker` [apps/user_profile/services/profile_permissions.py](apps/user_profile/services/profile_permissions.py)
```python
class ProfilePermissionChecker:
    def __init__(self, viewer, profile): ...
    
    def get_all_permissions(self) -> dict:
        return {
            'viewer_role': ...,  # 'owner', 'follower', 'visitor', 'anonymous'
            'is_own_profile': ...,
            'can_view_profile': ...,
            'can_view_social_links': ...,
            'can_view_followers': ...,
            'can_view_following': ...,
            'can_view_game_passports': ...,
            'can_view_achievements': ...,
            # ...
        }
```

---

### Game Passports

**Model:** `GameProfile` [apps/user_profile/models_main.py](apps/user_profile/models_main.py#L1749)
```python
class GameProfile(models.Model):
    user = models.ForeignKey(User, related_name='game_profiles')
    game = models.ForeignKey('games.Game', related_name='passports')
    
    # Identity fields
    ign = models.CharField(max_length=64, db_index=True)
    discriminator = models.CharField(max_length=32, null=True, blank=True)
    platform = models.CharField(max_length=32, null=True, blank=True)
    in_game_name = models.CharField(max_length=100)  # Computed
    
    # Rank
    rank_name = models.CharField(max_length=50, blank=True)
    rank_tier = models.IntegerField(default=0)
    
    # Stats
    matches_played = models.IntegerField(default=0)
    win_rate = models.IntegerField(default=0)
    kd_ratio = models.FloatField(null=True, blank=True)
    
    # Visibility
    visibility = models.CharField(max_length=20, choices=..., default='PUBLIC')
    is_lft = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    pinned_order = models.SmallIntegerField(null=True, blank=True)
    
    # Verification
    verification_status = models.CharField(max_length=20, choices=..., default='PENDING')
    
    class Meta:
        unique_together = [['user', 'game']]
```

**Service:** `GamePassportService` [apps/user_profile/services/game_passport_service.py](apps/user_profile/services/game_passport_service.py#L74)

---

### Social Links

**Model:** `SocialLink` [apps/user_profile/models_main.py](apps/user_profile/models_main.py#L1608)
```python
class SocialLink(models.Model):
    PLATFORM_CHOICES = [
        ('twitch', 'Twitch'),
        ('youtube', 'YouTube'),
        ('kick', 'Kick'),
        ('facebook_gaming', 'Facebook Gaming'),
        ('twitter', 'Twitter/X'),
        ('discord', 'Discord'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('facebook', 'Facebook'),
        ('steam', 'Steam'),
        ('riot', 'Riot Games'),
        ('github', 'GitHub'),
    ]
    
    user = models.ForeignKey(User, related_name='social_links')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    url = models.URLField(max_length=500)
    handle = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        unique_together = [['user', 'platform']]
```

---

### Hardware Gear

**Model:** `HardwareGear` [apps/user_profile/models_main.py](apps/user_profile/models_main.py)
```python
class HardwareGear(models.Model):
    CATEGORY_CHOICES = [
        ('MOUSE', 'Mouse'),
        ('KEYBOARD', 'Keyboard'),
        ('HEADSET', 'Headset'),
        ('MONITOR', 'Monitor'),
        ('MOUSEPAD', 'Mousepad'),
        ('GPU', 'Graphics Card'),
        ('CPU', 'Processor'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, related_name='hardware_gear')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    is_public = models.BooleanField(default=True)
```

---

### Career (NEEDS INVESTIGATION)

**Status:** No dedicated Career model found in audit. Career data appears to come from:
- `TeamMembership` model (apps/teams/models.py)
- `user_teams` context in view

**Context Keys:**
```python
user_teams = [
    {
        'name': ...,
        'tag': ...,
        'logo_url': ...,
        'role': ...,  # 'CAPTAIN', 'MANAGER', 'MEMBER'
        'game': ...,
    }
]
```

---

## 🔐 PRIVACY RULES SUMMARY

### Follow/Following Visibility

**From PrivacySettings model:**
- `show_followers_count` (default: True)
- `show_following_count` (default: True)
- `show_followers_list` (default: True)
- `show_following_list` (default: True)

**Instagram-like rules (to implement):**
- Owner: Always see everything
- Visitors: See counts only if `show_followers_count`/`show_following_count` enabled
- Visitors: See lists only if `show_followers_list`/`show_following_list` enabled
- If profile is private (`is_private_account=True`) and viewer is not a follower:
  - Option 1: Hide counts entirely
  - Option 2: Show counts but hide lists (recommended)

---

### Social Links Visibility

**Current Rule:**
- Owner always sees
- Visitors see if `PrivacySettings.show_social_links = True` (default)

**Requirement:** Make public (no privacy)

---

### Game Passports Visibility

**Current Rule:**
- Owner always sees
- Visitors see if `ProfilePermissionChecker.can_view_game_passports = True`

**Based on:**
- `PrivacySettings.show_game_ids = True` (default)

---

### Stream Settings Visibility

**Status:** No specific stream privacy setting exists

**Proposed Rule:**
- Owner always sees
- Visitors see if social links are public (piggyback on `show_social_links`)

---

## 🚧 MISSING IMPLEMENTATIONS

### 1. Follow System API Endpoints

**Status:** ❌ NOT FOUND

**Need to create:**
- `POST /api/profile/<username>/follow/`
- `POST /api/profile/<username>/unfollow/`
- Optional: `GET /api/profile/<username>/follow-state/`

**CSRF Protection:** Required
**Auth:** Required
**Response:** JSON with updated counts

---

### 2. Recruit Eligibility Logic

**Status:** ❌ LOGIC UNCLEAR

**Current Check:** `relationship_ctx.can_recruit` (computed in view)

**Need to define:**
- What determines recruit eligibility?
- Is viewer a Team Owner?
- Is viewer a Team Manager?
- Which teams can recruit this user?

**Proposed Service:**
```python
def can_recruit_user(viewer_user, target_user) -> bool:
    """
    Check if viewer is Team Owner/Manager and can recruit target.
    """
    from apps.teams.models import TeamMembership
    
    # Get viewer's teams where they are Owner or Manager
    viewer_teams = TeamMembership.objects.filter(
        user=viewer_user,
        role__in=['OWNER', 'MANAGER'],
        status='ACTIVE'
    )
    
    return viewer_teams.exists()
```

---

### 3. Settings Completion Calculator

**Status:** ❌ NOT FOUND

**Need to create:** Service to calculate profile completion percentage

**Proposed Logic:**
```python
class SettingsCompletionService:
    @staticmethod
    def calculate_completion(user_profile) -> dict:
        """
        Calculate profile completion percentage.
        
        Returns:
            {
                'percentage': 85,
                'completed_items': ['avatar', 'bio', ...],
                'missing_items': ['hardware', 'primary_team', ...],
                'checklist': [
                    {'key': 'avatar', 'label': 'Profile Picture', 'completed': True, 'url': '/settings/#avatar'},
                    {'key': 'bio', 'label': 'Bio', 'completed': True, 'url': '/settings/#bio'},
                    {'key': 'hardware', 'label': 'Hardware Loadout', 'completed': False, 'url': '/settings/#gear'},
                    # ...
                ]
            }
        """
        checklist_items = [
            ('avatar', 'Profile Picture', bool(user_profile.avatar), '/settings/#avatar'),
            ('bio', 'Bio', bool(user_profile.bio), '/settings/#bio'),
            ('primary_game', 'Primary Game', bool(user_profile.primary_game), '/settings/#games'),
            ('primary_team', 'Primary Team', bool(user_profile.primary_team), '/settings/#teams'),
            ('social_links', 'Social Links', user_profile.user.social_links.exists(), '/settings/#social'),
            ('hardware', 'Hardware Gear', HardwareGear.objects.filter(user=user_profile.user).exists(), '/settings/#gear'),
            ('game_passports', 'Game Passports', GameProfile.objects.filter(user=user_profile.user).exists(), '/settings/#passports'),
            ('kyc', 'KYC Verification', user_profile.kyc_status == 'verified', '/settings/#kyc'),
        ]
        
        completed = [item for item in checklist_items if item[2]]
        percentage = int((len(completed) / len(checklist_items)) * 100)
        
        return {
            'percentage': percentage,
            'completed_items': [item[0] for item in completed],
            'missing_items': [item[0] for item in checklist_items if not item[2]],
            'checklist': [
                {
                    'key': item[0],
                    'label': item[1],
                    'completed': item[2],
                    'url': item[3]
                }
                for item in checklist_items
            ]
        }
```

---

### 4. Stream Settings Integration

**Status:** ⚠️ PARTIAL (social links exist, no live status)

**Exists:**
- Twitch/YouTube/Kick links in `SocialLink` model

**Missing:**
- Live status detection (complex, requires API integration)
- Last stream date/time
- Dedicated stream settings page

**Simplified Approach (Phase 8):**
- Display Twitch/YouTube/Kick links if they exist
- Show "Offline" with link to channel
- Skip live status detection (future phase)

---

## 📊 CONTEXT KEYS INVENTORY

### Currently Used in Template

```python
# Hero
profile_user                   # User object
profile                        # UserProfile object
user_profile                   # Alias for profile
user_teams                     # List of teams
follower_count                 # Int
following_count                # Int
user_stats.total_wins          # Int
identity_ctx.country_name      # String
identity_ctx.country_flag_url  # String
relationship_ctx.show_edit_button     # Bool (owner check)
relationship_ctx.can_follow           # Bool
relationship_ctx.is_following         # Bool
relationship_ctx.follow_requested     # Bool
relationship_ctx.can_recruit          # Bool
relationship_ctx.is_private_account   # Bool
follow_url                     # URL (not wired)
unfollow_url                   # URL (not wired)
settings_url                   # URL
preferred_contact.href         # URL (contact method)
preferred_contact.icon         # Icon class

# Left Sidebar
is_owner                       # Bool (alias for is_own_profile)
permissions.can_view_social_links   # Bool
social_links                   # QuerySet
social_links_map               # Dict {platform: SocialLink}
social_links_renderable        # List of dicts
discord_handle                 # String
discord_url                    # String
hardware_gears                 # QuerySet
wallet_balance                 # Int

# Right Sidebar
# (Live section has no real data)
user_teams                     # List of teams (same as hero)

# Overview Tab
stats_ctx.kd_ratio             # Float
stats_ctx.total_kills          # Int
stats_ctx.total_deaths         # Int
stats_ctx.win_rate             # Int
stats_ctx.total_wins           # Int
stats_ctx.total_matches        # Int
stats_ctx.tournaments_won      # Int
stats_ctx.tournaments_played   # Int
pinned_passports               # QuerySet
unpinned_passports             # QuerySet
permissions.can_view_game_passports  # Bool
```

### Missing Context Keys (Need to Add)

```python
# Phase 8 additions
completion_data = {
    'percentage': 85,
    'checklist': [...],
    'missing_items': [...]
}
stream_data = {
    'twitch_url': ...,
    'youtube_url': ...,
    'kick_url': ...,
    'is_live': False,  # Future
    'last_stream': None  # Future
}
career_items = [...]  # Top 2 teams/experiences
can_recruit = True/False  # Proper logic
```

---

## 🛠️ RECOMMENDED IMPLEMENTATION PLAN

### Priority Order

**Phase 8.1: Follow System (CRITICAL)**
1. Create follow/unfollow API endpoints
2. Add AJAX handlers in template
3. Update counts without page refresh
4. Enforce privacy rules for counts/lists
5. Handle private account follow requests

**Phase 8.2: Recruit Widget**
1. Define recruit eligibility logic (Team Owner/Manager check)
2. Add deep link to Career tab (`?tab=career` or `#career`)
3. Show recruit button in hero and affiliations widget
4. Wire to Career tab scroll/focus logic

**Phase 8.3: Profile Status Widget**
1. Create `SettingsCompletionService`
2. Calculate real completion percentage
3. Generate checklist with CTA links
4. Make widget owner-only
5. Link "Complete Now" to Settings sections

**Phase 8.4: Connect Widget**
1. Change privacy default to public (or remove check)
2. Keep existing UI (already good)

**Phase 8.5: Gear Widget**
1. Polish spacing and typography
2. Improve empty state design
3. Add hover effects

**Phase 8.6: Live Section**
1. Wire to Twitch/YouTube/Kick links from SocialLink
2. Show "Offline" with channel link
3. Skip live status detection (future phase)
4. Respect privacy (owner always sees, visitors if social links public)

**Phase 8.7: Overview Widgets**
1. Wire Career widget to real team data (limit to 2)
2. Add "View all" link to Career tab
3. Limit Game Passports widget to 2 items
4. Add "View all" link to Career tab

---

## ✅ ACCEPTANCE CRITERIA

### Hero Section
- [ ] Visitor can follow/unfollow without page refresh
- [ ] Follower/following counts update instantly
- [ ] Privacy rules enforced (counts visibility based on settings)
- [ ] Recruit button only visible to Team Owner/Manager
- [ ] Recruit button links to Career tab (deep link)
- [ ] Follow request system works for private accounts

### Left Sidebar
- [ ] Profile Status widget shows real completion percentage
- [ ] Profile Status checklist links to correct Settings sections
- [ ] Profile Status widget only visible to owner
- [ ] Connect widget visible to everyone (public)
- [ ] Gear widget has polished UI (spacing, empty state)

### Right Sidebar
- [ ] Live section shows Twitch/YouTube/Kick links if they exist
- [ ] Live section shows "Offline" state when not streaming
- [ ] Live section respects privacy (owner always sees, visitors if social links public)

### Overview Tab
- [ ] Career widget shows 2 most recent teams
- [ ] Career widget links to Career tab
- [ ] Game Passports widget shows 2 passports
- [ ] Game Passports widget links to Career tab

### Privacy Enforcement
- [ ] Followers/following counts respect `show_followers_count`/`show_following_count`
- [ ] Followers/following lists respect `show_followers_list`/`show_following_list`
- [ ] Private accounts require follow approval
- [ ] Stream links respect social links privacy

---

## 🚨 CRITICAL NOTES

1. **NO GLOBAL REFACTORS** — Keep changes scoped to hero, sidebars, overview
2. **Preserve Design Language** — Glass panels, neon accents, existing layout
3. **No v1/v2 files** — Use meaningful default names, delete replaced code
4. **Security First** — Owner-only widgets must be enforced server-side
5. **Privacy Compliance** — Instagram-like rules for followers/following
6. **Vanilla JS Only** — No frameworks, keep it simple

---

## 📝 NEXT STEPS

After audit approval:
1. Create follow system API endpoints
2. Implement recruit eligibility service
3. Build settings completion calculator
4. Wire live section to social links
5. Update Overview widgets with real data
6. Write implementation report

**Estimated Effort:** 3-4 hours (scoped changes only)

---

**Audit Complete** ✅  
Ready for implementation after review and approval.
