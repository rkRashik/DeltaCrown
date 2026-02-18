# Tournament Redevelopment — Master Tracker

*Auto-tracked. Updated at the start and end of every work session.*
*Reference: `02_UPDATED_EXECUTION_PLAN.md` for full details on each task.*

---

## Current Status

| Metric | Value |
|--------|-------|
| **Current Phase** | Phase 6 — Testing & Hardening |
| **Overall Progress** | 100% (50/50 tasks) |
| **Last Updated** | February 18, 2026 |
| **Blockers** | None |
| **Active Plan** | `02_UPDATED_EXECUTION_PLAN.md` (v2) |

---

## Phase Progress

| Phase | Name | Status | Progress | Tasks Done / Total |
|-------|------|--------|----------|-------------------|
| 0 | Cleanup | ✅ Complete | 100% | 7 / 7 |
| 1 | Foundation Wiring | ✅ Complete | 100% | 6 / 6 |
| 1.5 | Admin Modernization | ✅ Complete | 100% | 6 / 6 |
| 2 | Service Consolidation | ✅ Complete | 100% | 6 / 6 |
| 3 | Views & URL Restructure | ✅ Complete | 100% | 5 / 5 |
| 4 | Frontend Rebuild | ✅ Complete | 100% | 11 / 11 |
| 5 | Lifecycle & Automation | ✅ Complete | 100% | 4 / 4 |
| 6 | Testing & Hardening | ✅ Complete | 100% | 5 / 5 |

**Total Tasks: 50**

---

## Phase 0: Cleanup (3-5 days)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 0.1 | Remove legacy Game model from tournaments | ✅ | Removed ~120-line Game class, redirected 19 imports (3 production + 16 test files), created migration `0007_remove_legacy_game_model` |
| 0.2 | Remove all riot_id/steam_id references | ✅ | Replaced ~50+ refs: wizard→GameProfile lookup, DTOs→game_ids dict, 7 templates, seed_form_templates, autofill service |
| 0.3 | Remove backup/deprecated files | ✅ | Deleted `registration_demo_backup/` (12 files) + `marketplace/` (2 files) |
| 0.4 | Consolidate duplicate services | ✅ | Deleted dead code: `analytics.py`, `bracket_generator.py`. Redirected `check_in_service.py` → `checkin_service.py`. `registration.py` vs `registration_service.py` confirmed NOT duplicates |
| 0.5 | Consolidate duplicate models | ✅ | Added deprecation notices to legacy `Dispute` (match.py) and `TournamentStaffRole` (staff.py). Full migration deferred (8+ import sites for Dispute, 6 for StaffPermissionChecker) |
| 0.6 | Fix cross-app FK violations (FK → IntegerField) | ✅ | Converted 9 FKs across 6 files (dispute, form_template, group, lobby, result_submission, team_invitation, permission_request). Created `0008_decouple_cross_app_fks` migration (SeparateDatabaseAndState, faked) |
| 0.7 | Fix tournament_ops adapter field bugs | ✅ | Fixed `TeamDTO.from_model()`: captain via OWNER membership, members via TeamMembership, game via slug property, is_verified via status, logo via `get_effective_logo_url()`. Fixed `UserProfileDTO.from_model()`: email from user.email, email_verified from allauth/is_active, discord from SocialLink, age from date_of_birth. 26 DTO tests pass |

## Phase 1: Foundation Wiring (1 week)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 1.1 | Wire EconomyAdapter to economy.services | ✅ | `charge_registration_fee()` → `debit()` with idempotency keys, `refund_registration_fee()` → `credit()`, `get_balance()` → real balance, `verify_payment()` → DeltaCrownTransaction lookup, `check_health()` → DeltaCrownWallet exists |
| 1.2 | Wire NotificationAdapter to notifications.services | ✅ | `_notify()` central dispatcher → `notifications.services.notify()`, 5 methods: submission_created, dispute_created, evidence_added, dispute_resolved, auto_confirmed. Fire-and-forget with logging |
| 1.3 | Verify & fix TeamAdapter (organizations) | ✅ | Adapter code already clean (uses `get_team_by_any_id`, `organizations.models.Team`). Fixed all test mock targets: `apps.teams.services.team_service.TeamService` → `apps.organizations.services.compat.get_team_by_any_id`, `apps.teams.models._legacy.Team.objects` → `apps.organizations.models.Team.objects`. SimpleNamespace fakes for `from_model()` compat |
| 1.4 | Verify & fix UserAdapter (GameProfile) | ✅ | Adapter code already correct (Phase 0.7 fixed `from_model()`). Fixed test mocks: patched `UserProfileDTO.from_model` + `UserAdapter.get_user_profile` to isolate adapter logic from ORM internals (allauth, SocialLink, GameProfile queries) |
| 1.5 | Wire event publishing (EventBus) | ✅ | Created `events/publishers.py` with 10 helper functions bridging to `apps.core.events` EventBus: tournament (created/published/started/completed), registration (created/confirmed), match (scheduled/completed/result_verified), payment (verified). Discovered 3 separate EventBus singletons (core, common, apps.common) — publishers standardize on core bus |
| 1.6 | Add Celery beat task scheduling | ✅ | Added 3 tasks to `deltacrown/celery.py` beat_schedule: `auto_confirm_submission_task` (every 30 min), `opponent_response_reminder_task` (hourly at :20), `dispute_escalation_task` (every 6h at :45) |

## Phase 1.5: Admin Modernization (3-5 days) — NEW

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 1.5.1 | Install & configure Django Unfold | ✅ | `django-unfold==0.80.0`, INSTALLED_APPS (`unfold`, `unfold.contrib.forms` before `django.contrib.admin`), UNFOLD config with DeltaCrown branding, sidebar nav for all apps |
| 1.5.2 | Custom Admin Dashboard | ✅ | `admin_callbacks.py` dashboard callback: live stats (users, tournaments, teams, revenue), recent activity feed, system health checks |
| 1.5.3 | Tournament Admin Polish | ✅ | `@display` decorators for status badges, game-color pills, inline sections for matches/registrations, organizer hub links |
| 1.5.4 | Rich Form Widgets | ✅ | `admin_widgets.py` with WYSIWYG (UnfoldWYSIWYGWidget), searchable selects, JSON field GUI, custom form Meta classes |
| 1.5.5 | All App Admin Alignment | ✅ | 24+ admin files updated — economy, games, organizations, profile, accounts, challenges, etc. all using `ModelAdmin` from unfold |
| 1.5.6 | Admin User Guide | ✅ | Help text on all major fields, fieldset descriptions, inline admin help for non-tech admins |

## Phase 2: Service Consolidation (2 weeks)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 2.1 | Unified Registration Service | ✅ | Event publishing at 5 transitions: `register_participant` → `registration.created`, `verify_payment` → `registration.confirmed` + `payment.verified`, `approve_registration` → `registration.confirmed`, `cancel_registration` → `registration.cancelled`, `withdraw_registration` → `registration.withdrawn`. All via `transaction.on_commit`. `tournament_ops` docstring clarified as DTO facade. `registration.py` deprecated |
| 2.2 | Unified Match Service | ✅ | Event publishing at 3 transitions: `create_match` → `match.scheduled`, `transition_to_live` → `match.live`, `confirm_result` → `match.completed`. `_publish_match_event()` helper. `tournament_ops` docstring clarified as DTO facade |
| 2.3 | Unified Bracket Service + Swiss completion | ✅ | Full Swiss `generate_subsequent_round()` implementation: score-bracket grouping, multi-key sort (wins/points/buchholz), sliding pair algorithm, `frozenset` repeat avoidance, cross-bracket fallback, bye handling. `_publish_bracket_event()` helper + `bracket.finalized` event |
| 2.4 | Unified Check-In Service | ✅ | `_publish_checkin_event()` helper, events at `check_in` → `checkin.completed` and `undo_check_in` → `checkin.reverted` |
| 2.5 | Unified Analytics Service | ✅ | Bridge methods `get_user_analytics()` and `get_team_analytics()` on canonical `AnalyticsService` — delegates to `AnalyticsEngineService` with full adapter set. `analytics_engine_service.py` docstring clarified |
| 2.6 | Unified Staff Service | ✅ | Legacy `staff.py` models formally deprecated. `StaffPermissionChecker` rewritten: Phase 7 `TournamentStaffAssignment` first, legacy `TournamentStaff` fallback. `_publish_staff_event_to_core()` helper wired at 4 event sites: `staff.assigned_to_tournament`, `staff.removed_from_tournament`, `referee.assigned_to_match`, `referee.unassigned_from_match` |

## Phase 3: Views & URL Restructure (2 weeks)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 3.1 | Create new view files (clean structure) | ✅ | Split monolithic `main.py` (1,142 lines) → `discovery.py` (TournamentListView) + `detail.py` (TournamentDetailView + participant_checkin). Split `organizer.py` (1,380→655 lines) → `organizer_participants.py` (7 FBVs) + `organizer_payments.py` (6 FBVs) + `organizer_matches.py` (5 FBVs). `main.py` → thin redirect. Deleted dead `template_marketplace.py` (288 lines). Fixed unreachable code bug in `_get_registration_status`. |
| 3.2 | Rewrite urls.py (clean URL patterns) | ✅ | Fixed 2 URL name collisions: `registration_success` (resolved via `dynamic_registration_success` alias), `registration_dashboard` (resolved via `registration_management` rename). Removed dead marketplace comments. Updated imports to new split files. 91 unique named patterns, 0 collisions. |
| 3.3 | Registration view rewrite | ✅ | Audited 4 registration implementations. `registration.py` marked deprecated (main wizard URL commented out, payment helpers still active). Removed dead `SoloRegistrationDemoView` import. Removed dead `import requests` from `result_submission.py`. AutoFillService already wired in both active flows (wizard + dynamic). |
| 3.4 | Organizer hub views | ✅ | OrganizerHubView (7 tabs) already clean. All 7 hub templates verified present. FBV extraction was the main cleanup (done in 3.1). Dead dispute FBVs (unimported DisputeService) removed. |
| 3.5 | Verify all URLs (200/302/403 responses) | ✅ | `manage.py check` → 0 issues. URL resolver → 91 patterns, 0 name collisions. Server boots clean, `/healthz/` → HTTP 200. |

## Phase 4: Frontend Rebuild (2-3 weeks) — EXPANDED

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 4.0 | Archive all old tournament frontend files | ✅ | Archived 288 templates + 42 static files to `backups/template_archives/` |
| 4.1 | Build component library (partials) | ✅ | `tournaments/base.html`, 7 component partials (`_status_badge`, `_tournament_card`, `_game_icon`, `_empty_state`, `_pagination`, `_info_bar`, `_tabs`), `tournaments.css`, Tailwind config, Lucide icons CDN |
| 4.2 | Tournament List page (landing) | ✅ | `list.html` — hero carousel, 3-column layout (filters sidebar, card grid, right sidebar), game/status/format filters, search, pagination |
| 4.3 | Tournament Detail page | ✅ | `detailPages/detail.html` — hero section, info bar, tabs, overview/bracket/standings |
| 4.4 | Registration wizard | ✅ | 8 templates: `solo_step1-3`, `solo_success`, `team_step1-3`, `team_success` + form builder templates (`form_step`, `registration_success`, `registration_dashboard`) + 7 ancillary pages (ineligible, status, resubmit_payment, withdraw, 3 error pages) |
| 4.5 | Lobby & match pages | ✅ | 3 templates: `lobby/hub.html`, `match_detail.html`, `submit_result_form.html` |
| 4.6 | Bracket & standings views | ✅ | 4 templates: `bracket.html`, `results.html`, `leaderboard/index.html`, `groups/standings.html` |
| 4.7 | Organizer dashboard (10+ pages) | ✅ | 15+ templates: dashboard, tournament_detail, `_hub_base` + 7 hub tabs (overview, participants, brackets, disputes_enhanced, payments, announcements, settings), create_tournament, pending_results, disputes, health_metrics, groups/config, groups/draw |
| 4.8 | Player section | ✅ | 2 templates: `my_tournaments.html`, `my_matches.html` |
| 4.9 | Spectator hub | ✅ | `spectator/hub.html` — live tournaments, featured matches, recent results, leaderboards |
| 4.10 | Mobile responsiveness pass | ✅ | 5 fixes across 4 files — responsive breakpoints, touch targets, horizontal scroll nav |
| 4.11 | Bug fixes & verification | ✅ | Fixed: RecursionError on /tournaments/ (multi-line `{#` comments with self-include), `NoReverseMatch` (URL names needed `tournaments:` namespace prefix), team media upload 404 (`status=TeamStatus.ACTIVE` → `is_active=True`), PyCharm unfold.contrib import (conditional `_HAS_UNFOLD` guard). `manage.py check` → 0 issues |

## Phase 5: Lifecycle & Automation (1-2 weeks)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 5.1 | Tournament state machine service | ✅ | `lifecycle_service.py` — formal transition graph (16 transitions), guard functions, on-enter callbacks, `transition()` with audit trail, `auto_advance()` / `auto_advance_all()`, `can_transition()` / `allowed_transitions()` |
| 5.2 | Scheduled transitions (Celery) | ✅ | `tasks/lifecycle.py` — 3 Celery tasks: `auto_advance_tournaments` (every 5 min), `check_tournament_wrapup` (hourly), `auto_archive_tournaments` (daily 4 AM). All registered in `celery.py` beat schedule |
| 5.3 | Tournament completion pipeline | ✅ | `completion_pipeline.py` — 5-step orchestrator: standings → winners → certificates → analytics → notifications. `CompletionReport` dataclass, isolated error handling, metadata persisted in `config['completion_pipeline']` |
| 5.4 | Archive generation | ✅ | `archive_service.py` — comprehensive JSON snapshot: tournament, participants, matches, brackets, standings, prizes, groups, statistics. Versioned format, stored in `config['archive']` |

## Phase 6: Testing & Hardening (1-2 weeks)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 6.1 | Adapter unit tests | ✅ | Pure unit tests — 5 test classes (Economy, Notification, Team, User, Tournament), 13 tests, no DB. `unittest.mock.patch` + `SimpleNamespace` fakes |
| 6.2 | Service integration tests | ✅ | DB integration tests for lifecycle_service, completion_pipeline, archive_service. 4 test classes, 15 tests covering transitions, guards, force override, auto-advance, audit trail, pipeline metadata, archive snapshots |
| 6.3 | View tests | ✅ | Public view smoke tests (list, detail) + auth views. 3 test classes, 14 tests — 200/404 status, template selection, context variables, draft visibility, anon access, auth redirects |
| 6.4 | Template rendering tests | ✅ | Parametrized rendering across 8 statuses + edge cases (group_playoff, solo, zero prize, markdown description). 2 test classes, 8 tests |
| 6.5 | Lifecycle integration test (end-to-end) | ✅ | Full happy path: DRAFT→PUBLISHED→REG_OPEN→REG_CLOSED→LIVE→COMPLETED(+pipeline)→ARCHIVED(+archive). 6 tests covering full lifecycle, cancellation, backward prevention, auto-advance chain, pipeline/archive rejections |

---

## Files Changed Log

*Updated after each task completion.*

| Date | Phase.Task | Files Created | Files Modified | Files Deleted |
|------|-----------|---------------|----------------|---------------|
| 2026-02-17 | Planning | `02_UPDATED_EXECUTION_PLAN.md` | `TRACKER.md` | — |
| 2026-02-17 | 0.1 | migration `0007_remove_legacy_game_model` | `tournament.py` (Game class removed), 3 production files + 16 test files (import redirects) | — |
| 2026-02-17 | 0.2 | — | `registration_wizard.py`, `tournament_team_registration.py`, `registration_autofill.py`, `dtos/user.py`, `test_dtos.py`, `test_adapters.py`, `seed_form_templates.py`, 7 templates in `team_registration/` | — |
| 2026-02-17 | 0.3 | — | — | 12 files in `registration_demo_backup/`, 2 files in `marketplace/` |
| 2026-02-17 | 0.4 | — | `check_in_service.py` (→ thin redirect) | `analytics.py`, `bracket_generator.py` |
| 2026-02-17 | 0.5 | — | `match.py` (Dispute deprecation), `staff.py` (TournamentStaffRole deprecation) | — |
| 2026-02-17 | 0.6 | migration `0008_decouple_cross_app_fks` | `dispute.py`, `form_template.py`, `group.py`, `lobby.py`, `result_submission.py`, `team_invitation.py`, `permission_request.py` | — |
| 2026-02-17 | 0.7 | — | `dtos/team.py` (from_model rewrite), `dtos/user.py` (from_model rewrite) | — |
| 2026-02-17 | 1.1 | — | `adapters/economy_adapter.py` (full rewrite: stubs → debit/credit/get_balance wiring) | — |
| 2026-02-17 | 1.2 | — | `adapters/notification_adapter.py` (full rewrite: pass stubs → notify() wiring) | — |
| 2026-02-17 | 1.3-1.4 | — | `tests/test_adapters.py` (fixed all mock targets: team, user, economy, architecture guards) | — |
| 2026-02-17 | 1.5 | `events/publishers.py` | `events/__init__.py` (added publisher exports) | — |
| 2026-02-17 | 1.6 | — | `deltacrown/celery.py` (added 3 tournament_ops beat tasks) | — |
| 2026-02-17 | 1.5.1 | — | `deltacrown/settings.py` (INSTALLED_APPS + UNFOLD config), `requirements.txt` (django-unfold==0.80.0) | — |
| 2026-02-17 | 1.5.2 | `deltacrown/admin_callbacks.py` | `deltacrown/settings.py` (UNFOLD dashboard callback) | — |
| 2026-02-17 | 1.5.3 | — | `apps/tournaments/admin.py` (@display decorators, inlines, status badges) | — |
| 2026-02-17 | 1.5.4 | `deltacrown/admin_widgets.py` | `apps/tournaments/admin.py` (rich form widgets) | — |
| 2026-02-17 | 1.5.5 | — | 24+ admin.py files across all apps (unfold ModelAdmin alignment) | — |
| 2026-02-17 | 1.5.6 | — | Multiple admin.py files (help_text, fieldset descriptions) | — |
| 2026-02-17 | 2.1 | — | `tournaments/services/registration_service.py` (event publishing), `tournament_ops/services/registration_service.py` (docstring), `tournaments/services/registration.py` (deprecated) | — |
| 2026-02-17 | 2.2 | — | `tournaments/services/match_service.py` (event publishing), `tournament_ops/services/match_service.py` (docstring) | — |
| 2026-02-17 | 2.3 | — | `tournament_ops/services/bracket_generators/swiss.py` (full Swiss implementation), `tournaments/services/bracket_service.py` (bracket events) | — |
| 2026-02-17 | 2.4 | — | `tournaments/services/checkin_service.py` (event publishing) | — |
| 2026-02-17 | 2.5 | — | `tournaments/services/analytics_service.py` (bridge methods), `tournament_ops/services/analytics_engine_service.py` (docstring) | — |
| 2026-02-17 | 2.6 | — | `tournaments/models/staff.py` (deprecated), `tournaments/services/staff_permission_checker.py` (Phase 7 rewrite), `tournament_ops/services/staffing_service.py` (core bus wiring) | — |
| 2026-02-17 | 3.1 | `views/discovery.py`, `views/detail.py`, `views/organizer_participants.py`, `views/organizer_payments.py`, `views/organizer_matches.py` | `views/main.py` (→ thin redirect, 1142→18 lines), `views/organizer.py` (1380→655 lines), `views/__init__.py` (updated imports) | `views/template_marketplace.py` (288 lines dead code) |
| 2026-02-17 | 3.2 | — | `urls.py` (split organizer imports, 2 name collisions fixed, marketplace comments removed), `views/dynamic_registration.py` (redirect URL name fix), `templates/registration_dashboard/dashboard.html` (URL name fix) | — |
| 2026-02-17 | 3.3 | — | `views/registration.py` (deprecation header), `urls.py` (removed dead SoloRegistrationDemoView import), `views/result_submission.py` (removed dead `import requests`) | — |
| 2026-02-17 | 4.0 | — | — | 288 templates + 42 static files archived to `backups/template_archives/` |
| 2026-02-17 | 4.1 | `tournaments/base.html`, 7 component partials, `tournaments.css` | `static/siteui/js/tailwind-config.js` | — |
| 2026-02-17 | 4.2 | `tournaments/list.html` | `views/discovery.py` (template_name) | — |
| 2026-02-17 | 4.3 | `tournaments/detailPages/detail.html` | — | — |
| 2026-02-17 | 4.4 | 8 registration wizard templates + 3 form builder + 7 ancillary | — | — |
| 2026-02-17 | 4.5 | `lobby/hub.html`, `match_detail.html`, `submit_result_form.html` | — | — |
| 2026-02-17 | 4.6 | `bracket.html`, `results.html`, `leaderboard/index.html`, `groups/standings.html` | `tournament_tags.py` (added `attr` filter) | — |
| 2026-02-17 | 4.7 | 15+ organizer templates | — | — |
| 2026-02-17 | 4.8 | `my_tournaments.html`, `my_matches.html` | — | — |
| 2026-02-17 | 4.9 | `spectator/hub.html` | — | — |
| 2026-02-17 | 4.10 | — | 4 templates (responsive fixes) | — |
| 2026-02-17 | 4.11 | — | 8 component templates (multi-line comment fix), 36 tournament templates (URL namespace prefix), `team_manage.py` (status→is_active), `settings.py` (conditional unfold), `breadcrumbs.html`, `dashboard/matches.html` | — |
| 2026-02-18 | 4.3+ | — | `detailPages/detail.html` (styling overhaul: glass classes, bg-dc-card, border-white/[0.06], section-card/sidebar-card CSS), `tailwind-config.js` (dc-card→#111111, dc-surface→#0d0d0d, +dc-card-hover) | — |
| 2026-02-18 | 5.1 | `services/lifecycle_service.py` | — | — |
| 2026-02-18 | 5.2 | `tasks/__init__.py`, `tasks/lifecycle.py` | `deltacrown/celery.py` (2 new beat tasks) | — |
| 2026-02-18 | 5.3 | `services/completion_pipeline.py` | — | — |
| 2026-02-18 | 5.4 | `services/archive_service.py` | — | — |
| 2026-02-18 | 6.1 | `tests/test_adapters_unit.py` | — | — |
| 2026-02-18 | 6.2 | `tests/test_service_integration.py` | — | — |
| 2026-02-18 | 6.3 | `tests/test_views_phase6.py` | — | — |
| 2026-02-18 | 6.4 | `tests/test_template_rendering.py` | — | — |
| 2026-02-18 | 6.5 | `tests/test_lifecycle_e2e.py` | — | — |

---

## Decisions Made

*Record every design decision here so we never revisit settled questions.*

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-14 | Keep two-app architecture (tournaments + tournament_ops) | Clear separation: data layer vs logic layer |
| 2026-02-14 | Views stay in tournaments app | They render Django templates, which live in templates/tournaments/ |
| 2026-02-14 | FK → IntegerField for all cross-app team references | Decoupling from frozen teams app |
| 2026-02-14 | Keep Phase 7 staff models, deprecate OG staff models | Capability-based is better than boolean-flags |
| 2026-02-14 | Keep DisputeRecord, remove old Dispute | Phase 6 model is comprehensive |
| 2026-02-14 | Game theming via CSS variables (Game.primary_color) | No hardcoded game colors in templates |
| 2026-02-14 | Events via EventBus, not direct cross-app calls | Decoupled, testable, auditable |
| 2026-02-17 | Use Django Unfold for admin modernization | Best maintained Tailwind-based admin theme in 2025-2026, SaaS-grade UX |
| 2026-02-17 | Complete frontend rebuild from scratch | Old templates (158 files) have too much duplication and legacy patterns; user's demo templates set new design direction |
| 2026-02-17 | Frontend stack: Tailwind CSS + vanilla JS + HTML5 | Modern, no framework dependency, responsive, compatible |
| 2026-02-17 | Admin modernization after Phase 1, before Phase 2 | Admins need usable tools during service consolidation work |
| 2026-02-17 | Archive old templates/static before rebuild | Never delete without backup; `backups/` directory for rollback |
| 2026-02-17 | Demo templates are design references only | `My drafts/tournament_demo/` guides the look; production code goes in `templates/tournaments/` |
| 2026-02-17 | Tracker is the single source of truth | Every task updates TRACKER.md before starting and after completing |

---

## Known Issues / Tech Debt

| Issue | Severity | When to Fix |
|-------|----------|-------------|
| ~~Swiss bracket generator only does Round 1~~ | ~~HIGH~~ | ✅ Fixed in Phase 2, Task 2.3 — full Swiss implementation |
| TournamentOpsService is 3,031 lines | MEDIUM | Future (split into sub-facades) |
| Group stage has hardcoded game logic for 9 games | HIGH | Future refactor |
| No WebSocket for real-time updates | LOW | Future phase |
| Event bus is synchronous (in-memory) | MEDIUM | Future phase (Celery workers) |
| ~~Django Admin is stock — no theme~~ | ~~HIGH~~ | ✅ Fixed in Phase 1.5 — Django Unfold installed |
| ~~158 tournament templates with duplicates/legacy versions~~ | ~~HIGH~~ | ✅ Fixed in Phase 4.0-4.10 — full rebuild from scratch |
| ~~49 scattered tournament static files (CSS/JS)~~ | ~~HIGH~~ | ✅ Fixed in Phase 4.1 — consolidated component library |
| 3 active registration paths writing to 2 different models (Registration vs FormResponse) | HIGH | Future consolidation |
| Dual lobby implementations: checkin.py (Sprint 5) + lobby.py (Sprint 10 v2) | MEDIUM | Phase 4.5 (consolidate during rebuild) |
| `OrganizerTournamentDetailView` unused (replaced by `OrganizerHubView`) | LOW | Can remove class from organizer.py |
| `init_default_games.py` mgmt command is entirely broken (refs Game fields that don't exist) | MEDIUM | Phase 1 |
| ~~`test_adapters.py` has stale mock targets~~ | ~~MEDIUM~~ | ✅ Fixed in Phase 1 (Tasks 1.3-1.4) |
| ~~EconomyAdapter is fully stubbed~~ | ~~HIGH~~ | ✅ Fixed in Phase 1, Task 1.1 |
| ~~NotificationAdapter is fully no-op~~ | ~~MEDIUM~~ | ✅ Fixed in Phase 1, Task 1.2 |
| ~~3 separate EventBus singletons — events fragmented~~ | ~~HIGH~~ | ✅ Fixed in Phase 2 — all new event publishing standardized on core bus |
| Legacy Dispute model still has 8+ production import sites | MEDIUM | Future (full migration when refactoring dispute system) |
| ~~Legacy TournamentStaffRole still has 6 import sites~~ | ~~MEDIUM~~ | ✅ Fixed in Phase 2, Task 2.6 — StaffPermissionChecker uses Phase 7 models, OG deprecated |

---

## Design References

| File | Purpose |
|------|---------|
| `templates/My drafts/tournament_demo/list_demo.html` | Visual reference for tournament list page (Phase 4.2) |
| `templates/My drafts/tournament_demo/tournamnt_detail_demo.html` | Visual reference for tournament detail page (Phase 4.3) |
