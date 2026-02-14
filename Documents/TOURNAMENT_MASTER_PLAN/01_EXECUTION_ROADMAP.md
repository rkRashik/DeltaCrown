# The Execution Roadmap — Phase by Phase

*Written February 14, 2026*

---

## How This Is Organized

The work is split into **7 Phases**, each one building on the previous. Each phase has clear deliverables that you can test and verify before moving to the next one. No phase depends on anything that hasn't been built in a previous phase.

**Estimated total time: 10-14 weeks of focused work.**

---

## Phase 0: The Cleanup (3-5 days)

### Goal
Remove all legacy code, backup files, duplicate implementations, and broken references. When this phase is done, the codebase should compile cleanly and have zero dead code.

### Why First?
You can't build new features on a messy foundation. Every duplicate creates confusion about which code is active. Every broken reference is a ticking crash. Clean first, build after.

### Tasks

#### 0.1 — Remove the Legacy Game Model
The `Game` model defined inside `apps/tournaments/models/tournament.py` is dead. The real one lives in `apps/games/models/game.py`.

- Remove the `Game` class from `tournament.py`
- Remove its re-export from `apps/tournaments/models/__init__.py`
- Find every file that imports `from apps.tournaments.models import Game` or `from apps.tournaments.models.tournament import Game` and change to `from apps.games.models import Game`
- The `apps.core.models` reference needs updating too

#### 0.2 — Remove All riot_id/steam_id Hardcoded References
These fields no longer exist on UserProfile. They've been replaced by GameProfile.

- `registration_wizard.py` — 6 references
- `tournament_team_registration.py` — 12+ references (player2_riot_id, etc.)
- `test_adapters.py` — 12 references in test mocks
- `test_dtos.py` — 4 references
- `registration_autofill.py` — any `profile.riot_id` access must use GameProfile
- Search the entire codebase for `riot_id|steam_id|epic_id|activision_id|ea_id` in tournament files

#### 0.3 — Remove Backup/Deprecated Files
- Delete `apps/tournaments/views_old_backup.py`
- Delete `apps/tournaments/views/registration_demo_backup.py`
- Delete `templates/tournaments/registration_demo_backup/` (entire directory)
- Delete `templates/tournaments/marketplace/` (entire directory — feature removed)
- Delete `templates/tournaments/old_backup/` (entire directory)

#### 0.4 — Consolidate Duplicate Services
For each pair of duplicates, keep the better one:

| Keep | Delete | Reason |
|------|--------|--------|
| `tournament_ops/services/dispute_service.py` (661 lines) | `tournaments/services/dispute_service.py` (76-line stub) | Ops version is complete |
| `checkin_service.py` (425 lines) | `check_in_service.py` (256 lines) | Keep the one with more features, merge unique parts |
| `eligibility_service.py` (325 lines) | `registration_eligibility.py` (214 lines) | Merge into one, remove module-level imports |
| `analytics_service.py` (783 lines) | `analytics.py` (239 lines) | Keep the comprehensive one |

#### 0.5 — Consolidate Duplicate Models
- Remove the old `Dispute` model from `models/match.py` — keep `DisputeRecord` from `models/dispute.py`
- Remove `TemplateRating` model (marketplace removed) — or verify table doesn't exist
- Decide on staff model: Keep the Phase 7 system (`StaffRole`, `TournamentStaffAssignment`, `MatchRefereeAssignment`), deprecate the old one (`TournamentStaffRole`, `TournamentStaff`) — **do NOT delete yet** if they have data, just stop using them in new code

#### 0.6 — Fix Direct Cross-App FK Violations
These models have ForeignKey to `teams.Team` (the frozen legacy app):

- `MatchResultSubmission` → change `submitted_by_team = ForeignKey('teams.Team')` to `team_id = IntegerField(null=True, blank=True)`
- `DisputeRecord` → same change: FK → IntegerField
- `TournamentTeamInvitation` → same change: FK → IntegerField
- `TeamRegistrationPermissionRequest` → change `from apps.organizations.models import Team` at module level to method-level import, and change FK to IntegerField

#### 0.7 — Fix tournament_ops Adapter Bugs
- `match_ops_adapter.py` references `match.status` but the field is `match.state` → fix
- `match_scheduling_adapter.py` references `match.stage` and `match.participant1/2` → verify field names and fix
- Any adapter importing from `apps.teams` → update to `apps.organizations`

### Deliverable
`python manage.py check` passes cleanly. `python manage.py test apps.tournaments apps.tournament_ops` runs. No broken imports, no crash-on-import.

---

## Phase 1: The Foundation Wiring (1-2 weeks)

### Goal
Wire all tournament_ops adapters to real apps. After this phase, every adapter returns real data instead of stubs or hardcoded values.

### Why?
The adapters are the bridge between tournament_ops services and the rest of the platform. If the bridges are broken, nothing built on top works.

### Tasks

#### 1.1 — Wire EconomyAdapter
Currently all-stub, returning hardcoded success.

```
charge(profile_id, amount, reason, idempotency_key)
  → calls economy.services.award(profile, -amount, reason, ...)
  
refund(profile_id, amount, reason, idempotency_key)  
  → calls economy.services.award(profile, +amount, reason, ...)
  
get_balance(profile_id)
  → calls economy.services.wallet_for(profile).cached_balance
  
process_entry_fee(registration_id, profile_id, amount)
  → calls award() with reason=ENTRY_FEE_DEBIT
```

#### 1.2 — Wire NotificationAdapter
Currently no-op.

```
notify_registration_confirmed(user_id, tournament_id)
  → calls notifications.services.notify([user], event='REG_CONFIRMED', ...)
  
notify_match_scheduled(user_ids, match_id)
  → calls notify() with event='MATCH_SCHEDULED'
  
notify_result_verified(user_ids, match_id)
  → calls notify() with event='RESULT_VERIFIED'
  
notify_dispute_opened(user_ids, dispute_id)
  → calls notify() with event='DISPUTE_OPENED'
  
notify_tournament_completed(user_ids, tournament_id)
  → calls notify() with event='TOURNAMENT_COMPLETED'
```

#### 1.3 — Verify & Fix TeamAdapter
- Primary source: `apps.organizations.models.Team`
- Fallback: `apps.teams.models.Team` (for legacy data only)
- Methods must use `TeamMembership` from organizations for roster checks
- `validate_roster()` must call `game_service.validate_roster_size()`

#### 1.4 — Verify & Fix UserAdapter
- `get_player_identity()` must use `GameProfile` from user_profile
- No references to `profile.riot_id` or any hardcoded game fields
- Must use `GamePassportSchema` for field validation

#### 1.5 — Wire Event Publishing
Tournament actions need to publish events to the event bus:

| Action | Event Name |
|--------|------------|
| Registration confirmed | `registration.confirmed` |
| Match started | `match.started` |
| Match completed | `match.completed` |
| Result submitted | `result.submitted` |
| Result verified | `result.verified` |
| Dispute opened | `dispute.opened` |
| Dispute resolved | `dispute.resolved` |
| Tournament completed | `tournament.completed` |
| Check-in completed | `checkin.completed` |

The leaderboards app already listens for `match.completed`. Adding more consumers for other events comes later.

#### 1.6 — Add Celery Beat Tasks
Add the 3 tournament_ops tasks to `CELERY_BEAT_SCHEDULE` in settings:
- `opponent_response_reminder_task` — every hour
- `dispute_escalation_task` — every 4 hours  
- `auto_confirm_submission_task` — every 2 hours

### Deliverable
Write integration tests for each adapter: call the adapter method, verify it reads/writes the correct model. All adapters return real data.

---

## Phase 2: Service Consolidation (2 weeks)

### Goal
Create one definitive service for each domain, remove duplicates, and make all views call the correct service.

### Why?
Three registration services means three possible code paths, three sets of bugs, and no clarity about which is "right." One service, one truth.

### Tasks

#### 2.1 — Unified Registration Service
Create the definitive registration flow in `tournament_ops/services/registration_service.py`:

1. **Eligibility Check** — merge from `registration_eligibility.py` + `eligibility_service.py`:
   - Player has GameProfile for tournament's game
   - Player meets minimum rank/level requirements (from GameTournamentConfig)
   - Player isn't already registered
   - Tournament has available slots
   - Team roster meets size requirements (if team tournament)
   - Player is 16+ (if required)
   - Player's KYC status is sufficient (if required)

2. **Draft Creation** — from smart registration models:
   - Create `RegistrationDraft` with auto-generated registration number
   - Pre-fill fields from GameProfile
   - Lock verified/immutable fields
   - Return checklist of requirements (passed/pending)

3. **Payment Processing**:
   - If free tournament → skip
   - If paid → debit from wallet via EconomyAdapter
   - Record transaction with idempotency key

4. **Confirmation**:
   - Move RegistrationDraft → Registration
   - Publish `registration.confirmed` event
   - Send notification via NotificationAdapter
   - Update slot count

5. Delete `tournaments/services/registration_eligibility.py`
6. Delete `tournaments/services/eligibility_service.py`
7. Keep `tournaments/services/registration_service.py` only for ORM-level helper methods that the ops service calls through adapters

#### 2.2 — Unified Match Service
Consolidate `tournaments/services/match_service.py` (1,284 lines) and `tournament_ops/services/match_service.py` (372 lines):

- Keep the state machine from tournaments (it works)
- Wrap all state transitions through tournament_ops (for event publishing and notifications)
- Result submission → `tournament_ops/services/result_submission_service.py` (already complete)
- Result verification → `tournament_ops/services/result_verification_service.py` (already complete)

#### 2.3 — Unified Bracket Service
Consolidate into `tournament_ops/services/bracket_engine_service.py`:

- Single Elimination generator → keep (works)
- Double Elimination generator → keep (works)
- Round Robin generator → keep (works)
- Swiss generator → **complete rounds 2+** (currently stubbed)
- Group Stage logic → port from `tournaments/services/group_stage_service.py` — **remove hardcoded game logic** and use GameTournamentConfig instead

#### 2.4 — Unified Check-In Service
Merge `checkin_service.py` and `check_in_service.py`:
- Keep the audit logging from `checkin_service.py`
- Keep the validation from `check_in_service.py`
- One service, one file

#### 2.5 — Unified Analytics Service
Consolidate the three analytics implementations:
- Keep `tournament_ops/services/analytics_engine_service.py` as the primary
- Port useful queries from `tournaments/services/analytics_service.py`
- Delete `tournaments/services/analytics.py`

#### 2.6 — Unified Staff Service
- Keep the Phase 7 `tournament_ops/services/staffing_service.py`
- Keep the Phase 7 models (`StaffRole`, `TournamentStaffAssignment`, `MatchRefereeAssignment`)
- Delete `tournaments/services/staff_permission_checker.py` (use StaffingAdapter instead)
- Deprecate old staff models (don't delete — data migration needed)

### Deliverable
Each domain has exactly one service. A service diagram shows: View → OpsService → Adapter → Model. No shortcuts.

---

## Phase 3: Views & URL Restructure (2 weeks)

### Goal
Clean up all 26+ view files and 80+ URL patterns into a logical, maintainable set. Every view calls tournament_ops services.

### URL Structure (Clean)

```
/tournaments/                         → Browse/discover tournaments
/tournaments/create/                  → Tournament creation wizard
/tournaments/<slug>/                  → Tournament detail page
/tournaments/<slug>/register/         → Registration wizard (smart)
/tournaments/<slug>/lobby/            → Participant lobby (check-in, announcements)
/tournaments/<slug>/bracket/          → Live bracket view
/tournaments/<slug>/standings/        → Group standings (if group format)
/tournaments/<slug>/leaderboard/      → Tournament leaderboard
/tournaments/<slug>/results/          → Tournament results/archive

/tournaments/<slug>/match/<id>/       → Match detail page
/tournaments/<slug>/match/<id>/submit-result/ → Result submission
/tournaments/<slug>/match/<id>/dispute/       → Dispute filing

/tournaments/<slug>/manage/           → Organizer hub (overview)
/tournaments/<slug>/manage/participants/  → Registration management
/tournaments/<slug>/manage/bracket/       → Bracket editor
/tournaments/<slug>/manage/matches/       → Match management
/tournaments/<slug>/manage/results/       → Result review inbox
/tournaments/<slug>/manage/disputes/      → Dispute management
/tournaments/<slug>/manage/staff/         → Staff management
/tournaments/<slug>/manage/finances/      → Financial dashboard
/tournaments/<slug>/manage/analytics/     → Analytics dashboard
/tournaments/<slug>/manage/settings/      → Tournament settings

/tournaments/my/                      → Player's tournaments (registered, active, past)
/tournaments/my/matches/              → Player's match schedule
/tournaments/my/results/              → Player's result history

/api/tournaments/...                  → REST API endpoints
```

### View Architecture

```
views/
  browse.py           → TournamentListView, TournamentSearchView
  detail.py           → TournamentDetailView, TournamentArchiveView
  create.py           → TournamentCreateWizard (multi-step)
  registration.py     → SmartRegistrationView (single unified flow)
  lobby.py            → LobbyView, CheckInView
  bracket.py          → BracketView (public), BracketEditorView (organizer)
  match.py            → MatchDetailView
  result.py           → ResultSubmissionView, ResultVerificationView
  dispute.py          → DisputeView (filing + management)
  organizer/
    hub.py            → OrganizerHubView (overview dashboard)
    participants.py   → ParticipantManagementView
    matches.py        → MatchManagementView
    results.py        → ResultInboxView
    disputes.py       → DisputeManagementView
    staff.py          → StaffManagementView
    finances.py       → FinancialDashboardView
    analytics.py      → AnalyticsDashboardView
    settings.py       → TournamentSettingsView
  player.py           → MyTournamentsView, MyMatchesView, MyResultsView
  api/                → REST API views (existing, cleaned up)
```

### Tasks

#### 3.1 — Create New View Files
Write new views following the clean structure above. Each view:
- Accepts HTTP request
- Calls tournament_ops service for business logic
- Returns rendered template
- Has proper permission checks (is_authenticated, is_organizer, is_staff)

#### 3.2 — Update urls.py
Replace the 80-pattern spaghetti with the clean URL structure above.

#### 3.3 — Verify Every URL
After restructuring, test every URL for 200/302/403 responses. Ensure nothing is broken.

#### 3.4 — Registration View Rewrite
The biggest single task. The current wizard (`registration_wizard.py`) is hardcoded for specific games. The new one:
- Uses `SmartRegistrationService` for draft creation
- Uses `GameProfile` for auto-fill (via UserAdapter)
- Uses `GamePlayerIdentityConfig` for field definitions
- Uses `EligibilityService` for pre-check
- Shows requirements checklist before the form
- Saves progress automatically

#### 3.5 — Organizer Hub Views
Build the organizer management interface. Each sub-view calls the corresponding ops service:
- Participants → `RegistrationService`
- Bracket → `BracketEngineService`
- Results → `ReviewInboxService` + `ResultVerificationService`
- Disputes → `DisputeService`
- Staff → `StaffingService`
- Health → `AnalyticsEngineService`

### Deliverable
Clean URL structure. Every view calls its service. No direct ORM queries in views.

---

## Phase 4: Template Rebuild (2 weeks)

### Goal
Build a clean, consistent set of templates. One version per page. Platform design tokens. Game-aware theming.

### Template Structure (Clean)

```
templates/tournaments/
  browse/
    list.html                → Tournament listing with filters
    _card.html               → Reusable tournament card partial
    _filters.html            → Filter sidebar partial
  
  detail/
    page.html                → Tournament detail page
    _info.html               → Tournament info section
    _schedule.html           → Schedule/timeline section
    _rules.html              → Rules section
    _prizes.html             → Prize display
    _registration_cta.html   → Registration call-to-action
  
  registration/
    wizard.html              → Smart registration wrapper
    _step_identity.html      → Step: identity verification
    _step_requirements.html  → Step: eligibility requirements
    _step_payment.html       → Step: payment
    _step_confirm.html       → Step: review & confirm
    _eligibility_card.html   → Pass/fail card for each requirement
    success.html             → Registration confirmed
    ineligible.html          → Registration blocked
  
  lobby/
    hub.html                 → Lobby main page
    _checkin.html             → Check-in panel
    _announcements.html       → Announcement feed
    _roster.html              → Participant list
    _schedule.html            → Match schedule
  
  bracket/
    view.html                → Public bracket view
    editor.html              → Organizer bracket editor
    _node.html               → Single bracket match node
  
  match/
    detail.html              → Match detail page
    submit_result.html       → Result submission form
    dispute.html             → Dispute filing form
  
  standings/
    groups.html              → Group stage standings
    leaderboard.html         → Tournament leaderboard
  
  organizer/
    hub.html                 → Dashboard overview
    participants.html        → Registration management
    bracket_editor.html      → Bracket editor
    matches.html             → Match management
    result_inbox.html        → Pending results
    disputes.html            → Dispute queue
    staff.html               → Staff management
    finances.html            → Financial overview
    analytics.html           → Analytics dashboard
    settings.html            → Tournament settings
  
  player/
    my_tournaments.html      → Player's tournaments
    my_matches.html          → Player's matches
    my_results.html          → Player's results
  
  archive/
    view.html                → Completed tournament archive
    _match_history.html      → Match-by-match results
    _final_standings.html    → Final placements
  
  components/
    _game_theme.html         → Game color variables (uses Game.primary_color)
    _status_badge.html       → Tournament status badges
    _countdown.html          → Countdown timer
    _notification.html       → Toast notifications
    _loading.html            → Loading states
    _pagination.html         → Pagination
    _empty_state.html        → Empty state illustrations
  
  emails/
    registration_confirmed.html
    match_scheduled.html
    result_reminder.html
    tournament_completed.html
    certificate_ready.html
```

### Design Principles
1. **Game theming via CSS variables** — `<div style="--game-color: {{ game.primary_color }};">` — no hardcoded colors
2. **Platform tokens** — Use `delta-surface`, `electric`, `violet`, `gold` from design tokens
3. **Tailwind utility classes** — consistent spacing, typography, responsive design
4. **Partial-first** — build reusable `_partial.html` files, compose pages from partials
5. **Minimal JavaScript** — form validation, countdown timers, draft save. No SPA framework.

### Tasks

#### 4.1 — Build Component Library
Create the `components/` partials first — they're reused everywhere.

#### 4.2 — Build Browse & Detail Pages
The public-facing tournament discovery and detail pages.

#### 4.3 — Build Registration Wizard
The smart registration flow with auto-fill, eligibility checks, and payment.

#### 4.4 — Build Lobby & Match Pages
The participant experience during a live tournament.

#### 4.5 — Build Bracket & Standings Views
Live bracket visualization and group standings tables.

#### 4.6 — Build Organizer Dashboard
All 10 organizer management sub-pages.

#### 4.7 — Build Player Section
My Tournaments, My Matches, My Results.

#### 4.8 — Build Archive View
The permanent tournament record page.

#### 4.9 — Delete Old Templates
Remove everything we replaced. No backup directories, no `_new` variants, no `_enhanced` versions.

### Deliverable
Every URL renders a clean template. Consistent design. No broken partials.

---

## Phase 5: Lifecycle & Automation (1-2 weeks)

### Goal
The full tournament lifecycle works end-to-end, with all automated processes running.

### The Lifecycle

```
DRAFT
  ↓ Organizer clicks "Publish"
PUBLISHED
  ↓ Registration open date arrives (or immediate)
REGISTRATION_OPEN
  ↓ Registration close date arrives, or organizer closes manually
REGISTRATION_CLOSED
  ↓ Check-in window opens
CHECK_IN
  ↓ Check-in window closes, no-shows removed
LIVE
  ↓ All matches completed
COMPLETING
  ↓ Results finalized, prizes distributed, certificates generated
COMPLETED
  ↓ Archive data generated
ARCHIVED
```

Special transitions:
- **CANCELLED** — from any state before COMPLETED
- **SUSPENDED** — admin-only, pauses tournament

### Tasks

#### 5.1 — Tournament State Machine Service
Create `TournamentLifecycleService` with methods for each transition:
- `publish(tournament_id)` — DRAFT → PUBLISHED
- `open_registration(tournament_id)` — PUBLISHED → REGISTRATION_OPEN (or auto on date)
- `close_registration(tournament_id)` — REGISTRATION_OPEN → REGISTRATION_CLOSED
- `open_checkin(tournament_id)` — REGISTRATION_CLOSED → CHECK_IN
- `start_tournament(tournament_id)` — CHECK_IN → LIVE (remove no-shows, generate bracket)
- `complete_tournament(tournament_id)` — LIVE → COMPLETING → COMPLETED
- `archive_tournament(tournament_id)` — COMPLETED → ARCHIVED
- `cancel_tournament(tournament_id)` — any → CANCELLED (with refunds)

Each transition:
1. Validates the current state
2. Runs pre-transition logic (e.g., bracket generation before LIVE)
3. Updates the state
4. Runs post-transition logic (e.g., notifications, events)
5. Publishes domain event

#### 5.2 — Scheduled Transitions via Celery
- Registration auto-open when `registration_opens_at` arrives
- Registration auto-close when `registration_closes_at` arrives
- Check-in auto-open X minutes before tournament start
- Check-in auto-close at tournament start time
- Auto-disqualify no-shows when check-in closes

#### 5.3 — Tournament Completion Pipeline
When the last match finishes:
1. Determine final placements (Winner, Runner-Up, Top 4, etc.)
2. Create `TournamentResult` records
3. Distribute prizes via EconomyAdapter
4. Generate certificates
5. Publish `tournament.completed` event
6. Update all participant stats via event bus
7. Send completion notifications

#### 5.4 — Archive Generation
When a tournament is archived:
- Snapshot all bracket data
- Snapshot all match results with scores
- Snapshot final standings
- Snapshot participant list with placements
- This data becomes the permanent archive, queryable even if live models change

### Deliverable
You can create a tournament, register players, run matches, and complete it — entirely through the UI. Every state transition works.

---

## Phase 6: Testing & Hardening (1-2 weeks, parallel with Phase 5)

### Goal
Comprehensive test coverage. No regressions.

### Tasks

#### 6.1 — Adapter Unit Tests
Test each adapter independently:
- Create test data (models) → call adapter method → verify DTO output
- Test error cases (missing data, invalid IDs)

#### 6.2 — Service Integration Tests
Test each service with real adapters (not mocks):
- Registration flow: create user → create tournament → register → verify confirmation
- Match flow: start match → submit result → verify → update bracket
- Dispute flow: submit conflicting results → create dispute → resolve

#### 6.3 — View Tests
For each URL pattern:
- Test unauthenticated access (should redirect to login or show 403)
- Test wrong permissions (non-organizer accessing organizer pages)
- Test correct flow (POST data → expected redirect/response)

#### 6.4 — Template Rendering Tests
Render every template with sample context data. Verify:
- No `TemplateSyntaxError`
- No undefined variable crashes
- No broken `{% url %}` references

#### 6.5 — Lifecycle Integration Test
Automated test that runs the complete lifecycle:
1. Create tournament → verify DRAFT state
2. Publish → verify PUBLISHED
3. Register 2 players → verify registrations
4. Open check-in → check in both players
5. Start tournament → verify bracket generated
6. Submit match result → verify result recorded
7. Complete tournament → verify prizes distributed
8. Archive → verify archive data generated

### Deliverable
`pytest apps/tournaments/ apps/tournament_ops/ -v` passes with 80%+ coverage.

---

## Phase Summary

| Phase | Duration | Key Deliverable |
|-------|----------|----------------|
| **0: Cleanup** | 3-5 days | Zero legacy code, clean imports, no duplicates |
| **1: Foundation** | 1-2 weeks | All adapters wired, events published, Celery tasks scheduled |
| **2: Services** | 2 weeks | One service per domain, no duplicates |
| **3: Views & URLs** | 2 weeks | Clean URL structure, all views call ops services |
| **4: Templates** | 2 weeks | One template per page, design tokens, game theming |
| **5: Lifecycle** | 1-2 weeks | Full lifecycle automation, completion pipeline |
| **6: Testing** | 1-2 weeks | 80%+ test coverage, lifecycle integration test |

**Total: 10-14 weeks**

---

## Critical Path

The critical path (longest chain of dependencies):

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5
                                  ↑           ↑
                              Phase 6 starts here (parallel)
```

Phase 4 (Templates) can partially overlap with Phase 3 (Views) since some templates can be built before their views are finalized.

Phase 6 (Testing) should start during Phase 3 and continue through Phase 5.
