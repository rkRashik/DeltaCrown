# Stable Apps Contract — What Tournaments Can Use

*This document is the "API contract." Every method listed here is what the tournament system is allowed to call. Do NOT import models directly — use these services/functions.*

*Updated: February 14, 2026*

---

## apps.games — Game Configuration

### GameService (singleton: `game_service`)
```python
from apps.games.services import game_service

game_service.get_game(slug: str) → Game
game_service.get_game_by_id(id: int) → Game
game_service.list_active_games() → QuerySet[Game]
game_service.list_featured_games() → QuerySet[Game]
game_service.get_roster_config(game: Game) → GameRosterConfig
game_service.get_roster_limits(game: Game) → dict  # {min_team, max_team, min_subs, max_subs}
game_service.validate_roster_size(game: Game, players: int, subs: int) → bool
game_service.get_choices() → list[tuple]  # (id, display_name)
```

### GameRulesEngine
```python
from apps.games.services import GameRulesEngine

engine = GameRulesEngine()
engine.score_match(game_slug, match_payload) → dict
engine.determine_winner(game_slug, match_payload) → dict  # {winner_id, reason}
engine.validate_result_schema(game_slug, match_payload) → ValidationResult
```

### GameValidationService
```python
from apps.games.services import GameValidationService

validator = GameValidationService()
validator.validate_identity(game_slug, identity_payload) → ValidationResult
validator.validate_registration(game_slug, user_dto, team_dto, config) → EligibilityResultDTO
validator.validate_match_result(game_slug, match_payload) → ValidationResult
```

### Key Models (READ via adapters only)
- `Game` — name, slug, primary_color, game_type, category, platforms
- `GameTournamentConfig` — bracket formats, scoring, check-in config, identity requirements
- `GameRosterConfig` — team sizes, substitute limits, role requirements
- `GamePlayerIdentityConfig` — required identity fields per game
- `GameMatchResultSchema` — match result payload validation
- `GameScoringRule` — scoring configuration
- `GameRole` — game-specific player roles

---

## apps.organizations — Teams

### TeamService
```python
from apps.organizations.services import TeamService

ts = TeamService()
ts.get_team_identity(team_id: int) → TeamIdentity  # name, tag, logo, game_id, status
ts.validate_roster(team_id, tournament_id, game_id) → ValidationResult
ts.get_wallet_info(team_id) → WalletInfo
ts.list_roster(team_id) → list[RosterMember]
```

### Tournament Helper Functions
```python
from apps.organizations.adapters.tournament_helpers import (
    get_team_url_for_tournament,
    validate_team_roster_for_tournament,
    get_team_identity_for_tournament,
)
```

### Key Models (READ via adapters only)
- `Team` — name, slug, tag, game_id, region, status, organization FK
- `TeamMembership` — user, team, role (OWNER/PLAYER/SUB/etc.), roster_slot, is_tournament_captain
- `Organization` — name, slug, is_verified

---

## apps.economy — Wallet & Payments

### Service Functions
```python
from apps.economy.services import wallet_for, award, award_placements

wallet = wallet_for(profile: UserProfile) → DeltaCrownWallet
# cached_balance, pending_balance, lifetime_earnings

award(profile, amount, reason, tournament=None, registration=None, idempotency_key=None) → DeltaCrownTransaction
# amount > 0 = credit, amount < 0 = debit
# reason: one of DeltaCrownTransaction.Reason (ENTRY_FEE_DEBIT, WINNER, RUNNER_UP, TOP4, PARTICIPATION, REFUND, MANUAL_ADJUST)

award_placements(tournament) → list[DeltaCrownTransaction]
# Reads CoinPolicy for the tournament and distributes prizes automatically
```

### Key Models (READ via adapters only)
- `DeltaCrownWallet` — 1:1 UserProfile, cached_balance
- `DeltaCrownTransaction` — immutable ledger line, amount, reason, idempotency_key
- `CoinPolicy` — per-tournament payout amounts

---

## apps.notifications — Notification Delivery

### Core Function
```python
from apps.notifications.services import notify

notify(
    recipients: list[User],       # Who to notify
    event: str,                   # e.g. 'REG_CONFIRMED', 'MATCH_SCHEDULED'
    title: str,                   # Notification title
    body: str,                    # Notification body
    url: str = None,              # Link to relevant page
    tournament_id: int = None,    # Tournament context
    match_id: int = None,         # Match context
    category: str = 'tournaments', # Category for filtering
    bypass_user_prefs: bool = False,
)
```

### Available Notification Types
```
REG_CONFIRMED, BRACKET_READY, MATCH_SCHEDULED, RESULT_VERIFIED,
CHECKIN_OPEN, MATCH_RESULT, INVITE_SENT, INVITE_ACCEPTED,
ROSTER_CHANGED, TOURNAMENT_REGISTERED, RANKING_CHANGED,
PAYOUT_RECEIVED, DISPUTE_OPENED, DISPUTE_RESOLVED
```

---

## apps.user_profile — Player Identity

### GameProfile Model (via adapter)
```python
# Used through UserAdapter, not directly
GameProfile.objects.filter(user=user, game=game).first()
# Fields: ign, discriminator, in_game_name, identity_key, 
#         rank_name, rank_tier, platform, region, verification_status
```

### UserProfile Key Fields (via adapter)
```python
profile.primary_team_id  # FK to organizations.Team
profile.primary_game_id  # FK to games.Game
profile.kyc_status       # for prize eligibility
profile.reputation_score # for fair play requirements
profile.skill_rating     # for ELO-based seeding
profile.is_16_plus       # age verification
profile.region           # for region locking
```

### GamePassportSchema (via adapter)
```python
# Defines what identity fields a game requires
GamePassportSchema.objects.get(game=game)
# Fields: identity_fields (JSON), rank_choices, region_choices, platform_choices
```

---

## apps.leaderboards — Stats & Rankings

### Service Functions
```python
from apps.leaderboards.services import get_tournament_leaderboard, get_player_leaderboard_history

get_tournament_leaderboard(tournament_id) → LeaderboardResponseDTO
get_player_leaderboard_history(player_id) → PlayerHistoryDTO
```

### Event Handler (Automatic)
```python
# This is already wired — just publish match.completed events
@event_handler("match.completed")
def handle_match_completed_for_stats(event):
    # Updates UserStats, TeamStats (ELO), UserMatchHistory
```

---

## common.events — Event Bus

### Publishing Events
```python
from common.events import Event, get_event_bus

event = Event(
    name="match.completed",
    payload={
        "match_id": 123,
        "tournament_id": 456,
        "winner_id": 789,
        "loser_id": 101,
        "scores": {"winner": 13, "loser": 8},
    },
    user_id=requesting_user.id,
    correlation_id=f"tournament-{tournament_id}",
)
get_event_bus().publish(event)
```

### Subscribing to Events
```python
from common.events import event_handler

@event_handler("tournament.completed")
def handle_tournament_completed(event):
    tournament_id = event.payload["tournament_id"]
    # ...do something
```

---

## RULES

1. **Never import models directly in tournament_ops** — always go through adapters
2. **tournament views can import tournament models** — they're in the same app
3. **tournament views should NOT import from other apps** — call tournament_ops services instead
4. **All cross-app communication goes through adapters or the event bus**
5. **Idempotency keys on all financial operations** — `f"entry-fee-{registration_id}"` pattern
6. **Use game_service for all game config lookups** — never hardcode game properties
