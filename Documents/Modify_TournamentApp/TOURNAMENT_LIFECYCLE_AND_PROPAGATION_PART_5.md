# Part 5/6: Tournament Lifecycle & Result Propagation

**Document Purpose**: Overview of tournament lifecycle stages, involved models/services, and how results propagate to other platform components (stats, leaderboards, history).

**Audit Date**: December 8, 2025  
**Scope**: Full tournament flow from creation to completion, automatic updates, manual gaps

---

## 1. Tournament Lifecycle Overview

### 1.1 Status State Machine

```
DRAFT
  ↓
PENDING_APPROVAL (if approval required)
  ↓
PUBLISHED
  ↓
REGISTRATION_OPEN
  ↓
REGISTRATION_CLOSED
  ↓
LIVE (matches in progress)
  ↓
COMPLETED (all matches finished)
  ↓
ARCHIVED (optional)
```

**Additional States**: `CANCELLED` (can transition from any state)

**Source**: `apps/tournaments/models/tournament.py` lines 168-185

---

## 2. Stage-by-Stage Breakdown

### Stage 1: Tournament Creation

**Status**: `DRAFT` → `PUBLISHED` → `REGISTRATION_OPEN`

**Models Involved**:
- `Tournament` - Core tournament record
- `Game` - Game configuration (team size, result types)
- `CustomField` - Optional registration fields
- `TournamentStaff` - Organizer permissions

**Services**:
- `TournamentService.create_tournament()` - Initial creation
- No automation - manual organizer setup via admin/organizer console

**Auto-Updates**: None (manual creation)

**Manual Steps**:
1. Organizer fills tournament details (name, game, format, dates, prize pool)
2. Configure registration fields (optional custom fields)
3. Set entry fee and payment methods
4. Publish tournament → `REGISTRATION_OPEN`

---

### Stage 2: Registration

**Status**: `REGISTRATION_OPEN`

**Models Involved**:
- `Registration` - Participant registration record
- `Payment` - Payment tracking (if entry fee required)
- `Team` (indirect) - Team ID stored as IntegerField (loose coupling)
- `UserProfile` - Auto-fill source for player data

**Services**:
- `RegistrationService.register_participant()` - Create registration
- `RegistrationAutoFillService.get_autofill_data()` - Pre-fill form fields
- `RegistrationEligibilityService.check_eligibility()` - Validate participant
- `PaymentService.process_deltacoin_payment()` - Instant payment verification
- `PaymentService.submit_payment()` - Manual payment proof submission

**Auto-Updates**:
- ✅ `Registration.status` → `CONFIRMED` (if DeltaCoin payment or no fee)
- ✅ `Registration.status` → `PAYMENT_SUBMITTED` (if manual payment)
- ✅ DeltaCoin wallet deducted automatically
- ❌ **No user/team stats updated during registration**

**Manual Steps**:
- Organizer verifies manual payments (bKash/Nagad) → `Payment.status = VERIFIED`
- Organizer approves/rejects registrations

**Transition Trigger**: Organizer manually closes registration → `REGISTRATION_CLOSED`

---

### Stage 3: Match Generation / Bracket Creation

**Status**: `REGISTRATION_CLOSED` → `LIVE`

**Models Involved**:
- `Bracket` - Tournament bracket structure
- `Match` - Individual match records
- `Registration` - Participants seeded into bracket

**Services**:
- `BracketService.generate_bracket()` - Create bracket tree
- `BracketService.create_matches_from_bracket()` - Generate match records
- `BracketGeneratorService.generate_bracket_for_tournament()` - Legacy wrapper

**Bracket Types Supported**:
- Single Elimination
- Double Elimination
- Round Robin
- Swiss System
- Group Stage + Playoff

**Auto-Updates**:
- ✅ Creates all `Match` records with initial state `SCHEDULED`
- ✅ Assigns `participant1_id`, `participant2_id` (IntegerField IDs, not ForeignKeys)
- ✅ Calculates `round_number`, `match_number`
- ✅ Sets `scheduled_time` (if provided)
- ✅ Sets `check_in_deadline` (if check-in enabled)
- ❌ **No bracket auto-generation on registration close** (manual trigger required)

**Manual Steps**:
- Organizer clicks "Generate Bracket" button
- Organizer selects seeding method (random, ranked, manual)
- Organizer schedules match times (optional)

**Transition Trigger**: First match starts → `Tournament.status = LIVE`

---

### Stage 4: Playing Matches (Check-in → Live → Result Submission)

**Status**: `LIVE`

**Match State Flow**:
```
SCHEDULED
  ↓
CHECK_IN (participants checking in)
  ↓
READY (both participants ready)
  ↓
LIVE (match in progress)
  ↓
PENDING_RESULT (result submitted, awaiting confirmation)
  ↓
COMPLETED (result confirmed)
```

**Alternative Paths**:
- `CHECK_IN` → `FORFEIT` (missed check-in deadline)
- `PENDING_RESULT` → `DISPUTED` (opponent contests result)

**Models Involved**:
- `Match` - Match state and scores
- `Dispute` - Dispute records (if contested)

**Services**:
- `MatchService.check_in_participant()` - Handle check-in
- `MatchService.transition_to_live()` - Start match
- `MatchService.submit_result()` - Participant submits score
- `MatchService.confirm_result()` - Opponent/organizer confirms
- `MatchService.report_dispute()` - Create dispute
- `CheckInService` - Check-in deadline enforcement

**Auto-Updates During Match Completion**:

**When `confirm_result()` Called** (line 405 in `match_service.py`):
1. ✅ `Match.state = COMPLETED`
2. ✅ `Match.completed_at = timezone.now()`
3. ✅ `Match.winner_id`, `Match.loser_id` set
4. ✅ **Bracket progression**: Winner advances to next round (via `BracketService.update_bracket_after_match()`)
5. ✅ **WebSocket broadcast**: `match_completed` event (real-time notification)
6. ❌ **Player stats NOT updated** (TODO comment in code: "Update player stats - Module 2.x - AnalyticsService")
7. ❌ **DeltaCoin rewards NOT awarded** (TODO comment: "Award DeltaCoin for win - Module 2.x - EconomyService")

**Evidence of Missing Auto-Updates** (from `match_service.py` line 482):
```python
# TODO: Award DeltaCoin for win (Module 2.x - EconomyService)
# TODO: Update player stats (Module 2.x - AnalyticsService)
```

**Manual Steps**:
- Organizer resolves disputes
- Organizer overrides incorrect results
- Organizer manually awards points (if not automated)

---

### Stage 5: Tournament Completion & Winner Determination

**Status**: `LIVE` → `COMPLETED`

**Models Involved**:
- `TournamentResult` - Winner, runner-up, third place records
- `Certificate` - Achievement certificates
- `PrizeTransaction` - Prize payouts

**Services**:
- `WinnerDeterminationService.determine_winner()` - Identify winner from bracket
- `PayoutService.calculate_prize_distribution()` - Calculate prize splits
- `PayoutService.process_payouts()` - Distribute prizes
- `CertificateService.generate_certificate()` - Create PDF certificates

**Winner Determination Flow** (from `winner_service.py` line 1-70):

1. **Verify All Matches Completed**:
   - Check no matches in `SCHEDULED`, `LIVE`, `PENDING_RESULT`, `DISPUTED` state
   - If incomplete → `ValidationError`

2. **Traverse Bracket Tree**:
   - Identify finals match winner → 1st place
   - Identify finals match loser → 2nd place
   - Identify 3rd place match winner (if exists) → 3rd place

3. **Apply Tie-Breaking Rules** (if needed):
   - Head-to-head record
   - Score differential
   - Seed ranking
   - Match completion time
   - If all fail → `ValidationError` (manual resolution required)

4. **Create `TournamentResult` Record**:
   - `winner_id`, `runner_up_id`, `third_place_id`
   - `determination_method` (e.g., "bracket_finals", "tie_breaker_head_to_head")
   - `rules_applied` (JSONB audit trail)
   - `requires_review` (flag for forfeit chains)

5. **Update Tournament Status**:
   - `Tournament.status = COMPLETED` (atomic transaction)

6. **Broadcast WebSocket Event**:
   - `tournament_completed` event (via `broadcast_tournament_event()`)

**Auto-Updates on Tournament Completion**:
- ✅ `TournamentResult` created with winner/runner-up/third place
- ✅ `Tournament.status = COMPLETED`
- ✅ WebSocket broadcast to all spectators
- ✅ **Idempotency**: Returns existing `TournamentResult` if called again
- ❌ **Team stats NOT auto-updated** (see Section 3 below)
- ❌ **User history NOT auto-updated** (no global leaderboard integration)
- ❌ **Certificates NOT auto-generated** (manual trigger required)
- ❌ **Prizes NOT auto-paid** (manual payout via `PayoutService`)

**Manual Steps**:
- Organizer triggers "Determine Winner" action
- Organizer generates certificates for top 3 + participants
- Organizer processes prize payouts

---

### Stage 6: Rewards, Certificates, Payouts

**Status**: `COMPLETED`

**Models Involved**:
- `Certificate` - PDF/PNG achievement certificates
- `PrizeTransaction` - Prize payout records
- `DeltaCrownTransaction` (Economy app) - Wallet transactions
- `DeltaCrownWallet` - User wallets

**Services**:
- `CertificateService.generate_certificate()` - Create certificates
- `PayoutService.process_payouts()` - Distribute prizes

**Certificate Generation** (from `certificate_service.py` line 100-200):

**Input**:
- `registration_id`
- `certificate_type`: winner | runner_up | third_place | participant
- `placement`: '1', '2', '3' (optional)
- `language`: 'en' | 'bn'

**Process**:
1. Verify `Tournament.status == COMPLETED`
2. Check for existing non-revoked certificate (idempotency)
3. Generate PDF with ReportLab (A4 landscape)
4. Embed QR code (links to verification endpoint)
5. Calculate SHA-256 hash (tamper detection)
6. Convert to PNG (optional)
7. Save `Certificate` record with file paths + hash

**Auto-Updates**:
- ❌ **Certificates NOT auto-generated** (organizer must click "Generate Certificates")
- ✅ **Idempotent**: Returns existing certificate if already generated

**Prize Payouts** (from `payout_service.py` line 30-100):

**Distribution Modes**:
1. **Percentage-based**: `{1: 50, 2: 30, 3: 20}` (50% to winner, etc.)
2. **Fixed amounts**: `{"1st": "500.00", "2nd": "300.00", "3rd": "200.00"}`

**Process**:
1. Calculate amounts from `tournament.prize_distribution` (JSONB field)
2. Call `economy.services.award()` to add funds to wallets
3. Create `PrizeTransaction` records (audit trail)
4. Use idempotency keys to prevent duplicate payouts

**Auto-Updates**:
- ❌ **Prizes NOT auto-paid on completion** (manual trigger required)
- ✅ **Idempotent**: Prevents duplicate payouts via unique constraints
- ✅ **DeltaCoin wallets updated** when payout triggered

---

## 3. Stats & History Propagation

### 3.1 Team Stats Updates

**Models**:
- `TeamAnalytics` (`apps/teams/models/analytics.py`) - Advanced stats tracking
- `TeamStats` (`apps/teams/models/stats.py`) - Legacy simple stats

**Fields Tracked**:
```python
total_matches = models.PositiveIntegerField(default=0)
matches_won = models.PositiveIntegerField(default=0)
matches_lost = models.PositiveIntegerField(default=0)
win_rate = models.DecimalField(...)
tournaments_participated = models.PositiveIntegerField(default=0)
tournaments_won = models.PositiveIntegerField(default=0)
current_streak = models.IntegerField(default=0)  # Win/loss streak
game_specific_stats = models.JSONField(default=dict)
```

**Current State**: ❌ **NOT AUTOMATICALLY UPDATED**

**Evidence**:
- No service hooks in `MatchService.confirm_result()` to update team stats
- No service hooks in `WinnerDeterminationService.determine_winner()` to increment `tournaments_won`
- `TeamAnalytics` model exists but no integration with tournament completion

**Expected Behavior** (not implemented):
- Match completion → Increment `total_matches`, `matches_won`/`matches_lost`, update `win_rate`
- Tournament completion → Increment `tournaments_participated`, `tournaments_won` (if winner)
- Streak calculation → Update `current_streak` based on last match result

**Manual Workaround**: Organizers/admins manually update team stats via admin panel

---

### 3.2 User/Player Stats Updates

**Models**: 
- No dedicated `UserStats` or `PlayerStats` model found in codebase
- `UserProfile` (`apps/user_profile/models.py`) has profile fields but no match/tournament counters

**Current State**: ❌ **NO USER STATS TRACKING IMPLEMENTED**

**Evidence**:
- Grep search for `tournament.*history|stats|match.*played` in `apps/user_profile/models/*.py` → **No matches found**
- Grep search for `update_player_stats` in `apps/tournaments/services/*.py` → **No matches found**
- TODO comment in `match_service.py` confirms this is planned but not built

**Expected Behavior** (not implemented):
- Match completion → Increment user's `matches_played`, `wins`, `losses`
- Tournament completion → Increment `tournaments_entered`, `podium_finishes`
- Track per-game stats (e.g., Valorant wins, PUBG wins separately)

---

### 3.3 Rankings & Leaderboards Updates

**Models**:
- `TeamRanking` (`apps/teams/models/ranking.py`) - Team ranking with ELO/points
- Leaderboard models in `apps/leaderboards/` (separate app)

**Team Ranking Fields** (line 394 in `ranking.py`):
```python
matches_played = models.IntegerField(default=0)
matches_won = models.IntegerField(default=0)
win_rate = models.DecimalField(...)
tournament_winner_points = models.IntegerField(default=0)
```

**Current State**: ❌ **NOT AUTOMATICALLY UPDATED**

**Evidence**:
- Grep search for `def update|def recalculate|tournament.*complete` in `apps/leaderboards/*.py` → **No matches found**
- No service integration between `WinnerDeterminationService` and ranking updates

**Expected Behavior** (not implemented):
- Tournament completion → Award points to top 3 teams
- Match win → Increment `matches_played`, `matches_won`, recalculate `win_rate`
- ELO calculation → Update team ELO rating based on opponent strength

**Leaderboards App**: Separate from tournaments, likely manual or cron-based updates (not triggered by tournament events)

---

### 3.4 Match History Tracking

**Models**:
- `TeamMatchHistory` (`apps/teams/models/analytics.py` line 333) - Per-match records

**Fields**:
```python
match_date = models.DateTimeField()
opponent_name = models.CharField(max_length=200)
result = models.CharField(choices=[('win', 'Win'), ('loss', 'Loss'), ('draw', 'Draw')])
score = models.CharField(max_length=50)
tournament_name = models.CharField(max_length=200)
game = models.CharField(max_length=50)
```

**Current State**: ❌ **NOT AUTOMATICALLY CREATED**

**Evidence**: No service calls to create `TeamMatchHistory` records in `MatchService.confirm_result()`

**Expected Behavior** (not implemented):
- Match completion → Create `TeamMatchHistory` entry for both teams
- Store opponent, result, score, tournament name
- Link to original `Match` record (if ForeignKey added)

---

## 4. Manual vs Automatic Updates Summary

### 4.1 Fully Automated

| Action | Trigger | Auto-Updates |
|--------|---------|--------------|
| DeltaCoin Payment | Registration submission | ✅ Wallet deducted, Payment created, Registration confirmed |
| Match Result Confirmation | Opponent confirms score | ✅ Match status → COMPLETED, Winner advances in bracket |
| Bracket Progression | Match completion | ✅ Winner moved to next round, Loser eliminated |
| WebSocket Broadcasts | Match/tournament state changes | ✅ Real-time events sent to spectators |
| Winner Determination | Organizer triggers | ✅ TournamentResult created, Tournament.status → COMPLETED |

### 4.2 Partially Automated (Requires Manual Trigger)

| Action | Trigger | Auto-Updates | Manual Step |
|--------|---------|--------------|-------------|
| Manual Payment Verification | Organizer approves | ✅ Payment.status → VERIFIED | Organizer clicks "Verify Payment" |
| Bracket Generation | Organizer clicks button | ✅ All matches created | Must manually trigger after registration closes |
| Certificate Generation | Organizer triggers | ✅ PDF/PNG created with QR code | Must manually generate for each participant |
| Prize Payouts | Organizer triggers | ✅ Wallets credited via EconomyService | Must manually process payouts |

### 4.3 Not Automated (Manual Only)

| Feature | Current State | Expected Behavior |
|---------|---------------|-------------------|
| Team Stats Updates | ❌ No automation | Match completion should increment wins/losses/matches_played |
| User Stats Tracking | ❌ Not implemented | No user-level stats exist in codebase |
| Team Match History | ❌ Not created | Match completion should create TeamMatchHistory records |
| Tournament Participation Count | ❌ Not incremented | Tournament registration should increment user.tournaments_entered |
| Rankings/Leaderboard Updates | ❌ No integration | Tournament completion should award ranking points |
| ELO Rating Calculation | ❌ Not implemented | Match results should update team ELO ratings |

---

## 5. Integration Points & Dependencies

### 5.1 Cross-App Dependencies

**Tournament → Economy Integration**:
- ✅ DeltaCoin payments: `PaymentService.process_deltacoin_payment()` calls `economy.services.award()`
- ✅ Prize payouts: `PayoutService.process_payouts()` calls `economy.services.award()`
- ✅ Uses IntegerField references (no ForeignKeys) for loose coupling

**Tournament → Teams Integration**:
- ⚠️ **Loose coupling**: `Registration.team_id` is IntegerField (not ForeignKey)
- ❌ **No stats sync**: Team wins/losses not updated on match completion
- ❌ **No ranking updates**: Team rankings not updated on tournament completion

**Tournament → User Profile Integration**:
- ✅ Auto-fill: `RegistrationAutoFillService` reads `UserProfile` fields
- ❌ **No stats write-back**: User profile not updated with tournament results

**Tournament → Leaderboards Integration**:
- ❌ **No integration found**: Separate app, likely independent data source

### 5.2 Service-to-Service Calls

**Working Integrations**:
1. `MatchService.confirm_result()` → `BracketService.update_bracket_after_match()` ✅
2. `PaymentService.process_deltacoin_payment()` → `economy.services.award()` ✅
3. `PayoutService.process_payouts()` → `economy.services.award()` ✅
4. `MatchService` → `broadcast_match_completed()` (WebSocket) ✅

**Missing Integrations**:
1. `MatchService.confirm_result()` → `TeamStatsService.update_stats()` ❌ (does not exist)
2. `WinnerDeterminationService.determine_winner()` → `RankingService.award_points()` ❌ (does not exist)
3. `RegistrationService.register_participant()` → `UserProfile.increment_tournaments()` ❌ (field does not exist)

---

## 6. Incomplete Features & Technical Debt

### 6.1 TODO Comments in Production Code

**From `match_service.py` line 482-483**:
```python
# TODO: Award DeltaCoin for win (Module 2.x - EconomyService)
# TODO: Update player stats (Module 2.x - AnalyticsService)
```

**From `match_service.py` line 198** (check-in):
```python
# TODO: Send notification to participants (Module 2.x)
# TODO: WebSocket broadcast: match created (ADR-007)
```

**From `match_service.py` line 256** (match created):
```python
# TODO: Send notification to participants (Module 2.x)
# TODO: WebSocket broadcast: match created (ADR-007)
```

**Interpretation**: Core stat tracking and economy rewards deferred to "Module 2.x" (future phase)

### 6.2 Missing Models

1. **UserStats** - No global user stats tracking (only team-level analytics exists)
2. **TournamentParticipation** - No dedicated model linking users to tournament history
3. **PlayerMatchHistory** - Only `TeamMatchHistory` exists, no individual player tracking

### 6.3 Missing Services

1. **TeamStatsService** - No service to update `TeamAnalytics` on match completion
2. **RankingService** - No service to update team rankings on tournament completion
3. **AnalyticsService** - Referenced in TODO comments but not implemented
4. **UserHistoryService** - No service to track user tournament participation

---

## 7. Lifecycle Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│ STAGE 1: CREATION (MANUAL)                                      │
│  - Organizer creates tournament via admin panel                 │
│  - Status: DRAFT → PUBLISHED → REGISTRATION_OPEN               │
│  - Auto-updates: None                                           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│ STAGE 2: REGISTRATION (SEMI-AUTOMATIC)                          │
│  - Users submit registrations                                   │
│  - DeltaCoin payments auto-verified ✅                          │
│  - Manual payments require organizer approval ❌                │
│  - Auto-updates: Registration records, Payment records          │
│  - Missing: User tournament count, team participation tracking  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│ STAGE 3: BRACKET GENERATION (MANUAL TRIGGER)                    │
│  - Organizer clicks "Generate Bracket"                          │
│  - All Match records created ✅                                 │
│  - Participants seeded into bracket ✅                          │
│  - Auto-updates: Match records with state SCHEDULED             │
│  - Missing: Auto-generation on registration close               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│ STAGE 4: MATCHES (AUTOMATIC PROGRESSION)                        │
│  - Check-in → Ready → Live → Pending → Completed ✅             │
│  - Winner advances in bracket ✅                                │
│  - WebSocket real-time updates ✅                               │
│  - Auto-updates: Match status, bracket tree                     │
│  - Missing: Team stats, user stats, match history, DeltaCoin    │
│          rewards, player analytics                              │
└───────────────────────┬─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│ STAGE 5: COMPLETION (MANUAL TRIGGER)                            │
│  - Organizer clicks "Determine Winner"                          │
│  - TournamentResult created ✅                                  │
│  - Tournament.status → COMPLETED ✅                             │
│  - WebSocket broadcast ✅                                       │
│  - Auto-updates: TournamentResult record                        │
│  - Missing: Team tournament count, rankings, leaderboards       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│ STAGE 6: REWARDS (MANUAL TRIGGER)                               │
│  - Organizer generates certificates (per participant) ❌        │
│  - Organizer processes prize payouts ❌                         │
│  - Auto-updates: Certificate PDFs, wallet transactions          │
│  - Missing: Auto-generation, bulk certificate creation          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Key Findings

### 8.1 What Works Well
1. ✅ **Match lifecycle automation**: Check-in → Live → Result → Bracket progression fully automated
2. ✅ **Payment integration**: DeltaCoin payments auto-verified via EconomyService
3. ✅ **Real-time updates**: WebSocket broadcasts for match/tournament events
4. ✅ **Idempotency**: Winner determination, certificates, payouts prevent duplicates
5. ✅ **Atomic transactions**: Tournament completion + result creation in single transaction

### 8.2 What's Missing
1. ❌ **Team stats sync**: Match results don't update `TeamAnalytics.matches_won`, `win_rate`, etc.
2. ❌ **User stats tracking**: No global user stats model or tracking system
3. ❌ **Match history**: `TeamMatchHistory` model exists but never populated
4. ❌ **Rankings integration**: Tournament completion doesn't award ranking points
5. ❌ **Leaderboards sync**: No connection between tournament results and leaderboards app
6. ❌ **Auto-certificates**: Must manually generate for each participant (no bulk action)
7. ❌ **Auto-payouts**: Must manually trigger prize distribution
8. ❌ **DeltaCoin match rewards**: TODO in code, not implemented

### 8.3 Manual Workarounds
- Organizers manually update team stats via admin panel after tournaments
- Leaderboards likely updated via scheduled jobs or manual triggers
- Certificates generated one-by-one (no batch generation)
- Prize payouts triggered manually after verifying tournament integrity

---

**End of Part 5: Tournament Lifecycle & Result Propagation**

**Next**: Part 6 - Recommendations & Modernization Roadmap
