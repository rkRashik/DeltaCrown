# Frontend Tournament Sitemap

**Date**: November 14, 2025  
**Scope**: Complete URL structure and page inventory for tournament-focused frontend  
**Status**: Planning phase

---

## Overview

This document answers: **"What pages exist under `/tournaments/` and related URLs?"**

All tournament-related pages organized by user persona and tournament lifecycle. Includes URL patterns, authentication requirements, primary purpose, key content, navbar navigation path, and backend API dependencies.

**Personas**:
- **Player**: User participating in tournaments
- **Spectator**: Public viewer (may not be logged in)
- **Organizer**: User who creates and manages tournaments
- **Admin**: Platform administrator (not covered here, admin panel separate)

---

## URL Structure Overview

```
/tournaments/                           # Public tournament list/discovery
/tournaments/<slug>/                    # Tournament detail page (adapts based on state)
/tournaments/<slug>/register/           # Registration wizard (logged-in only)
/tournaments/<slug>/bracket/            # Live bracket view
/tournaments/<slug>/matches/            # Match list
/tournaments/<slug>/matches/<id>/       # Match detail page
/tournaments/<slug>/leaderboard/        # Tournament leaderboard
/tournaments/<slug>/results/            # Final results (after tournament ends)
/tournaments/<slug>/certificate/<user>/ # Winner certificate (PDF download)

/dashboard/tournaments/                 # Player: My tournaments dashboard
/dashboard/organizer/                   # Organizer: My hosted tournaments dashboard
/dashboard/organizer/tournaments/<slug>/  # Organizer: Manage specific tournament

/profile/<username>/tournaments/        # User's public tournament history (P2)
```

---

## Section 1: Public Pages (Discovery & Detail)

### 1.1 Tournament Discovery / List Page

**URL**: `/tournaments/`  
**Method**: GET  
**Personas**: Spectator (public), Player  
**Auth**: Not required (public)

**Purpose**:  
Browse and discover available tournaments with filters and search.

**Key Content**:
- Page title: "Tournaments" or "Browse Tournaments"
- Filter bar: Game (dropdown), Status (tabs: All, Registration Open, Live, Upcoming, Completed)
- Search box: Search by tournament name
- Tournament cards grid/list:
  - Each card shows:
    - Tournament name
    - Game badge/logo
    - Status pill (Registration Open, Full, Live, Completed)
    - Format (e.g., "Single Elimination, 5v5")
    - Prize pool (if configured)
    - Start date
    - Slots filled/total (e.g., "16/32")
    - CTA button ("Register" or "View Details")
- Pagination or "Load More" button
- Empty state if no tournaments match filters

**Navbar Path**: `Tournaments` (top-level nav item)

**Backend APIs**:
- `GET /api/tournaments/discovery/`
  - Query params: `?game=<game_slug>&status=<status>&search=<query>&page=<num>`
  - Returns: Paginated list of tournaments

**Existing Template Reference**:
- `templates/spectator/tournament_list.html` (exists, needs enhancement)

**Mobile Considerations**:
- Cards stack vertically
- Filters collapse into dropdown or bottom sheet
- Sticky filter bar on scroll

---

### 1.2 Tournament Detail Page (Pre-Registration / Pre-Live)

**URL**: `/tournaments/<slug>/`  
**Method**: GET  
**Personas**: Spectator (public), Player  
**Auth**: Not required (public, but some content visible only if logged in)

**Purpose**:  
Comprehensive information page for a tournament before it goes live. Adapts based on tournament state (before, during, after).

**Key Content** (Before Tournament State):

**Hero Section**:
- Tournament banner image (if configured)
- Tournament name (H1)
- Game badge
- Status pill (e.g., "Registration Open", "Starting in 3 days")
- Registration countdown timer (if applicable)

**Key Info Bar**:
- Format (e.g., "Single Elimination")
- Date & Time (start date, timezone)
- Prize Pool (if configured, e.g., "৳50,000")
- Slots: "24/32 registered"

**Tab Navigation**:
1. **Overview** (default):
   - Tournament description (rich text)
   - Eligibility requirements
   - Rules summary
   - Organizer info (name, avatar, link to profile)
   - Contact/support link (if available)

2. **Schedule**:
   - Match schedule (if bracket generated)
   - Round structure
   - Estimated duration

3. **Prizes**:
   - Prize distribution table (1st, 2nd, 3rd, etc.)
   - Visual breakdown (pie chart or stacked bar)

4. **Rules & FAQ**:
   - Accordion sections for detailed rules
   - FAQ items

**Registration Section** (prominent CTA):
- Dynamic registration button with states:
  - "Register Now" (green, if registration open and user eligible)
  - "Registration Opens in X days" (gray, with countdown)
  - "Registration Closed" (gray, disabled)
  - "Tournament Full" (gray, disabled)
  - "You're Registered" (green with checkmark, if already registered)
  - "Login to Register" (blue, if not authenticated)
- If already registered: Show "Manage Registration" link

**Sidebar** (desktop) or cards (mobile):
- Organizer card (avatar, name, rating, "View Profile")
- Participants count
- Recent registrations (avatars or names)
- Social share buttons (Twitter, Facebook, copy link)

**Navbar Path**: `Tournaments` → `[Tournament Name]`

**Backend APIs**:
- `GET /api/tournaments/<slug>/`
  - Returns: Tournament detail, description, rules, prizes, organizer, registration status
- `GET /api/tournaments/<slug>/registration-status/`
  - Returns: `{ can_register: bool, reason: string, state: enum, is_registered: bool }`

**Existing Template Reference**:
- `templates/spectator/tournament_detail.html` (exists, adapt state-based rendering)

**Mobile Considerations**:
- Hero section collapses (smaller image, vertical layout)
- Tabs become dropdown or swipeable
- Registration CTA sticky at bottom
- Sidebar cards stack after main content

**State Adaptation**:
- **Before Tournament**: Show registration info, countdown, static schedule
- **During Tournament**: Show live bracket, leaderboard, matches (see 1.3)
- **After Tournament**: Show results, winners, final bracket (see 1.8)

---

### 1.3 Tournament Detail Page (During Tournament - Live State)

**URL**: `/tournaments/<slug>/` (same URL, different content based on state)  
**Method**: GET  
**Personas**: Spectator (public), Player  
**Auth**: Not required (public)

**Purpose**:  
Show live tournament progress with bracket, leaderboard, and matches.

**Key Content** (During Tournament State):

**Hero Section** (condensed):
- Tournament name
- Game badge
- Status pill ("Live" with pulsing dot)
- Current round indicator (e.g., "Round 3 of 5")

**Tab Navigation**:
1. **Live Bracket** (default):
   - Visual bracket tree (SVG or canvas-based)
   - Shows all matches with current scores
   - Highlight ongoing matches
   - Click on match to see detail
   - Toggle between bracket view and list view

2. **Leaderboard**:
   - Real-time rankings table
   - Rank, Team/Player, Wins, Losses, Points
   - Highlight current user's row (if logged in as participant)
   - Auto-updates via WebSocket or HTMX polling

3. **Matches**:
   - List of all matches (past, ongoing, upcoming)
   - Filter by round, status (completed, live, upcoming)
   - Per match: participants, scores, status, "View Details" link
   - "My Matches" filter (if logged in as participant)

4. **Overview**:
   - Tournament info (same as pre-tournament, read-only)
   - Participants list
   - Organizer info

**Real-Time Updates**:
- WebSocket connection for live score updates
- HTMX polling fallback (`hx-get` every 10s on leaderboard/bracket)
- Toast notification on match updates (if user is participant)

**Navbar Path**: `Tournaments` → `[Tournament Name]`

**Backend APIs**:
- `GET /api/tournaments/<slug>/` (tournament detail with live flag)
- `GET /api/tournaments/<slug>/bracket/` (bracket structure with live scores)
- `GET /api/tournaments/<slug>/matches/` (match list)
- `GET /api/tournaments/<slug>/leaderboard/` (real-time rankings)
- WebSocket: `/ws/tournaments/<slug>/` (live updates)

**Existing Template Reference**:
- `templates/spectator/tournament_detail.html` (adapt for live state)
- `legacy_backup/templates/tournaments/tournaments/bracket.html` (bracket reference)

**Mobile Considerations**:
- Bracket: horizontal scroll, or prefer list view
- Leaderboard: horizontal scroll for wide table, or card view
- Sticky "My Matches" button (if participant)

---

### 1.4 Tournament Detail Page (After Tournament - Results State)

**URL**: `/tournaments/<slug>/` (same URL, state-based rendering)  
**Method**: GET  
**Personas**: Spectator (public), Player  
**Auth**: Not required (public)

**Purpose**:  
Show final results, winners, and match history after tournament concludes.

**Key Content** (After Tournament State):

**Hero Section**:
- Tournament name
- Game badge
- Status pill ("Completed")
- "Archived" label

**Winners Section** (prominent):
- Podium visual (Top 3 teams/players)
  - 1st place: larger card, gold medal
  - 2nd place: medium card, silver medal
  - 3rd place: medium card, bronze medal
- Each winner card shows: Team/player name, avatar, prize won
- Confetti animation on page load (subtle, skippable)

**Tab Navigation**:
1. **Results** (default):
   - Final leaderboard table (complete rankings)
   - Match history (all matches with final scores, expandable)
   - Stats summary: Total matches, upsets, tournament duration

2. **Bracket**:
   - Final bracket with all scores (read-only)

3. **Prizes**:
   - Prize distribution with winners highlighted

4. **Overview**:
   - Tournament info (same as before)

**Actions** (for participants):
- "Download Certificate" button (if winner/participant, logged in)
- "Share Result" social buttons

**Navbar Path**: `Tournaments` → `[Tournament Name]`

**Backend APIs**:
- `GET /api/tournaments/<slug>/` (tournament detail with completed flag)
- `GET /api/tournaments/<slug>/results/` (final results, winners, rankings)
- `GET /api/tournaments/<slug>/certificate/<user_id>/` (certificate PDF, authenticated)

**Existing Template Reference**:
- Adapt `templates/spectator/tournament_detail.html` for completed state

**Mobile Considerations**:
- Podium stacks vertically (1st, 2nd, 3rd)
- Leaderboard scrolls horizontally or uses card view
- Certificate download button sticky at bottom

---

## Section 2: Registration Pages (Player)

### 2.1 Registration Wizard Entry

**URL**: `/tournaments/<slug>/register/`  
**Method**: GET  
**Personas**: Player (logged in)  
**Auth**: **Required** (redirect to login if not authenticated)

**Purpose**:  
Multi-step registration wizard guiding player through tournament registration.

**Entry Conditions**:
- User must be logged in
- Registration must be open
- Tournament must not be full
- User must not already be registered
- User must meet eligibility requirements (validated by backend)

**Wizard Steps** (dynamic based on tournament configuration):

**Step 1: Eligibility Check** (auto-check, may skip if passed):
- Backend validates user meets requirements
- If team tournament: user must be member of at least one eligible team
- If failed: Show error message + reason, block progress

**Step 2: Team/Solo Selection** (conditional):
- **For Team Tournaments**:
  - Dropdown: Select team from user's teams (only teams user captains or is member of)
  - Team card preview: Team name, logo, roster
- **For Solo Tournaments**:
  - Skip this step

**Step 3: Custom Fields** (conditional, if tournament has custom fields):
- Dynamic form based on tournament configuration
- Examples:
  - "In-Game ID" (text input, required)
  - "Discord Username" (text input, optional)
  - "Preferred Role" (dropdown: Top, Jungle, Mid, etc.)
- Inline validation on blur
- Help text for each field

**Step 4: Payment Information** (conditional, if tournament has entry fee):
- **If Free Tournament**: Skip this step
- **If Paid Tournament**:
  - Show price prominently (e.g., "৳500")
  - Breakdown: Entry fee, platform fee, total
  - Payment method selector (radio cards):
    - bKash (logo + instructions)
    - Nagad (logo + instructions)
    - Rocket (logo + instructions)
    - Credit/Debit Card (via SSLCommerz)
  - Note: "You will be redirected to secure payment gateway"

**Step 5: Review & Confirm**:
- Summary section:
  - Tournament name, game
  - Team selected (if applicable)
  - Custom field values entered
  - Payment method selected (if paid)
  - Total amount (if paid)
- Checkbox: "I agree to the tournament rules and terms" (required)
- Note: "Registration is final. Refunds only as per refund policy."
- Submit button: "Complete Registration" or "Proceed to Payment"

**Step 6: Confirmation / Payment Redirect**:
- **If Free**: Show success message, "You're registered!"
- **If Paid**: Redirect to payment gateway (external)
- After successful payment (redirected back): Show success confirmation

**Stepper Component** (top of page):
- Visual progress indicator (Step X of Y)
- Step labels: Team, Info, Payment, Confirm
- Disable clicking ahead (must go in order)

**Actions**:
- "Back" button (available on steps 2-5)
- "Next" button (validates current step before proceeding)
- "Cancel" button (top-right, confirm before abandoning)

**Navbar Path**: `Tournaments` → `[Tournament Name]` → `Register`

**Backend APIs**:
- `GET /api/tournaments/<slug>/registration-form/`
  - Returns: Form structure, custom fields, pricing, eligibility requirements
- `POST /api/tournaments/<slug>/register/`
  - Body: `{ team_id: int (optional), custom_fields: object, payment_method: string }`
  - Returns: Registration ID, payment redirect URL (if paid)
- `GET /api/payments/methods/`
  - Returns: Available payment methods

**Existing Template Reference**:
- `templates/ecommerce/checkout_wizard.html` (checkout wizard pattern)
- `static/siteui/js/reg_wizard.js` (existing registration wizard logic)
- `static/js/dynamic-registration.js` (dynamic form handling)

**Mobile Considerations**:
- Single-column layout
- Stepper becomes horizontal dots
- Sticky "Next" button at bottom
- Minimize form fields per screen (split into more steps if needed)

**Error Handling**:
- If registration fills up during wizard: Show "Tournament Full" modal, block submit
- If payment fails: Show error, allow retry or change payment method
- If session expires: Save progress to localStorage, restore on re-login (P1)

---

### 2.2 Registration Success / Payment Callback

**URL**: `/tournaments/<slug>/register/success/`  
**Method**: GET  
**Personas**: Player (logged in)  
**Auth**: **Required**

**Purpose**:  
Confirmation page after successful registration (free or after payment callback).

**Key Content**:
- Success icon/animation (checkmark, confetti)
- Heading: "You're Registered!"
- Tournament name, game badge
- Next steps:
  - "Check-in opens X hours before tournament starts"
  - "You will receive email/notification with match schedule"
  - "View tournament page for updates"
- Actions:
  - Button: "View Tournament" (link to `/tournaments/<slug>/`)
  - Button: "View My Tournaments" (link to `/dashboard/tournaments/`)
- If paid: Show receipt summary (transaction ID, amount, date)

**Navbar Path**: `Tournaments` → `[Tournament Name]` → `Registration Success`

**Backend APIs**:
- `GET /api/tournaments/<slug>/registration/<registration_id>/`
  - Returns: Registration details, receipt (if paid)

**Existing Template Reference**:
- `templates/ecommerce/order_success.html` (order confirmation pattern)

**Mobile Considerations**:
- Centered content, large checkmark
- CTAs stacked vertically

---

### 2.3 Registration Error / Failure

**URL**: `/tournaments/<slug>/register/error/`  
**Method**: GET  
**Personas**: Player (logged in)  
**Auth**: **Required**

**Purpose**:  
Error page if registration fails (payment failed, tournament full, eligibility issue).

**Key Content**:
- Error icon (X or alert)
- Heading: "Registration Failed"
- Error message (from backend or URL param)
- Reason: "Payment was declined" / "Tournament is now full" / "You don't meet eligibility requirements"
- Actions:
  - Button: "Try Again" (back to registration wizard)
  - Button: "View Tournament" (link to tournament detail)
  - Button: "Contact Support" (if critical error)

**Navbar Path**: `Tournaments` → `[Tournament Name]` → `Registration Error`

**Backend APIs**:
- Error messages passed via URL params or session

**Mobile Considerations**:
- Centered content, clear error message
- CTAs stacked vertically

---

### 2.4 Tournament Lobby / Participant Hub

**URL**: `/tournaments/<slug>/lobby/`  
**Method**: GET, POST (for check-in and actions)  
**Personas**: Player (registered participant only)  
**Auth**: **Required** (must be registered participant)  
**ID**: FE-T-007  
**BACKEND_IMPACT**: Pending (needs lobby API with participant-only access control)

**Purpose**:  
Central hub page for registered participants during registration-closed → tournament-complete phases. Replaces need for external Discord/WhatsApp for participant coordination.

**Access Control**:
- Only accessible to registered participants
- Backend validates registration status
- Non-participants redirected to public tournament detail page
- Available from: Registration closes → Tournament completes

**Key Content**:

**Tournament Overview Panel**:
- Tournament name, game badge, format, date/time
- Registration status: "You're registered as [Solo/Team Name]"
- Check-in status indicator (checked in / pending)
- Tournament status: Waiting to Start / Live / Completed

**Check-In Widget** (before tournament starts):
- Check-in button (only available during check-in window)
- Check-in deadline countdown
- Visual indicator: "Checked In ✓" (green) or "Not Checked In - Click Here" (amber warning)
- Check-in confirmation modal
- Warning: "Check-in required to participate. No-shows will be disqualified"

**Participant Roster**:
- List of all registered participants (players/teams)
- Per participant: Name, avatar, check-in status (icon)
- Total participants count vs capacity (e.g., "28/32 checked in")
- Search/filter roster (search by name, filter by checked-in status)
- Sortable: Name (alphabetical), Check-in status, Registration date

**Match Schedule Widget** (after bracket generation):
- "Your Next Match" highlighted card (prominent, top of section)
  - Opponent name/avatar
  - Match time with countdown
  - Match number and round
  - "View Match" button
- "Your Match History" list (expandable)
  - Past matches with scores
  - Upcoming matches (full schedule)
  - Filter: Show only my matches / Show all matches
- Link to full bracket view

**Announcements Panel**:
- Tournament announcements from organizer
- Chronological list (newest first)
- Per announcement: Title, message, timestamp
- Pin important announcements to top
- Example announcements: "Check-in opens in 1 hour", "Bracket generated", "Round 2 starting"

**Communication Section** (optional P1):
- Chat widget or Q&A panel
- Participants can ask questions to organizer
- Organizer can broadcast messages
- Note: If not implemented, show "Contact organizer at [email/discord]"

**Rules & Info Section**:
- Quick access to tournament rules (expandable/collapsible)
- FAQ items relevant to participants
- Link to full tournament detail page

**Navbar Path**: `Tournaments` → `[Tournament Name]` → `Lobby` (or shown as tab in tournament detail for participants)

**Backend APIs**:
- `GET /api/tournaments/<slug>/lobby/`
  - Returns: Lobby data (requires participant auth, returns 403 if not registered)
  - Data: Tournament info, check-in status, roster, match schedule, announcements
- `POST /api/tournaments/<slug>/check-in/`
  - Body: `{ confirm: true }`
  - Returns: Check-in confirmation, updates participant status
- `GET /api/tournaments/<slug>/lobby/roster/`
  - Returns: Full participant list with check-in statuses
- `GET /api/tournaments/<slug>/lobby/announcements/`
  - Returns: Organizer announcements

**Existing Template Reference**:
- Create new template: `templates/tournaments/lobby/index.html`
- Reuse components: participant cards, countdown timer, status pills

**Mobile Considerations**:
- Panels stack vertically
- Check-in button sticky at top (if not checked in)
- "Your Next Match" card prominent
- Roster uses card view (not table)
- Announcements collapsible by default

**Notes**:
- Lobby is participant-exclusive (not spectator-accessible)
- Purpose: Pre-tournament coordination, check-in management, participant communication
- Replaces need for external communication tools
- Must handle check-in window enforcement (backend manages timing)
- Real-time updates: Poll for roster/check-in status changes every 30s (HTMX `hx-trigger="every 30s"`)

---

## Section 3: Live Tournament Pages (During Tournament)

### 3.1 Tournament Bracket / Schedule View

**URL**: `/tournaments/<slug>/bracket/`  
**Method**: GET  
**Personas**: Player, Spectator (public)  
**Auth**: Not required (public)

**Purpose**:  
Visual bracket display showing tournament structure and match progression.

**Key Content**:

**Tab/View Toggle**:
1. **Bracket View**:
   - Visual tree structure (SVG or canvas)
   - Shows all rounds, matches, and participants
   - Live scores displayed inline
   - Ongoing matches highlighted (pulsing border or icon)
   - Clickable matches (link to match detail)
   - Horizontal scroll for large brackets

2. **Schedule View**:
   - List/table of all matches
   - Columns: Match #, Round, Participants, Status, Time, Score
   - Filter by: Round (dropdown), Status (tabs: All, Live, Upcoming, Completed)
   - Sort by: Time (default), Match #

3. **My Matches** (if logged in as participant):
   - Filtered view showing only matches involving current user's team
   - Highlight next match prominently
   - Show check-in status (if required)

**Real-Time Updates**:
- WebSocket: Live score updates, match status changes
- HTMX fallback: Poll every 10s (`hx-get="/tournaments/<slug>/bracket/" hx-trigger="every 10s"`)

**Navbar Path**: `Tournaments` → `[Tournament Name]` → `Bracket` (or shown in main tournament page tab)

**Backend APIs**:
- `GET /api/tournaments/<slug>/bracket/`
  - Returns: Bracket structure, matches with participants and scores
- `GET /api/tournaments/<slug>/matches/`
  - Query params: `?round=<num>&status=<enum>&my_matches=true`
  - Returns: Match list

**Existing Template Reference**:
- `legacy_backup/templates/tournaments/tournaments/bracket.html` (bracket reference)
- `templates/spectator/_leaderboard_table.html` (table pattern)

**Mobile Considerations**:
- Bracket view: horizontal scroll, pinch-to-zoom
- Schedule view preferred on mobile (easier to read)
- "My Matches" sticky filter button
- Reduce bracket visual complexity (smaller text, icons)

---

### 3.2 Match Detail / Lobby Page

**URL**: `/tournaments/<slug>/matches/<match_id>/`  
**Method**: GET, POST (for score reporting)  
**Personas**: Player (participant), Spectator (public)  
**Auth**: Not required for viewing, required for actions (report score, dispute)

**Purpose**:  
Detailed view of a specific match, showing participants, scores, lobby info, and actions.

**Key Content**:

**Match Header**:
- Match number (e.g., "Match #12")
- Round (e.g., "Round 3 - Semifinals")
- Status pill ("Upcoming", "Live", "Completed", "Disputed")
- Scheduled time (with countdown if upcoming)

**Participants Section**:
- Two columns: Team A vs Team B (or Player A vs Player B)
- Each side shows:
  - Team/player name
  - Avatar/logo
  - Score (if match started or completed)
  - Roster (expandable, if team match)
- Score display: Large, centered, visual (e.g., "3 - 1")

**Match Timeline** (for live/completed matches):
- Chronological list of events:
  - Match started
  - Score updates (e.g., "Team A wins Game 1")
  - Match ended
  - Dispute raised (if applicable)
  - Score updated by organizer (if applicable)
- Timestamps for each event

**Lobby Information** (for participants only, if match upcoming/live):
- Game lobby details:
  - Server/region
  - Lobby code/password
  - Join instructions
  - Voice chat link (if configured, e.g., Discord)
- Note: "Join lobby 10 minutes before match start"

**Actions** (for participants only, logged in, role-based):
- **Before Match**: "Check-In" button (if required)
- **After Match** (if participant and no score reported yet): "Report Score" button (opens modal)
- **After Match** (if score reported by opponent and dispute window open): "Dispute Score" button (opens modal)
- **During Match**: No actions, just view

**Actions** (for spectators):
- No action buttons, read-only view
- "Follow Match" button (optional P2, adds to watchlist)

**Score Reporting Modal** (participant only):
- Form: Enter score for each game/map (depends on format)
- Example: "Game 1: ___ - ___", "Game 2: ___ - ___"
- Checkbox: "I confirm these scores are accurate"
- Submit button: "Submit Score"
- Note: "Both teams must report scores. If scores match, match is auto-confirmed. If mismatch, organizer reviews."

**Dispute Modal** (participant only):
- Dropdown: Reason for dispute (e.g., "Opponent cheated", "Wrong score", "Technical issue")
- Text area: Additional details (optional)
- File upload: Evidence (screenshots, optional)
- Submit button: "Submit Dispute"
- Note: "Organizer will review and resolve within 24 hours"

**Navbar Path**: `Tournaments` → `[Tournament Name]` → `Matches` → `Match #X`

**Backend APIs**:
- `GET /api/matches/<match_id>/`
  - Returns: Match detail, participants, scores, timeline, lobby info (if participant)
- `POST /api/matches/<match_id>/report-score/`
  - Body: `{ scores: array of game scores }`
  - Returns: Success, score submitted
- `POST /api/matches/<match_id>/dispute/`
  - Body: `{ reason: string, details: string, evidence: file (optional) }`
  - Returns: Dispute ID

**Existing Template Reference**:
- `templates/spectator/match_detail.html` (spectator view)
- `templates/teams/match_detail.html` (team match detail, adapt)

**Mobile Considerations**:
- Participants stack vertically (Team A on top, Team B below)
- Timeline scrolls independently
- Action buttons sticky at bottom
- Modals full-screen on mobile

---

### 3.3 Tournament Leaderboard

**URL**: `/tournaments/<slug>/leaderboard/`  
**Method**: GET  
**Personas**: Player, Spectator (public)  
**Auth**: Not required (public)

**Purpose**:  
Real-time rankings of participants based on tournament format rules.

**Key Content**:

**Leaderboard Table**:
- Columns: Rank, Team/Player, Games Played, Wins, Losses, Points (or format-specific stats)
- Highlight current user's row (if logged in as participant, different background color)
- Top 3 rows have medal icons (🥇, 🥈, 🥉)
- Pagination or infinite scroll for large tournaments

**Filters** (for round-robin/swiss formats):
- Group selector (if groups configured)
- Round selector (show standings after specific round)

**Real-Time Updates**:
- WebSocket: Auto-update on match completions
- HTMX fallback: Poll every 10s (`hx-get hx-trigger="every 10s"`)
- Toast notification: "Leaderboard updated" (subtle)

**Empty State**:
- If tournament hasn't started: "Leaderboard will be available once matches begin"

**Navbar Path**: `Tournaments` → `[Tournament Name]` → `Leaderboard` (or shown in main tournament page tab)

**Backend APIs**:
- `GET /api/tournaments/<slug>/leaderboard/`
  - Query params: `?group=<num>&round=<num>`
  - Returns: Array of rankings with stats

**Existing Template Reference**:
- `templates/spectator/_leaderboard_table.html` (existing leaderboard partial)

**Mobile Considerations**:
- Horizontal scroll for wide tables
- Alternative: Card view (Rank + Team + Key Stats per card)
- Sticky header row
- Reduce columns (hide less important stats)

---

## Section 4: Post-Tournament Pages

### 4.1 Tournament Results / Recap Page

**URL**: `/tournaments/<slug>/results/`  
**Method**: GET  
**Personas**: Player, Spectator (public)  
**Auth**: Not required (public)

**Purpose**:  
Final results, winners, and complete match history after tournament concludes.

**Key Content**:

**Winners Section** (hero):
- Podium visual (Top 3)
  - 1st place: Larger card, gold medal, prize amount
  - 2nd place: Medium card, silver medal, prize amount
  - 3rd place: Medium card, bronze medal, prize amount
- Each card shows: Team/player name, avatar/logo, prize won
- Optional: Confetti animation on load (subtle, can skip)

**Final Leaderboard**:
- Complete rankings table (all participants)
- Columns: Rank, Team/Player, Final Score, Placement
- Searchable/filterable (for large tournaments)

**Match History**:
- Accordion or expandable list of all matches
- Per match: Participants, scores, round, date
- Chronological order (most recent first) or by round

**Tournament Stats Summary**:
- Cards: Total Matches, Total Participants, Tournament Duration, Largest Upset (if supported)

**Actions**:
- Button: "Download Certificate" (if logged in as winner/participant, P2)
- Social share buttons: "Share Result" (Twitter, Facebook, copy link)

**Navbar Path**: `Tournaments` → `[Tournament Name]` → `Results` (or shown in main tournament page after completion)

**Backend APIs**:
- `GET /api/tournaments/<slug>/results/`
  - Returns: Winners, final leaderboard, match history, stats

**Existing Template Reference**:
- Adapt `templates/spectator/tournament_detail.html` for completed state

**Mobile Considerations**:
- Podium stacks vertically
- Leaderboard scrolls or switches to card view
- Match history uses accordion (collapse by default)

---

### 4.2 Certificate Download (Winner/Participant)

**URL**: `/tournaments/<slug>/certificate/<username>/`  
**Method**: GET  
**Personas**: Player (logged in, winner or participant)  
**Auth**: **Required** (must be the user requesting their own certificate)

**Purpose**:  
Download or preview achievement certificate for winners/participants.

**Key Content**:
- Certificate preview (modal or new page)
- PDF download link
- "Share Certificate" social buttons (optional)

**Backend APIs**:
- `GET /api/tournaments/<slug>/certificate/<user_id>/`
  - Returns: PDF file (download)
  - Backend generates certificate via Module 6.6

**Navbar Path**: Accessed from results page or user profile

**Mobile Considerations**:
- Direct PDF download
- Preview in browser (if supported)

**Notes**:
- P2 priority feature
- Certificate design handled by backend (PDF generation)
- Frontend just provides download link and preview modal

---

## Section 5: Dashboard Pages (Player View)

### 5.1 My Tournaments Dashboard Card

**URL**: `/dashboard/` (main dashboard, tournament card embedded)  
**Method**: GET  
**Personas**: Player (logged in)  
**Auth**: **Required**

**Purpose**:  
Small widget in user dashboard showing registered tournaments.

**Key Content** (Tournament Card in Dashboard):
- Card title: "My Tournaments"
- List of user's registered tournaments (max 5, show "View All" if more)
- Per tournament mini-card:
  - Tournament name
  - Game badge
  - Status pill (Upcoming, Live, Completed)
  - Next match time (if upcoming/live)
  - CTA: "View Tournament" link
- "View All Tournaments" link (expands to full page, P2)

**Backend APIs**:
- `GET /api/users/me/tournaments/`
  - Returns: User's tournament registrations with status

**Existing Template Reference**:
- `templates/dashboard/index.html` (main dashboard, add tournament card)

**Navbar Path**: `Dashboard` (top-level nav item)

**Mobile Considerations**:
- Card full-width
- List stacks vertically

**Notes**:
- This is a small addition to existing dashboard (FE-T-005 in backlog)
- Full "My Tournaments" page is P2, not in MVP scope

---

## Section 6: Organizer Dashboard Pages

### 6.1 Organizer Dashboard (My Hosted Tournaments)

**URL**: `/dashboard/organizer/`  
**Method**: GET  
**Personas**: Organizer (logged in, user with organizer role)  
**Auth**: **Required** (organizer role)

**Purpose**:  
Dashboard for organizers to see all their hosted tournaments and key metrics.

**Key Content**:

**Summary Metrics** (top cards):
- Total Tournaments Hosted
- Total Participants (across all tournaments)
- Total Revenue (if applicable)
- Active Tournaments (currently live)

**Tournament List** (table or cards):
- Columns: Tournament Name, Game, Status, Participants, Start Date, Actions
- Status: Draft, Registration Open, Live, Completed, Cancelled
- Actions per row:
  - "Manage" button (link to `/dashboard/organizer/tournaments/<slug>/`)
  - "View Public Page" link (link to `/tournaments/<slug>/`)
- Filters: Status (tabs), Game (dropdown), Date range

**Actions** (top-right):
- Button: "Create Tournament" (link to create tournament flow, not in scope here)

**Navbar Path**: `Dashboard` → `Organizer` (or `Dashboard` if user has organizer role, context-based)

**Backend APIs**:
- `GET /api/organizer/tournaments/`
  - Returns: List of organizer's tournaments, summary metrics

**Existing Template Reference**:
- `templates/dashboard/index.html` (adapt for organizer view)

**Mobile Considerations**:
- Metrics stack vertically
- Table converts to cards
- Filters collapse into drawer or bottom sheet

**Notes**:
- If user is both player and organizer, show tabs: "My Tournaments" (player) / "My Hosted Tournaments" (organizer)
- Only show organizer view if user has organizer role (backend permission check)

---

### 6.2 Manage Tournament (Organizer Admin Page)

**URL**: `/dashboard/organizer/tournaments/<slug>/`  
**Method**: GET, POST (for actions)  
**Personas**: Organizer (logged in, tournament creator/owner)  
**Auth**: **Required** (organizer role, must own this tournament)

**Purpose**:  
Comprehensive tournament management interface for organizers.

**Key Content**:

**Tab Navigation**:

**1. Overview Tab**:
- Tournament info summary (read-only): Name, game, format, dates, status
- Actions (button group):
  - "Start Tournament" (if registration closed and ready to start)
  - "Pause Tournament" (if live, pause all matches)
  - "Cancel Tournament" (if not started, cancel and issue refunds)
  - "Edit Details" (link to edit tournament form, not in scope)
- Status timeline: Created → Registration Open → Registration Closed → Live → Completed
- Next action needed: e.g., "Close registration and start tournament in 2 days"

**2. Participants Tab**:
- Table: Participant Name, Team (if applicable), Registration Date, Payment Status, Actions
- Payment Status: Paid, Unpaid, Refunded
- Actions per row:
  - "View Details" (expand row or modal)
  - "Remove" (if registration open, triggers confirmation modal)
  - "Approve" (if manual approval enabled, approve pending registration)
- Filters: Status (All, Confirmed, Pending, Disqualified), Payment (All, Paid, Unpaid)
- Bulk actions: "Approve All Pending", "Export CSV"

**3. Matches Tab**:
- Table: Match #, Participants, Scheduled Time, Status, Score, Actions
- Status: Scheduled, Live, Completed, Disputed
- Actions per row:
  - "Reschedule" (change match time, opens modal)
  - "Override Score" (if disputed or incorrect, opens modal)
  - "Forfeit" (mark match as forfeit, opens modal)
- Filters: Round, Status
- "Generate Bracket" button (if not yet generated)

**4. Payments Tab**:
- Summary cards: Total Expected, Total Received, Pending, Refunded
- Table: Participant, Amount, Payment Method, Status, Date
- Export button: "Download CSV"
- Note: Read-only view, no transaction actions (admin handles refunds)

**5. Disputes Tab**:
- Table: Match #, Disputing Party, Reason, Status (Open, Resolved), Date
- Actions per row: "View & Resolve" (link to dispute detail page)
- Empty state: "No active disputes"

**6. Health Tab** (P2):
- Real-time tournament health metrics from Module 2.5
- Gauges: API Latency, Error Rate, Active Connections
- Status: Operational, Degraded, Down
- Alerts: Critical issues list
- Note: P2 priority, can defer

**Navbar Path**: `Dashboard` → `Organizer` → `[Tournament Name]`

**Backend APIs**:
- `GET /api/organizer/tournaments/<slug>/`
  - Returns: Tournament admin data (all tabs)
- `POST /api/organizer/tournaments/<slug>/start/`
- `POST /api/organizer/tournaments/<slug>/pause/`
- `POST /api/organizer/tournaments/<slug>/cancel/`
- Module 8.1: Admin lock enforcement (backend validates organizer permissions)

**Existing Template Reference**:
- `templates/dashboard/index.html` (adapt for tournament management)

**Mobile Considerations**:
- Tabs convert to dropdown or swipeable
- Tables convert to cards
- Action buttons stack vertically in modals

**Notes**:
- Must enforce organizer permissions (backend returns 403 if not owner)
- Critical actions (start, cancel, override score) require confirmation modal with reason input
- All actions logged in audit trail (Module 8.3, backend handles)

---

### 6.3 Dispute Resolution Page (Organizer)

**URL**: `/dashboard/organizer/tournaments/<slug>/disputes/<dispute_id>/`  
**Method**: GET, POST (for resolution)  
**Personas**: Organizer (logged in, tournament owner)  
**Auth**: **Required** (organizer role, must own this tournament)

**Purpose**:  
Detailed view and resolution interface for match disputes.

**Key Content**:

**Dispute Header**:
- Dispute ID
- Match number and participants
- Status: Open, Resolved
- Date raised

**Match Info Section**:
- Original match detail (participants, scheduled time)
- Original score (reported by both parties)
- Disputed score (if score mismatch)

**Evidence Section**:
- **Party A Submission**:
  - Score reported
  - Reason for dispute (text)
  - Evidence (screenshots, if uploaded)
- **Party B Submission**:
  - Score reported
  - Reason (if responding to dispute)
  - Evidence (screenshots, if uploaded)

**Timeline**:
- Chronological events:
  - Match completed
  - Team A reported score
  - Team B reported different score
  - Dispute raised by Team B
  - Organizer viewed dispute
  - Dispute resolved (if applicable)

**Resolution Actions** (if dispute still open):
- Button: "Accept Team A's Score"
- Button: "Accept Team B's Score"
- Button: "Override Score" (custom score input, opens modal)
- Button: "Reject Dispute" (mark as invalid, opens modal with reason)
- Note: "All parties will be notified of resolution"

**Override Score Modal**:
- Form: Enter final score (custom input)
- Text area: Reason for override (required)
- Submit button: "Set Final Score"

**Reject Dispute Modal**:
- Text area: Reason for rejection (required)
- Checkbox: "Confirm rejection"
- Submit button: "Reject Dispute"

**Navbar Path**: `Dashboard` → `Organizer` → `[Tournament Name]` → `Disputes` → `Dispute #X`

**Backend APIs**:
- `GET /api/disputes/<dispute_id>/`
  - Returns: Dispute detail, evidence, match info
- `POST /api/disputes/<dispute_id>/resolve/`
  - Body: `{ resolution: enum (accept_a, accept_b, override, reject), final_score: object (if override), reason: string }`
  - Returns: Success, dispute resolved
- Module 5.5: Dispute service

**Existing Template Reference**:
- Create new template for dispute detail

**Mobile Considerations**:
- Evidence images: swipeable gallery
- Actions stack vertically
- Modals full-screen

**Notes**:
- Dispute window is 24 hours (Module 5.5 enforces, backend)
- After 24 hours, dispute auto-resolves to organizer review
- Must show both parties' evidence clearly and fairly

---

### 6.4 Group Stage Configuration (Organizer)

**URL**: `/dashboard/organizer/tournaments/<slug>/groups/config/`  
**Method**: GET, POST  
**Personas**: Organizer (logged in, tournament owner)  
**Auth**: **Required** (organizer role, must own this tournament)  
**ID**: FE-T-011  
**BACKEND_IMPACT**: Pending (needs group stage models & configuration service)

**Purpose**:  
Configure group stage settings for multi-game tournaments (eFootball, FC Mobile, Valorant, PUBG Mobile, Free Fire, CS2, FIFA, Mobile Legends, Call of Duty Mobile).

**Key Content**:

**Configuration Form**:
- Number of groups (dropdown: 2, 4, 8, 16)
- Participants per group (auto-calculated based on total participants and group count)
- Match format: Round-robin (everyone plays everyone) / Single round-robin
- Points system: Win/Draw/Loss points (e.g., 3/1/0)
- Top N advance from each group (dropdown: 1, 2, 4)
- Preview: Visual preview of group structure

**Actions**:
- Button: "Save Configuration"
- Button: "Generate Groups" (triggers random assignment or seeded draw)
- Button: "Cancel" (back to manage tournament)

**Validation**:
- Must have even number of participants for balanced groups
- Warn if group configuration results in odd participants per group

**Navbar Path**: `Dashboard` → `Organizer` → `[Tournament Name]` → `Groups` → `Configure`

**Backend APIs**:
- `POST /api/organizer/tournaments/<slug>/groups/configure/`
  - Body: `{ num_groups: int, points_system: object, top_n_advance: int }`
  - Returns: Configuration saved
- `POST /api/organizer/tournaments/<slug>/groups/generate/`
  - Returns: Groups generated with participant assignments

**Notes**:
- Only available for tournaments configured with group stage format
- Must configure before tournament starts
- Supports all 9 active games in DeltaCrown

---

### 6.5 Live Group Draw Interface (Organizer)

**URL**: `/dashboard/organizer/tournaments/<slug>/groups/draw/`  
**Method**: GET, POST  
**Personas**: Organizer (logged in, tournament owner)  
**Auth**: **Required** (organizer role, must own this tournament)  
**ID**: FE-T-012  
**BACKEND_IMPACT**: Pending (needs live draw service & animation)

**Purpose**:  
Interactive live draw interface for randomly assigning participants to groups (alternative to automatic generation).

**Key Content**:

**Draw Interface**:
- Group containers: Visual boxes for each group (e.g., Group A, Group B, Group C, Group D)
- Participant pool: List of all registered participants (shuffled)
- Draw button: "Draw Next Participant" (assigns to next group, animated)
- Auto-assign button: "Auto-Assign Remaining" (completes draw automatically)
- Reset button: "Start Over" (clears assignments)

**Draw Animation**:
- Participant name/avatar animates from pool to assigned group
- Sound effect on each draw (optional, toggle)
- Confetti when draw complete (optional)

**Live Broadcast** (optional P1):
- Share link for participants to watch live draw
- Read-only view for spectators
- WebSocket updates as each participant drawn

**Actions**:
- Button: "Confirm Draw" (finalizes and saves group assignments)
- Button: "Cancel Draw" (discard and go back)

**Navbar Path**: `Dashboard` → `Organizer` → `[Tournament Name]` → `Groups` → `Live Draw`

**Backend APIs**:
- `GET /api/organizer/tournaments/<slug>/groups/draw/`
  - Returns: Current draw state (if in progress)
- `POST /api/organizer/tournaments/<slug>/groups/draw/next/`
  - Returns: Next participant assignment (random)
- `POST /api/organizer/tournaments/<slug>/groups/draw/finalize/`
  - Returns: Draw completed, groups saved

**Notes**:
- Optional feature (can use auto-generate instead)
- Provides transparency and excitement for live-streamed draws
- Must enforce fairness (true randomization, no manual assignment)

---

### 6.6 Group Standings Page

**URL**: `/tournaments/<slug>/groups/` or `/tournaments/<slug>/standings/`  
**Method**: GET  
**Personas**: Spectator (public), Player  
**Auth**: Not required (public)  
**ID**: FE-T-013  
**BACKEND_IMPACT**: Pending (needs group standings calculation service)

**Purpose**:  
Display group stage standings for tournaments with group format. Supports all 9 active games.

**Key Content**:

**Group Selector** (if multiple groups):
- Tabs: Group A, Group B, Group C, Group D, All Groups
- Default: Show all groups side-by-side (desktop) or stacked (mobile)

**Per Group Standings Table**:
- Group name header (e.g., "Group A")
- Columns: Rank, Team/Player, Played, Won, Drawn, Lost, GF (Goals For), GA (Goals Against), GD (Goal Difference), Points
- Highlight: Top N advancing teams (green background or icon)
- Elimination zone: Bottom teams (red background or icon, if applicable)
- Current user's team highlighted (if logged in as participant)

**Match Results Section** (per group):
- Accordion or expandable: "View Group A Matches"
- Table: Match #, Participants, Score, Date
- Filter: Completed / Upcoming matches

**Real-Time Updates**:
- HTMX polling: Refresh standings every 30s during live matches
- WebSocket (optional P1): Instant updates on match completions

**Navbar Path**: `Tournaments` → `[Tournament Name]` → `Groups` or `Standings`

**Backend APIs**:
- `GET /api/tournaments/<slug>/groups/standings/`
  - Returns: Standings for all groups with match results
- `GET /api/tournaments/<slug>/groups/<group_id>/matches/`
  - Returns: Match list for specific group

**Existing Template Reference**:
- Adapt `templates/spectator/_leaderboard_table.html` for group standings

**Mobile Considerations**:
- Groups stack vertically (one group table per section)
- Horizontal scroll for wide tables
- Tabs convert to dropdown for group selection

**Notes**:
- Standings calculation: Backend handles points, goal difference, tiebreakers
- Supports multi-game tournaments (eFootball, FC Mobile, Valorant, PUBG Mobile, Free Fire, CS2, FIFA, Mobile Legends, Call of Duty Mobile)
- Must show advancement criteria clearly (e.g., "Top 2 from each group advance")

---

## Section 7: Excluded Pages (Out of Scope)

The following pages exist in the current frontend but are **not** included in this tournament-focused sitemap:

### 7.1 Teams Module Pages
- `/teams/` - Team list
- `/teams/<slug>/` - Team detail
- `/teams/create/` - Team creation
- `/teams/<slug>/edit/` - Team edit
- `/teams/<slug>/members/` - Team members management
- **Status**: Existing pages work, only touch if tournament integration required (e.g., team selector in registration)

### 7.2 Community Pages
- `/community/` - Community hub
- `/forums/` - Discussion boards (if exists)
- **Status**: Deferred to post-tournament phase

### 7.3 Arena Pages
- `/arena/` - Arena homepage (if exists)
- Live event pages
- VOD pages
- **Status**: Future feature, no implementation now

### 7.4 CrownStore Pages
- `/store/` - Store homepage
- `/store/products/<slug>/` - Product detail
- `/store/cart/` - Shopping cart
- `/store/checkout/` - Checkout flow
- **Status**: Existing pages work, deferred

### 7.5 Profile Pages
- `/profile/<username>/` - User profile
- `/profile/<username>/edit/` - Edit profile
- `/profile/<username>/achievements/` - Achievements
- **Status**: Only add tournament history section (P2), no full redesign

### 7.6 Generic Dashboard Pages
- `/dashboard/` - Main dashboard (add tournament card only)
- `/dashboard/stats/` - User stats
- `/dashboard/settings/` - Settings
- **Status**: Only add tournament widgets, no full redesign

### 7.7 Authentication Pages
- `/accounts/login/` - Login
- `/accounts/signup/` - Sign up
- `/accounts/password/reset/` - Password reset
- **Status**: Use existing pages as-is

---

## URL Summary Table

| URL | Persona | Auth | Purpose | Priority |
|-----|---------|------|---------|----------|
| `/tournaments/` | Spectator, Player | No | Tournament list/discovery | P0 |
| `/tournaments/<slug>/` | Spectator, Player | No | Tournament detail (state-based) | P0 |
| `/tournaments/<slug>/register/` | Player | Yes | Registration wizard | P0 |
| `/tournaments/<slug>/register/success/` | Player | Yes | Registration success | P0 |
| `/tournaments/<slug>/register/error/` | Player | Yes | Registration error | P0 |
| `/tournaments/<slug>/lobby/` | Player | Yes (participant) | Tournament lobby/hub | P0 |
| `/tournaments/<slug>/bracket/` | Spectator, Player | No | Bracket/schedule view | P0 |
| `/tournaments/<slug>/matches/<id>/` | Spectator, Player | No (actions require auth) | Match detail | P0 |
| `/tournaments/<slug>/leaderboard/` | Spectator, Player | No | Tournament leaderboard | P0 |
| `/tournaments/<slug>/results/` | Spectator, Player | No | Final results | P0 |
| `/tournaments/<slug>/groups/` or `/standings/` | Spectator, Player | No | Group standings | P0 |
| `/tournaments/<slug>/certificate/<user>/` | Player | Yes (self only) | Certificate download | P2 |
| `/dashboard/` | Player | Yes | User dashboard (add tournament card) | P1 |
| `/dashboard/tournaments/` | Player | Yes | My tournaments (full page, P2) | P2 |
| `/dashboard/organizer/` | Organizer | Yes (role) | Organizer dashboard | P0 |
| `/dashboard/organizer/tournaments/<slug>/` | Organizer | Yes (role + owner) | Manage tournament | P0 |
| `/dashboard/organizer/tournaments/<slug>/groups/config/` | Organizer | Yes (role + owner) | Group configuration | P0 |
| `/dashboard/organizer/tournaments/<slug>/groups/draw/` | Organizer | Yes (role + owner) | Live group draw | P1 |
| `/dashboard/organizer/tournaments/<slug>/disputes/<id>/` | Organizer | Yes (role + owner) | Resolve dispute | P1 |

---

## Navigation Integration

### Navbar (Top-Level)

**Current Navbar** (as per FRONTEND_INVENTORY.md):
```
[DeltaCrown Logo] Tournaments | Teams | Dashboard | Community | Arena | CrownStore | [User Avatar]
```

**Tournament Pages Access**:
- Click `Tournaments` → `/tournaments/` (tournament list)
- From tournament list → click tournament card → `/tournaments/<slug>/` (detail)
- From tournament detail → "Register" button → `/tournaments/<slug>/register/`
- From dashboard → "My Tournaments" card → `/dashboard/tournaments/` (P2) or click tournament → detail

**Organizer Access**:
- Click `Dashboard` (if organizer role) → See "Organizer" section or tab
- From organizer dashboard → click tournament → `/dashboard/organizer/tournaments/<slug>/`

**Mobile Navbar**:
- Hamburger menu (existing pattern)
- `Tournaments` should be prominent (top-level item)
- Organizer pages accessed via dashboard hamburger

---

## Backend API Summary

**Critical APIs Needed** (must be available before frontend implementation):

**Tournament Discovery & Detail**:
- `GET /api/tournaments/discovery/` (Module 9.1)
- `GET /api/tournaments/<slug>/` (Module 9.1)
- `GET /api/tournaments/<slug>/registration-status/` (Module 4.1)
- `GET /api/tournaments/<slug>/registration-form/` (Module 4.1)

**Registration**:
- `POST /api/tournaments/<slug>/register/` (Module 4.1)
- `GET /api/payments/methods/` (Module 3.1)

**Live Tournament**:
- `GET /api/tournaments/<slug>/bracket/` (Module 5.1)
- `GET /api/tournaments/<slug>/matches/` (Module 5.1)
- `GET /api/tournaments/<slug>/leaderboard/` (Module 5.3)
- `GET /api/matches/<match_id>/` (Module 5.2)
- `POST /api/matches/<match_id>/report-score/` (Module 5.4)
- `POST /api/matches/<match_id>/dispute/` (Module 5.5)

**Results**:
- `GET /api/tournaments/<slug>/results/` (Module 6.5)
- `GET /api/tournaments/<slug>/certificate/<user_id>/` (Module 6.6, P2)

**Tournament Lobby** (NEW - Pending Backend):
- `GET /api/tournaments/<slug>/lobby/` (participant-only access)
- `POST /api/tournaments/<slug>/check-in/` (participant check-in)
- `GET /api/tournaments/<slug>/lobby/roster/` (participant list with check-in status)
- `GET /api/tournaments/<slug>/lobby/announcements/` (organizer announcements)

**Group Stages** (NEW - Pending Backend):
- `GET /api/tournaments/<slug>/groups/standings/` (group standings)
- `GET /api/tournaments/<slug>/groups/<group_id>/matches/` (group matches)
- `POST /api/organizer/tournaments/<slug>/groups/configure/` (organizer: configure groups)
- `POST /api/organizer/tournaments/<slug>/groups/generate/` (organizer: auto-generate groups)
- `GET /api/organizer/tournaments/<slug>/groups/draw/` (organizer: live draw state)
- `POST /api/organizer/tournaments/<slug>/groups/draw/next/` (organizer: draw next participant)
- `POST /api/organizer/tournaments/<slug>/groups/draw/finalize/` (organizer: finalize draw)

**Organizer**:
- `GET /api/organizer/tournaments/` (Module 9.3)
- `GET /api/organizer/tournaments/<slug>/` (Module 8.1)
- `POST /api/organizer/tournaments/<slug>/start/` (Module 8.1)
- `POST /api/organizer/tournaments/<slug>/pause/` (Module 8.1)
- `POST /api/organizer/tournaments/<slug>/cancel/` (Module 8.1)
- `GET /api/organizer/tournaments/<slug>/participants/` (Module 4.2)
- `POST /api/organizer/tournaments/<slug>/participants/<id>/remove/` (Module 4.2)
- `GET /api/organizer/tournaments/<slug>/payments/` (Module 3.1)
- `PATCH /api/organizer/matches/<match_id>/reschedule/` (Module 8.1)
- `POST /api/organizer/matches/<match_id>/override-score/` (Module 8.1)
- `GET /api/disputes/<dispute_id>/` (Module 5.5)
- `POST /api/disputes/<dispute_id>/resolve/` (Module 5.5)

**Real-Time**:
- WebSocket: `/ws/tournaments/<slug>/` (live updates)
- HTMX endpoints: All GET endpoints support HTMX polling

---

## Open Questions

1. **Single Page vs Separate Pages**: Should tournament detail adapt based on state (before/during/after) or have separate URLs for each state?
   - **Recommendation**: Single URL with state-based rendering (simpler, better SEO, no redirect needed)

2. **Mobile-First Bracket View**: Should mobile users see simplified bracket or list view by default?
   - **Recommendation**: List view (schedule) by default on mobile, bracket view optional (requires horizontal scroll)

3. **Registration Progress Save**: Should registration wizard save progress to localStorage if user abandons mid-flow?
   - **Recommendation**: P1 feature, nice to have but not critical for MVP

4. **My Tournaments Full Page**: P2 priority - create dedicated `/dashboard/tournaments/` page or keep as dashboard card only?
   - **Recommendation**: Dashboard card only for MVP, full page in later phase

5. **Certificate Preview**: Should certificates preview in modal before download, or direct download only?
   - **Recommendation**: Direct download for MVP, preview modal is P2 enhancement

---

## Success Criteria

**For Complete Sitemap**:
- ✅ All tournament pages have defined URLs
- ✅ All pages have clear personas and auth requirements
- ✅ All pages have backend API dependencies listed
- ✅ All pages have existing template references (where applicable)
- ✅ All pages have mobile considerations documented

**For Implementation**:
- URL patterns are RESTful and consistent
- Authentication/authorization enforced on all protected pages
- State-based rendering handles before/during/after tournament gracefully
- Real-time updates work on live pages (bracket, leaderboard, matches)
- Mobile experience is first-class (not an afterthought)

---

**End of Tournament Sitemap**
