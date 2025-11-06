# PART 4.3: TOURNAMENT MANAGEMENT SCREENS

**Navigation:**
- [← Previous: PART_4.2 - UI Components & Navigation](PART_4.2_UI_COMPONENTS_NAVIGATION.md)
- [→ Next: PART_4.4 - Registration & Payment Flow](PART_4.4_REGISTRATION_PAYMENT_FLOW.md)
- [↑ Back to Index](INDEX_MASTER_NAVIGATION.md)

---

.pagination-link-active {
    color: var(--text-primary);
    background: var(--brand-primary);
    border-color: var(--brand-primary);
}

.pagination-link-active:hover {
    background: #2563EB;
}

.pagination-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    pointer-events: none;
}

.pagination-ellipsis {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    height: 40px;
    color: var(--text-tertiary);
}
```

---

### 4.12 Tooltip / Popover

```html
<!-- Tooltip -->
<button class="btn btn-ghost" data-tooltip="Delete tournament">
    <svg class="icon-base"><!-- Trash icon --></svg>
</button>

<!-- Tooltip implementation -->
<div class="tooltip" role="tooltip" hidden>
    Delete tournament
</div>
```

```css
[data-tooltip] {
    position: relative;
}

[data-tooltip]::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: calc(100% + var(--space-2));
    left: 50%;
    transform: translateX(-50%);
    padding: var(--space-2) var(--space-3);
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: var(--text-sm);
    white-space: nowrap;
    border-radius: var(--radius-base);
    border: 1px solid var(--border-primary);
    box-shadow: var(--shadow-lg);
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--duration-fast);
    z-index: 1000;
}

[data-tooltip]::before {
    content: '';
    position: absolute;
    bottom: calc(100% + var(--space-2) - 6px);
    left: 50%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-top-color: var(--border-primary);
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--duration-fast);
    z-index: 1001;
}

[data-tooltip]:hover::after,
[data-tooltip]:hover::before {
    opacity: 1;
}
```

---

### 4.13 Empty States

```html
<div class="empty-state">
    <div class="empty-state-icon">
        <svg class="icon-xl"><!-- Trophy icon --></svg>
    </div>
    <h3 class="empty-state-title">No tournaments found</h3>
    <p class="empty-state-message">
        There are no active tournaments matching your filters. Try adjusting your search criteria.
    </p>
    <button class="btn btn-primary">
        Create Tournament
    </button>
</div>
```

```css
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-16);
    text-align: center;
}

.empty-state-icon {
    width: 80px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: 50%;
    color: var(--text-tertiary);
    margin-bottom: var(--space-6);
}

.empty-state-title {
    font-size: var(--text-2xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin-bottom: var(--space-3);
}

.empty-state-message {
    font-size: var(--text-base);
    color: var(--text-secondary);
    max-width: 400px;
    margin-bottom: var(--space-6);
}
```

---

### 4.14 Error & Edge States (Comprehensive Templates)

**Purpose:** Explicit designs for failure scenarios, preventing user confusion.

**1. No Internet Connection / Offline**

```html
<div class="error-state error-state-offline">
    <div class="error-icon">
        <svg class="icon-xl"><!-- WiFi off icon --></svg>
    </div>
    <h3 class="error-title">No Internet Connection</h3>
    <p class="error-message">
        You're currently offline. Some features may not be available.
    </p>
    <div class="error-actions">
        <button class="btn btn-primary" onclick="location.reload()">
            Retry Connection
        </button>
    </div>
    <div class="error-info">
        <p class="text-sm text-secondary">
            Your actions will be saved and synced when connection is restored.
        </p>
    </div>
</div>
```

**HTMX Offline Handling:**
```javascript
// Queue actions when offline
document.body.addEventListener('htmx:sendError', (event) => {
    if (!navigator.onLine) {
        // Queue request for retry
        queueOfflineAction(event.detail);
        showToast('Action queued. Will sync when online.', 'info');
    }
});
```

**2. Server Error (500, Bracket Load Failure)**

```html
<div class="error-state error-state-server">
    <div class="error-icon error-icon-danger">
        <svg class="icon-xl"><!-- Alert triangle icon --></svg>
    </div>
    <h3 class="error-title">Unable to Load Bracket</h3>
    <p class="error-message">
        We're experiencing technical difficulties. Please try again in a moment.
    </p>
    <div class="error-actions">
        <button class="btn btn-primary" onclick="location.reload()">
            <svg class="icon-sm"><!-- Refresh icon --></svg>
            Retry
        </button>
        <button class="btn btn-secondary" onclick="contactSupport()">
            Contact Support
        </button>
    </div>
    <details class="error-details">
        <summary>Technical Details</summary>
        <code>Error ID: ERR-500-ABC123<br>Timestamp: 2025-11-03 10:30:45 BST</code>
    </details>
</div>
```

**3. Payment File Validation Errors**

```html
<!-- File Too Large -->
<div class="alert alert-error">
    <svg class="alert-icon"><!-- X circle icon --></svg>
    <div class="alert-content">
        <p class="alert-title">File Too Large</p>
        <p class="alert-message">
            Your file (7.2 MB) exceeds the maximum size of 5 MB.
            <a href="/help/compress-images" class="alert-link">Learn how to compress images</a>
        </p>
    </div>
    <button class="btn btn-sm btn-ghost">
        Choose Different File
    </button>
</div>

<!-- Invalid File Format -->
<div class="alert alert-error">
    <svg class="alert-icon"><!-- X circle icon --></svg>
    <div class="alert-content">
        <p class="alert-title">Invalid File Format</p>
        <p class="alert-message">
            File type ".txt" is not supported. Please upload JPG, PNG, or PDF.
            <a href="/examples/payment-screenshot" class="alert-link">View example screenshot</a>
        </p>
    </div>
</div>

<!-- Corrupted File -->
<div class="alert alert-error">
    <svg class="alert-icon"><!-- X circle icon --></svg>
    <div class="alert-content">
        <p class="alert-title">Unable to Read File</p>
        <p class="alert-message">
            The file appears to be corrupted or damaged. Please try uploading a different file.
        </p>
    </div>
    <button class="btn btn-sm btn-ghost">
        Try Again
    </button>
</div>
```

**Sample Screenshot Preview Link:**
- Opens modal with annotated example
- Shows required elements: Transaction ID, Amount, Date/Time
- Highlights acceptable and unacceptable screenshots

**4. Zero States (No Data Yet)**

```html
<!-- No Tournaments Created Yet (Organizer Dashboard) -->
<div class="empty-state">
    <div class="empty-state-icon">
        <svg class="icon-xl"><!-- Sparkles icon --></svg>
    </div>
    <h3 class="empty-state-title">Create Your First Tournament</h3>
    <p class="empty-state-message">
        You haven't created any tournaments yet. Get started by creating your first tournament and inviting players!
    </p>
    <button class="btn btn-primary btn-lg">
        <svg class="icon-sm"><!-- Plus icon --></svg>
        Create Tournament
    </button>
</div>

<!-- No Matches Yet (Live Matches Section) -->
<div class="empty-state">
    <div class="empty-state-icon">
        <svg class="icon-xl"><!-- Clock icon --></svg>
    </div>
    <h3 class="empty-state-title">No Live Matches</h3>
    <p class="empty-state-message">
        There are no matches in progress right now. Check back when the tournament starts!
    </p>
</div>

<!-- No Certificates Yet (Player Dashboard) -->
<div class="empty-state">
    <div class="empty-state-icon">
        <svg class="icon-xl"><!-- Award icon --></svg>
    </div>
    <h3 class="empty-state-title">No Certificates Yet</h3>
    <p class="empty-state-message">
        Earn certificates by participating in tournaments and achieving top placements!
    </p>
    <button class="btn btn-secondary">
        Browse Tournaments
    </button>
</div>
```

**5. Permission Denied (Access Control)**

```html
<div class="error-state error-state-forbidden">
    <div class="error-icon error-icon-warning">
        <svg class="icon-xl"><!-- Lock icon --></svg>
    </div>
    <h3 class="error-title">Access Restricted</h3>
    <p class="error-message">
        You don't have permission to view this page. This tournament may be private or you may need to log in.
    </p>
    <div class="error-actions">
        <button class="btn btn-primary" onclick="window.location='/login'">
            Sign In
        </button>
        <button class="btn btn-ghost" onclick="history.back()">
            Go Back
        </button>
    </div>
</div>
```

**Error State Styles:**

```css
.error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-16);
    text-align: center;
    min-height: 400px;
}

.error-icon {
    width: 80px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: 50%;
    color: var(--text-tertiary);
    margin-bottom: var(--space-6);
}

.error-icon-danger {
    background: rgba(239, 68, 68, 0.1);
    color: var(--error);
}

.error-icon-warning {
    background: rgba(245, 158, 11, 0.1);
    color: var(--warning);
}

.error-title {
    font-size: var(--text-2xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin-bottom: var(--space-3);
}

.error-message {
    font-size: var(--text-base);
    color: var(--text-secondary);
    max-width: 400px;
    margin-bottom: var(--space-6);
}

.error-actions {
    display: flex;
    gap: var(--space-3);
    margin-bottom: var(--space-6);
}

.error-info {
    padding: var(--space-4);
    background: var(--bg-tertiary);
    border-radius: var(--radius-lg);
    max-width: 400px;
}

.error-details {
    margin-top: var(--space-4);
    padding: var(--space-4);
    background: var(--bg-tertiary);
    border-radius: var(--radius-base);
    text-align: left;
}

.error-details summary {
    cursor: pointer;
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin-bottom: var(--space-2);
}

.error-details code {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-tertiary);
}
```

---

## Component Library Summary

✅ **20+ Components Documented:**

1. **Buttons** - Primary, secondary, ghost, danger, loading, sizes
2. **Cards** - Tournament card, match card with live states
3. **Form Elements** - Input, select, checkbox, radio, textarea with validation states
4. **Badges & Tags** - Game badges, status badges, live indicators, counters
5. **Modal / Dialog** - Overlay, header, body, footer with animations
6. **Navigation** - Navbar, breadcrumbs
7. **Tabs** - Tab navigation with ARIA support
8. **Loading States** - Spinner, skeleton loader, progress bar
9. **Toast Notifications** - Success, error, warning, info with animations
10. **Alert / Banner** - Inline alerts with variants
11. **Dropdown Menu** - Context menus with dividers
12. **Pagination** - Page navigation with ellipsis
13. **Tooltip / Popover** - Hover hints with positioning
14. **Empty States** - No data placeholders

**Each component includes:**
- HTML structure with semantic markup
- Complete CSS with custom properties
- Accessibility features (ARIA labels, keyboard support)
- Responsive behavior
- Hover/focus states
- Animation specifications

---

## 5. Tournament Management Screens

### 5.1 Tournament Listing Page

**Purpose:** Browse and discover active, upcoming, and past tournaments with filtering and search capabilities.

**URL:** `/tournaments`

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Hero Section                                            │
│  - Heading: "Discover Tournaments"                      │
│  - Search bar (prominent)                               │
│  - Quick filter chips (Live, Upcoming, Popular)         │
├────────────────────────────────────────────────────────┤
│ Filters (Sidebar)      │ Tournament Grid                │
│  - Game                │  ┌─────┐ ┌─────┐ ┌─────┐      │
│  - Date Range          │  │ Card│ │ Card│ │ Card│      │
│  - Prize Pool          │  └─────┘ └─────┘ └─────┘      │
│  - Status              │  ┌─────┐ ┌─────┐ ┌─────┐      │
│  - Entry Fee           │  │ Card│ │ Card│ │ Card│      │
│  - Format              │  └─────┘ └─────┘ └─────┘      │
│                        │  [Load More]                   │
└────────────────────────────────────────────────────────┘
```

**Key Features:**

1. **Hero Search Section**
   - Large search input with autocomplete
   - Voice search icon (future enhancement)
   - Quick filter chips: "Live Now" (with pulsing red dot), "Starting Soon", "High Prize Pool"
   - Trending games carousel

2. **Sidebar Filters**
   - **Game Selection:** Checkboxes with game icons (VALORANT, eFootball, PUBG Mobile, etc.)
   - **Date Range:** Calendar picker with presets (Today, This Week, This Month)
   - **Prize Pool:** Range slider (৳0 - ৳100,000+)
   - **Status:** Radio buttons (All, Registration Open, Ongoing, Completed)
   - **Entry Fee:** Checkboxes (Free, ৳0-500, ৳500-1000, ৳1000+)
   - **Format:** Checkboxes (Single Elimination, Double Elimination, Round Robin)
   - **Reset Filters** button at bottom

3. **Tournament Grid**
   - 3-column grid on desktop (1 column mobile, 2 columns tablet)
   - Tournament cards with:
     - Banner image with live badge overlay
     - Game badge and date
     - Tournament title
     - Stats (teams, prize pool, registered count)
     - Progress bar showing registration status
     - Primary CTA: "Register Now" or "View Details"
   - Sort dropdown (top-right): "Relevance", "Start Date", "Prize Pool", "Participants"

4. **Empty State**
   - Trophy icon
   - "No tournaments found"
   - "Try adjusting your filters or create your own tournament"
   - "Create Tournament" button

**Responsive Behavior:**

- **Desktop (1024px+):** Sidebar + 3-column grid
- **Tablet (768px-1023px):** Collapsible sidebar + 2-column grid
- **Mobile (<768px):** Bottom sheet filters + 1-column grid

**Interactions:**

- Hover on card: Lift effect (4px translateY) + border glow
- Click "Register Now": Opens registration modal (if logged in) or redirects to login
- Click card anywhere else: Navigate to tournament detail page
- Scroll infinite: Auto-load more tournaments (with skeleton loaders)

**HTMX Integration:**

```html
<!-- Infinite scroll -->
<div 
    hx-get="/tournaments?page=2" 
    hx-trigger="revealed" 
    hx-swap="afterend"
    class="loading-trigger"
>
    <div class="spinner"></div>
</div>

<!-- Filter update -->
<form 
    hx-get="/tournaments/filter" 
    hx-trigger="change" 
    hx-target="#tournament-grid"
    hx-swap="innerHTML"
>
    <!-- Filter inputs -->
</form>
```

---

### 5.2 Tournament Detail Page

**Purpose:** Comprehensive view of a single tournament with all information, registration, and live updates.

**URL:** `/tournaments/<tournament-slug>`

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Hero Section (Full-width banner)                        │
│  - Background: Tournament banner image                  │
│  - Overlay gradient                                     │
│  - Game badge, Live badge (if applicable)               │
│  - Tournament title (H1)                                │
│  - Organizer info (avatar, name, verified badge)        │
│  - Primary CTA: "Register Now" (prominent)              │
├────────────────────────────────────────────────────────┤
│ Breadcrumbs: Home / Tournaments / [Tournament Name]     │
├────────────────────────────────────────────────────────┤
│ Stats Cards (4 columns, responsive)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ 32 Teams │ │ ৳50,000  │ │ Dec 15   │ │ 16/32    │  │
│  │ Capacity │ │ Prize    │ │ Start    │ │ Registered│  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├────────────────────────────────────────────────────────┤
│ Tabs Navigation                                         │
│  [Details] [Participants] [Bracket] [Rules] [Sponsors] │
├────────────────────────────────────────────────────────┤
│ Tab Content Area                                        │
│  (Details, Participants, Bracket, Rules, or Sponsors)   │
├────────────────────────────────────────────────────────┤
│ Sidebar (Desktop only)                                  │
│  - Quick Actions card                                   │
│  - Timeline card                                        │
│  - Sponsors card                                        │
│  - Share buttons                                        │
└────────────────────────────────────────────────────────┘
```

**Tab 1: Details**

Content:
- **Description** (rich text with markdown support)
- **Format Information:** Single Elimination, Best of 3
- **Entry Fee:** ৳500 (or "Free Entry" or "500 DC" if DeltaCoin enabled)
- **Prize Distribution:**
  ```
  🥇 1st Place: ৳25,000
  🥈 2nd Place: ৳15,000
  🥉 3rd Place: ৳10,000
  ```
- **Check-in Window:** 30 minutes before start
- **Custom Fields:** (if defined by organizer)
  - In-Game Username
  - Team Discord Server
  - etc.
- **Contact Organizer:** Button (prominent, always visible, opens message modal)

**Tab 2: Participants**

Content:
- Search/filter participants
- Grid of participant cards:
  - Team logo
  - Team name
  - **"✓ Verified Winner"** chip (if certificate issued for past tournaments)
  - Rank/seed (if applicable)
  - Registration date
  - Payment status (for organizer only)
  - Past placement badges (🥇, 🥈, 🥉 with count)
- Total count: "16 / 32 teams registered"
- Export list button (organizer only)

**Tab 3: Bracket**

Content:
- Interactive bracket visualization (SVG-based)
- Zoom/pan controls
- Match cards within bracket nodes
- Highlight user's team path
- Real-time updates (WebSocket)
- Download bracket image button

**Tab 4: Rules**

Content:
- Formatted rules text (markdown) — stored in `Tournament.rules_text` field
- Sections:
  - Eligibility
  - Match Rules
  - Conduct & Fair Play
  - Disputes
  - Anti-Cheat Requirements
- Accept rules checkbox (for registration)

**Field Name Convention:** UI displays "Rules" but API/database field is `rules_text` (consistent with Part 2 & 3)

**Tab 5: Sponsors**

Content:
- Sponsor logos with links
- Sponsor tier badges (Platinum, Gold, Silver, Bronze)
- Click to view sponsor profile

**Sidebar Cards:**

1. **Quick Actions**
   - Register button (primary)
   - Save tournament (bookmark icon)
   - Share (dropdown: Facebook, Twitter, Discord, Copy Link)
   - Report tournament (flag icon)
   - **Contact Organizer** (message icon, opens dialog)

2. **Timeline**
   - Registration Opens: Dec 1, 2025
   - Registration Closes: Dec 14, 2025
   - Check-in: Dec 15, 2025 (9:30 AM)
   - Tournament Start: Dec 15, 2025 (10:00 AM)
   - Visual progress indicator

3. **Organizer Card**
   - Avatar, name, verified badge
   - Rating: ⭐ 4.8 (120 reviews)
   - "View Profile" link
   - **"Contact Organizer"** button (primary action, opens message modal)

**Contact Organizer Modal:**
- Pre-filled subject: "Question about [Tournament Name]"
- Message textarea
- Send button (creates notification for organizer + optional email)
- Response time estimate: "Usually responds within 24 hours"

---

#### Contact Organizer Placement Hierarchy

**Purpose:** Ensure "Contact Organizer" button is accessible at every critical touchpoint where users may need support or clarification.

**Primary Placements (Always Visible):**

```
┌────────────────────────────────────────────────────────┐
│ 1. Tournament Detail Page - Organizer Card             │
│    Location: Right sidebar (desktop) / Bottom (mobile) │
│    Visual: Primary button with message icon            │
│    Priority: HIGH - Primary support channel             │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ 2. Tournament Header Bar                                │
│    Location: Top-right corner, next to Register button │
│    Visual: Ghost button with envelope icon 💬          │
│    Priority: MEDIUM - Quick access without scrolling    │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ 3. Registration Form Footer                             │
│    Location: Below form fields, before Submit button    │
│    Visual: Ghost button, left-aligned                   │
│    Text: "Need help? Contact Organizer"                │
│    Priority: HIGH - Registration assistance             │
└────────────────────────────────────────────────────────┘
```

**Contextual Placements (Conditional):**

```
┌────────────────────────────────────────────────────────┐
│ 4. Payment Rejection Notice                            │
│    Trigger: Payment status = "Rejected"                │
│    Visual: Primary button in error alert                │
│    Text: "Contact Organizer" (discuss rejection)       │
│    Pre-fill: Subject "Payment Rejection Inquiry"       │
│    Priority: CRITICAL - Dispute resolution              │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ 5. Payment Expiration Alert                            │
│    Trigger: Payment deadline passed, status "Expired"  │
│    Visual: Secondary button in warning alert            │
│    Text: "Request Extension"                           │
│    Pre-fill: Subject "Payment Extension Request"       │
│    Priority: HIGH - Time-sensitive resolution           │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ 6. Check-In Missed Alert                               │
│    Trigger: User missed check-in deadline              │
│    Visual: Secondary button in error state              │
│    Text: "Contact Organizer" (appeal disqualification) │
│    Pre-fill: Subject "Check-in Missed Appeal"          │
│    Priority: HIGH - Last chance to resolve              │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ 7. Match Dispute Panel                                 │
│    Trigger: User clicks "Dispute Result"               │
│    Visual: Ghost button below evidence upload          │
│    Text: "Escalate to Organizer"                       │
│    Pre-fill: Subject "Match Result Dispute - [Match]"  │
│    Priority: MEDIUM - Formal dispute process            │
└────────────────────────────────────────────────────────┘
```

**Visual Hierarchy Reference:**

```
Tournament Detail Page (Desktop):
┌────────────────────────────────────────────────────────┐
│ Header Bar: [💬 Contact Organizer]         [Register] │ ← Ghost button
├────────────────────────────────────────────────────────┤
│ Main Content        │ Sidebar                          │
│                     │ ┌─────────────────────────────┐  │
│                     │ │ Organizer Card              │  │
│                     │ │ 👤 JohnDoe                  │  │
│                     │ │ ⭐ 4.8 (120 reviews)        │  │
│                     │ │ [Contact Organizer] ←───────┼──┼ Primary button
│                     │ │ [View Profile]              │  │
│                     │ └─────────────────────────────┘  │
└────────────────────────────────────────────────────────┘

Registration Form:
┌────────────────────────────────────────────────────────┐
│ [Team Name Input]                                      │
│ [Player Fields...]                                     │
│ [Custom Fields...]                                     │
├────────────────────────────────────────────────────────┤
│ Footer Actions:                                        │
│ [Need help? Contact Organizer] ←────── [Submit Entry] │ ← Left-aligned ghost
└────────────────────────────────────────────────────────┘

Payment Rejected State:
┌────────────────────────────────────────────────────────┐
│ ❌ Payment Rejected                                    │
│ Reason: Invalid transaction ID format                  │
│ Please review and resubmit your payment proof.         │
│ [Resubmit Payment] [Contact Organizer] ←───────────────┼ Primary action
└────────────────────────────────────────────────────────┘
```

**Button Styling by Context:**

| Location | Style | Icon | Color | Size |
|----------|-------|------|-------|------|
| Organizer Card | `btn-primary` | 💬 | Blue | Large (full-width) |
| Header Bar | `btn-ghost` | 💬 | Gray | Medium |
| Form Footer | `btn-ghost` | None | Gray | Small |
| Error Alerts | `btn-primary` | None | Blue | Medium |
| Warning Alerts | `btn-secondary` | ⚠️ | Amber | Medium |

**Mobile Optimization:**

- **Tournament Page:** Fixed bottom bar (sticky)
  ```
  ┌────────────────────────────────────────┐
  │ [Contact Organizer] [Register Now]     │ ← 50/50 split
  └────────────────────────────────────────┘
  ```
- **Registration Form:** Inline with submit button (stacked on small screens)
- **Alerts:** Full-width buttons (stacked vertically)

**Analytics Tracking:**

```html
<!-- All Contact Organizer buttons use consistent ID pattern -->
<button data-analytics-id="dc-contact-organizer-{context}" 
        data-tournament-id="{{ tournament.id }}"
        data-context="header|sidebar|registration|payment_rejected|check_in_missed|dispute">
    Contact Organizer
</button>
```

**Context Values:**
- `header` - Header bar placement
- `sidebar` - Organizer card placement
- `registration` - Registration form footer
- `payment_rejected` - Payment rejection alert
- `payment_expired` - Payment expiration alert
- `check_in_missed` - Check-in failure alert
- `dispute` - Match dispute panel

**Live Updates (WebSocket):**

When tournament status changes:
- Registration count updates in real-time
- Live badge appears when tournament starts
- Match results update bracket immediately
- Toast notifications for important events

**Responsive Behavior:**

- **Desktop:** Sidebar visible, 8-column main + 4-column sidebar
- **Tablet/Mobile:** Sidebar content moved to bottom sections

**CTA States:**

- **Before Registration Opens:** "Notify Me" button
- **Registration Open:** "Register Now" (blue, glowing)
- **Registration Full:** "Waitlist" button
- **Registration Closed:** "Registration Closed" (gray, disabled)
- **User Registered:** "Registered ✓" (green) + "Manage Registration" button

---

### 5.3 Tournament Creation Wizard

**Purpose:** Multi-step form for organizers to create and publish tournaments.

**URL:** `/tournaments/create`

**Access:** Requires authentication + organizer permissions

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Progress Header                                         │
│  [1. Basic Info] → [2. Format] → [3. Rules] → [4. Preview]│
│  ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  25%          │
├────────────────────────────────────────────────────────┤
│ Form Area (centered, max-width 800px)                   │
│  ┌────────────────────────────────────────────────┐    │
│  │ Step Content                                    │    │
│  │ (Form fields for current step)                  │    │
│  │                                                 │    │
│  │                                                 │    │
│  │                                                 │    │
│  └────────────────────────────────────────────────┘    │
├────────────────────────────────────────────────────────┤
│ Footer Actions                                          │
│  [← Back]                    [Save Draft] [Next →]     │
└────────────────────────────────────────────────────────┘
```

**Step 1: Basic Information**

Fields:
- **Tournament Name*** (text input, 60 char max)
  - Real-time availability check
  - Slug preview: `/tournaments/deltacrown-valorant-cup-2025`
- **Game*** (dropdown with search)
  - VALORANT, eFootball, PUBG Mobile, Free Fire, MLBB, CS2, Dota 2, EA Sports FC
- **Banner Image*** (file upload)
  - Recommended: 1920x1080px
  - Drag-and-drop area
  - Image preview with crop tool
- **Description*** (rich text editor)
  - Markdown toolbar
  - Character count: 0/2000
  - Preview button
- **Start Date & Time*** (datetime picker)
  - Timezone: Bangladesh Standard Time (BST)
  - Minimum: 24 hours from now
- **Organizer Name** (auto-filled from profile, editable)
- **Contact Email*** (auto-filled, editable)
- **Discord Server** (optional URL)

Validation:
- All required fields marked with *
- Real-time validation with inline errors
- "Next" button disabled until valid

**Step 2: Format & Settings**

Fields:
- **Tournament Format*** (radio select with visual icons)
  - Single Elimination (bracket diagram)
  - Double Elimination (bracket diagram)
  - Round Robin (table diagram)
- **Team Capacity*** (select or number input)
  - 4, 8, 16, 32, 64, 128, Custom
  - Warning if >64: "Large tournaments require approval"
- **Match Format*** (select)
  - Best of 1 (BO1)
  - Best of 3 (BO3)
  - Best of 5 (BO5)
- **Check-in Required** (toggle)
  - If enabled: Check-in window duration (15/30/60 minutes)
- **Entry Fee** (toggle + amount)
  - Free Entry (toggle)
  - If paid: Amount in BDT (৳0-10,000)
  - **Accept DeltaCoin** (toggle) — allows players to pay with earned DC
  - Payment methods accepted: bKash, Nagad, Rocket, Bank Transfer (+ DeltaCoin if enabled)
- **Prize Pool*** (number input + distribution)
  - Total Prize Pool: ৳______
  - Auto-calculate distribution:
    - 1st: 50% (৳_____)
    - 2nd: 30% (৳_____)
    - 3rd: 20% (৳_____)
  - Or custom distribution (advanced)
- **Registration Window***
  - Opens: (datetime picker)
  - Closes: (datetime picker)
  - Validation: Closes before tournament start

---

**Advanced Options** (collapsible section, collapsed by default)

**Visual Hierarchy Mockup:**

```
┌────────────────────────────────────────────────────────┐
│ ⚙️ Advanced Options                        [Show ▼]    │  ← Collapsed state
│                                                         │
│ Fine-tune tournament behavior and features              │
└────────────────────────────────────────────────────────┘

When expanded → [Hide ▲]:

┌────────────────────────────────────────────────────────┐
│ ⚙️ Advanced Options                        [Hide ▲]    │
├────────────────────────────────────────────────────────┤
│ Fine-tune tournament behavior and features              │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 🎯 Dynamic Seeding                        [⚪ OFF] │ │
│ │ Automatically balance bracket based on              │ │
│ │ participant rankings and history                    │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 💰 Entry Fee Waivers                     [⚪ OFF] │ │
│ │ Waive fees for top-ranked teams to attract talent  │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 🏆 Custom Challenges                     [⚪ OFF] │ │
│ │ Bonus challenges with DeltaCoin/prize rewards      │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 📡 Live Match Updates                     [🔵 ON] │ │
│ │ Real-time scoreboard and WebSocket updates         │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 🔔 Check-in Reminders                    [🔵 ON] │ │
│ │ Send reminders 1 hour & 15 min before check-in    │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 👥 Public Registration List              [🔵 ON] │ │
│ │ Show registered teams publicly on tournament page  │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

**Component Specification:**

- **Section Header:** `h3` with gear icon ⚙️, subtitle text-secondary
- **Collapsible Trigger:** Button with `[Show ▼]` / `[Hide ▲]` (150ms transition)
- **Option Cards:** Each option in bordered card with:
  - **Icon:** Emoji or SVG (24x24px) representing feature
  - **Title:** Semibold, 16px, with toggle aligned right
  - **Description:** One-line explanation, text-secondary, 14px
  - **Learn More Link:** Small ghost button, opens help drawer (HTMX)
- **Toggle States:**
  - OFF: `⚪` gray circle, card background: `--bg-secondary`
  - ON: `🔵` blue circle, card background: `--bg-secondary` with `--brand-primary` left border (4px)
- **Spacing:** 16px between cards, 20px section padding
- **Animation:** 
  - Expand: 300ms ease-out with max-height transition
  - Toggle switch: 150ms ease-in-out
  - Card hover: 200ms transform translateY(-2px)

**Accessibility:**
- `aria-expanded="false"` on collapsed state
- `role="region"` for expanded content
- `aria-labelledby` linking header to content
- Keyboard navigation: Space/Enter to toggle

Click "Show Advanced Options ▼" to reveal:

1. **Dynamic Seeding** (toggle, default: off)
   - Description: "Automatically balance bracket based on participant rankings and history"
   - When enabled: Show seeding algorithm dropdown (Skill-based, Random with seed restrictions, Manual)
   - [Learn More →] (opens help article)
   - **Tooltip** (on hover): "Seed teams based on DeltaCrown ranking or match history to create balanced brackets"

2. **Entry Fee Waivers for Top Teams** (toggle, default: off)
   - Description: "Automatically waive entry fees for top-ranked teams to attract talent"
   - **Tooltip:** "Invite high-skill teams without entry fees based on their DeltaCrown ranking"
   - When enabled:
     - Select number of teams: 2, 4, 8
     - Minimum rank required: Input field (e.g., "Top 10")
     - Auto-notify waived teams (toggle)
   - [Learn More →]

3. **Custom Tournament Challenges** (toggle, default: off)
   - Description: "Create bonus challenges with extra prizes or DeltaCoin rewards"
   - **Tooltip:** "Add side objectives like 'Most Kills' or 'Fastest Win' with bonus rewards"
   - When enabled: Opens challenge builder:
     - Add Challenge button (repeatable)
     - For each challenge:
       - Challenge Name* (e.g., "Most Kills", "Fastest Win")
       - Description
       - Reward Type: DeltaCoin / Cash Prize / Badge
       - Reward Amount
       - Challenge Type: Individual / Team
     - Challenges display on match pages and player dashboards
   - [Learn More →]

4. **Live Match Updates** (toggle, default: on)
   - Description: "Enable real-time scoreboard integration and WebSocket updates"
   - **Tooltip:** "Live scores and bracket updates powered by WebSocket (recommended for competitive events)"
   - When disabled: Shows "Manual Updates" mode globally
     - Organizer must manually enter all scores
     - No live badges or real-time bracket updates
     - Reduces server load for casual tournaments
   - [Learn More →]

5. **Automated Check-in Reminders** (toggle, default: on)
   - Description: "Send email/Discord reminders 1 hour and 15 minutes before check-in"
   - **Tooltip:** "Reduce no-shows with automatic reminders sent before check-in window"
   - When enabled: Configure reminder channels (Email, Discord, Both)

6. **Public Registration List** (toggle, default: on)
   - Description: "Show registered teams/players publicly on tournament page"
   - **Tooltip:** "Make registrations public or keep them private until tournament starts"
   - When disabled: Only organizer can see registrations (for surprise reveals)

Each toggle includes:
- One-line description
- Small "Learn More →" link (opens help drawer)
- Visual indicator when enabled (blue accent)

**Step 3: Rules & Custom Fields**

Sections:

1. **Tournament Rules** (rich text editor)
   - Template option: "Use Standard Rules for [Game]"
   - Sections: Eligibility, Match Rules, Conduct, Disputes
   - Character count: 0/5000
   - Field name in database: `rules_text`

2. **Custom Registration Fields** (repeatable component with power-ups)
   
   **Field List View with Drag-Drop:**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ Custom Fields                          [+ Add Field]   │
   ├────────────────────────────────────────────────────────┤
   │ Drag to reorder · 3 fields configured                  │
   │                                                         │
   │ ┌────────────────────────────────────────────────────┐ │
   │ │ ⋮⋮ 📝 Team Discord Server              [Edit] [×] │ │  ← Drag handle
   │ │    Text · Required                                 │ │
   │ └────────────────────────────────────────────────────┘ │
   │                                                         │
   │ ┌────────────────────────────────────────────────────┐ │
   │ │ ⋮⋮ 🎮 In-Game ID                       [Edit] [×] │ │
   │ │    Text · Required · Validation: Riot ID           │ │
   │ └────────────────────────────────────────────────────┘ │
   │                                                         │
   │ ┌────────────────────────────────────────────────────┐ │
   │ │ ⋮⋮ 📎 Team Logo                        [Edit] [×] │ │
   │ │    File Upload · Optional · Max 5MB                │ │
   │ └────────────────────────────────────────────────────┘ │
   └────────────────────────────────────────────────────────┘
   ```
   
   **Drag-Drop Behavior:**
   - Drag handle (⋮⋮) on left side of each field card
   - On drag: Card elevates with shadow, cursor changes to `grab`
   - Drop zones highlight with blue dashed border
   - On drop: Smooth animation (200ms) to new position
   - Order saves automatically
   - **Alpine.js Implementation:** `x-sort` directive or Sortable.js integration
   
   **Add Field** button → Opens field builder modal:
   
   **Field Builder Modal Layout:**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ Add Custom Field                             [×Close]  │
   ├────────────────────────────────────────────────────────┤
   │ ┌──────────────────────┬─────────────────────────────┐ │
   │ │ Configuration        │ Live Preview                │ │  ← Split view
   │ │                      │                             │ │
   │ │ (Form on left)       │ (Field renders on right)    │ │
   │ └──────────────────────┴─────────────────────────────┘ │
   ├────────────────────────────────────────────────────────┤
   │                                [Cancel] [Save Field]   │
   └────────────────────────────────────────────────────────┘
   ```
   
   **For each field:**
   
   a) **Basic Settings**
   - Field Label* (text, 60 char max)
   - Field Type* (dropdown with ICONS):
     - 📝 Text (single line)
     - 🔢 Number
     - 🔗 URL
     - 📋 Select (dropdown)
     - ☑️ Multi-Select (checkboxes, multiple choices)
     - ✅ Checkbox Group (multiple yes/no options)
     - 📎 File Upload (for documents, images)
     - 📅 Date (date picker)
     - 📧 Email (validated email input)
     - 🎮 Game-specific (pre-configured Riot ID, Steam ID, etc.)
   - Required? (toggle)
   - Help Text (optional, shown below field, live preview updates)
   
   **Icon Display in Dropdown:**
   Each option shows icon + label with brief description on hover.
   Example: `📝 Text` → Hover shows "Single-line text input for short answers"
   
   b) **Validation** (if applicable)
   - Validation Preset (dropdown):
     - None
     - **Riot ID** (PlayerName#TAG format)
     - **Discord Tag** (username#1234 format)
     - **Bangladesh Phone** (+880 1XXX-XXXXXX format)
     - **URL** (valid http/https)
     - **Email**
     - Custom Regex (advanced)
   - Min/Max length or value constraints
   - Error message (custom validation failure text)
   
   c) **Conditional Visibility** (advanced)
   - Show this field only when: (dropdown)
     - Always (default)
     - Game = [Select Game] (e.g., only show "Riot ID" for VALORANT)
     - Another field has value = [condition]
   - Example use case: "Show 'Rank Limit' only when Game=VALORANT"
   
   d) **Display & Placement**
   - Display on Tournament Page (toggle)
     - If enabled: Shows field value as read-only badge on participant list
     - Example: Show "Team Discord Server" publicly
   - Collect at Registration (toggle, default: on)
     - If disabled: Admin-only field (organizer fills later)
   - Placement order: Drag to reorder fields in registration form
   
   e) **Field Options** (for Select/Multi-Select/Checkbox Group)
   - Add Option button (repeatable)
   - Option Label, Option Value
   - Default selection (for Select fields)
   
   **Live Preview Panel** (right side of modal, updates in real-time):
   
   ```
   ┌────────────────────────────────────────┐
   │ Preview: How players see this field    │
   ├────────────────────────────────────────┤
   │                                         │
   │ Team Discord Server *                  │  ← Field label (updates as you type)
   │ ┌───────────────────────────────────┐  │
   │ │ https://discord.gg/...            │  │  ← Field input (type-appropriate)
   │ └───────────────────────────────────┘  │
   │ Enter your team's Discord invite link  │  ← Help text (if provided)
   │                                         │
   │ [Preview on Dark Mode] [Preview Mobile]│  ← Toggle options
   └────────────────────────────────────────┘
   ```
   
   **Preview Features:**
   - **Real-time Updates:** Every change in configuration instantly updates preview
   - **Dark Mode Toggle:** See field in light/dark theme
   - **Mobile Preview:** Show how field renders on mobile (320px width)
   - **Validation Preview:** If validation selected, show example valid/invalid states
   - **Conditional Visibility Demo:** If conditions set, show "This field will appear when..."
   
   **Example Preview States:**
   
   1. **Text Field with Riot ID Validation:**
      ```
      In-Game Riot ID *
      ┌─────────────────────────┐
      │ PlayerName#TAG          │  ← Placeholder shows format
      └─────────────────────────┘
      Format: YourName#1234
      
      ✓ Valid: "Faker#KR1" (green check)
      ✗ Invalid: "BadFormat" (red error: "Must match PlayerName#TAG")
      ```
   
   2. **File Upload Field with Thumbnail & Progress:**
      
      **Before Upload:**
      ```
      Team Logo
      ┌─────────────────────────┐
      │  📎 Choose File         │  ← File button
      └─────────────────────────┘
      Accepted: PNG, JPG, WebP · Max: 5MB
      ```
      
      **During Upload (Progress Bar):**
      ```
      Team Logo
      ┌─────────────────────────┐
      │ 📷 team-logo.png (2.3MB)│
      │ ████████░░░░░░░░░ 45%   │  ← Progress bar
      └─────────────────────────┘
      Uploading...
      ```
      
      **After Upload (Thumbnail Preview):**
      ```
      Team Logo
      ┌──────────┐
      │ [Image]  │  ← Thumbnail (80x80px)
      │  Logo    │
      └──────────┘
      ✓ team-logo.png (2.3MB)
      [Change File] [Remove]
      ```
      
      **Error States:**
      
      a) **File Too Large:**
      ```
      ❌ File too large (8.5MB). Maximum size is 5MB.
      [Choose Another File]
      ```
      
      b) **Invalid Type:**
      ```
      ❌ Invalid file type (.pdf). Accepted formats: PNG, JPG, WebP
      [Choose Another File]
      ```
      
      c) **Upload Failed:**
      ```
      ❌ Upload failed. Please check your connection and try again.
      [Retry Upload]
      ```
   
   3. **Multi-Select with Options:**
      ```
      Preferred Match Times
      ☐ Morning (9 AM - 12 PM)
      ☐ Afternoon (12 PM - 5 PM)
      ☑ Evening (5 PM - 10 PM)    ← Pre-checked if default
      ☐ Night (10 PM - 2 AM)
      ```
   
   **Actions:**
   - **Cancel** (closes modal, discards changes)
   - **Save Field** (primary button, adds field to list, closes modal)
   - Duplicate Field (copy all settings)
   - Delete Field (with confirmation)
   - Drag handle (reorder fields)

3. **Seeding Method** (radio select)
   - Random Seeding
   - First-Come-First-Served
   - Use Team Rankings (if DeltaCrown rankings available)
   - Manual Seeding (organizer assigns after registration closes)
   - **Dynamic Seeding** (if enabled in Advanced Options)

4. **Sponsors** (optional, repeatable)
   - Add Sponsor button
   - For each sponsor:
     - Sponsor Name
     - Logo Upload (WebP/PNG/JPG, max 1MB)
     - Website URL (validation: valid URL)
     - Tier (Platinum/Gold/Silver/Bronze)
     - Sponsor Description (optional, 200 chars)

**Step 4: Preview & Publish**

Content:
- Full preview of tournament page (read-only)
- Tabs: Details, Rules, Sponsors
- Edit buttons next to each section (jump back to that step)
- Agreement checkbox:
  - "I agree to DeltaCrown Terms of Service"
  - "I confirm all information is accurate"
- Action buttons:
  - **Save as Draft** (gray) - Tournament not visible to public
  - **Publish Tournament** (blue, glowing) - Goes live immediately

**Validation Summary:**
- List of all validation errors (if any)
- Click error to jump to that step/field

**Success State:**
- After publishing: Redirect to tournament detail page
- Toast notification: "Tournament published successfully!"
- Confetti animation (brief celebration)

**Auto-save:**
- Draft auto-saved every 30 seconds
- "Last saved: 2 minutes ago" indicator (top-right)
- Resume draft from dashboard

**Responsive Behavior:**
- **Mobile:** Single-column form, larger touch targets
- **Desktop:** Form centered with max-width, sticky progress header

---

### 5.4 Organizer Dashboard

**Purpose:** Centralized management interface for tournament organizers.

**URL:** `/organizer/dashboard`

**Access:** Requires organizer role

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Dashboard Header                                        │
│  - Greeting: "Welcome back, OrganizersName!"            │
│  - Quick action: [+ Create Tournament]                  │
├────────────────────────────────────────────────────────┤
│ Overview Stats (4 cards)                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ 3 Active │ │ 47 Pending│ │ ৳12,500  │ │ 4.8 ⭐   │  │
│  │ Tournaments│ │ Payments │ │ To Payout│ │ Rating   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├────────────────────────────────────────────────────────┤
│ Tabs Navigation                                         │
│  [Active] [Upcoming] [Completed] [Drafts]              │
├────────────────────────────────────────────────────────┤
│ Tournament Table                                        │
│  ┌───────┬──────────┬────────┬──────────┬─────────┐   │
│  │ Title │ Date     │ Status │ Participants │ Actions│   │
│  ├───────┼──────────┼────────┼──────────┼─────────┤   │
│  │ Row 1 │ ...      │ ...    │ ...      │ [...]   │   │
│  │ Row 2 │ ...      │ ...    │ ...      │ [...]   │   │
│  └───────┴──────────┴────────┴──────────┴─────────┘   │
│  [Pagination]                                           │
└────────────────────────────────────────────────────────┘
```

**Overview Stats Cards:**

1. **Active Tournaments**
   - Count of live tournaments
   - Click to filter active

2. **Pending Payments**

---

**Navigation:**
- [← Previous: PART_4.2 - UI Components & Navigation](PART_4.2_UI_COMPONENTS_NAVIGATION.md)
- [→ Next: PART_4.4 - Registration & Payment Flow](PART_4.4_REGISTRATION_PAYMENT_FLOW.md)
- [↑ Back to Index](INDEX_MASTER_NAVIGATION.md)
