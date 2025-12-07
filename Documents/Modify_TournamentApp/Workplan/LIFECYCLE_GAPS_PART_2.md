# Part 2: Tournament Lifecycle Gaps Analysis

**Document Purpose**: Define the ideal tournament lifecycle and identify what DeltaCrown has vs. what's missing.

**Created**: December 8, 2025  
**Scope**: End-to-end tournament flow analysis, gap identification

---

## 1. Lifecycle Overview

### 1.1 Complete Tournament Lifecycle (6 Stages)

```
┌─────────────────────────────────────────────────────────────────────┐
│ STAGE 1: DISCOVERY & BROWSING                                      │
│  User finds tournaments → Filters by game/format → Views details   │
└────────────────────┬────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────────┐
│ STAGE 2: REGISTRATION & PAYMENT                                    │
│  Eligibility check → Fill form → Submit payment → Confirmation     │
└────────────────────┬────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────────┐
│ STAGE 3: BRACKET & SEEDING                                         │
│  Registration closes → Generate bracket → Seed teams → Publish     │
└────────────────────┬────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────────┐
│ STAGE 4: MATCH OPERATIONS                                          │
│  Schedule → Check-in → Lobby info → Play → Report result → Verify  │
└────────────────────┬────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────────┐
│ STAGE 5: TOURNAMENT COMPLETION                                     │
│  Final match → Determine winner → Distribute prizes → Certificates │
└────────────────────┬────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────────────┐
│ STAGE 6: POST-TOURNAMENT STATS & HISTORY                           │
│  Update stats → Update rankings → Store history → Show on profile  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Stage 1: Discovery & Browsing

### 2.1 Ideal Capabilities

**What a top-tier system should have**:

1. **Browse & Search**:
   - List all upcoming tournaments (paginated, sorted)
   - Filter by: game, format, entry fee, status, region, date range
   - Search by tournament name or organizer
   - Quick filters: "Free tournaments", "Starting soon", "High prizes"

2. **Tournament Preview**:
   - Tournament card showing: game, format, prize pool, entry fee, participant count, dates
   - Visual badges: "Featured", "Full", "Registration Open", "Live"
   - Quick actions: "Register Now", "View Bracket", "Spectate"

3. **Tournament Detail Page**:
   - Full details: rules, format, schedule, prizes, requirements
   - Tabs: Overview, Bracket, Participants, Matches, Rules
   - Live participant count: "45/64 slots filled"
   - Registration deadline countdown: "Closes in 3 days 4 hours"

4. **Notifications & Alerts**:
   - "Registration opens soon" reminders
   - "Last day to register" alerts
   - "Tournament starting soon" notifications
   - Email/Discord/in-app delivery

---

### 2.2 DeltaCrown Current State

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Browse tournaments list** | ✅ **EXISTS** | `apps/tournaments/views/tournament_list.py` | Basic listing view |
| **Filter by game/status** | ✅ **EXISTS** | Query params in views | Basic filtering |
| **Search by name** | ✅ **EXISTS** | Search functionality | Text search |
| **Tournament detail page** | ✅ **EXISTS** | `tournament_detail.html` | Comprehensive details |
| **Participant count display** | ✅ **EXISTS** | Template shows registration count | Live count |
| **Registration deadline** | ✅ **EXISTS** | `registration_deadline` field | Date field exists |
| **Countdown timer** | ❌ **MISSING** | No JS countdown | Static date display only |
| **Visual badges (Featured, Full)** | ⚠️ **PARTIAL** | Status badges exist, not "Featured" | No featured flag |
| **Quick actions on cards** | ⚠️ **PARTIAL** | Register button exists | No "Spectate" or "View Bracket" quick links |
| **Filter by entry fee range** | ❌ **MISSING** | No price range filter | Only game/status filters |
| **Filter by region** | ❌ **MISSING** | No region field in Tournament model | All tournaments global |
| **"Starting soon" filter** | ❌ **MISSING** | No date-based filter | Manual date search only |
| **Registration reminder notifications** | ❌ **MISSING** | No scheduled notifications | Users must check manually |
| **Email alerts for registration** | ❌ **MISSING** | No email integration | Only in-app notifications |
| **Discord integration** | ❌ **MISSING** | No Discord bot/webhooks | Future feature |

---

### 2.3 Key Gaps - Stage 1

**Must-Add Features**:
1. ❌ **Registration deadline countdown** (client-side JS timer)
2. ❌ **Featured tournaments flag** (promote important tournaments)
3. ❌ **Email notifications** (registration opens/closes reminders)
4. ❌ **Quick "View Bracket" link** on tournament cards

**Nice-to-Have** (lower priority):
- Filter by entry fee range (slider: $0 - $100)
- Filter by region/timezone
- Discord integration (post tournament announcements)

---

## 3. Stage 2: Registration & Payment

### 3.1 Ideal Capabilities

**What a top-tier system should have**:

1. **Eligibility Validation**:
   - Pre-registration eligibility check (before form display)
   - Clear pass/fail with specific reasons: "Minimum rank: Diamond (you are Gold)"
   - Check: age, game rank, region, verified account, team size, already registered

2. **Smart Registration Form**:
   - Auto-fill from UserProfile and Team (verified fields locked)
   - Unique registration number assigned: `VCT-2025-001234`
   - Draft persistence (resume on different device)
   - Real-time validation (field-level API checks)
   - Progress indicator (% complete)

3. **Payment Processing**:
   - Multiple payment methods:
     - DeltaCoin (instant, preferred)
     - Manual upload (proof of payment → admin approval)
     - Payment gateway (future: Stripe, PayPal)
   - Instant confirmation for DeltaCoin
   - PENDING status for manual uploads
   - Idempotent payment (no double-charging)

4. **Confirmation & Next Steps**:
   - Show registration number prominently
   - Email confirmation with:
     - Registration details
     - Payment receipt
     - Tournament schedule (.ics calendar invite)
     - Check-in instructions
   - Add to "My Tournaments" dashboard
   - Show countdown to tournament start

---

### 3.2 DeltaCrown Current State

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Eligibility check (age)** | ✅ **EXISTS** | `RegistrationEligibilityService` | Age validation |
| **Eligibility check (already registered)** | ✅ **EXISTS** | Duplicate check exists | Prevents re-registration |
| **Eligibility check (team size)** | ✅ **EXISTS** | Team member count validation | For team tournaments |
| **Game-specific eligibility (rank)** | ❌ **MISSING** | No rank validation | All ranks allowed |
| **Region/server lock** | ❌ **MISSING** | No region field | No region restrictions |
| **Verified account requirement** | ❌ **MISSING** | No verification check | Unverified users can register |
| **Auto-fill from UserProfile** | ✅ **EXISTS** | `reg_wizard.js` auto-fills fields | 7 games supported |
| **Auto-fill from Team** | ✅ **EXISTS** | Team name, captain, members | For team tournaments |
| **Field locking (verified fields)** | ❌ **MISSING** | All fields editable | Email/game IDs can be changed |
| **Unique registration number** | ❌ **MISSING** | No reg number field | Uses auto-increment ID only |
| **Draft persistence** | ❌ **MISSING** | Session-only wizard data | Lost on session expire |
| **Cross-device resume** | ❌ **MISSING** | No UUID-based drafts | No resume capability |
| **Real-time validation** | ⚠️ **PARTIAL** | Client-side only | No API validation endpoints |
| **Progress indicator** | ✅ **EXISTS** | Step 1/3, 2/3, 3/3 shown | Visual wizard steps |
| **DeltaCoin payment** | ✅ **EXISTS** | `EconomyService` integration | Instant deduction |
| **Manual payment upload** | ✅ **EXISTS** | Proof image upload | Admin approval required |
| **Payment idempotency** | ⚠️ **PARTIAL** | Basic checks exist | No idempotency keys |
| **Email confirmation** | ❌ **MISSING** | No email service | Only in-app notification |
| **Calendar invite (.ics)** | ❌ **MISSING** | No .ics generation | Users add manually |
| **"My Tournaments" dashboard** | ✅ **EXISTS** | User dashboard shows registrations | Basic list view |
| **Payment receipt** | ❌ **MISSING** | No receipt generation | Only transaction log |

---

### 3.3 Key Gaps - Stage 2

**Must-Add Features**:
1. ❌ **Unique registration number** (format: `{GAME}-{YEAR}-{SEQUENCE}`)
2. ❌ **Field locking** (lock verified email, phone, game IDs)
3. ❌ **Email confirmation** (registration details + payment receipt)
4. ❌ **Draft persistence** (database-backed, UUID-based)
5. ❌ **Configurable eligibility rules** (rank, region, verification status)

**Nice-to-Have**:
- Real-time API validation (field-level)
- Calendar invite (.ics file)
- Payment gateway integration (Stripe)

---

## 4. Stage 3: Bracket & Seeding

### 4.1 Ideal Capabilities

**What a top-tier system should have**:

1. **Automatic Bracket Generation**:
   - Trigger: Registration deadline passes or organizer clicks "Generate Bracket"
   - Supports: Single Elimination, Double Elimination, Round Robin, Swiss
   - Auto-seed based on:
     - Random (default)
     - Rank/ELO (competitive)
     - Custom seed order (organizer input)

2. **Bracket Customization**:
   - Organizer can manually adjust seeds before publishing
   - Swap participants between bracket positions
   - Add/remove participants (if slots unfilled)
   - Preview bracket before finalizing

3. **Bracket Publishing**:
   - Publish bracket → All participants notified
   - Bracket viewable by:
     - Participants (see own matches)
     - Spectators (public view)
     - Organizer (edit/manage)
   - First-round matches auto-scheduled based on tournament start time

4. **Bracket Visualization**:
   - Interactive bracket tree (click match → see details)
   - Show match status: Scheduled, Live, Completed
   - Show scores on completed matches
   - Highlight winner path to championship
   - Mobile-friendly (collapse/expand rounds)

---

### 4.2 DeltaCrown Current State

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Bracket generation (Single Elim)** | ✅ **EXISTS** | `BracketService.generate_bracket()` | Single elimination only |
| **Bracket generation (Double Elim)** | ⚠️ **PARTIAL** | Code exists but untested | May have bugs |
| **Bracket generation (Round Robin)** | ⚠️ **PARTIAL** | Code exists but untested | May have bugs |
| **Bracket generation (Swiss)** | ❌ **MISSING** | No Swiss format support | Single/Double only |
| **Auto-seeding (random)** | ✅ **EXISTS** | Default seeding is random | Works |
| **Auto-seeding (by rank/ELO)** | ❌ **MISSING** | No ranking-based seeding | Random only |
| **Manual seed adjustment** | ❌ **MISSING** | No seed editor UI | Auto-generated only |
| **Swap participants in bracket** | ❌ **MISSING** | No drag-and-drop UI | No manual adjustments |
| **Preview before publish** | ❌ **MISSING** | Bracket published immediately | No preview step |
| **Bracket publish notification** | ⚠️ **PARTIAL** | In-app notification exists | No email notification |
| **Bracket visualization** | ✅ **EXISTS** | `bracket_view.html` template | Tree view exists |
| **Interactive bracket (click match)** | ⚠️ **PARTIAL** | Match details page exists | Not in-bracket modal |
| **Match status badges** | ✅ **EXISTS** | Scheduled/Live/Completed shown | Color-coded |
| **Show scores on bracket** | ✅ **EXISTS** | Completed matches show scores | Visible |
| **Winner path highlight** | ❌ **MISSING** | No visual winner path | No highlighting |
| **Mobile-friendly bracket** | ⚠️ **PARTIAL** | Responsive but not optimized | Horizontal scroll issues |
| **Auto-schedule first-round** | ⚠️ **PARTIAL** | Matches created, no times | `scheduled_time` is NULL |

---

### 4.3 Key Gaps - Stage 3

**Must-Add Features**:
1. ❌ **Auto-schedule first-round matches** (set `scheduled_time` based on tournament start)
2. ❌ **Bracket preview + edit** (organizer approval before publish)
3. ❌ **Bracket publish email notification** (notify all participants)
4. ❌ **Ranking-based seeding** (seed by ELO/rank, not random)

**Nice-to-Have**:
- Swiss format support
- Manual seed adjustment UI (drag-and-drop)
- Winner path highlighting on bracket
- Mobile-optimized bracket (collapse/expand)

---

## 4A. Manual Tournament Management Capabilities

### 4A.1 Overview

DeltaCrown must support **both automated and manual tournament management** to give organizers full control over every aspect of their tournaments. While automation handles common cases, manual overrides are essential for:
- Correcting mistakes (wrong seeds, bracket errors)
- Handling edge cases (last-minute dropouts, disputes)
- Customizing tournament structure (non-standard formats)
- Managing complex multi-stage tournaments

---

### 4A.2 Manual Team Placement & Bracket Creation

**Ideal Capabilities**:

1. **Manual Bracket Creation**:
   - Organizer can create bracket from scratch (no auto-generation)
   - Drag-and-drop participants into bracket positions
   - Create custom bracket structures (non-standard round counts)
   - Set byes for specific seeds manually
   - Create asymmetric brackets (different branch sizes)

2. **Bracket Override & Editing**:
   - After auto-generation, edit any aspect:
     - Swap participants between matches
     - Replace participant (if withdrawal/substitution)
     - Remove match (if bye needed)
     - Split/merge bracket branches
   - Real-time preview of changes
   - Undo/redo capability
   - Validate bracket integrity before publishing

3. **Manual Team Placement**:
   - Place teams into specific bracket positions
   - Override auto-seeding (1st seed doesn't have to be position 1)
   - Create balanced brackets (separate strong teams intentionally)
   - Handle special requests (rival teams in opposite brackets)

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Manual bracket creation** | ❌ **MISSING** | Auto-generation only | No UI to create from scratch |
| **Drag-and-drop bracket editor** | ❌ **MISSING** | No interactive editor | Bracket is read-only after generation |
| **Swap participants in bracket** | ❌ **MISSING** | No swap functionality | Would require BracketEditService |
| **Replace participant** | ❌ **MISSING** | No substitution flow | Manual DB edit only |
| **Remove match/assign bye** | ❌ **MISSING** | No bye assignment UI | Auto-calculated only |
| **Bracket validation** | ⚠️ **PARTIAL** | Basic validation exists | No comprehensive checks |
| **Bracket edit undo/redo** | ❌ **MISSING** | No edit history | Changes are immediate/permanent |
| **Bracket integrity checks** | ❌ **MISSING** | No validation service | Can create invalid brackets |

**Gap Priority**: **HIGH** - Organizers need manual control for professional tournaments.

---

### 4A.3 Manual Group Assignment & Editing

**Ideal Capabilities**:

1. **Group Stage Setup**:
   - Create custom number of groups (2, 4, 8, etc.)
   - Name groups (Group A, North America, Challengers, etc.)
   - Set max participants per group
   - Define advancement rules (top 2 advance, top 4 advance)

2. **Manual Group Assignment**:
   - Assign participants to specific groups
   - Drag-and-drop between groups
   - Swap participants between groups
   - Auto-balance groups (equal participant count)
   - Seeded distribution (1st seed → Group A, 2nd → Group B, etc.)

3. **Group Editing**:
   - Rename groups mid-tournament
   - Merge/split groups if needed
   - Adjust group sizes
   - Rebalance if participants withdraw

4. **Group-to-Knockout Transition**:
   - Auto-advance top N from each group to knockout bracket
   - Manual override advancement (if tiebreaker needed)
   - Seeding for knockout based on group standings
   - Cross-group matchups (Group A #1 vs Group B #2)

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Group creation** | ⚠️ **PARTIAL** | `TournamentGroup` model exists | No UI for creation |
| **Group assignment** | ❌ **MISSING** | No assignment service | Groups exist but unused |
| **Manual assignment UI** | ❌ **MISSING** | No drag-and-drop | No group assignment interface |
| **Auto-balance groups** | ❌ **MISSING** | No balancing algorithm | Manual assignment only |
| **Seeded distribution** | ❌ **MISSING** | No snake draft algorithm | Random would be only option |
| **Group editing** | ❌ **MISSING** | No edit UI | Created groups are immutable |
| **Group advancement logic** | ❌ **MISSING** | No standings calculation | No group→knockout transition |
| **Tiebreaker handling** | ❌ **MISSING** | No tiebreaker system | Undefined behavior |

**Gap Priority**: **MEDIUM** - Essential for World Cup-style tournaments (Group Stage → Playoffs).

---

### 4A.4 Manual Scheduling Controls

**Ideal Capabilities**:

1. **Match Time Setting**:
   - Set specific start time for each match
   - Bulk schedule (set all Round 1 matches at same time)
   - Staggered scheduling (Round 1: Match 1 at 2 PM, Match 2 at 3 PM, etc.)
   - Recurring time slots (every match on the hour)

2. **Round Scheduling**:
   - Set round start times manually
   - Define interval between rounds (Round 2 starts 2 hours after Round 1 completes)
   - Override auto-scheduling (if algorithm doesn't fit)
   - Adjust for delays (push entire tournament back 30 mins)

3. **Calendar Integration**:
   - Visual calendar view (drag matches to time slots)
   - Conflict detection (same team in 2 matches at same time)
   - Time zone handling (display in participant's local time)
   - Export to Google Calendar, iCal

4. **Rescheduling**:
   - Organizer can reschedule any match
   - Participants can request reschedule (admin approval)
   - Reschedule reason logged (for transparency)
   - Participants notified of time change

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Manual match time setting** | ❌ **MISSING** | No scheduling UI | `scheduled_time` always NULL |
| **Bulk scheduling** | ❌ **MISSING** | No bulk schedule service | Per-match edit only |
| **Staggered scheduling** | ❌ **MISSING** | No algorithm | Would need MatchSchedulingService |
| **Round start times** | ❌ **MISSING** | No round-level scheduling | Match-level only |
| **Calendar view** | ❌ **MISSING** | No calendar UI | List view only |
| **Conflict detection** | ❌ **MISSING** | No validation | Can schedule overlapping matches |
| **Time zone display** | ❌ **MISSING** | UTC only | No user-specific timezone |
| **Reschedule functionality** | ❌ **MISSING** | No reschedule service | Would need edit + notification |
| **Reschedule requests** | ❌ **MISSING** | No participant request flow | Organizer-only |
| **Export to calendar** | ❌ **MISSING** | No iCal export | Manual copy only |

**Gap Priority**: **HIGH** - Match scheduling is critical for tournament operations.

---

### 4A.5 Manual Result Submission & Override

**Ideal Capabilities**:

1. **Organizer Result Entry**:
   - Organizer can enter results directly (bypass player submission)
   - Select winner, enter scores
   - Upload proof on behalf of participants
   - Reason field (why organizer entered result)

2. **Result Override**:
   - Override existing result (if error or dispute resolved)
   - Reverse match outcome (if incorrect winner recorded)
   - Update scores (if typo in original submission)
   - Override reason logged (audit trail)
   - Previous result stored (rollback capability)

3. **Bulk Result Entry**:
   - Enter multiple match results at once (for offline tournaments)
   - CSV import (match_id, winner, score)
   - Validate before applying (check for errors)
   - Preview results before finalizing

4. **Result Verification Workflow**:
   - Participant submits result → Organizer reviews → Approve/Reject
   - Approval confirms result, advances winner
   - Rejection sends back to participants for re-submission
   - Reason for rejection communicated to participants

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Organizer result entry** | ❌ **MISSING** | No admin result form | Players only |
| **Result override** | ❌ **MISSING** | No override service | Once set, permanent |
| **Override audit trail** | ❌ **MISSING** | No logging | No history of changes |
| **Reverse match outcome** | ❌ **MISSING** | No reversal logic | Would break bracket progression |
| **Bulk result entry** | ❌ **MISSING** | No bulk upload | Per-match only |
| **CSV import** | ❌ **MISSING** | No import functionality | Manual entry only |
| **Result verification workflow** | ❌ **MISSING** | No review queue | Auto-approval on submission |
| **Approval/rejection** | ❌ **MISSING** | No admin approval UI | Results immediately final |

**Gap Priority**: **CRITICAL** - Organizers need control over results for dispute resolution.

---

### 4A.6 Role-Based Actions

**Ideal Capabilities**:

1. **Organizer Role**:
   - Full control over tournament (create, edit, delete)
   - Manage registrations (approve, reject, refund)
   - Edit bracket (swap, override)
   - Enter/override results
   - Manage schedule
   - Access audit logs
   - Appoint staff/referees

2. **Staff Role** (Organizer delegates):
   - View tournament dashboard
   - Approve payments
   - Verify match results
   - Reschedule matches
   - Cannot delete tournament or edit core settings

3. **Referee Role** (Match officials):
   - Assigned to specific matches
   - Enter match results
   - Resolve disputes
   - View lobby info
   - Cannot edit bracket or schedule

4. **Participant Role** (Players/Teams):
   - View tournament details, bracket
   - Register/withdraw
   - Submit match results
   - Dispute results
   - View own stats

5. **Spectator Role** (Public):
   - View tournament details
   - View bracket (read-only)
   - View live matches
   - Cannot submit results or access admin features

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Organizer role** | ✅ **EXISTS** | `tournament.organizer` field | Full control |
| **Staff role** | ❌ **MISSING** | No staff model | Organizer only |
| **Referee role** | ❌ **MISSING** | No referee system | No match officials |
| **Participant role** | ✅ **EXISTS** | Registration system | Basic participant permissions |
| **Spectator role** | ✅ **EXISTS** | Public tournament views | Read-only access |
| **Permission system** | ⚠️ **PARTIAL** | Django permissions exist | Not granular per tournament |
| **Delegate staff** | ❌ **MISSING** | No delegation mechanism | Organizer must do everything |
| **Referee assignment** | ❌ **MISSING** | No match officials | No per-match staff |
| **Role-based UI** | ⚠️ **PARTIAL** | Organizer sees edit buttons | Not comprehensive |
| **Audit logs per role** | ❌ **MISSING** | No role tracking in logs | Can't see who did what |

**Gap Priority**: **MEDIUM** - Important for large tournaments with multiple staff members.

---

## 4B. Results Pipeline (No Game API Reality)

### 4B.1 Overview

DeltaCrown operates in a **no direct game API integration** reality. Unlike platforms with official API access (Riot Games API, Steam API), DeltaCrown cannot automatically fetch match results. Instead, results flow through a **manual submission → verification → propagation** pipeline.

**Core Principle**: Trust but verify. Users submit results with proof, organizers verify, system propagates.

---

### 4B.2 Result Submission by Users/Teams

**Workflow**:

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Match Completion (Off-Platform)                         │
│  Teams play match in-game → One team wins → Match ends          │
└────────────────────┬─────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────┐
│ STEP 2: Result Submission (Platform)                            │
│  Winner or loser navigates to match page                        │
│  Clicks "Submit Result"                                          │
│  Fills form:                                                     │
│    - Select winner (Team A or Team B)                            │
│    - Enter scores (13-7)                                         │
│    - Upload proof screenshot (scoreboard image)                  │
│    - Optional: Add notes (GG, close match, etc.)                 │
│  Submits form → MatchResultSubmission record created             │
└────────────────────┬─────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────┐
│ STEP 3: Opponent Notification                                   │
│  Opponent receives notification:                                │
│    "Team A submitted match result. Please confirm or dispute."  │
│  Opponent views submission (winner, scores, proof)               │
│  Opponent has 3 options:                                         │
│    1. Confirm → Match result finalized                           │
│    2. Dispute → Escalate to organizer                            │
│    3. Ignore → Auto-confirm after 24 hours                       │
└──────────────────────────────────────────────────────────────────┘
```

**Submission Form Fields**:
- **Winner**: Radio buttons (Team A / Team B)
- **Scores**: Number inputs (Team A score, Team B score)
- **Map/Mode** (if applicable): Dropdown (Ascent, Bind, etc.)
- **Proof Screenshot**: File upload (required, image only, max 5MB)
- **Additional Notes**: Text area (optional)

**Validation Rules**:
- Winner must match scores (if Team A won, Team A score > Team B score)
- Scores must be valid for game type (Valorant: 0-13, PUBG: placement 1-16)
- Screenshot required (no submission without proof)
- Submitter must be participant in match

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Result submission form** | ✅ **EXISTS** | `submit_result.html` | Basic form exists |
| **Winner selection** | ✅ **EXISTS** | Radio buttons in form | Works |
| **Score entry** | ✅ **EXISTS** | Score inputs | Works |
| **Proof upload** | ✅ **EXISTS** | File upload field | Uploads to S3 |
| **Validation** | ⚠️ **PARTIAL** | Basic validation exists | No game-specific rules |
| **Opponent notification** | ❌ **MISSING** | No notification sent | Opponent must check manually |
| **MatchResultSubmission model** | ❌ **MISSING** | Results go directly to Match | No submission queue |

**Gap Priority**: **CRITICAL** - Need proper submission → review → finalize workflow.

---

### 4B.3 Opponent Confirmation/Dispute

**Confirmation Workflow**:

```
┌──────────────────────────────────────────────────────────────────┐
│ Opponent receives notification with link to result submission    │
│  "Team A submitted result: Team A won 13-7. Review now."        │
└────────────────────┬─────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────┐
│ Opponent views submission details:                              │
│  - Claimed winner: Team A                                        │
│  - Scores: 13-7                                                  │
│  - Proof: [View screenshot]                                      │
│  - Submitted by: PlayerX (Team A captain)                        │
│  - Submitted at: Dec 8, 2025 2:45 PM                             │
└────────────────────┬─────────────────────────────────────────────┘
                     │
           ┌─────────┴─────────┐
           │                   │
           ▼                   ▼
    ┌─────────────┐     ┌─────────────┐
    │  CONFIRM    │     │  DISPUTE    │
    └──────┬──────┘     └──────┬──────┘
           │                   │
           ▼                   ▼
┌──────────────────┐   ┌──────────────────────────┐
│ Match.state =    │   │ Create DisputeRecord     │
│ COMPLETED        │   │ Status = DISPUTED        │
│ Winner set       │   │ Escalate to organizer    │
│ Advance to next  │   │ Match.state = DISPUTED   │
│ Publish event    │   │ Notify organizer         │
└──────────────────┘   └──────────────────────────┘
```

**Dispute Workflow**:

```
┌──────────────────────────────────────────────────────────────────┐
│ Opponent clicks "Dispute Result"                                │
│  Form appears:                                                   │
│    - Reason: Dropdown (Incorrect score, Fake proof, Cheating)   │
│    - Explanation: Text area (required, min 50 chars)             │
│    - Counter-proof: File upload (optional, recommended)          │
│  Submits dispute → DisputeRecord created                         │
└────────────────────┬─────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────┐
│ Organizer receives notification:                                │
│  "Match #123 has a disputed result. Review required."           │
│  Organizer navigates to dispute review page                      │
│  Views both submissions:                                         │
│    - Original submission (Team A: won 13-7, proof)               │
│    - Dispute (Team B: claims 13-7 loss is wrong, counter-proof) │
│  Organizer makes decision:                                       │
│    - Approve original → Team A wins                              │
│    - Approve dispute → Team B wins (or rematch)                  │
│    - Request more info → Ask both teams for clarification        │
└────────────────────┬─────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────┐
│ Organizer decision applied:                                      │
│  - Match.winner set to correct team                              │
│  - DisputeRecord.status = RESOLVED                               │
│  - DisputeRecord.resolution = "Organizer decision: ..."          │
│  - Both teams notified of final decision                         │
│  - Match progresses (winner advances)                            │
└──────────────────────────────────────────────────────────────────┘
```

**Auto-Confirmation**:
- If opponent doesn't respond within 24 hours → Auto-confirm
- Notification sent: "You didn't respond. Result auto-confirmed."
- Prevents indefinite blocking (malicious non-response)

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Opponent confirmation** | ❌ **MISSING** | No confirmation flow | Results immediately final |
| **Dispute submission** | ⚠️ **PARTIAL** | Dispute model exists | No dispute UI |
| **Dispute review UI** | ❌ **MISSING** | No organizer review page | Manual resolution only |
| **Counter-proof upload** | ❌ **MISSING** | No field in dispute form | Text-only disputes |
| **Auto-confirmation** | ❌ **MISSING** | No timeout logic | Infinite wait possible |
| **Dispute resolution logging** | ❌ **MISSING** | No resolution field | No decision record |
| **Notification on dispute** | ❌ **MISSING** | No organizer alert | Organizer must check manually |

**Gap Priority**: **CRITICAL** - Without confirmation/dispute flow, result accuracy cannot be ensured.

---

### 4B.4 Organizer Verification via Results Inbox

**Results Inbox Concept**:

A centralized queue where organizers review all pending match results before finalizing.

**Inbox View**:

```
┌──────────────────────────────────────────────────────────────────┐
│ RESULTS INBOX (5 pending)                                        │
├──────────────────────────────────────────────────────────────────┤
│ Filters: [ All ] [ Pending ] [ Conflicted ] [ Approved ]        │
├──────────────────────────────────────────────────────────────────┤
│ Match #45: Team Alpha vs Team Beta (Pending)                    │
│  Submitted by: PlayerX (Team Alpha)                              │
│  Claimed winner: Team Alpha (13-7)                               │
│  Proof: [View screenshot]                                        │
│  Opponent status: Awaiting confirmation                          │
│  [Approve] [Reject] [View Details]                               │
├──────────────────────────────────────────────────────────────────┤
│ Match #46: Team Gamma vs Team Delta (CONFLICTED) ⚠️             │
│  Submission 1: PlayerY claims Team Gamma won 13-10               │
│  Submission 2: PlayerZ claims Team Delta won 13-10               │
│  Both teams submitted different results!                         │
│  [View Conflict] [Resolve]                                       │
├──────────────────────────────────────────────────────────────────┤
│ Match #47: Team Echo vs Team Foxtrot (Pending)                  │
│  Submitted by: PlayerA (Team Echo)                               │
│  Claimed winner: Team Echo (forfeit - opponent no-show)          │
│  Proof: [No screenshot - forfeit claim]                          │
│  [Approve Forfeit] [Reject] [Contact Opponent]                   │
└──────────────────────────────────────────────────────────────────┘
```

**Inbox Features**:
1. **Pending Results**: All submissions awaiting organizer approval
2. **Conflicted Results**: Both teams submitted different winners (priority)
3. **Auto-Verified**: Results confirmed by opponent (review optional)
4. **Approved**: Results organizer has approved (historical)
5. **Rejected**: Results organizer rejected (with reason)

**Approval Actions**:
- **Approve**: Finalize result, advance winner, publish event
- **Reject**: Send back to participants with reason
- **Request More Info**: Ask for additional proof or clarification

**Conflict Resolution**:
- View both submissions side-by-side
- Compare proof screenshots
- Make judgment call (which submission is correct)
- Enter final result manually if neither is correct
- Log decision reason

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Results inbox** | ❌ **MISSING** | No inbox view | Results auto-finalize |
| **Pending queue** | ❌ **MISSING** | No submission queue model | Direct to Match table |
| **Conflict detection** | ❌ **MISSING** | No duplicate submission check | Last submission wins |
| **Side-by-side comparison** | ❌ **MISSING** | No comparison UI | Manual checking only |
| **Approval workflow** | ❌ **MISSING** | No approve/reject service | Auto-approval |
| **Rejection reason** | ❌ **MISSING** | No rejection message | No feedback to participants |
| **Request more info** | ❌ **MISSING** | No communication flow | Binary approve/reject |
| **Decision logging** | ❌ **MISSING** | No audit trail | No record of organizer actions |

**Gap Priority**: **CRITICAL** - Results inbox is core to tournament integrity without game APIs.

---

### 4B.5 Dispute Resolution Integration with TournamentOps

**TournamentOps Orchestration**:

```python
# tournament_ops/services/result_verification_service.py
class ResultVerificationService:
    """Orchestrate result submission → verification → finalization."""
    
    @staticmethod
    @transaction.atomic
    def approve_result(submission_id: int, admin_user_id: int) -> Match:
        """
        Approve submitted result and finalize match.
        
        Workflow:
        1. Get submission
        2. Validate result (scores match winner, proof exists)
        3. Apply result to Match
        4. Mark submission as approved
        5. Reject conflicting submissions
        6. Publish MatchCompletedEvent
        7. Advance winner to next round
        8. Send notifications
        """
        submission = MatchResultSubmission.objects.get(id=submission_id)
        
        # Apply result
        match = ResultManagementService.enter_result_manual(
            match_id=submission.match_id,
            winner_id=submission.claimed_winner_id,
            scores=submission.scores,
            admin_user_id=admin_user_id,
            reason=f"Approved submission from {submission.submitted_by.username}"
        )
        
        # Mark approved
        submission.status = 'approved'
        submission.reviewed_by_id = admin_user_id
        submission.reviewed_at = timezone.now()
        submission.save()
        
        # Reject conflicts
        MatchResultSubmission.objects.filter(
            match=submission.match,
            status__in=['pending', 'conflicted']
        ).exclude(id=submission.id).update(
            status='rejected',
            reviewed_by_id=admin_user_id,
            reviewed_at=timezone.now(),
            review_notes='Conflicting submission rejected'
        )
        
        # Publish event
        EventBus.publish(MatchCompletedEvent(
            match_id=match.id,
            tournament_id=match.tournament_id,
            winner_id=match.winner_id,
            loser_id=get_loser_id(match),
            scores=match.scores
        ))
        
        # Advance winner
        if match.next_match_id:
            BracketService.advance_winner(match.id)
        
        # Notify participants
        NotificationService.send_result_approved(match.id)
        
        return match
    
    @staticmethod
    @transaction.atomic
    def resolve_dispute(
        dispute_id: int,
        admin_user_id: int,
        decision: str,  # 'approve_original', 'approve_dispute', 'rematch'
        resolution_notes: str
    ):
        """
        Resolve disputed result.
        
        Decisions:
        - approve_original: Original submission was correct
        - approve_dispute: Disputer was correct (override original)
        - rematch: Both submissions invalid, order rematch
        """
        dispute = DisputeRecord.objects.get(id=dispute_id)
        match = dispute.match
        
        if decision == 'approve_original':
            # Original submission wins
            ResultVerificationService.approve_result(
                dispute.original_submission_id,
                admin_user_id
            )
        
        elif decision == 'approve_dispute':
            # Override with dispute claim
            ResultManagementService.override_result(
                match_id=match.id,
                new_winner_id=dispute.claimed_correct_winner_id,
                new_scores=dispute.claimed_correct_scores,
                admin_user_id=admin_user_id,
                reason=f"Dispute upheld: {resolution_notes}"
            )
        
        elif decision == 'rematch':
            # Reset match, order rematch
            match.state = Match.SCHEDULED
            match.winner = None
            match.scores = None
            match.save()
            
            NotificationService.send_rematch_ordered(match.id, resolution_notes)
        
        # Mark dispute resolved
        dispute.status = 'resolved'
        dispute.resolved_by_id = admin_user_id
        dispute.resolved_at = timezone.now()
        dispute.resolution = decision
        dispute.resolution_notes = resolution_notes
        dispute.save()
        
        # Notify both teams
        NotificationService.send_dispute_resolved(dispute.id, decision)
```

**Current State**: ❌ **ENTIRELY MISSING** - No TournamentOps integration for result verification.

**Gap Priority**: **CRITICAL** - Core to results pipeline integrity.

---

### 4B.6 Event-Driven Result Propagation

**After result finalization, events trigger cascading updates**:

```
MatchCompletedEvent published
        │
        ├──> Event Handler 1: BracketService.advance_winner()
        │    └──> Winner added to next round match
        │
        ├──> Event Handler 2: TeamStatsService.record_match_result()
        │    ├──> Team.matches_played += 1 (both teams)
        │    ├──> Team.matches_won += 1 (winner)
        │    └──> Team.win_rate recalculated
        │
        ├──> Event Handler 3: UserStatsService.record_match_result()
        │    ├──> User.matches_played += 1 (all players)
        │    ├──> User.matches_won += 1 (winning team players)
        │    └──> User.win_rate recalculated
        │
        ├──> Event Handler 4: MatchHistoryService.create_history_entry()
        │    └──> TeamMatchHistory record created
        │
        ├──> Event Handler 5: RankingService.update_elo_ratings()
        │    ├──> Winner ELO += 25
        │    └──> Loser ELO -= 25
        │
        ├──> Event Handler 6: PayoutService.award_match_bonus()
        │    └──> Winner receives DeltaCoin bonus (if configured)
        │
        └──> Event Handler 7: NotificationService.send_result_notifications()
             ├──> Winner notification: "You won! Advancing to Round 2."
             └──> Loser notification: "Match complete. Better luck next time."
```

**Idempotency**: All event handlers must be idempotent (safe to retry).

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Event publishing on result** | ⚠️ **PARTIAL** | Some events exist | Not comprehensive |
| **Bracket advancement handler** | ✅ **EXISTS** | Works | Functional |
| **Team stats handler** | ❌ **MISSING** | No handler | Stats never update |
| **User stats handler** | ❌ **MISSING** | No handler | No user stats |
| **Match history handler** | ❌ **MISSING** | No handler | TeamMatchHistory empty |
| **ELO update handler** | ❌ **MISSING** | No ranking system | No ELO tracking |
| **Payout handler** | ⚠️ **PARTIAL** | Tournament prizes only | No per-match bonuses |
| **Notification handler** | ⚠️ **PARTIAL** | In-app only | No email |
| **Idempotency checks** | ❌ **MISSING** | No duplicate prevention | Handlers can run twice |

**Gap Priority**: **HIGH** - Event-driven propagation prevents forgotten updates.

---

## 4C. Multi-Stage Tournament Lifecycle

### 4C.1 Overview

Complex tournaments often have **multiple stages** (e.g., Group Stage → Playoffs, Swiss System → Top 8 Bracket). Each stage has its own lifecycle, and transitions between stages require careful orchestration.

**Example: World Cup Format**:
- **Stage 1**: Group Stage (8 groups, 4 teams each, round-robin)
- **Stage 2**: Round of 16 (single-elimination knockout)
- **Stage 3**: Quarterfinals (single-elimination)
- **Stage 4**: Semifinals (single-elimination)
- **Stage 5**: Finals (best-of-3 series)

Each stage advances based on standings/results from prior stage.

---

### 4C.2 Group Stage → Knockout Transition

**Group Stage Completion Requirements**:
1. All group matches completed
2. Final standings calculated (with tiebreakers if needed)
3. Advancement criteria met (top 2 from each group advance)

**Transition Workflow**:

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Group Stage Completion Detection                        │
│  System monitors all group matches                              │
│  When last match completed → Trigger GroupStageCompletedEvent   │
└────────────────────┬─────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────┐
│ STEP 2: Calculate Final Standings                               │
│  For each group:                                                 │
│    - Sort teams by wins, then tiebreakers (head-to-head, GD)    │
│    - Assign final ranks (1st, 2nd, 3rd, 4th)                    │
│  Mark top N teams as "advanced"                                 │
│  Mark remaining teams as "eliminated"                            │
└────────────────────┬─────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────┐
│ STEP 3: Generate Knockout Bracket                               │
│  Use advancement seeding rules:                                  │
│    - Group A #1 vs Group B #2                                    │
│    - Group B #1 vs Group A #2                                    │
│    - etc.                                                        │
│  Generate bracket matches (Round of 16)                          │
│  Assign teams to bracket positions                               │
└────────────────────┬─────────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────────┐
│ STEP 4: Publish Bracket & Notify Participants                   │
│  Bracket visible on tournament page                             │
│  Notify advanced teams: "You advanced! Round of 16 starts..."   │
│  Notify eliminated teams: "Tournament over. Thanks for playing."│
│  Organizer notification: "Group stage complete. Playoffs ready." │
└──────────────────────────────────────────────────────────────────┘
```

**Tiebreaker Logic**:

When teams have equal wins, apply tiebreakers:
1. **Head-to-head record** (if 2 teams tied)
2. **Goal differential** (total goals scored - conceded)
3. **Total goals scored**
4. **Fastest match win** (avg match duration)
5. **Random** (if all else equal)

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Multi-stage tournaments** | ❌ **MISSING** | Single bracket only | No stage concept |
| **Group stage completion detection** | ❌ **MISSING** | No event | Manual advancement only |
| **Standings calculation** | ❌ **MISSING** | No standings service | Manual calculation |
| **Tiebreaker system** | ❌ **MISSING** | No tiebreaker logic | Undefined behavior |
| **Advancement marking** | ❌ **MISSING** | No "advanced" status | No concept of elimination |
| **Knockout generation from groups** | ❌ **MISSING** | No cross-stage generation | Manual bracket creation |
| **Seeding from group standings** | ❌ **MISSING** | No seeding rules | Random or manual |
| **Stage transition notifications** | ❌ **MISSING** | No stage events | No advancement alerts |

**Gap Priority**: **HIGH** - Multi-stage tournaments are common (esports World Cups, qualifiers).

---

### 4C.3 Swiss System → Top Cut Bracket

**Swiss System Overview**:
- All participants play N rounds (usually 5-7)
- Each round, participants paired with similar records (3-1 vs 3-1)
- After N rounds, top X advance to single-elimination bracket

**Example: Magic: The Gathering Tournament**:
- 128 players
- 7 rounds Swiss (all players play 7 matches)
- Top 8 after Swiss advance to single-elimination Top 8

**Swiss Pairing Algorithm**:

```python
# tournament_ops/services/swiss_pairing_service.py
class SwissPairingService:
    """Generate Swiss pairings each round."""
    
    @staticmethod
    def generate_round(tournament_id: int, round_number: int):
        """
        Generate pairings for next Swiss round.
        
        Pairing Rules:
        1. Sort participants by current record (descending)
        2. Group participants by same record (3-0, 2-1, 1-2, 0-3)
        3. Within each group, pair top-half vs bottom-half
        4. Avoid rematches (never pair teams who already played)
        5. Handle byes (if odd number, lowest-ranked gets bye)
        """
        standings = SwissStandingsService.get_standings(tournament_id)
        
        # Group by record
        record_groups = defaultdict(list)
        for participant in standings:
            record_groups[participant.record].append(participant)
        
        pairings = []
        
        for record, participants in record_groups.items():
            # Sort by tiebreakers within record group
            participants.sort(key=lambda p: p.tiebreaker_score, reverse=True)
            
            # Pair top-half vs bottom-half
            mid = len(participants) // 2
            top_half = participants[:mid]
            bottom_half = participants[mid:]
            
            for i in range(len(top_half)):
                if bottom_half:
                    opponent = bottom_half.pop(0)
                    
                    # Check if already played
                    if not has_played_before(top_half[i].id, opponent.id):
                        pairings.append((top_half[i], opponent))
                    else:
                        # Find next available opponent
                        opponent = find_next_valid_opponent(
                            top_half[i], bottom_half
                        )
                        pairings.append((top_half[i], opponent))
            
            # Handle bye
            if len(participants) % 2 == 1:
                bye_participant = participants[-1]
                pairings.append((bye_participant, None))  # Bye
        
        # Create matches
        for pair in pairings:
            Match.objects.create(
                tournament_id=tournament_id,
                round_number=round_number,
                participant1=pair[0],
                participant2=pair[1],  # None if bye
                state=Match.SCHEDULED
            )
        
        return pairings
```

**Top Cut Transition**:

After Swiss rounds complete:
1. Calculate final standings (wins, tiebreakers)
2. Take top N (usually 8)
3. Seed into single-elimination bracket (1 vs 8, 2 vs 7, etc.)
4. Eliminate remaining participants

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Swiss pairing algorithm** | ❌ **MISSING** | No Swiss system | Only single-elim/round-robin |
| **Swiss standings** | ❌ **MISSING** | No standings service | No concept |
| **Rematch avoidance** | ❌ **MISSING** | No pairing history | Can pair twice |
| **Bye handling** | ❌ **MISSING** | No bye logic | Undefined for odd participants |
| **Top cut selection** | ❌ **MISSING** | No advancement service | Manual selection |
| **Top cut bracket generation** | ❌ **MISSING** | No cross-stage generation | Manual bracket |
| **Tiebreaker system** | ❌ **MISSING** | No tiebreakers | Undefined ranking |

**Gap Priority**: **MEDIUM** - Swiss is popular in card games, esports qualifiers.

---

### 4C.4 Best-of-N Series Management

**Series Overview**:
- Instead of single matches, some tournaments use **series** (best-of-3, best-of-5)
- Series = collection of games where first to win N games wins series
- Used in playoffs, finals (higher stakes)

**Example: Best-of-5 Finals**:
- Team A vs Team B
- First to 3 wins takes series
- Possible outcomes: 3-0, 3-1, 3-2

**Series Model**:

```python
# tournaments/models.py
class MatchSeries(models.Model):
    """Represents a best-of-N series."""
    tournament = models.ForeignKey(Tournament)
    round_number = models.IntegerField()
    participant1 = models.ForeignKey(Team, related_name='series_as_p1')
    participant2 = models.ForeignKey(Team, related_name='series_as_p2')
    
    format = models.CharField(
        max_length=10,
        choices=[('bo1', 'Best of 1'), ('bo3', 'Best of 3'), ('bo5', 'Best of 5')]
    )
    games_to_win = models.IntegerField()  # 1 for bo1, 2 for bo3, 3 for bo5
    
    state = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ]
    )
    
    winner = models.ForeignKey(Team, null=True, blank=True)
    
    # Series scores (e.g., "2-1" means participant1 won 2 games, participant2 won 1)
    p1_games_won = models.IntegerField(default=0)
    p2_games_won = models.IntegerField(default=0)

class Game(models.Model):
    """Individual game within a series."""
    series = models.ForeignKey(MatchSeries, related_name='games')
    game_number = models.IntegerField()  # 1, 2, 3, etc.
    
    winner = models.ForeignKey(Team, null=True, blank=True)
    scores = models.JSONField(null=True, blank=True)  # Game-specific scores
    
    state = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed')
        ]
    )
```

**Series Progression**:

```
Series: Team A vs Team B (Best of 5)
  ├── Game 1: Team A wins (1-0)
  ├── Game 2: Team B wins (1-1)
  ├── Game 3: Team A wins (2-1)
  ├── Game 4: Team A wins (3-1) → SERIES OVER (Team A wins 3-1)
  └── Game 5: Not played (series ended early)
```

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Series concept** | ❌ **MISSING** | Single match only | No multi-game series |
| **Best-of-N model** | ❌ **MISSING** | No MatchSeries model | Only Match exists |
| **Game tracking** | ❌ **MISSING** | No Game model | Can't track individual games |
| **Series progression** | ❌ **MISSING** | No series state machine | No concept of series end |
| **Series result submission** | ❌ **MISSING** | No series result form | Single match results only |
| **Series advancement** | ❌ **MISSING** | No series winner advancement | Match-level only |

**Gap Priority**: **MEDIUM** - Important for playoffs/finals, but not all tournaments need it.

---

### 4C.5 Stage Scheduling & Dependencies

**Multi-Stage Scheduling Requirements**:
- **Stage dependencies**: Playoffs can't start until Group Stage completes
- **Date ranges**: Each stage has start/end date
- **Match scheduling within stage**: All group matches must fit within Group Stage dates

**Stage Model**:

```python
# tournaments/models.py
class TournamentStage(models.Model):
    """Represents a stage within a tournament."""
    tournament = models.ForeignKey(Tournament, related_name='stages')
    name = models.CharField(max_length=100)  # "Group Stage", "Playoffs", "Finals"
    order = models.IntegerField()  # 1, 2, 3 (execution order)
    
    format = models.CharField(
        max_length=20,
        choices=[
            ('round_robin', 'Round Robin'),
            ('single_elim', 'Single Elimination'),
            ('double_elim', 'Double Elimination'),
            ('swiss', 'Swiss System')
        ]
    )
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Advancement rules
    advancement_count = models.IntegerField()  # How many advance to next stage
    advancement_criteria = models.CharField(
        max_length=20,
        choices=[
            ('top_n', 'Top N'),
            ('top_n_per_group', 'Top N per Group'),
            ('all', 'All participants')
        ]
    )
    
    state = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('active', 'Active'),
            ('completed', 'Completed')
        ],
        default='pending'
    )
    
    depends_on_stage = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='dependent_stages'
    )  # Previous stage that must complete first
```

**Stage Transition Logic**:

```python
# tournament_ops/services/stage_progression_service.py
class StageProgressionService:
    """Manage progression between tournament stages."""
    
    @staticmethod
    @transaction.atomic
    def complete_stage(stage_id: int):
        """
        Mark stage as completed and activate next stage.
        
        Workflow:
        1. Verify all matches in stage are completed
        2. Calculate final standings
        3. Determine advancing participants
        4. Mark stage as completed
        5. Activate next stage
        6. Generate bracket for next stage with advancing participants
        7. Notify participants of advancement/elimination
        """
        stage = TournamentStage.objects.get(id=stage_id)
        
        # Verify completion
        incomplete_matches = Match.objects.filter(
            stage=stage,
            state__in=[Match.SCHEDULED, Match.IN_PROGRESS]
        )
        if incomplete_matches.exists():
            raise ValidationError("Cannot complete stage with unfinished matches")
        
        # Calculate standings
        standings = StandingsService.calculate_for_stage(stage.id)
        
        # Determine advancing participants
        advancing = select_advancing_participants(
            standings,
            stage.advancement_count,
            stage.advancement_criteria
        )
        
        # Mark stage complete
        stage.state = TournamentStage.COMPLETED
        stage.save()
        
        # Activate next stage
        next_stage = TournamentStage.objects.filter(
            tournament=stage.tournament,
            depends_on_stage=stage
        ).first()
        
        if next_stage:
            next_stage.state = TournamentStage.ACTIVE
            next_stage.save()
            
            # Generate bracket for next stage
            BracketService.generate_bracket(
                stage_id=next_stage.id,
                participants=advancing,
                format=next_stage.format
            )
            
            # Notify
            NotificationService.send_stage_transition(
                stage.id,
                next_stage.id,
                advancing_ids=[p.id for p in advancing]
            )
```

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **TournamentStage model** | ❌ **MISSING** | Single-stage only | No stage concept |
| **Stage dependencies** | ❌ **MISSING** | No dependency tracking | All matches in one pool |
| **Stage scheduling** | ❌ **MISSING** | No stage dates | Tournament-level dates only |
| **Advancement criteria** | ❌ **MISSING** | No advancement rules | Manual promotion |
| **Stage completion detection** | ❌ **MISSING** | No completion events | Manual progression |
| **Stage transition service** | ❌ **MISSING** | No service | Manual bracket creation |
| **Stage-specific standings** | ❌ **MISSING** | No stage standings | Global tournament standings |
| **Multi-stage bracket generation** | ❌ **MISSING** | No cross-stage generation | Single bracket only |

**Gap Priority**: **HIGH** - Multi-stage tournaments are very common in esports.

---

## 4D. Organizer & Admin Panel Workflows

### 4D.1 Overview

Organizers need a **centralized dashboard** to manage all aspects of their tournament. This "command center" should provide at-a-glance status and quick actions for common tasks.

---

### 4D.2 Tournament Dashboard

**Dashboard Layout**:

```
┌──────────────────────────────────────────────────────────────────┐
│ TOURNAMENT DASHBOARD: Summer 2025 Valorant Cup                  │
├──────────────────────────────────────────────────────────────────┤
│ Status: 🟢 ACTIVE  |  Format: Single Elim  |  32 Teams           │
│ Start: Dec 15, 2025  |  Prize Pool: $5,000  |  Entry: $25        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ QUICK STATS                                                      │
│ ┌─────────────┬─────────────┬─────────────┬─────────────┐       │
│ │ 32/32       │ 12/16       │ 5 Pending   │ $800/800    │       │
│ │ Registered  │ Completed   │ Disputes    │ Collected   │       │
│ └─────────────┴─────────────┴─────────────┴─────────────┘       │
│                                                                  │
│ ALERTS (3) ⚠️                                                    │
│ • Match #45 overdue by 2 hours (Team A vs Team B)               │
│ • 5 disputed results pending review                             │
│ • Payment reversal: Team Delta requested refund                 │
│                                                                  │
│ QUICK ACTIONS                                                    │
│ [Edit Tournament] [View Bracket] [Results Inbox (5)]            │
│ [Manage Teams] [Schedule Matches] [Send Announcement]           │
│                                                                  │
│ RECENT ACTIVITY                                                  │
│ • 2 mins ago: Match #46 completed (Team Gamma won)              │
│ • 15 mins ago: Team Echo submitted result for Match #47         │
│ • 1 hour ago: You approved result for Match #44                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Dashboard Sections**:
1. **Tournament Overview**: Name, status, format, prize, dates
2. **Quick Stats**: Registrations, match completion, disputes, payments
3. **Alerts**: Overdue matches, pending disputes, payment issues
4. **Quick Actions**: Common tasks (edit, view bracket, inbox, schedule)
5. **Recent Activity**: Live feed of tournament events

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Organizer dashboard** | ⚠️ **PARTIAL** | Basic dashboard exists | Missing stats, alerts, feed |
| **Quick stats** | ❌ **MISSING** | No aggregated stats | Manual counting |
| **Alerts system** | ❌ **MISSING** | No alert detection | No overdue/dispute alerts |
| **Quick actions** | ⚠️ **PARTIAL** | Some links exist | Not centralized |
| **Activity feed** | ❌ **MISSING** | No feed | No recent events |
| **Real-time updates** | ❌ **MISSING** | Static page | Must refresh manually |

**Gap Priority**: **HIGH** - Dashboard is organizer's primary interface.

---

### 4D.3 Overdue Match Alerts & Tools

**Overdue Match Detection**:
- Match has `scheduled_time` set
- Current time > `scheduled_time + grace_period` (e.g., 30 mins)
- Match state is still `SCHEDULED` or `IN_PROGRESS`
- No result submitted

**Overdue Match Alert**:

```
⚠️ OVERDUE MATCH

Match #45: Team Alpha vs Team Beta
Scheduled: Dec 8, 2025 2:00 PM
Current Time: Dec 8, 2025 4:30 PM
Status: 2 hours 30 minutes overdue

Possible Actions:
[Contact Teams] [Reschedule] [Forfeit Both] [Award Win to Team Alpha]
```

**Organizer Actions**:

1. **Contact Teams**:
   - Send in-app notification: "Your match is overdue. Please report status."
   - Optionally send email/Discord ping

2. **Reschedule**:
   - Set new `scheduled_time`
   - Notify both teams of new time
   - Log reason for reschedule

3. **Forfeit One Team**:
   - If one team is present, other is no-show → Award win to present team
   - Mark absent team as forfeited
   - Log forfeit reason

4. **Forfeit Both**:
   - If neither team responds → Double forfeit
   - Both eliminated (or advance random team if must fill bracket)

**Automated Overdue Handling**:

```python
# tournament_ops/tasks.py
@periodic_task(run_every=timedelta(minutes=15))
def check_overdue_matches():
    """
    Check for overdue matches and take action.
    
    Actions:
    - Send reminder at +15 mins overdue
    - Send warning at +30 mins overdue
    - Auto-forfeit at +60 mins overdue (if configured)
    """
    now = timezone.now()
    grace_period = timedelta(minutes=15)
    
    overdue_matches = Match.objects.filter(
        state__in=[Match.SCHEDULED, Match.IN_PROGRESS],
        scheduled_time__lt=now - grace_period
    )
    
    for match in overdue_matches:
        overdue_duration = now - match.scheduled_time
        
        if overdue_duration >= timedelta(minutes=60):
            # Auto-forfeit if enabled
            if match.tournament.auto_forfeit_enabled:
                handle_auto_forfeit(match.id)
        
        elif overdue_duration >= timedelta(minutes=30):
            # Send warning
            NotificationService.send_overdue_warning(match.id)
        
        elif overdue_duration >= timedelta(minutes=15):
            # Send reminder
            NotificationService.send_overdue_reminder(match.id)
```

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Overdue detection** | ❌ **MISSING** | No overdue logic | Matches can be overdue forever |
| **Overdue alerts** | ❌ **MISSING** | No alerts | Organizer must check manually |
| **Contact teams action** | ❌ **MISSING** | No contact UI | Manual messaging |
| **Reschedule action** | ❌ **MISSING** | No reschedule service | Edit match manually |
| **Forfeit one team** | ❌ **MISSING** | No forfeit service | Manual result entry |
| **Forfeit both teams** | ❌ **MISSING** | No double forfeit | Undefined |
| **Auto-forfeit** | ❌ **MISSING** | No automation | Manual only |
| **Overdue notifications** | ❌ **MISSING** | No reminders | Teams never reminded |

**Gap Priority**: **HIGH** - Overdue matches block tournament progress.

---

### 4D.4 Dispute Handling Workflow

**Dispute Queue**:

```
┌──────────────────────────────────────────────────────────────────┐
│ DISPUTE QUEUE (5 pending)                                        │
├──────────────────────────────────────────────────────────────────┤
│ Filters: [ All ] [ Pending ] [ Resolved ] [ Escalated ]         │
├──────────────────────────────────────────────────────────────────┤
│ Dispute #12 - Match #46 (HIGH PRIORITY) 🔴                      │
│  Disputer: Team Beta                                             │
│  Original Claim: Team Alpha won 13-7                             │
│  Dispute Reason: "Fake screenshot - we actually won 13-10"       │
│  Evidence: [View counter-proof screenshot]                       │
│  Age: 2 hours                                                    │
│  [Review Dispute] [Resolve] [Escalate]                           │
├──────────────────────────────────────────────────────────────────┤
│ Dispute #11 - Match #43 (MEDIUM PRIORITY) 🟡                    │
│  Disputer: Team Gamma                                            │
│  Original Claim: Team Delta won 13-8                             │
│  Dispute Reason: "Opponent used cheats"                          │
│  Evidence: [View replay footage link]                            │
│  Age: 5 hours                                                    │
│  [Review Dispute] [Resolve] [Ban User]                           │
└──────────────────────────────────────────────────────────────────┘
```

**Dispute Review Page**:

```
┌──────────────────────────────────────────────────────────────────┐
│ DISPUTE #12 REVIEW                                               │
├──────────────────────────────────────────────────────────────────┤
│ Match: #46 - Team Alpha vs Team Beta                            │
│ Scheduled: Dec 8, 2025 2:00 PM                                   │
├──────────────────────────────────────────────────────────────────┤
│ ORIGINAL SUBMISSION                                              │
│  Submitted by: PlayerX (Team Alpha captain)                      │
│  Claimed winner: Team Alpha                                      │
│  Scores: 13-7                                                    │
│  Proof: [View screenshot ↗]                                      │
│  Submitted at: Dec 8, 2025 3:15 PM                               │
├──────────────────────────────────────────────────────────────────┤
│ DISPUTE                                                          │
│  Submitted by: PlayerY (Team Beta captain)                       │
│  Reason: Fake screenshot - incorrect score                       │
│  Explanation: "We actually won 13-10. Their screenshot is        │
│               photoshopped. See our proof below."                │
│  Counter-proof: [View screenshot ↗]                              │
│  Disputed at: Dec 8, 2025 3:45 PM                                │
├──────────────────────────────────────────────────────────────────┤
│ RESOLUTION ACTIONS                                               │
│  [ ] Approve Original (Team Alpha wins 13-7)                     │
│  [ ] Approve Dispute (Team Beta wins 13-10)                      │
│  [ ] Order Rematch (both claims invalid)                         │
│  [ ] Request More Info                                           │
│                                                                  │
│  Resolution Notes: [Text area for explanation]                   │
│  [Submit Decision]                                               │
└──────────────────────────────────────────────────────────────────┘
```

**Resolution Outcomes**:
1. **Approve Original**: Original submission was correct, dispute rejected
2. **Approve Dispute**: Dispute was valid, override original result
3. **Order Rematch**: Both submissions suspect, teams must replay
4. **Request More Info**: Need additional evidence before decision

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Dispute queue** | ❌ **MISSING** | No queue UI | Disputes in generic list |
| **Dispute priority** | ❌ **MISSING** | No prioritization | All equal priority |
| **Dispute review page** | ❌ **MISSING** | No review UI | View dispute details only |
| **Side-by-side evidence** | ❌ **MISSING** | No comparison view | Manual tab switching |
| **Resolution actions** | ❌ **MISSING** | No resolution workflow | Manual result override |
| **Resolution notes** | ❌ **MISSING** | No notes field | No explanation logged |
| **Rematch ordering** | ❌ **MISSING** | No rematch service | Manual match creation |
| **Request more info** | ❌ **MISSING** | No communication flow | Manual messaging |

**Gap Priority**: **CRITICAL** - Dispute resolution is essential for fair tournaments.

---

### 4D.5 Audit Logs & History Tracking

**Audit Log Purpose**:
- Track all organizer actions (for transparency and debugging)
- Show who did what, when, and why
- Prevent unauthorized changes
- Provide rollback capability

**Audit Log Entries**:

```
┌──────────────────────────────────────────────────────────────────┐
│ TOURNAMENT AUDIT LOG                                             │
├──────────────────────────────────────────────────────────────────┤
│ Dec 8, 2025 4:45 PM - OrganizerX                                │
│  Action: Approved disputed result                               │
│  Target: Match #46                                               │
│  Details: Approved Team Alpha win (13-7), rejected Team Beta    │
│            dispute. Reason: "Team Alpha's proof was valid."      │
│  [View Full Details] [Rollback]                                  │
├──────────────────────────────────────────────────────────────────┤
│ Dec 8, 2025 3:30 PM - OrganizerX                                │
│  Action: Edited bracket                                          │
│  Target: Match #50                                               │
│  Changes: Swapped Team Echo (pos 5) ↔ Team Foxtrot (pos 12)    │
│  Reason: "Corrected seeding error"                               │
│  [View Before/After] [Rollback]                                  │
├──────────────────────────────────────────────────────────────────┤
│ Dec 8, 2025 2:00 PM - OrganizerX                                │
│  Action: Rescheduled match                                       │
│  Target: Match #45                                               │
│  Changes: Scheduled time: 2:00 PM → 4:00 PM                      │
│  Reason: "Team Alpha requested delay (connection issues)"        │
│  [View Details]                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Audit Log Model**:

```python
# tournaments/models.py
class TournamentAuditLog(models.Model):
    """Tracks all organizer actions on tournament."""
    tournament = models.ForeignKey(Tournament, related_name='audit_logs')
    user = models.ForeignKey(User)  # Who performed the action
    
    action = models.CharField(
        max_length=50,
        choices=[
            ('edit_settings', 'Edited Tournament Settings'),
            ('edit_bracket', 'Edited Bracket'),
            ('approve_result', 'Approved Result'),
            ('reject_result', 'Rejected Result'),
            ('override_result', 'Overrode Result'),
            ('resolve_dispute', 'Resolved Dispute'),
            ('reschedule_match', 'Rescheduled Match'),
            ('forfeit_team', 'Forfeited Team'),
            ('ban_participant', 'Banned Participant'),
            ('refund_payment', 'Refunded Payment')
        ]
    )
    
    target_type = models.CharField(max_length=50)  # 'Match', 'Team', 'Tournament'
    target_id = models.IntegerField()  # ID of affected object
    
    changes = models.JSONField()  # Before/after snapshot
    reason = models.TextField()  # Why action was taken
    
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(null=True)
```

**Rollback Capability**:
- Audit log stores `before` and `after` state
- Organizer can rollback action by applying `before` state
- Rollback itself is logged (for audit trail)

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Audit log model** | ❌ **MISSING** | No TournamentAuditLog | No logging |
| **Action logging** | ❌ **MISSING** | No log creation | Actions not tracked |
| **Audit log UI** | ❌ **MISSING** | No log viewer | Can't see history |
| **Before/after snapshots** | ❌ **MISSING** | No change tracking | No rollback data |
| **Reason field** | ❌ **MISSING** | No reason logging | No explanations |
| **Rollback capability** | ❌ **MISSING** | No rollback service | Changes permanent |
| **IP/user agent tracking** | ❌ **MISSING** | No metadata | Can't identify source |

**Gap Priority**: **MEDIUM** - Important for transparency and debugging, but not critical for basic tournaments.

---

### 4D.6 Guidance & Help System

**Organizer Guidance**:
- **Tooltips**: Explain each field in tournament creation form
- **Wizards**: Step-by-step tournament setup (as in ARCH_PLAN_PART_1)
- **Help Center**: FAQs, tutorials, video guides
- **Suggested Actions**: "You should schedule Round 2 matches now"

**In-Context Help**:

```
┌──────────────────────────────────────────────────────────────────┐
│ CREATE TOURNAMENT                                                │
├──────────────────────────────────────────────────────────────────┤
│ Tournament Format: [Dropdown ▼] ❓                               │
│                                                                  │
│ ╔══════════════════════════════════════════════════════════════╗ │
│ ║ 💡 HELP: Tournament Format                                   ║ │
│ ║                                                              ║ │
│ ║ • Single Elimination: Fastest format. Lose once = out.      ║ │
│ ║   Best for: Quick tournaments, large participant counts.    ║ │
│ ║                                                              ║ │
│ ║ • Double Elimination: More forgiving. 2 losses = out.       ║ │
│ ║   Best for: Competitive fairness, smaller groups.           ║ │
│ ║                                                              ║ │
│ ║ • Round Robin: Everyone plays everyone. Most fair.          ║ │
│ ║   Best for: Small groups (≤8 teams), league play.           ║ │
│ ║                                                              ║ │
│ ║ [Learn More] [Watch Tutorial]                               ║ │
│ ╚══════════════════════════════════════════════════════════════╝ │
└──────────────────────────────────────────────────────────────────┘
```

**Suggested Actions**:

Dashboard shows context-aware suggestions:
- Registration open, 0 teams → "Promote your tournament on Discord"
- 32/32 teams, registration closed → "Generate bracket now"
- Bracket generated, no matches scheduled → "Schedule Round 1 matches"
- Round 1 complete → "Publish Round 2 schedule"
- 5 disputed results → "Review disputes in Results Inbox"

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Tooltips** | ⚠️ **PARTIAL** | Some tooltips exist | Not comprehensive |
| **Wizards** | ❌ **MISSING** | No wizard UI | Form-only creation |
| **Help center** | ❌ **MISSING** | No help docs | External docs only |
| **Video tutorials** | ❌ **MISSING** | No embedded videos | External YouTube |
| **Suggested actions** | ❌ **MISSING** | No context-aware suggestions | Static dashboard |
| **In-context help** | ❌ **MISSING** | No expandable help | Tooltips only |

**Gap Priority**: **LOW** - Nice-to-have for UX, but not critical for functionality.

---

## 4E. User & Team Experience

### 4E.1 Overview

While organizers need powerful tools, **participants need simplicity**. The user experience should guide players/teams through registration → matches → results with minimal friction.

---

### 4E.2 Guided Registration Experience

**Registration Wizard**:

```
┌──────────────────────────────────────────────────────────────────┐
│ REGISTER FOR: Summer 2025 Valorant Cup                          │
├──────────────────────────────────────────────────────────────────┤
│ STEP 1 OF 4: Team Selection                                      │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                  │
│ Select Team: [Dropdown ▼]                                       │
│   [ ] My Team Alpha (5 members, 2.5 KD avg) ✓ Eligible         │
│   [ ] Beta Squad (3 members, 1.8 KD avg) ⚠️ Needs 2 more       │
│   [ ] Gamma Force (6 members, 3.1 KD avg) ✓ Eligible           │
│                                                                  │
│ [Create New Team Instead]                                        │
│                                                                  │
│ [Next Step: Payment →]                                           │
└──────────────────────────────────────────────────────────────────┘
```

**Eligibility Checks** (Real-Time):
- Team size: 5/5 required ✓
- Skill rating: 1500+ required ✓
- Game account: Valorant account linked ✓
- Payment: $25 entry fee ⚠️ Pending

**Error Prevention**:
- Can't proceed to Step 2 if team ineligible
- Clear explanation of what's missing
- Link to fix issue (e.g., "Invite 2 more members")

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Registration wizard** | ❌ **MISSING** | Single-page form | No step-by-step flow |
| **Real-time eligibility checks** | ❌ **MISSING** | Submit-time validation only | No live feedback |
| **Team selection dropdown** | ⚠️ **PARTIAL** | Team list exists | No eligibility indicators |
| **Error prevention** | ⚠️ **PARTIAL** | Basic validation | Not user-friendly |
| **Clear error messages** | ⚠️ **PARTIAL** | Generic errors | No actionable guidance |
| **Fix issue links** | ❌ **MISSING** | No links | Manual navigation |

**Gap Priority**: **MEDIUM** - Improves UX, reduces registration errors.

---

### 4E.3 Match Reporting Guidance

**Match Page (Participant View)**:

```
┌──────────────────────────────────────────────────────────────────┐
│ YOUR MATCH: Team Alpha vs Team Beta                             │
├──────────────────────────────────────────────────────────────────┤
│ Status: 🟡 IN PROGRESS                                           │
│ Scheduled: Dec 8, 2025 2:00 PM                                   │
│ Map: Ascent                                                      │
├──────────────────────────────────────────────────────────────────┤
│ WHAT TO DO NOW:                                                  │
│                                                                  │
│ 1. Play your match in Valorant                                  │
│ 2. Take screenshot of final scoreboard                          │
│ 3. Return here and submit result                                │
│                                                                  │
│ ⏰ Time Remaining: 1 hour 30 mins                                │
│                                                                  │
│ [Join Match Lobby] [Submit Result] [Request Reschedule]         │
└──────────────────────────────────────────────────────────────────┘
```

**Submit Result Guidance**:

```
┌──────────────────────────────────────────────────────────────────┐
│ SUBMIT MATCH RESULT                                              │
├──────────────────────────────────────────────────────────────────┤
│ Winner: ( ) Team Alpha  (●) Team Beta                           │
│                                                                  │
│ Scores:                                                          │
│  Team Alpha: [7__]  ⚠️ Must be less than Team Beta              │
│  Team Beta:  [13_]  ✓ Valid                                      │
│                                                                  │
│ Proof Screenshot: [Choose File] [No file chosen]                │
│  💡 TIP: Take screenshot showing final scoreboard with all       │
│          player names and scores visible.                        │
│                                                                  │
│ Additional Notes (optional):                                     │
│  [Good game! Close match.]                                       │
│                                                                  │
│ ✓ I confirm this result is accurate                              │
│                                                                  │
│ [Submit Result]                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Real-Time Validation**:
- Winner must match scores (Team Beta score > Team Alpha score)
- Scores must be valid for game (Valorant: 0-13)
- Screenshot required (can't submit without)
- Confirmation checkbox required

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Match page guidance** | ⚠️ **PARTIAL** | Basic match view | No "What to do now" section |
| **Time remaining** | ❌ **MISSING** | No countdown | Static scheduled time |
| **Submit result button** | ✅ **EXISTS** | Button works | No guidance |
| **Real-time score validation** | ❌ **MISSING** | Submit-time only | No live validation |
| **Screenshot tips** | ❌ **MISSING** | No tips | Users guess what to upload |
| **Confirmation checkbox** | ❌ **MISSING** | No checkbox | No explicit confirmation |

**Gap Priority**: **MEDIUM** - Reduces user errors, improves result accuracy.

---

### 4E.4 Dispute Submission Experience

**Dispute Form (Participant View)**:

```
┌──────────────────────────────────────────────────────────────────┐
│ DISPUTE MATCH RESULT                                             │
├──────────────────────────────────────────────────────────────────┤
│ Match: #46 - Team Alpha vs Team Beta                            │
│ Submitted Result: Team Alpha won 13-7                           │
├──────────────────────────────────────────────────────────────────┤
│ Why are you disputing this result?                              │
│                                                                  │
│ Reason: [Dropdown ▼]                                             │
│   [ ] Incorrect score                                            │
│   [●] Fake/manipulated proof                                     │
│   [ ] Opponent cheated                                           │
│   [ ] Opponent didn't show up (forfeit claim is wrong)          │
│   [ ] Other                                                      │
│                                                                  │
│ Explanation (required, min 50 characters):                       │
│  [Their screenshot is photoshopped. We actually won 13-10.      │
│   See our proof screenshot attached below. You can clearly see  │
│   the correct score.]                                            │
│  (85 characters) ✓                                               │
│                                                                  │
│ Counter-Proof (recommended):                                     │
│  [Choose File] screenshot_proof.png (2.3 MB) ✓                  │
│                                                                  │
│ ⚠️ WARNING: False disputes may result in penalties or bans.     │
│                                                                  │
│ [ ] I confirm this dispute is legitimate                         │
│                                                                  │
│ [Submit Dispute] [Cancel]                                        │
└──────────────────────────────────────────────────────────────────┘
```

**After Submission**:

```
┌──────────────────────────────────────────────────────────────────┐
│ ✓ DISPUTE SUBMITTED                                              │
├──────────────────────────────────────────────────────────────────┤
│ Your dispute has been submitted to the tournament organizer.     │
│                                                                  │
│ WHAT HAPPENS NEXT:                                               │
│  1. Organizer will review your dispute and the original result   │
│  2. They may request additional information from you             │
│  3. A decision will be made within 24 hours                      │
│  4. You'll be notified of the final ruling                       │
│                                                                  │
│ Dispute ID: #12                                                  │
│ Status: Pending Review                                           │
│                                                                  │
│ [View Dispute Status] [Return to Tournament]                     │
└──────────────────────────────────────────────────────────────────┘
```

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Dispute form** | ⚠️ **PARTIAL** | Basic form exists | No guidance |
| **Reason dropdown** | ❌ **MISSING** | Text-only | No categorization |
| **Character minimum** | ❌ **MISSING** | No validation | Can submit "No" |
| **Counter-proof upload** | ❌ **MISSING** | No field | Text-only disputes |
| **False dispute warning** | ❌ **MISSING** | No warning | No deterrent |
| **Confirmation checkbox** | ❌ **MISSING** | No checkbox | No confirmation |
| **Post-submission guidance** | ❌ **MISSING** | Generic success message | No "what's next" |
| **Dispute status page** | ❌ **MISSING** | No tracking | Can't check progress |

**Gap Priority**: **MEDIUM** - Improves dispute quality, reduces frivolous disputes.

---

### 4E.5 Tutorial & Onboarding

**First-Time User Tutorial**:

```
┌──────────────────────────────────────────────────────────────────┐
│ WELCOME TO DELTACROWN! 🎮                                        │
├──────────────────────────────────────────────────────────────────┤
│ Let's get you started with your first tournament.               │
│                                                                  │
│ QUICK START GUIDE:                                               │
│                                                                  │
│ 1️⃣ Create or Join a Team                                        │
│    Tournaments require teams. You'll need 4 other players.      │
│    [Create Team] [Browse Teams Looking for Players]             │
│                                                                  │
│ 2️⃣ Link Your Game Account                                       │
│    We'll verify your skill level and match history.             │
│    [Link Valorant] [Link PUBG] [Link CS:GO]                     │
│                                                                  │
│ 3️⃣ Browse Tournaments                                            │
│    Find tournaments that match your skill and schedule.          │
│    [Browse Tournaments] [View Recommended]                       │
│                                                                  │
│ [Skip Tutorial] [Next Tip]                                       │
└──────────────────────────────────────────────────────────────────┘
```

**Interactive Walkthrough**:
- Highlight key UI elements on first visit
- Show tooltip: "This is where you submit match results"
- Offer to skip tutorial if experienced user

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **First-time tutorial** | ❌ **MISSING** | No onboarding | Users must discover features |
| **Interactive walkthrough** | ❌ **MISSING** | No UI highlights | Static pages only |
| **Quick start guide** | ❌ **MISSING** | No guide | External docs only |
| **Skip tutorial option** | ❌ **MISSING** | N/A | No tutorial to skip |

**Gap Priority**: **LOW** - Nice-to-have, but not critical.

---

## 4F. Expanded Missing Features List

### 4F.1 Core Functionality Gaps

**Registration & Eligibility**:
- ❌ Real-time eligibility validation (team size, skill, game account)
- ❌ Waitlist for full tournaments
- ❌ Registration approval workflow (organizer approves each team)
- ❌ Team substitution (replace player mid-tournament)
- ❌ Late registration (join after tournament starts, if allowed)

**Bracket Management**:
- ❌ Manual bracket creation (no auto-generation)
- ❌ Drag-and-drop bracket editor
- ❌ Bracket validation (ensure no impossible matchups)
- ❌ Bracket export (PDF, image, CSV)
- ❌ Bracket templates (save bracket structure for reuse)
- ❌ Dynamic bracket (add/remove participants after generation)

**Scheduling**:
- ❌ Calendar view for match scheduling
- ❌ Time zone conversion (show in participant's local time)
- ❌ Conflict detection (same team, 2 matches at once)
- ❌ Bulk scheduling (set all Round 1 matches at once)
- ❌ Recurring schedules (every match on the hour)
- ❌ iCal export (add matches to Google Calendar)

**Results**:
- ❌ Opponent confirmation workflow
- ❌ Results inbox for organizers
- ❌ Conflict resolution (both teams submit different results)
- ❌ Proof verification (organizer reviews screenshots)
- ❌ Result override (organizer changes result)
- ❌ Bulk result entry (offline tournaments)

**Multi-Stage Tournaments**:
- ❌ Stage model (Group Stage, Playoffs, Finals)
- ❌ Stage dependencies (Playoffs can't start until Groups complete)
- ❌ Advancement logic (top 2 from each group advance)
- ❌ Cross-stage bracket generation (Group winners seed into Playoffs)
- ❌ Stage-specific standings
- ❌ Swiss System pairing algorithm
- ❌ Best-of-N series (best-of-3, best-of-5)

---

### 4F.2 Organizer Tools

**Dashboard & Monitoring**:
- ❌ Organizer dashboard (stats, alerts, recent activity)
- ❌ Overdue match alerts
- ❌ Dispute queue (prioritized by severity)
- ❌ Payment monitoring (who paid, who didn't)
- ❌ Real-time activity feed (live tournament events)

**Manual Management**:
- ❌ Manual group creation & assignment
- ❌ Manual seeding (override auto-seeding)
- ❌ Manual match scheduling
- ❌ Manual result entry (organizer submits on behalf of teams)
- ❌ Forfeit workflow (mark team as no-show)
- ❌ Rematch ordering (reset match, order replay)

**Communication**:
- ❌ Announcement system (broadcast to all participants)
- ❌ Direct messaging (organizer → participant)
- ❌ Email notifications (not just in-app)
- ❌ Discord integration (auto-post updates to server)
- ❌ SMS notifications (for critical alerts)

**Administration**:
- ❌ Staff roles (delegate permissions to helpers)
- ❌ Referee system (assign referees to matches)
- ❌ Audit logs (track all organizer actions)
- ❌ Rollback capability (undo changes)
- ❌ Ban management (ban participants from future tournaments)
- ❌ Refund processing (issue refunds for cancelled tournaments)

---

### 4F.3 Participant Experience

**Registration**:
- ❌ Registration wizard (step-by-step flow)
- ❌ Team eligibility preview (see if team qualifies before registering)
- ❌ Payment plan (pay entry fee in installments)
- ❌ Group registration discount (register multiple teams, get discount)

**Match Experience**:
- ❌ Match reminders (notification 15 mins before match)
- ❌ Lobby creation assistance (auto-generate lobby code)
- ❌ Match chat (in-platform communication with opponent)
- ❌ Live match tracking (report progress mid-match)
- ❌ Match VOD upload (upload replay for organizer review)

**Results & Disputes**:
- ❌ Guided result submission (tooltips, validation)
- ❌ Dispute status tracking (see resolution progress)
- ❌ Appeal system (appeal organizer decision)

**Community**:
- ❌ Team profiles (showcase stats, achievements)
- ❌ Player profiles (personal stats, match history)
- ❌ Tournament badges (awards for winners, participants)
- ❌ Leaderboards (global rankings, ELO)
- ❌ Social sharing (share tournament results on Twitter, Discord)

---

### 4F.4 Technical Infrastructure

**Event System**:
- ❌ Comprehensive event coverage (all lifecycle events)
- ❌ Event replay (replay events for testing/debugging)
- ❌ Event handlers for stats, rankings, payouts
- ❌ Idempotency checks (prevent duplicate event processing)

**Integrations**:
- ❌ Discord bot (tournament updates in Discord servers)
- ❌ Twitch integration (embed live streams)
- ❌ Payment gateway (Stripe, PayPal for entry fees)
- ❌ Game API integration (Riot API for Valorant stats) - future
- ❌ Email service (SendGrid, AWS SES for notifications)

**Observability**:
- ❌ Performance monitoring (match result submission latency)
- ❌ Error tracking (Sentry for exceptions)
- ❌ Analytics (Google Analytics, Mixpanel for user behavior)
- ❌ Alerts (Slack alerts for critical issues)

**Testing**:
- ❌ End-to-end tests for tournament lifecycle
- ❌ Load testing (1000+ concurrent matches)
- ❌ Chaos engineering (fault injection for resilience testing)

---

### 4F.5 Advanced Features (Stretch Goals)

**AI/ML**:
- ❌ Skill-based matchmaking (pair similar-skill opponents)
- ❌ Fraud detection (detect fake screenshots, match-fixing)
- ❌ Predictive scheduling (optimize match times based on participant availability)
- ❌ Automated bracket balancing (distribute strong teams evenly)

**Gamification**:
- ❌ Achievement system (unlock badges for milestones)
- ❌ XP/leveling (earn XP from matches, level up)
- ❌ Seasons (ranked seasons with resets)
- ❌ Tournaments of the Month (featured tournaments with bonus prizes)

**Monetization**:
- ❌ Premium tournaments (paid entry, higher prizes)
- ❌ Sponsorships (display sponsor logos on tournament pages)
- ❌ Merchandise (sell branded gear)
- ❌ DeltaCoin economy (earn/spend virtual currency)

**Mobile App**:
- ❌ Mobile app (iOS, Android)
- ❌ Push notifications (match reminders, results)
- ❌ Mobile result submission (upload screenshots from phone)
- ❌ Mobile bracket viewing (touch-optimized bracket UI)

---

---

### 4B.6 Event-Driven Result Propagation

**After result finalization, events trigger cascading updates**:

```
MatchCompletedEvent published
        │
        ├──> Event Handler 1: BracketService.advance_winner()
        │    └──> Winner added to next round match
        │
        ├──> Event Handler 2: TeamStatsService.record_match_result()
        │    ├──> Team.matches_played += 1 (both teams)
        │    ├──> Team.matches_won += 1 (winner)
        │    └──> Team.win_rate recalculated
        │
        ├──> Event Handler 3: UserStatsService.record_match_result()
        │    ├──> User.matches_played += 1 (all players)
        │    ├──> User.matches_won += 1 (winning team players)
        │    └──> User.win_rate recalculated
        │
        ├──> Event Handler 4: MatchHistoryService.create_history_entry()
        │    └──> TeamMatchHistory record created
        │
        ├──> Event Handler 5: RankingService.update_elo_ratings()
        │    ├──> Winner ELO += 25
        │    └──> Loser ELO -= 25
        │
        ├──> Event Handler 6: PayoutService.award_match_bonus()
        │    └──> Winner receives DeltaCoin bonus (if configured)
        │
        └──> Event Handler 7: NotificationService.send_result_notifications()
             ├──> Winner notification: "You won! Advancing to Round 2."
             └──> Loser notification: "Match complete. Better luck next time."
```

**Idempotency**: All event handlers must be idempotent (safe to retry).

**Current State**:

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Event publishing on result** | ⚠️ **PARTIAL** | Some events exist | Not comprehensive |
| **Bracket advancement handler** | ✅ **EXISTS** | Works | Functional |
| **Team stats handler** | ❌ **MISSING** | No handler | Stats never update |
| **User stats handler** | ❌ **MISSING** | No handler | No user stats |
| **Match history handler** | ❌ **MISSING** | No handler | TeamMatchHistory empty |
| **ELO update handler** | ❌ **MISSING** | No ranking system | No ELO tracking |
| **Payout handler** | ⚠️ **PARTIAL** | Tournament prizes only | No per-match bonuses |
| **Notification handler** | ⚠️ **PARTIAL** | In-app only | No email |
| **Idempotency checks** | ❌ **MISSING** | No duplicate prevention | Handlers can run twice |

**Gap Priority**: **HIGH** - Event-driven propagation prevents forgotten updates.

---

## 5. Stage 4: Match Operations

### 5.1 Ideal Capabilities

**What a top-tier system should have**:

1. **Match Scheduling**:
   - First-round matches: Auto-scheduled based on tournament start time
   - Subsequent rounds: Auto-scheduled after previous round completes
   - Organizer can manually adjust match times
   - Participants notified of match schedule (email + in-app)

2. **Pre-Match Check-In**:
   - Check-in window: 15 minutes before match start
   - Both participants must check in (click "Ready" button)
   - If participant doesn't check in → Auto-forfeit or admin intervention
   - Check-in status visible to both teams and organizer

3. **Lobby Information**:
   - After check-in → Show lobby details:
     - Game server info (IP, password)
     - Voice chat link (Discord, TeamSpeak)
     - Map/mode selection
     - Spectator links (Twitch, YouTube)
   - Organizer can update lobby info in real-time

4. **Match Execution**:
   - Match goes "LIVE" after check-in
   - Live indicator on bracket (match in progress)
   - Optional: Live score updates (if API integration exists)
   - Optional: Spectator view (embed stream)

5. **Result Reporting**:
   - Either participant can submit result:
     - Winner/loser
     - Scores (if applicable)
     - Screenshot proof (optional)
   - Result submission triggers:
     - Opponent notification: "Opponent reported result, confirm?"
     - If opponent confirms → Match COMPLETED
     - If opponent disputes → Escalate to organizer

6. **Dispute Handling**:
   - Participant can dispute result (within 15 mins)
   - Dispute reason: dropdown (wrong score, no-show, cheating, other)
   - Organizer reviews:
     - View submitted scores from both sides
     - View screenshots
     - Chat with participants
     - Make final decision (approve original result or override)
   - Decision is final → Match COMPLETED

7. **Auto-Progression**:
   - Match COMPLETED → Winner auto-advances to next round
   - Next match auto-created (if bracket requires)
   - Loser eliminated (single elim) or moved to loser bracket (double elim)
   - Next round auto-scheduled (if all matches in round complete)

---

### 5.2 DeltaCrown Current State

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Auto-schedule first-round** | ⚠️ **PARTIAL** | Matches created, `scheduled_time=NULL` | No times set |
| **Auto-schedule subsequent rounds** | ❌ **MISSING** | No auto-scheduling logic | Organizer sets manually |
| **Manual match time adjustment** | ✅ **EXISTS** | Organizer can edit match times | Admin UI exists |
| **Match schedule notifications** | ❌ **MISSING** | No email/push notifications | Users check manually |
| **Check-in system** | ✅ **EXISTS** | `Match.CHECK_IN` state exists | Check-in logic implemented |
| **Check-in window (15 mins)** | ⚠️ **PARTIAL** | Check-in state exists, no timer | No auto-forfeit |
| **Auto-forfeit for no-show** | ❌ **MISSING** | No auto-forfeit logic | Manual admin decision |
| **Check-in status visibility** | ✅ **EXISTS** | Match detail page shows status | Visible to participants |
| **Lobby information display** | ⚠️ **PARTIAL** | `lobby_info` TextField exists | No structured fields |
| **Lobby info (server IP, password)** | ⚠️ **PARTIAL** | Stored as text blob | No structured schema |
| **Voice chat links** | ❌ **MISSING** | No Discord/TS integration | Text field only |
| **Spectator links** | ❌ **MISSING** | No stream embed | Manual links only |
| **Match goes LIVE** | ✅ **EXISTS** | `Match.LIVE` state exists | State machine works |
| **Live indicator on bracket** | ✅ **EXISTS** | LIVE matches highlighted | Color-coded |
| **Live score updates** | ❌ **MISSING** | No real-time score API | Final scores only |
| **Result reporting (by participant)** | ✅ **EXISTS** | Participants can submit results | Form exists |
| **Result submission includes scores** | ✅ **EXISTS** | `participant1_score`, `participant2_score` | Integer fields |
| **Screenshot proof upload** | ✅ **EXISTS** | `result_proof_image` field | S3 upload |
| **Opponent result confirmation** | ⚠️ **PARTIAL** | `Match.PENDING_RESULT` state exists | No confirm workflow |
| **Auto-confirm if opponent agrees** | ❌ **MISSING** | Organizer must confirm manually | No auto-confirm |
| **Dispute submission** | ✅ **EXISTS** | `Match.DISPUTED` state exists | Dispute flag exists |
| **Dispute reason dropdown** | ⚠️ **PARTIAL** | Free-text reason only | No structured reasons |
| **Organizer dispute review UI** | ✅ **EXISTS** | Admin can view disputes | Basic UI |
| **Chat with participants (dispute)** | ❌ **MISSING** | No in-app chat | Email communication only |
| **Auto-progression (winner advances)** | ✅ **EXISTS** | `BracketService.advance_winner()` | Works |
| **Auto-create next match** | ✅ **EXISTS** | Next round matches created | Works |
| **Auto-schedule next round** | ❌ **MISSING** | Matches created, no schedule | `scheduled_time=NULL` |

---

### 5.3 Key Gaps - Stage 4

**Must-Add Features**:
1. ❌ **Auto-schedule match times** (first round + subsequent rounds)
2. ❌ **Match schedule notifications** (email/push 1 hour before match)
3. ❌ **Auto-forfeit for no-show** (if no check-in within 15 mins)
4. ❌ **Result confirmation workflow** (opponent confirms → auto-complete)
5. ❌ **Structured lobby info** (server IP, password, voice chat as separate fields)

**Nice-to-Have**:
- In-app chat for disputes (participant ↔ organizer)
- Live score updates (API integration)
- Spectator stream embed (Twitch/YouTube)

---

## 6. Stage 5: Tournament Completion

### 6.1 Ideal Capabilities

**What a top-tier system should have**:

1. **Winner Determination**:
   - Auto-detect when final match completes
   - Traverse bracket to determine:
     - 1st place (champion)
     - 2nd place (runner-up)
     - 3rd place (if 3rd place match exists or semi-final losers)
   - Create `TournamentResult` record with placements

2. **Prize Distribution**:
   - Read `prize_distribution` JSONB (configured during tournament creation)
   - Auto-calculate prize amounts:
     - Example: Total pool $1,000 → 1st: $500, 2nd: $300, 3rd: $200
   - Transfer prizes to winners' wallets:
     - DeltaCoin: Instant transfer (via `EconomyService`)
     - Manual: Create payout records for admin processing
   - Idempotent (no double-payouts)
   - Log all transactions for audit

3. **Certificate Generation**:
   - Auto-generate certificates for:
     - Winner (1st place)
     - Runner-up (2nd place)
     - 3rd place
     - Optional: All participants (participation certificate)
   - Certificate includes:
     - Tournament name, game, date
     - Player/team name
     - Placement (1st, 2nd, 3rd, Participant)
     - QR code (verify authenticity)
     - Organizer signature
   - Formats: PDF (download) + PNG (share on social)
   - Store in S3, link from user profile

4. **Tournament Closure**:
   - Update tournament status: `COMPLETED`
   - Publish final results:
     - Results page (podium, all placements)
     - Bracket with all scores visible
   - Notify all participants:
     - Email: "Tournament completed! View results"
     - Winners: "You won! Prize deposited. Certificate ready."
   - Archive tournament (read-only, no more edits)

---

### 6.2 DeltaCrown Current State

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Auto-detect final match completion** | ⚠️ **PARTIAL** | Final match completes, no auto-trigger | Manual finalization |
| **Winner determination logic** | ✅ **EXISTS** | `WinnerService.determine_winner()` | Bracket traversal works |
| **1st/2nd/3rd placement** | ✅ **EXISTS** | `TournamentResult` model stores placements | Works |
| **Prize distribution config** | ✅ **EXISTS** | `prize_distribution` JSONB field | Configured at creation |
| **Auto-calculate prize amounts** | ✅ **EXISTS** | `PayoutService.process_payouts()` | Calculation works |
| **DeltaCoin prize transfer** | ✅ **EXISTS** | `EconomyService.add_funds()` | Instant transfer |
| **Manual payout records** | ⚠️ **PARTIAL** | Payout model exists, no workflow | No admin processing UI |
| **Payout idempotency** | ⚠️ **PARTIAL** | Basic checks, no idempotency keys | Risk of double-payout |
| **Transaction logging** | ✅ **EXISTS** | `Transaction` model logs all payouts | Audit trail exists |
| **Certificate generation** | ✅ **EXISTS** | `CertificateService.generate()` | PDF + PNG generation |
| **Certificate content (name, date, etc.)** | ✅ **EXISTS** | All details included | Template complete |
| **QR code on certificate** | ✅ **EXISTS** | QR code links to verification page | Works |
| **Store certificates in S3** | ✅ **EXISTS** | S3 upload implemented | Works |
| **Certificates for all participants** | ⚠️ **PARTIAL** | Can generate, not auto-triggered | Manual generation |
| **Auto-generate certificates** | ❌ **MISSING** | Manual trigger only | No auto-generation |
| **Tournament status → COMPLETED** | ✅ **EXISTS** | Manual status update | Organizer clicks "Finalize" |
| **Final results page** | ✅ **EXISTS** | `tournament_results.html` | Podium display |
| **Bracket with all scores** | ✅ **EXISTS** | Bracket view shows all scores | Works |
| **Email notification (completion)** | ❌ **MISSING** | No email service | In-app only |
| **Winner prize notification** | ❌ **MISSING** | No email notification | Users check dashboard |
| **Certificate ready notification** | ❌ **MISSING** | No email notification | Users check profile |
| **Archive tournament (read-only)** | ⚠️ **PARTIAL** | COMPLETED status prevents edits | No explicit archive flag |

---

### 6.3 Key Gaps - Stage 5

**Must-Add Features**:
1. ❌ **Auto-trigger finalization** (when final match completes)
2. ❌ **Auto-generate certificates** (bulk generation for all participants)
3. ❌ **Email notifications** (tournament complete, prize deposited, certificate ready)
4. ❌ **Payout idempotency keys** (prevent double-payouts on retry)

**Nice-to-Have**:
- Manual payout processing UI (for non-DeltaCoin prizes)
- Social share integration (share certificate on Twitter/Discord)

---

## 7. Stage 6: Post-Tournament Stats & History

### 7.1 Ideal Capabilities

**What a top-tier system should have**:

1. **Team Stats Updates**:
   - Auto-update after every match:
     - `matches_played` +1 (both teams)
     - `matches_won` +1 (winner)
     - `win_rate` recalculated: `(matches_won / matches_played) * 100`
   - Auto-update after tournament completion:
     - `tournaments_participated` +1 (all teams)
     - `tournaments_won` +1 (winner)
   - Fields should NEVER be manually updated (event-driven only)

2. **Team Tournament History**:
   - Create `TeamTournamentHistory` record for each team:
     - Tournament reference
     - Placement (1st, 2nd, 3rd, Top 8, etc.)
     - Matches played, matches won
     - DeltaCoin earned
     - Certificate link
   - Visible on team profile page ("Tournament History" tab)

3. **User Stats Updates**:
   - Auto-update after every match (for each player on team):
     - `matches_played` +1
     - `matches_won` +1 (if on winning team)
     - `win_rate` recalculated
   - Auto-update after tournament completion:
     - `tournaments_entered` +1
     - `tournaments_completed` +1
     - `tournaments_won` +1 (if 1st place)
     - `podium_finishes` +1 (if top 3)
     - `total_deltacoin_earned` += prize amount
   - Per-game breakdown: `game_stats` JSONB tracks stats per game

4. **User Tournament History**:
   - Create `UserTournamentHistory` record for each participant:
     - Tournament reference
     - Registration reference
     - Placement
     - Matches played, matches won
     - DeltaCoin earned
     - Certificate link
   - Visible on user profile page ("Tournament History" tab)

5. **Match History**:
   - Populate `TeamMatchHistory` model (currently unused):
     - Match reference
     - Team reference
     - Opponent team
     - Result (win/loss)
     - Score
     - Date
   - Visible on team profile ("Match History" tab)

6. **Leaderboard Updates**:
   - After tournament completion → Update global leaderboards:
     - ELO rating adjustments (based on match results)
     - Tournament points awarded (1st: 100pts, 2nd: 75pts, 3rd: 50pts)
     - Per-game rankings recalculated
   - Leaderboards auto-refresh (no manual recalculation)

7. **Profile Display**:
   - User profile shows:
     - Overall stats (W/L, tournaments won, total earnings)
     - Recent tournaments (last 5 with placements)
     - Achievements/badges (if system exists)
   - Team profile shows:
     - Team stats (W/L, tournament count, current streak)
     - Tournament history
     - Match history
     - Current ranking (per game)

---

### 7.2 DeltaCrown Current State

| Feature | Status | Evidence | Notes |
|---------|--------|----------|-------|
| **Team stats auto-update (matches)** | ❌ **MISSING** | No event handlers | Manual update only |
| **Team stats auto-update (tournaments)** | ❌ **MISSING** | No event handlers | Never updated |
| **Team.matches_played field** | ✅ **EXISTS** | Field exists in model | Always 0 (not updated) |
| **Team.matches_won field** | ✅ **EXISTS** | Field exists in model | Always 0 (not updated) |
| **Team.win_rate field** | ✅ **EXISTS** | Field exists in model | Always 0 (not updated) |
| **Team.tournaments_won field** | ✅ **EXISTS** | Field exists in model | Always 0 (not updated) |
| **TeamTournamentHistory model** | ❌ **MISSING** | No model exists | No team history tracking |
| **Team tournament history display** | ❌ **MISSING** | No UI exists | No history to display |
| **User stats auto-update (matches)** | ❌ **MISSING** | No event handlers | No user stats exist |
| **User stats auto-update (tournaments)** | ❌ **MISSING** | No event handlers | No user stats exist |
| **UserTournamentStats model** | ❌ **MISSING** | No model exists | No user stats tracking |
| **UserTournamentHistory model** | ❌ **MISSING** | No model exists | No user history tracking |
| **User tournament history display** | ❌ **MISSING** | No UI exists | No history to display |
| **TeamMatchHistory model** | ✅ **EXISTS** | Model exists in `teams/models/analytics.py` | NEVER populated |
| **TeamMatchHistory population** | ❌ **MISSING** | No service writes to it | Empty table |
| **Match history display** | ❌ **MISSING** | No UI exists | No data to display |
| **Leaderboard system** | ❌ **MISSING** | No leaderboards app | Planned feature |
| **ELO rating system** | ❌ **MISSING** | No ELO calculations | No ranking algorithm |
| **Tournament points system** | ❌ **MISSING** | No points awarded | No leaderboard integration |
| **User profile stats display** | ⚠️ **PARTIAL** | Basic profile exists | No tournament stats shown |
| **Team profile stats display** | ⚠️ **PARTIAL** | Basic team page exists | Stats always show 0 |
| **Achievements/badges** | ❌ **MISSING** | No achievement system | Future feature |

---

### 7.3 Key Gaps - Stage 6

**CRITICAL Missing Features** (Must-Add):
1. ❌ **Team stats auto-update** (event handlers for match/tournament completion)
2. ❌ **User stats tracking** (new models: `UserTournamentStats`, `UserTournamentHistory`)
3. ❌ **Match history population** (`TeamMatchHistory` exists but never used)
4. ❌ **Leaderboards system** (ELO ratings, tournament points, global rankings)

**Nice-to-Have**:
- Per-game stats breakdown (user JSONB field `game_stats`)
- Achievement/badge system
- Team ranking display on profile

---

## 8. Missing & Must-Add Features Summary

### 8.1 Critical Gaps (Blocking Full Lifecycle)

These features are **essential** for a complete end-to-end tournament experience:

| # | Feature | Current State | Impact | Priority |
|---|---------|---------------|--------|----------|
| 1 | **Email notifications** | ❌ No email service | Users miss important updates | 🔴 HIGH |
| 2 | **Team/user stats auto-update** | ❌ No event handlers | Stats always show 0, no progression | 🔴 HIGH |
| 3 | **User tournament history** | ❌ No models exist | Users can't see past tournaments | 🔴 HIGH |
| 4 | **Match auto-scheduling** | ⚠️ Matches created, no times | Participants don't know when to play | 🔴 HIGH |
| 5 | **Auto-generate certificates** | ⚠️ Manual trigger only | Winners don't get certificates | 🟡 MEDIUM |
| 6 | **Result confirmation workflow** | ⚠️ Organizer must confirm | Slow match progression | 🟡 MEDIUM |
| 7 | **Leaderboards/rankings** | ❌ No system exists | No competitive progression | 🟡 MEDIUM |
| 8 | **Draft persistence** | ❌ Session-only | Users lose progress on timeout | 🟡 MEDIUM |
| 9 | **Unique registration numbers** | ❌ No reg numbers | Hard to track registrations | 🟢 LOW |
| 10 | **Field locking** | ❌ All fields editable | Risk of fraud/errors | 🟢 LOW |

---

### 8.2 Feature Completeness by Stage

```
STAGE 1: DISCOVERY & BROWSING               [████████░░] 80% Complete
  ✅ Browse/filter/search                   EXISTS
  ✅ Tournament detail page                 EXISTS
  ❌ Email reminders                        MISSING
  ❌ Countdown timers                       MISSING

STAGE 2: REGISTRATION & PAYMENT             [██████░░░░] 60% Complete
  ✅ Auto-fill form                         EXISTS
  ✅ DeltaCoin payment                      EXISTS
  ✅ Manual payment upload                  EXISTS
  ❌ Email confirmation                     MISSING
  ❌ Draft persistence                      MISSING
  ❌ Field locking                          MISSING
  ❌ Unique reg numbers                     MISSING

STAGE 3: BRACKET & SEEDING                  [███████░░░] 70% Complete
  ✅ Bracket generation                     EXISTS
  ✅ Bracket visualization                  EXISTS
  ❌ Auto-schedule first round              MISSING
  ❌ Ranking-based seeding                  MISSING
  ❌ Bracket preview/edit                   MISSING

STAGE 4: MATCH OPERATIONS                   [██████░░░░] 60% Complete
  ✅ Check-in system                        EXISTS
  ✅ Result reporting                       EXISTS
  ✅ Dispute handling                       EXISTS
  ✅ Auto-progression                       EXISTS
  ❌ Match schedule notifications           MISSING
  ❌ Auto-forfeit no-shows                  MISSING
  ❌ Result auto-confirm                    MISSING
  ❌ Auto-schedule next round               MISSING

STAGE 5: TOURNAMENT COMPLETION              [███████░░░] 70% Complete
  ✅ Winner determination                   EXISTS
  ✅ Prize distribution                     EXISTS
  ✅ Certificate generation                 EXISTS
  ❌ Auto-generate certificates             MISSING
  ❌ Email notifications (winners)          MISSING
  ❌ Auto-trigger finalization              MISSING

STAGE 6: POST-TOURNAMENT STATS & HISTORY    [██░░░░░░░░] 20% Complete
  ❌ Team stats auto-update                 MISSING
  ❌ User stats tracking                    MISSING
  ❌ Match history population               MISSING
  ❌ Leaderboards/rankings                  MISSING
  ❌ Tournament history display             MISSING
```

**Overall Lifecycle Completeness**: **~60%**

---

### 8.3 Prioritized Implementation Plan

#### Phase 1: Core Missing Features (Weeks 1-4)

**Goal**: Fix critical gaps blocking full lifecycle.

**Deliverables**:
1. ✅ **Email notification service**:
   - Registration confirmation
   - Tournament completion
   - Prize deposited
   - Certificate ready
   - Match schedule reminders

2. ✅ **Team/user stats auto-update**:
   - Event handlers for `MatchCompletedEvent`
   - Event handlers for `TournamentCompletedEvent`
   - Create `UserTournamentStats` model
   - Create `UserTournamentHistory` model
   - Populate `TeamMatchHistory` on match completion

3. ✅ **Match auto-scheduling**:
   - Set `scheduled_time` for first-round matches
   - Auto-schedule subsequent rounds after previous round completes
   - Send match schedule notifications

---

#### Phase 2: Registration Improvements (Weeks 5-6)

**Goal**: Improve registration UX and data integrity.

**Deliverables**:
1. ✅ **Unique registration numbers**: `{GAME}-{YEAR}-{SEQUENCE}`
2. ✅ **Field locking**: Lock verified email, phone, game IDs
3. ✅ **Draft persistence**: Database-backed drafts with UUID
4. ✅ **Email confirmation**: Registration details + payment receipt

---

#### Phase 3: Match Operations Automation (Weeks 7-8)

**Goal**: Reduce manual intervention in match operations.

**Deliverables**:
1. ✅ **Result confirmation workflow**:
   - Opponent confirms result → Auto-complete
   - Auto-advance winner to next round
2. ✅ **Auto-forfeit for no-shows**:
   - If no check-in within 15 mins → Forfeit
   - Winner auto-advances
3. ✅ **Structured lobby info**:
   - Server IP, password, voice chat as separate fields
   - Display in clean UI

---

#### Phase 4: Leaderboards & Rankings (Weeks 9-12)

**Goal**: Competitive progression system.

**Deliverables**:
1. ✅ **Create leaderboards app**
2. ✅ **ELO rating system**:
   - Calculate ELO after each match
   - Update user/team ELO ratings
3. ✅ **Tournament points system**:
   - Award points based on placement (1st: 100, 2nd: 75, etc.)
   - Global leaderboard per game
4. ✅ **Leaderboard UI**:
   - Top 100 players per game
   - Top 100 teams per game
   - User/team rank display on profile

---

#### Phase 5: Post-Tournament Features (Weeks 13-14)

**Goal**: Complete post-tournament experience.

**Deliverables**:
1. ✅ **Auto-generate certificates**:
   - Bulk generation for all participants on tournament completion
   - Email notification when ready
2. ✅ **Tournament history UI**:
   - User profile: "My Tournaments" tab (past tournaments with placements)
   - Team profile: "Tournament History" tab
3. ✅ **Match history UI**:
   - Team profile: "Match History" tab (all matches with scores)

---

### 8.4 Essential vs. Nice-to-Have

#### Essential Features (Must-Add for MVP)

1. ✅ Email notifications (critical for user engagement)
2. ✅ Team/user stats auto-update (core competitive feature)
3. ✅ Match auto-scheduling (remove manual work)
4. ✅ User tournament history (users expect to see past tournaments)
5. ✅ Leaderboards (core competitive feature)

#### Nice-to-Have Features (Post-MVP)

1. ⚠️ Discord integration (webhooks, notifications)
2. ⚠️ Live score updates (requires game API integration)
3. ⚠️ Spectator stream embeds (Twitch, YouTube)
4. ⚠️ Achievement/badge system
5. ⚠️ In-app chat (participant ↔ organizer)
6. ⚠️ Payment gateway integration (Stripe, PayPal)
7. ⚠️ Calendar invite generation (.ics files)
8. ⚠️ Social sharing (share certificate, results)

---

## 9. Lifecycle Health Checklist

Use this checklist to verify each stage is fully functional:

### ✅ Stage 1: Discovery & Browsing
- [ ] Users can browse all tournaments (paginated)
- [ ] Users can filter by game, format, status
- [ ] Tournament cards show participant count (X/64 filled)
- [ ] Registration deadline visible on card
- [ ] Tournament detail page shows full rules, prizes, schedule
- [ ] Email reminders sent before registration closes

### ✅ Stage 2: Registration & Payment
- [ ] Eligibility checked before form display (age, rank, region)
- [ ] Form auto-fills from UserProfile and Team
- [ ] Verified fields are locked (email, game IDs)
- [ ] Unique registration number assigned (e.g., VCT-2025-001234)
- [ ] Draft persisted (resume on different device)
- [ ] DeltaCoin payment instant (wallet deducted, registration confirmed)
- [ ] Manual payment upload works (proof image → admin approval)
- [ ] Email confirmation sent (registration details + receipt)

### ✅ Stage 3: Bracket & Seeding
- [ ] Bracket auto-generated when registration closes
- [ ] First-round matches auto-scheduled (based on tournament start time)
- [ ] Bracket published, all participants notified (email + in-app)
- [ ] Bracket visualization shows all matches (interactive)
- [ ] Match statuses visible: Scheduled, Live, Completed

### ✅ Stage 4: Match Operations
- [ ] Match schedule notifications sent (1 hour before match)
- [ ] Check-in window opens (15 mins before match)
- [ ] Both participants must check in (click "Ready")
- [ ] Auto-forfeit if no check-in (after 15 mins)
- [ ] Lobby info displayed (server IP, password, voice chat)
- [ ] Match goes LIVE after check-in
- [ ] Either participant can submit result (scores + proof)
- [ ] Opponent confirms result → Auto-complete
- [ ] Opponent disputes result → Escalate to organizer
- [ ] Winner auto-advances to next round

### ✅ Stage 5: Tournament Completion
- [ ] Final match completion auto-triggers finalization
- [ ] Winner determined (1st, 2nd, 3rd placements)
- [ ] Prizes auto-distributed to wallets (DeltaCoin)
- [ ] Certificates auto-generated for all participants
- [ ] Email notifications sent (completion, prizes, certificates)
- [ ] Tournament status → COMPLETED
- [ ] Final results page visible (podium, full bracket)

### ✅ Stage 6: Post-Tournament Stats & History
- [ ] Team stats auto-updated (matches_played, matches_won, win_rate)
- [ ] User stats auto-updated (tournaments_entered, matches_won, etc.)
- [ ] Match history populated (TeamMatchHistory records created)
- [ ] Tournament history visible on user profile
- [ ] Tournament history visible on team profile
- [ ] Leaderboards auto-updated (ELO ratings, tournament points)
- [ ] User/team rank displayed on profile

---

## 10. Enhanced Feature Gaps Summary

### 10.1 Manual Tournament Management Capabilities

**Critical Gaps**:
- ❌ Manual bracket creation and editing (drag-and-drop bracket editor)
- ❌ Manual group assignment and balancing (Group Stage → Knockout transitions)
- ❌ Manual scheduling controls (calendar view, bulk scheduling, conflict detection)
- ❌ Manual result entry and override (organizer result submission, override workflow)
- ❌ Role-based permissions (Staff, Referee, Organizer roles with granular access)

**Impact**: Organizers have no control over tournament structure or results after generation. Any mistakes require database edits or starting over.

**Priority**: 🔴 **CRITICAL** - Professional tournaments require manual management tools.

---

### 10.2 Results Pipeline (No Game API Reality)

**Critical Gaps**:
- ❌ Result submission workflow (user/team submits with proof)
- ❌ Opponent confirmation/dispute system (confirm or dispute submitted results)
- ❌ Results inbox for organizers (centralized queue for pending/disputed results)
- ❌ Dispute resolution workflow (side-by-side evidence comparison, resolution actions)
- ❌ Result verification integration with TournamentOps (orchestrated approval pipeline)
- ❌ Event-driven result propagation (stats, rankings, payouts triggered by MatchCompletedEvent)

**Impact**: No verification mechanism for match results. Results immediately finalize with no review, creating potential for fraud and errors.

**Priority**: 🔴 **CRITICAL** - Without game API integration, manual verification is essential.

---

### 10.3 Multi-Stage Tournament Lifecycle

**Critical Gaps**:
- ❌ TournamentStage model (Group Stage, Playoffs, Finals as separate entities)
- ❌ Stage dependencies and transitions (automatic progression between stages)
- ❌ Group Stage → Knockout bracket generation (advancement logic, seeding from groups)
- ❌ Swiss System pairing algorithm (record-based pairing, rematch avoidance)
- ❌ Best-of-N series management (MatchSeries model, game-by-game tracking)
- ❌ Stage-specific scheduling and standings (per-stage dates, standings calculation)

**Impact**: Only single-stage tournaments possible. Cannot support complex formats like World Cup (Group → Knockout), qualifiers (Swiss → Top 8), or playoff series.

**Priority**: 🔴 **HIGH** - Multi-stage tournaments are common in esports and competitive gaming.

---

### 10.4 Organizer & Admin Panel Workflows

**Critical Gaps**:
- ❌ Comprehensive tournament dashboard (stats, alerts, activity feed, quick actions)
- ❌ Overdue match detection and alerts (automated reminders, auto-forfeit)
- ❌ Dispute queue and review interface (prioritized disputes, side-by-side evidence, resolution workflow)
- ❌ Audit logs and history tracking (all organizer actions logged with before/after snapshots)
- ❌ Guidance and help system (tooltips, wizards, suggested actions, help center)

**Impact**: Organizers lack visibility into tournament status and must manually track issues. No tools for common tasks like handling overdue matches or resolving disputes efficiently.

**Priority**: 🔴 **HIGH** - Dashboard and dispute resolution are critical for tournament operations.

---

### 10.5 User & Team Experience

**Critical Gaps**:
- ❌ Guided registration experience (wizard flow, real-time eligibility checks, error prevention)
- ❌ Match reporting guidance (tooltips, real-time validation, screenshot tips)
- ❌ Dispute submission experience (categorized reasons, counter-proof upload, status tracking)
- ❌ Tutorial and onboarding (first-time user walkthrough, interactive UI highlights)

**Impact**: High error rates in registration and result submission. Users confused about requirements and processes.

**Priority**: 🟡 **MEDIUM** - Improves UX and reduces errors, but tournaments can function without it.

---

### 10.6 Expanded Missing Features List

**Core Functionality** (Additional):
- ❌ Waitlist for full tournaments
- ❌ Registration approval workflow
- ❌ Team substitution (mid-tournament player replacement)
- ❌ Bracket templates (save/reuse bracket structures)
- ❌ Dynamic brackets (add/remove participants after generation)
- ❌ Bracket export (PDF, image, CSV)
- ❌ Time zone conversion and iCal export

**Organizer Tools** (Additional):
- ❌ Announcement system (broadcast to all participants)
- ❌ Direct messaging (organizer ↔ participant)
- ❌ Discord/SMS integration
- ❌ Ban management and refund processing
- ❌ Payment monitoring dashboard

**Participant Experience** (Additional):
- ❌ Payment plans (installment payments)
- ❌ Match reminders (15 mins before match)
- ❌ Match chat (in-platform communication)
- ❌ Match VOD upload (replay submission)
- ❌ Team/player profiles with badges and achievements

**Technical Infrastructure** (Additional):
- ❌ Comprehensive event coverage (all lifecycle events)
- ❌ Event replay capability (testing/debugging)
- ❌ Idempotency checks (prevent duplicate processing)
- ❌ Discord bot, Twitch integration, email service integration
- ❌ Performance monitoring, error tracking, analytics

**Advanced Features** (Stretch):
- ❌ AI/ML (skill-based matchmaking, fraud detection, predictive scheduling)
- ❌ Gamification (achievements, XP/leveling, seasons)
- ❌ Monetization (premium tournaments, sponsorships, DeltaCoin economy)
- ❌ Mobile app (iOS/Android with push notifications)

---

## 11. Revised Feature Completeness by Stage

```
STAGE 1: DISCOVERY & BROWSING                      [████████░░] 80% Complete
  ✅ Browse/filter/search                          EXISTS
  ✅ Tournament detail page                        EXISTS
  ❌ Email reminders                               MISSING
  ❌ Countdown timers                              MISSING

STAGE 2: REGISTRATION & PAYMENT                    [██████░░░░] 60% Complete
  ✅ Auto-fill form                                EXISTS
  ✅ DeltaCoin payment                             EXISTS
  ✅ Manual payment upload                         EXISTS
  ❌ Guided wizard                                 MISSING
  ❌ Real-time eligibility checks                  MISSING
  ❌ Email confirmation                            MISSING
  ❌ Draft persistence                             MISSING
  ❌ Field locking                                 MISSING
  ❌ Unique reg numbers                            MISSING

STAGE 3: BRACKET & SEEDING                         [████░░░░░░] 40% Complete
  ✅ Bracket generation (single-elim)             EXISTS
  ✅ Bracket visualization                         EXISTS
  ❌ Multi-stage tournaments                       MISSING
  ❌ Manual bracket creation/editing               MISSING
  ❌ Group stage support                           MISSING
  ❌ Swiss System                                  MISSING
  ❌ Best-of-N series                              MISSING
  ❌ Auto-schedule first round                     MISSING
  ❌ Ranking-based seeding                         MISSING
  ❌ Bracket preview/edit                          MISSING

STAGE 4: MATCH OPERATIONS                          [████░░░░░░] 40% Complete
  ✅ Check-in system                               EXISTS
  ✅ Result reporting                              EXISTS
  ✅ Dispute handling (basic)                      EXISTS
  ✅ Auto-progression                              EXISTS
  ❌ Results inbox (organizer verification)        MISSING
  ❌ Opponent confirmation/dispute workflow        MISSING
  ❌ Manual result entry/override                  MISSING
  ❌ Guided result submission                      MISSING
  ❌ Match schedule notifications                  MISSING
  ❌ Auto-forfeit no-shows                         MISSING
  ❌ Auto-schedule next round                      MISSING
  ❌ Calendar integration                          MISSING

STAGE 5: TOURNAMENT COMPLETION                     [███████░░░] 70% Complete
  ✅ Winner determination                          EXISTS
  ✅ Prize distribution                            EXISTS
  ✅ Certificate generation                        EXISTS
  ❌ Auto-generate certificates                    MISSING
  ❌ Email notifications (winners)                 MISSING
  ❌ Auto-trigger finalization                     MISSING

STAGE 6: POST-TOURNAMENT STATS & HISTORY           [██░░░░░░░░] 20% Complete
  ❌ Team stats auto-update                        MISSING
  ❌ User stats tracking                           MISSING
  ❌ Match history population                      MISSING
  ❌ Leaderboards/rankings                         MISSING
  ❌ Tournament history display                    MISSING

MANUAL MANAGEMENT CAPABILITIES                     [░░░░░░░░░░] 0% Complete
  ❌ Manual bracket creation/editing               MISSING
  ❌ Manual group assignment                       MISSING
  ❌ Manual scheduling controls                    MISSING
  ❌ Manual result entry/override                  MISSING
  ❌ Role-based permissions                        MISSING

RESULTS PIPELINE (NO GAME API)                     [██░░░░░░░░] 20% Complete
  ⚠️ User result submission                       PARTIAL (no proof required)
  ❌ Opponent confirmation/dispute                 MISSING
  ❌ Results inbox                                 MISSING
  ❌ Dispute resolution workflow                   MISSING
  ❌ TournamentOps integration                     MISSING
  ❌ Event-driven propagation                      MISSING

ORGANIZER & ADMIN PANELS                           [███░░░░░░░] 30% Complete
  ⚠️ Basic dashboard                              PARTIAL (no stats/alerts)
  ❌ Overdue match alerts                          MISSING
  ❌ Dispute queue                                 MISSING
  ❌ Audit logs                                    MISSING
  ❌ Guidance system                               MISSING

USER & TEAM EXPERIENCE                             [████░░░░░░] 40% Complete
  ⚠️ Registration form                            EXISTS (no guidance)
  ⚠️ Match page                                   EXISTS (no guidance)
  ❌ Guided registration wizard                    MISSING
  ❌ Guided result submission                      MISSING
  ❌ Dispute submission guidance                   MISSING
  ❌ Tutorial/onboarding                           MISSING
```

**Overall Lifecycle Completeness**: **~40%** (down from ~60% when considering all new requirements)

---

## 12. Revised Prioritized Implementation Plan

### Phase 1: Critical Missing Features (Weeks 1-6)

**Focus**: Core tournament lifecycle gaps + Results pipeline

**Deliverables**:
1. ✅ **Results Pipeline Foundation**:
   - `MatchResultSubmission` model (submission queue)
   - `DisputeRecord` enhancements (counter-proof, resolution tracking)
   - Opponent confirmation/dispute workflow
   - Results inbox UI (organizer verification queue)
   - `ResultVerificationService` (TournamentOps integration)

2. ✅ **Email Notification Service**:
   - Registration confirmation
   - Match schedule reminders (1 hour before)
   - Result submission notifications (opponent must confirm)
   - Dispute notifications (organizer review required)
   - Tournament completion (prizes, certificates)

3. ✅ **Team/User Stats Auto-Update**:
   - Event handlers for `MatchCompletedEvent`
   - Event handlers for `TournamentCompletedEvent`
   - Create `UserTournamentStats` model
   - Create `UserTournamentHistory` model
   - Populate `TeamMatchHistory` on match completion

4. ✅ **Match Auto-Scheduling**:
   - Set `scheduled_time` for first-round matches
   - Auto-schedule subsequent rounds after previous round completes
   - Send match schedule notifications

---

### Phase 2: Manual Management Tools (Weeks 7-10)

**Focus**: Organizer control and flexibility

**Deliverables**:
1. ✅ **Manual Bracket Editing**:
   - `BracketEditingService` (swap participants, override matches)
   - Bracket editor UI (drag-and-drop interface)
   - `BracketEditLog` model (audit trail for edits)
   - Bracket validation (ensure integrity before publishing)

2. ✅ **Manual Result Management**:
   - `ResultManagementService.enter_result_manual()` (organizer submits results)
   - `ResultManagementService.override_result()` (change existing results)
   - Result override UI with reason field
   - Override logging (audit trail)

3. ✅ **Manual Scheduling Controls**:
   - `MatchSchedulingService` (set match times, bulk schedule)
   - Calendar view UI (visual scheduling interface)
   - Conflict detection (same team, overlapping times)
   - Reschedule workflow (update time, notify participants)

4. ✅ **Role-Based Permissions**:
   - `TournamentStaff` model (Staff, Referee roles)
   - Permission checks (role-based actions)
   - Staff assignment UI (organizer delegates permissions)

---

### Phase 3: Multi-Stage Tournaments (Weeks 11-16)

**Focus**: Complex tournament formats

**Deliverables**:
1. ✅ **Stage Infrastructure**:
   - `TournamentStage` model (name, order, format, dates, dependencies)
   - Stage progression service (completion detection, transition logic)
   - Stage-specific standings calculation

2. ✅ **Group Stage → Knockout**:
   - `GroupManagementService` (create groups, assign participants)
   - Group assignment UI (drag-and-drop)
   - Advancement logic (top N from each group)
   - Knockout bracket generation from group standings

3. ✅ **Swiss System**:
   - `SwissPairingService` (record-based pairing algorithm)
   - Rematch avoidance logic
   - Bye handling (odd participant count)
   - Top cut selection (Swiss → Single Elimination)

4. ✅ **Best-of-N Series**:
   - `MatchSeries` model (series container)
   - `Game` model (individual games within series)
   - Series progression logic (first to N wins)
   - Series result submission UI

---

### Phase 4: Organizer & Admin Panels (Weeks 17-20)

**Focus**: Dashboard and operational tools

**Deliverables**:
1. ✅ **Enhanced Dashboard**:
   - Quick stats (registrations, matches, disputes, payments)
   - Alerts system (overdue matches, pending disputes)
   - Activity feed (real-time tournament events)
   - Quick actions (edit, inbox, schedule, announce)

2. ✅ **Overdue Match Management**:
   - Overdue detection (periodic task every 15 mins)
   - Automated reminders (15 mins, 30 mins, 60 mins overdue)
   - Auto-forfeit workflow (configurable timeout)
   - Manual forfeit actions (forfeit one, forfeit both)

3. ✅ **Dispute Queue & Resolution**:
   - Dispute queue UI (prioritized by age/severity)
   - Dispute review page (side-by-side evidence comparison)
   - Resolution actions (approve original, approve dispute, rematch, request info)
   - Resolution logging (`DisputeRecord.resolution`, `resolution_notes`)

4. ✅ **Audit Logs**:
   - `TournamentAuditLog` model (action, target, changes, reason)
   - Audit log UI (chronological list with filters)
   - Rollback capability (apply before state)

---

### Phase 5: User Experience & Guidance (Weeks 21-24)

**Focus**: Participant-facing improvements

**Deliverables**:
1. ✅ **Guided Registration**:
   - Registration wizard (multi-step flow)
   - Real-time eligibility checks (team size, skill, linked accounts)
   - Error prevention (can't proceed if ineligible)
   - Clear error messages with fix links

2. ✅ **Guided Match Reporting**:
   - Match page guidance ("What to do now" section)
   - Real-time result validation (winner matches scores)
   - Screenshot tips (what to upload)
   - Confirmation checkbox (explicit accuracy confirmation)

3. ✅ **Guided Dispute Submission**:
   - Dispute form with categorized reasons
   - Counter-proof upload
   - Character minimum (prevent "No" disputes)
   - False dispute warning (deter frivolous disputes)
   - Post-submission guidance ("What happens next")

4. ✅ **Tutorial & Onboarding**:
   - First-time user tutorial (quick start guide)
   - Interactive walkthrough (highlight key UI elements)
   - Skip tutorial option

---

### Phase 6: Leaderboards & Rankings (Weeks 25-28)

**Focus**: Competitive progression system

**Deliverables**:
1. ✅ **Leaderboards App**:
   - Create `leaderboards` app
   - `UserRanking` model (ELO, tournament points per game)
   - `TeamRanking` model (team ELO, tournament points)

2. ✅ **ELO Rating System**:
   - ELO calculation algorithm (K-factor based on match importance)
   - Event handler for `MatchCompletedEvent` (update ELO)
   - Display ELO on user/team profiles

3. ✅ **Tournament Points System**:
   - Points awarded by placement (1st: 100, 2nd: 75, 3rd: 50, etc.)
   - Event handler for `TournamentCompletedEvent` (award points)
   - Global leaderboard per game (top 100)

4. ✅ **Leaderboard UI**:
   - Top players per game (filterable)
   - Top teams per game (filterable)
   - User rank display on profile ("Ranked #342 in Valorant")
   - Team rank display on profile

---

### Phase 7: Post-Tournament Features (Weeks 29-32)

**Focus**: Complete post-tournament experience

**Deliverables**:
1. ✅ **Auto-Certificate Generation**:
   - Bulk generation on tournament completion (all participants)
   - Email notification when certificates ready
   - Certificate download link in tournament history

2. ✅ **Tournament History UI**:
   - User profile: "My Tournaments" tab (past tournaments with placements)
   - Team profile: "Tournament History" tab (all team tournaments)
   - Tournament card shows: Name, date, placement, prize won

3. ✅ **Match History UI**:
   - Team profile: "Match History" tab (all matches with scores)
   - Match card shows: Opponent, result (W/L), score, date, tournament
   - Filter by tournament, game, date range

---

## 13. Essential vs. Nice-to-Have (Revised)

### Essential Features (Must-Add for Production)

**Tier 1** (Blocking Production):
1. ✅ Results pipeline (submission → verification → finalization)
2. ✅ Email notifications (critical for user engagement)
3. ✅ Team/user stats auto-update (core competitive feature)
4. ✅ Match auto-scheduling (remove manual work)
5. ✅ User tournament history (users expect to see past tournaments)

**Tier 2** (Needed for Professional Tournaments):
6. ✅ Manual bracket editing (organizers need control)
7. ✅ Manual result entry/override (dispute resolution)
8. ✅ Results inbox (organizer verification queue)
9. ✅ Dispute resolution workflow (fair tournament operations)
10. ✅ Overdue match alerts (prevent tournament stalls)

**Tier 3** (Important for Competitive Scene):
11. ✅ Leaderboards & ELO (core competitive feature)
12. ✅ Multi-stage tournaments (Group → Knockout, Swiss → Top 8)
13. ✅ Organizer dashboard (visibility and control)
14. ✅ Audit logs (transparency and debugging)

### Nice-to-Have Features (Post-MVP Enhancements)

**User Experience**:
- ⚠️ Guided registration wizard (reduces errors, but not critical)
- ⚠️ Guided result submission (improves accuracy, but optional)
- ⚠️ Tutorial/onboarding (helpful for new users, not essential)

**Integrations**:
- ⚠️ Discord bot (notifications in Discord servers)
- ⚠️ Twitch integration (embed live streams)
- ⚠️ SMS notifications (critical alerts via text)

**Advanced Features**:
- ⚠️ Payment gateway integration (Stripe, PayPal for entry fees)
- ⚠️ Live score updates (requires game API integration - future)
- ⚠️ Achievement/badge system (gamification)
- ⚠️ In-app chat (participant ↔ organizer communication)
- ⚠️ Calendar invite generation (.ics files for match schedules)
- ⚠️ Social sharing (share certificates, results on social media)

**Stretch Goals**:
- ⚠️ AI/ML fraud detection (detect fake screenshots, match-fixing)
- ⚠️ Skill-based matchmaking (pair similar-skill opponents)
- ⚠️ Mobile app (iOS/Android with push notifications)
- ⚠️ Seasons & ranked play (ranked seasons with resets)

---

## 14. Final Conclusion

### Revised Current State Summary

**What DeltaCrown Does Well**:
- ✅ Basic tournament creation and configuration
- ✅ Bracket generation and visualization (single elimination only)
- ✅ Basic match state management (check-in, live, result reporting)
- ✅ Prize distribution (DeltaCoin auto-transfer)
- ✅ Certificate generation (PDF + PNG with QR codes)
- ✅ Auto-progression (winner advances to next round - basic)

**Critical Missing Pieces** (Expanded Analysis):

**1. Results Pipeline** (🔴 CRITICAL):
- No verification workflow (results immediately final, no review)
- No opponent confirmation/dispute system
- No organizer results inbox (no centralized verification queue)
- No proof requirement enforcement (can submit without screenshot)
- No event-driven propagation (stats/rankings never update)

**2. Manual Management Capabilities** (🔴 CRITICAL):
- No manual bracket creation or editing (auto-generation only)
- No manual result entry or override (organizer can't fix errors)
- No manual scheduling controls (no calendar view, conflict detection)
- No role-based permissions (organizer must do everything)

**3. Multi-Stage Tournaments** (🔴 HIGH):
- No stage concept (single-stage tournaments only)
- No Group Stage → Knockout transitions
- No Swiss System support
- No Best-of-N series (best-of-3, best-of-5)

**4. Organizer & Admin Tools** (🔴 HIGH):
- No comprehensive dashboard (stats, alerts, activity feed)
- No overdue match detection or alerts
- No dispute queue or review interface
- No audit logs (no action history tracking)

**5. Post-Tournament Features** (🔴 HIGH):
- No team/user stats auto-update (stats always 0)
- No user tournament history (no models exist)
- No match history population (`TeamMatchHistory` exists but empty)
- No leaderboards or rankings (no ELO, no tournament points)

**6. User Experience** (🟡 MEDIUM):
- No guided registration (high error rates)
- No guided result submission (screenshot tips, validation)
- No tutorial/onboarding (new users confused)

**Overall Assessment**: DeltaCrown has **~40% of a complete, professional tournament platform**. The basic tournament flow works (create → register → bracket → matches → winners), but lacks:
- **Verification systems** (results pipeline)
- **Manual control** (editing, overrides)
- **Complex formats** (multi-stage, Swiss, series)
- **Operational tools** (dashboard, dispute queue, audit logs)
- **Competitive features** (stats, history, rankings)

### Success Criteria for Production Readiness

DeltaCrown will be **production-ready** when:

1. ✅ **Results Pipeline Complete**:
   - Results require proof (screenshot upload mandatory)
   - Opponent must confirm or dispute results
   - Organizer reviews all results in inbox before finalizing
   - Disputes resolved with clear workflow (approve, reject, rematch)

2. ✅ **Manual Management Available**:
   - Organizers can manually edit brackets (swap, override)
   - Organizers can manually enter/override results
   - Organizers can manually schedule matches (calendar view)
   - Staff roles implemented (delegate permissions)

3. ✅ **Stats & History Functional**:
   - Team stats auto-update after every match
   - User stats auto-update after every match
   - Match history populated (`TeamMatchHistory`)
   - Tournament history visible on profiles
   - Leaderboards show ELO and tournament points

4. ✅ **Email Notifications Active**:
   - Registration confirmation
   - Match schedule reminders
   - Result submission notifications
   - Dispute notifications
   - Tournament completion

5. ✅ **Multi-Stage Support** (For Complex Tournaments):
   - Stage model implemented
   - Group Stage → Knockout transitions working
   - Swiss System pairing functional
   - Best-of-N series management available

6. ✅ **Organizer Dashboard Functional**:
   - Stats, alerts, activity feed visible
   - Overdue match alerts working
   - Dispute queue accessible
   - Audit logs tracking all actions

### Implementation Timeline

- **Phase 1** (Weeks 1-6): Results Pipeline + Core Missing Features → **60% Complete**
- **Phase 2** (Weeks 7-10): Manual Management Tools → **70% Complete**
- **Phase 3** (Weeks 11-16): Multi-Stage Tournaments → **80% Complete**
- **Phase 4** (Weeks 17-20): Organizer & Admin Panels → **90% Complete**
- **Phase 5** (Weeks 21-24): User Experience & Guidance → **95% Complete**
- **Phase 6** (Weeks 25-28): Leaderboards & Rankings → **100% Complete**
- **Phase 7** (Weeks 29-32): Post-Tournament Features → **100% + Polish**

**Total Timeline**: **32 weeks (8 months)** to full production readiness.

By addressing these expanded gaps systematically, DeltaCrown will transform from a **basic tournament system** into a **comprehensive, professional tournament platform** capable of handling complex formats, ensuring result integrity, and providing world-class organizer and participant experiences.

---

**End of Enhanced Lifecycle Gaps Analysis**
