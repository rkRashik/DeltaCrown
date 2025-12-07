# TournamentOps System Design (Draft)

## 1. Vision & Scope

### Problem Statement

The current `apps.tournaments` implementation, while comprehensive with 23 models and 37+ services, suffers from fundamental architectural problems that prevent it from scaling across multiple games and operating efficiently:

**Critical Issues Identified in Audits:**

1. **Dual Game Architecture Confusion**
   - Legacy `tournaments.models.tournament.Game` exists alongside modern `apps.games.Game`
   - Hardcoded game slug checks scattered across `registration_wizard.py`, `leaderboard.py`, templates
   - Game-specific logic embedded directly in tournament code (e.g., Valorant rank requirements, CS2 Steam ID validation)
   - Impossible to add new games without modifying tournament core code

2. **Tight Cross-App Coupling**
   - 50+ direct imports of `Team` and `TeamMembership` models throughout tournaments app
   - Direct model queries violate domain boundaries
   - Registration uses `team_id = IntegerField` (not ForeignKey) as workaround for loose coupling
   - No service abstraction layer for Teams integration

3. **Broken Integration Points**
   - Ranking system integration incomplete: imports exist but `TeamRankingService` not utilized
   - Inconsistent use of `GameService` - exists but bypassed in favor of direct model access
   - Economy integration excellent (via `economy.services.PaymentService`) but isolated example
   - No event-driven architecture for cross-app coordination

4. **Operational Gaps**
   - No unified dispute resolution workflow
   - Manual match result verification scattered across admin actions
   - Bracket generation/seeding logic embedded in tournament models
   - Certificate generation and reward distribution lack dedicated orchestration
   - No audit trail for operator actions across tournament lifecycle

### What TournamentOps Solves

**TournamentOps** is a dedicated orchestration layer that manages tournament operations from registration through completion, sitting **above** the existing tournaments app and coordinating work across Games, Teams, Users, and Economy apps through well-defined service contracts.

**Core Responsibilities:**

1. **Registration & Eligibility Management**
   - Validate player/team eligibility via `GameService` (rank requirements, identity verification)
   - Coordinate with `TeamService` for roster validation and captain verification
   - Enforce tournament-specific rules (team size, region locks, previous ban checks)
   - Provide unified registration API regardless of tournament format (solo/team/game type)

2. **Scheduling & Match Operations**
   - Generate brackets based on seeding algorithms (configurable by game via `GameTournamentConfig`)
   - Coordinate match scheduling with automated check-in workflows
   - Manage match state transitions (Scheduled → In Progress → Pending Verification → Completed)
   - Handle lobby creation coordination (via external game APIs through `GameService`)

3. **Result Processing & Dispute Resolution**
   - Centralized result submission and verification workflow
   - Dispute ticket system with SLA tracking and escalation
   - Evidence attachment and review workflows for moderators
   - Automated result propagation to standings and rankings after verification

4. **Standings & Ranking Sync**
   - Real-time standings calculation based on tournament scoring rules
   - Sync tournament performance back to global rankings via `TeamRankingService`
   - Leaderboard generation for spectator/dashboard views
   - Historical performance tracking per player/team

5. **Completion & Rewards**
   - Certificate generation with cryptographic verification
   - Prize distribution via `economy.services` (DeltaCrown wallet credits, physical prizes)
   - Achievement/badge unlocking coordination
   - Post-tournament analytics and reporting

6. **Operator Tools & Audit Trail**
   - Comprehensive action logging for all operator interventions
   - Admin override capabilities with justification requirements
   - Rollback capabilities for disputed actions
   - Observability into tournament health and progress metrics

### What TournamentOps Will NOT Do

**Out of Scope (remains in existing apps):**

- **Tournament Definition/Configuration**: Stays in `apps.tournaments` (Tournament, TournamentFormat, Prize, Sponsor models)
- **Game Metadata Management**: Stays in `apps.games` (Game, GameRosterConfig, GameTournamentConfig)
- **Team/Player Data Ownership**: Stays in `apps.teams` and `apps.accounts`
- **Wallet/Transaction Management**: Stays in `apps.economy`
- **Content/Marketing**: Tournament descriptions, images, sponsors remain in `apps.tournaments`
- **Spectator Features**: Live match viewing, VOD hosting, commentary integration (handled by `apps.spectator`)
- **External Game API Integration**: Riot API, Steam API calls remain in `apps.games.GameService`

**Principle**: TournamentOps **orchestrates** but does not **own** domain data. It coordinates workflows across apps through service APIs, maintaining only operational state (registrations in-flight, match operations, disputes, audit logs).

---

## 2. Domain Model & Core Concepts

This section defines the **conceptual domain** for TournamentOps. These are logical entities that may map to one or more Django models, but the focus here is on **what** exists and **where** data ownership lives.

### 2.1 Tournament (Operational View)

**What It Represents:**
- The operational lifecycle wrapper around a `tournaments.Tournament` instance
- State machine tracking tournament progression: Draft → Registration Open → Seeding → Live → Completed → Archived
- Operational metadata not relevant to tournament definition (e.g., operator notes, health checks)

**Cross-App Connections:**
- **Source of Truth**: `apps.tournaments.Tournament` (owns config, prizes, sponsors, format)
- **Depends On**: `apps.games.Game` (via `Tournament.game_id`) for game-specific rules
- **Coordinates**: Team/player registration via TournamentOps services

**Data Ownership:**
- `apps.tournaments` owns the Tournament model
- `apps.tournament_ops` may maintain a `TournamentOperationalState` model that references `Tournament` via FK
- Operational state includes: current_phase, operator_lock_status, health_metrics

---

### 2.2 TournamentPhase

**What It Represents:**
- Discrete phases within tournament lifecycle: Registration → Check-In → Bracket Seeding → Group Stage → Playoffs → Finals → Completion
- Phase-specific configuration (e.g., registration window dates, check-in reminder timings)
- Phase transition triggers and validation rules

**Cross-App Connections:**
- **Owned By**: `apps.tournament_ops` (operational concern, not tournament definition)
- **References**: `apps.tournaments.Tournament` for which tournament this phase belongs to
- **Influences**: Match scheduling (can't schedule matches before Bracket Seeding phase completes)

**Data Ownership:**
- `apps.tournament_ops.TournamentPhase` model
- Links to `Tournament` via FK
- Stores: phase_type (enum), start_time, end_time, auto_transition_enabled, completion_criteria

---

### 2.3 RegistrationEntity

**What It Represents:**
- A pending or confirmed participant in a tournament (could be solo player or team)
- Captures registration submission, eligibility check results, confirmation status
- Polymorphic concept: may reference `User` (solo) or `Team` (team tournaments)

**Cross-App Connections:**
- **Owned By**: `apps.tournament_ops` (operational data about registration attempt)
- **References**: 
  - `apps.tournaments.Tournament` (which tournament)
  - `apps.accounts.User` OR `apps.teams.Team` (who is registering)
  - `apps.games.Game` (for game-specific eligibility checks)
- **Validated Via**: 
  - `GameService.check_player_eligibility()` for rank/identity requirements
  - `TeamService.validate_roster()` for team composition rules

**Data Ownership:**
- `apps.tournament_ops.TournamentRegistration` model
- Stores: registration_time, status (pending/approved/rejected), entity_type (solo/team), entity_id (generic FK or separate FKs)
- Links to `EligibilityCheck` results via reverse relation

---

### 2.4 EligibilityCheck

**What It Represents:**
- A validation task run against a `RegistrationEntity` to ensure it meets tournament requirements
- Multiple checks may run: rank requirements, region lock, identity verification, roster size, previous ban status
- Check results stored with evidence for audit and dispute resolution

**Cross-App Connections:**
- **Owned By**: `apps.tournament_ops` (operational workflow)
- **References**: `TournamentRegistration` (which registration attempt)
- **Delegates To**:
  - `apps.games.GameService.verify_player_identity()` for game account validation
  - `apps.games.GameService.check_rank_eligibility()` for rank requirements
  - `apps.teams.TeamService.validate_roster()` for roster rules
  - `apps.moderation` (future) for ban checks

**Data Ownership:**
- `apps.tournament_ops.EligibilityCheckResult` model
- Stores: check_type (enum), result (pass/fail/pending), evidence (JSON), checked_at, checked_by (system/admin)
- Links to `TournamentRegistration` via FK

---

### 2.5 MatchOperation

**What It Represents:**
- The operational lifecycle of a single match in a tournament
- State machine: Scheduled → Check-In Open → Ready → In Progress → Pending Verification → Verified → Completed (or Disputed)
- Coordinator for lobby creation, check-in tracking, result submission, dispute handling

**Cross-App Connections:**
- **Owned By**: `apps.tournament_ops` (operational state)
- **References**: 
  - `apps.tournaments.Match` (owns match definition: participants, round, scheduled_time)
  - `apps.games.Game` (for game-specific lobby creation APIs)
- **Coordinates**:
  - Lobby creation via `GameService.create_tournament_lobby()` (external API call)
  - Check-in reminders via `apps.notifications`
  - Result verification workflow

**Data Ownership:**
- `apps.tournaments.Match` model owns match definition (exists already)
- `apps.tournament_ops.MatchOperationalState` model stores operational metadata
  - Stores: current_state, check_in_status (JSON per team), lobby_id (external), operator_notes
  - Links to `Match` via OneToOneField

---

### 2.6 ScheduleBlock

**What It Represents:**
- A time slot reservation for matches within a tournament
- Prevents overlapping match assignments for teams/players
- Enables automated scheduling algorithms to assign matches to available blocks

**Cross-App Connections:**
- **Owned By**: `apps.tournament_ops` (scheduling concern)
- **References**: `apps.tournaments.Tournament` (which tournament)
- **Influences**: `Match` scheduling (matches assigned to blocks)

**Data Ownership:**
- `apps.tournament_ops.ScheduleBlock` model
- Stores: start_time, end_time, capacity (how many concurrent matches), assigned_match_ids (JSON or M2M)
- May link to `apps.tournaments.Match` via M2M for assigned matches

---

### 2.7 DisputeTicket

**What It Represents:**
- A formal dispute raised about a match result, eligibility decision, or tournament ruling
- Tracks dispute lifecycle: Submitted → Under Review → Evidence Collection → Ruling → Closed
- Links to evidence (screenshots, VODs, chat logs) and moderator review history

**Cross-App Connections:**
- **Owned By**: `apps.tournament_ops` (operational dispute workflow)
- **References**:
  - `apps.tournaments.Match` (if disputing match result)
  - `TournamentRegistration` (if disputing eligibility rejection)
  - `apps.accounts.User` (dispute submitter and assigned moderator)
- **Integrates With**:
  - `apps.moderation` (for moderator assignment and ban enforcement if dispute reveals cheating)
  - `apps.notifications` (for dispute status updates)

**Data Ownership:**
- `apps.tournament_ops.DisputeTicket` model
- Stores: dispute_type (result/eligibility/conduct), status (enum), submitted_at, resolved_at, resolution_note, evidence_urls (JSON)
- Links to `Match` or `TournamentRegistration` via nullable FKs (only one set)

---

### 2.8 ResultSubmission

**What It Represents:**
- A claim about match outcome submitted by a participant or operator
- Multiple submissions may exist for one match (both teams submit, admin overrides)
- Verification workflow determines which submission becomes canonical result

**Cross-App Connections:**
- **Owned By**: `apps.tournament_ops` (result verification workflow)
- **References**:
  - `apps.tournaments.Match` (which match)
  - `apps.accounts.User` (submitter, could be player/captain/admin)
- **Produces**: Verified result propagates to `Match.winner`, `Match.score`, and triggers standings update

**Data Ownership:**
- `apps.tournament_ops.ResultSubmission` model
- Stores: submitted_by (User FK), submission_time, claimed_winner (team/player ID), claimed_score (JSON), evidence_urls (JSON), verification_status (pending/verified/rejected)
- Links to `Match` via FK

---

### 2.9 OpsActionLog

**What It Represents:**
- Audit trail of all operator/admin actions within TournamentOps workflows
- Captures who did what, when, and why (justification required for override actions)
- Enables rollback and accountability

**Cross-App Connections:**
- **Owned By**: `apps.tournament_ops` (audit concern)
- **References**:
  - `apps.accounts.User` (operator who performed action)
  - Polymorphic reference to affected entity (Match, Registration, DisputeTicket, etc.)
- **Read By**: Admin audit dashboards, compliance reports

**Data Ownership:**
- `apps.tournament_ops.OpsActionLog` model
- Stores: action_type (enum), performed_by (User FK), performed_at, affected_entity_type (ContentType), affected_entity_id, justification (text), previous_state (JSON), new_state (JSON)

---

### 2.10 RewardDistribution

**What It Represents:**
- A record of prize/reward allocation for tournament completion
- Tracks distribution status: Pending → Approved → Distributed → Confirmed
- Handles both virtual (DeltaCrown credits) and physical (shipped merchandise) prizes

**Cross-App Connections:**
- **Owned By**: `apps.tournament_ops` (distribution workflow)
- **References**:
  - `apps.tournaments.Tournament` (source of prize definitions)
  - `apps.tournaments.Prize` (which prize tier)
  - `apps.accounts.User` or `apps.teams.Team` (recipient)
- **Delegates To**:
  - `apps.economy.services.credit()` for wallet credits
  - External fulfillment API for physical prizes

**Data Ownership:**
- `apps.tournament_ops.RewardDistribution` model
- Stores: recipient_type (user/team), recipient_id, prize_type (currency/physical/badge), prize_value (JSON), distribution_status (enum), distributed_at, confirmation_code
- Links to `Tournament` and `Prize` via FKs

---

### 2.11 CertificateRecord

**What It Represents:**
- A cryptographically-signed certificate of participation/achievement for tournament completion
- Stores certificate metadata and verification hash for authenticity
- Enables public verification of tournament results

**Cross-App Connections:**
- **Owned By**: `apps.tournament_ops` (certificate generation workflow)
- **References**:
  - `apps.tournaments.Tournament` (which tournament)
  - `apps.accounts.User` or `apps.teams.Team` (certificate recipient)
- **Read By**: 
  - User profile pages (display certificates)
  - Public verification API (validate certificate authenticity)

**Data Ownership:**
- `apps.tournament_ops.CertificateRecord` model
- Stores: recipient_type (user/team), recipient_id, tournament_id (FK), achievement_type (participation/winner/finalist), issued_at, verification_hash (cryptographic signature), certificate_url (PDF/image S3 link)

---

## 3. Service Layer & Cross-App APIs

This section defines the **service contracts** that TournamentOps exposes and consumes. Services are the ONLY permitted cross-app integration mechanism (no direct model imports).

### 3.1 Services Exposed by TournamentOps

These services provide the public API for other apps and the tournament management UI to interact with TournamentOps workflows.

---

#### 3.1.1 `RegistrationService`

**Purpose**: Manage tournament registration lifecycle from submission through approval.

**Key Methods:**

```python
class RegistrationService:
    @staticmethod
    def submit_registration(
        tournament_id: int,
        entity_type: str,  # "solo" or "team"
        entity_id: int,    # User.id or Team.id
        submitted_by_user_id: int
    ) -> RegistrationResult:
        """
        Submit a registration and trigger eligibility checks.
        
        Returns:
            RegistrationResult with status (pending/approved/rejected) 
            and list of eligibility check results
        """
    
    @staticmethod
    def check_eligibility(registration_id: int) -> List[EligibilityCheckResult]:
        """
        Run all eligibility checks for a registration.
        Delegates to GameService, TeamService, ModerationService.
        
        Returns:
            List of check results (pass/fail with evidence)
        """
    
    @staticmethod
    def approve_registration(registration_id: int, approved_by_user_id: int) -> bool:
        """
        Manually approve a registration (admin override).
        Logs action in OpsActionLog.
        """
    
    @staticmethod
    def reject_registration(
        registration_id: int, 
        reason: str, 
        rejected_by_user_id: int
    ) -> bool:
        """
        Reject a registration with justification.
        Triggers notification to applicant.
        """
    
    @staticmethod
    def get_tournament_registrations(
        tournament_id: int, 
        status_filter: Optional[str] = None
    ) -> List[RegistrationEntity]:
        """
        Retrieve all registrations for a tournament, optionally filtered by status.
        """
```

**Cross-App Dependencies:**
- Calls `GameService.check_player_eligibility(user_id, game_id, rank_requirement)`
- Calls `TeamService.validate_roster(team_id, game_id, roster_rules)`
- Calls `NotificationService.send_registration_status_update(user_id, status)`

---

#### 3.1.2 `MatchOpsService`

**Purpose**: Coordinate match lifecycle operations (scheduling, check-in, lobby creation, state transitions).

**Key Methods:**

```python
class MatchOpsService:
    @staticmethod
    def schedule_match(
        tournament_id: int,
        participants: List[int],  # Team/Player IDs
        scheduled_time: datetime,
        round_info: dict
    ) -> MatchOperation:
        """
        Create a match and assign it to a schedule block.
        Creates MatchOperationalState tracking record.
        """
    
    @staticmethod
    def open_check_in(match_id: int) -> bool:
        """
        Transition match to Check-In Open state.
        Sends check-in notifications to participants.
        """
    
    @staticmethod
    def record_check_in(match_id: int, entity_id: int) -> bool:
        """
        Record that a team/player has checked in for the match.
        Auto-transitions to Ready when all participants checked in.
        """
    
    @staticmethod
    def create_lobby(match_id: int) -> LobbyCreationResult:
        """
        Delegate to GameService to create external game lobby.
        Stores lobby_id in MatchOperationalState.
        
        Returns:
            LobbyCreationResult with lobby_id, join_code, and instructions
        """
    
    @staticmethod
    def start_match(match_id: int) -> bool:
        """
        Transition match to In Progress state.
        Triggers match monitoring (if applicable).
        """
    
    @staticmethod
    def complete_match(match_id: int, final_state: dict) -> bool:
        """
        Transition match to Pending Verification state.
        Awaits result submission from participants.
        """
```

**Cross-App Dependencies:**
- Calls `GameService.create_tournament_lobby(game_id, participants, match_config)`
- Calls `NotificationService.send_check_in_reminder(entity_id, match_id)`
- Reads `apps.tournaments.Match` for match definition (via service, not direct import)

---

#### 3.1.3 `ResultVerificationService`

**Purpose**: Handle result submission, verification, and dispute workflows.

**Key Methods:**

```python
class ResultVerificationService:
    @staticmethod
    def submit_result(
        match_id: int,
        submitted_by_user_id: int,
        claimed_winner_id: int,
        claimed_score: dict,
        evidence_urls: List[str]
    ) -> ResultSubmission:
        """
        Submit a result claim for a match.
        If both teams submit matching results, auto-verify.
        If mismatch, flag for admin review.
        """
    
    @staticmethod
    def verify_result(
        submission_id: int, 
        verified_by_user_id: int
    ) -> bool:
        """
        Admin verification of a result submission.
        Propagates verified result to Match model and triggers standings update.
        """
    
    @staticmethod
    def auto_verify_consensus(match_id: int) -> Optional[ResultSubmission]:
        """
        Check if multiple submissions agree. If consensus exists, auto-verify.
        Returns verified submission or None if no consensus.
        """
    
    @staticmethod
    def reject_result(
        submission_id: int, 
        reason: str, 
        rejected_by_user_id: int
    ) -> bool:
        """
        Reject a fraudulent result submission.
        May trigger investigation/ban via ModerationService.
        """
```

**Cross-App Dependencies:**
- Writes to `apps.tournaments.Match.winner` and `Match.score` after verification
- Calls `StandingsService.recalculate_standings(tournament_id)` after result verification
- May call `ModerationService.flag_for_investigation(user_id, evidence)` on fraud detection

---

#### 3.1.4 `DisputeService`

**Purpose**: Manage dispute ticket lifecycle and resolution.

**Key Methods:**

```python
class DisputeService:
    @staticmethod
    def create_dispute(
        dispute_type: str,  # "match_result", "eligibility", "conduct"
        related_entity_id: int,  # Match or Registration ID
        submitted_by_user_id: int,
        description: str,
        evidence_urls: List[str]
    ) -> DisputeTicket:
        """
        Create a dispute ticket and assign to moderation queue.
        Triggers SLA timer for review.
        """
    
    @staticmethod
    def assign_moderator(dispute_id: int, moderator_user_id: int) -> bool:
        """
        Assign a dispute to a moderator for review.
        """
    
    @staticmethod
    def request_additional_evidence(
        dispute_id: int, 
        requested_by_user_id: int, 
        evidence_request: str
    ) -> bool:
        """
        Moderator requests more evidence from disputing party.
        Pauses SLA timer until evidence submitted.
        """
    
    @staticmethod
    def resolve_dispute(
        dispute_id: int,
        resolution: str,  # "upheld", "overturned", "dismissed"
        resolution_note: str,
        resolved_by_user_id: int
    ) -> bool:
        """
        Close dispute with final ruling.
        May trigger result reversal or registration status change.
        """
```

**Cross-App Dependencies:**
- May call `ResultVerificationService.verify_result()` or `reject_result()` based on ruling
- May call `RegistrationService.approve_registration()` or `reject_registration()` based on ruling
- Calls `NotificationService.send_dispute_status_update(user_id, status)`
- May call `ModerationService.issue_ban(user_id, reason)` if dispute reveals rule violation

---

#### 3.1.5 `StandingsService`

**Purpose**: Calculate and publish tournament standings/leaderboards in real-time.

**Key Methods:**

```python
class StandingsService:
    @staticmethod
    def recalculate_standings(tournament_id: int) -> List[StandingEntry]:
        """
        Recalculate standings based on all verified match results.
        Uses tournament-specific scoring rules from GameTournamentConfig.
        
        Returns:
            Ordered list of standings (rank, entity_id, points, wins, losses)
        """
    
    @staticmethod
    def get_standings(
        tournament_id: int, 
        as_of_time: Optional[datetime] = None
    ) -> List[StandingEntry]:
        """
        Retrieve current or historical standings.
        """
    
    @staticmethod
    def sync_to_global_rankings(tournament_id: int) -> bool:
        """
        After tournament completion, sync results to global team rankings.
        Delegates to TeamRankingService with tournament performance data.
        """
```

**Cross-App Dependencies:**
- Reads `apps.tournaments.Match` results (via service accessor)
- Reads `apps.games.GameTournamentConfig.scoring_rules` for points calculation
- Calls `TeamRankingService.update_ranking(team_id, tournament_result)` after completion

---

#### 3.1.6 `CompletionService`

**Purpose**: Orchestrate post-tournament completion workflows (certificates, rewards, analytics).

**Key Methods:**

```python
class CompletionService:
    @staticmethod
    def finalize_tournament(tournament_id: int) -> bool:
        """
        Mark tournament as completed, freeze standings, trigger reward distribution.
        """
    
    @staticmethod
    def generate_certificates(tournament_id: int) -> List[CertificateRecord]:
        """
        Generate cryptographically-signed certificates for all participants.
        Stores certificate URLs in CertificateRecord.
        """
    
    @staticmethod
    def distribute_rewards(tournament_id: int) -> List[RewardDistribution]:
        """
        Distribute prizes to winners based on final standings.
        Delegates to EconomyService for wallet credits.
        Creates RewardDistribution records for tracking.
        """
    
    @staticmethod
    def verify_certificate(certificate_hash: str) -> Optional[CertificateRecord]:
        """
        Public API to verify certificate authenticity.
        Returns certificate details if hash matches, None if invalid.
        """
```

**Cross-App Dependencies:**
- Calls `economy.services.credit(user_id, amount, reason)` for prize distribution
- Calls `StandingsService.sync_to_global_rankings(tournament_id)` during finalization
- May call external PDF generation service for certificate PDFs

---

### 3.2 Services Consumed by TournamentOps

These are external services that TournamentOps depends on from other apps. TournamentOps MUST use these service APIs (never direct model imports).

---

#### 3.2.1 `GameService` (from `apps.games`)

**Expected API:**

```python
class GameService:
    @staticmethod
    def get_game_config(game_id: int) -> GameConfig:
        """
        Retrieve game configuration (roster rules, tournament config, identity config).
        
        Returns:
            GameConfig with roster_config, tournament_config, player_identity_config
        """
    
    @staticmethod
    def check_player_eligibility(
        user_id: int, 
        game_id: int, 
        rank_requirement: Optional[str] = None
    ) -> EligibilityResult:
        """
        Verify player meets rank requirements for game.
        May call external APIs (Riot API, Steam API) to check current rank.
        
        Returns:
            EligibilityResult with pass/fail and evidence (current rank, account link status)
        """
    
    @staticmethod
    def verify_player_identity(user_id: int, game_id: int) -> IdentityVerificationResult:
        """
        Verify user has linked and verified their game account (Riot ID, Steam ID, etc).
        
        Returns:
            IdentityVerificationResult with verified status and linked account info
        """
    
    @staticmethod
    def create_tournament_lobby(
        game_id: int, 
        participants: List[int], 
        match_config: dict
    ) -> LobbyCreationResult:
        """
        Create a tournament lobby via external game API.
        
        Returns:
            LobbyCreationResult with lobby_id, join_code, lobby_url
        """
    
    @staticmethod
    def get_tournament_scoring_rules(game_id: int) -> dict:
        """
        Retrieve scoring rules for tournament standings calculation.
        From GameTournamentConfig.scoring_rules.
        
        Returns:
            dict with points_per_win, points_per_loss, tiebreaker_rules, etc.
        """
```

**Usage in TournamentOps:**
- `RegistrationService.check_eligibility()` → calls `check_player_eligibility()` and `verify_player_identity()`
- `MatchOpsService.create_lobby()` → calls `create_tournament_lobby()`
- `StandingsService.recalculate_standings()` → calls `get_tournament_scoring_rules()`

---

#### 3.2.2 `TeamService` (from `apps.teams`)

**Expected API:**

```python
class TeamService:
    @staticmethod
    def get_team_roster(team_id: int) -> TeamRoster:
        """
        Retrieve current team roster with roles (captain, members).
        
        Returns:
            TeamRoster with captain_id, member_ids, game_id
        """
    
    @staticmethod
    def validate_roster(
        team_id: int, 
        game_id: int, 
        roster_rules: dict
    ) -> RosterValidationResult:
        """
        Validate team meets roster requirements (size, role distribution, substitutes).
        
        Args:
            roster_rules: from GameRosterConfig (min_players, max_players, require_substitutes)
        
        Returns:
            RosterValidationResult with pass/fail and validation details
        """
    
    @staticmethod
    def is_team_captain(user_id: int, team_id: int) -> bool:
        """
        Check if user is the captain of the team (for registration authorization).
        """
    
    @staticmethod
    def get_team_game_roster(team_id: int, game_id: int) -> GameSpecificRoster:
        """
        Retrieve game-specific roster (e.g., ValorantTeam roster with Riot IDs).
        
        Returns:
            GameSpecificRoster with player_identities, roles, substitutes
        """
```

**Usage in TournamentOps:**
- `RegistrationService.check_eligibility()` → calls `validate_roster()`
- `RegistrationService.submit_registration()` → calls `is_team_captain()` to authorize submission
- `MatchOpsService.create_lobby()` → calls `get_team_game_roster()` for participant identities

---

#### 3.2.3 `UserService` (from `apps.accounts`)

**Expected API:**

```python
class UserService:
    @staticmethod
    def get_user_profile(user_id: int) -> UserProfile:
        """
        Retrieve user profile with game account links.
        
        Returns:
            UserProfile with riot_id, steam_id, epic_id, region, etc.
        """
    
    @staticmethod
    def is_user_banned(user_id: int) -> BanStatus:
        """
        Check if user is currently banned from tournaments.
        
        Returns:
            BanStatus with is_banned, ban_reason, ban_expiry
        """
    
    @staticmethod
    def get_user_tournament_history(user_id: int) -> List[TournamentParticipation]:
        """
        Retrieve user's previous tournament participations.
        Useful for eligibility checks (e.g., "first-time players only" tournaments).
        """
```

**Usage in TournamentOps:**
- `RegistrationService.check_eligibility()` → calls `is_user_banned()` and `get_user_tournament_history()`
- `ResultVerificationService.submit_result()` → calls `get_user_profile()` to verify submitter identity

---

#### 3.2.4 `EconomyService` (from `apps.economy.services`)

**Existing API (already well-designed):**

```python
# From audit: apps.economy.services already has PaymentService
class PaymentService:
    @staticmethod
    def credit(user_id: int, amount: Decimal, reason: str) -> Transaction:
        """Credit user wallet with DeltaCrown currency."""
    
    @staticmethod
    def debit(user_id: int, amount: Decimal, reason: str) -> Transaction:
        """Debit user wallet."""
    
    @staticmethod
    def transfer(from_user_id: int, to_user_id: int, amount: Decimal, reason: str) -> Transaction:
        """Transfer between wallets."""
```

**Usage in TournamentOps:**
- `RegistrationService.submit_registration()` → may call `debit()` if tournament has entry fee
- `CompletionService.distribute_rewards()` → calls `credit()` for prize distribution

**Additional Needed Methods (may require extending EconomyService):**

```python
class EconomyService:
    @staticmethod
    def reserve_funds(user_id: int, amount: Decimal, reason: str) -> Reservation:
        """
        Reserve funds for pending transaction (e.g., entry fee during registration review).
        Funds locked but not transferred until registration approved.
        """
    
    @staticmethod
    def release_reservation(reservation_id: int) -> bool:
        """
        Release reserved funds if registration rejected.
        """
    
    @staticmethod
    def capture_reservation(reservation_id: int) -> Transaction:
        """
        Convert reservation to actual transaction if registration approved.
        """
```

---

#### 3.2.5 `TeamRankingService` (from `apps.teams`)

**Expected API (currently broken per audit, needs implementation):**

```python
class TeamRankingService:
    @staticmethod
    def update_ranking(
        team_id: int, 
        game_id: int, 
        tournament_result: dict
    ) -> RankingUpdate:
        """
        Update team's global ranking based on tournament performance.
        
        Args:
            tournament_result: dict with placement, points_earned, opponents_faced
        
        Returns:
            RankingUpdate with new_rank, rank_change, rating_change
        """
    
    @staticmethod
    def get_team_ranking(team_id: int, game_id: int) -> Ranking:
        """
        Retrieve team's current ranking for a game.
        
        Returns:
            Ranking with rank, rating, tier, last_updated
        """
```

**Usage in TournamentOps:**
- `StandingsService.sync_to_global_rankings()` → calls `update_ranking()` after tournament completion
- `RegistrationService.check_eligibility()` → calls `get_team_ranking()` for rank-restricted tournaments

---

#### 3.2.6 `NotificationService` (from `apps.notifications`)

**Expected API:**

```python
class NotificationService:
    @staticmethod
    def send_registration_status_update(user_id: int, registration_id: int, status: str):
        """Notify user of registration approval/rejection."""
    
    @staticmethod
    def send_check_in_reminder(entity_id: int, match_id: int, check_in_deadline: datetime):
        """Send check-in reminder to team/player before match."""
    
    @staticmethod
    def send_match_ready_notification(entity_id: int, match_id: int, lobby_info: dict):
        """Notify participants that match lobby is ready."""
    
    @staticmethod
    def send_dispute_status_update(user_id: int, dispute_id: int, status: str):
        """Notify disputing party of dispute resolution."""
    
    @staticmethod
    def send_reward_distribution_confirmation(user_id: int, reward_id: int, reward_details: dict):
        """Notify winner of prize distribution."""
```

**Usage in TournamentOps:**
- Used throughout all services to keep participants informed of workflow state changes

---

#### 3.2.7 `ModerationService` (from `apps.moderation`)

**Expected API:**

```python
class ModerationService:
    @staticmethod
    def flag_for_investigation(user_id: int, reason: str, evidence: dict) -> Investigation:
        """Flag user for cheating/fraud investigation."""
    
    @staticmethod
    def issue_ban(user_id: int, ban_type: str, duration: timedelta, reason: str) -> Ban:
        """Issue tournament ban to user."""
    
    @staticmethod
    def check_active_bans(user_id: int) -> List[Ban]:
        """Check if user has active bans."""
```

**Usage in TournamentOps:**
- `RegistrationService.check_eligibility()` → calls `check_active_bans()`
- `DisputeService.resolve_dispute()` → may call `issue_ban()` if dispute reveals cheating

---

### 3.3 Integration Principles

**Golden Rules:**

1. **No Direct Model Imports**: TournamentOps NEVER imports `Team`, `Game`, `User`, `DeltaCrownWallet` models directly. All access via service APIs.

2. **Service-Only Communication**: Other apps access TournamentOps workflows via `RegistrationService`, `MatchOpsService`, etc. (not direct model queries).

3. **Event-Driven Architecture** (Future Enhancement): 
   - TournamentOps emits events: `RegistrationApproved`, `MatchCompleted`, `TournamentFinalized`
   - Other apps subscribe to events instead of polling for state changes
   - Example: Economy app listens for `TournamentFinalized` event to trigger reward distribution

4. **Idempotency**: All service methods must be idempotent (safe to retry on failure).

5. **Transaction Boundaries**: Service methods define transaction boundaries. Cross-app workflows use saga pattern for distributed transactions.

---

## 4. Tournament Lifecycle & State Machines

### 4.1 Tournament State Machine

**States:**

```
Draft → RegistrationOpen → RegistrationClosed → Seeding → Live → Completed → Archived
```

**Detailed State Definitions:**

#### State: `Draft`
- **Description**: Tournament created but not published. Configuration in progress.
- **Entry Conditions**: Tournament created by admin via tournament management UI.
- **Allowed Actions**: Edit tournament config, set prizes, configure game rules, delete tournament.
- **Exit Trigger**: Admin publishes tournament → transitions to `RegistrationOpen`.
- **Owning Service**: `TournamentManagementService` (may live in `apps.tournaments`, not TournamentOps).
- **TournamentOps Responsibility**: None (tournament not yet operational).

---

#### State: `RegistrationOpen`
- **Description**: Tournament published, accepting registrations.
- **Entry Conditions**: 
  - Tournament published from `Draft` state.
  - Registration window start time reached (if scheduled).
- **Allowed Actions**: 
  - Players/teams submit registrations via `RegistrationService.submit_registration()`.
  - Admins review pending registrations via `RegistrationService.approve_registration()` / `reject_registration()`.
  - Participants can withdraw registration.
- **Auto-Transitions**:
  - When registration deadline reached → `RegistrationClosed`.
  - If tournament cancelled → `Archived`.
- **Manual Transitions**: Admin closes registration early → `RegistrationClosed`.
- **Owning Service**: `RegistrationService` (TournamentOps).
- **External Notifications**:
  - `NotificationService.send_registration_status_update()` on each approval/rejection.
  - System broadcasts "registration opened" event for dashboards.

---

#### State: `RegistrationClosed`
- **Description**: Registration window closed, preparing for tournament start.
- **Entry Conditions**: Registration deadline reached or admin manually closed.
- **Allowed Actions**:
  - Admins review final registrations, handle late appeals.
  - Seeding algorithm preparation (gather team rankings, calculate seeds).
  - No new registrations accepted (unless admin override).
- **Exit Trigger**: Admin initiates seeding/bracket generation → `Seeding`.
- **Owning Service**: `RegistrationService` transitions out, `MatchOpsService` prepares seeding.
- **External Notifications**: None (internal state).

---

#### State: `Seeding`
- **Description**: Participants being assigned to brackets/groups based on seeding algorithm.
- **Entry Conditions**: Admin initiates bracket generation.
- **Allowed Actions**:
  - System generates brackets via `MatchOpsService.generate_brackets()`.
  - Admin can manually adjust seeds, bracket placement.
  - Matches created and assigned to schedule blocks.
- **Exit Trigger**: Bracket finalized, first match scheduled → `Live`.
- **Owning Service**: `MatchOpsService` (TournamentOps).
- **External Notifications**:
  - `NotificationService` sends bracket announcements to participants.
  - `TeamRankingService.get_team_ranking()` called for seeding inputs.

---

#### State: `Live`
- **Description**: Tournament in progress, matches being played.
- **Entry Conditions**: Brackets finalized, first match ready to start.
- **Allowed Actions**:
  - Matches transition through match state machine (see 4.2).
  - Results submitted, verified, standings updated.
  - Disputes raised and resolved.
  - Admins can pause tournament (emergency situations).
- **Exit Trigger**: All matches completed, final standings calculated → `Completed`.
- **Owning Service**: `MatchOpsService`, `ResultVerificationService`, `DisputeService`, `StandingsService` (all TournamentOps).
- **External Notifications**:
  - Continuous updates to `StandingsService` (real-time leaderboards).
  - `NotificationService` for match reminders, lobby creation, results.

---

#### State: `Completed`
- **Description**: All matches finished, results finalized, awaiting prize distribution.
- **Entry Conditions**: Final match verified, standings locked.
- **Allowed Actions**:
  - Admin reviews final standings, resolves any pending disputes.
  - `CompletionService.generate_certificates()` creates participation certificates.
  - `CompletionService.distribute_rewards()` triggers prize distribution.
  - Late disputes may be filed (grace period).
- **Exit Trigger**: Rewards distributed, certificates issued, grace period expired → `Archived`.
- **Owning Service**: `CompletionService` (TournamentOps).
- **External Notifications**:
  - `EconomyService.credit()` for prize distribution.
  - `TeamRankingService.update_ranking()` for global ranking sync.
  - `NotificationService.send_reward_distribution_confirmation()`.

---

#### State: `Archived`
- **Description**: Tournament finalized, historical record only.
- **Entry Conditions**: Completion workflows finished, tournament closed.
- **Allowed Actions**: Read-only access to results, certificates, replay data.
- **Exit Trigger**: None (terminal state). Could be "unarchived" for corrections (rare).
- **Owning Service**: None (read-only state).
- **External Notifications**: None.

---

### 4.2 Match State Machine

**States:**

```
Scheduled → CheckInOpen → Ready → InProgress → ResultPending → Verified → Completed
                                                                    ↓
                                                                Disputed → Resolved
```

**Detailed State Definitions:**

#### State: `Scheduled`
- **Description**: Match created, scheduled for future time.
- **Entry Conditions**: Bracket generation assigns participants, schedule block allocated.
- **Allowed Actions**: 
  - Participants view scheduled matches in dashboard.
  - Admins can reschedule (move to different time block).
- **Exit Trigger**: Check-in window opens (typically 15-30 min before scheduled time) → `CheckInOpen`.
- **Owning Service**: `MatchOpsService.schedule_match()`.
- **External Notifications**: `NotificationService` sends "upcoming match" reminder 1 hour before check-in.

---

#### State: `CheckInOpen`
- **Description**: Check-in window active, participants must confirm availability.
- **Entry Conditions**: Check-in window start time reached.
- **Allowed Actions**:
  - Participants call `MatchOpsService.record_check_in(match_id, entity_id)`.
  - System tracks which teams/players have checked in.
  - If participant fails to check-in by deadline → forfeit logic triggers.
- **Auto-Transitions**:
  - All participants checked in → `Ready`.
  - Check-in deadline passed with incomplete check-ins → match cancelled or forfeit awarded.
- **Owning Service**: `MatchOpsService.open_check_in()`.
- **External Notifications**: `NotificationService.send_check_in_reminder()` at check-in open time.

---

#### State: `Ready`
- **Description**: All participants checked in, lobby creation imminent.
- **Entry Conditions**: All participants confirmed check-in.
- **Allowed Actions**:
  - System calls `MatchOpsService.create_lobby(match_id)` → delegates to `GameService.create_tournament_lobby()`.
  - Lobby credentials (join code, server info) stored in `MatchOperationalState`.
  - Participants notified of lobby details.
- **Exit Trigger**: Lobby created, participants join → `InProgress`.
- **Owning Service**: `MatchOpsService.create_lobby()`.
- **External Notifications**: `NotificationService.send_match_ready_notification()` with lobby join instructions.

---

#### State: `InProgress`
- **Description**: Match actively being played in external game.
- **Entry Conditions**: Lobby created, participants joined.
- **Allowed Actions**:
  - Match duration timer running (for SLA tracking).
  - Participants play match externally (Riot client, Steam, etc.).
  - System may poll game API for live match status (if available).
- **Exit Trigger**: Match completed (detected via API or manual trigger) → `ResultPending`.
- **Owning Service**: `MatchOpsService.start_match()`.
- **External Notifications**: Live match status may broadcast to `apps.spectator` for viewing.

---

#### State: `ResultPending`
- **Description**: Match finished, awaiting result submission from participants.
- **Entry Conditions**: Match timer expired or game API reports match complete.
- **Allowed Actions**:
  - Participants call `ResultVerificationService.submit_result()` with claimed winner/score.
  - System stores multiple submissions (one per team/player).
  - If submissions agree → auto-verify.
  - If submissions conflict → flag for admin review.
- **Auto-Transitions**:
  - Consensus reached via `ResultVerificationService.auto_verify_consensus()` → `Verified`.
  - Submission deadline passed with no submission → admin contacted.
- **Manual Transitions**: Admin manually verifies result → `Verified`.
- **Owning Service**: `ResultVerificationService.submit_result()`.
- **External Notifications**: `NotificationService` reminds participants to submit results if overdue.

---

#### State: `Verified`
- **Description**: Result confirmed, ready to update standings.
- **Entry Conditions**: Result submission verified (auto or admin).
- **Allowed Actions**:
  - System updates `apps.tournaments.Match.winner` and `Match.score`.
  - `StandingsService.recalculate_standings(tournament_id)` triggered.
  - Dispute grace period begins (typically 15-30 min).
- **Exit Trigger**: Dispute grace period expires → `Completed`.
- **Dispute Override**: Participant files dispute → `Disputed`.
- **Owning Service**: `ResultVerificationService.verify_result()`.
- **External Notifications**: `StandingsService` updates leaderboard, broadcasts to dashboards.

---

#### State: `Disputed`
- **Description**: Result challenged by participant, under investigation.
- **Entry Conditions**: Participant calls `DisputeService.create_dispute()` within grace period.
- **Allowed Actions**:
  - Moderator reviews evidence via `DisputeService.assign_moderator()`.
  - Parties provide additional evidence via `DisputeService.request_additional_evidence()`.
  - Moderator issues ruling via `DisputeService.resolve_dispute()`.
- **Exit Trigger**: Dispute resolved → `Resolved` (may also transition back to `Verified` if dispute dismissed).
- **Owning Service**: `DisputeService`.
- **External Notifications**: `NotificationService.send_dispute_status_update()` to both parties and moderator.

---

#### State: `Resolved`
- **Description**: Dispute adjudicated, final ruling applied.
- **Entry Conditions**: Moderator issues ruling via `DisputeService.resolve_dispute()`.
- **Allowed Actions**:
  - If dispute upheld (result overturned): System updates `Match.winner`, recalculates standings.
  - If dispute dismissed: Original result stands.
  - Ruling logged in `OpsActionLog`.
- **Exit Trigger**: Ruling applied → `Completed`.
- **Owning Service**: `DisputeService.resolve_dispute()`.
- **External Notifications**: 
  - `StandingsService.recalculate_standings()` if result changed.
  - `NotificationService` sends final ruling to participants.

---

#### State: `Completed`
- **Description**: Match finalized, result locked.
- **Entry Conditions**: Verified result grace period expired or dispute resolved.
- **Allowed Actions**: Read-only access to match history.
- **Exit Trigger**: None (terminal state for match).
- **Owning Service**: None (passive state).
- **External Notifications**: None.

---

### 4.3 State Transition Ownership Summary

| State Machine | Primary Owner Service | External Services Notified |
|---------------|----------------------|---------------------------|
| **Tournament State** | `RegistrationService`, `MatchOpsService`, `CompletionService` | `NotificationService`, `TeamRankingService`, `EconomyService` |
| **Match State** | `MatchOpsService`, `ResultVerificationService`, `DisputeService` | `GameService`, `NotificationService`, `StandingsService` |

**Key Principles:**
- State transitions are **event-driven**: Services emit events (`RegistrationApproved`, `MatchVerified`, etc.).
- Other apps **subscribe** to events (future enhancement) rather than polling for state changes.
- All state transitions logged in `OpsActionLog` for audit trail.

---

## 5. Major Flows (End-to-End)

### 5.1 Registration & Eligibility Flow

**Scenario**: Team captain registers their team for a Valorant tournament with rank requirements (Immortal+).

**Step-by-Step Technical Flow:**

1. **Registration Submission**
   - Captain navigates to tournament page, clicks "Register Team".
   - Frontend calls `RegistrationService.submit_registration(tournament_id, entity_type="team", entity_id=team.id, submitted_by_user_id=captain.id)`.
   - Service validates:
     - `TeamService.is_team_captain(captain.id, team.id)` → confirms captain authorization.
     - Tournament state is `RegistrationOpen`.
     - Team not already registered for this tournament.
   - Creates `TournamentRegistration` record with status=`pending`.
   - Returns `registration_id` to frontend.

2. **Eligibility Check Orchestration**
   - `RegistrationService.check_eligibility(registration_id)` triggered automatically (async Celery task recommended).
   - Service retrieves tournament requirements from `apps.tournaments.Tournament`:
     - `game_id` (Valorant).
     - `min_rank_requirement` (Immortal).
     - `region_lock` (NA only).
     - `roster_size` (5 players, 1 substitute).

3. **Game-Specific Eligibility Checks**
   - **Check 1: Roster Validation**
     - Calls `TeamService.validate_roster(team_id, game_id, roster_rules={'min_players': 5, 'max_players': 6, 'require_substitutes': True})`.
     - `TeamService` returns roster with Riot IDs for each player.
     - Creates `EligibilityCheckResult` record: `check_type="roster_size"`, `result="pass"`.
   
   - **Check 2: Identity Verification**
     - For each team member:
       - Calls `GameService.verify_player_identity(user_id, game_id=valorant)`.
       - `GameService` checks if `UserProfile.riot_id` is linked and verified.
       - If any player missing Riot ID → creates `EligibilityCheckResult`: `check_type="identity_verification"`, `result="fail"`, `evidence={"missing_riot_id_users": [user_ids]}`.
   
   - **Check 3: Rank Verification**
     - For each team member:
       - Calls `GameService.check_player_eligibility(user_id, game_id, rank_requirement="Immortal+")`.
       - `GameService` calls external Riot API to fetch current rank (may cache for 24h).
       - If any player below Immortal → creates `EligibilityCheckResult`: `check_type="rank_requirement"`, `result="fail"`, `evidence={"below_rank_users": [{"user_id": 123, "current_rank": "Diamond 3"}]}`.
   
   - **Check 4: Region Lock**
     - For each team member:
       - Retrieves `UserProfile.region`.
       - If any player outside NA → creates `EligibilityCheckResult`: `check_type="region_lock"`, `result="fail"`.
   
   - **Check 5: Ban Status**
     - For each team member:
       - Calls `UserService.is_user_banned(user_id)`.
       - If any player has active tournament ban → creates `EligibilityCheckResult`: `check_type="ban_check"`, `result="fail"`.

4. **Registration Decision**
   - If all checks pass:
     - `RegistrationService.approve_registration(registration_id, approved_by_user_id=SYSTEM_USER_ID)`.
     - Updates `TournamentRegistration.status = "approved"`.
     - Calls `NotificationService.send_registration_status_update(captain.id, registration_id, status="approved")`.
   
   - If any check fails:
     - `RegistrationService.reject_registration(registration_id, reason="Eligibility checks failed: [list failed checks]", rejected_by_user_id=SYSTEM_USER_ID)`.
     - Calls `NotificationService.send_registration_status_update(captain.id, registration_id, status="rejected")` with detailed failure reasons.
     - Captain can appeal via support ticket or fix issues (e.g., link Riot ID) and resubmit.

5. **Entry Fee Processing (if applicable)**
   - If tournament has entry fee:
     - During registration submission, calls `EconomyService.reserve_funds(captain.id, amount=entry_fee, reason="Tournament entry fee reservation")`.
     - Funds locked in user wallet (not yet deducted).
   - On approval:
     - Calls `EconomyService.capture_reservation(reservation_id)` → funds transferred to tournament prize pool.
   - On rejection:
     - Calls `EconomyService.release_reservation(reservation_id)` → funds returned to user wallet.

**Solo Tournament Variation:**
- `entity_type="solo"`, `entity_id=user.id`.
- Skips `TeamService` calls, directly validates individual user.
- Same eligibility checks (identity, rank, region, ban) applied to single user.

---

### 5.2 Grouping, Seeding & Bracket Generation Flow

**Scenario**: Admin initiates bracket generation for a 32-team CS2 tournament after registration closes.

**Step-by-Step Technical Flow:**

1. **Transition to Seeding State**
   - Admin clicks "Generate Brackets" in tournament management UI.
   - Frontend calls `MatchOpsService.initiate_seeding(tournament_id)`.
   - Service validates:
     - Tournament state is `RegistrationClosed`.
     - Sufficient registrations approved (meets tournament min/max participant requirements).
   - Updates tournament operational state to `Seeding`.

2. **Retrieve Seeding Configuration**
   - Service retrieves tournament configuration:
     - `apps.tournaments.Tournament.tournament_format` → "single_elimination", "double_elimination", "round_robin", "swiss", etc.
     - `apps.games.GameTournamentConfig.seeding_algorithm` → "rank_based", "random", "manual", "regional_groups".
   - Service retrieves approved registrations:
     - `RegistrationService.get_tournament_registrations(tournament_id, status_filter="approved")`.
     - Returns list of 32 teams.

3. **Seeding Algorithm Execution**

   **Option A: Rank-Based Seeding** (default for competitive tournaments)
   - For each team:
     - Calls `TeamRankingService.get_team_ranking(team_id, game_id)`.
     - Retrieves `ranking.rating` (ELO/MMR score).
   - Sorts teams by rating descending.
   - Assigns seeds 1-32 based on ranking (Seed 1 = highest rated team).
   - Bracket structure follows tournament format (e.g., single elimination: Seed 1 vs Seed 32, Seed 2 vs Seed 31, etc.).

   **Option B: Regional Groups** (for international tournaments)
   - Groups teams by region first (NA, EU, APAC, etc.).
   - Within each region, applies rank-based seeding.
   - Creates initial group stage with regional pools.
   - Top teams from each pool advance to knockout bracket.

   **Option C: Random Seeding** (for casual/community tournaments)
   - Shuffles approved registrations randomly.
   - Assigns seeds 1-N randomly.

   **Option D: Manual Seeding** (admin override)
   - Admin provides custom seed assignments via UI.
   - System validates no duplicate seeds, all teams assigned.

4. **Bracket Structure Creation**
   - Based on tournament format and seeding:
     - **Single Elimination (32 teams)**: 
       - Creates 16 Round 1 matches (Seeds 1v32, 2v31, ..., 16v17).
       - Creates 8 Round 2 match placeholders (winners of R1 matches).
       - Creates 4 Quarterfinal, 2 Semifinal, 1 Final match placeholders.
       - Total: 31 matches.
     
     - **Double Elimination**:
       - Creates winners bracket (same as single elim).
       - Creates losers bracket (losers from winners bracket drop down).
       - Grand Finals (winners bracket champion vs losers bracket champion).
       - Total: ~60 matches for 32 teams.
     
     - **Round Robin (4 groups of 8)**:
       - Divides 32 teams into 4 groups.
       - Within each group: every team plays every other team once (8 teams = 28 matches per group).
       - Total: 112 group stage matches.
       - Creates knockout bracket for top 2 from each group (8 teams → 7 playoff matches).

5. **Match Scheduling**
   - Service calls `MatchOpsService.schedule_matches(tournament_id, match_list)`.
   - For each match:
     - Assigns to `ScheduleBlock` based on:
       - Match round (Round 1 matches all scheduled before Round 2).
       - Team availability (prevent teams from playing overlapping matches).
       - Timezone considerations (if tournament spans regions).
     - Creates `apps.tournaments.Match` record with:
       - `tournament_id`, `round`, `match_number`, `participant1_id`, `participant2_id`, `scheduled_time`.
     - Creates `MatchOperationalState` record linked to `Match`.
     - Sets match state to `Scheduled`.

6. **Bracket Finalization**
   - Admin reviews generated bracket in UI (visual bracket tree).
   - Admin can manually adjust:
     - Swap seeds (e.g., move Team A from Seed 5 to Seed 8).
     - Reschedule matches (move to different time slots).
   - Once satisfied, admin clicks "Finalize Bracket".
   - Service transitions tournament state to `Live`.
   - Calls `NotificationService` to broadcast bracket announcements to all participants.

**Edge Cases Handled:**
- **Odd number of teams**: If 31 teams registered, highest seed gets "bye" (auto-advances to Round 2).
- **Late withdrawals**: If team withdraws after bracket generated, opponent awarded forfeit win, bracket adjusts.
- **Seeding ties**: If two teams have identical ranking, uses tiebreaker rules (recent performance, head-to-head record, or random).

---

### 5.3 Scheduling & Check-In Flow

**Scenario**: Match scheduled for 8:00 PM EST, check-in opens at 7:45 PM, both teams must confirm readiness.

**Step-by-Step Technical Flow:**

1. **Match Scheduled (Initial State)**
   - Match exists in `Scheduled` state with `scheduled_time = 2025-12-07 20:00:00 EST`.
   - `MatchOperationalState` stores: `check_in_window_start = 2025-12-07 19:45:00 EST`.

2. **Check-In Window Opens (Auto-Triggered)**
   - At 7:45 PM EST, Celery scheduled task runs:
     - Queries all matches where `check_in_window_start <= now()` and `state = "Scheduled"`.
     - For each match:
       - Calls `MatchOpsService.open_check_in(match_id)`.
       - Transitions match state to `CheckInOpen`.
       - Calls `NotificationService.send_check_in_reminder(team1_id, match_id, check_in_deadline=7:55 PM)`.
       - Calls `NotificationService.send_check_in_reminder(team2_id, match_id, check_in_deadline=7:55 PM)`.

3. **Team Check-In (User Action)**
   - Team captain receives notification (email, SMS, in-app push).
   - Captain navigates to match page, clicks "Check In".
   - Frontend calls `MatchOpsService.record_check_in(match_id, entity_id=team1.id)`.
   - Service validates:
     - Match state is `CheckInOpen`.
     - `entity_id` is a participant in this match.
     - Team has not already checked in.
   - Updates `MatchOperationalState.check_in_status` JSON:
     - `{"team1_id": {"checked_in": true, "timestamp": "2025-12-07 19:47:00"}, "team2_id": {"checked_in": false}}`.
   - Returns success to frontend (UI shows "Team 1 Checked In ✓").

4. **Both Teams Checked In (Auto-Transition)**
   - When second team checks in:
     - Service detects all participants checked in.
     - Automatically calls `MatchOpsService.create_lobby(match_id)`.
     - Transitions match state to `Ready`.

5. **Lobby Creation (Delegated to GameService)**
   - `MatchOpsService.create_lobby(match_id)`:
     - Retrieves match participants (Team 1, Team 2).
     - Calls `TeamService.get_team_game_roster(team1_id, game_id)` to get player identities (Steam IDs for CS2).
     - Calls `GameService.create_tournament_lobby(game_id, participants=[team1_roster, team2_roster], match_config={map: "de_dust2", best_of: 3})`.
     - `GameService` calls external Steam API to reserve tournament server, returns:
       - `lobby_id = "steam_match_12345"`.
       - `join_code = "connect 192.168.1.100:27015; password deltacrownmatch123"`.
     - Stores lobby details in `MatchOperationalState.lobby_id` and `lobby_credentials` (JSON).
     - Transitions match state to `Ready`.

6. **Match Ready Notification**
   - `NotificationService.send_match_ready_notification(team1_id, match_id, lobby_info={join_code, server_ip})`.
   - `NotificationService.send_match_ready_notification(team2_id, match_id, lobby_info={join_code, server_ip})`.
   - Teams join server, match begins.
   - When first round starts, service calls `MatchOpsService.start_match(match_id)` (may be triggered by game server webhook or manual admin action).
   - Transitions match state to `InProgress`.

**Failure Scenarios:**

- **Partial Check-In (Only Team 1 checks in by deadline)**:
  - At 7:55 PM (check-in deadline), Celery task runs:
    - Queries matches in `CheckInOpen` state past deadline.
    - For `match_id`, checks `check_in_status`: only Team 1 checked in.
    - Calls `MatchOpsService.handle_no_show(match_id, no_show_team_id=team2.id)`.
    - Awards forfeit win to Team 1.
    - Creates `apps.tournaments.Match.winner = team1_id`, `score = "Forfeit"`.
    - Transitions match directly to `Verified` (skips `InProgress`, `ResultPending`).
    - Calls `StandingsService.recalculate_standings(tournament_id)`.

- **No Teams Check In**:
  - Match cancelled (double forfeit).
  - Both teams may receive warnings or penalties (TBD by tournament rules).

- **Timezone Conflicts**:
  - All scheduled times stored in UTC in database.
  - Check-in notifications include local timezone conversion for each user: "Your match is at 8:00 PM EST (5:00 PM PST)".
  - Users in different regions see correct local times in UI.

---

### 5.4 Result Reporting & Dispute Flow

**Scenario**: Match finishes, both teams submit results, but scores conflict. Dispute raised.

**Step-by-Step Technical Flow:**

1. **Match Completion**
   - Match in `InProgress` state.
   - Game completes externally (e.g., CS2 best-of-3 finishes with Team A winning 2-1).
   - Options for result capture:
     - **Option A (Automated)**: Game server webhook calls TournamentOps API with final score → auto-creates verified result.
     - **Option B (Manual)**: Admin or players manually submit results.
   - Assuming manual submission (more common initially):
     - Service calls `MatchOpsService.complete_match(match_id, final_state={})`.
     - Transitions match state to `ResultPending`.

2. **Result Submission by Team A**
   - Team A captain navigates to match page, clicks "Submit Result".
   - Frontend form: "Winner: Team A", "Score: 2-1 (16-14, 10-16, 16-12)", optionally uploads screenshots.
   - Frontend calls `ResultVerificationService.submit_result(match_id, submitted_by_user_id=captainA.id, claimed_winner_id=teamA.id, claimed_score={"maps": [{"map": "de_dust2", "score": "16-14"}, ...]}, evidence_urls=[screenshot_url])`.
   - Service creates `ResultSubmission` record:
     - `submission_id = 1`.
     - `submitted_by = captainA.id`.
     - `claimed_winner = teamA.id`.
     - `claimed_score = {"teamA": 2, "teamB": 1, "maps": [...]}`.
     - `verification_status = "pending"`.
   - Returns success to frontend.

3. **Result Submission by Team B (Conflicting)**
   - Team B captain submits: "Winner: Team B", "Score: 2-1 (14-16, 16-10, 16-14)".
   - Service creates second `ResultSubmission` record:
     - `submission_id = 2`.
     - `claimed_winner = teamB.id`.
     - `claimed_score = {"teamA": 1, "teamB": 2, "maps": [...]}`.

4. **Consensus Check (Auto-Verification Attempt)**
   - Service calls `ResultVerificationService.auto_verify_consensus(match_id)`.
   - Retrieves all submissions for `match_id`: finds 2 submissions with conflicting winners.
   - No consensus → flags for manual review.
   - Sends notification to tournament admins: "Match #123 requires manual verification (conflicting results)".

5. **Admin Manual Verification**
   - Admin navigates to disputed matches queue in admin dashboard.
   - Reviews both submissions, evidence screenshots.
   - Determines Team A's submission is correct (video evidence confirms 2-1 win for Team A).
   - Admin calls `ResultVerificationService.verify_result(submission_id=1, verified_by_user_id=admin.id)`.
   - Service:
     - Updates `ResultSubmission[1].verification_status = "verified"`.
     - Updates `ResultSubmission[2].verification_status = "rejected"`.
     - Writes to `apps.tournaments.Match`:
       - `winner = teamA.id`.
       - `score = {"teamA": 2, "teamB": 1, "maps": [...]}`.
     - Transitions match state to `Verified`.
     - Logs action in `OpsActionLog`: `action_type="result_verified_manually"`, `performed_by=admin.id`, `justification="Video evidence confirms Team A win"`.
     - Calls `StandingsService.recalculate_standings(tournament_id)`.

6. **Dispute Grace Period**
   - Match enters `Verified` state with 15-minute grace period before finalizing to `Completed`.
   - Team B (losing team) receives notification: "Match result: Team A won 2-1. Dispute deadline: 8:45 PM EST."

7. **Dispute Raised by Team B**
   - Team B captain believes result is incorrect, clicks "Dispute Result" at 8:40 PM.
   - Frontend form: "Dispute reason: Team A disconnected in final round, we should have won", uploads video evidence.
   - Frontend calls `DisputeService.create_dispute(dispute_type="match_result", related_entity_id=match_id, submitted_by_user_id=captainB.id, description="...", evidence_urls=[video_url])`.
   - Service creates `DisputeTicket` record:
     - `dispute_id = 42`.
     - `dispute_type = "match_result"`.
     - `status = "submitted"`.
     - `submitted_at = 2025-12-07 20:40:00`.
     - `related_match_id = match_id`.
   - Transitions match state from `Verified` to `Disputed`.
   - Calls `NotificationService.send_dispute_status_update(captainB.id, dispute_id=42, status="submitted")`.
   - Assigns dispute to moderation queue.

8. **Dispute Assignment to Moderator**
   - Moderator receives notification, claims dispute.
   - Moderator calls `DisputeService.assign_moderator(dispute_id=42, moderator_user_id=mod.id)`.
   - Updates `DisputeTicket.status = "under_review"`, `assigned_moderator = mod.id`.

9. **Evidence Review**
   - Moderator reviews:
     - Original result submissions from both teams.
     - Team A's screenshots.
     - Team B's dispute video evidence.
   - Moderator determines Team B's claim is invalid (disconnect occurred after round was already lost).
   - Moderator calls `DisputeService.resolve_dispute(dispute_id=42, resolution="dismissed", resolution_note="Evidence shows disconnect occurred after final round outcome determined, original result stands", resolved_by_user_id=mod.id)`.

10. **Dispute Resolution Applied**
    - Service updates `DisputeTicket.status = "closed"`, `resolution = "dismissed"`.
    - Match state transitions from `Disputed` to `Resolved`, then immediately to `Completed`.
    - Original result (Team A win) remains unchanged.
    - Logs in `OpsActionLog`: `action_type="dispute_resolved"`, `resolution="dismissed"`.
    - Calls `NotificationService.send_dispute_status_update(captainB.id, dispute_id=42, status="dismissed")` with moderator's resolution note.

**Alternative Outcome: Dispute Upheld**
- If moderator determines Team B's evidence proves Team A cheated:
  - Resolution: `resolution="upheld"`, `resolution_note="Team A used unauthorized software, result overturned"`.
  - Service calls `ResultVerificationService.verify_result(submission_id=2, verified_by_user_id=mod.id)` to apply Team B's submission.
  - Updates `Match.winner = teamB.id`.
  - Calls `StandingsService.recalculate_standings(tournament_id)` to reflect corrected result.
  - May call `ModerationService.issue_ban(team_a_captain.id, ban_type="tournament_ban", duration=timedelta(days=90), reason="Cheating in tournament match")`.

---

### 5.5 Standings & Ranking Sync Flow

**Scenario**: Real-time standings updates as matches complete, final rankings synced to global team rankings after tournament ends.

**Step-by-Step Technical Flow:**

1. **Match Result Verified (Trigger)**
   - When `ResultVerificationService.verify_result()` completes:
     - Publishes event: `MatchResultVerified(match_id, tournament_id, winner_id, loser_id, score)`.
     - Event listener (Celery task or signal handler) calls `StandingsService.recalculate_standings(tournament_id)`.

2. **Standings Recalculation**
   - `StandingsService.recalculate_standings(tournament_id)`:
     - Retrieves tournament configuration:
       - `apps.games.GameTournamentConfig.scoring_rules` for the tournament's game.
       - Example scoring rules: `{"points_per_win": 3, "points_per_loss": 0, "points_per_draw": 1, "tiebreaker": ["head_to_head", "round_diff", "total_rounds_won"]}`.
     - Queries all verified matches for `tournament_id`:
       - Filters: `Match.tournament_id = tournament_id AND Match.winner IS NOT NULL`.
     - For each participant (team/player):
       - Calculates:
         - `wins` = count of matches where `Match.winner = participant_id`.
         - `losses` = count of matches where participant was loser.
         - `points` = (wins * points_per_win) + (losses * points_per_loss).
         - `round_diff` = sum of (rounds won - rounds lost) across all matches.
       - Creates `StandingEntry`:
         - `tournament_id`, `participant_id`, `rank` (TBD), `points`, `wins`, `losses`, `round_diff`.
     - Sorts participants by:
       - Primary: `points` descending.
       - Tiebreaker 1: `head_to_head` (if two teams tied, who won when they played each other).
       - Tiebreaker 2: `round_diff` descending.
       - Tiebreaker 3: `total_rounds_won` descending.
     - Assigns `rank` 1-N based on sorted order.
     - Stores standings in cache (Redis) and database table `TournamentStanding`:
       - `tournament_id`, `participant_id`, `rank`, `points`, `wins`, `losses`, `updated_at`.

3. **Real-Time Leaderboard Update**
   - After standings recalculated:
     - Publishes event: `StandingsUpdated(tournament_id, standings_snapshot)`.
     - Frontend websocket listeners receive event, update leaderboard UI in real-time.
     - `apps.dashboard` and `apps.spectator` display updated standings without page refresh.

4. **Tournament Completion (Final Standings Lock)**
   - When tournament transitions to `Completed` state:
     - `CompletionService.finalize_tournament(tournament_id)`:
       - Calls `StandingsService.recalculate_standings(tournament_id)` one final time.
       - Locks standings (no further changes allowed):
         - Sets `TournamentStanding.locked = True`.
       - Determines prize distribution based on final ranks:
         - Rank 1 → Prize tier 1 (e.g., $1000 + Gold badge).
         - Rank 2 → Prize tier 2 (e.g., $500 + Silver badge).
         - Rank 3 → Prize tier 3 (e.g., $250 + Bronze badge).

5. **Global Ranking Sync**
   - `CompletionService.finalize_tournament(tournament_id)` calls:
     - `StandingsService.sync_to_global_rankings(tournament_id)`.
   - For each participant in final standings:
     - Prepares `tournament_result` payload:
       - `placement` (rank in tournament).
       - `points_earned` (total tournament points).
       - `opponents_faced` (list of opponent IDs with their ranks).
       - `tournament_tier` (e.g., "premier", "regional", "community" - affects rating multiplier).
     - Calls `TeamRankingService.update_ranking(team_id, game_id, tournament_result)`.
   - `TeamRankingService` (in `apps.teams`):
     - Retrieves team's current global ranking:
       - `TeamGameRanking.objects.get(team_id=team_id, game_id=game_id)`.
       - Current `rating = 1850` (ELO-like system).
     - Applies ranking algorithm (e.g., ELO update):
       - `expected_performance = calculate_expected(team_rating, opponents_ratings)`.
       - `actual_performance = placement / total_teams`.
       - `rating_change = K_factor * (actual_performance - expected_performance)`.
       - Example: Team placed 1st out of 32 teams, beat teams rated 1800-1900.
         - `new_rating = 1850 + 25 = 1875`.
     - Updates `TeamGameRanking.rating = 1875`, `rank` (recalculated across all teams).
     - Stores tournament participation record in `TeamTournamentHistory`:
       - `team_id`, `tournament_id`, `placement`, `points_earned`, `rating_before`, `rating_after`, `completed_at`.
     - Returns `RankingUpdate(new_rank=12, rank_change=+3, rating_change=+25)`.

6. **Ranking Update Notification**
   - After global ranking sync completes:
     - Calls `NotificationService` to notify team members:
       - "Your team's global ranking updated: #15 → #12 (+3) after Tournament X. New rating: 1875."
     - Updates team profile page with new ranking badge.

**Caching & Performance:**
- Standings cached in Redis with TTL = 5 minutes during `Live` state.
- Real-time updates invalidate cache, trigger recalculation.
- Read-heavy endpoints (leaderboard API) serve from cache.
- Final locked standings persisted to database for historical queries.

---

### 5.6 Completion: Certificates & Rewards Flow

**Scenario**: Tournament finishes, top 3 teams receive prizes (DeltaCrown credits + physical trophies), all participants receive certificates.

**Step-by-Step Technical Flow:**

1. **Tournament Finalization Trigger**
   - After final match verified, admin clicks "Finalize Tournament" in admin UI.
   - Frontend calls `CompletionService.finalize_tournament(tournament_id)`.
   - Service validates:
     - All matches in `Completed` state (no pending disputes).
     - Standings locked (final rankings determined).
   - Transitions tournament state to `Completed`.

2. **Certificate Generation**
   - `CompletionService.generate_certificates(tournament_id)`:
     - Retrieves all approved registrations:
       - `RegistrationService.get_tournament_registrations(tournament_id, status_filter="approved")`.
     - For each participant (32 teams):
       - Determines achievement level:
         - Rank 1 → `achievement_type="champion"`.
         - Rank 2-3 → `achievement_type="finalist"`.
         - Rank 4-32 → `achievement_type="participant"`.
       - Generates certificate data:
         - `recipient_name` (team name or player name).
         - `tournament_name`, `game`, `completion_date`, `placement`.
         - `verification_hash` = `sha256(recipient_id + tournament_id + placement + secret_salt)`.
       - Calls external certificate generation service (PDF template rendering):
         - API: `POST /api/certificates/generate` with certificate data.
         - Service returns PDF URL: `https://cdn.deltacrown.com/certificates/tournament_123_team_456.pdf`.
       - Creates `CertificateRecord`:
         - `recipient_type="team"`, `recipient_id=team.id`, `tournament_id`, `achievement_type`, `issued_at=now()`, `verification_hash`, `certificate_url`.
       - Stores record in database.
     - Returns list of generated certificates (32 records).

3. **Certificate Delivery**
   - For each certificate:
     - Calls `NotificationService` to email certificate to team captain:
       - Subject: "Your DeltaCrown Tournament Certificate".
       - Body: "Congratulations on completing Tournament X! Download your certificate: [PDF link]. Verify authenticity: [verification URL]."
     - Certificate also appears in user profile:
       - `apps.user_profile` displays "Achievements" section with tournament certificates.

4. **Reward Distribution (Prize Tiers)**
   - `CompletionService.distribute_rewards(tournament_id)`:
     - Retrieves tournament prize configuration:
       - `apps.tournaments.Prize.objects.filter(tournament_id=tournament_id)`.
       - Example prizes:
         - Rank 1: 10,000 DC credits + physical trophy.
         - Rank 2: 5,000 DC credits + physical medal.
         - Rank 3: 2,500 DC credits + physical medal.
     - Retrieves final standings:
       - `StandingsService.get_standings(tournament_id)`.
     - For each prize tier:
       - **Rank 1 (Champion)**:
         - Recipient: Team A (team_id=123).
         - Virtual prize (DC credits):
           - Determines distribution method (team prize → split among members or captain receives full amount, TBD by tournament rules).
           - Assuming split among 5 team members: 10,000 / 5 = 2,000 DC per player.
           - For each team member:
             - Calls `EconomyService.credit(user_id, amount=2000, reason="Tournament X - 1st Place Prize")`.
             - Creates `DeltaCrownTransaction` record (handled by EconomyService).
         - Physical prize (trophy):
           - Creates `RewardDistribution` record:
             - `recipient_type="team"`, `recipient_id=123`, `prize_type="physical"`, `prize_value={"item": "trophy", "shipping_address": team_captain.address}`, `distribution_status="pending_fulfillment"`.
           - Sends order to external fulfillment API (or queues for manual processing):
             - `POST /api/fulfillment/orders` with recipient address.
           - Fulfillment service ships trophy, updates `distribution_status="shipped"` via webhook.
       
       - **Rank 2-3**: Similar process with different prize amounts.
   
5. **Reward Confirmation**
   - For virtual prizes (DC credits):
     - `EconomyService.credit()` returns `Transaction` object.
     - `CompletionService` creates `RewardDistribution` record:
       - `prize_type="currency"`, `distribution_status="distributed"`, `distributed_at=now()`, `confirmation_code=transaction.id`.
     - Calls `NotificationService.send_reward_distribution_confirmation(user_id, reward_id, reward_details={"amount": 2000, "type": "DeltaCrown Credits"})`.
   
   - For physical prizes:
     - `RewardDistribution` record remains in `pending_fulfillment` or `shipped` state.
     - Team captain receives shipping notification when order ships.
     - Once delivered, recipient confirms delivery via UI → updates `distribution_status="confirmed"`.

6. **Global Ranking Sync (Cross-App Integration)**
   - After rewards distributed:
     - Calls `StandingsService.sync_to_global_rankings(tournament_id)` (as described in 5.5).
     - Global team rankings updated, team profiles show new ranks.

7. **Analytics & Reporting**
   - `CompletionService` generates post-tournament report:
     - Total participants, total matches played, average match duration.
     - Dispute rate (% of matches disputed).
     - Payout summary (total prizes distributed).
     - Stores report in `TournamentCompletionReport` model (TBD).
   - Report accessible to tournament organizers and admins for retrospective analysis.

**Edge Cases:**
- **Unclaimed Prizes**: If winner doesn't claim prize within 30 days, prize may be forfeited or donated (per tournament rules).
- **Tax Reporting**: For large prizes (>$600), may require tax forms (W-9) - out of scope for TournamentOps, handled by finance team.
- **Prize Disputes**: If participant disputes prize amount, handled via support tickets (not dispute system, as tournament already completed).

---

## 6. Phase Plan (T1–T6)

This section provides a **Copilot-friendly implementation roadmap** for building TournamentOps incrementally across 6 phases. Each phase is designed to deliver vertical slices of functionality that can be tested and deployed independently.

### Design Principles for Phased Rollout

1. **Vertical Slice Delivery**: Each phase delivers end-to-end functionality (models + services + APIs + tests).
2. **Backward Compatibility**: Existing `apps.tournaments` remains functional; TournamentOps layers on top.
3. **Service-First Integration**: Cross-app communication via services only (no direct model imports).
4. **Test Coverage Requirement**: Each phase must include unit tests (90%+ coverage) and integration tests.
5. **Feature Flags**: New TournamentOps features gated by feature flags for gradual rollout.

---

### T1 – Registration & Eligibility Engine

**Goal**: Build the registration workflow with comprehensive eligibility checking.

**Deliverables:**

1. **Django App Scaffolding**
   - Create `apps/tournament_ops/` app structure.
   - Models: `TournamentOperationalState`, `TournamentRegistration`, `EligibilityCheckResult`.
   - Migrations for initial schema.

2. **RegistrationService Implementation**
   - `submit_registration()`: Create registration record, trigger eligibility checks.
   - `check_eligibility()`: Orchestrate checks via GameService, TeamService, UserService.
   - `approve_registration()` / `reject_registration()`: Manual admin actions.
   - `get_tournament_registrations()`: Query registrations with filtering.

3. **Eligibility Check Integrations**
   - **GameService Integration**:
     - Define `GameService` interface in `apps/games/services.py` (if doesn't exist):
       - `check_player_eligibility(user_id, game_id, rank_requirement)`.
       - `verify_player_identity(user_id, game_id)`.
     - Implement for at least 1 game (Valorant or CS2 as pilot).
   - **TeamService Integration**:
     - Define `TeamService` interface in `apps/teams/services.py`:
       - `validate_roster(team_id, game_id, roster_rules)`.
       - `is_team_captain(user_id, team_id)`.
       - `get_team_roster(team_id)`.
     - Implement using existing Team/TeamMembership models.
   - **UserService Integration**:
     - Define `UserService` interface in `apps/accounts/services.py`:
       - `is_user_banned(user_id)`.
       - `get_user_profile(user_id)`.

4. **Entry Fee Integration (Optional for T1)**
   - Integrate with `apps.economy.services.PaymentService`:
     - Extend with `reserve_funds()`, `capture_reservation()`, `release_reservation()` methods.
   - Handle entry fee debit on registration approval.

5. **Admin UI**
   - Django Admin panels for:
     - `TournamentRegistration`: List view with status filters, approve/reject actions.
     - `EligibilityCheckResult`: Read-only view of check results per registration.

6. **REST API Endpoints**
   - `POST /api/tournament-ops/tournaments/{id}/register`: Submit registration.
   - `GET /api/tournament-ops/tournaments/{id}/registrations`: List registrations (admin only).
   - `POST /api/tournament-ops/registrations/{id}/approve`: Approve registration (admin).
   - `POST /api/tournament-ops/registrations/{id}/reject`: Reject registration (admin).

7. **Tests**
   - Unit tests for `RegistrationService` methods (mock external service calls).
   - Integration tests:
     - Solo registration flow (user registers, passes eligibility, approved).
     - Team registration flow (team captain registers, roster validation).
     - Eligibility failure scenarios (missing game account, below rank requirement, banned user).

**Dependencies:**
- `apps.tournaments` (read `Tournament` model for tournament config).
- `apps.games` (GameService must be implemented or stubbed).
- `apps.teams` (TeamService must be implemented).
- `apps.accounts` (UserService minimal implementation).
- `apps.economy` (PaymentService extension for entry fees).

**Success Criteria:**
- Tournament organizers can enable TournamentOps registration for a pilot tournament.
- Solo and team registrations submitted successfully.
- Eligibility checks execute and return pass/fail results.
- Admins can approve/reject registrations via admin UI or API.

**Timeline Estimate**: 2-3 weeks (with existing service APIs defined).

---

### T2 – MatchOps (Scheduling, Check-In, Result Handling)

**Goal**: Automate match scheduling, check-in workflows, and result submission.

**Deliverables:**

1. **Models**
   - `MatchOperationalState`: One-to-one with `apps.tournaments.Match`, stores operational metadata.
   - `ScheduleBlock`: Time slot reservations for match scheduling.
   - `ResultSubmission`: Result claims submitted by participants.

2. **MatchOpsService Implementation**
   - `schedule_match()`: Create match, assign to schedule block.
   - `generate_brackets()`: Bracket generation with seeding algorithms (start with rank-based, single elimination).
   - `open_check_in()`: Transition match to CheckInOpen state, send notifications.
   - `record_check_in()`: Track participant check-ins.
   - `create_lobby()`: Delegate to GameService for lobby creation.
   - `start_match()` / `complete_match()`: Transition match states.
   - `handle_no_show()`: Award forfeit if participant doesn't check in.

3. **ResultVerificationService Implementation**
   - `submit_result()`: Accept result claim from participant.
   - `auto_verify_consensus()`: Check if multiple submissions agree.
   - `verify_result()`: Admin manual verification, update Match model.
   - `reject_result()`: Reject fraudulent submission.

4. **Bracket Generation Algorithms**
   - Single elimination bracket generator (support powers of 2: 8, 16, 32 teams).
   - Handle byes for odd participant counts.
   - Rank-based seeding integration with `TeamRankingService.get_team_ranking()`.

5. **Check-In Automation**
   - Celery scheduled task:
     - Runs every minute, queries matches where `check_in_window_start <= now()`.
     - Calls `MatchOpsService.open_check_in()` for eligible matches.
   - Celery task for check-in deadline enforcement:
     - Queries matches in `CheckInOpen` state past deadline.
     - Calls `handle_no_show()` for participants who didn't check in.

6. **GameService Lobby Creation Integration**
   - Define `GameService.create_tournament_lobby()` interface:
     - Inputs: `game_id`, `participants`, `match_config`.
     - Outputs: `lobby_id`, `join_code`, `lobby_url`.
   - Implement stub for pilot game (returns mock lobby credentials).
   - Real implementation connects to external game APIs (Riot, Steam) in future phase.

7. **Notification Integration**
   - Define `NotificationService` interface in `apps/notifications/services.py`:
     - `send_check_in_reminder(entity_id, match_id, deadline)`.
     - `send_match_ready_notification(entity_id, match_id, lobby_info)`.
   - Implement email/SMS notifications for check-in and match ready events.

8. **Admin UI**
   - Django Admin panels:
     - `MatchOperationalState`: View match state, manual state transitions (admin override).
     - `ResultSubmission`: Review conflicting submissions, verify/reject results.
   - Bracket visualization UI (simple tree view, can be enhanced in later phase).

9. **REST API Endpoints**
   - `POST /api/tournament-ops/tournaments/{id}/generate-brackets`: Initiate bracket generation (admin).
   - `POST /api/tournament-ops/matches/{id}/check-in`: Record check-in (participant).
   - `GET /api/tournament-ops/matches/{id}/status`: Get match state and check-in status.
   - `POST /api/tournament-ops/matches/{id}/submit-result`: Submit result claim.
   - `POST /api/tournament-ops/results/{id}/verify`: Admin verify result.

10. **Tests**
    - Unit tests for `MatchOpsService` and `ResultVerificationService`.
    - Integration tests:
      - Bracket generation for 8-team tournament.
      - Check-in flow (both teams check in → lobby created).
      - Forfeit scenario (one team no-show).
      - Result submission consensus (both teams agree → auto-verify).
      - Result submission conflict (teams disagree → admin review).

**Dependencies:**
- T1 (registration must be complete to have participants for brackets).
- `apps.games.GameService` (lobby creation interface).
- `apps.notifications.NotificationService` (check-in reminders).
- `apps.teams.TeamRankingService` (for seeding).

**Success Criteria:**
- Brackets generated automatically for pilot tournament.
- Check-in workflow functional (participants notified, lobby created after check-in).
- Result submission and verification workflow tested.
- No-show handling awards forfeits correctly.

**Timeline Estimate**: 3-4 weeks.

---

### T3 – Dispute Resolution System

**Goal**: Build comprehensive dispute handling workflow with moderator tools.

**Deliverables:**

1. **Models**
   - `DisputeTicket`: Dispute records with lifecycle tracking.
   - Link to `apps.moderation` if moderation models exist (or create minimal moderation models).

2. **DisputeService Implementation**
   - `create_dispute()`: File dispute against match result or eligibility decision.
   - `assign_moderator()`: Assign dispute to moderation queue.
   - `request_additional_evidence()`: Moderator requests more info from parties.
   - `resolve_dispute()`: Apply moderator ruling (uphold, overturn, dismiss).
   - Integration with `ResultVerificationService` to revert/update results based on ruling.

3. **Dispute SLA Tracking**
   - Add `sla_deadline` field to `DisputeTicket` (e.g., disputes must be resolved within 48 hours).
   - Celery task to escalate overdue disputes to senior moderators.
   - Metrics tracking: average dispute resolution time, dispute rate per tournament.

4. **Evidence Attachment System**
   - Support file uploads (screenshots, videos) for dispute evidence.
   - Store evidence URLs in `DisputeTicket.evidence_urls` (JSON field).
   - Integrate with S3 or CDN for evidence storage.

5. **ModerationService Integration**
   - Define `ModerationService` interface in `apps/moderation/services.py`:
     - `flag_for_investigation(user_id, reason, evidence)`.
     - `issue_ban(user_id, ban_type, duration, reason)`.
     - `check_active_bans(user_id)`.
   - Implement ban enforcement: disputed cheating → issue tournament ban.

6. **Admin UI**
   - Django Admin panels:
     - `DisputeTicket`: Queue view for moderators (filter by status, SLA urgency).
     - Dispute detail view: evidence gallery, action buttons (request evidence, resolve).
   - Moderation dashboard (filter disputes by game, tournament, urgency).

7. **REST API Endpoints**
   - `POST /api/tournament-ops/matches/{id}/dispute`: File dispute.
   - `GET /api/tournament-ops/disputes/{id}`: Get dispute details.
   - `POST /api/tournament-ops/disputes/{id}/assign`: Assign moderator (admin).
   - `POST /api/tournament-ops/disputes/{id}/request-evidence`: Request additional evidence (moderator).
   - `POST /api/tournament-ops/disputes/{id}/resolve`: Resolve dispute (moderator).

8. **Tests**
   - Unit tests for `DisputeService` methods.
   - Integration tests:
     - Dispute filed → assigned to moderator → resolved (upheld).
     - Dispute dismissed (original result stands).
     - Dispute overturns result → standings recalculated.
     - Evidence upload and retrieval.

**Dependencies:**
- T2 (disputes arise from match results).
- `apps.moderation` (ban enforcement).
- `apps.notifications` (dispute status updates).

**Success Criteria:**
- Moderators can review and resolve disputes via admin UI.
- Dispute rulings correctly update match results and standings.
- SLA tracking prevents disputes from languishing unresolved.

**Timeline Estimate**: 2-3 weeks.

---

### T4 – Standings & Ranking Integration

**Goal**: Real-time standings calculation and global ranking sync.

**Deliverables:**

1. **Models**
   - `TournamentStanding`: Cache of current standings (participant, rank, points, wins, losses).

2. **StandingsService Implementation**
   - `recalculate_standings()`: Compute standings based on scoring rules.
   - `get_standings()`: Retrieve current or historical standings.
   - `sync_to_global_rankings()`: Push tournament results to TeamRankingService.

3. **Scoring Rules Configuration**
   - Retrieve scoring rules from `apps.games.GameTournamentConfig.scoring_rules`.
   - Support configurable rules:
     - Points per win/loss/draw.
     - Tiebreaker rules (head-to-head, round differential, total rounds won).
   - Handle multiple formats (round-robin, single-elim, double-elim).

4. **Real-Time Standings Updates**
   - Event-driven architecture:
     - `ResultVerificationService.verify_result()` emits `MatchResultVerified` event.
     - Event handler calls `StandingsService.recalculate_standings()`.
   - WebSocket integration (optional for T4, can defer to T6):
     - Broadcast `StandingsUpdated` event to frontend clients.
     - Live leaderboard updates without page refresh.

5. **TeamRankingService Integration**
   - Implement or extend `TeamRankingService` in `apps/teams`:
     - `update_ranking(team_id, game_id, tournament_result)`: Apply ELO/MMR update based on tournament performance.
     - `get_team_ranking(team_id, game_id)`: Retrieve current global ranking.
   - Tournament result payload includes:
     - Placement, points earned, opponents faced, tournament tier.
   - ELO algorithm implementation (or use existing if already present).

6. **Caching Strategy**
   - Store standings in Redis with TTL = 5 minutes during `Live` tournament state.
   - Invalidate cache on each standings update.
   - Persist final locked standings to database when tournament completes.

7. **Admin UI**
   - Django Admin panel:
     - `TournamentStanding`: Read-only view of current standings.
   - Standings management page:
     - Manual recalculation trigger (admin override).
     - View historical standings snapshots.

8. **REST API Endpoints**
   - `GET /api/tournament-ops/tournaments/{id}/standings`: Get current standings.
   - `POST /api/tournament-ops/tournaments/{id}/recalculate-standings`: Force recalculation (admin).

9. **Tests**
   - Unit tests for standings calculation logic (various scoring rules, tiebreakers).
   - Integration tests:
     - Standings update after each match result verified.
     - Tiebreaker scenarios (head-to-head, round diff).
     - Global ranking sync after tournament completion.

**Dependencies:**
- T2 (match results feed into standings).
- `apps.games.GameTournamentConfig` (scoring rules).
- `apps.teams.TeamRankingService` (global ranking updates).

**Success Criteria:**
- Standings calculated correctly for pilot tournament.
- Real-time updates reflect match results immediately.
- Global team rankings updated after tournament finalized.

**Timeline Estimate**: 2-3 weeks.

---

### T5 – Certificates & Prize Integration

**Goal**: Automate certificate generation and prize distribution.

**Deliverables:**

1. **Models**
   - `CertificateRecord`: Store certificate metadata and verification hashes.
   - `RewardDistribution`: Track prize distribution status (pending, distributed, confirmed).

2. **CompletionService Implementation**
   - `finalize_tournament()`: Lock standings, trigger reward distribution.
   - `generate_certificates()`: Create certificates for all participants.
   - `distribute_rewards()`: Distribute prizes via EconomyService.
   - `verify_certificate()`: Public API to verify certificate authenticity.

3. **Certificate Generation**
   - Integration with PDF generation service (e.g., WeasyPrint, external API, or templating engine).
   - Certificate template design:
     - DeltaCrown branding, tournament name, game, participant name, placement, date.
     - Verification QR code linking to `/api/certificates/verify/{hash}`.
   - Cryptographic verification:
     - `verification_hash = sha256(recipient_id + tournament_id + placement + secret_salt)`.
   - Store certificate PDFs in S3/CDN, link URL in `CertificateRecord`.

4. **Prize Distribution (Virtual)**
   - Integration with `apps.economy.services.PaymentService.credit()`:
     - Distribute DeltaCrown credits to winners.
     - Support team prize splitting (divide among team members).
   - Create `RewardDistribution` records for audit trail.
   - Send confirmation notifications via `NotificationService`.

5. **Prize Distribution (Physical)**
   - Create `RewardDistribution` records with `prize_type="physical"`.
   - Queue for manual fulfillment or integrate with external fulfillment API.
   - Track shipping status (pending, shipped, delivered).

6. **Badge/Achievement Integration (Optional)**
   - If `apps.user_profile` supports achievements/badges:
     - Award "Tournament Champion", "Tournament Participant" badges.
     - Display badges on user profiles.

7. **Admin UI**
   - Django Admin panels:
     - `CertificateRecord`: View generated certificates, regenerate if needed.
     - `RewardDistribution`: Track prize distribution status, mark as shipped/confirmed.
   - Prize distribution dashboard:
     - Bulk approve prize distributions.
     - Export prize distribution report for accounting.

8. **REST API Endpoints**
   - `POST /api/tournament-ops/tournaments/{id}/finalize`: Finalize tournament (admin).
   - `POST /api/tournament-ops/tournaments/{id}/generate-certificates`: Generate certificates (admin).
   - `POST /api/tournament-ops/tournaments/{id}/distribute-rewards`: Distribute prizes (admin).
   - `GET /api/certificates/verify/{hash}`: Public certificate verification.
   - `GET /api/tournament-ops/users/{id}/certificates`: User's certificates list.

9. **Tests**
   - Unit tests for `CompletionService` methods.
   - Integration tests:
     - Certificate generation for 32-team tournament.
     - Certificate verification (valid hash → returns certificate, invalid hash → 404).
     - Prize distribution (credits added to user wallets).
     - Physical prize tracking (status updates).

**Dependencies:**
- T4 (final standings must be locked before prize distribution).
- `apps.economy.services.PaymentService` (credit distribution).
- `apps.notifications` (reward confirmation notifications).
- PDF generation service (external or library).

**Success Criteria:**
- Certificates generated automatically for all participants after tournament completion.
- Prizes distributed to winners (virtual credits confirmed in wallets).
- Public certificate verification API functional.

**Timeline Estimate**: 2-3 weeks.

---

### T6 – Operator Dashboards, Analytics, Final Cleanup

**Goal**: Build operator tools, observability, and production readiness.

**Deliverables:**

1. **OpsActionLog Implementation**
   - Model: `OpsActionLog` (comprehensive audit trail).
   - Middleware/decorator to auto-log all admin actions:
     - Registration approvals/rejections.
     - Result verifications.
     - Dispute resolutions.
     - State transitions (tournament, match).
   - Store: `action_type`, `performed_by`, `affected_entity`, `justification`, `previous_state`, `new_state`.

2. **Operator Dashboard UI**
   - Tournament health overview:
     - Active tournaments, registrations pending review, matches awaiting check-in, disputes pending resolution.
   - Real-time metrics:
     - Check-in success rate, dispute rate, average result verification time.
   - Quick actions:
     - Approve pending registrations in bulk.
     - Manually verify batch of results.
     - Reassign disputes to different moderators.

3. **Analytics & Reporting**
   - Post-tournament analytics:
     - Total participants, match completion rate, dispute rate.
     - Average match duration, check-in compliance rate.
     - Prize distribution summary.
   - Export reports (CSV, PDF) for tournament retrospectives.
   - Integration with analytics platform (e.g., Grafana dashboards).

4. **Observability**
   - Logging: Structured logging for all service calls (JSON format).
   - Metrics: Instrument services with Prometheus metrics:
     - `tournament_ops_registrations_total{status="approved|rejected"}`.
     - `tournament_ops_matches_total{state="completed|disputed"}`.
     - `tournament_ops_disputes_resolution_time_seconds`.
   - Alerts: Set up alerts for:
     - High dispute rate (>10% of matches).
     - SLA breaches (disputes unresolved for >48h).
     - Check-in failures (>20% no-show rate).

5. **Feature Flags**
   - Integrate with feature flag system (e.g., Django Waffle, LaunchDarkly):
     - `tournament_ops_registration_enabled`: Gate new registration flow.
     - `tournament_ops_auto_verification_enabled`: Toggle auto result verification.
   - Allow per-tournament feature flag overrides.

6. **Migration Path for Existing Tournaments**
   - Data migration script:
     - Backfill `TournamentOperationalState` for active tournaments in `apps.tournaments`.
     - Link existing `Match` records to `MatchOperationalState`.
   - Provide rollback mechanism if issues arise.
   - Gradual rollout: Enable TournamentOps for new tournaments first, migrate existing tournaments later.

7. **Performance Optimization**
   - Database query optimization:
     - Add indexes on frequently queried fields (`tournament_id`, `status`, `state`).
     - Use `select_related()` / `prefetch_related()` to reduce N+1 queries.
   - Celery task optimization:
     - Batch check-in reminders (send 100 notifications per task instead of 1).
     - Use Celery beat for scheduled tasks (check-in windows, standings updates).
   - Redis caching for hot paths (standings, leaderboards).

8. **Documentation**
   - API documentation (OpenAPI/Swagger):
     - Document all REST API endpoints with examples.
   - Operator runbook:
     - How to approve registrations, resolve disputes, manually verify results.
     - Troubleshooting guide (common issues, how to rollback actions).
   - Architecture documentation:
     - Update system architecture diagrams to include TournamentOps.
     - Document service contracts and integration points.

9. **Security Hardening**
   - API authentication: Ensure all endpoints require authentication (user or admin).
   - Authorization checks: Verify user permissions (e.g., only moderators can resolve disputes).
   - Rate limiting: Prevent abuse (e.g., spam result submissions).
   - Evidence upload validation: Scan uploaded files for malware, enforce size limits.

10. **Final Testing**
    - End-to-end testing:
      - Full tournament lifecycle test (registration → brackets → matches → results → disputes → completion).
    - Load testing:
      - Simulate 100-team tournament with concurrent check-ins, result submissions.
    - Chaos testing:
      - Test failure scenarios (external API timeouts, database failures, Celery task failures).

**Dependencies:**
- T1-T5 (all core features must be complete).
- Monitoring infrastructure (Prometheus, Grafana).
- Feature flag system.

**Success Criteria:**
- TournamentOps deployed to production with full observability.
- Operator dashboard provides actionable insights.
- System handles realistic load (500+ concurrent users, 100+ team tournament).
- Feature flags enable gradual rollout without downtime.

**Timeline Estimate**: 3-4 weeks.

---

### Phase Plan Summary

| Phase | Duration | Dependencies | Key Deliverables |
|-------|----------|--------------|------------------|
| **T1** | 2-3 weeks | None | Registration & Eligibility Engine |
| **T2** | 3-4 weeks | T1 | MatchOps (Scheduling, Check-In, Results) |
| **T3** | 2-3 weeks | T2 | Dispute Resolution System |
| **T4** | 2-3 weeks | T2, T3 | Standings & Ranking Integration |
| **T5** | 2-3 weeks | T4 | Certificates & Prize Distribution |
| **T6** | 3-4 weeks | T1-T5 | Operator Dashboards, Analytics, Production Hardening |
| **Total** | **15-22 weeks** (~4-5 months) | | Full TournamentOps System |

**Rollout Strategy:**
- **Week 1-3 (T1)**: Enable registration for pilot tournament (invite-only).
- **Week 4-7 (T2)**: Run first live tournament with automated brackets and check-in.
- **Week 8-10 (T3)**: Enable dispute system for subsequent tournaments.
- **Week 11-13 (T4)**: Activate global ranking sync for competitive tournaments.
- **Week 14-16 (T5)**: Deploy automated certificates and prize distribution.
- **Week 17-22 (T6)**: Full production rollout, migrate all active tournaments to TournamentOps.

---

## 7. Risks & Open Questions

### 7.1 Architectural Risks

**Risk 1: Dual System Complexity**
- **Issue**: Running TournamentOps alongside existing `apps.tournaments` creates two sources of truth.
- **Mitigation**:
  - TournamentOps reads from `apps.tournaments.Tournament` for configuration (tournament definition remains in existing app).
  - TournamentOps owns operational state only (`TournamentOperationalState`, `MatchOperationalState`).
  - Clear ownership boundaries documented and enforced via code reviews.
- **Residual Risk**: Developers may bypass TournamentOps and modify `apps.tournaments` directly. Requires team discipline and linting rules.

**Risk 2: Service Contract Breakage**
- **Issue**: If `GameService`, `TeamService`, etc. change interfaces without TournamentOps awareness, integrations break.
- **Mitigation**:
  - Define service contracts as Python protocols/abstract base classes.
  - Service contracts versioned (e.g., `GameServiceV1`, `GameServiceV2`).
  - Integration tests run on every commit to catch breaking changes.
  - Deprecation policy: 2-sprint notice before removing old interface.
- **Residual Risk**: Requires cross-team coordination. May need API governance committee.

**Risk 3: Performance Degradation from Service Hops**
- **Issue**: Service-to-service calls add latency (TournamentOps → GameService → external Riot API).
- **Mitigation**:
  - Cache external API responses (e.g., player rank cached for 24h).
  - Async task processing (Celery) for non-blocking workflows (eligibility checks run in background).
  - Database read replicas for heavy queries (standings calculation).
  - Load testing to identify bottlenecks early.
- **Monitoring**: Track P95 latency for service calls, alert if >500ms.

**Risk 4: State Machine Deadlocks**
- **Issue**: Match stuck in `CheckInOpen` state forever if Celery task fails to transition to `Ready`.
- **Mitigation**:
  - Celery task retries with exponential backoff.
  - Manual admin override actions to force state transitions.
  - Stale state detection: Celery task runs hourly, flags matches in unexpected states (e.g., `CheckInOpen` for >2 hours).
  - Dead letter queue for failed tasks.
- **Monitoring**: Alert if >5% of matches in stale states.

---

### 7.2 Migration Risks

**Risk 5: Data Inconsistency During Migration**
- **Issue**: Backfilling `TournamentOperationalState` for active tournaments may conflict with live updates.
- **Mitigation**:
  - Migration runs during maintenance window (low-traffic period).
  - Feature flag: TournamentOps disabled during migration, re-enabled after validation.
  - Migration script is idempotent (safe to re-run if partial failure).
  - Rollback plan: Revert migration, fall back to old `apps.tournaments` logic.
- **Testing**: Dry-run migration on staging environment with production data snapshot.

**Risk 6: Tournament Mid-Flight Transition**
- **Issue**: Tournament starts with old system, needs to transition to TournamentOps mid-tournament.
- **Mitigation**:
  - TournamentOps only enabled for tournaments in `Draft` or `RegistrationOpen` state initially.
  - Existing live tournaments complete on old system.
  - Gradual rollout: New tournaments use TournamentOps, old tournaments grandfathered.
- **Trade-off**: Two systems running in parallel for 1-2 months until old tournaments complete.

**Risk 7: User Behavior Disruption**
- **Issue**: New check-in workflow differs from old system, confuses users.
- **Mitigation**:
  - User education: In-app tooltips, email announcements, FAQ updates.
  - A/B testing: Roll out to 10% of users first, gather feedback, iterate.
  - Support team trained on new workflows before launch.
- **Monitoring**: Track support ticket volume for "check-in confusion" during rollout.

---

### 7.3 Performance Considerations

**Bottleneck 1: Standings Recalculation**
- **Concern**: Recalculating standings for 500-team round-robin tournament (124,750 matches) may take >10 seconds.
- **Optimization**:
  - Incremental standings updates (only recalculate affected participants after each match, not full recalc).
  - Precompute partial standings (standings for each group stage, then merge for playoffs).
  - Database indexes on `Match.tournament_id`, `Match.winner`.
- **Acceptance Criteria**: Standings update completes in <2 seconds for 500-team tournament.

**Bottleneck 2: Eligibility Check External API Calls**
- **Concern**: Riot API rate limits (100 requests/2 minutes) may throttle eligibility checks for large tournaments.
- **Optimization**:
  - Batch eligibility checks (process 10 teams per Celery task, queue 100 tasks).
  - Cache rank lookups (24-hour TTL).
  - Fallback: If Riot API unavailable, flag for manual review instead of failing registration.
- **Acceptance Criteria**: 500 registrations processed within 1 hour (avg 7 seconds per registration).

**Bottleneck 3: Websocket Broadcast for Standings**
- **Concern**: Broadcasting standings to 10,000 spectators may overload websocket server.
- **Optimization**:
  - Use PubSub pattern (Redis Pub/Sub or Kafka) for scalable broadcasts.
  - Throttle broadcasts (max 1 update per 10 seconds even if matches complete faster).
  - Frontend clients poll if websocket connection fails (graceful degradation).
- **Acceptance Criteria**: Support 50,000 concurrent spectators without websocket latency >1 second.

---

### 7.4 Product & UX Uncertainties

**Open Question 1: Scoring Rules Complexity**
- **Question**: How should TournamentOps handle game-specific scoring (e.g., Valorant round differential vs CS2 map differential)?
- **Options**:
  - A) Hardcode scoring logic per game in TournamentOps (violates game-agnostic principle).
  - B) Store scoring rules in `GameTournamentConfig.scoring_rules` as JSON, interpret dynamically (flexible but complex).
  - C) Allow tournament organizers to upload custom scoring plugins (Python scripts, sandboxed execution).
- **Decision Needed**: Product team to define supported scoring models (likely Option B for MVP, Option C for future).

**Open Question 2: Dispute SLA Policy**
- **Question**: What is acceptable dispute resolution time? 24h? 48h? Varies by tournament tier?
- **Options**:
  - A) Fixed 48-hour SLA for all disputes.
  - B) Tiered SLA (premier tournaments: 24h, community tournaments: 72h).
  - C) Dynamic SLA based on tournament progress (disputes during finals: 6h, disputes during group stage: 48h).
- **Decision Needed**: Operations team to define SLA policy (likely Option B).

**Open Question 3: Entry Fee Refund Policy**
- **Question**: If team withdraws after registration approved, should entry fee be refunded?
- **Options**:
  - A) No refunds after approval (prevents abuse).
  - B) Partial refund (50%) if withdrawal >24h before tournament start.
  - C) Full refund until check-in window opens.
- **Decision Needed**: Finance/product team to define refund policy.

**Open Question 4: Team Prize Distribution**
- **Question**: When team wins prize, should it split among all members or captain decides distribution?
- **Options**:
  - A) Equal split among all team members automatically.
  - B) Captain receives full amount, distributes manually (TournamentOps tracks captain's distribution for transparency).
  - C) Team configures distribution percentages in team settings before tournament.
- **Decision Needed**: Product team to define prize distribution UX (likely Option A for MVP, Option C for future).

**Open Question 5: Certificate Regeneration**
- **Question**: If user changes username after tournament, should certificate be regenerated with new name?
- **Options**:
  - A) Certificates are immutable snapshots (username at tournament completion).
  - B) Certificates regenerate on-demand with current username (verification hash changes).
  - C) Allow one-time certificate update within 30 days of issuance.
- **Decision Needed**: Product team to define certificate immutability policy (likely Option A for authenticity).

---

### 7.5 Compliance & Legal Risks

**Risk 8: Prize Tax Reporting**
- **Issue**: US tax law requires 1099 forms for prizes >$600. TournamentOps may need tax reporting features.
- **Mitigation**:
  - Phase 1: Manual process (finance team exports prize distribution reports, files taxes separately).
  - Phase 2: Integrate with tax reporting service (e.g., Stripe Tax, TaxJar) to auto-generate 1099s.
- **Legal Review Required**: Consult legal team before distributing prizes >$600.

**Risk 9: GDPR Compliance (Evidence Storage)**
- **Issue**: Dispute evidence (screenshots, videos) may contain personal data (player names, chat logs). GDPR requires data deletion upon request.
- **Mitigation**:
  - Evidence retention policy: Delete evidence 90 days after dispute resolved (unless flagged for fraud investigation).
  - GDPR deletion API: Allow users to request evidence deletion.
  - Evidence anonymization: Blur player names in stored evidence.
- **Legal Review Required**: Confirm retention policy complies with GDPR Article 17 (right to erasure).

**Risk 10: Age Verification for Prize Eligibility**
- **Issue**: Some jurisdictions require age verification for prize contests (minors may need parental consent).
- **Mitigation**:
  - Age gate during registration: Users confirm age >18 (or >13 with parental consent).
  - Store age verification timestamp in `UserProfile`.
  - Prize distribution blocked for unverified minors (manual review required).
- **Legal Review Required**: Verify age verification requirements per jurisdiction.

---

### 7.6 Technical Debt & Future Enhancements

**Deferred to Post-T6:**

1. **Real-Time Match Monitoring**
   - Goal: Integrate with game server APIs to auto-detect match completion (no manual result submission).
   - Complexity: Requires game-specific webhooks (Riot, Steam), API key management.
   - Timeline: 1-2 sprints post-T6.

2. **Advanced Bracket Formats**
   - Goal: Support Swiss system, double-elimination with losers bracket resets, group stage + playoffs.
   - Complexity: Complex bracket logic, many edge cases.
   - Timeline: 2-3 sprints post-T6 (incrementally add formats).

3. **Automated Seeding ML Model**
   - Goal: Use ML to predict team strength (beyond ELO), optimize seeding for competitive balance.
   - Complexity: Requires historical match data, model training, inference pipeline.
   - Timeline: Long-term research project (6+ months).

4. **Live Spectator Integration**
   - Goal: Embed live match streams in tournament pages, sync with match state.
   - Complexity: Requires `apps.spectator` integration, CDN for video streaming.
   - Timeline: 3-4 sprints post-T6.

5. **Mobile App Support**
   - Goal: Mobile-optimized check-in, result submission, dispute filing.
   - Complexity: Requires mobile API endpoints, push notifications, offline support.
   - Timeline: Separate mobile app project (3+ months).

---

### 7.7 Rollback & Contingency Plans

**Scenario 1: Critical Bug in TournamentOps During Live Tournament**
- **Symptoms**: Match states stuck, results not saving, check-ins failing.
- **Response**:
  - Feature flag: Disable `tournament_ops_enabled` immediately (rollback to old system).
  - Admin override: Manually update `apps.tournaments.Match` records to unblock tournament.
  - Postmortem: Identify bug, fix, deploy hotfix, re-enable TournamentOps for next tournament.
- **Prevention**: Pre-launch dry runs, canary deployments (enable for 1 tournament before full rollout).

**Scenario 2: External Service Outage (Riot API Down)**
- **Symptoms**: Eligibility checks failing, registrations stuck in pending.
- **Response**:
  - Fallback mode: Skip external API checks, flag registrations for manual review.
  - Admin bulk approval: Admins review flagged registrations, approve based on cached data.
  - Resume automation: When Riot API recovers, re-run eligibility checks for flagged registrations.
- **Prevention**: Circuit breaker pattern (if Riot API fails 3x, skip checks for 10 minutes).

**Scenario 3: Database Performance Degradation**
- **Symptoms**: Standings calculation timing out (>30 seconds).
- **Response**:
  - Emergency cache: Serve stale standings from Redis until DB query optimized.
  - Query optimization: Add missing indexes, rewrite slow queries.
  - Scale up: Increase database resources (vertical scaling) or add read replicas (horizontal scaling).
- **Prevention**: Load testing before each major tournament (simulate 500-team load).

---

**END OF PART 2 (All Sections Complete)**

