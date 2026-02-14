# Report 4: The Updated Execution Plan

**Date:** February 14, 2026  
**Purpose:** A realistic, prioritized plan for redeveloping the tournament apps — accounting for everything that changed

---

## Executive Summary

This is not a rewrite-from-scratch plan. You have a lot of working code. The goal is to:

1. **Wire up** what's already built (tournament_ops services → views)
2. **Fix** what's broken (adapter stubs, outdated imports, removed profile fields)
3. **Align** with the new reality (organizations app, GameProfile, leaderboards events)
4. **Build** the remaining UI/UX features

The work is organized into **6 execution waves**, each building on the previous one. Each wave produces something testable and deployable.

---

## Wave 0: Critical Fixes (Do First — Before Anything Else)

**Goal:** Fix things that are actively broken or dangerous right now.

**Duration:** 2-3 days

### 0.1 — Fix the Auto-Fill Crash
The registration wizard references `profile.riot_id`, `profile.steam_id`, etc. — fields that **no longer exist** on UserProfile. This will crash in production.

**What to do:**
- In `apps/tournaments/views/registration_wizard.py` and `apps/tournaments/services/registration_autofill.py`:
  - Replace all `profile.riot_id` / `profile.steam_id` / etc. with `GameProfile` queries
  - Use `GameProfile.objects.filter(user=user, game=tournament.game).first()` to get the player's identity
  - Fall back to `game_service.get_identity_validation_rules(game)` for field metadata
- This is the hardcoded game slug logic that needs to become:
  ```python
  game_profile = GameProfile.objects.filter(user=user, game=tournament.game).first()
  if game_profile:
      auto_filled['game_id'] = game_profile.in_game_name or ''
  ```

### 0.2 — Wire EconomyAdapter
The EconomyAdapter has hardcoded return values. Any tournament_ops flow that touches payments silently does nothing.

**What to do:**
- In `apps/tournament_ops/adapters/economy_adapter.py`:
  - `charge()` → call `economy.services.debit(profile, amount, reason=..., idempotency_key=...)`
  - `refund()` → call `economy.services.credit(profile, amount, reason=..., idempotency_key=...)`
  - `get_balance()` → call `economy.services.get_balance(profile)`
  - Import: `from apps.economy import services as economy_services`

### 0.3 — Wire NotificationAdapter
Tournament events silently swallow notifications.

**What to do:**
- In `apps/tournament_ops/adapters/notification_adapter.py`:
  - Import: `from apps.notifications.services import notify`
  - Map tournament_ops notification calls to `notify(recipients, ntype=..., title=..., body=..., tournament_id=...)`
  - Use existing notification types: `REG_CONFIRMED`, `BRACKET_READY`, `MATCH_SCHEDULED`, `RESULT_VERIFIED`, etc.

### 0.4 — Fix Dispute Task Bug
The opponent response reminder task uses the submitter's ID instead of querying for the actual opponent.

**What to do:**
- In `apps/tournament_ops/tasks_dispute.py`:
  - Query the match to find the other participant
  - Send the reminder to the correct user

---

## Wave 1: Adapter Alignment (1 week)

**Goal:** Make all adapters reflect the current state of external apps.

### 1.1 — Update TeamAdapter for Organizations
The `TeamAdapter` currently imports from `apps.teams.models`. With teams frozen:

**What to do:**
- Add support for `apps.organizations.models.Team` as the primary source
- Keep fallback to `apps.teams.models.Team` for legacy tournament data
- Strategy: Try organizations first, fall back to legacy teams
- Update `validate_membership()` to check organization membership models
- Update `validate_team_eligibility()` for new org structure

### 1.2 — Update UserAdapter for GameProfile
The `UserAdapter` may still reference old profile fields.

**What to do:**
- Update `get_player_identity()` to use `GameProfile` model
- Update `get_user_profile()` to not expect game ID fields on UserProfile
- Add method `get_game_profiles(user_id)` returning all GameProfile records
- Add method `get_game_profile(user_id, game_id)` for specific game identity

### 1.3 — Validate All Adapter Protocols
Go through each adapter and verify its protocol matches the current state of the target app.

**Quick checklist:**
- [ ] `TeamAdapter` — organizations + legacy teams
- [ ] `UserAdapter` — GameProfile, no riot_id fields
- [ ] `GameAdapter` — likely fine (games app hasn't changed)
- [ ] `EconomyAdapter` — wired in Wave 0
- [ ] `NotificationAdapter` — wired in Wave 0
- [ ] `TournamentAdapter` — should be fine (own app)
- [ ] `MatchAdapter` — should be fine
- [ ] All stats/ranking adapters — verify leaderboards integration

### 1.4 — Publish Events from Tournaments App
The `events/` directory in tournaments app is a stub. It needs to actually publish events.

**What to do:**
- In `apps/tournaments/signals.py`, after match completion → publish `MatchCompletedEvent` via the event bus
- In tournament lifecycle transitions → publish lifecycle events
- This connects to the existing leaderboards event handler

---

## Wave 2: Service Wiring (2 weeks)

**Goal:** Connect the tournaments app views to the tournament_ops services.

This is the biggest wave. Currently, views call old services directly. They need to call `TournamentOpsService` instead.

### 2.1 — Registration Flow Rewiring

**Current path:** View → `tournaments/services/registration_service.py` → direct model access
**Target path:** View → `TournamentOpsService.register_participant()` → adapters → models

**What to do:**
- In `apps/tournaments/views/registration_wizard.py`:
  - Import `TournamentOpsService` (or its `RegistrationService`)
  - Replace `RegistrationService.register_participant()` calls with ops service calls
  - Replace auto-fill logic with adapter-based approach
  - Keep the view's template rendering logic — only change the data source

### 2.2 — Tournament Lifecycle Rewiring

**What to do:**
- In organizer views that change tournament status:
  - Route through `TournamentOpsService.open_tournament()`, `.start_tournament()`, `.complete_tournament()`, `.cancel_tournament()`
  - These enforce the state machine and publish events

### 2.3 — Match Result Rewiring

**What to do:**
- Result submission views → `TournamentOpsService.submit_match_result()`
- Result confirmation → `TournamentOpsService.confirm_match_result()`
- This automatically triggers:
  - Opponent verification workflow
  - Dispute creation if disagreement
  - Event publishing for stats updates

### 2.4 — Payment Verification Rewiring

**What to do:**
- Admin payment verification → `TournamentOpsService.verify_payment_and_confirm_registration()`
- This orchestrates: payment update + registration confirmation + wallet update + notification

---

## Wave 3: Smart Registration (2 weeks)

**Goal:** Replace the session-based wizard with the persistent draft system.

### 3.1 — Frontend: New Registration Wizard
The smart registration models (`RegistrationDraft`, `RegistrationQuestion`, `RegistrationAnswer`) exist. The views and templates need to be built.

**What to do:**
- Create new registration view that uses `SmartRegistrationService.create_draft_registration()`
- Auto-save drafts every 30 seconds via AJAX
- Lock verified fields (from `GameProfile` data)
- Show progress based on completion percentage
- Generate registration number on draft creation

### 3.2 — Auto-Fill from GameProfile
Replace the hardcoded game-slug auto-fill with `GameProfile` + `GamePlayerIdentityConfig`:

```python
# New approach
game_profile = GameProfile.objects.filter(user=user, game=tournament.game).first()
identity_configs = game_service.get_identity_validation_rules(tournament.game)

for config in identity_configs:
    auto_filled[config.display_name] = {
        'value': game_profile.in_game_name if game_profile else '',
        'locked': config.is_immutable and game_profile is not None,
        'source': 'game_passport',
    }
```

### 3.3 — Eligibility Pre-Check
Before showing the registration form, check eligibility via `TournamentOpsService`:
- Is the user/team already registered?
- Does the tournament have slots available?
- Does the user have the required game profile?
- Does the team meet roster requirements?

Show clear pass/fail with reasons.

### 3.4 — Template Cleanup
Remove the legacy template variants:
- Delete `solo_step1.html`, `solo_step1_new.html` (keep only `_enhanced.html` or write fresh)
- Same for team registration templates
- Consolidate to one version per step

---

## Wave 4: Organizer Console (2 weeks)

**Goal:** Build the organizer-facing UI that leverages the Phase 7 services.

### 4.1 — Results Inbox Page
The `ReviewInboxService` exists. Build the template:
- List pending result submissions with filtering
- One-click verify / reject actions
- Bulk operations (mass approve, mass reject)

### 4.2 — Match Operations Dashboard
The `MatchOpsService` exists. Build the template:
- Match timeline with all events
- Force complete / pause / resume controls
- Referee assignment
- Moderator notes

### 4.3 — Staff Management Page
The `StaffingService` exists. Build the template:
- Assign staff to tournament with roles
- View staff workload
- Assign referees to specific matches

### 4.4 — Tournament Health Dashboard
Show organizers:
- Registration stats (confirmed vs pending vs rejected)
- Match progress (completed vs scheduled vs disputed)
- Payment status overview
- Dispute count and resolution rate

---

## Wave 5: Frontend Polish & Game Theming (1-2 weeks)

**Goal:** Remove hardcoded game styling and use the Games app color data.

### 5.1 — Game-Themed Tournament Pages
Replace hardcoded color blocks:
```django
{# OLD #}
{% if game_spec.slug == 'valorant' %}
    <div class="from-red-950/40">

{# NEW #}
<div style="--game-color: {{ game_spec.primary_color }};">
```

### 5.2 — Registration Wizard Styling
Apply platform design tokens (delta-surface, electric, violet, gold) consistently across the registration flow.

### 5.3 — Tournament Cards
Standardize tournament card components with:
- Game icon and color from `Game.primary_color`
- Status badges (Open, Live, Completed)
- Countdown timer to registration close
- Prize pool display with proper currency formatting

---

## Wave 6: Testing & Hardening (Ongoing, but dedicated 1-2 weeks)

### 6.1 — Tournament Ops Service Tests
Currently 3 test files. Need comprehensive tests for:
- All 21 services (especially with real adapters, not mocks)
- Integration tests: full registration flow end-to-end
- Integration tests: match result → event → stats update pipeline

### 6.2 — Adapter Integration Tests
Test each adapter against the real models:
- TeamAdapter with organizations.Team
- UserAdapter with GameProfile
- EconomyAdapter with real wallet operations

### 6.3 — Template Regression Tests
Ensure all tournament templates render without errors:
- No references to removed UserProfile fields
- No broken imports
- No hardcoded game slugs in critical paths

### 6.4 — Celery Task Scheduling
Add tasks to `CELERY_BEAT_SCHEDULE`:
- `opponent_response_reminder_task`
- `dispute_escalation_task`
- `auto_confirm_submission_task`

---

## Execution Order Summary

```
Wave 0 (2-3 days) ──→ Wave 1 (1 week) ──→ Wave 2 (2 weeks)
  Fix crashes          Align adapters       Wire services
                                               ↓
                           Wave 5 (1-2 wks) ← Wave 4 (2 weeks) ← Wave 3 (2 weeks)
                           Polish UI         Organizer console   Smart registration
                                               ↓
                                           Wave 6 (1-2 weeks)
                                           Testing & hardening
```

**Total estimated duration: 8-11 weeks**

---

## What NOT To Do

1. **Don't rewrite the Tournament model** — It works, it has data, it has 50 related models. Refactor, don't rewrite.

2. **Don't create a third registration service** — You already have two (old + tournament_ops). Pick tournament_ops and wire it.

3. **Don't build a custom frontend framework** — Stay with Django templates + Tailwind + vanilla JS. The frontend_sdk was written but you don't need React/Vue for this.

4. **Don't migrate legacy data mid-development** — Keep `team_id` IntegerField as-is. Don't try to FK-ify it during the rewire.

5. **Don't duplicate the leaderboards logic** — The leaderboards app handles stats updates via events. Don't manually call `UserStatsService` from tournament_ops if the event bus does it.

---

## Decision Points (You Need To Decide)

Before starting, you need to make these decisions:

### Decision 1: Team Source
**Options:**
- A) `TeamAdapter` reads from `apps.organizations.Team` only (new data)
- B) `TeamAdapter` tries organizations first, falls back to `apps.teams.Team` (dual-source)
- C) All old `team_id` references point to organizations (requires data migration)

**Recommendation:** Option B (dual-source) for now. Migrate to A later.

### Decision 2: Registration System
**Options:**
- A) Rewire existing wizard views to call `TournamentOpsService`
- B) Build entirely new registration views alongside old ones
- C) Build API-first registration (JSON endpoints + HTMX frontend)

**Recommendation:** Option A. The existing views/templates are usable. Just swap the backend calls.

### Decision 3: Stats Pipeline
**Options:**
- A) Use `tournament_ops/services/user_stats_service.py` + `team_stats_service.py`
- B) Publish events and let `apps/leaderboards` handle everything
- C) Both (tournament_ops for orchestration, leaderboards for computation)

**Recommendation:** Option B. The leaderboards app already has event handlers for `match.completed`. Just publish events.

### Decision 4: Legacy Cleanup Timing
**Options:**
- A) Clean up legacy code as you go (remove old services, templates, backups)
- B) Do all cleanup in a dedicated wave after everything works
- C) Never clean up (leave both paths)

**Recommendation:** Option B. Get everything working first, then clean up.
