# Frontend Tournament Backlog

**Date**: November 15, 2025  
**Scope**: Tournament-focused frontend features only  
**Status**: Planning phase - no implementation yet  
**Last Updated**: Enhanced with team permissions, lobby hub, group stages, match reporting, and guidance sections

---

## Overview

This backlog focuses exclusively on **Tournament lifecycle** screens and their directly related Dashboard/Admin surfaces. All other areas (Teams, Community, Arena, CrownStore, generic Profile/Dashboard) are deferred to later phases.

**Tournament Lifecycle Structure**:
1. **Before Tournament** - Discovery, detail, registration, participant hub
2. **During Tournament** - Live matches, brackets, spectator views, group stages, match reporting
3. **After Tournament** - Results, awards, certificates
4. **Organizer/Admin** - Tournament management, disputes, health metrics

**Priority Levels**:
- **P0**: Critical for tournament MVP (must have)
- **P1**: Important for good experience (should have)
- **P2**: Nice to have, can defer (could have)

**Backend Integration Status**:
- **BACKEND_IMPACT: ✓ Complete** - Backend work finished, frontend can implement
- **BACKEND_IMPACT: Pending (...)** - Backend work needed before frontend implementation

---

## 1. Before Tournament (Player Side)

### 1.1 Tournament Discovery & List View

**Item**: Tournament List Page  
**ID**: FE-T-001  
**Priority**: P0

**Description**:  
Public-facing tournament list/discovery page with filters, search, and cards displaying upcoming/open tournaments.

**Target Persona**: Player, Spectator (public)

**User Stories**:
- As a player, I want to browse all available tournaments by game
- As a player, I want to filter tournaments by status (upcoming, registration open, live, completed)
- As a player, I want to see key info (game, format, prize, date, slots) on each card
- As a player, I want to see if registration is open or closed at a glance

**Backend APIs**:
- `GET /api/tournaments/discovery/` (Module 9.1 - Discovery service)
- Returns: paginated tournament list with filters

**Components Needed**:
- Tournament card component (reuse existing card pattern from `components/card.html`)
- Filter orb component (exists: `static/siteui/js/filter-orb.js`)
- Game badge component (exists: `templates/components/game_badge.html`)
- Status pill component (new: registration open/closed/full/live/completed)
- Empty state component (exists: `templates/components/empty.html`)

**Design References**:
- PART_4.3: Tournament Management Screens → Tournament List
- PART_4.1: Design tokens for cards, spacing, colors

**Notes**:
- Leverage existing `templates/spectator/tournament_list.html` as starting point
- Must work on mobile (360px width)
- Pagination via URL params or infinite scroll (TBD)

---

### 1.2 Tournament Detail Page (Pre-Registration View)

**Item**: Tournament Detail Page (Public)  
**ID**: FE-T-002  
**Priority**: P0

**Description**:  
Comprehensive tournament detail page showing all info a player needs before deciding to register.

**Target Persona**: Player, Spectator (public)

**User Stories**:
- As a player, I want to see tournament name, game, format, schedule, prize pool
- As a player, I want to see registration requirements and eligibility
- As a player, I want to see the organizer's profile/credibility
- As a player, I want to see how many slots are filled/remaining
- As a player, I want to see the registration deadline prominently
- As a spectator, I want to see the same info for tournaments I'm following

**Backend APIs**:
- `GET /api/tournaments/{slug}/` (Tournament detail endpoint)
- `GET /api/tournaments/{slug}/registration-status/` (Check if user can register)

**Content Sections**:
1. **Hero Section**: Tournament banner, name, game badge, status
2. **Key Info Bar**: Format, date/time, prize pool, slots
3. **About Section**: Description, rules, requirements
4. **Schedule Tab**: Match schedule/bracket preview (if available)
5. **Prize Distribution**: Visual breakdown of prizes by placement
6. **Registration Section**: CTA button with status (open/closed/full)
7. **Organizer Info**: Organizer name, rating, past tournaments hosted
8. **FAQ/Rules Accordion**: Expandable sections for detailed rules

**Components Needed**:
- Hero section with background image/gradient
- Tab navigation (reuse existing pattern)
- Accordion component for rules/FAQ
- Prize breakdown visual (table or cards)
- Registration CTA button with states
- Countdown timer (if registration closing soon)

**Design References**:
- PART_4.3: Tournament Management Screens → Tournament Detail Screen
- PART_4.1: Hero section patterns, card layouts
- Existing: `templates/spectator/tournament_detail.html` as baseline

**Notes**:
- Must show real-time slot availability
- Registration button state changes based on backend status
- Mobile: hero section must be responsive, tabs convert to accordion

---

### 1.3 Tournament Registration Entry Point

**Item**: Registration Entry Point & States  
**ID**: FE-T-003  
**Priority**: P0  
**BACKEND_IMPACT**: ✓ Complete (registration_service.py with team permission validation)

**Description**:  
Clear UI indicating registration status with appropriate CTAs and messaging. Now includes team permission validation for team tournaments.

**Target Persona**: Player

**User Stories**:
- As a player, I want to see if I can register (open) or why I can't (closed, full, not eligible)
- As a player, I want a clear button to start registration when it's open
- As a player, I want to see a countdown if registration opens soon
- As a player, I want to be notified if I'm already registered
- **NEW**: As a team member, I want to know if I'm authorized to register my team for tournaments

**Registration States**:
1. **Not Open Yet**: Show countdown + "Notify Me" button (optional)
2. **Registration Open**: Show "Register Now" button (primary CTA)
3. **Registration Closed**: Show "Registration Closed" message + reason (deadline passed)
4. **Tournament Full**: Show "Tournament Full" message
5. **Already Registered**: Show "You're Registered" + manage registration link
6. **Not Eligible**: Show reason (e.g., "Team required for team tournaments")
7. **NEW - No Team Permission**: Show "You don't have permission to register this team" (for team tournaments)

**Backend APIs**:
- `GET /api/tournaments/{slug}/registration-status/` (Check eligibility)
- Returns: `{ can_register: bool, reason: string, state: enum }`
- Backend now validates team permissions (owner/manager/can_register_tournaments=True)

**Components Needed**:
- Button with dynamic states (disabled, enabled, loading)
- Status badge component
- Countdown timer component (exists: `static/js/countdown-timer.js`)
- Modal for "Already registered" details
- **NEW**: Info tooltip explaining team permission requirements

**Design References**:
- PART_4.4: Registration & Payment Flow → Entry points
- PART_4.1: Button states and CTA design

**Notes**:
- Button must be accessible (ARIA states)
- Mobile: button should be sticky at bottom
- Toast notification on state changes
- **NEW**: Display clear error message when user lacks team registration permission
- **NEW**: Link to team settings page where owners/managers can grant permissions

---

### 1.4 Tournament Registration Flow (Multi-Step)

**Item**: Registration Wizard UI  
**ID**: FE-T-004  
**Priority**: P0  
**BACKEND_IMPACT**: ✓ Complete (registration_service.py with team permission validation)

**Description**:  
Multi-step registration form adapting to tournament type (solo vs team), game-specific fields, and payment requirements. Now includes team permission checks.

**Target Persona**: Player

**User Stories**:
- As a player, I want a clear step-by-step registration process
- As a player, I want to select my team (for team tournaments) or go solo
- As a player, I want to fill game-specific custom fields (e.g., in-game ID)
- As a player, I want to see pricing and payment options clearly
- As a player, I want to confirm my registration before submitting
- **NEW**: As a team member, I want to see only teams I'm authorized to register

**Registration Steps**:

**Step 1: Eligibility Check**
- Backend validates: user logged in, meets requirements
- If team tournament: user must select a team they captain/are member of
- **NEW**: Backend validates team permission (can_register_tournaments=True OR owner/manager)

**Step 2: Team/Solo Selection** (conditional)
- For team tournaments: dropdown of eligible teams
- **NEW**: Team selector only shows teams where user has permission:
  - Teams where user is owner/manager (auto-granted permission)
  - Teams where user has explicit can_register_tournaments=True
- Display permission indicator next to each team (e.g., "Owner", "Manager", "Authorized")
- Show helper text: "Only teams you're authorized to register are shown"
- For solo tournaments: skip to Step 3

**Step 3: Custom Fields** (conditional)
- Dynamic form based on tournament's custom field configuration
- Examples: In-game ID, Discord username, preferred role
- Validation on blur, error messages inline

**Step 4: Payment Information** (conditional)
- If free: skip
- If paid: show price, breakdown, payment gateway selection
- Display payment methods (bKash, Nagad, Rocket, card via SSLCommerz)
- External payment handled by Module 3.1 backend

**Step 5: Review & Confirm**
- Summary: team/player, custom fields, payment info
- Checkbox: "I agree to tournament rules and terms"
- Submit button

**Step 6: Confirmation**
- Success state: "You're registered!" message
- Show receipt (if payment)
- CTA: "View My Tournaments" or "Return to Tournament Page"

**Backend APIs**:
- `GET /api/tournaments/{slug}/registration-form/` (Get form structure)
- `GET /api/teams/eligible-for-registration/{slug}/` (Get teams with permission)
- `POST /api/tournaments/{slug}/register/` (Submit registration - validates permission)
- `GET /api/payments/methods/` (Get payment options)
- Module 4.1: Registration validation service with team permission enforcement

**Components Needed**:
- Stepper component (progress indicator)
- Form field components (text, select, checkbox) - reuse existing
- **NEW**: Team selector dropdown with permission badges
- **NEW**: Empty state for "No eligible teams" scenario
- Payment method selector (radio cards)
- Form validator (client-side, exists: `form-validator.js`)
- Loading spinner for async validations
- Success modal/page

**Error Handling**:
- **NEW**: "Not authorized to register this team" error if permission check fails
- **NEW**: "You don't have any teams with registration permission" if eligible teams list is empty
- **NEW**: Link to team settings or team creation page in error states
- Graceful fallback if team permission API fails

**Design References**:
- PART_4.4: Registration & Payment Flow (entire section)
- PART_4.2: Form components
- Existing: `static/siteui/js/reg_wizard.js`, `static/js/dynamic-registration.js`

**Notes**:
- Must support game-specific custom fields (dynamic)
- Payment integration is read-only UI (backend handles transactions)
- Mobile: wizard should be single-column, sticky nav
- Save progress in localStorage for multi-step (optional P1)
- Must handle errors gracefully (e.g., team not eligible, slots filled during registration)
- **NEW**: Team permission model: Owner/Manager auto-granted, others need explicit permission
- **NEW**: Backend enforces XOR constraint: user_id XOR team_id (not both)

---

### 1.5 "My Tournaments" Dashboard Card

**Item**: My Tournaments Widget in Dashboard  
**ID**: FE-T-005  
**Priority**: P1

**Description**:  
Small dashboard card showing user's registered/active tournaments.

**Target Persona**: Player

**User Stories**:
- As a player, I want to see my upcoming tournaments on my dashboard
- As a player, I want to see my tournament status (registered, checked-in, eliminated, winner)
- As a player, I want quick links to tournament detail or check-in

**Display**:
- Card in `templates/dashboard/index.html` (existing dashboard)
- List of tournaments (max 5, "View All" link)
- Per tournament: name, game badge, status, next match time (if live)

**Backend APIs**:
- `GET /api/users/me/tournaments/` (User's tournament registrations)
- Returns: list of tournaments with status

**Components Needed**:
- Dashboard card component (reuse existing)
- Tournament mini-card (compact version)
- Status badge

**Design References**:
- PART_4.3: Player dashboard views
- Existing: `templates/dashboard/index.html`

**Notes**:
- This is a small addition to existing dashboard, not a full redesign
- Link to "My Tournaments" full page (deferred to P2 or later)

---

### 1.6 Tournament Lobby / Participant Hub

**Item**: Tournament Lobby Page (Participant-Only Hub)  
**ID**: FE-T-007  
**Priority**: P0  
**BACKEND_IMPACT**: Pending (needs lobby API with participant-only access control)

**Description**:  
Central hub page for registered participants during registration-closed → tournament-complete phases. Replaces need for external Discord/WhatsApp for participant coordination.

**Target Persona**: Player (registered participants only)

**User Stories**:
- As a registered participant, I want a dedicated page to see all tournament info before it starts
- As a participant, I want to check in before the tournament begins
- As a participant, I want to see the full roster of other participants
- As a participant, I want to see my match schedule once brackets are generated
- As a participant, I want to communicate with the organizer or other participants
- As a participant, I want to access tournament rules and important announcements

**Access Control**:
- URL: `/tournaments/{slug}/lobby/`
- Access: Only registered participants (backend validates registration status)
- Redirect non-participants to public tournament detail page
- Available from: Registration closes → Tournament completes

**Content Sections**:

1. **Tournament Overview Panel**
   - Tournament name, game, format, date/time
   - Registration status: "You're registered as [Solo/Team Name]"
   - Check-in status indicator

2. **Check-In Widget** (before tournament starts)
   - Check-in button (only available during check-in window)
   - Check-in deadline countdown
   - Visual indicator: "Checked In ✓" or "Not Checked In - Click to Check In"
   - Check-in confirmation modal

3. **Participant Roster**
   - List of all registered participants (players/teams)
   - Check-in status per participant (checked in/pending)
   - Total participants count vs capacity
   - Search/filter roster

4. **Match Schedule Widget** (after bracket generation)
   - "Your Next Match" highlighted card
   - Full schedule with times
   - Filter: Show only my matches / Show all matches
   - Link to live bracket view

5. **Announcements Panel**
   - Organizer announcements (chronological)
   - Important updates (schedule changes, rules clarifications)
   - Pinned messages

6. **Quick Links**
   - View Full Bracket (when available)
   - Download Tournament Rules (PDF)
   - View Prize Distribution
   - Contact Organizer

7. **Chat / Q&A Section** (Optional P2)
   - Simple message board for participant questions
   - Organizer can post and respond
   - Read-only after tournament starts (to avoid spam)

**During Tournament Guidance**:
- "What to do if opponent doesn't show up" - link to dispute flow
- "How to report match results" - link to result submission guide
- "Technical issues? Contact organizer" - organizer contact info
- "Match schedule changed? Check announcements panel"

**After Tournament Guidance** (when tournament completes):
- "How to claim your prize" - prize claim instructions
- "Download your certificate" - link to certificate download (if winner/participant)
- "Rate this tournament" - feedback form link
- "View final results" - link to results page

**Backend APIs**:
- `GET /api/tournaments/{slug}/lobby/` (Lobby data - participant-only endpoint)
- `POST /api/tournaments/{slug}/check-in/` (Check-in action)
- `GET /api/tournaments/{slug}/roster/` (Full participant list)
- `GET /api/tournaments/{slug}/announcements/` (Organizer announcements)
- `GET /api/tournaments/{slug}/lobby/schedule/` (Participant's match schedule)

**Components Needed**:
- Access gate component (redirect if not participant)
- Check-in button with countdown timer
- Roster table with status badges
- Announcement feed component
- Match schedule widget (compact view)
- Quick links card
- Modal for check-in confirmation
- Empty states (no announcements, no matches yet)

**Design References**:
- PART_4.3: Participant hub concepts
- PART_4.5: Dashboard card layouts

**States**:
1. **Pre-Check-In Window**: Show roster, announcements, "Check-in opens in X hours"
2. **Check-In Open**: Prominent check-in button, countdown, roster with check-in status
3. **Post-Check-In**: Show bracket preview, match schedule, "Tournament starts soon"
4. **During Tournament**: Show live bracket link, next match, current standings
5. **Post-Tournament**: Show final results, certificate link, feedback form

**OPTIONAL_ENHANCEMENT**:
- Push notifications 10 minutes before participant's next match
- Live chat with organizer (real-time messaging)
- Team huddle space (for team tournaments, private team-only space)
- In-lobby music/hype video embed

**Notes**:
- This page is the PRIMARY participant experience pre-tournament
- Must be mobile-optimized (participants often check on phones)
- Real-time updates for announcements and check-in status
- Consider WebSocket for live roster updates
- Link to lobby from "My Tournaments" dashboard card
- Lobby remains accessible after tournament for certificate download and feedback

---

## 2. During Tournament (Live Views)

### 2.1 Live Bracket / Schedule View

**Item**: Tournament Bracket & Schedule Page  
**ID**: FE-T-008  
**Priority**: P0

**Description**:  
Visual bracket display showing tournament structure, matches, and live scores.

**Target Persona**: Player, Spectator

**User Stories**:
- As a player, I want to see the tournament bracket with my team's path
- As a player, I want to see upcoming matches and their schedule
- As a spectator, I want to follow the bracket and see live score updates
- As a user, I want to switch between bracket view and list view

**Views**:
1. **Bracket View**: Visual tree (single-elim, double-elim)
2. **Schedule View**: List of all matches with dates/times
3. **My Matches**: Filtered view showing only user's matches (for players)

**Backend APIs**:
- `GET /api/tournaments/{slug}/bracket/` (Bracket structure)
- `GET /api/tournaments/{slug}/matches/` (Match list)
- WebSocket: `spectator_ws.js` for live score updates

**Components Needed**:
- Bracket visualization component (SVG or canvas-based)
- Match card component (compact)
- Tab switcher (Bracket / Schedule / My Matches)
- Live indicator (pulsing dot for ongoing matches)
- Filter bar (round, status)

**Design References**:
- PART_4.3: Bracket & Match Screens
- PART_4.5: Spectator views
- Existing: `legacy_backup/templates/tournaments/tournaments/bracket.html` (reference only)

**Notes**:
- Bracket rendering is complex - consider using existing library or custom SVG
- Must handle different formats (single-elim, double-elim, round-robin, swiss)
- Mobile: bracket should scroll horizontally, schedule view preferred
- Real-time updates via WebSocket (fallback to HTMX polling)

---

### 2.2 Match Detail / Lobby Page

**Item**: Live Match Detail Page  
**ID**: FE-T-009  
**Priority**: P0

**Description**:  
Detailed view of a specific match showing participants, scores, timeline, and lobby info.

**Target Persona**: Player (participating), Spectator

**User Stories**:
- As a player, I want to see my match details (opponent, time, game lobby info)
- As a player, I want to report scores after the match
- As a spectator, I want to see live scores and match timeline
- As a player, I want to dispute results if needed

**Content Sections**:
1. **Match Header**: Round, status (upcoming, live, completed)
2. **Participants**: Team/player names, logos, scores
3. **Lobby Info** (for players): Game lobby details (join instructions)
4. **Timeline**: Match events (start, score updates, end)
5. **Actions** (for players): Report score, dispute, forfeit buttons
6. **Spectator Stream** (optional P2): Embed link if available

**Backend APIs**:
- `GET /api/matches/{match_id}/` (Match detail)
- `POST /api/matches/{match_id}/report-score/` (Player reports score)
- `POST /api/matches/{match_id}/dispute/` (Initiate dispute)
- WebSocket: live updates

**Components Needed**:
- Match score display (visual vs component)
- Timeline component (chronological events)
- Action button group (report, dispute, forfeit)
- Modal for score reporting form
- Modal for dispute form

**Design References**:
- PART_4.3: Match detail screens
- PART_4.5: Spectator match view
- Existing: `templates/spectator/match_detail.html`, `templates/teams/match_detail.html`

**Notes**:
- Score reporting must be restricted to participants only
- Dispute flow triggers backend Module 5.5
- Real-time updates critical during live matches
- Mobile: stacked layout, actions sticky at bottom

---

### 2.3 Live Leaderboard (Tournament-Level)

**Item**: Tournament Leaderboard Page  
**ID**: FE-T-010  
**Priority**: P0

**Description**:  
Real-time ranking of participants based on wins/losses, points, or tournament format rules.

**Target Persona**: Player, Spectator

**User Stories**:
- As a player, I want to see my current ranking in the tournament
- As a spectator, I want to see the top players/teams
- As a user, I want the leaderboard to update live as matches conclude

**Display**:
- Table format: Rank, Team/Player, Games Played, Wins, Losses, Points
- Highlight current user's row (if player)
- Pagination or infinite scroll for large tournaments
- Filter by group (for round-robin/swiss formats)

**Backend APIs**:
- `GET /api/tournaments/{slug}/leaderboard/` (Leaderboard data)
- WebSocket: live rank updates
- HTMX: fallback polling (`hx-get`, `hx-trigger="every 10s"`)

**Components Needed**:
- Data table component with sorting
- Rank badge (medals for top 3, numbers for others)
- User highlight (different bg color for current user)
- Live indicator

**Design References**:
- PART_4.3: Leaderboard/standings screens
- PART_4.5: Spectator leaderboard
- Existing: `templates/spectator/_leaderboard_table.html` (partial)

**Notes**:
- Must handle tie-breaking rules (backend calculates ranks)
- Real-time updates via WebSocket + HTMX fallback
- Mobile: horizontal scroll for wide tables, consider card view alternative

---

### 2.4 Spectator View (Public Live Page)

**Item**: Public Spectator Tournament Page  
**ID**: FE-T-006  
**Priority**: P1

**Description**:  
Public-facing page for spectators to watch tournament progress without logging in.

**Target Persona**: Spectator (public, not logged in)

**User Stories**:
- As a spectator, I want to see live matches and scores without logging in
- As a spectator, I want to see the bracket and leaderboard
- As a spectator, I want to follow my favorite team's progress

**Content**:
- Tab navigation: Overview, Bracket, Leaderboard, Matches
- Overview: Tournament info, current round, featured matches
- Bracket/Leaderboard/Matches: Same as player views but read-only
- No score reporting or dispute actions (spectator-only)

**Backend APIs**:
- Same as FE-T-006, FE-T-007, FE-T-008 (public endpoints)

**Components Needed**:
- Same as player views but with restricted actions
- "Login to participate" CTA if not authenticated

**Design References**:
- PART_4.5: Spectator & Mobile Accessibility
- Existing: `templates/spectator/tournament_detail.html`

**Notes**:
- This may be the same page as tournament detail (FE-T-002) but with live data during tournament
- Consider unified page with state-driven UI (before/during/after tournament)
- Must be mobile-optimized (high mobile traffic expected)

---

### 2.5 Group Stage Management & Draw

**Item**: Group Stage Configuration & Live Draw Interface  
**ID**: FE-T-011, FE-T-012, FE-T-013  
**Priority**: P0 (critical for multi-game support)  
**BACKEND_IMPACT**: Pending (needs group stage models, draw service, standings calculation for all 9 games)

**Description**:  
UI for organizers to configure group stages and perform live draws, plus group standings pages for all supported games.

**Target Persona**: Organizer (config/draw), Player/Spectator (standings view)

**Supported Games** (9 total):
1. eFootball
2. FC Mobile
3. Valorant
4. PUBG Mobile
5. Free Fire
6. CS2 (Counter-Strike 2)
7. FIFA
8. Mobile Legends
9. Call of Duty Mobile

---

#### FE-T-011: Group Configuration Interface

**User Stories**:
- As an organizer, I want to configure how many groups my tournament has
- As an organizer, I want to set participants per group
- As an organizer, I want to choose group naming (Group A/B/C or custom names)

**Configuration Options**:
- Number of groups (2-8)
- Participants per group (auto-calculated or manual override)
- Group names (auto: A/B/C/D or custom)
- Seeding rules (random, ranked, manual)

**Backend APIs**:
- `POST /api/organizer/tournaments/{slug}/groups/configure/` (Set group config)

**Components**:
- Group configuration form
- Preview of group structure
- Validation (total capacity matches registration count)

**OPTIONAL_ENHANCEMENT**:
- AI-suggested group configuration based on participant count
- Historical data on optimal group sizes for specific games

---

#### FE-T-012: Live Draw / Random Assignment Interface

**User Stories**:
- As an organizer, I want to perform a live draw to assign participants to groups
- As an organizer, I want the draw to be transparent and fair (provably random)
- As a spectator, I want to watch the live draw happen in real-time (optional)

**Draw Interface**:
- Button: "Start Live Draw"
- Animation showing participants being assigned to groups
- Visual: Cards flipping/sliding into groups
- Progress indicator (X of Y participants assigned)
- Confirmation after draw completes

**Draw Methods**:
1. **Random Draw**: Fully random assignment
2. **Seeded Draw**: Ranked participants distributed evenly
3. **Manual Assignment**: Organizer drags participants to groups

**Backend APIs**:
- `POST /api/organizer/tournaments/{slug}/groups/draw/` (Execute draw)
- Returns: Final group assignments
- Optional: WebSocket for live draw animation data

**Components**:
- Draw animation component
- Drag-and-drop interface (for manual assignment)
- Confirmation modal
- Provability display (draw seed/hash for transparency)

**OPTIONAL_ENHANCEMENT**:
- Public live stream of draw (spectators can watch)
- Draw replay/history
- Export group assignments as image/PDF for sharing

---

#### FE-T-013: Group Standings Page (Multi-Game)

**User Stories**:
- As a player, I want to see my group's standings with points and rankings
- As a player, I want to see standings for all groups in the tournament
- As a spectator, I want to understand how groups advance to playoffs

**Standings Display** (adapts per game):

**Common to All Games**:
- Group name header
- Table columns: Rank, Team/Player, Played, Wins, Losses, Points
- Highlight: Top N teams advance (configurable per tournament)
- Color coding: Green for advancing, gray for eliminated

**Game-Specific Columns**:

- **eFootball, FC Mobile, FIFA**: Goals For, Goals Against, Goal Difference
- **Valorant, CS2**: Rounds Won, Rounds Lost, Round Difference
- **PUBG Mobile, Free Fire**: Total Kills, Total Placement Points, Average Survival Time
- **Mobile Legends**: Kills, Deaths, Assists, KDA Ratio
- **Call of Duty Mobile**: Eliminations, Deaths, K/D Ratio, Score

**Group Stage Formats**:
1. **Round Robin**: Each team plays every other team in group
2. **Swiss System**: Pairing based on current standings
3. **Double Round Robin**: Play each team twice

**Backend APIs**:
- `GET /api/tournaments/{slug}/groups/` (All groups list)
- `GET /api/tournaments/{slug}/groups/{group_id}/standings/` (Group standings)
- Game-specific scoring logic handled by backend

**Components**:
- Group selector tabs (Group A, Group B, etc.)
- Standings table (sortable)
- Game-specific stat columns (dynamic based on game type)
- Advancement indicator (visual line showing cutoff)
- Match schedule per group

**Real-Time Updates**:
- WebSocket for live standings updates during matches
- HTMX fallback polling every 30 seconds

**During Tournament Guidance**:
- "How do tiebreakers work?" - tooltip explaining tiebreaker rules per game
- "How many teams advance?" - clear visual indicator
- "What if teams have equal points?" - tiebreaker criteria display

**OPTIONAL_ENHANCEMENT**:
- Head-to-head record display in standings
- Mini-bracket preview showing potential playoff matchups
- Stats leaders per group (top scorer, most kills, etc.)
- Export standings as image for social sharing

**Notes**:
- Group stage system must be flexible for all 9 games
- Each game has different scoring metrics (goals vs kills vs rounds)
- Backend must handle game-specific standings calculation
- Frontend must adapt table columns dynamically based on game type
- Mobile: horizontal scroll for wide tables, consider card view

---

### 2.6 Match Result Reporting & Disputes

**Item**: Match Result Submission & Dispute Resolution Flow  
**ID**: FE-T-014, FE-T-015, FE-T-016, FE-T-017  
**Priority**: P0 (critical for match integrity)  
**BACKEND_IMPACT**: Pending (needs dispute models, resolution workflow, evidence storage)

**Description**:  
Two-phase flow for match results: participants submit → organizer approves. Includes dispute system when results don't match.

**Target Persona**: Player (submission), Organizer (approval), Admin (dispute resolution)

---

#### FE-T-014: Participant Match Result Submission

**User Stories**:
- As a participant, I want to submit my match result after playing
- As a participant, I want to upload a screenshot as proof
- As a participant, I want to see if my opponent submitted a different result

**Result Submission Flow**:

1. **Access Point**: 
   - From match detail page (FE-T-009)
   - Button: "Report Result" (only available to match participants)
   - Available: Match scheduled time → 2 hours after match end

2. **Submission Form**:
   - Score input fields (depends on game type)
   - Winner selection (Me / Opponent / Draw)
   - Screenshot upload (required or optional based on tournament rules)
   - Notes field (optional, e.g., "Opponent left mid-game")

3. **Screenshot Upload**:
   - Drag-and-drop or file picker
   - Image preview before upload
   - Max file size: 5MB
   - Formats: JPG, PNG
   - Multiple screenshots allowed (up to 3)

4. **Confirmation**:
   - Review submitted data
   - "Submit Result" button
   - Success message: "Result submitted! Waiting for opponent/organizer approval"

**Backend APIs**:
- `POST /api/matches/{match_id}/submit-result/` (Submit result with screenshot)
- `POST /api/matches/{match_id}/upload-evidence/` (Upload screenshot)

**Components**:
- Result submission form (game-specific fields)
- File upload component with preview
- Score input (adapts to game: goals, rounds, kills, etc.)
- Confirmation modal

**States**:
- **No submissions yet**: Both participants can submit
- **One submitted**: Show "Your opponent submitted [score]. Do you agree?" with Accept/Dispute options
- **Both submitted & match**: Auto-approved (if both submitted same result)
- **Both submitted & mismatch**: Dispute opened automatically

**During Tournament Guidance**:
- "Always take a screenshot immediately after match ends"
- "You have 2 hours to submit your result"
- "If you don't submit, organizer may rule against you"

**OPTIONAL_ENHANCEMENT**:
- OCR to auto-extract score from screenshot
- Video upload support (for high-stakes matches)
- Quick-submit templates for common game results

---

#### FE-T-015: Organizer Result Approval/Override Interface

**User Stories**:
- As an organizer, I want to see all pending match results
- As an organizer, I want to approve results when both parties agree
- As an organizer, I want to override results if I have evidence

**Organizer Approval Dashboard**:

1. **Pending Results Table**:
   - Columns: Match, Participants, Submitted Results, Status, Actions
   - Filter: Pending approval, Disputed, Approved
   - Sort: By match time, by priority

2. **Per-Match View**:
   - Player A submission: [score] + screenshot
   - Player B submission: [score] + screenshot
   - Comparison view (side-by-side)
   - Actions: Approve A, Approve B, Override (enter own result)

3. **Approval Actions**:
   - **Approve**: Accept one party's submission
   - **Override**: Enter organizer-determined result (requires reason)
   - **Request Re-submission**: Ask participants to resubmit with better evidence

4. **Bulk Actions**:
   - "Approve All Matching" (where both parties submitted same result)
   - Export pending results list

**Backend APIs**:
- `GET /api/organizer/tournaments/{slug}/pending-results/` (Pending results list)
- `POST /api/matches/{match_id}/approve-result/` (Approve one submission)
- `POST /api/matches/{match_id}/override-result/` (Organizer override)

**Components**:
- Results table with filtering
- Side-by-side comparison view
- Screenshot lightbox viewer
- Override form with reason field
- Bulk action toolbar

**After Tournament Guidance** (for organizer):
- "Review all results before finalizing tournament"
- "Always document override reasons for transparency"
- "Export match results for record-keeping"

**OPTIONAL_ENHANCEMENT**:
- AI-assisted result verification (analyze screenshots)
- Organizer can flag suspicious results for manual review
- Automatic approval for results with matching screenshots

---

#### FE-T-016: Dispute Submission Flow

**User Stories**:
- As a participant, I want to dispute a result if it's incorrect
- As a participant, I want to explain why I'm disputing
- As a participant, I want to provide additional evidence

**Dispute Submission**:

1. **Trigger Points**:
   - When opponent submits different result: "Dispute Result" button appears
   - When organizer approves opponent's submission: "File Dispute" link (within 24h)

2. **Dispute Form**:
   - Reason dropdown: Wrong score, Opponent cheated, Technical issue, Other
   - Detailed explanation (text area)
   - Additional evidence upload (screenshots, video link)
   - Submit button

3. **Dispute States**:
   - **Open**: Waiting for organizer review
   - **Under Review**: Organizer is investigating
   - **Resolved - Accepted**: Your dispute was accepted
   - **Resolved - Rejected**: Your dispute was rejected
   - **Expired**: Dispute window closed

4. **Dispute Timeline**:
   - Show all events: Submission, Dispute filed, Organizer actions, Resolution
   - Timestamps for each event

**Backend APIs**:
- `POST /api/matches/{match_id}/dispute/` (File dispute)
- `GET /api/disputes/{dispute_id}/` (Dispute detail)
- `POST /api/disputes/{dispute_id}/add-evidence/` (Add more evidence)

**Components**:
- Dispute form with reason selection
- Evidence upload (reuse from FE-T-014)
- Dispute timeline component
- Status badge (open/resolved/expired)

**During Tournament Guidance**:
- "You have 24 hours to file a dispute after result approval"
- "Provide clear evidence (screenshots, video)"
- "Organizer decision is final"

**OPTIONAL_ENHANCEMENT**:
- Dispute voting (other participants vote on outcome)
- Appeal process for rejected disputes
- Dispute history per participant (to track serial disputers)

---

#### FE-T-017: Admin Dispute Resolution Panel

**User Stories**:
- As an organizer/admin, I want to see all active disputes
- As an organizer, I want to review evidence from both parties
- As an organizer, I want to make a final ruling on disputes

**Dispute Resolution Interface**:

1. **Dispute List Dashboard**:
   - All disputes for tournament
   - Priority sort: Oldest first, High-stakes matches first
   - Filter: Open, Under Review, Resolved

2. **Dispute Detail View**:
   - **Match Context**: Participants, scheduled time, tournament round
   - **Original Submissions**: Player A result + evidence, Player B result + evidence
   - **Dispute Reason**: Disputing party's explanation
   - **Additional Evidence**: Any extra screenshots/videos submitted
   - **Chat Log** (optional): Communication between organizer and participants

3. **Resolution Actions**:
   - **Accept Disputant**: Change result to disputing party's submission
   - **Reject Dispute**: Keep original result
   - **Override**: Enter new result (neither party was correct)
   - **Request More Evidence**: Ask both parties for additional proof
   - **Escalate**: Flag for higher-level admin review

4. **Resolution Form**:
   - Selected action
   - Final score (if overriding)
   - Admin notes (explanation visible to participants)
   - Confirmation checkbox: "I have reviewed all evidence"
   - Submit resolution

5. **Audit Trail**:
   - All actions logged with timestamps
   - Who made the decision
   - Evidence reviewed
   - Reason for decision

**Backend APIs**:
- `GET /api/organizer/disputes/` (All disputes for organizer's tournaments)
- `POST /api/disputes/{dispute_id}/resolve/` (Resolve dispute)
- `POST /api/disputes/{dispute_id}/request-evidence/` (Ask for more evidence)
- `GET /api/disputes/{dispute_id}/timeline/` (Full dispute history)

**Components**:
- Dispute list table
- Evidence viewer (image gallery, video embed)
- Resolution form
- Timeline/audit log component
- Participant contact buttons (send message)

**After Tournament Guidance** (for organizer):
- "All disputes must be resolved before tournament completion"
- "Document your reasoning for transparency"
- "Export dispute resolutions for post-tournament review"

**OPTIONAL_ENHANCEMENT**:
- Video call integration (organizer can call participants for clarification)
- Community jury (trusted members vote on disputes)
- Dispute analytics (common dispute reasons, resolution times)
- Auto-suggest resolution based on evidence quality

**Notes**:
- Disputes are HIGH-STAKES - UI must be clear and admin-friendly
- Must support multiple evidence formats (images, videos, links)
- Resolution must be logged for transparency and accountability
- Mobile: simplified view, focus on essential evidence
- Consider implementing 24-hour dispute window (backend enforces)
- Two-phase approval flow reduces disputes (both parties submit first)

---

## 3. After Tournament (Results & Recap)

### 3.1 Final Results Page

**Item**: Tournament Results & Recap Page  
**ID**: FE-T-018  
**Priority**: P0

**Description**:  
Post-tournament page showing final rankings, winners, and match history.

**Target Persona**: Player, Spectator

**User Stories**:
- As a player, I want to see my final placement and stats
- As a spectator, I want to see the winners and prize distribution
- As a user, I want to see the final bracket with all scores

**Content Sections**:
1. **Winners Section**: Top 3 teams/players with podium visual
2. **Final Leaderboard**: Complete rankings
3. **Match History**: All matches with final scores
4. **Stats Summary**: Total matches, upsets, MVP (if supported)
5. **Prize Distribution**: Who won what (if prizes configured)

**Backend APIs**:
- `GET /api/tournaments/{slug}/results/` (Final results)
- Returns: rankings, winners, match history, stats

**Components Needed**:
- Podium component (visual top 3)
- Final leaderboard table
- Match history cards (expandable)
- Stats cards (total matches, duration, participants)

**Design References**:
- PART_4.3: Results and recap screens
- PART_4.6: Animation patterns for winner reveals

**Notes**:
- Should be archived/permanent (accessible after tournament ends)
- Consider confetti animation for top 3 (subtle, not over-the-top)
- Mobile: podium stacks vertically

---

### 3.2 Certificates & Shareable Summary

**Item**: Winner Certificates & Social Sharing  
**ID**: FE-T-019  
**Priority**: P2

**Description**:  
Generate shareable certificates for winners and participants, plus social media cards.

**Target Persona**: Player (winners)

**User Stories**:
- As a winner, I want to download a certificate of achievement
- As a player, I want to share my tournament result on social media
- As an organizer, I want winners to promote the tournament brand

**Features**:
- PDF certificate generation (backend via Module 6.6)
- Social media card preview (Open Graph, Twitter Card)
- "Share to Twitter/Facebook" buttons
- Download certificate button

**Backend APIs**:
- `GET /api/tournaments/{slug}/certificate/{user_id}/` (Certificate PDF)
- Module 6.6: Certificate service

**Components Needed**:
- Certificate preview modal
- Social share buttons
- Download button

**Design References**:
- PART_4.3: Certificates section (if mentioned)
- PART_4.6: Animation for certificate reveal

**Notes**:
- P2 priority - can defer if time-constrained
- Certificate design should be professional and branded
- Consider using existing `static/siteui/og/` assets for social cards

---

## 4. Organizer / Admin (Tournament Management)

### 4.1 Organizer Tournament Dashboard

**Item**: Organizer's Tournament Overview Dashboard  
**ID**: FE-T-020  
**Priority**: P0

**Description**:  
Dashboard for organizers to manage their tournaments, see key metrics, and take actions.

**Target Persona**: Organizer (tournament host)

**User Stories**:
- As an organizer, I want to see all my tournaments (draft, live, completed)
- As an organizer, I want to see key metrics (registrations, revenue, active matches)
- As an organizer, I want quick links to manage specific tournaments

**Display**:
- List/grid of organizer's tournaments
- Per tournament card: name, status, registration count, next action needed
- Summary metrics: Total tournaments, total revenue, avg participants
- CTAs: Create Tournament, View Details, Manage

**Backend APIs**:
- `GET /api/organizer/tournaments/` (Organizer's tournaments)
- Module 9.3: Organizer dashboard service

**Components Needed**:
- Dashboard cards (reuse existing)
- Metric summary cards
- Tournament list table
- Status badges

**Design References**:
- PART_4.3: Organizer dashboard screens
- Existing: `templates/dashboard/index.html` (adapt for organizer view)

**Notes**:
- This dashboard is accessed via navbar → Dashboard (with organizer role)
- Role-based rendering: show organizer view if user has organizer permissions
- Mobile: card layout, stacked metrics

---

### 4.2 Tournament Management UI (Per-Tournament Admin)

**Item**: Single Tournament Management Page  
**ID**: FE-T-021  
**Priority**: P0

**Description**:  
Comprehensive admin page for organizers to manage a specific tournament.

**Target Persona**: Organizer

**Tabs/Sections**:
1. **Overview**: Status, start/end date, registration count, actions (start, pause, cancel)
2. **Participants**: List of registered teams/players with status (confirmed, pending, checked-in)
3. **Payments**: Revenue overview, pending payments (read-only, handled by backend)
4. **Matches**: Match list with actions (schedule, reschedule, edit scores)
5. **Disputes**: Active disputes list with actions (view, resolve)
6. **Health**: Tournament health metrics from Module 2.5 (system status, API latency, error rates)

**Backend APIs**:
- `GET /api/organizer/tournaments/{slug}/` (Tournament admin data)
- `POST /api/organizer/tournaments/{slug}/start/` (Start tournament)
- `POST /api/organizer/tournaments/{slug}/pause/` (Pause tournament)
- Module 8.1: Admin lock enforcement (ensures organizer permissions)

**Components Needed**:
- Tab navigation
- Data tables for participants, payments, matches, disputes
- Action button groups (start, pause, edit)
- Modal for confirmation dialogs
- Health metrics dashboard (gauges, charts)

**Design References**:
- PART_4.3: Tournament management screens (organizer section)
- PART_2.5: Health metrics visualization

**Notes**:
- Must enforce organizer permissions (backend validates, frontend hides/disables)
- Critical actions (start, cancel) require confirmation modal
- Mobile: tabs convert to accordion or dropdown selector

---

### 4.3 Participant Management

**Item**: Manage Tournament Participants UI  
**ID**: FE-T-022  
**Priority**: P1

**Description**:  
Interface for organizers to view, approve, or remove participants.

**Target Persona**: Organizer

**User Stories**:
- As an organizer, I want to see all registered participants
- As an organizer, I want to approve pending registrations (if manual approval)
- As an organizer, I want to remove participants (with reason)
- As an organizer, I want to see payment status per participant

**Display**:
- Table: Participant name, team (if applicable), registration date, payment status, actions
- Filters: Status (confirmed, pending, disqualified), payment (paid, unpaid)
- Bulk actions: Approve all, export list

**Backend APIs**:
- `GET /api/organizer/tournaments/{slug}/participants/` (Participant list)
- `POST /api/organizer/tournaments/{slug}/participants/{id}/approve/` (Approve)
- `POST /api/organizer/tournaments/{slug}/participants/{id}/remove/` (Remove)

**Components Needed**:
- Data table with sorting and filtering
- Action buttons (approve, remove)
- Modal for remove confirmation (must provide reason)
- Bulk selection checkboxes

**Design References**:
- PART_4.3: Participant management section

**Notes**:
- Remove action triggers backend validation (Module 4.2)
- Must show reason for removal (logged in backend)
- Mobile: table rows become cards

---

### 4.4 Payment Review UI

**Item**: Tournament Payment Overview (Read-Only)  
**ID**: FE-T-023  
**Priority**: P1

**Description**:  
Read-only dashboard showing payment summary and per-participant payment status.

**Target Persona**: Organizer

**User Stories**:
- As an organizer, I want to see total revenue and pending payments
- As an organizer, I want to see which participants have paid and which haven't
- As an organizer, I want to download payment reports (CSV export)

**Display**:
- Summary cards: Total expected, total received, pending, refunded
- Table: Participant, amount, status (paid, pending, refunded), date
- Export button (CSV download)

**Backend APIs**:
- `GET /api/organizer/tournaments/{slug}/payments/` (Payment summary)
- `GET /api/organizer/tournaments/{slug}/payments/export/` (CSV export)
- Module 3.1: Payment service (read-only UI, no transaction actions)

**Components Needed**:
- Summary metric cards
- Payment table with status badges
- Export button
- Date range filter (optional)

**Design References**:
- PART_4.4: Payment screens for organizers

**Notes**:
- This is read-only - organizers cannot process refunds from frontend (admin action)
- Must clearly show payment gateway (bKash, Nagad, card) per transaction
- Mobile: summary cards stack, table scrolls horizontally

---

### 4.5 Match Management UI

**Item**: Organizer Match Control Panel  
**ID**: FE-T-024  
**Priority**: P1

**Description**:  
Interface for organizers to manage matches (schedule, reschedule, override scores, forfeit).

**Target Persona**: Organizer

**User Stories**:
- As an organizer, I want to see all matches in the tournament
- As an organizer, I want to reschedule a match if needed
- As an organizer, I want to override a disputed score
- As an organizer, I want to mark a match as forfeited

**Display**:
- Match list table: Match ID, participants, scheduled time, status, actions
- Filters: Round, status (scheduled, live, completed, disputed)
- Per-match actions: Edit time, override score, forfeit

**Backend APIs**:
- `GET /api/organizer/tournaments/{slug}/matches/` (Match list)
- `PATCH /api/organizer/matches/{match_id}/reschedule/` (Change time)
- `POST /api/organizer/matches/{match_id}/override-score/` (Set final score)
- `POST /api/organizer/matches/{match_id}/forfeit/` (Mark forfeit)

**Components Needed**:
- Match table
- Modal for reschedule (datetime picker)
- Modal for override score (score input form)
- Modal for forfeit confirmation

**Design References**:
- PART_4.3: Match management for organizers

**Notes**:
- Critical actions (override, forfeit) must require confirmation + reason
- Backend logs all organizer actions (audit trail from Module 8.3)
- Mobile: match cards with dropdown actions

---

### 4.6 Dispute Resolution UI

**Item**: Dispute Management Dashboard  
**ID**: FE-T-025  
**Priority**: P1

**Description**:  
Interface for organizers to view and resolve match disputes.

**Target Persona**: Organizer

**User Stories**:
- As an organizer, I want to see all active disputes
- As an organizer, I want to review evidence submitted by both parties
- As an organizer, I want to resolve disputes by accepting one party's claim or overriding

**Display**:
- Dispute list table: Match, disputing party, reason, status (open, resolved)
- Per dispute detail view:
  - Match info
  - Original score vs disputed score
  - Evidence submitted (text, screenshots if supported)
  - Resolution actions: Accept Team A, Accept Team B, Override Score, Reject Dispute

**Backend APIs**:
- `GET /api/organizer/tournaments/{slug}/disputes/` (Dispute list)
- `GET /api/disputes/{dispute_id}/` (Dispute detail)
- `POST /api/disputes/{dispute_id}/resolve/` (Resolve dispute)
- Module 5.5: Dispute service

**Components Needed**:
- Dispute table with status badges
- Dispute detail modal/page
- Evidence display (text, image gallery if supported)
- Resolution action buttons
- Timeline of dispute events

**Design References**:
- PART_4.3: Dispute resolution screens

**Notes**:
- Must show both parties' submitted evidence clearly
- Resolution must require confirmation (high-stakes action)
- Backend enforces 24-hour dispute window (Module 5.5)
- Mobile: dispute cards with expandable detail

---

### 4.7 Tournament Health Metrics View

**Item**: Organizer Health Dashboard  
**ID**: FE-T-026  
**Priority**: P2

**Description**:  
Real-time health metrics for a tournament, leveraging Module 2.5 observability backend.

**Target Persona**: Organizer, Admin

**User Stories**:
- As an organizer, I want to see if the tournament system is healthy
- As an organizer, I want to see API latency and error rates
- As an admin, I want to monitor all active tournaments

**Metrics Displayed**:
- System status: Operational, degraded, down
- API latency: Registration, match reporting, leaderboard updates
- Error rates: Failed match reports, payment errors
- Active connections: WebSocket connections, HTMX polling clients
- Alerts: Critical issues requiring attention

**Backend APIs**:
- `GET /api/health/tournament/{slug}/` (Module 2.5 health endpoint)
- WebSocket: Live metric updates

**Components Needed**:
- Gauge charts for latency
- Status indicator (green/yellow/red)
- Alert list with severity badges
- Time-series charts (optional P2)

**Design References**:
- PART_2.5: Observability & monitoring specs
- Existing: Consider using existing `arena-watch.js` patterns

**Notes**:
- P2 priority - nice to have but not critical for MVP
- This is mostly for organizers running large tournaments
- Mobile: simplified card view with key metrics only

---

## 5. Integration with Existing Surfaces

### 5.1 Dashboard Integration

**Item**: Tournament Widget in User Dashboard  
**ID**: FE-T-027  
**Priority**: P1

**Description**:  
Add tournament-related cards to existing `templates/dashboard/index.html`.

**Changes to Existing Dashboard**:
- Add "My Tournaments" card (FE-T-005 implementation)
- If user is organizer: Add "My Hosted Tournaments" card
- Show upcoming matches from registered tournaments
- Show check-in reminder if tournament starts soon

**Backend APIs**:
- `GET /api/users/me/tournaments/` (Player tournaments)
- `GET /api/organizer/tournaments/` (Organizer tournaments)

**Notes**:
- Minimal changes to existing dashboard structure
- Just adding new cards, not redesigning entire dashboard
- Dashboard redesign deferred to Phase Later

---

### 5.2 Profile Integration

**Item**: Tournament History in User Profile  
**ID**: FE-T-028  
**Priority**: P2

**Description**:  
Add tournament participation history to user profile page.

**Changes to Existing Profile**:
- Add "Tournament History" tab or section in `templates/user_profile/profile_modern.html`
- Show list of tournaments participated in, placements, win/loss record
- Link to tournament results pages

**Backend APIs**:
- `GET /api/users/{username}/tournament-history/` (Public tournament history)

**Notes**:
- P2 priority - can defer
- Public profiles should show tournament achievements
- Profile redesign deferred to Phase Later

---

## 6. Excluded from This Backlog (Phase Later)

The following are explicitly **not** included in this tournament-first frontend plan:

### 6.1 Teams Module Polish
- Team list redesign
- Team detail page improvements
- Team creation flow polish
- Team analytics enhancements
- **Status**: Use existing pages as-is, only touch if tournament flows require integration

### 6.2 Community Features
- Community hub redesign
- Social features
- Discussion boards
- User-generated content
- **Status**: Deferred to post-tournament phase

### 6.3 Arena Features
- Arena homepage/hub
- Live event streaming
- VOD platform
- **Status**: Future feature, rough ideas only, no implementation

### 6.4 CrownStore (E-commerce)
- Store redesign
- Product pages
- Shopping cart improvements
- Checkout flow polish
- **Status**: Existing pages work, deferred

### 6.5 Generic Dashboard Redesign
- Full dashboard redesign
- Analytics widgets
- Customizable dashboard
- **Status**: Only add tournament widgets (FE-T-019), no full redesign

### 6.6 Profile Module Redesign
- Profile page redesign
- Edit profile improvements
- Privacy settings
- **Status**: Only add tournament history (FE-T-020), no full redesign

---

## Priority Summary

### P0 (Must Have for Tournament MVP)
- FE-T-001: Tournament List Page
- FE-T-002: Tournament Detail Page
- FE-T-003: Registration Entry Point & States (✓ Backend Complete)
- FE-T-004: Registration Wizard UI (✓ Backend Complete)
- FE-T-007: Tournament Lobby / Participant Hub
- FE-T-008: Live Bracket / Schedule View
- FE-T-009: Live Match Detail Page
- FE-T-010: Tournament Leaderboard
- FE-T-011: Group Configuration Interface
- FE-T-012: Live Draw / Random Assignment
- FE-T-013: Group Standings Page (Multi-Game)
- FE-T-014: Participant Match Result Submission
- FE-T-015: Organizer Result Approval/Override
- FE-T-016: Dispute Submission Flow
- FE-T-017: Admin Dispute Resolution Panel
- FE-T-018: Final Results Page
- FE-T-020: Organizer Tournament Dashboard
- FE-T-021: Tournament Management UI

### P1 (Important for Good Experience)
- FE-T-005: My Tournaments Dashboard Card
- FE-T-006: Public Spectator View
- FE-T-022: Participant Management
- FE-T-023: Payment Review UI
- FE-T-024: Match Management UI
- FE-T-025: Dispute Resolution UI (Admin View)
- FE-T-027: Dashboard Integration

### P2 (Nice to Have, Can Defer)
- FE-T-019: Certificates & Social Sharing
- FE-T-026: Tournament Health Metrics View
- FE-T-028: Profile Integration

---

## Implementation Order (Recommended)

**Sprint 1: Before Tournament (Player)**
1. FE-T-001: Tournament List
2. FE-T-002: Tournament Detail
3. FE-T-003: Registration Entry Point (✓ Backend Complete)

**Sprint 2: Registration Flow**
4. FE-T-004: Registration Wizard (✓ Backend Complete - includes team permissions)
5. FE-T-005: My Tournaments Dashboard Card

**Sprint 3: Participant Hub & Lobby**
6. FE-T-007: Tournament Lobby / Participant Hub (requires backend work)
7. FE-T-027: Dashboard Integration (link to lobby)

**Sprint 4: Group Stage System**
8. FE-T-011: Group Configuration Interface (requires backend work)
9. FE-T-012: Live Draw Interface (requires backend work)
10. FE-T-013: Group Standings Page (multi-game support) (requires backend work)

**Sprint 5: Match Reporting Flow**
11. FE-T-014: Participant Result Submission (requires backend work)
12. FE-T-015: Organizer Result Approval (requires backend work)
13. FE-T-016: Dispute Submission Flow (requires backend work)
14. FE-T-017: Admin Dispute Resolution (requires backend work)

**Sprint 6: During Tournament (Live Views)**
15. FE-T-008: Bracket/Schedule View
16. FE-T-009: Match Detail Page (with result reporting integration)
17. FE-T-010: Tournament Leaderboard
18. FE-T-006: Public Spectator View

**Sprint 7: After Tournament**
19. FE-T-018: Final Results Page
20. FE-T-019: Certificates & Social Sharing (if time permits)

**Sprint 8: Organizer Dashboard**
21. FE-T-020: Organizer Dashboard
22. FE-T-021: Tournament Management UI

**Sprint 9: Organizer Management**
23. FE-T-022: Participant Management
24. FE-T-023: Payment Review
25. FE-T-024: Match Management

**Sprint 10: Organizer Advanced**
26. FE-T-025: Dispute Resolution UI
27. FE-T-026: Health Metrics (if time permits)
28. FE-T-028: Profile Integration (if time permits)

---

## Open Questions & Dependencies

### Questions for Review

1. **Bracket Rendering**: Should we use an existing library (e.g., d3-bracket) or build custom SVG? Custom has better control but more complex.

2. **Real-Time Strategy**: Primary WebSocket + HTMX fallback, or HTMX-first with WebSocket as enhancement? Current analysis shows both exist.

3. **Mobile Navigation**: Tournament pages are accessed from navbar → Tournaments, but should there be a separate mobile bottom nav item or use existing hamburger menu?

4. **Registration Payment UX**: External payment (SSLCommerz) opens new window/redirect - should we use iframe or full redirect? Current backend uses redirect.

5. **Certificates**: PDF generation is backend (Module 6.6) - should frontend just download link or preview in modal first?

6. **Spectator Login Wall**: Should spectators be required to log in to view live tournaments, or fully public? Current analysis shows public spectator pages exist.

### Dependencies on Backend

**Completed Backend Work** (✓ Ready for frontend implementation):
- **Registration with Team Permissions** (FE-T-003, FE-T-004):
  - `apps/tournaments/services/registration_service.py` with team permission validation
  - Supports owner/manager auto-permission + explicit can_register_tournaments grants
  - XOR constraint: user_id XOR team_id (not both)
  - 11 comprehensive tests passing

**Critical APIs Needed** (must be developed before frontend implementation):
- **Tournament Lobby APIs** (FE-T-007):
  - `GET /api/tournaments/{slug}/lobby/` (participant-only access)
  - `POST /api/tournaments/{slug}/check-in/`
  - `GET /api/tournaments/{slug}/roster/`
  - `GET /api/tournaments/{slug}/announcements/`

- **Group Stage System** (FE-T-011, FE-T-012, FE-T-013):
  - Group stage models (Group, GroupStanding)
  - `POST /api/organizer/tournaments/{slug}/groups/configure/`
  - `POST /api/organizer/tournaments/{slug}/groups/draw/`
  - `GET /api/tournaments/{slug}/groups/{group_id}/standings/`
  - Multi-game scoring logic (9 games: eFootball, FC Mobile, Valorant, PUBG Mobile, Free Fire, CS2, FIFA, Mobile Legends, Call of Duty Mobile)

- **Match Result Reporting & Disputes** (FE-T-014, FE-T-015, FE-T-016, FE-T-017):
  - Dispute models (Dispute, DisputeEvidence, DisputeResolution)
  - `POST /api/matches/{match_id}/submit-result/` (with screenshot upload)
  - `POST /api/matches/{match_id}/approve-result/`
  - `POST /api/matches/{match_id}/dispute/`
  - `POST /api/disputes/{dispute_id}/resolve/`
  - Evidence storage (S3 for screenshots/videos)
  - 24-hour dispute window enforcement
  - Two-phase approval workflow

- **Existing APIs** (likely already available):
  - Module 9.1: Tournament discovery API (FE-T-001)
  - Module 5.1: Match bracket & schedule (FE-T-008)
  - Module 9.3: Organizer dashboard data (FE-T-020)

**Real-Time Infrastructure**:
- WebSocket server for live updates (exists: `spectator_ws.js`)
- HTMX endpoints for polling fallback (exists in spectator pages)
- WebSocket channels needed for: lobby updates, check-in status, group standings, match results

**Payment Integration**:
- Module 3.1: Payment gateway integration (read-only UI)
- No frontend payment processing, just display status

**Storage & Media**:
- S3 integration for evidence uploads (screenshots, videos)
- Certificate PDF generation (Module 6.6)
- Tournament banners and game assets

---

## Success Criteria

**For Tournament MVP (P0 items complete)**:
- ✅ Players can discover and register for tournaments (with team permission validation)
- ✅ Players have access to participant lobby/hub before tournament starts
- ✅ Players can check in for tournaments
- ✅ Organizers can configure group stages for all 9 supported games
- ✅ Organizers can perform live draws to assign participants to groups
- ✅ Players can view group standings with game-specific stats
- ✅ Players can view bracket and live scores during tournament
- ✅ Spectators can follow tournaments without logging in
- ✅ Players can submit match results with screenshot evidence
- ✅ Organizers can approve or override match results
- ✅ Players can dispute incorrect results
- ✅ Organizers can resolve disputes with full evidence review
- ✅ Players can see final results after tournament
- ✅ Organizers can create and manage tournaments end-to-end
- ✅ Organizers can resolve disputes and manage participants

**Performance Targets**:
- Tournament list page loads < 2s on 3G mobile
- Lobby page loads < 1.5s for participants
- Live score updates appear < 3s after backend change (WebSocket)
- Group standings update < 2s after match completion
- Registration flow completion rate > 80%
- Result submission completion rate > 90% (with evidence)
- Mobile usability score > 85 (Lighthouse)
- Screenshot upload completes < 5s (on 4G)

**Quality Targets**:
- WCAG 2.1 AA compliance (accessibility)
- Zero critical bugs in P0 flows
- Browser support: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- Mobile-first: 360px to 428px width tested
- Evidence upload supports JPG, PNG (up to 5MB)
- Dispute resolution time < 24 hours average

**Multi-Game Support**:
- All 9 games supported: eFootball, FC Mobile, Valorant, PUBG Mobile, Free Fire, CS2, FIFA, Mobile Legends, Call of Duty Mobile
- Game-specific scoring displays correctly in standings
- Game-specific result submission forms adapt correctly

---

**End of Tournament Backlog**
