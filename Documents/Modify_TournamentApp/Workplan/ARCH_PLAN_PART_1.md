# DeltaCrown Architecture & Vision Plan

**Document Purpose**: High-level architectural vision for DeltaCrown as a professional, multi-game esports platform.

**Created**: December 8, 2025  
**Scope**: Platform vision, domain architecture, design principles, target state

---

## 1. Platform Vision

### 1.1 What is DeltaCrown?

DeltaCrown is a **comprehensive esports tournament platform** that enables competitive gaming communities to organize, participate in, and spectate tournaments across **11 different games** (Valorant, PUBG Mobile, Free Fire, CS2, MLBB, COD Mobile, Apex Legends, League of Legends, Rocket League, FIFA, Fortnite).

**Core Value Propositions**:
- **For Players**: Discover tournaments, register easily, track stats, earn rewards, climb leaderboards
- **For Teams**: Manage rosters, enter team tournaments, build competitive reputation
- **For Organizers**: Create and manage tournaments with flexible formats, automated brackets, payment collection
- **For Spectators**: Follow live matches, view brackets, track favorite teams/players
- **For Admins**: Monitor platform health, handle disputes, enforce rules, manage economy

---

### 1.2 User Experience Principles

#### Players
- **"One-Click Registration"**: Auto-fill from verified profile, lock critical fields, instant eligibility check
- **"Smart Stats"**: Every match updates personal history, win rates, rankings automatically
- **"Transparent Rewards"**: Clear prize pools, instant DeltaCoin payouts, downloadable certificates
- **"Multi-Game Profile"**: Single account for all 11 games, unified wallet, cross-game leaderboards

#### Teams
- **"Effortless Management"**: Invite members, assign roles, register for tournaments as a team
- **"Team Identity"**: Verified team badges, team stats (W/L records, tournament history)
- **"Competitive Progression"**: Team rankings, ELO ratings, achievement system

#### Organizers
- **"Tournament Creation Wizard"**: Step-by-step setup (game, format, rules, prizes, schedule)
- **"Automated Operations"**: Bracket generation, match scheduling, result tracking, prize distribution
- **"Payment Flexibility"**: DeltaCoin (instant) or manual payment uploads
- **"Real-Time Control"**: Live tournament dashboard, dispute handling, participant communication

#### Admins
- **"Platform Oversight"**: Global dashboard (active tournaments, revenue, user growth)
- **"Moderation Tools"**: Review payments, handle disputes, enforce community rules
- **"Economy Management"**: Monitor DeltaCoin circulation, adjust pricing, track payouts
- **"Analytics & Insights"**: Platform health metrics, game popularity trends, revenue reports

---

## 2. Architecture Overview

### 2.1 Domain Areas & Responsibilities

DeltaCrown is organized into **7 core domain areas**, each with clear ownership and boundaries.

```
┌─────────────────────────────────────────────────────────────┐
│ DOMAIN AREAS (Apps)                                         │
├─────────────────────────────────────────────────────────────┤
│ 1. Games           - Game configurations, identity rules    │
│ 2. Teams           - Team management, rosters, stats        │
│ 3. Tournaments     - Core tournament/match/bracket logic    │
│ 4. TournamentOps   - Orchestration, workflows, operations   │
│ 5. Economy         - DeltaCoin wallet, payments, prizes     │
│ 6. Users/Profile   - User accounts, profiles, verification  │
│ 7. Leaderboards    - Rankings, analytics, stats (planned)   │
└─────────────────────────────────────────────────────────────┘
```

---

#### 1. Games Domain (`apps/games/`)

**Owns**:
- Game catalog (11 games: Valorant, PUBG, CS2, etc.)
- Game-specific configurations:
  - Player identity fields (Riot ID, Steam ID, PUBG ID, etc.)
  - Team size requirements (5v5, 4v4, solo)
  - Validation rules (rank restrictions, server locks)
  - Tournament formats (Single Elimination, Round Robin, etc.)
- Platform integration configs (OAuth, API keys)

**Responsibilities**:
- Provide game metadata to other domains
- Validate game-specific identities (Riot ID format, Steam ID length)
- Define eligibility rules templates (min rank, region locks)

**Does NOT Own**:
- Tournament records (owned by Tournaments domain)
- Team records (owned by Teams domain)
- User game accounts (owned by Users domain, validated by Games)

**API Surface**:
```python
# games/services/game_service.py
class GameService:
    @staticmethod
    def get_game_by_slug(slug: str) -> Game
    
    @staticmethod
    def get_identity_validation_rules(game_id: int) -> List[IdentityConfig]
    
    @staticmethod
    def get_supported_tournament_formats(game_id: int) -> List[str]
    
    @staticmethod
    def validate_player_identity(game_id: int, identity_data: dict) -> ValidationResult
```

---

#### 2. Teams Domain (`apps/teams/`)

**Owns**:
- Team records (name, logo, verified status)
- Team rosters (members, captain, roles)
- Team analytics (matches played, W/L record, tournament count)
- Team invitations and membership requests

**Responsibilities**:
- Team CRUD operations
- Membership management (invite, join, kick)
- Team statistics tracking (via event handlers)
- Team verification/badges

**Does NOT Own**:
- Tournament registrations (owned by Tournaments, references team_id)
- Match results (owned by Tournaments, updates team stats via events)

**API Surface**:
```python
# teams/services/team_service.py
class TeamService:
    @staticmethod
    def create_team(user_id: int, team_data: dict) -> Team
    
    @staticmethod
    def get_team(team_id: int) -> Team
    
    @staticmethod
    def check_tournament_eligibility(team_id: int, tournament_id: int) -> bool
    
    @staticmethod
    def has_tournament_permission(user_id: int, team_id: int) -> bool

# teams/services/team_stats_service.py
class TeamStatsService:
    @staticmethod
    @event_handler(MatchCompletedEvent)
    def record_match_result(team_id: int, match_id: int, result: str)
    
    @staticmethod
    @event_handler(TournamentCompletedEvent)
    def increment_tournaments_won(team_id: int)
```

---

#### 3. Tournaments Domain (`apps/tournaments/`)

**Owns**:
- Tournament records (name, game, format, rules, prizes)
- Registration records (user/team registrations)
- Bracket/match structure (bracket trees, match pairings)
- Match results (scores, winners, disputes)
- Tournament results (final placements)
- Payment records (entry fees, proof uploads)
- Certificates (PDF/PNG generation)

**Responsibilities**:
- Tournament lifecycle management (DRAFT → PUBLISHED → LIVE → COMPLETED)
- Registration workflows (eligibility checks, payment validation)
- Bracket generation (single elimination, double elimination, round robin)
- Match state management (SCHEDULED → CHECK_IN → LIVE → COMPLETED)
- Result recording and validation
- Certificate generation

**Does NOT Own**:
- Wallet transactions (owned by Economy, triggered by Tournaments)
- Team/user stats updates (owned by Teams/Users, triggered via events)
- Leaderboard rankings (owned by Leaderboards, triggered via events)

**API Surface**:
```python
# tournaments/services/tournament_service.py
class TournamentService:
    @staticmethod
    def create_tournament(organizer_id: int, tournament_data: dict) -> Tournament
    
    @staticmethod
    def publish_tournament(tournament_id: int) -> Tournament
    
    @staticmethod
    def get_tournament(tournament_id: int) -> Tournament

# tournaments/services/registration_service.py
class RegistrationService:
    @staticmethod
    def create_registration(tournament_id: int, user_id: int, data: dict) -> Registration
    
    @staticmethod
    def check_eligibility(tournament_id: int, user_id: int, team_id: int = None) -> EligibilityResult

# tournaments/services/match_service.py
class MatchService:
    @staticmethod
    def create_match(tournament_id: int, participant1_id: int, participant2_id: int) -> Match
    
    @staticmethod
    def record_result(match_id: int, result_data: dict) -> Match
    
    @staticmethod
    def confirm_result(match_id: int, confirmed_by: User) -> Match

# tournaments/services/bracket_service.py
class BracketService:
    @staticmethod
    def generate_bracket(tournament_id: int) -> List[Match]
    
    @staticmethod
    def advance_winner(match_id: int) -> Match
```

---

#### 4. TournamentOps Domain (`apps/tournament_ops/`)

**Owns**:
- High-level workflows and orchestration
- Cross-domain coordination logic
- Business process implementations
- Event publishing (domain events)

**Responsibilities**:
- Orchestrate multi-service workflows:
  - Complete registration flow (eligibility → registration → payment → notification)
  - Tournament finalization (winner determination → prizes → certificates → stats)
  - Payment verification workflow (admin approval → wallet update → confirmation)
- Coordinate between domains without creating tight coupling
- Publish domain events for async updates
- Serve as the "glue" layer for complex operations

**Does NOT Own**:
- Core domain logic (delegated to domain services)
- Direct model access (uses adapters/services)

**API Surface**:
```python
# tournament_ops/services/ops_service.py
class TournamentOpsService:
    @staticmethod
    @transaction.atomic
    def process_registration_workflow(
        tournament_id: int,
        user_id: int,
        registration_data: dict,
        payment_method: str = None
    ) -> Registration:
        """
        Complete registration orchestration:
        1. Check eligibility (via adapters)
        2. Create registration (RegistrationService)
        3. Process payment (EconomyAdapter)
        4. Update user stats (UserAdapter)
        5. Send notifications (NotificationService)
        6. Publish event (EventBus)
        """
        pass
    
    @staticmethod
    @transaction.atomic
    def finalize_tournament(tournament_id: int) -> Tournament:
        """
        Complete tournament finalization:
        1. Determine winner (WinnerService)
        2. Process payouts (PayoutService + EconomyAdapter)
        3. Generate certificates (CertificateService)
        4. Update team/user stats (via events)
        5. Update leaderboards (via events)
        6. Send notifications (NotificationService)
        """
        pass
    
    @staticmethod
    @transaction.atomic
    def verify_manual_payment(payment_id: int, admin_id: int, approved: bool) -> Payment:
        """
        Manual payment verification workflow:
        1. Update payment status (PaymentService)
        2. Update registration status (RegistrationService)
        3. Update wallet if approved (EconomyAdapter)
        4. Send notification (NotificationService)
        5. Publish event (EventBus)
        """
        pass
```

---

#### 5. Economy Domain (`apps/economy/`)

**Owns**:
- DeltaCoin wallet records (user balances)
- Wallet transactions (deposits, withdrawals, transfers)
- Payment gateway integrations (future: Stripe, PayPal)
- Pricing configurations (entry fees, prizes)

**Responsibilities**:
- Wallet CRUD operations (create, fund, deduct)
- Transaction logging (audit trail)
- Balance validation (prevent overdrafts)
- Payment processing (DeltaCoin instant transfers)

**Does NOT Own**:
- Tournament entry fees (owned by Tournaments, processed via Economy)
- Prize payouts (triggered by TournamentOps, executed by Economy)

**API Surface**:
```python
# economy/services/wallet_service.py
class WalletService:
    @staticmethod
    def get_wallet(user_id: int) -> DeltaCrownWallet
    
    @staticmethod
    def get_balance(user_id: int) -> Decimal
    
    @staticmethod
    @transaction.atomic
    def deduct_funds(
        user_id: int, 
        amount: Decimal, 
        reason: str,
        idempotency_key: str = None
    ) -> Transaction
    
    @staticmethod
    @transaction.atomic
    def add_funds(
        user_id: int, 
        amount: Decimal, 
        reason: str,
        idempotency_key: str = None
    ) -> Transaction
    
    @staticmethod
    def validate_balance(user_id: int, required_amount: Decimal) -> bool
```

---

#### 6. Users/Profile Domain (`apps/accounts/`, `apps/user_profile/`)

**Owns**:
- User authentication (login, registration, password reset)
- User profiles (name, email, phone, Discord, etc.)
- Game account identities (Riot ID, Steam ID, PUBG ID, etc.)
- Account verification (email, phone, platform OAuth)
- User tournament statistics (new: tournaments entered, wins, match records)
- User tournament history (new: per-tournament participation records)

**Responsibilities**:
- User CRUD operations
- Profile data management
- Verification workflows
- User stats tracking (via event handlers)

**Does NOT Own**:
- Tournament registrations (owned by Tournaments, references user_id)
- Team memberships (owned by Teams, references user_id)

**API Surface**:
```python
# user_profile/services/profile_service.py
class ProfileService:
    @staticmethod
    def get_profile(user_id: int) -> UserProfile
    
    @staticmethod
    def update_game_identity(user_id: int, game_slug: str, identity_value: str) -> UserProfile
    
    @staticmethod
    def verify_email(user_id: int, token: str) -> bool
    
    @staticmethod
    def verify_phone(user_id: int, code: str) -> bool

# user_profile/services/user_stats_service.py (NEW)
class UserStatsService:
    @staticmethod
    @event_handler(RegistrationCompletedEvent)
    def increment_tournaments_entered(user_id: int)
    
    @staticmethod
    @event_handler(MatchCompletedEvent)
    def record_match_result(user_id: int, match_id: int, result: str)
    
    @staticmethod
    @event_handler(TournamentCompletedEvent)
    def record_tournament_completion(user_id: int, tournament_id: int, placement: str)
```

---

#### 7. Leaderboards/Analytics Domain (`apps/leaderboards/`) - **PLANNED**

**Owns**:
- Global leaderboards (top players, top teams per game)
- ELO/MMR rating calculations
- Ranking algorithms (tournament points, win rates)
- Platform-wide analytics (tournament trends, game popularity)

**Responsibilities**:
- Leaderboard calculations (triggered by events)
- Ranking updates (after tournament completion)
- Analytics dashboards (for admins)

**Does NOT Own**:
- Raw match/tournament data (owned by Tournaments)
- Team/user stats (owned by Teams/Users, consumed by Leaderboards)

**API Surface**:
```python
# leaderboards/services/ranking_service.py (PLANNED)
class RankingService:
    @staticmethod
    @event_handler(MatchCompletedEvent)
    def update_elo_ratings(winner_id: int, loser_id: int)
    
    @staticmethod
    @event_handler(TournamentCompletedEvent)
    def award_tournament_points(tournament_id: int)
    
    @staticmethod
    def get_global_leaderboard(game_id: int, limit: int = 100) -> List[LeaderboardEntry]
    
    @staticmethod
    def get_user_rank(user_id: int, game_id: int) -> int
```

---

### 2.2 Cross-Domain Communication

**Key Principle**: **No direct model imports across domains**. All cross-domain communication happens via:
1. **Service calls** (via adapters)
2. **Domain events** (async updates)
3. **DTOs** (data transfer objects, not model instances)

---

#### Communication Pattern 1: Service Adapters (Synchronous)

**Purpose**: Request data or trigger actions in other domains during request/response cycle.

**Example**: Tournament registration needs team data

```python
# ❌ BAD: Direct model import (tight coupling)
from apps.teams.models import Team
team = Team.objects.get(id=team_id)

# ✅ GOOD: Via adapter (loose coupling)
from tournaments.adapters.team_adapter import TeamAdapter
team_data = TeamAdapter.get_team(team_id)  # Returns TeamDTO, not Team model
```

**Adapter Implementation**:
```python
# tournaments/adapters/team_adapter.py
from apps.teams.services import TeamService

class TeamAdapter:
    """Adapter for teams domain integration."""
    
    @staticmethod
    def get_team(team_id: int) -> TeamDTO:
        """Get team data without importing Team model."""
        team = TeamService.get_team(team_id)
        return TeamDTO(
            id=team.id,
            name=team.name,
            captain_id=team.captain_id,
            member_ids=[m.user_id for m in team.members.all()],
            game=team.game,
            is_verified=team.is_verified
        )
    
    @staticmethod
    def check_permission(user_id: int, team_id: int) -> bool:
        """Check if user can register team for tournaments."""
        return TeamService.has_tournament_permission(user_id, team_id)
```

**Benefits**:
- ✅ Teams domain can refactor Team model without breaking Tournaments
- ✅ Clear API contract via DTOs
- ✅ Easy to mock in tests
- ✅ No circular dependencies

---

#### Communication Pattern 2: Domain Events (Asynchronous)

**Purpose**: Notify other domains of important state changes without creating tight coupling.

**Example**: Match completion triggers multiple updates

```python
# 1. Tournaments domain publishes event
@transaction.atomic
def confirm_match_result(match_id: int):
    match = Match.objects.select_for_update().get(id=match_id)
    match.state = Match.COMPLETED
    match.save()
    
    # Publish event (no knowledge of handlers)
    events.publish(MatchCompletedEvent(
        match_id=match.id,
        tournament_id=match.tournament_id,
        winner_id=match.winner_id,
        loser_id=match.loser_id,
    ))

# 2. Teams domain listens to event (handler in teams app)
@event_handler(MatchCompletedEvent)
def update_team_stats(event: MatchCompletedEvent):
    TeamStatsService.record_match_result(event.winner_id, 'win', event.match_id)
    TeamStatsService.record_match_result(event.loser_id, 'loss', event.match_id)

# 3. Leaderboards domain listens to event (handler in leaderboards app)
@event_handler(MatchCompletedEvent)
def update_rankings(event: MatchCompletedEvent):
    RankingService.update_elo_ratings(event.winner_id, event.loser_id)

# 4. Economy domain listens to event (handler in economy app)
@event_handler(MatchCompletedEvent)
def award_match_rewards(event: MatchCompletedEvent):
    reward = calculate_match_reward(event.tournament_id)
    WalletService.add_funds(event.winner_id, reward, f'Match win: {event.match_id}')
```

**Benefits**:
- ✅ Tournaments domain doesn't know about Teams/Leaderboards/Economy
- ✅ Easy to add new handlers (e.g., AchievementService, NotificationService)
- ✅ Handlers can be async (non-blocking)
- ✅ Event log serves as audit trail

---

#### Communication Rules

| From Domain | To Domain | Method | Example |
|-------------|-----------|--------|---------|
| Tournaments | Teams | Adapter (sync) | Get team data for registration |
| Tournaments | Users | Adapter (sync) | Get user profile for auto-fill |
| Tournaments | Economy | Adapter (sync) | Deduct entry fee |
| Tournaments | Teams | Event (async) | Update team stats after match |
| Tournaments | Users | Event (async) | Update user stats after match |
| Tournaments | Leaderboards | Event (async) | Update rankings after tournament |
| TournamentOps | All | Adapter (sync) | Orchestrate workflows |
| TournamentOps | All | Event (async) | Publish domain events |

---

## 3. Design Principles

### Principle 1: Single Source of Truth

**Rule**: Each piece of data has ONE authoritative owner.

**Examples**:
- ✅ Team name → Owned by `teams.Team` model
- ✅ User email → Owned by `accounts.User` model
- ✅ Tournament status → Owned by `tournaments.Tournament` model
- ❌ Don't duplicate team name in `tournaments.Registration` (use team_id reference)

**Benefits**:
- No data sync issues
- Clear update ownership
- Simplified debugging

---

### Principle 2: Configuration Over Code

**Rule**: Game-specific logic should be database configuration, not hardcoded if-else statements.

**Examples**:
- ✅ Game identity fields → `GamePlayerIdentityConfig` model
- ✅ Eligibility rules → `EligibilityRule` model
- ✅ Prize distribution → Tournament.prize_distribution JSONB
- ❌ Don't hardcode: `if game_slug == 'valorant': field = 'riot_id'`

**Benefits**:
- Add new games without code changes
- Organizers can customize rules via admin
- Easier testing (change config, not code)

---

### Principle 3: Event-Driven Updates

**Rule**: State changes trigger events; downstream updates happen via event handlers.

**Examples**:
- ✅ Match completion → Event → Update stats, rankings, history
- ✅ Tournament completion → Event → Award prizes, generate certificates
- ✅ Payment verification → Event → Update registration status
- ❌ Don't call `TeamStatsService.update()` directly in match confirmation logic

**Benefits**:
- Decoupled services
- No forgotten updates
- Extensible (add handlers without changing trigger code)
- Audit trail via event log

---

### Principle 4: Service Boundaries

**Rule**: Cross-domain communication only via services/adapters, never direct model imports.

**Examples**:
- ✅ `TeamAdapter.get_team(team_id)` → Returns DTO
- ✅ `UserAdapter.get_profile(user_id)` → Returns DTO
- ❌ `from apps.teams.models import Team` in tournaments app

**Benefits**:
- Loose coupling
- Clear API contracts
- Easy to refactor internals without breaking consumers
- Mockable for testing

---

### Principle 5: API-First Design

**Rule**: Build RESTful API endpoints for all core workflows (even if only web UI exists today).

**Examples**:
- ✅ `POST /api/v1/tournaments/{id}/registrations/` (create registration)
- ✅ `POST /api/v1/matches/{id}/results/` (submit match result)
- ✅ `POST /api/v1/tournaments/{id}/finalize/` (determine winner)

**Benefits**:
- Mobile app ready (future)
- Third-party integrations (Discord bots, Twitch overlays)
- OpenAPI documentation
- Easier to migrate to microservices

---

### Principle 6: Immutable Critical Fields

**Rule**: Once verified, critical identity fields (email, game IDs) should be locked.

**Examples**:
- ✅ Lock Riot ID after OAuth verification
- ✅ Lock email after email verification
- ✅ Lock team name for verified teams
- ❌ Don't allow editing verified email (require re-verification)

**Benefits**:
- Prevent fraud (account hijacking, impersonation)
- Trust in tournament integrity
- Clear audit trail (who verified what, when)

---

### Principle 7: Idempotent Operations

**Rule**: Critical operations should be safely retryable (same input = same result, no duplicates).

**Examples**:
- ✅ Wallet deductions with `idempotency_key` (no double-charging)
- ✅ Certificate generation with existing certificate check (no duplicates)
- ✅ Event handlers with `processed` flag (no duplicate stats updates)
- ❌ Don't increment `matches_played` without checking if already counted

**Benefits**:
- Safe retries on failure
- No duplicate charges/rewards
- Predictable behavior

---

### Principle 8: Fail Fast with Clear Errors

**Rule**: Validate early, provide specific error messages, prevent invalid state.

**Examples**:
- ✅ Check eligibility BEFORE creating registration record
- ✅ Validate wallet balance BEFORE tournament creation (if using DeltaCoin prizes)
- ✅ Return clear errors: "Minimum rank: Diamond (you are Gold)"
- ❌ Don't create registration then fail at payment step (orphaned records)

**Benefits**:
- Better UX (early feedback)
- Fewer orphaned/inconsistent records
- Easier debugging

---

### Principle 9: Testability

**Rule**: Design services to be unit-testable (mock dependencies, clear inputs/outputs).

**Examples**:
- ✅ Services accept DTOs, return DTOs (no model coupling)
- ✅ Adapters are interfaces (mockable)
- ✅ Event handlers are pure functions (given event, update state)
- ✅ Use dependency injection (pass services as parameters)

**Benefits**:
- Fast unit tests (no database hits)
- Reliable tests (no external dependencies)
- Confidence in refactoring

---

### Principle 10: Observable Operations

**Rule**: Log important events, track metrics, enable monitoring.

**Examples**:
- ✅ Log all domain events to `DomainEvent` table
- ✅ Track metrics: registration completion rate, payment approval time
- ✅ Alert on anomalies: >5% payment rejections, >3 event handler failures
- ✅ Store event handler retry count for debugging

**Benefits**:
- Audit trail for debugging
- Platform health visibility
- Early detection of issues
- Data-driven decisions

---

## 4. Target Architecture Diagram

### 4.1 Domain Interaction Map

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │  Web Views │  │  REST API  │  │  GraphQL   │  │  Admin UI  │        │
│  │  (Django)  │  │   (DRF)    │  │  (Future)  │  │  (Django)  │        │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘        │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                                  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  TournamentOps Service (apps/tournament_ops/)                     │  │
│  │   - process_registration_workflow()                               │  │
│  │   - finalize_tournament()                                         │  │
│  │   - verify_manual_payment()                                       │  │
│  │   - handle_dispute_resolution()                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  TOURNAMENTS  │  │     TEAMS     │  │     USERS     │
│    DOMAIN     │  │    DOMAIN     │  │    DOMAIN     │
├───────────────┤  ├───────────────┤  ├───────────────┤
│ - Tournament  │  │ - Team        │  │ - User        │
│ - Registration│  │ - Membership  │  │ - Profile     │
│ - Match       │  │ - TeamStats   │  │ - UserStats   │
│ - Bracket     │  │               │  │ - GameAccount │
│ - Payment     │  │               │  │               │
│ - Certificate │  │               │  │               │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│     GAMES     │  │    ECONOMY    │  │  LEADERBOARDS │
│    DOMAIN     │  │    DOMAIN     │  │    DOMAIN     │
├───────────────┤  ├───────────────┤  ├───────────────┤
│ - Game        │  │ - Wallet      │  │ - Rankings    │
│ - IdentityRule│  │ - Transaction │  │ - ELO         │
│ - FormatConfig│  │ - PaymentGW   │  │ - Leaderboard │
│ - Validation  │  │               │  │ - Analytics   │
└───────────────┘  └───────────────┘  └───────────────┘
        │                  │                  │
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      EVENT BUS (RabbitMQ / Redis)                │
│  - MatchCompletedEvent                                           │
│  - TournamentCompletedEvent                                      │
│  - RegistrationCompletedEvent                                    │
│  - PaymentVerifiedEvent                                          │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │PostgreSQL│  │  Redis   │  │  S3/CDN  │  │WebSocket │        │
│  │(Primary) │  │ (Cache)  │  │  (Media) │  │(Channels)│        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

---

### 4.2 Key Data Flows

#### Flow 1: Tournament Registration (Happy Path)

```
User (Web UI)
    │
    ▼
POST /tournaments/{slug}/register/
    │
    ▼
TournamentOpsService.process_registration_workflow()
    │
    ├──> GameAdapter.get_identity_rules(game_id)
    │    └──> Returns: Required fields (riot_id, rank, etc.)
    │
    ├──> UserAdapter.get_profile(user_id)
    │    └──> Returns: Auto-fill data (email, phone, riot_id)
    │
    ├──> TeamAdapter.get_team(team_id) [if team tournament]
    │    └──> Returns: Team data, members, captain
    │
    ├──> RegistrationService.check_eligibility(...)
    │    └──> Validates: Age, rank, region, team size
    │
    ├──> RegistrationService.create_registration(...)
    │    └──> Creates: Registration record
    │
    ├──> EconomyAdapter.deduct_entry_fee(user_id, amount)
    │    └──> Deducts: DeltaCoin from wallet
    │
    ├──> UserAdapter.increment_tournaments_entered(user_id)
    │    └──> Updates: User tournament count
    │
    ├──> NotificationService.send_confirmation(registration_id)
    │    └──> Sends: Email + in-app notification
    │
    └──> EventBus.publish(RegistrationCompletedEvent)
         └──> Triggers: Any registered event handlers
```

---

#### Flow 2: Match Result → Stats Propagation

```
Organizer/Admin (Admin UI)
    │
    ▼
POST /api/matches/{id}/confirm-result/
    │
    ▼
MatchService.confirm_result(match_id)
    │
    ├──> Match.state = COMPLETED
    ├──> Match.save()
    │
    └──> EventBus.publish(MatchCompletedEvent{
             match_id, tournament_id, winner_id, loser_id, scores
         })
         │
         ├──> Event Handler 1 (BracketService)
         │    └──> Advance winner to next round
         │
         ├──> Event Handler 2 (TeamStatsService)
         │    ├──> Increment team.matches_played (both teams)
         │    ├──> Increment team.matches_won (winner)
         │    └──> Recalculate team.win_rate
         │
         ├──> Event Handler 3 (UserStatsService)
         │    ├──> Increment user.matches_played (all players)
         │    ├──> Increment user.matches_won (winning players)
         │    └──> Recalculate user.win_rate
         │
         ├──> Event Handler 4 (MatchHistoryService)
         │    └──> Create TeamMatchHistory record
         │
         ├──> Event Handler 5 (RankingService)
         │    └──> Update ELO ratings (winner +25, loser -25)
         │
         ├──> Event Handler 6 (EconomyService)
         │    └──> Award DeltaCoin (match win reward)
         │
         └──> Event Handler 7 (NotificationService)
              └──> Send match result notifications
```

---

#### Flow 3: Tournament Finalization → Prizes & Certificates

```
Organizer (Admin UI)
    │
    ▼
POST /api/tournaments/{id}/finalize/
    │
    ▼
TournamentOpsService.finalize_tournament(tournament_id)
    │
    ├──> WinnerService.determine_winner(tournament_id)
    │    ├──> Traverse bracket tree to root
    │    └──> Create TournamentResult (1st, 2nd, 3rd)
    │
    ├──> PayoutService.process_payouts(tournament_id)
    │    ├──> Read prize_distribution JSONB
    │    ├──> EconomyAdapter.add_funds(winner_id, prize_amount)
    │    └──> Log payout transactions
    │
    ├──> CertificateService.generate_bulk_certificates(tournament_id)
    │    ├──> Generate PDFs for all participants
    │    ├──> Upload to S3
    │    └──> Store certificate records
    │
    ├──> Tournament.status = COMPLETED
    ├──> Tournament.save()
    │
    └──> EventBus.publish(TournamentCompletedEvent{
             tournament_id, winner_id, runner_up_id, ...
         })
         │
         ├──> Event Handler 1 (TeamStatsService)
         │    ├──> Increment tournaments_participated (all teams)
         │    └──> Increment tournaments_won (winner)
         │
         ├──> Event Handler 2 (UserStatsService)
         │    ├──> Record tournament completion in user history
         │    ├──> Update total_deltacoin_earned
         │    └──> Increment podium_finishes (top 3)
         │
         ├──> Event Handler 3 (LeaderboardService)
         │    ├──> Award tournament points (1st: 100pts, 2nd: 75pts, ...)
         │    └──> Recalculate global rankings
         │
         └──> Event Handler 4 (NotificationService)
              ├──> Send winner announcement
              └──> Send certificate ready emails
```

---

#### Flow 4: Payment Verification (Manual)

```
User uploads payment proof
    │
    ▼
POST /api/registrations/{id}/submit-payment/
    │
    ├──> Payment.status = PENDING
    └──> Payment.proof_image uploaded to S3

Admin reviews payment (Admin UI)
    │
    ▼
POST /api/payments/{id}/verify/
    │
    ▼
TournamentOpsService.verify_manual_payment(payment_id, approved=True)
    │
    ├──> PaymentService.update_status(payment_id, 'VERIFIED')
    │
    ├──> RegistrationService.update_status(registration_id, 'CONFIRMED')
    │
    ├──> EconomyAdapter.add_funds(organizer_wallet_id, entry_fee)
    │    └──> Transfer entry fee to organizer
    │
    ├──> NotificationService.send_payment_approved(user_id)
    │
    └──> EventBus.publish(PaymentVerifiedEvent{
             payment_id, registration_id, user_id
         })
```

---

## 5. Frontend Framework Support & Developer Guide Specifications

### 5.1 Overview

To ensure seamless frontend development and maintain strict alignment between frontend and backend systems, DeltaCrown provides a comprehensive **Frontend Developer Support System**. This system includes API specifications, component contracts, reusable schemas, design tokens, and UX guidelines.

**Core Principle**: Frontend developers should never need to guess data structures, API contracts, or design decisions. Everything must be documented, typed, and version-controlled.

---

### 5.2 Required Documentation & Support Files

#### 5.2.1 API Specifications (OpenAPI/Swagger)

**Location**: `docs/api/openapi.yaml` (auto-generated from DRF)

**Contents**:
- **REST API Endpoints**: All endpoints with request/response schemas
- **Authentication**: JWT token format, refresh token flow
- **Error Responses**: Standard error format with error codes
- **Rate Limiting**: Per-endpoint rate limits
- **Versioning**: API version strategy (v1, v2, etc.)

**Example OpenAPI Schema**:
```yaml
paths:
  /api/v1/tournaments/{slug}/registrations/:
    post:
      summary: Create tournament registration
      operationId: createRegistration
      tags:
        - Registrations
      security:
        - BearerAuth: []
      parameters:
        - name: slug
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/RegistrationCreateRequest'
      responses:
        '201':
          description: Registration created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RegistrationResponse'
        '400':
          description: Validation error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '402':
          description: Insufficient funds
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '409':
          description: Already registered
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  schemas:
    RegistrationCreateRequest:
      type: object
      required:
        - player_identities
        - team_id
        - payment_method
      properties:
        player_identities:
          type: object
          additionalProperties:
            type: string
          example:
            riot_id: "Player#TAG"
            discord_username: "player#1234"
        team_id:
          type: integer
          nullable: true
        payment_method:
          type: string
          enum: [deltacoin, manual_upload]
        payment_proof:
          type: string
          format: uri
          description: S3 URL for manual payment proof
    
    RegistrationResponse:
      type: object
      properties:
        id:
          type: integer
        registration_number:
          type: string
          example: "VCT-2025-001234"
        status:
          type: string
          enum: [draft, pending_payment, confirmed, withdrawn]
        created_at:
          type: string
          format: date-time
        tournament:
          $ref: '#/components/schemas/TournamentBriefDTO'
        participant:
          oneOf:
            - $ref: '#/components/schemas/UserDTO'
            - $ref: '#/components/schemas/TeamDTO'
```

**Auto-Generation**: Use `drf-spectacular` to auto-generate OpenAPI from Django REST Framework serializers.

---

#### 5.2.2 Component Contracts (TypeScript Interfaces)

**Location**: `frontend/src/types/` (if React/Vue) or `docs/frontend/types/`

**Purpose**: Define TypeScript interfaces that mirror backend DTOs exactly.

**Example - Tournament Types**:
```typescript
// frontend/src/types/tournament.ts

export enum TournamentStatus {
  DRAFT = 'draft',
  PUBLISHED = 'published',
  REGISTRATION_OPEN = 'registration_open',
  REGISTRATION_CLOSED = 'registration_closed',
  BRACKET_GENERATED = 'bracket_generated',
  LIVE = 'live',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled'
}

export enum TournamentFormat {
  SINGLE_ELIMINATION = 'single_elimination',
  DOUBLE_ELIMINATION = 'double_elimination',
  ROUND_ROBIN = 'round_robin',
  SWISS = 'swiss',
  GROUP_KNOCKOUT = 'group_knockout'
}

export interface Tournament {
  id: number;
  slug: string;
  name: string;
  game: Game;
  format: TournamentFormat;
  status: TournamentStatus;
  max_participants: number;
  current_participants: number;
  entry_fee: number;
  prize_pool: number;
  start_datetime: string; // ISO 8601
  end_datetime: string | null;
  registration_deadline: string;
  description: string;
  rules: string;
  organizer: UserBriefDTO;
  is_team_tournament: boolean;
  team_size: number | null;
  created_at: string;
  updated_at: string;
}

export interface TournamentBriefDTO {
  id: number;
  slug: string;
  name: string;
  game: GameBriefDTO;
  format: TournamentFormat;
  status: TournamentStatus;
  current_participants: number;
  max_participants: number;
  start_datetime: string;
}

export interface TournamentCreateRequest {
  name: string;
  game_id: number;
  format: TournamentFormat;
  max_participants: number;
  entry_fee: number;
  prize_distribution: PrizeDistribution;
  start_datetime: string;
  registration_deadline: string;
  description: string;
  rules: string;
  is_team_tournament: boolean;
  team_size?: number;
  eligibility_rules?: EligibilityRule[];
}

export interface PrizeDistribution {
  first_place: number;
  second_place: number;
  third_place: number;
  // Dynamic placements
  [key: string]: number;
}
```

**Example - Registration Types**:
```typescript
// frontend/src/types/registration.ts

export enum RegistrationStatus {
  DRAFT = 'draft',
  PENDING_PAYMENT = 'pending_payment',
  CONFIRMED = 'confirmed',
  PAYMENT_REJECTED = 'payment_rejected',
  WITHDRAWN = 'withdrawn'
}

export interface RegistrationDraft {
  uuid: string;
  registration_number: string;
  tournament: TournamentBriefDTO;
  form_data: Record<string, any>;
  autofill_data: AutoFillData;
  created_at: string;
  updated_at: string;
  expires_at: string;
}

export interface AutoFillData {
  fields: AutoFillField[];
}

export interface AutoFillField {
  name: string;
  label: string;
  value: string | null;
  locked: boolean;
  verification_status: 'verified' | 'unverified';
  confidence: 'high' | 'medium' | 'low';
  source: 'user_profile' | 'team' | 'game_config';
}

export interface RegistrationSubmitRequest {
  draft_uuid: string;
  player_identities: Record<string, string>;
  team_id?: number;
  payment_method: 'deltacoin' | 'manual_upload';
  payment_proof_url?: string;
}
```

**Example - Match & Bracket Types**:
```typescript
// frontend/src/types/match.ts

export enum MatchState {
  SCHEDULED = 'scheduled',
  CHECK_IN = 'check_in',
  LIVE = 'live',
  PENDING_RESULT = 'pending_result',
  COMPLETED = 'completed',
  DISPUTED = 'disputed',
  CANCELLED = 'cancelled'
}

export interface Match {
  id: number;
  tournament_id: number;
  round_number: number;
  match_number: number;
  state: MatchState;
  scheduled_time: string | null;
  participant1: MatchParticipant | null;
  participant2: MatchParticipant | null;
  winner: MatchParticipant | null;
  scores: MatchScore | null;
  next_match_id: number | null; // For bracket traversal
  created_at: string;
  updated_at: string;
}

export interface MatchParticipant {
  id: number;
  type: 'user' | 'team';
  name: string;
  avatar_url: string | null;
  seed: number | null;
}

export interface MatchScore {
  participant1_score: number;
  participant2_score: number;
  details: Record<string, any>; // Game-specific (maps, rounds, kills)
}

export interface BracketNode {
  match: Match;
  children: [BracketNode | null, BracketNode | null]; // [left, right]
}
```

---

#### 5.2.3 Reusable UI Schemas (JSON Schema for Forms)

**Location**: `docs/frontend/ui-schemas/`

**Purpose**: Define dynamic form schemas that drive registration forms, match result forms, and tournament creation wizards.

**Example - Registration Form Schema**:
```json
{
  "schema_version": "1.0",
  "tournament_id": 123,
  "game": "valorant",
  "form_sections": [
    {
      "id": "player_info",
      "title": "Player Information",
      "order": 1,
      "fields": [
        {
          "name": "riot_id",
          "label": "Riot ID",
          "type": "text",
          "required": true,
          "locked": false,
          "verified": false,
          "validation": {
            "pattern": "^[a-zA-Z0-9 ]+#[a-zA-Z0-9]+$",
            "error_message": "Format: Username#TAG"
          },
          "placeholder": "Player#TAG",
          "help_text": "Your Riot ID from Valorant",
          "autofill_source": "user_profile.riot_id"
        },
        {
          "name": "rank",
          "label": "Current Rank",
          "type": "select",
          "required": true,
          "locked": false,
          "verified": false,
          "options": [
            {"value": "iron", "label": "Iron"},
            {"value": "bronze", "label": "Bronze"},
            {"value": "silver", "label": "Silver"},
            {"value": "gold", "label": "Gold"},
            {"value": "platinum", "label": "Platinum"},
            {"value": "diamond", "label": "Diamond"},
            {"value": "immortal", "label": "Immortal"},
            {"value": "radiant", "label": "Radiant"}
          ],
          "validation": {
            "min_rank": "gold",
            "error_message": "Minimum rank: Gold"
          }
        },
        {
          "name": "discord_username",
          "label": "Discord Username",
          "type": "text",
          "required": true,
          "locked": false,
          "verified": false,
          "validation": {
            "pattern": "^.+#\\d{4}$",
            "error_message": "Format: username#1234"
          },
          "placeholder": "player#1234",
          "autofill_source": "user_profile.discord_username"
        }
      ]
    },
    {
      "id": "contact_info",
      "title": "Contact Information",
      "order": 2,
      "fields": [
        {
          "name": "email",
          "label": "Email Address",
          "type": "email",
          "required": true,
          "locked": true,
          "verified": true,
          "validation": {
            "email": true
          },
          "autofill_source": "user_profile.email",
          "help_text": "This field is locked because your email is verified"
        },
        {
          "name": "phone",
          "label": "Phone Number",
          "type": "tel",
          "required": false,
          "locked": false,
          "verified": false,
          "validation": {
            "pattern": "^\\+?[1-9]\\d{1,14}$",
            "error_message": "Enter valid phone number with country code"
          },
          "autofill_source": "user_profile.phone"
        }
      ]
    }
  ],
  "submission": {
    "endpoint": "/api/v1/tournaments/vct-2025-qualifier/registrations/",
    "method": "POST",
    "payment_required": true,
    "entry_fee": 10
  }
}
```

**Example - Match Result Form Schema**:
```json
{
  "schema_version": "1.0",
  "match_id": 456,
  "game": "valorant",
  "format": "single_elimination",
  "form_fields": [
    {
      "name": "winner",
      "label": "Match Winner",
      "type": "radio",
      "required": true,
      "options": [
        {"value": "participant1", "label": "Team Alpha"},
        {"value": "participant2", "label": "Team Beta"}
      ]
    },
    {
      "name": "final_score",
      "label": "Final Score",
      "type": "score_input",
      "required": true,
      "validation": {
        "min": 0,
        "max": 13,
        "error_message": "Valorant: First to 13 rounds"
      },
      "fields": [
        {"name": "participant1_score", "label": "Team Alpha Score"},
        {"name": "participant2_score", "label": "Team Beta Score"}
      ]
    },
    {
      "name": "map_played",
      "label": "Map",
      "type": "select",
      "required": false,
      "options": [
        {"value": "ascent", "label": "Ascent"},
        {"value": "bind", "label": "Bind"},
        {"value": "haven", "label": "Haven"},
        {"value": "split", "label": "Split"},
        {"value": "icebox", "label": "Icebox"}
      ]
    },
    {
      "name": "proof_screenshot",
      "label": "Match Proof (Screenshot)",
      "type": "file",
      "required": true,
      "validation": {
        "accept": "image/*",
        "max_size": 5242880,
        "error_message": "Max file size: 5MB"
      }
    }
  ],
  "submission": {
    "endpoint": "/api/v1/matches/456/submit-result/",
    "method": "POST"
  }
}
```

---

#### 5.2.4 Design Token System

**Location**: `frontend/src/design-tokens/` or `docs/frontend/design-tokens.json`

**Purpose**: Centralize all design decisions (colors, spacing, typography) for consistency across UI components.

**Example - Design Tokens (JSON)**:
```json
{
  "version": "1.0",
  "colors": {
    "primary": {
      "50": "#eff6ff",
      "100": "#dbeafe",
      "200": "#bfdbfe",
      "300": "#93c5fd",
      "400": "#60a5fa",
      "500": "#3b82f6",
      "600": "#2563eb",
      "700": "#1d4ed8",
      "800": "#1e40af",
      "900": "#1e3a8a"
    },
    "success": {
      "light": "#10b981",
      "main": "#059669",
      "dark": "#047857"
    },
    "error": {
      "light": "#ef4444",
      "main": "#dc2626",
      "dark": "#b91c1c"
    },
    "warning": {
      "light": "#f59e0b",
      "main": "#d97706",
      "dark": "#b45309"
    },
    "info": {
      "light": "#3b82f6",
      "main": "#2563eb",
      "dark": "#1d4ed8"
    },
    "neutral": {
      "50": "#f9fafb",
      "100": "#f3f4f6",
      "200": "#e5e7eb",
      "300": "#d1d5db",
      "400": "#9ca3af",
      "500": "#6b7280",
      "600": "#4b5563",
      "700": "#374151",
      "800": "#1f2937",
      "900": "#111827"
    }
  },
  "spacing": {
    "xs": "0.25rem",
    "sm": "0.5rem",
    "md": "1rem",
    "lg": "1.5rem",
    "xl": "2rem",
    "2xl": "3rem",
    "3xl": "4rem"
  },
  "typography": {
    "fontFamily": {
      "sans": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      "mono": "'Fira Code', 'Courier New', monospace"
    },
    "fontSize": {
      "xs": "0.75rem",
      "sm": "0.875rem",
      "base": "1rem",
      "lg": "1.125rem",
      "xl": "1.25rem",
      "2xl": "1.5rem",
      "3xl": "1.875rem",
      "4xl": "2.25rem"
    },
    "fontWeight": {
      "light": 300,
      "normal": 400,
      "medium": 500,
      "semibold": 600,
      "bold": 700
    },
    "lineHeight": {
      "tight": 1.25,
      "normal": 1.5,
      "relaxed": 1.75
    }
  },
  "borderRadius": {
    "none": "0",
    "sm": "0.125rem",
    "md": "0.375rem",
    "lg": "0.5rem",
    "xl": "0.75rem",
    "full": "9999px"
  },
  "shadows": {
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
    "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
  },
  "transitions": {
    "fast": "150ms ease-in-out",
    "normal": "300ms ease-in-out",
    "slow": "500ms ease-in-out"
  }
}
```

**Usage in Frontend**:
```typescript
// frontend/src/components/Button.tsx
import tokens from '@/design-tokens/tokens.json';

const Button = ({ variant = 'primary' }) => {
  const styles = {
    backgroundColor: tokens.colors.primary[600],
    color: tokens.colors.neutral[50],
    padding: `${tokens.spacing.sm} ${tokens.spacing.lg}`,
    borderRadius: tokens.borderRadius.md,
    fontSize: tokens.typography.fontSize.base,
    fontWeight: tokens.typography.fontWeight.medium,
    transition: tokens.transitions.normal
  };
  
  return <button style={styles}>Click Me</button>;
};
```

---

#### 5.2.5 UX Rules & Guidelines

**Location**: `docs/frontend/ux-guidelines.md`

**Purpose**: Define consistent UX patterns, interaction behaviors, and user flow standards.

**Key UX Rules**:

**1. Form Validation**
- ✅ Validate on blur (not on every keystroke)
- ✅ Show inline errors below field (red text + icon)
- ✅ Show success indicators (green checkmark for valid fields)
- ✅ Disable submit button until all required fields valid
- ❌ Don't validate on first keystroke (wait for user to finish typing)

**2. Loading States**
- ✅ Show skeleton loaders for content (not spinners)
- ✅ Disable buttons during async operations (add spinner to button)
- ✅ Show optimistic UI updates (immediate feedback, rollback on error)
- ❌ Don't block entire page with full-screen spinner

**3. Error Handling**
- ✅ Show toast notifications for async errors (top-right corner, 5s auto-dismiss)
- ✅ Show inline errors for form validation (below field)
- ✅ Provide actionable error messages ("Insufficient funds. Add DeltaCoin?")
- ❌ Don't show generic errors ("An error occurred")

**4. Navigation & Breadcrumbs**
- ✅ Show breadcrumbs on deep pages (Tournaments > VCT 2025 > Registrations)
- ✅ Highlight active nav item (bold + color)
- ✅ Preserve scroll position on back navigation
- ❌ Don't navigate away without save confirmation (if form dirty)

**5. Accessibility**
- ✅ All interactive elements keyboard-navigable (Tab, Enter, Space)
- ✅ ARIA labels on all form inputs
- ✅ Color contrast ratio ≥ 4.5:1 (WCAG AA)
- ✅ Focus indicators visible (blue outline on focus)

**6. Responsive Design**
- ✅ Mobile-first design (320px min width)
- ✅ Breakpoints: Mobile (< 640px), Tablet (640-1024px), Desktop (> 1024px)
- ✅ Touch targets ≥ 44x44px on mobile
- ✅ Stack vertically on mobile, side-by-side on desktop

**7. Confirmation Dialogs**
- ✅ Confirm destructive actions (delete tournament, withdraw registration)
- ✅ Show consequences ("This will refund your entry fee and remove you from the bracket")
- ✅ Primary action on right (Confirm), secondary on left (Cancel)
- ❌ Don't ask for confirmation on non-destructive actions (save draft)

---

### 5.3 Frontend-Backend Alignment System

**Goal**: Ensure frontend and backend stay in sync as system evolves.

#### 5.3.1 Automated Type Generation

**Strategy**: Generate TypeScript types from Django models/serializers automatically.

**Tools**:
- **drf-spectacular**: Auto-generate OpenAPI schema from DRF serializers
- **openapi-typescript**: Generate TypeScript types from OpenAPI schema

**Workflow**:
```bash
# 1. Backend generates OpenAPI schema
python manage.py spectacular --file docs/api/openapi.yaml

# 2. Generate TypeScript types
npx openapi-typescript docs/api/openapi.yaml --output frontend/src/types/api.ts

# 3. Frontend imports generated types
import { Tournament, Registration, Match } from '@/types/api';
```

**Benefits**:
- ✅ Types always match backend (auto-generated)
- ✅ Compile-time errors if backend changes break frontend
- ✅ No manual type maintenance

---

#### 5.3.2 API Contract Testing

**Strategy**: Test that backend API responses match OpenAPI schema.

**Tools**:
- **schemathesis**: Property-based testing for API contracts

**Example Test**:
```python
# tests/api/test_api_contracts.py
import schemathesis

schema = schemathesis.from_uri("http://localhost:8000/api/schema/")

@schema.parametrize()
def test_api_contract(case):
    """Test all API endpoints match OpenAPI schema."""
    response = case.call()
    case.validate_response(response)
```

**Benefits**:
- ✅ Catch breaking changes before deployment
- ✅ Ensure API responses match docs
- ✅ Prevent frontend breaking on backend updates

---

#### 5.3.3 Versioning Strategy

**Strategy**: Version API to allow gradual frontend migrations.

**API Versioning**:
- `/api/v1/` → Current stable API
- `/api/v2/` → Next major version (breaking changes)
- Deprecation notices in v1 responses (HTTP header: `X-API-Deprecated: Migrate to v2 by 2026-01-01`)

**Frontend Compatibility**:
```typescript
// frontend/src/api/client.ts
const API_VERSION = process.env.REACT_APP_API_VERSION || 'v1';

export const apiClient = axios.create({
  baseURL: `/api/${API_VERSION}/`,
  headers: {
    'Content-Type': 'application/json'
  }
});
```

---

#### 5.3.4 Change Communication Protocol

**Process for Backend Changes**:

1. **Proposal**: Backend team proposes API change (GitHub issue)
2. **Review**: Frontend team reviews impact (breaking vs. non-breaking)
3. **Migration Plan**: Document migration path (if breaking)
4. **Implementation**: Backend implements with deprecation warnings
5. **Frontend Update**: Frontend migrates to new API
6. **Cleanup**: Remove deprecated endpoints after migration window

**Example - Breaking Change Migration**:
```markdown
## API Change Proposal: Registration Auto-Fill Response Structure

**Current (v1)**:
```json
{
  "autofill_data": {
    "email": "user@example.com",
    "riot_id": "Player#TAG"
  }
}
```

**Proposed (v2)**:
```json
{
  "autofill_data": {
    "fields": [
      {
        "name": "email",
        "value": "user@example.com",
        "locked": true,
        "verified": true
      },
      {
        "name": "riot_id",
        "value": "Player#TAG",
        "locked": false,
        "verified": false
      }
    ]
  }
}
```

**Migration Path**:
1. Deploy v2 endpoint (2025-12-15)
2. Frontend updates to use v2 (2025-12-20)
3. Deprecate v1 (2026-01-01)
4. Remove v1 (2026-02-01)
```

---

### 5.4 Frontend Developer Onboarding Checklist

**For New Frontend Developers**:

- [ ] Read `docs/frontend/ux-guidelines.md`
- [ ] Review OpenAPI docs at `/api/schema/swagger-ui/`
- [ ] Import TypeScript types from `frontend/src/types/api.ts`
- [ ] Use design tokens from `frontend/src/design-tokens/tokens.json`
- [ ] Test API integration with Postman collection (`docs/api/postman_collection.json`)
- [ ] Review form schemas in `docs/frontend/ui-schemas/`
- [ ] Set up API contract tests (`npm run test:api-contracts`)
- [ ] Join `#frontend-backend-sync` Slack channel (for change notifications)

---

## 6. Manual & Automatic Tournament Management Architecture

### 6.1 Overview

DeltaCrown supports **both automated and manual tournament management** to accommodate different organizer preferences and tournament complexities. Some organizers want full automation (bracket generation, scheduling, result tracking), while others need granular control (manual seeding, bracket editing, match scheduling).

**Design Principle**: Provide intelligent defaults with manual override capabilities at every step.

---

### 6.2 Manual Tournament Management Features

#### 6.2.1 Manual Group Creation

**Use Case**: Organizers want to manually assign participants to groups (e.g., regional groups, skill-based groups).

**Implementation**:

**Models**:
```python
# tournaments/models.py
class TournamentGroup(models.Model):
    """Manual group assignment for group-stage tournaments."""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='groups')
    name = models.CharField(max_length=100)  # "Group A", "North America", etc.
    order = models.IntegerField(default=0)
    max_participants = models.IntegerField(default=4)
    created_at = models.DateTimeField(auto_now_add=True)

class GroupMembership(models.Model):
    """Participant assignment to groups."""
    group = models.ForeignKey(TournamentGroup, on_delete=models.CASCADE, related_name='members')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        unique_together = ('group', 'registration')
```

**Service**:
```python
# tournament_ops/services/group_management_service.py
class GroupManagementService:
    @staticmethod
    @transaction.atomic
    def create_groups(tournament_id: int, group_config: List[dict]) -> List[TournamentGroup]:
        """
        Create groups manually.
        
        group_config: [
            {"name": "Group A", "max_participants": 4},
            {"name": "Group B", "max_participants": 4}
        ]
        """
        groups = []
        for idx, config in enumerate(group_config):
            group = TournamentGroup.objects.create(
                tournament_id=tournament_id,
                name=config['name'],
                max_participants=config['max_participants'],
                order=idx
            )
            groups.append(group)
        return groups
    
    @staticmethod
    @transaction.atomic
    def assign_to_group(
        registration_id: int, 
        group_id: int, 
        assigned_by_user_id: int
    ) -> GroupMembership:
        """Manually assign participant to group."""
        group = TournamentGroup.objects.select_for_update().get(id=group_id)
        
        # Validate group not full
        if group.members.count() >= group.max_participants:
            raise ValidationError(f"Group {group.name} is full")
        
        # Create membership
        membership = GroupMembership.objects.create(
            group=group,
            registration_id=registration_id,
            assigned_by_id=assigned_by_user_id
        )
        return membership
    
    @staticmethod
    def auto_assign_to_groups(tournament_id: int, strategy: str = 'round_robin') -> List[GroupMembership]:
        """
        Auto-assign participants to groups using strategy.
        
        Strategies:
        - 'round_robin': Distribute evenly (1, 2, 3, 4, 1, 2, 3, 4, ...)
        - 'random': Random assignment
        - 'seeded': Distribute by seed (1st seed to Group A, 2nd to Group B, etc.)
        """
        tournament = Tournament.objects.get(id=tournament_id)
        groups = list(tournament.groups.all().order_by('order'))
        registrations = list(tournament.registrations.filter(status='confirmed').order_by('?'))
        
        memberships = []
        if strategy == 'round_robin':
            for idx, registration in enumerate(registrations):
                group = groups[idx % len(groups)]
                membership = GroupMembership.objects.create(
                    group=group,
                    registration=registration,
                    assigned_by=None  # Auto-assigned
                )
                memberships.append(membership)
        
        elif strategy == 'seeded':
            # Sort by seed (if exists), else registration order
            registrations = sorted(registrations, key=lambda r: r.seed or 999)
            for idx, registration in enumerate(registrations):
                group = groups[idx % len(groups)]
                membership = GroupMembership.objects.create(
                    group=group,
                    registration=registration,
                    assigned_by=None
                )
                memberships.append(membership)
        
        return memberships
```

**Admin UI**:
- Drag-and-drop interface to assign participants to groups
- Bulk assign (select participants → assign to group)
- Auto-assign with strategy selector (Round Robin, Seeded, Random)

---

#### 6.2.2 Manual Seeding

**Use Case**: Organizers want to manually set seeds (not based on registration order or rank).

**Implementation**:

**Model Field**:
```python
# tournaments/models.py
class Registration(models.Model):
    # ... existing fields ...
    seed = models.IntegerField(null=True, blank=True, help_text="Manual seed for bracket generation")
    seed_set_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='seeded_registrations')
    seed_set_at = models.DateTimeField(null=True, blank=True)
```

**Service**:
```python
# tournament_ops/services/seeding_service.py
class SeedingService:
    @staticmethod
    @transaction.atomic
    def set_seed(registration_id: int, seed: int, admin_user_id: int) -> Registration:
        """Manually set seed for a registration."""
        registration = Registration.objects.select_for_update().get(id=registration_id)
        
        # Validate seed not already taken
        existing = Registration.objects.filter(
            tournament=registration.tournament,
            seed=seed
        ).exclude(id=registration_id).exists()
        
        if existing:
            raise ValidationError(f"Seed {seed} already assigned")
        
        registration.seed = seed
        registration.seed_set_by_id = admin_user_id
        registration.seed_set_at = timezone.now()
        registration.save()
        
        return registration
    
    @staticmethod
    @transaction.atomic
    def auto_seed(tournament_id: int, strategy: str = 'registration_order') -> List[Registration]:
        """
        Auto-assign seeds using strategy.
        
        Strategies:
        - 'registration_order': First registered = #1 seed
        - 'rank': Highest rank = #1 seed (game-specific)
        - 'elo': Highest ELO = #1 seed
        - 'random': Random seeds
        """
        registrations = Registration.objects.filter(
            tournament_id=tournament_id,
            status='confirmed'
        )
        
        if strategy == 'registration_order':
            registrations = registrations.order_by('created_at')
        elif strategy == 'rank':
            # Game-specific ranking logic (complex)
            pass
        elif strategy == 'elo':
            # Order by ELO rating
            registrations = registrations.order_by('-user__elo_rating')
        elif strategy == 'random':
            registrations = registrations.order_by('?')
        
        for idx, registration in enumerate(registrations, start=1):
            registration.seed = idx
            registration.seed_set_by = None  # Auto-assigned
            registration.seed_set_at = timezone.now()
            registration.save()
        
        return list(registrations)
    
    @staticmethod
    def swap_seeds(registration1_id: int, registration2_id: int, admin_user_id: int):
        """Swap seeds between two registrations."""
        with transaction.atomic():
            reg1 = Registration.objects.select_for_update().get(id=registration1_id)
            reg2 = Registration.objects.select_for_update().get(id=registration2_id)
            
            # Swap seeds
            reg1.seed, reg2.seed = reg2.seed, reg1.seed
            reg1.seed_set_by_id = admin_user_id
            reg2.seed_set_by_id = admin_user_id
            reg1.seed_set_at = timezone.now()
            reg2.seed_set_at = timezone.now()
            
            reg1.save()
            reg2.save()
```

**Admin UI**:
- Seeding table (drag to reorder seeds)
- Swap seeds (click two participants to swap)
- Auto-seed button with strategy dropdown
- Visual indicators (manual vs. auto seed)

---

#### 6.2.3 Manual Bracket Editing

**Use Case**: Organizers need to fix bracket errors (wrong matchup, bye assignment, seed correction).

**Implementation**:

**Service**:
```python
# tournament_ops/services/bracket_editing_service.py
class BracketEditingService:
    @staticmethod
    @transaction.atomic
    def swap_participants(match_id: int, position1: str, position2: str, admin_user_id: int) -> Match:
        """
        Swap participants in bracket (e.g., swap participant1 with participant2).
        
        position1/position2: 'participant1' or 'participant2'
        """
        match = Match.objects.select_for_update().get(id=match_id)
        
        if match.state not in [Match.SCHEDULED, Match.CHECK_IN]:
            raise ValidationError("Cannot edit match that has started")
        
        # Swap participants
        if position1 == 'participant1' and position2 == 'participant2':
            match.participant1, match.participant2 = match.participant2, match.participant1
        
        match.save()
        
        # Log edit
        BracketEditLog.objects.create(
            match=match,
            edit_type='swap_participants',
            edited_by_id=admin_user_id,
            details={'positions': [position1, position2]}
        )
        
        return match
    
    @staticmethod
    @transaction.atomic
    def replace_participant(
        match_id: int, 
        old_registration_id: int, 
        new_registration_id: int,
        admin_user_id: int
    ) -> Match:
        """Replace a participant in a match."""
        match = Match.objects.select_for_update().get(id=match_id)
        
        if match.state not in [Match.SCHEDULED, Match.CHECK_IN]:
            raise ValidationError("Cannot edit match that has started")
        
        # Find and replace
        if match.participant1_id == old_registration_id:
            match.participant1_id = new_registration_id
        elif match.participant2_id == old_registration_id:
            match.participant2_id = new_registration_id
        else:
            raise ValidationError("Old participant not in this match")
        
        match.save()
        
        # Log edit
        BracketEditLog.objects.create(
            match=match,
            edit_type='replace_participant',
            edited_by_id=admin_user_id,
            details={
                'old_registration_id': old_registration_id,
                'new_registration_id': new_registration_id
            }
        )
        
        return match
    
    @staticmethod
    @transaction.atomic
    def assign_bye(match_id: int, bye_position: str, admin_user_id: int) -> Match:
        """
        Assign bye to a position (participant1 or participant2).
        
        This auto-advances the other participant to next round.
        """
        match = Match.objects.select_for_update().get(id=match_id)
        
        if match.state != Match.SCHEDULED:
            raise ValidationError("Match must be in SCHEDULED state")
        
        # Set bye
        if bye_position == 'participant1':
            match.participant1 = None  # Bye
            winner = match.participant2
        elif bye_position == 'participant2':
            match.participant2 = None  # Bye
            winner = match.participant1
        else:
            raise ValidationError("Invalid bye position")
        
        # Auto-advance winner
        match.winner = winner
        match.state = Match.COMPLETED
        match.save()
        
        # Advance to next round
        if match.next_match_id:
            BracketService.advance_winner(match.id)
        
        # Log edit
        BracketEditLog.objects.create(
            match=match,
            edit_type='assign_bye',
            edited_by_id=admin_user_id,
            details={'bye_position': bye_position}
        )
        
        return match
    
    @staticmethod
    def regenerate_from_round(tournament_id: int, from_round: int, admin_user_id: int):
        """
        Regenerate bracket from specific round (delete all matches >= from_round, rebuild).
        
        WARNING: Destructive operation. Requires confirmation.
        """
        with transaction.atomic():
            # Delete matches from round onwards
            Match.objects.filter(
                tournament_id=tournament_id,
                round_number__gte=from_round
            ).delete()
            
            # Regenerate bracket
            BracketService.generate_bracket(tournament_id)
            
            # Log regeneration
            BracketEditLog.objects.create(
                tournament_id=tournament_id,
                edit_type='regenerate_bracket',
                edited_by_id=admin_user_id,
                details={'from_round': from_round}
            )
```

**Audit Log Model**:
```python
# tournament_ops/models.py
class BracketEditLog(models.Model):
    """Audit log for bracket edits."""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=True)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, null=True)
    edit_type = models.CharField(max_length=50, choices=[
        ('swap_participants', 'Swap Participants'),
        ('replace_participant', 'Replace Participant'),
        ('assign_bye', 'Assign Bye'),
        ('regenerate_bracket', 'Regenerate Bracket'),
        ('manual_seed', 'Manual Seed'),
    ])
    edited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    edited_at = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-edited_at']
```

**Admin UI**:
- Bracket visual editor (drag participants between matches)
- Swap button (click two matches to swap participants)
- Replace participant modal (search and replace)
- Bye assignment (right-click participant → Assign Bye)
- Regenerate bracket button (with confirmation dialog)
- Edit history viewer (audit log table)

---

#### 6.2.4 Manual Match Scheduling

**Use Case**: Organizers want to set specific match times (not auto-scheduled).

**Implementation**:

**Service**:
```python
# tournament_ops/services/match_scheduling_service.py
class MatchSchedulingService:
    @staticmethod
    @transaction.atomic
    def schedule_match(match_id: int, scheduled_time: datetime, admin_user_id: int) -> Match:
        """Manually schedule a match."""
        match = Match.objects.select_for_update().get(id=match_id)
        
        if match.state not in [Match.SCHEDULED, Match.CHECK_IN]:
            raise ValidationError("Cannot reschedule match that has started")
        
        match.scheduled_time = scheduled_time
        match.save()
        
        # Send notifications to participants
        NotificationService.send_match_scheduled(match_id)
        
        # Log scheduling
        MatchScheduleLog.objects.create(
            match=match,
            scheduled_by_id=admin_user_id,
            scheduled_time=scheduled_time
        )
        
        return match
    
    @staticmethod
    @transaction.atomic
    def bulk_schedule_round(tournament_id: int, round_number: int, start_time: datetime, interval_minutes: int = 60):
        """
        Schedule all matches in a round with intervals.
        
        Example: Round 1 starts at 2:00 PM, matches every 60 minutes
        - Match 1: 2:00 PM
        - Match 2: 3:00 PM
        - Match 3: 4:00 PM
        """
        matches = Match.objects.filter(
            tournament_id=tournament_id,
            round_number=round_number,
            state=Match.SCHEDULED
        ).order_by('match_number')
        
        current_time = start_time
        for match in matches:
            match.scheduled_time = current_time
            match.save()
            current_time += timedelta(minutes=interval_minutes)
        
        return list(matches)
    
    @staticmethod
    def auto_schedule_tournament(tournament_id: int, strategy: str = 'sequential'):
        """
        Auto-schedule entire tournament.
        
        Strategies:
        - 'sequential': Each round starts after previous round completes
        - 'parallel': All Round 1 matches at same time, Round 2 after Round 1, etc.
        - 'staggered': Matches in same round staggered by interval
        """
        tournament = Tournament.objects.get(id=tournament_id)
        start_time = tournament.start_datetime
        
        if strategy == 'staggered':
            rounds = Match.objects.filter(tournament_id=tournament_id).values('round_number').distinct()
            current_time = start_time
            
            for round_data in rounds:
                round_number = round_data['round_number']
                MatchSchedulingService.bulk_schedule_round(
                    tournament_id, 
                    round_number, 
                    current_time, 
                    interval_minutes=60
                )
                # Next round starts 2 hours after last match of current round
                match_count = Match.objects.filter(
                    tournament_id=tournament_id,
                    round_number=round_number
                ).count()
                current_time += timedelta(hours=match_count + 2)
```

**Admin UI**:
- Calendar view (drag matches to time slots)
- Bulk schedule (select round → set start time + interval)
- Auto-schedule button with strategy dropdown
- Conflict warnings (overlapping matches for same participant)

---

#### 6.2.5 Manual Result Entry & Override

**Use Case**: Organizers need to enter results on behalf of participants or override disputed results.

**Implementation**:

**Service**:
```python
# tournament_ops/services/result_management_service.py
class ResultManagementService:
    @staticmethod
    @transaction.atomic
    def enter_result_manual(
        match_id: int, 
        winner_id: int, 
        scores: dict, 
        admin_user_id: int,
        reason: str = None
    ) -> Match:
        """
        Manually enter match result (organizer override).
        
        scores: {
            "participant1_score": 13,
            "participant2_score": 7,
            "map": "Ascent"
        }
        """
        match = Match.objects.select_for_update().get(id=match_id)
        
        # Validate winner is in match
        if winner_id not in [match.participant1_id, match.participant2_id]:
            raise ValidationError("Winner must be a participant in this match")
        
        # Set result
        match.winner_id = winner_id
        match.scores = scores
        match.state = Match.COMPLETED
        match.result_entered_by_id = admin_user_id
        match.result_entered_manually = True
        match.manual_result_reason = reason
        match.save()
        
        # Advance bracket
        if match.next_match_id:
            BracketService.advance_winner(match.id)
        
        # Publish event
        EventBus.publish(MatchCompletedEvent(
            match_id=match.id,
            tournament_id=match.tournament_id,
            winner_id=winner_id,
            loser_id=match.participant2_id if winner_id == match.participant1_id else match.participant1_id,
            scores=scores
        ))
        
        # Log manual entry
        ResultOverrideLog.objects.create(
            match=match,
            override_by_id=admin_user_id,
            reason=reason,
            scores=scores
        )
        
        return match
    
    @staticmethod
    @transaction.atomic
    def override_result(
        match_id: int, 
        new_winner_id: int, 
        new_scores: dict, 
        admin_user_id: int,
        reason: str
    ) -> Match:
        """
        Override existing match result (dispute resolution).
        
        This reverses the previous result and applies new result.
        """
        match = Match.objects.select_for_update().get(id=match_id)
        
        if match.state != Match.COMPLETED:
            raise ValidationError("Can only override completed matches")
        
        old_winner_id = match.winner_id
        old_scores = match.scores
        
        # Reverse previous result
        if match.next_match_id:
            # Remove winner from next round
            next_match = Match.objects.get(id=match.next_match_id)
            if next_match.participant1_id == old_winner_id:
                next_match.participant1 = None
            elif next_match.participant2_id == old_winner_id:
                next_match.participant2 = None
            next_match.save()
        
        # Apply new result
        match.winner_id = new_winner_id
        match.scores = new_scores
        match.result_overridden = True
        match.result_override_by_id = admin_user_id
        match.result_override_reason = reason
        match.save()
        
        # Advance new winner
        if match.next_match_id:
            BracketService.advance_winner(match.id)
        
        # Publish events (reverse old, apply new)
        EventBus.publish(MatchResultOverriddenEvent(
            match_id=match.id,
            old_winner_id=old_winner_id,
            new_winner_id=new_winner_id,
            reason=reason
        ))
        
        # Log override
        ResultOverrideLog.objects.create(
            match=match,
            override_by_id=admin_user_id,
            reason=reason,
            old_winner_id=old_winner_id,
            old_scores=old_scores,
            new_winner_id=new_winner_id,
            new_scores=new_scores
        )
        
        return match
```

**Admin UI**:
- Manual result entry form (select winner, enter scores)
- Override result button (on completed matches)
- Override history viewer (audit log)
- Reason field (required for overrides)

---

#### 6.2.6 Results Inbox System

**Use Case**: Participants submit match results; organizers review and approve/reject.

**Implementation**:

**Model**:
```python
# tournaments/models.py
class MatchResultSubmission(models.Model):
    """User-submitted match results awaiting organizer review."""
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='result_submissions')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    # Result data
    claimed_winner = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='claimed_wins')
    scores = models.JSONField()
    proof_images = models.JSONField(default=list)  # List of S3 URLs
    
    # Review status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('conflicted', 'Conflicted')  # Both teams submitted different results
    ], default='pending')
    
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reviewed_results')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
```

**Service**:
```python
# tournament_ops/services/result_inbox_service.py
class ResultInboxService:
    @staticmethod
    @transaction.atomic
    def submit_result(
        match_id: int,
        user_id: int,
        winner_id: int,
        scores: dict,
        proof_images: List[str]
    ) -> MatchResultSubmission:
        """Submit match result for organizer review."""
        match = Match.objects.get(id=match_id)
        
        # Validate user is participant
        registration = Registration.objects.filter(
            tournament=match.tournament,
            user_id=user_id
        ).first()
        
        if not registration:
            raise ValidationError("You are not a participant in this match")
        
        # Check for existing submission by this user
        existing = MatchResultSubmission.objects.filter(
            match=match,
            submitted_by_id=user_id,
            status='pending'
        ).first()
        
        if existing:
            raise ValidationError("You have already submitted a result for this match")
        
        # Create submission
        submission = MatchResultSubmission.objects.create(
            match=match,
            submitted_by_id=user_id,
            claimed_winner_id=winner_id,
            scores=scores,
            proof_images=proof_images,
            status='pending'
        )
        
        # Check for conflict (both teams submitted different winners)
        other_submissions = MatchResultSubmission.objects.filter(
            match=match,
            status='pending'
        ).exclude(id=submission.id)
        
        if other_submissions.exists():
            other = other_submissions.first()
            if other.claimed_winner_id != winner_id:
                # Conflict detected
                submission.status = 'conflicted'
                submission.save()
                other.status = 'conflicted'
                other.save()
                
                # Notify organizer
                NotificationService.send_result_conflict_alert(match.tournament.organizer_id, match.id)
        
        return submission
    
    @staticmethod
    @transaction.atomic
    def approve_result(submission_id: int, admin_user_id: int) -> Match:
        """Approve submitted result and finalize match."""
        submission = MatchResultSubmission.objects.select_for_update().get(id=submission_id)
        
        if submission.status != 'pending' and submission.status != 'conflicted':
            raise ValidationError("Can only approve pending/conflicted submissions")
        
        # Apply result to match
        match = ResultManagementService.enter_result_manual(
            match_id=submission.match_id,
            winner_id=submission.claimed_winner_id,
            scores=submission.scores,
            admin_user_id=admin_user_id,
            reason=f"Approved submission from {submission.submitted_by.username}"
        )
        
        # Mark submission as approved
        submission.status = 'approved'
        submission.reviewed_by_id = admin_user_id
        submission.reviewed_at = timezone.now()
        submission.save()
        
        # Reject conflicting submissions
        MatchResultSubmission.objects.filter(
            match=submission.match,
            status__in=['pending', 'conflicted']
        ).exclude(id=submission.id).update(
            status='rejected',
            reviewed_by_id=admin_user_id,
            reviewed_at=timezone.now(),
            review_notes='Conflicting submission rejected'
        )
        
        return match
    
    @staticmethod
    @transaction.atomic
    def reject_result(submission_id: int, admin_user_id: int, reason: str):
        """Reject submitted result."""
        submission = MatchResultSubmission.objects.select_for_update().get(id=submission_id)
        
        submission.status = 'rejected'
        submission.reviewed_by_id = admin_user_id
        submission.reviewed_at = timezone.now()
        submission.review_notes = reason
        submission.save()
        
        # Notify submitter
        NotificationService.send_result_rejected(submission.submitted_by_id, submission.match_id, reason)
    
    @staticmethod
    def get_pending_results(tournament_id: int) -> List[MatchResultSubmission]:
        """Get all pending result submissions for organizer review."""
        return MatchResultSubmission.objects.filter(
            match__tournament_id=tournament_id,
            status__in=['pending', 'conflicted']
        ).select_related('match', 'submitted_by', 'claimed_winner')
```

**Admin UI - Results Inbox**:
- Inbox view (list of pending submissions)
- Filters: All / Pending / Conflicted
- Submission detail modal:
  - Submitted by: User A
  - Claimed winner: Team Alpha
  - Scores: 13-7
  - Proof images: [View gallery]
  - Conflicting submission (if exists): User B claims Team Beta won 13-10
- Actions: Approve / Reject / Request More Proof
- Bulk approve (checkbox selection)

---

### 6.3 Integration with TournamentOps

All manual management features integrate into TournamentOps as optional workflows:

```python
# tournament_ops/services/ops_service.py
class TournamentOpsService:
    # ... existing methods ...
    
    @staticmethod
    @transaction.atomic
    def setup_tournament_groups(
        tournament_id: int, 
        group_config: List[dict],
        auto_assign: bool = True,
        assignment_strategy: str = 'round_robin'
    ):
        """
        Setup groups for tournament (manual or auto).
        """
        # Create groups
        groups = GroupManagementService.create_groups(tournament_id, group_config)
        
        # Auto-assign if requested
        if auto_assign:
            GroupManagementService.auto_assign_to_groups(tournament_id, assignment_strategy)
        
        return groups
    
    @staticmethod
    @transaction.atomic
    def finalize_seeding(
        tournament_id: int,
        auto_seed: bool = True,
        seeding_strategy: str = 'registration_order'
    ):
        """
        Finalize seeding before bracket generation.
        """
        if auto_seed:
            SeedingService.auto_seed(tournament_id, seeding_strategy)
        
        # Validate all participants seeded
        unseeded = Registration.objects.filter(
            tournament_id=tournament_id,
            status='confirmed',
            seed__isnull=True
        ).count()
        
        if unseeded > 0:
            raise ValidationError(f"{unseeded} participants not seeded")
        
        return True
    
    @staticmethod
    @transaction.atomic
    def generate_bracket_with_validation(tournament_id: int):
        """
        Generate bracket with pre-flight checks.
        """
        tournament = Tournament.objects.get(id=tournament_id)
        
        # Validate tournament ready for bracket generation
        if tournament.current_participants < 2:
            raise ValidationError("Need at least 2 participants")
        
        # Check seeding complete (if required)
        if tournament.requires_seeding:
            unseeded = Registration.objects.filter(
                tournament=tournament,
                status='confirmed',
                seed__isnull=True
            ).count()
            if unseeded > 0:
                raise ValidationError(f"{unseeded} participants not seeded")
        
        # Generate bracket
        matches = BracketService.generate_bracket(tournament_id)
        
        # Auto-schedule if configured
        if tournament.auto_schedule_matches:
            MatchSchedulingService.auto_schedule_tournament(
                tournament_id,
                strategy=tournament.scheduling_strategy
            )
        
        # Update tournament status
        tournament.status = Tournament.BRACKET_GENERATED
        tournament.save()
        
        return matches
```

---

## 7. Universal Tournament Format Layer (Multi-Format Bracket System)

### 7.1 Overview

DeltaCrown must support **all major esports tournament formats** to accommodate different game communities and organizer preferences. Instead of hardcoding bracket generation logic for each format, we implement a **pluggable Bracket Generator Interface** with multiple format-specific implementations.

**Supported Formats**:
1. **Single Elimination**: Standard knockout bracket (8→4→2→1)
2. **Double Elimination**: Winners + Losers bracket (second chance)
3. **Round Robin**: Everyone plays everyone (league format)
4. **Swiss System**: Pairing based on current record (no elimination)
5. **Group Stage → Knockout**: Preliminary groups + elimination bracket
6. **League Format**: Season-based (home/away matches)
7. **Multi-Map/Round**: Best-of-3, Best-of-5 series

---

### 7.2 Bracket Generator Interface

**Design Pattern**: Strategy Pattern with pluggable generators.

**Base Interface**:
```python
# tournaments/bracket_generators/base.py
from abc import ABC, abstractmethod
from typing import List, Dict
from tournaments.models import Tournament, Match, Registration

class BracketGeneratorInterface(ABC):
    """Base interface for tournament format generators."""
    
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self.participants = self.get_seeded_participants()
    
    def get_seeded_participants(self) -> List[Registration]:
        """Get confirmed participants ordered by seed."""
        return list(
            Registration.objects.filter(
                tournament=self.tournament,
                status='confirmed'
            ).order_by('seed')
        )
    
    @abstractmethod
    def generate(self) -> List[Match]:
        """
        Generate bracket structure.
        
        Returns: List of Match objects (not yet saved to database).
        """
        pass
    
    @abstractmethod
    def validate_participant_count(self) -> bool:
        """
        Validate participant count is valid for this format.
        
        Raises ValidationError if invalid.
        """
        pass
    
    @abstractmethod
    def get_next_round_matches(self, current_round: int) -> List[Match]:
        """
        Get matches for next round based on current round results.
        
        Used for formats that generate rounds progressively (Swiss, Round Robin).
        """
        pass
    
    def get_bye_slots(self) -> List[int]:
        """
        Calculate which seeds get byes (if needed).
        
        Returns: List of seed numbers that receive byes.
        """
        return []
    
    def calculate_total_rounds(self) -> int:
        """Calculate total number of rounds for this format."""
        pass
    
    def get_format_metadata(self) -> Dict:
        """Return format-specific metadata (description, rules, etc.)."""
        return {
            'name': self.__class__.__name__,
            'description': '',
            'total_rounds': self.calculate_total_rounds(),
            'total_matches': 0,
            'supports_draws': False
        }
```

---

### 7.3 Format Implementations

#### 7.3.1 Single Elimination Generator

```python
# tournaments/bracket_generators/single_elimination.py
import math
from tournaments.bracket_generators.base import BracketGeneratorInterface
from tournaments.models import Match
from django.core.exceptions import ValidationError

class SingleEliminationGenerator(BracketGeneratorInterface):
    """
    Single elimination bracket generator.
    
    Features:
    - Standard knockout bracket
    - Byes for non-power-of-2 participant counts
    - Seeded bracket (1 vs lowest, 2 vs second-lowest, etc.)
    """
    
    def validate_participant_count(self) -> bool:
        count = len(self.participants)
        if count < 2:
            raise ValidationError("Single elimination requires at least 2 participants")
        return True
    
    def calculate_total_rounds(self) -> int:
        """Total rounds = log2(participants) rounded up."""
        return math.ceil(math.log2(len(self.participants)))
    
    def get_bye_slots(self) -> List[int]:
        """
        Calculate byes for non-power-of-2 brackets.
        
        Example: 6 participants → next power of 2 is 8 → 2 byes needed
        Byes go to top seeds (seed 1 and 2).
        """
        count = len(self.participants)
        next_power = 2 ** math.ceil(math.log2(count))
        byes_needed = next_power - count
        
        # Top seeds get byes
        return list(range(1, byes_needed + 1))
    
    def generate(self) -> List[Match]:
        """
        Generate single elimination bracket.
        
        Algorithm:
        1. Calculate byes
        2. Create Round 1 matches (non-bye participants)
        3. Create subsequent rounds (empty, filled as winners advance)
        4. Link matches to next round
        """
        self.validate_participant_count()
        
        total_rounds = self.calculate_total_rounds()
        bye_seeds = self.get_bye_slots()
        matches = []
        
        # Round 1: Pair non-bye participants
        round1_participants = [p for p in self.participants if p.seed not in bye_seeds]
        round1_matches = []
        
        match_number = 1
        for i in range(0, len(round1_participants), 2):
            if i + 1 < len(round1_participants):
                match = Match(
                    tournament=self.tournament,
                    round_number=1,
                    match_number=match_number,
                    participant1=round1_participants[i],
                    participant2=round1_participants[i + 1],
                    state=Match.SCHEDULED
                )
                round1_matches.append(match)
                matches.append(match)
                match_number += 1
        
        # Subsequent rounds: Create empty matches, link to previous round
        previous_round_matches = round1_matches
        for round_num in range(2, total_rounds + 1):
            round_matches = []
            match_number = 1
            
            # Create matches for this round (winners will fill in later)
            for i in range(0, len(previous_round_matches), 2):
                match = Match(
                    tournament=self.tournament,
                    round_number=round_num,
                    match_number=match_number,
                    participant1=None,  # Winner of previous match
                    participant2=None,  # Winner of previous match
                    state=Match.SCHEDULED
                )
                round_matches.append(match)
                matches.append(match)
                match_number += 1
            
            previous_round_matches = round_matches
        
        # Link matches (set next_match_id after saving)
        # This happens in BracketService.save_and_link_matches()
        
        return matches
    
    def get_next_round_matches(self, current_round: int) -> List[Match]:
        """Single elimination generates all rounds upfront."""
        return []  # Not used (all matches pre-generated)
    
    def get_format_metadata(self) -> Dict:
        return {
            'name': 'Single Elimination',
            'description': 'Standard knockout bracket. Lose once, you\'re out.',
            'total_rounds': self.calculate_total_rounds(),
            'total_matches': len(self.participants) - 1,  # N-1 matches for N participants
            'supports_draws': False,
            'bye_seeds': self.get_bye_slots()
        }
```

---

#### 7.3.2 Double Elimination Generator

```python
# tournaments/bracket_generators/double_elimination.py
class DoubleEliminationGenerator(BracketGeneratorInterface):
    """
    Double elimination bracket generator.
    
    Features:
    - Winners bracket (traditional elimination)
    - Losers bracket (second chance)
    - Grand finals (winner of each bracket)
    - Grand finals reset (if loser bracket winner wins first match)
    """
    
    def validate_participant_count(self) -> bool:
        count = len(self.participants)
        if count < 2:
            raise ValidationError("Double elimination requires at least 2 participants")
        return True
    
    def calculate_total_rounds(self) -> int:
        """
        Winners bracket rounds: log2(N)
        Losers bracket rounds: 2 * log2(N) - 1
        Grand finals: 1-2 matches
        """
        n = len(self.participants)
        winners_rounds = math.ceil(math.log2(n))
        losers_rounds = 2 * winners_rounds - 1
        return winners_rounds + losers_rounds + 2  # +2 for grand finals
    
    def generate(self) -> List[Match]:
        """
        Generate double elimination bracket.
        
        Structure:
        - Winners Bracket: Standard single elimination
        - Losers Bracket: Losers from winners bracket drop down
        - Grand Finals: Winner of winners bracket vs winner of losers bracket
        """
        self.validate_participant_count()
        
        matches = []
        
        # Generate Winners Bracket (same as single elimination)
        winners_bracket = SingleEliminationGenerator(self.tournament).generate()
        for match in winners_bracket:
            match.bracket_type = 'winners'
        matches.extend(winners_bracket)
        
        # Generate Losers Bracket
        losers_bracket = self._generate_losers_bracket(winners_bracket)
        matches.extend(losers_bracket)
        
        # Generate Grand Finals
        grand_finals = self._generate_grand_finals()
        matches.extend(grand_finals)
        
        return matches
    
    def _generate_losers_bracket(self, winners_bracket: List[Match]) -> List[Match]:
        """
        Generate losers bracket.
        
        Pattern:
        - Round 1: Losers from Winners R1 play each other
        - Round 2: Winners of Losers R1 play losers from Winners R2
        - Round 3: Winners of Losers R2 play each other
        - Round 4: Winners of Losers R3 play losers from Winners R3
        - ... (alternating pattern)
        """
        losers_matches = []
        losers_round = 1
        
        # Complex logic to interleave losers from winners bracket
        # (Simplified for brevity - full implementation would handle all edge cases)
        
        # Round 1: Losers from Winners Round 1
        winners_r1_matches = [m for m in winners_bracket if m.round_number == 1]
        for i in range(0, len(winners_r1_matches), 2):
            match = Match(
                tournament=self.tournament,
                round_number=losers_round,
                match_number=i // 2 + 1,
                bracket_type='losers',
                participant1=None,  # Loser from Winners R1 Match i
                participant2=None,  # Loser from Winners R1 Match i+1
                state=Match.SCHEDULED
            )
            losers_matches.append(match)
        
        # ... (continue pattern for all losers rounds)
        
        return losers_matches
    
    def _generate_grand_finals(self) -> List[Match]:
        """
        Generate grand finals.
        
        - Match 1: Winners bracket winner vs Losers bracket winner
        - Match 2 (if needed): Reset if losers bracket winner wins Match 1
        """
        grand_finals = [
            Match(
                tournament=self.tournament,
                round_number=999,  # Special round number for grand finals
                match_number=1,
                bracket_type='grand_finals',
                participant1=None,  # Winner of winners bracket
                participant2=None,  # Winner of losers bracket
                state=Match.SCHEDULED,
                is_grand_finals=True
            )
        ]
        
        # Grand finals reset (conditional on Match 1 result)
        grand_finals.append(
            Match(
                tournament=self.tournament,
                round_number=999,
                match_number=2,
                bracket_type='grand_finals_reset',
                participant1=None,
                participant2=None,
                state=Match.SCHEDULED,
                is_conditional=True,  # Only played if losers bracket winner wins Match 1
                is_grand_finals_reset=True
            )
        )
        
        return grand_finals
    
    def get_format_metadata(self) -> Dict:
        n = len(self.participants)
        total_matches = (2 * n) - 2  # Double elim: ~2N-2 matches
        
        return {
            'name': 'Double Elimination',
            'description': 'Two brackets (Winners + Losers). Lose twice, you\'re out.',
            'total_rounds': self.calculate_total_rounds(),
            'total_matches': total_matches,
            'supports_draws': False,
            'has_grand_finals': True,
            'has_grand_finals_reset': True
        }
```

---

#### 7.3.3 Round Robin Generator

```python
# tournaments/bracket_generators/round_robin.py
class RoundRobinGenerator(BracketGeneratorInterface):
    """
    Round robin generator (everyone plays everyone).
    
    Features:
    - Single round robin: Each pair plays once
    - Double round robin: Each pair plays twice (home/away)
    - Final standings based on points (3 for win, 1 for draw, 0 for loss)
    """
    
    def __init__(self, tournament: Tournament, double_round: bool = False):
        super().__init__(tournament)
        self.double_round = double_round
    
    def validate_participant_count(self) -> bool:
        count = len(self.participants)
        if count < 3:
            raise ValidationError("Round robin requires at least 3 participants")
        return True
    
    def calculate_total_rounds(self) -> int:
        """
        Total rounds = N-1 (where N = participants)
        Double round robin: 2 * (N-1)
        """
        n = len(self.participants)
        rounds = n - 1 if n % 2 == 0 else n
        return rounds * 2 if self.double_round else rounds
    
    def generate(self) -> List[Match]:
        """
        Generate round robin schedule using round-robin algorithm.
        
        Algorithm (Circle method):
        1. Fix one participant (#1)
        2. Rotate others clockwise each round
        3. Create pairings
        """
        self.validate_participant_count()
        
        participants = self.participants.copy()
        n = len(participants)
        
        # Add dummy participant if odd number
        if n % 2 != 0:
            participants.append(None)  # Bye
            n += 1
        
        matches = []
        match_number = 1
        
        # Generate single round robin
        for round_num in range(1, n):
            round_matches = []
            
            # Pair participants
            for i in range(n // 2):
                p1 = participants[i]
                p2 = participants[n - 1 - i]
                
                # Skip if bye
                if p1 is None or p2 is None:
                    continue
                
                match = Match(
                    tournament=self.tournament,
                    round_number=round_num,
                    match_number=match_number,
                    participant1=p1,
                    participant2=p2,
                    state=Match.SCHEDULED
                )
                matches.append(match)
                match_number += 1
            
            # Rotate participants (keep first fixed)
            participants = [participants[0]] + [participants[-1]] + participants[1:-1]
        
        # Double round robin: Reverse home/away
        if self.double_round:
            reverse_matches = []
            for match in matches:
                reverse_match = Match(
                    tournament=self.tournament,
                    round_number=match.round_number + (n - 1),
                    match_number=match_number,
                    participant1=match.participant2,  # Swap home/away
                    participant2=match.participant1,
                    state=Match.SCHEDULED
                )
                reverse_matches.append(reverse_match)
                match_number += 1
            
            matches.extend(reverse_matches)
        
        return matches
    
    def get_next_round_matches(self, current_round: int) -> List[Match]:
        """Round robin generates all rounds upfront."""
        return []
    
    def get_format_metadata(self) -> Dict:
        n = len(self.participants)
        total_matches = (n * (n - 1)) // 2  # Combinations: C(n, 2)
        if self.double_round:
            total_matches *= 2
        
        return {
            'name': 'Round Robin' + (' (Double)' if self.double_round else ''),
            'description': 'Everyone plays everyone. Winner determined by points.',
            'total_rounds': self.calculate_total_rounds(),
            'total_matches': total_matches,
            'supports_draws': True,
            'point_system': {'win': 3, 'draw': 1, 'loss': 0}
        }
```

---

#### 7.3.4 Swiss System Generator

```python
# tournaments/bracket_generators/swiss.py
class SwissSystemGenerator(BracketGeneratorInterface):
    """
    Swiss system generator (dynamic pairing based on record).
    
    Features:
    - No elimination (everyone plays all rounds)
    - Pairing based on current standings (similar records play each other)
    - Avoid repeat matchups
    - Typically 4-7 rounds (log2(N) + 1)
    """
    
    def __init__(self, tournament: Tournament, num_rounds: int = None):
        super().__init__(tournament)
        self.num_rounds = num_rounds or (math.ceil(math.log2(len(self.get_seeded_participants()))) + 1)
    
    def validate_participant_count(self) -> bool:
        count = len(self.participants)
        if count < 4:
            raise ValidationError("Swiss system requires at least 4 participants")
        return True
    
    def calculate_total_rounds(self) -> int:
        return self.num_rounds
    
    def generate(self) -> List[Match]:
        """
        Generate Round 1 only (subsequent rounds generated dynamically).
        
        Round 1 pairing: By seed (1 vs 2, 3 vs 4, etc.)
        """
        self.validate_participant_count()
        
        matches = []
        match_number = 1
        
        # Round 1: Pair by seed
        for i in range(0, len(self.participants), 2):
            if i + 1 < len(self.participants):
                match = Match(
                    tournament=self.tournament,
                    round_number=1,
                    match_number=match_number,
                    participant1=self.participants[i],
                    participant2=self.participants[i + 1],
                    state=Match.SCHEDULED
                )
                matches.append(match)
                match_number += 1
        
        return matches
    
    def get_next_round_matches(self, current_round: int) -> List[Match]:
        """
        Generate next round matches based on current standings.
        
        Algorithm:
        1. Get current standings (sorted by wins, then tie-breakers)
        2. Pair top half of each score bracket (avoid repeat matchups)
        3. Create matches
        """
        if current_round >= self.num_rounds:
            return []  # Tournament complete
        
        # Get standings
        standings = self._calculate_standings()
        
        # Group by score (e.g., all 2-0 players together)
        score_groups = {}
        for standing in standings:
            score = standing['wins']
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(standing['registration'])
        
        # Pair within each score group
        matches = []
        match_number = 1
        next_round = current_round + 1
        
        for score, group_participants in sorted(score_groups.items(), reverse=True):
            # Pair participants in this group
            paired = []
            for i in range(0, len(group_participants), 2):
                if i + 1 < len(group_participants):
                    p1 = group_participants[i]
                    p2 = group_participants[i + 1]
                    
                    # Avoid repeat matchups
                    if self._have_played_before(p1, p2):
                        # Try pairing with next available (complex logic)
                        p2 = self._find_unpaired_opponent(p1, group_participants, paired)
                    
                    if p2:
                        match = Match(
                            tournament=self.tournament,
                            round_number=next_round,
                            match_number=match_number,
                            participant1=p1,
                            participant2=p2,
                            state=Match.SCHEDULED
                        )
                        matches.append(match)
                        paired.extend([p1, p2])
                        match_number += 1
        
        return matches
    
    def _calculate_standings(self) -> List[Dict]:
        """Calculate current standings (wins, tie-breakers)."""
        # Query completed matches, count wins
        # (Implementation details omitted for brevity)
        pass
    
    def _have_played_before(self, p1: Registration, p2: Registration) -> bool:
        """Check if two participants have already played."""
        return Match.objects.filter(
            tournament=self.tournament,
            participant1__in=[p1, p2],
            participant2__in=[p1, p2],
            state=Match.COMPLETED
        ).exists()
    
    def _find_unpaired_opponent(self, p1: Registration, group: List[Registration], paired: List[Registration]):
        """Find unpaired opponent who hasn't played p1 before."""
        for p2 in group:
            if p2 not in paired and not self._have_played_before(p1, p2):
                return p2
        return None
    
    def get_format_metadata(self) -> Dict:
        n = len(self.participants)
        total_matches = (n // 2) * self.num_rounds
        
        return {
            'name': 'Swiss System',
            'description': f'{self.num_rounds} rounds. Pairing based on current standings.',
            'total_rounds': self.num_rounds,
            'total_matches': total_matches,
            'supports_draws': True,
            'dynamic_pairing': True
        }
```

---

#### 7.3.5 Group Stage → Knockout Generator

```python
# tournaments/bracket_generators/group_knockout.py
class GroupKnockoutGenerator(BracketGeneratorInterface):
    """
    Multi-stage tournament: Group Stage → Knockout Stage.
    
    Features:
    - Group stage: Round robin within groups
    - Knockout stage: Top N from each group advance to single/double elimination
    - Configurable: groups, advance count, knockout format
    """
    
    def __init__(
        self, 
        tournament: Tournament, 
        num_groups: int = 4,
        advance_per_group: int = 2,
        knockout_format: str = 'single_elimination'
    ):
        super().__init__(tournament)
        self.num_groups = num_groups
        self.advance_per_group = advance_per_group
        self.knockout_format = knockout_format
    
    def validate_participant_count(self) -> bool:
        count = len(self.participants)
        if count < self.num_groups * 2:
            raise ValidationError(f"Need at least {self.num_groups * 2} participants for {self.num_groups} groups")
        return True
    
    def generate(self) -> List[Match]:
        """
        Generate group stage + knockout stage.
        
        Steps:
        1. Distribute participants to groups (seeded distribution)
        2. Generate round robin for each group
        3. Generate knockout bracket (placeholder, filled after group stage)
        """
        self.validate_participant_count()
        
        matches = []
        
        # Step 1: Create groups and assign participants
        groups = self._create_groups()
        
        # Step 2: Generate round robin for each group
        group_matches = self._generate_group_stage(groups)
        matches.extend(group_matches)
        
        # Step 3: Generate knockout stage (participants TBD)
        knockout_matches = self._generate_knockout_stage()
        matches.extend(knockout_matches)
        
        return matches
    
    def _create_groups(self) -> Dict[str, List[Registration]]:
        """Distribute participants to groups (seeded snake draft)."""
        groups = {f'Group {chr(65 + i)}': [] for i in range(self.num_groups)}
        group_names = list(groups.keys())
        
        # Seeded distribution (1→A, 2→B, 3→C, 4→D, 5→D, 6→C, 7→B, 8→A, ...)
        for idx, participant in enumerate(self.participants):
            snake_idx = idx % (2 * self.num_groups)
            if snake_idx < self.num_groups:
                group_idx = snake_idx
            else:
                group_idx = (2 * self.num_groups - 1) - snake_idx
            
            groups[group_names[group_idx]].append(participant)
        
        return groups
    
    def _generate_group_stage(self, groups: Dict[str, List[Registration]]) -> List[Match]:
        """Generate round robin for each group."""
        matches = []
        match_number = 1
        
        for group_name, group_participants in groups.items():
            # Create temporary tournament for round robin
            # (Simplified - actual implementation would handle properly)
            rr_generator = RoundRobinGenerator(self.tournament, double_round=False)
            rr_generator.participants = group_participants
            
            group_matches = rr_generator.generate()
            
            # Tag matches with group name
            for match in group_matches:
                match.group_name = group_name
                match.match_number = match_number
                match_number += 1
            
            matches.extend(group_matches)
        
        return matches
    
    def _generate_knockout_stage(self) -> List[Match]:
        """
        Generate knockout bracket (participants filled after group stage).
        
        Seeding for knockout:
        - 1st place Group A vs 2nd place Group B
        - 1st place Group B vs 2nd place Group A
        - etc.
        """
        # Calculate knockout participants
        knockout_count = self.num_groups * self.advance_per_group
        
        # Generate bracket (single or double elimination)
        if self.knockout_format == 'single_elimination':
            generator = SingleEliminationGenerator(self.tournament)
        elif self.knockout_format == 'double_elimination':
            generator = DoubleEliminationGenerator(self.tournament)
        
        # Generate with placeholder participants
        knockout_matches = generator.generate()
        
        # Mark as knockout stage
        for match in knockout_matches:
            match.is_knockout_stage = True
            match.participant1 = None  # Filled after group stage
            match.participant2 = None
        
        return knockout_matches
    
    def get_format_metadata(self) -> Dict:
        n = len(self.participants)
        group_size = n // self.num_groups
        group_matches_per_group = (group_size * (group_size - 1)) // 2
        total_group_matches = group_matches_per_group * self.num_groups
        knockout_participants = self.num_groups * self.advance_per_group
        knockout_matches = knockout_participants - 1
        
        return {
            'name': f'{self.num_groups} Groups → {self.knockout_format.replace("_", " ").title()}',
            'description': f'Group stage (top {self.advance_per_group} advance) → Knockout stage',
            'total_rounds': None,  # Variable (group rounds + knockout rounds)
            'total_matches': total_group_matches + knockout_matches,
            'supports_draws': True,
            'num_groups': self.num_groups,
            'knockout_format': self.knockout_format
        }
```

---

### 7.4 Bracket Service Integration

**Bracket service uses strategy pattern to select generator**:

```python
# tournaments/services/bracket_service.py
from tournaments.bracket_generators import (
    SingleEliminationGenerator,
    DoubleEliminationGenerator,
    RoundRobinGenerator,
    SwissSystemGenerator,
    GroupKnockoutGenerator
)

class BracketService:
    GENERATORS = {
        'single_elimination': SingleEliminationGenerator,
        'double_elimination': DoubleEliminationGenerator,
        'round_robin': RoundRobinGenerator,
        'round_robin_double': lambda t: RoundRobinGenerator(t, double_round=True),
        'swiss': SwissSystemGenerator,
        'group_knockout': GroupKnockoutGenerator,
    }
    
    @staticmethod
    @transaction.atomic
    def generate_bracket(tournament_id: int) -> List[Match]:
        """
        Generate bracket using appropriate generator for tournament format.
        """
        tournament = Tournament.objects.select_for_update().get(id=tournament_id)
        
        # Select generator
        generator_class = BracketService.GENERATORS.get(tournament.format)
        if not generator_class:
            raise ValueError(f"Unsupported format: {tournament.format}")
        
        # Instantiate generator
        generator = generator_class(tournament)
        
        # Validate and generate
        generator.validate_participant_count()
        matches = generator.generate()
        
        # Save matches to database
        saved_matches = Match.objects.bulk_create(matches)
        
        # Link matches (set next_match_id)
        BracketService._link_matches(saved_matches, tournament.format)
        
        # Update tournament status
        tournament.bracket_generated_at = timezone.now()
        tournament.status = Tournament.BRACKET_GENERATED
        tournament.save()
        
        return saved_matches
    
    @staticmethod
    def _link_matches(matches: List[Match], format: str):
        """
        Link matches to next round (set next_match_id).
        
        Logic varies by format:
        - Single/Double Elimination: Winner advances to specific next match
        - Round Robin/Swiss: No next_match (standings-based)
        """
        if format in ['single_elimination', 'double_elimination']:
            # Link by round pairs (Match 1 + Match 2 → Match 1 of next round)
            rounds = {}
            for match in matches:
                if match.round_number not in rounds:
                    rounds[match.round_number] = []
                rounds[match.round_number].append(match)
            
            for round_num in sorted(rounds.keys())[:-1]:  # Exclude final round
                current_round = rounds[round_num]
                next_round = rounds.get(round_num + 1, [])
                
                for i in range(0, len(current_round), 2):
                    if i + 1 < len(current_round) and i // 2 < len(next_round):
                        match1 = current_round[i]
                        match2 = current_round[i + 1]
                        next_match = next_round[i // 2]
                        
                        match1.next_match = next_match
                        match2.next_match = next_match
                        match1.save()
                        match2.save()
    
    @staticmethod
    @transaction.atomic
    def advance_winner(match_id: int) -> Match:
        """
        Advance match winner to next round.
        
        Called after match completion.
        """
        match = Match.objects.select_for_update().get(id=match_id)
        
        if not match.winner:
            raise ValidationError("Match has no winner")
        
        if not match.next_match:
            return match  # Final match, no advancement
        
        # Add winner to next match
        next_match = Match.objects.select_for_update().get(id=match.next_match_id)
        
        if next_match.participant1 is None:
            next_match.participant1 = match.winner
        elif next_match.participant2 is None:
            next_match.participant2 = match.winner
        else:
            raise ValidationError("Next match already full")
        
        next_match.save()
        
        return next_match
    
    @staticmethod
    def get_bracket_tree(tournament_id: int) -> Dict:
        """
        Get bracket as hierarchical tree (for frontend rendering).
        
        Returns: Nested JSON structure representing bracket
        """
        matches = Match.objects.filter(tournament_id=tournament_id).order_by('round_number', 'match_number')
        
        # Build tree (complex logic - simplified here)
        tree = {
            'format': 'single_elimination',
            'rounds': []
        }
        
        # Group by rounds
        rounds = {}
        for match in matches:
            if match.round_number not in rounds:
                rounds[match.round_number] = []
            rounds[match.round_number].append(match)
        
        # Build round structure
        for round_num in sorted(rounds.keys()):
            round_matches = rounds[round_num]
            tree['rounds'].append({
                'round_number': round_num,
                'matches': [
                    {
                        'id': m.id,
                        'participant1': m.participant1.get_display_name() if m.participant1 else 'TBD',
                        'participant2': m.participant2.get_display_name() if m.participant2 else 'TBD',
                        'winner': m.winner.get_display_name() if m.winner else None,
                        'scores': m.scores
                    }
                    for m in round_matches
                ]
            })
        
        return tree
```

---

### 7.5 Format Selection UI

**Tournament creation wizard includes format selector**:

```python
# Template: tournaments/create_tournament.html
<div class="format-selector">
  <h3>Tournament Format</h3>
  
  <div class="format-grid">
    <div class="format-card" data-format="single_elimination">
      <h4>Single Elimination</h4>
      <p>Standard knockout bracket. Lose once, you're out.</p>
      <span class="badge">Best for: Quick tournaments</span>
    </div>
    
    <div class="format-card" data-format="double_elimination">
      <h4>Double Elimination</h4>
      <p>Winners + Losers bracket. Lose twice, you're out.</p>
      <span class="badge">Best for: Competitive fairness</span>
    </div>
    
    <div class="format-card" data-format="round_robin">
      <h4>Round Robin</h4>
      <p>Everyone plays everyone. Winner by points.</p>
      <span class="badge">Best for: Small groups (4-8 teams)</span>
    </div>
    
    <div class="format-card" data-format="swiss">
      <h4>Swiss System</h4>
      <p>4-7 rounds. Pairing based on standings.</p>
      <span class="badge">Best for: Large tournaments</span>
    </div>
    
    <div class="format-card" data-format="group_knockout">
      <h4>Group Stage → Knockout</h4>
      <p>Preliminary groups, then elimination bracket.</p>
      <span class="badge">Best for: World Cup style</span>
    </div>
  </div>
  
  <!-- Format-specific settings (shown after selection) -->
  <div id="format-settings" class="hidden">
    <!-- Single Elimination: No extra settings -->
    
    <!-- Double Elimination: Grand finals reset? -->
    <div data-format="double_elimination">
      <label>
        <input type="checkbox" name="grand_finals_reset" checked>
        Enable grand finals bracket reset
      </label>
    </div>
    
    <!-- Round Robin: Single or double round? -->
    <div data-format="round_robin">
      <label>
        <input type="radio" name="round_robin_type" value="single" checked> Single Round Robin
      </label>
      <label>
        <input type="radio" name="round_robin_type" value="double"> Double Round Robin
      </label>
    </div>
    
    <!-- Swiss: Number of rounds -->
    <div data-format="swiss">
      <label>Number of rounds:
        <input type="number" name="swiss_rounds" value="5" min="3" max="10">
      </label>
    </div>
    
    <!-- Group Knockout: Groups + advance count -->
    <div data-format="group_knockout">
      <label>Number of groups:
        <select name="num_groups">
          <option value="2">2 Groups</option>
          <option value="4" selected>4 Groups</option>
          <option value="8">8 Groups</option>
        </select>
      </label>
      <label>Teams advancing per group:
        <select name="advance_per_group">
          <option value="1">Top 1</option>
          <option value="2" selected>Top 2</option>
          <option value="4">Top 4</option>
        </select>
      </label>
      <label>Knockout format:
        <select name="knockout_format">
          <option value="single_elimination" selected>Single Elimination</option>
          <option value="double_elimination">Double Elimination</option>
        </select>
      </label>
    </div>
  </div>
</div>
```

---

## 8. Organizer & Admin Guidance System

### Phase 1: Foundation (Weeks 1-4)

**Goals**: Establish core architecture patterns

**Deliverables**:
1. Create `apps/tournament_ops/` app
2. Implement adapter pattern:
   - `TeamAdapter`
   - `UserAdapter`
   - `GameAdapter`
   - `EconomyAdapter`
3. Define DTOs for cross-domain data transfer
4. Refactor 3 parallel registration systems → 1 unified system
5. Add draft persistence with unique registration numbers

**Success Criteria**:
- ✅ No direct model imports in tournaments app (all via adapters)
- ✅ Single registration workflow (Classic Wizard deprecated)
- ✅ Draft persistence working (cross-device resume)

---

### Phase 2: Event System (Weeks 5-8)

**Goals**: Implement event-driven architecture

**Deliverables**:
1. Create `DomainEvent` model and `EventBus` service
2. Implement event handlers:
   - `MatchCompletedEvent` → Update stats, history, rankings
   - `TournamentCompletedEvent` → Prizes, certificates, leaderboards
   - `RegistrationCompletedEvent` → User stats
   - `PaymentVerifiedEvent` → Registration confirmation
3. Migrate existing manual updates to event handlers
4. Add event replay capability (for debugging/backfill)

**Success Criteria**:
- ✅ All stats updates happen via events (no manual service calls)
- ✅ Event log stores all domain events
- ✅ Event handlers are idempotent (safe retries)

---

### Phase 3: Stats & History (Weeks 9-12)

**Goals**: Complete user/team analytics

**Deliverables**:
1. Create `UserTournamentStats` model
2. Create `UserTournamentHistory` model
3. Populate `TeamMatchHistory` (currently unused)
4. Implement `UserStatsService` with event handlers
5. Build user stats dashboard (my tournaments, W/L record, earnings)
6. Backfill historical data from existing registrations

**Success Criteria**:
- ✅ User stats auto-update after every match/tournament
- ✅ Team stats auto-update (matches_won, win_rate, tournaments_won)
- ✅ Match history populated for all completed matches

---

### Phase 4: Leaderboards (Weeks 13-16)

**Goals**: Global rankings and leaderboards

**Deliverables**:
1. Create `apps/leaderboards/` app
2. Implement `RankingService`:
   - ELO rating calculation
   - Tournament points system
   - Win rate rankings
3. Create `LeaderboardAdapter` for tournaments integration
4. Build leaderboard UI (global, per-game, per-region)
5. Add event handler: `TournamentCompletedEvent` → Update rankings

**Success Criteria**:
- ✅ Leaderboards auto-update after tournament completion
- ✅ ELO ratings calculated for all matches
- ✅ Top 100 players per game visible on site

---

### Phase 5: Configuration & Flexibility (Weeks 17-20)

**Goals**: Make system game-agnostic and configurable

**Deliverables**:
1. Create `GamePlayerIdentityConfig` model
2. Create `EligibilityRule` model (configurable per tournament)
3. Migrate hardcoded game logic to config:
   - Replace 7 if-else checks with config-driven field resolution
   - Move rank restrictions to eligibility rules
4. Build admin UI for configuring games/rules
5. Add 2-3 new games to prove config-driven approach works

**Success Criteria**:
- ✅ Adding new game requires only config (no code deployment)
- ✅ Organizers can set custom eligibility rules via admin
- ✅ All game-specific logic driven by database config

---

### Phase 6: API & Mobile-Ready (Weeks 21-24)

**Goals**: RESTful API for all workflows

**Deliverables**:
1. Build DRF (Django REST Framework) API endpoints:
   - `POST /api/v1/tournaments/{id}/registrations/`
   - `POST /api/v1/matches/{id}/results/`
   - `POST /api/v1/tournaments/{id}/finalize/`
   - `GET /api/v1/leaderboards/{game_slug}/`
2. Add OpenAPI documentation (Swagger UI)
3. Implement API authentication (JWT tokens)
4. Build API rate limiting
5. Create API client SDK (Python/JavaScript)

**Success Criteria**:
- ✅ All TournamentOps workflows accessible via API
- ✅ OpenAPI docs auto-generated and browsable
- ✅ Third-party integrations possible (Discord bots)

---

## 6. Success Metrics

### Platform Health Metrics

| Metric | Current | Target (6 months) |
|--------|---------|-------------------|
| Registration completion rate | ~60% | 85%+ |
| Payment verification time (avg) | 24 hours | <6 hours |
| Match result dispute rate | Unknown | <3% |
| Tournament completion rate | ~75% | 90%+ |
| User retention (30-day) | Unknown | 40%+ |

### Technical Metrics

| Metric | Current | Target (6 months) |
|--------|---------|-------------------|
| API response time (p95) | N/A | <500ms |
| Event handler success rate | N/A | >99% |
| Code coverage (unit tests) | ~40% | 70%+ |
| Direct model imports (cross-app) | 50+ | 0 |
| Hardcoded game logic instances | 7+ | 0 |

---

## 7. Appendix: Technology Stack

### Current Stack
- **Backend**: Django 4.x + Python 3.11
- **Database**: PostgreSQL 15
- **Cache**: Redis (sessions, caching)
- **Storage**: AWS S3 (media, certificates)
- **Frontend**: Django templates + Tailwind CSS + vanilla JS
- **Task Queue**: Celery (background jobs)

### Planned Additions
- **Event Bus**: RabbitMQ or Redis Streams (domain events)
- **API Framework**: Django REST Framework (DRF)
- **WebSockets**: Django Channels (live match updates)
- **Monitoring**: Prometheus + Grafana (metrics)
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)

---

## 8. Conclusion

DeltaCrown's **expanded target architecture** now includes:

1. **Clean domain boundaries** between Games, Teams, Tournaments, Economy, TournamentOps, Leaderboards
2. **Loose coupling** via adapters and events (zero direct model imports)
3. **Configuration-driven** game support (add games without code changes)
4. **Event-driven** stats updates (automatic, no manual triggers)
5. **API-first** design (mobile-ready, integration-friendly)
6. **Frontend developer support** (OpenAPI specs, TypeScript types, UI schemas, design tokens)
7. **Universal bracket formats** (pluggable generators for all esports formats)
8. **Manual tournament management** (organizer control over seeding, brackets, scheduling, results)
9. **Intelligent guidance systems** (organizer onboarding, player hints, contextual help)
10. **Comprehensive audit trails** (full history of all tournament actions)

**Key Architectural Enhancements**:

- **Frontend Support System**: Complete documentation ecosystem (API specs, TypeScript contracts, JSON form schemas, design tokens, UX guidelines) ensures frontend-backend alignment
- **Multi-Format Bracket Engine**: Pluggable bracket generators support Single/Double Elimination, Round Robin, Swiss, Group→Knockout formats with format-specific configuration
- **Manual Management Layer**: Organizers have granular control (manual seeding, bracket editing, match scheduling, result override, results inbox approval)
- **Guidance Engine**: Context-aware next actions, error prevention warnings, onboarding checklists, and inline help reduce organizer errors
- **Results Inbox**: Player-submitted results → Organizer review → Conflict detection → Approval/rejection workflow with audit logging

By following these enhanced architectural principles and the expanded roadmap, DeltaCrown will become a **world-class, scalable, multi-game esports platform** supporting millions of players across 11+ games with:
- Professional-grade tournament management tools
- Seamless frontend-backend collaboration
- Flexible tournament formats (all major esports structures)
- Intelligent automation with manual override capabilities
- Comprehensive guidance and error prevention

**Total Architecture Completeness**: This document now defines **complete end-to-end architecture** from frontend contracts through domain services to infrastructure, with clear guidance for both developers (frontend + backend) and users (organizers + players).

---

**End of Enhanced Architecture Plan**
