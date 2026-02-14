# Report 1: Current State Audit — Tournament Apps

**Date:** February 14, 2026  
**Scope:** `apps/tournaments` + `apps/tournament_ops`  
**Purpose:** Ground-truth snapshot of both apps before redevelopment begins

---

## Executive Summary

You have two tournament-related apps in your codebase:

1. **`apps/tournaments`** — The "big app." It holds all the models, views, templates, admin pages, API endpoints, and most of the business logic for running tournaments. Think of it as the **warehouse** where everything tournament-related lives today.

2. **`apps/tournament_ops`** — The "orchestration layer." It was designed to sit above `tournaments` and coordinate workflows across your platform (teams, games, economy, notifications). Think of it as the **traffic controller** that makes sure every piece talks to each other correctly.

**Bottom line:** The `tournaments` app is a large, feature-rich app that works but has accumulated legacy patterns. The `tournament_ops` app has excellent architecture (adapters, DTOs, clean service boundaries) but is only about 65-70% wired up — key integrations like payments and notifications are still stubbed out.

---

## Part A: `apps/tournaments` — The Tournament Engine

### What It Is

This is the core of your tournament system. It was built organically over many months and contains everything from tournament creation to certificates. It's big, it works, and it has technical debt.

### By the Numbers

| Metric | Count |
|--------|-------|
| Model files | 28 |
| Total models | ~50 |
| URL patterns | ~80 |
| View files | 30+ |
| Service modules | 37+ |
| API endpoint files | 20+ |
| Signal handlers | 8 |
| Celery tasks | 4 |
| Management commands | 9 |
| Template tag files | 2 |
| Form files | 1 |
| Test files | 24 |
| Admin modules | 8 |

### Core Models (What Data It Owns)

Here's every model group and what it does:

#### Tournament & Game Configuration
| Model | What It Does |
|-------|-------------|
| `Tournament` | The main event — name, game, format, prizes, status, dates, registration settings. 1,011 lines. Uses soft-delete. |
| `Game` | **Legacy stub** — now re-exports from `apps.games.Game`. Kept for backward compatibility only. |
| `CustomField` | Per-tournament custom registration fields |
| `TournamentVersion` | Audit snapshots when tournament config changes |
| `TournamentTemplate` | Reusable tournament presets |

#### Registration & Payments
| Model | What It Does |
|-------|-------------|
| `Registration` | Who signed up for what. Has `user` FK (solo) or `team_id` IntegerField (teams). JSONB `registration_data`. Status: pending → confirmed/rejected. |
| `Payment` | Payment proof records for entry fees |
| `PaymentVerification` | Admin verification workflow for manual payments |
| `TournamentPaymentMethod` | Which payment methods a tournament accepts |
| `TournamentTeamInvitation` | Organizer invites teams directly |
| `TeamRegistrationPermissionRequest` | Team member requests permission to register |

#### Smart Registration (Phase 5)
| Model | What It Does |
|-------|-------------|
| `RegistrationDraft` | Persistent draft storage (replaces session-only wizard) |
| `RegistrationQuestion` | Dynamic registration questions |
| `RegistrationAnswer` | Answers to dynamic questions |
| `RegistrationRule` | Auto-approval/rejection rule configurations |

#### Brackets & Stages
| Model | What It Does |
|-------|-------------|
| `Bracket` | Tournament bracket structure (single/double elim, etc.) |
| `BracketNode` | Individual positions in the bracket tree |
| `BracketEditLog` | Audit trail for bracket editor changes |
| `Group`, `GroupStanding`, `GroupStage` | Group stage support |
| `TournamentStage` | Multi-stage tournaments (groups → playoffs) |

#### Matches & Results
| Model | What It Does |
|-------|-------------|
| `Match` | Individual match records with state machine (SCHEDULED → LIVE → COMPLETED) |
| `Dispute` | Legacy dispute model (in match.py) |
| `MatchResultSubmission` | Phase 6: Participant result submissions |
| `ResultVerificationLog` | Phase 6: Result verification audit trail |
| `DisputeRecord`, `DisputeEvidence` | Phase 6: Formal dispute system |
| `TournamentResult` | Final placements (1st, 2nd, 3rd, etc.) |

#### Match Operations (Phase 7)
| Model | What It Does |
|-------|-------------|
| `MatchOperationLog` | Staff actions on matches |
| `MatchModeratorNote` | Referee/staff notes on matches |

#### Staff & Permissions
| Model | What It Does |
|-------|-------------|
| `TournamentStaffRole` | Role definitions (head_admin, moderator, etc.) |
| `TournamentStaff` | Staff assignments to tournaments |
| `StaffRole` | Phase 7 capability-based roles |
| `TournamentStaffAssignment` | Phase 7 per-tournament assignments |
| `MatchRefereeAssignment` | Phase 7 per-match referees |

#### Post-Tournament
| Model | What It Does |
|-------|-------------|
| `PrizeTransaction` | Prize payout tracking |
| `Certificate` | Achievement certificates (S3-backed) |

#### Dynamic Forms
| Model | What It Does |
|-------|-------------|
| `RegistrationFormTemplate` | Reusable form templates |
| `TournamentRegistrationForm` | Per-tournament form config |
| `FormResponse` | Form submissions |
| `TournamentFormConfiguration` | Form configuration |
| `FormWebhook`, `WebhookDelivery` | Webhook integration |

#### Other
| Model | What It Does |
|-------|-------------|
| `TournamentAnnouncement` | Tournament-wide announcements |
| `TournamentLobby`, `CheckIn`, `LobbyAnnouncement` | Lobby & check-in system |
| `AuditLog` | Security audit entries |

### Services — The Business Logic

37+ service files handle all tournament logic. The biggest ones:

| Service | Lines | What It Does |
|---------|-------|-------------|
| `registration_service.py` | ~1,710 | All registration logic: eligibility, auto-fill, payment, cancellation, waitlist |
| `bracket_service.py` | ~1,250 | Bracket generation, seeding, advancement |
| `match_service.py` | Large | Match state transitions, result submission, disputes |
| `leaderboard.py` | Medium | Standings calculation (has hardcoded game logic) |
| `tournament_service.py` | Medium | Tournament CRUD and lifecycle |
| `payment_service.py` | Medium | DeltaCoin integration, payment verification |
| `certificate_service.py` | Medium | Certificate generation |
| `notification_service.py` | Medium | Notification dispatching |

Plus 20+ more specialized services (analytics, group stage, lobby, ranking, eligibility, autofill, etc.)

### Templates — The Frontend

All tournament templates live in `templates/tournaments/`:

| Folder | What's In It |
|--------|-------------|
| `detailPages/` | Tournament detail pages |
| `team_registration/` | 24 registration wizard templates (solo + team, 3 steps each, multiple versions) |
| `registration/` | Registration status pages |
| `organizer/` | Organizer management pages |
| `lobby/` | Tournament lobby pages |
| `groups/` | Group stage UI |
| `components/` | Reusable UI components |
| `analytics/` | Analytics dashboards |
| `spectator/` | Spectator view pages |
| `marketplace/` | Template marketplace |

### What Works Well

- **Feature-complete tournament lifecycle** — draft through archived
- **Service layer pattern** — business logic is properly separated from views
- **Multiple bracket formats** — single/double elimination, round robin, Swiss, group stage
- **DeltaCoin payment integration** — instant wallet deduction with idempotency
- **Signal handlers** — auto-create certificates, sync profile match history, auto-convert form responses
- **Smart registration models** — drafts, dynamic questions, auto-approval rules already in the schema

### What's Broken or Messy

1. **The Legacy Game model** — `tournaments.Game` is a stub re-exporting from `apps.games.Game`. Earlier code still references the local model via FK. This is a migration landmine.

2. **Hardcoded game logic** — `if game_slug == 'valorant'` style checks in registration wizard, leaderboard calculations, and templates. Should use `GameService` and `GamePlayerIdentityConfig`.

3. **IntegerField team references** — `Registration.team_id` and `Match.participant1_id` are plain `IntegerField`, not ForeignKeys. No referential integrity. No `select_related`. Manual lookups everywhere.

4. **Direct cross-app imports** — 50+ places directly import `Team`, `TeamMembership`, `UserProfile` models instead of going through service APIs.

5. **Two staffing systems** — Both `staff.py` (legacy) and `staffing.py` (Phase 7) exist with overlapping models.

6. **Two dispute systems** — `match.py > Dispute` (legacy) and `dispute.py > DisputeRecord, DisputeEvidence` (Phase 6). Both live in the codebase.

7. **Events system is a stub** — `events/` directory exists with `register_tournament_event_handlers()` but it's empty. No events are actually published from the tournaments app.

8. **Validators directory is empty** — Created but never populated.

9. **`views_old_backup.py`** — Dead code still in the codebase.

---

## Part B: `apps/tournament_ops` — The Orchestration Layer

### What It Is

This is the "clean architecture" layer designed to sit between the outside world and the tournaments engine. It never touches the database directly — instead it uses **adapters** to talk to other apps and **DTOs** to pass data around without coupling.

It has **zero Django models**. It's pure Python orchestration.

### By the Numbers

| Metric | Count |
|--------|-------|
| DTO modules | 25 |
| DTO classes | ~55 |
| Service modules | 21 |
| Adapter modules | 22 |
| Event classes | 14 |
| Exception classes | 24 |
| Celery tasks | 3 |
| Test files | 3 |

### Architectural Pattern

```
                    ┌─────────────────────┐
                    │  TournamentOpsService │  ← Facade (3,031 lines)
                    │  (the front door)    │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    ┌─────────▼──────┐ ┌─────▼──────┐ ┌──────▼─────────┐
    │ Registration   │ │ Lifecycle  │ │ Match / Result │
    │ Service        │ │ Service    │ │ Services       │
    └─────────┬──────┘ └─────┬──────┘ └──────┬─────────┘
              │               │               │
    ┌─────────▼───────────────▼───────────────▼─────────┐
    │              ADAPTER LAYER                         │
    │  TeamAdapter | GameAdapter | EconomyAdapter | ...  │
    └─────────────────────┬─────────────────────────────┘
                          │
    ┌─────────────────────▼─────────────────────────────┐
    │           EXTERNAL APPS (via their own APIs)       │
    │  apps/teams | apps/games | apps/economy | ...      │
    └───────────────────────────────────────────────────┘
```

### Services — What's Implemented

| Service | Status | What It Does |
|---------|--------|-------------|
| `TournamentOpsService` | ✅ Working | Master facade — 60 methods, delegates to sub-services |
| `RegistrationService` | ✅ Working | Start/complete/validate/withdraw registration flows |
| `TournamentLifecycleService` | ✅ Working | State machine: draft → registration → live → completed |
| `MatchService` | ✅ Working | Schedule/report/accept/void match results |
| `PaymentOrchestrationService` | ⚠️ Partial | Charge/refund flows exist but EconomyAdapter is stubbed |
| `ResultSubmissionService` | ✅ Working | Player result submissions with opponent confirmation |
| `DisputeService` | ✅ Working | Dispute creation, assignment, evidence, resolution |
| `ReviewInboxService` | ✅ Working | Organizer results inbox with filtering |
| `ResultVerificationService` | ✅ Working | Verify/finalize/dry-run result verification |
| `MatchOpsService` | ✅ Working | Staff match operations (force complete, pause, override) |
| `StaffingService` | ✅ Working | Staff role assignment, referee assignment |
| `ManualSchedulingService` | ✅ Working | Manual match scheduling, bulk shift |
| `SmartRegistrationService` | ⚠️ Partial | Draft creation, form building — some TODOs remain |
| `AuditLogService` | ✅ Working | Operator action audit trail |
| `HelpAndOnboardingService` | ✅ Working | Contextual help content |
| `UserStatsService` | ✅ Working | User stats tracking |
| `TeamStatsService` | ✅ Working | Team stats tracking |
| `MatchHistoryService` | ✅ Working | Match history records |
| `BracketEngineService` | ✅ Working | Pluggable bracket generation (SE/DE/RR/Swiss) |
| `AnalyticsEngineService` | ✅ Working | Analytics snapshots |

### Adapters — What's Wired vs. Stubbed

| Adapter | Status | Notes |
|---------|--------|-------|
| `TeamAdapter` | ✅ Implemented | Talks to teams models |
| `UserAdapter` | ✅ Implemented | Talks to user_profile |
| `GameAdapter` | ✅ Implemented | Talks to apps.games |
| `TournamentAdapter` | ✅ Implemented | Talks to tournaments models |
| `MatchAdapter` | ✅ Implemented | Talks to Match model |
| `SmartRegistrationAdapter` | ✅ Implemented | Talks to smart_registration models |
| `ResultSubmissionAdapter` | ✅ Implemented | Talks to MatchResultSubmission |
| `DisputeAdapter` | ✅ Implemented | Talks to DisputeRecord |
| `ReviewInboxAdapter` | ✅ Implemented | Queries result submissions |
| `StaffingAdapter` | ✅ Implemented | Talks to staffing models |
| `MatchOpsAdapter` | ✅ Implemented | Talks to match ops models |
| `AuditLogAdapter` | ✅ Implemented | Talks to audit log |
| `HelpContentAdapter` | ✅ Implemented | Help content system |
| `UserStatsAdapter` | ✅ Implemented | User stats queries |
| `TeamStatsAdapter` | ✅ Implemented | Team stats queries |
| `TeamRankingAdapter` | ✅ Implemented | Ranking queries |
| `MatchHistoryAdapter` | ✅ Implemented | Match history queries |
| `AnalyticsAdapter` | ✅ Implemented | Analytics queries |
| **`EconomyAdapter`** | ❌ **STUBBED** | Every method returns hardcoded values. TODOs everywhere. |
| **`NotificationAdapter`** | ❌ **STUBBED** | All methods are no-ops. |
| `MatchSchedulingAdapter` | ⚠️ Orphaned | File exists but not exported from `__init__.py` |
| `SchemaValidationAdapter` | ✅ Implemented | Schema validation integration |

### What's Missing / Incomplete

1. **EconomyAdapter** — This is the biggest gap. `charge()`, `refund()`, `get_balance()`, `verify_transaction()` all return hardcoded dummy data. No actual wallet integration.

2. **NotificationAdapter** — All notification calls are swallowed silently. Tournament events don't trigger any user notifications through this path.

3. **Swiss bracket rounds 2+** — The Swiss system generator handles round 1 but subsequent rounds (standings-based pairing, repeat avoidance) are stubbed.

4. **Test coverage** — Only 3 test files for 21 services and 22 adapters. This is critically thin.

5. **Celery beat wiring** — 3 tasks are defined but not added to `CELERY_BEAT_SCHEDULE`. They won't run automatically.

6. **Dispute task bug** — The opponent response reminder task uses the submitter's user ID instead of querying for the actual opponent.

---

## Part C: How the Two Apps Relate Today

### The Intended Relationship

```
Views/Templates → TournamentOpsService → Adapters → Models (in tournaments, teams, games, etc.)
```

### The Reality

The `tournament_ops` services are built but the **views and templates in `apps/tournaments` still bypass them**. The views currently call the old `tournaments/services/` layer directly. The `tournament_ops` layer exists as a parallel path that nothing in production actually calls.

This means:
- There are **two registration services** — `tournaments/services/registration_service.py` (1,710 lines, used in production) and `tournament_ops/services/registration_service.py` (378 lines, not called by views)
- There are **two match services** — same pattern
- The old services have hardcoded game logic; the new services use adapters

### What This Means for Redevelopment

You essentially have two choices:
1. **Rewire the views** to call `tournament_ops` services instead of the old ones
2. **Merge the best patterns** from both into a single clean implementation

Either way, the old direct-model-import services need to be retired.

---

## Part D: Template & Frontend State

### Registration Wizard Templates (24 files)

The registration wizard has **multiple versions** of each step:
- `solo_step1.html` (legacy)
- `solo_step1_new.html` (iteration)
- `solo_step1_enhanced.html` (current production)
- Same pattern for team registration

This creates confusion about which template is actually used in production.

### Hardcoded Game UI

The tournament detail page has blocks like:
```django
{% if game_spec.slug == 'valorant' %}
    <div class="from-red-950/40">...</div>
{% elif game_spec.slug == 'cs2' %}
    <div class="from-orange-950/40">...</div>
{% endif %}
```

Should use `game_spec.primary_color` from the Games app.

### Styling System

Templates use a mix of:
- Tailwind utility classes (primary)
- Scoped `<style>` blocks (per-template)
- Platform design tokens (`tokens.css`)
- Hardcoded colors vs. CSS variables

---

## Summary Scorecard

| Area | Tournaments App | Tournament Ops App |
|------|----------------|-------------------|
| **Models** | 50 models ✅ Complete | 0 models (by design) |
| **Services** | 37+ ✅ Prod-ready but messy | 21 ✅ Clean but partially stubbed |
| **Views** | 30+ ✅ All working | 0 (uses tournaments views) |
| **Templates** | Extensive ✅ But has duplicates | N/A |
| **API endpoints** | 80 URL patterns ✅ | N/A |
| **Tests** | 24 files ⚠️ | 3 files ❌ |
| **Architecture** | Organic/messy ⚠️ | Clean/layered ✅ |
| **Game integration** | Partial ⚠️ (mix of legacy + GameService) | Via GameAdapter ✅ |
| **Team integration** | Direct imports ❌ | Via TeamAdapter ✅ |
| **Economy integration** | Working ✅ (via economy.services) | Stubbed ❌ |
| **Notifications** | Working ✅ (via signals) | Stubbed ❌ |
| **Event publishing** | Stub only ❌ | 14 events defined ✅ |
