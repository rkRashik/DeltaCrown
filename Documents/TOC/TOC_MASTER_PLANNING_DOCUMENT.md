# Tournament Operations Center (TOC) — Master Planning Document

**Version:** 1.5 (Pro-Circuit Patch)
**Date:** 2026-02-23
**Last Revised:** 2026-02-23 — Pro-Circuit Patch (4 additions) + Apex Industry Standards (5) + Final Enterprise Closure (6) + Operational UX Tools (5) + Tier-1 Enterprise Additions (8)
**Purpose:** Complete architecture audit and feature specification for the Tournament Operations Center. This document covers ALL backend logic, data flows, features, workflows, tools, and database interactions. This is the authoritative source of truth for what the TOC must do before any UI/UX work begins.

**Scope:** Backend logic, data models, service layers, API endpoints, workflows, state machines, edge cases, and integration points ONLY. No CSS, styling, layouts, or visual design.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Pillar 1 — Tournament Lifecycle & State Machine](#2-pillar-1--tournament-lifecycle--state-machine)
3. [Pillar 2 — Registration & Participant Management](#3-pillar-2--registration--participant-management)
4. [Pillar 3 — Financial Operations (Payments, Refunds, Prize Distribution)](#4-pillar-3--financial-operations)
5. [Pillar 4 — The Competition Engine (Brackets, Draws & Scheduling)](#5-pillar-4--the-competition-engine)
6. [Pillar 5 — Live Match Operations & Match Medic](#6-pillar-5--live-match-operations--match-medic)
7. [Pillar 6 — Disputes, Evidence & Resolution](#7-pillar-6--disputes-evidence--resolution)
8. [Pillar 7 — Tournament Configuration & Communications](#8-pillar-7--tournament-configuration--communications)
9. [Pillar 8 — Data, Stats & Leaderboards](#9-pillar-8--data-stats--leaderboards)
10. [Pillar 9 — Staff & Role-Based Access Control (RBAC)](#10-pillar-9--staff--role-based-access-control)
11. [Pillar 10 — Economy Integration (DeltaCoin & Wallets)](#11-pillar-10--economy-integration)
12. [Pillar 11 — Audit Trail, Versioning & Compliance](#12-pillar-11--audit-trail-versioning--compliance)
13. [Pillar 12 — Real-Time & WebSocket Architecture](#13-pillar-12--real-time--websocket-architecture)
14. [Cross-Cutting Concerns](#14-cross-cutting-concerns)
15. [Gap Analysis — What Exists vs What's Needed](#15-gap-analysis)
16. [Database Schema Inventory](#16-database-schema-inventory)
17. [API Endpoint Inventory](#17-api-endpoint-inventory)
18. [Edge Cases & Tier-1 Esports Requirements](#18-edge-cases--tier-1-esports-requirements)

---

## 1. System Overview

### 1.1 What Is the TOC?

The Tournament Operations Center (TOC) is the **organizer-facing command center** for managing every aspect of a tournament's lifecycle. It is a 9-tab hub at `/tournaments/organizer/<slug>/` powered by `OrganizerHubView`.

The TOC is NOT the public tournament page — it is the equivalent of a **tournament admin dashboard** that only the organizer, co-organizers, and assigned staff members can access.

### 1.2 Current Architecture

| Layer | Component | File |
|-------|-----------|------|
| **View** | `OrganizerHubView` (CBV, 9 tab methods) | `apps/tournaments/views/organizer.py` |
| **View** | FBV endpoints (approve, reject, verify, etc.) | `apps/tournaments/views/organizer_participants.py` |
| **Service** | `CommandCenterService` (alerts, lifecycle, events) | `apps/tournaments/services/command_center_service.py` |
| **Service** | `RegistrationVerificationService` (7 auto-checks) | `apps/tournaments/services/registration_verification.py` |
| **Service** | `CheckinService` (check-in/undo/bulk/toggle) | `apps/tournaments/services/checkin_service.py` |
| **Service** | `StaffPermissionChecker` (RBAC dual-path) | `apps/tournaments/services/staff_permission_checker.py` |
| **Service** | `BracketService` (generation, seeding) | `apps/tournaments/services/bracket_service.py` |
| **Models** | 25+ models across 15 files | `apps/tournaments/models/` |
| **Templates** | 9 tab templates + _base.html | `templates/tournaments/manage/` |

### 1.3 The 9 TOC Tabs

| Tab | Purpose | Key Actions |
|-----|---------|-------------|
| **Overview** | Command center dashboard — alerts, lifecycle, upcoming events | View alerts, track lifecycle stage |
| **Participants** | Manage registrations, rosters, check-in, waitlist | Approve/reject/bulk-approve/DQ/promote/force-checkin/export |
| **Payments** | Verify payments, manage refunds, track revenue | Verify/reject/refund/bulk-verify/export |
| **Brackets** | Generate and manage bracket trees | Generate/reset/reorder-seeds/publish |
| **Matches** | Monitor and manage individual matches | Submit scores/reschedule/forfeit/override/cancel |
| **Schedule** | Round scheduling, check-in management | Auto-schedule/bulk-shift/add-breaks/manage check-in window |
| **Disputes** | Handle match disputes and evidence | Review/resolve/escalate disputes |
| **Announcements** | Broadcast messages to participants | Create/pin/mark-important announcements |
| **Settings** | Tournament configuration and staff management | Edit settings/manage payment methods/manage staff |

### 1.4 Technology Stack

- **Backend:** Django 5.2.8, Python 3.12
- **Database:** PostgreSQL 16 (Neon serverless)
- **Cache/Pub-Sub:** Redis
- **Task Queue:** Celery
- **Real-Time:** Django Channels (WebSocket)
- **File Storage:** Local → S3 (planned migration)
- **Event System:** Internal event bus (`common.events`)

---

## 2. Pillar 1 — Tournament Lifecycle & State Machine

### 2.1 Status States (Complete)

The tournament lifecycle is governed by the `status` field on the `Tournament` model:

```
DRAFT → PENDING_APPROVAL → PUBLISHED → REGISTRATION_OPEN → REGISTRATION_CLOSED → LIVE → COMPLETED → ARCHIVED
                                                                                   ↕         ↓
                                                                                FROZEN    CANCELLED
```

| Status | DB Value | Description | Who Can Trigger |
|--------|----------|-------------|-----------------|
| **Draft** | `draft` | Tournament being configured. Not visible to public. | Organizer (auto on create) |
| **Pending Approval** | `pending_approval` | Submitted for platform review. Locked from edits. | Organizer (submit action) |
| **Published** | `published` | Approved and publicly visible. Registration not yet open. | Platform admin (approve) |
| **Registration Open** | `registration_open` | Accepting registrations. Entry fee collection begins. | Auto (at `registration_start`) or manual |
| **Registration Closed** | `registration_closed` | No new registrations. Pre-tournament prep phase. | Auto (at `registration_end`) or manual |
| **Live** | `live` | Tournament actively running. Matches being played. | Organizer (start tournament) |
| **Completed** | `completed` | All matches finished. Results finalized. | Auto (all matches completed) or manual |
| **Cancelled** | `cancelled` | Tournament cancelled before or during play. | Organizer or platform admin |
| **Frozen** | `frozen` | Global emergency freeze. All timers paused, all operations suspended. | Head Admin (Global Killswitch) |
| **Archived** | `archived` | Historical record. Read-only. | Auto (30 days after completion) or manual |

### 2.2 State Transition Rules

**Valid transitions (enforce in service layer):**

| From | Allowed To | Conditions |
|------|------------|------------|
| `draft` | `pending_approval` | All required fields filled; at least one payment method configured (if entry fee); rules text or rules PDF present |
| `pending_approval` | `published`, `draft` | Admin approval required for `published`; rejection returns to `draft` with notes |
| `published` | `registration_open` | `registration_start` datetime reached OR manual override |
| `registration_open` | `registration_closed` | `registration_end` datetime reached OR manual override; OR `max_participants` reached (auto-close option) |
| `registration_closed` | `live` | Bracket generated; minimum participants met (`min_participants`); check-in window completed (if `enable_check_in`) |
| `live` | `completed` | All matches in terminal state (completed/forfeit/cancelled); OR manual force-complete |
| `completed` | `archived` | Grace period elapsed (configurable days); all prize claims processed; all disputes resolved |
| ANY pre-live | `cancelled` | Organizer discretion; triggers automatic refund workflow |
| `live` | `cancelled` | Emergency only; requires admin approval or organizer with reason; triggers complex refund logic |
| `live` | `frozen` | Head Admin triggers Global Killswitch; no preconditions — immediate freeze |
| `frozen` | `live` | Head Admin lifts freeze; all timers resume with adjusted deadlines |
| `frozen` | `cancelled` | Tournament cancelled from frozen state; triggers full refund workflow |

### 2.3 State Transition Side Effects

Each transition MUST trigger specific side effects:

| Transition | Side Effects |
|------------|--------------|
| → `registration_open` | Set `published_at` if not set; emit `tournament.registration_opened` event; schedule auto-close job (Celery beat) |
| → `registration_closed` | Emit `tournament.registration_closed` event; send notification to all registrants; enable check-in window timer |
| → `live` | Lock all registrations (no more changes); emit `tournament.started` event; update denormalized counts; start match monitoring |
| → `completed` | Emit `tournament.completed` event; trigger `award_placements()` for DeltaCoin payouts; generate `TournamentResult` record; compute final leaderboard entries; issue certificates (if enabled) |
| → `cancelled` | Emit `tournament.cancelled` event; trigger refund workflow for ALL verified payments; cancel all pending/scheduled matches; notify all registrants; remove from featured/active lists |
| → `frozen` | Emit `tournament.frozen` event; **immediately** freeze ALL auto-forfeit timers, check-in windows, payment deadlines, and match auto-confirm deadlines; push emergency WebSocket broadcast to ALL active player/organizer Hubs; log freeze reason and actor; set `frozen_at` timestamp |
| `frozen` → `live` | Emit `tournament.unfrozen` event; recalculate ALL paused deadlines (add elapsed freeze duration); resume check-in windows and payment deadlines; push "Tournament Resumed" WebSocket broadcast; log unfreeze actor and duration |
| → `archived` | Soft-lock all edit endpoints; emit `tournament.archived` event |

### 2.4 Automated Timers & Scheduled Jobs

| Job | Trigger | Action |
|-----|---------|--------|
| **Auto-Open Registration** | `registration_start` datetime | Transition `published` → `registration_open` |
| **Auto-Close Registration** | `registration_end` datetime | Transition `registration_open` → `registration_closed` |
| **Auto-Close on Full** | `total_registrations >= max_participants` | Optional: transition to `registration_closed` |
| **Check-In Window Open** | `tournament_start - check_in_minutes_before` | Open check-in window; emit event; notify registrants |
| **Check-In Window Close** | `tournament_start - check_in_closes_minutes_before` | Close check-in; auto-forfeit no-shows (if configured); promote waitlist |
| **Payment Deadline Enforcer** | `registration.created_at + payment_deadline_hours` | Expire unpaid registrations; move to `cancelled`; promote waitlist |
| **Auto-Archive** | `completed_at + 30 days` | Transition `completed` → `archived` |
| **Stale Draft Cleanup** | Weekly | Warn then delete drafts > 90 days old |

### 2.5 Lifecycle Tracking in TOC (CommandCenterService)

**CURRENT IMPLEMENTATION:**
- `get_lifecycle_progress(tournament)` → Returns 5-stage progress: Draft → Registration → Brackets → Live → Completed
- Stages: `{name, status: past|current|future, icon}` + `{stage, progress_pct}`

**NEEDED ENHANCEMENTS:**
- Granular sub-stages (e.g., "Registration Open — 12/32 slots filled — 3 days remaining")
- Time-to-next-stage estimates
- Blocker detection (e.g., "Cannot go Live: bracket not generated, 2 unverified payments")
- Transition readiness checklist (all conditions met? Y/N per condition)

### 2.6 Tournament Versioning

**EXISTS:** `TournamentVersion` model tracks snapshots of tournament state:
- `version_number`, `version_data` (full JSONB snapshot), `change_summary`, `changed_by`, `changed_at`
- `is_active`, `rolled_back_at`, `rolled_back_by`

**PURPOSE:** Audit trail for tournament configuration changes. Enables rollback of settings changes.

**NEEDED:**
- Auto-snapshot on every status transition
- Diff view between versions
- Rollback capability in TOC settings tab

### 2.7 Global Killswitch — Tournament Freeze

**PURPOSE:** Respond to global emergencies (game server outages, widespread internet failures, LAN power failures, security incidents) by freezing the entire tournament in a single action.

**TRIGGER:** Head Admin presses the "Global Killswitch" button in the TOC Overview tab.

**WHAT GETS FROZEN (immediately upon trigger):**

| System | Freeze Behavior |
|--------|----------------|
| **Auto-Forfeit Timers** | All active match-level auto-forfeit countdowns paused; elapsed time preserved |
| **Check-In Windows** | All open check-in windows paused; remaining time preserved |
| **Payment Deadlines** | All pending payment deadline timers paused |
| **Auto-Confirm Deadlines** | All match result auto-confirm countdowns paused |
| **Scheduled Transitions** | Celery beat tasks for auto-open/close registration suspended |
| **Match Starts** | No matches can transition to LIVE during freeze |
| **Score Submissions** | Player score submission blocked (organizer override still available) |

**BROADCAST:**
- Emergency WebSocket message pushed to `tournament.{id}.emergency` channel
- All connected player and organizer Hubs receive real-time freeze notification
- Banner message injected: "Tournament has been temporarily suspended by administration"

**DATA MODEL ADDITIONS:**

| Field | Type | Description |
|-------|------|-------------|
| `Tournament.frozen_at` | DateTimeField (nullable) | Timestamp when freeze was activated |
| `Tournament.frozen_by` | FK → User (nullable) | Admin who triggered the freeze |
| `Tournament.freeze_reason` | TextField (blank) | Reason for emergency freeze |
| `Tournament.freeze_duration_seconds` | PositiveIntegerField (default 0) | Total accumulated freeze time (supports multiple freeze/unfreeze cycles) |

**RESUME LOGIC:**
When the Head Admin lifts the freeze:
1. Calculate `freeze_elapsed = now() - frozen_at`
2. Add `freeze_elapsed` to `freeze_duration_seconds` (cumulative)
3. For every active timer (auto-forfeit, check-in, payment deadline, auto-confirm):
   - `new_deadline = original_deadline + freeze_elapsed`
4. Clear `frozen_at`, `frozen_by`
5. Transition back to `live`
6. Broadcast "Tournament Resumed" via WebSocket
7. Push notifications to all participants

**AUDIT:** Every freeze/unfreeze cycle recorded in `TournamentVersion` with full snapshot.

---

## 3. Pillar 2 — Registration & Participant Management

### 3.1 Registration Model — Complete Data Flow

**Registration States:**

```
DRAFT → SUBMITTED → PENDING → [AUTO_APPROVED | NEEDS_REVIEW] → [PAYMENT_SUBMITTED] → CONFIRMED
                                                                                        ↓
                                                                              REJECTED | CANCELLED | WAITLISTED | NO_SHOW
```

| Status | DB Value | Description |
|--------|----------|-------------|
| `draft` | Wizard in progress. `RegistrationDraft` exists. Not yet submitted. |
| `submitted` | Form submitted but not yet triaged. |
| `pending` | Awaiting organizer review. |
| `auto_approved` | Passed all `RegistrationRule` auto-approve checks. |
| `needs_review` | Flagged by a `RegistrationRule` for manual review. |
| `payment_submitted` | Payment proof submitted, awaiting verification. |
| `confirmed` | Fully approved + payment verified. Participant is locked in. |
| `rejected` | Organizer rejected the registration. |
| `cancelled` | Participant self-cancelled or admin-cancelled. |
| `waitlisted` | Tournament full. Queued in FIFO order (`waitlist_position`). |
| `no_show` | Did not check in within the check-in window. |

### 3.2 Smart Registration Wizard

**EXISTS:** 5-step wizard backed by `RegistrationDraft`:
1. **Player Info** — Game ID, contact details (auto-filled from profile)
2. **Team Info** — Team selection (if team tournament), display name override
3. **Custom Questions** — Dynamic questions from `RegistrationQuestion` (per-tournament or per-game)
4. **Review** — Confirmation of all details
5. **Payment** — Entry fee payment (if `has_entry_fee`)

**Key Models:**
- `RegistrationDraft` — Persistent wizard state with `form_data` JSONB, `auto_filled_fields`, `locked_fields`, `completion_percentage`, `current_step`, `expires_at`
- `RegistrationQuestion` — Dynamic form fields with `type` (text/select/multi_select/boolean/number/file/date), `scope` (team/player), `show_if` conditional JSONB, `is_built_in` flag
- `RegistrationAnswer` — Stores answers with `value` JSONB + `normalized_value`
- `RegistrationRule` — Auto-processing rules: `auto_approve`, `auto_reject`, `flag_for_review` with `condition` JSONB and `priority` ordering

### 3.3 Registration Processing Pipeline

```
Player submits registration
    ↓
RegistrationDraft → Registration (status: submitted)
    ↓
Run RegistrationRules (ordered by priority):
  - auto_approve rules → set CONFIRMED (if no payment) or AUTO_APPROVED (if payment needed)
  - auto_reject rules → set REJECTED + reason
  - flag_for_review rules → set NEEDS_REVIEW
  - no rules match → set PENDING
    ↓
If tournament is full:
  → set WAITLISTED + assign waitlist_position (FIFO)
    ↓
If entry fee required and not waived:
  → Player submits payment → PAYMENT_SUBMITTED
  → Organizer verifies → CONFIRMED
    ↓
If no entry fee or fee waived:
  → Directly CONFIRMED (if approved)
```

### 3.4 Organizer Tools — Participants Tab

**EXISTING ACTIONS:**

| Action | Endpoint | Method | Conditions |
|--------|----------|--------|------------|
| Approve Registration | `approve-registration/<reg_id>/` | POST | Status in (pending, needs_review, submitted) |
| Reject Registration | `reject-registration/<reg_id>/` | POST | Status in (pending, needs_review, submitted, payment_submitted) |
| Bulk Approve | `bulk-approve-registrations/` | POST | Selected registrations, same conditions |
| Bulk Reject | `bulk-reject-registrations/` | POST | Selected registrations |
| Disqualify | `disqualify/<reg_id>/` | POST | Status = confirmed; cascades to bracket |
| DQ with Cascade | `dq-cascade/<reg_id>/` | POST | Status = confirmed; DQs and advances opponent in bracket |
| Promote Waitlist | `promote-waitlist/<reg_id>/` | POST | Status = waitlisted; slot available |
| Auto-Promote Next | `auto-promote-waitlist/` | POST | Promotes next in FIFO order |
| Add Manual Participant | `add-participant/` | POST | Organizer adds participant directly |
| Toggle Check-In | `toggle-checkin/<reg_id>/` | POST | Organizer override check-in |
| Force Check-In | `force-checkin/<reg_id>/` | POST | Force check-in regardless of window |
| Drop No-Show | `drop-noshow/<reg_id>/` | POST | Mark as NO_SHOW |
| Close & Drop No-Shows | `close-drop-noshows/` | POST | Batch close check-in + drop all not checked in |
| Export Roster CSV | `export-roster/` | GET | Download all registrations as CSV |
| Registration Detail API | `api/registration/<reg_id>/` | GET | JSON detail for drawer/modal |
| Tournament Verification API | `api/verify/` | GET | Run full verification sweep |

### 3.5 Automated Verification Checks (RegistrationVerificationService)

**7 checks, run on-demand or before going Live:**

| # | Check | Code | Severity | Description |
|---|-------|------|----------|-------------|
| 1 | Duplicate Game IDs | `duplicate_game_id` | critical | Two registrations have the same in-game ID |
| 2 | Missing Game IDs | `missing_game_id` | warning | Registration has no game ID in roster data |
| 3 | Roster Undersize | `roster_undersize` | critical | Team has fewer players than minimum required |
| 4 | Roster Oversize | `roster_oversize` | warning | Team has more players than maximum allowed |
| 5 | No Captain/IGL | `no_captain` | warning | Team has no player marked as captain/IGL |
| 6 | Duplicate Users | `duplicate_user` | critical | Same user appears in multiple team registrations |
| 7 | Banned Players | `banned_player` | critical | Player flagged as banned/suspended in system |

**NEEDED ADDITIONAL CHECKS:**
| # | Check | Description |
|---|-------|-------------|
| 8 | **Payment Mismatch** | Registration is confirmed but payment is not verified |
| 9 | **Stale Draft** | Registration draft has been idle > X hours |
| 10 | **Minimum Age** | Player does not meet minimum age requirement (if configured) |
| 11 | **Region Restriction** | Player is from a restricted region (if tournament has region rules) |
| 12 | **Roster Lock Violation** | Team roster changed after registration lock deadline |
| 13 | **Duplicate Registration** | Same team/user attempting to register twice |
| 14 | **Incomplete Custom Answers** | Required `RegistrationQuestion` answers missing |

### 3.6 Check-In System

**CURRENT IMPLEMENTATION (CheckinService):**

| Feature | Status | Details |
|---------|--------|---------|
| Single check-in | ✅ | Eligibility validation, idempotent, audit logged |
| Undo check-in | ✅ | 15-min window for owners, unlimited for organizers |
| Bulk check-in | ✅ | Up to 200 registrations, organizer only |
| Organizer toggle | ✅ | Bypass all validation |
| Check-in window timing | ✅ | Opens X min before start, closes Y min before |
| Auto-forfeit no-shows | ✅ | Via `TournamentLobby.auto_forfeit_no_show` flag |
| Events published | ✅ | `checkin.completed`, `checkin.reverted` |

**EXISTS in TournamentLobby model:**
- `check_in_opens_at`, `check_in_closes_at`
- `check_in_required` (bool)
- `auto_forfeit_no_show` (bool)
- `lobby_message`, `rules_url`, `discord_server_url`
- `bracket_visibility` (hidden/seeded_only/full)
- `roster_visibility` (hidden/count_only/full)

**NEEDED ENHANCEMENTS:**
| Feature | Description |
|---------|-------------|
| **Team Captain Check-In** | Only team captain can check in the team (not any member) |
| **Partial Team Check-In** | Allow individual player check-in within a team, with minimum threshold |
| **Check-In Reminders** | Push/email notification X minutes before check-in opens and before it closes |
| **Emergency Extension** | Organizer can extend check-in window by N minutes on the fly |
| **Check-In Analytics** | Real-time check-in velocity chart (how fast are people checking in?) |
| **Substitute Check-In** | Allow a substitute player to check in on behalf of a rostered player |

### 3.7 Waitlist Management

**CURRENT:** FIFO-based waitlist with `waitlist_position` field.

**WORKFLOW:**
```
Registration when tournament full
    → Set status = WAITLISTED
    → Assign waitlist_position = MAX(existing positions) + 1
    ↓
When slot opens (cancellation/DQ/no-show):
    → Auto-promote next waitlisted (FIFO) OR organizer manual promote
    → Set status = PENDING or CONFIRMED (depending on payment)
    → Notify promoted participant
    → Shift all remaining waitlist positions down
```

**NEEDED:**
- Waitlist cap (max waitlist size)
- Waitlist expiry (auto-remove after X days if not promoted)
- Priority waitlist (seed returning champions, invite-code holders)
- Waitlist notification preferences (email/push/SMS)

### 3.8 Guest Teams

**EXISTS:**
- `Registration.is_guest_team` — Boolean flag
- `Registration.invite_token` — 64-char unique token for invite-only flow
- `Tournament.max_guest_teams` — Cap on guest team slots (0 = disabled)

**WORKFLOW:**
Organizer creates invite link → Guest team captain receives link → Registers with token → Marked as guest team → Organizer can approve/reject.

**NEEDED:**
- Guest team registration form (simplified — no DeltaCrown account required for team registration, but individual players need accounts)
- Guest team roster submission via invite link
- Guest team payment handling (may differ from regular flow)

### 3.9 Fee Waiver System

**EXISTS:**
- `Tournament.enable_fee_waiver` — Master toggle
- `Tournament.fee_waiver_top_n_teams` — Auto-waive for top N teams by ranking
- `Payment.waived`, `Payment.waive_reason`

**NEEDED:**
- Manual waiver tool in TOC (organizer selects registration, clicks "Waive Fee", enters reason)
- Invite-code-based waivers (specific invite codes grant free entry)
- Sponsor-funded waivers (sponsor covers entry fee for X participants)
- Waiver audit log (who waived, when, why)

### 3.10 Roster Lock & Emergency Substitution Mechanics

**THE PROBLEM:** Registration closing does not mean rosters are locked. There is currently no enforcement point that prevents captains from swapping players after registration closes but before (or during) the tournament.

#### 3.10.1 Roster Lock Deadline

A new `roster_lock_deadline` field (DateTimeField, nullable) on the `Tournament` model, **separate from `registration_end`**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `roster_lock_deadline` | DateTimeField | `registration_end` | After this datetime, team rosters are immutable |

**ENFORCEMENT:**
- Before `roster_lock_deadline`: Captains can freely add/remove/swap players via the registration edit flow
- After `roster_lock_deadline`: All roster modification endpoints return `403 Roster Locked`
- The lock is enforced at the service layer, not just the view layer
- Organizer override: Organizers can still modify rosters after the lock (audit-logged)

**AUTOMATED JOBS:**

| Job | Trigger | Action |
|-----|---------|--------|
| **Roster Lock Warning** | `roster_lock_deadline - 24h` | Notify all captains that roster lock is approaching |
| **Roster Lock Enforcement** | `roster_lock_deadline` | Lock all roster editing endpoints; emit `tournament.roster_locked` event |

#### 3.10.2 Emergency Substitution System

When a player drops out, disconnects, or becomes unavailable **after** the roster lock, the captain needs a formal process to substitute a player.

**NEW MODEL: `EmergencySubRequest`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `tournament` | FK → Tournament | Tournament context |
| `registration` | FK → Registration | Team registration |
| `requested_by` | FK → User | Captain who filed the request |
| `dropping_player` | FK → User | Player being replaced |
| `substitute_player` | FK → User | Proposed substitute |
| `reason` | TextField | Reason for substitution (illness, internet, etc.) |
| `status` | CharField | `pending` / `approved` / `denied` |
| `reviewed_by` | FK → User (nullable) | Admin who reviewed |
| `reviewed_at` | DateTimeField (nullable) | Review timestamp |
| `review_notes` | TextField (blank) | Admin notes on decision |
| `created_at` | DateTimeField (auto) | Request timestamp |

**WORKFLOW:**
```
Player drops out after roster lock
    → Captain opens "Emergency Sub Request" form in Team Hub
    → Selects dropping player + proposed substitute
    → Enters reason
    → Request appears in TOC Participants tab under "Emergency Sub Requests" section
    ↓
Organizer reviews request:
    → System auto-checks:
        - Substitute is not already registered in another team for this tournament
        - Substitute meets eligibility requirements (age, region, etc.)
        - Substitute is not on a ban list
    → APPROVE:
        - Dropping player removed from roster (marked as `emergency_replaced`)
        - Substitute added to roster
        - Substitute can now check in to matches
        - Both players notified
        - Audit log entry created
    → DENY:
        - Captain notified with reason
        - Team must play with reduced roster or forfeit
```

**TOC INTEGRATION:**

| Location | Feature |
|----------|---------|
| **Participants Tab** | New "Emergency Sub Requests" panel showing pending/approved/denied requests |
| **Registration Detail Drawer** | Show roster change history including emergency subs |
| **Verification Check #12** | `roster_lock_violation` — Flag if roster was modified after lock without approved emergency sub |

### 3.11 Quick Comms — WhatsApp & Direct Contact Integration

**THE PROBLEM:** The platform relies on email and in-app notifications for participant communication. In South Asian esports, organizers need **instant, direct contact** — especially for payment follow-ups, last-minute check-in issues, and LAN logistics. Email has multi-hour lag. Push notifications get buried. The captain's phone number is already collected during registration, but the TOC provides no way to use it.

**SOLUTION:** Add a "Quick Comms" module to every participant record in the TOC, surfacing direct communication channels.

#### 3.11.1 Data Source

The player's contact information is already available from two sources:
- `UserProfile.phone_number` — Primary phone registered on the platform
- `RegistrationAnswer` — If the tournament has a custom "Phone Number" or "WhatsApp Number" registration question

The system should resolve contact info in priority order:
1. Tournament-specific registration answer (most relevant)
2. `UserProfile.phone_number` (fallback)

#### 3.11.2 Quick Comms Panel (TOC Participants Tab)

**Location:** Inside each participant's detail drawer/row in the Participants tab.

| Action Button | Behavior | Icon |
|---------------|----------|------|
| **WhatsApp** | Opens `https://wa.me/{phone}?text={pre-filled_message}` in new tab | WhatsApp icon |
| **Call** | Opens `tel:{phone}` protocol (triggers system dialer on mobile/desktop) | Phone icon |
| **SMS** | Opens `sms:{phone}?body={pre-filled_message}` protocol | Message icon |
| **Email** | Opens `mailto:{email}?subject={tournament_name}` with pre-filled subject | Email icon |
| **Copy Phone** | Copies phone number to clipboard | Copy icon |

**PRE-FILLED MESSAGE TEMPLATES:**

Organizers should not have to type the same message 50 times. Pre-filled templates auto-populate based on context:

| Context | Pre-Filled WhatsApp Message |
|---------|----------------------------|
| **Payment Reminder** | "Hi {captain_name}, your payment for {tournament_name} is still pending. Please submit proof by {deadline}. — {organizer_name}" |
| **Check-In Reminder** | "Hi {captain_name}, check-in for {tournament_name} opens in {minutes} minutes. Don't miss it! — {organizer_name}" |
| **Match Starting** | "Hi {captain_name}, your match against {opponent_name} is starting now. Please join the lobby. — {organizer_name}" |
| **Custom** | Organizer types a custom message (saved as template for reuse) |

#### 3.11.3 Bulk Quick Comms

| Action | Description |
|--------|-------------|
| **Bulk WhatsApp** | Open WhatsApp Web with a list of selected participants' phone numbers (one-by-one sequential opening, as WhatsApp doesn't support true bulk) |
| **Bulk Email** | Compose email to all selected participants (BCC) |
| **Export Phone List** | Export all captain phone numbers to CSV for external tools (WhatsApp Business broadcast, SMS gateway) |

#### 3.11.4 Privacy & Consent

| Rule | Description |
|------|-------------|
| **Consent** | Phone numbers are only visible to organizer/staff with `manage_registrations` permission |
| **Opt-Out** | Players can opt out of phone contact during registration (checkbox: "Allow organizer to contact me via phone/WhatsApp") |
| **Audit** | Every "contact initiated" action is logged (who contacted whom, when, via which channel) |
| **Masking** | If Admin Pseudonym is active, the pre-filled message uses the organizer's tournament name, not their personal name |

**NEW REGISTRATION QUESTION (Built-In, Optional):**

| Field | Type | Description |
|-------|------|-------------|
| `contact_whatsapp` | `phone` | "WhatsApp number (for organizer contact during tournament)" |
| `contact_consent` | `boolean` | "I consent to being contacted via WhatsApp/phone for tournament-related matters" |

### 3.12 Free Agent / LFG (Looking For Group) Pool

**THE PROBLEM:** Many solo players want to compete but have no team. Currently, they cannot register for team-based tournaments at all. Meanwhile, organizers often have unfilled bracket slots and no mechanism to form ad-hoc teams from available individuals. Other platforms (start.gg, Battlefy) offer "free agent" pools where solo players can be grouped into mix teams automatically or drafted by team captains.

**SOLUTION:** A **Free Agent registration path** that creates a pool of solo players available for team formation. Organizers can bulk-assign free agents into auto-generated "Mix Teams," or enable a captain draft mode where existing team captains pick from the pool.

#### 3.12.1 Configuration (Tournament-Level)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_free_agents` | BooleanField | `False` | Allow solo Free Agent registrations for this team tournament |
| `free_agent_pool_size` | PositiveIntegerField (nullable) | `null` | Max free agents accepted (null = unlimited) |
| `free_agent_deadline` | DateTimeField (nullable) | Registration deadline | Separate deadline for free agent signups |
| `team_formation_mode` | CharField | `organizer_assign` | `organizer_assign` / `captain_draft` / `auto_match` / `self_form` |
| `auto_match_criteria` | JSONField | `["game", "rank"]` | Criteria for auto-matching: game, rank/tier, region, preferred role |
| `min_free_agents_for_team` | PositiveIntegerField | Tournament's `team_size_min` | Minimum FAs needed to form a mix team |
| `mix_team_name_prefix` | CharField(50) | `"Mix Team"` | Name prefix for auto-generated teams (e.g., "Mix Team Alpha") |

#### 3.12.2 New Model: `FreeAgentRegistration`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `tournament` | FK → Tournament | Target tournament |
| `user` | FK → User | The free agent player |
| `registration` | FK → Registration (nullable) | Created once assigned to a team |
| `status` | CharField | `available` / `drafted` / `assigned` / `self_formed` / `withdrawn` / `expired` |
| `preferred_role` | CharField(100, blank) | Player's preferred in-game role (e.g., "IGL", "Entry Fragger", "Support") |
| `rank_info` | CharField(100, blank) | Player's self-reported rank (e.g., "Diamond 3", "Heroic") |
| `bio` | TextField (blank) | Short pitch ("Former IGL for Team Phoenix, 2000+ hours in Valorant") |
| `availability_notes` | TextField (blank) | Schedule constraints ("Available after 6pm weekdays") |
| `game_id` | CharField(200, blank) | In-game identifier (IGN) |
| `drafted_by` | FK → User (nullable) | Captain who drafted this FA |
| `assigned_to_team` | FK → Team (nullable) | Team the FA was assigned to |
| `assigned_at` | DateTimeField (nullable) | When assigned/drafted |
| `created_at` | DateTimeField (auto) | Signup timestamp |

#### 3.12.3 Team Formation Modes

**Mode 1 — Organizer Assign (`organizer_assign`):**
```
Free Agent Pool created
    → Registration deadline passes
    → Organizer opens TOC Free Agent Workspace
    → View all FAs sorted by rank/role/availability
    → Drag-and-drop FAs into team slots
    → Click "Generate Mix Teams" → system creates Team objects
    → Each FA gets a Registration linked to their Mix Team
    → FAs notified: "You've been assigned to Mix Team Bravo"
```

**Mode 2 — Captain Draft (`captain_draft`):**
```
Free Agent Pool created
    → Existing team captains browse FA pool
    → Captain sends "Draft Request" to FA
    → FA accepts/declines
    → On accept: FA added to captain's roster; Registration created
    → Draft window has configurable deadline
```

**Mode 3 — Auto Match (`auto_match`):**
```
Free Agent Pool created
    → Registration deadline passes
    → System groups FAs by auto_match_criteria (rank similarity → role diversity → region)
    → Balanced teams generated algorithmically
    → FAs notified with teammates; given 24h to accept or opt out
    → Unmatched FAs placed on waitlist
```

**Mode 4 — Self Form (`self_form`):**
```
Free Agents can browse the pool themselves
    → FA sends "Team Up Request" to other FAs
    → When min_free_agents_for_team accept, they form a team
    → One is randomly designated captain (or they choose)
    → Team registered normally
```

#### 3.12.4 TOC Free Agent Workspace

| Feature | Description |
|---------|-------------|
| **FA Pool Grid** | Sortable/filterable table: username, rank, preferred role, availability, bio, signup date |
| **Drag-and-Drop Team Builder** | Visual team slots — drag FAs from pool into team slots |
| **Auto-Generate Teams** | "Fill Remaining Slots" button: auto-form balanced teams from remaining FAs |
| **Draft Monitor** | For captain_draft mode: view draft requests, accept rates, unmatched FAs |
| **FA → Team Conversion** | One-click: create Team, create Registrations, assign captain, notify all |
| **Waitlist Management** | FAs who couldn't be placed — offer refund or keep on standby |
| **Role Distribution View** | Visual breakdown: "12 Entry Fraggers, 8 Supports, 3 IGLs, 2 unspecified" |
| **Communication** | Bulk WhatsApp/notification to all FAs (uses Quick Comms §3.11) |

#### 3.12.5 Smart Registration Integration

The existing 5-step registration wizard (§3.3) gains a **Step 0 fork**:

```
Tournament Registration Page
    → IF enable_free_agents AND tournament.is_team_based:
        → "How do you want to register?"
            → [Register as Team Captain] → Normal 5-step wizard
            → [Register as Free Agent]  → FA registration flow:
                → Step 1: Profile confirmation (name, IGN)
                → Step 2: Role/rank/availability
                → Step 3: Payment (if entry fee applies to FAs)
                → Step 4: Rules acceptance
                → Step 5: Confirmation → FreeAgentRegistration created
    → IF NOT enable_free_agents:
        → Normal team registration only
```

### 3.13 LAN QR Desk Check-In

**THE PROBLEM:** At offline/hybrid LAN events, check-in is chaotic. Players arrive, queue at a desk, and staff manually search for their team name in the TOC participant list, verify identity, and click "Check In." This takes 2–5 minutes per team and creates long queues. With 64+ teams, the check-in phase alone can consume over an hour. Staff errors (checking in the wrong team, missing a player) compound under time pressure.

**SOLUTION:** A **QR Code Check-In** system where each team captain sees a unique QR code on their Team Hub page. At the LAN venue, TOC staff open a "Scanner View" on their mobile device, scan the captain's QR code, and the system instantly triggers the `CheckinService` for the entire roster — completing check-in in under 5 seconds per team.

#### 3.13.1 QR Code Generation

**New Fields on `Registration`:**

| Field | Type | Description |
|-------|------|-------------|
| `checkin_qr_token` | UUIDField (unique, auto-generated) | Unique token embedded in the QR code |
| `checkin_qr_generated_at` | DateTimeField (nullable) | When the QR code was generated |
| `checkin_qr_expires_at` | DateTimeField (nullable) | QR expiry (regenerates after expiry for security) |

**QR Code Content:** `https://deltacrown.com/checkin/qr/{checkin_qr_token}/`

**QR Display Locations:**
- Captain's Team Hub page (prominent "Show QR for Check-In" button)
- Captain's mobile app (if future app exists)
- Downloadable as PNG (for printing on paper badge)

#### 3.13.2 Scanner View (TOC Staff Mobile Endpoint)

**Endpoint:** `GET /toc/{tournament_slug}/scanner/` — lightweight mobile-optimized page.

```
┌────────────────────────────────────┐
│  🎯 LAN CHECK-IN SCANNER          │
│                                    │
│  Tournament: DeltaCrown S3 Finals  │
│                                    │
│  ┌──────────────────────────────┐  │
│  │                              │  │
│  │     [Camera Viewport]        │  │
│  │     Scan Captain's QR        │  │
│  │                              │  │
│  └──────────────────────────────┘  │
│                                    │
│  Last scan:                        │
│  ✅ Team Phoenix — Checked in      │
│     Captain: @shadow_strike        │
│     Players: 5/5 roster confirmed  │
│     14:32:05 BST                   │
│                                    │
│  Stats: 42/64 teams checked in     │
│  ████████████████░░░░ 65.6%        │
│                                    │
│  [Manual Search] [Scan History]    │
└────────────────────────────────────┘
```

#### 3.13.3 Scan Workflow

```
Staff opens Scanner View on mobile phone/tablet
    → Browser requests camera access
    → Staff points camera at captain's QR code on screen/paper
    → JS QR scanner reads token → POST /toc/{slug}/scanner/verify/
    → Backend:
        → Lookup Registration by checkin_qr_token
        → Validate: token not expired, tournament matches, check-in window is open
        → IF valid:
            → Call CheckinService.check_in_team(registration)
            → All roster members marked as checked in
            → Return: ✅ team_name, captain, roster_count, timestamp
            → Staff sees green success banner
            → Captain sees "You've been checked in!" on their Hub
        → IF invalid:
            → Return error: "QR expired", "Wrong tournament", "Already checked in", "Check-in not open"
            → Staff sees red error banner with reason
```

#### 3.13.4 Configuration (Tournament-Level)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_qr_checkin` | BooleanField | `False` | Enable QR code check-in for this LAN/hybrid tournament |
| `qr_token_ttl_hours` | PositiveIntegerField | `24` | QR token expiry (hours); auto-regenerates on expiry |
| `qr_checkin_auto_roster` | BooleanField | `True` | Scanning captain's QR checks in entire roster (not just captain) |
| `qr_checkin_require_staff_confirm` | BooleanField | `False` | Require staff to press "Confirm" after scan (vs. instant check-in) |
| `qr_show_roster_on_scan` | BooleanField | `True` | Show full roster list to staff on scan (for identity verification) |

#### 3.13.5 Security Considerations

| Concern | Mitigation |
|---------|------------|
| **QR Screenshot Forwarding** | Token is single-use per check-in window; cannot check in twice |
| **Token Leakage** | Tokens expire and regenerate; short TTL for LAN events |
| **Wrong Person Scanning** | `qr_checkin_require_staff_confirm` adds manual identity verification step |
| **Camera Permissions** | Graceful fallback to manual search if camera access denied |
| **Slow Network at Venue** | Scanner View is minimal HTML; works on 3G; offline queue with sync when connected |

### 3.14 Asymmetric Rosters — Man-Down Allowance

**THE PROBLEM:** In team-based tournaments, a strict roster size requirement (e.g., exactly 5 players for Valorant) means that if a player disconnects, loses internet, or has a personal emergency and no substitute is available (or the Emergency Sub Request hasn't been processed yet), the entire team is forced to forfeit. This is especially brutal in LAN events where a player might be stuck in traffic. The current system offers a binary choice: full roster or forfeit. There is no middle ground.

**SOLUTION:** A tournament-level **Man-Down Allowance** setting that permits matches to start or continue when a team has fewer than the required roster size. The organizer defines the minimum roster threshold below which a match cannot proceed.

#### 3.14.1 Configuration (Tournament-Level)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `allow_undermanned_starts` | BooleanField | `False` | Allow matches to start with fewer than full roster |
| `min_roster_for_start` | PositiveIntegerField (nullable) | `null` | Minimum players required to start (e.g., 4 for a 5v5 game). Null = full roster required |
| `undermanned_grace_period_minutes` | PositiveIntegerField | `10` | Minutes to wait for missing player before starting undermanned |
| `undermanned_score_penalty` | BooleanField | `False` | Apply a score penalty to the undermanned team (game-specific) |
| `undermanned_penalty_value` | JSONField (nullable) | `null` | Penalty config: `{"type": "rounds", "value": -2}` or `{"type": "points", "value": -5}` |
| `allow_late_join` | BooleanField | `True` | Allow the missing player to join mid-match if they arrive |

#### 3.14.2 Man-Down Match Workflow

```
Match SCHEDULED → CHECK_IN window opens
    → Team A: 5/5 checked in ✅
    → Team B: 4/5 checked in ⚠️ (1 missing)
    → Check-in window closes
    → IF NOT allow_undermanned_starts:
        → Standard behavior: Team B forfeits (or grace period → forfeit)
    → IF allow_undermanned_starts:
        → IF Team B roster >= min_roster_for_start (e.g., 4 >= 4):
            → Match proceeds with warning:
                "Team B starting with 4/5 players. Man-down allowance active."
            → Grace period timer starts (undermanned_grace_period_minutes)
            → During grace period:
                → Missing player CAN still join (if allow_late_join)
                → Match state: LIVE (with undermanned flag)
            → After grace period:
                → Match continues regardless
                → IF undermanned_score_penalty: apply penalty to Team B
            → Match result recorded normally
            → Audit log: "Match played 4v5 — undermanned allowance"
        → IF Team B roster < min_roster_for_start (e.g., 3 < 4):
            → Team B forfeits (below minimum threshold)
```

#### 3.14.3 New Fields on `Match`

| Field | Type | Description |
|-------|------|-------------|
| `is_undermanned` | BooleanField (default False) | Whether any team started below full roster |
| `undermanned_team` | FK → Registration (nullable) | Which team was undermanned |
| `undermanned_count` | PositiveIntegerField (nullable) | How many players the undermanned team had |
| `undermanned_penalty_applied` | BooleanField (default False) | Whether a score penalty was applied |
| `late_join_player` | FK → User (nullable) | Player who joined late (if allow_late_join triggered) |
| `late_join_at` | DateTimeField (nullable) | When the late player joined |

#### 3.14.4 TOC Match Operations Integration

| Feature | Description |
|---------|-------------|
| **Undermanned Indicator** | Match card shows ⚠️ "4v5" badge when a team is undermanned |
| **Grace Period Timer** | Countdown visible to organizer: "Missing player can join for 8:42 more" |
| **Force Start** | Organizer can force-start an undermanned match before grace period expires |
| **Override to Forfeit** | Organizer can override man-down allowance and force a forfeit regardless |
| **Late Join Notification** | If missing player checks in during grace period, organizer is notified immediately |
| **Post-Match Flag** | Completed undermanned matches are flagged in results for transparency |

---

## 4. Pillar 3 — Financial Operations

### 4.1 Payment Model Architecture

**Payment states:**
```
PENDING → SUBMITTED → VERIFIED → (REFUNDED)
                   ↓
               REJECTED → (player resubmits) → SUBMITTED
                                                   ↓
                                               EXPIRED (if deadline passes)
```

Also: `WAIVED` (fee waived by organizer)

**Payment Methods (Bangladesh-focused):**
- bKash, Nagad, Rocket (mobile financial services)
- Bank Transfer
- DeltaCoin (platform virtual currency)

### 4.2 Payment Verification Workflow

```
Player selects payment method
    → Player sends money externally (bKash/Nagad/Rocket/Bank)
    → Player enters transaction ID + uploads proof screenshot
    → Payment.status → SUBMITTED
    ↓
Organizer sees payment in TOC Payments tab:
    → Views proof image side-by-side with details
    → Verifies transaction ID matches amount
    → VERIFY → Payment.status → VERIFIED, Registration.status → CONFIRMED
    → REJECT (with reason) → Payment.status → REJECTED, player can resubmit
    ↓
If DeltaCoin payment:
    → Automatic debit from wallet
    → Auto-verify (no manual proof needed)
    → Registration.status → CONFIRMED immediately
```

**Payment per-method configuration (TournamentPaymentMethod model):**
Each tournament has per-method settings:
- bKash/Nagad/Rocket: account number, account name, account type (personal/agent/merchant), reference_required flag
- Bank: bank name, branch, account number, routing number
- DeltaCoin: instructions text
- Per-method: `is_enabled`, `display_order`

### 4.3 Organizer Tools — Payments Tab

**EXISTING ACTIONS:**

| Action | Endpoint | Method | Details |
|--------|----------|--------|---------|
| Verify Payment | `verify-payment/<pay_id>/` | POST | Sets verified, records `verified_by`, `verified_at` |
| Reject Payment | `reject-payment/<pay_id>/` | POST | Sets rejected with reason, `resubmission_count` increments |
| Bulk Verify | `bulk-verify-payments/` | POST | Mass verify selected payments |
| Process Refund | `refund-payment/<pay_id>/` | POST | Sets refunded, records `refunded_by`, `refunded_at` |
| Export Payments CSV | `export-payments/` | GET | Download all payments data |
| Payment History | `registrations/<reg_id>/payment-history/` | GET | Full payment timeline for one registration |

**EXISTING CONTEXT DATA:**
- `payment_stats`: total, submitted, verified, rejected, total_amount
- `method_breakdown`: per-method count and revenue subtotal

### 4.4 Revenue Analytics (NEEDED)

**Currently missing from TOC — critical for Tier-1:**

| Feature | Description |
|---------|-------------|
| **Real-time Revenue Counter** | Live total collected vs expected (confirmed x entry_fee) |
| **Collection Rate** | % of confirmed registrations with verified payments |
| **Outstanding Payments** | List of confirmed registrations without verified payment |
| **Refund Tracker** | Total refunded amount, refund rate, reasons breakdown |
| **Payment Timeline** | Histogram of payment submissions over time |
| **Method Conversion** | Which payment methods have highest verification success rate |
| **Deadline Tracker** | Registrations approaching payment deadline |

### 4.5 Refund Workflow

**CURRENT:** Basic refund flag on Payment model.

**NEEDED COMPLETE WORKFLOW:**
```
Refund initiated (organizer action OR tournament-cancelled auto-refund)
    → Check refund_policy:
        - no_refund: Block (unless organizer override or tournament cancelled)
        - refund_until_checkin: Allow if before check-in window
        - refund_until_bracket: Allow if bracket not yet generated
        - full_refund: Always allow
        - custom: Check refund_policy_text for rules
    → If DeltaCoin payment:
        → Auto-credit wallet with refund transaction
        → Mark Payment.status = REFUNDED
    → If bKash/Nagad/Rocket/Bank:
        → Mark Payment.status = REFUNDED
        → Create refund record with payout destination
        → Organizer processes external refund manually
        → Mark external refund as completed
    → Update Registration.status based on context:
        - If player-initiated cancel: CANCELLED
        - If tournament cancelled: stays CONFIRMED but marked refunded
        - If DQ: stays registration status, payment refunded
```

### 4.6 Prize Distribution

**EXISTS:**
- `Tournament.prize_pool`, `prize_currency`, `prize_deltacoin`
- `Tournament.prize_distribution` — JSONB (e.g., `{"1": "50%", "2": "30%", "3": "20%"}`)
- `PrizeTransaction` — Records prize amounts per placement
- `PrizeClaim` — Player claims their prize via preferred payout method

**WORKFLOW:**
```
Tournament → COMPLETED
    → TournamentResult created (winner, runner_up, third_place)
    → award_placements() service runs:
        - For each placement in prize_distribution:
            - Calculate amount from percentage
            - Create PrizeTransaction
            - If DeltaCoin: auto-credit wallet
            - If cash: create PrizeClaim (status: pending)
    → Players see prize in wallet or "Claim Prize" button
    → If cash claim:
        - Player selects payout method (bKash/Nagad/Rocket/Bank)
        - Enters payout destination (account number)
        - Organizer/admin processes manual payout
        - Admin marks PrizeClaim as PAID
```

**NEEDED:**
- Prize distribution preview tool (show exact amounts before tournament starts)
- Split prizes for tied placements
- Tax withholding calculations (if applicable)
- Prize claim deadline enforcement
- Automatic DeltaCoin prize distribution (no manual claim needed)
- Prize pool funded by entry fees calculation: `total_verified_payments * percentage`

### 4.7 Partial Payment Verification & MFS Edge Cases

**THE PROBLEM:** Bangladesh's mobile financial services (bKash, Nagad, Rocket) deduct cash-out charges from the sender. A player who needs to send ৳500 often sends ৳490 or ৳485 because they miscalculate the MFS fee. Currently, the organizer can only VERIFY (full amount) or REJECT — there is no middle ground.

#### 4.7.1 Partial Verification Status

**NEW PAYMENT STATUS:** `partially_verified`

Updated payment states:
```
PENDING → SUBMITTED → VERIFIED → (REFUNDED)
                   ↓
               REJECTED → (resubmit) → SUBMITTED
                   ↓
           PARTIALLY_VERIFIED → (balance resolved) → VERIFIED
                                                       ↓
                                                   EXPIRED
```

| Status | DB Value | Description |
|--------|----------|-------------|
| `partially_verified` | Payment received but amount is short. Player owes a balance. |

**NEW FIELDS ON Payment MODEL:**

| Field | Type | Description |
|-------|------|-------------|
| `received_amount` | DecimalField (nullable) | Actual amount received (may differ from `amount`) |
| `shortfall_amount` | DecimalField (nullable) | `amount - received_amount` (auto-calculated) |
| `overpayment_amount` | DecimalField (nullable) | `received_amount - amount` if overpaid |
| `partial_verification_note` | TextField (blank) | Organizer note (e.g., "Received ৳490, owes ৳10 MFS fee") |
| `shortfall_resolution` | CharField (nullable) | `deduct_from_prize` / `manual_collection` / `waived` |

**WORKFLOW:**
```
Organizer sees payment submission for ৳500, transaction shows ৳490 received
    → Clicks "Partially Verify"
    → Enters received_amount = 490
    → System calculates shortfall = 10
    → Selects resolution method:
        a) "Deduct from Prize" → shortfall deducted from any future prize winnings
        b) "Manual Collection" → organizer will collect remaining balance in person (LAN) or later
        c) "Waive" → absorb the difference (with reason)
    → Payment.status → PARTIALLY_VERIFIED
    → Registration.status → CONFIRMED (player can compete)
    → Shortfall flagged on participant's record
```

**OVERPAYMENT HANDLING:**
If `received_amount > amount`:
- Organizer notes the overpayment
- Surplus held in escrow or refunded at tournament end
- Tracked via `overpayment_amount` field

#### 4.7.2 Shortfall Deduction from Prizes

When a player with an outstanding shortfall wins a prize:
```
Prize awarded (e.g., ৳2000)
    → Check: Does player have any partially_verified payments with shortfall?
    → If yes: Deduct shortfall from prize
        → Net prize = ৳2000 - ৳10 = ৳1990
        → Payment.shortfall_amount → 0
        → Payment.status → VERIFIED (shortfall resolved)
        → PrizeTransaction records both: gross prize, deduction, net payout
    → If no: Normal prize distribution
```

### 4.8 Platform Take-Rate & Fee Deduction

**THE PROBLEM:** The Prize Distribution engine distributes the full `prize_pool` amount. It does not account for any platform service fee or organizer commission deducted from the pool before distribution.

**NEW FIELDS ON Tournament MODEL:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `platform_fee_percentage` | DecimalField(5,2) | `0.00` | Platform's percentage cut of the total prize pool |
| `platform_fee_flat` | DecimalField (nullable) | `null` | Flat platform fee (alternative to percentage) |
| `organizer_fee_percentage` | DecimalField(5,2) | `0.00` | Organizer's percentage cut (for profit-sharing tournaments) |
| `net_prize_pool` | DecimalField (computed) | — | `prize_pool - platform_fee - organizer_fee` (auto-calculated) |

**UPDATED PRIZE DISTRIBUTION PIPELINE:**
```
Tournament COMPLETED
    → Calculate gross prize pool = Tournament.prize_pool
    → Deduct platform fee:
        - If percentage: platform_cut = prize_pool × (platform_fee_percentage / 100)
        - If flat: platform_cut = platform_fee_flat
    → Deduct organizer fee:
        - organizer_cut = (prize_pool - platform_cut) × (organizer_fee_percentage / 100)
    → Net distributable pool = prize_pool - platform_cut - organizer_cut
    → Apply prize_distribution percentages to NET pool (not gross)
    → Create PrizeTransaction records with:
        - gross_amount (before deductions)
        - platform_fee_deducted
        - net_amount (actual payout)
    → Platform fee recorded as DeltaCrownTransaction (reason: `platform_fee`)
    → Organizer fee recorded as DeltaCrownTransaction (reason: `organizer_commission`)
```

**TOC VISIBILITY (Prize Distribution Preview):**

| Data Point | Description |
|------------|-------------|
| Gross Prize Pool | Total announced prize pool |
| Platform Fee | Amount/percentage deducted by DeltaCrown |
| Organizer Fee | Amount/percentage retained by organizer |
| Net Distributable | Actual amount going to players |
| Per-Placement Breakdown | Net amount per placement position |

### 4.10 Custom Bounties & Special Prizes

**THE PROBLEM:** The current prize distribution engine (`award_placements()`) only distributes prizes based on bracket placement (1st, 2nd, 3rd, etc.). But competitive tournaments routinely award non-placement prizes: Tournament MVP, Highest Fragger, Most Clutches, Best Newcomer, Community Vote Winner, etc. Organizers currently have no mechanism to allocate a portion of the prize pool to a specific user for a specific achievement — they must do this entirely off-platform via manual bank transfers, which creates no audit trail and breaks the financial record.

**SOLUTION:** A **Bounty System** that extends the Prize Distribution engine to support named, non-placement prize allocations. Organizers define bounties with descriptions and prize amounts, then assign them to any registered user post-tournament.

#### 4.10.1 New Model: `TournamentBounty`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `tournament` | FK → Tournament | Parent tournament |
| `name` | CharField(200) | Bounty display name (e.g., "Tournament MVP", "Highest Fragger") |
| `description` | TextField (blank) | Bounty description / criteria |
| `bounty_type` | CharField | `mvp` / `stat_leader` / `community_vote` / `special_achievement` / `custom` |
| `prize_amount` | DecimalField | Prize amount for this bounty |
| `prize_currency` | CharField | `BDT` / `deltacoin` |
| `source` | CharField | `prize_pool` (deducted from main pool) / `sponsor` (separate fund) / `platform` (DeltaCrown-funded) |
| `sponsor_name` | CharField(200, blank) | Sponsor name if source = sponsor (e.g., "Grameenphone Frag Award") |
| `is_assigned` | BooleanField (default False) | Whether a winner has been selected |
| `assigned_to` | FK → User (nullable) | Winner of the bounty |
| `assigned_to_registration` | FK → Registration (nullable) | Winner's registration context |
| `assigned_by` | FK → User (nullable) | Organizer who assigned |
| `assigned_at` | DateTimeField (nullable) | Assignment timestamp |
| `assignment_reason` | TextField (blank) | Justification ("42 kills across 6 matches — highest in tournament") |
| `claim_status` | CharField | `pending` / `claimed` / `paid_out` |
| `created_at` | DateTimeField (auto) | Bounty creation timestamp |

#### 4.10.2 Prize Pool Integration

```
Tournament Prize Pool: 50,000 BDT
    → Placement Allocation: 40,000 BDT (80%)
        → 1st: 20,000  2nd: 12,000  3rd: 8,000
    → Bounty Allocation: 10,000 BDT (20%)
        → MVP Award: 5,000 BDT (source: prize_pool)
        → Highest Fragger: 3,000 BDT (source: prize_pool)
        → Best Newcomer: 2,000 BDT (source: sponsor — "Robi Rising Star")
    → Validation:
        → SUM(placement_allocation + bounty_allocation where source='prize_pool') <= prize_pool
        → Sponsor-funded bounties do NOT count against the pool
        → Warn if bounty allocation > 30% of prize_pool (configurable threshold)
```

#### 4.10.3 Bounty Assignment Workflow

```
Tournament COMPLETED → Final results confirmed
    → Organizer opens TOC Prize tab → "Bounties" panel
    → Pre-defined bounties listed (created during tournament setup)
    → For each bounty:
        → Click "Assign Winner"
        → Search/select from registered participants
        → Add assignment_reason (optional but recommended)
        → Confirm assignment
    → System creates PrizeTransaction for the bounty:
        → If prize_currency == 'deltacoin': Credit winner's DeltaCrownWallet
        → If prize_currency == 'BDT': Create PrizeClaim (same flow as placement prizes)
    → Winner notified: "You've been awarded the {bounty.name}! Prize: {amount}"
    → Bounty appears on winner's profile and tournament results page
    → If KYC required (§4.9) and amount >= threshold: KYC gate applies
```

#### 4.10.4 TOC Bounty Management Panel

| Feature | Description |
|---------|-------------|
| **Bounty Setup** | Create/edit bounties during tournament settings phase (before or during tournament) |
| **Stat-Based Suggestions** | For `stat_leader` type: auto-suggest top performers based on tournament stats (kills, KDA, MVP count) |
| **Assign UI** | Dropdown/search of all participants; show relevant stats next to each name |
| **Budget Tracker** | Visual breakdown: "Pool: 50K → Placements: 40K | Bounties: 8K allocated / 10K budgeted | 2K unassigned" |
| **Multi-Winner Support** | Some bounties can have multiple winners (e.g., "All-Star Team" — 5 players each get 1,000 BDT) |
| **Bounty History** | Archive of bounties from previous tournaments (templates for re-use) |
| **Public Announcement** | "Announce Bounty Winners" button → pushes announcement to tournament lobby |

#### 4.10.5 Bounty Templates

| Template | Type | Typical Amount | Description |
|----------|------|---------------|-------------|
| **Tournament MVP** | `mvp` | 10% of pool | Overall best performer (organizer's choice) |
| **Highest Fragger** | `stat_leader` | 5% of pool | Most kills across the tournament |
| **Clutch King** | `stat_leader` | 3% of pool | Most clutch rounds won (manual or stat-tracked) |
| **Best Newcomer** | `special_achievement` | 3% of pool | Best performance from a first-time participant |
| **Community Favorite** | `community_vote` | 2% of pool | Voted by spectators/community (if fan voting enabled) |
| **Ace Award** | `special_achievement` | Fixed amount | First player to achieve an ace/pentakill in the tournament |

### 4.9 KYC / Identity Verification for Prize Claims

**THE PROBLEM:** DeltaCrown distributes cash prizes via `PrizeClaim`, but there is no identity verification gate before payout. Any account — including freshly-created alts, impersonators, or compromised accounts — can claim prizes without proving they are a real, unique person. This creates fraud risk, violates mobile money compliance norms (bKash/Nagad require real-name accounts), and exposes the platform to money-laundering liability.

**SOLUTION:** A configurable **KYC (Know Your Customer) verification** step that activates when a prize claim exceeds a monetary threshold. The player must upload identity documentation that an organizer or platform admin verifies before the payout is released.

#### 4.9.1 Configuration (Tournament-Level + Platform-Level)

| Setting | Level | Type | Default | Description |
|---------|-------|------|---------|-------------|
| `REQUIRE_KYC_FOR_PRIZES` | Platform | Feature Flag | `True` | Master toggle — when False, no KYC required anywhere |
| `kyc_threshold_amount` | Tournament | DecimalField | `500.00` (BDT) | Prize claim amount above which KYC is required |
| `kyc_threshold_currency` | Tournament | CharField | `BDT` | Currency for threshold comparison |
| `kyc_required_documents` | Tournament | JSONField | `["national_id"]` | Array of required document types |
| `kyc_auto_approve_returning` | Tournament | BooleanField | `False` | Auto-approve KYC if player was verified in a previous tournament within 6 months |

#### 4.9.2 Document Types

| Document Type | Code | Description |
|---------------|------|-------------|
| **National ID (NID)** | `national_id` | Bangladeshi NID card — front + back |
| **Passport** | `passport` | International passport photo page |
| **Student ID** | `student_id` | University/school student ID (for lower-tier events) |
| **Mobile Account Screenshot** | `mfs_account` | Screenshot of bKash/Nagad account showing registered name |
| **Selfie with ID** | `selfie_with_id` | Photo of player holding their ID next to their face |

#### 4.9.3 KYC Workflow

```
Tournament Completes → PrizeClaim created (status: pending)
    → IF prize_amount >= kyc_threshold_amount AND REQUIRE_KYC_FOR_PRIZES:
        → PrizeClaim.status → `kyc_required`
        → Player notified: "Submit identity verification to claim your prize"
        → Player uploads documents via Prize Claim page
        → KYCSubmission created (status: submitted)
        → Organizer/Admin reviews in TOC Prize tab:
            → APPROVE → PrizeClaim.status → `approved` → Payout proceeds
            → REJECT (reason: blurry, mismatch, expired) → Player can re-upload
            → FLAG → Escalate to platform admin for manual review
    → IF prize_amount < kyc_threshold_amount OR NOT REQUIRE_KYC_FOR_PRIZES:
        → Normal payout flow (no KYC gate)
    → IF kyc_auto_approve_returning AND player has valid KYC from <6 months:
        → Auto-approve; skip upload; notify player
```

#### 4.9.4 New Model: `KYCSubmission`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `user` | FK → User | Player submitting verification |
| `tournament` | FK → Tournament | Context tournament |
| `prize_claim` | FK → PrizeClaim | Associated prize claim |
| `document_type` | CharField | One of: `national_id`, `passport`, `student_id`, `mfs_account`, `selfie_with_id` |
| `document_front` | FileField | Front of document (image/PDF) |
| `document_back` | FileField (nullable) | Back of document (for NID) |
| `selfie_image` | ImageField (nullable) | Selfie with ID (if required) |
| `status` | CharField | `submitted` / `approved` / `rejected` / `flagged` / `expired` |
| `reviewer` | FK → User (nullable) | Admin/organizer who reviewed |
| `reviewed_at` | DateTimeField (nullable) | Review timestamp |
| `rejection_reason` | TextField (blank) | Why the submission was rejected |
| `expires_at` | DateTimeField | Verification valid until (default: 6 months from approval) |
| `created_at` | DateTimeField (auto) | Submission timestamp |

#### 4.9.5 TOC Prize Tab — KYC Review Panel

| Feature | Description |
|---------|-------------|
| **KYC Queue** | List of pending KYC submissions, sorted by prize amount descending |
| **Document Viewer** | Inline image viewer (zoom, rotate) for uploaded documents |
| **Name Cross-Check** | Display registered name, team name, and document name side-by-side for comparison |
| **Approve / Reject / Flag** | One-click actions with mandatory reason on reject |
| **Bulk Approve** | Select multiple submissions for bulk approval (e.g., returning players) |
| **KYC History** | View player's previous KYC submissions across all tournaments |
| **Expiry Tracking** | Warn when a player's KYC is about to expire |

#### 4.9.6 Privacy & Data Handling

| Concern | Policy |
|---------|--------|
| **Storage** | Documents stored in private S3 bucket with server-side encryption |
| **Access** | Only tournament organizer + platform admins can view documents |
| **Retention** | Documents auto-deleted 12 months after `expires_at`, or on user request |
| **GDPR / Privacy** | Player can request deletion of KYC data; platform must comply within 30 days |
| **Audit Trail** | All KYC reviews logged with reviewer, timestamp, and decision |

---

## 5. Pillar 4 — The Competition Engine

### 5.1 Supported Formats

| Format | DB Value | Status | Description |
|--------|----------|--------|-------------|
| **Single Elimination** | `single_elimination` | ✅ Implemented | Standard bracket, lose once = eliminated |
| **Double Elimination** | `double_elimination` | ✅ Implemented | Winners + losers bracket, lose twice = eliminated |
| **Round Robin** | `round_robin` | ✅ Implemented | Everyone plays everyone, points-based standings |
| **Swiss** | `swiss` | 🔶 Partially | Model exists, engine not fully wired |
| **Group Stage + Playoff** | `group_playoff` | 🔶 Partially | Models exist (Group, GroupStage, GroupStanding) |

### 5.2 Bracket Architecture

**Models:**
- `Bracket` — One per tournament. Contains `format`, `total_rounds`, `total_matches`, `bracket_structure` (JSONB metadata), `seeding_method`, `is_finalized`
- `BracketNode` — Individual slots in the bracket tree. Self-referential FK structure: `parent_node` (winner advances to), `child1_node`, `child2_node`. Contains `participant1_id/name`, `participant2_id/name`, `winner_id`, `match` (1:1 with Match), `bracket_type` (main/losers/third-place), `is_bye`
- `Match` — Actual match record linked from BracketNode

**Seeding Methods:**
| Method | DB Value | Description |
|--------|----------|-------------|
| Slot Order | `slot-order` | Registration order (first registered = seed 1) |
| Random | `random` | Random shuffle |
| Ranked | `ranked` | By team ELO/ranking from `TeamRanking` model |
| Manual | `manual` | Organizer drag-and-drop seeding |

### 5.3 Bracket Generation Pipeline

```
Organizer clicks "Generate Bracket" in TOC
    → POST to generate-bracket/
    → Validate: tournament in (registration_closed, live), confirmed registrations >= min_participants
    → Fetch confirmed registrations (optionally with seeds)
    → Route to BracketService.generate_bracket_universal_safe():
        → Feature flag check: BRACKETS_USE_UNIVERSAL_ENGINE
        → Calculate total rounds from participant count
        → Create Bracket record
        → Generate BracketNode tree (with byes for non-power-of-2 counts)
        → Apply seeding method to assign participants to nodes
        → Create Match records for each BracketNode
        → Link Match ↔ BracketNode
    → Broadcast via WebSocket (bracket_updated)
    → Publish event via event_bus
    → Return success with bracket data
```

### 5.4 Bracket Operations — TOC Actions

| Action | Endpoint | Description |
|--------|----------|-------------|
| Generate Bracket | `generate-bracket/` | Creates bracket + matches |
| Reset Bracket | `reset-bracket/` | Deletes bracket + all matches (only if no matches started) |
| Reorder Seeds | `reorder-seeds/` | Manual drag-and-drop seed assignment |
| Publish Bracket | `publish-bracket/` | Makes bracket visible to participants |

### 5.5 Group Stage System

**EXISTS (models):**
- `TournamentStage` — Multi-stage tournaments (e.g., Group Stage → Knockout)
  - Fields: `order`, `format`, `state` (pending/active/completed), `advancement_count`, `advancement_criteria` (top_n/top_n_per_group/all)
- `GroupStage` — Top-level group stage config: `num_groups`, `group_size`, `format` (round_robin/double_round_robin), `advancement_count_per_group`
- `Group` — Individual group: `name`, `max_participants`, `advancement_count`, `draw_seed`, `is_finalized`
- `GroupStanding` — Per-participant-per-group stats: `rank`, `matches_played/won/drawn/lost`, `points`, `goals_for/against/difference`, `rounds_won/lost`, `total_kills/deaths`, `kda_ratio`, `is_advancing`, `is_eliminated`, `game_stats` JSONB

**EXISTS (views):**
- `GroupConfigurationView` at `groups/configure/`
- `GroupDrawView` at `groups/draw/`

**GROUP STAGE WORKFLOW:**
```
Organizer configures group stage:
    → Set num_groups, group_size, advancement count
    → Choose draw method (random, seeded, manual)
    ↓
Draw:
    → Distribute confirmed registrations into groups
    → Create Group records with participants
    → Generate round-robin matches within each group
    ↓
Play:
    → Matches played within groups
    → GroupStanding auto-updated after each match
    → Tiebreaker rules applied (configurable)
    ↓
Advancement:
    → Top N from each group advance
    → Create knockout bracket from advancing teams
    → Seed based on group standings
```

**NEEDED:**
| Feature | Description |
|---------|-------------|
| **Group Draw Animation** | Visual draw ceremony (assign teams to groups one by one) |
| **Group Tiebreaker Config** | Configurable tiebreaker hierarchy (head-to-head → goal difference → goals scored → coin flip) |
| **Cross-Group Comparison** | Best 3rd-place teams advancing (like FIFA World Cup format) |
| **Group Rebalancing** | If a team withdraws, redistribute groups to maintain balance |
| **Double Round-Robin** | Each team plays every other team twice (home/away concept) |

### 5.6 Swiss System

**EXISTS:** Model `format: swiss` in choices but engine not fully implemented.

**NEEDED - COMPLETE SWISS ENGINE:**
```
Round N:
    → Pair players/teams with similar records (same W-L)
    → Avoid repeat matchups
    → Apply Buchholz tiebreaker
    → Generate Round N matches
    ↓
After Round N:
    → Update standings
    → Calculate Buchholz, Sonneborn-Berger, etc.
    → Check termination: players with X wins advance, players with X losses eliminated
    → If not all decided: proceed to Round N+1
    ↓
Final standings determined by record + tiebreakers
```

**Swiss-specific fields needed:**
- Max rounds (usually log2(participants) + 1)
- Win threshold for advancement
- Loss threshold for elimination
- Tiebreaker hierarchy: Buchholz → Sonneborn-Berger → head-to-head → median

### 5.7 Re-Seeding & Dynamic Bracketing

**NEEDED for Tier-1:**
| Feature | Description |
|---------|-------------|
| **Re-seeding between stages** | After group stage, re-seed knockout bracket based on group performance |
| **Forfeit cascade** | When a team is DQ'd mid-bracket, advance their opponent and cascade through subsequent rounds |
| **Late substitution** | Allow roster changes mid-tournament with organizer approval |
| **Bracket freeze** | Lock bracket from further changes once matches begin |
| **Match dependency chain** | Clear visibility of which matches feed into which |

### 5.8 Double Elimination — Bracket Reset (True Finals)

**THE PROBLEM:** In Double Elimination, the Grand Final pits the Winners Bracket champion against the Losers Bracket champion. The Winners Bracket champion has never lost — they have earned the right to "lose twice" before being eliminated. If the Losers Bracket champion wins the Grand Final, the bracket must reset to a **second Grand Final** to maintain competitive fairness.

**RULE:** The "Bracket Reset" (also called "True Finals") is the most complex and defining mechanic of Double Elimination. The current implementation must explicitly handle this.

**LOGIC:**
```
Grand Final (Match G):
    Winner = Winners Bracket Champion (Team A)
    vs.
    Winner = Losers Bracket Champion (Team B)
    ↓
IF Team A wins Match G:
    → Tournament complete. Team A is champion.
    → No bracket reset needed (Team A never lost).
    ↓
IF Team B wins Match G:
    → Both teams now have exactly 1 loss each.
    → BRACKET RESET TRIGGERED.
    → System auto-generates Grand Final Reset (Match G2).
    → Match G2: Team A vs Team B (rematch).
    → Winner of Match G2 = Tournament Champion.
```

**IMPLEMENTATION REQUIREMENTS:**

| Requirement | Description |
|-------------|-------------|
| **Auto-Detection** | After Grand Final score submission, BracketService checks: did the Losers Bracket team win? |
| **Auto-Generation** | If bracket reset triggered, automatically create a new BracketNode + Match for the reset match |
| **Bracket Tree Update** | The new Grand Final Reset node becomes the actual final node; original Grand Final becomes semi-final in the tree |
| **WebSocket Broadcast** | Push `bracket_reset_triggered` event to all connected clients |
| **UI Indicator** | Bracket display must clearly label "Grand Final" vs "Grand Final Reset" |
| **Total Rounds Update** | `Bracket.total_rounds` and `Bracket.total_matches` must increment when bracket reset occurs |

**DATA MODEL:**

| Field | Type | Description |
|-------|------|-------------|
| `BracketNode.is_bracket_reset` | BooleanField (default False) | Marks this node as a bracket reset match |
| `Bracket.bracket_reset_triggered` | BooleanField (default False) | Whether this bracket has undergone a reset |
| `Match.is_bracket_reset_match` | BooleanField (default False) | Mirror flag on Match for easy querying |

**EDGE CASES:**
- If the original Grand Final is cancelled/forfeited, no bracket reset applies
- If the Grand Final ends in a dispute, bracket reset decision deferred until dispute resolved
- Organizer can manually override and skip bracket reset (with audit log + reason)

### 5.9 Seed-Based Map/Side Advantage

**THE PROBLEM:** Map vetoes and side selection are mentioned in match lobby features, but the system does not define **who acts first** based on bracket seeding. In competitive esports, the higher seed earns a tangible advantage.

**RULE:** The bracket engine must pass **Seed Advantage** metadata to the Match Lobby. The higher-seeded team receives "First Action" privilege.

**IMPLEMENTATION:**

| Field | Type | Description |
|-------|------|-------------|
| `Match.higher_seed_participant` | FK → Registration (nullable) | Auto-set by bracket engine based on seeding |
| `Match.seed_advantage_type` | CharField (nullable) | `first_pick` / `first_ban` / `side_selection` / `none` |
| `Tournament.seed_advantage_rule` | CharField | `first_pick` / `first_ban` / `side_selection` / `none` (default: `none`) |

**AUTO-ASSIGNMENT LOGIC:**
```
When BracketNode is populated with two participants:
    → Compare seed numbers (from Bracket seeding)
    → Lower seed number = higher seed (Seed #1 > Seed #8)
    → Set Match.higher_seed_participant = higher seed
    → Set Match.seed_advantage_type = Tournament.seed_advantage_rule
```

**MATCH LOBBY INTEGRATION:**
- Match Lobby displays: "[Team A] has First Pick/Ban advantage (Seed #1)"
- Map veto system enforces turn order: higher seed acts first
- Side selection: higher seed chooses Team A / Team B (CT/T, Attackers/Defenders)

**SPECIAL CASES:**

| Scenario | Handling |
|----------|----------|
| **Same seed** (e.g., group stage crossover) | Coin flip / random assignment |
| **Manual seeding override** | Organizer can manually set advantage |
| **Grand Final Reset** | Advantage carried by the original upper bracket champion |
| **No seeding** (random bracket) | No advantage assigned; both teams equal |

### 5.10 Live Broadcast Director — Draw Control Panel

**THE PROBLEM:** The backend supports Live Draws via `LiveDrawConsumer` WebSocket, and the Group Stage system can distribute teams randomly/seeded/manually. But the TOC has no **control interface** for the organizer to theatrically direct the draw ceremony. The organizer cannot control the pace — all teams are assigned at once, with no suspense.

**SOLUTION:** A "Live Broadcast Director" view in the TOC that gives the organizer a step-by-step control panel to reveal one team at a time into each group.

#### 5.10.1 Draw Director View (TOC — Brackets/Groups Tab)

**Access:** When a tournament uses Group Stage format and groups are not yet finalized, a "Start Live Draw" button appears in the Brackets/Groups tab.

**WORKFLOW:**
```
Organizer clicks "Start Live Draw"
    → System validates: confirmed registrations ≥ min_participants, groups configured
    → Draw pool populated: all confirmed registrations shuffled (or seeded, per config)
    → WebSocket channel opened: tournament.{id}.live_draw
    → Public tournament page switches to "Live Draw" mode
    ↓
Draw Director Panel shows:
    ┌─────────────────────────────────────────────┐
    │  LIVE DRAW DIRECTOR                         │
    │                                             │
    │  Remaining in Pool: 97 teams                │
    │  Next Group Slot:   Group A — Slot 3 of 10  │
    │                                             │
    │  [ 🎲 DRAW NEXT TEAM ]   [ ⏸ Pause Draw ]  │
    │                                             │
    │  Group A: Team1, Team2, ___                 │
    │  Group B: Team3, ___                        │
    │  Group C: ___                               │
    │  ...                                        │
    └─────────────────────────────────────────────┘
    ↓
Organizer clicks "Draw Next Team":
    → System selects next team from pool (random or seeded algorithm)
    → WebSocket push: { event: 'team_drawn', team: {...}, group: 'A', slot: 3 }
    → Public page shows reveal animation (the team name appears with suspense)
    → Organizer sees confirmation and updated group state
    → Process repeats until all teams placed
    ↓
Organizer clicks "Finalize Draw":
    → All Group records created/finalized
    → Round-robin matches generated within each group
    → Draw results published
    → WebSocket push: { event: 'draw_complete', groups: [...] }
```

#### 5.10.2 Draw Algorithm Options

| Algorithm | Description | Use Case |
|-----------|-------------|----------|
| **Pure Random** | Teams drawn in random order from shuffled pool | Default, maximally fair |
| **Seeded Pots** | Pool divided into pots by ranking; one from each pot per group (FIFA World Cup style) | Ensures balanced group strength |
| **Manual Override** | Organizer can manually assign the next team instead of random draw | Fix errors, invited teams |
| **Pre-Drawn (Instant)** | Skip the ceremony; auto-assign all teams instantly | When live draw not needed |

#### 5.10.3 WebSocket Events

| Event | Payload | Receiver |
|-------|---------|----------|
| `draw_started` | `{ total_teams, num_groups, group_size }` | Public page + Broadcast feed |
| `team_drawn` | `{ team_name, team_logo, group_name, slot_number, remaining }` | Public page + Broadcast feed |
| `draw_paused` | `{ paused_by }` | Public page |
| `draw_resumed` | `{ resumed_by }` | Public page |
| `draw_complete` | `{ groups: [{name, teams: [...]}] }` | Public page + Broadcast feed |

#### 5.10.4 Draw Director Features

| Feature | Description |
|---------|-------------|
| **Pause/Resume** | Organizer can pause the draw (e.g., for commentary, technical issues) |
| **Undo Last Draw** | Put the last drawn team back into the pool (for errors) |
| **Skip Group** | Move to next group's slot (fill groups round-robin style for suspense) |
| **Commentary Timer** | Optional countdown timer between draws (e.g., 10s delay for stream pacing) |
| **Audience Counter** | Show number of connected WebSocket viewers |
| **Draw History Log** | Real-time log showing: "14:32:05 — Team Phoenix drawn into Group C (Slot 2)" |

**INTEGRATION WITH BROADCAST API:**
The Broadcast Feed (§8.6) should include a `/broadcast/{token}/draw/` endpoint that streams draw events in real-time, allowing OBS overlays to render the draw animation directly on stream.

### 5.11 Multi-Wave Qualifier Pipelines

**THE PROBLEM:** Large-scale tournaments routinely operate in multiple stages: Open Qualifier A → Open Qualifier B → Closed Qualifier → Main Event. Each stage is currently a separate `Tournament` object with no formal linkage. The organizer must manually copy qualifying teams from one tournament's results into the next tournament's registration list. This breaks when: (a) the qualifier isn't completed yet (organizer pre-registers teams that might not qualify), (b) team rosters change between qualifiers, and (c) there's no auditable record of *how* a team earned their main event slot.

**SOLUTION:** A **Qualifier Pipeline** system that links multiple tournament stages into a single pipeline, with auto-promotion rules that advance qualifying teams from one stage to the next.

#### 5.11.1 Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  QUALIFIER PIPELINE: "DeltaCrown Season 3 Championship"      │
│                                                              │
│  Stage 1: Open Qualifier A ──┐                               │
│    (256 teams → Top 8)       │                               │
│                              ├──→ Stage 3: Closed Qualifier  │
│  Stage 2: Open Qualifier B ──┘      (16 teams → Top 4)      │
│    (256 teams → Top 8)                     │                 │
│                                            ▼                 │
│                              Stage 4: Main Event             │
│                                (4 qualified + 4 invited)     │
│                                                              │
│  Invited Slots: [Team X] [Team Y] [Team Z] [Team W]         │
│    (Direct invite — bypass qualifiers)                       │
└──────────────────────────────────────────────────────────────┘
```

#### 5.11.2 New Model: `QualifierPipeline`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `name` | CharField(200) | Pipeline display name (e.g., "Season 3 Championship") |
| `slug` | SlugField (unique) | URL-safe identifier |
| `organizer` | FK → User | Pipeline owner |
| `organization` | FK → Organization (nullable) | Org context |
| `game` | FK → Game | Game for all stages |
| `status` | CharField | `draft` / `active` / `completed` / `cancelled` |
| `created_at` | DateTimeField (auto) | Creation timestamp |
| `description` | TextField (blank) | Public description / overview |

#### 5.11.3 New Model: `PipelineStage`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `pipeline` | FK → QualifierPipeline | Parent pipeline |
| `tournament` | OneToOneField → Tournament | The actual tournament for this stage |
| `stage_order` | PositiveIntegerField | Execution order (1 = first qualifier, N = main event) |
| `stage_type` | CharField | `open_qualifier` / `closed_qualifier` / `main_event` / `play_in` / `last_chance` |
| `is_final_stage` | BooleanField (default False) | Whether this is the main event |

#### 5.11.4 New Model: `PromotionRule`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `source_stage` | FK → PipelineStage | Where teams qualify from |
| `target_stage` | FK → PipelineStage | Where teams auto-advance to |
| `promotion_criteria` | CharField | `top_n` / `top_percentage` / `group_winners` / `manual` |
| `promotion_count` | PositiveIntegerField (nullable) | Number of teams to promote (for `top_n`) |
| `promotion_percentage` | DecimalField (nullable) | Percentage of teams to promote (for `top_percentage`) |
| `seed_carry_forward` | BooleanField (default True) | Whether to carry qualifier placement as seed into next stage |
| `auto_register` | BooleanField (default True) | Auto-create Registration in target tournament on promotion |
| `auto_confirm` | BooleanField (default True) | Auto-confirm registration (skip payment if main event is free for qualifiers) |

#### 5.11.5 New Model: `PipelineInvite`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `pipeline` | FK → QualifierPipeline | Parent pipeline |
| `target_stage` | FK → PipelineStage | Stage the invite is for (usually main event) |
| `team` | FK → Team (nullable) | Invited team |
| `player` | FK → User (nullable) | Invited solo player |
| `invite_reason` | CharField(200) | "Defending champion", "Regional qualifier winner", "Partner invite" |
| `status` | CharField | `pending` / `accepted` / `declined` / `expired` |
| `invited_by` | FK → User | Organizer who sent invite |
| `responded_at` | DateTimeField (nullable) | When invite was accepted/declined |
| `expires_at` | DateTimeField (nullable) | Invite expiry deadline |

#### 5.11.6 Promotion Workflow

```
Source Stage Tournament Completes
    → TournamentResult finalized (placements determined)
    → System evaluates PromotionRule for this stage:
        → IF promotion_criteria == 'top_n':
            → Take top N teams from TournamentResult
        → IF promotion_criteria == 'top_percentage':
            → Take top X% of participants
        → IF promotion_criteria == 'group_winners':
            → Take teams where GroupStanding.is_advancing == True
        → IF promotion_criteria == 'manual':
            → Organizer manually selects teams in TOC Pipeline tab
    → For each promoted team:
        → IF auto_register: Create Registration in target_stage.tournament
        → IF auto_confirm: Set Registration.status = CONFIRMED
        → IF seed_carry_forward: Store qualifier_seed on Registration
        → Create PromotionRecord (audit trail)
    → Notify promoted teams: "You've qualified for {target_stage.tournament.title}!"
    → Pipeline dashboard updates with promotion status
```

#### 5.11.7 TOC Pipeline Management Tab

| Feature | Description |
|---------|-------------|
| **Pipeline Overview** | Visual pipeline diagram showing all stages, team counts, and flow |
| **Stage Status** | Per-stage status (draft/active/completed) with progress bars |
| **Promotion Queue** | After a stage completes, shows pending promotions for organizer review |
| **Manual Override** | Organizer can manually promote/demote teams (override auto-rules) |
| **Invite Manager** | Send/track direct invites to the main event |
| **Cross-Stage Roster Check** | Verify team rosters haven't changed between qualifier and main event |
| **Seed Preview** | Show projected seeding in the next stage based on current qualifier standings |
| **Pipeline Analytics** | Total unique teams across all stages, qualification rate, dropout rate |

### 5.12 Drag-and-Drop Tiebreaker Engine

**THE PROBLEM:** Group Stages and Swiss formats require tiebreaker rules when teams are level on points. The current `GroupStanding` model sorts by `points` → `goal_difference` → `total_kills` → `pk` — a hardcoded ordering that cannot be customized. Different games and tournament cultures demand different tiebreaker hierarchies. PUBG Mobile uses total kills as the primary differentiator; CS2 uses round difference; football-style tournaments use head-to-head first. Organizers have no control over this.

**SOLUTION:** A **configurable Tiebreaker Hierarchy** stored as a JSON array on the tournament/stage level. Organizers build the tiebreaker order via a drag-and-drop interface in the TOC Settings tab, and the Group Standing / Swiss sorting engine evaluates them in sequence.

#### 5.12.1 Tiebreaker Configuration

**New Fields on `Tournament` / `GroupStage`:**

| Field | Model | Type | Default |
|-------|-------|------|---------|
| `tiebreaker_hierarchy` | Tournament | JSONField | `["points", "head_to_head", "round_difference", "total_kills", "goal_difference"]` |
| `tiebreaker_hierarchy` | GroupStage (overrides tournament) | JSONField (nullable) | `null` (inherit from tournament) |

**Available Tiebreaker Criteria:**

| Criterion | Code | Description | Data Source |
|-----------|------|-------------|-------------|
| **Points** | `points` | Total match points (W=3, D=1, L=0 or custom) | `GroupStanding.points` |
| **Head-to-Head** | `head_to_head` | Direct result between tied teams | Computed from `Match` records |
| **Round Difference** | `round_difference` | Rounds won minus rounds lost | `GroupStanding.rounds_won - rounds_lost` |
| **Goal/Objective Difference** | `goal_difference` | Goals/objectives for minus against | `GroupStanding.goals_for - goals_against` |
| **Total Kills** | `total_kills` | Aggregate kills across all group matches | `GroupStanding.total_kills` |
| **Kill/Death Ratio** | `kda_ratio` | Aggregate KDA ratio | `GroupStanding.kda_ratio` |
| **Total Score** | `total_score` | Sum of all match scores | `GroupStanding.total_score` |
| **Rounds Won** | `rounds_won` | Total rounds won (without deducting losses) | `GroupStanding.rounds_won` |
| **Goals For** | `goals_for` | Total goals/objectives scored | `GroupStanding.goals_for` |
| **Placement Points (BR)** | `placement_points` | BR placement points (uses BR Scoring Matrix §8.10) | `GroupStanding.placement_points` |
| **Average Placement (BR)** | `avg_placement` | Average finish position in BR matches | `GroupStanding.average_placement` |
| **Buchholz Score (Swiss)** | `buchholz` | Sum of opponents' scores (Swiss tiebreaker) | Computed from Match + GroupStanding |
| **Median Buchholz (Swiss)** | `median_buchholz` | Buchholz minus best and worst opponent scores | Computed |
| **Sonneborn-Berger** | `sonneborn_berger` | Sum of defeated opponents' scores (chess/Swiss) | Computed |
| **Coin Flip / Random** | `random` | Random tiebreak (last resort) | System RNG |

#### 5.12.2 Tiebreaker Resolution Algorithm

```python
def resolve_tiebreaker(tied_teams: list, hierarchy: list[str], group_matches: list) -> list:
    """
    Recursively break ties using the configured hierarchy.
    Returns teams in resolved order.
    """
    if len(tied_teams) <= 1 or not hierarchy:
        return tied_teams  # Can't break further

    criterion = hierarchy[0]
    remaining_criteria = hierarchy[1:]

    if criterion == 'head_to_head':
        # Special: only meaningful for 2-team ties
        # For 3+ teams: compute mini-table among tied teams only
        scores = compute_head_to_head(tied_teams, group_matches)
    elif criterion == 'buchholz':
        scores = compute_buchholz(tied_teams, group_matches)
    elif criterion == 'median_buchholz':
        scores = compute_median_buchholz(tied_teams, group_matches)
    elif criterion == 'sonneborn_berger':
        scores = compute_sonneborn_berger(tied_teams, group_matches)
    elif criterion == 'random':
        random.shuffle(tied_teams)
        return tied_teams
    else:
        # Direct field lookup on GroupStanding
        scores = {team: getattr(team.standing, criterion, 0) for team in tied_teams}

    # Group by score value
    grouped = group_by_score(tied_teams, scores)  # {score: [teams]}

    result = []
    for score in sorted(grouped.keys(), reverse=True):
        sub_tied = grouped[score]
        if len(sub_tied) > 1:
            # Still tied — recurse with next criterion
            result.extend(resolve_tiebreaker(sub_tied, remaining_criteria, group_matches))
        else:
            result.extend(sub_tied)

    return result
```

#### 5.12.3 TOC Tiebreaker Configuration UI

```
┌─────────────────────────────────────────────────────────┐
│  TIEBREAKER HIERARCHY                                   │
│                                                         │
│  Drag to reorder:                                       │
│                                                         │
│  1. ☰ Points                            [🔒 Required]   │
│  2. ☰ Head-to-Head                      [✕ Remove]      │
│  3. ☰ Round Difference                  [✕ Remove]      │
│  4. ☰ Total Kills                       [✕ Remove]      │
│  5. ☰ Random (Final Tiebreaker)         [🔒 Required]   │
│                                                         │
│  [+ Add Criterion ▾]                                    │
│                                                         │
│  Presets: [FPS Standard ▾] [BR Standard] [Swiss Chess]  │
│           [Football/Soccer] [Custom]                    │
│                                                         │
│  [ Preview Standings with Current Hierarchy ]            │
└─────────────────────────────────────────────────────────┘
```

#### 5.12.4 Built-In Presets

| Preset | Hierarchy |
|--------|-----------|
| **FPS Standard** | Points → Head-to-Head → Round Difference → Total Kills → Random |
| **BR Standard** | Points → Placement Points → Total Kills → Avg Placement → Random |
| **Swiss Chess** | Points → Buchholz → Median Buchholz → Sonneborn-Berger → Random |
| **Football/Soccer** | Points → Goal Difference → Goals For → Head-to-Head → Random |
| **MOBA Standard** | Points → Head-to-Head → KDA Ratio → Total Score → Random |

#### 5.12.5 Integration Points

| System | Integration |
|--------|-------------|
| **GroupStanding sorting** | `get_group_standings()` uses `tiebreaker_hierarchy` instead of hardcoded sort |
| **Swiss pairing** | Swiss engine uses hierarchy for opponent strength ranking |
| **Bracket seeding** | When groups feed into playoffs, tiebreaker order determines seed positions |
| **Standings display** | Public standings page shows the active tiebreaker hierarchy as a tooltip/footer |
| **Broadcast widget** | Iframe standings widget (§8.8) reflects tiebreaker-resolved ordering |
| **BR Scoring Matrix** | Placement Points criterion reads from BR Scoring Matrix (§8.10) configuration |

---

## 6. Pillar 5 — Live Match Operations & Match Medic

### 6.1 Match State Machine

```
SCHEDULED → CHECK_IN → READY → LIVE → PENDING_RESULT → COMPLETED
                                 ↓                         ↓
                             DISPUTED                   FORFEIT
                                                          ↓
                                                      CANCELLED
```

| State | DB Value | Description |
|-------|----------|-------------|
| `scheduled` | Match created but not yet started. Time assigned. |
| `check_in` | Match-level check-in open (participants confirm readiness). |
| `ready` | Both participants checked in. Ready to play. |
| `live` | Match actively being played. |
| `pending_result` | Match played, awaiting result submission. |
| `completed` | Result confirmed and finalized. |
| `disputed` | Result challenged by a participant. |
| `forfeit` | One or both sides forfeited. |
| `cancelled` | Match cancelled by organizer. |

### 6.2 Match Operations — TOC Actions

| Action | Endpoint | Method | Description |
|--------|----------|--------|-------------|
| Submit Score | `submit-score/<match_id>/` | POST | Organizer enters final score |
| Reschedule | `reschedule-match/<match_id>/` | POST | Change scheduled_time |
| Forfeit | `forfeit-match/<match_id>/` | POST | Declare forfeit for one side |
| Override Score | `override-score/<match_id>/` | POST | Force override previously submitted score |
| Cancel Match | `cancel-match/<match_id>/` | POST | Cancel match entirely |
| Mark Live | `match-ops/<match_id>/mark-live/` | POST | Manually set match to LIVE |
| Pause | `match-ops/<match_id>/pause/` | POST | Pause a live match |
| Resume | `match-ops/<match_id>/resume/` | POST | Resume paused match |
| Force Complete | `match-ops/<match_id>/force-complete/` | POST | Force a stuck match to completed |
| Add Note | `match-ops/<match_id>/add-note/` | POST | Add organizer note to match |
| Force Start | `match-ops/<match_id>/force-start/` | POST | Start match without both check-ins |
| Auto Schedule Round | `auto-schedule-round/` | POST | Auto-assign times to unscheduled matches |
| Bulk Shift | `bulk-shift-matches/` | POST | Shift all match times by N minutes |
| Add Break | `add-schedule-break/` | POST | Insert break between rounds |

### 6.3 Result Submission Pipeline

**EXISTS (MatchResultSubmission model):**
```
Participant submits result:
    → Creates MatchResultSubmission with:
        - raw_result_payload (JSONB: scores, map info, etc.)
        - proof_screenshot_url
        - submitter_notes
        - auto_confirm_deadline (datetime)
    → Status: PENDING
    ↓
Opponent confirms/disputes:
    → CONFIRM: Status → CONFIRMED → auto-finalize
    → DISPUTE: Status → DISPUTED → DisputeRecord created
    ↓
If no response by auto_confirm_deadline:
    → Status: AUTO_CONFIRMED → auto-finalize
    ↓
Organizer can also finalize directly:
    → Status: FINALIZED
    → Match scores updated
    → Match state → COMPLETED
    → Winner/loser set
    → Bracket progression triggered (winner advances to parent node)
```

**ResultVerificationLog** tracks each step: `schema_validation`, `scoring_calculation`, `organizer_review`, `finalization`, `opponent_confirm`, `opponent_dispute`, `dispute_escalated`, `dispute_resolved`

### 6.4 Match Lobby Information

**EXISTS on Match model:**
- `lobby_info` — JSONB for game-specific lobby data: room code, password, server IP, map, etc.
- `stream_url` — URL for match stream

**NEEDED:**
| Feature | Description |
|---------|-------------|
| **Lobby Code Generator** | Auto-generate or organizer-set lobby codes per match |
| **Map/Veto System** | Map ban/pick workflow for games that support map selection |
| **Server Assignment** | Auto-assign game servers from a pool (for LAN/dedicated server tournaments) |
| **Match Room Chat** | Per-match communication channel (Discord thread or in-app) |
| **Ready-Up Protocol** | Both sides must click "Ready" before match can begin |
| **Anti-Cheat Integration** | Placeholder for future anti-cheat service integration |
| **Match Timer** | Track elapsed match time for scheduling purposes |
| **Best-of-N Support** | Matches can be best-of-3, best-of-5, etc. with per-game scores |

### 6.5 Match Medic — Organizer Intervention Tools

**CONCEPT:** "Match Medic" is the organizer's ability to intervene in any match at any point.

**EXISTING:**
- Force-start, pause, resume, force-complete
- Override score, cancel match
- Add organizer notes

**NEEDED:**
| Tool | Description |
|------|-------------|
| **Match Timeline View** | Complete timeline of every event in a match (check-in, start, score submission, disputes, notes, pauses) |
| **Match Reset** | Reset a match to SCHEDULED state (clear all scores, submissions) |
| **Technical Timeout** | Pause all matches in a round due to technical issues |
| **Match Swap** | Swap two participants in a match (fix bracket seeding errors) |
| **Bulk Score Entry** | Enter scores for multiple matches at once (for organizers running offline events) |
| **Match Replay/Rematch** | Create a rematch of a completed match (preserve original, create new) |
| **Walkover Declaration** | Declare walkover (opponent advances, no score recorded) |
| **Score Audit** | Show all score submissions, overrides, and changes with timestamps |

### 6.6 Scoring & Result Architecture

**CURRENT Match fields:**
- `participant1_score`, `participant2_score` (PositiveIntegerField)
- `winner_id`, `loser_id`

**TournamentResult model (per-tournament):**
- `winner`, `runner_up`, `third_place` (FK → Registration)
- `determination_method` (normal/tiebreaker/forfeit_chain/manual)
- `series_score` (JSONB), `game_results` (JSONB)
- `total_kills`, `best_placement`, `avg_placement`, `matches_played`
- `is_override`, `override_reason`, `override_actor`, `override_timestamp`

**NEEDED:**
| Feature | Description |
|---------|-------------|
| **Game-Specific Scoring** | Different games have different score formats (kills vs rounds vs objectives) |
| **Map-Level Scores** | For BO3/BO5, store per-map scores |
| **Custom Score Fields** | Organizer defines what scores to collect (kills, deaths, assists, damage, etc.) |
| **Score Validation Rules** | Auto-validate scores (e.g., in CS2, max rounds per half = 12+1, overtime rules) |
| **Score Import** | Import scores from game APIs or CSV |

### 6.7 Data-Entry Verification UI — API-Less Score Verification

**THE PROBLEM:** DeltaCrown has no game API integrations. All match results are manually entered by participants and verified by organizers. The current workflow forces the organizer to: (1) open the score submission, (2) copy the proof screenshot URL, (3) open it in a new tab, (4) mentally compare the screenshot against the typed scores. This is slow, error-prone, and doesn't scale when an organizer is verifying 50+ match results in a live tournament.

**SOLUTION:** A purpose-built **split-screen verification UI** in the TOC Match Operations tab that places the proof screenshot directly next to the score input fields.

#### 6.7.1 Verification Split-Screen Layout

**CONCEPT:**
```
┌──────────────────────────────────┬──────────────────────────────────┐
│  LEFT PANEL: Evidence Viewer     │  RIGHT PANEL: Score Entry        │
│                                  │                                  │
│  [Player-uploaded screenshot]    │  Match: Team A vs Team B         │
│  ┌────────────────────────────┐  │  Round: Quarterfinal — BO3       │
│  │                            │  │                                  │
│  │   End-game scoreboard      │  │  Map 1: Ascent                   │
│  │   screenshot displayed     │  │  Team A Score: [13]              │
│  │   at full resolution       │  │  Team B Score: [11]              │
│  │                            │  │                                  │
│  │   🔍 Zoom  ↻ Rotate       │  │  Map 2: Haven                    │
│  │                            │  │  Team A Score: [9]               │
│  └────────────────────────────┘  │  Team B Score: [13]              │
│                                  │                                  │
│  Submitted by: Captain_A         │  Map 3: Bind                     │
│  Submitted at: 14:32 BST        │  Team A Score: [___]             │
│  TrxID: N/A (score, not pay)    │  Team B Score: [___]             │
│                                  │                                  │
│  [View Captain B's Screenshot]   │  Custom Fields:                  │
│                                  │  MVP: [___]  Total Kills: [___] │
│                                  │                                  │
│                                  │  [ ✅ Confirm ] [ ❌ Dispute ]  │
│                                  │  [ ✏️ Override ] [ 📝 Add Note ] │
└──────────────────────────────────┴──────────────────────────────────┘
```

#### 6.7.2 Evidence Viewer Features

| Feature | Description |
|---------|-------------|
| **Inline Image Display** | Screenshot rendered directly in the panel — no new tabs |
| **Zoom & Pan** | Pinch-to-zoom / scroll-to-zoom on the screenshot for reading small text |
| **Rotate** | Rotate image 90°/180° (players sometimes upload sideways screenshots) |
| **Toggle Between Submissions** | Tab between Captain A and Captain B screenshots side-by-side |
| **Lightbox Fullscreen** | Click to expand screenshot to fullscreen overlay |
| **Image Gallery** | If multiple proof images uploaded, carousel/gallery navigation |

#### 6.7.3 Smart Mismatch Detection

When both captains have submitted results:

| Scenario | UI Indicator |
|----------|-------------|
| **Scores match perfectly** | Green banner: "✅ Both submissions agree. Auto-confirm available." |
| **Scores differ** | Red banner: "⚠️ MISMATCH — Captain A says 13-11, Captain B says 12-13. Review required." |
| **Only one submitted** | Yellow banner: "⏳ Waiting for opponent submission. Auto-confirm in {hours}h." |
| **Custom fields differ** | Orange banner: "Scores match but stats differ (kills: 45 vs 42). Minor discrepancy." |

#### 6.7.4 Bulk Score Verification Queue

For tournaments with 50+ matches, the organizer needs to process verifications quickly:

```
┌─────────────────────────────────────────────────────────┐
│  SCORE VERIFICATION QUEUE                      12 / 32  │
│                                                         │
│  ⬅ Previous Match     Current: QF-3     Next Match ➡   │
│                                                         │
│  [Split-screen view as above]                           │
│                                                         │
│  Quick Actions:                                         │
│  [ ✅ Approve & Next ]  [ ❌ Reject & Next ]  [ ⏭ Skip ]│
└─────────────────────────────────────────────────────────┘
```

| Feature | Description |
|---------|-------------|
| **Queue Navigation** | Previous / Next buttons cycle through all pending verifications |
| **Approve & Next** | One-click confirm + auto-advance to next pending match |
| **Progress Counter** | "12 of 32 verified" with progress bar |
| **Filter Queue** | Show only: mismatches, single submissions, specific rounds |
| **Keyboard Shortcuts** | `Enter` = Approve & Next, `Esc` = Skip, `D` = Dispute |

### 6.8 Mutual Reschedule Requests

**THE PROBLEM:** Matches are scheduled at fixed times by the bracket engine or organizer. When both teams agree they'd prefer a different time, there's no formal workflow — they message the organizer on WhatsApp/Discord, who manually changes the match time. This is untracked, creates no audit trail, and scales terribly in a 64-team bracket with 20+ reschedule requests.

**SOLUTION:** A **team-initiated reschedule request** workflow where one team proposes a new time, the opponent confirms or counter-proposes, and the system auto-approves if the new time doesn't conflict with the round deadline.

#### 6.8.1 New Model: `RescheduleRequest`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `match` | FK → Match | The match being rescheduled |
| `requested_by` | FK → User | Captain who initiated the request |
| `requested_by_team` | FK → Registration | Team requesting the change |
| `original_time` | DateTimeField | Original scheduled match time |
| `proposed_time` | DateTimeField | New proposed time |
| `proposed_reason` | TextField (blank) | Optional reason ("Exams", "Player unavailable") |
| `status` | CharField | `pending` / `accepted` / `counter_proposed` / `rejected` / `expired` / `auto_approved` / `organizer_overridden` |
| `opponent_response` | CharField (nullable) | `accept` / `reject` / `counter` |
| `counter_proposed_time` | DateTimeField (nullable) | If opponent counter-proposes |
| `counter_reason` | TextField (blank) | Counter-proposal reason |
| `round_deadline` | DateTimeField | Hard deadline — the round must finish by this time |
| `auto_approve_eligible` | BooleanField | Whether the proposed time falls before round_deadline |
| `resolved_by` | FK → User (nullable) | Organizer who intervened (if any) |
| `resolved_at` | DateTimeField (nullable) | Resolution timestamp |
| `created_at` | DateTimeField (auto) | Request timestamp |

#### 6.8.2 Reschedule Workflow

```
Captain A proposes new time for Match #42
    → RescheduleRequest created (status: pending)
    → System checks: proposed_time < round_deadline?
        → YES: auto_approve_eligible = True
        → NO: auto_approve_eligible = False; requires organizer approval
    → Captain B notified: "Team Alpha wants to reschedule to Feb 25, 8pm"
    ↓
Captain B responds:
    → ACCEPT:
        → IF auto_approve_eligible:
            → Match.scheduled_time updated → proposed_time
            → Status → auto_approved
            → Both teams notified: "Match rescheduled to Feb 25, 8pm"
        → IF NOT auto_approve_eligible:
            → Status → accepted (pending organizer approval)
            → Organizer notified in TOC
    → COUNTER-PROPOSE:
        → Status → counter_proposed
        → Captain A reviews counter-proposal (same flow)
    → REJECT:
        → Status → rejected
        → Original time remains; both notified
    → NO RESPONSE (within 24h):
        → Status → expired
        → Original time remains
```

#### 6.8.3 Configuration (Tournament-Level)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `allow_reschedule_requests` | BooleanField | `True` | Enable/disable the feature |
| `reschedule_request_deadline_hours` | PositiveIntegerField | `24` | Minimum hours before match to request reschedule |
| `max_reschedules_per_match` | PositiveIntegerField | `2` | Maximum reschedule attempts per match |
| `auto_approve_if_within_deadline` | BooleanField | `True` | Auto-approve if both agree and time is before round deadline |
| `require_organizer_approval` | BooleanField | `False` | Always require organizer sign-off (disables auto-approve) |

#### 6.8.4 TOC Match Operations — Reschedule Queue

| Feature | Description |
|---------|-------------|
| **Reschedule Queue** | List of pending reschedule requests needing organizer action |
| **Timeline Conflict Check** | Visual indicator if proposed time conflicts with other matches in the round |
| **Approve / Reject / Override** | Organizer can approve, reject, or set a different time entirely |
| **Reschedule History** | Per-match log of all reschedule attempts |
| **Bulk Actions** | For Swiss/RR formats: approve all non-conflicting reschedules at once |

### 6.9 Match VOD & Media Archiving

**THE PROBLEM:** After a tournament completes, match replays and VOD recordings exist somewhere — on a player's local drive, a Twitch VOD, or buried in a Discord message. There is no centralized place to link replay URLs, upload highlight clips, or provide a "Watch Replay" button on the match detail page. For competitive integrity (dispute review), historical reference, and spectator engagement, match media should be tracked at the platform level.

**SOLUTION:** A **Match VOD / Replay** system that allows participants, organizers, or the system to attach replay URLs and media files to completed matches.

#### 6.9.1 New Model: `MatchMedia`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `match` | FK → Match | Associated match |
| `media_type` | CharField | `vod` / `replay_file` / `highlight` / `screenshot` / `stream_clip` |
| `url` | URLField (blank) | External URL (YouTube, Twitch, Google Drive, etc.) |
| `file` | FileField (nullable) | Direct file upload (for replay files, screenshots) |
| `title` | CharField(200, blank) | Optional title ("Game 2 — Overtime finish") |
| `description` | TextField (blank) | Optional description |
| `uploaded_by` | FK → User | Who attached this media |
| `upload_source` | CharField | `participant` / `organizer` / `system` / `broadcast` |
| `map_number` | PositiveIntegerField (nullable) | For BO3/BO5: which game (1, 2, 3...) |
| `is_public` | BooleanField (default True) | Whether visible on public match page |
| `is_featured` | BooleanField (default False) | Highlighted as the primary replay |
| `created_at` | DateTimeField (auto) | Upload timestamp |

#### 6.9.2 Media Collection Workflow

```
Match COMPLETED
    → IF tournament.require_replay_upload == True:
        → Notify winning captain: "Upload match replay within 48h"
        → Match flagged as "Replay Pending" in organizer view
    → Participants can voluntarily attach VOD/replay URLs via Match Detail page
    → Organizer can attach media from TOC Match Operations tab
    → Broadcast system can auto-attach stream clips (if Broadcast API connected)
```

#### 6.9.3 Configuration (Tournament-Level)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `require_replay_upload` | BooleanField | `False` | Mandate replay upload for completed matches |
| `replay_upload_deadline_hours` | PositiveIntegerField | `48` | Deadline for mandatory replay uploads |
| `allow_participant_uploads` | BooleanField | `True` | Let participants attach media |
| `max_media_per_match` | PositiveIntegerField | `10` | Maximum attachments per match |
| `accepted_media_extensions` | JSONField | `[".mp4", ".webm", ".dem", ".replay"]` | Allowed file extensions |

#### 6.9.4 TOC Match Operations — Media Panel

| Feature | Description |
|---------|-------------|
| **Media Gallery** | Per-match gallery showing all attached VODs, replays, and screenshots |
| **Replay Compliance** | Queue of matches where replay upload is required but missing |
| **Featured Replay** | Mark one replay as "Featured" — shown prominently on public match page |
| **Bulk Media Import** | CSV import of VOD URLs (columns: match_id, url, media_type, map_number) |
| **Media Moderation** | Review participant-uploaded media; remove inappropriate content |
| **Dispute Integration** | When a dispute is opened, auto-surface all media for that match |

#### 6.9.5 Public Match Page Integration

| Feature | Description |
|---------|-------------|
| **Watch Replay Button** | Prominent button on Match Detail page linking to featured replay |
| **Media Tab** | Tab showing all public media for the match |
| **Embed Player** | For YouTube/Twitch URLs, inline embed player |
| **Download Link** | For uploaded replay files, direct download button |
| **Map-by-Map Replays** | For BO3/BO5, show replays organized by game number |

### 6.10 Broadcast Stream & Station Dispatcher

**THE PROBLEM:** In LAN tournaments and multi-stream online events, organizers must route specific matches to physical LAN stations (Station 1–12) or streaming channels (Main Stream, B-Stream, C-Stream). Currently, there is no way to assign a match to a station or stream — casters manually check which match is "next" and hope they pick the right one. The Broadcast API (§8.6) can serve data, but it doesn't know *which* match the production team wants featured on which stream.

**SOLUTION:** A **Station & Stream Dispatcher** in the TOC Match Operations tab that lets organizers assign matches to named stations/streams. The Broadcast API then filters its data feed per station, so each OBS instance pulls only its assigned match.

#### 6.10.1 New Model: `BroadcastStation`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `tournament` | FK → Tournament | Parent tournament |
| `station_name` | CharField(100) | Display name (e.g., "Main Stage", "Station 3", "B-Stream") |
| `station_type` | CharField | `lan_station` / `stream_channel` / `hybrid` |
| `stream_url` | URLField (blank) | Live stream URL (Twitch/YouTube) for stream channels |
| `obs_scene_name` | CharField(100, blank) | OBS scene name for automation (e.g., "Match-A-Scene") |
| `is_active` | BooleanField (default True) | Whether this station is currently in use |
| `display_order` | PositiveIntegerField | Sort order in dispatcher UI |
| `max_concurrent_matches` | PositiveIntegerField (default 1) | How many matches this station can run simultaneously |
| `created_at` | DateTimeField (auto) | Creation timestamp |

#### 6.10.2 Match Model Extension

**New Fields on `Match`:**

| Field | Type | Description |
|-------|------|-------------|
| `broadcast_station` | FK → BroadcastStation (nullable) | Assigned station/stream for this match |
| `broadcast_priority` | PositiveIntegerField (default 0) | Priority ranking (higher = featured more prominently) |
| `broadcast_notes` | TextField (blank) | Production notes ("Expected upset — camera on crowd reactions") |
| `station_assigned_at` | DateTimeField (nullable) | When the match was assigned to a station |
| `station_assigned_by` | FK → User (nullable) | Who assigned it |

#### 6.10.3 Dispatcher Workflow

```
Bracket generated → Matches in SCHEDULED state
    → Organizer opens TOC Match Operations → "Stream Dispatcher" panel
    → Left panel: Unassigned matches (sorted by round, time, broadcast_priority)
    → Right panel: Station columns (one per BroadcastStation)
    → Drag match card from left → drop onto station column
        → Match.broadcast_station = selected station
        → Match.station_assigned_at = now()
    → Broadcast API: GET /broadcast/{token}/station/{station_id}/
        → Returns ONLY matches assigned to that station
        → OBS overlay pulls from station-specific feed
    → When match completes:
        → Station auto-freed (or organizer manually reassigns next match)
        → "Up Next" queue per station shown to production team
```

#### 6.10.4 TOC Stream Dispatcher UI

```
┌────────────────────────────────────────────────────────────────────────┐
│  STREAM DISPATCHER                                    Round: QF       │
│                                                                       │
│  UNASSIGNED (4)        │ MAIN STREAM     │ B-STREAM      │ STATION 3 │
│  ┌──────────────┐      │ ┌────────────┐  │ ┌───────────┐ │           │
│  │ QF-1: Alpha  │      │ │ QF-3: Neon │  │ │ QF-4: Rex │ │  (empty)  │
│  │ vs Omega     │ ───→ │ │ vs Phoenix │  │ │ vs Storm  │ │           │
│  │ ⭐ Priority:3│      │ │ 🔴 LIVE    │  │ │ ⏳ 14:30  │ │  [Drop    │
│  └──────────────┘      │ └────────────┘  │ └───────────┘ │   here]   │
│  ┌──────────────┐      │                 │               │           │
│  │ QF-2: Delta  │      │ UP NEXT:        │ UP NEXT:      │           │
│  │ vs Sigma     │      │ SF-1 (pending)  │ (none)        │           │
│  │ ⭐ Priority:1│      │                 │               │           │
│  └──────────────┘      │                 │               │           │
└────────────────────────────────────────────────────────────────────────┘
```

#### 6.10.5 Broadcast API Station Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /broadcast/{token}/stations/` | GET | List all stations with current match assignments |
| `GET /broadcast/{token}/station/{station_id}/` | GET | Data feed for a specific station (current match, scores, teams) |
| `GET /broadcast/{token}/station/{station_id}/next/` | GET | Next match queued for this station |
| `WS /broadcast/{token}/station/{station_id}/live/` | WebSocket | Real-time score updates for the station's current match |

#### 6.10.6 Station Management Features

| Feature | Description |
|---------|-------------|
| **Station CRUD** | Create/edit/delete stations from TOC Settings |
| **Auto-Assign** | "Auto-fill stations" distributes unassigned matches across stations by priority/time |
| **Conflict Detection** | Warn if two matches overlap on the same station |
| **Stream Link** | Deep link from station to the live stream URL (opens Twitch/YouTube) |
| **Station Status** | Real-time status: Idle / Match Assigned / Live / Post-Match |
| **Production Notes** | Per-match notes visible to production team ("Crowd favorite — use crowd cam") |
| **Historical Log** | Full history of station assignments for post-tournament analysis |

---

## 7. Pillar 6 — Disputes, Evidence & Resolution

### 7.1 Dispute Model (DisputeRecord — Phase 6)

**States:**
```
OPEN → UNDER_REVIEW → [RESOLVED_FOR_SUBMITTER | RESOLVED_FOR_OPPONENT | CANCELLED | ESCALATED]
```

**Reason Codes:**
- `score_mismatch` — Submitted scores don't match
- `wrong_winner` — Wrong winner declared
- `cheating_suspicion` — Suspected cheating
- `incorrect_map` — Wrong map was played
- `match_not_played` — Match was never actually played
- `other` — Freeform reason

### 7.2 Evidence System (DisputeEvidence)

**Types:** `screenshot`, `video`, `chat_log`, `other`
**Fields:** `evidence_type`, `url` (500 chars), `notes`, `uploaded_by`

### 7.3 Dispute Resolution Workflow

```
Participant opens dispute on MatchResultSubmission
    → DisputeRecord created (status: OPEN)
    → Both parties notified
    → Match state → DISPUTED
    ↓
Organizer reviews in TOC Disputes tab:
    → View submission details + all evidence
    → May request additional evidence
    → Decisions:
        a) RESOLVED_FOR_SUBMITTER → Original submission stands, scores updated per submitter
        b) RESOLVED_FOR_OPPONENT → Counter-claim accepted, scores updated per opponent
        c) CANCELLED → Dispute invalid, original result stands
        d) ESCALATED → Escalated to platform moderators/admins
    ↓
Resolution applied:
    → Match scores updated (if changed)
    → Match state → COMPLETED
    → Winner/loser updated
    → Bracket progression recalculated (if needed)
    → Resolution notes recorded
    → Both parties notified of outcome
```

### 7.4 TOC Dispute Actions

| Action | Endpoint | Method |
|--------|----------|--------|
| View disputes (filtered) | Disputes tab | GET |
| Resolve dispute | `resolve-dispute/<dispute_id>/` | POST |
| Update status | `update-dispute-status/<dispute_id>/` | POST |
| Manage disputes (dedicated view) | `disputes/manage/` | GET |

### 7.5 NEEDED Dispute Enhancements

| Feature | Description |
|---------|-------------|
| **Dispute Time Window** | Configurable dispute window (e.g., 15 min after result submission) |
| **Evidence Upload In-App** | Direct file upload for evidence (currently URL-based) |
| **Judge Assignment** | Assign specific staff member as dispute judge |
| **Dispute Templates** | Pre-built resolution templates for common scenarios |
| **Dispute Escalation Tiers** | Tier 1: Organizer → Tier 2: Platform moderator → Tier 3: Platform admin |
| **Auto-Resolution** | If opponent doesn't respond within X hours, auto-resolve in submitter's favor |
| **Penalty System** | Assign penalties (warnings, temp bans, DQ) as part of dispute resolution |
| **Dispute History** | Player/team's dispute history across all tournaments |
| **Match Replay Review** | If game API provides replay data, link it to the dispute |

### 7.6 Protest Bond — Anti-Spam Dispute System

**THE PROBLEM:** There is no cost to filing a dispute. A frustrated losing team can spam the Match Medic with frivolous disputes, freezing bracket progression and creating significant administrative overhead for organizers. Post-hoc penalties address abuse after the damage is done.

**SOLUTION:** Integrate the DeltaCoin economy into the dispute system via a **Protest Bond** — a refundable stake required to open a dispute.

**CONFIGURATION (Tournament-level):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `Tournament.dispute_bond_enabled` | BooleanField | `False` | Master toggle for protest bond system |
| `Tournament.dispute_bond_amount` | PositiveIntegerField | `50` | DeltaCoin amount required to file a dispute |
| `Tournament.dispute_bond_refund_on_valid` | BooleanField | `True` | Refund bond if dispute is ruled valid |
| `Tournament.dispute_bond_burn_on_frivolous` | BooleanField | `True` | Burn (destroy) bond if dispute is frivolous/false |

**NEW FIELDS ON DisputeRecord:**

| Field | Type | Description |
|-------|------|-------------|
| `bond_transaction_id` | FK → DeltaCrownTransaction (nullable) | The debit transaction for the bond |
| `bond_amount` | PositiveIntegerField (default 0) | Amount staked |
| `bond_status` | CharField | `held` / `refunded` / `burned` / `not_applicable` |
| `bond_resolution_transaction_id` | FK → DeltaCrownTransaction (nullable) | The refund or burn transaction |

**WORKFLOW:**
```
Team wants to file dispute on match result
    ↓
IF Tournament.dispute_bond_enabled:
    → Check team captain's DeltaCoin wallet balance
    → IF balance < dispute_bond_amount:
        → BLOCK: "Insufficient DeltaCoin to file protest (requires {amount} DC)"
        → Dispute cannot be opened
    → IF balance >= dispute_bond_amount:
        → Debit dispute_bond_amount from wallet (reason: `dispute_bond_hold`)
        → Create DisputeRecord with bond_status = 'held'
        → Proceed with normal dispute workflow
    ↓
Organizer resolves dispute:
    → IF resolved in submitter's favor (RESOLVED_FOR_SUBMITTER):
        → Refund bond: Credit dispute_bond_amount back to wallet (reason: `dispute_bond_refund`)
        → bond_status → 'refunded'
    → IF resolved against submitter (RESOLVED_FOR_OPPONENT / CANCELLED as frivolous):
        → Burn bond: No refund. DeltaCoin destroyed (reason: `dispute_bond_burned`)
        → bond_status → 'burned'
    → IF escalated:
        → Bond remains held until final resolution
    ↓
IF NOT Tournament.dispute_bond_enabled:
    → Normal dispute flow (no bond required)
```

**ECONOMY INTEGRATION:**
- Uses existing `DeltaCrownWallet.award()` with idempotency key: `dispute_bond_{dispute_id}`
- Bond debit reason: `dispute_bond_hold`
- Bond refund reason: `dispute_bond_refund`
- Bond burn reason: `dispute_bond_burned`
- All transactions linked via `bond_transaction_id` and `bond_resolution_transaction_id`

**ANTI-GAMING MEASURES:**

| Scenario | Handling |
|----------|----------|
| Team files dispute, then cancels immediately | Bond still burns if organizer marks as frivolous; refund if cancelled before review |
| Team has 0 DC and disputes are bond-free | Tournaments without bonds still allow free disputes (organizer choice) |
| Team borrows DC from another player to post bond | Allowed — the economy is player-driven |
| Multiple disputes on same match | Each requires its own bond |

---

## 8. Pillar 7 — Tournament Configuration & Communications

### 8.1 Tournament Settings (Editable in TOC Settings Tab)

**Core Settings:**
| Category | Fields |
|----------|--------|
| **Basic Info** | name, description, banner_image, thumbnail_image, promo_video_url |
| **Game & Format** | game, format, participation_type, platform, mode |
| **Capacity** | max_participants, min_participants |
| **Schedule** | registration_start, registration_end, tournament_start, tournament_end |
| **Entry Fee** | has_entry_fee, entry_fee_amount, entry_fee_currency, entry_fee_deltacoin, payment_deadline_hours |
| **Payment Methods** | payment_methods (ArrayField), per-method config via TournamentPaymentMethod |
| **Prize Pool** | prize_pool, prize_currency, prize_deltacoin, prize_distribution |
| **Check-In** | enable_check_in, check_in_minutes_before, check_in_closes_minutes_before |
| **Features** | enable_dynamic_seeding, enable_live_updates, enable_certificates, enable_challenges, enable_fan_voting |
| **Venue** (LAN/Hybrid) | venue_name, venue_address, venue_city, venue_map_url |
| **Rules** | rules_text, rules_pdf, terms_and_conditions, terms_pdf, require_terms_acceptance |
| **Social/Media** | stream_youtube_url, stream_twitch_url, social_twitter/instagram/youtube/website/discord, contact_email |
| **Refund** | refund_policy, refund_policy_text, enable_fee_waiver, fee_waiver_top_n_teams |
| **Advanced** | allow_display_name_override, max_guest_teams, config (JSONB), registration_form_overrides (JSONB) |
| **SEO** | meta_description, meta_keywords |

**Custom Fields (CustomField model):**
Organizer can add arbitrary custom fields to the tournament:
- Types: text, number, media, toggle, date, url, dropdown
- Each has: `field_name`, `field_key` (slug), `field_config` (JSONB), `field_value` (JSONB), `order`, `is_required`, `help_text`

### 8.2 Custom Registration Questions

**RegistrationQuestion model:**
- Per-tournament or per-game scope
- Types: text, select, multi_select, boolean, number, file, date
- Scope: team-level or player-level
- Conditional visibility: `show_if` JSONB (show this question only if another answer matches)
- `is_built_in` flag for system-generated questions (game ID, etc.)

### 8.3 Announcement System

**EXISTS:**
- `TournamentAnnouncement` model: `title`, `message`, `created_by`, `is_pinned`, `is_important`
- `LobbyAnnouncement` model: same but scoped to lobby, with `announcement_type` (info/warning/urgent/success), `display_until`, `is_visible`

**TOC Actions:**
- Create announcement (Announcements tab)
- Pin/unpin announcement
- Mark as important

**NEEDED:**
| Feature | Description |
|---------|-------------|
| **Push Notifications** | Broadcast announcement to all registrants via push/email/in-app |
| **Targeted Announcements** | Send to specific groups (checked-in only, waitlisted only, specific group/bracket section) |
| **Scheduled Announcements** | Schedule announcement for future datetime |
| **Discord Webhook Integration** | Auto-post announcements to linked Discord server |
| **SMS Blast** (optional) | For LAN events, SMS announcements |
| **Read Receipts** | Track which participants have seen the announcement |
| **Announcement Templates** | Pre-built templates (check-in reminder, match starting, schedule change, etc.) |

### 8.4 Discord & External Comms Integration

**EXISTS:**
- `Tournament.social_discord` — Discord invite URL
- `TournamentLobby.discord_server_url` — Discord server for lobby

**NEEDED:**
| Feature | Description |
|---------|-------------|
| **Discord Bot Integration** | Link tournament to Discord bot for auto-announcements |
| **Auto Voice Channels** | Create per-match voice channels in Discord |
| **Match Room Discord Threads** | Auto-create Discord thread for each match |
| **Tournament Role Assignment** | Auto-assign Discord roles to participants, staff |
| **Stream Go-Live Notification** | Auto-post when tournament stream goes live |

### 8.5 Sponsor Management

**EXISTS (TournamentSponsor model):**
- `name`, `tier` (title/gold/silver/bronze/partner), `logo`, `website_url`, `banner_image`, `description`, `display_order`, `is_active`

**TOC Actions (in Settings tab):**
- Add/edit/remove sponsors
- Set sponsor tier and display order

**NEEDED:**
- Sponsor analytics (impressions, clicks on sponsor links)
- Sponsor visibility rules (which pages show which sponsors)
- Sponsor contract management (start/end dates, obligations)

### 8.6 Broadcast API — OBS/vMix Data Feed

**THE PROBLEM:** Tournament organizers who stream on Twitch/YouTube need to display live brackets, scores, and map veto results on their broadcast overlays. Currently, they must manually type scores into OBS text sources — error-prone, laggy, and unprofessional.

**SOLUTION:** Provide a secure, read-only JSON data feed URL per tournament that broadcast tools (OBS, vMix, Singular.live, Livestream Studio) can consume directly.

#### 8.6.1 Broadcast Feed Configuration

**NEW MODEL: `BroadcastFeed`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `tournament` | OneToOneField → Tournament | One feed per tournament |
| `feed_token` | CharField(64) | Unique secret token for feed URL authentication |
| `is_enabled` | BooleanField (default False) | Master toggle |
| `created_by` | FK → User | Organizer who created the feed |
| `created_at` | DateTimeField (auto) | Creation timestamp |
| `last_accessed_at` | DateTimeField (nullable) | Last time feed was polled |
| `access_count` | PositiveIntegerField (default 0) | Total poll count |
| `allowed_origins` | ArrayField(CharField) (blank) | CORS whitelist for browser-based overlays |
| `refresh_interval_seconds` | PositiveIntegerField (default 15) | Recommended polling interval |

**FEED URL FORMAT:**
```
GET /api/tournaments/{slug}/broadcast/{feed_token}/
```
- No authentication required (token IS the auth) — designed for OBS browser sources
- Rate limited: 1 request per `refresh_interval_seconds`
- CORS headers based on `allowed_origins`
- Cache-Control: `max-age={refresh_interval_seconds}`

#### 8.6.2 Broadcast Feed Endpoints

| Endpoint | Response | Use Case |
|----------|----------|----------|
| `/broadcast/{token}/` | Full tournament state (meta + bracket + active matches) | Master overlay |
| `/broadcast/{token}/bracket/` | Complete bracket tree with scores and progression | Bracket overlay |
| `/broadcast/{token}/matches/live/` | Currently live matches with real-time scores | Live score ticker |
| `/broadcast/{token}/matches/{match_id}/` | Single match detail (teams, scores, map, veto) | Match spotlight overlay |
| `/broadcast/{token}/standings/` | Current standings (groups or bracket) | Standings overlay |
| `/broadcast/{token}/schedule/` | Upcoming matches with times | Schedule overlay |
| `/broadcast/{token}/veto/{match_id}/` | Map veto results for a specific match | Map veto overlay |

#### 8.6.3 Response Schema (Master Endpoint)

```json
{
  "tournament": {
    "name": "DeltaCrown Championship S1",
    "status": "live",
    "format": "double_elimination",
    "game": "CS2",
    "current_round": 3,
    "total_rounds": 7
  },
  "live_matches": [
    {
      "match_id": "abc-123",
      "round": 3,
      "team_a": { "name": "Team Alpha", "seed": 1, "logo_url": "..." },
      "team_b": { "name": "Team Beta", "seed": 8, "logo_url": "..." },
      "score": { "team_a": 13, "team_b": 10 },
      "status": "live",
      "map": "Mirage",
      "started_at": "2026-02-23T14:30:00Z"
    }
  ],
  "recent_results": ["..."],
  "upcoming_matches": ["..."],
  "bracket_url": "/broadcast/{token}/bracket/",
  "updated_at": "2026-02-23T15:00:05Z"
}
```

#### 8.6.4 TOC Integration

| Location | Feature |
|----------|---------||
| **Settings Tab** | "Broadcast Feed" panel: Enable/disable, generate token, copy feed URL, set CORS origins |
| **Overview Tab** | Feed status indicator: active/inactive, last polled, total polls |
| **Match Detail** | "Copy Broadcast URL for this match" quick-action |

**SECURITY:**
- Feed tokens are 64-character random strings (same entropy as invite tokens)
- Organizer can regenerate token at any time (invalidates old URL)
- Feed can be disabled without deleting (toggle `is_enabled`)
- No write operations exposed — strictly read-only
- Rate limiting prevents abuse

### 8.7 Game Logic & Veto Builder — Per-Tournament Match Rules Engine

**THE PROBLEM:** Different esports titles have radically different pre-match rituals. Valorant requires map ban/pick sequences. CS2 has map vetoes + side selection. eFootball needs weather/time/stadium configuration. PUBG Mobile has no vetoes but needs drop zone rules. The TOC document mentions that a "Map/Veto System" is needed (Gap #12), but does not specify **how the organizer configures** these game-specific rules.

**SOLUTION:** A "Game Logic & Veto Builder" tool in the TOC Settings tab that lets organizers define the complete pre-match rule set per tournament, including map pools, veto sequences, side selection rules, and game-specific configuration.

#### 8.7.1 Configuration Model

**NEW MODEL: `GameMatchConfig`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `tournament` | OneToOneField → Tournament | One config per tournament |
| `game` | FK → Game | Game reference (auto-set from tournament) |
| `map_pool` | JSONField | Array of enabled maps: `[{"name": "Ascent", "image_url": "...", "enabled": true}]` |
| `veto_sequence` | JSONField | Ordered sequence: `[{"action": "ban", "actor": "higher_seed"}, {"action": "pick", "actor": "lower_seed"}, ...]` |
| `veto_enabled` | BooleanField (default True) | Master toggle for veto system |
| `side_selection_enabled` | BooleanField (default True) | Enable CT/T or Attack/Defend side selection |
| `side_selection_rule` | CharField | `winner_picks` / `loser_picks` / `higher_seed_picks` / `alternating` / `none` |
| `custom_rules` | JSONField | Game-specific rules (freeform): `{"weather": "clear", "time": "night", "stadium": "any"}` |
| `toss_method` | CharField | `coin_flip` / `higher_seed` / `organizer_assigns` |
| `bo_format` | CharField | `bo1` / `bo3` / `bo5` / `bo7` |
| `created_by` | FK → User | Organizer who configured |
| `updated_at` | DateTimeField (auto) | Last modified |

**NEW MODEL: `MapPoolEntry`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `game_match_config` | FK → GameMatchConfig | Parent config |
| `map_name` | CharField(100) | Map display name (e.g., "Ascent", "Mirage") |
| `map_code` | SlugField | Normalized identifier (e.g., `ascent`, `mirage`) |
| `map_image` | ImageField (nullable) | Custom map image uploaded by organizer |
| `default_image_url` | URLField (blank) | Platform-provided default image |
| `is_active` | BooleanField (default True) | Whether this map is in the active pool |
| `display_order` | PositiveIntegerField | Sort order in veto screen |

#### 8.7.2 TOC Veto Builder Interface

**Location:** TOC Settings Tab → "Match Rules" panel.

**STEP 1 — Map Pool Configuration:**
```
┌─────────────────────────────────────────────────────────┐
│  MAP POOL — Valorant                                    │
│                                                         │
│  ☑ Ascent    [🖼️ Upload Image]  [Default ▾]             │
│  ☑ Bind      [🖼️ Upload Image]  [Default ▾]             │
│  ☑ Haven     [🖼️ Upload Image]  [Default ▾]             │
│  ☐ Icebox    (disabled for this tournament)              │
│  ☑ Lotus     [🖼️ Upload Image]  [Default ▾]             │
│  ☑ Split     [🖼️ Upload Image]  [Default ▾]             │
│  ☑ Sunset    [🖼️ Upload Image]  [Default ▾]             │
│  ☐ Fracture  (disabled for this tournament)              │
│                                                         │
│  [+ Add Custom Map]                                     │
└─────────────────────────────────────────────────────────┘
```

**STEP 2 — Veto Sequence Builder:**
```
┌─────────────────────────────────────────────────────────┐
│  VETO SEQUENCE — BO3                                    │
│                                                         │
│  Step 1: [Ban ▾]   by [Higher Seed ▾]                   │
│  Step 2: [Ban ▾]   by [Lower Seed ▾]                    │
│  Step 3: [Pick ▾]  by [Higher Seed ▾]                   │
│  Step 4: [Pick ▾]  by [Lower Seed ▾]                    │
│  Step 5: [Ban ▾]   by [Higher Seed ▾]                   │
│  Step 6: [Ban ▾]   by [Lower Seed ▾]                    │
│  Step 7: [Decider] (remaining map)                      │
│                                                         │
│  [+ Add Step]  [Reset to Default]                       │
│                                                         │
│  Preview: Ban-Ban-Pick-Pick-Ban-Ban-Decider             │
└─────────────────────────────────────────────────────────┘
```

**STEP 3 — Game-Specific Custom Rules (varies by game):**

| Game | Custom Rule Options |
|------|--------------------|
| **Valorant** | Map pool, agent ban (optional), overtime rules |
| **CS2** | Map pool, overtime format (MR3/MR6), knife round for side |
| **eFootball** | Weather (clear/rain/snow), time (day/night), stadium, match length (6/8/10 min) |
| **PUBG Mobile** | Map (Erangel/Miramar/etc.), mode (TPP/FPP), circle settings, loot level |
| **Free Fire** | Map, mode, custom room settings |
| **FIFA** | Half length, difficulty, formation restrictions |

Organizers configure these as key-value pairs stored in `custom_rules` JSONField. The system provides **game-specific templates** with pre-built rule sets.

#### 8.7.3 Match-Level Veto Execution

When a match enters the `READY` state, the veto process begins:

```
Match → READY state
    → System loads GameMatchConfig for this tournament
    → IF veto_enabled:
        → Create MatchVetoSession (linked to Match)
        → Notify both captains: "Veto phase starting"
        → Display veto screen to captains (public match lobby page)
        → Captains take turns per veto_sequence:
            Step 1: Higher seed bans a map → push WebSocket event
            Step 2: Lower seed bans a map → push WebSocket event
            ... (continues per sequence)
        → Veto complete → maps decided → stored on Match.lobby_info
    → IF NOT veto_enabled:
        → Organizer pre-assigns maps OR random selection
    → Match proceeds to LIVE
```

**NEW MODEL: `MatchVetoSession`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `match` | OneToOneField → Match | Parent match |
| `config` | FK → GameMatchConfig | Config used |
| `status` | CharField | `pending` / `in_progress` / `completed` / `timed_out` |
| `veto_log` | JSONField | Ordered log: `[{"step": 1, "action": "ban", "actor": "Team A", "map": "Icebox", "timestamp": "..."}]` |
| `decided_maps` | JSONField | Final map list: `["Ascent", "Bind", "Haven"]` |
| `started_at` | DateTimeField (nullable) | When veto phase started |
| `completed_at` | DateTimeField (nullable) | When veto phase completed |
| `timeout_seconds` | PositiveIntegerField (default 30) | Time limit per veto step |

**VETO TIMEOUT:** If a captain doesn't act within `timeout_seconds`, the system auto-selects randomly from remaining maps. Prevents stalling.

**BROADCAST INTEGRATION:** Veto sessions push events to the Broadcast Feed (`/broadcast/{token}/veto/{match_id}/`) so OBS overlays can animate the ban/pick sequence live on stream.

### 8.8 Embeddable Iframe Widget Generator

**THE PROBLEM:** Tournament organizers, gaming communities, and partner websites want to display live brackets, standings, and schedules on their own sites. Currently, the only option is to link to the DeltaCrown tournament page. There is no embeddable widget — no `<iframe>` code, no JavaScript snippet, no oEmbed support. This limits platform reach and forces external sites to choose between linking out (losing visitors) or manually copying data (stale).

**SOLUTION:** An **Iframe Widget Generator** in the TOC that produces embeddable `<iframe>` codes for read-only tournament data views. These widgets are lightweight, auto-updating, and styled to fit any external site.

#### 8.8.1 Widget Types

| Widget | Embed Content | Dimensions (default) |
|--------|---------------|---------------------|
| **Bracket** | Live single/double elimination bracket | 800×600 |
| **Group Standings** | Group stage tables with W/L/D/Points | 600×400 |
| **Match Schedule** | Upcoming matches with times + teams | 400×800 |
| **Live Score** | Currently live match with real-time score | 400×120 |
| **Leaderboard** | Top N players/teams from tournament standings | 400×600 |
| **Registration Counter** | "42 / 64 slots filled — Register Now!" with CTA | 300×80 |
| **Recent Results** | Last 5 completed matches with scores | 400×300 |

#### 8.8.2 Widget Configuration (TOC Settings Tab)

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_embeds` | BooleanField | `True` | Master toggle for widget generation |
| `allowed_widget_types` | JSONField | `["bracket", "standings", "schedule"]` | Which widgets to expose |
| `widget_theme` | CharField | `auto` | `auto` / `light` / `dark` — controls widget appearance |
| `custom_accent_color` | CharField (nullable) | `null` | Hex color for branding (e.g., `#FF5722`) |
| `show_powered_by` | BooleanField | `True` | Show "Powered by DeltaCrown" footer |
| `allowed_domains` | JSONField (blank) | `[]` | Restrict embedding to specific domains (empty = allow all) |
| `widget_refresh_interval` | PositiveIntegerField | `30` | Widget data refresh interval in seconds |

#### 8.8.3 Embed Code Generation

**Output for organizer (copy-paste from TOC):**
```html
<!-- DeltaCrown Tournament Widget — Bracket -->
<iframe
  src="https://deltacrown.com/embed/{tournament_slug}/bracket/?theme=dark&accent=FF5722"
  width="800"
  height="600"
  frameborder="0"
  allow="autoplay"
  loading="lazy"
  title="Tournament Bracket — {tournament_title}"
></iframe>
```

**URL Pattern:** `/embed/{tournament_slug}/{widget_type}/`

**Query Parameters:**

| Param | Values | Description |
|-------|--------|-------------|
| `theme` | `auto` / `light` / `dark` | Override widget theme |
| `accent` | Hex color (no #) | Override accent color |
| `lang` | `en` / `bn` | Language override |
| `group` | Group name | For `standings` widget: show specific group only |
| `round` | Round number | For `schedule` widget: show specific round only |
| `limit` | Integer | For `leaderboard` / `results`: max items shown |
| `refresh` | Integer (seconds) | Override refresh interval |

#### 8.8.4 Widget Backend

| Component | Description |
|-----------|-------------|
| **Endpoint** | `GET /embed/{slug}/{widget}/` — returns lightweight HTML page with minimal CSS + JS |
| **Data Source** | Reads from same Redis cache as Broadcast API; no extra DB queries |
| **Security** | Domain restriction via `X-Frame-Options` / CSP `frame-ancestors` based on `allowed_domains` |
| **Rate Limiting** | Per-widget rate limit (60 req/min per widget per IP) |
| **Caching** | Widget HTML cached for `widget_refresh_interval` seconds |
| **Responsive** | Widget auto-scales to iframe dimensions using CSS container queries |
| **No Auth Required** | Widgets are public read-only views; no login needed |

#### 8.8.5 TOC Widget Management Panel

| Feature | Description |
|---------|-------------|
| **Widget Previewer** | Live preview of each widget type as it would appear embedded |
| **Embed Code Copier** | One-click copy of `<iframe>` code for each widget type |
| **Analytics** | View count per widget, top referring domains, peak usage times |
| **Domain Whitelist** | Manage allowed embedding domains |
| **Custom CSS Override** | Advanced: inject custom CSS into widget for brand matching |
| **Widget Status** | Show which widgets are active, paused, or disabled |

### 8.9 Rulebook Versioning & Forced Re-Consent

**THE PROBLEM:** Tournament rules are stored in a freeform `TextField` (`Tournament.rules_text`) and a file upload (`Tournament.rules_pdf_url`). When the organizer edits the rules mid-tournament (e.g., adding a map pool change, adjusting overtime rules), there is no version history, no diff view, and — critically — **no mechanism to notify active participants that the rules changed and require them to re-acknowledge**. A player could be penalized under a rule that was silently added after they registered.

**SOLUTION:** A **Rulebook Versioning** system that creates an immutable snapshot every time rules are edited, and a **Forced Re-Consent** mechanism that pushes a mandatory acknowledgment modal to all active participants when a material rule change occurs.

#### 8.9.1 New Model: `RulebookVersion`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `tournament` | FK → Tournament | Parent tournament |
| `version_number` | PositiveIntegerField | Auto-incrementing per tournament (1, 2, 3...) |
| `rules_text` | TextField | Snapshot of rules text at this version |
| `rules_pdf` | FileField (nullable) | Snapshot of rules PDF at this version |
| `change_summary` | TextField (blank) | Organizer's description of what changed |
| `change_type` | CharField | `initial` / `minor` (typo, clarification) / `material` (rule addition/removal/change) |
| `published_by` | FK → User | Organizer who published this version |
| `published_at` | DateTimeField (auto) | Version creation timestamp |
| `requires_reconsent` | BooleanField | Whether active participants must re-acknowledge |
| `reconsent_deadline` | DateTimeField (nullable) | Deadline by which participants must re-consent |
| `previous_version` | FK → self (nullable) | Link to previous version (for diff) |

#### 8.9.2 New Model: `RulebookConsent`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `rulebook_version` | FK → RulebookVersion | Which version was acknowledged |
| `user` | FK → User | Participant who consented |
| `registration` | FK → Registration | Their registration in this tournament |
| `consented_at` | DateTimeField (auto) | Consent timestamp |
| `ip_address` | GenericIPAddressField (nullable) | IP at time of consent (legal compliance) |
| `user_agent` | TextField (blank) | Browser UA string (legal compliance) |

#### 8.9.3 Rulebook Edit Workflow

```
Organizer edits rules in TOC Settings Tab
    → System detects change (diff against current version)
    → Organizer prompted:
        → Change type: [Minor (no re-consent)] [Material (require re-consent)]
        → Change summary: "Added overtime rules for BO5 finals"
        → Re-consent deadline: [48 hours from now ▾]
    → RulebookVersion created (version_number = previous + 1)
    → IF change_type == 'material' AND requires_reconsent:
        → All active registrations queried
        → Players without consent for this version are flagged
        → Push notification: "Tournament rules have been updated. Review and accept to continue."
        → Modal shown on tournament pages: "Rules updated — you must review and accept"
        → IF player does not consent by reconsent_deadline:
            → Registration.status → SUSPENDED (cannot play until consent given)
            → Organizer notified in TOC: "X players haven't accepted updated rules"
        → IF player consents:
            → RulebookConsent created
            → Registration remains CONFIRMED
    → IF change_type == 'minor':
        → RulebookVersion created (for audit trail) but no re-consent required
        → Participants can view version history on tournament page
```

#### 8.9.4 TOC Rules Management Panel

| Feature | Description |
|---------|-------------|
| **Version History** | Chronological list of all rulebook versions with timestamps and change summaries |
| **Diff Viewer** | Side-by-side diff between any two versions (highlighted additions/removals) |
| **Consent Dashboard** | For material changes: list of participants, consent status, and deadline countdown |
| **Bulk Reminder** | Send reminder notification to all players who haven't re-consented |
| **Grace Period Extension** | Extend re-consent deadline if needed |
| **Consent Export** | Export consent records as CSV (legal compliance) |
| **Suspend Non-Compliant** | One-click suspend all registrations that missed re-consent deadline |

#### 8.9.5 Participant-Facing Views

| View | Description |
|------|-------------|
| **Rules Page** | Always shows latest version with "Last updated: {date}" |
| **Version Selector** | Dropdown to view previous versions |
| **Change Log** | Summarized list of all rule changes with dates |
| **Re-Consent Modal** | Blocking modal: "Rules updated on {date}. Summary: {change_summary}. [Read Full Rules] [I Accept]" |
| **Registration Wizard** | Step 4 (rules acceptance) always references latest RulebookVersion |

### 8.10 Battle Royale (BR) Scoring Matrix Builder

**THE PROBLEM:** Battle Royale games (PUBG Mobile, Free Fire, Fortnite, Apex Legends) use a fundamentally different scoring model from versus matchups. A team's total score = placement points + kill points, where the point values for each placement position and per-kill vary by tournament. The `GameMatchConfig` (§8.7) handles map pools and veto sequences, but has no mechanism for defining a **placement-to-points scoring table**. Organizers currently have no way to configure "1st Place = 15 pts, 2nd = 12 pts, ... , kill = 1 pt" — and the result engine has no way to auto-calculate total scores from raw kills/placement data.

**SOLUTION:** A **BR Scoring Matrix** extension to `GameMatchConfig` that stores a configurable placement→points mapping and a kill multiplier. The Smart Result Engine (score verification flow §6.7) reads this matrix to auto-calculate team totals from manually inputted kills and placement.

#### 8.10.1 New Model: `BRScoringMatrix`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `game_match_config` | OneToOneField → GameMatchConfig | Parent config (one matrix per tournament config) |
| `name` | CharField(200) | Matrix name (e.g., "PUBG Mobile Standard", "Free Fire Custom") |
| `placement_points` | JSONField | Ordered dict: `{"1": 15, "2": 12, "3": 10, "4": 8, "5": 6, "6": 4, "7": 2, "8": 1, ...}` |
| `kill_points` | DecimalField | Points per kill (e.g., `1.0`, `0.5`) |
| `assist_points` | DecimalField (default 0) | Points per assist (optional) |
| `damage_points_per_100` | DecimalField (default 0) | Points per 100 damage dealt (optional, for Apex) |
| `max_placement_slots` | PositiveIntegerField (default 20) | Number of placement positions with defined points |
| `default_placement_points` | DecimalField (default 0) | Points for placements beyond `max_placement_slots` |
| `is_per_match` | BooleanField (default True) | Points calculated per match (multi-match BR adds up across games) |
| `total_matches` | PositiveIntegerField (default 6) | Number of BR matches in this tournament stage |
| `drop_worst_n` | PositiveIntegerField (default 0) | Drop N worst match scores from total (e.g., drop 1 of 6) |
| `created_by` | FK → User | Organizer who configured |
| `updated_at` | DateTimeField (auto) | Last modified |

#### 8.10.2 Built-In Scoring Presets

| Preset | 1st | 2nd | 3rd | 4th | 5th | 6th–8th | 9th–12th | Kill |
|--------|-----|-----|-----|-----|-----|---------|----------|------|
| **PUBG Mobile (PMPL Standard)** | 15 | 12 | 10 | 8 | 6 | 4 | 2 | 1 |
| **Free Fire (FFWS Standard)** | 12 | 9 | 7 | 5 | 4 | 3 | 1 | 1 |
| **Fortnite (FNCS Standard)** | 25 | 20 | 16 | 14 | 11 | 8 | 5 | 1 |
| **Apex Legends (ALGS Standard)** | 12 | 9 | 7 | 5 | 4 | 3→2 | 1 | 1 |
| **Custom** | Organizer-defined | — | — | — | — | — | — | — |

#### 8.10.3 Score Calculation Engine

```python
def calculate_br_match_score(matrix: BRScoringMatrix, placement: int, kills: int,
                               assists: int = 0, damage: int = 0) -> dict:
    """
    Calculate a team's total score for one BR match using the scoring matrix.
    """
    placement_str = str(placement)
    placement_pts = matrix.placement_points.get(
        placement_str,
        matrix.default_placement_points
    )
    kill_pts = kills * matrix.kill_points
    assist_pts = assists * matrix.assist_points
    damage_pts = (damage / 100) * matrix.damage_points_per_100

    total = placement_pts + kill_pts + assist_pts + damage_pts

    return {
        "placement": placement,
        "placement_points": placement_pts,
        "kills": kills,
        "kill_points": kill_pts,
        "assist_points": assist_pts,
        "damage_points": damage_pts,
        "total_points": total,
    }


def calculate_br_tournament_total(matrix: BRScoringMatrix,
                                    match_results: list[dict]) -> dict:
    """
    Calculate aggregate score across all BR matches, with optional worst-drop.
    """
    match_scores = sorted(
        [calculate_br_match_score(matrix, r['placement'], r['kills'],
                                   r.get('assists', 0), r.get('damage', 0))
         for r in match_results],
        key=lambda x: x['total_points']
    )

    if matrix.drop_worst_n > 0 and len(match_scores) > matrix.drop_worst_n:
        dropped = match_scores[:matrix.drop_worst_n]
        counted = match_scores[matrix.drop_worst_n:]
    else:
        dropped = []
        counted = match_scores

    return {
        "match_scores": [s for s in sorted(match_scores, key=lambda x: -x['total_points'])],
        "dropped_matches": dropped,
        "counted_matches": counted,
        "total_placement_points": sum(s['placement_points'] for s in counted),
        "total_kill_points": sum(s['kill_points'] for s in counted),
        "grand_total": sum(s['total_points'] for s in counted),
        "matches_played": len(match_scores),
        "matches_counted": len(counted),
    }
```

#### 8.10.4 New Model: `BRMatchResult`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `match` | FK → Match | The BR match (one per game in the multi-game series) |
| `registration` | FK → Registration | Team participating |
| `game_number` | PositiveIntegerField | Which game in the series (1, 2, 3, ...) |
| `placement` | PositiveIntegerField | Finish position (1st, 2nd, 3rd...) |
| `kills` | PositiveIntegerField (default 0) | Team's total kills |
| `assists` | PositiveIntegerField (default 0) | Team's total assists |
| `damage_dealt` | PositiveIntegerField (default 0) | Total damage dealt |
| `placement_points` | DecimalField | Auto-calculated from matrix |
| `kill_points` | DecimalField | Auto-calculated from matrix |
| `total_points` | DecimalField | Auto-calculated grand total |
| `is_dropped` | BooleanField (default False) | Whether this game was dropped from total |
| `submitted_by` | FK → User | Who entered this result |
| `verified` | BooleanField (default False) | Organizer verified |
| `created_at` | DateTimeField (auto) | Submission timestamp |

#### 8.10.5 TOC BR Scoring Configuration UI

```
┌─────────────────────────────────────────────────────────┐
│  BR SCORING MATRIX — PUBG Mobile                        │
│                                                         │
│  Preset: [PMPL Standard ▾]  [Custom ▾]                  │
│                                                         │
│  Placement Points:                                      │
│  1st: [15]  2nd: [12]  3rd: [10]  4th: [8]              │
│  5th: [ 6]  6th: [ 4]  7th: [ 2]  8th: [ 1]            │
│  9th+: [ 0] (default for unlisted)                      │
│                                                         │
│  Kill Points: [1.0] per kill                            │
│  Assist Points: [0.0] per assist                        │
│  Damage Points: [0.0] per 100 damage                    │
│                                                         │
│  Matches in Stage: [6]  Drop Worst: [1]                 │
│                                                         │
│  [Preview Scoring Table]  [Save Matrix]                 │
└─────────────────────────────────────────────────────────┘
```

#### 8.10.6 Smart Result Engine Integration

When an organizer enters BR match results via the Score Verification UI (§6.7):

1. **Input:** Organizer enters placement + kills for each team per game
2. **Auto-Calculate:** System reads `BRScoringMatrix` for the tournament and computes `placement_points`, `kill_points`, `total_points` per team per game
3. **Running Total:** Dashboard shows cumulative standings across all games with live rank updates
4. **Drop Worst:** After all games played, worst N scores auto-marked as `is_dropped`
5. **Final Standings:** `GroupStanding` / `TournamentResult` updated with final totals
6. **Tiebreaker Integration:** BR tiebreaker criteria (`placement_points`, `total_kills`, `avg_placement` from §5.12) use these calculated values

#### 8.10.7 BR Results Dashboard (TOC Match Ops)

| Feature | Description |
|---------|-------------|
| **Live Leaderboard** | Real-time standings as games are played — total points, kills, placement per team |
| **Per-Game Breakdown** | Expandable rows showing each game's result per team |
| **Auto-Rank** | Standings auto-sort by total points using BR tiebreaker hierarchy |
| **Drop Indicator** | Dropped games shown with strikethrough styling |
| **Bulk Entry** | Paste scores from spreadsheet (tab-separated: Team, Placement, Kills) |
| **CSV Import** | Import results via CSV for each game |
| **Point Audit** | Click any team's total to see full calculation breakdown |
| **Broadcast Feed** | BR standings pushed to Broadcast API (§8.6) for live OBS overlays |

### 8.11 Server Region Vetoes

**THE PROBLEM:** In cross-regional tournaments (e.g., South-East Asia Open, Global Invitational), server location is a critical competitive variable. A team based in Dhaka has 20ms ping to a Singapore server but 180ms to a Frankfurt server — a difference that decides gunfights. Currently, matches default to a single hard-coded server region set per tournament, or worse, to no specification at all. Captains have no formal mechanism to negotiate or veto unfavorable server regions, leading to disputes, ghost-dropped matches, and rehosts.

**SOLUTION:** Extend the **Veto Builder** (§8.7) and `GameMatchConfig` to support **Server Region** as a vetoing dimension alongside Maps and Sides. Organizers define a server pool; captains ban/pick servers using the same alternating veto sequence. The final selected server is locked into the match record.

#### 8.11.1 New Model: `ServerRegion`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `game` | FK → Game | Game this server applies to (different games have different server lists) |
| `name` | CharField(100) | Display name (e.g., "Singapore", "Mumbai", "Frankfurt") |
| `code` | CharField(20, unique per game) | Short code (e.g., `sg`, `in-mum`, `eu-fra`) |
| `provider` | CharField(100, blank) | Hosting provider info (e.g., "AWS ap-southeast-1") |
| `latitude` | FloatField (nullable) | For distance-based auto-suggestions |
| `longitude` | FloatField (nullable) | For distance-based auto-suggestions |
| `is_active` | BooleanField (default True) | Whether region is currently available |
| `order` | PositiveIntegerField | Display ordering |

#### 8.11.2 Server Pool on `GameMatchConfig`

| Field | Type | Description |
|-------|------|-------------|
| `server_regions` | M2M → ServerRegion | Available server regions for this game configuration |
| `server_veto_enabled` | BooleanField (default False) | Whether server is included in veto sequence |
| `server_veto_format` | CharField | `ban_ban_pick` / `ban_pick` / `organizer_pick` / `auto_nearest` |
| `default_server_region` | FK → ServerRegion (nullable) | Fallback if veto not used or both teams agree |

#### 8.11.3 Veto Sequence Integration

The existing `MatchVetoSession` (§8.7) gains a new `veto_dimension`:

```
Current veto_type values: 'map_ban' / 'map_pick' / 'side_pick'
New values:               'server_ban' / 'server_pick'

Example 3-phase veto sequence for international BO3:
  Phase 1 — Server Veto (from pool of 5 regions):
    Team A bans 1 server → Team B bans 1 server → Team A picks 1 server
    → Picked server locked for all games in this match
  Phase 2 — Map Veto (from pool of 7 maps):
    Team A ban → Team B ban → Team A ban → Team B ban → Team A pick → Team B pick → Last map auto
  Phase 3 — Side Pick:
    Team B picks side on Map 1 (since Team A picked first map)
```

#### 8.11.4 `MatchServerSelection` Record

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `match` | OneToOneField → Match | Match this selection applies to |
| `selected_region` | FK → ServerRegion | Final selected server region |
| `selection_method` | CharField | `veto` / `organizer_assigned` / `auto_nearest` / `mutual_agreement` |
| `veto_session` | FK → MatchVetoSession (nullable) | Link to veto session if method is veto |
| `team_a_preferred` | FK → ServerRegion (nullable) | Team A's preferred region (for auto_nearest) |
| `team_b_preferred` | FK → ServerRegion (nullable) | Team B's preferred region (for auto_nearest) |
| `locked_at` | DateTimeField (nullable) | When selection was finalized |

#### 8.11.5 Auto-Nearest Algorithm (Optional Mode)

```
If server_veto_format == 'auto_nearest':
    → Read team_a_preferred and team_b_preferred regions
    → If same region → use that region
    → If different → calculate midpoint:
        → For each region in server_pool:
            → avg_distance = (distance_to_team_a_region + distance_to_team_b_region) / 2
        → Select region with minimum avg_distance
        → If tie → select region with lower max_distance (fairness priority)
    → Lock selection → notify both teams
    → Either captain can protest within 5 minutes → escalates to organizer manual pick
```

#### 8.11.6 TOC Server Management Panel

| Feature | Description |
|---------|-------------|
| **Region Library** | Manage global server region list per game (add/edit/deactivate regions) |
| **Tournament Server Pool** | Select which regions are available for this tournament's matches |
| **Veto Config** | Set server veto format — integrated into the existing Veto Builder UI (§8.7) |
| **Override** | Organizer can manually assign a server region to any match, overriding veto result |
| **Ping Advisory** | Optional: display estimated ping ranges for each team based on their country/region profile |
| **Match Record** | Server region shown in match details and broadcast feed |
| **Dispute Log** | If a team claims server issues mid-match — log with evidence for admin review |

#### 8.11.7 Configuration Defaults

| Setting | Default | Description |
|---------|---------|-------------|
| `DEFAULT_SERVER_VETO_FORMAT` | `organizer_pick` | Default for non-international tournaments |
| `SERVER_VETO_TIMEOUT_SECONDS` | `45` | Time per server ban/pick action |
| `AUTO_NEAREST_PROTEST_WINDOW_MINUTES` | `5` | Time window for captain protest on auto-nearest selection |
| `MAX_SERVER_REGIONS_IN_POOL` | `7` | Maximum regions in a tournament's server pool |

---

## 9. Pillar 8 — Data, Stats & Leaderboards

### 9.1 Leaderboard System (Complete Architecture)

**9 Models in `apps/leaderboards/`:**

| Model | Purpose |
|-------|---------|
| `LeaderboardEntry` | Pre-computed leaderboard row. Types: tournament, seasonal, all_time, team, game_specific, mmr, elo, tier |
| `LeaderboardSnapshot` | Daily rank history per player/team |
| `UserStats` | Per-user per-game stats (matches, tournaments, W/L, KDA) |
| `TeamStats` | Per-team per-game stats |
| `TeamRanking` | ELO ratings per team per game (K=32) |
| `UserMatchHistory` | Per-user match results chain |
| `TeamMatchHistory` | Per-team match results with ELO delta |
| `Season` | Competitive season with decay rules |
| `UserAnalyticsSnapshot` | Rich user analytics (tier, percentile, rolling averages, streaks) |
| `TeamAnalyticsSnapshot` | Rich team analytics (tier, synergy, activity) |

**Tier System:**
| Tier | ELO Range |
|------|-----------|
| Bronze | 0–1199 |
| Silver | 1200–1599 |
| Gold | 1600–1999 |
| Diamond | 2000–2399 |
| Crown | 2400+ |

**Service Layer:**
- Redis-cached leaderboards with feature flags
- `get_tournament_leaderboard()`, `get_player_leaderboard_history()`, `get_scoped_leaderboard()`
- PII-free DTOs for API responses

### 9.2 Tournament-Specific Stats

**GroupStanding** provides per-group stats:
- `matches_played/won/drawn/lost`, `points`
- `goals_for/against/difference` (for sports-like games)
- `rounds_won/lost/difference` (for FPS games)
- `total_kills/deaths`, `kda_ratio`, `total_assists`, `total_score`
- `placement_points`, `average_placement` (for BR games)
- `game_stats` JSONB (extensible per-game stats)
- `is_advancing`, `is_eliminated`

**TournamentResult** provides final standings:
- winner, runner_up, third_place
- total_kills, best_placement, avg_placement, matches_played
- series_score (JSONB), game_results (JSONB)

### 9.3 TOC Stats Integration (NEEDED)

**What the TOC should show organizers:**

| Stat Category | Data Points |
|---------------|-------------|
| **Registration Analytics** | Registration velocity (signups/day), conversion funnel (view → register → pay → confirm), drop-off points |
| **Match Analytics** | Average match duration, score distributions, closest matches, biggest upsets |
| **Player Performance** | Top performers in this tournament (kills, wins, K/D), MVP candidates |
| **Tournament Health** | Dispute rate, no-show rate, forfeit rate, average check-in speed |
| **Engagement** | Page views, spectator count (if tracked), stream viewers, announcement read rate |
| **Financial** | Revenue collected, outstanding, refund rate, average payment time |

### 9.4 Post-Tournament Report (NEEDED)

**Auto-generated after tournament completion:**
- Tournament summary (format, participants, duration, match count)
- Final standings/bracket
- Top performers / MVP
- Financial summary (collected, paid out, net)
- Dispute summary
- Participant feedback (if collected)
- Exportable as PDF or shareable link

### 9.5 Rewards & Certificate Builder — Trophies, Badges & Certificates

**THE PROBLEM:** The `enable_certificates` flag exists on the Tournament model, and the completion flow mentions "certificates issued." But there is zero implementation: no certificate templates, no dynamic text mapping, no digital trophies, and no mechanism for badges to appear on player profiles. Gap #23 acknowledges this.

**SOLUTION:** A "Rewards & Certificate Builder" tool in the TOC that allows organizers to create customizable certificates, assign digital profile badges/trophies, and manage the complete post-tournament rewards pipeline.

#### 9.5.1 Certificate Builder

**NEW MODEL: `CertificateTemplate`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `tournament` | FK → Tournament | Parent tournament |
| `name` | CharField(200) | Template name (e.g., "Winner Certificate", "Participation Certificate") |
| `template_type` | CharField | `winner` / `runner_up` / `top4` / `participant` / `mvp` / `custom` |
| `background_image` | ImageField | Uploaded PDF/image template background |
| `layout_config` | JSONField | Dynamic field positions + styles (see below) |
| `is_active` | BooleanField (default True) | Active toggle |
| `created_by` | FK → User | Organizer who created |

**DYNAMIC VARIABLE MAPPING (layout_config):**

Organizers upload a background image (certificate design) and then place dynamic text fields on it, mapped to tournament data:

| Variable | Resolves To | Example |
|----------|------------|----------|
| `{{player_name}}` | Player's display name | "Sakib Hossain" |
| `{{team_name}}` | Team display name | "Team Phoenix" |
| `{{tournament_name}}` | Tournament title | "DeltaCrown Championship S1" |
| `{{placement}}` | Ordinal placement | "1st Place" |
| `{{placement_number}}` | Numeric placement | "1" |
| `{{game_name}}` | Game title | "Valorant" |
| `{{date}}` | Tournament completion date | "February 23, 2026" |
| `{{organizer_name}}` | Organizer's display name | "DeltaCrown Esports" |
| `{{prize_amount}}` | Prize won | "৳5,000" |
| `{{total_matches}}` | Matches played by participant | "7" |
| `{{total_wins}}` | Match wins | "6" |
| `{{kda}}` | Kill/Death/Assist ratio | "2.4" |
| `{{custom_field_X}}` | Any custom field value | Varies |

**CERTIFICATE GENERATION PIPELINE:**
```
Tournament → COMPLETED
    → System checks: enable_certificates == True AND CertificateTemplate(s) exist
    → For each applicable template:
        → Query eligible participants (based on template_type):
            - winner: TournamentResult.winner
            - runner_up: TournamentResult.runner_up
            - top4: Top 4 from bracket/standings
            - participant: All confirmed registrations
            - mvp: Custom selection by organizer
        → For each eligible participant:
            → Render template: overlay dynamic text on background_image
            → Generate PDF (server-side rendering via WeasyPrint or Pillow)
            → Store as CertificateRecord (linked to user + tournament)
            → Notify participant: "Your certificate is ready!"
    → Certificates accessible from player's profile page and tournament results page
```

**NEW MODEL: `CertificateRecord`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `template` | FK → CertificateTemplate | Template used |
| `tournament` | FK → Tournament | Tournament context |
| `user` | FK → User | Recipient |
| `registration` | FK → Registration (nullable) | Registration context |
| `rendered_pdf_url` | URLField | Generated certificate PDF/image URL |
| `variable_snapshot` | JSONField | Exact values used for rendering (audit) |
| `issued_at` | DateTimeField (auto) | When generated |
| `downloaded_count` | PositiveIntegerField (default 0) | Track certificate downloads |
| `shared_count` | PositiveIntegerField (default 0) | Track social shares |

#### 9.5.2 Digital Profile Trophies & Badges

**NEW MODEL: `ProfileTrophy`**

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `name` | CharField(200) | Trophy display name (e.g., "DeltaCrown Champion S1") |
| `description` | TextField | Trophy description |
| `trophy_image` | ImageField | Trophy/badge icon (displayed on profile) |
| `trophy_type` | CharField | `champion` / `runner_up` / `top4` / `participant` / `mvp` / `streak` / `custom` |
| `rarity` | CharField | `common` / `uncommon` / `rare` / `epic` / `legendary` |
| `tournament` | FK → Tournament (nullable) | Source tournament (null for platform-wide trophies) |
| `game` | FK → Game (nullable) | Game context |
| `is_platform_trophy` | BooleanField (default False) | Platform-issued vs organizer-issued |
| `created_by` | FK → User | Issuer |

**NEW MODEL: `UserTrophy`** (M2M through table)

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `user` | FK → User | Trophy holder |
| `trophy` | FK → ProfileTrophy | The trophy |
| `awarded_at` | DateTimeField (auto) | When awarded |
| `awarded_for` | TextField (blank) | Context (e.g., "Won DeltaCrown Championship S1") |
| `is_displayed` | BooleanField (default True) | Whether user shows this on their profile |
| `display_order` | PositiveIntegerField (default 0) | Trophy showcase order |

**TROPHY AWARD PIPELINE:**
```
Tournament → COMPLETED
    → award_placements() runs (existing)
    → ADDITIONALLY: award_trophies() runs:
        → Check if organizer configured trophies for this tournament
        → For each placement:
            - Winner → Champion trophy (Legendary rarity)
            - Runner-up → Runner-up trophy (Epic rarity)
            - Top 4 → Semi-finalist trophy (Rare rarity)
            - All participants → Participant badge (Common rarity)
            - MVP (if selected) → MVP trophy (Epic rarity)
        → Create UserTrophy records
        → Trophies appear on user's profile showcase
```

#### 9.5.3 TOC Rewards Builder Interface

**Location:** TOC Settings Tab → "Rewards & Certificates" panel.

| Section | Features |
|---------|----------|
| **Certificate Templates** | Upload background, drag-and-drop dynamic field placement, preview with sample data, duplicate/edit/delete |
| **Trophy Configuration** | Select which placement trophies to award, upload custom trophy images, set rarity |
| **MVP Selection** | After tournament completes, organizer selects MVP from top performers list |
| **Bulk Issue** | "Generate All Certificates" button + progress bar |
| **Preview & Test** | Render a sample certificate with dummy data before tournament ends |
| **Download All** | ZIP download of all generated certificates (for physical printing at LAN events) |

#### 9.5.4 Player-Facing Integration

| Location | What Appears |
|----------|--------------|
| **User Profile Page** | Trophy showcase: grid of earned trophy icons with hover details |
| **Tournament Results Page** | "Download Certificate" button next to player's placement |
| **Social Sharing** | "Share Certificate" button → generates shareable OG image for Twitter/Facebook |
| **Profile Stats** | Total trophies count, rarest trophy, trophy history timeline |

### 9.6 Player Trust & Reputation Index

**THE PROBLEM:** DeltaCrown has no quantitative measure of player reliability. Repeat offenders — chronic no-shows, serial dispute abusers, and players who forfeit mid-bracket — face no systemic consequence beyond individual tournament penalties. Organizers cannot filter out low-quality players at registration time, and high-quality players have no visible reputation advantage. Platforms like ESEA and FACEIT solved this with trust/karma scores that reward consistent, fair play.

**SOLUTION:** A global **Trust Score** (0–100) on `UserProfile` that dynamically adjusts based on player behavior across all tournaments. Organizers can set a minimum trust score as a registration requirement.

#### 9.6.1 Trust Score Architecture

**New Fields on `UserProfile`:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `trust_score` | DecimalField(5,2) | `75.00` | Current trust score (0.00 – 100.00) |
| `trust_score_updated_at` | DateTimeField | auto | Last recalculation timestamp |
| `trust_events_count` | PositiveIntegerField | `0` | Total events that have affected trust score |
| `trust_tier` | CharField | `good` | Computed: `excellent` (90+) / `good` (70–89) / `moderate` (50–69) / `low` (25–49) / `restricted` (0–24) |

**New Tournament Setting:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `minimum_trust_score_required` | DecimalField (nullable) | `null` | Minimum trust score to register (null = no requirement) |
| `show_trust_scores_to_organizer` | BooleanField | `True` | Organizer can see participant trust scores in TOC |
| `show_trust_tier_publicly` | BooleanField | `False` | Show trust tier badge on public tournament profile |

#### 9.6.2 New Model: `TrustEvent`

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |
| `user` | FK → User | Affected player |
| `event_type` | CharField | See event types table below |
| `tournament` | FK → Tournament (nullable) | Context tournament |
| `match` | FK → Match (nullable) | Context match |
| `delta` | DecimalField | Points change (positive = increase, negative = decrease) |
| `score_before` | DecimalField | Trust score before this event |
| `score_after` | DecimalField | Trust score after this event |
| `reason` | TextField (blank) | Human-readable reason |
| `created_by` | FK → User (nullable) | Admin who triggered (null for system events) |
| `is_system_generated` | BooleanField (default True) | Auto-generated vs manual admin override |
| `created_at` | DateTimeField (auto) | Event timestamp |
| `expires_at` | DateTimeField (nullable) | For decaying events: when the impact expires |

#### 9.6.3 Trust Event Types & Point Values

**Positive Events (Trust Increases):**

| Event | Code | Base Delta | Description |
|-------|------|------------|-------------|
| Match completed (no disputes) | `match_clean_complete` | +0.5 | Every clean match slightly boosts trust |
| Tournament completed (no incidents) | `tournament_clean_complete` | +2.0 | Full tournament participation without issues |
| Dispute resolved in player's favor | `dispute_won` | +1.0 | Player's dispute was legitimate |
| Consecutive clean tournaments (streak) | `clean_streak_3` / `_5` / `_10` | +3.0 / +5.0 / +10.0 | Streak bonuses at 3, 5, 10 consecutive clean tournaments |
| Account age bonus | `account_maturity` | +0.1/month | Slow passive increase for account longevity (capped at +12) |
| Admin trust boost (manual) | `admin_boost` | Variable | Admin manually awards trust (e.g., community contribution) |

**Negative Events (Trust Decreases):**

| Event | Code | Base Delta | Description |
|-------|------|------------|-------------|
| No-show / Forfeit (unexcused) | `no_show` | -5.0 | Failed to appear for a scheduled match |
| Dispute filed against (lost) | `dispute_lost` | -3.0 | Player was found at fault in a dispute |
| Frivolous dispute (Protest Bond burned) | `frivolous_dispute` | -4.0 | Filed a dispute that was rejected + bond burned |
| Match Medic penalty | `medic_penalty` | -2.0 | Received a penalty during match operations |
| DQ from tournament | `disqualified` | -8.0 | Disqualified for rule violation |
| Toxic behavior report (confirmed) | `toxic_behavior` | -6.0 | Confirmed toxic behavior report |
| Score manipulation attempt | `score_fraud` | -15.0 | Attempted to submit fraudulent scores |
| Admin manual deduction | `admin_penalty` | Variable | Admin manually deducts trust |

#### 9.6.4 Trust Score Calculation

```python
def recalculate_trust_score(user: User) -> Decimal:
    """
    Recalculate trust score from all non-expired trust events.
    Score is clamped to [0, 100] range.
    New accounts start at 75.
    """
    BASE_SCORE = Decimal('75.00')

    # Get all non-expired events
    events = TrustEvent.objects.filter(
        user=user,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now())
    )

    total_delta = events.aggregate(total=Sum('delta'))['total'] or Decimal('0')

    raw_score = BASE_SCORE + total_delta
    clamped_score = max(Decimal('0'), min(Decimal('100'), raw_score))

    # Update tier
    if clamped_score >= 90:
        tier = 'excellent'
    elif clamped_score >= 70:
        tier = 'good'
    elif clamped_score >= 50:
        tier = 'moderate'
    elif clamped_score >= 25:
        tier = 'low'
    else:
        tier = 'restricted'

    user.profile.trust_score = clamped_score
    user.profile.trust_tier = tier
    user.profile.trust_score_updated_at = now()
    user.profile.save(update_fields=['trust_score', 'trust_tier', 'trust_score_updated_at'])

    return clamped_score
```

#### 9.6.5 Registration Gate Integration

```
Player attempts registration for Tournament X
    → IF tournament.minimum_trust_score_required is not null:
        → Fetch player.profile.trust_score
        → IF trust_score < minimum_trust_score_required:
            → Registration BLOCKED
            → Message: "This tournament requires a trust score of {min}+. Your score: {current}."
            → Link to "How to improve your trust score" help page
        → IF trust_score >= minimum_trust_score_required:
            → Registration proceeds normally
    → IF minimum_trust_score_required is null:
        → No trust gate; registration proceeds
```

#### 9.6.6 Trust Dashboard (TOC Participants Tab)

| Feature | Description |
|---------|-------------|
| **Trust Column** | Participant grid shows trust score + tier badge per player |
| **Trust Distribution** | Chart showing trust tier breakdown of registered players |
| **Flagged Players** | Highlight players below a configurable threshold (e.g., below 50) |
| **Trust History** | Click any player → view full trust event timeline |
| **Manual Adjustment** | Organizer can submit trust adjustment request (platform admin approves) |
| **Export Trust Data** | CSV export of all participant trust scores for analysis |

#### 9.6.7 Player-Facing Trust Features

| Location | What Appears |
|----------|--------------|
| **User Profile Page** | Trust tier badge: 🟢 Excellent / 🔵 Good / 🟡 Moderate / 🟠 Low / 🔴 Restricted |
| **Profile Stats** | Trust score (if user opts to show), trust event history |
| **Registration Page** | If tournament requires min trust: "Your trust score: 82/100 ✅" or "⚠️ Below minimum" |
| **Trust Improvement Guide** | Help page explaining how trust score works and how to improve |
| **Trust Appeal** | If player believes score is unfair, submit appeal to platform admin |

#### 9.6.8 Event Decay & Score Normalization

| Rule | Description |
|------|-------------|
| **Negative Event Decay** | Negative events older than 6 months have their delta halved; older than 12 months → zeroed |
| **Positive Event Persistence** | Positive events never expire (reward long-term good behavior) |
| **Score Floor** | Trust score cannot go below 0; players at 0 are effectively platform-restricted |
| **Score Ceiling** | Trust score cannot exceed 100 |
| **Recalculation Frequency** | Recalculated on every trust-affecting event + daily batch job for decay processing |
| **Initial Score** | New accounts start at 75 ("assumed good faith") |
| **Smurf Protection** | Accounts younger than 30 days capped at trust score 80 (cannot bypass high-trust gates immediately) |

---

## 10. Pillar 9 — Staff & Role-Based Access Control

### 10.1 Staff Architecture (Dual System)

**Legacy System (TournamentStaffRole + TournamentStaff):**
- 13 boolean permission fields on TournamentStaffRole
- Direct role-to-user assignment

**Phase 7 System (StaffRole + TournamentStaffAssignment + MatchRefereeAssignment):**
- `StaffRole` with `code` (unique) and `capabilities` (JSON array)
- `TournamentStaffAssignment` — User + Role + Tournament + optional Stage scope
- `MatchRefereeAssignment` — Assign staff to specific matches as referee

**StaffPermissionChecker** (dual-path):
- Checks Phase 7 `TournamentStaffAssignment` first (capability JSON)
- Falls back to legacy `TournamentStaff` if Phase 7 not found
- Organizer and superuser always pass all checks

### 10.2 Permission Codes

| Code | Description | Used By |
|------|-------------|---------|
| `manage_registrations` | Approve/reject registrations, manage waitlist | Participants tab |
| `approve_payments` | Verify/reject payments, process refunds | Payments tab |
| `manage_brackets` | Generate/reset/seed brackets | Brackets tab |
| `resolve_disputes` | Review and resolve disputes | Disputes tab |
| `make_announcements` | Create/edit announcements | Announcements tab |
| `edit_settings` | Change tournament configuration | Settings tab |
| `manage_staff` | Add/remove staff, assign roles | Settings tab |
| `view_all` | Read-only access to all tabs | All tabs |

### 10.3 Tab-Level Access Matrix

| Tab | Required Permission | Fallback |
|-----|-------------------|----------|
| Overview | Any staff role | Always visible |
| Participants | `manage_registrations` | Read-only if `view_all` |
| Payments | `approve_payments` | Read-only if `view_all` |
| Brackets | `manage_brackets` | Read-only if `view_all` |
| Matches | `manage_brackets` | Read-only if `view_all` |
| Schedule | `manage_brackets` | Read-only if `view_all` |
| Disputes | `resolve_disputes` | Read-only if `view_all` |
| Announcements | `make_announcements` | Read-only if `view_all` |
| Settings | `edit_settings` | Hidden unless `edit_settings` or `manage_staff` |

### 10.4 NEEDED RBAC Enhancements

| Feature | Description |
|---------|-------------|
| **Granular Action Permissions** | Per-action permissions (can approve but not reject, can verify but not refund) |
| **Stage-Scoped Staff** | Staff assigned only to specific stages (e.g., "Group Stage Referee") |
| **Match-Scoped Referee** | Referee only sees/manages their assigned matches (EXISTS in model, needs view integration) |
| **Staff Invitation Workflow** | Invite staff by email/username, they accept/decline |
| **Staff Activity Log** | Track all actions taken by each staff member |
| **Staff Shift Scheduling** | For large tournaments, schedule staff shifts |
| **Permission Templates** | Pre-built role templates (Head Admin, Scorekeeper, Media Manager, etc.) |
| **Temporary Elevation** | Temporarily grant additional permissions with expiry |
| **Staff Dashboard** | Dedicated view for staff showing only their relevant tasks |

### 10.5 Suggested Default Role Templates

| Role | Capabilities |
|------|-------------|
| **Head Admin** | All permissions |
| **Registration Manager** | manage_registrations, approve_payments, view_all |
| **Match Official / Referee** | manage_brackets (matches only), resolve_disputes, view_all |
| **Scorekeeper** | manage_brackets (scores only), view_all |
| **Media Manager** | make_announcements, view_all |
| **Observer** | view_all only |

### 10.6 Admin Pseudonyms — Staff Identity Protection

**THE PROBLEM:** Tournament staff who interact with players through dispute resolution chats, announcement posts, and Match Medic communications are exposed by their personal usernames. Angry players can (and do) target admins with off-platform harassment — social media abuse, Discord DMs, and in-game griefing.

**SOLUTION:** Introduce an "Admin Masking" system that allows staff members to post under organizational pseudonyms instead of their personal accounts.

**CONFIGURATION:**

| Level | Setting | Description |
|-------|---------|-------------|
| **Platform-wide** | `ADMIN_MASKING_AVAILABLE` (feature flag) | Master feature toggle |
| **Tournament-level** | `Tournament.enable_admin_masking` (BooleanField, default True) | Organizer can disable for their tournament |
| **Staff-level** | `TournamentStaffAssignment.use_pseudonym` (BooleanField, default False) | Per-staff toggle |

**NEW FIELDS:**

| Model | Field | Type | Description |
|-------|-------|------|-------------|
| `TournamentStaffAssignment` | `use_pseudonym` | BooleanField (default False) | Whether this staff member posts under a pseudonym |
| `TournamentStaffAssignment` | `pseudonym_name` | CharField(100, blank) | Custom pseudonym (e.g., "Tournament Official #3") |
| `TournamentStaffAssignment` | `pseudonym_display` | CharField(100, blank) | Pre-set display name if no custom name set |

**PRE-SET PSEUDONYM OPTIONS:**
- "Tournament Official"
- "DeltaCrown Admin"
- "Match Official"
- "Tournament Referee"
- Custom (staff sets their own pseudonym)

**WHERE MASKING APPLIES:**

| Context | Masked? | Display Name |
|---------|---------|-------------|
| **Dispute Chat** (3-Way Match Medic) | Yes | Pseudonym replaces real username in chat messages |
| **Global Announcements** | Yes | "Posted by Tournament Official" instead of real name |
| **Lobby Announcements** | Yes | Pseudonym in author field |
| **Match Notes** (organizer notes on matches) | Yes | Pseudonym in note author |
| **Registration Rejection Reasons** | Yes | "Reviewed by Tournament Official" |
| **TOC Internal Views** (organizer-only) | No | Real username always shown to other staff |
| **Audit Log** | No | Real username always recorded for accountability |
| **Admin Panel** | No | Real identity always visible to platform admins |

**KEY PRINCIPLE: Pseudonyms are player-facing only.** All internal systems (TOC views, audit logs, admin panels) always show the real identity. This ensures accountability while protecting staff from player harassment.

**IMPLEMENTATION:**
```python
# In any player-facing context:
def get_display_name(staff_assignment):
    if staff_assignment.use_pseudonym and tournament.enable_admin_masking:
        return (
            staff_assignment.pseudonym_name
            or staff_assignment.pseudonym_display
            or "Tournament Official"
        )
    return staff_assignment.user.username
```

---

## 11. Pillar 10 — Economy Integration

### 11.1 DeltaCoin Wallet System

**DeltaCrownWallet (one per user):**
- `cached_balance` — Current usable balance
- `pending_balance` — Locked during pending withdrawals
- `lifetime_earnings` — Total earned (never decremented)
- Bangladesh payment accounts: bKash, Nagad, Rocket numbers; bank details
- PIN security: `pin_hash`, `pin_enabled`, lockout after failed attempts

**DeltaCrownTransaction (immutable ledger):**
- Reasons: `participation`, `top4`, `runner_up`, `winner`, `entry_fee_debit`, `refund`, `manual_adjust`, `correction`, `p2p_transfer`
- Idempotency key prevents duplicate transactions
- Amount nonzero CHECK constraint

### 11.2 Tournament ↔ Economy Integration Points

| Integration | Direction | Description |
|-------------|-----------|-------------|
| **Entry Fee (DeltaCoin)** | Player → Platform | Debit wallet for entry fee; auto-create Payment record as VERIFIED |
| **Entry Fee (MFS)** | Player → Organizer | Manual payment + proof; organizer verifies |
| **Participation Reward** | Platform → Player | Award DeltaCoin to all confirmed participants after tournament |
| **Placement Prize (DeltaCoin)** | Platform → Player | Award DeltaCoin prizes per placement (winner/runner-up/top4) |
| **Placement Prize (Cash)** | Organizer → Player | Manual payout via PrizeClaim workflow |
| **Refund (DeltaCoin)** | Platform → Player | Credit wallet when DeltaCoin payment is refunded |
| **CoinPolicy** | Config | Per-tournament payout rates: participation (5), top4 (25), runner_up (50), winner (100) defaults |

### 11.3 Economy Services Used by TOC

| Service | Method | Called When |
|---------|--------|------------|
| `wallet_for(profile)` | Get/create wallet | Registration with DeltaCoin payment |
| `award(profile, amount, reason, idempotency_key)` | Credit/debit | All economy operations |
| `award_participation_for_registration(reg)` | Credit participation coins | Tournament completion |
| `award_placements(tournament)` | Credit placement prizes | Tournament completion |

---

## 12. Pillar 11 — Audit Trail, Versioning & Compliance

### 12.1 Existing Audit Mechanisms

| Mechanism | Model/Field | Description |
|-----------|-------------|-------------|
| `TournamentVersion` | Full JSONB snapshots | Every configuration change versioned |
| `ResultVerificationLog` | Per-submission step log | Every step of result verification logged |
| `Payment.*_by`, `*_at` fields | Per-action actor+timestamp | Who verified/rejected/refunded each payment and when |
| `Registration.checked_in_by` | FK → User | Who performed check-in |
| `DisputeRecord.resolved_by_user` | FK → User | Who resolved each dispute |
| `TournamentStaffAssignment.assigned_by` | FK → User | Who assigned each staff member |
| `SoftDeleteModel` | `is_deleted`, `deleted_at` | Soft-delete, never hard-delete |
| `TimestampedModel` | `created_at`, `updated_at` | Auto-timestamps on all models |

### 12.2 NEEDED Audit Enhancements

| Feature | Description |
|---------|-------------|
| **Unified Audit Log** | Single table recording ALL organizer actions: who, what, when, IP, user-agent |
| **Action Replay** | View chronological timeline of all actions in a tournament |
| **Export Audit Log** | CSV/JSON export for compliance |
| **IP Logging** | Record IP address for all sensitive actions (payment verification, score override, etc.) |
| **Reason Requirement** | Force reason field for destructive actions (DQ, score override, tournament cancel) |
| **Change Diff** | Show exact field-level diff for configuration changes |
| **Data Retention Policy** | Auto-archive/purge old audit data per compliance requirements |
| **Tampering Detection** | Hash chain on critical records (payment verifications, score submissions) |

---

## 13. Pillar 12 — Real-Time & WebSocket Architecture

### 13.1 Current WebSocket Usage

**BracketService** broadcasts `bracket_updated` event via WebSocket when bracket is generated/modified.

**EXISTS (infrastructure):**
- Django Channels configured in `deltacrown/routing.py`
- ASGI application in `deltacrown/asgi.py`
- Redis channel layer

### 13.2 NEEDED Real-Time Features

| Feature | Channel | Events |
|---------|---------|--------|
| **Live Score Updates** | `tournament.{id}.scores` | `match_score_updated`, `match_completed` |
| **Bracket Progression** | `tournament.{id}.bracket` | `bracket_updated`, `match_winner_set` |
| **Check-In Status** | `tournament.{id}.checkin` | `player_checked_in`, `checkin_undone`, `checkin_window_changed` |
| **Match State Changes** | `match.{id}.state` | `match_started`, `match_paused`, `match_completed` |
| **Announcements** | `tournament.{id}.announcements` | `new_announcement`, `announcement_pinned` |
| **Registration Feed** | `tournament.{id}.registrations` | `new_registration`, `registration_confirmed` |
| **Dispute Alerts** | `tournament.{id}.disputes` | `dispute_opened`, `dispute_resolved` |
| **Schedule Updates** | `tournament.{id}.schedule` | `match_rescheduled`, `round_started` |
| **Organizer Alerts** | `tournament.{id}.organizer` | `payment_submitted`, `dispute_opened`, `check_in_warning` |

### 13.3 Event Bus Integration

**EXISTS:** Internal event bus (`common.events`) for decoupled service communication.

**Events published:**
- `checkin.completed`, `checkin.reverted`
- `bracket.generated`, `bracket.updated`
- `tournament.registration_opened`, `tournament.started`, `tournament.completed`, `tournament.cancelled`

**NEEDED events:**
- `payment.submitted`, `payment.verified`, `payment.rejected`, `payment.refunded`
- `match.started`, `match.completed`, `match.disputed`, `match.forfeited`
- `dispute.opened`, `dispute.resolved`, `dispute.escalated`
- `announcement.created`
- `staff.assigned`, `staff.removed`
- `registration.confirmed`, `registration.rejected`, `registration.waitlisted`

---

## 14. Cross-Cutting Concerns

### 14.1 Notification System

**NEEDED — Unified notification dispatch:**

| Event | Recipients | Channels |
|-------|-----------|----------|
| Registration confirmed | Player | In-app, email, push |
| Payment verified | Player | In-app, email |
| Payment rejected | Player | In-app, email (with reason + resubmit link) |
| Check-in reminder | All confirmed | In-app, email, push |
| Match scheduled | Match participants | In-app, push |
| Match starting soon | Match participants | In-app, push |
| Score submitted | Opponent | In-app, push |
| Dispute opened | Both parties + organizer | In-app, email |
| Dispute resolved | Both parties | In-app, email |
| Announcement published | All registrants (or targeted) | In-app, push, Discord webhook |
| Prize available | Winner | In-app, email |
| Tournament cancelled | All registrants | In-app, email |
| Waitlist promoted | Promoted player | In-app, email, push |

### 14.2 Export & Reporting

**EXISTING:**
- `export-roster/` — Registration CSV
- `export-payments/` — Payment CSV

**NEEDED:**
| Export | Format | Contents |
|--------|--------|----------|
| Match Results | CSV/JSON | All matches with scores, winners, times |
| Tournament Report | PDF | Full tournament summary (standings, stats, financials) |
| Bracket Data | JSON | Complete bracket tree for external consumption |
| Audit Log | CSV | All organizer actions |
| Participant Communications | CSV | All announcements sent |
| Leaderboard | CSV | Final tournament leaderboard |

### 14.3 Performance & Scaling

| Concern | Current | Target |
|---------|---------|--------|
| **Query Optimization** | Some N+1 queries in organizer views | All queries optimized with select_related/prefetch_related |
| **Denormalization** | `total_registrations`, `total_matches`, `completed_matches` on Tournament | Add more counters as needed, update via signals/services |
| **Caching** | Redis for leaderboards | Cache tournament stats, bracket data, payment summaries |
| **Pagination** | 20 per page on registrations/payments | Configurable, cursor-based for large tournaments |
| **Background Jobs** | Celery for scheduled tasks | More jobs: auto-verification, reminder emails, stale cleanup |
| **Concurrent Writes** | Basic ORM saves | Optimistic locking for bracket progression, score submission |

### 14.4 Error Handling & Recovery

| Scenario | Handling |
|----------|----------|
| Bracket generation fails mid-creation | Atomic transaction — all or nothing |
| Payment verification race condition | Idempotency key on Payment |
| Double score submission | MatchResultSubmission tracks all submissions, idempotent finalization |
| WebSocket disconnection | Client-side reconnect with state sync |
| Celery task failure | Retry with exponential backoff, dead letter queue |
| Tournament status conflict | State machine validation before every transition |

---

## 15. Gap Analysis — What Exists vs What's Needed

### 15.1 Critical Gaps (Must Build)

| # | Gap | Priority | Description |
|---|-----|----------|-------------|
| 1 | **State Machine Enforcement** | P0 | Transitions are ad-hoc, no centralized state machine with validation |
| 2 | **Swiss System Engine** | P0 | Model exists but no pairing/ranking engine |
| 3 | **Revenue Analytics** | P0 | No financial dashboard in TOC |
| 4 | **Refund Workflow** | P0 | Basic flag exists, no complete workflow |
| 5 | **Notification Dispatch** | P0 | No unified notification system for tournament events |
| 6 | **Post-Tournament Report** | P1 | No auto-generated report after completion |
| 7 | **Unified Audit Log** | P1 | Audit data scattered across models |
| 8 | **Transition Readiness Checks** | P1 | No automated pre-flight checks before status transitions |
| 9 | **Global Killswitch (Tournament Freeze)** | P0 | No mechanism to freeze all tournament operations during global emergencies |
| 10 | **Roster Lock & Emergency Substitution** | P0 | No formal roster lock enforcement or substitute request workflow after registration closes |
| 11 | **Double Elimination Bracket Reset** | P0 | True Finals (bracket reset when LB winner beats UB winner in Grand Final) not implemented |

### 15.2 Important Gaps (Should Build)

| # | Gap | Priority | Description |
|---|-----|----------|-------------|
| 9 | **Match Timeline** | P1 | No event log per match |
| 10 | **Staff Activity Log** | P1 | No tracking of staff actions |
| 11 | **Best-of-N Support** | P1 | Single score pair, not BO3/BO5 per-map scores |
| 12 | **Map/Veto System & Game Logic Builder** | P0 | No map pick/ban workflow; no per-game rule configuration engine; promotes to P0 with full Veto Builder spec |
| 13 | **Dispute Time Window** | P1 | No configurable dispute filing deadline |
| 14 | **Real-Time WebSocket Events** | P1 | Only bracket updates, missing scores/checkin/announcements |
| 15 | **Prize Distribution Preview** | P1 | No tool to preview exact prize amounts |
| 16 | **Partial Payment Verification (MFS)** | P1 | No partial approval for bKash/Nagad shortfalls; verify-or-reject binary only |
| 17 | **Platform Take-Rate & Fee Deduction** | P1 | Prize distribution does not deduct platform/organizer fees before payout |
| 18 | **Protest Bond (Anti-Spam Disputes)** | P1 | No economic deterrent against frivolous dispute filings |
| 19 | **Admin Pseudonyms (Staff Protection)** | P1 | Staff personal usernames exposed in all player-facing communications |
| 20 | **Seed-Based Map/Side Advantage** | P1 | Bracket engine does not pass seed advantage data to match lobbies |
| 21 | **Data-Entry Verification UI (Split-Screen)** | P0 | No side-by-side screenshot + score entry view for API-less result verification |
| 22 | **Quick Comms / WhatsApp Integration** | P1 | No direct phone/WhatsApp contact from TOC participant grid |
| 23 | **Live Broadcast Director (Draw Control)** | P1 | No organizer-controlled step-by-step draw reveal interface for live ceremonies |
| 24 | **Rewards & Certificate Builder** | P1 | Certificate flag exists but no template system, no trophy/badge system, no generation pipeline |
| 25 | **Multi-Wave Qualifier Pipelines** | P1 | No formal linkage between qualifier stages; organizer manually copies qualified teams between tournaments |
| 26 | **Embeddable Iframe Widgets** | P1 | No `<iframe>` embed codes for external sites to display live brackets, standings, or schedules |
| 27 | **Mutual Reschedule Requests** | P1 | No team-initiated reschedule workflow; all schedule changes require manual organizer intervention |
| 28 | **KYC / Identity Verification for Prize Claims** | P0 | No identity verification gate before cash payouts; fraud and compliance risk |
| 29 | **Rulebook Versioning & Forced Re-Consent** | P1 | No version history for rule edits; no re-acknowledgment mechanism when rules change mid-tournament |
| 30 | **Match VOD & Media Archiving** | P1 | No centralized replay/VOD attachment on matches; no "Watch Replay" integration |
| 31 | **Battle Royale Scoring Matrix** | P0 | No configurable placement→points mapping or kill multiplier for BR games; no auto-score calculation engine |
| 32 | **Broadcast Stream & Station Dispatcher** | P1 | No mechanism to assign matches to LAN stations or stream channels; Broadcast API has no per-station filtering |
| 33 | **Drag-and-Drop Tiebreaker Engine** | P1 | Group/Swiss standings use hardcoded sort order; organizer cannot configure custom tiebreaker hierarchies |
| 34 | **Free Agent / LFG Pool** | P1 | Solo players cannot register for team tournaments; no free agent pool, no mix-team formation workflow |
| 35 | **Player Trust & Reputation Index** | P1 | No quantitative measure of player reliability; no trust-based registration gating or behavioral history tracking |
| 36 | **LAN QR Desk Check-In** | P1 | No venue-side identity verification for LAN events; online check-in cannot confirm physical presence, enabling ghost registrations |
| 37 | **Asymmetric Rosters — Man-Down Allowance** | P1 | No support for undermanned matches; if a player disconnects or is absent, the match must be forfeited — no partial-roster continuation policy |
| 38 | **Custom Bounties & Special Prizes** | P1 | Prize distribution limited to bracket placement; no named bounties (MVP, Highest Fragger), no sponsor-funded awards, no stat-leader suggestions |
| 39 | **Server Region Vetoes** | P1 | No formal server selection mechanism for cross-regional matches; hard-coded single region per tournament, no captain veto/ban on server location |

### 15.3 Nice-to-Have Gaps (Could Build)

| # | Gap | Priority | Description |
|---|-----|----------|-------------|
| 16 | **Discord Bot Integration** | P2 | Manual Discord link only |
| 17 | **Anti-Cheat Integration** | P3 | No anti-cheat hooks |
| 18 | **Group Draw Animation** | P2 | No visual draw ceremony |
| 19 | **Match Replay/Rematch** | P2 | No rematch creation tool |
| 20 | **Score Import from Game API** | P3 | Manual score entry only |
| 21 | **SMS Blast** | P3 | No SMS for LAN events |
| 22 | **Fan Voting** | P3 | Flag exists, no implementation |
| 23 | **Certificate Generation** | P1 | Promoted from P2 → P1; now covered by Rewards & Certificate Builder spec (§9.5) |
| 24 | **Broadcast API (OBS/vMix Feed)** | P2 | No read-only JSON data feed for broadcast overlay tools (OBS, vMix, Singular.live) |

---

## 16. Database Schema Inventory

### 16.1 All Tournament-Related Models (25+)

| Model | File | Records |
|-------|------|---------|
| `Tournament` | `models/tournament.py` | Core tournament entity |
| `CustomField` | `models/tournament.py` | Custom field definitions per tournament |
| `TournamentVersion` | `models/tournament.py` | Configuration version snapshots |
| `Registration` | `models/registration.py` | Participant registrations |
| `Payment` | `models/registration.py` | Registration payments |
| `PaymentVerification` | `models/payment_verification.py` | Legacy payment verification (consolidated into Payment) |
| `TournamentPaymentMethod` | `models/payment_config.py` | Per-method payment account config |
| `Match` | `models/match.py` | Individual matches |
| `Bracket` | `models/bracket.py` | Bracket tree metadata |
| `BracketNode` | `models/bracket.py` | Bracket tree nodes |
| `TournamentStage` | `models/stage.py` | Multi-stage tournament stages |
| `Group` | `models/group.py` | Groups for group-stage format |
| `GroupStanding` | `models/group.py` | Per-participant group standings |
| `GroupStage` | `models/group.py` | Group stage configuration |
| `TournamentLobby` | `models/lobby.py` | Pre-tournament lobby settings |
| `CheckIn` | `models/lobby.py` | Check-in records |
| `LobbyAnnouncement` | `models/lobby.py` | Lobby-specific announcements |
| `TournamentAnnouncement` | `models/announcement.py` | Tournament-wide announcements |
| `TournamentSponsor` | `models/sponsor.py` | Sponsor entries |
| `MatchResultSubmission` | `models/result_submission.py` | Player-submitted match results |
| `ResultVerificationLog` | `models/result_submission.py` | Per-step verification log |
| `DisputeRecord` | `models/dispute.py` | Phase 6 dispute records |
| `DisputeEvidence` | `models/dispute.py` | Evidence attachments |
| `Dispute` (legacy) | `models/match.py` | Deprecated inline dispute |
| `TournamentResult` | `models/result.py` | Final tournament standings |
| `PrizeTransaction` | `models/prize.py` | Prize amount records |
| `PrizeClaim` | `models/prize_claim.py` | Prize payout claims |
| `TournamentStaffRole` (legacy) | `models/staff.py` | Legacy role definitions |
| `TournamentStaff` (legacy) | `models/staff.py` | Legacy staff assignments |
| `StaffRole` (Phase 7) | `models/staffing.py` | Capability-based roles |
| `TournamentStaffAssignment` | `models/staffing.py` | Phase 7 staff assignments |
| `MatchRefereeAssignment` | `models/staffing.py` | Per-match referee assignments |
| `RegistrationQuestion` | `models/smart_registration.py` | Dynamic form questions |
| `RegistrationDraft` | `models/smart_registration.py` | In-progress registration wizard |
| `RegistrationAnswer` | `models/smart_registration.py` | Answers to custom questions |
| `RegistrationRule` | `models/smart_registration.py` | Auto-processing rules |
| `EmergencySubRequest` | `models/registration.py` (new) | Emergency substitute requests after roster lock |
| `BroadcastFeed` | `models/broadcast.py` (new) | Per-tournament broadcast data feed configuration |
| `GameMatchConfig` | `models/match_config.py` (new) | Per-tournament map pool, veto sequence, and game-specific rules |
| `MapPoolEntry` | `models/match_config.py` (new) | Individual map entries with custom images |
| `MatchVetoSession` | `models/match_config.py` (new) | Per-match veto execution log and results |
| `CertificateTemplate` | `models/rewards.py` (new) | Organizer-uploaded certificate templates with dynamic field mapping |
| `CertificateRecord` | `models/rewards.py` (new) | Generated certificate records per participant |
| `ProfileTrophy` | `models/rewards.py` (new) | Digital trophy/badge definitions |
| `UserTrophy` | `models/rewards.py` (new) | User ↔ Trophy M2M with display settings |
| `KYCSubmission` | `models/prize_claim.py` (new) | Identity document submissions for prize claim verification |
| `QualifierPipeline` | `models/pipeline.py` (new) | Multi-stage qualifier pipeline linking multiple tournaments |
| `PipelineStage` | `models/pipeline.py` (new) | Individual stage within a qualifier pipeline |
| `PromotionRule` | `models/pipeline.py` (new) | Auto-promotion rules between pipeline stages |
| `PipelineInvite` | `models/pipeline.py` (new) | Direct invites to pipeline stages (bypass qualifiers) |
| `RescheduleRequest` | `models/match.py` (new) | Team-initiated mutual reschedule requests |
| `MatchMedia` | `models/match.py` (new) | VOD/replay/media attachments on completed matches |
| `RulebookVersion` | `models/rulebook.py` (new) | Immutable rulebook version snapshots with change tracking |
| `RulebookConsent` | `models/rulebook.py` (new) | Per-participant consent records for rulebook versions |
| `FreeAgentRegistration` | `models/registration.py` (new) | Solo free agent signup records for team tournaments |
| `BRScoringMatrix` | `models/match_config.py` (new) | Configurable placement→points and kill multiplier for BR games |
| `BRMatchResult` | `models/match_config.py` (new) | Per-team-per-game BR result (placement, kills, calculated points) |
| `BroadcastStation` | `models/broadcast.py` (new) | Named LAN stations or stream channels for match routing |
| `TrustEvent` | `models/trust.py` (new) | Behavioral events that adjust a player's trust score |
| `TournamentBounty` | `models/prizes.py` (new) | Named non-placement prizes (MVP, Highest Fragger) with organizer assignment workflow |
| `ServerRegion` | `models/match_config.py` (new) | Game-specific server region definitions with geo-coordinates for auto-nearest |
| `MatchServerSelection` | `models/match_config.py` (new) | Per-match server region selection record (veto result, auto-nearest, or organizer override) |

### 16.2 Cross-App Models Used by TOC

| Model | App | Usage |
|-------|-----|-------|
| `DeltaCrownWallet` | economy | DeltaCoin payments/prizes |
| `DeltaCrownTransaction` | economy | Ledger entries |
| `CoinPolicy` | economy | Per-tournament payout config |
| `LeaderboardEntry` | leaderboards | Post-tournament stat generation |
| `UserStats` / `TeamStats` | leaderboards | Player/team performance |
| `TeamRanking` | leaderboards | ELO-based seeding |
| `Season` | leaderboards | Seasonal competition context |
| `Game` | games | Game reference |
| `User` | accounts | Organizer, participants, staff |
| `UserProfile` | user_profile | Wallet link, profile data |
| `Team` | teams/organizations | Team participants |

---

## 17. API Endpoint Inventory

### 17.1 All Organizer/Manage Endpoints (50+)

**Navigation:**
| Endpoint | Name | Description |
|----------|------|-------------|
| `organizer/` | `organizer_dashboard` | Organizer's tournament list |
| `organizer/create/` | `create_tournament` | Create new tournament |
| `organizer/<slug>/` | `organizer_tournament_detail` | TOC Overview tab |
| `organizer/<slug>/<tab>/` | `organizer_hub` | TOC tab router |

**Registration Management (11 endpoints):**
| Endpoint | Name |
|----------|------|
| `approve-registration/<reg_id>/` | `approve_registration` |
| `reject-registration/<reg_id>/` | `reject_registration` |
| `bulk-approve-registrations/` | `bulk_approve_registrations` |
| `bulk-reject-registrations/` | `bulk_reject_registrations` |
| `disqualify/<reg_id>/` | `disqualify_participant` |
| `dq-cascade/<reg_id>/` | `disqualify_with_cascade` |
| `promote-waitlist/<reg_id>/` | `promote_registration` |
| `auto-promote-waitlist/` | `auto_promote_next` |
| `add-participant/` | `add_participant_manually` |
| `export-roster/` | `export_roster_csv` |
| `api/registration/<reg_id>/` | `registration_detail_api` |

**Check-In (4 endpoints):**
| Endpoint | Name |
|----------|------|
| `toggle-checkin/<reg_id>/` | `toggle_checkin` |
| `force-checkin/<reg_id>/` | `force_checkin` |
| `drop-noshow/<reg_id>/` | `drop_noshow` |
| `close-drop-noshows/` | `close_drop_noshows` |

**Payment Management (6 endpoints):**
| Endpoint | Name |
|----------|------|
| `verify-payment/<pay_id>/` | `verify_payment` |
| `reject-payment/<pay_id>/` | `reject_payment` |
| `bulk-verify-payments/` | `bulk_verify_payments` |
| `refund-payment/<pay_id>/` | `process_refund` |
| `export-payments/` | `export_payments_csv` |
| `registrations/<reg_id>/payment-history/` | `payment_history` |

**Bracket (4 endpoints):**
| Endpoint | Name |
|----------|------|
| `generate-bracket/` | `generate_bracket` |
| `reset-bracket/` | `reset_bracket` |
| `reorder-seeds/` | `reorder_seeds` |
| `publish-bracket/` | `publish_bracket` |

**Match Operations (12 endpoints):**
| Endpoint | Name |
|----------|------|
| `submit-score/<match_id>/` | `submit_match_score` |
| `reschedule-match/<match_id>/` | `reschedule_match` |
| `forfeit-match/<match_id>/` | `forfeit_match` |
| `override-score/<match_id>/` | `override_match_score` |
| `cancel-match/<match_id>/` | `cancel_match` |
| `match-ops/<match_id>/mark-live/` | `match_mark_live` |
| `match-ops/<match_id>/pause/` | `match_pause` |
| `match-ops/<match_id>/resume/` | `match_resume` |
| `match-ops/<match_id>/force-complete/` | `match_force_complete` |
| `match-ops/<match_id>/add-note/` | `match_add_note` |
| `match-ops/<match_id>/force-start/` | `match_force_start` |
| `pending-results/` | `pending_results` |

**Scheduling (3 endpoints):**
| Endpoint | Name |
|----------|------|
| `auto-schedule-round/` | `auto_schedule_round` |
| `bulk-shift-matches/` | `bulk_shift_matches` |
| `add-schedule-break/` | `add_schedule_break` |

**Disputes (3 endpoints):**
| Endpoint | Name |
|----------|------|
| `disputes/manage/` | `disputes_manage` |
| `resolve-dispute/<dispute_id>/` | `resolve_dispute` |
| `update-dispute-status/<dispute_id>/` | `update_dispute_status` |

**Result Verification (3 endpoints):**
| Endpoint | Name |
|----------|------|
| `confirm-result/<match_id>/` | `confirm_result` |
| `reject-result/<match_id>/` | `reject_result` |
| `override-result/<match_id>/` | `override_result` |

**Groups (2 endpoints):**
| Endpoint | Name |
|----------|------|
| `groups/configure/` | `group_configure` |
| `groups/draw/` | `group_draw` |

**Other (2 endpoints):**
| Endpoint | Name |
|----------|------|
| `health/` | `health_metrics` |
| `api/verify/` | `tournament_verification_api` |

---

## 18. Edge Cases & Tier-1 Esports Requirements

### 18.1 Registration Edge Cases

| Scenario | Required Handling |
|----------|------------------|
| Player registers, then their team disbands before tournament | Auto-flag registration for review; offer to convert to solo or cancel |
| Two teams register, then merge into one | Organizer tool to merge registrations (cancel one, reassign roster) |
| Player is on multiple team rosters across different tournaments | Allowed, unless tournament-specific rule prevents it |
| Registration spam (bot signups) | Rate limiting, CAPTCHA, requires verified email |
| Payment submitted but wrong amount | Organizer can partial-approve or reject with specific reason |
| MFS fee calculation error (player sends slightly less due to cash-out charges) | Partial verification workflow; track received vs expected amount; resolve shortfall via prize deduction, manual collection, or waiver |
| Platform fee misconfigured (percentage too high, eats entire prize pool) | Validation: `platform_fee_percentage + organizer_fee_percentage` must be < 100%; warn if net prize < 50% of gross |
| Player changes game IGN after registration | Roster re-verification check; flag if game ID no longer matches |
| Team captain transfers captaincy mid-registration | Re-validate captain/IGL assignment |
| Registration submitted right at deadline (race condition) | Use DB-level atomic check: `registration_end >= NOW()` at insert time |
| Waitlisted player promotes but doesn't pay by deadline | Auto-demote back to waitlist, promote next |

### 18.2 Match Edge Cases

| Scenario | Required Handling |
|----------|------------------|
| Both participants submit different scores | Auto-flag as dispute; show both submissions to organizer |
| Neither participant submits a score | After X hours, match auto-flags for organizer attention |
| Player disconnects mid-match | Technical pause state; configurable wait time before forfeit |
| Double forfeit (both sides no-show) | Both eliminated; if bracket, use placeholder/BYE for next round |
| Match result overridden after bracket progression | Cascade undo: revert subsequent matches, re-advance correct winner |
| Score submission after dispute window closedBR | Reject late submissions; only organizer can override |
| Tie in elimination bracket | Must have clear tiebreaker rules; cannot end in tie |
| Player DQ'd mid-bracket | All their future matches become opponent walkovers; cascade through bracket |
| Bracket reset dispute (Grand Final result disputed before reset can trigger) | Defer bracket reset decision until dispute fully resolved; do not auto-generate reset match while Grand Final is in DISPUTED state |
| Losers bracket winner forfeits Grand Final | No bracket reset; upper bracket champion wins automatically; match recorded as forfeit, not played |
| Emergency substitution during live match | Sub request must be filed between matches, not during; organizer can pause bracket during review |

### 18.3 Financial Edge Cases

| Scenario | Required Handling |
|----------|------------------|
| DeltaCoin payment but wallet balance drops after registration | Registration confirmed at time of debit; no clawback |
| Tournament cancelled after prizes distributed | Recovery workflow needed (separate from entry fee refunds) |
| Partial refund (tournament cancelled mid-way, some matches played) | Policy-based: refund entry fee minus service fee, or full refund |
| Currency conversion (BDT → DeltaCoin) | Fixed exchange rate per policy, not real-time |
| Duplicate payment submission | Idempotency key on Payment; second submission blocked |
| Payment deadline expires while payment is in "submitted" status | Grace period: if proof already submitted, don't expire; notify organizer |
| Organizer runs tournament for profit (entry fees > prizes) | Platform policy enforcement; take rate calculation |

### 18.4 Tournament Format Edge Cases

| Scenario | Required Handling |
|----------|------------------|
| Odd number of participants in single elimination | BYE system: top seeds get first-round BYE |
| 3 players/teams in double elimination | Degenerative bracket; may need special handling |
| Group stage with unequal group sizes | Normalize points per group (points-per-game or head-to-head tiebreaker) |
| Team withdraws after groups drawn but before group matches start | Re-balance groups OR give walkovers for their matches |
| Swiss system produces impossible pairings (all same-record players already played each other) | Fallback pairing algorithm; allow one rung-up/down pairing |
| Tournament format changed mid-tournament | Only allow before bracket generation; version the change |
| Power outage during LAN event | Suspend all matches; resume capability with match state preservation |
| Global game server outage during online event | Head Admin triggers Global Killswitch (Tournament Freeze); all timers frozen; resume when servers return with adjusted deadlines |
| Roster lock deadline passes but captain hasn't finalized roster | Lock enforced regardless; captain must file Emergency Sub Request for any changes |
| Player banned platform-wide after roster lock but before tournament | Emergency Sub Request auto-generated; admin reviews whether ban warrants DQ of entire team |

### 18.5 Staff & Security Edge Cases

| Scenario | Required Handling |
|----------|------------------|
| Staff member registers as participant in same tournament | Block: staff cannot be participants (enforce in registration validation) |
| Organizer account compromised | 2FA enforcement for organizer actions; require password for destructive actions |
| Staff collusion (insider gives advantage to specific team) | Audit log accountability; random referee assignment option |
| Multiple organizers editing settings simultaneously | Optimistic locking on tournament settings (version check) |
| Admin harassed off-platform after visible dispute ruling | Admin Pseudonym masking prevents personal username exposure in player-facing contexts |
| Broadcast feed token leaked to unauthorized party | Organizer regenerates token from TOC Settings; old URL immediately invalidated |

### 18.6 Tier-1 Platform Requirements Checklist

| Requirement | Status |
|-------------|--------|
| Sub-100ms response time for all TOC pages | 🔶 Needs optimization pass |
| Handle 256-participant tournaments without performance degradation | ✅ Bracket service handles up to 256 |
| Handle 1000+ concurrent viewers on live tournament page | 🔶 Needs WebSocket scaling plan |
| Zero data loss on match results (idempotent, atomic) | ✅ Idempotency keys exist |
| Full audit trail for all organizer actions | 🔶 Partial — needs unified audit log |
| Global emergency freeze capability (Tournament Killswitch) | 🔶 Needs implementation (v1.1 spec) |
| Roster lock enforcement with emergency substitution workflow | 🔶 Needs implementation (v1.1 spec) |
| Double elimination bracket reset (True Finals) | 🔶 Needs implementation (v1.1 spec) |
| Partial payment verification for MFS edge cases | 🔶 Needs implementation (v1.1 spec) |
| Anti-spam dispute system (Protest Bond via DeltaCoin) | 🔶 Needs implementation (v1.1 spec) |
| Broadcast data feed for OBS/vMix overlays | 🔶 Needs implementation (v1.1 spec) |
| Staff identity protection (Admin Pseudonyms) | 🔶 Needs implementation (v1.1 spec) |
| API-less score verification (split-screen proof + entry UI) | 🔶 Needs implementation (v1.2 spec) |
| Game-specific veto/map pool configuration engine | 🔶 Needs implementation (v1.2 spec) |
| Live draw director with WebSocket-controlled reveal | 🔶 Needs implementation (v1.2 spec) |
| Direct participant contact (WhatsApp/phone integration) | 🔶 Needs implementation (v1.2 spec) |
| Certificate generation & digital trophy system | 🔶 Needs implementation (v1.2 spec) |
| Multi-wave qualifier pipeline with auto-promotion | 🔶 Needs implementation (v1.3 spec) |
| Embeddable iframe widgets for external sites | 🔶 Needs implementation (v1.3 spec) |
| Team-initiated mutual reschedule workflow | 🔶 Needs implementation (v1.3 spec) |
| KYC identity verification for prize claims | 🔶 Needs implementation (v1.3 spec) |
| Rulebook versioning with forced re-consent | 🔶 Needs implementation (v1.3 spec) |
| Match VOD & media archiving system | 🔶 Needs implementation (v1.3 spec) |
| Battle Royale scoring matrix with auto-calculation engine | 🔶 Needs implementation (v1.4 spec) |
| Broadcast stream & LAN station dispatcher | 🔶 Needs implementation (v1.4 spec) |
| Drag-and-drop tiebreaker hierarchy engine | 🔶 Needs implementation (v1.4 spec) |
| Free agent / LFG pool with mix-team formation | 🔶 Needs implementation (v1.4 spec) |
| Player trust & reputation index with registration gating | 🔶 Needs implementation (v1.4 spec) |
| LAN QR desk check-in with venue-side scanner | 🔶 Needs implementation (v1.5 spec) |
| Asymmetric rosters with man-down allowance policy | 🔶 Needs implementation (v1.5 spec) |
| Custom bounties & special prizes with sponsor support | 🔶 Needs implementation (v1.5 spec) |
| Server region vetoes with auto-nearest algorithm | 🔶 Needs implementation (v1.5 spec) |
| RBAC with principle of least privilege | ✅ Phase 7 capability-based system |
| Rate limiting on all organizer endpoints | 🔶 Needs implementation |
| CSRF + authentication on all mutation endpoints | ✅ Django's built-in CSRF + @login_required |
| Soft-delete with recovery (no permanent data loss) | ✅ SoftDeleteModel on all key models |
| Timezone-aware scheduling (BST default, configurable) | 🔶 Needs per-tournament timezone field |
| Multi-language support (Bangla + English) | 🔶 Django i18n exists but not applied to tournament content |
| Mobile-responsive API for future mobile app | 🔶 REST API exists (DRF) but not comprehensive for TOC operations |

---

## Appendix A — Data Flow Diagrams

### A.1 Registration → Confirmation Flow
```
Player → RegistrationDraft (5-step wizard)
    → Registration (status: submitted)
    → RegistrationRules (auto-processing)
    → [AUTO_APPROVED | NEEDS_REVIEW | PENDING | REJECTED | WAITLISTED]
    → If payment needed: Payment (status: pending)
        → Player submits proof → Payment (status: submitted)
        → Organizer verifies → Payment (status: verified)
        → Registration → CONFIRMED
    → If no payment: Registration → CONFIRMED
    → DeltaCoin: auto-debit wallet → Payment VERIFIED → Registration CONFIRMED
```

### A.2 Match Lifecycle Flow
```
Bracket Generated → Match (SCHEDULED)
    → Check-in window opens → Match (CHECK_IN)
    → Both checked in → Match (READY)
    → Organizer/auto start → Match (LIVE)
    → Score submitted → Match (PENDING_RESULT)
        → Opponent confirms OR auto-confirm deadline → Match (COMPLETED)
        → Opponent disputes → Match (DISPUTED) → Dispute Resolution → Match (COMPLETED)
    → No score → timeout → Organizer forced to intervene
    → Winner set → BracketNode.winner_id updated → Advance to parent node
```

### A.3 Tournament Complete Flow
```
All matches COMPLETED/FORFEIT/CANCELLED
    → Tournament status → COMPLETED
    → TournamentResult created (winner, runner_up, third_place)
    → award_placements() runs:
        → PrizeTransaction per placement
        → DeltaCoin credits to wallets
        → Cash PrizeClaims created (status: pending)
    → award_participation_for_registration() runs:
        → DeltaCoin participation reward to all confirmed
    → LeaderboardEntry records updated
    → UserStats/TeamStats updated
    → TeamRanking ELO recalculated
    → UserMatchHistory/TeamMatchHistory created
    → Certificates generated (if enabled)
    → Post-tournament report auto-generated
```

---

## Appendix B — Existing Planning Document Index

| Document | Location | Relevance |
|----------|----------|-----------|
| Tournament Lifecycle Build Plan | `Documents/TOURNAMENT_LIFECYCLE_BUILD_PLAN.md` | Public-facing lifecycle (detail pages, lobby, arena) — 90% complete |
| Complete Rebuild Plan (Registration) | `Documents/Registration_system/07_COMPLETE_REBUILD_PLAN.md` | 7-step wizard rebuild plan |
| Command Center v1 Architecture | `Documents/CommandCenter_v1/` | Original TOC architecture planning |
| Leaderboards Spec v1 | `docs/specs/LEADERBOARDS_SPEC_V1.md` | Comprehensive leaderboard specification |
| System Architecture | `docs/architecture/system_architecture.md` | High-level system architecture |
| For New Tournament Design (8 docs) | `Documents/For_New_Tournament_design/` | Enterprise tournament architecture from external analysis |
| Modules 1.1–9.6 | `Documents/ExecutionPlan/Modules/` | Detailed module completion reports |
| Phase 3–7 Archives | `Documents/Archive/Phase*/` | Historical phase completion records |
| Tournament OPS Audit (Dec 19) | `Documents/Audit/Tournament OPS dec19/` | Full audit of models, views, services |

---

*This document is the single source of truth for the Tournament Operations Center architecture. All future UI/UX work, PRDs, and implementation sprints should reference this document for backend requirements and data flows.*

*Last updated: 2026-02-23*
