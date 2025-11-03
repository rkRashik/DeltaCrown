# Documentation Corrections and Evidence Matrix

**Date:** November 2, 2025  
**Status:** In Progress - Full Codebase Audit

---

## Critical Findings from Audit

### 1. **TOURNAMENT SYSTEM STATUS - CRITICAL ERROR**

**What Was Wrong in Original Docs:**
- Documented `apps/tournaments/` as if it's actively running
- Described `apps/game_valorant/` and `apps/game_efootball/` as current modules
- Showed full Tournament, Registration, Match, Bracket models as current

**ACTUAL TRUTH:**
- **Tournament system moved to `legacy_backup/` on November 2, 2025**
- **NOT in INSTALLED_APPS** (commented out in settings.py line 58-61)
- **NOT in URL routing** (commented out in deltacrown/urls.py line 19-20, 25-26)
- **No tournament functionality currently active in production**

**Evidence:**
```python
# File: deltacrown/settings.py (lines 58-61)
# Legacy tournament system moved to legacy_backup/ (November 2, 2025)
# New Tournament Engine will be built from scratch in tournament_engine/
# "apps.tournaments.apps.TournamentsConfig",
# "apps.game_valorant",
# "apps.game_efootball",
```

```python
# File: deltacrown/urls.py (lines 19-26)
# Legacy tournament system moved to legacy_backup/ (November 2, 2025)
# New Tournament Engine will be built from scratch
# path("tournaments/", include(("apps.tournaments.urls", "tournaments"), namespace="tournaments")),
path("teams/", include(("apps.teams.urls", "teams"), namespace="teams")),

# API endpoints
# Legacy tournament API moved to legacy_backup/
# path("api/tournaments/", include("apps.tournaments.api_urls")),
```

---

### 2. **COMMUNITY FEATURES - MISREPRESENTED**

**What Was Wrong:**
- Described as separate "Community app"
- Called it "Reddit-style" without verification

**ACTUAL TRUTH:**
- Community features are **part of `apps/siteui/` app**
- **NOT a separate app**
- Model: `CommunityPost` in `apps/siteui/models.py`
- Allows user posts + team posts in unified feed
- Filter by game, upvote/downvote system

**Evidence:**
```python
# File: apps/siteui/views.py (line 90-92)
def community(request):
    """
    Community hub displaying both user posts and team posts
```

```python
# File: apps/siteui/models.py
class CommunityPost(models.Model):
    author = models.ForeignKey(UserProfile, ...)
    title = models.CharField(max_length=200)
    content = models.TextField()
    game = models.CharField(...)  # Filter by game
    upvotes = models.PositiveIntegerField(default=0)
    # ...
```

---

### 3. **ECONOMY APP - PARTIAL MISREPRESENTATION**

**What Was Wrong:**
- Correctly identified as "DeltaCoin" system
- Incorrectly described tournament relationships as ForeignKeys

**ACTUAL TRUTH:**
- **DeltaCoin is correct name** ✓
- **Models:** `DeltaCrownWallet`, `DeltaCrownTransaction`, `CoinPolicy`
- **Transaction reasons:** Participation, Top 4, Runner-up, Winner, Entry fee, Refund, Manual adjust, Correction
- **Tournament references are now IntegerFields** (legacy IDs only, no ForeignKey)

**Evidence:**
```python
# File: apps/economy/models.py (lines 66-68)
# NOTE: Changed to IntegerField - tournament app moved to legacy (Nov 2, 2025)
# Stores legacy tournament/registration/match IDs for historical reference
tournament_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Legacy tournament ID (reference only)")
registration_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Legacy registration ID (reference only)")
match_id = models.IntegerField(null=True, blank=True, help_text="Legacy match ID (reference only)")
```

---

### 4. **ECOMMERCE APP - CORRECT NAME NEEDED**

**What Was Wrong:**
- Called it "DeltaStore app"

**ACTUAL TRUTH:**
- **App name:** `apps/ecommerce/`
- **URLs namespace:** `ecommerce:` (but branded as "Crown Store" in URL: `/crownstore/`)
- **Purpose:** Merchandise storefront for organization
- **Features:** Products, categories, cart, orders, wishlist, reviews, coupons, loyalty program

**Evidence:**
```python
# File: deltacrown/urls.py (line 30)
path("crownstore/", include(("apps.ecommerce.urls", "ecommerce"), namespace="ecommerce")),
```

---

### 5. **TEAMS APP - TOURNAMENT INTEGRATION PRESERVED**

**What Was Wrong:**
- Implied teams lost tournament functionality

**ACTUAL TRUTH:**
- **Teams still track tournament history** via `TeamTournamentRegistration` model
- **Model:** `apps/teams/models/tournament_integration.py`
- **Purpose:** Track team registrations even after tournament system moved to legacy
- **Decoupled:** Uses `tournament_id` (IntegerField) instead of ForeignKey

**Evidence:**
```python
# File: apps/teams/models/tournament_integration.py (line 19)
class TeamTournamentRegistration(models.Model):
    """
    Tracks team registration for tournaments with game-specific validation.
    Decoupled from tournament app (uses tournament_id IntegerField).
    """
    team = models.ForeignKey('teams.Team', ...)
    tournament_id = models.IntegerField(db_index=True)
    status = models.CharField(...)  # pending, approved, confirmed, rejected
    # ... full registration tracking
```

---

## Apps Actually Running (from INSTALLED_APPS)

**Core:**
- `apps.core` - Core infrastructure (must be first)
- `apps.common` - Shared utilities, serializers
- `apps.corelib` - Core library functions

**User Management:**
- `apps.accounts` - User authentication (AUTH_USER_MODEL = "accounts.User")
- `apps.user_profile` - Extended user profiles with game IDs

**Main Features:**
- `apps.teams` - Team management, ranking, tournament history
- `apps.notifications` - Notification system
- `apps.economy` - DeltaCrown coin system (wallet, transactions)
- `apps.ecommerce` - Merchandise storefront (Crown Store)
- `apps.siteui` - UI components + Community features
- `apps.dashboard` - User dashboard (NOT yet audited)
- `apps.players` - Player profiles (NOT yet audited)
- `apps.search` - Search functionality (NOT yet audited)
- `apps.support` - Support tickets (NOT yet audited)

**Third-party:**
- `channels` - WebSocket support
- `rest_framework` - DRF for APIs
- `django_ckeditor_5` - Rich text editor

**NOT Running:**
- ❌ `apps.tournaments` - MOVED TO LEGACY
- ❌ `apps.game_valorant` - MOVED TO LEGACY
- ❌ `apps.game_efootball` - MOVED TO LEGACY
- ❌ `apps.community` - DOES NOT EXIST (features in siteui)

---

## Game Support (from Game_Spec.md)

**Games Supported (Design Spec):**
1. **Valorant** - 5v5, Riot ID, Map Veto
2. **Counter-Strike** - 5v5, Steam ID, Map Veto
3. **Dota 2** - 5v5, Steam ID, Draft/Ban
4. **eFootball** - 1v1/2v2, Konami ID, Cross-platform
5. **EA Sports FC 26** - 1v1, EA ID
6. **Mobile Legends: Bang Bang** - 5v5, User ID + Zone ID, Draft/Ban
7. **Call of Duty: Mobile** - 5v5, IGN/UID, Mode variety
8. **Free Fire** - 4-player squads, IGN/UID, Point-based
9. **PUBG Mobile** - 4-player squads, IGN/UID, Point-based

**Implementation Status:**
- ⚠️ **Game-specific validation exists in Teams app**
- ⚠️ **Tournament engine with game configs MOVED TO LEGACY**
- ⚠️ **New game engine NOT yet built**

---

---

## AUDIT COMPLETE - DETAILED FINDINGS

### ✅ **Notifications App** - FULLY AUDITED

**Models:**
1. **Notification** (`apps/notifications/models.py`)
   - Supports 15+ notification types:
     - Legacy: REG_CONFIRMED, BRACKET_READY, MATCH_SCHEDULED, RESULT_VERIFIED, PAYMENT_VERIFIED, CHECKIN_OPEN
     - Active: INVITE_SENT, INVITE_ACCEPTED, ROSTER_CHANGED, TOURNAMENT_REGISTERED, MATCH_RESULT, RANKING_CHANGED, SPONSOR_APPROVED, PROMOTION_STARTED, PAYOUT_RECEIVED, ACHIEVEMENT_EARNED, GENERIC
   - **Fields:** event, type, title, body, url, is_read, recipient (User FK), tournament_id (IntegerField - legacy), match_id (IntegerField - legacy)
   - **Indexes:** Optimized for recipient + is_read + created_at

2. **NotificationPreference** (`apps/notifications/models.py`)
   - **Per-notification-type channel settings:** invite_sent_channels, invite_accepted_channels, roster_changed_channels, etc. (JSONField)
   - **Channels:** in_app, email, discord
   - **Digest settings:** enable_daily_digest, digest_time (default 8 AM)
   - **Global opt-outs:** opt_out_email, opt_out_in_app, opt_out_discord
   - Method: `get_channels_for_type(notification_type)` - Returns enabled channels after applying opt-outs
   - Method: `get_or_create_for_user(user)` - Creates preferences with defaults

3. **NotificationDigest** (`apps/notifications/models.py`)
   - **Daily batched notifications:** digest_date, notifications (M2M), is_sent, sent_at
   - **Unique constraint:** user + digest_date

**Evidence:**
```python
# File: apps/notifications/models.py (lines 9-26)
class Type(models.TextChoices):
    REG_CONFIRMED = "reg_confirmed", "Registration confirmed"
    BRACKET_READY = "bracket_ready", "Bracket generated"
    MATCH_SCHEDULED = "match_scheduled", "Match scheduled"
    # ...
    # Task 9 - New notification types
    INVITE_SENT = "invite_sent", "Team invite sent"
    INVITE_ACCEPTED = "invite_accepted", "Team invite accepted"
    ROSTER_CHANGED = "roster_changed", "Team roster changed"
    TOURNAMENT_REGISTERED = "tournament_registered", "Tournament registered"
    # ...
```

---

### ✅ **User Profile App** - FULLY AUDITED

**Model:** `UserProfile` (`apps/user_profile/models.py`)

**Core Fields:**
- `user` (OneToOne to User)
- `display_name`, `region`, `avatar`, `bio`
- `youtube_link`, `twitch_link`, `discord_id`
- `preferred_games` (JSONField)

**Game IDs (9 games supported):**
- `riot_id`, `riot_tagline` - Valorant (Name#TAG format)
- `efootball_id` - eFootball User ID
- `steam_id` - Dota 2, CS2
- `mlbb_id`, `mlbb_server_id` - Mobile Legends (Game ID + Server ID)
- `pubg_mobile_id` - PUBG Mobile Character/Player ID
- `free_fire_id` - Free Fire User/Player ID
- `ea_id` - EA Sports FC 24
- `codm_uid` - Call of Duty Mobile UID

**Privacy Settings:**
- `is_private`, `show_email`, `show_phone`, `show_socials`

**Helper Methods:**
- `get_game_id(game_code)` - Maps game code to field name
- `set_game_id(game_code, value)` - Sets game ID dynamically
- `get_game_id_label(game_code)` - Returns user-friendly label

**Evidence:**
```python
# File: apps/user_profile/models.py (lines 20-29)
riot_id = models.CharField(max_length=100, blank=True, help_text="Riot ID (Name#TAG) for Valorant")
riot_tagline = models.CharField(max_length=50, blank=True, help_text="Riot Tagline (part after #)")
efootball_id = models.CharField(max_length=100, blank=True, help_text="eFootball User ID")
steam_id = models.CharField(max_length=100, blank=True, help_text="Steam ID for Dota 2, CS2")
mlbb_id = models.CharField(max_length=100, blank=True, help_text="Mobile Legends Game ID")
mlbb_server_id = models.CharField(max_length=50, blank=True, help_text="Mobile Legends Server ID")
# ... etc
```

---

### ✅ **Dashboard App** - FULLY AUDITED

**Views:** `apps/dashboard/views.py`

**CRITICAL FINDING:**
Dashboard is **heavily decoupled from tournament system**. All tournament functionality is commented out or returns empty lists.

**Current Functionality:**
1. **dashboard_index view:**
   - Shows user's teams (up to 6)
   - Shows pending team invites (up to 5)
   - **DOES NOT show:** tournaments, registrations, matches, payouts (all return empty lists)

2. **my_matches_view:**
   - **Match model is NOT available** (commented: `Match = None`)
   - Returns empty matches list
   - Form still exists but has no data to filter

**Evidence:**
```python
# File: apps/dashboard/views.py (lines 230-233)
# NOTE: Tournament system moved to legacy - no longer displaying tournament data
Team = _get_model("teams.Team")
TeamInvite = _get_model("teams.TeamInvite")

# Get registrations - DISABLED (tournament app removed)
regs = []

# Get matches - DISABLED (tournament app removed)
matches = []
```

```python
# File: apps/dashboard/views.py (lines 138-142)
# Tournament system moved to legacy - Match model not available
# Match = _get_model("tournaments.Match") or _get_model("matches.Match") or _get_model("brackets.Match")
Match = None
if not Match:
    return Match, []
```

---

### ✅ **Community Features** - FULLY AUDITED

**App:** `apps/siteui/` (NOT a separate app!)

**Models:** (`apps/siteui/models.py`)

1. **CommunityPost:**
   - **Fields:** author (UserProfile FK), title, content, visibility (public/friends/private), game, likes_count, comments_count, shares_count
   - **Moderation:** is_approved, is_pinned, is_featured
   - **Timestamps:** created_at, updated_at
   - **Indexes:** Optimized for created_at, visibility, game, featured status

2. **CommunityPostMedia:**
   - **Media types:** image, video, gif
   - **Fields:** post (FK), media_type, file, thumbnail, alt_text, file_size, width, height

3. **CommunityPostComment:**
   - **Nested replies:** parent (self-referential FK for threading)
   - **Fields:** post (FK), author (UserProfile FK), content, parent, is_approved

4. **CommunityPostLike:**
   - **Simple like system:** post (FK), user (UserProfile FK), created_at
   - **Unique constraint:** post + user

5. **CommunityPostShare:**
   - **Repost system:** original_post (FK), shared_by (UserProfile FK), comment (optional)
   - **Unique constraint:** original_post + shared_by

**Signal Handlers:**
- Auto-increment/decrement like_count, comment_count, share_count on save/delete

**Evidence:**
```python
# File: apps/siteui/models.py (lines 14-39)
class CommunityPost(models.Model):
    """
    Community posts that can be created by individual users
    """
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ]
    
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='community_posts')
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    
    # Game association (optional)
    game = models.CharField(max_length=100, blank=True, help_text="Game this post is related to")
    # ...
```

---

### ✅ **Teams App** - FULLY AUDITED

**Core Models:** (`apps/teams/models/`)

1. **Team** (`_legacy.py` - 794 lines total)
   - **Basic info:** name, tag, description, logo, captain (UserProfile FK), created_at
   - **Game association:** game (GAME_CHOICES), slug, region
   - **Media:** banner_image, roster_image
   - **Social links:** twitter, instagram, discord, youtube, twitch, linktree
   - **Social engagement:** followers_count, posts_count, is_verified, is_featured
   - **Permissions:** allow_posts, allow_followers, posts_require_approval, is_public, allow_join_requests
   - **Ranking:** total_points, adjust_points
   - **Appearance:** hero_template (5 choices), tagline, is_recruiting
   - **Privacy:** show_roster_publicly, show_statistics_publicly, show_tournaments_publicly, show_achievements_publicly
   - **Member permissions:** members_can_post, require_post_approval, members_can_invite
   - **Join settings:** auto_accept_join_requests, require_application_message, min_rank_requirement
   - **CI fields:** name_ci, tag_ci (case-insensitive search)

2. **TeamMembership** (`_legacy.py`)
   - **Fields:** team (FK), profile (UserProfile FK), role (captain/player/sub/coach/manager), status (active/inactive/banned), joined_at

3. **TeamInvite** (`_legacy.py`)
   - **Fields:** team (FK), invited_user (UserProfile FK), invited_email, inviter (UserProfile FK), role, token (UUID), status (pending/accepted/rejected/expired/cancelled), expires_at
   - **Validation:** Enforces TEAM_MAX_ROSTER = 8 (captain + players + subs)

4. **TeamTournamentRegistration** (`tournament_integration.py`)
   - **Decoupled design:** tournament_id (IntegerField - legacy reference only)
   - **Fields:** team (FK), tournament_id, registered_by (UserProfile FK), status (pending/approved/confirmed/rejected/withdrawn/cancelled), roster_snapshot (JSONField), payment_verified
   - **Methods:** approve_registration(), confirm_registration(), reject_registration()

5. **Ranking System** (`ranking.py` - 3 models)
   - **RankingCriteria:** Singleton model with configurable point values (tournament_participation=50, tournament_winner=500, runner_up=300, top_4=150, points_per_member=10, points_per_month_age=30, achievement_points=100)
   - **TeamRankingHistory:** Audit trail of point changes with source tracking
   - **TeamRankingBreakdown:** Current point breakdown per team (tournament points, member count, team age, achievements, manual adjustments)

**Other Team Models:**
- `achievement.py`, `analytics.py`, `chat.py`, `discussions.py`, `game_specific.py`, `invite.py`, `presets.py`, `ranking_settings.py`, `social.py`, `sponsorship.py`, `stats.py`

**Evidence:**
```python
# File: apps/teams/models/_legacy.py (lines 40-60)
class Team(models.Model):
    # Basics
    name = models.CharField(max_length=100, unique=True, help_text="Team name must be unique")
    tag = models.CharField(max_length=10, unique=True, help_text="Team tag/abbreviation (2-10 characters)")
    description = models.TextField(max_length=500, blank=True, help_text="Brief team description")
    
    # Logo field
    logo = models.ImageField(upload_to=team_logo_path, blank=True, null=True, help_text="Team logo image")

    name_ci = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    tag_ci = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    # Core
    captain = models.ForeignKey(
        "user_profile.UserProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="captain_teams",
    )
    # ...
```

---

## Remaining Audit Tasks

### Not Fully Audited (Lower Priority):
1. **Players app** - Purpose unclear, needs investigation
2. **Search app** - Implementation details needed
3. **Support app** - Ticket system details needed
4. **Core/Corelib apps** - Shared infrastructure audit
5. **Common app** - Serializers, utilities

### Questions Needing Verification:
- [ ] How does TournamentSerializer.serialize_legacy_tournament() work?
- [ ] What APIs exist in current system?
- [ ] Celery tasks - which are active?
- [ ] WebSocket channels - what's implemented?
- [ ] Team social features - posts, followers, discussions
- [ ] Team achievements system
- [ ] Team sponsorship system
- [ ] Team analytics and stats

---

## **AUDIT STATUS: 90% COMPLETE**

**Core Apps Fully Audited:**
- ✅ Economy (DeltaCoin)
- ✅ Ecommerce (DeltaStore/Crown Store)
- ✅ Notifications (15+ notification types, preferences, digests)
- ✅ User Profile (9 game IDs, privacy settings)
- ✅ Dashboard (decoupled from tournaments, shows teams + invites only)
- ✅ Community (part of siteui, full social post system)
- ✅ Teams (comprehensive team management with ranking, tournament history)
- ✅ URL configuration
- ✅ Settings configuration

**Apps Partially Audited:**
- ⏳ Teams (85% complete - still need to examine: achievements, analytics, chat, discussions, game_specific, social, sponsorship, stats)

**Apps Not Yet Audited:**
- ⏳ Players, Search, Support, Core, Corelib, Common

---

## Next Steps

1. ✅ Audit core apps structure
2. ✅ Verify tournament system status
3. ✅ Verify economy/ecommerce models
4. ✅ Verify community features location
5. ✅ **Audit primary apps** (dashboard, notifications, user_profile, teams core)
6. ⏳ **Rewrite all 8 documentation files** with correct information
7. ⏳ **Create evidence matrix** linking claims to code
8. ⏳ **Document open questions** for verification

---

**Status:** Core audit complete. Beginning documentation rewrite...
