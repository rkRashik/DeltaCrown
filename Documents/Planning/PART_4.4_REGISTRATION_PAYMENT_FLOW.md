# PART 4.4: REGISTRATION & PAYMENT FLOW

**Navigation:**
- [← Previous: PART_4.3 - Tournament Management Screens](PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md)
- [→ Next: PART_4.5 - Bracket Match & Player Experience](PART_4.5_BRACKET_MATCH_PLAYER_EXPERIENCE.md)
- [↑ Back to Index](INDEX_MASTER_NAVIGATION.md)

---

2. **Pending Payments**
   - Count of unverified payment submissions
   - Red badge if >10
   - Click to navigate to payment verification tab

3. **Pending Payouts**
   - Total prize money to be paid out
   - Click to view payout schedule

4. **Average Rating**
   - Organizer rating (1-5 stars)
   - Based on participant feedback
   - Click to view reviews

**Tournament Table Columns:**

- **Thumbnail** (small banner preview)
- **Title** (clickable to tournament page)
- **Game** (badge)
- **Start Date**
- **Status** (badge with color coding):
  - Draft (gray)
  - Registration Open (blue)
  - Registration Full (purple)
  - Ongoing (green, live badge)
  - Completed (neutral)
  - Cancelled (red)
- **Participants** (progress: "16 / 32")
- **Payments** (progress: "12 verified, 4 pending")
- **Actions** (dropdown menu):
  - View Tournament
  - Edit Details
  - Manage Participants
  - Verify Payments
  - Manage Bracket
  - View Analytics
  - Duplicate
  - Cancel Tournament
  - Archive

**Active Tab Content:**

Features:
- Quick filters: "Live Now", "Needs Attention" (pending actions)
- Search by tournament name
- Sort by: Start date, participants, status
- Bulk actions: (checkbox column)
  - Send Announcement (to all participants)
  - Export Participants
  - Archive Selected

**Payment Verification Section** (when clicked):

Modal or slide-over panel showing:
- List of pending payment submissions
- For each submission:
  - Participant name and team
  - Payment method (bKash/Nagad/etc.)
  - Transaction ID
  - Amount
  - Proof image (zoomable)
  - Submitted date
  - Actions:
    - **Verify** (green button) - Marks payment as confirmed
    - **Reject** (red button) - Opens rejection reason modal
    - **Contact** (opens message dialog)

Real-time updates:
- New payment submissions appear with badge notification
- Toast notification: "New payment submission from Team Alpha"

**Bracket Management** (when clicked):

Interface for:
- Viewing current bracket
- Entering match results (if not submitted by participants)
- Resolving disputes
- Advancing winners
- Marking no-shows (disqualification)
- Exporting bracket as image/PDF

**Analytics Section:**

Charts and metrics (using **Chart.js** for template-first implementation):
- Registration timeline graph (line chart)
- Participant demographics (bar chart: regions, ranks)
- Traffic sources (pie chart: how users found tournament)
- Engagement metrics (views, registrations, completion rate)

**Tech Stack:** Chart.js 4.x for all data visualizations (aligned with Part 2, template-compatible, no React)

**Responsive Behavior:**

- **Desktop:** Table view with all columns
- **Tablet:** Hide less critical columns, horizontal scroll
- **Mobile:** Card view instead of table

---

### 5.5 Staff & Roles Management (Organizer Dashboard)

**Purpose:** Delegate tournament management tasks to staff members (referees, bracket managers, payment verifiers).

**URL:** `/organizer/dashboard/tournaments/<tournament-id>/staff`

**Access:** Tournament organizer (creator) only

**Layout:**

```
┌────────────────────────────────────────────────────────┐
│ Staff Management - DeltaCrown Valorant Cup 2025        │
├────────────────────────────────────────────────────────┤
│ Current Staff Members                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │ [Avatar] PlayerName  |  Referee     | [Remove]  │  │
│  │ [Avatar] OtherUser   |  Bracket Mgr | [Remove]  │  │
│  └──────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────┤
│ Add Staff Member                                        │
│  [Search users...] [Role Dropdown] [Add]               │
└────────────────────────────────────────────────────────┘
```

**Staff Roles & Permissions:**

| Role | Permissions |
|------|-------------|
| **Referee** | View all matches, enter/override scores, resolve disputes, disqualify teams |
| **Bracket Manager** | Edit bracket structure, advance winners, manage seeding, handle no-shows |
| **Payment Verifier** | View payment submissions, approve/reject payments, contact participants |
| **Moderator** | Manage community discussions, remove inappropriate content, ban users |
| **Co-Organizer** | All permissions except delete tournament or remove organizer |

**Add Staff Flow:**

1. Search for user by username/email
2. Select role from dropdown
3. Click "Add" — sends invitation notification
4. User must accept invitation (notification + email)
5. Once accepted, staff member appears in list

**Staff Member Actions:**

- **Edit Role:** Change permissions (dropdown)
- **Remove:** Revoke access (confirmation dialog)
- **View Activity Log:** See actions performed by staff member

**Audit Ribbon on Sensitive Screens:**

For actions performed by staff (or organizer), show audit notice:

```html
<div class="audit-ribbon">
    <svg class="icon-sm"><!-- Shield icon --></svg>
    <span>This action is logged for tournament integrity</span>
</div>
```

```css
.audit-ribbon {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: var(--radius-base);
    font-size: var(--text-xs);
    color: var(--warning);
    margin-bottom: var(--space-4);
}
```

**Examples of audited actions:**
- Score override by referee
- Payment approval/rejection
- Disqualification
- Bracket manual edit
- Prize payout confirmation

**Audit Log View (Organizer Only):**

- URL: `/organizer/dashboard/tournaments/<tournament-id>/audit-log`
- Table with columns: Timestamp, Staff Member, Action, Details
- Filter by: Date range, Staff member, Action type
- Export as CSV for records

---

## Tournament Management Summary

✅ **4 Screens Documented:**

1. **Tournament Listing Page** - Browse, filter, search with infinite scroll
2. **Tournament Detail Page** - Comprehensive view with tabs, live updates, sidebar actions
3. **Tournament Creation Wizard** - 4-step form with validation, preview, auto-save
4. **Organizer Dashboard** - Centralized management with stats, tables, payment verification

**Key UI Patterns:**
- Responsive grid layouts (1/2/3 columns)
- Tabbed navigation for content organization
- Progress indicators for multi-step flows
- Real-time updates via HTMX + WebSocket
- Contextual CTAs based on state
- Comprehensive filtering and search
- Empty states with helpful CTAs

---

## 6. Registration & Payment Flow

### 6.1 Registration Form

**Purpose:** Allow participants to register for a tournament with team/player information and custom fields.

**URL:** `/tournaments/<slug>/register` (modal or dedicated page)

**Entry Points:**
- "Register Now" button on tournament detail page
- "Register" CTA on tournament cards
- Direct link from tournament listing

**Prerequisites:**
- User must be logged in
- Tournament registration must be open
- User must not already be registered
- Capacity not yet reached

**Layout Structure (Modal Version):**

```
┌────────────────────────────────────────────────────────┐
│ Modal Overlay (backdrop blur)                           │
│  ┌────────────────────────────────────────────────┐    │
│  │ Header                                          │    │
│  │  "Register for DeltaCrown Valorant Cup 2025"   │    │
│  │  [X] Close                                      │    │
│  ├────────────────────────────────────────────────┤    │
│  │ Progress Steps                                  │    │
│  │  [1. Team Info] → [2. Custom Fields] → [3. Review]│    │
│  │  ████████████████░░░░░░░░░░░░░░░░░░░░  60%    │    │
│  ├────────────────────────────────────────────────┤    │
│  │ Form Content (scrollable)                       │    │
│  │  ┌────────────────────────────────────────┐    │    │
│  │  │ [Current step form fields]             │    │    │
│  │  │                                         │    │    │
│  │  └────────────────────────────────────────┘    │    │
│  ├────────────────────────────────────────────────┤    │
│  │ Footer Actions                                  │    │
│  │  [← Back]                      [Next →]        │    │
│  └────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

**Step 1: Team/Player Information**

**For Team-based Tournaments:**

Fields:
- **Select Team*** (dropdown)
  - List of user's existing teams
  - "+ Create New Team" option (opens inline form)
  - Team preview card (logo, name, members)
  
- **Team Members Verification** (read-only display)
  - List of team members with avatars
  - Check if meets min/max requirements
  - Warning if member already registered in another team

- **Captain Confirmation** (checkbox)
  - "I confirm I am authorized to register this team"
  - "All team members are aware and available"

**For Solo Tournaments:**

Fields:
- **Player Name*** (auto-filled from profile)
- **In-Game Username*** (auto-filled if available, editable)
- **Region*** (dropdown: Dhaka, Chittagong, Sylhet, etc.)

**Auto-fill Smart Features:**
- Pre-populate fields from user profile
- Remember last used team for similar tournaments
- Suggest teams based on game and team size

**Step 2: Custom Fields**

Dynamic fields based on organizer configuration:

Examples:
- **Discord Username** (text input)
  - Placeholder: "username#1234"
  - Validation: Discord username format
  
- **Riot ID** (text input, for VALORANT)
  - Placeholder: "PlayerName#TAG"
  - Real-time validation badge
  
- **Preferred Communication** (select)
  - Discord, WhatsApp, Telegram
  
- **Team Logo URL** (URL input)
  - Optional thumbnail preview
  
- **Emergency Contact** (phone number)
  - Bangladesh phone format validation

**Help Text:**
- Each field has contextual help icon
- Tooltip on hover with instructions
- Example values shown in placeholder

**Step 3: Review & Confirm**

Content:
- **Tournament Summary Card**
  - Tournament name, game, date
  - Entry fee: ৳500 (highlighted if paid)
  - Payment required badge (if applicable)

- **Registration Summary**
  - Team/Player info review
  - All custom field values
  - Edit buttons (jump back to specific step)

- **Rules Acceptance**
  - Expandable rules section (collapsible)
  - Checkbox: "I have read and accept the tournament rules"
  - Link to full rules in new tab

- **Entry Fee Notice** (if applicable)
  - Alert box (warning style):
    ```
    ⚠️ Entry Fee Required
    After registration, you must submit payment of ৳500
    Registration will be pending until payment is verified
    ```

- **Consent Checkboxes**
  - "I agree to DeltaCrown Terms of Service"
  - "I consent to share my in-game stats for tournament use"

**Action Buttons:**
- **Back** (go to previous step)
- **Register** (primary, blue, disabled until all checkboxes checked)
- **Contact Organizer** (ghost button, bottom-left, opens message dialog)

**Loading State:**
- Button shows spinner: "Processing..."
- Disable form interactions

**Success State:**
- Checkmark animation
- "Registration Successful!" message
- If entry fee required: Redirect to payment submission
- If free: Show confirmation screen

**Error Handling:**
- Inline validation on each field (real-time)
- Summary of errors at top of form
- Scroll to first error field
- Toast notification for server errors
- **"Contact Organizer"** option if persistent errors

---

### 6.2 Payment Submission

**Purpose:** Allow registered participants to submit payment proof for entry fee verification.

**URL:** `/tournaments/<slug>/payment` or `/registrations/<id>/payment`

**Access:** 
- Shown immediately after registration (if entry fee required)
- Accessible from user dashboard ("Pending Payment" badge)
- Email reminder with direct link

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Breadcrumbs: Dashboard / My Tournaments / Payment       │
├────────────────────────────────────────────────────────┤
│ Page Header                                             │
│  H1: "Submit Payment Proof"                             │
│  Subtitle: "For DeltaCrown Valorant Cup 2025"           │
├────────────────────────────────────────────────────────┤
│ Layout (2-column on desktop)                            │
│ ┌─────────────────────────┬─────────────────────────┐  │
│ │ Payment Instructions    │ Payment Form            │  │
│ │ (Left, sticky)          │ (Right)                 │  │
│ │                         │                         │  │
│ │ - Amount: ৳500          │ - Payment Method*       │  │
│ │ - Methods accepted      │ - Transaction ID*       │  │
│ │ - Account numbers       │ - Screenshot Upload*    │  │
│ │ - Deadline countdown    │ - Amount Paid*          │  │
│ │                         │ - Notes (optional)      │  │
│ │                         │ [Submit]                │  │
│ └─────────────────────────┴─────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

**Payment Instructions Panel (Left):**

Content:
- **Amount to Pay:** ৳500 (large, bold, highlighted)
  
- **Accepted Payment Methods** (visual cards):
  ```
  ┌─────────┬─────────┬─────────┬─────────┬──────────┐
  │ bKash   │ Nagad   │ Rocket  │ Bank    │DeltaCoin │
  │ [Logo]  │ [Logo]  │ [Logo]  │Transfer │ [Icon]   │
  └─────────┴─────────┴─────────┴─────────┴──────────┘
  ```

- **DeltaCoin Option** (if enabled by organizer):
  - Display: "💰 **Pay with DeltaCoin:** 500 DC"
  - Help text: "DeltaCoin earned from achievements and past tournament winnings"
  - Balance display: "Your balance: 1,250 DC"
  - If insufficient: "Insufficient balance. Earn more DC or use cash payment."
  - **Auto-deduct on submission** (no screenshot required)

- **Organizer Cash Payment Details** (for bKash/Nagad/Rocket/Bank):
  - **bKash Personal:** 01712345678 [Copy 📋]
    - Send Money → Enter this number → Amount: ৳500
  
  - **Nagad:** 01812345678 [Copy 📋]
  - **Rocket:** 01912345678 [Copy 📋]
  - **Bank Transfer:**
    - Bank: Dutch-Bangla Bank
    - Account: 1234567890123 [Copy 📋]
    - Name: Tournament Organizer Name

- **Deadline Countdown** (prominent):
  ```
  ⏰ Submit payment within:
  [23 : 45 : 32]
   HH   MM   SS
  ```
  - After 48 hours: Registration may be cancelled

- **Help Section:**
  - "Need Help?" expandable
  - FAQ: How long for verification? What if rejected?
  - Contact organizer button

**Payment Form (Right):**

Fields:

1. **Payment Method*** (radio button cards)
   ```
   ○ DeltaCoin  ○ bKash  ○ Nagad  ○ Rocket  ○ Bank Transfer
   ```
   - Large, clickable cards with logos
   - Selected state: Blue border + check icon
   - **DeltaCoin card:** Shows DC balance, auto-hides fields 2-4 when selected

2. **Transaction ID / Reference Number*** (text input — hidden if DeltaCoin)
   - Placeholder: "Enter transaction/reference ID from receipt"
   - Help text: "Found on your mobile banking app receipt"
   - Character count if needed

3. **Amount Paid*** (number input — hidden if DeltaCoin)
   - Pre-filled: ৳500
   - Validation: Must match entry fee exactly
   - **Error states:**
     - Underpaid: "❌ Amount is ৳450. Entry fee is ৳500. Please pay the full amount."
     - Overpaid: "⚠️ Amount is ৳550. Entry fee is ৳500. Excess will not be refunded."
   - Real-time validation feedback

4. **Payment Screenshot*** (file upload — hidden if DeltaCoin)
   - Drag-and-drop area
   - Supported formats: JPG, PNG, PDF (max 5MB)
   - Image preview after upload (zoomable)
   - Requirements:
     - Must show transaction ID
     - Must show amount
     - Must show date/time
   - Example screenshot button (shows sample)
   - **File validation errors:**
     - Too large: "File size is 7.2MB. Maximum is 5MB. Try compressing the image."
     - Invalid format: "File type .txt not supported. Please upload JPG, PNG, or PDF."
     - Corrupted: "Unable to read file. Please try again or use a different file."

5. **Additional Notes** (textarea, optional)
   - Placeholder: "Any additional information..."
   - Character limit: 500

**Validation:**
- All required fields must be filled (except DeltaCoin auto-payment)
- Transaction ID format check (alphanumeric, min 6 characters)
- Amount must match exactly (warn on overpay, error on underpay)
- File must be valid image/PDF under 5MB

**Submit Button:**
- **DeltaCoin:** "Confirm Payment (500 DC)"
- **Cash methods:** "Submit Payment Proof"
- Loading state: Spinner + "Processing..." or "Uploading..."
- Disabled until form valid

**Success State:**
- Redirect to confirmation screen
- Toast: "Payment proof submitted successfully!"

**Payment Status Visual States:**

1. **Pending Verification** (Yellow badge - `--warning`):
   - Show submitted details (read-only)
   - Badge: `🕐 Pending Verification`
   - Estimated verification time: "Usually within 24 hours"
   - "Edit Submission" button (if organizer allows)
   - "Cancel Registration" button (with confirmation)
   - **"Contact Organizer"** button (prominent, opens message dialog)
   - **Analytics:** `data-analytics-id="payment_pending_view"`

2. **Verification In Progress** (Blue badge - `--info`):
   - Badge: `🔍 Verification In Progress`
   - Message: "Organizer is currently reviewing your payment proof"
   - Progress indicator: "Started 2 hours ago"
   - No edit allowed during verification
   - **"Contact Organizer"** button available

3. **Approved** (Green badge - `--success`):
   - Badge: `✓ Payment Verified`
   - Confetti animation on first view
   - Message: "Your payment has been approved. You're all set!"
   - Display: Approved by [Organizer Name], Verified on [Date]
   - Next steps card: "Check-in opens 30 minutes before start"
   - **Analytics:** `data-analytics-id="payment_approved_view"`

4. **Rejected** (Red badge - `--error`):
   - Badge: `✗ Payment Rejected`
   - Red alert box with rejection reason from organizer
   - Reason display: "Screenshot unclear - amount not visible"
   - "Resubmit Payment" button (clears form, pre-fills details)
   - **"Contact Organizer"** button (discuss rejection)
   - **Analytics:** `data-analytics-id="payment_rejected_resubmit"`

5. **Refunded** (Purple badge - `--brand-secondary`):
   - Badge: `↩️ Refunded`
   - Message: "Your payment has been refunded to [Method]"
   - Reason: "Tournament cancelled" or "Organizer-initiated"
   - Refund amount: ৳500
   - Refund date: [Date]
   - No action buttons (final state)

6. **Fee Waived** (Gold badge - `--brand-accent`):
   - Badge: `🎉 Fee Waived`
   - Message: "Entry fee waived by organizer - You're a featured participant!"
   - Reason: "Top-ranked team" or "Sponsor invitation" or "Promotional waiver"
   - Display: Waived by [Organizer Name]
   - No payment required

7. **Expired** (Gray badge - faded `--error`):
   - Badge: `⏰ Payment Expired`
   - Warning alert: "Payment deadline passed. Your registration has been cancelled."
   - Explanation: "The tournament may allow late registration if spots are available."
   - **"Contact Organizer"** button (request extension)
   - "Re-register" button (if tournament still open)
   - **Analytics:** `data-analytics-id="payment_expired_contact"`

**Edge State Banners (contextual alerts):**

**Color Token Reference for All Alerts:**
- **Error/Critical** → `--error` (#EF4444) - payment rejected, check-in missed, duplicate entries
- **Warning/Caution** → `--warning` (#F59E0B) - underpaid, team conflict, deadline approaching
- **Info/Notice** → `--info` (#3B82F6) - overpaid, helpful tips
- **Success** → `--success` (#10B981) - payment approved, registration confirmed

1. **Underpaid Amount:** (Warning - `--warning`)
   ```
   ⚠️ Your submitted amount (৳450) is less than the entry fee (৳500).
   Please resubmit with the correct amount or contact the organizer.
   ```
   - **CSS Class:** `alert alert-warning`
   - **Icon:** `⚠️` warning triangle
   - **Action:** "Resubmit Payment" button

2. **Overpaid Amount:** (Info - `--info`)
   ```
   ℹ️ Your submitted amount (৳550) exceeds the entry fee (৳500).
   The excess ৳50 will not be refunded. Proceed only if intended.
   ```
   - **CSS Class:** `alert alert-info`
   - **Icon:** `ℹ️` info circle
   - **Action:** "Confirm Anyway" button

3. **Check-in Missed:** (Error - `--error`)
   ```
   ❌ Check-in deadline passed. You have been disqualified from the tournament.
   Contact the organizer if you believe this is an error.
   ```
   - **CSS Class:** `alert alert-error`
   - **Icon:** `❌` cross mark
   - **"Contact Organizer"** button (secondary, opens message dialog with pre-filled subject: "Check-in Missed Appeal")

4. **Team Member Already Registered:** (Warning - `--warning`)
   ```
   ⚠️ Player "PlayerName" is already registered in another team for this tournament.
   Please select a different team member or withdraw their other registration.
   ```
   - **CSS Class:** `alert alert-warning`
   - **Icon:** `⚠️` warning triangle
   - **Action:** "Change Team Member" button

5. **Duplicate Registration Attempt:** (Error - `--error`)
   ```
   ❌ Your team is already registered for this tournament.
   You cannot register the same team twice.
   ```
   - **CSS Class:** `alert alert-error`
   - **Icon:** `❌` cross mark
   - **Action:** "View Existing Registration" button

6. **Payment Expired:** (Error - `--error`)
   ```
   ⏰ Payment deadline expired. Your registration has been cancelled.
   Contact the organizer to request an extension if spots are still available.
   ```
   - **CSS Class:** `alert alert-error`
   - **Icon:** `⏰` clock
   - **Action:** "Contact Organizer" button (primary)

---

### 6.3 Confirmation Screen

**Purpose:** Confirm successful registration and guide user to next steps.

**URL:** `/tournaments/<slug>/registered` or `/registrations/<id>/confirmation`

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Success Hero (centered, full-width)                     │
│  ✓ Success Icon (large, animated checkmark)            │
│  H1: "Registration Successful!"                         │
│  Subtitle: "You're all set for DeltaCrown Valorant Cup"│
├────────────────────────────────────────────────────────┤
│ Status Card (centered, max-width 800px)                 │
│  ┌────────────────────────────────────────────────┐    │
│  │ Registration Status                             │    │
│  │  - Team: Team Alpha                             │    │
│  │  - Tournament: DeltaCrown Valorant Cup 2025     │    │
│  │  - Status: [Pending Payment] or [Confirmed]     │    │
│  │  - Registration Date: Nov 3, 2025               │    │
│  └────────────────────────────────────────────────┘    │
├────────────────────────────────────────────────────────┤
│ Next Steps (3-column cards)                             │
│  ┌──────────┬──────────┬──────────┐                    │
│  │ 1. Pay   │ 2. Check │ 3. Play  │                    │
│  │ Entry Fee│ -In      │ Tournament│                    │
│  └──────────┴──────────┴──────────┘                    │
├────────────────────────────────────────────────────────┤
│ Quick Actions (button group)                            │
│  [View Tournament] [Add to Calendar] [Share]            │
├────────────────────────────────────────────────────────┤
│ Important Information (card)                            │
│  - Check-in time, Discord server, Rules reminder        │
└────────────────────────────────────────────────────────┘
```

**Success Hero Section:**

Visual:
- Large checkmark icon (80px) with green glow
- Confetti animation (brief, 2 seconds)
- Success message tailored to status:
  - If payment required: "Registration Received!"
  - If free entry: "You're Registered!"
  - If waitlist: "You're on the Waitlist!"

**Status Card:**

Information displayed:
- **Registration ID:** REG-12345 (copyable)
- **Tournament:** [Tournament Name] (link)
- **Team/Player:** [Team Name]
- **Status:** Badge with color coding
  - 🟡 Pending Payment (yellow)
  - 🟢 Confirmed (green)
  - 🔵 Waitlisted (blue)
- **Registration Date:** Nov 3, 2025 10:30 AM
- **Entry Fee:** ৳500 (if applicable)
  - Link to payment submission if not paid

**Next Steps Cards:**

**Card 1: Complete Payment** (if applicable)
- Icon: 💳
- Title: "Submit Payment Proof"
- Description: "Upload your payment screenshot to confirm your spot"
- Deadline: "Within 48 hours"
- Button: "Submit Payment" (primary)

**Card 2: Check-In**
- Icon: ✅
- Title: "Check-In Required"
- Description: "Check in 30 minutes before tournament start"
- Time: "Dec 15, 2025 - 9:30 AM BST"
- Button: "Set Reminder"

**Card 3: Prepare**
- Icon: 🎮
- Title: "Get Ready to Play"
- Description: "Join tournament Discord and review rules"
- Button: "Join Discord"

**Quick Actions:**

Buttons:
1. **View Tournament Details** (secondary button)
   - Navigates back to tournament page

2. **Add to Calendar** (ghost button)
   - Dropdown: Google Calendar, Outlook, iCal
   - Pre-filled event with tournament details

3. **Share with Team** (ghost button)
   - Dropdown: Copy link, WhatsApp, Discord
   - Shareable link: "I just registered for [Tournament]!"

**Important Information Card:**

Alert-style box (info):

Content:
- **Check-in Window:** Dec 15, 2025 - 9:30 AM to 10:00 AM BST
  - "Failure to check in will result in disqualification"
  
- **Tournament Discord:** [Join Server] button
  - "Mandatory for communication and match coordination"
  
- **Tournament Rules:** [Read Full Rules] link
  - "Make sure all team members are aware"
  
- **Contact Organizer:** [Message] button
  - "For any questions or issues"

**Email Confirmation:**

User receives email with:
- Registration confirmation
- All important dates and times
- Payment instructions (if applicable)
- Calendar attachment (.ics file)
- Tournament rules PDF

**Status-Specific Variations:**

**Free Entry (No Payment Required):**
- Skip Card 1 (payment)
- Status: "Confirmed ✓" (green)
- Emphasize preparation steps

**Waitlisted:**
- Hero: "You're on the Waitlist"
- Explanation: "You'll be automatically enrolled if a spot opens"
- Status: "Waitlisted (Position #5)"
- Email notification when spot opens

**Responsive Behavior:**
- **Desktop:** 3-column next steps cards
- **Mobile:** Stacked cards, full-width buttons

---

## Registration & Payment Flow Summary

✅ **3 Screens Documented:**

1. **Registration Form** - Multi-step modal/page with team selection, custom fields, review
2. **Payment Submission** - Split layout with instructions + upload form, deadline countdown
3. **Confirmation Screen** - Success state with status, next steps, quick actions

**Key UX Features:**
- **Progressive Disclosure:** Multi-step forms reduce cognitive load
- **Smart Auto-fill:** Pre-populate from user profile and team data
- **Real-time Validation:** Instant feedback on field errors
- **Clear Instructions:** Payment details prominently displayed with copy buttons
- **Deadline Awareness:** Countdown timer for payment submission
- **Status Transparency:** Clear badges and explanations for each state
- **Action-Oriented:** Next steps guide users through post-registration tasks
- **Calendar Integration:** Easy addition to user's calendar
- **Mobile Optimization:** Touch-friendly, single-column layouts

**Error Prevention:**
- Required field indicators (*)
- Inline validation messages
- Confirmation dialogs for destructive actions
- Image preview before submission
- Amount matching validation

**Accessibility:**
- Form labels with explicit associations
- Error announcements via aria-live regions
- Keyboard navigable multi-step forms
- High contrast status badges

---

## 7. Bracket & Match Screens

### 7.1 Bracket Visualization

**Purpose:** Interactive tournament bracket for viewing matchups, results, and progression.

**URL:** `/tournaments/<slug>/bracket`

**Key Features:**
- **SVG-based bracket tree** with zoom/pan controls
- **Responsive layouts:** Single/double elimination, round robin table
- **Real-time updates** via WebSocket
- **User highlight:** User's team path emphasized
- **Match navigation:** Click node to view match details

**Bracket Controls:**
- Zoom in/out buttons (+/-)
- Fit to screen button
- Download as image (PNG/PDF)
- Fullscreen mode
- Minimap for large brackets (>32 teams)

**Bracket Node Structure:**
```
┌───────────────────────┐
│ SEMIFINALS - Match 1  │
├───────────────────────┤
│ Team Alpha        [2] │ ← Winner (bold)
│ Team Beta         [0] │
└───────────────────────┘
```

**States:**
- **Upcoming:** Gray border, TBD teams
- **In Progress:** Blue border, live badge, pulsing
- **Completed:** Green border, winner highlighted
- **User's Team:** Neon cyan border with glow

### 7.2 Match Card (Compact)

**Purpose:** Display match information in bracket or list views.

**Visual (from Component Library 4.2):**
- Team logos, names, scores
- Match status badge (Scheduled/Live/Completed)
- Round indicator (Quarterfinals, Semifinals, etc.)
- Stream link icon (if available)
- Click to expand to full match page

### 7.3 Live Match Page

**Purpose:** Real-time match tracking with scores, chat, and stream integration.

**URL:** `/tournaments/<slug>/matches/<match-id>`

**Layout:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Match Header                                            │
│  [LIVE] SEMIFINALS - Match 1                            │
│  DeltaCrown Valorant Cup 2025                           │
│  👁️ 1,234 viewers online                               │  ← Viewers counter
├────────────────────────────────────────────────────────┤
│ Scoreboard (prominent)                                  │
│  ┌─────────────────────────────────────────────┐       │
│  │ Team Alpha  [13]  VS  [8]  Team Beta        │       │
│  │ [Logo]                          [Logo]      │       │
│  └─────────────────────────────────────────────┘       │
├────────────────────────────────────────────────────────┤
│ Content Tabs                                            │
│  [Stream] [Map Stats] [Chat] [Info]                    │
├────────────────────────────────────────────────────────┤
│ Tab Content Area                                        │
│  (Stream embed, stats, chat, or match info)            │
└────────────────────────────────────────────────────────┘
```

**Viewers Online Counter:**

**Position:** Below match title, right-aligned or center

**Visual Design:**
```
👁️ 1,234 viewers online
```
- **Icon:** Eye emoji (👁️) or SVG eye icon
- **Count:** Formatted with commas (1,234 / 12,345 / 123K for > 100k)
- **Label:** "viewers online" in text-secondary color
- **Styling:** 
  - Small badge style with subtle background (`--bg-tertiary`)
  - Pulsing green dot (•) next to icon when count is updating
  - Font size: 14px, medium weight

**Update Behavior:**
- **Real-time Updates:** WebSocket connection tracks page views
- **Update Frequency:** Every 5 seconds (batched to reduce load)
- **Animation:** Smooth number transition (150ms ease-out) when count changes
- **Peak Indicator:** Show "🔥 Peak: 2,456" on hover (tooltip)
- **Historical Data:** Organizers can view viewer graph in dashboard

**Technical Implementation:**
```javascript
// WebSocket message for viewer count update
{
    "type": "viewer_count",
    "match_id": 123,
    "count": 1234,
    "peak": 2456
}

// Update counter with animation
function updateViewerCount(newCount) {
    const counter = document.querySelector('.viewer-count');
    const oldCount = parseInt(counter.textContent);
    
    // Animate number transition
    animateCounter(oldCount, newCount, 150);
    
    // Add pulse effect
    counter.classList.add('count-updated');
    setTimeout(() => counter.classList.remove('count-updated'), 150);
}
```

**Viewer Tracking:**
- **Active Viewer:** User has page tab active (Page Visibility API)
- **Idle Detection:** User idle > 5 minutes = not counted
- **Session Timeout:** Disconnect after 10 minutes of inactivity
- **Unique Count:** One count per user session (not page refreshes)
- **Bot Prevention:** Rate limiting and CAPTCHA challenges if suspicious

**Display Rules:**
- **Live matches:** Show real-time count
- **Upcoming matches:** Show "Match starts in X minutes"
- **Completed matches:** Show "Watched by 2,456 viewers" (peak count)
- **No viewers:** Show "Be the first to watch" (encourages engagement)

**Privacy:**
- **Anonymous Counting:** No individual user tracking displayed publicly
- **Organizer View:** Detailed analytics in dashboard (viewer timeline graph)

**Scoreboard Features:**
- **Live score updates** (WebSocket)
- **Map progress:** "Map 1 of 3" (for BO3/BO5)
- **Round-by-round timeline** (expandable)
- **Team rosters:** Hover team logo to see players

**Stream Tab:**
- YouTube/Twitch embed (responsive iframe)
- If no stream: "No stream available" empty state
- Viewer count display
- Chat integration alongside stream

**Map Stats Tab** (for applicable games):
- Kill/death leaderboard
- Objective completions
- Economy graphs (CS2, VALORANT)
- MVP highlight

**Chat Tab:**
- Live chat room (WebSocket)
- Moderation controls (for organizers)
- Emoji reactions
- Rate limiting to prevent spam

**Info Tab:**
- Match schedule
- Tournament rules excerpt
- Referee information
- **Contact Organizer** button (prominent, opens message dialog)
- Report issue button

### 7.4 Result Submission

**Purpose:** Allow participants to submit match results and evidence.

**URL:** `/tournaments/<slug>/matches/<match-id>/submit`

**Access:** Only participants of the match

**Form Fields:**

1. **Match Outcome*** (radio select)
   - ○ We Won
   - ○ We Lost
   - ○ Draw (if applicable)

2. **Score*** (number inputs)
   - Our Score: ___
   - Opponent Score: ___
   - Validation: Must be valid for match format

3. **Evidence Upload*** (multiple files)
   - Screenshot(s) of final scoreboard
   - Supported: PNG, JPG (max 10MB per file, up to 5 files)
   - Drag-and-drop area with preview grid
   - Help text: "Include full scoreboard with both team names visible"

4. **Additional Notes** (textarea, optional)
   - Any relevant match details
   - Issues encountered
   - Character limit: 500

**Submit Button:**
- "Submit Result"
- Confirmation dialog: "This will notify the opponent and referee"

**States:**
- **Both teams submitted same result:** Auto-approved, winner advances
- **Conflicting results:** Creates dispute, referee notified
- **One team submitted:** Shows "Waiting for opponent confirmation"

---

## 8. Player Experience Screens

### 8.1 Player Dashboard

**Purpose:** Personalized hub for players to manage tournaments, matches, and achievements.

**URL:** `/dashboard` or `/my/tournaments`

**Layout:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Welcome Header & Profile Badge Progress                │
│  Avatar + "Welcome back, PlayerName!"                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 🏅 Badge Level: Competitive Player (Lvl 15)      │  │
│  │ ████████████░░░░░░░░ 2,450 / 3,000 XP (82%)     │  │  ← Progress bar
│  │ 550 XP to next level: "Elite Competitor"         │  │
│  └──────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────┤
│ Quick Stats (4 cards)                                   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                  │
│  │ 5    │ │ 2    │ │ 12   │ │ 3    │                  │
│  │Active│ │Live  │ │Total │ │Wins  │                  │
│  └──────┘ └──────┘ └──────┘ └──────┘                  │
├────────────────────────────────────────────────────────┤
```

**Profile Badge Level Progress Bar:**

**Visual Design:**
```
┌────────────────────────────────────────────────────────┐
│ 🏅 Badge Level: Competitive Player (Lvl 15)            │
│ ████████████████░░░░ 2,450 / 3,000 XP (82%)           │  ← Gradient fill
│ 🎯 550 XP to Elite Competitor                          │
└────────────────────────────────────────────────────────┘
```

**Badge Level Tiers:**
1. **Rookie** (Lvl 1-4): Gray badge, 0-1,000 XP
2. **Amateur** (Lvl 5-9): Green badge, 1,000-2,500 XP
3. **Competitive** (Lvl 10-14): Blue badge, 2,500-5,000 XP
4. **Elite** (Lvl 15-19): Purple badge, 5,000-10,000 XP
5. **Pro** (Lvl 20-24): Gold badge, 10,000-20,000 XP
6. **Legend** (Lvl 25+): Rainbow gradient, 20,000+ XP

**XP Earning:**
- Tournament participation: 100 XP
- Tournament win: 500 XP
- Match win: 50 XP
- Perfect game: 100 XP bonus
- Prediction correct: 10 XP
- MVP vote: 25 XP

**Progress Bar Styling:**
- **Gradient Fill:** Tier-specific colors (blue for Competitive tier)
- **Smooth Animation:** 400ms ease-out on XP gain
- **Percentage Display:** Shows % completion
- **Next Level Preview:** "550 XP to Elite Competitor"

**Level Up Animation:**

When player earns enough XP to level up:

1. **Progress Bar Fills:** Smooth animation (1s) from current to 100%
2. **Flash Effect:** Gold flash across bar
3. **Confetti Burst:** Canvas-confetti celebration (1.5s)
4. **Level Up Modal:**
   ```
   ┌────────────────────────────────────┐
   │ 🎉 LEVEL UP! 🎉                   │
   │                                    │
   │ You are now Level 16!              │
   │ 🏅 Elite Competitor                │
   │                                    │
   │ New Perks Unlocked:                │
   │ ✓ Priority tournament registration │
   │ ✓ Special badge on profile         │
   │ ✓ 100 DC bonus reward 🪙           │
   │                                    │
   │ [Share Achievement] [Continue]     │
   └────────────────────────────────────┘
   ```
5. **Sound Effect:** Optional "level up" sound (can disable in settings)
6. **Profile Badge Updates:** New tier badge appears immediately
7. **Analytics:** `data-analytics-id="gamification_level_up"`

**Progress Bar CSS:**
```css
.progress-bar-gamification {
    height: 24px;
    background: var(--bg-tertiary);
    border-radius: var(--radius-full);
    position: relative;
    overflow: hidden;
}

.progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #3B82F6, #8B5CF6); /* Tier gradient */
    border-radius: var(--radius-full);
    transition: width 400ms ease-out;
    position: relative;
}

.progress-bar-fill.leveling-up {
    animation: level-up-flash 1s ease-out;
}

@keyframes level-up-flash {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; box-shadow: 0 0 30px var(--brand-accent); }
}
```

**Hover Tooltip:**
- Hovering over progress bar shows detailed XP breakdown:
  ```
  Recent XP Gains:
  • Tournament Win: +500 XP
  • 3 Match Wins: +150 XP
  • 5 Correct Predictions: +50 XP
  Total this week: +700 XP
  ```

├────────────────────────────────────────────────────────┤
│ Sections (tabs or cards)                                │
│  - Upcoming Tournaments                                 │
│  - Active Matches (live badge if any)                   │
│  - Recent Achievements                                  │
│  - Pending Actions (payment, check-in, result submit)   │
└────────────────────────────────────────────────────────┘
```

**Upcoming Tournaments Section:**
- Card list with tournament info
- Countdown to start
- Check-in button (if within window)
- View bracket link
- Withdraw button (with confirmation)

**Active Matches:**
- Match cards with live updates
- "Submit Result" button (if match completed)
- Join stream button
- Real-time score updates

**Pending Actions (Priority):**
- Red badge count
- Action items:
  - "Submit payment for [Tournament]" (urgent, deadline shown)
  - "Check in for [Tournament]" (urgent, time remaining)
  - "Submit match result" (reminder)
  - "Resolve dispute" (if applicable)

### 8.2 Tournament History

**Purpose:** Archive of past tournament participations and results.

**URL:** `/profile/tournaments` or `/my/history`

**Features:**
- **Timeline view** (default) or **grid view** toggle
- **Filters:** Date range, game, status (Completed/Cancelled)
- **Search:** Tournament name
- **Sort:** Most recent, best placement, highest prize

**Tournament History Card:**
- Tournament name, game badge
- Date participated
- Placement badge: 🥇 1st, 🥈 2nd, 🥉 3rd, or "Top 8"
- Prize earned: ৳5,000 (if won)
- Certificate link (if issued)
- "View Details" button

**Statistics Summary:**
- Total tournaments: 24
- Win rate: 35%
- Total prizes earned: ৳15,000
- Best placement: 🥇 Champion (3x)
- Favorite game: VALORANT (15 tournaments)

### 8.3 Certificate View

**Purpose:** Display and share tournament certificates.

**URL:** `/certificates/<certificate-id>`

**Layout:**

```
┌────────────────────────────────────────────────────────┐
│ 🎊 Confetti Animation (1.5s on page load) 🎊           │  ← Celebration!
├────────────────────────────────────────────────────────┤
│ Certificate Preview (full-width, elegant design)        │
│  ┌────────────────────────────────────────────────┐    │
│  │ ╔════════════════════════════════════════════╗ │    │
│  │ ║  DeltaCrown Tournament Engine              ║ │    │
│  │ ║  Certificate of Achievement                ║ │    │
│  │ ║                                            ║ │    │
│  │ ║  This certifies that                       ║ │    │
│  │ ║  [Team Alpha]                              ║ │    │
│  │ ║  has achieved                              ║ │    │
│  │ ║  🥇 1st Place                              ║ │    │
│  │ ║  in                                        ║ │    │
│  │ ║  DeltaCrown Valorant Cup 2025              ║ │    │
│  │ ║                                            ║ │    │
│  │ ║  Prize: ৳25,000                            ║ │    │
│  │ ║  Date: December 15, 2025                   ║ │    │
│  │ ║                                            ║ │    │
│  │ ║  [QR Code]  [Organizer Signature]         ║ │    │
│  │ ║  Verify: CERT-ABC123                       ║ │    │
│  │ ╚════════════════════════════════════════════╝ │    │
│  └────────────────────────────────────────────────┘    │
├────────────────────────────────────────────────────────┤
│ Actions                                                 │
│  [📥 Download PDF] [📤 Share] [✓ Verify Certificate]   │
├────────────────────────────────────────────────────────┤
│ Share on Social (expanded when clicking Share)          │
│  ┌────────────────────────────────────────────────┐    │
│  │ [📘 Facebook] [🐦 Twitter] [💼 LinkedIn]       │    │
│  │ [📸 Instagram Story] [📋 Copy Link]            │    │
│  └────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

**Page Load Animation:**
- **Confetti burst** on first certificate view (1.5s duration)
- Uses canvas-confetti.js with gold colors (#FFD700, #FFA500, #DAA520)
- Triggered once per session (localStorage flag prevents repeat)
- Respects `prefers-reduced-motion`
- **Analytics:** `data-analytics-id="certificate_confetti_triggered"`

**Certificate Features:**
- **Dynamic design** based on placement (gold, silver, bronze themes)
- **QR code** for verification (links to public verification page)
- **Unique ID:** CERT-ABC123 (verifiable)
- **Organizer signature** (digital or uploaded image)
- **Featured winner badge** (if organizer marked as featured)

**Actions:**

1. **Download PDF** 
   - High-res PDF for printing (A4 landscape, 1920x1080, 300 DPI)
   - Filename: `DeltaCrown_Certificate_TeamAlpha_2025.pdf`
   - **Analytics:** `data-analytics-id="certificate_download_pdf"`

2. **Share on Social** (expandable dropdown)
   
   **Facebook:**
   - Pre-filled post: "🏆 We won 1st Place at DeltaCrown Valorant Cup 2025! ৳25,000 prize 🎉 #DeltaCrown #VALORANT #Esports"
   - Auto-generates OG image (certificate thumbnail)
   - Link: Certificate verification URL
   - **Analytics:** `data-analytics-id="certificate_share_facebook"`
   
   **Twitter:**
   - Pre-filled tweet: "🥇 Champions! Just won @DeltaCrown Valorant Cup 2025! ৳25,000 prize pool 🔥 [Certificate Link] #DeltaCrown #VALORANTEsports"
   - Twitter Card with certificate preview
   - Character count: 280 limit respected
   - **Analytics:** `data-analytics-id="certificate_share_twitter"`
   
   **LinkedIn:**
   - Professional post: "Proud to announce our team secured 1st place at DeltaCrown Valorant Cup 2025, competing against 32 teams. This achievement reflects our dedication to competitive gaming excellence."
   - Certificate image attachment
   - **Analytics:** `data-analytics-id="certificate_share_linkedin"`
   
   **Instagram Story:**
   - Opens Instagram app (mobile) or web (desktop)
   - Pre-formatted story template with certificate
   - Stickers: "🏆 Winner", "@deltacrown", "#VALORANT"
   - **Analytics:** `data-analytics-id="certificate_share_instagram"`
   
   **Copy Link:**
   - Copies certificate URL to clipboard
   - Toast notification: "Link copied! Share it anywhere"
   - URL format: `deltacrown.gg/certificates/ABC123`
   - **Analytics:** `data-analytics-id="certificate_copy_link"`

3. **Verify Certificate**
   - Opens public verification page (`/verify/<hash>`)
   - Shows authenticity indicators
   - QR code visible for physical certificate verification
   - **Analytics:** `data-analytics-id="certificate_verify_click"`

**Public Verification Page:**

**URL:** `/verify/<hash>` (e.g., `/verify/e7a4b9c2d1f5`)

**Layout:**

```
┌────────────────────────────────────────────────────────┐
│ Certificate Verification                                │
├────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────┐ │
│ │  ✓ VERIFIED DELTACROWN CERTIFICATE                 │ │  ← Green banner
│ │  This certificate is authentic and issued by       │ │
│ │  DeltaCrown Tournament Engine                      │ │
│ └────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────┤
│ Certificate Details                                     │
│  ┌──────────────────────────┬──────────────────────┐   │
│  │ Certificate ID:          │ CERT-ABC123          │   │
│  │ Issued To:               │ Team Alpha           │   │
│  │ Achievement:             │ 🥇 1st Place         │   │
│  │ Tournament:              │ DeltaCrown Valorant  │   │
│  │                          │ Cup 2025             │   │
│  │ Organizer:               │ DeltaCrown eSports   │   │
│  │ Prize:                   │ ৳25,000              │   │
│  │ Date:                    │ December 15, 2025    │   │
│  │ Issued On:               │ Dec 16, 2025 2:30 PM │   │
│  │ Verification Hash:       │ e7a4b9c2d1f5a3b8     │   │
│  └──────────────────────────┴──────────────────────┘   │
├────────────────────────────────────────────────────────┤
│ Security Indicators                                     │
│  ✓ Certificate matches DeltaCrown records              │
│  ✓ Tournament organizer verified                       │
│  ✓ Issued within 48 hours of tournament completion     │
│  ✓ QR code matches hash                                │
├────────────────────────────────────────────────────────┤
│ [View Full Certificate] [Download PDF] [Report Issue]  │
└────────────────────────────────────────────────────────┘
```

**Verification Features:**
- **QR Code Integration:** Scan QR on physical certificate → auto-redirects to `/verify/<hash>`
- **Security Indicators:**
  - ✓ Certificate matches DeltaCrown records
  - ✓ Tournament organizer verified account
  - ✓ Issued within reasonable timeframe
  - ✓ Hash integrity check passed
- **Verification Hash:** Unique, tamper-proof identifier (SHA-256 of certificate data)
- **Blockchain Future-Proofing:** Hash stored for future blockchain verification
- **Invalid Certificate Handling:**
  ```
  ✗ INVALID CERTIFICATE
  This certificate ID does not exist in our records or has been revoked.
  [Report Fake Certificate] [Contact Support]
  ```
- **Revoked Certificate:**
  ```
  ⚠️ CERTIFICATE REVOKED
  This certificate was revoked by the tournament organizer.
  Reason: [Organizer's reason]
  Revoked On: [Date]
  ```
- **Expired Link (if > 5 years old):**
  ```
  ℹ️ ARCHIVED CERTIFICATE
  This certificate is from [Date]. Records are archived but authenticity is confirmed.
  [View Archived Details]
  ```

**Reporting Mechanism:**
- **"Report Fake Certificate"** button (if user suspects forgery)
- Opens form:
  - Reason for report (dropdown: Forged, Altered, Duplicate, Other)
  - Additional details (textarea)
  - Upload suspicious certificate image (optional)
  - Reporter email (for follow-up)
- Submission creates moderation ticket for DeltaCrown staff review

---

### Organizer Certificate Issuance (Organizer Dashboard)

**After Tournament Completion:**

New action in organizer dashboard: **"Issue Certificates"** button

**Certificate Issuance Workflow:**

1. **Eligible Recipients** (auto-populated)

---

**Navigation:**
- [← Previous: PART_4.3 - Tournament Management Screens](PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md)
- [→ Next: PART_4.5 - Bracket Match & Player Experience](PART_4.5_BRACKET_MATCH_PLAYER_EXPERIENCE.md)
- [↑ Back to Index](INDEX_MASTER_NAVIGATION.md)
