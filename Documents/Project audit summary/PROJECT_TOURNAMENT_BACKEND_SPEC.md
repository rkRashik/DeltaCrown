# Project Architecture – Core Apps & Tournament Domain (Backend Overview)

**Document Version:** 1.0  
**Last Updated:** November 20, 2025  
**Purpose:** Comprehensive backend architecture documentation for the DeltaCrown tournament platform  
**Scope:** Part 1 - Backend structure, core apps, and tournament domain models

---

## 1. Repo & App Map

### Django Configuration

**Framework:** Django 4.x+ with Python 3.10+  
**Database:** PostgreSQL 15+ (with JSONB, ArrayField, GIN indexes)  
**Authentication:** Custom User model (`accounts.User`) with JWT (SimpleJWT)  
**Real-Time:** Django Channels 3 with Redis backend  
**Task Queue:** Celery with Redis broker  
**API Framework:** Django REST Framework with JWT authentication

### INSTALLED_APPS Architecture

```python
# Core Infrastructure (MUST be first)
- django_prometheus      # Metrics collection (Phase 3 Prep)
- apps.core             # Core infrastructure
- apps.common           # Shared models (SoftDelete, Timestamped)
- apps.corelib          # Core library utilities

# Django Core
- django.contrib.admin
- django.contrib.auth
- django.contrib.contenttypes
- django.contrib.sessions
- django.contrib.messages
- django.contrib.staticfiles
- django.contrib.humanize
- django.contrib.sites
- django.contrib.sitemaps

# Third-Party
- rest_framework        # Django REST Framework
- django_ckeditor_5     # Rich text editor
- corsheaders          # CORS headers for frontend integration
- channels             # WebSocket support

# Authentication & User Management
- apps.accounts         # Custom User model, email verification
- apps.user_profile     # Extended profiles with game IDs

# Tournament System (NEW - November 2025)
- apps.tournaments      # Tournament engine (Phase 1-6 complete)
- apps.teams           # Team management, rankings, invitations

# Economy & Monetization (Phase 7)
- apps.economy         # DeltaCoin wallet system (Module 7.1 complete)
- apps.shop            # Shop items & purchases (Module 7.2 complete)

# Community & Engagement
- apps.notifications   # Notification system with webhooks (Phase 5 complete)
- apps.leaderboards    # Player rankings (Phase E/F complete)
- apps.spectator       # Live views (Phase G complete)
- apps.moderation      # Admin tools (Phase 8)

# Supporting Apps
- apps.ecommerce       # E-commerce functionality
- apps.siteui          # Site-wide UI components
- apps.dashboard       # User dashboards
- apps.players         # Player profiles
- apps.search          # Search functionality
- apps.support         # Help & support pages
```

### URL Routing Structure

**Main URL Configuration:** `deltacrown/urls.py`

```
Root Routes:
├── /                           → apps.siteui (homepage)
├── /admin/                     → Django Admin
├── /account/                   → apps.accounts (login, signup, logout)
├── /healthz/                   → Health check endpoint
├── /readiness/                 → Readiness check (DB + Redis validation)
├── /metrics/                   → Prometheus metrics

API Routes (JWT Required):
├── /api/token/                 → JWT token obtain
├── /api/token/refresh/         → JWT token refresh
├── /api/token/verify/          → JWT token verify
├── /api/tournaments/           → Tournament REST API (apps.tournaments.api.urls)
└── /api/teams/                 → Team Management API (apps.teams.api.urls)

Frontend Routes (Django Templates):
├── /tournaments/               → Tournament pages (apps.tournaments.urls)
├── /teams/                     → Team pages (apps.teams.urls)
├── /spectator/                 → Spectator live views (apps.spectator.urls)
├── /user/                      → User profiles (apps.user_profile.urls)
├── /notifications/             → Notification center (apps.notifications.urls)
└── /crownstore/                → E-commerce shop (apps.ecommerce.urls)

WebSocket Routes (Django Channels):
├── ws://domain/ws/tournament/<slug>/bracket/   → TournamentBracketConsumer
├── ws://domain/ws/match/<id>/                  → MatchConsumer (real-time updates)
└── (Additional consumers in apps/tournaments/realtime/routing.py)
```

---

## 2. Core Apps Overview

### 2.1 apps.core
**Purpose:** Core infrastructure and foundational utilities  
**Wired In:**
- `INSTALLED_APPS`: First in list (critical for initialization order)
- No URL routes (backend infrastructure only)

**Key Features:**
- Base configuration management
- Shared utilities and helpers
- Application initialization hooks

---

### 2.2 apps.common
**Purpose:** Shared models and utilities used across all apps  
**Wired In:**
- `INSTALLED_APPS`: Early in list (dependency for other apps)
- Context processors for templates

**Key Models:**

#### SoftDeleteModel (Abstract Base)
```python
class SoftDeleteModel(models.Model):
    is_deleted = BooleanField(default=False)
    deleted_at = DateTimeField(null=True, blank=True)
    deleted_by = ForeignKey(User, null=True, on_delete=SET_NULL)
    
    objects = SoftDeleteManager()  # Filters out deleted by default
    all_objects = Manager()         # Includes deleted records
```

#### TimestampedModel (Abstract Base)
```python
class TimestampedModel(models.Model):
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Cross-App Integrations:**
- Template tags: `seo_tags`, `assets`, `dashboard_widgets`, `string_utils`
- Context processors: `ui_settings`, `game_assets_context`, `homepage_context`

---

### 2.3 apps.accounts
**Purpose:** Authentication, user management, email verification  
**Wired In:**
- `INSTALLED_APPS`: Listed as "apps.accounts"
- `AUTH_USER_MODEL = "accounts.User"`
- URLs: `/account/` namespace

**Key Models:**

#### User (Custom AbstractUser)
```python
class User(AbstractUser):
    email = EmailField(unique=True, max_length=255)
    is_verified = BooleanField(default=False)
    email_verified_at = DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    
    objects = UserManager()  # Enforces email requirement
```

**Key Methods:**
- `mark_email_verified()` - Sets verification flags and activates user

#### PendingSignup
```python
class PendingSignup(models.Model):
    email = EmailField(unique=True)
    username = CharField(unique=True, max_length=150)
    password_hash = CharField(max_length=255)
    created_at = DateTimeField(auto_now_add=True)
    
    def create_user() -> User:
        # Promotes to verified User (atomic transaction)
```

#### EmailOTP
```python
class EmailOTP(models.Model):
    class Purpose(TextChoices):
        SIGNUP = 'signup', 'Signup Verification'
    
    code = CharField(max_length=6)  # 6-digit OTP
    user = ForeignKey(User, null=True, on_delete=CASCADE)
    pending_signup = ForeignKey(PendingSignup, null=True, on_delete=CASCADE)
    purpose = CharField(max_length=20, choices=Purpose.choices)
    expires_at = DateTimeField()
    attempts = PositiveIntegerField(default=0)
    is_used = BooleanField(default=False)
    
    # Constraints: XOR between user_id and pending_signup_id
```

**Security Features:**
- Rate limiting: Max 3 OTPs per 2-minute window (raises `RequestThrottled`)
- Verification: Max 5 attempts, locks and deletes account on failure
- Cleanup: `prune_stale_unverified()` removes accounts older than 24 hours
- Constant-time comparison for OTP codes

**Cross-App Integrations:**
- Referenced by: tournaments (organizer FK), teams (captain FK), notifications (recipient FK)
- Signals: Connected to tournament/team creation events

---

### 2.4 apps.user_profile
**Purpose:** Extended user profiles with game IDs and social links  
**Wired In:**
- `INSTALLED_APPS`: Listed as "apps.user_profile"
- URLs: `/user/` namespace

**Key Models:**

#### UserProfile (OneToOne with User)
```python
class UserProfile(models.Model):
    user = OneToOneField(User, on_delete=CASCADE, related_name='profile')
    
    # Basic Info
    display_name = CharField(max_length=100, blank=True)
    region = CharField(max_length=2, choices=REGION_CHOICES)  # BD/SA/AS/EU/NA
    avatar = ImageField(upload_to='avatars/', null=True, blank=True)
    bio = TextField(max_length=500, blank=True)
    
    # Social Links
    youtube_link = URLField(blank=True)
    twitch_link = URLField(blank=True)
    discord_id = CharField(max_length=100, blank=True)
    
    # Game IDs (9 platforms)
    riot_id = CharField(max_length=50, blank=True)           # Valorant
    riot_tagline = CharField(max_length=50, blank=True)      # #TAG
    efootball_id = CharField(max_length=50, blank=True)      # eFootball
    steam_id = CharField(max_length=50, blank=True)          # Dota 2, CS2
    mlbb_id = CharField(max_length=50, blank=True)           # Mobile Legends
    mlbb_server_id = CharField(max_length=50, blank=True)    # ML server
    pubg_mobile_id = CharField(max_length=50, blank=True)    # PUBG Mobile
    free_fire_id = CharField(max_length=50, blank=True)      # Free Fire
    ea_id = CharField(max_length=50, blank=True)             # EA Sports FC 26
    codm_uid = CharField(max_length=50, blank=True)          # Call of Duty Mobile
    
    # Privacy Settings
    is_private = BooleanField(default=False)
    show_email = BooleanField(default=False)
    show_phone = BooleanField(default=False)
    show_socials = BooleanField(default=True)
    
    # Metadata
    preferred_games = JSONField(default=list)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Methods:**
- `get_game_id(game_code)` - Returns game ID for specified game
- `set_game_id(game_code, value)` - Sets game ID for specified game
- `get_game_id_label(game_code)` - Returns display label for game ID field

**Game Code Mappings:**
- `valorant` → riot_id
- `efootball` → efootball_id
- `dota2`, `cs2` → steam_id
- `mlbb` → mlbb_id
- `pubgm` → pubg_mobile_id
- `freefire` → free_fire_id
- `fc24` → ea_id
- `codm` → codm_uid

**Cross-App Integrations:**
- Referenced by: tournaments (registration data), teams (memberships), economy (wallet owner)

---

### 2.5 apps.teams
**Purpose:** Team management, rankings, memberships, and invitations  
**Wired In:**
- `INSTALLED_APPS`: Listed as "apps.teams"
- URLs: `/teams/` namespace
- API: `/api/teams/` (Phase 3, Module 3.3 complete)

**Key Models:**

#### Team (Core Model - 50+ fields)
```python
class Team(models.Model):
    # Basic Identity
    name = CharField(max_length=50, unique=True)  # Min 3, max 50 chars
    tag = CharField(max_length=10, unique=True)   # Min 2, max 10 chars (uppercase alphanumeric)
    slug = SlugField(max_length=60, unique=True)
    description = TextField(max_length=500, blank=True)
    
    # Leadership
    captain = ForeignKey(UserProfile, null=True, on_delete=SET_NULL, related_name='captained_teams')
    
    # Game & Region
    game = CharField(max_length=50, choices=GAME_CHOICES)
    primary_game = CharField(max_length=50, blank=True)
    region = CharField(max_length=50, blank=True)
    
    # Media
    logo = ImageField(upload_to='teams/logos/', null=True, blank=True)
    banner_image = ImageField(upload_to='teams/banners/', null=True, blank=True)
    roster_image = ImageField(upload_to='teams/rosters/', null=True, blank=True)
    
    # Social Links (6 platforms)
    twitter = URLField(blank=True)
    instagram = URLField(blank=True)
    discord = URLField(blank=True)
    youtube = URLField(blank=True)
    twitch = URLField(blank=True)
    linktree = URLField(blank=True)
    
    # Engagement Metrics
    followers_count = PositiveIntegerField(default=0)
    posts_count = PositiveIntegerField(default=0)
    is_verified = BooleanField(default=False)
    is_featured = BooleanField(default=False)
    
    # Settings & Privacy
    allow_posts = BooleanField(default=True)
    allow_followers = BooleanField(default=True)
    posts_require_approval = BooleanField(default=False)
    is_active = BooleanField(default=True)
    is_public = BooleanField(default=True)
    allow_join_requests = BooleanField(default=True)
    show_statistics = BooleanField(default=True)
    
    # Ranking System
    total_points = PositiveIntegerField(default=0, editable=False)  # Calculated from TeamRankingBreakdown
    adjust_points = IntegerField(default=0)  # Manual adjustment by admin
    
    # Template Customization
    hero_template = CharField(
        max_length=20,
        choices=[
            ('default', 'Default'),
            ('centered', 'Centered'),
            ('split', 'Split Screen'),
            ('minimal', 'Minimal'),
            ('championship', 'Championship')
        ],
        default='default'
    )
    tagline = CharField(max_length=100, blank=True)
    is_recruiting = BooleanField(default=False)
    
    # Privacy Controls
    show_roster_publicly = BooleanField(default=True)
    show_statistics_publicly = BooleanField(default=True)
    show_tournaments_publicly = BooleanField(default=True)
    show_achievements_publicly = BooleanField(default=True)
    hide_member_stats = BooleanField(default=False)
    hide_social_links = BooleanField(default=False)
    show_captain_only = BooleanField(default=False)
    
    # Permissions
    members_can_post = BooleanField(default=True)
    require_post_approval = BooleanField(default=False)
    members_can_invite = BooleanField(default=True)
    
    # Join Settings
    auto_accept_join_requests = BooleanField(default=False)
    require_application_message = BooleanField(default=True)
    min_rank_requirement = CharField(max_length=50, blank=True)
    
    # Audit Fields
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    # Case-insensitive search fields
    name_ci = CharField(max_length=50, editable=False, db_index=True)
    tag_ci = CharField(max_length=10, editable=False, db_index=True)
```

**Constraints:**
- Unique: `(game, slug)` combination
- Case-insensitive indexes: `name_ci`, `tag_ci`
- Tag validation: Uppercase alphanumeric only (A-Z, 0-9)

**Indexes:**
- `teams_leaderboard_idx`: `(-total_points, name)` for leaderboard queries
- `teams_game_leader_idx`: `(game, -total_points)` for per-game rankings
- `teams_recent_idx`: `(-created_at)` for recent teams

**Key Properties:**
- `members_count` - Count of active memberships
- `active_members` - QuerySet of active team members
- `can_accept_members` - Boolean check against `TEAM_MAX_ROSTER`
- `display_name` - Formatted name with tag: "TeamName (TAG)"
- `logo_url`, `banner_url` - Media URLs or None

**Key Methods:**
- `has_member(profile)` - Check if profile is an active member
- `ensure_captain_membership()` - Auto-creates OWNER membership for captain
- `is_captain(profile)` - Check if profile is the team captain
- `can_user_post(user_profile)` - Check posting permissions
- `get_follower_count()` - Follower count (if followers feature enabled)
- `is_followed_by(user_profile)` - Check if user follows team
- `get_recent_posts(limit=5)` - Recent published posts
- `get_activity_feed(limit=10)` - Recent public activity

**Validation:**
- Name: 3-50 characters, stripped whitespace
- Tag: 2-10 characters, uppercase, alphanumeric only
- Slug: Auto-generated from name (60 char limit)

#### TeamMembership
```python
class TeamMembership(models.Model):
    class Role(TextChoices):
        OWNER = "OWNER", "Team Owner"
        MANAGER = "MANAGER", "Manager"
        COACH = "COACH", "Coach"
        PLAYER = "PLAYER", "Player"
        SUBSTITUTE = "SUBSTITUTE", "Substitute"
        CAPTAIN = "CAPTAIN", "Captain (Legacy)"  # For migration support
    
    class Status(TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        SUSPENDED = "SUSPENDED", "Suspended"
    
    team = ForeignKey(Team, on_delete=CASCADE, related_name='memberships')
    profile = ForeignKey(UserProfile, on_delete=CASCADE, related_name='team_memberships')
    role = CharField(max_length=20, choices=Role.choices)
    status = CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    joined_at = DateTimeField(auto_now_add=True)
    left_at = DateTimeField(null=True, blank=True)
    
    # Permission cache (updated by update_permission_cache())
    can_manage_roster = BooleanField(default=False)
    can_edit_team = BooleanField(default=False)
    can_post = BooleanField(default=False)
```

**Constants:**
- `TEAM_MAX_ROSTER` - Maximum team size (value TBD, likely 10-15)

---

### 2.6 apps.teams (Ranking System)
**Purpose:** Configurable team ranking with audit trail  
**Models:** 3 models for comprehensive ranking management

#### RankingCriteria (Singleton Configuration)
```python
class RankingCriteria(models.Model):
    # Tournament Performance Points
    participation_points = PositiveIntegerField(default=50)
    winner_points = PositiveIntegerField(default=500)
    runner_up_points = PositiveIntegerField(default=300)
    top_4_points = PositiveIntegerField(default=150)
    
    # Team Composition Points
    points_per_member = PositiveIntegerField(default=10)
    points_per_month_age = PositiveIntegerField(default=30)
    achievement_points = PositiveIntegerField(default=100)
    
    # Singleton enforcement via save() override
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Methods:**
- `get_active_criteria()` (classmethod) - Returns singleton instance
- `get_point_values()` - Returns dict of all point values

#### TeamRankingHistory (Immutable Audit Log)
```python
class TeamRankingHistory(models.Model):
    class Source(TextChoices):
        TOURNAMENT_PARTICIPATION = 'tournament_participation'
        TOURNAMENT_WINNER = 'tournament_winner'
        TOURNAMENT_RUNNER_UP = 'tournament_runner_up'
        TOURNAMENT_TOP_4 = 'tournament_top_4'
        MEMBER_COUNT = 'member_count'
        TEAM_AGE = 'team_age'
        ACHIEVEMENT = 'achievement'
        MANUAL_ADJUSTMENT = 'manual_adjustment'
        RECALCULATION = 'recalculation'
    
    team = ForeignKey(Team, on_delete=CASCADE, related_name='ranking_history')
    source = CharField(max_length=50, choices=Source.choices)
    points_change = IntegerField()  # Can be negative
    points_before = IntegerField()
    points_after = IntegerField()
    reason = TextField()
    
    # Related Object References
    related_object_type = CharField(max_length=50, blank=True)  # 'Tournament', 'Achievement', etc.
    related_object_id = PositiveIntegerField(null=True, blank=True)
    
    # Admin Tracking
    admin_user = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)
    created_at = DateTimeField(auto_now_add=True)
```

**Validation:**
- `clean()` enforces: `points_before + points_change = points_after`

#### TeamRankingBreakdown (Current Point Breakdown)
```python
class TeamRankingBreakdown(models.Model):
    team = OneToOneField(Team, on_delete=CASCADE, related_name='ranking_breakdown')
    
    # Tournament Performance Components
    tournament_participation_points = PositiveIntegerField(default=0)
    tournament_winner_points = PositiveIntegerField(default=0)
    tournament_runner_up_points = PositiveIntegerField(default=0)
    tournament_top_4_points = PositiveIntegerField(default=0)
    
    # Team Composition Components
    member_count_points = PositiveIntegerField(default=0)
    team_age_points = PositiveIntegerField(default=0)
    achievement_points = PositiveIntegerField(default=0)
    
    # Adjustments
    manual_adjustment_points = IntegerField(default=0)
    
    # Calculated Totals
    calculated_total = PositiveIntegerField(default=0, editable=False)
    final_total = IntegerField(default=0, editable=False)
    
    last_calculated_at = DateTimeField(auto_now=True)
```

**Key Methods:**
- `calculate_total()` - Sums all auto-calculated points
- `get_breakdown_dict()` - Returns dict of all components
- `get_tournament_points_total()` - Sum of tournament-related points
- `get_team_composition_total()` - Sum of composition points
- `get_detailed_breakdown()` - Full breakdown with labels
- `get_recent_changes(limit=10)` - Recent history entries
- `to_frontend_dict()` - Formatted dict for API responses

**Auto-Calculation:**
- On save: Triggers calculation and updates `Team.total_points`
- Formula: `final_total = calculated_total + manual_adjustment_points`

**Cross-App Integrations:**
- Referenced by: tournaments (team registrations, fee waivers based on ranking)
- Signals: Tournament completion triggers ranking point updates
- API: Module 4.2 (Ranking & Seeding Integration) uses for tournament seeding

---

### 2.7 apps.economy
**Purpose:** DeltaCoin wallet system with immutable transaction ledger  
**Wired In:**
- `INSTALLED_APPS`: Listed as "apps.economy"
- URLs: Included in root urlconf
- Status: Module 7.1 complete (100% tests passing)

**Key Models:**

#### DeltaCrownWallet (One per UserProfile)
```python
class DeltaCrownWallet(models.Model):
    profile = OneToOneField(UserProfile, on_delete=CASCADE, related_name='deltacoin_wallet')
    cached_balance = IntegerField(default=0, help_text="Derived from transaction ledger")
    allow_overdraft = BooleanField(default=False, help_text="Allow negative balance")
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Methods:**
- `recalc_and_save()` - Atomic recalculation with SELECT FOR UPDATE row lock
- Returns corrected balance after recalculation
- Invariant: `cached_balance = SUM(transactions.amount)`

#### DeltaCrownTransaction (Immutable Ledger)
```python
class DeltaCrownTransaction(models.Model):
    class Reason(TextChoices):
        PARTICIPATION = 'participation', 'Tournament Participation'
        TOP4 = 'top4', 'Tournament Top 4'
        RUNNER_UP = 'runner_up', 'Tournament Runner Up'
        WINNER = 'winner', 'Tournament Winner'
        ENTRY_FEE_DEBIT = 'entry_fee_debit', 'Tournament Entry Fee'
        REFUND = 'refund', 'Refund'
        MANUAL_ADJUST = 'manual_adjust', 'Manual Adjustment'
        CORRECTION = 'correction', 'Balance Correction'
        P2P_TRANSFER = 'p2p_transfer', 'Peer-to-Peer Transfer'
    
    wallet = ForeignKey(DeltaCrownWallet, on_delete=PROTECT, related_name='transactions')
    amount = IntegerField(help_text="Positive = credit, negative = debit")
    reason = CharField(max_length=50, choices=Reason.choices)
    
    # Context References (IntegerField for legacy compatibility)
    tournament_id = IntegerField(null=True, blank=True, db_index=True)
    registration_id = IntegerField(null=True, blank=True, db_index=True)
    match_id = IntegerField(null=True, blank=True, db_index=True)
    
    note = TextField(blank=True)
    created_by = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)
    
    # Idempotency Support
    idempotency_key = CharField(max_length=255, unique=True, null=True, blank=True)
    
    created_at = DateTimeField(auto_now_add=True, db_index=True)
```

**Constraints:**
- CHECK: `amount != 0` (no zero-amount transactions)
- UNIQUE: `idempotency_key` (prevents duplicate transactions)
- Immutability: `save()` override raises exception if modifying existing transaction

**Indexes:**
- `wallet` (foreign key)
- `reason` (for filtering by transaction type)
- `created_at` (for time-based queries)
- `tournament_id`, `registration_id`, `match_id` (for context lookups)

**Idempotency:**
- Services MUST set `idempotency_key` for all transactions
- Duplicate key raises `IntegrityError` (caught by service layer)
- Prevents double-charging/double-crediting in concurrent scenarios

**Legacy Note:**
- Tournament FKs changed to IntegerField on November 2, 2025
- Legacy tournament system moved to `backup_legacy/`
- New tournament engine uses IntegerField references for flexibility

#### CoinPolicy (Per-Tournament Configuration)
```python
class CoinPolicy(models.Model):
    tournament_id = IntegerField(unique=True, null=True, blank=True, db_index=True)
    enabled = BooleanField(default=True)
    
    # Reward Amounts
    participation = PositiveIntegerField(default=5)
    top4 = PositiveIntegerField(default=25)
    runner_up = PositiveIntegerField(default=50)
    winner = PositiveIntegerField(default=100)
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Service Layer (Module 7.1):**
- `EconomyService.credit()` - Add coins to wallet
- `EconomyService.debit()` - Deduct coins from wallet (with overdraft check)
- `EconomyService.transfer()` - P2P transfer between wallets
- `EconomyService.get_balance()` - Current wallet balance
- `EconomyService.get_transaction_history()` - Paginated transaction list

**Cross-App Integrations:**
- Referenced by: tournaments (entry fees, prize distribution)
- Signals: Tournament completion triggers prize payouts (Module 5.2)
- API: `/api/economy/` endpoints for wallet operations

---

### 2.8 apps.shop
**Purpose:** Shop items and purchase authorization (two-phase commit)  
**Wired In:**
- `INSTALLED_APPS`: Listed as "apps.shop"
- Status: Module 7.2 complete (100% tests passing)

**Key Models:**

#### ShopItem (Catalog)
```python
class ShopItem(models.Model):
    name = CharField(max_length=200)
    description = TextField()
    price = PositiveIntegerField(help_text="Price in DeltaCoins")
    image = ImageField(upload_to='shop/items/', null=True, blank=True)
    stock = PositiveIntegerField(default=0, help_text="0 = unlimited")
    is_active = BooleanField(default=True)
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

#### ReservationHold (Two-Phase Commit State Machine)
```python
class ReservationHold(models.Model):
    class State(TextChoices):
        AUTHORIZED = 'authorized', 'Authorized'
        CAPTURED = 'captured', 'Captured'
        RELEASED = 'released', 'Released'
        EXPIRED = 'expired', 'Expired'
    
    wallet = ForeignKey(DeltaCrownWallet, on_delete=PROTECT, related_name='holds')
    amount = PositiveIntegerField(help_text="Held amount (positive)")
    state = CharField(max_length=20, choices=State.choices, default=State.AUTHORIZED)
    
    # Idempotency
    idempotency_key = CharField(max_length=255, unique=True)
    
    # Lifecycle Tracking
    authorized_at = DateTimeField(auto_now_add=True)
    captured_at = DateTimeField(null=True, blank=True)
    released_at = DateTimeField(null=True, blank=True)
    expires_at = DateTimeField(help_text="Auto-release if not captured")
    
    # Transaction References
    debit_transaction = ForeignKey(DeltaCrownTransaction, null=True, on_delete=SET_NULL, related_name='+')
    
    # Metadata (JSONB for extensibility)
    meta = JSONField(default=dict, help_text="Additional context (item_id, quantity, etc.)")
```

**State Machine:**
```
authorized → captured (purchase confirmed, transaction created)
authorized → released (purchase cancelled, hold removed)
authorized → expired (TTL exceeded, auto-released)
```

**Service Layer (Module 7.2):**
- `ShopService.authorize_spend()` - Reserve coins (two-phase commit phase 1)
- `ShopService.capture()` - Confirm purchase, create debit transaction (phase 2)
- `ShopService.release()` - Cancel purchase, remove hold
- `ShopService.refund()` - Process refund with cumulative tracking
- `ShopService.get_available_balance()` - Balance minus pending holds

**Features:**
- Idempotency: Duplicate `idempotency_key` returns existing hold
- Concurrency-safe: Lock ordering and retry logic
- Cumulative refunds: Tracks total refunded via `meta['refunds']`
- Automatic expiry: Background task releases expired holds (TTL configurable)

**Cross-App Integrations:**
- Economy: Integrates with DeltaCrownWallet and DeltaCrownTransaction
- Tournaments: Could be used for entry fee authorization (not yet implemented)

---

### 2.9 apps.notifications
**Purpose:** Multi-channel notification system with webhooks  
**Wired In:**
- `INSTALLED_APPS`: Listed as "apps.notifications"
- URLs: `/notifications/` namespace
- Context processors: `notification_counts`, `unread_notifications`
- Status: Phase 5, Module 5.5 complete (webhooks integrated)

**Key Models:**

#### Notification
```python
class Notification(models.Model):
    class Event(TextChoices):
        PAYMENT_VERIFIED = 'payment_verified'
        PAYMENT_REJECTED = 'payment_rejected'
        REGISTRATION_APPROVED = 'registration_approved'
        MATCH_STARTED = 'match_started'
        MATCH_RESULT = 'match_result'
        TOURNAMENT_COMPLETED = 'tournament_completed'
        # ... (20+ event types)
    
    recipient = ForeignKey(User, on_delete=CASCADE, related_name='notifications')
    event = CharField(max_length=50, choices=Event.choices)
    title = CharField(max_length=200)
    body = TextField()
    url = URLField(blank=True, help_text="Call-to-action link")
    
    # Related Objects
    tournament = ForeignKey(Tournament, null=True, on_delete=CASCADE)
    match = ForeignKey(Match, null=True, on_delete=CASCADE)
    
    # State
    is_read = BooleanField(default=False)
    read_at = DateTimeField(null=True, blank=True)
    
    created_at = DateTimeField(auto_now_add=True, db_index=True)
```

#### NotificationPreference
```python
class NotificationPreference(models.Model):
    user = OneToOneField(User, on_delete=CASCADE, related_name='notification_preferences')
    
    # Channel Preferences
    email_enabled = BooleanField(default=True)
    push_enabled = BooleanField(default=True)
    sms_enabled = BooleanField(default=False)
    
    # Event-Specific Preferences (JSONB)
    event_preferences = JSONField(default=dict)
    # Example: {'payment_verified': {'email': True, 'push': True}, ...}
```

#### NotificationDigest
```python
class NotificationDigest(models.Model):
    class Frequency(TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
    
    user = ForeignKey(User, on_delete=CASCADE, related_name='notification_digests')
    frequency = CharField(max_length=20, choices=Frequency.choices)
    last_sent_at = DateTimeField(null=True, blank=True)
    next_send_at = DateTimeField()
```

**Service Layer:**
- `NotificationService.notify()` - Create notification + send email
- `NotificationService.emit()` - Bulk notification dispatch
- `WebhookService.deliver()` - HTTP webhook delivery with retry

**Webhook Features (Module 5.5):**
- HMAC-SHA256 signature for authenticity
- Exponential backoff retry (0s, 2s, 4s)
- Feature flag: `NOTIFICATIONS_WEBHOOK_ENABLED` (default: False)
- PII-safe: IDs and counts only, no emails/usernames
- Failure isolation: Webhook errors don't break notifications

**Cross-App Integrations:**
- Signals: Connected to tournament/payment/match events
- Templates: Email templates in `templates/notifications/email/`
- Celery: Background email sending via `send_notification_email.delay()`

---

### 2.10 apps.leaderboards
**Purpose:** Player ranking system with seasonal and all-time boards  
**Wired In:**
- `INSTALLED_APPS`: Listed as "apps.leaderboards"
- Status: Phase E/F complete (service layer + ranking engine V2)

**Key Models:**

#### LeaderboardEntry
```python
class LeaderboardEntry(models.Model):
    class Scope(TextChoices):
        SEASONAL = 'seasonal', 'Seasonal'
        ALL_TIME = 'all_time', 'All-Time'
        GAME_SPECIFIC = 'game_specific', 'Game-Specific'
    
    profile = ForeignKey(UserProfile, on_delete=CASCADE, related_name='leaderboard_entries')
    scope = CharField(max_length=20, choices=Scope.choices)
    game = CharField(max_length=50, blank=True, help_text="For game-specific leaderboards")
    
    # Metrics
    rank = PositiveIntegerField()
    total_points = PositiveIntegerField(default=0)
    tournaments_played = PositiveIntegerField(default=0)
    tournaments_won = PositiveIntegerField(default=0)
    win_rate = DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    # Metadata
    last_tournament_at = DateTimeField(null=True, blank=True)
    updated_at = DateTimeField(auto_now=True)
```

#### LeaderboardSnapshot
```python
class LeaderboardSnapshot(models.Model):
    scope = CharField(max_length=20)
    game = CharField(max_length=50, blank=True)
    snapshot_data = JSONField(help_text="Top 100 entries with full metrics")
    captured_at = DateTimeField(auto_now_add=True, db_index=True)
```

**Service Layer:**
- `LeaderboardService.calculate_player_points()` - Calculate points from tournament results
- `LeaderboardService.update_leaderboard()` - Recalculate rankings
- `LeaderboardService.get_leaderboard()` - Retrieve leaderboard with pagination
- Redis caching with 5min-24h TTL based on volatility

**Celery Tasks:**
- `refresh_seasonal_leaderboard` - Hourly update
- `refresh_all_time_leaderboard` - Daily update
- `create_leaderboard_snapshot` - Weekly archival
- `prune_inactive_entries` - Monthly cleanup

**Cross-App Integrations:**
- Tournaments: Points calculated from TournamentResult model
- User Profile: Linked to UserProfile for player identification

---

### 2.11 apps.spectator
**Purpose:** Public read-only tournament and match viewing  
**Wired In:**
- `INSTALLED_APPS`: Listed as "apps.spectator"
- URLs: `/spectator/` namespace
- Status: Phase G complete (live views implemented)

**Purpose:** Spectator-optimized views separate from organizer/participant interfaces

**Key Views:**
- Tournament live view - Current matches and bracket state
- Match live view - Real-time score updates (WebSocket)
- Bracket visualization - Interactive bracket display
- Leaderboard view - Current tournament standings

**Features:**
- Read-only access (no authentication required for public tournaments)
- WebSocket subscriptions for live updates
- Optimized queries (select_related, prefetch_related)
- Mobile-responsive layouts

**Cross-App Integrations:**
- Tournaments: Reads Tournament, Match, Bracket models
- WebSocket: Connects to tournament/match consumer channels

---

### 2.12 apps.moderation
**Purpose:** Admin moderation tools, sanctions, audit logs, abuse reports  
**Wired In:**
- `INSTALLED_APPS`: Listed as "apps.moderation"
- Status: Phase 8 (in development)

**Key Models:**

#### ModerationSanction
```python
class ModerationSanction(models.Model):
    class SanctionType(TextChoices):
        WARNING = 'warning', 'Warning'
        MUTE = 'mute', 'Mute'
        BAN = 'ban', 'Ban'
        SUSPENSION = 'suspension', 'Suspension'
    
    user = ForeignKey(User, on_delete=CASCADE, related_name='sanctions')
    sanction_type = CharField(max_length=20, choices=SanctionType.choices)
    reason = TextField()
    duration_hours = PositiveIntegerField(null=True, blank=True, help_text="None = permanent")
    
    issued_by = ForeignKey(User, on_delete=SET_NULL, null=True, related_name='issued_sanctions')
    issued_at = DateTimeField(auto_now_add=True)
    expires_at = DateTimeField(null=True, blank=True)
    is_active = BooleanField(default=True)
```

#### ModerationAudit
```python
class ModerationAudit(models.Model):
    class Action(TextChoices):
        USER_BANNED = 'user_banned'
        USER_UNBANNED = 'user_unbanned'
        CONTENT_DELETED = 'content_deleted'
        REPORT_RESOLVED = 'report_resolved'
        # ... (15+ action types)
    
    action = CharField(max_length=50, choices=Action.choices)
    moderator = ForeignKey(User, on_delete=SET_NULL, null=True)
    target_user = ForeignKey(User, null=True, on_delete=SET_NULL, related_name='moderation_targets')
    
    # Context
    content_type = CharField(max_length=50, blank=True)
    content_id = PositiveIntegerField(null=True, blank=True)
    reason = TextField()
    
    created_at = DateTimeField(auto_now_add=True, db_index=True)
```

#### AbuseReport
```python
class AbuseReport(models.Model):
    class Status(TextChoices):
        PENDING = 'pending', 'Pending'
        INVESTIGATING = 'investigating', 'Under Investigation'
        RESOLVED = 'resolved', 'Resolved'
        DISMISSED = 'dismissed', 'Dismissed'
    
    class ReportType(TextChoices):
        SPAM = 'spam', 'Spam'
        HARASSMENT = 'harassment', 'Harassment'
        CHEATING = 'cheating', 'Cheating'
        INAPPROPRIATE = 'inappropriate', 'Inappropriate Content'
        OTHER = 'other', 'Other'
    
    reporter = ForeignKey(User, on_delete=CASCADE, related_name='reports_submitted')
    reported_user = ForeignKey(User, on_delete=CASCADE, related_name='reports_received')
    report_type = CharField(max_length=50, choices=ReportType.choices)
    description = TextField()
    status = CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Evidence
    evidence_urls = JSONField(default=list, help_text="Screenshot URLs, etc.")
    
    # Resolution
    reviewed_by = ForeignKey(User, null=True, on_delete=SET_NULL, related_name='reports_reviewed')
    reviewed_at = DateTimeField(null=True, blank=True)
    resolution_notes = TextField(blank=True)
    
    created_at = DateTimeField(auto_now_add=True, db_index=True)
```

**Cross-App Integrations:**
- Connects to all content models (posts, comments, matches, etc.)
- Integrated with user authentication (ban checks on login)

---

## 3. Tournament App – Models & Responsibilities

### Overview
**App:** `apps.tournaments`  
**Purpose:** Complete tournament engine for esports competitions  
**Status:** Phases 1-6 complete (70% of planned functionality)  
**Architecture:** Service layer pattern with REST API + WebSocket real-time updates

### URL Structure
```
Frontend Routes (/tournaments/):
├── / (list)                                    → TournamentListView
├── /<slug>/ (detail)                          → TournamentDetailView
├── /<slug>/register/                          → Registration form
├── /<slug>/bracket/                           → Bracket visualization
├── /<slug>/matches/<id>/                      → Match detail
├── /<slug>/results/                           → Tournament results
├── /<slug>/lobby/                             → Participant lobby
├── /my-tournaments/                           → Player dashboard
└── /organizer/<slug>/dashboard/               → Organizer console

API Routes (/api/tournaments/):
├── tournaments/                               → TournamentViewSet (CRUD)
├── registrations/                             → RegistrationViewSet
├── payments/                                  → PaymentViewSet
├── brackets/                                  → BracketViewSet
├── matches/                                   → MatchViewSet
├── results/                                   → ResultViewSet
├── certificates/                              → Certificate download/verify
├── analytics/                                 → Analytics endpoints
└── payouts/                                   → Prize payout endpoints

WebSocket Routes (/ws/):
├── tournament/<slug>/bracket/                 → TournamentBracketConsumer
└── match/<id>/                                → MatchConsumer
```

---

### 3.1 Core Tournament Models

#### Game (Game Configuration)
**File:** `apps/tournaments/models/tournament.py`  
**Purpose:** Define supported games and their tournament settings

```python
class Game(models.Model):
    name = CharField(max_length=100, unique=True)
    slug = SlugField(max_length=100, unique=True)
    
    # Team Configuration
    min_team_size = PositiveIntegerField(default=1)
    max_team_size = PositiveIntegerField(default=5)
    allow_substitutes = BooleanField(default=True)
    max_substitutes = PositiveIntegerField(default=2)
    
    # Result Types
    result_type = CharField(
        max_length=20,
        choices=[
            ('score', 'Score-Based'),
            ('win_loss', 'Win/Loss'),
            ('points', 'Points-Based'),
            ('placement', 'Placement-Based'),  # Battle Royale
        ],
        default='win_loss'
    )
    
    # Game-Specific Fields
    game_config = JSONField(
        default=dict,
        help_text="Game-specific settings (map pools, bans, etc.)"
    )
    
    # Profile ID Mapping
    profile_id_field = CharField(
        max_length=50,
        blank=True,
        help_text="UserProfile field for this game's ID (e.g., 'riot_id', 'steam_id')"
    )
    
    # Metadata
    icon = ImageField(upload_to='games/icons/', null=True, blank=True)
    is_active = BooleanField(default=True)
```

**Supported Games (9 platforms):**
1. Valorant (5v5, Riot ID: name#TAG, Map score)
2. Counter-Strike 2 (5v5, Steam ID: 17 digits, Map score)
3. Dota 2 (5v5, Steam ID, Draft/Ban validation)
4. eFootball (1v1, Konami ID: 9-12 digits)
5. EA Sports FC 26 (1v1, EA ID: 5-20 alphanumeric)
6. Mobile Legends (5v5, UID+Zone, Draft/Ban validation)
7. Call of Duty Mobile (5v5, IGN/UID)
8. Free Fire (4-squad BR, IGN/UID, Points: 1st=12, 2nd=9, 3rd=7...)
9. PUBG Mobile (4-squad BR, IGN/UID, Points: same as FF)

---

#### Tournament (Main Entity - 71+ fields)
**File:** `apps/tournaments/models/tournament.py`  
**Purpose:** Core tournament configuration and lifecycle management

```python
class Tournament(models.Model):
    class Status(TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        PUBLISHED = 'published', 'Published'
        REGISTRATION_OPEN = 'registration_open', 'Registration Open'
        REGISTRATION_CLOSED = 'registration_closed', 'Registration Closed'
        LIVE = 'live', 'Live'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        ARCHIVED = 'archived', 'Archived'
    
    class Format(TextChoices):
        SINGLE_ELIMINATION = 'single-elimination', 'Single Elimination'
        DOUBLE_ELIMINATION = 'double-elimination', 'Double Elimination'
        ROUND_ROBIN = 'round-robin', 'Round Robin'
        SWISS = 'swiss', 'Swiss System'
        GROUP_PLAYOFF = 'group-playoff', 'Group + Playoff'
    
    class ParticipationType(TextChoices):
        TEAM = 'team', 'Team-Based'
        SOLO = 'solo', 'Individual'
    
    # Identity
    name = CharField(max_length=200)
    slug = SlugField(max_length=200, unique=True)
    subtitle = CharField(max_length=300, blank=True)
    description = TextField()
    
    # Game & Organizer
    game = ForeignKey(Game, on_delete=PROTECT, related_name='tournaments')
    organizer = ForeignKey(User, on_delete=PROTECT, related_name='organized_tournaments')
    is_official = BooleanField(default=False, help_text="Official DeltaCrown tournament")
    
    # Tournament Configuration
    format = CharField(max_length=50, choices=Format.choices)
    participation_type = CharField(max_length=20, choices=ParticipationType.choices)
    status = CharField(max_length=50, choices=Status.choices, default=Status.DRAFT)
    
    # Capacity
    max_participants = PositiveIntegerField(help_text="Max teams/players")
    min_participants = PositiveIntegerField(default=4)
    
    # Dates & Times
    registration_start = DateTimeField()
    registration_end = DateTimeField()
    tournament_start = DateTimeField()
    tournament_end = DateTimeField(null=True, blank=True)
    
    # Entry Fee
    has_entry_fee = BooleanField(default=False)
    entry_fee_amount = DecimalField(max_digits=10, decimal_places=2, default=0)
    entry_fee_currency = CharField(max_length=3, default='BDT')
    entry_fee_deltacoin = PositiveIntegerField(default=0)
    
    # Payment Methods
    payment_methods = ArrayField(
        CharField(max_length=50),
        default=list,
        help_text="Accepted payment methods: bkash, nagad, rocket, bank_transfer, deltacoin"
    )
    
    # Fee Waiver (Top Ranked Teams)
    enable_fee_waiver = BooleanField(default=False)
    fee_waiver_top_n_teams = PositiveIntegerField(
        default=0,
        help_text="Number of top-ranked teams that get free entry"
    )
    
    # Prize Pool
    prize_pool = DecimalField(max_digits=12, decimal_places=2, default=0)
    prize_currency = CharField(max_length=3, default='BDT')
    prize_deltacoin = PositiveIntegerField(default=0)
    prize_distribution = JSONField(
        default=dict,
        help_text="Prize breakdown by placement: {'1': 50000, '2': 30000, '3': 20000}"
    )
    
    # Sponsors
    sponsors = JSONField(
        default=list,
        help_text="List of sponsor objects: [{'name': 'X', 'logo_url': '...', 'website': '...'}]"
    )
    
    # Rules & Terms
    rules_text = TextField(blank=True)
    rules_pdf = FileField(upload_to='tournaments/rules/', null=True, blank=True)
    terms_and_conditions = TextField(blank=True)
    terms_pdf = FileField(upload_to='tournaments/terms/', null=True, blank=True)
    
    # Media
    banner_image = ImageField(upload_to='tournaments/banners/', null=True, blank=True)
    thumbnail_image = ImageField(upload_to='tournaments/thumbnails/', null=True, blank=True)
    promo_video_url = URLField(blank=True)
    
    # Streaming
    stream_youtube_url = URLField(blank=True)
    stream_twitch_url = URLField(blank=True)
    
    # Region
    region = CharField(max_length=50, blank=True, help_text="BD, SA, AS, EU, NA, etc.")
    
    # Feature Flags
    enable_check_in = BooleanField(default=True)
    check_in_start_minutes = PositiveIntegerField(default=30, help_text="Minutes before start")
    check_in_end_minutes = PositiveIntegerField(default=5, help_text="Minutes before start")
    
    enable_dynamic_seeding = BooleanField(default=False)
    use_team_rankings_for_seeding = BooleanField(default=False)
    
    enable_live_updates = BooleanField(default=True)
    enable_certificates = BooleanField(default=True)
    enable_challenges = BooleanField(default=False)
    enable_fan_voting = BooleanField(default=False)
    
    # Denormalized Counts (updated via signals)
    total_registrations = PositiveIntegerField(default=0)
    total_matches = PositiveIntegerField(default=0)
    completed_matches = PositiveIntegerField(default=0)
    
    # Audit Fields
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Methods:**
- `is_registration_open()` - Checks status and time window
- `spots_remaining()` - Calculates available slots
- `is_full()` - Boolean capacity check
- `save()` - Auto-generates unique slug, assigns official organizer

**Lifecycle States:**
```
draft → pending_approval → published → registration_open 
    → registration_closed → live → completed/cancelled → archived
```

---

#### CustomField (Dynamic Organizer Fields)
**File:** `apps/tournaments/models/tournament.py`  
**Purpose:** Allow organizers to define custom registration fields

```python
class CustomField(models.Model):
    class FieldType(TextChoices):
        TEXT = 'text', 'Text Input'
        NUMBER = 'number', 'Number'
        MEDIA = 'media', 'Image/Video Upload'
        TOGGLE = 'toggle', 'Yes/No Toggle'
        DATE = 'date', 'Date Picker'
        URL = 'url', 'URL'
        DROPDOWN = 'dropdown', 'Dropdown Select'
    
    tournament = ForeignKey(Tournament, on_delete=CASCADE, related_name='custom_fields')
    field_name = CharField(max_length=100)
    field_type = CharField(max_length=20, choices=FieldType.choices)
    is_required = BooleanField(default=False)
    help_text = CharField(max_length=200, blank=True)
    
    # For dropdown/select fields
    choices = JSONField(default=list, help_text="List of options for dropdown")
    
    # Validation Rules
    validation_rules = JSONField(
        default=dict,
        help_text="Validation constraints: {'min': 1, 'max': 100, 'pattern': '...'}"
    )
    
    order = PositiveIntegerField(default=0, help_text="Display order")
```

**Example Usage:**
- "Discord Username" (text, required)
- "Player Age" (number, min: 13, max: 99)
- "Team Logo" (media, optional)
- "Accept Code of Conduct" (toggle, required)

---

#### TournamentVersion (Configuration Snapshots)
**File:** `apps/tournaments/models/tournament.py`  
**Purpose:** Audit trail and rollback support for tournament configuration changes

```python
class TournamentVersion(models.Model):
    tournament = ForeignKey(Tournament, on_delete=CASCADE, related_name='versions')
    version_number = PositiveIntegerField()
    snapshot_data = JSONField(help_text="Full tournament configuration at this version")
    
    # Audit
    created_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    created_at = DateTimeField(auto_now_add=True)
    change_reason = TextField(blank=True)
```

**Key Features:**
- Auto-created on tournament save (if significant fields changed)
- Allows rollback to previous configuration
- Audit trail for compliance/disputes

---

### 3.2 Registration & Payment Models

#### Registration (Participant Registration)
**File:** `apps/tournaments/models/registration.py`  
**Purpose:** Track user/team registrations with payment and check-in workflow  
**Status:** Module 1.3 complete (650+ lines, 26 unit tests)

```python
class Registration(models.Model):
    class Status(TextChoices):
        PENDING = 'pending', 'Pending'
        PAYMENT_SUBMITTED = 'payment_submitted', 'Payment Submitted'
        CONFIRMED = 'confirmed', 'Confirmed'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'
    
    # Core References
    tournament = ForeignKey(Tournament, on_delete=CASCADE, related_name='registrations')
    user = ForeignKey(User, null=True, blank=True, on_delete=CASCADE, related_name='tournament_registrations')
    team_id = IntegerField(null=True, blank=True, db_index=True, help_text="Reference to Team (IntegerField for flexibility)")
    
    # Status & Workflow
    status = CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    
    # Registration Data
    registration_data = JSONField(
        default=dict,
        help_text="Game IDs, contact info, custom field responses"
    )
    # Example: {
    #   'riot_id': 'Player#1234',
    #   'discord': 'player#0001',
    #   'phone': '+880...',
    #   'custom_fields': {'team_logo': 'url...', 'accept_rules': True}
    # }
    
    # Check-In System
    checked_in = BooleanField(default=False)
    checked_in_at = DateTimeField(null=True, blank=True)
    checked_in_by = ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name='checked_in_registrations',
        help_text="Who performed check-in (self or organizer)"
    )
    
    # Seeding
    slot_number = PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Registration order slot (1, 2, 3...)"
    )
    seed = PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Tournament seeding position (for ranked seeding)"
    )
    
    # Audit
    registered_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [
            ('tournament', 'user'),
            ('tournament', 'team_id'),
            ('tournament', 'slot_number'),  # Each slot assigned once
        ]
        constraints = [
            CheckConstraint(
                check=Q(user__isnull=False) | Q(team_id__isnull=False),
                name='registration_has_user_or_team'
            ),
            CheckConstraint(
                check=~(Q(user__isnull=False) & Q(team_id__isnull=False)),
                name='registration_not_both_user_and_team'
            ),
        ]
```

**Key Methods:**
- `check_in_participant(actor)` - Mark participant as checked in
- `assign_slot(slot_number)` - Assign registration order slot
- `assign_seed(seed_value)` - Assign tournament seeding position

**Workflow States:**
```
pending → payment_submitted (if entry fee) → confirmed (by organizer/auto)
confirmed → checked_in (if check-in enabled)
any state → cancelled (by participant)
any state → rejected (by organizer)
confirmed → no_show (if didn't check in)
```

---

#### Payment (Payment Verification)
**File:** `apps/tournaments/models/registration.py`  
**Purpose:** Track payment proof submission and verification  
**Relationship:** OneToOne with Registration

```python
class Payment(models.Model):
    class PaymentMethod(TextChoices):
        BKASH = 'bkash', 'bKash'
        NAGAD = 'nagad', 'Nagad'
        ROCKET = 'rocket', 'Rocket'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        DELTACOIN = 'deltacoin', 'DeltaCoin'
    
    class Status(TextChoices):
        PENDING = 'pending', 'Pending Submission'
        SUBMITTED = 'submitted', 'Submitted for Review'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'
        REFUNDED = 'refunded', 'Refunded'
    
    registration = OneToOneField(Registration, on_delete=CASCADE, related_name='payment')
    
    # Payment Details
    payment_method = CharField(max_length=50, choices=PaymentMethod.choices)
    amount = DecimalField(max_digits=10, decimal_places=2)
    currency = CharField(max_length=3, default='BDT')
    
    # Proof Upload
    payment_proof = FileField(
        upload_to='tournaments/payment_proofs/',
        null=True,
        blank=True,
        help_text="Screenshot/receipt (max 5MB, JPG/PNG/PDF)"
    )
    file_type = CharField(max_length=10, blank=True, help_text="Auto-detected: jpg, png, pdf")
    
    # Transaction Details
    transaction_id = CharField(max_length=100, blank=True)
    reference_number = CharField(max_length=100, blank=True)
    
    # Verification
    status = CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    verified_by = ForeignKey(User, null=True, blank=True, on_delete=SET_NULL, related_name='verified_payments')
    verified_at = DateTimeField(null=True, blank=True)
    admin_notes = TextField(blank=True, help_text="Internal notes for verification team")
    
    # Audit
    submitted_at = DateTimeField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Methods:**
- `verify(admin_user)` - Mark payment as verified
- `reject(admin_user, reason)` - Reject payment with reason
- `refund(admin_user, reason)` - Process refund
- `_validate_proof_file()` - Validates file size (max 5MB) and type (JPG/PNG/PDF)

**Validation:**
- File size: Max 5MB
- File types: JPG, PNG, PDF only
- Auto-detects file type on upload
- Atomic state transitions (prevents invalid workflows)

---

### 3.3 Match & Bracket Models

#### Match (Match Lifecycle)
**File:** `apps/tournaments/models/match.py`  
**Purpose:** Individual match state machine with scoring and lobby info  
**Status:** Module 1.4 complete (950+ lines, 34 unit tests)

```python
class Match(models.Model):
    class Status(TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        CHECK_IN = 'check_in', 'Check-In Period'
        READY = 'ready', 'Ready to Start'
        LIVE = 'live', 'In Progress'
        PENDING_RESULT = 'pending_result', 'Awaiting Result Confirmation'
        COMPLETED = 'completed', 'Completed'
        DISPUTED = 'disputed', 'Under Dispute'
        FORFEIT = 'forfeit', 'Forfeit'
        CANCELLED = 'cancelled', 'Cancelled'
    
    # Tournament Context
    tournament = ForeignKey(Tournament, on_delete=CASCADE, related_name='matches')
    bracket = ForeignKey('Bracket', null=True, on_delete=SET_NULL, related_name='matches')
    round_number = PositiveIntegerField()
    match_number = PositiveIntegerField(help_text="Match number within round")
    
    # Participants (IntegerField for team/registration references)
    participant1_id = IntegerField(null=True, blank=True, help_text="Team/Player ID")
    participant1_name = CharField(max_length=200, blank=True, help_text="Cached name for display")
    participant2_id = IntegerField(null=True, blank=True)
    participant2_name = CharField(max_length=200, blank=True)
    
    # Scores
    participant1_score = PositiveIntegerField(default=0)
    participant2_score = PositiveIntegerField(default=0)
    
    # Winner/Loser Tracking
    winner_id = IntegerField(null=True, blank=True)
    loser_id = IntegerField(null=True, blank=True)
    
    # Status & Timing
    status = CharField(max_length=50, choices=Status.choices, default=Status.SCHEDULED)
    scheduled_time = DateTimeField(null=True, blank=True)
    started_at = DateTimeField(null=True, blank=True)
    completed_at = DateTimeField(null=True, blank=True)
    
    # Check-In
    participant1_checked_in = BooleanField(default=False)
    participant2_checked_in = BooleanField(default=False)
    check_in_deadline = DateTimeField(null=True, blank=True)
    
    # Lobby Information (Game-Specific)
    lobby_info = JSONField(
        default=dict,
        help_text="Game lobby details: map, server, lobby code, password, etc."
    )
    # Example: {
    #   'map': 'Haven',
    #   'server': 'Singapore',
    #   'lobby_code': 'ABC123',
    #   'password': 'deltacrown',
    #   'voice_channel': 'discord.gg/...'
    # }
    
    # Streaming
    stream_url = URLField(blank=True)
    
    # Audit
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Properties:**
- `is_both_checked_in` - Both participants checked in
- `is_ready_to_start` - Both checked in and status is READY
- `has_result` - Winner determined
- `is_in_progress` - Status is LIVE

**Key Methods:**
- `get_lobby_detail(key)` - Retrieve lobby info by key
- `set_lobby_detail(key, value)` - Set lobby info

**State Transitions:**
```
scheduled → check_in → ready → live → pending_result → completed
                                  ↓           ↓
                              forfeit      disputed → completed
any state → cancelled
```

---

#### Dispute (Dispute Resolution)
**File:** `apps/tournaments/models/match.py`  
**Purpose:** Handle match result disputes with evidence submission

```python
class Dispute(models.Model):
    class Reason(TextChoices):
        SCORE_MISMATCH = 'score_mismatch', 'Score Mismatch'
        NO_SHOW = 'no_show', 'Opponent No Show'
        CHEATING = 'cheating', 'Suspected Cheating'
        TECHNICAL_ISSUE = 'technical_issue', 'Technical Issue'
        OTHER = 'other', 'Other'
    
    class Status(TextChoices):
        OPEN = 'open', 'Open'
        UNDER_REVIEW = 'under_review', 'Under Review'
        RESOLVED = 'resolved', 'Resolved'
        ESCALATED = 'escalated', 'Escalated'
    
    # Core References
    match = ForeignKey(Match, on_delete=CASCADE, related_name='disputes')
    raised_by_id = IntegerField(help_text="Participant ID who raised dispute")
    
    # Dispute Details
    reason = CharField(max_length=50, choices=Reason.choices)
    description = TextField()
    status = CharField(max_length=50, choices=Status.choices, default=Status.OPEN)
    
    # Evidence
    evidence_screenshot = ImageField(upload_to='disputes/screenshots/', null=True, blank=True)
    evidence_video_url = URLField(blank=True)
    
    # Claimed Results
    claimed_participant1_score = PositiveIntegerField(null=True, blank=True)
    claimed_participant2_score = PositiveIntegerField(null=True, blank=True)
    
    # Resolution
    resolved_by_id = IntegerField(null=True, blank=True, help_text="Admin/organizer who resolved")
    resolved_at = DateTimeField(null=True, blank=True)
    resolution_notes = TextField(blank=True)
    final_participant1_score = PositiveIntegerField(null=True, blank=True)
    final_participant2_score = PositiveIntegerField(null=True, blank=True)
    
    # Audit
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Properties:**
- `is_open` - Status is OPEN or UNDER_REVIEW
- `is_resolved` - Status is RESOLVED
- `has_evidence` - Has screenshot or video URL

---

#### Bracket (Tournament Bracket Container)
**File:** `apps/tournaments/models/bracket.py`  
**Purpose:** Bracket generation configuration and structure storage  
**Status:** Module 1.5 complete (500+ lines, 45+ unit tests)

```python
class Bracket(models.Model):
    class Format(TextChoices):
        SINGLE_ELIMINATION = 'single-elimination', 'Single Elimination'
        DOUBLE_ELIMINATION = 'double-elimination', 'Double Elimination'
        ROUND_ROBIN = 'round-robin', 'Round Robin'
        SWISS = 'swiss', 'Swiss System'
        GROUP_STAGE = 'group-stage', 'Group Stage'
    
    class SeedingMethod(TextChoices):
        SLOT_ORDER = 'slot-order', 'Registration Order'
        RANDOM = 'random', 'Random Draw'
        MANUAL = 'manual', 'Manual Seeding'
        RANKED = 'ranked', 'Team Rankings'
    
    # Tournament Reference
    tournament = OneToOneField(Tournament, on_delete=CASCADE, related_name='bracket')
    
    # Configuration
    format = CharField(max_length=50, choices=Format.choices)
    seeding_method = CharField(max_length=50, choices=SeedingMethod.choices)
    
    # Structure Metadata
    total_rounds = PositiveIntegerField()
    total_matches = PositiveIntegerField()
    bracket_structure = JSONField(
        default=dict,
        help_text="Complete bracket structure with rounds, matches, positions"
    )
    # Example structure:
    # {
    #   'format': 'single-elimination',
    #   'total_participants': 8,
    #   'rounds': [
    #     {'round_number': 1, 'round_name': 'Quarter Finals', 'matches': 4},
    #     {'round_number': 2, 'round_name': 'Semi Finals', 'matches': 2},
    #     {'round_number': 3, 'round_name': 'Finals', 'matches': 1}
    #   ]
    # }
    
    # State
    is_finalized = BooleanField(
        default=False,
        help_text="Prevents regeneration once tournament starts"
    )
    generated_at = DateTimeField(auto_now_add=True)
```

**Key Methods:**
- `get_round_name(round_number)` - Returns display name for round (e.g., "Quarter Finals")

**Key Properties:**
- `has_third_place_match` - Boolean check for 3rd place match
- `total_participants` - Calculated from bracket_structure

**Indexes:**
- GIN index on `bracket_structure` for JSON queries

---

#### BracketNode (Individual Bracket Position)
**File:** `apps/tournaments/models/bracket.py`  
**Purpose:** Double-linked list navigation for bracket progression

```python
class BracketNode(models.Model):
    class NodeType(TextChoices):
        MAIN = 'main', 'Main Bracket'
        LOSERS = 'losers', 'Losers Bracket'  # Double elimination
        THIRD_PLACE = 'third-place', 'Third Place Match'
    
    # Bracket Reference
    bracket = ForeignKey(Bracket, on_delete=CASCADE, related_name='nodes')
    
    # Navigation (Double-Linked List)
    parent_node = ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name='child_nodes',
        help_text="Next match (winner advances here)"
    )
    child1_node = ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name='+',
        help_text="Previous match feeding into position 1"
    )
    child2_node = ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name='+',
        help_text="Previous match feeding into position 2"
    )
    parent_slot = PositiveIntegerField(
        null=True,
        blank=True,
        choices=[(1, 'Slot 1'), (2, 'Slot 2')],
        help_text="Which slot winner advances to in parent match"
    )
    
    # Position Tracking
    position = PositiveIntegerField(unique=True, help_text="Unique position in bracket")
    round_number = PositiveIntegerField()
    match_number_in_round = PositiveIntegerField()
    
    # Participants (Cached for Performance)
    participant1_id = IntegerField(null=True, blank=True)
    participant1_name = CharField(max_length=200, blank=True)
    participant2_id = IntegerField(null=True, blank=True)
    participant2_name = CharField(max_length=200, blank=True)
    winner_id = IntegerField(null=True, blank=True)
    
    # Match Reference
    match = OneToOneField(Match, null=True, blank=True, on_delete=SET_NULL, related_name='bracket_node')
    
    # Node Type
    node_type = CharField(max_length=20, choices=NodeType.choices, default=NodeType.MAIN)
    
    # Special Flags
    is_bye = BooleanField(
        default=False,
        help_text="Automatic advancement (odd participant count)"
    )
```

**Key Properties:**
- `has_both_participants` - Both positions filled
- `has_winner` - Winner determined
- `is_ready_for_match` - Both participants present and no winner yet

**Key Methods:**
- `get_winner_name()` - Returns winner display name
- `get_loser_id()` - Returns loser participant ID
- `advance_winner_to_parent()` - Advances winner to next match

**Navigation Pattern:**
```
Round 1 (Quarters)         Round 2 (Semis)           Round 3 (Finals)
├── Node 1 (Match 1) ────┐
├── Node 2 (Match 2) ────┼── Node 5 (Match 5) ────┐
├── Node 3 (Match 3) ────┤                         ├── Node 7 (Finals)
└── Node 4 (Match 4) ────┴── Node 6 (Match 6) ────┘
```

---

### 3.4 Result & Certificate Models

#### TournamentResult (Winner Determination)
**File:** `apps/tournaments/models/result.py`  
**Purpose:** Final tournament results with audit trail  
**Status:** Module 5.1 complete (14 tests, 81% coverage)

```python
class TournamentResult(models.Model):
    class DeterminationMethod(TextChoices):
        NORMAL = 'normal', 'Normal Bracket Completion'
        TIEBREAKER = 'tiebreaker', 'Tiebreaker Applied'
        FORFEIT_CHAIN = 'forfeit_chain', 'Forfeit Chain (Requires Review)'
        MANUAL = 'manual', 'Manual Override'
    
    # Tournament Reference
    tournament = OneToOneField(Tournament, on_delete=CASCADE, related_name='result')
    
    # Placements (FK to Registration)
    winner = ForeignKey(
        Registration,
        on_delete=PROTECT,
        related_name='tournaments_won',
        help_text="1st place winner"
    )
    runner_up = ForeignKey(
        Registration,
        null=True,
        blank=True,
        on_delete=PROTECT,
        related_name='tournaments_runner_up',
        help_text="2nd place"
    )
    third_place = ForeignKey(
        Registration,
        null=True,
        blank=True,
        on_delete=PROTECT,
        related_name='tournaments_third_place',
        help_text="3rd place"
    )
    
    # Determination Details
    determination_method = CharField(max_length=50, choices=DeterminationMethod.choices)
    rules_applied = JSONField(
        default=list,
        help_text="Ordered list of tiebreaker rules applied: [{'rule': 'head_to_head', 'outcome': '...'}]"
    )
    
    # Review System
    requires_review = BooleanField(
        default=False,
        help_text="Flagged for manual review (e.g., >50% forfeit chain)"
    )
    
    # Override Support
    is_override = BooleanField(default=False)
    override_reason = TextField(blank=True)
    override_actor = ForeignKey(User, null=True, on_delete=SET_NULL, related_name='+')
    override_timestamp = DateTimeField(null=True, blank=True)
    
    # Battle Royale Metadata (if applicable)
    total_kills = PositiveIntegerField(null=True, blank=True)
    best_placement = PositiveIntegerField(null=True, blank=True)
    avg_placement = DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    matches_played = PositiveIntegerField(null=True, blank=True)
    
    # Series Metadata (if applicable)
    series_score = JSONField(
        default=dict,
        help_text="Best-of-N series: {'participant1': 2, 'participant2': 1}"
    )
    game_results = JSONField(
        default=list,
        help_text="Individual game results in series: [{'game': 1, 'winner': 123, 'score': '16-14'}, ...]"
    )
    
    # Audit
    created_by = ForeignKey(User, on_delete=SET_NULL, null=True, related_name='tournament_results_created')
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            CheckConstraint(
                check=~Q(runner_up=F('winner')),
                name='runner_up_not_winner'
            ),
            CheckConstraint(
                check=~Q(third_place=F('winner')) & ~Q(third_place=F('runner_up')),
                name='third_place_unique'
            ),
        ]
```

**Tiebreaker Cascade (5 rules):**
1. Head-to-head record
2. Total score differential
3. Seeding position (lower seed wins)
4. Match completion time (earlier wins)
5. ValidationError (cannot determine)

**Key Features:**
- Idempotent: Returns existing result if already determined
- Atomic: All placements set in single transaction
- WebSocket: Broadcasts `tournament_completed` event on creation
- Audit trail: `rules_applied` JSONB contains full decision chain

---

#### Certificate (Achievement Certificates)
**File:** `apps/tournaments/models/certificate.py`  
**Purpose:** PDF/PNG certificates with tamper detection  
**Status:** Module 5.3 complete (35 tests, 85% coverage)

```python
class Certificate(models.Model):
    class CertificateType(TextChoices):
        WINNER = 'winner', 'Winner Certificate'
        RUNNER_UP = 'runner_up', 'Runner-Up Certificate'
        PARTICIPANT = 'participant', 'Participation Certificate'
    
    # Core References
    tournament = ForeignKey(Tournament, on_delete=CASCADE, related_name='certificates')
    participant = ForeignKey(Registration, on_delete=CASCADE, related_name='certificates')
    
    # Certificate Details
    certificate_type = CharField(max_length=50, choices=CertificateType.choices)
    placement = PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Final placement (1, 2, 3, etc.)"
    )
    
    # Generated Files
    file_pdf = FileField(upload_to='certificates/pdf/%Y/%m/', null=True, blank=True)
    file_image = FileField(upload_to='certificates/images/%Y/%m/', null=True, blank=True)
    
    # Verification & Security
    verification_code = UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text="Public verification code (QR code embedded)"
    )
    certificate_hash = CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hash of PDF for tamper detection"
    )
    
    # Download Tracking
    downloaded_at = DateTimeField(null=True, blank=True, help_text="First download timestamp")
    download_count = PositiveIntegerField(default=0)
    
    # Revocation
    is_revoked = BooleanField(default=False)
    revoked_at = DateTimeField(null=True, blank=True)
    revoked_reason = TextField(blank=True)
    
    # Audit
    generated_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [('tournament', 'participant')]
```

**Key Features:**
- **PDF Generation:** ReportLab (A4 landscape, 842x595pt)
- **PNG Rasterization:** Pillow (1920x1080px)
- **QR Codes:** Embedded verification URL
- **Multi-Language:** English + Bengali (Noto Sans font)
- **Tamper Detection:** SHA-256 hash verification
- **Streaming Downloads:** ETag caching with 300s TTL
- **Public Verification:** `/api/tournaments/certificates/verify/<uuid>/` endpoint

**API Endpoints:**
- `GET /api/tournaments/certificates/<id>/` - Download (owner/organizer/admin only)
- `GET /api/tournaments/certificates/verify/<uuid>/` - Public verification (no auth)

---

### 3.5 Prize & Analytics Models

#### PrizeTransaction (Prize Distribution Tracking)
**File:** `apps/tournaments/models/prize.py`  
**Purpose:** Track prize payouts with economy integration  
**Status:** Module 5.2 complete (36 tests, 85% coverage)

```python
class PrizeTransaction(models.Model):
    class Status(TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
    
    # Core References
    tournament = ForeignKey(Tournament, on_delete=PROTECT, related_name='prize_transactions')
    participant = ForeignKey(Registration, on_delete=PROTECT, related_name='prize_transactions')
    
    # Prize Details
    placement = PositiveIntegerField(help_text="Final placement (1, 2, 3, etc.)")
    amount = DecimalField(max_digits=12, decimal_places=2, help_text="Prize amount in currency")
    currency = CharField(max_length=3, default='BDT')
    deltacoin_amount = PositiveIntegerField(default=0, help_text="Prize in DeltaCoins")
    
    # Economy Integration
    coin_transaction = ForeignKey(
        'economy.DeltaCrownTransaction',
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name='prize_payouts'
    )
    
    # Status & Processing
    status = CharField(max_length=50, choices=Status.choices, default=Status.PENDING)
    processed_by = ForeignKey(User, null=True, on_delete=SET_NULL, related_name='processed_prizes')
    processed_at = DateTimeField(null=True, blank=True)
    
    # Audit
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Service Layer (PayoutService):**
- `calculate_distribution()` - Calculate prize amounts from `prize_distribution` JSON
- `process_payouts()` - Distribute prizes to winners (integrates with economy app)
- `process_refunds()` - Refund entry fees for cancelled tournaments
- `verify_reconciliation()` - Validate total payouts = prize pool

**API Endpoints:**
- `POST /api/tournaments/<id>/payouts/` - Process prize payouts (organizer/admin)
- `POST /api/tournaments/<id>/refunds/` - Process refunds (organizer/admin)
- `GET /api/tournaments/<id>/payouts/verify/` - Verify reconciliation

---

## 4. Team App – Basic Integration

### Overview
The `apps.teams` app provides comprehensive team management that integrates tightly with the tournament system for team-based competitions.

### Core Integration Points

#### 4.1 Tournament Registration Integration
**How Tournaments Connect to Teams:**

```python
# Registration Model (tournament side)
class Registration(models.Model):
    tournament = ForeignKey(Tournament)
    user = ForeignKey(User, null=True)          # For solo tournaments
    team_id = IntegerField(null=True)            # For team tournaments
    
    # XOR Constraint: Exactly one of user or team_id must be set
```

**Registration Flow for Team-Based Tournaments:**
1. Captain initiates registration via tournament detail page
2. System validates:
   - Captain has permission (checks `TeamMembership` with role OWNER/CAPTAIN)
   - Team meets size requirements (`min_team_size` ≤ active members ≤ `max_team_size`)
   - Team hasn't already registered
   - Tournament has capacity
3. Creates `Registration` with `team_id` reference
4. Captures team roster in `registration_data` JSON:
   ```json
   {
     "team_id": 123,
     "team_name": "Team DeltaCrown",
     "team_tag": "DC",
     "roster": [
       {"user_id": 1, "role": "OWNER", "game_id": "Player#1234"},
       {"user_id": 2, "role": "PLAYER", "game_id": "Player2#5678"},
       ...
     ]
   }
   ```

#### 4.2 Team Ranking for Seeding
**Module 4.2:** Ranking & Seeding Integration (complete)

**How Rankings Affect Tournaments:**

```python
# BracketService uses TournamentRankingService
from apps.teams.models import TeamRankingBreakdown

class TournamentRankingService:
    def get_ranked_participants(tournament):
        """
        Returns participants sorted by team ranking for seeding.
        Uses TeamRankingBreakdown.final_total as primary sort key.
        """
        registrations = tournament.registrations.filter(status='confirmed', team_id__isnull=False)
        
        # Fetch rankings for all teams
        team_ids = [r.team_id for r in registrations]
        rankings = TeamRankingBreakdown.objects.filter(team_id__in=team_ids)
        
        # Sort by: points DESC, team age DESC, team ID ASC (deterministic)
        return sorted(registrations, key=lambda r: (
            -rankings.get(team_id=r.team_id).final_total,
            -get_team_age(r.team_id),
            r.team_id
        ))
```

**Ranking Components Used:**
- `tournament_winner_points` (500 default)
- `tournament_runner_up_points` (300 default)
- `tournament_top_4_points` (150 default)
- `tournament_participation_points` (50 default)
- `manual_adjustment_points` (admin overrides)

**Seeding Method:** `seeding_method='ranked'` in BracketGenerationSerializer

#### 4.3 Fee Waiver for Top Teams
**Tournament Model Fields:**

```python
class Tournament(models.Model):
    enable_fee_waiver = BooleanField(default=False)
    fee_waiver_top_n_teams = PositiveIntegerField(
        default=0,
        help_text="Top N ranked teams get free entry"
    )
```

**RegistrationService Logic:**

```python
def check_eligibility(user, tournament):
    if tournament.has_entry_fee and tournament.enable_fee_waiver:
        # Get user's team for this tournament's game
        team = get_users_team_for_game(user, tournament.game)
        
        if team:
            # Get team's rank from TeamRankingBreakdown
            ranking = TeamRankingBreakdown.objects.get(team=team)
            
            # Check if team is in top N
            top_teams = get_top_n_teams(tournament.game, tournament.fee_waiver_top_n_teams)
            
            if team in top_teams:
                return {'eligible': True, 'fee_waived': True, 'reason': 'Top ranked team'}
    
    return {'eligible': True, 'fee_waived': False}
```

#### 4.4 Team Display in Standings/Participants
**Match Model References Teams:**

```python
class Match(models.Model):
    participant1_id = IntegerField()      # Can be team_id
    participant1_name = CharField()       # Cached "TeamName (TAG)"
    participant2_id = IntegerField()
    participant2_name = CharField()
```

**Cache Update on Team Changes:**
- Signal: `post_save` on Team model
- Updates: All matches/registrations with this team_id
- Recaches: `display_name` property

#### 4.5 Team Permissions for Tournament Actions
**Who Can Act on Behalf of Team:**

```python
def can_act_for_team(user, team_id):
    """Check if user has permission to act for team in tournaments."""
    try:
        membership = TeamMembership.objects.get(
            team_id=team_id,
            profile__user=user,
            status=TeamMembership.Status.ACTIVE
        )
        
        # OWNER and CAPTAIN can register/manage tournaments
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.CAPTAIN
        ]
    except TeamMembership.DoesNotExist:
        return False
```

**Permission Checks:**
- Register team → OWNER or CAPTAIN
- Submit match results → OWNER or CAPTAIN
- Check-in team → OWNER or CAPTAIN
- Withdraw from tournament → OWNER only

---

## 5. Users, Profiles & Roles – High-Level

### 5.1 User Model Architecture

**Base User:** `accounts.User` (Custom AbstractUser)
- **Purpose:** Authentication, email verification, basic identity
- **Key Fields:** `username`, `email`, `is_verified`, `email_verified_at`
- **Authentication:** JWT tokens (60min access, 7-day refresh)
- **Verification:** EmailOTP system with 6-digit codes

**Extended Profile:** `user_profile.UserProfile` (OneToOne)
- **Purpose:** Gaming identity, preferences, social links
- **Key Fields:** `display_name`, `region`, `avatar`, game IDs for 9 platforms
- **Privacy:** Granular controls (`show_email`, `show_socials`, etc.)

### 5.2 Role Architecture

#### Generic User (No Special Permissions)
- Can browse tournaments
- Can create/join teams
- Can follow teams/tournaments
- Cannot register for tournaments without verification

#### Tournament Participant
**Becomes participant when:**
- Successfully registers for a tournament
- Registration status = CONFIRMED

**Permissions:**
- View tournament lobby
- Submit match results (for their matches)
- Report disputes
- Check-in (self)
- View/download their certificates

**Check via:**
```python
def is_tournament_participant(user, tournament):
    return Registration.objects.filter(
        tournament=tournament,
        user=user,
        status='confirmed'
    ).exists()
```

#### Tournament Organizer
**Becomes organizer when:**
- Creates a tournament (auto-set as `tournament.organizer`)
- Granted organizer role by admin

**Permissions:**
- Create/edit/cancel tournaments
- Approve/reject registrations
- Verify/reject payments
- Start/cancel matches
- Resolve disputes
- Submit/confirm match results
- Force check-in participants
- Generate brackets
- Distribute prizes
- Access organizer dashboard
- View analytics

**Check via:**
```python
def is_tournament_organizer(user, tournament):
    return tournament.organizer == user

# Or for any tournament by user
def user_organized_tournaments(user):
    return Tournament.objects.filter(organizer=user)
```

#### Team Captain
**Becomes captain when:**
- Creates a team (auto-set as `team.captain`)
- Transferred captain role by previous captain

**Permissions:**
- Register team for tournaments
- Submit match results for team matches
- Manage team roster (invite/remove members)
- Transfer captain role
- Disband team

**Check via:**
```python
def is_team_captain(user, team_id):
    from apps.teams.models import Team
    return Team.objects.filter(
        id=team_id,
        captain__user=user
    ).exists()
```

#### Staff/Admin
**Django built-in roles:**
- `is_staff` → Can access Django admin panel
- `is_superuser` → Full permissions

**Tournament System Permissions:**
- All organizer permissions for all tournaments
- Approve pending tournaments
- Mark tournaments as official
- Ban/unban participants
- Override match results
- Manual prize distribution
- Access moderation tools
- View all analytics

### 5.3 Permission Checking Patterns

**DRF Permission Classes (apps/tournaments/api/permissions.py):**

```python
class IsOrganizerOrAdmin(BasePermission):
    """Allow organizers and admins."""
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_staff or
            obj.organizer == request.user
        )

class IsParticipantOrOrganizer(BasePermission):
    """Allow participants and organizers."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or obj.tournament.organizer == request.user:
            return True
        
        return Registration.objects.filter(
            tournament=obj.tournament,
            user=request.user,
            status='confirmed'
        ).exists()

class IsOwnerOrOrganizer(BasePermission):
    """Allow registration owner or tournament organizer."""
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_staff or
            obj.tournament.organizer == request.user or
            obj.user == request.user or
            (obj.team_id and can_act_for_team(request.user, obj.team_id))
        )
```

**View-Level Checks:**

```python
# In views
@login_required
def submit_match_result(request, match_id):
    match = get_object_or_404(Match, id=match_id)
    
    # Check: User is participant in this match
    registration = Registration.objects.filter(
        tournament=match.tournament,
        user=request.user,
        status='confirmed'
    ).first()
    
    if not registration:
        return HttpResponseForbidden("Not a participant")
    
    # Check: Match belongs to user's participant
    if registration.team_id:
        is_participant = match.participant1_id == registration.team_id or \
                        match.participant2_id == registration.team_id
    else:
        is_participant = match.participant1_id == registration.id or \
                        match.participant2_id == registration.id
    
    if not is_participant:
        return HttpResponseForbidden("Not your match")
    
    # Process result submission...
```

### 5.4 Role Assignment Flow

**New User Registration:**
```
1. User signs up → PendingSignup created
2. Email OTP sent
3. User verifies OTP → User created with is_verified=True
4. UserProfile auto-created via signal
5. DeltaCrownWallet auto-created via signal
```

**Becoming Tournament Organizer:**
```
Option 1: Create tournament → Auto-set as organizer
Option 2: Admin assigns organizer role (future feature)
```

**Becoming Team Captain:**
```
Option 1: Create team → Auto-set as captain
Option 2: Receive captain transfer from current captain
```

**Becoming Tournament Participant:**
```
1. Browse tournaments
2. Click "Register" (solo) or captain registers team
3. Submit payment (if required)
4. Payment verified by organizer
5. Registration status → CONFIRMED
6. Now a participant with lobby/match access
```

---

## 6. Backend Execution Plans – Relevant Points for Tournament & Team

### 6.1 Phase 1: Core Models & Database (COMPLETE)
**Status:** ✅ All 5 modules complete (November 2025)

**Key Achievements:**
- **Module 1.1:** Base models (SoftDelete, Timestamped) with managers
- **Module 1.2:** Tournament & Game models (71+ fields, 25 tests, 88% coverage)
- **Module 1.3:** Registration & Payment models (462 lines, 26 tests, 65% coverage)
- **Module 1.4:** Match & Dispute models (950+ lines, 34 tests, 80%+ coverage)
- **Module 1.5:** Bracket & BracketNode models (500+ lines, 45+ tests, 80%+ coverage)

**Implementation Notes:**
- All models use PostgreSQL features (JSONB, ArrayField, CHECK constraints)
- Immutability patterns (Transaction ledger, TournamentVersion)
- Soft delete pattern consistently applied
- Migration tested and working

---

### 6.2 Phase 2: Real-Time Features & Security (COMPLETE)
**Status:** ✅ All 6 modules complete (November 2025)

**Key Achievements:**
- **Module 2.1:** Infrastructure (Django Channels, JWT, Sentry, Prometheus)
- **Module 2.2:** WebSocket consumers (TournamentConsumer with 4 event types)
- **Module 2.3:** Service layer integration (broadcasts from Match/Bracket services)
- **Module 2.4:** Security hardening (role-based permissions, audit logging)
- **Module 2.5:** Rate limiting (token bucket, connection limits, payload caps)
- **Module 2.6:** Monitoring (Prometheus metrics, structured JSON logging)

**WebSocket Event Types:**
- `match_started` → New match begins
- `score_updated` → Match score changes
- `match_completed` → Match finishes with confirmed result
- `bracket_updated` → Bracket progression after match completion
- `registration_checked_in` → Participant checks in
- `tournament_completed` → Tournament finishes with winner determined

**Security Features:**
- JWT authentication required (query param: `?token=<jwt>`)
- Role hierarchy: SPECTATOR < PLAYER < ORGANIZER < ADMIN
- Rate limits: 10 msg/sec, 3 concurrent connections per user
- Payload cap: 16 KB max
- Room capacity: 2000 spectators per tournament

---

### 6.3 Phase 3: Registration & Check-in (COMPLETE)
**Status:** ✅ All 4 modules complete (January 2025)

**Key Achievements:**
- **Module 3.1:** Registration API (14 tests, eligibility validation)
- **Module 3.2:** Payment verification (29 tests, multipart upload, organizer approval)
- **Module 3.3:** Team management (27 tests, invite/accept/remove/transfer/disband)
- **Module 3.4:** Check-in system (36 tests, 30-min window, team captain check-in)

**Registration Workflow:**
```
POST /api/tournaments/registrations/
  → eligibility checks
  → create Registration (status=PENDING)
  → if has_entry_fee: create Payment (status=PENDING)
  → notification sent

POST /api/tournaments/payments/{id}/submit-proof/
  → upload screenshot/receipt
  → Payment status → SUBMITTED
  → organizer notified

POST /api/tournaments/payments/{id}/verify/
  → organizer reviews
  → Payment status → VERIFIED
  → Registration status → CONFIRMED
  → participant notified
```

**Check-In Workflow:**
```
POST /api/tournaments/checkin/{id}/check-in/
  → validates check-in window (30 min before start)
  → registration.checked_in = True
  → WebSocket broadcast: registration_checked_in
  → if team: captain can check in entire team

POST /api/tournaments/checkin/{id}/undo/
  → organizer can undo anytime
  → participant can undo within 15 minutes
```

---

### 6.4 Phase 4: Tournament Live Operations (COMPLETE)
**Status:** ✅ All 6 modules complete (November 2025)

**Key Achievements:**
- **Module 4.1:** Bracket generation (4 seeding strategies, bye handling, 24 tests)
- **Module 4.2:** Ranking & seeding (deterministic tie-breaking, 42 tests)
- **Module 4.3:** Match management (7 API endpoints, scheduling, 25 tests)
- **Module 4.4:** Result submission (two-step confirmation, 5 statuses, 24 tests)
- **Module 4.5:** WebSocket enhancements (match-specific channels, heartbeat, 18 tests)
- **Module 4.6:** API polish (consistency audit, error catalog, 10 tests)

**Bracket Generation:**
```
POST /api/tournaments/brackets/<tournament_id>/generate/
  {
    "seeding_method": "ranked",  // or "slot-order", "random", "manual"
    "format": "single-elimination"
  }
  → validates tournament ready (min participants, registration closed)
  → generates bracket structure
  → creates BracketNode instances with navigation
  → creates Match instances
  → WebSocket broadcast: bracket_generated
```

**Match Lifecycle:**
```
SCHEDULED → CHECK_IN → READY → LIVE → PENDING_RESULT → COMPLETED
                                   ↓           ↓
                               FORFEIT      DISPUTED
```

---

### 6.5 Phase 5: Tournament Post-Game (COMPLETE)
**Status:** ✅ All 6 modules complete (November 2025)

**Key Achievements:**
- **Module 5.1:** Winner determination (5-step tiebreaker, 14 tests, 81% coverage)
- **Module 5.2:** Prize payouts (idempotent, economy integration, 36 tests)
- **Module 5.3:** Certificates (PDF/PNG, QR codes, tamper detection, 35 tests)
- **Module 5.4:** Analytics & reports (25 metrics, CSV export, 37 tests)
- **Module 5.5:** Notifications & webhooks (HMAC-SHA256, retry logic, 43 tests)

**Winner Determination:**
```
When all matches complete:
  → WinnerDeterminationService.determine_winner()
  → verify all matches complete/forfeit
  → traverse bracket tree to find final winner
  → apply tiebreaker rules if needed:
    1. Head-to-head record
    2. Score differential
    3. Seeding position
    4. Completion time
    5. Manual review (ValidationError)
  → create TournamentResult
  → update Tournament.status = COMPLETED
  → WebSocket broadcast: tournament_completed
```

**Prize Distribution:**
```
POST /api/tournaments/<id>/payouts/
  → calculate amounts from prize_distribution JSON
  → create PrizeTransaction for each placement
  → integrate with DeltaCrownWallet
  → create DeltaCrownTransaction records
  → verify reconciliation (total payouts = prize pool)
```

**Certificate Generation:**
```
POST /api/tournaments/certificates/{id}/
  → generates PDF (ReportLab, A4 landscape)
  → rasterizes to PNG (Pillow, 1920x1080)
  → embeds QR code with verification URL
  → calculates SHA-256 hash for tamper detection
  → stores files and returns download link

GET /api/tournaments/certificates/verify/<uuid>/
  → public verification endpoint
  → checks is_revoked flag
  → validates certificate_hash
  → returns validity status (no PII)
```

---

### 6.6 Phase 6: Performance & Polish (COMPLETE)
**Status:** ✅ 8 modules complete (November 2025)

**Key Achievements:**
- **Module 6.1:** Async-native WebSocket helpers (event-loop-safe, 4 tests)
- **Module 6.2:** Materialized views (70.5× speedup, hourly refresh, 13 tests)
- **Module 6.3:** URL routing audit (duplicate prefix fix, 6 tests)
- **Module 6.4:** Module 4.2 test fixes (19/19 tests passing)
- **Module 6.5:** S3 migration planning (design doc, no implementation)
- **Module 6.6:** Realtime coverage uplift (45% coverage, 61 tests)
- **Module 6.7:** Coverage carry-forward (77% utils, 83% consumer, 47 tests)
- **Module 6.8:** Redis-backed enforcement (62% middleware, 18 tests)

**Performance Optimizations:**
- Materialized view: `analytics_tournament_organizer_mv` (refreshed hourly)
- Query optimization: Reduces analytics queries from 5.26ms → 0.07ms avg
- WebSocket: 100ms micro-batching for score updates (latest-wins)
- Certificate storage: S3 migration planned (Q1-Q2 2026)

---

### 6.7 Phase 7: Economy & Monetization (IN PROGRESS)
**Status:** 🟡 3/5 modules complete (November 2025)

**Completed Modules:**
- **Module 7.1:** DeltaCoin system (immutable ledger, 50 tests, 91% coverage)
- **Module 7.2:** Shop & purchases (two-phase commit, 73 tests, 93% coverage)
- **Module 7.3:** Transaction history (pagination, CSV export, 32 tests)

**Pending Modules:**
- **Module 7.4:** Revenue analytics (planned)
- **Module 7.5:** Payment gateway integration (planned)

**Economy Integration with Tournaments:**
- Entry fees deducted via `EconomyService.debit()`
- Prize payouts credited via `EconomyService.credit()`
- Refunds processed via `PayoutService.process_refunds()`
- All transactions use idempotency keys to prevent duplicates

---

### 6.8 Implementation Status Summary

**Current Implementation Status (November 20, 2025):**

| Phase | Modules | Status | Completion | Notes |
|-------|---------|--------|------------|-------|
| Phase 0 | 4 | Partial | 25% | Implicit (settings, DB, CI) |
| Phase 1 | 5 | ✅ Complete | 100% | All models implemented |
| Phase 2 | 6 | ✅ Complete | 100% | Real-time + security |
| Phase 3 | 4 | ✅ Complete | 100% | Registration + check-in |
| Phase 4 | 6 | ✅ Complete | 100% | Live operations |
| Phase 5 | 6 | ✅ Complete | 100% | Post-game + analytics |
| Phase 6 | 8 | ✅ Complete | 100% | Performance + polish |
| Phase 7 | 3/5 | 🟡 In Progress | 60% | Economy integration |
| Phase 8 | 0/5 | 📋 Planned | 0% | Mobile + accessibility |
| Phase 9 | 0/6 | 📋 Planned | 0% | Testing + deployment |

**Overall Progress:** ~42/67 modules complete (~63%)

**Test Coverage:**
- Total Tests Written: 800+ tests
- Total Test Code: ~30,000+ lines
- Overall Pass Rate: 95%+
- Coverage: 80-90% average across implemented modules

**Documentation:**
- Planning docs: 17,529 lines (14 files)
- Execution tracking: MAP.md (3,002 lines)
- Module completion reports: 40+ comprehensive status docs

---

## 7. Key Integration Patterns

### 7.1 Tournament → Team Integration
```python
# Tournament checks team eligibility
from apps.teams.models import Team, TeamRankingBreakdown

def get_team_for_registration(user, tournament):
    # Find user's team for this game
    team = Team.objects.filter(
        game=tournament.game.slug,
        memberships__profile__user=user,
        memberships__status='ACTIVE',
        memberships__role__in=['OWNER', 'CAPTAIN']
    ).first()
    
    if not team:
        return None, "Not a captain of any team for this game"
    
    # Check team size requirements
    member_count = team.members_count
    if member_count < tournament.game.min_team_size:
        return None, f"Team has {member_count} members, need {tournament.game.min_team_size}"
    
    if member_count > tournament.game.max_team_size:
        return None, f"Team has {member_count} members, max {tournament.game.max_team_size}"
    
    return team, None
```

### 7.2 Tournament → Economy Integration
```python
# Entry fee deduction
from apps.economy.services import EconomyService

def process_entry_fee(registration):
    if registration.tournament.entry_fee_deltacoin > 0:
        wallet = registration.user.profile.deltacoin_wallet
        
        try:
            transaction = EconomyService.debit(
                wallet=wallet,
                amount=registration.tournament.entry_fee_deltacoin,
                reason='entry_fee_debit',
                tournament_id=registration.tournament.id,
                registration_id=registration.id,
                idempotency_key=f'entry-{registration.id}'
            )
            return transaction
        except InsufficientFunds:
            raise ValidationError("Insufficient DeltaCoins for entry fee")
```

### 7.3 Tournament → Notification Integration
```python
# Payment verified notification
from apps.notifications.services import NotificationService

def notify_payment_verified(payment):
    NotificationService.notify(
        recipient=payment.registration.user,
        event='payment_verified',
        title='Payment Verified',
        body=f"Your payment for '{payment.registration.tournament.name}' has been verified.",
        url=f"/tournaments/{payment.registration.tournament.slug}/",
        tournament=payment.registration.tournament
    )
```

### 7.4 Tournament → Leaderboard Integration
```python
# Update leaderboards after tournament completion
from apps.leaderboards.services import LeaderboardService

def update_leaderboards_after_tournament(tournament_result):
    winner_registration = tournament_result.winner
    
    # Calculate points from tournament placement
    points = LeaderboardService.calculate_player_points(
        tournament=tournament_result.tournament,
        placement=1,
        total_participants=tournament_result.tournament.total_registrations
    )
    
    # Update seasonal and all-time leaderboards
    LeaderboardService.update_leaderboard(
        profile=winner_registration.user.profile,
        game=tournament_result.tournament.game.slug,
        points=points,
        scope='seasonal'
    )
```

---

## 8. Planned vs Implemented Features

### 8.1 Fully Implemented ✅
- Tournament CRUD (creation, editing, cancellation)
- Registration flow (solo & team)
- Payment submission & verification
- Check-in system with time windows
- Bracket generation (single-elimination, byes, 4 seeding strategies)
- Match management & scheduling
- Result submission (two-step confirmation)
- Dispute handling
- Winner determination (5-step tiebreaker)
- Prize distribution (economy integration)
- Certificate generation (PDF/PNG with QR codes)
- Analytics & reporting (25 metrics, CSV export)
- Real-time updates (WebSocket broadcasts for 6 event types)
- Team integration (registration, seeding, fee waivers)
- Notification system (multi-channel with webhooks)
- Leaderboard integration
- Rate limiting & security hardening
- Audit logging (18 sensitive actions tracked)

### 8.2 Partially Implemented 🟡
- Double elimination brackets (signature ready, algorithm deferred)
- Round robin & Swiss formats (models ready, generation logic pending)
- Group stage + playoffs (models ready, implementation pending)
- Dynamic seeding (flag exists, real-time implementation pending)
- Fan voting (flag exists, voting system not implemented)
- Challenges system (flag exists, challenge logic not implemented)

### 8.3 Planned but Not Started 📋
- Waitlist management (Module 3.4 deferred)
- Live match HUD (spectator enhancement)
- Discussion system (comments/threads)
- Prediction system (betting mechanics)
- Live chat (real-time messaging)
- Mobile responsive views (Phase 8)
- Accessibility features (WCAG 2.1 AA compliance)
- PWA & offline support
- E2E test suite (Phase 9)
- Load testing & performance benchmarks

### 8.4 Known Technical Debt
- Certificate storage on local filesystem (S3 migration planned Q1-Q2 2026)
- Tournament FKs as IntegerField (legacy migration, consider proper ForeignKey)
- Materialized view has infinite retention (implement partitioning in production)
- No automatic JWT refresh on WebSocket (clients must reconnect)
- WebSocket in-memory fallback not suitable for multi-process scaling
- Rate limit enforcement missing message RPS tests (47% coverage gap)

---

**End of Part 1: Backend Architecture & Core Apps**

**Document Status:** Complete  
**Total Sections:** 8 major sections  
**Total Lines:** ~1,200 lines  
**Coverage:** Comprehensive backend overview with real code references

