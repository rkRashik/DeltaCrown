# DeltaCrown Development Tracker

> Last updated: Phase 29B — Bounty API Team Fields, Migration Applied, Org Error Fix

---

## ✅ Completed — This Sprint

### 1. Critical Bug Fixes

| # | Issue | Fix | File |
|---|-------|-----|------|
| 1 | `NoReverseMatch: Reverse for 'profile_detail' not found` on `/me/settings/` | Changed `user_profile:profile_detail` → `user_profile:public_profile` | `settings_control_deck.html` L1443 |
| 2 | Search input icon misaligned in Recruit Members | Restructured icon into `<span>` wrapper with `pointer-events-none z-10`, `pl-9` padding | `team_create.html` |
| 3 | Player remove (X) button not working | Replaced inline `onclick` with `data-remove-recruit` + event delegation on parent list | `team_create.html` |
| 4 | Profile stats bars were decorative, not data-driven | Rebuilt with `widthratio`-based progress bars (K/D, Win Rate, W/L split, Tournaments) | `_tab_overview.html` |
| 5 | Missing `total_losses` in profile stats | Added `max(matches_played - matches_won, 0)` to view + all fallback dicts | `public_profile_views.py` |

### 2. UI/UX Improvements

| # | Feature | Details | File |
|---|---------|---------|------|
| 1 | Dynamic player slots by game format | Game cards now expose `data-max-roster`, `data-max-team`, `data-max-subs`. JS auto-updates counter when game changes | `team_create.html`, `team.py` |
| 2 | Roster config prefetch | `list_active_games().select_related('roster_config')` added to team create view | `team.py` |
| 3 | DeltaCoin Đ symbol | Replaced all plain `DC` text with styled `Đ` symbol across bounty tab, settings, and modals | `_tab_bounty.html`, `settings_control_deck.html`, `public_profile.html` |
| 4 | Bounty "How It Works" onboarding | 4-step visual guide for new users (Issue → Accept → Play → Payout) with escrow/type badges | `_tab_bounty.html` |
| 5 | Escrow explainer | Collapsible "How Escrow Works" section in challenge modal with DeltaCoin/dispute/payout details | `_tab_bounty.html` |
| 6 | Wager tooltip | Inline tooltip on wager input explaining stake matching requirement | `_tab_bounty.html` |

### 3. Bounty System — Team Challenge Support

| # | Change | Details | File |
|---|--------|---------|------|
| 1 | `BountyType` enum | `SOLO`, `TEAM` choices added | `bounties.py` |
| 2 | Team FK fields | `creator_team`, `acceptor_team`, `target_team` (nullable FKs to Team) | `bounties.py` |
| 3 | `challenge_type` field | CharField with `BountyType` choices, default `SOLO` | `bounties.py` |
| 4 | Model validation | `clean()` validates: team bounties need `creator_team`, game must support teams (`max_team_size > 1`), no self-team-challenge | `bounties.py` |
| 5 | DB indexes | `challenge_type + status`, `creator_team + status` | `bounties.py` |
| 6 | Migration 0033 | `0033_add_team_bounty_support.py` — 4 fields + 2 indexes | `migrations/` |
| 7 | `create_bounty()` | Team params, game roster_config validation, membership check, self-challenge prevention | `bounty_service.py` |
| 8 | `accept_bounty()` | Team acceptance validation, target team check, own-team prevention, membership verification | `bounty_service.py` |
| 9 | Model export | `BountyType` added to `__init__.py` `__all__` | `models/__init__.py` |

### 4. Frontend Team Bounty Integration

| # | Feature | File |
|---|---------|------|
| 1 | Team badge on active bounty cards | `_tab_bounty.html` |
| 2 | Team badge on match history entries | `_tab_bounty.html` |
| 3 | Challenge type badge in accept modal | `_tab_bounty.html` |
| 4 | `openBountyModal()` updated for `challengeType` parameter | `public_profile.html` |

### 5. Bounty API — Team Fields Wired

| # | Change | Details | File |
|---|--------|---------|------|
| 1 | `create_bounty` API | Now accepts `challenge_type`, `creator_team_id`, `target_team_id`; resolves Team objects; passes to service | `bounty_api.py` |
| 2 | `accept_bounty` API | Reads `acceptor_team_id` from request body for team bounties; resolves Team; passes to service | `bounty_api.py` |
| 3 | `BountyType` import | Added to API view imports | `bounty_api.py` |

### 6. Bug Fixes — Phase 29B

| # | Issue | Fix | File |
|---|-------|-----|------|
| 1 | `ProgrammingError: column challenge_type does not exist` | Applied migration 0033 to database | `manage.py migrate` |
| 2 | `OrganizationNotFoundError` not defined (compile error) | Added to imports from `services.exceptions` | `organizations/api/views/__init__.py` |

---

## 🔧 Architecture Notes

### Bounty State Machine
```
open → accepted → in_progress → pending_result → completed
                                               → disputed
     → expired (72hr timeout)
     → cancelled (creator withdraws before acceptance)
```

### DeltaCoin Economy
- **Wallet**: `DeltaCrownWallet` with `cached_balance`, `pending_balance`, `available_balance`
- **Escrow**: Idempotent transactions keyed by `bounty:escrow:{bounty_id}:{user_id}`
- **Payout**: 95% to winner, 5% platform fee
- **Refund**: Full refund on expired/cancelled bounties

### GameRosterConfig
- `max_roster_size` (default 10) — total roster including substitutes
- `max_team_size` (default 5) — active players in a match
- `max_substitutes` (default 2) — max subs allowed
- Used for: dynamic recruit slots, team bounty validation

---

## 📦 Modified Files Index

| File | Changes |
|------|---------|
| `apps/user_profile/models/bounties.py` | BountyType, team FKs, validation, indexes |
| `apps/user_profile/models/__init__.py` | BountyType export |
| `apps/user_profile/services/bounty_service.py` | Team create/accept logic |
| `apps/user_profile/views/public_profile_views.py` | total_losses in user_stats |
| `apps/user_profile/migrations/0033_add_team_bounty_support.py` | Migration |
| `apps/organizations/views/team.py` | select_related('roster_config') |
| `templates/organizations/team/team_create.html` | Icon fix, dynamic slots, remove button |
| `templates/user_profile/profile/tabs/_tab_bounty.html` | Đ symbol, team badges, onboarding, escrow guide |
| `templates/user_profile/profile/tabs/_tab_overview.html` | Progress bars redesign |
| `templates/user_profile/profile/settings_control_deck.html` | profile_detail fix, Đ symbol |
| `templates/user_profile/profile/public_profile.html` | openBountyModal team support |
| `apps/user_profile/views/bounty_api.py` | Team fields wired: challenge_type, creator_team_id, target_team_id, acceptor_team_id |
| `apps/organizations/api/views/__init__.py` | Added OrganizationNotFoundError import |

---

## 🧪 Testing Checklist

- [ ] Bounty creation (solo) — verify escrow debit
- [ ] Bounty creation (team) — verify game roster_config validation
- [ ] Bounty acceptance (solo) — verify matching stake
- [ ] Bounty acceptance (team) — verify team membership + target team
- [ ] Self-challenge prevention (solo + team)
- [ ] Solo game blocks team bounties
- [ ] Profile stats progress bars display correctly
- [ ] Search icon alignment in team create
- [ ] Dynamic slot count changes with game selection
- [ ] Player remove button works via event delegation
- [ ] `/me/settings/` loads without NoReverseMatch
- [ ] DeltaCoin Đ symbol renders in all bounty contexts
