# Cross-App Integration Audit

**Date:** December 7, 2025  
**Auditor:** GitHub Copilot  
**Scope:** Integration patterns between tournaments, games, teams, users, and economy apps  
**Purpose:** Map cross-app dependencies to inform TournamentOps app design

---

## Executive Summary

The DeltaCrown platform demonstrates **progressive evolution** from hardcoded legacy patterns to modern service-oriented architecture. The tournaments app sits at the intersection of games, teams, users, and economy apps, creating a **complex web of dependencies** with both modern (GameService, economy.services) and legacy (direct model imports, hardcoded logic) integration patterns.

**Critical Finding:** The tournaments app exhibits **dual personality disorder** — simultaneously using:
- ✅ Modern apps.games.Game model + GameService (partial)
- ❌ Legacy tournaments.Game model with hardcoded slug logic
- ✅ Modern economy.services integration
- ⚠️ Direct Team/TeamMembership model imports (tight coupling)

**Opportunity:** A well-designed TournamentOps app can act as **orchestration layer** to standardize these integrations and eliminate legacy patterns.

---

## 1. Overview of Major Apps

### 1.1 apps/games — Game Configuration Hub

**Purpose:** Single source of truth for game configuration, replacing hardcoded game logic.

**Core Models:**
- `Game` — Master game registry (Valorant, CS2, MLBB, PUBG Mobile, etc.)
- `GameRosterConfig` — Team composition rules (min/max players, roles, substitutes)
- `GamePlayerIdentityConfig` — Profile field mapping (riot_id, steam_id, pubg_mobile_id)
- `GameTournamentConfig` — Tournament-specific settings (formats, scoring, tiebreakers)
- `GameRole` — Game-specific roles (Duelist, Controller, Sentinel for Valorant)

**Service Layer:**
- `GameService` / `game_service` — Central API for game operations
  - `get_game(slug)` → Fetch game by slug
  - `list_active_games()` → All active games
  - `normalize_slug(code)` → Convert legacy codes (PUBGM → pubg-mobile)
  - `get_roster_config(game)` → Roster rules
  - `get_tournament_config(game)` → Tournament settings
  - `get_identity_validation_rules(game)` → Profile field mapping

**Status:** ✅ **Modern, well-designed** — Ready for use as single source of truth

---

### 1.2 apps/tournaments — Tournament Management Engine

**Purpose:** Complete tournament lifecycle from creation → registration → brackets → matches → results.

**Core Models:**
- `Tournament` — Tournament entity (⚠️ references legacy Game model)
- `Registration` — Participant registration (user or team_id IntegerField)
- `Bracket`, `BracketNode` — Tournament bracket structure
- `Match`, `Dispute` — Match management with state machine
- `Group`, `GroupStanding` — Group stage support
- `Payment`, `PaymentVerification` — Entry fee processing
- `TournamentResult`, `PrizeTransaction`, `Certificate` — Post-tournament

**Service Layer:** 37+ service modules (see TOURNAMENT_CURRENT_IMPLEMENTATION_AUDIT.md)

**Status:** ⚠️ **Feature-rich but architecturally fragmented** — Needs modernization

---

### 1.3 apps/teams — Team Management System

**Purpose:** Team roster management, rankings, social features, tournament integration.

**Core Models:**
- `Team` — Team entity (uses game slug CharField, not ForeignKey)
- `TeamMembership` — Roster management (OWNER, CAPTAIN, MANAGER, PLAYER, SUB)
- `TeamInvite`, `TeamJoinRequest` — Recruitment workflow
- `TeamRankingHistory`, `TeamRankingBreakdown` — Points-based ranking system
- `TeamAnalytics`, `PlayerStats`, `MatchRecord` — Performance tracking
- `TeamTournamentRegistration`, `TournamentParticipation` — Tournament integration models
- **Game-specific models:** ValorantTeam, CS2Team, Dota2Team, etc. (new architecture)

**Service Layer:**
- `TeamRankingService` / `ranking_service` — Ranking calculations
- `AnalyticsCalculator` — Performance metrics
- Team chat, discussions, sponsorship services

**Status:** ✅ **Recently modernized** with game-specific team models and comprehensive ranking system

---

### 1.4 apps/accounts & apps/user_profile — User Identity

**Purpose:** User authentication and profile management.

**Core Models:**
- `accounts.User` — Django auth user (username, email, password)
- `user_profile.UserProfile` — Extended profile with game IDs:
  - `riot_id`, `steam_id`, `pubg_mobile_id`, `mlbb_id`, `free_fire_id`, etc.
  - `avatar`, `banner`, `bio`
  - `region`, `country`, `language`

**Status:** ✅ **Stable** — UserProfile stores game-specific identity fields

---

### 1.5 apps/economy — Virtual Currency System

**Purpose:** DeltaCoin wallet management, transactions, prize payouts.

**Core Models:**
- `DeltaCrownWallet` — User wallet with balance tracking
  - `cached_balance` — Current balance
  - `pending_balance` — Locked for withdrawals
  - `lifetime_earnings` — Historical earnings
  - Bangladesh payment integration (bKash, Nagad, Rocket)
- `DeltaCrownTransaction` — Immutable transaction ledger

**Service Layer:**
- `economy.services` — Core wallet operations:
  - `credit(profile, amount, reason, idempotency_key)` → Add funds
  - `debit(profile, amount, reason, idempotency_key)` → Remove funds
  - `transfer(from, to, amount, reason)` → Transfer between wallets
  - `get_balance(profile)` → Query balance
  - `award(profile, amount, reason)` → **Deprecated tournament integration**

**Status:** ✅ **Well-designed** with idempotency guarantees and transaction safety

---

## 2. Tournaments ↔ Games Integration

### 2.1 Direct Dependencies

#### **Legacy Game Model (⚠️ Problem)**

**tournaments.models.tournament.Game:**
- Defined in `apps/tournaments/models/tournament.py` (lines 1-150)
- Duplicates functionality of `apps.games.Game`
- Still used by Tournament model: `game = models.ForeignKey('Game', ...)`

**Evidence:**
```python
# apps/tournaments/models/tournament.py
class Tournament(SoftDeleteModel, TimestampedModel):
    game = models.ForeignKey(
        'Game',  # ⚠️ References tournaments.Game, NOT apps.games.Game
        on_delete=models.PROTECT,
        related_name='tournaments',
    )
```

**Impact:** Two sources of truth for game data, impossible to fully leverage apps.games features.

---

#### **GameService Integration (✅ Partial Success)**

**50+ references found** to `apps.games.services.game_service` in tournaments code:

**admin.py (line 34-35):**
```python
from apps.games.services import game_service
from apps.games.models import Game
```

**Views using GameService:**
- `views/main.py` (lines 27, 167, 239-240)
- `views/registration.py` (lines 255-257, 384-386)
- `views/registration_wizard.py` (line 31, 469)
- `views/group_stage.py` (lines 273-274, 291, 295)
- `views/spectator.py` (lines 78-79)

**Common Patterns:**
```python
# Pattern 1: Normalize slug and fetch game
canonical_slug = game_service.normalize_slug(tournament.game.slug)
game_spec = game_service.get_game(canonical_slug)

# Pattern 2: Get active games for filters
all_games = game_service.list_active_games()

# Pattern 3: Get tournament config
tournament_config = game_service.get_tournament_config(tournament.game)

# Pattern 4: Get identity validation rules
identity_configs = game_service.get_identity_validation_rules(tournament.game)
```

**Assessment:** GameService usage is **increasing but inconsistent**. Some areas use it, others don't.

---

### 2.2 Hardcoded Game Logic (❌ Legacy Pattern)

**Location: registration_wizard.py (lines 479-491)**
```python
# Legacy hardcoded mapping (backward compatibility)
if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id or ''
elif game_slug == 'pubg-mobile':
    auto_filled['game_id'] = profile.pubg_mobile_id or ''
elif game_slug == 'mobile-legends':
    auto_filled['game_id'] = profile.mlbb_id or ''
elif game_slug == 'free-fire':
    auto_filled['game_id'] = profile.free_fire_id or ''
elif game_slug == 'cod-mobile':
    auto_filled['game_id'] = profile.codm_uid or ''
elif game_slug == 'dota-2' or game_slug == 'cs2':
    auto_filled['game_id'] = profile.steam_id or ''
elif game_slug == 'efootball' or game_slug == 'ea-fc':
    auto_filled['game_id'] = profile.efootball_id or profile.ea_id or ''
```

**Problem:** Should use `GamePlayerIdentityConfig` from apps.games instead.

**Modern Approach (already partially implemented):**
```python
identity_configs = game_service.get_identity_validation_rules(tournament.game)
for config in identity_configs:
    if hasattr(profile, config.field_name):
        auto_filled['game_id'] = getattr(profile, config.field_name, '') or ''
        if auto_filled['game_id']:
            break
```

---

**Location: leaderboard.py (lines 107-111)**
```python
from apps.games.services import game_service
game_slug = game_service.normalize_slug(tournament.game.slug)
if game_slug == 'free-fire':
    points = calc_ff_points(kills, placement)
elif game_slug == 'pubg-mobile':
    points = calc_pubgm_points(kills, placement)
```

**Problem:** Point calculations hardcoded in `tournaments/games/points.py` instead of stored in `GameTournamentConfig`.

---

**Location: templates/tournaments/detailPages/detail.html (lines 14-67)**
```django
{% if game_spec.slug == 'valorant' %}
    <div class="... from-red-950/40 ..."></div>
{% elif game_spec.slug == 'cs2' or game_spec.slug == 'csgo' %}
    <div class="... from-orange-950/40 ..."></div>
{% elif game_spec.slug == 'mlbb' or game_spec.slug == 'mobile_legends' %}
    <div class="... from-blue-950/40 ..."></div>
...
{% endif %}
```

**Problem:** Should use `game_spec.primary_color` and `game_spec.secondary_color` from apps.games.Game model.

---

### 2.3 What Works Well

✅ **GameService.normalize_slug()** — Used throughout to handle legacy codes:
- PUBGM → pubg-mobile
- CODM → call-of-duty-mobile
- MLBB → mobile-legends

✅ **GameService.list_active_games()** — Used in admin and views for dropdowns

✅ **GameService.get_tournament_config()** — Used in group_stage_service.py for scoring rules

---

### 2.4 What Needs Fixing

❌ **Tournament.game ForeignKey** — Points to tournaments.Game instead of apps.games.Game

❌ **Profile field mapping** — Hardcoded game slug checks instead of GamePlayerIdentityConfig

❌ **Point calculations** — Hardcoded in tournaments/games/points.py instead of GameTournamentConfig

❌ **Template branding** — Hardcoded colors by slug instead of Game.primary_color

---

## 3. Tournaments ↔ Teams Integration

### 3.1 Team Registration Pattern

**Model Structure:**
```python
# apps/tournaments/models/registration.py
class Registration(SoftDeleteModel, TimestampedModel):
    user = models.ForeignKey('accounts.User', null=True, blank=True)
    team_id = models.IntegerField(  # ⚠️ IntegerField, not ForeignKey
        null=True,
        blank=True,
        db_index=True,
        help_text="Team ID reference"
    )
```

**Constraint:**
```python
# XOR constraint: Either user OR team_id must be set
models.CheckConstraint(
    check=(
        Q(user__isnull=False, team_id__isnull=True) |
        Q(user__isnull=True, team_id__isnull=False)
    ),
    name='registration_user_xor_team'
)
```

**Why IntegerField?**
- Avoids circular dependency between tournaments and teams apps
- Teams app can evolve independently
- No database-level cascade constraints

**Tradeoff:**
- ❌ No referential integrity enforcement
- ❌ Orphaned registrations possible if team deleted
- ❌ More complex queries (can't use select_related)
- ✅ Loose coupling between apps

---

### 3.2 Direct Team Model Imports (⚠️ Tight Coupling)

**50+ references found** to `apps.teams.models`:

**Service Layer:**
- `registration_service.py` (line 274): `from apps.teams.models import TeamMembership, Team`
- `registration_eligibility.py` (line 10): `from apps.teams.models import Team, TeamMembership`
- `eligibility_service.py` (line 17): `from apps.teams.models import Team, TeamMembership`
- `checkin_service.py` (line 353): `from apps.teams.models import TeamMembership`
- `lobby_service.py` (line 155): `from apps.teams.models import Team, TeamMembership`

**Common Usage Pattern:**
```python
from apps.teams.models import Team, TeamMembership

# Check if user can register team
membership = TeamMembership.objects.filter(
    team_id=team_id,
    profile__user=user,
    status=TeamMembership.Status.ACTIVE
).first()

if membership.role in [
    TeamMembership.Role.OWNER,
    TeamMembership.Role.MANAGER,
    TeamMembership.Role.CAPTAIN
]:
    # Allow registration
```

**Assessment:** **Direct model imports create tight coupling**. Should use TeamService abstraction.

---

### 3.3 TeamMembership Role Checks

**Tournaments code assumes TeamMembership.Role structure:**
- `OWNER` — Team owner (can register for tournaments)
- `CAPTAIN` — Legacy support
- `MANAGER` — Can manage team
- `PLAYER` — Regular player
- `SUB` — Substitute

**Eligibility Logic:**
```python
# registration_eligibility.py (lines 131-133)
allowed_roles = [
    TeamMembership.Role.OWNER,
    TeamMembership.Role.MANAGER,
    TeamMembership.Role.CAPTAIN,  # legacy support
]

member = TeamMembership.objects.filter(team=team, profile__user=user).first()
if not member or member.role not in allowed_roles:
    return False, "Only team owners/managers/captains can register"
```

**Problem:** Changes to teams.TeamMembership.Role enum would break tournaments code.

---

### 3.4 Match Participants (IntegerField Pattern)

**Model Structure:**
```python
# apps/tournaments/models/match.py
class Match(SoftDeleteModel, TimestampedModel):
    participant1_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Team ID or User ID for participant 1'
    )
    participant1_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Denormalized name for display'
    )
    
    participant2_id = models.PositiveIntegerField(...)
    participant2_name = models.CharField(...)
```

**Assessment:** Same IntegerField pattern as Registration. **Denormalized name** reduces queries but creates data inconsistency risk.

---

### 3.5 Team Ranking Integration

**Reference found in result.py (line 270):**
```python
from apps.teams.services.game_ranking_service import game_ranking_service
```

**Note:** File `apps/teams/services/game_ranking_service.py` does **not exist** — this is a **broken import**.

**Expected Flow:**
1. Tournament result created (Team finishes 1st, 2nd, etc.)
2. TournamentOps should call TeamRankingService to update points
3. TeamRankingBreakdown.tournament_points incremented

**Current State:** **Integration incomplete** — tournament results don't auto-update team rankings.

---

### 3.6 What Works

✅ **IntegerField pattern** — Allows teams app to evolve independently

✅ **Permission checks** — Properly validates team roles before allowing registration

---

### 3.7 What Needs Fixing

❌ **Direct model imports** — Should use TeamService abstraction layer

❌ **Broken ranking integration** — Tournament results don't update TeamRankingBreakdown

❌ **Denormalized names** — participant1_name can become stale if team renamed

❌ **No service layer** — Tournaments directly query TeamMembership instead of calling TeamService

---

## 4. Tournaments ↔ Users Integration

### 4.1 User References in Tournaments

**ForeignKey to accounts.User:**
```python
# Tournament organizer
Tournament.organizer = models.ForeignKey('accounts.User', ...)

# Registration user
Registration.user = models.ForeignKey('accounts.User', null=True, blank=True)

# Match checked_in_by
Match.checked_in_by = models.ForeignKey('accounts.User', ...)

# Payment verified_by
Payment.verified_by = models.ForeignKey('accounts.User', ...)
```

**Assessment:** ✅ **Clean ForeignKey references** — No circular dependency issues.

---

### 4.2 UserProfile Dependencies

**40+ references found** to `apps.user_profile.models.UserProfile`:

**Auto-fill Registration Data:**
```python
# registration_wizard.py (lines 432-433)
from apps.user_profile.models import UserProfile
profile = UserProfile.objects.get(user=user)

# Auto-fill game IDs
auto_filled = {
    'game_id': profile.riot_id or '',  # ⚠️ Hardcoded
    'phone': profile.phone_number or '',
    'discord': profile.discord_tag or '',
}
```

**Eligibility Checks:**
```python
# eligibility_service.py (lines 88, 196)
user_profile = UserProfile.objects.filter(user=user).first()
if not user_profile:
    return False, "User profile not found"
```

**Check-in Workflow:**
```python
# checkin_service.py (lines 354-358)
profile = UserProfile.objects.get(user=user)
membership = TeamMembership.objects.filter(
    team_id=team_id,
    profile=profile,  # TeamMembership uses profile FK
    status=TeamMembership.Status.ACTIVE
).first()
```

**Assessment:** ⚠️ **Hardcoded profile field access** — Should use GameService to get field mapping.

---

### 4.3 Profile Field Mapping (Legacy vs Modern)

**Legacy Pattern (❌):**
```python
if game_slug == 'valorant':
    game_id = profile.riot_id
elif game_slug == 'pubg-mobile':
    game_id = profile.pubg_mobile_id
```

**Modern Pattern (✅ Partial):**
```python
identity_configs = game_service.get_identity_validation_rules(tournament.game)
for config in identity_configs:
    if hasattr(profile, config.field_name):
        game_id = getattr(profile, config.field_name, '')
```

**Problem:** Modern pattern exists but is **not consistently used** throughout codebase.

---

### 4.4 User Eligibility Logic

**Registration Eligibility Checks:**
- User must have UserProfile
- User must not be banned
- User must not already be registered
- User must have required game ID populated
- User must meet age/region requirements (if configured)

**Team Registration Eligibility:**
- User must be OWNER/MANAGER/CAPTAIN of team
- Team must have minimum roster size
- Team members must have game IDs populated
- Team must not already be registered

**Assessment:** ✅ **Comprehensive eligibility checks** in `eligibility_service.py`.

---

### 4.5 What Works

✅ **Clean User ForeignKeys** — No circular dependencies

✅ **UserProfile integration** — Auto-fill registration data from profile

✅ **Eligibility service** — Centralized validation logic

---

### 4.6 What Needs Fixing

❌ **Hardcoded profile field access** — Should use GamePlayerIdentityConfig

❌ **Inconsistent modern pattern usage** — Mix of legacy and modern approaches

---

## 5. Tournaments ↔ Economy Integration

### 5.1 DeltaCoin Payment Integration (✅ Excellent)

**Service Layer:**
```python
# apps/tournaments/services/payment_service.py
from apps.economy import services as economy_services
from apps.economy.exceptions import InsufficientFunds, InvalidAmount
from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet

class PaymentService:
    @staticmethod
    def get_wallet_balance(user) -> int:
        profile = user.profile
        return economy_services.get_balance(profile)
    
    @staticmethod
    def process_deltacoin_payment(registration_id, user, idempotency_key):
        # Check balance
        balance = economy_services.get_balance(user.profile)
        if balance < amount:
            raise InsufficientFunds()
        
        # Debit wallet
        debit_result = economy_services.debit(
            profile=user.profile,
            amount=amount,
            reason=f"Tournament entry: {tournament.name}",
            idempotency_key=idempotency_key
        )
        
        # Auto-verify (no manual review needed)
        registration.status = Registration.CONFIRMED
        registration.save()
```

**Assessment:** ✅ **Excellent integration** — Uses economy.services API, not direct model access.

---

### 5.2 Entry Fee Processing

**Tournament Model:**
```python
class Tournament:
    has_entry_fee = models.BooleanField(default=False)
    entry_fee_amount = models.DecimalField(...)
    entry_fee_currency = models.CharField(...)  # BDT, USD
    entry_fee_deltacoin = models.IntegerField(default=0)
    payment_methods = ArrayField(...)  # ['deltacoin', 'bkash', 'nagad']
```

**Payment Flow:**
1. User selects payment method (DeltaCoin, bKash, Nagad, Rocket)
2. If DeltaCoin:
   - `PaymentService.process_deltacoin_payment()` → Auto-verified
3. If bKash/Nagad/Rocket:
   - User uploads payment proof
   - Organizer manually verifies
   - Payment.verification_status = 'verified'

**Registration Service Integration:**
```python
# registration_service.py (lines 476-530)
from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.economy.exceptions import InsufficientFunds

wallet = DeltaCrownWallet.objects.select_for_update().get(profile=user.profile)
if wallet.cached_balance < deltacoin_amount:
    raise InsufficientFunds("Insufficient DeltaCoin balance")

# Debit via economy.services
debit_result = economy_services.debit(...)
```

**Assessment:** ✅ **Proper integration** with transaction locking and idempotency.

---

### 5.3 Prize Payout Integration

**Service Layer:**
```python
# apps/tournaments/services/payout_service.py (lines 26-27)
from apps.economy.services import award
from apps.economy.models import DeltaCrownTransaction

class PayoutService:
    @staticmethod
    def distribute_prizes(tournament):
        # Get winners from TournamentResult
        results = TournamentResult.objects.filter(
            tournament=tournament
        ).order_by('final_placement')
        
        for result in results:
            # Calculate prize from prize_distribution
            prize_amount = calculate_prize(result.final_placement)
            
            # Award via economy.services
            award(
                profile=result.participant_profile,
                amount=prize_amount,
                reason=f"Prize: {tournament.name} - {result.placement_display}"
            )
```

**Note:** `economy.services.award()` is **deprecated** (see economy/services.py line 69-93 comments). Should use `economy.services.credit()` instead.

---

### 5.4 Refund Processing

**Cancellation Flow:**
```python
# payment_service.py (lines 264-325)
def refund_deltacoin_payment(registration_id, admin_user, reason):
    # Get original payment
    payment = Payment.objects.get(registration_id=registration_id)
    
    # Credit wallet
    credit_result = economy_services.credit(
        profile=registration.user.profile,
        amount=payment.deltacoin_amount,
        reason=f"Refund: {tournament.name}",
        idempotency_key=f"refund-{payment.id}"
    )
    
    # Update payment status
    payment.refund_status = 'refunded'
    payment.save()
```

**Assessment:** ✅ **Idempotent refund processing** with proper transaction tracking.

---

### 5.5 Wallet UI Integration

**Views:**
```python
# registration.py (lines 314-318)
from apps.economy.models import DeltaCrownWallet

try:
    wallet = DeltaCrownWallet.objects.get(user=user)
    context['wallet_balance'] = wallet.cached_balance
except DeltaCrownWallet.DoesNotExist:
    context['wallet_balance'] = 0
```

**registration_wizard.py (line 217):**
```python
from apps.tournaments.services.payment_service import PaymentService
deltacoin_check = PaymentService.can_use_deltacoin(request.user, entry_fee)
```

**Assessment:** ✅ **Clean service layer usage** — Views use PaymentService, not direct model access.

---

### 5.6 What Works Excellently

✅ **PaymentService abstraction** — Tournaments don't directly access economy models

✅ **Idempotency keys** — Prevents duplicate charges/refunds

✅ **Transaction safety** — Uses select_for_update() and @transaction.atomic

✅ **DeltaCoin auto-verification** — Reduces manual work for organizers

✅ **Refund support** — Clean cancellation workflow

---

### 5.7 Minor Issues

⚠️ **Deprecated award() function** — Should migrate to credit() API

⚠️ **Direct DeltaCrownWallet access** — Views should use PaymentService.get_wallet_balance()

---

## 6. Global Observations & Pain Points

### 6.1 What Works Well Today

#### **✅ Economy Integration (Best-in-Class)**
- Clean service abstraction (economy.services)
- Idempotency guarantees
- Transaction safety
- No direct model access from tournaments
- **Reusable pattern for TournamentOps**

#### **✅ GameService Emergence**
- Modern apps.games.Game model is solid
- GameService provides clean API
- Partial adoption in tournaments showing benefits
- **Foundation exists, needs completion**

#### **✅ Service Layer Architecture**
- Tournaments app has comprehensive service layer
- Business logic properly abstracted from views
- Transaction safety with @transaction.atomic
- **Good pattern to extend to TournamentOps**

#### **✅ User Integration**
- Clean ForeignKey references
- No circular dependencies
- Eligibility checks well-implemented

---

### 6.2 Fragile/Legacy Patterns

#### **❌ Dual Game Model Architecture (Critical)**

**Problem:**
- `apps.tournaments.models.tournament.Game` (legacy)
- `apps.games.models.Game` (modern)
- Tournament.game → ForeignKey to legacy model

**Impact:**
- Can't use GameRosterConfig, GameTournamentConfig, GamePlayerIdentityConfig
- Hardcoded logic persists because modern features unavailable
- Data duplication and sync issues

**Migration Path:**
1. Change Tournament.game ForeignKey to apps.games.Game
2. Data migration script
3. Remove legacy Game model
4. Update all imports

---

#### **❌ Hardcoded Game Logic Everywhere**

**Locations:**
- registration_wizard.py → Profile field mapping
- leaderboard.py → Point calculations
- games/points.py → BR scoring formulas
- templates → Branding colors by slug

**Problem:**
- Non-scalable (new game = code changes)
- Violates DRY principle
- Makes testing difficult

**Solution:**
- Use GamePlayerIdentityConfig for profile mapping
- Use GameTournamentConfig.scoring_rules for points
- Use Game.primary_color/secondary_color for branding

---

#### **❌ Direct Team Model Imports (Tight Coupling)**

**Problem:**
```python
from apps.teams.models import Team, TeamMembership

# Direct queries throughout tournaments services
membership = TeamMembership.objects.filter(...)
```

**Impact:**
- Changes to TeamMembership break tournaments
- Can't replace teams implementation
- Hard to test in isolation

**Solution:**
- Create TeamService abstraction
- Tournaments call TeamService.get_team_membership()
- Teams app can evolve independently

---

#### **❌ IntegerField Team References**

**Problem:**
- Registration.team_id → IntegerField
- Match.participant1_id, participant2_id → IntegerField
- No referential integrity

**Impact:**
- Orphaned records if team deleted
- Can't use select_related() for optimization
- Manual integrity checks required

**Current Status:** **Accepted tradeoff** for loose coupling

**Alternative:** GenericForeignKey or polymorphic content type

---

#### **❌ Broken Team Ranking Integration**

**Evidence:**
```python
# result.py (line 270) - BROKEN IMPORT
from apps.teams.services.game_ranking_service import game_ranking_service
```

**Problem:**
- File doesn't exist
- Tournament results don't update team rankings
- Manual recalculation required

**Solution:** TournamentOps should listen for result events and call TeamRankingService

---

#### **❌ Inconsistent Service Usage**

**Examples:**
- ✅ Economy integration → Always uses economy.services
- ⚠️ GameService integration → Sometimes used, sometimes not
- ❌ Team integration → Always direct model imports

**Impact:** Unpredictable code patterns, maintenance nightmare

---

### 6.3 Tight Coupling Blockers

**Current Dependency Graph:**
```
tournaments
    ├──> games (partial, fragmented)
    ├──> teams (tight, direct model imports)
    ├──> user_profile (tight, hardcoded fields)
    └──> economy (✅ loose, via services)
```

**Problems:**
1. Can't replace teams implementation without breaking tournaments
2. Can't add new game without code changes
3. Can't refactor UserProfile game ID fields
4. Can't deploy tournaments independently

**Desired Dependency Graph:**
```
tournaments (or TournamentOps)
    ├──> GameService (clean API)
    ├──> TeamService (clean API)
    ├──> UserProfileService (clean API)
    └──> economy.services (✅ already clean)
```

---

## 7. Opportunities for TournamentOps App

### 7.1 Architectural Vision

**TournamentOps as Orchestration Layer:**

```
┌─────────────────────────────────────────────────┐
│           TournamentOps (New App)               │
│  • Tournament creation & lifecycle              │
│  • Result validation & processing               │
│  • Standings calculation                        │
│  • Prize distribution orchestration             │
│  • Event broadcasting                           │
└─────────────────────────────────────────────────┘
           ▲                    │
           │                    ▼
    ┌──────┴────────┬──────────────────┬──────────┐
    │               │                  │          │
    ▼               ▼                  ▼          ▼
┌────────┐    ┌─────────┐    ┌──────────┐   ┌─────────┐
│ Games  │    │  Teams  │    │   User   │   │ Economy │
│Service │    │ Service │    │  Profile │   │ Service │
└────────┘    └─────────┘    │  Service │   └─────────┘
                              └──────────┘
```

**Key Principles:**
1. ✅ **Service-only integration** — No direct model imports
2. ✅ **Event-driven** — Publish events, let services subscribe
3. ✅ **Data-driven** — Use GameTournamentConfig, not hardcoded logic
4. ✅ **Stateless orchestration** — Coordinate, don't duplicate

---

### 7.2 Integration Hooks (Event-Driven)

#### **Hook 1: Tournament Result Created**

**Event:** `tournament_result_created(tournament_id, participant_id, placement)`

**TournamentOps Actions:**
1. Validate result completeness
2. Calculate standings (using GameTournamentConfig scoring rules)
3. **Call TeamRankingService.update_tournament_points(team_id, points)**
4. **Call economy.services.credit() for prize distribution**
5. Generate certificates
6. Broadcast result to WebSocket subscribers
7. Send notifications

**Services Involved:**
- GameService → Get scoring rules
- TeamRankingService → Update team points
- economy.services → Distribute prizes
- notifications → Send alerts

---

#### **Hook 2: Tournament Registration**

**Event:** `tournament_registration_created(tournament_id, user_id, team_id)`

**TournamentOps Actions:**
1. **Call GameService.get_identity_validation_rules()** → Validate game IDs
2. **Call TeamService.validate_roster()** → Check team eligibility
3. Auto-fill from UserProfile (via GamePlayerIdentityConfig)
4. Assign slot number
5. Update tournament participant count
6. Broadcast to lobby WebSocket

**Services Involved:**
- GameService → Identity validation
- TeamService → Roster validation
- UserProfileService → Auto-fill data

---

#### **Hook 3: Match Result Submission**

**Event:** `match_result_submitted(match_id, winner_id, loser_id, scores)`

**TournamentOps Actions:**
1. Validate result (using GameTournamentConfig)
2. Update match state: PENDING_RESULT → COMPLETED
3. **Call BracketService.advance_winner(winner_id)**
4. Update group standings (if group stage)
5. **Call TeamAnalytics.record_match()** → Update team stats
6. Broadcast to spectators
7. Send notifications to participants

**Services Involved:**
- GameService → Result validation rules
- BracketService → Bracket progression
- TeamAnalytics → Performance tracking

---

#### **Hook 4: Payment Processed**

**Event:** `payment_verified(registration_id, amount, method)`

**TournamentOps Actions:**
1. Update registration status: PAYMENT_SUBMITTED → CONFIRMED
2. Assign bracket slot (if slots full, trigger bracket generation)
3. Send confirmation notification
4. Update tournament revenue tracking

**Services Involved:**
- economy.services → Already called by PaymentService
- notifications → Send confirmation

---

#### **Hook 5: Tournament Completion**

**Event:** `tournament_completed(tournament_id)`

**TournamentOps Actions:**
1. Finalize all results
2. **Call PayoutService.distribute_prizes()** → economy.services.credit()
3. **Call CertificateService.generate_all()** → Winner, runner-up, participation
4. **Call TeamRankingService.recalculate_affected_teams()** → Bulk update
5. Archive tournament data
6. Send completion notifications

**Services Involved:**
- economy.services → Prize distribution
- TeamRankingService → Ranking updates
- CertificateService → Achievement proofs

---

### 7.3 Recommended Service Abstractions

#### **GameService (Already Exists ✅)**

**Methods to leverage:**
- `get_game(slug)` → Fetch game config
- `get_roster_config(game)` → Team composition rules
- `get_tournament_config(game)` → Scoring, formats, tiebreakers
- `get_identity_validation_rules(game)` → Profile field mapping
- `normalize_slug(code)` → Legacy code handling

**TournamentOps Usage:**
```python
from apps.games.services import game_service

# Get scoring rules
config = game_service.get_tournament_config(tournament.game)
scoring_rules = config.scoring_rules  # JSONB

# Get identity fields
identity_fields = game_service.get_identity_validation_rules(tournament.game)
```

---

#### **TeamService (Needs Creation ⚠️)**

**Proposed API:**
```python
from apps.teams.services import team_service

# Get team with members
team = team_service.get_team(team_id)

# Validate roster eligibility
is_eligible, message = team_service.validate_tournament_eligibility(
    team_id=team_id,
    tournament_id=tournament_id,
    min_players=5,
    max_players=10
)

# Get team captain/owner
captain = team_service.get_team_captain(team_id)

# Check user permission
can_register = team_service.can_user_register_team(
    user_id=user_id,
    team_id=team_id
)

# Record match result
team_service.record_match_result(
    team_id=team_id,
    opponent_team_id=opponent_id,
    result='win',
    score='13-11'
)
```

**TournamentOps Usage:**
```python
# Check eligibility
is_eligible, msg = team_service.validate_tournament_eligibility(
    team_id=registration.team_id,
    tournament_id=tournament.id,
    min_players=tournament.min_team_size,
    max_players=tournament.max_team_size
)

if not is_eligible:
    raise ValidationError(msg)
```

---

#### **UserProfileService (Needs Creation ⚠️)**

**Proposed API:**
```python
from apps.user_profile.services import user_profile_service

# Get game ID for user
game_id = user_profile_service.get_game_identity(
    user=user,
    game=game  # apps.games.Game instance
)

# Auto-fill registration data
auto_fill = user_profile_service.get_registration_autofill(
    user=user,
    game=game
)
# Returns: {'game_id': '...', 'phone': '...', 'discord': '...'}

# Validate game ID format
is_valid = user_profile_service.validate_game_identity(
    game_id='Player#TAG',
    game=game
)
```

**TournamentOps Usage:**
```python
# Auto-fill registration
auto_fill = user_profile_service.get_registration_autofill(
    user=request.user,
    game=tournament.game
)

registration_data = {
    **auto_fill,
    **user_provided_data  # User overrides
}
```

---

### 7.4 Event Publishing System

**Proposed Event Bus:**
```python
from apps.tournament_ops.events import tournament_events

# Publish event
tournament_events.publish(
    event_type='tournament_result_created',
    tournament_id=tournament.id,
    participant_id=participant_id,
    placement=1,
    prize_amount=5000
)

# Subscribers (in respective apps)
@tournament_events.subscribe('tournament_result_created')
def update_team_ranking(event):
    team_id = event['participant_id']
    placement = event['placement']
    
    # Calculate points
    points = calculate_placement_points(placement)
    
    # Update team ranking
    TeamRankingService.add_tournament_points(
        team_id=team_id,
        tournament_id=event['tournament_id'],
        points=points
    )
```

**Benefits:**
- ✅ Loose coupling — Apps don't depend on each other
- ✅ Extensible — New subscribers can be added
- ✅ Testable — Can mock event bus
- ✅ Auditable — All events logged

---

### 7.5 Data-Driven Configuration

**Replace hardcoded logic with config:**

**Before (❌):**
```python
if game_slug == 'valorant':
    game_id = profile.riot_id
elif game_slug == 'pubg-mobile':
    game_id = profile.pubg_mobile_id
```

**After (✅):**
```python
game_id = user_profile_service.get_game_identity(user, game)
```

**Before (❌):**
```python
if game_slug == 'free-fire':
    points = kills + placement_bonus_ff[placement]
elif game_slug == 'pubg-mobile':
    points = kills + placement_bonus_pubgm[placement]
```

**After (✅):**
```python
scoring_rules = game_service.get_tournament_config(game).scoring_rules
points = calculate_points(kills, placement, scoring_rules)
```

---

## 8. Summary & Recommendations

### 8.1 Current State

**Strengths:**
- ✅ Economy integration is excellent (model for others)
- ✅ GameService exists and is partially adopted
- ✅ Service layer architecture in place
- ✅ Comprehensive feature coverage

**Weaknesses:**
- ❌ Dual Game model architecture
- ❌ Hardcoded game logic throughout
- ❌ Direct Team model imports (tight coupling)
- ❌ Broken team ranking integration
- ❌ Inconsistent service usage patterns

---

### 8.2 Critical Path for TournamentOps

**Phase 1: Foundation (Before TournamentOps)**
1. ✅ Migrate Tournament.game to apps.games.Game
2. ✅ Create TeamService abstraction
3. ✅ Create UserProfileService abstraction
4. ✅ Remove hardcoded game logic
5. ✅ Fix team ranking integration

**Phase 2: TournamentOps Core**
1. Create TournamentOps app with clean service-only integration
2. Implement event publishing system
3. Build orchestration layer for result processing
4. Migrate prize distribution to event-driven model
5. Migrate standings calculation to data-driven config

**Phase 3: Migration**
1. Move tournament creation to TournamentOps
2. Move result processing to TournamentOps
3. Deprecate legacy tournaments app services
4. Update all integration points
5. Remove legacy code

---

### 8.3 Key Integration Principles

**For TournamentOps App:**

1. **Service-Only Integration**
   - ✅ Use GameService, TeamService, UserProfileService, economy.services
   - ❌ Never import models from other apps

2. **Event-Driven Architecture**
   - ✅ Publish events for all state changes
   - ✅ Let services subscribe and react
   - ❌ Don't call other app services synchronously (except read operations)

3. **Data-Driven Configuration**
   - ✅ Use GameTournamentConfig for all game-specific logic
   - ✅ Use GameRosterConfig for team validation
   - ❌ No hardcoded game slug checks

4. **Idempotency & Transaction Safety**
   - ✅ Use idempotency keys for all financial operations
   - ✅ Wrap multi-step operations in @transaction.atomic
   - ✅ Follow economy.services patterns

5. **Loose Coupling**
   - ✅ Apps can evolve independently
   - ✅ Interfaces over implementations
   - ✅ IntegerField team_id pattern acceptable for now

---

### 8.4 Integration Checklist

**Before building TournamentOps:**

- [ ] Migrate Tournament.game to apps.games.Game
- [ ] Remove legacy tournaments.Game model
- [ ] Create TeamService with clean API
- [ ] Create UserProfileService with clean API
- [ ] Replace all hardcoded game slug checks with GameService calls
- [ ] Fix broken team ranking integration
- [ ] Document event schema for tournament lifecycle
- [ ] Define service API contracts
- [ ] Write integration tests for cross-app flows

**During TournamentOps development:**

- [ ] Use only service layer APIs (no direct model imports)
- [ ] Implement event publishing for all state changes
- [ ] Use GameTournamentConfig for all scoring/validation
- [ ] Follow economy.services patterns for payments
- [ ] Build comprehensive integration tests
- [ ] Document all integration points
- [ ] Create migration guide for legacy tournaments code

---

**End of Cross-App Integration Audit**

**Next Steps:**
1. Review this audit with stakeholders
2. Prioritize Phase 1 fixes (Game model migration, service abstractions)
3. Design TournamentOps service API
4. Define event schema
5. Begin implementation

**Key Takeaway:** The foundation for excellent cross-app integration exists (economy.services, GameService), but needs **systematic completion and standardization** before TournamentOps can be built correctly.
