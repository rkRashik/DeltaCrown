# Part 6/6: Smart Registration & Architecture Recommendations

**Document Purpose**: Recommendations for evolving DeltaCrown's tournament system into a modern, automated platform with smart registration, automatic stat propagation, and clean service boundaries.

**Audit Date**: December 8, 2025  
**Scope**: Future architecture, smart registration design, automation strategy

---

## 1. Smart Registration System Design

### 1.1 Auto-Fill Intelligence

**Current State** (from Part 3):
- ✅ Auto-fill from UserProfile (riot_id, phone, discord, etc.)
- ✅ Auto-fill from Team model (team_name, captain_name, etc.)
- ✅ Visual feedback (progress bars, badges, confidence levels)
- ❌ Hardcoded game logic (7 if-else checks for game slugs)
- ❌ All fields editable (no field locking)

**Recommended Evolution**:

#### A. Dynamic Field Resolution via Game Configuration

Replace hardcoded game checks with configuration-driven field mapping:

```python
# Current (hardcoded):
if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id or ''
elif game_slug == 'pubg-mobile':
    auto_filled['game_id'] = profile.pubg_mobile_id or ''
# ... 7 total games

# Recommended (configuration-driven):
identity_configs = game_service.get_identity_validation_rules(tournament.game)
for config in identity_configs:
    field_value = getattr(user_profile, config.field_name, None)
    if field_value:
        auto_filled[config.display_name] = AutoFillField(
            value=field_value,
            source='game_account',
            locked=config.is_immutable,  # NEW: Lock critical fields
            validation_pattern=config.validation_pattern,
            field_name=config.field_name
        )
```

**Benefits**:
- ✅ Adding new games requires only config changes (no code deployment)
- ✅ Game-specific validation rules (Riot ID format, Steam ID length, etc.)
- ✅ Field immutability controlled per game configuration

---

#### B. Field Locking Strategy

**Critical Fields (Should Be Locked)**:
1. **User Identity**:
   - User ID (always locked, never displayed)
   - Email (locked if verified, display only)
   - Phone (locked if verified, display only)
   
2. **Platform Identity**:
   - Riot ID (locked after verification)
   - Steam ID (locked after verification)
   - Platform-specific IDs (locked if verified via OAuth)
   
3. **Team Identity** (team tournaments):
   - Team ID (locked, hidden field)
   - Team Name (locked if official team)
   - Captain (locked, read-only display)

**Editable Fields**:
- Display Name / In-game Name (cosmetic)
- Discord Username (can change)
- Preferred Contact Method (preference)
- Age (can update if birthday passed)

**Implementation**:

```python
class AutoFillField:
    value: Any
    source: str              # 'profile' | 'team' | 'game_account'
    confidence: str          # 'high' | 'medium' | 'low'
    locked: bool = False     # NEW: Field immutability
    verified: bool = False   # NEW: Email/phone verification status
    validation_pattern: str = None
    help_text: str = None
```

**Template Rendering**:
```django
{% if autofill_data.email.locked %}
    <input type="email" value="{{ autofill_data.email.value }}" readonly disabled
           class="bg-gray-700 cursor-not-allowed">
    <span class="text-xs text-gray-400">
        <i class="fas fa-lock"></i> Verified - Cannot be changed
    </span>
{% else %}
    <input type="email" value="{{ autofill_data.email.value }}">
{% endif %}
```

---

#### C. Unique Registration Number System

**Problem**: No unique identifier for tracking registration forms across sessions/devices.

**Recommended Solution**:

```python
class RegistrationDraft(models.Model):
    """
    Persistent draft storage for multi-session registration.
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    registration_number = models.CharField(
        max_length=20, 
        unique=True, 
        help_text="Human-readable: TOURN-2025-001234"
    )
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    tournament = models.ForeignKey('tournaments.Tournament', on_delete=models.CASCADE)
    form_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    last_saved_at = models.DateTimeField(auto_now=True)
    submitted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = [('user', 'tournament')]  # One draft per user per tournament
```

**Registration Number Format**:
- Pattern: `{TOURNAMENT_PREFIX}-{YEAR}-{SEQUENCE}`
- Example: `VCT-2025-001234`, `PUBG-2025-005678`
- Benefits: Easy support lookup, printable on certificates, URL-friendly

**Usage Flow**:
1. User clicks "Register" → Create `RegistrationDraft` with UUID
2. Auto-save every 30 seconds → Update `form_data` JSONB
3. User switches device → Resume via UUID in URL: `/register?draft=abc123-def456`
4. Submit form → Create `Registration` record, mark draft as `submitted=True`

---

#### D. Eligibility Validation via Configuration

**Current State** (from Part 2):
- ✅ Basic eligibility checks (age, already registered, team requirements)
- ❌ No game-specific validation (rank restrictions, server locks, platform requirements)
- ❌ No team size validation against game config

**Recommended Eligibility Engine**:

```python
class EligibilityRule(models.Model):
    """
    Configurable eligibility rules per tournament.
    """
    tournament = models.ForeignKey('tournaments.Tournament', on_delete=models.CASCADE)
    rule_type = models.CharField(choices=[
        ('MIN_AGE', 'Minimum Age'),
        ('MAX_AGE', 'Maximum Age'),
        ('MIN_RANK', 'Minimum Rank'),
        ('MAX_RANK', 'Maximum Rank'),
        ('SERVER_LOCK', 'Server/Region Lock'),
        ('PLATFORM_LOCK', 'Platform Restriction'),
        ('VERIFIED_ACCOUNT', 'Verified Account Required'),
        ('TEAM_SIZE', 'Team Size Requirement'),
    ])
    config = models.JSONField(help_text='{"min": 18} or {"allowed_servers": ["Asia", "SEA"]}')
    error_message = models.TextField(help_text='Custom error shown to user')
    
class RegistrationEligibilityService:
    @staticmethod
    def check_eligibility(tournament, user, team=None) -> EligibilityResult:
        """
        Execute all eligibility rules for tournament.
        Returns aggregated pass/fail with specific reasons.
        """
        rules = EligibilityRule.objects.filter(tournament=tournament, is_active=True)
        failures = []
        
        for rule in rules:
            validator = RULE_VALIDATORS[rule.rule_type]
            passed, reason = validator(user, team, rule.config)
            if not passed:
                failures.append(reason)
        
        return EligibilityResult(
            is_eligible=(len(failures) == 0),
            reasons=failures
        )
```

**Example Rules**:
```python
# Tournament: Valorant Championship
EligibilityRule.objects.create(
    tournament=vct,
    rule_type='MIN_RANK',
    config={'min_rank': 'Diamond', 'rank_field': 'valorant_rank'},
    error_message='Minimum rank: Diamond (you are {user_rank})'
)

EligibilityRule.objects.create(
    tournament=vct,
    rule_type='SERVER_LOCK',
    config={'allowed_servers': ['Asia', 'Southeast Asia']},
    error_message='Tournament restricted to Asia/SEA servers'
)
```

**Benefits**:
- ✅ Tournament organizers configure rules via admin (no code changes)
- ✅ Rules evaluated in order with clear failure messages
- ✅ Can require verified accounts (email/phone verification)
- ✅ Game-agnostic system (works for any game via JSONB config)

---

### 1.2 Registration Workflow Improvements

**Current Issues** (from Part 4):
- ❌ 3 parallel registration systems (Classic Wizard, Form Builder, Legacy)
- ❌ Session-based wizard data (lost on session expiration)
- ❌ No cross-device resume capability

**Recommended Unified Registration Flow**:

```
┌─────────────────────────────────────────────────────────────┐
│ Step 0: Pre-Registration Check                             │
│  - Check eligibility (async API call)                      │
│  - Display clear pass/fail with reasons                    │
│  - Show "Continue to Register" only if eligible            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Step 1: Create Draft (Server-side)                         │
│  - POST /api/tournaments/{slug}/registration/drafts/        │
│  - Returns: {draft_uuid, registration_number, resume_url}  │
│  - Auto-fill data loaded from UserProfile/Team             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Step 2: Multi-Step Form (with Auto-save)                   │
│  - Auto-save to draft every 30 seconds (PUT /drafts/{uuid})│
│  - Lock verified fields (show lock icon)                   │
│  - Real-time validation via API (as user types)            │
│  - Progress indicator (% complete)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Step 3: Review & Submit                                     │
│  - Display all data with edit links (unlocked fields only) │
│  - Show registration number: VCT-2025-001234               │
│  - Accept terms checkbox                                   │
│  - Submit → POST /api/registrations/ (atomic)              │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Step 4: Payment (if required)                              │
│  - DeltaCoin: Instant verification ✅                      │
│  - Manual: Upload proof → PENDING state                    │
│  - Webhook integration for payment gateways (future)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ Step 5: Confirmation                                        │
│  - Display registration number                             │
│  - Email confirmation with calendar invite (.ics)          │
│  - Add to "My Tournaments" dashboard                       │
└─────────────────────────────────────────────────────────────┘
```

**Key Improvements**:
1. **API-First Design**: RESTful endpoints (`/api/tournaments/{id}/registrations/`)
2. **Draft Persistence**: Database-backed drafts (not session-only)
3. **Cross-Device Resume**: UUID-based draft URLs
4. **Real-Time Validation**: Field-level validation API (`/api/validate-field/`)
5. **Atomic Submission**: Single transaction for Registration + Payment + Wallet deduction

---

## 2. Automation & Result Propagation

### 2.1 Current Gaps (from Part 5)

**Missing Auto-Updates**:
- ❌ Team stats (wins, losses, win_rate, tournaments_won)
- ❌ User stats (no model exists)
- ❌ Match history (TeamMatchHistory model exists but never populated)
- ❌ Rankings/leaderboards (no integration)
- ❌ DeltaCoin match rewards (TODO in code)

**What Works**:
- ✅ Match completion → Bracket progression
- ✅ Tournament completion → TournamentResult creation
- ✅ DeltaCoin payments → Wallet updates

---

### 2.2 Recommended Event-Driven Architecture

**Core Principle**: One action (match result) triggers cascading updates via event system.

```python
# Example: Match result confirmed
@transaction.atomic
def confirm_match_result(match_id: int, confirmed_by: User):
    match = Match.objects.select_for_update().get(id=match_id)
    
    # 1. Update match record
    match.state = Match.COMPLETED
    match.completed_at = timezone.now()
    match.save()
    
    # 2. Emit domain event
    events.publish(MatchCompletedEvent(
        match_id=match.id,
        tournament_id=match.tournament_id,
        winner_id=match.winner_id,
        loser_id=match.loser_id,
        participant1_score=match.participant1_score,
        participant2_score=match.participant2_score,
    ))
    
    # All downstream updates happen via event handlers (decoupled)
```

**Event Handlers (Separate Services)**:

```python
# Handler 1: BracketService
@event_handler(MatchCompletedEvent)
def update_bracket_progression(event: MatchCompletedEvent):
    BracketService.advance_winner_to_next_round(event.match_id)

# Handler 2: TeamStatsService
@event_handler(MatchCompletedEvent)
def update_team_stats(event: MatchCompletedEvent):
    TeamStatsService.record_match_result(
        team_id=event.winner_id,
        result='win',
        match_id=event.match_id
    )
    TeamStatsService.record_match_result(
        team_id=event.loser_id,
        result='loss',
        match_id=event.match_id
    )

# Handler 3: MatchHistoryService
@event_handler(MatchCompletedEvent)
def create_match_history(event: MatchCompletedEvent):
    MatchHistoryService.create_history_entry(event)

# Handler 4: RankingService
@event_handler(MatchCompletedEvent)
def update_rankings(event: MatchCompletedEvent):
    RankingService.update_elo_ratings(
        winner_id=event.winner_id,
        loser_id=event.loser_id
    )

# Handler 5: EconomyService (DeltaCoin rewards)
@event_handler(MatchCompletedEvent)
def award_match_rewards(event: MatchCompletedEvent):
    reward_amount = calculate_match_reward(event.tournament_id)
    EconomyService.award_deltacoin(
        user_id=event.winner_id,
        amount=reward_amount,
        reason=f'Match win in tournament {event.tournament_id}'
    )

# Handler 6: NotificationService
@event_handler(MatchCompletedEvent)
def send_notifications(event: MatchCompletedEvent):
    NotificationService.notify_match_result(event)
```

**Benefits**:
- ✅ Single trigger → Multiple updates (no forgotten steps)
- ✅ Services decoupled (TeamStatsService doesn't know about RankingService)
- ✅ Easy to add new handlers (e.g., AchievementService for badges)
- ✅ Event log serves as audit trail
- ✅ Handlers can be async (non-blocking)

---

### 2.3 Tournament Completion Cascade

**Recommended Event Flow**:

```python
# Organizer triggers winner determination
TournamentOpsService.finalize_tournament(tournament_id)
    ↓
# Event 1: TournamentCompletedEvent
events.publish(TournamentCompletedEvent(
    tournament_id=...,
    winner_id=...,
    runner_up_id=...,
    third_place_id=...,
))
    ↓
# Handler 1: Update Tournament Status
Tournament.objects.filter(id=...).update(status='COMPLETED')
    ↓
# Handler 2: Award Prizes (via EconomyService)
PayoutService.process_payouts(tournament_id)
    ↓
# Handler 3: Generate Certificates (Bulk)
CertificateService.generate_bulk_certificates(tournament_id)
    ↓
# Handler 4: Update Team Tournament Counts
TeamStatsService.increment_tournaments_participated([winner_id, runner_up_id, ...])
TeamStatsService.increment_tournaments_won(winner_id)
    ↓
# Handler 5: Update User Histories (NEW)
UserHistoryService.record_tournament_participation(all_participants)
UserHistoryService.record_podium_finish(winner_id, placement='1st')
    ↓
# Handler 6: Update Rankings/Leaderboards
RankingService.award_tournament_points(tournament_id)
LeaderboardService.recalculate_rankings(game_id)
    ↓
# Handler 7: Send Notifications
NotificationService.send_winner_announcement(tournament_id)
NotificationService.send_certificate_ready_emails(participants)
```

**Key Design Principles**:
1. **Idempotent Handlers**: Re-running event doesn't duplicate rewards/certificates
2. **Compensating Transactions**: Failed handler triggers rollback event (e.g., RefundPrizesEvent)
3. **Event Sourcing**: Store all events in `DomainEvent` table for audit/replay
4. **Async Execution**: Non-critical handlers (notifications, certificates) run async

---

### 2.4 Stats Models & Services (NEW)

**Recommended Models**:

```python
class UserTournamentStats(models.Model):
    """
    Per-user tournament statistics (NEW - does not exist).
    """
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='tournament_stats')
    
    # Tournament Participation
    tournaments_entered = models.PositiveIntegerField(default=0)
    tournaments_completed = models.PositiveIntegerField(default=0)
    tournaments_won = models.PositiveIntegerField(default=0)
    podium_finishes = models.PositiveIntegerField(default=0)  # Top 3
    
    # Match Statistics
    matches_played = models.PositiveIntegerField(default=0)
    matches_won = models.PositiveIntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Rewards
    total_deltacoin_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_prize_money = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Per-game breakdown (JSONB)
    game_stats = models.JSONField(default=dict, help_text='{game_slug: {wins, losses, ...}}')
    
    updated_at = models.DateTimeField(auto_now=True)

class UserTournamentHistory(models.Model):
    """
    Individual tournament participation records (NEW).
    """
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='tournament_history')
    tournament = models.ForeignKey('tournaments.Tournament', on_delete=models.CASCADE)
    registration = models.OneToOneField('tournaments.Registration', on_delete=models.CASCADE)
    
    placement = models.CharField(max_length=20, null=True, help_text='1st, 2nd, 3rd, Top 8, etc.')
    deltacoin_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    matches_played = models.PositiveIntegerField(default=0)
    matches_won = models.PositiveIntegerField(default=0)
    
    certificate_generated = models.BooleanField(default=False)
    certificate = models.ForeignKey('tournaments.Certificate', null=True, on_delete=models.SET_NULL)
    
    created_at = models.DateTimeField(auto_now_add=True)
```

**Service Methods**:

```python
class UserStatsService:
    @staticmethod
    def record_tournament_completion(user_id: int, tournament_id: int, placement: str):
        stats, _ = UserTournamentStats.objects.get_or_create(user_id=user_id)
        
        stats.tournaments_completed += 1
        if placement == '1st':
            stats.tournaments_won += 1
            stats.podium_finishes += 1
        elif placement in ['2nd', '3rd']:
            stats.podium_finishes += 1
        
        stats.save()
        
        # Create history record
        UserTournamentHistory.objects.create(
            user_id=user_id,
            tournament_id=tournament_id,
            placement=placement
        )
    
    @staticmethod
    def record_match_result(user_id: int, match_id: int, result: str):
        stats, _ = UserTournamentStats.objects.get_or_create(user_id=user_id)
        
        stats.matches_played += 1
        if result == 'win':
            stats.matches_won += 1
        
        stats.win_rate = (stats.matches_won / stats.matches_played) * 100
        stats.save()
```

---

## 3. Architectural Recommendations

### 3.1 Current Architecture Issues

**Problems Identified**:
1. **Tight Coupling**: Tournament views directly import Team, UserProfile, DeltaCrownWallet models
2. **Hardcoded Logic**: Game-specific logic scattered in views (7 if-else checks)
3. **Fragmented Registration**: 3 parallel systems (Classic Wizard, Form Builder, Legacy)
4. **Missing Abstractions**: No TeamService, UserService, GameService wrappers
5. **No Event System**: Updates require manual service calls (easy to forget)
6. **IntegerField References**: team_id is int, not ForeignKey (loose coupling but no constraints)

**Source Evidence** (from Part 2):
- 12+ direct Team model imports across tournament views
- 7 hardcoded game slug checks in `registration_wizard.py`
- No service layer for cross-app communication

---

### 3.2 Recommended Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Web Views   │  │   REST API   │  │  GraphQL     │          │
│  │  (Django)    │  │  (DRF)       │  │  (Future)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│              APPLICATION LAYER (TournamentOps)                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  TournamentOpsService (Orchestration)                      │ │
│  │   - create_and_publish_tournament()                        │ │
│  │   - process_registration_workflow()                        │ │
│  │   - finalize_tournament()                                  │ │
│  │   - handle_payment_verification()                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   DOMAIN SERVICES LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Tournament   │  │ Registration │  │   Bracket    │          │
│  │   Service    │  │   Service    │  │   Service    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    Match     │  │   Payment    │  │  Certificate │          │
│  │   Service    │  │   Service    │  │   Service    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│              INTEGRATION/ADAPTER LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ TeamAdapter  │  │ UserAdapter  │  │ GameAdapter  │          │
│  │ (teams app)  │  │ (accounts)   │  │ (games app)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │EconomyAdapter│  │LeaderboardAdp│                            │
│  │ (economy app)│  │(leaderboards)│                            │
│  └──────────────┘  └──────────────┘                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │    Redis     │  │   S3/CDN     │          │
│  │  (Primary)   │  │  (Cache)     │  │   (Media)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │  WebSocket   │  │  EventBus    │                            │
│  │  (Channels)  │  │ (RabbitMQ)   │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.3 TournamentOps Layer (Orchestration)

**Purpose**: High-level workflows that coordinate multiple domain services.

**Example: Registration Workflow Orchestration**

```python
class TournamentOpsService:
    """
    Orchestrates complex multi-service workflows.
    Domain services remain simple, single-responsibility.
    """
    
    @staticmethod
    @transaction.atomic
    def process_registration_workflow(
        tournament_id: int,
        user_id: int,
        registration_data: dict,
        payment_method: str = None
    ) -> Registration:
        """
        Complete registration workflow orchestration.
        
        Steps:
        1. Validate eligibility (via GameAdapter, TeamAdapter)
        2. Create registration record
        3. Process payment (via EconomyAdapter)
        4. Send notifications (via NotificationService)
        5. Update user stats (via UserAdapter)
        """
        
        # Step 1: Eligibility check (cross-app)
        tournament = TournamentService.get_tournament(tournament_id)
        user = UserAdapter.get_user(user_id)
        team = TeamAdapter.get_user_team(user_id) if tournament.is_team_based else None
        
        eligibility = RegistrationEligibilityService.check_eligibility(
            tournament, user, team
        )
        if not eligibility.is_eligible:
            raise ValidationError(eligibility.reasons)
        
        # Step 2: Create registration
        registration = RegistrationService.create_registration(
            tournament_id=tournament_id,
            user_id=user_id,
            data=registration_data
        )
        
        # Step 3: Payment processing
        if tournament.has_entry_fee:
            if payment_method == 'deltacoin':
                # Via EconomyAdapter (decoupled from economy app)
                EconomyAdapter.process_deltacoin_payment(
                    user_id=user_id,
                    amount=tournament.entry_fee_amount,
                    reason=f'Tournament registration: {tournament.name}',
                    idempotency_key=f'reg-{registration.id}'
                )
                registration.status = Registration.CONFIRMED
            else:
                # Manual payment
                PaymentService.create_payment_record(
                    registration_id=registration.id,
                    payment_method=payment_method
                )
                registration.status = Registration.PAYMENT_SUBMITTED
            
            registration.save()
        
        # Step 4: Update user stats (via UserAdapter)
        UserAdapter.increment_tournaments_entered(user_id)
        
        # Step 5: Send notifications
        NotificationService.send_registration_confirmation(registration)
        
        # Step 6: Publish domain event
        events.publish(RegistrationCompletedEvent(
            registration_id=registration.id,
            tournament_id=tournament_id,
            user_id=user_id
        ))
        
        return registration
```

**Benefits**:
- ✅ All cross-app logic in one place (TournamentOps layer)
- ✅ Domain services remain simple (RegistrationService only creates records)
- ✅ Easy to test orchestration separately from domain logic
- ✅ Clear separation: Domain = "what", TournamentOps = "how"

---

### 3.4 Adapter Pattern for Cross-App Integration

**Problem**: Direct imports create tight coupling.

**Current** (from Part 2):
```python
# tournaments/views/registration_wizard.py
from apps.teams.models import Team  # Direct import
from apps.user_profile.models import UserProfile
from apps.economy.models import DeltaCrownWallet

team = Team.objects.get(id=team_id)  # Direct query
```

**Recommended** (Adapter Pattern):

```python
# tournaments/adapters/team_adapter.py
class TeamAdapter:
    """
    Adapter for teams app integration.
    Isolates tournaments app from teams app changes.
    """
    
    @staticmethod
    def get_team(team_id: int) -> TeamDTO:
        """
        Fetch team data via service call (not direct model import).
        Returns DTO (Data Transfer Object) to avoid coupling to Team model.
        """
        from apps.teams.services import TeamService
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
    def check_user_team_permission(user_id: int, team_id: int) -> bool:
        """Check if user can register team for tournaments."""
        from apps.teams.services import TeamService
        return TeamService.has_tournament_permission(user_id, team_id)
    
    @staticmethod
    def update_team_stats(team_id: int, stats_update: dict):
        """Update team stats after match (decoupled)."""
        from apps.teams.services import TeamStatsService
        TeamStatsService.update_stats(team_id, stats_update)

# Usage in tournaments app
team_data = TeamAdapter.get_team(team_id)  # No direct Team import
if not TeamAdapter.check_user_team_permission(user.id, team_id):
    raise PermissionDenied()
```

**Benefits**:
- ✅ No direct model imports (only adapter imports)
- ✅ teams app can refactor Team model without breaking tournaments app
- ✅ Easy to mock adapters in tests
- ✅ Clear API contract via DTOs

**Adapters to Create**:
- `TeamAdapter` (teams app integration)
- `UserAdapter` (user profile integration)
- `GameAdapter` (game configuration integration)
- `EconomyAdapter` (DeltaCoin/wallet integration)
- `LeaderboardAdapter` (rankings integration)

---

### 3.5 Service Boundaries & Responsibilities

**Clear Separation**:

```
┌──────────────────────────────────────────────────────────┐
│ TournamentOps (apps/tournament_ops/)                     │
│  - Workflow orchestration                                │
│  - Cross-app coordination                                │
│  - Business process management                           │
│  - Event publishing                                      │
└──────────────────────────────────────────────────────────┘
        ↓ calls ↓
┌──────────────────────────────────────────────────────────┐
│ Tournament Domain Services (apps/tournaments/services/)  │
│  - TournamentService: CRUD, lifecycle management         │
│  - RegistrationService: Registration records only        │
│  - BracketService: Bracket tree logic                    │
│  - MatchService: Match state machine                     │
│  - PaymentService: Payment record management             │
│  - CertificateService: PDF generation                    │
└──────────────────────────────────────────────────────────┘
        ↓ uses ↓
┌──────────────────────────────────────────────────────────┐
│ Cross-App Adapters (apps/tournaments/adapters/)          │
│  - TeamAdapter: Team data/permissions                    │
│  - UserAdapter: User profile/stats                       │
│  - GameAdapter: Game configs/identity rules              │
│  - EconomyAdapter: Wallet operations                     │
│  - LeaderboardAdapter: Ranking updates                   │
└──────────────────────────────────────────────────────────┘
```

**Rules**:
1. **TournamentOps** can call **Domain Services** + **Adapters**
2. **Domain Services** can call **other Domain Services** + **Adapters**
3. **Domain Services** CANNOT call **TournamentOps** (no circular dependencies)
4. **Adapters** CANNOT call **Domain Services** (one-way dependency)
5. **Views** should call **TournamentOps** (not Domain Services directly)

---

### 3.6 Migration Strategy (Incremental)

**Phase 1: Consolidate Registration Systems** (2-3 weeks)
- ✅ Deprecate Legacy and Form Builder registration
- ✅ Enhance Classic Wizard with draft persistence
- ✅ Add field locking and unique registration numbers
- ✅ Implement eligibility rules engine

**Phase 2: Create Adapter Layer** (2-3 weeks)
- ✅ Create TeamAdapter, UserAdapter, GameAdapter, EconomyAdapter
- ✅ Refactor existing views to use adapters (replace direct imports)
- ✅ Add DTOs for cross-app data transfer
- ✅ Write adapter tests with mocks

**Phase 3: Implement Event System** (3-4 weeks)
- ✅ Create DomainEvent model and EventBus service
- ✅ Add event handlers for match completion (stats, history, rankings)
- ✅ Add event handlers for tournament completion (prizes, certificates)
- ✅ Migrate existing manual updates to event handlers

**Phase 4: Build TournamentOps Layer** (2-3 weeks)
- ✅ Create TournamentOpsService with orchestration methods
- ✅ Extract workflow logic from views into TournamentOps
- ✅ Refactor views to thin controllers (call TournamentOps only)

**Phase 5: User Stats & History** (2-3 weeks)
- ✅ Create UserTournamentStats and UserTournamentHistory models
- ✅ Implement UserStatsService with event handlers
- ✅ Backfill historical data from existing registrations
- ✅ Add user stats dashboard

**Phase 6: Leaderboard Integration** (2-3 weeks)
- ✅ Create LeaderboardAdapter
- ✅ Add tournament completion → ranking update event handler
- ✅ Implement ELO rating calculation
- ✅ Add global leaderboards page

---

## 4. Future-Proofing Recommendations

### 4.1 API-First Development

**Recommendation**: Build REST API endpoints for all TournamentOps workflows.

**Benefits**:
- ✅ Mobile app can use same backend
- ✅ Third-party integrations (Discord bots, tournament platforms)
- ✅ Easier to migrate to microservices later
- ✅ OpenAPI documentation for frontend teams

**Example API Design**:
```
POST   /api/v1/tournaments/{id}/registrations/          # Create registration
GET    /api/v1/tournaments/{id}/registrations/{uuid}/  # Get draft
PUT    /api/v1/tournaments/{id}/registrations/{uuid}/  # Update draft
POST   /api/v1/tournaments/{id}/registrations/{uuid}/submit/  # Submit
DELETE /api/v1/tournaments/{id}/registrations/{uuid}/  # Delete draft

POST   /api/v1/registrations/{id}/payments/            # Submit payment
GET    /api/v1/registrations/{id}/status/              # Check status

POST   /api/v1/tournaments/{id}/finalize/              # Determine winner
POST   /api/v1/tournaments/{id}/certificates/generate/ # Bulk certificates
POST   /api/v1/tournaments/{id}/payouts/process/       # Process prizes
```

---

### 4.2 Configuration Over Code

**Recommendation**: Move hardcoded logic to database configuration.

**Examples**:

1. **Game Identity Fields** (replace 7 if-else checks):
```python
GamePlayerIdentityConfig.objects.create(
    game_id=valorant.id,
    field_name='riot_id',
    display_label='Riot ID',
    validation_pattern=r'^[\w]+#[\w]+$',
    help_text='Format: Username#TAG',
    is_required=True,
    is_immutable=True  # Lock after verification
)
```

2. **Eligibility Rules** (replace hardcoded age/rank checks):
```python
EligibilityRule.objects.create(
    tournament=tournament,
    rule_type='MIN_RANK',
    config={'min_rank': 'Diamond'},
    error_message='Minimum rank: Diamond'
)
```

3. **Prize Distribution** (already JSONB, good pattern):
```python
tournament.prize_distribution = {
    "1st": "500.00",
    "2nd": "300.00",
    "3rd": "200.00"
}
```

---

### 4.3 Observability & Monitoring

**Recommendation**: Add comprehensive logging and metrics.

**Event Tracking**:
```python
# Log all domain events
class DomainEvent(models.Model):
    event_type = models.CharField(max_length=100)
    aggregate_id = models.IntegerField()  # Tournament ID, Match ID, etc.
    payload = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    retry_count = models.IntegerField(default=0)
```

**Metrics to Track**:
- Registration completion rate (started / submitted)
- Payment verification latency (submission → approval time)
- Match result dispute rate (disputed / total matches)
- Tournament completion time (registration open → completed)
- Event handler failure rate (failed / total events)

**Alerting**:
- Alert if >5% of payments are rejected
- Alert if match completion takes >24 hours
- Alert if event handler fails >3 times (retry exhausted)

---

## 5. Key Takeaways

### 5.1 Smart Registration (Priority 1)

**Must-Have Features**:
1. ✅ **Field Locking**: Lock verified email/phone/game IDs (prevent fraud)
2. ✅ **Unique Registration Numbers**: Trackable across support, certificates, payouts
3. ✅ **Draft Persistence**: Database-backed drafts (cross-device resume)
4. ✅ **Configuration-Driven**: Game configs drive field rendering/validation
5. ✅ **Eligibility Engine**: Rules-based system (no hardcoded checks)

**Implementation Effort**: ~6-8 weeks (Phases 1-2)

---

### 5.2 Automation via Events (Priority 2)

**Must-Have Handlers**:
1. ✅ `MatchCompletedEvent` → Update team stats, match history, rankings
2. ✅ `TournamentCompletedEvent` → Award prizes, generate certificates, update leaderboards
3. ✅ `PaymentVerifiedEvent` → Confirm registration, send notification
4. ✅ `RegistrationCompletedEvent` → Update user tournament count

**Implementation Effort**: ~3-4 weeks (Phase 3)

---

### 5.3 Clean Architecture (Priority 3)

**Must-Have Layers**:
1. ✅ **TournamentOps**: Workflow orchestration (high-level)
2. ✅ **Domain Services**: Business logic (single responsibility)
3. ✅ **Adapters**: Cross-app integration (decoupled)
4. ✅ **DTOs**: Data transfer objects (no model leakage)

**Implementation Effort**: ~4-5 weeks (Phase 2, 4)

---

### 5.4 Stats & History (Priority 4)

**Must-Have Models**:
1. ✅ `UserTournamentStats` (global user stats)
2. ✅ `UserTournamentHistory` (per-tournament records)
3. ✅ `TeamMatchHistory` (auto-populated on match completion)

**Implementation Effort**: ~2-3 weeks (Phase 5)

---

## 6. Summary Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                    SMART REGISTRATION                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │ Config-     │  │  Field      │  │  Unique     │           │
│  │ Driven      │  │  Locking    │  │  Reg #      │           │
│  │ Fields      │  │             │  │             │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
│  ┌─────────────┐  ┌─────────────┐                            │
│  │ Eligibility │  │   Draft     │                            │
│  │ Rules       │  │ Persistence │                            │
│  └─────────────┘  └─────────────┘                            │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────────────────────────┐
│              EVENT-DRIVEN AUTOMATION                          │
│  MatchCompleted → Stats, History, Rankings, Rewards          │
│  TournamentCompleted → Prizes, Certificates, Leaderboards    │
│  PaymentVerified → Confirm Registration, Notify User         │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────────────────────────┐
│                  CLEAN ARCHITECTURE                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ TournamentOps (Orchestration)                           │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Domain     │  │  Adapters   │  │   Events    │         │
│  │  Services   │  │  (Cross-App)│  │   (Audit)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└───────────────────────────────────────────────────────────────┘
```

---

**End of Part 6: Smart Registration & Architecture Recommendations**

**Audit Series Complete** (Parts 1-6)
