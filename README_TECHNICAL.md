# DeltaCrown Platform - Bootstrap & Technical Guide

**Status**: Production-ready configuration  
**Last Updated**: 2026-02-02  
**Database**: Neon (ep-lively-queen-a13dp7w6) for all non-test environments

---

## 📋 Quick Start (Fresh Database)

```bash
# 1. Set environment variables
export DATABASE_URL='postgresql://neondb_owner:...'
export DATABASE_URL_TEST='postgresql://localhost:5432/deltacrown_test'

# 2. Run migrations
python manage.py migrate

# 3. Seed core data (order matters!)
python manage.py seed_games
python manage.py seed_game_passport_schemas
python manage.py seed_game_ranking_configs

# 4. Create superuser
python manage.py createsuperuser

# 5. (Optional) Backfill game profiles for existing users
python manage.py backfill_game_profiles --all --limit 100 --dry-run
python manage.py backfill_game_profiles --all --limit 100

# 6. Verify
python manage.py runserver
# Visit: http://localhost:8000/admin
```

---

## 🗄️ Database Configuration

### Environment Variables

**Runtime (Django server, management commands)**:
- `DATABASE_URL` - **REQUIRED** - Points to Neon for all environments
- Format: `postgresql://user:pass@ep-lively-queen-a13dp7w6.ap-southeast-1.aws.neon.tech:5432/deltacrown?sslmode=require`
- Used for: `runserver`, `migrate`, `seed_*`, `shell`, etc.

**Tests (pytest only)**:
- `DATABASE_URL_TEST` - **REQUIRED** - Points to local PostgreSQL
- Format: `postgresql://localhost:5432/deltacrown_test`
- Must NOT contain `neon.tech` (enforced by `tests/conftest.py`)
- Used for: `pytest` runs only

### Configuration Logic (deltacrown/settings.py)

```python
def get_database_environment():
    """
    Simple database selection:
    - Tests: Use DATABASE_URL_TEST (local only, remote refused)
    - Everything else: Use DATABASE_URL (Neon)
    
    No auto-switching, no fallbacks, no dev/prod/staging URLs.
    """
    if is_test:
        db_url = os.getenv('DATABASE_URL_TEST')
        if not db_url:
            sys.stderr.write("\n❌ DATABASE_URL_TEST required for tests.\n\n")
            sys.exit(1)
        return db_url, 'TEST'
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        sys.stderr.write("\n❌ DATABASE_URL required.\n\n")
        sys.exit(1)
    
    return db_url, 'PROD'
```

**Key Points**:
- No migration guard (Neon is dev database)
- Tests REFUSE to run on remote databases
- Runtime ALWAYS uses Neon via DATABASE_URL
- Clear error messages if DATABASE_URL missing

---

## 🌱 Seed Commands (Idempotent)

All seed commands are **idempotent** - safe to run multiple times.

### 1. seed_games
**Purpose**: Seeds 11 core games with comprehensive metadata  
**Location**: `apps/games/management/commands/seed_games.py`  
**What it creates**:
- Game records (LOL, VAL, CS2, DOTA2, RL, APEX, OW2, FORT, COD, R6, PUBG)
- GameRosterConfig (min/max players per game)
- GameRole (per-game competitive roles)
- GamePlayerIdentityConfig (identity field requirements)
- GameTournamentConfig (match formats, scoring)

**Usage**:
```bash
# Initial seed
python manage.py seed_games

# Re-seed (updates existing games)
python manage.py seed_games --force
```

**Data Date**: December 2025 competitive meta

---

### 2. seed_game_passport_schemas
**Purpose**: Seeds GamePassportSchema records (per-game identity configuration)  
**Location**: `apps/user_profile/management/commands/seed_game_passport_schemas.py`  
**What it creates**:
- GamePassportSchema (one per game)
- Defines identity fields (ign, discriminator, platform, region)
- Defines rank tiers, verification requirements, regions per game

**Dependencies**: Requires `seed_games` first

**Usage**:
```bash
# Initial seed (idempotent)
python manage.py seed_game_passport_schemas

# Reset (delete and recreate)
python manage.py seed_game_passport_schemas --reset
```

**⚠️ IMPORTANT**: This creates CONFIGURATION, not user data. User GameProfile instances are created separately.

---

### 3. seed_game_ranking_configs
**Purpose**: Seeds competition ranking configurations  
**Location**: `apps/competition/management/commands/seed_game_ranking_configs.py`  
**What it creates**:
- GameRankingConfig (per game)
- Ranking weights (win/loss/kill/death/assist)
- Tier thresholds (Bronze/Silver/Gold/etc.)
- Decay policy (LP decay for inactivity)
- Verification rules

**Dependencies**: Requires `seed_games` first

**Usage**:
```bash
python manage.py seed_game_ranking_configs
```

**Idempotency**: Uses `update_or_create`, safe to re-run

---

### 4. backfill_game_profiles (NEW)
**Purpose**: Create GameProfile instances for existing users  
**Location**: `apps/user_profile/management/commands/backfill_game_profiles.py`  
**What it creates**:
- GameProfile records (user game identities/passports)
- One per user per game (e.g., user "alice" gets 11 GameProfiles, one for each game)

**Dependencies**: 
- Requires `seed_games` first
- Requires `seed_game_passport_schemas` first
- Requires at least 1 user to exist

**Usage**:
```bash
# Dry-run (see what would be created)
python manage.py backfill_game_profiles --dry-run

# Backfill for specific user
python manage.py backfill_game_profiles --user alice
python manage.py backfill_game_profiles --user 123

# Backfill for all users (with safety limit)
python manage.py backfill_game_profiles --all --limit 100

# Backfill for specific game only
python manage.py backfill_game_profiles --all --game valorant --limit 50
```

**Behavior**:
- Only creates GameProfiles if user doesn't have one for that game
- Creates minimal skeleton (user fills in ign/rank/stats later)
- Safe to run on fresh database with zero users (exits gracefully)
- Uses `get_or_create` for atomic operation

**⚠️ IMPORTANT**: This is NOT required for fresh databases. GameProfiles can be created:
1. When user edits their profile via UI
2. When user verifies their game account via API
3. By this backfill command (for existing users from legacy system)

---

## 📊 Seed Sequence (Correct Order)

```bash
# Order matters due to foreign key dependencies:
python manage.py seed_games                      # 1. Games registry first
python manage.py seed_game_passport_schemas      # 2. Requires games
python manage.py seed_game_ranking_configs       # 3. Requires games

# Only if users exist:
python manage.py backfill_game_profiles --all    # 4. Requires games + schemas + users
```

---

## 🔄 Reset Workflow (Neon Database)

See: [docs/ops/neon-reset.md](docs/ops/neon-reset.md)

**Summary**:
```bash
# 1. Drop all tables (Neon Console or psql)
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

# 2. Fresh migrations
python manage.py migrate

# 3. Seed in order
python manage.py seed_games
python manage.py seed_game_passport_schemas
python manage.py seed_game_ranking_configs

# 4. Create admin
python manage.py createsuperuser

# 5. Verify
python manage.py runserver
```

---

## 🐛 Common Issues

### Issue 1: `organizations_team` missing

**Error**: `DoesNotExist: Table 'organizations_team' doesn't exist`  
**When**: Accessing `/teams/protocol-v/` before migrations run  
**Fix**:
```bash
python manage.py migrate organizations
```

**Root Cause**: URL accessed before `organizations.Team` model created by migrations.

---

### Issue 2: `competition_game_ranking_config` missing in admin

**Error**: Admin crashes when accessing Competition models  
**When**: Admin tries to register Competition models before table exists  
**Fix**: Already handled defensively in `apps/competition/admin.py`:

```python
try:
    from apps.competition.models import GameRankingConfig
    admin.site.register(GameRankingConfig, GameRankingConfigAdmin)
except Exception as e:
    print(f"⚠️ Could not register Competition admin: {e}")
```

**Prevention**: Always run `python manage.py migrate` before accessing admin.

---

### Issue 3: No games found when seeding passport schemas

**Error**: `❌ No games found. Run: python manage.py seed_games`  
**Fix**: Seed games first:
```bash
python manage.py seed_games
python manage.py seed_game_passport_schemas
```

---

### Issue 4: Tests try to run on Neon

**Error**: `❌ Tests cannot run on remote database: ep-lively-queen-a13dp7w6...`  
**Fix**: Set `DATABASE_URL_TEST` to local PostgreSQL:
```bash
export DATABASE_URL_TEST='postgresql://localhost:5432/deltacrown_test'
pytest
```

**Prevention**: `tests/conftest.py` enforces this automatically.

---

## 📁 Repository Structure (Post-Cleanup)

```
deltacrown/
├── README.md                      # Project overview
├── README_TECHNICAL.md            # This file - Bootstrap guide
├── requirements.txt               # Dependencies
├── manage.py                      # Django management
├── apps/                          # Application code
│   ├── games/
│   │   └── management/commands/
│   │       └── seed_games.py      # ✅ Idempotent games seeder
│   ├── user_profile/
│   │   └── management/commands/
│   │       ├── seed_game_passport_schemas.py  # ✅ Passport schemas
│   │       └── backfill_game_profiles.py      # ✅ NEW: User passports
│   ├── competition/
│   │   └── management/commands/
│   │       └── seed_game_ranking_configs.py   # ✅ Competition configs
│   ├── organizations/
│   │   └── models/
│   │       └── team.py             # organizations_team model
│   └── teams/
│       └── models/
│           └── team.py             # teams_team model (different!)
├── docs/
│   ├── ops/
│   │   └── neon-reset.md          # Neon reset workflow
│   └── vnext/
│       ├── README.md               # Historical docs index
│       ├── db-normalization-reset-report.md
│       └── ... (archived reports)
├── tests/
│   └── conftest.py                # ✅ Test DB protection
└── deltacrown/
    └── settings.py                # ✅ Simplified DB config
```

**Cleanup Summary**:
- ✅ Deleted 40+ temporary diagnostic scripts (check_*.py, fix_*.py, etc.)
- ✅ Deleted 30+ root-level reports (VNEXT_*.md, PHASE_*.md, etc.)
- ✅ Moved historical docs to `docs/vnext/`
- ✅ Root is now clean and production-like

---

## 🧪 Testing

**Local Test Database**:
```bash
# Setup (once)
createdb deltacrown_test
export DATABASE_URL_TEST='postgresql://localhost:5432/deltacrown_test'

# Run tests
pytest

# Tests will automatically refuse to run on Neon
```

**Test Protection**:
- `tests/conftest.py` enforces `DATABASE_URL_TEST` must be local
- Blocks `neon.tech`, requires `localhost` or `127.0.0.1` or `postgres:`
- Clear error message if misconfigured

---

## 🚀 Deployment

**Production Checklist**:
1. Set `DATABASE_URL` to production Neon connection string
2. Run `python manage.py migrate`
3. Run seed commands in order (games → schemas → configs)
4. Create superuser: `python manage.py createsuperuser`
5. Collect static files: `python manage.py collectstatic --noinput`
6. Run server: `gunicorn deltacrown.wsgi:application`

**Environment Variables**:
```bash
DATABASE_URL=postgresql://...neon.tech.../deltacrown?sslmode=require
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=deltacrown.com,www.deltacrown.com
```

---

## 💡 Key Principles

1. **DATABASE_URL for everything** (except tests)
2. **DATABASE_URL_TEST for tests** (local only, enforced)
3. **No migration guard** (Neon is dev database)
4. **All seed commands are idempotent**
5. **Seed order matters** (games → schemas → configs → user data)
6. **Tests refuse to run remotely** (safety)
7. **Clean repository** (no temporary scripts in root)

---

## 1. System Architecture Overview

DeltaCrown is a full-stack esports tournament platform built as a Django monolith with a service-oriented architecture. The platform supports the complete lifecycle of competitive gaming: player registration, team management, tournament organization, match execution, result verification, ranking calculation, payment processing, and community engagement.

### Core Technical Goals

**Scalability:** The system is designed to handle thousands of concurrent tournaments, tens of thousands of registered teams, and millions of player statistics records. Database optimization, caching strategies, and event-driven architecture support horizontal growth without architectural rewrites.

**Extensibility:** Game-specific behavior is abstracted through a configuration-driven game module system. New games can be added in minutes by creating database records, not code. Tournament formats are pluggable through a bracket generation engine that supports single/double elimination, round-robin, Swiss, and hybrid formats.

**Maintainability:** Business logic is isolated in service layers. Domain models enforce invariants. Audit trails track all state changes. The codebase follows strict separation of concerns with clear module boundaries and DTO-based inter-service communication.

---

## 2. High-Level Architecture

### Backend Architecture

DeltaCrown uses a **layered service architecture** within a Django monolith:

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│  (Django Views, Templates, REST APIs)   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Service Layer (Façades)         │
│  TournamentOps, RegistrationService,    │
│  TeamService, RankingService, etc.      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Domain Layer (Models)           │
│  Tournament, Team, Match, Player, etc.  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Data Layer (PostgreSQL)         │
│  Relational schema with JSONB for       │
│  flexible configurations                │
└─────────────────────────────────────────┘
```

**Why This Architecture:**

1. **Service Layer Isolation:** Business logic lives in services, not views. This enables reuse across REST APIs, admin actions, and background tasks.

2. **Domain-Driven Design:** Models enforce business rules through validation methods and custom managers. Complex workflows are orchestrated by services that coordinate multiple models.

3. **Event Bus Pattern:** Critical state changes emit domain events that other services consume asynchronously via Celery. This decouples systems (e.g., match completion triggers stats updates, notifications, and economy rewards without tight coupling).

4. **Adapter Pattern for External Integration:** Cross-app communication uses adapter layers (TeamAdapter, EconomyAdapter, UserAdapter) that wrap foreign models with DTOs, preventing tight coupling and circular dependencies.

### Frontend Architecture

The frontend uses **server-side rendering** with Django templates and progressive enhancement:

```
┌─────────────────────────────────────────┐
│         Base Templates                  │
│  (base.html, navigation, layouts)       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Page Templates                  │
│  (tournament_detail, team_dashboard,    │
│   bracket_view, registration_wizard)    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Component Partials              │
│  (cards, modals, forms, status pills)   │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Styling Layer                   │
│  Tailwind CSS (utility-first)           │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Interactivity Layer             │
│  Vanilla JS, AJAX, WebSocket updates    │
└─────────────────────────────────────────┘
```

**Why This Architecture:**

1. **Performance:** Server-side rendering delivers fully formed HTML. No client-side framework overhead. Fast time-to-interactive.

2. **Accessibility:** Semantic HTML with ARIA attributes. Works without JavaScript. Progressive enhancement for richer experiences.

3. **SEO-Friendly:** Search engines index tournament pages, team profiles, and player statistics directly.

4. **Maintainability:** Templates inherit from base layouts. Partials enforce component reuse. Clear separation between structure (HTML), presentation (Tailwind), and behavior (JS).

---

## 3. Core Subsystems

### Tournament Engine

The tournament engine manages the complete lifecycle from creation to completion:

**Models:**
- `Tournament`: Core metadata (name, game, format, prize pool, dates)
- `TournamentRegistration`: Player/team entries with eligibility validation
- `Bracket`: Tournament structure (single/double elimination, groups, etc.)
- `Match`: Individual games with scheduling, results, disputes

**Services:**
- `TournamentService`: CRUD operations, state transitions, validation
- `BracketService`: Generates bracket structures based on format and participant count
- `MatchService`: Scheduling, result submission, conflict resolution
- `RegistrationService`: Eligibility checks, payment verification, roster locking

**Key Design Decisions:**

1. **Soft Deletes:** Tournaments are never hard-deleted. `is_deleted=True` preserves historical data for analytics and audit.

2. **State Machines:** Tournaments transition through explicit states (DRAFT → OPEN → LIVE → COMPLETED) with validation guards preventing invalid transitions.

3. **JSONB Configuration:** Tournament-specific rules (round timings, tiebreaker logic, prize distribution) stored as JSONB, avoiding schema migrations for configuration changes.

4. **Event-Driven Match Results:** Match completion emits events consumed by stats aggregation, ranking recalculation, and economy reward services.

### Team & Player System

Teams are persistent professional entities, not temporary tournament groups.

**Models:**
- `Team`: Core team entity with game, region, roster limits
- `TeamMembership`: Role-based membership (Player, Captain, Manager, Coach)
- `TeamInvite`: Invitation workflow with expiration and accept/decline
- `PlayerStats`: Aggregated performance across all tournaments

**Services:**
- `TeamService`: Team creation, roster management, role permissions
- `MembershipService`: Invitation workflows, role transitions, validation
- `TeamRankingService`: Calculates team rankings based on tournament performance

**Key Design Decisions:**

1. **Role Hierarchy:** Teams have structured roles with distinct permissions. Captains manage rosters. Managers handle registrations. Coaches access analytics.

2. **Tournament Roster Locks:** When a team registers for a tournament, the roster is locked. No mid-tournament membership changes prevent competitive integrity issues.

3. **Cross-Game Support:** Teams persist across games. A team can compete in Valorant today and CS2 tomorrow without recreating entities.

4. **Sponsorship Integration:** Teams can add sponsors with logo visibility, creating revenue opportunities and brand partnerships.

### Ranking & Analytics

Rankings are calculated using a points-based system with configurable criteria.

**Models:**
- `RankingCriteria`: Defines point values for placements (1st = 100, 2nd = 80, etc.)
- `TeamRankingHistory`: Time-series snapshots of team rankings
- `PlayerStats`: Individual player performance across matches
- `MatchRecord`: Historical match data for trend analysis

**Services:**
- `RankingService`: Recalculates rankings after tournament completion
- `AnalyticsService`: Aggregates statistics for leaderboards
- `StatsAggregator`: Background task that processes match results into player/team stats

**Key Design Decisions:**

1. **Time-Series Snapshots:** Rankings are versioned over time, enabling historical analysis ("Team X was #3 in January 2025").

2. **Configurable Scoring:** Organizers can customize ranking criteria per game or region without code changes.

3. **Eventual Consistency:** Stats aggregation runs asynchronously. Rankings may lag behind live match results by seconds, trading real-time accuracy for database load reduction.

### Registration & Payments

Registration supports multiple payment methods with verification workflows.

**Models:**
- `TournamentRegistration`: Registration record with payment status
- `PaymentProof`: Uploaded proof for manual verification
- `PaymentVerification`: Admin approval workflow

**Services:**
- `RegistrationService`: Registration creation, eligibility validation, status updates
- `PaymentService`: Payment gateway integration (bKash, Nagad, cards)
- `VerificationService`: Admin tools for payment proof review

**Key Design Decisions:**

1. **Multi-Gateway Support:** Integrates local South Asian gateways (bKash, Nagad, Rocket) alongside international options (PayPal, Stripe).

2. **Manual Verification Option:** For cash/bank transfer, admins review uploaded screenshots before confirming registration.

3. **Registration States:** PENDING → PAYMENT_PENDING → CONFIRMED → CANCELLED. Clear state machine prevents race conditions.

4. **Idempotency:** Registration attempts are idempotent. Duplicate submissions for the same tournament are rejected.

### Disputes & Verification

Match results can be disputed by participants.

**Models:**
- `Dispute`: Dispute record with reason, evidence, status
- `DisputeEvidence`: File uploads (screenshots, VODs) supporting claims
- `DisputeResolution`: Admin decision with reasoning

**Services:**
- `DisputeService`: Dispute creation, evidence submission, status updates
- `ResolutionService`: Admin tools for reviewing and resolving disputes

**Key Design Decisions:**

1. **Evidence-Based:** Disputes require evidence uploads. No "he said, she said" without proof.

2. **Admin Moderation:** Disputes are reviewed by platform admins or tournament organizers with moderation permissions.

3. **Audit Trail:** All dispute actions are logged with timestamps and user IDs for accountability.

4. **Result Reversal Support:** Admins can override match results if disputes are upheld, triggering bracket and stats recalculation.

### Community & Content

Community features enable content creation and engagement.

**Models:**
- `CommunityPost`: User-generated posts with media
- `CommunityPostComment`: Threaded discussions
- `CommunityPostLike`: Social engagement tracking

**Services:**
- `CommunityService`: Post creation, moderation, trending calculation
- `ContentModerationService`: Spam detection, content flagging

**Key Design Decisions:**

1. **Media Uploads:** Posts support images, GIFs, and videos. File storage uses cloud-based CDN for performance.

2. **Engagement Metrics:** Posts track views, likes, comments, shares. Trending algorithm surfaces popular content.

3. **Moderation Tools:** Admins can flag, hide, or remove content violating community guidelines.

### Digital Economy (DeltaCoin)

DeltaCoin is the platform's internal currency.

**Models:**
- `DeltaCrownWallet`: User wallet with balance
- `DeltaCrownTransaction`: Transaction history with type, amount, metadata

**Services:**
- `WalletService`: Balance queries, transaction creation
- `RewardService`: Automatically awards coins for tournament participation, achievements

**Key Design Decisions:**

1. **Transaction Log Immutability:** Transactions are append-only. Balances are calculated from transaction history, preventing tampering.

2. **Event-Driven Rewards:** Match wins, tournament completions, and achievements emit events that trigger coin deposits.

3. **Spending Integration:** Coins can be spent in the DeltaStore (ecommerce) or for platform subscriptions.

---

## 4. Data & Domain Design

### Persistent Entities

DeltaCrown models the real-world esports ecosystem:

- **Players** have persistent identities across tournaments and teams
- **Teams** exist beyond individual tournaments, building reputation over time
- **Tournaments** create historical records that feed rankings and analytics
- **Matches** preserve competitive history for future analysis

### Lifecycle-Based Modeling

Entities transition through explicit states:

**Tournament Lifecycle:**
```
DRAFT → OPEN (registration) → CLOSED (pre-tournament) → LIVE (in-progress) → COMPLETED → ARCHIVED
```

**Match Lifecycle:**
```
SCHEDULED → IN_PROGRESS → PENDING_RESULTS → COMPLETED → DISPUTED → RESOLVED
```

**Registration Lifecycle:**
```
PENDING → PAYMENT_PENDING → CONFIRMED → CHECKED_IN → COMPLETED
```

State transitions enforce business rules. Attempting invalid transitions (e.g., completing a tournament while matches are unresolved) raises validation errors.

### Event-Based Workflows

Critical state changes emit domain events:

**Example: Match Completion Event**
```python
# Match result submitted
match.status = Match.Status.COMPLETED
match.save()

# Emit domain event
event_bus.emit('match.completed', {
    'match_id': match.id,
    'tournament_id': match.tournament_id,
    'winner_id': match.winner_id,
    'loser_id': match.loser_id,
    'score': match.score
})

# Asynchronous event handlers (Celery tasks)
# - StatsAggregator: Updates player/team statistics
# - RankingService: Recalculates tournament standings
# - EconomyService: Awards DeltaCoin to winners
# - NotificationService: Notifies participants of result
# - BracketService: Advances winner to next round
```

This decouples subsystems. Adding new post-match behaviors (e.g., streaming integration, social media posting) requires registering new event handlers, not modifying match completion logic.

### Audit & Traceability

All critical models include:
- `created_at` / `updated_at`: Timestamps for lifecycle tracking
- `created_by` / `updated_by`: User references for accountability
- `is_deleted` / `deleted_at`: Soft delete support for data retention
- `version`: Optimistic locking for concurrent update detection

Admin interfaces display full audit logs. Disputes reference specific versions of results for transparency.

---

## 5. Scalability & Extensibility

### Adding New Games

Games are configuration records, not code:

**Step 1: Create Game Record**
```python
Game.objects.create(
    name="Dota 2",
    slug="dota2",
    team_size=5,
    match_format="best_of_3",
    scoring_system={"type": "kills_and_objectives"},
    platform_requirements={"steam_id": "required"}
)
```

**Step 2: Define Team Composition Rules**
```python
GameTeamComposition.objects.create(
    game=dota2,
    min_players=5,
    max_players=5,
    substitute_limit=2
)
```

**Step 3: Configure Scoring Logic**
```python
GameScoringConfig.objects.create(
    game=dota2,
    scoring_fields=["kills", "deaths", "assists", "tower_kills", "roshan_kills"],
    win_condition={"type": "ancient_destroyed"}
)
```

**No Code Changes Required.** Tournament engine reads game configuration at runtime. New games integrate in 20 minutes.

### Supporting New Tournament Formats

Bracket generators are pluggable:

```python
class SwissBracketGenerator(BracketGenerator):
    def generate(self, participants, rounds):
        # Swiss pairing algorithm
        pass

# Register new generator
BracketService.register_generator('swiss', SwissBracketGenerator)
```

Organizers select formats from UI dropdown. Adding new formats requires implementing the generator interface, not modifying tournament models.

### Horizontal Growth Strategy

**Database Optimization:**
- Indexes on foreign keys, slug fields, and query-heavy columns
- JSONB GIN indexes for configuration queries
- Partitioning strategies for high-volume tables (MatchRecord, PlayerStats)

**Caching Layer:**
- Redis caching for leaderboards, team profiles, tournament listings
- Cache invalidation via event handlers (match completion clears rankings cache)

**Background Processing:**
- Celery workers handle stats aggregation, notification delivery, ranking recalculation
- Priority queues ensure critical tasks (match result processing) execute before analytics updates

**Read Replicas:**
- Analytics queries route to read replicas
- Write operations target primary database
- Eventual consistency acceptable for statistics

### API-First Design Considerations

While the current system uses server-side rendering, REST APIs are available for future integrations:

**Tournament API:**
- `GET /api/tournaments/` - List tournaments
- `POST /api/tournaments/{id}/register/` - Register for tournament
- `GET /api/tournaments/{id}/bracket/` - Fetch bracket data

**WebSocket API:**
- `/ws/tournament/{id}/` - Real-time bracket updates
- `/ws/match/{id}/` - Live match score updates

APIs use Django REST Framework with JWT authentication. OpenAPI/Swagger documentation auto-generates from serializers.

---

## 6. Security & Integrity

### Role-Based Permissions

Permissions follow the principle of least privilege:

**Tournament Organizers:**
- Create/edit their own tournaments
- Approve registrations for their events
- Submit/approve match results for their tournaments
- Cannot access other organizers' tournaments

**Team Captains:**
- Manage team roster (invite/remove members)
- Register team for tournaments
- Cannot modify other teams

**Players:**
- Join teams (with captain approval)
- Register for solo tournaments
- Submit match results (subject to organizer approval)

**Admins:**
- Full platform access
- Resolve disputes
- Override results if necessary
- Access audit logs

Permission checks occur at view, service, and model layers. Admin actions are logged for accountability.

### Dispute Handling

Disputes prevent result manipulation:

1. **Result Submission:** Player submits match result
2. **Opponent Review:** Opponent has 24-hour window to accept or dispute
3. **Auto-Accept:** If opponent doesn't respond, result auto-confirms after timeout
4. **Dispute Evidence:** Disputing party must upload evidence (screenshots, VOD links)
5. **Admin Review:** Platform moderators review evidence and make final ruling
6. **Result Finalization:** Ruling is binding. Losing party cannot re-dispute

This workflow prevents "rage disputes" while ensuring legitimate grievances are heard.

### Audit Logs

All state-changing operations are logged:

```python
AuditLog.objects.create(
    user=request.user,
    action='match.result.override',
    resource_type='Match',
    resource_id=match.id,
    changes={'winner': old_winner_id, 'new_winner': new_winner_id},
    reason='Dispute upheld - evidence showed incorrect initial result'
)
```

Audit logs are immutable. Admins cannot delete their own actions. This creates accountability and prevents insider tampering.

### Anti-Tampering Mechanisms

**Result Integrity:**
- Match results include hash of participant IDs + scores + timestamp
- Bracket progression validates hash chains to detect retroactive edits

**Transaction Integrity:**
- DeltaCoin transactions are append-only
- Balance calculations sum transaction history
- Attempting to edit past transactions invalidates subsequent balances

**Roster Lock Enforcement:**
- Teams cannot modify rosters after tournament registration closes
- Attempting to add/remove players during active tournaments raises database constraint errors

---

## 7. Operational Tooling

### Admin Interfaces

Django Admin provides power-user interfaces for platform management:

**Tournament Admin:**
- Bulk publish/archive tournaments
- Override registration limits
- Force-complete stuck tournaments
- Export participant lists as CSV

**Team Admin:**
- View team hierarchies (captain, manager, players, coaches)
- Resolve ownership disputes
- Merge duplicate teams
- Bulk actions for team verification

**Payment Verification Dashboard:**
- Queue of pending payment proofs
- Side-by-side comparison of proof vs. expected amount
- One-click approve/reject with notes
- Filtering by payment method, date range

**Dispute Resolution Console:**
- Queue of active disputes sorted by age
- Evidence viewer (images, videos, chat logs)
- Decision templates for common dispute types
- Resolution history per disputer (to flag serial disputers)

### Moderation Workflows

Content moderation uses a flag-and-review system:

1. **User Flags Content:** Reports inappropriate post/comment
2. **Auto-Hide Threshold:** Content with 5+ flags auto-hides pending review
3. **Moderator Review:** Admin reviews flagged content
4. **Action Options:**
   - Approve (unflag + unhide)
   - Remove (soft delete + log reason)
   - Ban User (if pattern of violations)
5. **Appeal Process:** Users can appeal removals via support ticket

Moderators have access to user history (past flags, bans, appeals) to inform decisions.

### Debugging & Monitoring Approach

**Logging Strategy:**
- INFO: Normal operations (tournament created, user registered)
- WARNING: Recoverable issues (payment gateway timeout, retried successfully)
- ERROR: Failures requiring intervention (dispute resolution failed, match result validation error)

Logs are structured JSON for machine parsing:

```json
{
  "timestamp": "2025-01-10T14:23:45Z",
  "level": "ERROR",
  "service": "RegistrationService",
  "action": "create_registration",
  "user_id": 12345,
  "tournament_id": 67890,
  "error": "Team roster exceeds tournament limit (6 > 5)",
  "traceback": "..."
}
```

**Metrics Collection:**
- Prometheus metrics for request counts, error rates, response times
- Custom business metrics (registrations/hour, matches completed/day, dispute resolution time)
- Grafana dashboards for real-time visualization

**Error Tracking:**
- Sentry integration for exception monitoring
- Automatic ticket creation for recurring errors
- Weekly error digest emails to engineering team

---

## 8. Development Philosophy

### Why Stability Over Rewrites

DeltaCrown has 17,000+ lines of production code. Rewriting would:
- Introduce new bugs in stable systems
- Delay feature development by 6-12 months
- Risk data migration issues
- Discard institutional knowledge embedded in code

Instead, the platform evolves through **incremental modernization**:
- Refactor small modules one at a time
- Maintain backward compatibility during transitions
- Deploy changes gradually with feature flags
- Comprehensive testing before replacing legacy code

### Why Incremental Modernization

**Example: Game Configuration Refactor**

**Before (Legacy):**
```python
# Hardcoded game logic in views
if tournament.game.slug == 'valorant':
    team_size = 5
elif tournament.game.slug == 'pubg':
    team_size = 4
# ... 11 more if-statements
```

**After (Configuration-Driven):**
```python
# Database-driven configuration
team_size = tournament.game.team_composition.min_players
```

**Migration Path:**
1. Create `GameTeamComposition` model
2. Populate with existing game configurations
3. Update services to read from database
4. Add tests comparing old vs. new logic
5. Deploy with feature flag (`USE_GAME_CONFIG_V2`)
6. Monitor for discrepancies
7. Remove hardcoded logic after validation period

This approach minimizes risk while continuously improving the codebase.

### Design Decisions Explained

**Why Monolith (Not Microservices)?**

DeltaCrown started as a monolith and remains one because:
- **Shared Transactions:** Tournament registration involves Teams, Economy, Notifications. Distributed transactions are complex.
- **Simplified Deployment:** Single deployment artifact reduces operational overhead.
- **Development Speed:** Cross-service changes don't require coordinating multiple repos.

Microservices may be appropriate in the future (e.g., analytics as separate service), but premature decomposition creates complexity without commensurate benefits.

**Why Server-Side Rendering (Not SPA)?**

Server-side rendering was chosen because:
- **SEO Requirements:** Tournament pages must rank in Google for discoverability.
- **Performance:** Server-rendered HTML loads faster than SPA hydration on mobile devices.
- **Simplicity:** No need for complex state management libraries, API versioning contracts.

Progressive enhancement adds interactivity (AJAX form submissions, real-time updates) without sacrificing base functionality.

**Why PostgreSQL (Not NoSQL)?**

PostgreSQL supports DeltaCrown's needs because:
- **Relational Integrity:** Foreign keys enforce referential integrity (teams can't register for deleted tournaments).
- **JSONB Flexibility:** Configuration data uses JSONB for schema-less storage where appropriate.
- **Battle-Tested:** 25+ years of production use. Excellent tooling, monitoring, backup strategies.

NoSQL databases lack ACID transactions and relational constraints critical for competitive integrity.

---

## 9. Future Evolution

### Mobile Apps

Mobile apps (iOS/Android) will use the existing REST APIs:

**Architecture:**
- React Native for cross-platform development
- JWT authentication (already implemented)
- WebSocket integration for live match updates
- Offline mode with local SQLite cache

**No Backend Changes Required.** APIs are version-controlled (`/api/v1/`, `/api/v2/`) to support mobile app iterations without breaking existing integrations.

### Microservices (Optional)

If scale demands, analytics could become a microservice:

**Current (Monolith):**
```
Tournament → Match → StatsAggregator (Celery) → PlayerStats
```

**Future (Microservice):**
```
Tournament → EventBus → Analytics Service (separate deployment)
                       ↓
                  Time-Series DB (InfluxDB)
                       ↓
                  Analytics API
```

**Benefits:**
- Horizontal scaling of analytics workers independent of core platform
- Specialized database (time-series DB) optimized for statistics queries
- Isolated failures (analytics downtime doesn't impact tournament operations)

**Migration Path:**
- Create analytics service as new Django app
- Dual-write to both monolith and service during transition
- Validate data consistency
- Migrate read queries to new service
- Deprecate monolith analytics models

### Frontend Modernization Paths

Potential frontend evolutions:

**Path 1: HTMX Integration (Incremental)**
- Replace AJAX calls with HTMX attributes
- Server returns HTML fragments, not JSON
- Maintains server-side rendering benefits
- Reduces JavaScript complexity

**Path 2: React Components (Hybrid)**
- Server-rendered pages remain Django templates
- Complex UI components (bracket visualizer, match scheduler) use React islands
- Next.js for organizer console (separate React app)
- Gradual migration page-by-page

**Path 3: Full SPA (Major Rewrite)**
- Next.js/React for all pages
- Django backend becomes pure API
- Significant frontend rearchitecture
- Only justified if SEO and performance can be maintained

**Recommendation:** Path 1 (HTMX) provides immediate benefits without architectural upheaval. Path 2 is viable for power-user tools (organizer console). Path 3 is not recommended unless business requirements fundamentally change.

---

## Conclusion

DeltaCrown is a production-grade esports platform architected for long-term stability, incremental evolution, and operational excellence. The system prioritizes:

- **Data Integrity:** Audit logs, soft deletes, state machines prevent data loss and manipulation
- **Extensibility:** Configuration-driven game modules and pluggable bracket generators enable growth without rewrites
- **Developer Experience:** Service layers, event buses, and clear domain boundaries create maintainable code
- **Operational Tooling:** Comprehensive admin interfaces and moderation workflows support platform management at scale

The architecture balances pragmatism (monolith, server-side rendering) with modern patterns (event-driven workflows, API-first services) to deliver a reliable, scalable esports infrastructure.

**Next Steps for Technical Review:**

1. Review [docs/architecture/FINAL_COMPLETION_AUDIT.md](docs/architecture/FINAL_COMPLETION_AUDIT.md) for system completion status
2. Explore [Documents/Planning/INDEX_MASTER_NAVIGATION.md](Documents/Planning/INDEX_MASTER_NAVIGATION.md) for comprehensive design documentation
3. Examine [apps/core/README.md](apps/core/README.md) for service architecture patterns
4. Review [frontend_sdk/README.md](frontend_sdk/README.md) for API integration contracts

---

**For questions about this architecture, contact the development team via the repository.**