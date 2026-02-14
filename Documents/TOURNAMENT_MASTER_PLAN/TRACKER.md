# Tournament Redevelopment — Master Tracker

*Auto-tracked. Updated at the start and end of every work session.*

---

## Current Status

| Metric | Value |
|--------|-------|
| **Current Phase** | Phase 0 — Not Started |
| **Overall Progress** | 0% |
| **Last Updated** | February 14, 2026 |
| **Blockers** | None |

---

## Phase Progress

| Phase | Status | Progress | Tasks Done / Total |
|-------|--------|----------|-------------------|
| 0: Cleanup | ⬜ Not Started | 0% | 0 / 7 |
| 1: Foundation Wiring | ⬜ Not Started | 0% | 0 / 6 |
| 2: Service Consolidation | ⬜ Not Started | 0% | 0 / 6 |
| 3: Views & URL Restructure | ⬜ Not Started | 0% | 0 / 5 |
| 4: Template Rebuild | ⬜ Not Started | 0% | 0 / 9 |
| 5: Lifecycle & Automation | ⬜ Not Started | 0% | 0 / 4 |
| 6: Testing & Hardening | ⬜ Not Started | 0% | 0 / 5 |

---

## Phase 0: Cleanup — Task Detail

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 0.1 | Remove legacy Game model from tournaments | ⬜ | |
| 0.2 | Remove all riot_id/steam_id references | ⬜ | |
| 0.3 | Remove backup/deprecated files | ⬜ | |
| 0.4 | Consolidate duplicate services | ⬜ | |
| 0.5 | Consolidate duplicate models | ⬜ | |
| 0.6 | Fix cross-app FK violations (FK → IntegerField) | ⬜ | |
| 0.7 | Fix tournament_ops adapter field bugs | ⬜ | |

## Phase 1: Foundation Wiring — Task Detail

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 1.1 | Wire EconomyAdapter to economy.services | ⬜ | |
| 1.2 | Wire NotificationAdapter to notifications.services | ⬜ | |
| 1.3 | Verify & fix TeamAdapter (organizations) | ⬜ | |
| 1.4 | Verify & fix UserAdapter (GameProfile) | ⬜ | |
| 1.5 | Wire event publishing (EventBus) | ⬜ | |
| 1.6 | Add Celery beat task scheduling | ⬜ | |

## Phase 2: Service Consolidation — Task Detail

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 2.1 | Unified Registration Service | ⬜ | |
| 2.2 | Unified Match Service | ⬜ | |
| 2.3 | Unified Bracket Service + Swiss completion | ⬜ | |
| 2.4 | Unified Check-In Service | ⬜ | |
| 2.5 | Unified Analytics Service | ⬜ | |
| 2.6 | Unified Staff Service | ⬜ | |

## Phase 3: Views & URL Restructure — Task Detail

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 3.1 | Create new view files (clean structure) | ⬜ | |
| 3.2 | Rewrite urls.py (clean URL patterns) | ⬜ | |
| 3.3 | Registration view rewrite | ⬜ | |
| 3.4 | Organizer hub views | ⬜ | |
| 3.5 | Verify all URLs (200/302/403 responses) | ⬜ | |

## Phase 4: Template Rebuild — Task Detail

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 4.1 | Build component library (partials) | ⬜ | |
| 4.2 | Build browse & detail pages | ⬜ | |
| 4.3 | Build registration wizard templates | ⬜ | |
| 4.4 | Build lobby & match pages | ⬜ | |
| 4.5 | Build bracket & standings views | ⬜ | |
| 4.6 | Build organizer dashboard (10 pages) | ⬜ | |
| 4.7 | Build player section (my tournaments/matches/results) | ⬜ | |
| 4.8 | Build archive view | ⬜ | |
| 4.9 | Delete all old templates | ⬜ | |

## Phase 5: Lifecycle & Automation — Task Detail

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 5.1 | Tournament state machine service | ⬜ | |
| 5.2 | Scheduled transitions (Celery) | ⬜ | |
| 5.3 | Tournament completion pipeline | ⬜ | |
| 5.4 | Archive generation | ⬜ | |

## Phase 6: Testing & Hardening — Task Detail

| ID | Task | Status | Notes |
|----|------|--------|-------|
| 6.1 | Adapter unit tests | ⬜ | |
| 6.2 | Service integration tests | ⬜ | |
| 6.3 | View tests | ⬜ | |
| 6.4 | Template rendering tests | ⬜ | |
| 6.5 | Lifecycle integration test (end-to-end) | ⬜ | |

---

## Files Changed Log

*Updated after each task completion.*

| Date | Phase.Task | Files Created | Files Modified | Files Deleted |
|------|-----------|---------------|----------------|---------------|
| | | | | |

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

---

## Known Issues / Tech Debt

| Issue | Severity | When to Fix |
|-------|----------|-------------|
| Swiss bracket generator only does Round 1 | HIGH | Phase 2, Task 2.3 |
| TournamentOpsService is 3,031 lines | MEDIUM | Phase 2 (split into sub-facades) |
| Group stage has hardcoded game logic for 9 games | HIGH | Phase 2, Task 2.3 |
| No WebSocket for real-time updates | LOW | Future phase |
| Event bus is synchronous (in-memory) | MEDIUM | Future phase (Celery workers) |
