# Tournament Redevelopment — Master Tracker

*Auto-tracked. Updated at the start and end of every work session.*
*Reference: `02_UPDATED_EXECUTION_PLAN.md` for full details on each task.*

---

## Current Status

| Metric | Value |
|--------|-------|
| **Current Phase** | Phase 1 — Complete ✅ |
| **Overall Progress** | 26% (13/50 tasks) |
| **Last Updated** | February 17, 2026 |
| **Blockers** | None |
| **Active Plan** | `02_UPDATED_EXECUTION_PLAN.md` (v2) |

---

## Phase Progress

| Phase | Name | Status | Progress | Tasks Done / Total |
|-------|------|--------|----------|-------------------|
| 0 | Cleanup | ✅ Complete | 100% | 7 / 7 |
| 1 | Foundation Wiring | ✅ Complete | 100% | 6 / 6 |
| 1.5 | Admin Modernization | ⬜ Not Started | 0% | 0 / 6 |
| 2 | Service Consolidation | ⬜ Not Started | 0% | 0 / 6 |
| 3 | Views & URL Restructure | ⬜ Not Started | 0% | 0 / 5 |
| 4 | Frontend Rebuild | ⬜ Not Started | 0% | 0 / 11 |
| 5 | Lifecycle & Automation | ⬜ Not Started | 0% | 0 / 4 |
| 6 | Testing & Hardening | ⬜ Not Started | 0% | 0 / 5 |

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
| 1.5.1 | Install & configure Django Unfold | ⬜ | Package install, INSTALLED_APPS, base theme (colors, branding, sidebar) |
| 1.5.2 | Custom Admin Dashboard | ⬜ | Visual command center: stats, recent activity, system health |
| 1.5.3 | Tournament Admin Polish | ⬜ | Status badges, game colors, inline sections, organizer links |
| 1.5.4 | Rich Form Widgets | ⬜ | WYSIWYG descriptions, searchable selects, JSON field GUI |
| 1.5.5 | All App Admin Alignment | ⬜ | Unfold styling for ALL apps (economy, games, orgs, profile, etc.) |
| 1.5.6 | Admin User Guide | ⬜ | Tooltips, field descriptions, inline help for non-tech admins |

## Phase 2: Service Consolidation (2 weeks)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 2.1 | Unified Registration Service | ⬜ | Merge old (1,710 lines) + new (378 lines) |
| 2.2 | Unified Match Service | ⬜ | Single service with event publishing |
| 2.3 | Unified Bracket Service + Swiss completion | ⬜ | Complete Swiss Rounds 2+ |
| 2.4 | Unified Check-In Service | ⬜ | |
| 2.5 | Unified Analytics Service | ⬜ | |
| 2.6 | Unified Staff Service | ⬜ | Phase 7 models, deprecate OG |

## Phase 3: Views & URL Restructure (2 weeks)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 3.1 | Create new view files (clean structure) | ⬜ | |
| 3.2 | Rewrite urls.py (clean URL patterns) | ⬜ | |
| 3.3 | Registration view rewrite | ⬜ | GameProfile auto-fill |
| 3.4 | Organizer hub views | ⬜ | |
| 3.5 | Verify all URLs (200/302/403 responses) | ⬜ | |

## Phase 4: Frontend Rebuild (2-3 weeks) — EXPANDED

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 4.0 | Archive all old tournament frontend files | ⬜ | Move 158 templates + 49 static files to `backups/` |
| 4.1 | Build component library (partials) | ⬜ | Base layout, navbar, cards, badges, modals, status pills, forms |
| 4.2 | Tournament List page (landing) | ⬜ | Reference: `list_demo.html` |
| 4.3 | Tournament Detail page | ⬜ | Reference: `tournamnt_detail_demo.html` |
| 4.4 | Registration wizard | ⬜ | Multi-step, GameProfile auto-fill, persistent draft |
| 4.5 | Lobby & match pages | ⬜ | Check-in, match cards, live scores, result submit |
| 4.6 | Bracket & standings views | ⬜ | Visual bracket, group tables, Swiss pairings |
| 4.7 | Organizer dashboard (10+ pages) | ⬜ | Overview, participants, brackets, matches, payments, disputes, etc. |
| 4.8 | Player section | ⬜ | My tournaments, my matches, my results |
| 4.9 | Archive view | ⬜ | Past tournaments with search/filter |
| 4.10 | Mobile responsiveness pass | ⬜ | All pages on mobile/tablet/desktop |

## Phase 5: Lifecycle & Automation (1-2 weeks)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 5.1 | Tournament state machine service | ⬜ | |
| 5.2 | Scheduled transitions (Celery) | ⬜ | |
| 5.3 | Tournament completion pipeline | ⬜ | |
| 5.4 | Archive generation | ⬜ | |

## Phase 6: Testing & Hardening (1-2 weeks)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 6.1 | Adapter unit tests | ⬜ | |
| 6.2 | Service integration tests | ⬜ | |
| 6.3 | View tests | ⬜ | |
| 6.4 | Template rendering tests | ⬜ | All new templates render without errors |
| 6.5 | Lifecycle integration test (end-to-end) | ⬜ | |

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
| Swiss bracket generator only does Round 1 | HIGH | Phase 2, Task 2.3 |
| TournamentOpsService is 3,031 lines | MEDIUM | Phase 2 (split into sub-facades) |
| Group stage has hardcoded game logic for 9 games | HIGH | Phase 2, Task 2.3 |
| No WebSocket for real-time updates | LOW | Future phase |
| Event bus is synchronous (in-memory) | MEDIUM | Future phase (Celery workers) |
| Django Admin is stock — no theme | HIGH | Phase 1.5 (Django Unfold) |
| 158 tournament templates with duplicates/legacy versions | HIGH | Phase 4.0 (archive) + Phase 4.1-4.10 (rebuild) |
| 49 scattered tournament static files (CSS/JS) | HIGH | Phase 4.0 (archive) + Phase 4.1-4.10 (rebuild) |
| `init_default_games.py` mgmt command is entirely broken (refs Game fields that don't exist) | MEDIUM | Phase 1 |
| ~~`test_adapters.py` has stale mock targets~~ | ~~MEDIUM~~ | ✅ Fixed in Phase 1 (Tasks 1.3-1.4) |
| ~~EconomyAdapter is fully stubbed~~ | ~~HIGH~~ | ✅ Fixed in Phase 1, Task 1.1 |
| ~~NotificationAdapter is fully no-op~~ | ~~MEDIUM~~ | ✅ Fixed in Phase 1, Task 1.2 |
| 3 separate EventBus singletons (core, common, apps.common) — events fragmented | HIGH | Phase 2 (standardize on core bus) |
| Legacy Dispute model still has 8+ production import sites | MEDIUM | Phase 2 |
| Legacy TournamentStaffRole still has 6 import sites | MEDIUM | Phase 2 |

---

## Design References

| File | Purpose |
|------|---------|
| `templates/My drafts/tournament_demo/list_demo.html` | Visual reference for tournament list page (Phase 4.2) |
| `templates/My drafts/tournament_demo/tournamnt_detail_demo.html` | Visual reference for tournament detail page (Phase 4.3) |
