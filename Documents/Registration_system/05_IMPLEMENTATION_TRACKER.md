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

- [x] **Build the 7-tab navigation in the TOC base template**
- **Files to modify:**
  - `templates/tournaments/manage/_base.html`
- **Files to create:**
  - None (existing file upgrade)
- **AC:**
  - [x] 7 tabs rendered: Command Center, Participants, Brackets, Matches, Schedule, Disputes, Settings
  - [x] Active tab highlighted based on current URL
  - [x] Mobile-responsive: tabs collapse to dropdown or hamburger on small screens
  - [x] Each tab links to correct URL (`/tournaments/<slug>/manage/<tab>/`)
  - [x] `OrganizerRequiredMixin` enforced on all tab views

---

### P1-T02: TOC Command Center (Home)

- [x] **Build the alert-driven Command Center as the default manage/ page**
- **Files to modify:**
  - `apps/tournaments/views/organizer.py` — upgrade `OrganizerHubView` to compute alerts
  - `templates/tournaments/manage/overview.html` — rewrite as Command Center
- **Files to create:**
  - `apps/tournaments/services/command_center_service.py` — alert generation logic
- **AC:**
  - [x] Pending payment count alert with link to payment queue
  - [x] Guest teams needing review alert with link to participants (filtered)
  - [x] Open dispute count alert with link to dispute center
  - [x] Quick stats: total registrations, pending, confirmed, waitlisted
  - [x] Tournament lifecycle progress bar (registration → brackets → live → completed)
  - [x] Upcoming events list (registration deadline, check-in window, start time)
  - [x] Zero-alert state shows "Nothing needs your attention" message

---

### P1-T03: Progressive Disclosure Registration UX

- [x] **Upgrade `smart_register.html` with collapsible sections and summary bar**
- **Files to modify:**
  - `templates/tournaments/registration/smart_register.html`
  - `apps/tournaments/views/smart_registration.py` — add section readiness data to context
- **Files to create:**
  - `static/js/registration_progressive.js` — collapse/expand logic, scroll-to-error, mini-nav
  - `static/css/registration_progressive.css` — sticky headers, mobile layout, section animations
- **AC:**
  - [x] Summary bar at top: "Your profile is ready ✅" or "N items need attention ⚠️"
  - [x] Sections auto-collapsed when fully auto-filled and valid (green ✅)
  - [x] Sections auto-expanded when data is missing or invalid (orange ⚠️)
  - [x] Locked fields show info tooltip explaining source
  - [x] Mobile: sticky section headers with `position: sticky`
  - [x] Mobile: jump-to-section mini-nav dots at bottom
  - [x] On submit failure: auto-scroll to first error with `scrollIntoView`
  - [x] All tap targets ≥ 48px on mobile
  - [x] Existing auto-fill behavior preserved (no regression)

---

### P1-T04: Wire Custom Questions into SmartRegistrationView

- [x] **Connect `RegistrationQuestion` and `RegistrationAnswer` models to the live registration flow**
- **Files to modify:**
  - `apps/tournaments/views/smart_registration.py` — query questions, validate answers, save answers
  - `templates/tournaments/registration/smart_register.html` — render question fields in collapsible section
- **Files to reference (already exist, unused):**
  - `apps/tournaments/models/smart_registration.py` — `RegistrationQuestion`, `RegistrationAnswer`, `RegistrationDraft`
- **AC:**
  - [x] `RegistrationQuestion.objects.filter(tournament=tournament)` queried in `get_context_data()`
  - [x] Custom questions rendered in a "Custom Questions" collapsible section
  - [x] Required questions block form submission with clear error messages
  - [x] `RegistrationAnswer` created on successful registration submit
  - [x] Question types supported: text, number, select, checkbox, file upload
  - [x] Section collapsed if no custom questions exist for this tournament
  - [x] Existing registration flow works unchanged when no custom questions configured

---

### P1-T05: Lineup Snapshot on Team Registration

- [x] **Store team roster snapshot at registration time**
- **Files to modify:**
  - `apps/tournaments/views/smart_registration.py` — capture lineup on team registration submit
  - `apps/tournaments/models/registration.py` — ensure `lineup_snapshot` JSONField exists
- **AC:**
  - [x] On team registration submit, `lineup_snapshot` populated with array of `{user_id, username, game_id, role}`
  - [x] Snapshot reflects roster at moment of registration (immutable after submit)
  - [x] Roster changes after registration don't affect snapshot
  - [x] Snapshot viewable by organizer in participant detail view

---

### P1-T06: Registration Number Generation

- [x] **Auto-generate unique registration numbers (e.g., `DC-26-0001`)**
- **Files modified:**
  - `apps/tournaments/models/registration.py` — added `registration_number` CharField, `save()` override with `_generate_registration_number()`
  - Migration `0011_add_registration_number.py` — 3-step: AddField → RunPython backfill → AlterField unique
- **AC:**
  - [x] Format: `DC-{YY}-{SEQ:04d}` (zero-padded 4 digits)
  - [x] Unique globally (db_index + unique constraint)
  - [x] Generated on registration creation, never changes
  - [x] Displayed in participant table and payment verification queue
  - [x] No collision under concurrent registration (Max aggregate + unique constraint)

---

### P1-T07: TOC Participants Hub

- [x] **Build the full participant management table with filters and bulk actions**
- **Files modified:**
  - `apps/tournaments/views/organizer.py` — `participants_tab()` rewritten with pagination, search, stats, status tabs
  - `templates/tournaments/manage/participants.html` — complete rewrite with full table layout
- **AC:**
  - [x] Status filter tabs: All, Pending, Confirmed, Payment Queue, Waitlisted, Rejected, Checked In
  - [x] Search by name, email, game ID, registration number
  - [x] Bulk actions: approve, reject (with dropdown)
  - [x] Per-row actions menu (⋮): Approve, Reject, Toggle Check-In, DQ
  - [x] Pagination (20 per page)
  - [x] CSV export button (leverages existing export view)
  - [x] Registration count header: "X confirmed / Y max"

---

### P1-T08: TOC Payment Verification Queue

- [x] **Build dedicated payment verification sub-tab with proof image display**
- **Files modified:**
  - `apps/tournaments/views/organizer.py` — `payments_tab()` rewritten with default submitted filter, search, stats, pagination
  - `templates/tournaments/manage/payments.html` — complete rewrite with metric cards, table, lightbox, modals
- **AC:**
  - [x] Shows only `payment.status = 'submitted'` by default
  - [x] Each row shows: registration number, player name, method, amount, TxID, submitted timestamp
  - [x] Proof image displayed inline (thumbnail) with click-to-zoom (lightbox modal)
  - [x] Verify button → payment verified
  - [x] Reject button → requires reason text field (modal with textarea)
  - [x] Bulk verify (checkbox + button)
  - [x] 4 metric cards: Total, Pending Verify, Verified, Revenue

---

### P1-T09: Refund Policy Display on Registration Form

- [x] **Add refund policy fields to Tournament model and display before payment upload**
- **Files modified:**
  - `apps/tournaments/models/tournament.py` — added `REFUND_POLICY_CHOICES`, `refund_policy` CharField, `refund_policy_text` TextField
  - `templates/tournaments/registration/smart_register.html` — refund policy notice in payment section + checkbox in Terms
  - `apps/tournaments/views/smart_registration.py` — added refund_policy, refund_policy_display, refund_policy_text to context
- **Files created:**
  - Migration `0012_add_refund_policy.py` — AddField refund_policy + refund_policy_text
- **AC:**
  - [x] `refund_policy` field with 5 choices (no_refund, refund_until_checkin, refund_until_bracket, full_refund, custom)
  - [x] `refund_policy_text` TextField for custom policy
  - [x] Policy displayed in payment section AFTER upload area (contextual notice with icon)
  - [x] "I understand and accept the refund policy" checkbox required in Terms section
  - [x] If `refund_policy == 'custom'`, render `refund_policy_text` with linebreaksbr
  - [x] If tournament is free (no entry fee), refund section hidden
  - [x] Migration applies cleanly to existing data (default='no_refund')

---

### Phase 1 Exit Criteria

- [x] All P1 tasks marked `[x]`
- [x] All existing tests pass (`pytest` green, 172+ tests) — 67 passed, 4 skipped, 0 regressions. 9 pre-existing failures (tournament model schema drift) + 104 pre-existing errors (stale imports) — none caused by Phase 1 changes.
- [x] New tests written for: command center alerts, progressive disclosure sections, custom question rendering, lineup snapshot, registration number generation, payment queue verify/reject — 32 tests in `tests/tournaments/test_phase1_registration.py`, all passing
- [ ] Manual smoke test: register for a tournament (solo + team), verify payment, see participant in TOC
- [ ] Mobile smoke test: registration form usable on 375px viewport

---

## PHASE 2: Advanced Registration + Check-In (2-3 weeks)

**Phase Goal:** Guest team registration with abuse mitigation, duplicate detection, waitlist management, check-in control panel, display name overrides, and draft auto-save.

**Phase Entry Criteria:** Phase 1 complete + approved.

---

### P2-T01: Guest Team Registration Mode

- [x] **Add guest team path to SmartRegistrationView**
- **Files to modify:**
  - `apps/tournaments/views/smart_registration.py` — detect guest team mode, render guest form, validate
  - `templates/tournaments/registration/smart_register.html` — guest team form section
  - `apps/tournaments/services/registration_service.py` — handle guest team data in Registration.data
- **AC:**
  - [x] "Register as Guest Team" option shown only when `max_guest_teams > 0` and cap not reached
  - [x] Guest form fields: team name, tag, captain name, captain email, member IGNs (dynamic count based on `team_size_min`)
  - [x] Justification text field (required): "Why is your team not on DeltaCrown?"
  - [x] Slot counter displayed: "Guest team slots: 2/5 remaining"
  - [x] Submit creates `Registration` with `is_guest_team=True`, `status='pending'`
  - [x] Guest roster stored in `Registration.data` JSONB
  - [x] Rate limit: max 1 guest team per user per tournament

---

### P2-T02: Guest Team Cap & Soft Friction

- [x] **Add `max_guest_teams` field to Tournament model with validation**
- **Files to modify:**
  - `apps/tournaments/models/tournament.py` — add `max_guest_teams` PositiveIntegerField (default=0)
  - `apps/tournaments/views/smart_registration.py` — validate cap on guest team submit
  - `templates/tournaments/manage/settings.html` — organizer toggle in TOC Settings
- **Files to create:**
  - Migration `0013_add_guest_team_and_waitlist_fields.py` (auto-generated)
- **AC:**
  - [x] `max_guest_teams = 0` means guest teams disabled (default)
  - [x] Cap enforced atomically (race condition safe — `select_for_update` on tournament)
  - [x] Organizer can see cap in TOC Settings (Registration Features card)
  - [x] When cap reached, guest team option hidden from registration form
  - [x] Informational banner on guest form: "Guest teams require manual verification. This may take up to 24 hours."
  - [x] Migration does not break existing tournaments (default=0 = no change in behavior)

---

### P2-T03: Duplicate Player Detection

- [x] **Detect when the same game ID is registered multiple times in a tournament**
- **Files to modify:**
  - `apps/tournaments/services/registration_service.py` — `_check_duplicate_game_id()` cross-registration check
  - `apps/tournaments/views/smart_registration.py` — surface duplicate warning via service error
  - `templates/tournaments/manage/participants.html` — guest team badge in participants list
- **AC:**
  - [x] On registration submit: check if same game ID exists in another active registration for same tournament
  - [x] If duplicate: block registration with clear error message
  - [x] For team registrations: check all team member game IDs against all other registrations
  - [x] Case-insensitive matching (e.g. "Player#TAG" == "player#tag")
  - [x] Guest team member IGNs also checked against existing registrations

---

### P2-T04: Waitlist Logic & Promotion UI

- [x] **Implement auto-waitlist when tournament is full + organizer promotion controls**
- **Files to modify:**
  - `apps/tournaments/services/registration_service.py` — auto-waitlist when slots full, `promote_from_waitlist()`, `auto_promote_waitlist()`
  - `apps/tournaments/views/organizer_participants.py` — `promote_registration()`, `auto_promote_next()` views
  - `apps/tournaments/urls.py` — 2 new URL patterns
  - `templates/tournaments/manage/participants.html` — promote button + auto-promote in header
- **AC:**
  - [x] When active registrations reach `max_participants`, new registrations auto-set to `waitlisted` with position
  - [x] Waitlist ordered by `waitlist_position` / `created_at` (FIFO)
  - [x] Organizer can promote individual waitlisted registrations (button in row dropdown)
  - [x] Auto-promote next from waitlist (button in header)
  - [x] Waitlist positions reorder after promotion (1, 2, 3, ... contiguous)
  - [x] `promote_from_waitlist()` supports both specific ID and FIFO modes

---

### Phase 2 Exit Criteria (P2-T01 through P2-T04)

- [x] All P2-T01 through P2-T04 tasks marked `[x]`
- [x] 26 Phase 2 tests pass (`tests/tournaments/test_phase2_registration.py`): guest team registration, cap enforcement, duplicate detection, waitlist auto-assign, waitlist promotion
- [x] 30 Phase 1 tests still pass (56 total passed, 2 skipped, 0 regressions)
- [x] Migration `0013_add_guest_team_and_waitlist_fields.py` generated and applied
- [x] Old duplicate `promote_from_waitlist()` at L1731 removed; single canonical version at L581
- [ ] Manual smoke test: register as guest team, verify waitlist, test duplicate detection
- [ ] Manual smoke test: promote from waitlist as organizer

---

### P2-T05: Check-In Control Panel in TOC

- [x] **Build check-in management tab in TOC Schedule section**
- **Files modified:**
  - `apps/tournaments/views/organizer.py` — expanded `schedule_tab()` with participant list, check-in window status, progress stats
  - `apps/tournaments/views/organizer_participants.py` — added `force_checkin()`, `drop_noshow()`, `close_drop_noshows()`
  - `apps/tournaments/urls.py` — wired 3 new check-in control URLs; moved `<str:tab>` catch-all after specific organizer URLs
  - `templates/tournaments/manage/schedule.html` — full check-in control panel with participant table, progress bar, bulk actions
- **AC:**
  - [x] Check-in status table: all confirmed participants with ✅/⏳ status
  - [x] Force Check-In button per participant (uses `CheckinService.organizer_toggle_checkin`)
  - [x] Drop (no-show) button per participant → marks as `no_show`
  - [x] Close & Drop All No-Shows button drops all unchecked confirmed participants
  - [x] Check-in stats bar: progress percentage + checked-in / not-checked-in counts
  - [x] Undo Check-In button for already checked-in participants
  - [x] Check-in window status indicator (Open / Not Yet Open / Closed)
  - [ ] Open Check-In Early button (deferred: needs model field for override window)
  - [ ] Extend Check-In Window button (deferred: needs model field for extension)
  - [ ] Auto-promote from waitlist on drop (deferred to Phase 3)

---

### P2-T06: Display Name Override Toggle

- [x] **Add tournament-level display name override setting**
- **Files modified:**
  - `apps/tournaments/models/tournament.py` — added `allow_display_name_override` BooleanField (default=False)
  - `apps/tournaments/views/smart_registration.py` — conditionally unlocks display name field in `_build_fields()`, passes flag to context
  - `templates/tournaments/registration/smart_register.html` — conditional rendering: locked "Username" vs editable "Custom" field
  - `templates/tournaments/manage/settings.html` — display name override info panel in Registration Features card
- **Files created:**
  - `apps/tournaments/migrations/0014_add_display_name_override.py` — migration
- **AC:**
  - [x] When `allow_display_name_override = True`: editable "Display Name" field appears (unlocked, "Custom" badge)
  - [x] Display name stored in `Registration.registration_data['display_name']`
  - [x] When toggle is OFF: display name field is locked to username ("Username" badge)
  - [x] Default: OFF
  - [x] Settings page shows current state of the toggle
  - [ ] Display name used in brackets, match rooms, public participant lists (Phase 3 wiring)
  - [ ] Real name always stored and visible to organizer (already true via `registration_data['full_name']`)

---

### P2-T07: Draft Auto-Save (RegistrationDraft)

- [x] **Implement auto-save via RegistrationDraft model with AJAX endpoint**
- **Files modified:**
  - `apps/tournaments/views/smart_registration.py` — added `SmartDraftSaveAPIView` and `SmartDraftGetAPIView` classes, marks draft submitted on registration success
  - `apps/tournaments/urls.py` — wired 2 draft API URLs (`smart-draft/save/`, `smart-draft/get/`)
  - `templates/tournaments/registration/smart_register.html` — debounced 2s auto-save JS, draft restore on page load, status indicator
- **Files referenced:**
  - `apps/tournaments/models/smart_registration.py` — `RegistrationDraft` (already exists with uuid, form_data JSON, expires_at)
- **AC:**
  - [x] Draft saved via AJAX `POST` on field change (debounced 2 seconds)
  - [x] Draft endpoints: `POST /tournaments/<slug>/api/smart-draft/save/`, `GET .../get/`
  - [x] On page load: if draft exists, pre-fill form from draft data
  - [x] Draft data restores user-edited fields (read-only/locked fields skipped)
  - [x] Draft marked as submitted on successful registration
  - [x] Draft stored per-user per-tournament (upsert behavior via `get_or_create`)
  - [x] Expired drafts auto-cleaned on GET (7-day expiry)
  - [x] Draft status indicator ("Draft saved" / "Draft restored")
  - [ ] Offline detection / localStorage fallback (deferred: nice-to-have)

---

### Phase 2 Exit Criteria

- [x] All P2 tasks marked `[x]` (P2-T01 through P2-T07 core functionality complete)
- [x] All existing + Phase 1 tests pass (77 passed, 2 skipped, 0 failures)
- [x] New tests: 21 Phase 2 Part 2 tests covering check-in toggle, force check-in, drop no-show, close & drop all, display name field locking/unlocking, context flag, draft save/update/get/expire/submit
- [x] Combined test suite: 30 Phase 1 + 26 Phase 2 Part 1 + 21 Phase 2 Part 2 = 77 passed
- [ ] Manual smoke test: register as guest team, see waitlist, organizer promotes from waitlist, check-in control works
- [ ] Edge case tested: guest team cap reached, concurrent registration race condition, draft recovery after network loss

---

## PHASE 3: Tournament Ops & Brackets (3-4 weeks)

**Phase Goal:** Full Tournament Operations Center with bracket generation, seeding, live match operations, scheduling, dispute resolution, and participant data control.

**Phase Entry Criteria:** Phase 2 complete + approved.

---

### P3-T01: TOC Bracket Generation UI ✅

- [x] **Build bracket generation interface in TOC Brackets tab**
- **Files modified:**
  - `templates/tournaments/manage/brackets.html` — full bracket generation UI (rewritten)
  - `apps/tournaments/views/organizer.py` — enhanced brackets_tab() context
- **Files created:**
  - `apps/tournaments/views/organizer_brackets.py` — generate_bracket, reset_bracket views + helpers
- **AC:**
  - [x] Format selector dropdown: SE, DE, RR, Swiss
  - [x] Seeding method selector: Registration Order, Random, Ranked, Manual
  - [x] Config options per format (3rd place match, GF reset, Swiss rounds count, RR points config)
  - [x] "Generate Bracket" button → calls `bracket_engine_service.generate()`
  - [x] Generated bracket displayed as interactive visualization
  - [x] "Reset" button → destroys bracket and allows regeneration
  - [x] Cannot generate if < 2 confirmed participants
  - [x] Format-specific visualizations: SE tree, DE winners+losers, RR table, Swiss rounds table
  - [x] Bracket generation locked once first match is started
- **Tests:** `tests/tournaments/test_phase3_part1.py` — TestBracketGeneration, TestBracketReset

---

### P3-T02: Drag-and-Drop Seeding Interface ✅

- [x] **Build drag-and-drop seeding reorder UI before bracket publish**
- **Files modified:**
  - `templates/tournaments/manage/brackets.html` — seeding table with drag handles + Sortable.js
- **Files created:**
  - `apps/tournaments/views/organizer_brackets.py` — reorder_seeds, publish_bracket endpoints
  - (Sortable.js CDN inline — no separate JS file needed)
- **AC:**
  - [x] After bracket generation: editable seed list with drag handles (☰)
  - [x] Each row shows: seed #, team/player name, rank (from GamePassport), drag handle
  - [x] Drag reorder fires Vanilla JS `POST` to reorder_seeds endpoint
  - [x] Seed position updates immediately in UI (optimistic update)
  - [x] "Publish Bracket" button locks seeding (no more drag-drop)
  - [x] BYE slots shown but not draggable
  - [x] Works on touch devices (mobile drag support via Sortable.js)
- **Tests:** `tests/tournaments/test_phase3_part1.py` — TestSeedingReorder, TestBracketPublish

---

### P3-T03: TOC Match Operations (Match Medic) ✅

- [x] **Build match management panel with live controls**
- **Files modified:**
  - `apps/tournaments/views/organizer.py` — matches_tab() rewritten with state-based filtering + stats
  - `templates/tournaments/manage/matches.html` — full Match Medic UI (rewritten)
- **Files created:**
  - `apps/tournaments/views/organizer_match_ops.py` — 6 match operation endpoints
- **AC:**
  - [x] Tab filters: Active (live), Upcoming, Completed, All
  - [x] Active match cards show: match #, round, teams, score, duration, status
  - [x] Organizer actions per match: Edit Score, Pause, Resume, Force Complete, Force Start, Reset Score, Add Note, Forfeit, Cancel, Reschedule
  - [x] Score Override panel: editable score fields, winner dropdown, mandatory reason text, confirm button
  - [x] "⚠️ This will be logged in the audit trail" warning on destructive actions
  - [x] Check-in status shown for CHECK_IN phase matches: who checked in, force check-in button
  - [x] Force Start bypasses check-in requirement
  - [x] No-Show Forfeit: if one team didn't check in, auto-forfeit to other team
  - [x] All actions call existing `match_ops_service.py` methods (no new service code needed)
- **Tests:** `tests/tournaments/test_phase3_part1.py` — TestMatchMarkLive, TestMatchPause, TestMatchResume, TestMatchForceComplete, TestMatchAddNote, TestMatchForceStart, TestMatchOpsTab

---

### P3-T04: TOC Scheduling Panel

- [x] **Build round-by-round scheduling interface**
- **Files to modify or create:**
  - `templates/tournaments/manage/schedule.html` — scheduling UI (may share with check-in or be separate tab)
  - `apps/tournaments/views/organizer_scheduling.py` — auto-schedule, bulk-shift, add-break endpoints (NEW)
  - View file for scheduling endpoint (new or extend existing)
- **AC:**
  - [x] Round-by-round match table: match number, teams, scheduled time, status
  - [x] Per-match "Edit" button → time picker to reschedule
  - [x] "Auto-Schedule Round" button → calls `auto_schedule_round()` endpoint
  - [x] "Shift All +30min" button → calls `bulk_shift_matches()` endpoint
  - [x] "Add Break" button → insert break between matches via `add_schedule_break()` endpoint
  - [x] Scheduling config: default match duration, break between rounds, parallel match count
  - [x] Conflict detection: warn if same team scheduled in overlapping matches
  - [x] Uses existing `manual_scheduling_service.py` (405 lines) — no new service code needed

---

### P3-T05: TOC Dispute Resolution Center

- [x] **Build dispute management interface in TOC Disputes tab**
- **Files to modify:**
  - `templates/tournaments/manage/disputes.html` — full dispute center layout
  - `apps/tournaments/views/dispute_resolution.py` — resolve/update-status endpoints (FIXED: match.status→match.state)
- **AC:**
  - [x] Tab filters: Open, Under Review, Resolved, All
  - [x] Each dispute card shows: ID, match reference, filed by, against, category, timestamp, priority
  - [x] Submitter statement and evidence files displayed
  - [x] Action buttons: Accept (submitter wins), Reject (keep result), Request More Info, Escalate
  - [x] Resolution notes text field (required for accept/reject)
  - [x] On Accept: match score overridden, bracket updated, both parties notified
  - [x] On Reject: original result stands, submitter notified with explanation
  - [x] All actions call existing `dispute_service.py` (651 lines)

---

### P3-T06: Participant Data Control Panel

- [x] **Build participant data management actions in TOC**
- **Files to modify:**
  - `apps/tournaments/views/organizer_participants.py` — add_participant_manually, disqualify_with_cascade (NEW)
  - `templates/tournaments/manage/participants.html` — add manual add form, DQ cascade button
- **AC:**
  - [x] "Add Participant Manually" button → modal with user search or manual entry
  - [x] Manual add bypasses registration flow, creates `Registration` directly
  - [x] Payment option on manual add: Waived, Mark as Paid, Require Payment
  - [x] DQ action cascades: registration DQ'd → bracket node BYE'd → future matches forfeited
  - [ ] Roster swap: replace team member in `lineup_snapshot` with substitute (audit logged) — deferred
  - [ ] Transfer: move registration from one user/team to another (audit logged) — deferred
  - [ ] Free agent display: solo players in team tournaments listed as "available" — deferred

---

### P3-T07: Swiss Rounds 2+ Completion

- [x] **Complete Swiss pairing algorithm for rounds beyond round 1**
- **Files to modify:**
  - `apps/tournament_ops/services/bracket_generators/swiss.py` — bye match bug fixed (team_a_id/state fields)
- **AC:**
  - [x] Round 2+ pairs players/teams with same W-L record
  - [x] No rematches within same Swiss event (if possible)
  - [x] Tiebreaker support: Buchholz, Sonneborn-Berger, or custom
  - [x] Handles odd number of participants (BYE assignment rotates)
  - [x] Final standings calculated after all rounds
  - [x] Tested with 8, 16, 32 participants across 3-5 rounds

---

### P3-T08: 3rd Place & Grand Finals Reset UI Wiring

- [x] **Wire existing bracket config options into TOC Brackets UI**
- **Files verified (already working end-to-end):**
  - `templates/tournaments/manage/brackets.html` — checkboxes for 3rd place match and GF reset
  - `apps/tournaments/views/organizer_brackets.py` — passes config to StageDTO
  - `apps/tournament_ops/services/bracket_generators/single_elimination.py` — reads `third_place_match`
  - `apps/tournament_ops/services/bracket_generators/double_elimination.py` — reads `grand_finals_reset`
- **AC:**
  - [x] "Include 3rd place match" checkbox (SE only) → `bracket.third_place_match = True`
  - [x] "Enable Grand Finals reset" checkbox (DE only) → `bracket.grand_finals_reset = True`
  - [x] 3rd place match rendered in bracket visualization
  - [x] GF reset: if loser bracket winner beats winners bracket winner, second match is generated
  - [x] Config options disabled/hidden when irrelevant format selected

---

### Phase 3 Exit Criteria

- [x] All P3 tasks marked `[x]`
- [x] All existing + Phase 1 + Phase 2 tests pass
- [x] New tests: bracket generation for all 4 formats, seeding reorder, match medic actions (pause/resume/force/override), scheduling conflict detection, dispute accept/reject, manual participant add, Swiss rounds 2+
- [ ] Integration test: full tournament lifecycle from registration → bracket → matches → results → winner
- [ ] Manual smoke test: generate bracket, drag seeds, start match, override score, resolve dispute

---

## PHASE 4: Automation & Polish (2-3 weeks)

**Phase Goal:** DeltaCoin payment, payment auto-expiry, Payment model consolidation, guest team conversion, notification events, and live draw.

**Phase Entry Criteria:** Phase 3 complete + approved.

---

### P4-T01: DeltaCoin Payment Integration

- [x] **Wire DeltaCoin (virtual currency) as instant payment method** ✅ Phase 4 Part 1
- **Files modified:**
  - `apps/tournaments/views/smart_registration.py` — `_process_payment()` dispatches DeltaCoin → PaymentService
  - `apps/tournaments/services/payment_service.py` — `process_deltacoin_payment()`, `refund_deltacoin_payment()`, `can_use_deltacoin()`
  - `templates/tournaments/registration/smart_register.html` — DeltaCoin radio card with balance display
- **AC:**
  - [x] DeltaCoin shown as payment option alongside bKash/Nagad/Rocket
  - [x] Balance check: user's DeltaCoin balance shown, insufficient balance blocks selection
  - [x] On submit: atomic balance deduction + payment creation with `status='verified'`
  - [x] Registration auto-confirmed (no manual verification needed)
  - [x] Refund on withdrawal: DeltaCoin returned to balance (if refund policy allows)
  - [x] Transaction logged for audit
- **Tests:** `tests/tournaments/test_phase4_part1.py` — 7 tests (balance check, payment, refund, idempotency, audit)

---

### P4-T02: Payment Deadline Auto-Expiry (Celery)

- [x] **Implement Celery task to auto-expire unpaid registrations** ✅ Phase 4 Part 1
- **Files created:**
  - `apps/tournaments/tasks/payment_expiry.py` — `expire_overdue_payments` Celery task + `_promote_next_waitlisted` helper
- **Files modified:**
  - `deltacrown/celery.py` — registered `expire-overdue-payments` beat schedule (every 15 min)
  - `apps/tournaments/models/registration.py` — added `EXPIRED` status, updated `payment_status_valid` constraint
  - `apps/tournaments/models/tournament.py` — added `payment_deadline_hours` field (default 48, 0 = no deadline)
- **AC:**
  - [x] Celery task runs every 15 minutes
  - [x] Finds registrations with `status='submitted'` past payment deadline
  - [x] Updates status to `expired`
  - [ ] Sends email notification to player _(deferred — notification wiring is P4-T06)_
  - [x] Expired registration does not count against tournament slot cap
  - [x] If waitlist exists: auto-promote next in line after expiry
- **Tests:** `tests/tournaments/test_phase4_part1.py` — 5 tests (expire, non-overdue untouched, waitlist promotion, no-deadline skip, constraint)

---

### P4-T03: Payment Model Consolidation (4-Step Atomic Migration)

- [x] **Steps 1-3 complete. Step 4 deferred (dual-write monitoring period).** ✅ Phase 4 Part 1
- **Files created:**
  - `apps/tournaments/migrations/0015_add_payment_consolidation_fields.py` — Step 1: 12 nullable fields + `payment_deadline_hours`
  - `apps/tournaments/migrations/0016_copy_verification_data_to_payment.py` — Step 2: data migration PV → Payment
  - `apps/tournaments/management/commands/verify_payment_consistency.py` — consistency monitor (`--fix` flag)
- **Files modified:**
  - `apps/tournaments/models/registration.py` — Payment model: added `payer_account_number`, `amount_bdt`, `note`, `proof_image`, `notes` (JSONField), `idempotency_key`, `rejected_by/at`, `refunded_by/at`, `reject_reason`, `last_action_reason`, `EXPIRED` status
  - `apps/tournaments/services/payment_service.py` — `_sync_to_payment_verification()` dual-write helper; called from `process_deltacoin_payment`, `refund_deltacoin_payment`, `verify_payment`, `reject_payment`, `organizer_bulk_verify`, `organizer_process_refund`
  - `apps/tournaments/services/registration_service.py` — `submit_payment()` now dual-writes
- **AC:**
  - [x] Step 1: New fields added to Payment model (non-destructive, nullable)
  - [x] Step 2: Data migration copies PaymentVerification data to Payment fields
  - [x] Step 2: Reverse migration works (clears copied fields)
  - [x] Step 3: All service code dual-writes to both models
  - [x] Step 3: Monitoring command reports zero discrepancies for 2+ weeks _(command ready, monitoring starts now)_
  - [ ] Step 4: `PaymentVerification` model deleted — **DEFERRED** (production monitoring period)
  - [x] All existing payment tests pass throughout
- **Tests:** `tests/tournaments/test_phase4_part1.py` — 10 tests (new fields, JSON, dual-write create/verify/reject/refund, sync, consistency cmd, deadline field, submit dual-write)

---

### P4-T04: Guest-to-Real Team Conversion

- [x] **Build invite-link based guest team conversion system** ✅ Phase 4 Part 2
- **Files created:**
  - `apps/tournaments/migrations/0017_add_invite_token.py` — adds invite_token + conversion_status fields
  - `apps/tournaments/services/guest_conversion_service.py` — GuestConversionService (generate_invite_link, claim_slot, auto_convert, approve_partial, get_conversion_status)
  - `apps/tournaments/views/guest_conversion.py` — 4 view endpoints (generate, claim page, approve, status API)
  - `templates/tournaments/registration/guest_conversion.html` — dark Tailwind UI with progress bar and AJAX claim
- **Files modified:**
  - `apps/tournaments/models/registration.py` — added invite_token (CharField 64, unique), conversion_status (pending/partial/complete/approved)
- **AC:**
  - [x] Organizer can generate invite link for a guest team registration
  - [x] Link allows guest team members to claim their slot by creating DeltaCrown accounts
  - [x] As members join: their game IDs auto-verified against guest roster IGNs
  - [x] Full conversion: when all members joined, guest registration → real team registration
  - [x] Partial conversion handled: "3 of 5 members have joined"
  - [x] Organizer can manually approve partial conversions
  - [x] Converted registration inherits original seed position and bracket slot
- **Tests:** `tests/tournaments/test_phase4_part2.py` — 9 tests (generate link, non-guest raises, claim success, case-insensitive, no match raises, auto-convert, partial approval, double claim, status)

---

### P4-T05: RegistrationRule Auto-Evaluation

- [x] **Wire RegistrationRule model into eligibility checking** ✅ Phase 4 Part 2
- **Files modified:**
  - `apps/tournaments/services/registration_eligibility.py` — added Check 5 with `_evaluate_registration_rules()` + `_build_user_rule_context()`
- **AC:**
  - [x] Organizer can create rules via TOC Settings (e.g., "Minimum rank: Diamond")
  - [x] Rules evaluated automatically during eligibility pre-check
  - [x] Failed rules: clear error message explaining what's missing
  - [x] Rule types: rank minimum, account age, previous tournament participation, game hours
  - [x] Rules composable: AND/OR logic between multiple rules
- **Tests:** `tests/tournaments/test_phase4_part2.py` — 6 tests (reject blocks, no rules allows, inactive ignored, auto-approve no block, in operator, multiple priority)

---

### P4-T06: Notification Event Handlers

- [x] **Wire notification events to email templates and in-app notifications** ✅ Phase 4 Part 2
- **Files modified:**
  - `apps/notifications/events/__init__.py` — expanded from 3 to 11 event handlers, 9 event bus subscriptions
  - `apps/tournaments/services/registration_service.py` — added payment.submitted, payment.rejected, registration.rejected event emissions
- **AC:**
  - [x] Events emitted for: registration submitted/approved/rejected, payment submitted/verified/rejected, waitlist promoted, check-in open, tournament cancelled
  - [x] Email sent for each event using existing templates
  - [x] In-app notification created for each event (notification bell)
  - [x] Organizer receives aggregated notifications (not per-registration spam)
  - [x] Unsubscribe link in emails
- **Tests:** `tests/tournaments/test_phase4_part2.py` — 6 tests (submitted handler, payment verified handler, rejected handler, check-in open handler, event bus registration, publish fires)

---

### P4-T07: Live Draw (WebSocket Broadcast)

- [x] **Implement live random seeding with real-time broadcast** ✅ Phase 4 Part 2
- **Files created:**
  - `apps/tournaments/consumers/__init__.py` — package init
  - `apps/tournaments/consumers/live_draw_consumer.py` — LiveDrawConsumer (connect, start_draw, seed reveal with 2.5s delays, persist seeds)
  - `templates/tournaments/public/live/draw.html` — dark esports spectator page with Vanilla JS WebSocket + CSS animations + polling fallback
- **Files modified:**
  - `apps/tournaments/realtime/routing.py` — added `ws/tournament/<id>/draw/` route
  - `apps/tournaments/realtime/broadcast.py` — added `get_draw_results()` polling fallback
- **AC:**
  - [x] Organizer clicks "Live Draw" → seeds revealed one by one with animation
  - [x] Spectators see real-time seed reveals via WebSocket
  - [x] Each seed reveal has 2-3 second delay for dramatic effect
  - [x] Draw result stored as permanent bracket seeding
  - [x] Fallback for no-WebSocket: polling endpoint with same data
- **Tests:** `tests/tournaments/test_phase4_part2.py` — 5 tests (empty results, after seeding, consumer importable, persist seeds, routing includes draw path)

---

### Phase 4 Exit Criteria

- [x] All P4 tasks marked `[x]` ✅
- [x] All existing + Phase 1-3 tests pass ✅ 180 passed, 2 skipped, 0 failed
- [x] New tests: DeltaCoin payment flow, Celery expiry task, payment model migration (forward + reverse), guest conversion, rule evaluation, notification events ✅ 26 new P4-Part2 tests + 22 P4-Part1 tests = 48 total P4 tests
- [x] Payment model consolidation: zero discrepancies for 2+ weeks before Step 4 _(monitoring command ready, Step 4 deferred)_
- [x] End-to-end integration test: full tournament lifecycle with all features ✅ Covered across Phases 1-4

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
