# Sprint 5: Tournament Check-In & Registration Validation Subsystem - Planning Document

**Sprint ID**: Sprint 5  
**Feature IDs**: FE-T-007 (Tournament Lobby), FE-T-003 (Registration Validation Enhancement)  
**Date**: November 16, 2025  
**Status**: Planning Complete  
**Target**: Full macro implementation (check-in + registration validation)

---

## Executive Summary

Sprint 5 implements the **Tournament Check-In & Registration Validation Subsystem**, combining two critical pre-tournament features:

1. **Check-In System** (FE-T-007): Tournament lobby/participant hub where registered players check in before tournament starts
2. **Registration Validation Enhancement** (FE-T-003): Enhanced validation states for registration entry points, including payment status, approval workflows, and eligibility checks

**Key Outcomes**:
- Registered participants can check in during designated window before tournament starts
- Check-in status tracked per participant, visible to all (roster transparency)
- Registration CTAs display accurate validation states (payment pending, approval required, etc.)
- No-show participants automatically disqualified if not checked in
- Mobile-optimized check-in flow with countdown timers and real-time status updates

---

## Feature IDs from Backlog

### Primary Features

**FE-T-007**: Tournament Lobby / Participant Hub
- **Priority**: P0 (critical for tournament flow)
- **Backend Status**: Pending (requires lobby API implementation)
- **Description**: Central hub for registered participants during registration-closed → tournament-complete phases
- **User Stories**:
  - As a registered participant, I want a dedicated lobby page to see tournament info and check in
  - As a participant, I want to check in before the tournament begins (required to avoid disqualification)
  - As a participant, I want to see the full roster of other participants with check-in status
  - As a participant, I want to see match schedule once brackets are generated
  - As a participant, I want to receive organizer announcements
  
**FE-T-003**: Registration Entry Point & States (Enhancement)
- **Priority**: P0 (critical for accurate user guidance)
- **Backend Status**: ✓ Complete (registration_service.py with team permissions)
- **Description**: Enhanced registration CTA states including validation workflows
- **User Stories**:
  - As a player, I want to see if registration requires payment and my payment status
  - As a player, I want to know if my registration requires organizer approval (pending validation)
  - As a player, I want clear messaging when I'm not eligible (banned, region-locked, etc.)

### Supporting Features

**Backend Dependencies**:
- Check-in service (Module 4.3 - to be created)
- Registration validation service (Module 4.1 - enhance existing)
- Lobby API with participant-only access control

---

## URL Map from Sitemap

### Check-In URLs

| URL | Method | Persona | Auth | Purpose |
|-----|--------|---------|------|---------|
| `/tournaments/<slug>/lobby/` | GET | Player (participant) | **Required** (participant only) | Tournament lobby/hub page |
| `/tournaments/<slug>/check-in/` | POST | Player (participant) | **Required** | Check-in action endpoint |
| `/tournaments/<slug>/check-in/complete/` | GET | Player (participant) | **Required** | Check-in confirmation page (optional) |

### Registration Validation URLs (Enhanced)

| URL | Method | Persona | Auth | Purpose |
|-----|--------|---------|------|---------|
| `/tournaments/<slug>/` | GET | Public | Optional | Tournament detail page (shows registration CTA with validation states) |
| `/tournaments/<slug>/register/` | GET | Player | **Required** | Registration wizard (blocked if validation fails) |

**Notes**:
- Check-in POST endpoint returns success/error (no separate page, handled in lobby)
- Optional `/check-in/complete/` page can be used for success message, or handle in lobby with toast
- All URLs match FRONTEND_TOURNAMENT_SITEMAP.md

---

## Template Map from File Structure

### Check-In Templates

```
templates/tournaments/lobby/
├── index.html                     # Main lobby page (FE-T-007)
├── _checkin.html                  # Check-in widget (button + status + countdown)
├── _roster.html                   # Participant roster with check-in status
├── _schedule.html                 # Match schedule widget (post-bracket)
├── _announcements.html            # Organizer announcements panel
└── _communication.html            # Optional: Q&A or chat (P2, defer)
```

**Partials**:
- `_checkin.html`: Check-in button, countdown timer, status indicator
- `_roster.html`: List of all participants with check-in checkmarks
- `_schedule.html`: "Your Next Match" card + match history
- `_announcements.html`: Chronological announcement feed

### Registration Validation Templates (Enhanced)

```
templates/tournaments/detail/
├── overview.html                  # Tournament detail page (FE-T-002/003)
├── _cta_card.html                 # Registration CTA card (ENHANCED with validation states)
└── _validation_messages.html      # NEW: Validation error/warning messages
```

**Enhanced States in `_cta_card.html`**:
1. Registration Open (eligible): "Register Now" button (green)
2. Registration Open (payment required): "Register Now" + "Entry Fee: ৳500"
3. Registration Pending Payment: "Payment Pending" (amber, show payment link)
4. Registration Pending Approval: "Awaiting Organizer Approval" (amber)
5. Registration Rejected: "Registration Rejected - [reason]" (red)
6. Not Eligible: "You're not eligible - [reason]" (gray)
7. Already Registered & Checked In: "You're Checked In ✓" (green)
8. Already Registered & Not Checked In: "Check In Now" button (amber, urgent)
9. Tournament Full: "Tournament Full" (gray)
10. Registration Closed: "Registration Closed" (gray)

---

## State Machine for Check-In

### Check-In States (Per Participant)

```
NOT_ELIGIBLE (before registration)
    ↓
REGISTERED (after successful registration)
    ↓
CHECK_IN_WINDOW_NOT_OPEN (waiting for check-in window)
    ↓
CHECK_IN_AVAILABLE (check-in window open)
    ↓ (user action: click "Check In")
CHECKED_IN (confirmed participation)
    OR
NOT_CHECKED_IN (if check-in window closes without action)
    ↓
DISQUALIFIED (no-show, removed from tournament)
```

### State Transitions

| Current State | User Action | Next State | Backend Effect |
|---------------|-------------|------------|----------------|
| REGISTERED | Wait | CHECK_IN_WINDOW_NOT_OPEN | None (auto-transition based on time) |
| CHECK_IN_WINDOW_NOT_OPEN | Wait | CHECK_IN_AVAILABLE | Backend opens check-in (scheduled) |
| CHECK_IN_AVAILABLE | Click "Check In" | CHECKED_IN | `POST /api/tournaments/<slug>/check-in/` |
| CHECK_IN_AVAILABLE | Do nothing | NOT_CHECKED_IN | Auto-transition when check-in window closes |
| NOT_CHECKED_IN | None | DISQUALIFIED | Backend marks as disqualified |

### Check-In Window Timing

**Configuration** (per tournament, set by organizer):
- `check_in_minutes_before` (default: 60 minutes before tournament start)
- `check_in_deadline` (default: 10 minutes before tournament start)

**Example**:
- Tournament starts: 2025-11-20 18:00
- Check-in opens: 2025-11-20 17:00 (60 min before)
- Check-in closes: 2025-11-20 17:50 (10 min before)

**Backend Enforcement**:
- Check-in endpoint validates: `check_in_open <= now < check_in_close`
- Returns 403 if outside check-in window

---

## Registration Validation Rules

### Validation Checks (Backend → Frontend Mapping)

| Validation Check | Backend Field | Frontend State | CTA Display |
|------------------|---------------|----------------|-------------|
| **Eligibility** | `can_register: bool` | ELIGIBLE / NOT_ELIGIBLE | "Register Now" / "Not Eligible" |
| **Payment Required** | `has_entry_fee: bool` | PAYMENT_REQUIRED | "Register Now - ৳500" |
| **Payment Status** | `payment_status: enum` | PAID / PENDING / FAILED | "Complete Payment" button |
| **Approval Required** | `requires_approval: bool` | PENDING_APPROVAL | "Awaiting Approval" (amber) |
| **Registration Status** | `registration.state: enum` | CONFIRMED / REJECTED / CANCELLED | "You're Registered" / "Rejected" |
| **Check-In Status** | `check_in_status: enum` | CHECKED_IN / NOT_CHECKED_IN | "Checked In ✓" / "Check In Now" |
| **Tournament Capacity** | `slots_filled >= max_participants` | FULL | "Tournament Full" (disabled) |
| **Registration Window** | `now < registration_end` | OPEN / CLOSED | "Register" / "Closed" |

### Backend API Response (Enhanced)

**Endpoint**: `GET /api/tournaments/<slug>/registration-status/`

**Response** (JSON):
```json
{
  "can_register": false,
  "is_registered": true,
  "registration_state": "confirmed",
  "check_in_status": "not_checked_in",
  "payment_required": true,
  "payment_status": "paid",
  "requires_approval": false,
  "rejection_reason": null,
  "check_in_window": {
    "opens_at": "2025-11-20T17:00:00Z",
    "closes_at": "2025-11-20T17:50:00Z",
    "is_open": false,
    "time_until_opens": 3600  // seconds
  },
  "state": "check_in_pending",
  "reason": "Check in before tournament starts"
}
```

**State Enum Values**:
- `not_registered` - User is not registered
- `registration_open` - Can register now
- `registration_closed` - Registration window closed
- `tournament_full` - No slots available
- `not_eligible` - User doesn't meet requirements
- `payment_pending` - Registration submitted, payment incomplete
- `pending_approval` - Registration submitted, awaiting organizer approval
- `confirmed` - Registration confirmed, awaiting check-in
- `check_in_pending` - Check-in window open, user must check in
- `checked_in` - User successfully checked in
- `disqualified` - User missed check-in, removed from tournament
- `rejected` - Registration rejected by organizer

---

## Edge Cases

### Check-In Edge Cases

1. **Early Check-In Attempt**
   - **Scenario**: User tries to check in before window opens
   - **Backend**: Returns 403 "Check-in not yet open"
   - **Frontend**: Disable button, show countdown "Check-in opens in X hours"

2. **Late Check-In Attempt**
   - **Scenario**: User tries to check in after window closes
   - **Backend**: Returns 403 "Check-in window closed"
   - **Frontend**: Show "Check-in closed - You're disqualified" message

3. **Duplicate Check-In**
   - **Scenario**: User already checked in, tries again
   - **Backend**: Returns 200 with message "Already checked in"
   - **Frontend**: Show "You're already checked in ✓" (no error)

4. **Network Failure During Check-In**
   - **Scenario**: POST request fails due to network issue
   - **Frontend**: Retry logic (3 attempts), show error toast, allow manual retry button

5. **Check-In Button Mashing**
   - **Scenario**: User clicks "Check In" multiple times rapidly
   - **Frontend**: Disable button immediately on first click, show loading spinner
   - **Backend**: Idempotent endpoint (returns same result for duplicate requests)

6. **Browser Refresh During Check-In**
   - **Scenario**: User refreshes page while check-in request in progress
   - **Frontend**: Check-in status on page load (re-fetch from API), show correct state

7. **Check-In Window Extended by Organizer**
   - **Scenario**: Organizer extends check-in deadline mid-window
   - **Backend**: Update `check_in_closes_at` timestamp
   - **Frontend**: Real-time countdown update via polling (HTMX every 30s)

### Registration Validation Edge Cases

1. **Payment Gateway Failure**
   - **Scenario**: User registers, payment gateway fails/times out
   - **Backend**: Registration created with `payment_status: pending`
   - **Frontend**: Show "Payment Pending - Complete payment" button, link to retry

2. **Organizer Approval Delay**
   - **Scenario**: Manual approval enabled, organizer takes 24+ hours
   - **Backend**: Registration remains `pending_approval`
   - **Frontend**: Show "Awaiting approval" with "Contact organizer" link

3. **Rejection After Registration**
   - **Scenario**: Organizer rejects registration after initial approval
   - **Backend**: Registration state changes to `rejected`, reason provided
   - **Frontend**: Show "Registration Rejected - [reason]" (email notification sent)

4. **Capacity Fills During Registration**
   - **Scenario**: User starts registration, tournament fills before submit
   - **Backend**: Returns 409 "Tournament full" on final submit
   - **Frontend**: Show error modal, offer waitlist option (P2)

5. **Team Permission Revoked Mid-Registration**
   - **Scenario**: User selects team, team owner revokes permission during wizard
   - **Backend**: Final submit validates permission, returns 403 if revoked
   - **Frontend**: Show "Team permission revoked - Select another team or contact team owner"

6. **Registration Window Closes During Wizard**
   - **Scenario**: User in step 3 of wizard, registration closes
   - **Backend**: Returns 409 "Registration closed" on submit
   - **Frontend**: Show error modal, lock form, "Registration period ended"

---

## Mobile + Accessibility Rules

### Mobile Optimization (360px - 428px width)

**Tournament Lobby**:
- Single-column layout
- Check-in button: Full-width, sticky at top (if not checked in)
- Roster: Card view (not table), scrollable
- Schedule: Collapse by default, expand on tap
- Announcements: Collapsible accordion

**Registration CTA**:
- CTA button: Full-width on mobile
- Validation messages: Stack above button, icon + text
- Countdown timer: Large, prominent display
- Payment info: Separate card, not inline

### Accessibility (WCAG 2.1 AA)

**Check-In Button**:
- `role="button"`
- `aria-label="Check in for tournament"`
- `aria-disabled="true"` (if outside window)
- `tabindex="0"` (keyboard accessible)
- Focus indicator: 2px solid border
- Space/Enter key activates

**Countdown Timer**:
- `aria-live="polite"` (updates announced to screen readers)
- `aria-atomic="true"` (entire timer announced, not just changed number)
- Visual + text format: "Check-in opens in 1 hour 23 minutes"

**Roster List**:
- `role="list"` and `role="listitem"` (semantic structure)
- Check-in status: ✓ icon + text "Checked In" (not icon alone)
- Search input: `aria-label="Search participants"`

**Validation Messages**:
- `role="alert"` (for errors)
- `aria-live="assertive"` (critical errors announced immediately)
- Color + icon + text (not color alone)
- Example: 🔴 "Registration rejected - [reason]" (red text + icon)

**Keyboard Navigation**:
- Tab order: Check-in button → Roster search → Roster items → Schedule → Announcements
- Escape key closes modals
- Arrow keys navigate roster list (optional enhancement)

---

## Integration Requirements

### Existing Services

**RegistrationService** (`apps/tournaments/services/registration_service.py`):
- Already handles team permission validation (✓ Complete)
- **Enhance** with check-in status tracking:
  - Add `check_in_status` field to Registration model (if not exists)
  - Add `get_check_in_status(registration_id)` method
  - Add `perform_check_in(registration_id, user_id)` method

**NEW: CheckInService** (to be created):
- `can_check_in(tournament, user)` - Validate check-in eligibility
- `check_in(tournament, user)` - Perform check-in action
- `get_roster(tournament)` - Get all participants with check-in status
- `is_check_in_window_open(tournament)` - Check if check-in available now

### Database Schema Changes (Backend)

**Tournament Model** (enhance):
```python
class Tournament(models.Model):
    # Existing fields...
    check_in_minutes_before = models.IntegerField(default=60)  # Minutes before start
    check_in_closes_minutes_before = models.IntegerField(default=10)  # Deadline
    
    @property
    def check_in_opens_at(self):
        return self.tournament_start - timedelta(minutes=self.check_in_minutes_before)
    
    @property
    def check_in_closes_at(self):
        return self.tournament_start - timedelta(minutes=self.check_in_closes_minutes_before)
    
    @property
    def is_check_in_open(self):
        now = timezone.now()
        return self.check_in_opens_at <= now < self.check_in_closes_at
```

**Registration Model** (enhance):
```python
class Registration(models.Model):
    # Existing fields...
    check_in_status = models.CharField(
        max_length=20,
        choices=[
            ('not_required', 'Check-in Not Required'),
            ('pending', 'Awaiting Check-In'),
            ('checked_in', 'Checked In'),
            ('no_show', 'No Show'),
        ],
        default='not_required'
    )
    checked_in_at = models.DateTimeField(null=True, blank=True)
    
    state = models.CharField(
        max_length=20,
        choices=[
            ('pending_payment', 'Pending Payment'),
            ('pending_approval', 'Pending Approval'),
            ('confirmed', 'Confirmed'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
            ('disqualified', 'Disqualified'),
        ],
        default='confirmed'  # If no payment/approval needed
    )
    rejection_reason = models.TextField(blank=True)
```

### API Endpoints (Backend to Implement)

**Check-In Endpoints**:
```
POST /api/tournaments/<slug>/check-in/
  - Auth: Required (must be registered participant)
  - Body: { confirm: true }
  - Response: { success: true, checked_in_at: "2025-11-20T17:05:00Z" }
  - Errors: 403 if outside window, 404 if not registered

GET /api/tournaments/<slug>/lobby/
  - Auth: Required (participant-only)
  - Response: {
      tournament: {...},
      check_in_window: { opens_at, closes_at, is_open },
      user_check_in_status: "checked_in",
      roster: [ { user, check_in_status, checked_in_at }, ... ],
      announcements: [ ... ],
      next_match: { ... } (if bracket generated)
    }
  - Errors: 403 if not registered participant

GET /api/tournaments/<slug>/roster/
  - Auth: Optional (public or participant)
  - Response: { participants: [ { name, avatar, check_in_status }, ... ] }
  - Note: Public can see roster, but not check-in button
```

**Registration Validation Endpoints** (enhance existing):
```
GET /api/tournaments/<slug>/registration-status/
  - Auth: Optional (show public info if not logged in)
  - Response: (see "Backend API Response" section above)
  - Enhancements:
    - Add check_in_status field
    - Add check_in_window object
    - Add state field (enum for CTA display)
```

---

## Architecture Summary

### Component Hierarchy

```
TournamentDetailPage (FE-T-002)
  └── RegistrationCTACard (FE-T-003 - Enhanced)
      ├── ValidationMessage (error/warning)
      ├── PaymentStatusPill
      ├── CountdownTimer (if applicable)
      └── CTAButton (state-driven)

TournamentLobbyPage (FE-T-007)
  ├── LobbyHero (tournament info)
  ├── CheckInWidget
  │   ├── CountdownTimer (check-in window)
  │   ├── CheckInButton (state-driven)
  │   └── StatusIndicator (checked in / pending)
  ├── ParticipantRoster
  │   ├── SearchInput
  │   ├── RosterList (virtualized for large tournaments)
  │   └── CheckInStatusIcon (per participant)
  ├── MatchScheduleWidget (post-bracket)
  │   ├── NextMatchCard
  │   └── MatchHistoryAccordion
  └── AnnouncementsPanel
      └── AnnouncementFeed (chronological)
```

### State Management

**Check-In State** (per participant):
- Stored in backend: `Registration.check_in_status`
- Fetched on page load: `GET /api/tournaments/<slug>/lobby/`
- Updated via: `POST /api/tournaments/<slug>/check-in/`
- Real-time sync: HTMX polling every 30s (roster updates)

**Registration Validation State**:
- Fetched on detail page load: `GET /api/tournaments/<slug>/registration-status/`
- Cached in frontend for 60s (avoid excessive API calls)
- Re-fetched on user action (e.g., after payment, after registration)

**No Frontend State Library** (use Django context + HTMX):
- Server-driven UI: Backend sends HTML fragments via HTMX
- Minimal JS: Only for countdown timers, button disable logic

---

## Real-Time Updates

### HTMX Polling Strategy

**Tournament Lobby**:
- **Roster**: Poll every 30s
  - `hx-get="/api/tournaments/<slug>/lobby/roster/"`
  - `hx-trigger="every 30s"`
  - `hx-target="#roster-list"`
  - Swap strategy: `innerHTML` (replace entire list)

- **Announcements**: Poll every 60s
  - `hx-get="/api/tournaments/<slug>/lobby/announcements/"`
  - `hx-trigger="every 60s"`
  - `hx-target="#announcements-feed"`
  - Swap strategy: `outerHTML` (highlight new announcements)

- **Check-In Status**: Poll every 10s (if not checked in)
  - `hx-get="/api/tournaments/<slug>/check-in-status/"`
  - `hx-trigger="every 10s"`
  - `hx-target="#checkin-widget"`
  - Stop polling after checked in

**Registration CTA**:
- **Payment Status**: No polling (user must manually refresh or click "Check Payment Status")
- **Approval Status**: No polling (rely on email notification)

### WebSocket Alternative (P2 Enhancement)

**Lobby WebSocket** (optional, defer if time-constrained):
- Channel: `/ws/tournaments/<slug>/lobby/`
- Events:
  - `participant_checked_in` - Broadcast when any participant checks in
  - `announcement_posted` - Real-time announcement push
  - `check_in_window_opened` - Notify when check-in becomes available
  - `check_in_window_closing` - Warning 5 min before deadline

**Frontend Handling**:
- WebSocket preferred if available, fall back to HTMX polling
- Toast notification on events (e.g., "10 participants checked in!")

---

## Sequence Diagrams

### Check-In Flow (Happy Path)

```
Participant → Frontend → Backend → Database

1. User visits /tournaments/<slug>/lobby/
   Frontend → Backend: GET /api/tournaments/<slug>/lobby/
   Backend → Database: Fetch tournament, registration, roster
   Backend → Frontend: { check_in_window: { is_open: false, opens_in: 3600 }, ... }
   Frontend: Display "Check-in opens in 1 hour" + countdown timer

2. Check-in window opens (scheduled, backend auto-transition)
   Backend: check_in_window.is_open = true (time-based)
   Frontend (polling): GET /api/tournaments/<slug>/lobby/ (every 30s)
   Backend → Frontend: { check_in_window: { is_open: true }, ... }
   Frontend: Enable "Check In Now" button (green, urgent)

3. User clicks "Check In Now"
   Frontend: Disable button, show loading spinner
   Frontend → Backend: POST /api/tournaments/<slug>/check-in/ { confirm: true }
   Backend → Database: Update registration.check_in_status = 'checked_in'
   Backend → Frontend: { success: true, checked_in_at: "2025-11-20T17:05:00Z" }
   Frontend: Show "You're Checked In ✓" (green checkmark), hide button

4. Frontend updates roster in real-time
   Frontend (polling): GET /api/tournaments/<slug>/roster/ (every 30s)
   Backend → Frontend: { participants: [ { name: "Player1", check_in_status: "checked_in" }, ... ] }
   Frontend: Display green checkmark next to participant's name in roster
```

### Registration Validation Flow (Payment Required)

```
User → Frontend → Backend → Payment Gateway

1. User visits /tournaments/<slug>/ (detail page)
   Frontend → Backend: GET /api/tournaments/<slug>/registration-status/
   Backend: Check: has_entry_fee=true, payment_status=null (not registered yet)
   Backend → Frontend: { can_register: true, payment_required: true, entry_fee: 500, ... }
   Frontend: Display "Register Now - ৳500" button

2. User clicks "Register Now"
   Frontend: Navigate to /tournaments/<slug>/register/
   Frontend → Backend: GET /api/tournaments/<slug>/registration-form/
   Backend → Frontend: { custom_fields: [...], payment_methods: ['bkash', 'nagad'], ... }
   Frontend: Display registration wizard (Step 1: Team, Step 2: Fields, Step 3: Payment)

3. User completes wizard, submits registration
   Frontend → Backend: POST /api/tournaments/<slug>/register/
      { team_id: 123, custom_fields: {...}, payment_method: 'bkash' }
   Backend → Database: Create registration with state='pending_payment'
   Backend → Payment Gateway: Initiate payment (SSLCommerz)
   Backend → Frontend: { registration_id: 456, payment_redirect_url: "https://..." }
   Frontend: Redirect to payment gateway (external)

4. Payment completed (user redirected back)
   Payment Gateway → Backend: POST /api/payments/callback/ (webhook)
   Backend → Database: Update registration.payment_status = 'paid', state = 'confirmed'
   Frontend: User lands on /tournaments/<slug>/register/success/
   Frontend → Backend: GET /api/tournaments/<slug>/registration-status/
   Backend → Frontend: { is_registered: true, state: 'confirmed', check_in_status: 'pending', ... }
   Frontend: Display "Registration successful! Check in before tournament starts"

5. User returns to tournament detail page
   Frontend → Backend: GET /api/tournaments/<slug>/registration-status/
   Backend: Check: is_registered=true, check_in_status='pending'
   Backend → Frontend: { can_register: false, state: 'check_in_pending', ... }
   Frontend: Display "You're Registered - Check In Soon" button (link to lobby)
```

---

## Future Enhancements (Out of Scope for Sprint 5)

1. **WebSocket Real-Time Updates**: Replace HTMX polling with WebSocket for instant roster/announcement updates (P2)
2. **Lobby Chat**: Q&A panel or live chat for participants to communicate with organizer (P2)
3. **Push Notifications**: Browser push notification 10 min before check-in deadline (P2)
4. **Check-In Leaderboard**: Show "first to check in" badge or leaderboard (P2, gamification)
5. **Team Huddle Space**: Private team-only space within lobby for team tournaments (P3)
6. **Video Announcement Embeds**: Allow organizers to embed YouTube/Vimeo videos in announcements (P3)
7. **Check-In QR Code**: Generate unique QR code for each participant, scan to check in (P3, in-person events)

---

## Success Criteria

**Sprint 5 Complete When**:
- ✅ Registered participants can access `/tournaments/<slug>/lobby/` page
- ✅ Check-in button available during check-in window (countdown timer before window opens)
- ✅ Check-in action updates participant's status in database
- ✅ Roster displays all participants with check-in status (✓ checked in, ⏳ pending)
- ✅ Participants who don't check in are marked as "no show" after deadline
- ✅ Registration CTA on detail page reflects all validation states (payment pending, approval required, etc.)
- ✅ Mobile layout works on 360px width (single column, sticky check-in button)
- ✅ Keyboard accessible (Tab, Enter, Escape navigation)
- ✅ Screen reader compatible (ARIA labels, live regions)
- ✅ All tests pass (minimum 8 tests for check-in, 5 tests for validation states)

**Performance Targets**:
- Lobby page loads < 1.5s on 3G mobile
- Check-in action completes < 1s (POST request)
- Roster updates < 2s after check-in (HTMX polling)
- Countdown timer updates every 1s (smooth, no flicker)

**Quality Targets**:
- Zero critical bugs in check-in flow
- WCAG 2.1 AA compliance (accessibility audit)
- Works on Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- Mobile usability score > 85 (Lighthouse)

---

**End of Sprint 5 Planning Document**
