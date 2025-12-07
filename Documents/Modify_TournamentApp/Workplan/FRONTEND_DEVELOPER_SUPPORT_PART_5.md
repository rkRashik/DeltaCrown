# Part 5: Frontend Developer Support & UI Specification

**Document Purpose**: Complete frontend developer specification for building DeltaCrown's user interface without requiring additional backend clarification.

**Created**: December 8, 2025  
**Scope**: UI architecture, screen inventory, component library, data contracts, user flows

**Source Documents**:
- Part 1: ARCH_PLAN_PART_1.md (Architecture & Vision)
- Part 2: LIFECYCLE_GAPS_PART_2.md (Tournament Lifecycle & Gaps)
- Part 3: SMART_REG_AND_RULES_PART_3.md (Smart Registration & Game Rules)
- Part 4: ROADMAP_AND_EPICS_PART_4.md (Development Roadmap)

---

## 1. Frontend Architecture Overview

### 1.1 Technology Stack

**Rendering Layer**: Django Templates
- Server-side rendering for all pages
- Template inheritance for consistent layouts
- Template tags for reusable UI components
- Context processors for global data (user, notifications)

**Styling**: Tailwind CSS
- Utility-first CSS framework
- Custom design system via `tailwind.config.js`
- Responsive design by default
- Dark mode support (optional)

**Interactivity**: Vanilla JavaScript + Progressive Enhancement
- Vanilla JS for core interactions (modals, dropdowns, form validation)
- Optional: HTMX for seamless partial updates (results inbox, live bracket updates)
- Optional: Alpine.js for simple reactive components (filter panels, tabs)
- No heavy frontend framework (React, Vue) required

**Form Handling**:
- Standard HTML forms with POST for submissions
- Client-side validation before submit
- Server-side validation with error display
- AJAX for real-time validation (username availability, game ID verification)

---

### 1.2 UI Architecture Separation

**Player-Facing UI** (Public + Authenticated Users):
- **Purpose**: Browse tournaments, register, view matches, submit results, track stats
- **Design**: Modern, game-focused, visually engaging
- **Layout**: Standard website layout (navbar, hero, content, footer)
- **URL Pattern**: `/tournaments/`, `/my-tournaments/`, `/profile/`

**Organizer/Staff Console** (Admin Interface):
- **Purpose**: Manage tournaments, verify registrations, review results, handle disputes
- **Design**: Dashboard-style, data-dense, workflow-optimized
- **Layout**: Sidebar navigation, tabbed content areas, action panels
- **URL Pattern**: `/organizer/`, `/organizer/tournaments/{id}/`, `/staff/`

**Separation Benefits**:
- Different navigation patterns (browse vs. manage)
- Different information density (engaging vs. efficient)
- Different permission models (RBAC for organizers)

---

### 1.3 Frontend-Backend Communication

**Standard Form Submission** (Traditional Flow):
```
User fills form → Submit → POST /api/register/ → Redirect with messages
```
- Used for: Registration, tournament creation, settings updates
- Django messages framework for success/error feedback
- Redirect-after-POST pattern (PRG)

**JSON Endpoints** (Dynamic Actions):
```
User action → Fetch → GET/POST /api/v1/{resource}/ → Update UI
```
- Used for: Real-time validation, autosave drafts, partial updates
- Returns JSON responses
- Updates UI without full page reload

**Example JSON Endpoints**:
- `POST /api/v1/validate-field/` - Validate single field (Riot ID, Steam ID)
- `POST /api/v1/drafts/{uuid}/autosave/` - Save registration draft
- `GET /api/v1/matches/{id}/status/` - Poll match status
- `POST /api/v1/results/{id}/confirm/` - Confirm opponent's result
- `GET /api/v1/tournaments/{id}/bracket/` - Fetch bracket data

**WebSocket** (Optional, for Real-Time):
- Live bracket updates during tournament
- Match notifications ("Your match is starting")
- Not required for MVP

---

### 1.4 Progressive Enhancement Philosophy

**Core Principle**: All features work without JavaScript, enhanced with JS.

**Example: Registration Form**
- **Without JS**: Multi-page form with server-side validation
- **With JS**: Single-page wizard with client-side validation + autosave

**Example: Bracket View**
- **Without JS**: Static HTML bracket with links to match pages
- **With JS**: Interactive bracket with hover details, zoom, drag-to-schedule

**Benefits**:
- Accessible to all users
- Works on slow connections
- SEO-friendly (server-rendered content)
- Degrades gracefully if JS fails

---

## 2. Screen Inventory (High-Level Page List)

### 2.1 Player/Team Screens

#### Screen 2.1.1: Home / Discover Tournaments
**URL**: `/` or `/tournaments/`

**Purpose**: Entry point for users to discover and browse active tournaments.

**Data Displayed**:
- Featured tournaments (hero section with large cards)
- Upcoming tournaments (filterable list)
- Recently completed tournaments (with winners)
- User's active tournaments (if logged in)
- Tournament filters: game, format, status, entry fee

**User Actions**:
- Search tournaments by name
- Filter by game (dropdown with 11 games)
- Filter by format (Single Elim, Double Elim, Swiss, etc.)
- Filter by status (Open for Registration, Live, Completed)
- Click tournament card → Navigate to Tournament Detail
- Click "Register" button (if eligible)

**UI Considerations**:
- Hero section with rotating featured tournaments
- Grid layout for tournament cards (responsive: 1 col mobile, 3 cols desktop)
- Empty state: "No tournaments match your filters"
- Loading skeleton while fetching tournaments
- Infinite scroll or pagination for large lists

---

#### Screen 2.1.2: Tournament Detail Page
**URL**: `/tournaments/{slug}/`

**Purpose**: Comprehensive tournament information and registration entry point.

**Data Displayed**:
- Tournament header (name, game icon, dates, status)
- Entry fee, prize pool, format, max participants
- Registration status (Open, Closed, Full, Live, Completed)
- Rules and description
- Schedule (dates for each stage: registration, group stage, playoffs, finals)
- Current participants count vs. max
- Bracket/Groups preview (if tournament started)
- Organizer information (name, contact)

**User Actions**:
- Click "Register Now" → Navigate to Registration Wizard
- Click "View Bracket" → Navigate to Bracket Page (if live)
- Click "View My Registration" (if already registered)
- Share tournament (copy link)
- Report tournament (abuse flag)

**UI Considerations**:
- Sticky "Register" button (follows scroll)
- Registration status badge (prominent color coding)
- Countdown timer to registration close
- Tabs for: Overview, Rules, Schedule, Participants, Bracket
- Responsive banner image
- Prize pool breakdown (1st, 2nd, 3rd)

---

#### Screen 2.1.3: Registration Wizard (Multi-Step)
**URL**: `/tournaments/{slug}/register/`

**Purpose**: Smart registration flow with auto-fill, validation, and payment.

**Data Displayed**:
- Progress indicator (Step 1 of 5)
- Current step content (fields, labels, help text)
- Auto-filled fields (with "Auto-filled from profile" badge)
- Locked fields (with lock icon, uneditable)
- Real-time validation errors
- Draft save status ("Saved 2 seconds ago")

**User Actions**:
**Step 1: Player/Team Selection**
- Select role (Solo Player / Team Captain / Team Member)
- Select team (if joining existing team)
- Create new team (if team tournament)

**Step 2: Identity & Game Accounts**
- Confirm identity fields (name, email, phone)
- Add/verify game identity (Riot ID, Steam ID, etc.)
- Upload rank screenshot (if required)

**Step 3: Tournament-Specific Questions**
- Answer game-specific questions (role, rank, server)
- Conditional fields (show if tournament type = ranked)

**Step 4: Documents & Verification**
- Upload required documents (ID, parent consent if < 18)
- Agree to terms and conditions

**Step 5: Payment & Confirmation**
- Select payment method (DeltaCoin / Manual)
- Upload payment proof (if manual)
- Review all information
- Submit registration

**Navigation**:
- "Next" button (validates current step before advancing)
- "Back" button (returns to previous step without losing data)
- "Save as Draft" button (saves progress, returns later)
- "Cancel" button (confirms before leaving)

**UI Considerations**:
- Multi-step wizard with clear progress bar
- Inline validation (real-time field errors)
- Auto-save every 30 seconds (draft persistence)
- Success modal with registration number after submit
- Field locking UI (grayed out + lock icon for verified fields)
- Conditional field rendering (JavaScript-driven)
- Mobile-friendly (vertical layout, large tap targets)
- Draft recovery banner if returning to abandoned draft

---

#### Screen 2.1.4: My Tournaments Dashboard
**URL**: `/my-tournaments/`

**Purpose**: Centralized hub for user's tournament participation.

**Data Displayed**:
- Active tournaments (currently participating)
  - Tournament name, game, status
  - Next match (if scheduled)
  - Current standing/rank
  - Days until next round
- Upcoming matches (across all tournaments)
  - Opponent, time, game, round
- Recent match results
- Tournament history (past tournaments)
  - Final placement, stats, awards

**User Actions**:
- Click tournament → Navigate to Tournament Detail
- Click match → Navigate to Match Details
- Filter by tournament status (Active, Upcoming, Completed)
- Filter by game

**UI Considerations**:
- Tabbed interface: Active, Upcoming Matches, History
- Card-based layout for tournaments
- List view for upcoming matches (chronological)
- Empty state: "You haven't joined any tournaments yet"
- Quick action buttons: "Report Result", "View Bracket"

---

#### Screen 2.1.5: Match Details & Result Submission
**URL**: `/matches/{id}/`

**Purpose**: View match information and submit/confirm results.

**Data Displayed**:
- Match header (participants, game, round, tournament)
- Scheduled time (if set)
- Match state (Pending, Live, Pending Result, Disputed, Completed)
- Current result submission status
- Score/result (if submitted or completed)
- Proof screenshots (if uploaded)
- Chat/comments (optional feature)

**User Actions**:
**If match is live and user is participant**:
- Click "Submit Result" → Open result submission form
  - Select winner
  - Enter scores (game-specific fields from schema)
  - Upload proof screenshot (required)
  - Add notes (optional)
  - Submit

**If opponent submitted result**:
- View submitted result (scores, proof)
- Click "Confirm Result" → Match advances
- Click "Dispute Result" → Navigate to Dispute Form

**If result is finalized**:
- View final scores
- View stats (if available: K/D, rounds won, etc.)
- Download match report

**UI Considerations**:
- State-based UI (different views for Pending, Live, Pending Confirmation, Disputed)
- Proof image lightbox (click to enlarge)
- Countdown timer for opponent confirmation (24 hours)
- Color-coded result badges (Pending=yellow, Confirmed=green, Disputed=red)
- Mobile-friendly result submission form
- Schema-driven result fields (dynamic based on game)

---

#### Screen 2.1.6: Dispute Submission Form
**URL**: `/matches/{id}/dispute/`

**Purpose**: Allow participants to dispute incorrect result submissions.

**Data Displayed**:
- Original submitted result (for reference)
- Original proof screenshot
- Dispute form fields

**User Actions**:
- Select dispute reason (dropdown: Incorrect Score, Fake Proof, Cheating, Wrong Winner)
- Enter detailed explanation (min 50 chars, required)
- Upload counter-proof screenshot (optional)
- Submit dispute

**UI Considerations**:
- Clear display of original submission vs. dispute claim
- Character counter for explanation (50 min, 500 max)
- Image comparison (original proof vs. counter-proof)
- Warning message: "Disputes are reviewed by organizers. False disputes may result in penalties."
- Confirmation modal before submit

---

#### Screen 2.1.7: Profile & Game Accounts
**URL**: `/profile/` or `/profile/{username}/`

**Purpose**: Manage user profile, game accounts, and view stats.

**Data Displayed**:
- Profile overview (username, avatar, bio, join date)
- Game accounts section
  - Connected accounts (Riot ID, Steam ID, etc.)
  - Verification status (Verified, Pending, Unverified)
- Stats overview
  - Total matches played
  - Win rate
  - Favorite games
  - Achievements/badges
- Match history (recent matches)
- Tournament history (placements)

**User Actions**:
- Edit profile (bio, avatar, social links)
- Add game account (game selector → identity field form)
- Verify game account (OAuth or manual verification)
- Remove game account
- View detailed stats (filter by game)

**UI Considerations**:
- Tabbed interface: Overview, Game Accounts, Stats, Match History
- Connected accounts displayed as cards (game icon, ID, verification badge)
- Add account button prominent but not intrusive
- Stats displayed as cards (large numbers, trend indicators)
- Match history as timeline or table

---

### 2.2 Organizer/Staff Screens

#### Screen 2.2.1: Organizer Dashboard (Tournament Overview)
**URL**: `/organizer/tournaments/{id}/`

**Purpose**: Centralized control panel for managing a single tournament.

**Data Displayed**:
- Tournament status widget (Draft, Open, Live, Completed)
- Key metrics (registrations, matches, disputes, overdue items)
  - Registrations: 45/64 (70% full)
  - Matches: 12 completed, 8 live, 4 pending
  - Disputes: 2 pending review
  - Overdue: 3 matches
- Quick action cards
  - "Generate Bracket" (if not generated)
  - "Review Pending Registrations" (if > 0)
  - "Verify Results" (if > 0 pending)
  - "Resolve Disputes" (if > 0 disputes)
- Recent activity feed (audit log)
- Upcoming tasks timeline

**User Actions**:
- Navigate to sub-pages via tabs:
  - Registrations
  - Bracket & Groups
  - Matches
  - Results Inbox
  - Disputes
  - Payouts
  - Settings
- Click quick action cards → Navigate to relevant page
- View notifications (bell icon with count)

**UI Considerations**:
- Dashboard layout with widgets (grid: 2-3 cols)
- Color-coded alerts (red for critical, yellow for warnings)
- Metric cards with trend indicators (↑ 12% from yesterday)
- Sidebar navigation for tournament sections
- Sticky header with tournament name and status
- Contextual help tooltips ("What does this metric mean?")

---

#### Screen 2.2.2: Registration Management Page
**URL**: `/organizer/tournaments/{id}/registrations/`

**Purpose**: Review, verify, and manage tournament registrations.

**Data Displayed**:
- Registrations table
  - Columns: Reg #, Player/Team, Game ID, Status, Payment, Documents, Registered Date
  - Filters: Status (All, Pending, Verified, Rejected), Payment (Paid, Pending, Failed)
  - Search: By name, reg number, email
- Registration detail panel (click row to expand)
  - Full registration data
  - Verification checklist (email ✓, game ID ✓, payment ✓, documents ✓)
  - Uploaded documents (view/download)
  - Notes/comments

**User Actions**:
- Filter registrations by status, payment
- Search by name or registration number
- Click row → View registration details
- Verify registration (mark checklist items)
  - Verify email
  - Verify game ID (manual check against screenshot)
  - Verify payment
  - Verify documents
- Approve registration → Status: Verified
- Reject registration (reason required)
- Bulk actions: Approve all pending, Export to CSV
- Send email to participant

**UI Considerations**:
- Sortable table columns
- Status badges (color-coded)
- Verification progress bar per registration (75% verified)
- Document viewer (inline or modal)
- Bulk selection checkboxes
- Empty state: "No pending registrations"
- Export button (CSV download)

---

#### Screen 2.2.3: Bracket & Groups Management Page
**URL**: `/organizer/tournaments/{id}/bracket/`

**Purpose**: Create, edit, and manage tournament structure (groups, brackets, stages).

**Data Displayed**:
**View Mode: Structure Overview**
- Tournament format summary (Swiss System, 4 rounds)
- Stages list (if multi-stage tournament)
  - Stage 1: Group Stage (4 groups)
  - Stage 2: Playoffs (Single Elimination)
- Participant list (seeding order)

**View Mode: Group Stage Editor**
- Groups grid (Group A, B, C, D)
- Participants assigned to each group
- Group matches (round-robin)
- Standings table per group

**View Mode: Bracket Editor**
- Bracket tree visualization
- Match slots (with participants or TBD)
- Winner connections (arrows)
- Edit controls (drag/drop, swap, edit)

**User Actions**:
- Generate bracket (if not created)
  - Select format (SE, DE, RR, Swiss)
  - Set seeding method (Random, By rank, Manual)
  - Confirm generation
- Create groups (if group stage)
  - Set number of groups
  - Auto-balance or manual assignment
- Edit bracket
  - Swap participants between matches
  - Move participant to different slot (drag/drop)
  - Remove participant (DQ, no-show)
  - Repair broken connections
- Advance stage (Groups → Playoffs)
  - Select advancement criteria (top 2 per group)
  - Generate next stage bracket
- Reset bracket (confirmation required)

**UI Considerations**:
- Tabbed interface: Overview, Groups, Bracket, Settings
- Bracket visualization (SVG or Canvas)
  - Zoom in/out controls
  - Horizontal scroll for large brackets
- Drag-and-drop for participant reordering
- Confirmation modals for destructive actions
- Bracket integrity validation ("Warning: This will orphan 3 matches")
- Mobile: List view instead of tree view

---

#### Screen 2.2.4: Match Operations Page
**URL**: `/organizer/tournaments/{id}/matches/`

**Purpose**: Monitor and manage all tournament matches.

**Data Displayed**:
- Matches table
  - Columns: Match #, Round, Participants, State, Scheduled Time, Actions
  - Filters: State (All, Pending, Live, Pending Result, Completed), Round
  - Search: By participant name
- Today's matches widget
- Overdue matches alert (red banner)
- Match detail panel (click row to expand)
  - Participants
  - Scheduled time
  - Result submissions (if any)
  - Actions

**User Actions**:
- Filter matches by state, round
- Search matches by participant
- Click match → View match details
- Schedule match (set date/time)
- Start match manually (change state to Live)
- View result submissions
- Override result (manual entry)
- Cancel match (reason required)
- Bulk actions: Schedule all Round 1 matches

**UI Considerations**:
- State badges (color-coded: Pending=gray, Live=blue, Completed=green)
- Overdue indicator (red "⏰ Overdue by 45 min")
- Scheduled time with countdown ("Starts in 2h 15m")
- Quick action buttons per row (Schedule, Start, View Result)
- Calendar view option (alternative to table)
- Empty state: "No matches in this round yet"

---

#### Screen 2.2.5: Results Inbox
**URL**: `/organizer/tournaments/{id}/results/`

**Purpose**: Review and approve/reject player-submitted match results.

**Data Displayed**:
- Results queue (tabbed)
  - Tab: Pending (awaiting opponent confirmation)
  - Tab: Disputed (opponent disputed result)
  - Tab: Conflicted (both teams submitted different results)
- Result inbox items
  - Match info (participants, round, game)
  - Submitted result (winner, scores)
  - Proof screenshot (thumbnail, click to enlarge)
  - Submission time, submitted by
  - Dispute info (if disputed: reason, counter-proof)
- Result detail panel (click item to expand)
  - Full result data
  - All submissions (if multiple)
  - Proof images
  - Dispute details
  - Action buttons

**User Actions**:
- Filter by tab (Pending, Disputed, Conflicted)
- Click item → View full details
- Approve result → Match finalized
- Reject result (reason required)
- Override result (manual entry)
- Order rematch (reset match to pending)
- Request more info (message participants)
- View proof images (lightbox)

**UI Considerations**:
- Inbox-style layout (list on left, detail panel on right)
- Color-coded tabs (Pending=yellow, Disputed=red)
- Proof image thumbnails (hover to preview, click to enlarge)
- Side-by-side comparison for conflicted results
- Age indicator ("Submitted 3 hours ago")
- Bulk actions: Approve all confirmed results
- Empty state: "No pending results to review"

---

#### Screen 2.2.6: Dispute Handling Page
**URL**: `/organizer/tournaments/{id}/disputes/`

**Purpose**: Review and resolve player disputes.

**Data Displayed**:
- Disputes table
  - Columns: Dispute #, Match, Disputer, Reason, Status, Created Date
  - Filters: Status (Pending, Resolved, Escalated)
- Dispute detail panel
  - Original submission (scores, proof)
  - Dispute claim (reason, explanation, counter-proof)
  - Match context (tournament, round, participants)
  - Resolution options

**User Actions**:
- Click dispute → View full details
- Compare proofs (side-by-side)
- Resolve dispute:
  - Approve original submission (dispute rejected)
  - Approve dispute (override original result)
  - Order rematch (both submissions invalid)
- Enter resolution notes (required)
- Escalate to admin (if complex)
- Message participants (request clarification)

**UI Considerations**:
- Dispute detail view (modal or panel)
- Image comparison UI (original vs. counter-proof)
- Resolution notes textarea (required, min 50 chars)
- Confirmation modal for resolution
- Escalation flag (marks dispute for admin review)
- Dispute history (all actions taken)

---

#### Screen 2.2.7: Tournament Settings / Stage Editor
**URL**: `/organizer/tournaments/{id}/settings/`

**Purpose**: Configure tournament settings, stages, and advanced options.

**Data Displayed**:
- General settings
  - Name, description, game, format
  - Dates (registration open/close, start date, end date)
  - Max participants, entry fee
- Stage configuration (if multi-stage)
  - Stage list (Group Stage, Playoffs)
  - Stage settings (format, advancement rules)
- Registration settings
  - Required fields
  - Document requirements
  - Payment settings
- Rules & scoring
  - Game-specific scoring rules
  - Tiebreaker settings
- Staff & permissions
  - Assigned staff (referees, moderators)
  - Role permissions

**User Actions**:
- Edit general settings
- Add/edit tournament stages
- Configure registration requirements
- Set document requirements (rank screenshot, ID, etc.)
- Assign staff members
- Save changes
- Publish tournament (make public)
- Cancel tournament (confirmation required)

**UI Considerations**:
- Tabbed interface: General, Stages, Registration, Rules, Staff
- Form-based settings (save button at bottom)
- Validation for date ranges ("Start date must be after registration close")
- Stage editor with drag-to-reorder
- Confirmation modals for destructive actions
- Unsaved changes warning

---

#### Screen 2.2.8: Payouts & Rewards Management
**URL**: `/organizer/tournaments/{id}/payouts/`

**Purpose**: Manage prize distribution and DeltaCoin rewards.

**Data Displayed**:
- Prize pool summary
  - Total prize pool
  - Distribution (1st: 50%, 2nd: 30%, 3rd: 20%)
- Winners table
  - Placement, Team/Player, Prize Amount, Status (Pending, Paid)
- Payout history
  - Transaction ID, Recipient, Amount, Date

**User Actions**:
- View final standings
- Calculate payouts (auto-distribution based on rules)
- Mark payout as sent
- Generate payout report (PDF/CSV)
- Send payout notifications

**UI Considerations**:
- Prize breakdown visualization (pie chart or bar chart)
- Winners list with placement badges (🥇🥈🥉)
- Payout status badges (Pending, Processing, Completed)
- Export button for reports
- Confirmation modal before marking paid

---

## 3. Component Library Blueprint

### 3.1 Layout Components

#### Component 3.1.1: Page Shell
**Purpose**: Consistent layout structure for all pages.

**Receives**:
- `page_title` (string): Browser tab title
- `user` (object): Current user data (if authenticated)
- `notifications` (array): Unread notifications count
- `breadcrumbs` (array): Navigation breadcrumb trail

**Structure**:
```
┌─────────────────────────────────────┐
│ Navbar (logo, nav links, user menu)│
├─────────────────────────────────────┤
│ Breadcrumbs (if applicable)        │
├─────────────────────────────────────┤
│                                     │
│ Main Content Area                   │
│ (slot: page content goes here)     │
│                                     │
├─────────────────────────────────────┤
│ Footer (links, social, copyright)  │
└─────────────────────────────────────┘
```

**States**:
- Authenticated: Show user menu, notifications bell
- Unauthenticated: Show "Login" and "Sign Up" buttons
- Mobile: Hamburger menu, collapsible navbar

---

#### Component 3.1.2: Navbar
**Purpose**: Primary navigation for player-facing pages.

**Receives**:
- `user` (object): Current user data
- `active_page` (string): Current page identifier (for highlighting)

**Structure**:
- Logo (link to home)
- Navigation links: Tournaments, Leaderboards, My Tournaments (if logged in)
- User menu (dropdown): Profile, Settings, Logout
- Notifications bell (icon with count badge)

**States**:
- Desktop: Horizontal nav
- Mobile: Hamburger menu → slide-out drawer

---

#### Component 3.1.3: Organizer Sidebar
**Purpose**: Navigation for organizer console.

**Receives**:
- `tournament` (object): Current tournament data
- `active_section` (string): Current section (for highlighting)

**Structure**:
- Tournament name header
- Navigation sections:
  - Dashboard
  - Registrations (count badge)
  - Bracket & Groups
  - Matches
  - Results Inbox (count badge)
  - Disputes (count badge)
  - Payouts
  - Settings

**States**:
- Desktop: Persistent sidebar (left side)
- Mobile: Collapsible drawer (hamburger toggle)
- Count badges: Red for alerts, gray for info

---

#### Component 3.1.4: Card
**Purpose**: Reusable card container for content grouping.

**Receives**:
- `title` (string, optional): Card header
- `footer` (boolean): Show footer section
- `padding` (string): Padding size (sm, md, lg)

**Structure**:
```
┌─────────────────────────┐
│ Title (optional)        │
├─────────────────────────┤
│ Body Content            │
│ (slot)                  │
├─────────────────────────┤
│ Footer (optional)       │
└─────────────────────────┘
```

**Variants**:
- Default: White background, shadow
- Flat: No shadow
- Bordered: Border instead of shadow
- Hoverable: Lift on hover (for clickable cards)

---

#### Component 3.1.5: Modal
**Purpose**: Dialog overlay for confirmations, forms, or details.

**Receives**:
- `title` (string): Modal header
- `size` (string): sm, md, lg, xl, full
- `closable` (boolean): Show close button
- `footer_actions` (array): Button configurations

**Structure**:
```
┌──────────────────────────────┐
│ ╔════════════════════════╗  │
│ ║ Title         [X]      ║  │
│ ╠════════════════════════╣  │
│ ║ Body content           ║  │
│ ║ (slot)                 ║  │
│ ╠════════════════════════╣  │
│ ║ [Cancel] [Confirm]     ║  │
│ ╚════════════════════════╝  │
│ (backdrop overlay)           │
└──────────────────────────────┘
```

**States**:
- Open: Visible with backdrop
- Closed: Hidden
- Loading: Disabled buttons, spinner

**Interactions**:
- Close on backdrop click (optional)
- Close on Escape key
- Focus trap (keyboard navigation stays in modal)

---

### 3.2 Form Components

#### Component 3.2.1: Text Input
**Purpose**: Standard text input field with label and validation.

**Receives**:
- `name` (string): Field name
- `label` (string): Field label
- `value` (string): Current value
- `placeholder` (string): Placeholder text
- `required` (boolean): Required field indicator
- `disabled` (boolean): Read-only state
- `locked` (boolean): Locked field (auto-filled, verified)
- `errors` (array): Validation error messages
- `help_text` (string): Helper text
- `type` (string): text, email, password, url

**Structure**:
```
Label * (asterisk if required)
┌──────────────────────────┐
│ Placeholder text      🔒 │ (lock icon if locked)
└──────────────────────────┘
Help text here
❌ Error message (if invalid)
```

**States**:
- Default: Empty, ready for input
- Filled: Contains value
- Locked: Grayed out + lock icon + tooltip ("Auto-filled from profile")
- Error: Red border + error message
- Disabled: Grayed out, not editable
- Focus: Blue border

---

#### Component 3.2.2: Select Dropdown
**Purpose**: Dropdown selection field.

**Receives**:
- `name` (string): Field name
- `label` (string): Field label
- `options` (array): `[{value, label}]`
- `value` (string): Selected value
- `required` (boolean): Required indicator
- `errors` (array): Validation errors
- `searchable` (boolean): Enable search/filter

**Structure**:
```
Label *
┌──────────────────────────▼┐
│ Select option...          │
└───────────────────────────┘
```

**States**:
- Closed: Shows selected value or placeholder
- Open: Dropdown menu visible with options
- Searchable: Filter input at top of dropdown
- Empty: "No options available"

---

#### Component 3.2.3: Multi-Step Progress Indicator
**Purpose**: Visual progress bar for multi-step wizards.

**Receives**:
- `steps` (array): `[{number, label, status}]`
- `current_step` (number): Active step
- `total_steps` (number): Total number of steps

**Structure**:
```
1 ━━━ 2 ━━━ 3 ─ ─ 4 ─ ─ 5
Identity  Team  Questions Payment Review
(active)
```

**States**:
- Completed: Filled circle, solid line
- Active: Highlighted circle, bold label
- Upcoming: Empty circle, dashed line

---

#### Component 3.2.4: Game Identity Field Block
**Purpose**: Game-specific identity input (Riot ID, Steam ID, etc.) with validation.

**Receives**:
- `game` (object): Game metadata (name, slug)
- `identity_config` (object): Field config from `GamePlayerIdentityConfig`
  - `field_name`: "riot_id"
  - `display_name`: "Riot ID"
  - `format`: "username#tag"
  - `validation_pattern`: regex
- `value` (string): Current value
- `locked` (boolean): Field locked (verified)
- `verification_status` (string): unverified, pending, verified

**Structure**:
```
Riot ID (Valorant) *
┌──────────────────────────┐
│ Player#1234           🔒 │
└──────────────────────────┘
✓ Verified via Riot API
```

**States**:
- Unverified: Yellow badge "Unverified"
- Pending: Blue badge "Verification pending"
- Verified: Green checkmark "Verified"
- Error: Red border + error message

**Interactions**:
- Real-time format validation (e.g., must match "username#tag")
- Verify button (triggers API verification)
- Link to verification guide

---

#### Component 3.2.5: Team Roster Editor
**Purpose**: Manage team members for team registration.

**Receives**:
- `team` (object): Team data (name, members)
- `max_members` (number): Max team size (e.g., 5 for Valorant)
- `min_members` (number): Min team size
- `editable` (boolean): Can add/remove members

**Structure**:
```
Team Roster (3/5 members)
┌──────────────────────────────────┐
│ 1. Player#1234 (Captain)    [X] │
│ 2. Player#5678               [X] │
│ 3. Player#9012               [X] │
├──────────────────────────────────┤
│ [+ Add Member]                   │
└──────────────────────────────────┘
```

**States**:
- Minimum met: Green border
- Minimum not met: Red border + warning
- Full: "Add Member" button disabled

**Interactions**:
- Add member: Input field → Search users → Select
- Remove member: Click [X] → Confirm modal
- Designate captain: Radio button per member

---

### 3.3 Tournament Components

#### Component 3.3.1: Tournament Card
**Purpose**: Display tournament summary in listing/grid views.

**Receives**:
- `tournament` (object):
  - `name`, `slug`
  - `game` (object): `{name, icon}`
  - `format` (string): "Single Elimination"
  - `status` (string): "Open", "Live", "Completed"
  - `entry_fee` (number)
  - `prize_pool` (number)
  - `max_participants` (number)
  - `current_participants` (number)
  - `registration_close_date` (datetime)
  - `start_date` (datetime)
  - `banner_image` (url)

**Structure**:
```
┌─────────────────────────────┐
│ [Banner Image]              │
│ ┌─────────────────────────┐ │
│ │ VALORANT          [Live]│ │
│ │ VCT Champions 2025      │ │
│ │ 45/64 • $500 Prize Pool │ │
│ │ Starts in 2 days        │ │
│ │ [Register Now]          │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

**States**:
- Open for Registration: Green "Register" button
- Registration Closed: Gray "View Tournament" button
- Live: Blue "Live" badge + "View Bracket" button
- Completed: Gray "Completed" badge + "View Results" button

**Interactions**:
- Click card → Navigate to tournament detail
- Click "Register" → Navigate to registration wizard
- Hover: Lift animation (shadow)

---

#### Component 3.3.2: Registration Status Badge
**Purpose**: Color-coded badge showing registration status.

**Receives**:
- `status` (string): "pending", "confirmed", "verified", "rejected", "withdrawn", "waitlisted"

**Variants**:
- `pending`: Yellow "⏳ Pending Verification"
- `confirmed`: Blue "✓ Confirmed"
- `verified`: Green "✓ Verified"
- `rejected`: Red "✗ Rejected"
- `withdrawn`: Gray "Withdrawn"
- `waitlisted`: Orange "Waitlisted"

---

#### Component 3.3.3: Match Card (Basic)
**Purpose**: Display match summary in lists.

**Receives**:
- `match` (object):
  - `id`, `round`, `game`
  - `participant1` (object): `{name, logo, score}`
  - `participant2` (object): `{name, logo, score}`
  - `state` (string): "pending", "live", "completed"
  - `scheduled_time` (datetime)
  - `winner_id` (number)

**Structure**:
```
┌──────────────────────────────────┐
│ Round 1 - Match 3      [Live]   │
│ ┌────────┐            ┌────────┐│
│ │ TeamA  │ 13 vs 7    │ TeamB  ││
│ └────────┘            └────────┘│
│ Scheduled: 3:00 PM               │
└──────────────────────────────────┘
```

**States**:
- Pending: Gray, no scores
- Live: Blue badge, live scores
- Completed: Winner highlighted (bold name)

**Interactions**:
- Click card → Navigate to match details

---

#### Component 3.3.4: Match Details Panel
**Purpose**: Expanded match view with all information and actions.

**Receives**:
- `match` (object): Full match data
- `can_submit_result` (boolean): User permission
- `result_submissions` (array): Submitted results (if any)

**Structure**:
```
┌───────────────────────────────────────┐
│ Round 1 - Best of 3        [Live]    │
├───────────────────────────────────────┤
│ Team Alpha    vs    Team Omega       │
│ [Logo]               [Logo]          │
│   13                   7              │
├───────────────────────────────────────┤
│ Map: Ascent                           │
│ Scheduled: Dec 8, 2025 3:00 PM       │
│ Status: Awaiting result confirmation │
├───────────────────────────────────────┤
│ [Submit Result] [View Bracket]       │
└───────────────────────────────────────┘
```

**States**:
- Pending: Show "Not started" message
- Live: Show "Submit Result" button (if participant)
- Pending Confirmation: Show submitted result + "Confirm" or "Dispute" buttons
- Completed: Show final scores + stats

---

#### Component 3.3.5: Group Standings Table
**Purpose**: Display group stage standings with tiebreakers.

**Receives**:
- `group` (object): Group data
- `standings` (array): `[{rank, team, matches_played, wins, losses, rounds_won, rounds_lost, round_diff, points}]`
- `show_tiebreakers` (boolean): Show tiebreaker columns
- `advancement_count` (number): Top N teams advance (for highlighting)

**Structure**:
```
Group A Standings
┌────┬───────────┬────┬────┬────┬────────┬───────┐
│Rank│ Team      │ MP │ W  │ L  │ Rounds │ Pts   │
├────┼───────────┼────┼────┼────┼────────┼───────┤
│ 1  │ Team A ✓  │ 3  │ 3  │ 0  │ +15    │ 9     │
│ 2  │ Team B ✓  │ 3  │ 2  │ 1  │ +5     │ 6     │
│ 3  │ Team C    │ 3  │ 1  │ 2  │ -3     │ 3     │
│ 4  │ Team D    │ 3  │ 0  │ 3  │ -17    │ 0     │
└────┴───────────┴────┴────┴────┴────────┴───────┘
✓ = Advances to Playoffs
```

**States**:
- Advances: Green row background + checkmark
- Eliminated: Red row background
- Tied: Same points, show tiebreaker tooltip

**Interactions**:
- Click team name → Navigate to team page
- Hover rank → Show tiebreaker details ("Head-to-head: 1-0 vs Team C")

---

#### Component 3.3.6: Bracket View
**Purpose**: Visual tournament bracket (tree structure).

**Receives**:
- `bracket_type` (string): "single_elimination", "double_elimination"
- `rounds` (array): `[{round_number, round_name, matches}]`
- `matches` (array): Match data with participant slots

**Structure** (Single Elimination):
```
Round 1          Semifinals        Finals
┌────────┐
│ Team A │─┐
└────────┘ │     ┌────────┐
           ├────>│ Team A │─┐
┌────────┐ │     └────────┘ │
│ Team B │─┘                │     ┌────────┐
└────────┘                  ├────>│ Team A │ 🏆
                            │     └────────┘
┌────────┐                  │
│ Team C │─┐                │
└────────┘ │     ┌────────┐ │
           ├────>│ Team C │─┘
┌────────┐ │     └────────┘
│ Team D │─┘
└────────┘
```

**States**:
- TBD slots: Grayed out "TBD"
- Completed matches: Winner highlighted
- Live matches: Blue highlight
- Clickable: Hover shows match details tooltip

**Interactions**:
- Click match → Navigate to match details
- Zoom controls (for large brackets)
- Horizontal scroll (mobile)

---

### 3.4 Organizer Tool Components

#### Component 3.4.1: Filter & Search Bar
**Purpose**: Combined filtering and search interface.

**Receives**:
- `filters` (array): `[{name, type, options}]`
  - type: "select", "checkbox", "date_range"
- `search_placeholder` (string)

**Structure**:
```
┌─────────────────────────────────────────────┐
│ 🔍 Search registrations...                  │
├─────────────────────────────────────────────┤
│ Status: [All ▼]  Payment: [All ▼]  [Reset] │
└─────────────────────────────────────────────┘
```

**States**:
- Default: All filters set to "All"
- Active: Filter dropdown open
- Applied: Show active filter count badge

**Interactions**:
- Type in search → Debounced search (300ms)
- Change filter → Instant filter application
- Reset button → Clear all filters

---

#### Component 3.4.2: Sortable Table (Registrations)
**Purpose**: Data table with sorting, pagination, and row actions.

**Receives**:
- `columns` (array): `[{key, label, sortable}]`
- `rows` (array): Data rows
- `per_page` (number): Rows per page
- `current_page` (number)
- `total_rows` (number)
- `row_actions` (array): `[{label, action, icon}]`

**Structure**:
```
┌─────┬─────────┬─────────┬────────┬────────┐
│ Reg#│ Player  │ Status  │Payment │Actions │
├─────┼─────────┼─────────┼────────┼────────┤
│ 001 │ Player1 │Verified │Paid    │ [...] ││
│ 002 │ Player2 │Pending  │Pending │ [...] ││
└─────┴─────────┴─────────┴────────┴────────┘
Showing 1-10 of 45 [< 1 2 3 4 5 >]
```

**States**:
- Sorted column: Arrow indicator (↑ or ↓)
- Row hover: Highlight background
- Loading: Skeleton rows
- Empty: "No results found" message

**Interactions**:
- Click column header → Sort (toggle asc/desc)
- Click row → Expand details (or navigate to detail page)
- Click action button → Execute action (approve, reject, etc.)
- Pagination: Click page number

---

#### Component 3.4.3: Result Inbox Item
**Purpose**: Display result submission in organizer inbox.

**Receives**:
- `submission` (object):
  - `match` (object): Match data
  - `submitted_by` (string): Username
  - `submitted_at` (datetime)
  - `claimed_winner` (string): Team name
  - `scores` (object): Score data
  - `proof_screenshot` (url)
  - `status` (string): "pending", "disputed", "conflicted"
  - `dispute` (object, optional): Dispute details

**Structure**:
```
┌────────────────────────────────────────────┐
│ Match 12: Team A vs Team B     [Disputed] │
│ Submitted by: Player1 · 2 hours ago       │
├────────────────────────────────────────────┤
│ Claimed: Team A won 13-7                  │
│ [View Proof Screenshot]                    │
│ ⚠️ Dispute: Incorrect score (by Player2)  │
├────────────────────────────────────────────┤
│ [Approve] [Reject] [Order Rematch]        │
└────────────────────────────────────────────┘
```

**States**:
- Pending: Yellow left border
- Disputed: Red left border + dispute banner
- Conflicted: Orange left border + "Both teams submitted different results"

**Interactions**:
- Click "View Proof" → Open image lightbox
- Click "Approve" → Confirmation modal → Finalize result
- Click "Reject" → Reason input modal
- Click "Order Rematch" → Confirmation modal

---

#### Component 3.4.4: Audit Log Entry
**Purpose**: Display audit trail entry for organizer actions.

**Receives**:
- `log_entry` (object):
  - `action` (string): "Approved registration", "Overrode result", etc.
  - `user` (string): Username who performed action
  - `timestamp` (datetime)
  - `details` (object): Additional context
  - `before_state` (object, optional): State before action
  - `after_state` (object, optional): State after action

**Structure**:
```
┌────────────────────────────────────────────┐
│ ✓ Approved registration #VCT-2025-001234  │
│ by: OrganizerName · 30 minutes ago        │
│ Details: Email verified, payment confirmed│
└────────────────────────────────────────────┘
```

**States**:
- Default: Timeline entry
- Expanded: Show before/after state comparison

**Interactions**:
- Click entry → Expand to show full details
- Hover → Highlight entry

---

---

## 4. Data Contracts & JSON Examples

### 4.1 Tournament Card Data

**Endpoint**: `GET /api/v1/tournaments/` (list) or context variable `tournaments`

**JSON Structure**:
```json
{
  "id": 42,
  "slug": "vct-champions-2025",
  "name": "VCT Champions 2025",
  "game": {
    "slug": "valorant",
    "name": "Valorant",
    "icon_url": "/media/games/valorant.png"
  },
  "format": "single_elimination",
  "format_display": "Single Elimination",
  "status": "open",  // open, live, completed, cancelled
  "status_display": "Open for Registration",
  "entry_fee": 10.00,  // DeltaCoins
  "prize_pool": 500.00,
  "max_participants": 64,
  "current_participants": 45,
  "registration_open_date": "2025-12-01T00:00:00Z",
  "registration_close_date": "2025-12-15T23:59:59Z",
  "start_date": "2025-12-20T10:00:00Z",
  "banner_image": "/media/tournaments/vct2025-banner.jpg",
  "is_team_based": true,
  "team_size": 5,
  "organizer": {
    "id": 7,
    "username": "RiotGames",
    "display_name": "Riot Games"
  },
  "user_registration_status": null,  // null (not registered), "pending", "verified"
  "can_register": true  // Based on user eligibility + tournament state
}
```

**Usage Notes**:
- Frontend displays `format_display` and `status_display` (human-readable)
- `can_register` determines if "Register" button is enabled
- `current_participants / max_participants` shows progress bar
- `registration_close_date` used for countdown timer

---

### 4.2 Registration Object (Player View)

**Endpoint**: `GET /api/v1/tournaments/{id}/my-registration/`

**JSON Structure**:
```json
{
  "registration_number": "VCT-2025-001234",
  "tournament": {
    "id": 42,
    "name": "VCT Champions 2025",
    "slug": "vct-champions-2025"
  },
  "status": "verified",  // pending, confirmed, verified, rejected, withdrawn
  "status_display": "Verified",
  "registered_at": "2025-12-05T14:30:00Z",
  "participant_type": "team_captain",  // solo, team_captain, team_member
  "team": {
    "id": 15,
    "name": "Team Alpha",
    "logo_url": "/media/teams/alpha-logo.png",
    "members": [
      {
        "user_id": 101,
        "username": "Player1",
        "game_identity": "Player1#NA1",
        "role": "captain",
        "status": "verified"
      },
      {
        "user_id": 102,
        "username": "Player2",
        "game_identity": "Player2#NA1",
        "role": "member",
        "status": "pending"
      }
    ]
  },
  "identity_data": {
    "riot_id": "Player1#NA1",
    "riot_id_verified": true,
    "rank": "Immortal 2",
    "region": "NA"
  },
  "payment": {
    "status": "paid",  // pending, paid, failed, refunded
    "amount": 10.00,
    "method": "deltacoin",
    "paid_at": "2025-12-05T14:32:00Z"
  },
  "verification_checklist": {
    "email_verified": true,
    "game_identity_verified": true,
    "payment_verified": true,
    "documents_verified": true,
    "all_verified": true
  },
  "documents": [
    {
      "type": "rank_screenshot",
      "url": "/media/registrations/001234/rank.png",
      "uploaded_at": "2025-12-05T14:31:00Z",
      "verified": true
    }
  ]
}
```

**Usage Notes**:
- Display `registration_number` prominently (unique ID for user reference)
- `verification_checklist` drives progress UI (checkmarks)
- `status` determines what actions are available (withdraw, edit, etc.)

---

### 4.3 Match Object

**Endpoint**: `GET /api/v1/matches/{id}/`

**JSON Structure**:
```json
{
  "id": 256,
  "tournament": {
    "id": 42,
    "name": "VCT Champions 2025",
    "slug": "vct-champions-2025"
  },
  "round": 3,
  "round_display": "Semifinals",
  "match_number": 12,
  "match_display": "Match 12",
  "state": "pending_confirmation",  // pending, live, pending_result, pending_confirmation, disputed, completed
  "state_display": "Pending Confirmation",
  "scheduled_time": "2025-12-21T15:00:00Z",
  "started_at": "2025-12-21T15:05:00Z",
  "completed_at": null,
  "participant1": {
    "id": 15,
    "name": "Team Alpha",
    "logo_url": "/media/teams/alpha-logo.png",
    "score": 13,
    "is_winner": null  // null (not decided), true, false
  },
  "participant2": {
    "id": 22,
    "name": "Team Omega",
    "logo_url": "/media/teams/omega-logo.png",
    "score": 7,
    "is_winner": null
  },
  "result_summary": {
    "winner_id": 15,
    "winner_name": "Team Alpha",
    "scores": {"participant1": 13, "participant2": 7},
    "details": {
      "map": "Ascent",
      "rounds": [
        {"half": "1st", "participant1": 7, "participant2": 5},
        {"half": "2nd", "participant1": 6, "participant2": 2}
      ]
    },
    "finalized": false
  },
  "result_submissions": [
    {
      "id": 401,
      "submitted_by": {
        "participant_id": 15,
        "participant_name": "Team Alpha",
        "user": "Player1"
      },
      "submitted_at": "2025-12-21T16:20:00Z",
      "claimed_winner_id": 15,
      "scores": {"participant1": 13, "participant2": 7},
      "proof_screenshot": "/media/results/401/proof.png",
      "notes": "Close game, GG!"
    }
  ],
  "dispute": null,  // Dispute object if state = "disputed"
  "user_permissions": {
    "can_submit_result": true,
    "can_confirm_result": false,
    "can_dispute_result": true
  },
  "next_match_id": 128,  // Bracket navigation
  "previous_match_ids": [64, 65]
}
```

**Usage Notes**:
- `state` drives UI rendering (different views for each state)
- `result_submissions` shows who submitted what (one or both sides)
- `user_permissions` determines which action buttons to display
- `result_summary.finalized` = true means result is official

---

### 4.4 Group Standings Row

**Endpoint**: `GET /api/v1/tournaments/{id}/groups/{group_id}/standings/`

**JSON Structure**:
```json
[
  {
    "rank": 1,
    "participant": {
      "id": 15,
      "name": "Team Alpha",
      "logo_url": "/media/teams/alpha-logo.png"
    },
    "matches_played": 3,
    "wins": 3,
    "losses": 0,
    "draws": 0,
    "rounds_won": 39,
    "rounds_lost": 24,
    "round_diff": 15,
    "points": 9,  // Typically 3 pts per win
    "advances": true,  // Top 2 advance (highlighted green)
    "tiebreaker_info": null  // "Head-to-head: 1-0 vs Team B" if tied
  },
  {
    "rank": 2,
    "participant": {
      "id": 22,
      "name": "Team Omega",
      "logo_url": "/media/teams/omega-logo.png"
    },
    "matches_played": 3,
    "wins": 2,
    "losses": 1,
    "draws": 0,
    "rounds_won": 32,
    "rounds_lost": 28,
    "round_diff": 4,
    "points": 6,
    "advances": true,
    "tiebreaker_info": null
  },
  {
    "rank": 3,
    "participant": {
      "id": 31,
      "name": "Team Charlie",
      "logo_url": "/media/teams/charlie-logo.png"
    },
    "matches_played": 3,
    "wins": 1,
    "losses": 2,
    "draws": 0,
    "rounds_won": 27,
    "rounds_lost": 33,
    "round_diff": -6,
    "points": 3,
    "advances": false,
    "tiebreaker_info": null
  }
]
```

**Usage Notes**:
- `advances` flag determines row highlighting (green = advances)
- `tiebreaker_info` displayed as tooltip when hovering rank
- `round_diff` shown with +/- sign for visual clarity

---

### 4.5 Bracket Node (Match Slot)

**Endpoint**: `GET /api/v1/tournaments/{id}/bracket/`

**JSON Structure** (Array of bracket nodes):
```json
{
  "bracket_type": "single_elimination",
  "rounds": [
    {
      "round_number": 1,
      "round_name": "Round of 16",
      "matches": [
        {
          "match_id": 201,
          "slot_id": "R1-M1",  // Frontend reference for positioning
          "position": 1,
          "participant1": {
            "id": 15,
            "name": "Team Alpha",
            "seed": 1,
            "logo_url": "/media/teams/alpha-logo.png",
            "score": 13
          },
          "participant2": {
            "id": 22,
            "name": "Team Omega",
            "seed": 16,
            "logo_url": "/media/teams/omega-logo.png",
            "score": 7
          },
          "state": "completed",
          "winner_id": 15,
          "next_match_slot": "R2-M1",  // Where winner advances
          "loser_next_match_slot": null  // For double elimination
        },
        {
          "match_id": 202,
          "slot_id": "R1-M2",
          "position": 2,
          "participant1": {
            "id": 8,
            "name": "Team Beta",
            "seed": 8,
            "logo_url": "/media/teams/beta-logo.png",
            "score": null
          },
          "participant2": {
            "id": null,
            "name": "TBD",  // Placeholder for unknown participant
            "seed": null,
            "logo_url": null,
            "score": null
          },
          "state": "pending",
          "winner_id": null,
          "next_match_slot": "R2-M1",
          "loser_next_match_slot": null
        }
      ]
    },
    {
      "round_number": 2,
      "round_name": "Quarterfinals",
      "matches": [
        {
          "match_id": 211,
          "slot_id": "R2-M1",
          "position": 1,
          "participant1": {
            "id": 15,
            "name": "Team Alpha",
            "seed": 1,
            "logo_url": "/media/teams/alpha-logo.png",
            "score": null
          },
          "participant2": {
            "id": null,
            "name": "TBD",
            "seed": null,
            "logo_url": null,
            "score": null
          },
          "state": "pending",
          "winner_id": null,
          "next_match_slot": "R3-M1",
          "loser_next_match_slot": null
        }
      ]
    }
  ]
}
```

**Usage Notes**:
- `slot_id` used for CSS positioning in bracket tree
- `next_match_slot` creates visual connections (arrows) between rounds
- `participant.name = "TBD"` renders as grayed-out placeholder
- Frontend uses `rounds` array to create columns (Round 1, Round 2, etc.)

---

### 4.6 Result Inbox Item (Organizer View)

**Endpoint**: `GET /api/v1/organizer/tournaments/{id}/results-inbox/`

**JSON Structure**:
```json
[
  {
    "id": 401,
    "match": {
      "id": 256,
      "match_display": "Match 12",
      "round_display": "Semifinals",
      "participant1_name": "Team Alpha",
      "participant2_name": "Team Omega"
    },
    "submission_type": "disputed",  // pending, disputed, conflicted
    "submission_type_display": "Disputed",
    "submitted_at": "2025-12-21T16:20:00Z",
    "age_display": "2 hours ago",
    "submitted_by": {
      "participant_id": 15,
      "participant_name": "Team Alpha",
      "user": "Player1"
    },
    "claimed_winner_id": 15,
    "claimed_winner_name": "Team Alpha",
    "scores": {
      "participant1": 13,
      "participant2": 7
    },
    "proof_screenshot": "/media/results/401/proof.png",
    "notes": "Close game, GG!",
    "dispute": {
      "id": 51,
      "disputed_by": {
        "participant_id": 22,
        "participant_name": "Team Omega",
        "user": "Player10"
      },
      "disputed_at": "2025-12-21T17:00:00Z",
      "reason": "incorrect_score",
      "reason_display": "Incorrect Score",
      "explanation": "The actual score was 13-8, not 13-7. Proof attached.",
      "counter_proof": "/media/disputes/51/counter-proof.png"
    },
    "conflicting_submission": null,  // If submission_type = "conflicted"
    "organizer_actions_available": [
      "approve_original",
      "approve_dispute",
      "order_rematch",
      "manual_override"
    ]
  },
  {
    "id": 402,
    "match": {
      "id": 257,
      "match_display": "Match 13",
      "round_display": "Semifinals",
      "participant1_name": "Team Delta",
      "participant2_name": "Team Echo"
    },
    "submission_type": "conflicted",
    "submission_type_display": "Conflicted",
    "submitted_at": "2025-12-21T18:00:00Z",
    "age_display": "30 minutes ago",
    "submitted_by": {
      "participant_id": 40,
      "participant_name": "Team Delta",
      "user": "Player20"
    },
    "claimed_winner_id": 40,
    "claimed_winner_name": "Team Delta",
    "scores": {"participant1": 13, "participant2": 10},
    "proof_screenshot": "/media/results/402/proof.png",
    "notes": null,
    "dispute": null,
    "conflicting_submission": {
      "id": 403,
      "submitted_by": {
        "participant_id": 45,
        "participant_name": "Team Echo",
        "user": "Player25"
      },
      "submitted_at": "2025-12-21T18:05:00Z",
      "claimed_winner_id": 45,
      "claimed_winner_name": "Team Echo",
      "scores": {"participant1": 10, "participant2": 13},
      "proof_screenshot": "/media/results/403/proof.png"
    },
    "organizer_actions_available": [
      "approve_submission_402",
      "approve_submission_403",
      "order_rematch",
      "manual_override"
    ]
  }
]
```

**Usage Notes**:
- `submission_type` determines inbox tab (Pending, Disputed, Conflicted)
- `dispute` object present only if `submission_type = "disputed"`
- `conflicting_submission` present only if `submission_type = "conflicted"`
- `organizer_actions_available` dynamically generates action buttons
- `age_display` shows human-readable time ("2 hours ago")

---

### 4.7 Registration Form Schema (Dynamic Fields)

**Endpoint**: `GET /api/v1/tournaments/{id}/registration-schema/`

**JSON Structure**:
```json
{
  "tournament": {
    "id": 42,
    "name": "VCT Champions 2025",
    "game": "valorant",
    "is_team_based": true,
    "team_size": 5
  },
  "steps": [
    {
      "step_number": 1,
      "step_name": "Team Selection",
      "step_description": "Select or create your team",
      "fields": [
        {
          "name": "participant_type",
          "type": "radio",
          "label": "I am registering as:",
          "required": true,
          "options": [
            {"value": "team_captain", "label": "Team Captain (creating new team)"},
            {"value": "team_member", "label": "Team Member (joining existing team)"}
          ]
        },
        {
          "name": "team_id",
          "type": "select",
          "label": "Select Team",
          "required": true,
          "conditional": {"field": "participant_type", "value": "team_member"},
          "options": [],  // Populated via AJAX
          "help_text": "Select the team you want to join"
        },
        {
          "name": "team_name",
          "type": "text",
          "label": "Team Name",
          "required": true,
          "conditional": {"field": "participant_type", "value": "team_captain"},
          "validation": {"min_length": 3, "max_length": 50}
        }
      ]
    },
    {
      "step_number": 2,
      "step_name": "Identity & Game Accounts",
      "step_description": "Verify your identity and game account",
      "fields": [
        {
          "name": "email",
          "type": "email",
          "label": "Email Address",
          "required": true,
          "auto_fill": true,
          "locked": true,
          "value": "user@example.com",
          "help_text": "Auto-filled from your profile (verified)"
        },
        {
          "name": "riot_id",
          "type": "game_identity",
          "label": "Riot ID",
          "required": true,
          "game": "valorant",
          "format": "username#tag",
          "validation_pattern": "^[a-zA-Z0-9\\s]{3,16}#[a-zA-Z0-9]{3,5}$",
          "auto_fill": true,
          "locked": false,
          "value": "Player1#NA1",
          "verification_required": true,
          "help_text": "Your Riot ID in the format: Username#TAG"
        },
        {
          "name": "rank",
          "type": "select",
          "label": "Current Rank",
          "required": true,
          "options": [
            {"value": "iron", "label": "Iron"},
            {"value": "bronze", "label": "Bronze"},
            {"value": "silver", "label": "Silver"},
            {"value": "gold", "label": "Gold"},
            {"value": "platinum", "label": "Platinum"},
            {"value": "diamond", "label": "Diamond"},
            {"value": "immortal", "label": "Immortal"},
            {"value": "radiant", "label": "Radiant"}
          ]
        }
      ]
    },
    {
      "step_number": 3,
      "step_name": "Tournament-Specific Questions",
      "step_description": "Answer game-specific questions",
      "fields": [
        {
          "name": "preferred_role",
          "type": "select",
          "label": "Preferred Role",
          "required": true,
          "options": [
            {"value": "duelist", "label": "Duelist"},
            {"value": "controller", "label": "Controller"},
            {"value": "sentinel", "label": "Sentinel"},
            {"value": "initiator", "label": "Initiator"}
          ]
        },
        {
          "name": "region",
          "type": "select",
          "label": "Region",
          "required": true,
          "options": [
            {"value": "na", "label": "North America"},
            {"value": "eu", "label": "Europe"},
            {"value": "apac", "label": "APAC"},
            {"value": "latam", "label": "LATAM"}
          ]
        }
      ]
    },
    {
      "step_number": 4,
      "step_name": "Documents & Verification",
      "step_description": "Upload required documents",
      "fields": [
        {
          "name": "rank_screenshot",
          "type": "file",
          "label": "Rank Screenshot",
          "required": true,
          "accept": "image/*",
          "max_size": 5242880,
          "help_text": "Upload a screenshot showing your current rank (max 5MB)"
        },
        {
          "name": "terms_accepted",
          "type": "checkbox",
          "label": "I agree to the tournament rules and code of conduct",
          "required": true
        }
      ]
    },
    {
      "step_number": 5,
      "step_name": "Payment & Confirmation",
      "step_description": "Complete payment and review your registration",
      "fields": [
        {
          "name": "payment_method",
          "type": "radio",
          "label": "Payment Method",
          "required": true,
          "options": [
            {"value": "deltacoin", "label": "DeltaCoin (10 DC)"},
            {"value": "manual", "label": "Manual Payment (Bank Transfer)"}
          ]
        },
        {
          "name": "payment_proof",
          "type": "file",
          "label": "Payment Proof Screenshot",
          "required": true,
          "conditional": {"field": "payment_method", "value": "manual"},
          "accept": "image/*",
          "max_size": 5242880
        }
      ]
    }
  ],
  "draft_autosave_enabled": true,
  "draft_autosave_interval": 30  // seconds
}
```

**Usage Notes**:
- `steps` array drives multi-step wizard UI
- `conditional` field shows/hides fields based on other field values (e.g., team selection)
- `auto_fill` indicates field pre-populated from user profile
- `locked` means field cannot be edited (verified data)
- `validation` object contains frontend validation rules
- `verification_required` triggers real-time API validation (e.g., Riot ID check)
- Frontend uses this schema to dynamically render the registration form

---

## 5. Key User Flows (Step-by-Step UI Interactions)

### 5.1 Smart Registration Flow (Multi-Step Wizard)

**Scenario**: A player wants to register for "VCT Champions 2025" as a team captain.

**User Actions & UI Responses**:

#### Step 0: Entry Point
1. **User clicks**: "Register Now" button on Tournament Detail page
2. **UI displays**: Loading spinner
3. **Backend checks**: User eligibility (logged in, meets requirements, slots available)
4. **UI transitions**: Navigate to Registration Wizard (`/tournaments/vct-champions-2025/register/`)

---

#### Step 1: Team Selection
**UI displays**:
- Progress bar: "Step 1 of 5 - Team Selection"
- Header: "How are you registering?"
- Radio buttons:
  - ○ Team Captain (creating new team)
  - ○ Team Member (joining existing team)

**User selects**: "Team Captain"

**UI updates** (conditional rendering):
- Hides: "Select Team" dropdown
- Shows: "Team Name" text input field
  - Label: "Team Name *"
  - Placeholder: "Enter your team name"
  - Help text: "3-50 characters, unique name"

**User types**: "Team Alpha" in Team Name field

**Real-time validation**:
- After 500ms of no typing, frontend sends: `POST /api/v1/validate-field/`
  ```json
  {"field": "team_name", "value": "Team Alpha", "tournament_id": 42}
  ```
- Backend responds: `{"valid": true}` or `{"valid": false, "error": "Team name already taken"}`
- UI shows: Green checkmark ✓ or red error message

**User clicks**: "Next" button

**Frontend validation**:
- Checks all required fields filled
- If valid: Enable "Next" button, proceed
- If invalid: Highlight missing fields with red borders, show error messages

**UI transitions**: Advance to Step 2

**Background action**: Auto-save draft (`POST /api/v1/drafts/{uuid}/autosave/` with current data)

---

#### Step 2: Identity & Game Accounts
**UI displays**:
- Progress bar: "Step 2 of 5 - Identity & Game Accounts"
- Auto-filled fields (with "Auto-filled from profile" badge):
  - Email: `user@example.com` [🔒 locked, grayed out]
  - Full Name: `John Doe` [🔒 locked]
- Editable field:
  - Riot ID: `Player1#NA1` [pre-filled but editable]
    - Status badge: 🟡 "Unverified"
    - Button: "Verify Riot ID"
- Dropdown:
  - Current Rank: [Select rank...] ▼

**User sees**: Email and name are locked with tooltip ("These fields are verified and cannot be changed. Update in your profile if needed.")

**User edits**: Riot ID to `Player123#NA1`

**User clicks**: "Verify Riot ID" button

**UI updates**:
- Button changes to: "Verifying..." [disabled, spinner]
- Frontend sends: `POST /api/v1/validate-game-identity/`
  ```json
  {"game": "valorant", "identity": "Player123#NA1"}
  ```

**Backend responds** (2 scenarios):

**Scenario A - Success**:
```json
{"verified": true, "player_data": {"level": 120, "rank": "Immortal 2"}}
```
- UI updates:
  - Button: "✓ Verified" [green, disabled]
  - Badge: 🟢 "Verified via Riot API"
  - Auto-fill rank field: "Immortal 2" selected

**Scenario B - Failure**:
```json
{"verified": false, "error": "Riot ID not found"}
```
- UI updates:
  - Button: "Verify Riot ID" [enabled again]
  - Error message: "❌ Riot ID not found. Please check and try again."
  - Badge: 🔴 "Verification failed"

**User selects**: Rank from dropdown (if not auto-filled)

**User clicks**: "Next"

**UI transitions**: Advance to Step 3

---

#### Step 3: Tournament-Specific Questions
**UI displays**:
- Progress bar: "Step 3 of 5 - Tournament-Specific Questions"
- Game-specific questions (from backend schema):
  - Preferred Role: [Select role...] ▼
    - Options: Duelist, Controller, Sentinel, Initiator
  - Region: [Select region...] ▼
    - Options: North America, Europe, APAC, LATAM

**User selects**:
- Preferred Role: "Duelist"
- Region: "North America"

**User clicks**: "Next"

**UI transitions**: Advance to Step 4

**Background action**: Auto-save draft (all data from Steps 1-3)

---

#### Step 4: Documents & Verification
**UI displays**:
- Progress bar: "Step 4 of 5 - Documents & Verification"
- File upload field:
  - Label: "Rank Screenshot *"
  - Help text: "Upload a screenshot showing your current rank (max 5MB)"
  - Upload button: [📁 Choose File]
- Checkbox:
  - ☐ I agree to the tournament rules and code of conduct
    - "rules and code of conduct" is a clickable link → opens modal with full text

**User clicks**: "Choose File" button

**Browser opens**: File picker dialog

**User selects**: `rank_screenshot.png` (3.2 MB)

**Frontend validation**:
- Checks file size: 3.2 MB < 5 MB ✓
- Checks file type: image/png ✓
- UI updates:
  - Shows image preview (thumbnail)
  - Displays: "rank_screenshot.png (3.2 MB)" with [X] remove button
  - Upload field shows: ✓ "Uploaded successfully"

**User checks**: "I agree to the tournament rules..." checkbox

**User clicks**: "Next"

**Frontend uploads file**:
- Shows upload progress bar: "Uploading... 45%"
- Sends: `POST /api/v1/registrations/upload-document/` (multipart form data)
- Backend responds: `{"url": "/media/registrations/draft-001/rank.png"}`
- UI updates: Progress bar → "✓ Upload complete"

**UI transitions**: Advance to Step 5

---

#### Step 5: Payment & Confirmation
**UI displays**:
- Progress bar: "Step 5 of 5 - Payment & Confirmation"
- Payment section:
  - Label: "Payment Method *"
  - Radio buttons:
    - ● DeltaCoin (10 DC) [selected by default]
      - Shows: "Current balance: 25 DC"
    - ○ Manual Payment (Bank Transfer)
- Review section (collapsible accordion):
  - Team Details: Team Name, Captain
  - Identity: Email, Riot ID (verified ✓), Rank
  - Questions: Role, Region
  - Documents: Rank Screenshot (thumbnail, ✓ uploaded)
  - Payment: DeltaCoin (10 DC)

**User selects**: "Manual Payment" radio button

**UI updates** (conditional rendering):
- Hides: DeltaCoin balance
- Shows: 
  - Bank account details (organizer's account info)
  - File upload field: "Payment Proof Screenshot *"
  - Help text: "Upload a screenshot of your bank transfer confirmation"

**User clicks**: "Choose File" → selects `payment_proof.png`

**UI updates**: Shows preview and ✓ "Uploaded successfully"

**User clicks**: "Review Registration" button (expands accordion)

**User reviews** all information displayed in accordion sections

**User clicks**: "Submit Registration" button

**Frontend validation**:
- Checks all required fields across all steps
- If invalid: Scroll to first error, highlight field, show error message
- If valid: Proceed

**UI displays**: Confirmation modal
- Title: "Confirm Registration"
- Message: "You are about to submit your registration for VCT Champions 2025. Entry fee: 10 DC via Manual Payment. Continue?"
- Buttons: [Cancel] [Confirm & Submit]

**User clicks**: "Confirm & Submit"

**UI updates**:
- Modal shows: "Submitting..." with spinner
- Button disabled

**Frontend sends**: `POST /api/v1/tournaments/42/register/` with all form data

**Backend processes** (takes 2-3 seconds):
- Validates all fields
- Creates registration record
- Processes payment (or marks as pending)
- Generates registration number

**Backend responds**:
```json
{
  "success": true,
  "registration_number": "VCT-2025-001234",
  "status": "pending",
  "message": "Registration submitted successfully. Pending organizer verification."
}
```

**UI displays**: Success modal
- Title: "✓ Registration Submitted!"
- Registration number: `VCT-2025-001234` (large, bold, copyable)
- Message: "Your registration is pending verification. You'll receive an email once it's reviewed."
- Status: 🟡 "Pending Verification"
- Buttons: [View My Registration] [Back to Tournament]

**User clicks**: "View My Registration"

**UI navigates**: To `/my-tournaments/` with registration highlighted

**Background action**: Delete draft (registration completed)

---

### 5.2 Match Result Submission Flow (Player → Opponent → Organizer)

**Scenario**: Team Alpha played Match 12 against Team Omega. Team Alpha wants to submit the result.

#### Phase 1: Player Submits Result

**User navigates**: To Match Details page (`/matches/256/`)

**UI displays**:
- Match header: "Match 12 - Semifinals"
- Participants: Team Alpha vs Team Omega
- State badge: 🔵 "Live"
- Match started: "2 hours ago"
- Action button: [Submit Result] (visible only to participants)

**User clicks**: "Submit Result" button

**UI displays**: Result Submission modal
- Title: "Submit Match Result - Match 12"
- Form fields:
  - Winner: Radio buttons
    - ● Team Alpha
    - ○ Team Omega
  - Score fields (game-specific, from schema):
    - Team Alpha Score: [__] (number input)
    - Team Omega Score: [__]
  - Map dropdown: [Select map...] ▼ (Ascent, Bind, Haven, etc.)
  - Proof Screenshot: [📁 Choose File] *
  - Notes: [Optional notes...] (textarea, optional)

**User selects**:
- Winner: Team Alpha
- Team Alpha Score: 13
- Team Omega Score: 7
- Map: Ascent
- Uploads proof screenshot: `match_result.png`
- Types notes: "Close game, GG!"

**User clicks**: "Submit Result" button

**Frontend validation**:
- Winner selected: ✓
- Scores entered: ✓
- Proof uploaded: ✓
- UI enables submit button

**UI displays**: Confirmation
- "Are you sure? Score: 13-7, Winner: Team Alpha"
- Buttons: [Cancel] [Confirm]

**User clicks**: "Confirm"

**Frontend sends**: `POST /api/v1/matches/256/submit-result/`
```json
{
  "winner_id": 15,
  "scores": {"team_alpha": 13, "team_omega": 7},
  "map": "ascent",
  "proof_screenshot": "/media/temp/proof.png",
  "notes": "Close game, GG!"
}
```

**Backend responds**:
```json
{
  "success": true,
  "submission_id": 401,
  "match_state": "pending_confirmation",
  "message": "Result submitted. Waiting for Team Omega to confirm."
}
```

**UI updates**:
- Modal closes
- Match state changes: 🟡 "Pending Confirmation"
- Result display section appears:
  - "Result Submitted by Team Alpha"
  - Score: 13-7
  - Proof: [View Screenshot] (clickable thumbnail)
  - Status: "⏳ Waiting for Team Omega to confirm (24 hours)"
  - Countdown timer: "23:58:32 remaining"
- Action button changes: [Edit Result] (allows resubmission)

**User sees**: Banner notification
- "✓ Result submitted successfully. Team Omega has 24 hours to confirm or dispute."

---

#### Phase 2: Opponent Confirms or Disputes

**Team Omega player navigates**: To Match Details page (receives email notification)

**UI displays**:
- Match state: 🟡 "Pending Confirmation"
- Result submitted by Team Alpha:
  - Winner: Team Alpha
  - Score: 13-7 (Ascent)
  - Proof: [View Screenshot]
  - Notes: "Close game, GG!"
- Confirmation section (visible only to Team Omega):
  - Message: "Team Alpha submitted a result. Do you agree?"
  - Buttons: [✓ Confirm Result] [⚠️ Dispute Result]

**Scenario A: Opponent Confirms**

**User clicks**: "Confirm Result" button

**UI displays**: Confirmation modal
- "Confirm that Team Alpha won 13-7?"
- Buttons: [Cancel] [Confirm]

**User clicks**: "Confirm"

**Frontend sends**: `POST /api/v1/matches/256/confirm-result/`

**Backend responds**:
```json
{
  "success": true,
  "match_state": "completed",
  "winner_id": 15
}
```

**UI updates**:
- Match state: 🟢 "Completed"
- Result finalized badge: "✓ Result Confirmed"
- Winner highlighted: Team Alpha (bold name, green border)
- Action buttons removed
- Displays: "Match completed on Dec 21, 2025"

**Both teams receive**: Email notification "Match 12 result confirmed"

**Tournament bracket**: Automatically updated (Team Alpha advances)

---

**Scenario B: Opponent Disputes**

**User clicks**: "Dispute Result" button

**UI navigates**: To Dispute Submission page (`/matches/256/dispute/`)

**UI displays**: Dispute form
- Header: "Dispute Match Result - Match 12"
- Original submission display (for reference):
  - Team Alpha claimed: Winner (13-7)
  - Proof: [View Screenshot]
- Dispute form fields:
  - Reason: [Select reason...] ▼ *
    - Options: Incorrect Score, Fake Proof, Cheating, Wrong Winner
  - Detailed Explanation: [Explain...] * (textarea, 50-500 chars)
    - Character counter: "0 / 50 minimum"
  - Counter-Proof Screenshot: [📁 Choose File] (optional)

**User selects**:
- Reason: "Incorrect Score"
- Types explanation: "The actual score was 13-8, not 13-7. Our proof shows the correct final score."
- Uploads counter-proof: `correct_result.png`

**User clicks**: "Submit Dispute" button

**Frontend validation**:
- Reason selected: ✓
- Explanation length: 89 chars (≥ 50) ✓
- UI enables submit button

**UI displays**: Warning modal
- "⚠️ Submitting a dispute will flag this match for organizer review. False disputes may result in penalties."
- Buttons: [Cancel] [I Understand, Submit Dispute]

**User clicks**: "I Understand, Submit Dispute"

**Frontend sends**: `POST /api/v1/matches/256/dispute/`
```json
{
  "reason": "incorrect_score",
  "explanation": "The actual score was 13-8, not 13-7. Our proof shows the correct final score.",
  "counter_proof": "/media/temp/counter-proof.png"
}
```

**Backend responds**:
```json
{
  "success": true,
  "dispute_id": 51,
  "match_state": "disputed"
}
```

**UI updates**:
- Navigate back to Match Details
- Match state: 🔴 "Disputed"
- Dispute banner displayed:
  - "⚠️ This result is disputed by Team Omega"
  - Reason: "Incorrect Score"
  - Status: "Pending organizer review"
- Both teams see: Action buttons disabled
- Message: "An organizer will review this dispute within 24 hours."

**Both teams receive**: Email notification "Match 12 result disputed - under review"

---

#### Phase 3: Organizer Verifies & Resolves

**Organizer navigates**: To Results Inbox (`/organizer/tournaments/42/results/`)

**UI displays**: Inbox with tabbed navigation
- Tabs: Pending (0) | Disputed (1) 🔴 | Conflicted (0)
- Active tab: "Disputed"

**Disputed results list shows**:
```
┌────────────────────────────────────────────┐
│ Match 12: Team Alpha vs Team Omega  [🔴]  │
│ Submitted by: Team Alpha · 3 hours ago    │
│ ⚠️ Disputed by: Team Omega · 1 hour ago   │
└────────────────────────────────────────────┘
```

**Organizer clicks**: Result item

**UI displays**: Detail panel (right side)
- Original submission (Team Alpha):
  - Winner: Team Alpha
  - Score: 13-7 (Ascent)
  - Proof: [View Screenshot] → Click opens lightbox
  - Notes: "Close game, GG!"
- Dispute details (Team Omega):
  - Reason: "Incorrect Score"
  - Explanation: "The actual score was 13-8..."
  - Counter-Proof: [View Screenshot] → Click opens lightbox
- Side-by-side proof comparison:
  - Left: Team Alpha's proof
  - Right: Team Omega's counter-proof
- Action buttons:
  - [Approve Original (13-7)]
  - [Approve Dispute (13-8)]
  - [Order Rematch]
  - [Manual Override]

**Organizer clicks**: "View Screenshot" for both proofs

**UI displays**: Lightbox with image zoom
- Organizer compares screenshots
- Team Omega's proof clearly shows "13-8" final score
- Team Alpha's proof appears to be from an earlier round

**Organizer clicks**: "Approve Dispute (13-8)" button

**UI displays**: Confirmation modal
- Title: "Approve Dispute & Override Result"
- Message: "This will change the score to 13-8 and override Team Alpha's original submission. Both teams will be notified."
- Resolution notes field: [Required explanation...]
  - Placeholder: "Explain your decision (min 50 chars)"

**Organizer types**: "Reviewed both proofs. Team Omega's screenshot clearly shows final score of 13-8. Team Alpha's proof appears to be from Round 11, not the final. Result updated to 13-8."

**Organizer clicks**: "Confirm & Resolve"

**Frontend sends**: `POST /api/v1/organizer/disputes/51/resolve/`
```json
{
  "resolution": "approve_dispute",
  "new_scores": {"team_alpha": 13, "team_omega": 8},
  "winner_id": 15,
  "notes": "Reviewed both proofs. Team Omega's screenshot clearly shows..."
}
```

**Backend responds**:
```json
{
  "success": true,
  "match_state": "completed",
  "dispute_status": "resolved"
}
```

**UI updates**:
- Result item removed from "Disputed" tab
- Match state: 🟢 "Completed"
- Final score: 13-8 (updated)
- Dispute status: "✓ Resolved by OrganizerName"

**Both teams receive**: Email notification
- "Dispute resolved for Match 12"
- Final score: 13-8, Winner: Team Alpha
- Organizer notes included

**Tournament bracket**: Updated with final result

---

### 5.3 Organizer Bracket & Group Management Flow

**Scenario**: Organizer needs to create groups for a tournament, then transition to playoffs bracket.

#### Part A: Create & Manage Groups

**Organizer navigates**: To Bracket & Groups page (`/organizer/tournaments/42/bracket/`)

**UI displays**: Empty state (tournament not yet structured)
- Message: "No tournament structure created yet"
- Action button: [Create Tournament Structure]

**Organizer clicks**: "Create Tournament Structure" button

**UI displays**: Tournament Structure wizard modal
- Step 1: Select Format
  - Radio buttons:
    - ○ Single Stage (Bracket only)
    - ● Multi-Stage (Groups → Playoffs)
    - ○ Swiss System
- Step 2: Configure Stages (if Multi-Stage selected)

**Organizer selects**: "Multi-Stage (Groups → Playoffs)"

**UI updates**: Shows stage configuration
- Stage 1: Group Stage
  - Number of groups: [4] (dropdown: 2, 4, 8, 16)
  - Teams per group: [Auto (16 teams ÷ 4 groups = 4 per group)]
  - Group format: [Round Robin ▼]
  - Top N advance: [2] (top 2 from each group)
- Stage 2: Playoffs
  - Format: [Single Elimination ▼]
  - Seeding: [By group standings ▼]

**Organizer clicks**: "Generate Structure" button

**Frontend sends**: `POST /organizer/tournaments/42/generate-structure/`
```json
{
  "format": "multi_stage",
  "stages": [
    {
      "name": "Group Stage",
      "type": "group",
      "groups_count": 4,
      "group_format": "round_robin",
      "advancement_count": 2
    },
    {
      "name": "Playoffs",
      "type": "bracket",
      "bracket_format": "single_elimination",
      "seeding": "by_group_standings"
    }
  ]
}
```

**Backend responds**: Structure created

**UI updates**: Navigate to Group Stage view

---

**UI displays**: Group Stage Editor
- Tabs: [Overview] [Group A] [Group B] [Group C] [Group D] [Settings]
- Active tab: "Overview"
- Overview shows:
  - 4 group cards side-by-side
  - Group A: 4 teams (Team Alpha, Team Beta, Team Gamma, Team Delta)
  - Group B: 4 teams (Team Echo, Team Foxtrot, ...)
  - Group C: 4 teams (...)
  - Group D: 4 teams (...)
- Each group card shows:
  - Team list (draggable)
  - Matches generated: "6 matches" (round robin)
  - Action button: [View Group Details]

**Organizer clicks**: "Group A" tab

**UI displays**: Group A detail view
- Left panel: Team roster
  ```
  Group A Teams (4)
  ┌────────────────────────┐
  │ 1. Team Alpha      [≡] │ (drag handle)
  │ 2. Team Beta       [≡] │
  │ 3. Team Gamma      [≡] │
  │ 4. Team Delta      [≡] │
  └────────────────────────┘
  [+ Add Team] [Remove Team]
  ```
- Right panel: Matches table
  ```
  Round Robin Matches (6)
  ┌─────────────────────────────┬────────┐
  │ Team Alpha vs Team Beta     │ [Edit] │
  │ Team Alpha vs Team Gamma    │ [Edit] │
  │ Team Alpha vs Team Delta    │ [Edit] │
  │ Team Beta vs Team Gamma     │ [Edit] │
  │ Team Beta vs Team Delta     │ [Edit] │
  │ Team Gamma vs Team Delta    │ [Edit] │
  └─────────────────────────────┴────────┘
  ```
- Bottom panel: Standings (initially empty)
  - Message: "Standings will update as matches are completed"

**Organizer wants to swap teams**: Drag Team Delta to Group B

**Organizer drags**: Team Delta from Group A roster

**UI shows**: Drag overlay (semi-transparent team card following cursor)

**Organizer drops**: On Group B tab

**UI displays**: Confirmation modal
- "Move Team Delta from Group A to Group B?"
- Warning: "This will regenerate matches for both groups."
- Buttons: [Cancel] [Confirm Move]

**Organizer clicks**: "Confirm Move"

**Frontend sends**: `POST /organizer/tournaments/42/groups/move-team/`
```json
{
  "team_id": 31,
  "from_group": "A",
  "to_group": "B"
}
```

**Backend responds**: Teams moved, matches regenerated

**UI updates**:
- Group A: 3 teams (Team Alpha, Beta, Gamma)
- Group B: 5 teams (Team Echo, Foxtrot, ..., Delta)
- Matches regenerated for both groups
- Toast notification: "✓ Team Delta moved to Group B"

---

**Matches complete over time** (organizer reviews results)

**UI displays**: Updated standings in Group A tab
```
Group A Standings
┌────┬────────────┬────┬───┬───┬────────┐
│Rank│ Team       │ MP │ W │ L │ Points │
├────┼────────────┼────┼───┼───┼────────┤
│ 1  │ Team Alpha │ 3  │ 3 │ 0 │ 9 ✓    │
│ 2  │ Team Beta  │ 3  │ 2 │ 1 │ 6 ✓    │
│ 3  │ Team Gamma │ 3  │ 0 │ 3 │ 0      │
└────┴────────────┴────┴───┴───┴────────┘
✓ = Advances to Playoffs
```

**All groups complete their matches**

---

#### Part B: Transition to Playoffs Bracket

**UI displays**: Banner notification
- "✅ Group Stage completed. Ready to generate Playoffs bracket."
- Button: [Generate Playoffs Bracket]

**Organizer clicks**: "Generate Playoffs Bracket"

**UI displays**: Confirmation modal
- Title: "Generate Playoffs Bracket"
- Message: "This will create the Single Elimination bracket with the following teams:"
- Team list:
  - From Group A: Team Alpha (1st), Team Beta (2nd)
  - From Group B: Team Echo (1st), Team Foxtrot (2nd)
  - From Group C: Team India (1st), Team Juliet (2nd)
  - From Group D: Team Mike (1st), Team November (2nd)
- Total: 8 teams
- Seeding: "1st place teams seeded 1-4, 2nd place teams seeded 5-8"
- Buttons: [Cancel] [Generate Bracket]

**Organizer clicks**: "Generate Bracket"

**Frontend sends**: `POST /organizer/tournaments/42/advance-stage/`
```json
{
  "from_stage": "group_stage",
  "to_stage": "playoffs",
  "advancement_rules": {"top_n_per_group": 2}
}
```

**Backend responds**: Bracket created with 8 teams

**UI transitions**: Navigate to Bracket view tab

---

#### Part C: Edit & Manage Bracket

**UI displays**: Bracket Editor (Single Elimination, 8 teams)
```
Quarterfinals       Semifinals        Finals
┌─────────────┐
│ 1. Alpha    │─┐
└─────────────┘ │   ┌─────────────┐
                ├──>│ TBD         │─┐
┌─────────────┐ │   └─────────────┘ │
│ 5. Foxtrot  │─┘                   │   ┌─────────────┐
└─────────────┘                     ├──>│ TBD         │ 🏆
                                    │   └─────────────┘
┌─────────────┐                     │
│ 2. Echo     │─┐                   │
└─────────────┘ │   ┌─────────────┐ │
                ├──>│ TBD         │─┘
┌─────────────┐ │   └─────────────┘
│ 6. Beta     │─┘
└─────────────┘

...continues for all 8 teams
```

**Controls displayed**:
- Zoom buttons: [−] [+]
- Edit mode toggle: [✏️ Edit Mode] (currently off)
- Action buttons: [Reset Bracket] [Export Bracket]

**Organizer clicks**: "Edit Mode" toggle

**UI updates**: Edit mode activated
- Bracket nodes become interactive
- Drag handles (≡) appear on each team card
- Edit buttons appear on each match slot: [✎ Edit]

**Organizer realizes**: Team Foxtrot should face Team Beta (different quarterfinal)

**Organizer drags**: Team Foxtrot from Match QF-1 to Match QF-2

**UI shows**: Drag overlay + valid drop zones highlighted (green border)

**Organizer drops**: Team Foxtrot into Match QF-2 (replacing Team Beta's position)

**UI displays**: Swap confirmation modal
- "Swap Team Foxtrot and Team Beta positions?"
- Before:
  - QF-1: Team Alpha vs Team Foxtrot
  - QF-2: Team Echo vs Team Beta
- After:
  - QF-1: Team Alpha vs Team Beta
  - QF-2: Team Echo vs Team Foxtrot
- Buttons: [Cancel] [Confirm Swap]

**Organizer clicks**: "Confirm Swap"

**Frontend sends**: `POST /organizer/tournaments/42/bracket/swap-participants/`
```json
{
  "match1_id": 301,
  "match2_id": 302,
  "participant1_id": 22,
  "participant2_id": 8
}
```

**Backend responds**: Swap successful

**UI updates**:
- Bracket redraws with swapped positions
- Toast notification: "✓ Teams swapped successfully"

**Organizer clicks**: "Edit Mode" toggle (to disable edit mode)

**UI updates**: Bracket locked (no more drag/drop)

---

**Organizer wants to manually set a match result** (for testing or admin override)

**Organizer clicks**: Match card (QF-1: Team Alpha vs Team Beta)

**UI displays**: Match detail modal
- Match info: Quarterfinals - Match 1
- Participants: Team Alpha vs Team Beta
- State: Pending
- Action button: [✏️ Set Result Manually]

**Organizer clicks**: "Set Result Manually"

**UI displays**: Manual result entry form
- Winner: [Team Alpha ▼]
- Scores:
  - Team Alpha: [13]
  - Team Beta: [7]
- Reason: [Testing ▼] (options: Testing, Admin Override, No-Show, Disqualification)
- Notes: [Optional notes...]

**Organizer fills**:
- Winner: Team Alpha
- Scores: 13-7
- Reason: "Testing"

**Organizer clicks**: "Save Result"

**Frontend sends**: `POST /organizer/tournaments/42/matches/301/manual-result/`
```json
{
  "winner_id": 15,
  "scores": {"team_alpha": 13, "team_beta": 7},
  "reason": "testing",
  "notes": ""
}
```

**Backend responds**: Result saved, match completed

**UI updates**:
- Match QF-1 state: Completed
- Winner: Team Alpha (highlighted)
- Score: 13-7 displayed
- Bracket updates: Team Alpha advances to SF-1
  - Semifinals Match 1 now shows: Team Alpha vs TBD
- Toast notification: "✓ Result saved. Team Alpha advanced to Semifinals."

**Organizer continues managing bracket** until tournament completes

---

## 6. Bracket & Groups UI Guidelines

### 6.1 Group Stage Tables

#### 6.1.1 Table Structure & Columns

**Required Columns** (in order):
1. **Rank** - Numeric position (1, 2, 3, ...)
2. **Team/Player** - Name + logo (clickable to profile)
3. **MP** (Matches Played) - Total matches
4. **W** (Wins) - Wins count
5. **L** (Losses) - Losses count
6. **D** (Draws) - Draws count (optional, if game supports draws)
7. **Rounds** - Round differential (+15, -3, etc.)
8. **Points** - Total points (typically 3 per win, 1 per draw)

**Optional Columns** (game-specific):
- **GF/GA** (Goals For/Against) - For soccer games
- **K/D** - Kill/Death ratio (FPS games)
- **Maps Won/Lost** - For multi-map games

**Column Alignment**:
- Text columns (Team, Player): Left-aligned
- Numeric columns (MP, W, L, Points): Center-aligned
- Rank: Center-aligned

---

#### 6.1.2 Sorting Rules

**Default Sort**: By rank (ascending: 1, 2, 3, ...)

**User Sorting**:
- Click column header → Sort by that column
- First click: Descending (highest first)
- Second click: Ascending (lowest first)
- Third click: Reset to default (by rank)

**Visual Indicators**:
- Sorted column: Bold header + arrow icon (↑ or ↓)
- Hoverable headers: Underline on hover (indicates sortable)

---

#### 6.1.3 Highlighting & Visual Cues

**Advancement Zones** (top N teams advance):
- **Green background** (light, subtle): Rows where `advances: true`
- **Checkmark icon** (✓): Next to team name in advancing rows
- **Separator line** (thick border): Between last advancing team and first eliminated team

**Elimination Zones**:
- **Red background** (very light): Bottom teams (if tournament has relegation/elimination)
- **X icon** (✗): Next to team name for eliminated teams

**Tied Teams**:
- **Yellow/Orange highlight**: Rows with same points (tiebreaker situation)
- **Tiebreaker tooltip**: Hover rank → Show tiebreaker explanation
  - Example: "Tied on points. Team A advances due to head-to-head record (1-0)."

**Current User's Team**:
- **Bold text**: Highlight user's team row
- **Blue left border** (thick): Visual indicator

---

#### 6.1.4 Responsive Behavior

**Desktop (≥ 1024px)**:
- Full table with all columns visible
- Fixed header (scrolls with content)
- Hover effects on rows

**Tablet (768px - 1023px)**:
- Hide optional columns (Rounds, K/D)
- Keep: Rank, Team, MP, W, L, Points
- Horizontal scroll if needed

**Mobile (< 768px)**:
- Switch to **card layout** instead of table:
  ```
  ┌─────────────────────────────┐
  │ 1. Team Alpha          ✓    │
  │ 3-0-0 (9 pts) · +15 rounds  │
  └─────────────────────────────┘
  ┌─────────────────────────────┐
  │ 2. Team Beta           ✓    │
  │ 2-1-0 (6 pts) · +5 rounds   │
  └─────────────────────────────┘
  ```
- Card shows: Rank, Team name, Record (W-L-D), Points, Round diff
- Advancement checkmark visible
- Tap card → Expand to show full details

---

### 6.2 Bracket Visualization

#### 6.2.1 Single Elimination Bracket

**Layout Structure**:
- **Horizontal flow**: Left (early rounds) → Right (finals)
- **Round columns**: Each round = vertical column
- **Match nodes**: Boxes containing team names + scores
- **Connection lines**: Arrows/lines from match to next round

**Match Node Design**:
```
┌─────────────────────┐
│ Team Alpha      13  │ ← Winner (bold, highlighted)
├─────────────────────┤
│ Team Omega       7  │ ← Loser (normal text)
└─────────────────────┘
```

**Visual Rules**:
- **Winner**: Bold name, green checkmark, thicker border
- **Loser**: Normal text, grayed out
- **TBD slots**: Grayed background, "TBD" placeholder text
- **Live match**: Blue border, pulsing animation
- **Connection lines**: Arrow from winner's side → next match

**Spacing**:
- Match height: 60px (2 teams × 30px each)
- Vertical gap between matches: 20px (early rounds), exponentially increases
- Round width: 200px per column
- Connection line width: 2px

---

#### 6.2.2 Double Elimination Bracket

**Layout Structure**:
- **Two sections**: Upper bracket (winners) + Lower bracket (losers)
- **Upper bracket**: Standard single-elim flow
- **Lower bracket**: Below upper bracket, receives losers from upper
- **Grand Finals**: Center bottom, combines upper/lower winners

**Visual Separation**:
- **Upper bracket**: Top half, white/light background
- **Lower bracket**: Bottom half, light gray background
- **Divider line**: Thick horizontal line separating upper/lower

**Connection Lines**:
- Upper bracket losers → Lower bracket (diagonal lines downward)
- Color-coded: Red/orange for "loser drops" connections

**Mobile Behavior**:
- Stack sections vertically: Upper bracket, then Lower bracket
- Horizontal scroll within each section

---

#### 6.2.3 Swiss System & League Formats

**Swiss System**:
- **Table view** (standings table, similar to groups)
- **Upcoming pairings**: Show next round matchups in separate section
- **Round history**: Accordion showing past rounds with match results

**UI Structure**:
```
┌─────────────────────────────────────┐
│ Standings (After Round 3)           │
│ [Standings Table]                   │
├─────────────────────────────────────┤
│ Round 4 Pairings                    │
│ Team Alpha vs Team Beta             │
│ Team Gamma vs Team Delta            │
├─────────────────────────────────────┤
│ Previous Rounds ▼                   │
│ > Round 3 (completed)               │
│ > Round 2 (completed)               │
│ > Round 1 (completed)               │
└─────────────────────────────────────┘
```

**League/Round Robin**:
- **Standings table** (main view)
- **Fixtures tab**: All matches in chronological order
- **Results tab**: Completed matches with scores

---

#### 6.2.4 Responsive Bracket Behavior

**Desktop (≥ 1024px)**:
- Full bracket tree visualization
- Zoom controls (+ / −)
- Pan/drag to navigate large brackets
- Hover match node → Tooltip with details

**Tablet (768px - 1023px)**:
- Horizontal scroll enabled
- Zoom controls visible
- Smaller match nodes (150px width instead of 200px)

**Mobile (< 768px)**:
- **Switch to list view** instead of tree:
  ```
  Round 1 (Completed)
  ┌─────────────────────────────┐
  │ Match 1: Team A 13-7 Team B │
  │ Match 2: Team C 10-13 Team D│
  └─────────────────────────────┘
  
  Round 2 (Semifinals)
  ┌─────────────────────────────┐
  │ Match 3: Team A vs Team D   │
  │ [View Match]                │
  └─────────────────────────────┘
  ```
- Accordion for rounds (expand/collapse)
- Tap match → Navigate to match details page

**Interactive Elements**:
- Click match node → Open match details modal/page
- Click team name → Navigate to team profile
- Hover connection line → Highlight path from start to current match

---

### 6.3 Bracket Integrity Visual Indicators

**Warnings & Errors**:
- **Orphaned matches**: Red border + warning icon
  - Tooltip: "This match has no participants from previous round"
- **Incomplete rounds**: Yellow banner above round
  - Message: "3 of 8 matches pending in this round"
- **Scheduling conflicts**: Orange highlight on conflicting matches
  - Tooltip: "Same team scheduled for multiple matches at same time"

**Edit Mode Indicators**:
- **Drag handles** (≡): Visible on match nodes when edit mode active
- **Drop zones**: Green dashed border when dragging over valid drop area
- **Invalid drops**: Red border + "X" cursor when hovering invalid area

---

## 7. Organizer Console UX & Guidance System

### 7.1 Organizer Dashboard Layout

#### 7.1.1 Dashboard Structure

**Top Section** (Header):
- Tournament name (H1)
- Status badge (Draft, Open, Live, Completed)
- Quick actions dropdown: [Publish] [Cancel Tournament] [Export Data]

**Main Content** (Grid Layout - 3 columns on desktop):

**Column 1: Key Metrics Cards**
```
┌────────────────────┐
│ Registrations      │
│ 45 / 64 (70%)      │
│ ↑ 12 today         │
└────────────────────┘

┌────────────────────┐
│ Pending Actions    │
│ 8 items            │
│ ⚠️ 2 urgent        │
└────────────────────┘

┌────────────────────┐
│ Matches            │
│ 12 completed       │
│ 4 pending results  │
└────────────────────┘
```

**Column 2: Action Cards (Prioritized)**
```
┌────────────────────────────┐
│ ⚠️ 3 Disputes Pending      │
│ [Review Disputes]          │
└────────────────────────────┘

┌────────────────────────────┐
│ ✓ Ready to Generate Bracket│
│ [Generate Bracket]         │
└────────────────────────────┘

┌────────────────────────────┐
│ 8 Pending Registrations    │
│ [Review Registrations]     │
└────────────────────────────┘
```

**Column 3: Recent Activity Feed**
```
┌────────────────────────────┐
│ Recent Activity            │
│ • Registration #001234     │
│   approved (5 min ago)     │
│ • Match 12 result verified │
│   (15 min ago)             │
│ • Team Alpha registered    │
│   (1 hour ago)             │
│ [View All Activity]        │
└────────────────────────────┘
```

**Color Coding**:
- **Red cards**: Urgent actions (disputes, overdue items)
- **Yellow cards**: Warnings (pending reviews)
- **Green cards**: Positive actions (ready to advance)
- **Blue cards**: Informational

---

#### 7.1.2 Navigation Patterns

**Sidebar Navigation** (Persistent left side):
```
Tournament Management
├─ 📊 Dashboard (active)
├─ 📝 Registrations (8)
├─ 🎯 Bracket & Groups
├─ ⚽ Matches (4)
├─ ✉️ Results Inbox (6)
├─ ⚠️ Disputes (3)
├─ 💰 Payouts
└─ ⚙️ Settings
```

**Count Badges**: Red circles with numbers (pending items)

**Active State**: Blue background + bold text

**Mobile Navigation**: Hamburger menu → Slide-out drawer

---

### 7.2 Results Inbox Interface

#### 7.2.1 Inbox Layout

**Tabbed Interface**:
- **Tab: Pending (6)** - Results awaiting opponent confirmation
- **Tab: Disputed (3)** - Results disputed by opponent
- **Tab: Conflicted (2)** - Both teams submitted different results
- **Tab: All (11)** - Complete history

**Active tab**: Bold + underline

**List-Detail Pattern**:
- **Left panel** (40%): Inbox list (scrollable)
- **Right panel** (60%): Selected item details

---

#### 7.2.2 Inbox Item Display

**List View** (each item):
```
┌────────────────────────────────────┐
│ Match 12: Team A vs Team B   [🔴] │ ← Status badge
│ Submitted by: Team A · 2h ago     │
│ ⚠️ Disputed: Incorrect score      │ ← Dispute flag
└────────────────────────────────────┘
```

**Status Badges**:
- 🟡 Yellow: Pending confirmation
- 🔴 Red: Disputed
- 🟠 Orange: Conflicted
- 🟢 Green: Resolved (archive)

**Sorting Options**:
- By date (newest first) - default
- By priority (disputed → conflicted → pending)
- By age (oldest first)

---

#### 7.2.3 Detail Panel Actions

**Pending Result** (no dispute):
```
┌──────────────────────────────────┐
│ Match 12 - Semifinals            │
│ Team A vs Team B                 │
├──────────────────────────────────┤
│ Submitted Result:                │
│ Winner: Team A (13-7)            │
│ Proof: [View Screenshot]         │
│ Notes: "Close game, GG!"         │
├──────────────────────────────────┤
│ Status: Awaiting Team B confirm  │
│ Time remaining: 23h 15m          │
├──────────────────────────────────┤
│ Organizer Actions:               │
│ [✓ Approve Result]               │
│ [✏️ Manual Override]             │
│ [✉️ Message Participants]        │
└──────────────────────────────────┘
```

**Disputed Result**:
```
┌──────────────────────────────────┐
│ Original Submission (Team A):    │
│ Winner: Team A (13-7)            │
│ Proof: [View] 📸                 │
├──────────────────────────────────┤
│ Dispute (Team B):                │
│ Reason: Incorrect Score          │
│ Explanation: "Score was 13-8..." │
│ Counter-Proof: [View] 📸         │
├──────────────────────────────────┤
│ [Compare Proofs Side-by-Side]   │ ← Opens lightbox
├──────────────────────────────────┤
│ Resolution Actions:              │
│ [Approve Original (13-7)]        │
│ [Approve Dispute (13-8)]         │
│ [Order Rematch]                  │
│ [Manual Override]                │
└──────────────────────────────────┘
```

---

#### 7.2.4 Bulk Actions

**Select Multiple Items**:
- Checkboxes on each inbox item
- Select all checkbox at top

**Bulk Actions Bar** (appears when items selected):
```
┌────────────────────────────────────┐
│ 3 items selected                   │
│ [Approve All] [Reject All] [Clear]│
└────────────────────────────────────┘
```

**Confirmation Modal** (before bulk action):
- "Approve 3 results? This cannot be undone."
- List of affected matches
- Buttons: [Cancel] [Confirm]

---

### 7.3 Dispute Handling UI

#### 7.3.1 Dispute Review Interface

**Side-by-Side Proof Comparison**:
```
┌──────────────┬──────────────┐
│ Original     │ Counter-Proof│
│ (Team A)     │ (Team B)     │
│              │              │
│ [Image]      │ [Image]      │
│              │              │
│ Click to     │ Click to     │
│ enlarge      │ enlarge      │
└──────────────┴──────────────┘
```

**Zoom Controls**:
- Click image → Open fullscreen lightbox
- Pinch-to-zoom on mobile
- Side-by-side sync scroll (optional)

---

#### 7.3.2 Resolution Form

**Required Fields**:
```
Resolution Decision: *
○ Approve original submission (13-7)
○ Approve dispute claim (13-8)
○ Order rematch
○ Manual override (custom result)

Resolution Notes: * (min 50 chars)
┌────────────────────────────────┐
│ Explain your decision...       │
│                                │
│ Character count: 0 / 50 min    │
└────────────────────────────────┘

[Cancel] [Resolve Dispute]
```

**Validation**:
- Decision selected: Required
- Notes min length: 50 characters
- Notes max length: 500 characters

**Confirmation Modal**:
- "Resolve dispute for Match 12?"
- Shows selected decision + notes preview
- Warning: "This will notify both teams and finalize the match result."
- Buttons: [Go Back] [Confirm Resolution]

---

### 7.4 Guidance & Help System

#### 7.4.1 Contextual Tooltips

**Trigger**: Hover (desktop) or tap info icon (mobile)

**Tooltip Design**:
- Small popup (max 200px width)
- Dark background, white text
- Arrow pointing to element
- Dismiss: Click outside or press Escape

**Tooltip Locations**:
- **Dashboard metrics**: "What does this number mean?"
- **Action buttons**: "What happens when I click this?"
- **Status badges**: "What does 'Pending Confirmation' mean?"
- **Form fields**: "What should I enter here?"

**Example Tooltips**:
- **Registrations (45/64)**: "45 verified registrations out of 64 max capacity. 70% full."
- **[Generate Bracket] button**: "This will create the tournament bracket based on current registrations. Cannot be undone."
- **Dispute reason**: "Select the primary reason for the dispute. This helps categorize issues."

---

#### 7.4.2 Step-by-Step Wizards

**First-Time User Guidance** (new organizer):
- On first dashboard visit: Show onboarding wizard modal
- 5-step introduction:
  1. "Welcome to Tournament Management"
  2. "Set up your tournament structure" → Navigate to Settings
  3. "Review registrations" → Navigate to Registrations
  4. "Generate bracket when ready" → Navigate to Bracket
  5. "Monitor matches and results" → Navigate to Results Inbox

**Progress Tracking**:
- Checklist sidebar widget: "Getting Started"
  - ☑ Create tournament ✓
  - ☑ Configure settings ✓
  - ☐ Review 10 registrations (8/10)
  - ☐ Generate bracket
  - ☐ Monitor first match

**Dismissible**: "Don't show again" checkbox

---

#### 7.4.3 Inline Help Messages

**Empty States** (when no data):
```
┌────────────────────────────────┐
│ No pending disputes 🎉         │
│                                │
│ You're all caught up!          │
│ Disputes will appear here when│
│ participants flag results.     │
└────────────────────────────────┘
```

**Warning Banners** (above content):
```
┌────────────────────────────────┐
│ ⚠️ Warning: 3 matches overdue  │
│ Some matches haven't been      │
│ played within the scheduled    │
│ time. [Review Matches]         │
└────────────────────────────────┘
```

**Info Banners** (guidance):
```
┌────────────────────────────────┐
│ ℹ️ Tip: Verifying registrations│
│ Check each participant's game  │
│ ID and payment before approval.│
│ [Learn More]                   │
└────────────────────────────────┘
```

**Color Coding**:
- Red: Error/Critical
- Yellow: Warning
- Blue: Info/Tip
- Green: Success

---

#### 7.4.4 "How This Works" Modals

**Trigger**: Clickable "?" icon or "How this works" link

**Modal Content** (example: Dispute Resolution):
```
┌──────────────────────────────────┐
│ How Dispute Resolution Works     │
├──────────────────────────────────┤
│ 1. Participant disputes result   │
│    • Provides reason & proof     │
│                                  │
│ 2. You review both submissions   │
│    • Compare proof screenshots   │
│    • Check match details         │
│                                  │
│ 3. Make a decision               │
│    • Approve original            │
│    • Approve dispute             │
│    • Order rematch               │
│                                  │
│ 4. Both teams are notified       │
│    • Email sent automatically    │
│    • Match result finalized      │
│                                  │
│ [Got It]                         │
└──────────────────────────────────┘
```

---

### 7.5 Role-Based UI (RBAC)

#### 7.5.1 Organizer (Full Access)
**Visible Elements**:
- All dashboard sections
- All action buttons (approve, reject, override, cancel)
- Settings and configuration
- Staff management
- Payout controls

---

#### 7.5.2 Staff/Moderator (Limited Access)
**Visible Elements**:
- Dashboard (read-only metrics)
- Review registrations (approve/reject only)
- Review results (cannot manually override)
- View disputes (cannot resolve, can add notes)

**Hidden/Disabled**:
- Tournament settings (grayed out)
- Cancel tournament button (hidden)
- Payout management (hidden)
- Staff management (hidden)

**Visual Indicator**: Role badge in header ("Staff" or "Moderator")

---

#### 7.5.3 Referee (Match-Specific Access)
**Visible Elements**:
- Assigned matches only (filtered view)
- Result submission interface
- Dispute flagging
- Match notes

**Hidden**:
- All registrations
- Full bracket editing
- Payouts
- Settings

**Visual Indicator**: "Referee" badge + assigned match list widget

---

## 8. Help & Tutorial Surfaces

### 8.1 Registration Wizard Help

**Step 1 (Team Selection)**:
- **Tooltip on "Team Captain"**: "As captain, you'll create a new team and invite members."
- **Tooltip on "Team Member"**: "Join an existing team by selecting it from the dropdown."
- **Info icon next to "Team Name"**: 
  - Click → Modal: "Team Name Guidelines"
    - 3-50 characters
    - No offensive language
    - Must be unique within tournament

**Step 2 (Game Identity)**:
- **"How to verify Riot ID" link**: Opens modal with screenshots
  - Step 1: Enter your Riot ID
  - Step 2: Click "Verify"
  - Step 3: System checks Riot API
  - Step 4: Verification badge appears
- **Inline help text**: "Your Riot ID is in the format Username#TAG (e.g., Player#NA1)"

**Step 3 (Documents)**:
- **"What is a rank screenshot?" link**: Opens modal with example image
  - Shows: "Take a screenshot of your in-game rank page showing your current rank and username."
- **File upload errors**: Inline error messages
  - "File too large (max 5MB)"
  - "Invalid file type (must be image)"

**Step 5 (Payment)**:
- **DeltaCoin info icon**: "DeltaCoin is our virtual currency. Current balance: 25 DC."
- **Manual payment help**: "Upload a screenshot of your bank transfer receipt showing transaction ID and amount."

---

### 8.2 Match Reporting Help

**Result Submission Form**:
- **"What is a valid proof screenshot?" link**: Opens modal
  - Example valid screenshots (in-game scoreboard showing final scores)
  - Example invalid screenshots (partial views, edited images)
  - Tips: "Include both team names and final scores in the screenshot"
  
**Dispute Form**:
- **"When should I dispute a result?" link**: Opens modal
  - Valid reasons: Incorrect scores, fake proof, cheating
  - Invalid reasons: Lost the match, didn't like opponent
  - Warning: "False disputes may result in penalties"

**Inline Guidance** (above submit button):
- "📝 Make sure your proof clearly shows the final score and both team names."

---

### 8.3 Bracket View Help

**First-Time Bracket View**:
- **Overlay tutorial** (dismissible):
  - Highlights bracket elements with arrows
  - "This is the tournament bracket showing all matches"
  - "Click any match to see details"
  - "Your team is highlighted in blue"
  - [Next] → [Got It, Don't Show Again]

**Interactive Elements**:
- **Hover TBD slots**: Tooltip "This participant will be determined by the outcome of previous matches"
- **Hover match node**: Tooltip shows:
  - Round name
  - Scheduled time
  - Current state
  - "Click for details"

---

### 8.4 Organizer Console Help

**Dashboard First Visit**:
- **Welcome banner** (dismissible):
  ```
  ┌──────────────────────────────────┐
  │ 👋 Welcome to your tournament    │
  │ dashboard!                       │
  │                                  │
  │ Key tasks to get started:        │
  │ • Review pending registrations   │
  │ • Configure tournament structure │
  │ • Generate bracket when ready    │
  │                                  │
  │ [Take a Tour] [Dismiss]          │
  └──────────────────────────────────┘
  ```

**Results Inbox Help**:
- **"?" icon** in header → Opens modal: "Understanding Result States"
  - Pending: Awaiting opponent confirmation (24-hour window)
  - Disputed: Opponent flagged the result
  - Conflicted: Both teams submitted different results
  - Action: You must review and make a decision

**Bracket Editor Help**:
- **Edit mode toggle tooltip**: "Enable edit mode to drag-and-drop teams and rearrange brackets"
- **Warning when dragging**: "Swapping teams will update bracket connections. Confirm before saving."

---

### 8.5 Tooltip Placement Guidelines

**General Rules**:
- Tooltips appear **above** element (if space available), otherwise below
- **Delay**: 500ms hover before showing (prevents accidental triggers)
- **Mobile**: Tap info icon (ℹ️) instead of hover
- **Max width**: 250px (wrap text if longer)
- **Dismiss**: Click outside, press Escape, or automatic after 10 seconds (for persistent tooltips)

**Accessibility**:
- Tooltips have `role="tooltip"` and `aria-describedby`
- Keyboard accessible (Tab to element → Tooltip shows)
- Screen reader friendly (text read aloud)

---

## 9. Frontend Developer Checklist

### 9.1 Phase 1: Project Setup & Layout
- [ ] Set up Django templates structure (`templates/` folder)
- [ ] Install and configure Tailwind CSS
  - [ ] Create `tailwind.config.js` with custom design tokens
  - [ ] Set up build process (PostCSS)
- [ ] Create base layout templates:
  - [ ] `base.html` (page shell with navbar, footer)
  - [ ] `base_auth.html` (for logged-in users)
  - [ ] `base_organizer.html` (organizer console layout with sidebar)
- [ ] Implement responsive navbar component
  - [ ] Desktop: Horizontal nav
  - [ ] Mobile: Hamburger menu
- [ ] Implement footer component
- [ ] Test layout on desktop, tablet, mobile

---

### 9.2 Phase 2: Core Components Library
- [ ] Build form components:
  - [ ] Text input (with label, error states, locked state)
  - [ ] Select dropdown (with search option)
  - [ ] Checkbox and radio buttons
  - [ ] File upload (with preview, progress bar)
  - [ ] Game identity field block (validation + verification)
  - [ ] Team roster editor (add/remove members)
- [ ] Build UI components:
  - [ ] Card component (variants: default, flat, bordered, hoverable)
  - [ ] Modal component (sizes: sm, md, lg, xl)
  - [ ] Button variants (primary, secondary, danger, success)
  - [ ] Badge components (status badges with colors)
  - [ ] Progress bar (multi-step wizard indicator)
  - [ ] Tooltip component (hover/click triggered)
- [ ] Build tournament-specific components:
  - [ ] Tournament card (for listing pages)
  - [ ] Match card (basic and expanded)
  - [ ] Registration status badge
- [ ] Test all components in isolation (component library page)

---

### 9.3 Phase 3: Player/Team Screens
- [ ] Build **Home / Discover Tournaments** page:
  - [ ] Hero section with featured tournaments
  - [ ] Tournament grid/list with filters
  - [ ] Search functionality
  - [ ] Pagination or infinite scroll
  - [ ] Empty state (no tournaments)
- [ ] Build **Tournament Detail** page:
  - [ ] Header (name, game, dates, status)
  - [ ] Tabbed interface (Overview, Rules, Participants, Bracket)
  - [ ] Registration status display
  - [ ] "Register Now" button (conditional visibility)
  - [ ] Countdown timer to registration close
- [ ] Build **Registration Wizard** (5-step multi-step form):
  - [ ] Step 1: Team Selection (conditional fields)
  - [ ] Step 2: Identity & Game Accounts (auto-fill, locked fields)
  - [ ] Step 3: Tournament-Specific Questions
  - [ ] Step 4: Documents & Verification (file uploads)
  - [ ] Step 5: Payment & Confirmation (review accordion)
  - [ ] Progress indicator component
  - [ ] Real-time validation (frontend + AJAX)
  - [ ] Auto-save draft functionality (every 30 seconds)
  - [ ] Draft recovery banner (if returning)
  - [ ] Success modal with registration number
- [ ] Build **My Tournaments Dashboard**:
  - [ ] Active tournaments section
  - [ ] Upcoming matches section
  - [ ] Tournament history section
  - [ ] Filters and search
- [ ] Build **Match Details** page:
  - [ ] Match header (participants, round, state)
  - [ ] State-based UI (Pending, Live, Pending Confirmation, Disputed, Completed)
  - [ ] Result submission form (modal or inline)
  - [ ] Opponent result confirmation UI
  - [ ] Dispute button (navigates to dispute form)
- [ ] Build **Dispute Submission Form**:
  - [ ] Display original submission
  - [ ] Dispute reason dropdown
  - [ ] Explanation textarea (character counter)
  - [ ] Counter-proof upload
  - [ ] Warning modal before submit
- [ ] Build **Profile & Game Accounts** page:
  - [ ] Profile overview
  - [ ] Connected accounts section (add/verify/remove)
  - [ ] Stats dashboard
  - [ ] Match history

---

### 9.4 Phase 4: Tournament Visualization
- [ ] Build **Group Standings Table**:
  - [ ] Desktop: Full table with all columns
  - [ ] Tablet: Hide optional columns
  - [ ] Mobile: Card layout
  - [ ] Sortable columns
  - [ ] Highlight advancement zones (green)
  - [ ] Tiebreaker tooltips
- [ ] Build **Bracket Visualization**:
  - [ ] Single Elimination bracket (horizontal tree)
  - [ ] Double Elimination bracket (upper/lower sections)
  - [ ] Match node component (team names, scores, state)
  - [ ] Connection lines (SVG or CSS)
  - [ ] Desktop: Full tree view with zoom controls
  - [ ] Mobile: List view (accordion by round)
  - [ ] Click match → Navigate to match details
  - [ ] Highlight user's team path
- [ ] Build **Swiss System View**:
  - [ ] Standings table
  - [ ] Upcoming pairings section
  - [ ] Round history accordion
- [ ] Test all formats on different screen sizes

---

### 9.5 Phase 5: Organizer Console
- [ ] Build **Organizer Dashboard**:
  - [ ] Sidebar navigation (with count badges)
  - [ ] Key metrics cards (registrations, matches, disputes)
  - [ ] Action cards (prioritized by urgency)
  - [ ] Recent activity feed
  - [ ] Mobile: Hamburger sidebar
- [ ] Build **Registration Management** page:
  - [ ] Registrations table (sortable, filterable)
  - [ ] Filter & search bar component
  - [ ] Registration detail panel (expandable rows)
  - [ ] Verification checklist UI
  - [ ] Document viewer (inline or modal)
  - [ ] Bulk actions (approve all, export CSV)
  - [ ] Approve/Reject buttons with modals
- [ ] Build **Bracket & Groups Management** page:
  - [ ] Tabbed interface (Overview, Groups, Bracket, Settings)
  - [ ] Tournament structure wizard (generate format)
  - [ ] Group editor:
    - [ ] Group roster with drag-and-drop
    - [ ] Matches table per group
    - [ ] Standings display
  - [ ] Bracket editor:
    - [ ] Interactive bracket with edit mode
    - [ ] Drag-and-drop team swapping
    - [ ] Validation warnings (orphaned matches)
    - [ ] Zoom and pan controls
  - [ ] Stage transition UI (Groups → Playoffs)
- [ ] Build **Match Operations** page:
  - [ ] Matches table (filterable by state, round)
  - [ ] Schedule match modal (date/time picker)
  - [ ] Manual result entry form
  - [ ] Bulk scheduling tools
- [ ] Build **Results Inbox**:
  - [ ] Tabbed interface (Pending, Disputed, Conflicted)
  - [ ] List-detail layout (inbox items + detail panel)
  - [ ] Result inbox item component
  - [ ] Proof image lightbox (side-by-side comparison)
  - [ ] Action buttons (approve, reject, override, rematch)
  - [ ] Resolution notes form
  - [ ] Bulk actions
- [ ] Build **Dispute Handling** page:
  - [ ] Disputes table
  - [ ] Dispute detail panel
  - [ ] Side-by-side proof comparison UI
  - [ ] Resolution form (with required notes)
  - [ ] Confirmation modals
- [ ] Build **Tournament Settings** page:
  - [ ] Tabbed settings (General, Stages, Registration, Rules, Staff)
  - [ ] Form fields with validation
  - [ ] Stage editor (add/edit/reorder stages)
  - [ ] Unsaved changes warning
- [ ] Build **Payouts** page:
  - [ ] Prize pool summary
  - [ ] Winners table
  - [ ] Payout status tracking
  - [ ] Export reports button

---

### 9.6 Phase 6: Help & Guidance Features
- [ ] Implement tooltip system:
  - [ ] Hover tooltips (desktop)
  - [ ] Tap-to-show tooltips (mobile with info icons)
  - [ ] Accessibility attributes (ARIA)
- [ ] Build "How This Works" modals:
  - [ ] Registration wizard help
  - [ ] Match reporting guidelines
  - [ ] Dispute resolution process
  - [ ] Bracket editing guide
- [ ] Create empty state components (for tables, lists, feeds)
- [ ] Create warning/info banner components
- [ ] Build first-time user onboarding wizard (organizer)
- [ ] Implement inline help text throughout forms

---

### 9.7 Phase 7: Data Integration
- [ ] Connect components to JSON data contracts:
  - [ ] Tournament card → `/api/v1/tournaments/`
  - [ ] Registration wizard → `/api/v1/tournaments/{id}/registration-schema/`
  - [ ] Match details → `/api/v1/matches/{id}/`
  - [ ] Group standings → `/api/v1/tournaments/{id}/groups/{group_id}/standings/`
  - [ ] Bracket data → `/api/v1/tournaments/{id}/bracket/`
  - [ ] Results inbox → `/api/v1/organizer/tournaments/{id}/results-inbox/`
  - [ ] Registration management → `/api/v1/organizer/tournaments/{id}/registrations/`
- [ ] Implement AJAX calls:
  - [ ] Real-time field validation (Riot ID, team name)
  - [ ] Auto-save registration draft (every 30 seconds)
  - [ ] Result submission
  - [ ] Dispute submission
  - [ ] Organizer actions (approve, reject, override)
- [ ] Implement error handling:
  - [ ] Network errors (display error banner)
  - [ ] Validation errors (highlight fields)
  - [ ] Server errors (show friendly message)
- [ ] Implement loading states:
  - [ ] Skeleton loaders for tables/cards
  - [ ] Spinners for buttons during submission
  - [ ] Progress bars for file uploads

---

### 9.8 Phase 8: Polish & Optimization
- [ ] Responsive design testing:
  - [ ] Desktop (1920px, 1440px, 1024px)
  - [ ] Tablet (768px)
  - [ ] Mobile (375px, 414px)
  - [ ] Test all pages and components
- [ ] Browser compatibility testing:
  - [ ] Chrome, Firefox, Safari, Edge
  - [ ] Mobile browsers (iOS Safari, Android Chrome)
- [ ] Accessibility audit:
  - [ ] Keyboard navigation (Tab, Enter, Escape)
  - [ ] Screen reader compatibility
  - [ ] Color contrast (WCAG AA standards)
  - [ ] Focus indicators visible
- [ ] Performance optimization:
  - [ ] Lazy load images
  - [ ] Minimize CSS/JS bundle size
  - [ ] Debounce search/filter inputs
  - [ ] Optimize bracket rendering (SVG or Canvas)
- [ ] Add animations:
  - [ ] Page transitions (fade in/out)
  - [ ] Modal open/close (slide up)
  - [ ] Hover effects (lift cards)
  - [ ] Loading spinners
  - [ ] Live match pulsing indicator
- [ ] Cross-browser polyfills (if needed for older browsers)

---

### 9.9 Phase 9: Testing & QA
- [ ] Manual testing:
  - [ ] Registration flow (all paths: solo, team captain, team member)
  - [ ] Match result submission (submit, confirm, dispute)
  - [ ] Organizer workflows (review registrations, resolve disputes, edit bracket)
  - [ ] Edge cases (empty states, max capacity, expired timers)
- [ ] User acceptance testing:
  - [ ] Test with real users (players, organizers)
  - [ ] Collect feedback on UX
  - [ ] Iterate on pain points
- [ ] Bug tracking:
  - [ ] Document issues in issue tracker
  - [ ] Prioritize critical bugs (broken functionality)
  - [ ] Fix and retest

---

### 9.10 Phase 10: Documentation & Handoff
- [ ] Create component documentation:
  - [ ] Props/parameters for each component
  - [ ] Usage examples
  - [ ] Code snippets
- [ ] Document API endpoints used:
  - [ ] Request/response formats
  - [ ] Error codes
- [ ] Create style guide:
  - [ ] Color palette
  - [ ] Typography
  - [ ] Spacing system
  - [ ] Component variants
- [ ] Handoff to backend team:
  - [ ] List of required JSON endpoints
  - [ ] Expected data formats
  - [ ] Error handling requirements

---

**End of Part 5: Frontend Developer Support & UI Specification**

**Document Summary**:
- **Section 1**: Frontend Architecture Overview
- **Section 2**: Screen Inventory (16 screens: 8 player, 8 organizer)
- **Section 3**: Component Library Blueprint (20+ components)
- **Section 4**: Data Contracts & JSON Examples (7 data structures)
- **Section 5**: Key User Flows (3 detailed workflows)
- **Section 6**: Bracket & Groups UI Guidelines
- **Section 7**: Organizer Console UX & Guidance System
- **Section 8**: Help & Tutorial Surfaces
- **Section 9**: Frontend Developer Checklist (10 phases, 150+ tasks)

**Total**: ~3,500 lines of comprehensive frontend specification for DeltaCrown tournament platform.

This document enables frontend developers to build the complete UI without backend clarification.
