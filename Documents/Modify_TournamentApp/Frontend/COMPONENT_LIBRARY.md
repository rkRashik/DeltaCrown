# DeltaCrown Component Library

**Epic:** Phase 9, Epic 9.3 - UI/UX Framework & Design Tokens  
**Date:** December 10, 2025  
**Purpose:** Comprehensive component specifications for frontend developers building DeltaCrown UI

**Related Files**:
- `Documents/Modify_TournamentApp/Frontend/design-tokens.json` - Design token definitions
- `Documents/Modify_TournamentApp/Frontend/tailwind.config.js` - Tailwind CSS configuration
- `FRONTEND_DEVELOPER_SUPPORT_PART_5.md` - Complete UI specification

---

## 1. Layout Components

### 1.1 PageShell
**Purpose:** Consistent layout structure for all pages

**Props:**
- `page_title` (string, required) - Browser tab title
- `user` (object, optional) - Current user data
- `notifications_count` (integer, default: 0) - Unread notifications
- `breadcrumbs` (array, optional) - Navigation trail

**Structure:**
```
┌─────────────────────────────────────┐
│ Navbar                              │
├─────────────────────────────────────┤
│ Breadcrumbs (if provided)          │
├─────────────────────────────────────┤
│ Main Content (slot)                 │
├─────────────────────────────────────┤
│ Footer                              │
└─────────────────────────────────────┘
```

**States:**
- Authenticated: Show user menu, notification bell
- Unauthenticated: Show Login/Sign Up buttons
- Mobile: Hamburger menu

**Accessibility:**
- Semantic HTML: `<header>`, `<main>`, `<footer>`
- Skip to main content link
- ARIA landmarks

---

### 1.2 Navbar
**Purpose:** Primary navigation for player-facing pages

**Props:**
- `user` (object, optional) - Current user
- `active_page` (string) - Current page identifier

**Navigation Items:**
- Home
- Tournaments
- Leaderboards
- My Tournaments (authenticated only)
- Profile/Settings (authenticated only)

**States:**
- Desktop: Horizontal layout
- Tablet: Collapsed some items
- Mobile: Hamburger → slide-out drawer

**Accessibility:**
- `role="navigation"`
- ARIA current page indicator
- Keyboard navigation (Tab, Enter)
- Focus visible indicators

---

### 1.3 OrganizerSidebar
**Purpose:** Navigation for organizer console

**Props:**
- `tournament` (object, required) - Current tournament
- `active_section` (string) - Current section
- `pending_counts` (object) - Badge counts

**Sections:**
- Dashboard
- Registrations (with badge)
- Bracket & Groups
- Matches
- Results Inbox (with badge)
- Disputes (with badge)
- Payouts
- Settings

**States:**
- Desktop: Persistent sidebar (240px width)
- Mobile: Collapsible drawer

**Accessibility:**
- `<nav>` with aria-label="Tournament navigation"
- Active section highlighted
- Badge counts announced by screen readers

---

### 1.4 Card
**Purpose:** Reusable content container

**Props:**
- `title` (string, optional) - Card header
- `has_footer` (boolean, default: false)
- `padding` (enum: sm|md|lg, default: md)
- `variant` (enum: default|flat|bordered|hoverable, default: default)

**CSS Classes (Tailwind):**
```
Default: bg-white shadow rounded-lg
Flat: bg-white rounded-lg
Bordered: bg-white border border-neutral-200 rounded-lg
Hoverable: ... hover:shadow-lg transition-shadow
```

**Structure:**
```html
<div class="card">
  <div class="card-header">{{ title }}</div>
  <div class="card-body">{{ slot }}</div>
  <div class="card-footer">{{ footer_slot }}</div>
</div>
```

**Accessibility:**
- Use `<article>` for standalone cards
- Heading hierarchy maintained

---

### 1.5 Modal
**Purpose:** Dialog overlay for confirmations, forms, details

**Props:**
- `title` (string, required)
- `size` (enum: sm|md|lg|xl|full, default: md)
- `closable` (boolean, default: true)
- `close_on_backdrop` (boolean, default: true)

**Sizes:**
- sm: 400px max-width
- md: 600px max-width
- lg: 800px max-width
- xl: 1000px max-width
- full: 90vw max-width

**States:**
- Open: Visible with backdrop (z-index: 1050)
- Closed: Hidden (display: none)
- Loading: Buttons disabled, spinner shown

**Keyboard Navigation:**
- Escape: Close modal (if closable)
- Tab: Focus trap within modal
- Enter on buttons: Submit/close

**Accessibility:**
- `role="dialog"` `aria-modal="true"`
- `aria-labelledby` pointing to title
- Focus management (trap and restore)
- Screen reader announcements

---

## 2. Form Components

### 2.1 TextInput
**Purpose:** Single-line text input field

**Props:**
- `name` (string, required)
- `label` (string, required)
- `value` (string, default: "")
- `placeholder` (string, optional)
- `help_text` (string, optional)
- `error` (string, optional) - Validation error
- `required` (boolean, default: false)
- `disabled` (boolean, default: false)
- `locked` (boolean, default: false) - Auto-filled, uneditable
- `type` (enum: text|email|tel|url, default: text)
- `maxlength` (integer, optional)

**States:**
- Default: Neutral border
- Focus: Brand primary border, ring
- Error: Error border, error icon
- Disabled: Gray background, cursor not-allowed
- Locked: Gray background, lock icon, tooltip explaining source

**Visual Indicators:**
- Required: Red asterisk after label
- Locked: Lock icon, "Auto-filled from profile" badge
- Character count: Show when nearing maxlength

**Accessibility:**
- `<label>` associated via `for` attribute
- `aria-describedby` for help text/errors
- `aria-invalid="true"` when error
- `aria-required="true"` if required

---

### 2.2 Select
**Purpose:** Dropdown selection field

**Props:**
- `name` (string, required)
- `label` (string, required)
- `options` (array, required) - [{ value, label }, ...]
- `value` (string, default: "")
- `placeholder` (string, default: "Select...")
- `error` (string, optional)
- `required` (boolean, default: false)
- `searchable` (boolean, default: false) - Enable search filtering
- `multiple` (boolean, default: false)

**Enhanced Searchable Select:**
- Input field to filter options
- Keyboard navigation (Up/Down arrows)
- Highlight matching text
- Clear button

**Accessibility:**
- `role="combobox"` for searchable
- `aria-expanded` state
- `aria-activedescendant` for highlighted option

---

### 2.3 Checkbox
**Purpose:** Boolean selection

**Props:**
- `name` (string, required)
- `label` (string, required)
- `checked` (boolean, default: false)
- `disabled` (boolean, default: false)
- `indeterminate` (boolean, default: false) - Partial selection

**States:**
- Unchecked: Empty box
- Checked: Box with checkmark
- Indeterminate: Box with dash (for "select all" scenarios)

**Accessibility:**
- Native `<input type="checkbox">`
- `aria-checked` for indeterminate state

---

### 2.4 FileUpload
**Purpose:** File selection with preview

**Props:**
- `name` (string, required)
- `label` (string, required)
- `accept` (string, optional) - MIME types (e.g., "image/*")
- `max_size` (integer, optional) - Max size in MB
- `multiple` (boolean, default: false)
- `required` (boolean, default: false)
- `preview` (boolean, default: true) - Show image previews

**States:**
- Empty: Dashed border, upload icon, "Drop files or click"
- Uploading: Progress bar
- Success: Preview thumbnail, filename, size, remove button
- Error: Error message (file too large, wrong type)

**Drag & Drop:**
- Highlight border on dragover
- Accept drop events
- Visual feedback

**Accessibility:**
- Hidden `<input type="file">` with visible `<label>`
- Keyboard accessible (Enter/Space to trigger)
- File list announced to screen readers

---

### 2.5 GameIdentityField
**Purpose:** Game-specific identity field with validation

**Props:**
- `game_slug` (string, required)
- `field_config` (object, required) - From GamePlayerIdentityConfig
- `value` (string, default: "")
- `error` (string, optional)
- `verified` (boolean, default: false)

**Features:**
- Real-time format validation (regex from config)
- AJAX verification against game API
- Locked state after verification
- Format hints (e.g., "name#tag for Riot ID")

**States:**
- Unverified: Normal input
- Verifying: Spinner icon
- Verified: Green checkmark, locked
- Failed: Red X, error message

**Example (Riot ID):**
```
Label: Riot ID
Placeholder: GameName#NA1
Help: Enter your Riot ID (e.g., Player#NA1)
Regex: ^[^#]+#[A-Z0-9]+$
```

**Accessibility:**
- Live region for verification status
- `aria-busy="true"` during verification

---

### 2.6 TeamRosterEditor
**Purpose:** Add/remove team members for team tournaments

**Props:**
- `max_members` (integer, required)
- `min_members` (integer, default: 1)
- `members` (array, default: []) - Current members
- `available_users` (array) - Searchable user list

**Features:**
- Add member button (opens user search modal)
- Remove member button (with confirmation)
- Drag to reorder (optional)
- Validation: min/max members enforced

**Structure:**
```
┌────────────────────────────┐
│ Team Roster (2/5 members)  │
├────────────────────────────┤
│ [Avatar] Player1 [Remove]  │
│ [Avatar] Player2 [Remove]  │
│ [+ Add Member]             │
└────────────────────────────┘
```

**Accessibility:**
- List with `role="list"`
- Remove buttons with `aria-label="Remove {username}"`
- Add button announces current count

---

## 3. Display Components

### 3.1 Badge
**Purpose:** Status indicator or label

**Props:**
- `text` (string, required)
- `variant` (enum: default|success|warning|error|info|tournament|match, required)
- `size` (enum: sm|md|lg, default: md)
- `icon` (string, optional) - Icon name

**Variants (mapped to design tokens):**
- success: Green background
- warning: Yellow background
- error: Red background
- info: Blue background
- tournament.{status}: Use tournament color
- match.{status}: Use match color

**CSS (Tailwind):**
```
bg-{variant}-100 text-{variant}-800 px-2 py-1 rounded text-sm
```

**Accessibility:**
- Color not sole indicator (include icon/text)
- `aria-label` for screen readers if icon-only

---

### 3.2 Button
**Purpose:** Clickable action trigger

**Props:**
- `text` (string, required)
- `variant` (enum: primary|secondary|danger|success|ghost, default: primary)
- `size` (enum: sm|md|lg, default: md)
- `icon` (string, optional) - Icon name
- `icon_position` (enum: left|right, default: left)
- `disabled` (boolean, default: false)
- `loading` (boolean, default: false)
- `type` (enum: button|submit|reset, default: button)

**Variants:**
- primary: Brand primary background, white text
- secondary: Neutral background, dark text
- danger: Error background, white text
- success: Success background, white text
- ghost: Transparent, border only

**States:**
- Default: Solid color
- Hover: Darken 10%
- Active: Darken 20%, scale 98%
- Disabled: Opacity 50%, cursor not-allowed
- Loading: Spinner icon, text "Loading..."

**Accessibility:**
- `aria-disabled="true"` when disabled
- `aria-busy="true"` when loading
- Focus visible ring

---

### 3.3 ProgressBar
**Purpose:** Visual progress indicator

**Props:**
- `value` (integer, required) - Current value (0-100)
- `max` (integer, default: 100)
- `size` (enum: sm|md|lg, default: md)
- `variant` (enum: primary|success|warning|error, default: primary)
- `show_label` (boolean, default: true) - Show percentage

**Structure:**
```
[=============>        ] 65%
```

**Accessibility:**
- `role="progressbar"`
- `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- `aria-label` describing purpose

---

### 3.4 Tooltip
**Purpose:** Contextual help on hover

**Props:**
- `text` (string, required) - Tooltip content
- `position` (enum: top|right|bottom|left, default: top)
- `trigger` (enum: hover|click, default: hover)
- `max_width` (integer, default: 250) - Max width in px

**Behavior:**
- Hover: Show after 300ms delay
- Click: Toggle on click, dismiss on outside click
- Keyboard: Show on focus (Tab to element)
- Auto-dismiss: After 10 seconds (for click-triggered)

**Accessibility:**
- `role="tooltip"`
- `aria-describedby` on trigger element
- Escape key dismisses

---

### 3.5 Toast
**Purpose:** Temporary notification message

**Props:**
- `message` (string, required)
- `variant` (enum: success|warning|error|info, default: info)
- `duration` (integer, default: 5000) - Auto-dismiss in ms
- `closable` (boolean, default: true)

**Position:** Top-right corner, stacked

**States:**
- Slide in from right
- Auto-dismiss after duration
- Slide out on close

**Accessibility:**
- `role="status"` for info/success
- `role="alert"` for warning/error
- Live region announces message

---

## 4. Tournament Components

### 4.1 TournamentCard
**Purpose:** Tournament listing card

**Props:**
- `tournament` (object, required) - TournamentSummary from TS SDK
- `show_actions` (boolean, default: true)

**Displays:**
- Game icon
- Tournament name
- Format badge (Single Elim, Round Robin, etc.)
- Status badge (Registration Open, Live, etc.)
- Dates (start - end)
- Participants (current / max)
- Entry fee (if applicable)
- Prize pool (if applicable)
- Register button (conditional)

**States:**
- Hoverable: Lift on hover
- Clickable: Navigate to tournament detail
- Status-dependent CTA:
  - Registration Open: "Register Now" button
  - Live: "View Bracket" button
  - Completed: "View Results" link

**Accessibility:**
- Card is `<article>`
- Heading is tournament name
- CTA button accessible

---

### 4.2 MatchCard
**Purpose:** Match information display

**Props:**
- `match` (object, required) - MatchSummary from TS SDK
- `variant` (enum: basic|expanded, default: basic)
- `show_actions` (boolean, default: false)

**Basic Variant:**
```
┌────────────────────────────┐
│ Round 1 - Match 3          │
│ [Player1] vs [Player2]     │
│ Status: Live               │
│ Time: Dec 10, 2PM          │
└────────────────────────────┘
```

**Expanded Variant:**
- + Score display
- + Result submission status
- + Dispute indicator
- + Action buttons (Submit Result, Confirm, Dispute)

**States:**
- scheduled: Gray border
- live: Red border, pulsing indicator
- awaiting_results: Yellow border
- completed: Green border

**Accessibility:**
- Status announced via `aria-live="polite"`
- Action buttons clearly labeled

---

### 4.3 BracketVisualizer
**Purpose:** Interactive tournament bracket display

**Props:**
- `tournament_id` (integer, required)
- `format` (enum: single_elim|double_elim, required)
- `matches` (array, required) - Match data
- `interactive` (boolean, default: true) - Click to view match details

**Structure (Single Elimination):**
```
Round 1    Quarter    Semi      Final
M1 ─┐
    ├─ M5 ─┐
M2 ─┘      │
           ├─ M7 ─┐
M3 ─┐      │      │
    ├─ M6 ─┘      ├─ M8 (Winner)
M4 ─┘             │
                  │
```

**Features:**
- Horizontal scrollable
- Zoom in/out controls
- Match popover on hover (participants, time, score)
- Click match → navigate to match detail
- Highlight user's matches

**Responsive:**
- Desktop: Horizontal layout
- Mobile: Vertical/stacked rounds

**Accessibility:**
- Alternative table view for screen readers
- Keyboard navigation (Tab through matches)
- ARIA labels for match relationships

---

### 4.4 StandingsTable
**Purpose:** Group stage or tournament standings

**Props:**
- `standings` (array, required) - Participant standings
- `columns` (array, optional) - Column configuration
- `highlight_advancement` (boolean, default: true)

**Columns:**
- Rank
- Participant (name, avatar)
- Played (matches played)
- Won
- Lost
- Win Rate
- Points
- Tiebreaker info (tooltip)

**Features:**
- Sortable columns
- Highlight advancement zones (green background)
- Tiebreaker tooltips
- Responsive (collapse columns on mobile)

**Mobile View:**
- Card layout instead of table
- Show top 3 stats only

**Accessibility:**
- `<table>` with proper headers
- `scope` attributes
- Sortable columns announced

---

## 5. Organizer Components

### 5.1 ResultsInboxTable
**Purpose:** Organizer's pending results review table

**Props:**
- `items` (array, required) - OrganizerReviewItem[] from TS SDK
- `on_action` (function) - Callback for bulk actions

**Columns:**
- Checkbox (for bulk selection)
- Match ID
- Tournament
- Participants
- Submission Status
- Dispute Status
- Submitted At
- Auto-confirm Deadline (countdown)
- Priority badge
- Actions (View, Finalize, Reject)

**Features:**
- Bulk select (select all checkbox)
- Bulk actions toolbar (Finalize Selected, Reject Selected)
- Sort by priority, age, deadline
- Filter by tournament, status
- Pagination

**Accessibility:**
- Table with `<thead>`, `<tbody>`
- Checkbox group with `role="group"`
- Bulk action buttons announced

---

### 5.2 SchedulingCalendar
**Purpose:** Match scheduling interface

**Props:**
- `tournament_id` (integer, required)
- `matches` (array, required) - MatchSchedulingItem[] from TS SDK
- `slots` (array, required) - SchedulingSlot[] from TS SDK

**Features:**
- Calendar grid (days × time slots)
- Drag & drop matches to slots
- Conflict detection (red border if conflict)
- Auto-schedule button (AI suggestion)
- Manual time picker modal

**Visual:**
```
         Mon 10th    Tue 11th    Wed 12th
10:00 AM [ M1    ]  [ M3    ]  [       ]
11:00 AM [ M2    ]  [       ]  [ M4    ]
12:00 PM [       ]  [       ]  [       ]
```

**Accessibility:**
- Keyboard drag (Space to grab, Arrows to move, Enter to drop)
- Screen reader announces slot details

---

### 5.3 DisputeReviewPanel
**Purpose:** Organizer's dispute review interface

**Props:**
- `dispute` (object, required) - DisputeSummary from TS SDK
- `match` (object, required) - MatchWithResult from TS SDK

**Sections:**
1. Original Submission (submitter, score, proof)
2. Opponent Confirmation Status
3. Dispute Details (filed by, reason, evidence)
4. Organizer Actions (Accept Original, Overturn, Split Decision, Dismiss)

**Features:**
- Side-by-side proof comparison
- Comment thread (organizer notes)
- Resolution form (verdict + explanation)
- Escalation button (to senior staff)

**Accessibility:**
- Clear headings for each section
- Form validation
- Confirmation modal before finalizing

---

## 6. Data Display Components

### 6.1 DataTable
**Purpose:** Generic sortable, filterable data table

**Props:**
- `columns` (array, required) - Column config
- `data` (array, required) - Row data
- `sortable` (boolean, default: true)
- `filterable` (boolean, default: false)
- `paginated` (boolean, default: true)
- `page_size` (integer, default: 20)

**Column Config:**
```javascript
{
  key: 'name',
  label: 'Player Name',
  sortable: true,
  width: '200px',
  render: (value, row) => `<a href="#">${value}</a>`
}
```

**Features:**
- Click header to sort
- Filter row (if filterable)
- Pagination controls
- Empty state ("No data")
- Loading skeleton

**Accessibility:**
- `<table>` with headers
- `aria-sort` on sortable columns
- Pagination with `aria-label`

---

### 6.2 PaginationControls
**Purpose:** Pagination for lists/tables

**Props:**
- `current_page` (integer, required)
- `total_pages` (integer, required)
- `on_page_change` (function, required)
- `show_page_numbers` (boolean, default: true)
- `max_visible_pages` (integer, default: 5)

**Structure:**
```
[Previous] 1 2 ... 5 [6] 7 ... 10 [Next]
```

**Features:**
- First/Last page buttons
- Truncate middle pages (1 2 ... 5 6 7 ... 10)
- Disable Previous on page 1
- Disable Next on last page

**Accessibility:**
- `<nav>` with `aria-label="Pagination"`
- Current page `aria-current="page"`
- Page numbers with `aria-label`

---

### 6.3 EmptyState
**Purpose:** Display when no data available

**Props:**
- `icon` (string, optional) - Icon name
- `title` (string, required) - Empty state message
- `description` (string, optional) - Additional context
- `action` (object, optional) - CTA button config

**Example:**
```
┌────────────────────────┐
│    [Icon: Trophy]      │
│ No Tournaments Found   │
│ Try adjusting filters  │
│ [Browse All]           │
└────────────────────────┘
```

**Accessibility:**
- Use `<section>` with heading
- Icon is decorative (`aria-hidden="true"`)

---

### 6.4 LoadingSkeleton
**Purpose:** Placeholder while content loads

**Props:**
- `type` (enum: card|table|list|text, required)
- `count` (integer, default: 3) - Number of skeletons

**Visual:**
- Animated gradient (pulse effect)
- Match layout of actual content
- Gray background

**Accessibility:**
- `aria-busy="true"` on parent
- `aria-live="polite"` for loading completion

---

## 7. Usage Guidelines

### Component Composition

**Good Practice:**
```html
<PageShell page_title="Tournaments" user="{{ user }}">
  <Card title="Featured Tournaments">
    {% for tournament in tournaments %}
      <TournamentCard tournament="{{ tournament }}" />
    {% endfor %}
  </Card>
</PageShell>
```

**Bad Practice:**
```html
<!-- Don't nest cards inside cards -->
<Card>
  <Card>Content</Card>
</Card>

<!-- Don't override component styles directly -->
<Button style="background: red !important">Bad</Button>
```

### Responsive Patterns

**Mobile-First Approach:**
1. Design for mobile (320px width)
2. Add breakpoints for tablet (768px)
3. Enhance for desktop (1024px+)

**Touch Targets:**
- Minimum 44×44px for buttons/links
- Spacing between interactive elements

### Color Usage

**Status Colors:**
- Success: Green (`success-500`)
- Warning: Yellow (`warning-500`)
- Error: Red (`error-500`)
- Info: Blue (`info-500`)

**Never rely on color alone** - include icons or text.

### Typography Hierarchy

**Headings:**
- H1: Page title (`text-4xl font-bold`)
- H2: Section title (`text-3xl font-semibold`)
- H3: Subsection (`text-2xl font-medium`)
- H4: Component title (`text-xl font-medium`)

**Body:**
- Default: `text-base` (16px)
- Small: `text-sm` (14px)
- Large: `text-lg` (18px)

### Spacing System

**Consistent Spacing:**
- Component padding: `p-4` (1rem)
- Section margins: `mb-8` (2rem)
- Card gap: `gap-6` (1.5rem)

---

## 8. Testing Components

### Accessibility Checklist

For each component, verify:
- [ ] Keyboard navigable (Tab, Enter, Escape)
- [ ] Screen reader friendly (proper ARIA)
- [ ] Focus visible (ring outline)
- [ ] Color contrast ≥ 4.5:1 (WCAG AA)
- [ ] Touch targets ≥ 44×44px
- [ ] No color-only indicators
- [ ] Form labels associated
- [ ] Error messages announced

### Browser Testing

Test on:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Android)

### Responsive Testing

Breakpoints:
- Mobile: 320px - 639px
- Tablet: 640px - 1023px
- Desktop: 1024px+

---

**Total Components Documented:** 35+  
**Categories:** Layout (5), Forms (6), Display (5), Tournament (4), Organizer (3), Data (4), Misc (8+)

**End of Component Library**
