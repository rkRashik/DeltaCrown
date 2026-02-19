# All 62 Questions Answered — DeltaCrown Registration System

> **Date:** February 19, 2026  
> **Context:** These are answers to all questions about how the registration system should work, based on codebase analysis, 59 prior planning docs, and platform research (Toornament, Battlefy, Start.gg, Challonge, FACEIT).

---

## Section 1: Core Registration Modes

### Q1. What are the registration types/modes?

Three registration modes, all served by the same `SmartRegistrationView`:

| Mode | When Used | How It Works |
|------|-----------|-------------|
| **Solo** | `tournament.registration_type = "solo"` | One player registers themselves. Form shows player + game info. |
| **Team** | `tournament.registration_type = "team"` | Captain/manager registers the entire team. Form shows team selector + roster + captain info. |
| **Guest Team** | `tournament.registration_type = "team"` + `allow_guest_teams = True` | Captain registers an external team by manually entering member info. Team members don't need DeltaCrown accounts. |

All three modes use the same view, same URL (`/tournaments/<slug>/register/`), same template (with conditional sections). The tournament configuration determines which mode and which sections appear.

### Q2. How does a solo player register?

1. Player visits tournament page → clicks "Register"
2. System checks eligibility (logged in, registration open, capacity, game passport exists, not already registered, meets any tournament rules)
3. If eligible → shows Smart Registration form:
   - **Player Info** (auto-filled from UserProfile): name, email, phone, country, Discord
   - **Game Info** (auto-filled from GamePassport): in-game name, game ID, rank, platform
   - **Custom Questions** (if organizer added any)
   - **Payment** (if entry fee > 0): method selection
4. Player reviews → clicks "Submit Registration"
5. Backend creates `Registration` (user=player, team=null, registration_type='solo')
6. Redirected to success page with registration number and next steps

### Q3. How does a team register?

1. Captain/manager visits tournament page → clicks "Register"
2. System checks:
   - Does user have teams for this game?
   - Does user have permission to register? (owner/manager/captain only)
   - Does team meet size requirements?
3. If multiple eligible teams → user picks one from dropdown
4. If one eligible team → auto-selected
5. Form shows:
   - **Team Info**: name, tag, logo (all auto-filled, locked)
   - **Roster**: all members with their game IDs, rank, role (auto-filled from each member's GamePassport)
   - **Captain Info**: registering user's info (auto-filled)
   - **Custom Questions + Payment** (same as solo)
6. On submit: creates `Registration` (user=captain, team_id=team, registration_type='team') + stores `lineup_snapshot` JSON

### Q4. How does the system decide solo vs team mode?

The `Tournament` model has a `registration_type` field (CharField with choices). The organizer sets this when creating the tournament. The SmartRegistrationView reads `tournament.registration_type` and adjusts:

- `"solo"` → no team section, no roster, just player fields
- `"team"` → adds team selection, roster display, captain info
- `"team"` + `allow_guest_teams` → also shows "Register as Guest Team" option

There is no mixed mode. A tournament is either solo or team, not both.

---

## Section 2: Smart Registration Logic

### Q5. What does "smart" registration mean?

"Smart" means the system does the work, not the user. Specifically:

1. **Auto-fill**: Pre-populates form fields from UserProfile, GamePassport, and Team data
2. **Auto-detect**: Determines which fields to show based on tournament game and type
3. **Readiness score**: Shows percentage of fields already filled and flags missing ones
4. **Field locking**: Locks verified fields (email, name) to prevent fraud
5. **Eligibility pre-check**: Evaluates rules before showing the form, prevents wasted effort
6. **One-page**: No multi-step wizard. Scroll through sections, everything visible at once.

### Q6. What data sources feed auto-fill?

Priority order (highest wins):

| Priority | Source | What It Provides |
|----------|--------|-----------------|
| 1 | Previous registration for this tournament (edit/retry) | All previously entered data |
| 2 | GamePassport for tournament's game | IGN, game ID, rank, platform |
| 3 | UserProfile | Name, email, phone, country, avatar, Discord |
| 4 | Team data | Team name, tag, logo, roster |
| 5 | Previous registrations (other tournaments, same game) | Common field values |

### Q7. Which fields are auto-filled vs manual?

| Field | Auto-fill Source | Editable? |
|-------|-----------------|-----------|
| Full name | UserProfile.display_name | ❌ Locked |
| Email | User.email | ❌ Locked |
| Phone | UserProfile.phone_number | ✅ Yes |
| Country | UserProfile.country | ✅ Yes |
| Avatar | UserProfile.avatar | Display only |
| In-game name | GamePassport.ign | ✅ Override allowed |
| Game ID | GamePassport.game_specific_id | ✅ Override allowed |
| Rank | GamePassport.rank | ✅ Override allowed |
| Platform | GamePassport.platform | ✅ Yes |
| Discord | UserProfile.discord_username | ✅ Yes |
| Team name | Team.name | ❌ Locked |
| Team tag | Team.tag | ❌ Locked |
| Custom questions | Not auto-filled | ✅ Manual entry |

### Q8. What is the readiness score?

A percentage showing how complete the form is before the user touches it:

```
Readiness: ████████░░ 80% (8/10 fields filled)
Missing:
  ⚠️ Phone number — [Add to profile →]
  ⚠️ Discord username — [Add to profile →]
```

The "Add to profile" links go to the user's profile page with a `?next=` URL so they return to the registration form after updating.

The score helps users understand what they need to fill in and encourages profile completion.

### Q9. What happens if auto-fill data is wrong/outdated?

Override-allowed fields (Game ID, Rank, Platform) can be changed during registration. The value entered in registration is what gets stored — it does NOT update the GamePassport or UserProfile. The user can separately update their profile/passport if they want the new data to persist.

Locked fields (Name, Email, Team Name) cannot be changed during registration. If they need to be changed, the user must update their profile first and then register.

### Q10. How does the system know which game-specific fields to show?

The tournament has a `game_id` field. Each game has different relevant fields:

| Game | Key Fields |
|------|-----------|
| Valorant | Riot ID, Rank (Iron→Radiant), Region |
| Dota 2 | Steam ID, MMR, Medal |
| League of Legends | Riot ID, Rank, Server |
| Overwatch 2 | BattleTag, Rank, Role |
| CS2 | Steam ID, Rank, FACEIT Level |
| PUBG Mobile | PUBG ID, Tier, Server |
| Mobile Legends | ML ID, Rank, Server |

The `RegistrationAutoFillService` has game-specific mappings. When a new game is added, the field mapping is added to the service configuration.

Future: use `GamePlayerIdentityConfig` model so adding a new game = adding DB rows via admin panel, zero code deployment.

---

## Section 3: User Without a Team

### Q11. What if a solo player doesn't have a team but the tournament is team-only?

The eligibility check catches this early. The player is shown the ineligible page:

```
❌ You don't have a team for Valorant

To register for this team tournament, you need to be on a team.

Options:
[Create a Team →]  [Join an existing team →]  [Browse Teams →]
```

They are NOT shown the registration form at all.

### Q12. What if the user has a team but isn't the captain?

The system checks the user's `TeamMembership` role:

- `OWNER` / `MANAGER` → can always register the team
- `is_tournament_captain = True` → can register the team
- Regular member → depends on team settings (`can_register_tournaments` permission flag)

If the user doesn't have permission:

```
❌ You don't have permission to register Phoenix Rising

Only team owners, managers, or designated captains can register
the team for tournaments.

Contact your team captain to register, or ask them to grant
you registration permissions.
```

### Q13. Can a player create a team during registration?

Not inline (yet). The plan is:

**Current (Phase A):** Show a "Create a Team" link that goes to the team creation page with a `?next=` return URL. After creating the team, the user is sent back to the registration page.

**Future (Phase C):** Inline team creation modal within the registration form. User fills in team name, tag, invites members, and continues registration without leaving the page.

### Q14. What if the team doesn't have enough members?

The team is shown in the team selector but with a warning:

```
○ Shadow Squad (3 members) ⚠️
  ↳ This tournament requires 5 players minimum. You need 2 more.
  [Invite Players →]
```

The team cannot be selected for registration until it meets the minimum size. The "Invite Players" link goes to the team management page.

---

## Section 4: Guest Team

### Q15. What is a guest team?

A guest team is a team where:
- The captain has a DeltaCrown account
- Some or all teammates do NOT have DeltaCrown accounts
- The captain manually enters teammate info (name, game ID, contact)

Guest teams are stored in the registration's `guest_team_data` JSON field, not as a real `Team` in the database.

### Q16. When are guest teams allowed?

Only when the tournament organizer enables `allow_guest_teams = True` in tournament settings. By default, it's off.

Use cases:
- Local LAN tournaments with walk-in teams
- Open tournaments wanting maximum participation
- Transitioning communities from other platforms

### Q17. How does a guest team register?

1. Captain visits tournament page → Register
2. System shows three options:
   - Register with existing team (if they have teams)
   - Create a new team & register
   - Register as guest team
3. Captain chooses "Guest Team" and fills:
   - Team name, team tag, optional logo
   - Roster: manually enter each player's name, game ID, role, contact (Discord/email)
   - Captain is auto-filled as first roster entry
   - Must meet minimum player count
4. On submit: `Registration` created with `is_guest_team=True`, `guest_team_data` = all the entered info
5. Status is **always** `needs_review` for guest teams (never auto-approved)

### Q18. How does the organizer verify a guest team?

In the registration detail view, the organizer sees:

- Guest team flag: "⚠️ Guest Team — Manual verification required"
- Team info: name, tag, logo
- Roster: each manually entered member with their game ID and contact
- Organizer can:
  - Click game IDs to verify on tracker sites
  - Contact captain via provided Discord/email
  - Approve or reject the registration

### Q19. Can a guest team convert to a real team?

Yes, through a "smart conversion" path (Phase C/D feature):

1. After guest registration, captain sees: "Unlock full features — invite teammates to DeltaCrown"
2. Captain shares invite link
3. Teammates create accounts and set up Game Passports
4. System matches game IDs from guest roster to new accounts
5. Once all members are on the platform → guest team can be converted to a real `Team`
6. Future registrations use the real team (with auto-fill)

This is optional. Guest registration works fully without it.

### Q20. What data is stored for guest teams?

```json
{
  "guest_team": {
    "name": "Apex Predators",
    "tag": "APX",
    "logo_url": "/media/guest_teams/apx_logo.png",
    "captain_user_id": 123,
    "roster": [
      {
        "name": "Ahmed (Captain)",
        "game_id": "Ahmed#BD01",
        "role": "captain",
        "contact": "ahmed#1234",
        "is_platform_user": true,
        "user_id": 123
      },
      {
        "name": "Rafiq",
        "game_id": "Rafiq#5678",
        "role": "player",
        "contact": "rafiq@discord",
        "is_platform_user": false,
        "user_id": null
      }
    ]
  }
}
```

---

## Section 5: Data Validation & Eligibility

### Q21. What eligibility checks run before showing the form?

Checks are run in order, stopping at the first failure:

| # | Check | Fail Message |
|---|-------|--------------|
| 1 | User is authenticated | Redirect to login |
| 2 | Registration is open (between start/end dates) | "Registration is not open yet" / "Registration has closed" |
| 3 | User hasn't already registered for this tournament | "You've already registered" |
| 4 | Capacity available (confirmed < max_participants) | "Tournament is full" (offer waitlist if enabled) |
| 5 | User has Game Passport for this game | "Set up your [Game] profile first" |
| 6 | (Team mode) User has teams for this game | "You need a team" |
| 7 | (Team mode) User has permission to register team | "Contact your team captain" |
| 8 | (Team mode) Team meets size requirements | "Need X more players" |
| 9 | Tournament-specific rules (RegistrationRule) | Dynamic message based on rule |

### Q22. What tournament-specific eligibility rules can organizers set?

Via the `RegistrationRule` model:

| Rule | Example Config | What It Checks |
|------|---------------|---------------|
| Minimum rank | `{"min_rank": "Diamond"}` | Player's GamePassport rank ≥ Diamond |
| Maximum rank | `{"max_rank": "Gold"}` | For amateur tournaments |
| Minimum age | `{"min_age": 16}` | Player's profile DOB |
| Maximum age | `{"max_age": 25}` | For under-25 tournaments |
| Region lock | `{"regions": ["BD", "IN"]}` | Player's country |
| Platform lock | `{"platforms": ["PC"]}` | Must be on specified platform |
| Verified email | `{"require_verified_email": true}` | Email must be verified |
| Previous participation | `{"require_previous": true}` | Must have competed before |
| Auto-approve | `{"conditions": {...}}` | Skip manual review if conditions met |
| Auto-reject | `{"conditions": {...}}` | Reject if conditions met |
| Flag for review | `{"conditions": {...}}` | Send to review queue if conditions met |

Currently: Rules model exists but is NOT automatically evaluated. Organizer checks manually.
Future: Wire rule evaluation into the eligibility check pipeline.

### Q23. How are game IDs validated?

**Current (Manual):**
- Format validation only (e.g., Riot ID must contain `#`)
- Organizer manually verifies by clicking links to tracker.gg, op.gg, etc.
- System provides quick links: `https://tracker.gg/valorant/profile/riot/{game_id}`

**Future (Automated):**
- API integration with game platforms
- Verify game ID exists and is active
- Pull rank data automatically
- Flag discrepancies (user says Diamond, API says Gold)

### Q24. What if required data is missing?

The form shows warnings next to incomplete sections and blocks submission if required fields are empty:

- Required fields: highlighted with red border + error message
- Readiness bar drops below 100%: "Fill all required fields to submit"
- Profile-linked missing data: "Add your phone number to your profile" with link

The submit button is disabled until all required fields are filled. JavaScript validates client-side, server validates again on POST.

### Q25. How does duplicate player detection work?

When a team registers, the system checks if any team member's game ID appears in another registration for the same tournament:

```python
# Check if game_id already registered for this tournament
existing = Registration.objects.filter(
    tournament=tournament,
    status__in=['submitted', 'pending', 'confirmed', 'payment_submitted'],
).exclude(team_id=team.id)

for member in roster:
    # Check in lineup_snapshot JSON and guest_team_data JSON
    if member.game_id found in existing registrations:
        flag_duplicate(member, existing_registration)
```

If duplicates are found:
- Registration is created but status → `needs_review`
- Organizer sees: "⚠️ Duplicate player detected: PlayerX#1234 also registered with Team Alpha"
- Organizer resolves the conflict manually

---

## Section 6: Custom Questions

### Q26. Can organizers add custom questions to the registration form?

Yes. Using the `RegistrationQuestion` model, organizers can add unlimited custom questions to their tournament's registration form.

### Q27. What types of custom questions are supported?

| Type | HTML Input | Example |
|------|-----------|---------|
| Text | `<input type="text">` | "What is your Discord username?" |
| Textarea | `<textarea>` | "Tell us about your team's competitive history" |
| Number | `<input type="number">` | "How many hours per week do you practice?" |
| Email | `<input type="email">` | "Team manager's email" |
| URL | `<input type="url">` | "Link to your stream" |
| Phone | `<input type="tel">` | "Emergency contact number" |
| Select | `<select>` | "Which role do you main?" (dropdown) |
| Radio | `<input type="radio">` | "Preferred match time?" (one choice) |
| Checkbox | `<input type="checkbox">` | "I agree to the tournament rules" |
| Multi-select | `<select multiple>` | "Which maps do you prefer?" (multiple) |
| Date | `<input type="date">` | "Date of birth" |
| File | `<input type="file">` | "Upload proof of identity" |

### Q28. Can questions be conditional?

Yes. `RegistrationQuestion` has `condition_field` and `condition_value` fields:

```python
# Only show this question if registration_type is "guest_team"
RegistrationQuestion(
    question_text="How did you hear about this tournament?",
    condition_field="is_guest_team",
    condition_value="true"
)
```

When the condition is met, the question appears. Otherwise it's hidden.

### Q29. Where are custom question answers stored?

In the `RegistrationAnswer` model:

```python
class RegistrationAnswer(models.Model):
    registration = ForeignKey(Registration)
    question = ForeignKey(RegistrationQuestion)
    answer_text = TextField()
    normalized_value = JSONField()  # For structured answers (select, multi-select)
```

Each answer is linked to both the registration and the specific question, making it easy to query, display, and export.

### Q30. Can organizers see custom question answers?

Yes. In the registration detail view, there's a "Custom Question Answers" section showing all Q&A pairs. Answers are also included in CSV exports.

---

## Section 7: Payment System

### Q31. What payment methods are supported?

| Method | Type | Verification |
|--------|------|-------------|
| bKash | Mobile money (Bangladesh) | Manual — organizer verifies proof |
| Nagad | Mobile money (Bangladesh) | Manual — organizer verifies proof |
| Rocket | Mobile money (Bangladesh) | Manual — organizer verifies proof |
| Bank Transfer | Bank transfer | Manual — organizer verifies proof |
| DeltaCoin | Platform currency | Auto — instant deduction + verification |

### Q32. How does the organizer configure payment for their tournament?

In tournament creation/edit, under "Registration Settings":

1. Set entry fee amount (৳ or DeltaCoin)
2. Check which payment methods to accept
3. For each manual method: enter merchant number/account details
4. Optionally: write custom payment instructions (Markdown)
5. Set payment deadline (default: 48 hours)

### Q33. What is the payment flow for bKash/Nagad/Rocket?

1. Player submits registration → sees payment instructions page:
   - Merchant number (with copy button)
   - Amount (with copy button)
   - Reference code (registration number, with copy button)
   - Countdown timer (48h deadline)
2. Player opens their mobile money app, sends money, takes screenshot
3. Player returns to DeltaCrown, uploads:
   - Transaction ID (from payment app confirmation)
   - Proof screenshot (JPG/PNG/PDF, max 5MB)
4. Payment status → `submitted`
5. Organizer reviews in payment verification queue:
   - Views proof image (zoomable)
   - Checks transaction ID + amount
   - Clicks "Verify" or "Reject" (with reason)
6. If verified: Payment → `verified`, Registration → `confirmed`
7. If rejected: Player notified with reason, can resubmit

### Q34. How does DeltaCoin payment work?

1. During registration, player selects "Pay with DeltaCoin"
2. System checks wallet balance via Economy app:
   - Sufficient → show "Pay [amount] DC" button with balance display
   - Insufficient → show "Not enough DeltaCoin" + option to use manual method
3. Player clicks "Pay" → instant deduction from wallet
4. Payment auto-verified (no organizer action needed)
5. Registration auto-confirmed
6. On cancellation: DeltaCoin auto-refunded

### Q35. What happens if payment is rejected?

1. Player receives notification: "Your payment was rejected: {reason}"
2. Player can go to their registration and click "Retry Payment"
3. Retry flow:
   - Same payment instructions shown
   - Upload new proof + transaction ID
   - Previous attempt is kept in history
4. New submission goes back to organizer's verification queue
5. No limit on retries within the deadline

### Q36. What happens if the payment deadline passes?

1. A scheduled Celery task runs every hour checking for expired payments
2. If `payment.created_at + tournament.payment_deadline_hours < now()` AND payment still pending:
   - Payment status → `expired`
   - Registration status → `cancelled`
   - Slot freed for waitlist
3. Player notified: "Your registration was cancelled due to payment deadline expiry"
4. If player pays via DeltaCoin before deadline → auto-extended

### Q37. Can organizers waive the entry fee?

Yes. In the registration detail view:
- Organizer clicks "Waive Fee" button
- Payment status → `waived`
- Registration status → `confirmed`
- Use case: invited teams, staff, sponsors, prize gifting

### Q38. What payment data is stored?

```python
class Payment(models.Model):
    registration = OneToOneField(Registration)
    amount = DecimalField(max_digits=10, decimal_places=2)
    method = CharField(choices=['bkash', 'nagad', 'rocket', 'bank_transfer', 'deltacoin'])
    status = CharField(choices=['pending', 'submitted', 'verified', 'rejected', 'refunded', 'waived', 'expired'])
    transaction_id = CharField(max_length=100, blank=True)
    proof_file = FileField(upload_to='payment_proofs/', blank=True)
    notes = TextField(blank=True)  # Player's notes
    
    # Verification (merged from PaymentVerification)
    verified_by = ForeignKey(User, null=True)
    verified_at = DateTimeField(null=True)
    rejection_reason = TextField(blank=True)
    verification_notes = TextField(blank=True)  # Organizer's internal notes
    
    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    expires_at = DateTimeField(null=True)
```

### Q39. How does the organizer verify payments efficiently?

The Payment Verification Queue (`/tournaments/<slug>/manage/payments/`):

1. Shows all payments with `status = submitted`, sorted by submission date (oldest first)
2. Each card shows:
   - Registration number + player/team name
   - Payment method + transaction ID + amount
   - Proof image thumbnail (click to enlarge/zoom)
   - "Verify" and "Reject" buttons
3. Organizer can verify payments one by one or use "Bulk Verify" for multiple
4. After verification:
   - Payment → `verified`
   - If `require_payment_before_confirmation`: Registration → `confirmed`
   - Count updates in dashboard header

---

## Section 8: Registration Status & Workflows

### Q40. What are all the registration statuses?

| Status | Internal Name | Meaning |
|--------|--------------|---------|
| Draft | `draft` | Auto-created when form loads, not submitted yet |
| Submitted | `submitted` | Form submitted, awaiting initial processing |
| Pending | `pending` | Processed, needs payment or organizer action |
| Payment Submitted | `payment_submitted` | Payment proof uploaded, awaiting verification |
| Needs Review | `needs_review` | Flagged for manual review (guest teams, rule flags, duplicates) |
| Auto-Approved | `auto_approved` | System approved (free + auto_approve enabled) |
| Confirmed | `confirmed` | Ready to play — approved and (if required) paid |
| Rejected | `rejected` | Denied by organizer or system |
| Cancelled | `cancelled` | Withdrawn by player or organizer |
| Waitlisted | `waitlisted` | Tournament full, in queue for slot |
| No-Show | `no_show` | Didn't check in on tournament day |

### Q41. What are the valid status transitions?

```
draft → submitted (player submits form)
submitted → pending (processed, needs payment)
submitted → confirmed (free + auto_approve)
submitted → needs_review (flagged for manual review)
submitted → waitlisted (tournament full)
pending → payment_submitted (payment proof uploaded)
pending → confirmed (organizer approves directly)
payment_submitted → confirmed (payment verified)
payment_submitted → rejected (payment rejected — can resubmit = back to pending)
needs_review → confirmed (organizer approves)
needs_review → rejected (organizer rejects)
waitlisted → pending (slot opens, promoted from waitlist)
waitlisted → cancelled (player withdraws)
confirmed → no_show (didn't check in)
confirmed → cancelled (player or organizer cancels)
ANY → cancelled (cancellation always allowed)
```

### Q42. Who can change registration status?

| Action | Who Can Do It |
|--------|--------------|
| Submit registration | The player/captain |
| Cancel own registration | The player/captain |
| Approve registration | Tournament organizer or staff |
| Reject registration | Tournament organizer or staff |
| Verify payment | Tournament organizer or staff |
| Reject payment | Tournament organizer or staff |
| Waive fee | Tournament organizer |
| Promote from waitlist | Tournament organizer or system (auto) |
| Mark no-show | System (auto after check-in window) or organizer |
| Bulk approve/reject | Tournament organizer |

### Q43. Can a player edit their registration after submitting?

**Current plan:** No. Once submitted, the registration data is frozen. If the player needs to change something (wrong game ID, etc.), they:
1. Cancel their registration
2. Re-register with correct info

**Future consideration:** Allow edits to non-critical fields (Discord, phone) while in `pending` or `needs_review` status. Critical fields (name, game ID, team) would remain locked.

### Q44. What statuses does the player see vs what the organizer sees?

Players see simplified statuses:

| Internal Status | Player Sees | Color |
|----------------|-------------|-------|
| `draft` | "Draft" | Gray |
| `submitted`, `pending`, `needs_review` | "Pending" | Yellow |
| `payment_submitted` | "Awaiting Payment Verification" | Yellow |
| `auto_approved`, `confirmed` | "Confirmed ✅" | Green |
| `rejected` | "Rejected — {reason}" | Red |
| `cancelled` | "Cancelled" | Gray |
| `waitlisted` | "Waitlisted (#N)" | Blue |
| `no_show` | "No-Show" | Orange |

Organizers see the full internal statuses with all details.

---

## Section 9: Check-In System

### Q45. How does check-in work?

1. Organizer enables check-in when creating tournament: `enable_check_in = True`
2. Sets window: `check_in_window_minutes = 30` (how long before tournament start)
3. At T-30 minutes:
   - System opens check-in
   - All confirmed participants get notification: "Check in now!"
   - "Check In" button appears on tournament page
4. Player clicks "Check In" → `checked_in = True`, `checked_in_at = now()`
5. At tournament start time (T-0):
   - Check-in closes
   - Unchecked participants → status: `no_show`
   - No-show slots offered to waitlist

### Q46. Can the organizer force-check-in a player?

Yes. In the check-in dashboard:
- Search for player/team
- Click "Force Check-In"
- Use case: player messaged on Discord, running late, organizer gives them a pass

### Q47. Can the organizer extend the check-in window?

Yes. "Extend Check-In" button adds 15/30/60 minutes. Notifies all unchecked participants.

### Q48. What happens to no-shows?

1. Status → `no_show`
2. Their slot opens up
3. If waitlist has entries → next in line promoted
4. Promoted player gets notification: "A slot opened! Check in within [X] minutes."
5. If paid tournament: no-show's payment may be forfeited (organizer policy)

---

## Section 10: Security & Anti-Abuse

### Q49. How is duplicate registration prevented?

Database constraint: unique together on `(tournament, user)` for solo, and `(tournament, team)` for team. If someone tries to register twice, they get "You've already registered for this tournament."

### Q50. How is the same player on multiple teams detected?

Cross-registration game ID check:
1. When a team registers, system scans all other registrations for the same tournament
2. Checks `lineup_snapshot` and `guest_team_data` for matching game IDs
3. If found: registration flagged `needs_review` with warning message
4. Organizer resolves: reject one, allow both (in rare cases like sub rules), etc.

### Q51. How are fake payment proofs detected?

Currently manual:
- Organizer opens proof image, zooms in, verifies visually
- Checks transaction ID format matches payment method
- Cross-references amount with entry fee
- Can reject with specific reason

Future:
- OCR on proof images to extract transaction ID + amount
- Cross-reference with payment provider APIs
- Flag suspicious patterns (same proof image hash used multiple times)

### Q52. How is bot registration prevented?

Layered approach:
1. Must have authenticated account (no anonymous registration)
2. Rate limiting: max 5 registration attempts per user per hour
3. CAPTCHA on submit (if enabled — currently not implemented but pluggable)
4. Honeypot fields in form (hidden fields that bots fill but humans don't)
5. Email verification required for account creation

### Q53. How is slot squatting prevented?

Payment deadline auto-cancellation:
1. When a paid registration is created → `expires_at` = `now() + payment_deadline_hours`
2. Celery task runs hourly, cancels expired unpaid registrations
3. Freed slots → waitlist promotion
4. This prevents someone from holding a slot without paying

### Q54. What data validation happens on the server?

Every form submission is validated server-side (client-side validation is for UX only):

| Field | Validation |
|-------|-----------|
| All required fields | Must be non-empty |
| Email | Valid format, must match account email |
| Phone | Valid format (E.164 or local BD format) |
| Game ID | Game-specific format validation (e.g., `Name#Tag` for Riot) |
| Transaction ID | Alphanumeric, 6-50 chars |
| Proof file | Max 5MB, allowed types: JPG, PNG, PDF |
| Team name | 2-50 chars |
| Custom question answers | Per-question validation (type, required, choices) |
| Roster size | ≥ min_team_size, ≤ max_team_size |

---

## Section 11: Product Intent & Future Direction

### Q55. What's the competitive advantage of DeltaCrown's registration?

1. **Bangladesh-first**: bKash/Nagad/Rocket payment (no international competitors support this)
2. **Smart auto-fill**: Less friction than any competitor for returning users
3. **Game Passport**: Single profile across all games on the platform
4. **DeltaCoin**: Platform currency for instant payment (no external payment needed)
5. **Guest teams**: Lower barrier than requiring all members to sign up
6. **Organizer tools**: Purpose-built for manual verification (Bangladesh's reality)

### Q56. What's the roadmap priority?

| Phase | What | Why | Timeline |
|-------|------|-----|----------|
| A | Organizer dashboard | Can't run tournaments without verifying registrations | 2-3 weeks |
| B | Smart registration upgrades | Wire existing models, add roster snapshot | 1-2 weeks |
| C | Guest team support | Lower barrier for new communities | 1 week |
| D | Payment automation | DeltaCoin wiring, auto-expiry, retries | 1-2 weeks |
| E | Notifications + check-in | Essential for tournament day operations | 1-2 weeks |

### Q57. What needs to change in tournament creation?

New fields added to tournament creation form (under a "Registration Settings" collapsible section):

- Guest teams toggle
- Auto-approve toggle
- Payment deadline hours
- Registration instructions (Markdown)
- Payment instructions (Markdown)
- Custom questions builder
- Eligibility rules builder (future)
- Check-in settings
- Waitlist toggle

These are all optional with sensible defaults — a tournament can be created with zero registration configuration (defaults: no guest teams, no auto-approve, 48h payment deadline, no custom questions, no check-in).

### Q58. How does registration interact with brackets/seeding?

Registration feeds into tournament seeding:
1. Only `confirmed` registrations are included in bracket generation
2. Bracket generation happens after registration closes
3. Seed order can be:
   - Registration order (first registered = seed 1)
   - Rank-based (from GamePassport rank)
   - Manual (organizer sets seeds)
   - Random
4. Registration data (game ID, rank) is passed to bracket/match systems

### Q59. What analytics should be tracked?

| Metric | Purpose |
|--------|---------|
| Registration funnel: page views → form loads → submissions → confirmations | Identify drop-off points |
| Auto-fill coverage: % of fields pre-filled per registration | Measure profile completeness |
| Average time from form load to submit | Measure friction |
| Payment conversion: submitted → verified | Track payment success rate |
| Waitlist conversion: waitlisted → confirmed | Track slot turnover |
| Custom question completion rate | Identify confusing questions |
| Guest team vs platform team ratio | Track platform adoption |

### Q60. How does this integrate with the rest of DeltaCrown?

| App | Integration |
|-----|------------|
| `accounts` | User authentication, profile data |
| `user_profile` | UserProfile + GamePassport for auto-fill |
| `teams` | Team model + TeamMembership for team registration |
| `economy` | DeltaCoin wallet for payment |
| `notifications` | Email + in-app notifications for status changes |
| `games` | Game model for game-specific field mapping |
| `tournaments` | Tournament model config, bracket/match generation |
| `leaderboards` | Future: registration count, win rate affect seeding |
| `organizations` | Organizer permissions, tournament management |

### Q61. What about internationalization/localization?

Current focus is English + Bengali (Bangladesh market):
- Form labels, error messages, payment instructions in both languages
- Currency: ৳ (Bangladeshi Taka) for entry fees
- Phone format: BD mobile numbers (+880)
- Payment methods: Bangladesh mobile money (bKash, Nagad, Rocket)

Future: full i18n framework for other markets.

### Q62. What's the migration strategy from the current state?

No migration needed for users — the current `SmartRegistrationView` already handles all existing registrations. The plan is:

1. **No breaking changes**: Existing Registration model works as-is. New fields are additive (null=True, default values).
2. **Wire unused models**: Connect `RegistrationQuestion`, `RegistrationDraft`, `RegistrationAnswer`, `RegistrationRule` to the view.
3. **Build new views**: Organizer dashboard is entirely new (no existing views to migrate).
4. **Consolidate payment models**: Add verification fields to `Payment`, deprecate `PaymentVerification`, migrate data.
5. **Remove dead code**: Form builder marketplace views (already unused), legacy templates.
6. **Test continuously**: All existing 172+ tests must continue passing through every change.

The registration system evolves in-place — no "big rewrite." Each phase adds capability without breaking what works.

---

*For the system plan, see `02_REGISTRATION_SYSTEM_PLAN.md`*  
*For the end-to-end explanation, see `03_REGISTRATION_END_TO_END.md`*
