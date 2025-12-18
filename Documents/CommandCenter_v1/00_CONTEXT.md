# 00_CONTEXT.md

**Initiative:** DeltaCrown Command Center + Lobby Room v1  
**Date:** December 19, 2025  
**Status:** Planning Phase

---

## 1. What is DeltaCrown?

DeltaCrown is a competitive esports tournament platform that enables organizers to create, manage, and operate tournaments while providing participants with registration, check-in, match participation, and results tracking capabilities.

**Technology Stack:**
- **Backend:** Django 4.x/5.x with PostgreSQL
- **Frontend:** Django Templates + Tailwind CSS + Vanilla JavaScript
- **Architecture:** Service-oriented with headless tournament_ops orchestration layer

**Note:** This platform does NOT use React, Next.js, or other JavaScript frameworks. All frontend is server-rendered Django templates with progressive enhancement via vanilla JS.

---

## 2. What is "Command Center"?

**Command Center** refers to the organizer operations interface - the control panel where tournament organizers manage their tournaments.

**Core Responsibilities:**
- **Registration Management:** Approve/reject participant registrations, verify payments
- **Match Management:** Schedule matches, record results, handle forfeits/cancellations
- **Results Management:** Confirm/reject/override match results submitted by participants
- **Dispute Resolution:** Review and resolve disputes raised by participants
- **Check-In Management:** Monitor participant check-in status, manually toggle check-in
- **Roster Management:** View participant lists, export rosters
- **Tournament Operations:** Bracket generation, seeding, tournament lifecycle management

**Current Implementation:**
- URL namespace: `/tournaments/<slug>/organizer/*`
- Views: `apps/tournaments/views/organizer.py`, `organizer_results.py`, `disputes_management.py`
- Templates: `templates/tournaments/organizer/*`

---

## 3. What is "Lobby Room"?

**Lobby Room** refers to the participant-facing interface - the hub where registered players/teams interact before and during tournaments.

**Core Responsibilities:**
- **Check-In:** Participants check in during the check-in window before tournament starts
- **Roster Display:** View list of all participants with check-in status
- **Announcements:** Receive organizer announcements and tournament updates
- **Match Information:** View upcoming matches, schedules, and lobby details
- **Result Submission:** Submit match results and evidence
- **Dispute Submission:** Report disputes on match results

**Current Implementation:**
- URL namespace: `/tournaments/<slug>/lobby/`, `/tournaments/<slug>/matches/*`
- Views: `apps/tournaments/views/checkin.py`, `lobby.py`, `result_submission.py`, `live.py`
- Templates: `templates/tournaments/lobby/*`, `templates/tournaments/public/live/*`

---

## 4. Initiative Scope

**Objective:** Consolidate and enhance the Command Center and Lobby Room experiences with:
1. Unified organizer dashboard (Command Center)
2. Unified participant hub (Lobby Room)
3. Consistent service layer usage across all operations
4. Real-time updates via HTMX/WebSockets
5. Professional UI/UX with Tailwind CSS

**Out of Scope:**
- Migrating to React/Next.js
- Rewriting tournament_ops orchestration layer
- Public spectator views (live bracket, match watch)
- Tournament creation/editing workflows

---

## 5. Why This Initiative?

**Current Issues:**
1. **Architectural Inconsistency:** Organizer views bypass service layer and manipulate ORM directly, while participant views properly use service layer
2. **Fragmented UI:** Multiple separate pages for related operations instead of unified dashboards
3. **Missing Real-Time Updates:** No live updates for roster changes, match results, disputes
4. **Incomplete Features:** Result submission and dispute flows have TODO comments indicating incomplete implementation
5. **Poor Code Maintainability:** Business logic scattered in view functions instead of centralized in services

**Business Impact:**
- Organizer confusion: Multiple pages to manage simple workflows
- Participant frustration: Stale data without real-time updates
- Developer friction: Duplicated logic, untestable view code
- Risk of bugs: Direct ORM manipulation bypasses validation and audit logging

---

## 6. Success Criteria

1. **Unified Dashboards:**
   - Command Center: Single organizer dashboard for all tournament operations
   - Lobby Room: Single participant hub for check-in, roster, announcements, matches

2. **Service Layer Consistency:**
   - All organizer actions delegate to service methods (no direct ORM .save())
   - All participant actions delegate to service methods (maintain current pattern)

3. **Real-Time Experience:**
   - Live roster updates as participants check in
   - Live match result updates
   - Live dispute notifications for organizers

4. **Complete Features:**
   - Result submission workflow fully implemented
   - Dispute submission workflow fully implemented
   - Backend API integration points completed

5. **Professional UI/UX:**
   - Tailwind-based responsive design
   - Consistent color scheme and typography
   - Accessible (WCAG 2.1 AA)
   - Fast page loads (<2s)

---

## 7. Stakeholders

**Primary Users:**
- **Tournament Organizers:** Need efficient tools to manage registrations, matches, results, disputes
- **Tournament Participants:** Need clear check-in process, match information, result submission

**Technical Stakeholders:**
- **Backend Team:** Maintain service layer architecture, ensure business logic is testable
- **Frontend Team:** Build responsive UIs with Django templates + Tailwind
- **QA Team:** Validate workflows end-to-end

---

## 8. Key Constraints

**Technical:**
- MUST use Django Templates (no React/Next.js)
- MUST use existing service layer (no new framework)
- MUST maintain tournament_ops integration points
- MUST preserve existing URL patterns (backward compatibility)

**Timeline:**
- Phase 0-1: 2-3 weeks (planning + service refactor)
- Phase 2: 2-3 weeks (Command Center UI)
- Phase 3: 2-3 weeks (Lobby Room UI + real-time)

**Resources:**
- 1 backend developer (service layer refactoring)
- 1 frontend developer (template + Tailwind implementation)
- 1 QA engineer (testing + validation)

---

**End of Context**
