# Frontend Tournament Implementation Checklist

**Date**: November 15, 2025  
**Purpose**: Simple task tracking for frontend tournament implementation  
**Status**: Planning Complete, Implementation Pending

---

## Task Table

| ID | Name | Sprint | Priority | Status | Notes |
|----|------|--------|----------|--------|-------|
| **FE-T-001** | Tournament List Page | Sprint 1 | P0 | TODO | Discovery page, filters, search |
| **FE-T-002** | Tournament Detail Page | Sprint 1 | P0 | TODO | State-based rendering (before/during/after) |
| **FE-T-003** | Registration Entry Point | Sprint 1 | P0 | TODO | Dynamic CTA button on detail page |
| **FE-T-004** | Registration Wizard | Sprint 1 | P0 | TODO | Team permission selector (backend ✅) |
| **FE-T-005** | My Tournaments Widget | Sprint 2 | P1 | TODO | Dashboard card with upcoming/live summary |
| **FE-T-007** | Tournament Lobby | Sprint 2 | P0 | BLOCKED | Participant hub - needs lobby API backend |
| **FE-T-008** | Live Bracket View | Sprint 3 | P0 | TODO | Bracket tree + schedule list |
| **FE-T-009** | Match Detail / Lobby | Sprint 3 | P0 | BLOCKED | Score reporting needs backend API |
| **FE-T-010** | Tournament Leaderboard | Sprint 3 | P0 | TODO | Real-time polling with HTMX |
| **FE-T-011** | Group Configuration | Sprint 4 | P0 | BLOCKED | Needs group stage models + service backend |
| **FE-T-012** | Live Group Draw | Sprint 4 | P1 | BLOCKED | Needs group stage service backend |
| **FE-T-013** | Group Standings | Sprint 4 | P0 | BLOCKED | Needs group stage models + API backend |
| **FE-T-014** | Match Result Submission | Sprint 3 | P0 | BLOCKED | Needs match result API backend |
| **FE-T-015** | Organizer Approval | Sprint 5 | P0 | BLOCKED | Needs match result approval backend |
| **FE-T-016** | Dispute Submission | Sprint 3 | P1 | BLOCKED | Needs dispute models + API backend |
| **FE-T-017** | Dispute Resolution | Sprint 5 | P1 | BLOCKED | Needs dispute resolution backend |
| **FE-T-018** | Final Results Page | Sprint 3 | P0 | TODO | Podium, summary, certificate CTA |
| **FE-T-020** | Organizer Dashboard | Sprint 5 | P0 | TODO | Hosted tournaments list |
| **FE-T-021** | Manage Tournament | Sprint 5 | P0 | TODO | Participants, payments, match controls |

---

## Sprint Planning

### Sprint 1: Discovery & Registration (Weeks 1-2)
**Goal**: Allow users to browse and register for tournaments

**Tasks**:
- FE-T-001: Tournament List Page
- FE-T-002: Tournament Detail Page
- FE-T-003: Registration Entry Point
- FE-T-004: Registration Wizard (with team permission selector)

**Deliverables**:
- `/tournaments/` (discovery page)
- `/tournaments/<slug>/` (detail page)
- `/tournaments/<slug>/register/` (registration wizard)
- Registration success/error pages

**Backend Dependencies**:
- ✅ Team registration permissions (MODULE_TOURNAMENT_REGISTRATION_ALIGNMENT_COMPLETION.md)
- ✅ Registration service validation (registration_service.py)
- ✅ GET /api/tournaments/discovery/
- ✅ GET /api/tournaments/<slug>/
- ✅ POST /api/tournaments/<slug>/register/

**Status**: ✅ **READY TO START**

---

### Sprint 2: Lobby & Dashboard (Week 3)
**Goal**: Provide participant hub and dashboard integration

**Tasks**:
- FE-T-005: My Tournaments Widget
- FE-T-007: Tournament Lobby

**Deliverables**:
- Dashboard tournament card
- `/tournaments/<slug>/lobby/` (participant hub)

**Backend Dependencies**:
- ✅ GET /api/tournaments/user/<user_id>/active/ (likely exists)
- ⏸️ GET /api/tournaments/<slug>/lobby/ (NEW - pending)
- ⏸️ POST /api/tournaments/<slug>/check-in/ (NEW - pending)
- ⏸️ GET /api/tournaments/<slug>/lobby/roster/ (NEW - pending)
- ⏸️ GET /api/tournaments/<slug>/lobby/announcements/ (NEW - pending)

**Status**: ⏸️ **BLOCKED on lobby API backend**

---

### Sprint 3: Live Tournament Views (Weeks 4-5)
**Goal**: Enable live tournament participation and spectating

**Tasks**:
- FE-T-008: Live Bracket View
- FE-T-009: Match Detail / Lobby
- FE-T-010: Tournament Leaderboard
- FE-T-014: Match Result Submission (if backend ready)
- FE-T-016: Dispute Submission (if backend ready)
- FE-T-018: Final Results Page

**Deliverables**:
- `/tournaments/<slug>/bracket/` (bracket view)
- `/tournaments/<slug>/matches/<id>/` (match detail)
- `/tournaments/<slug>/leaderboard/` (leaderboard)
- `/tournaments/<slug>/results/` (final results)
- Score reporting modal (if backend ready)
- Dispute submission modal (if backend ready)

**Backend Dependencies**:
- ✅ GET /api/tournaments/<slug>/bracket/ (likely exists)
- ✅ GET /api/tournaments/<slug>/matches/<id>/ (likely exists)
- ✅ GET /api/tournaments/<slug>/leaderboard/ (likely exists)
- ✅ GET /api/tournaments/<slug>/results/ (likely exists)
- ⏸️ POST /api/tournaments/<slug>/matches/<id>/report-score/ (NEW - pending)
- ⏸️ POST /api/tournaments/<slug>/matches/<id>/dispute/ (NEW - pending)

**Status**: ⚠️ **PARTIALLY READY** (FE-T-008, 010, 018 can start; FE-T-009, 014, 016 blocked)

---

### Sprint 4: Group Stages (Week 6)
**Goal**: Support group stage tournaments (all 9 games)

**Tasks**:
- FE-T-011: Group Configuration
- FE-T-012: Live Group Draw
- FE-T-013: Group Standings

**Deliverables**:
- `/dashboard/organizer/tournaments/<slug>/groups/config/` (config interface)
- `/dashboard/organizer/tournaments/<slug>/groups/draw/` (live draw)
- `/tournaments/<slug>/groups/` (standings page)

**Backend Dependencies**:
- ⏸️ Group stage models (TBD)
- ⏸️ Group stage service (TBD)
- ⏸️ POST /api/organizer/tournaments/<slug>/groups/configure/ (NEW - pending)
- ⏸️ POST /api/organizer/tournaments/<slug>/groups/generate/ (NEW - pending)
- ⏸️ GET /api/organizer/tournaments/<slug>/groups/draw/ (NEW - pending)
- ⏸️ POST /api/organizer/tournaments/<slug>/groups/draw/next/ (NEW - pending)
- ⏸️ POST /api/organizer/tournaments/<slug>/groups/draw/finalize/ (NEW - pending)
- ⏸️ GET /api/tournaments/<slug>/groups/standings/ (NEW - pending)
- ⏸️ GET /api/tournaments/<slug>/groups/<group_id>/matches/ (NEW - pending)

**Status**: ⏸️ **FULLY BLOCKED on backend group stage implementation**

---

### Sprint 5: Organizer Tools (Week 7)
**Goal**: Provide comprehensive tournament management for organizers

**Tasks**:
- FE-T-015: Organizer Match Approval
- FE-T-017: Dispute Resolution
- FE-T-020: Organizer Dashboard
- FE-T-021: Manage Tournament

**Deliverables**:
- `/dashboard/organizer/` (organizer dashboard)
- `/dashboard/organizer/tournaments/<slug>/` (manage tournament)
- `/dashboard/organizer/tournaments/<slug>/disputes/<id>/` (resolve dispute)
- Match approval interface
- Dispute resolution interface

**Backend Dependencies**:
- ✅ GET /api/organizer/tournaments/ (likely exists)
- ✅ GET /api/organizer/tournaments/<slug>/ (likely exists)
- ✅ POST /api/organizer/tournaments/<slug>/start/ (likely exists)
- ✅ POST /api/organizer/tournaments/<slug>/pause/ (likely exists)
- ✅ POST /api/organizer/tournaments/<slug>/cancel/ (likely exists)
- ✅ GET /api/organizer/tournaments/<slug>/participants/ (likely exists)
- ✅ POST /api/organizer/tournaments/<slug>/participants/<id>/remove/ (likely exists)
- ✅ GET /api/organizer/tournaments/<slug>/payments/ (likely exists)
- ✅ PATCH /api/organizer/matches/<match_id>/reschedule/ (likely exists)
- ✅ POST /api/organizer/matches/<match_id>/override-score/ (exists in Module 8.1)
- ⏸️ POST /api/organizer/matches/<match_id>/approve/ (NEW - pending)
- ⏸️ GET /api/organizer/tournaments/<slug>/disputes/ (NEW - pending)
- ⏸️ GET /api/organizer/tournaments/<slug>/disputes/<id>/ (NEW - pending)
- ⏸️ POST /api/organizer/tournaments/<slug>/disputes/<id>/resolve/ (NEW - pending)

**Status**: ⚠️ **PARTIALLY READY** (FE-T-020, 021 can start; FE-T-015, 017 blocked)

---

## Status Legend

- **TODO**: Ready to implement, no blockers
- **IN_PROGRESS**: Currently being worked on
- **DONE**: Implementation complete, tested
- **BLOCKED**: Waiting on backend dependency

---

## Summary

### Ready to Start (6 items)
- ✅ **Sprint 1** (4 items): FE-T-001, 002, 003, 004
- ✅ **Sprint 3** (3 items): FE-T-008, 010, 018
- ✅ **Sprint 5** (2 items): FE-T-020, 021

### Blocked (9 items)
- ⏸️ **Sprint 2** (2 items): FE-T-005 (maybe ready?), FE-T-007 (blocked on lobby API)
- ⏸️ **Sprint 3** (3 items): FE-T-009 (partial), 014, 016 (blocked on match result/dispute APIs)
- ⏸️ **Sprint 4** (3 items): FE-T-011, 012, 013 (blocked on group stage backend)
- ⏸️ **Sprint 5** (2 items): FE-T-015, 017 (blocked on match approval/dispute resolution)

### Total: 19 items (10 P0, 4 P1, 5 P2 excluded from checklist)

---

## Next Actions

1. **Green-light Sprint 1**: Confirm FE-T-001 to FE-T-004 ready to implement
2. **Backend coordination**: Share list of blocked APIs with backend team
3. **Start FE-T-001**: Begin with tournament list page as foundation
4. **Parallel backend work**: Backend team starts lobby API + group stage models
5. **Weekly sync**: Review progress, unblock items as backend APIs complete

---

**Related Documents**:
- [Tournament Backlog](../Backlog/FRONTEND_TOURNAMENT_BACKLOG.md) - Feature specifications
- [Tournament Sitemap](../Screens/FRONTEND_TOURNAMENT_SITEMAP.md) - URL structure
- [Tournament Trace](FRONTEND_TOURNAMENT_TRACE.yml) - Traceability map
- [Testing Strategy](FRONTEND_TOURNAMENT_TESTING_STRATEGY.md) - QA approach
