# DeltaCrown — Implementation Tracker v1.0

> **Version:** 1.0
> **Date:** February 19, 2026
> **Companion Doc:** `02_REGISTRATION_SYSTEM_PLAN.md` v3.0
> **Rule:** No task begins until this document is reviewed and approved.
> **Convention:** `[ ]` = not started, `[~]` = in progress, `[x]` = done, `[!]` = blocked

---

## How to Use This Tracker

1. Each task has a unique ID (e.g., `P1-T01`)
2. **File Paths** are relative to `G:\My Projects\WORK\DeltaCrown\`
3. **Acceptance Criteria (AC)** define "done" — every AC must pass before marking `[x]`
4. Tasks within a phase are ordered by dependency (top tasks unlock bottom tasks)
5. Cross-phase dependencies are noted explicitly

---

## PHASE 1: MVP — Registration + Core TOC (3-4 weeks)

**Phase Goal:** Players can register (solo + team) with payment verification. Organizers have a working Tournament Operations Center with Command Center, Participant Hub, and Payment Queue.

**Entry Criteria:** All existing tests pass (`pytest` green), no regressions.

---

### P1-T01: TOC Navigation Shell (`_base.html` Upgrade)

- [ ] **Build the 7-tab navigation in the TOC base template**
- **Files to modify:**
  - `templates/tournaments/manage/_base.html`
- **Files to create:**
  - None (existing file upgrade)
- **AC:**
  - [ ] 7 tabs rendered: Command Center, Participants, Brackets, Matches, Schedule, Disputes, Settings
  - [ ] Active tab highlighted based on current URL
  - [ ] Mobile-responsive: tabs collapse to dropdown or hamburger on small screens
  - [ ] Each tab links to correct URL (`/tournaments/<slug>/manage/<tab>/`)
  - [ ] `OrganizerRequiredMixin` enforced on all tab views

---

### P1-T02: TOC Command Center (Home)

- [ ] **Build the alert-driven Command Center as the default manage/ page**
- **Files to modify:**
  - `apps/tournaments/views/organizer.py` — upgrade `OrganizerHubView` to compute alerts
  - `templates/tournaments/manage/overview.html` — rewrite as Command Center
- **Files to create:**
  - `apps/tournaments/services/command_center_service.py` — alert generation logic
- **AC:**
  - [ ] Pending payment count alert with link to payment queue
  - [ ] Guest teams needing review alert with link to participants (filtered)
  - [ ] Open dispute count alert with link to dispute center
  - [ ] Quick stats: total registrations, pending, confirmed, waitlisted
  - [ ] Tournament lifecycle progress bar (registration → brackets → live → completed)
  - [ ] Upcoming events list (registration deadline, check-in window, start time)
  - [ ] Zero-alert state shows "Nothing needs your attention" message

---

### P1-T03: Progressive Disclosure Registration UX

- [ ] **Upgrade `smart_register.html` with collapsible sections and summary bar**
- **Files to modify:**
  - `templates/tournaments/registration/smart_register.html`
  - `apps/tournaments/views/smart_registration.py` — add section readiness data to context
- **Files to create:**
  - `static/js/registration_progressive.js` — collapse/expand logic, scroll-to-error, mini-nav
  - `static/css/registration_progressive.css` — sticky headers, mobile layout, section animations
- **AC:**
  - [ ] Summary bar at top: "Your profile is ready ✅" or "N items need attention ⚠️"
  - [ ] Sections auto-collapsed when fully auto-filled and valid (green ✅)
  - [ ] Sections auto-expanded when data is missing or invalid (orange ⚠️)
  - [ ] Locked fields show info tooltip explaining source
  - [ ] Mobile: sticky section headers with `position: sticky`
  - [ ] Mobile: jump-to-section mini-nav dots at bottom
  - [ ] On submit failure: auto-scroll to first error with `scrollIntoView`
  - [ ] All tap targets ≥ 48px on mobile
  - [ ] Existing auto-fill behavior preserved (no regression)

---

### P1-T04: Wire Custom Questions into SmartRegistrationView

- [ ] **Connect `RegistrationQuestion` and `RegistrationAnswer` models to the live registration flow**
- **Files to modify:**
  - `apps/tournaments/views/smart_registration.py` — query questions, validate answers, save answers
  - `templates/tournaments/registration/smart_register.html` — render question fields in collapsible section
- **Files to reference (already exist, unused):**
  - `apps/tournaments/models/smart_registration.py` — `RegistrationQuestion`, `RegistrationAnswer`, `RegistrationDraft`
- **AC:**
  - [ ] `RegistrationQuestion.objects.filter(tournament=tournament)` queried in `get_context_data()`
  - [ ] Custom questions rendered in a "Custom Questions" collapsible section
  - [ ] Required questions block form submission with clear error messages
  - [ ] `RegistrationAnswer` created on successful registration submit
  - [ ] Question types supported: text, number, select, checkbox, file upload
  - [ ] Section collapsed if no custom questions exist for this tournament
  - [ ] Existing registration flow works unchanged when no custom questions configured

---

### P1-T05: Lineup Snapshot on Team Registration

- [ ] **Store team roster snapshot at registration time**
- **Files to modify:**
  - `apps/tournaments/views/smart_registration.py` — capture lineup on team registration submit
  - `apps/tournaments/models/registration.py` — ensure `lineup_snapshot` JSONField exists
- **AC:**
  - [ ] On team registration submit, `lineup_snapshot` populated with array of `{user_id, username, game_id, role}`
  - [ ] Snapshot reflects roster at moment of registration (immutable after submit)
  - [ ] Roster changes after registration don't affect snapshot
  - [ ] Snapshot viewable by organizer in participant detail view

---

### P1-T06: Registration Number Generation

- [ ] **Auto-generate unique registration numbers (e.g., `VCS-2026-001`)**
- **Files to modify:**
  - `apps/tournaments/models/registration.py` — add `registration_number` field if not present, add auto-generation in `save()`
  - `apps/tournaments/services/registration_service.py` — generate number on creation
- **AC:**
  - [ ] Format: `{TOURNAMENT_SLUG_PREFIX}-{YEAR}-{SEQUENTIAL_NUMBER}` (zero-padded 3 digits)
  - [ ] Unique per tournament (not globally)
  - [ ] Generated on registration creation, never changes
  - [ ] Displayed in participant table and payment verification queue
  - [ ] No collision under concurrent registration (atomic counter or `F()` expression)

---

### P1-T07: TOC Participants Hub

- [ ] **Build the full participant management table with filters and bulk actions**
- **Files to modify:**
  - `apps/tournaments/views/organizer_participants.py` — add filtering, search, pagination
  - `templates/tournaments/manage/participants.html` — full table layout with tabs
- **AC:**
  - [ ] Status filter tabs: All, Pending, Confirmed, Waitlist, Payment Queue, Guest Teams, DQ'd
  - [ ] Search by name, team name, game ID, registration number
  - [ ] Sortable columns: name, status, payment, date
  - [ ] Bulk actions: approve, reject (with dropdown)
  - [ ] Per-row actions menu (⋮): View Details, Approve, Reject, Toggle Check-In, DQ
  - [ ] Pagination (20 per page)
  - [ ] Guest team rows show "⚠️ Guest Team" badge
  - [ ] CSV export button (leverages existing export view)
  - [ ] Registration count header: "24 confirmed / 32 max"

---

### P1-T08: TOC Payment Verification Queue

- [ ] **Build dedicated payment verification sub-tab with proof image display**
- **Files to modify:**
  - `apps/tournaments/views/organizer_payments.py` — add queue view with proof data
  - `templates/tournaments/manage/payments.html` — payment card layout with proof image
- **AC:**
  - [ ] Shows only `payment.status = 'submitted'` by default
  - [ ] Each payment card shows: registration number, player/team name, method, amount, TxID, submitted timestamp
  - [ ] Proof image displayed inline with click-to-zoom (lightbox)
  - [ ] Verify button → payment verified, registration confirmed (if auto-approve on payment)
  - [ ] Reject button → requires reason text field, sends email notification
  - [ ] Bulk verify/reject (checkbox + button)
  - [ ] Card count in tab: "Payment Queue (3)"

---

### P1-T09: Refund Policy Display on Registration Form

- [ ] **Add refund policy fields to Tournament model and display before payment upload**
- **Files to modify:**
  - `apps/tournaments/models/tournament.py` — add `refund_policy` CharField + `refund_policy_text` TextField
  - `templates/tournaments/registration/smart_register.html` — refund policy section in payment area
  - `apps/tournaments/views/smart_registration.py` — pass refund policy to context
- **Files to create:**
  - Migration file (auto-generated via `makemigrations`)
- **AC:**
  - [ ] `refund_policy` field with 5 choices (no_refund, refund_until_checkin, refund_until_bracket, full_refund, custom)
  - [ ] `refund_policy_text` TextField for custom policy (Markdown)
  - [ ] Policy displayed in payment section BEFORE upload area
  - [ ] "I understand and accept the refund policy" checkbox required before upload button enabled
  - [ ] If `refund_policy == 'custom'`, render `refund_policy_text` as Markdown
  - [ ] If tournament is free (no entry fee), refund section hidden
  - [ ] Migration applies cleanly to existing data (no breaking changes)

---

### Phase 1 Exit Criteria

- [ ] All P1 tasks marked `[x]`
- [ ] All existing tests pass (`pytest` green, 172+ tests)
- [ ] New tests written for: command center alerts, progressive disclosure sections, custom question rendering, lineup snapshot, registration number generation, payment queue verify/reject
- [ ] Manual smoke test: register for a tournament (solo + team), verify payment, see participant in TOC
- [ ] Mobile smoke test: registration form usable on 375px viewport

---

## PHASE 2: Advanced Registration + Check-In (2-3 weeks)

**Phase Goal:** Guest team registration with abuse mitigation, duplicate detection, waitlist management, check-in control panel, display name overrides, and draft auto-save.

**Phase Entry Criteria:** Phase 1 complete + approved.

---

### P2-T01: Guest Team Registration Mode

- [ ] **Add guest team path to SmartRegistrationView**
- **Files to modify:**
  - `apps/tournaments/views/smart_registration.py` — detect guest team mode, render guest form, validate
  - `templates/tournaments/registration/smart_register.html` — guest team form section
  - `apps/tournaments/services/registration_service.py` — handle guest team data in Registration.data
- **AC:**
  - [ ] "Register as Guest Team" option shown only when `max_guest_teams > 0` and cap not reached
  - [ ] Guest form fields: team name, tag, captain name, captain email, member IGNs (dynamic count based on `team_size_min`)
  - [ ] Justification text field (required): "Why is your team not on DeltaCrown?"
  - [ ] Slot counter displayed: "Guest team slots: 2/5 remaining"
  - [ ] Submit creates `Registration` with `is_guest_team=True`, `status='needs_review'`
  - [ ] Guest roster stored in `Registration.data` JSONB
  - [ ] Rate limit: max 1 guest team per user per tournament

---

### P2-T02: Guest Team Cap & Soft Friction

- [ ] **Add `max_guest_teams` field to Tournament model with validation**
- **Files to modify:**
  - `apps/tournaments/models/tournament.py` — add `max_guest_teams` PositiveIntegerField (default=0)
  - `apps/tournaments/views/smart_registration.py` — validate cap on guest team submit
  - `templates/tournaments/manage/settings.html` — organizer toggle in TOC Settings
- **Files to create:**
  - Migration file (auto-generated)
- **AC:**
  - [ ] `max_guest_teams = 0` means guest teams disabled (default)
  - [ ] Cap enforced atomically (race condition safe — use `select_for_update` or `F()`)
  - [ ] Organizer can change cap in TOC Settings
  - [ ] When cap reached, guest team option hidden from registration form
  - [ ] Informational banner on guest form: "Guest teams require manual verification. This may take up to 24 hours."
  - [ ] Migration does not break existing tournaments (default=0 = no change in behavior)

---

### P2-T03: Duplicate Player Detection

- [ ] **Detect when the same game ID is registered multiple times in a tournament**
- **Files to modify:**
  - `apps/tournaments/services/registration_eligibility.py` — add cross-registration game ID check
  - `apps/tournaments/views/smart_registration.py` — surface duplicate warning
  - `templates/tournaments/manage/participants.html` — duplicate badge + alert in Command Center
- **AC:**
  - [ ] On registration submit: check if same game ID exists in another active registration for same tournament
  - [ ] If duplicate: block registration with clear error message
  - [ ] For team registrations: check all team member game IDs against all other registrations
  - [ ] Organizer alert in Command Center if duplicates detected across registrations
  - [ ] Guest team IGNs also checked (best-effort match against existing registrations)

---

### P2-T04: Waitlist Logic & Promotion UI

- [ ] **Implement auto-waitlist when tournament is full + organizer promotion controls**
- **Files to modify:**
  - `apps/tournaments/services/registration_service.py` — auto-waitlist when slots full, promote method
  - `apps/tournaments/views/organizer_participants.py` — promote from waitlist action
  - `templates/tournaments/manage/participants.html` — waitlist tab with promote buttons
- **AC:**
  - [ ] When confirmed registrations reach `max_participants`, new registrations auto-set to `waitlisted`
  - [ ] Waitlist ordered by registration timestamp (FIFO)
  - [ ] Organizer can promote individual waitlisted registrations (button in row)
  - [ ] On withdrawal of confirmed registration: optional auto-promote from waitlist
  - [ ] Promoted participant receives email notification
  - [ ] Waitlist tab shows position number for each entry

---

### P2-T05: Check-In Control Panel in TOC

- [ ] **Build check-in management tab in TOC Schedule section**
- **Files to modify:**
  - `apps/tournaments/views/checkin.py` — add organizer check-in control view
  - `templates/tournaments/manage/schedule.html` — check-in control UI (new template or upgrade existing)
- **Files to create:**
  - `templates/tournaments/manage/schedule.html` (if not already present)
- **AC:**
  - [ ] Check-in status table: all confirmed participants with ✅/⏳/❌ status
  - [ ] Force Check-In button per participant
  - [ ] Drop (no-show) button per participant → marks as dropped + fills BYE in bracket
  - [ ] Open Check-In Early button
  - [ ] Extend Check-In Window (+15min) button
  - [ ] Close & Drop All No-Shows button
  - [ ] Check-in stats bar: "18/24 checked in"
  - [ ] Auto-promote from waitlist checkbox option on drop

---

### P2-T06: Display Name Override Toggle

- [ ] **Add tournament-level display name override setting**
- **Files to modify:**
  - `apps/tournaments/models/tournament.py` — add `allow_display_name_override` BooleanField (default=False)
  - `apps/tournaments/views/smart_registration.py` — conditionally render display name field
  - `templates/tournaments/registration/smart_register.html` — editable display name field
  - `templates/tournaments/manage/settings.html` — toggle in TOC Settings
- **Files to create:**
  - Migration file (auto-generated)
- **AC:**
  - [ ] When `allow_display_name_override = True`: editable "Display Name" field appears below locked "Full Name"
  - [ ] Display name stored in `Registration.data['display_name']`
  - [ ] Display name used in brackets, match rooms, public participant lists (instead of real name)
  - [ ] Real name always stored and visible to organizer
  - [ ] When toggle is OFF: no display name field shown, profile name used everywhere
  - [ ] Default: OFF

---

### P2-T07: Draft Auto-Save (RegistrationDraft)

- [ ] **Implement auto-save via RegistrationDraft model with AJAX endpoint**
- **Files to modify:**
  - `apps/tournaments/views/smart_registration.py` — add draft save/load AJAX endpoints
  - `templates/tournaments/registration/smart_register.html` — debounced JS auto-save
  - `static/js/registration_progressive.js` — auto-save logic
- **Files to reference:**
  - `apps/tournaments/models/smart_registration.py` — `RegistrationDraft` (already exists)
- **AC:**
  - [ ] Draft saved via AJAX `POST` on field change (debounced 2 seconds)
  - [ ] Draft endpoint: `POST /tournaments/<slug>/register/draft/`
  - [ ] On page load: if draft exists, pre-fill form from draft data
  - [ ] Draft data overrides auto-fill for user-edited fields
  - [ ] Draft deleted on successful registration submit
  - [ ] Draft stored per-user per-tournament (upsert behavior)
  - [ ] Offline detection: if AJAX fails, save to `localStorage` and sync when reconnected
  - [ ] Draft age displayed: "Draft from 2 hours ago"

---

### Phase 2 Exit Criteria

- [ ] All P2 tasks marked `[x]`
- [ ] All existing + Phase 1 tests pass
- [ ] New tests: guest team cap enforcement, duplicate detection, waitlist ordering/promotion, check-in toggle, display name rendering, draft save/load
- [ ] Manual smoke test: register as guest team, see waitlist, organizer promotes from waitlist, check-in control works
- [ ] Edge case tested: guest team cap reached, concurrent registration race condition, draft recovery after network loss

---

## PHASE 3: Tournament Ops & Brackets (3-4 weeks)

**Phase Goal:** Full Tournament Operations Center with bracket generation, seeding, live match operations, scheduling, dispute resolution, and participant data control.

**Phase Entry Criteria:** Phase 2 complete + approved.

---

### P3-T01: TOC Bracket Generation UI

- [ ] **Build bracket generation interface in TOC Brackets tab**
- **Files to modify:**
  - `templates/tournaments/manage/brackets.html` — full bracket generation UI
  - `apps/tournaments/views/organizer.py` or new view — bracket generation form handling
- **Files to create:**
  - `apps/tournaments/views/organizer_brackets.py` — bracket generation view (or add to existing)
- **AC:**
  - [ ] Format selector dropdown: SE, DE, RR, Swiss
  - [ ] Seeding method selector: Registration Order, Random, Ranked, Manual
  - [ ] Config options per format (3rd place match, GF reset, Swiss rounds count, RR points config)
  - [ ] "Generate Bracket" button → calls `bracket_engine_service.generate()`
  - [ ] Generated bracket displayed as interactive visualization
  - [ ] "Reset" button → destroys bracket and allows regeneration
  - [ ] Cannot generate if < 2 confirmed participants
  - [ ] Format-specific visualizations: SE tree, DE winners+losers, RR table, Swiss rounds table
  - [ ] Bracket generation locked once first match is started

---

### P3-T02: Drag-and-Drop Seeding Interface

- [ ] **Build drag-and-drop seeding reorder UI before bracket publish**
- **Files to modify:**
  - `templates/tournaments/manage/brackets.html` — seeding table with drag handles
- **Files to create:**
  - `static/js/bracket_seeding.js` — drag-and-drop logic using Sortable.js or HTML5 DnD
  - `apps/tournaments/views/organizer_brackets.py` — HTMX endpoint for seed reorder
- **AC:**
  - [ ] After bracket generation: editable seed list with drag handles (☰)
  - [ ] Each row shows: seed #, team/player name, rank (from GamePassport), drag handle
  - [ ] Drag reorder fires HTMX `POST` to `bracket_editor_service.swap_participants()`
  - [ ] Seed position updates immediately in UI (optimistic update)
  - [ ] "Publish Bracket" button locks seeding (no more drag-drop)
  - [ ] BYE slots shown but not draggable
  - [ ] Works on touch devices (mobile drag support)

---

### P3-T03: TOC Match Operations (Match Medic)

- [ ] **Build match management panel with live controls**
- **Files to modify:**
  - `apps/tournaments/views/organizer_matches.py` — expand with match medic actions
  - `templates/tournaments/manage/matches.html` — (create or upgrade) match operations UI
- **Files to create:**
  - `templates/tournaments/manage/matches.html` (if not present)
- **AC:**
  - [ ] Tab filters: Active (live), Upcoming, Completed, All
  - [ ] Active match cards show: match #, round, teams, score, duration, status
  - [ ] Organizer actions per match: Edit Score, Pause, Resume, Force Complete, Force Start, Reset Score, Add Note, Forfeit, Cancel, Reschedule
  - [ ] Score Override panel: editable score fields, winner dropdown, mandatory reason text, confirm button
  - [ ] "⚠️ This will be logged in the audit trail" warning on destructive actions
  - [ ] Check-in status shown for CHECK_IN phase matches: who checked in, force check-in button
  - [ ] Force Start bypasses check-in requirement
  - [ ] No-Show Forfeit: if one team didn't check in, auto-forfeit to other team
  - [ ] All actions call existing `match_ops_service.py` methods (no new service code needed)

---

### P3-T04: TOC Scheduling Panel

- [ ] **Build round-by-round scheduling interface**
- **Files to modify or create:**
  - `templates/tournaments/manage/schedule.html` — scheduling UI (may share with check-in or be separate tab)
  - View file for scheduling endpoint (new or extend existing)
- **AC:**
  - [ ] Round-by-round match table: match number, teams, scheduled time, status
  - [ ] Per-match "Edit" button → time picker to reschedule
  - [ ] "Auto-Schedule Round" button → calls `manual_scheduling_service.auto_schedule_round()`
  - [ ] "Shift All +30min" button → calls `manual_scheduling_service.bulk_shift_schedule()`
  - [ ] "Add Break" button → insert break between matches
  - [ ] Scheduling config: default match duration, break between rounds, parallel match count
  - [ ] Conflict detection: warn if same team scheduled in overlapping matches
  - [ ] Uses existing `manual_scheduling_service.py` (405 lines) — no new service code needed

---

### P3-T05: TOC Dispute Resolution Center

- [ ] **Build dispute management interface in TOC Disputes tab**
- **Files to modify:**
  - `templates/tournaments/manage/disputes.html` — full dispute center layout
  - `apps/tournaments/views/dispute_resolution.py` or `disputes_management.py` — ensure all actions wired
- **AC:**
  - [ ] Tab filters: Open, Under Review, Resolved, All
  - [ ] Each dispute card shows: ID, match reference, filed by, against, category, timestamp, priority
  - [ ] Submitter statement and evidence files displayed
  - [ ] Action buttons: Accept (submitter wins), Reject (keep result), Request More Info, Escalate
  - [ ] Resolution notes text field (required for accept/reject)
  - [ ] On Accept: match score overridden, bracket updated, both parties notified
  - [ ] On Reject: original result stands, submitter notified with explanation
  - [ ] All actions call existing `dispute_service.py` (651 lines)

---

### P3-T06: Participant Data Control Panel

- [ ] **Build participant data management actions in TOC**
- **Files to modify:**
  - `apps/tournaments/views/organizer_participants.py` — add manual add, transfer, roster swap endpoints
  - `apps/tournaments/services/registration_service.py` — add `create_manual_registration()`, `transfer_registration()`
  - `templates/tournaments/manage/participants.html` — add manual add form, action modals
- **AC:**
  - [ ] "Add Participant Manually" button → modal with user search or manual entry
  - [ ] Manual add bypasses registration flow, creates `Registration` directly
  - [ ] Payment option on manual add: Waived, Mark as Paid, Require Payment
  - [ ] DQ action cascades: registration DQ'd → bracket node BYE'd → future matches forfeited
  - [ ] Roster swap: replace team member in `lineup_snapshot` with substitute (audit logged)
  - [ ] Transfer: move registration from one user/team to another (audit logged)
  - [ ] Free agent display: solo players in team tournaments listed as "available"

---

### P3-T07: Swiss Rounds 2+ Completion

- [ ] **Complete Swiss pairing algorithm for rounds beyond round 1**
- **Files to modify:**
  - `apps/tournament_ops/services/bracket_generators/swiss.py` — implement rounds 2+ pairing
- **AC:**
  - [ ] Round 2+ pairs players/teams with same W-L record
  - [ ] No rematches within same Swiss event (if possible)
  - [ ] Tiebreaker support: Buchholz, Sonneborn-Berger, or custom
  - [ ] Handles odd number of participants (BYE assignment rotates)
  - [ ] Final standings calculated after all rounds
  - [ ] Tested with 8, 16, 32 participants across 3-5 rounds

---

### P3-T08: 3rd Place & Grand Finals Reset UI Wiring

- [ ] **Wire existing bracket config options into TOC Brackets UI**
- **Files to modify:**
  - `templates/tournaments/manage/brackets.html` — checkboxes for 3rd place match and GF reset
  - View handling bracket generation — pass config to generator
- **AC:**
  - [ ] "Include 3rd place match" checkbox (SE only) → `bracket.third_place_match = True`
  - [ ] "Enable Grand Finals reset" checkbox (DE only) → `bracket.grand_finals_reset = True`
  - [ ] 3rd place match rendered in bracket visualization
  - [ ] GF reset: if loser bracket winner beats winners bracket winner, second match is generated
  - [ ] Config options disabled/hidden when irrelevant format selected

---

### Phase 3 Exit Criteria

- [ ] All P3 tasks marked `[x]`
- [ ] All existing + Phase 1 + Phase 2 tests pass
- [ ] New tests: bracket generation for all 4 formats, seeding reorder, match medic actions (pause/resume/force/override), scheduling conflict detection, dispute accept/reject, manual participant add, Swiss rounds 2+
- [ ] Integration test: full tournament lifecycle from registration → bracket → matches → results → winner
- [ ] Manual smoke test: generate bracket, drag seeds, start match, override score, resolve dispute

---

## PHASE 4: Automation & Polish (2-3 weeks)

**Phase Goal:** DeltaCoin payment, payment auto-expiry, Payment model consolidation, guest team conversion, notification events, and live draw.

**Phase Entry Criteria:** Phase 3 complete + approved.

---

### P4-T01: DeltaCoin Payment Integration

- [ ] **Wire DeltaCoin (virtual currency) as instant payment method**
- **Files to modify:**
  - `apps/tournaments/views/smart_registration.py` — DeltaCoin payment option
  - `apps/economy/` (or relevant app) — balance check + deduction API
  - `templates/tournaments/registration/smart_register.html` — DeltaCoin option in payment section
- **AC:**
  - [ ] DeltaCoin shown as payment option alongside bKash/Nagad/Rocket
  - [ ] Balance check: user's DeltaCoin balance shown, insufficient balance blocks selection
  - [ ] On submit: atomic balance deduction + payment creation with `status='verified'`
  - [ ] Registration auto-confirmed (no manual verification needed)
  - [ ] Refund on withdrawal: DeltaCoin returned to balance (if refund policy allows)
  - [ ] Transaction logged for audit

---

### P4-T02: Payment Deadline Auto-Expiry (Celery)

- [ ] **Implement Celery task to auto-expire unpaid registrations**
- **Files to create:**
  - `apps/tournaments/tasks/payment_expiry.py` — Celery periodic task
- **Files to modify:**
  - `deltacrown/celery.py` — register task beat schedule
  - `apps/tournaments/models/registration.py` — ensure `expires_at` or payment deadline field exists
- **AC:**
  - [ ] Celery task runs every 15 minutes
  - [ ] Finds registrations with `status='submitted'` past payment deadline
  - [ ] Updates status to `expired`
  - [ ] Sends email notification to player: "Your registration has expired due to unpaid entry fee"
  - [ ] Expired registration does not count against tournament slot cap
  - [ ] If waitlist exists: auto-promote next in line after expiry

---

### P4-T03: Payment Model Consolidation (4-Step Atomic Migration)

- [ ] **Execute the 4-step migration plan from Section 11 of the Master Plan**
- **Files to create:**
  - Migration: `0XXX_add_verification_fields_to_payment.py` — Step 1
  - Migration: `0XXX_copy_verification_data.py` — Step 2
  - `apps/tournaments/management/commands/verify_payment_consistency.py` — dual-write monitor
- **Files to modify:**
  - Payment service files — dual-write logic (Step 3)
- **AC:**
  - [ ] Step 1: New fields added to Payment model (non-destructive, nullable)
  - [ ] Step 2: Data migration copies PaymentVerification data to Payment fields
  - [ ] Step 2: Reverse migration works (clears copied fields)
  - [ ] Step 3: All service code dual-writes to both models
  - [ ] Step 3: Monitoring command reports zero discrepancies for 2+ weeks
  - [ ] Step 4: `PaymentVerification` model deleted (only after confidence period)
  - [ ] Database backup taken before each step
  - [ ] All existing payment tests pass throughout

---

### P4-T04: Guest-to-Real Team Conversion

- [ ] **Build invite-link based guest team conversion system**
- **Files to create:**
  - `apps/tournaments/services/guest_conversion_service.py` — conversion logic
  - `apps/tournaments/views/guest_conversion.py` — conversion views
  - `templates/tournaments/registration/guest_conversion.html` — conversion UI
- **AC:**
  - [ ] Organizer can generate invite link for a guest team registration
  - [ ] Link allows guest team members to claim their slot by creating DeltaCrown accounts
  - [ ] As members join: their game IDs auto-verified against guest roster IGNs
  - [ ] Full conversion: when all members joined, guest registration → real team registration
  - [ ] Partial conversion handled: "3 of 5 members have joined"
  - [ ] Organizer can manually approve partial conversions
  - [ ] Converted registration inherits original seed position and bracket slot

---

### P4-T05: RegistrationRule Auto-Evaluation

- [ ] **Wire RegistrationRule model into eligibility checking**
- **Files to modify:**
  - `apps/tournaments/services/registration_eligibility.py` — evaluate rules
  - `apps/tournaments/models/smart_registration.py` — ensure `RegistrationRule.evaluate()` method works
- **AC:**
  - [ ] Organizer can create rules via TOC Settings (e.g., "Minimum rank: Diamond")
  - [ ] Rules evaluated automatically during eligibility pre-check
  - [ ] Failed rules: clear error message explaining what's missing
  - [ ] Rule types: rank minimum, account age, previous tournament participation, game hours
  - [ ] Rules composable: AND/OR logic between multiple rules

---

### P4-T06: Notification Event Handlers

- [ ] **Wire notification events to email templates and in-app notifications**
- **Files to modify:**
  - `apps/tournaments/services/registration_service.py` — emit events on state transitions
  - `apps/notifications/` — add tournament event handlers
  - `templates/tournaments/emails/` — verify/update email templates
- **AC:**
  - [ ] Events emitted for: registration submitted/approved/rejected, payment submitted/verified/rejected, waitlist promoted, check-in open, tournament cancelled
  - [ ] Email sent for each event using existing templates
  - [ ] In-app notification created for each event (notification bell)
  - [ ] Organizer receives aggregated notifications (not per-registration spam)
  - [ ] Unsubscribe link in emails

---

### P4-T07: Live Draw (WebSocket Broadcast)

- [ ] **Implement live random seeding with real-time broadcast**
- **Files to modify:**
  - `deltacrown/routing.py` — add WebSocket route for live draw
  - `apps/tournaments/views/organizer_brackets.py` — "Live Draw" button
- **Files to create:**
  - `apps/tournaments/consumers/live_draw_consumer.py` — WebSocket consumer
  - `templates/tournaments/public/live/draw.html` — spectator draw page
- **AC:**
  - [ ] Organizer clicks "Live Draw" → seeds revealed one by one with animation
  - [ ] Spectators see real-time seed reveals via WebSocket
  - [ ] Each seed reveal has 2-3 second delay for dramatic effect
  - [ ] Draw result stored as permanent bracket seeding
  - [ ] Fallback for no-WebSocket: polling endpoint with same data

---

### Phase 4 Exit Criteria

- [ ] All P4 tasks marked `[x]`
- [ ] All existing + Phase 1-3 tests pass
- [ ] New tests: DeltaCoin payment flow, Celery expiry task, payment model migration (forward + reverse), guest conversion, rule evaluation, notification events
- [ ] Payment model consolidation: zero discrepancies for 2+ weeks before Step 4
- [ ] End-to-end integration test: full tournament lifecycle with all features

---

## Cross-Cutting Concerns

### Testing Strategy

| Phase | Unit Tests | Integration Tests | Manual Smoke |
|-------|-----------|-------------------|-------------|
| Phase 1 | ~20 new tests | Registration + TOC flow | Solo + Team reg, payment verify |
| Phase 2 | ~15 new tests | Guest team + waitlist flow | Guest reg, waitlist promote, check-in |
| Phase 3 | ~25 new tests | Full tournament lifecycle | Bracket → match → result → winner |
| Phase 4 | ~15 new tests | Payment migration safety | DeltaCoin, expiry, conversion |

### Template Naming Convention

```
templates/tournaments/manage/
├── _base.html          ← TOC shell (tabs, sidebar)
├── overview.html       ← Command Center (Module 1)
├── participants.html   ← Participant Hub (Module 2)
├── payments.html       ← Payment Queue (Module 2 sub-tab)
├── brackets.html       ← Bracket Engine (Module 3)
├── matches.html        ← Match Operations (Module 4)
├── schedule.html       ← Scheduling & Check-In (Module 5)
├── disputes.html       ← Dispute Center (Module 6)
└── settings.html       ← Settings (Module 7)
```

### URL Convention

All TOC URLs under `/tournaments/<slug>/manage/`:

```python
# Base
path('manage/', ..., name='organizer_hub'),

# Module tabs
path('manage/participants/', ..., name='manage_participants'),
path('manage/payments/', ..., name='manage_payments'),
path('manage/brackets/', ..., name='manage_brackets'),
path('manage/matches/', ..., name='manage_matches'),
path('manage/schedule/', ..., name='manage_schedule'),
path('manage/disputes/', ..., name='manage_disputes'),
path('manage/settings/', ..., name='manage_settings'),

# HTMX action endpoints (POST)
path('manage/brackets/generate/', ..., name='manage_bracket_generate'),
path('manage/brackets/seed/', ..., name='manage_bracket_seed'),
path('manage/brackets/publish/', ..., name='manage_bracket_publish'),
path('manage/matches/<int:match_id>/score/', ..., name='manage_match_score'),
path('manage/matches/<int:match_id>/force-start/', ..., name='manage_match_force_start'),
path('manage/matches/<int:match_id>/pause/', ..., name='manage_match_pause'),
path('manage/schedule/checkin/', ..., name='manage_checkin_control'),
path('manage/schedule/checkin/<int:reg_id>/force/', ..., name='manage_force_checkin'),
path('manage/participants/add/', ..., name='manage_add_participant'),
path('manage/participants/<int:reg_id>/dq/', ..., name='manage_dq_participant'),
path('manage/disputes/<int:dispute_id>/resolve/', ..., name='manage_resolve_dispute'),
```

### Service Layer Mapping (Existing → TOC Module)

| Service File | Lines | TOC Module |
|-------------|-------|-----------|
| `registration_service.py` | 1,999 | Module 2 (Participants) |
| `registration_autofill.py` | 503 | Registration UX |
| `registration_eligibility.py` | 270 | Registration UX |
| `bracket_service.py` | 1,498 | Module 3 (Brackets) |
| `bracket_engine_service.py` | 267 | Module 3 (Brackets) |
| `bracket_editor_service.py` | 427 | Module 3 (Brackets) + Module 7 (Data Control) |
| `match_service.py` | 1,318 | Module 4 (Matches) |
| `match_ops_service.py` | 632 | Module 4 (Matches) |
| `manual_scheduling_service.py` | 405 | Module 5 (Scheduling) |
| `checkin_service.py` | 453 | Module 5 (Check-In) |
| `dispute_service.py` | 651 | Module 6 (Disputes) |
| `result_submission_service.py` | 500 | Module 4 (Matches) |
| `winner_service.py` | 926 | Module 3 + 4 |
| `group_stage_service.py` | 1,167 | Module 3 (Brackets) |
| `lifecycle_service.py` | 334 | Module 1 (Command Center) |
| `tournament_ops_service.py` | 2,829 | All modules |
| `staffing_service.py` | 563 | Module 7 (Settings) |

### Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Swiss R2+ algorithm bugs | Medium | High | Extensive test coverage, reference buchholz.py implementations |
| Payment migration data loss | Low | Critical | 4-step atomic migration, dual-write monitoring, backups |
| Guest team abuse spike | Medium | Medium | `max_guest_teams` cap, rate limiting, manual review requirement |
| Concurrent registration race | Medium | Medium | `select_for_update()` on slot count check |
| Template bloat | High | Low | HTMX partials, shared components, template inheritance |
| Mobile UX poor | Medium | High | Test on 375px viewport, sticky headers, mini-nav |

---

> **Ready to execute.** Awaiting review and approval before Phase 1 begins.
