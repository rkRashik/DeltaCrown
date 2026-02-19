# How Tournament Registration Works End-to-End in DeltaCrown

> **Date:** February 19, 2026  
> **Audience:** Anyone — written in simple language  
> **Purpose:** Explain how the entire registration system works from start to finish, covering every scenario

---

## Table of Contents

1. [The Big Picture](#1-the-big-picture)
2. [What Happens Before Registration Opens](#2-what-happens-before-registration-opens)
3. [Solo Player Registration — Step by Step](#3-solo-player-registration--step-by-step)
4. [Team Registration — Step by Step](#4-team-registration--step-by-step)
5. [Guest Team Registration — Step by Step](#5-guest-team-registration--step-by-step)
6. [What "Smart Auto-Fill" Does](#6-what-smart-auto-fill-does)
7. [How Payment Works](#7-how-payment-works)
8. [What the Organizer Does After Registration](#8-what-the-organizer-does-after-registration)
9. [What Happens When Things Go Wrong](#9-what-happens-when-things-go-wrong)
10. [The Waitlist](#10-the-waitlist)
11. [Check-In on Tournament Day](#11-check-in-on-tournament-day)
12. [The Full Timeline](#12-the-full-timeline)

---

## 1. The Big Picture

DeltaCrown is a competitive gaming platform where organizers create tournaments and players register to compete. Registration is the bridge between "I want to play" and "I'm in the tournament."

There are three ways to register:

| Mode | Who | When |
|------|-----|------|
| **Solo** | One player registers themselves | Tournament is set to "solo" mode |
| **Team** | A team captain registers their whole team | Tournament is set to "team" mode |
| **Guest Team** | A captain registers a team where members don't have DeltaCrown accounts | Tournament allows guest teams |

The registration form is **smart** — it automatically fills in as much information as possible from the player's profile, game accounts, and team data. The player reviews what's been filled in, adds anything missing, and submits.

---

## 2. What Happens Before Registration Opens

### The Organizer Creates a Tournament

When an organizer creates a tournament on DeltaCrown, they set up registration by configuring:

- **Registration type**: Solo or Team
- **Registration dates**: When it opens and closes
- **Max participants**: How many slots (e.g., 32 teams, 64 players)
- **Entry fee**: Free or paid (e.g., ৳500)
- **Payment methods**: Which methods accepted (bKash, Nagad, Rocket, DeltaCoin)
- **Guest teams**: Whether external teams can join
- **Custom questions**: Any extra questions (e.g., "What's your Discord?")
- **Eligibility rules**: Any restrictions (e.g., Diamond rank minimum, age 16+)

### What Players See Before Registration Opens

If a player visits the tournament page before registration opens, they see:
- Tournament details (game, format, prize pool, schedule)
- "Registration opens on [date]" countdown
- No registration button yet

### When Registration Opens

At the configured date/time:
- "Register" button appears on the tournament page
- Players can click it to start registering
- If the tournament is full, new visitors see a "Join Waitlist" button instead

---

## 3. Solo Player Registration — Step by Step

### Step 1: Player Clicks "Register"

The player is on the tournament page (e.g., `/tournaments/valorant-champions-2026/`) and clicks the green "Register" button.

### Step 2: System Checks Eligibility

Before showing the form, the system silently checks:

- ✅ Is the player logged in? (If not → redirect to login)
- ✅ Is registration open? (If closed → show "Registration closed" message)
- ✅ Is there capacity? (If full → offer waitlist)
- ✅ Has the player already registered? (If yes → show "Already registered" message)
- ✅ Does the player have a Game Passport for this game? (If no → show "Set up your game profile first" with link)
- ✅ Does the player meet tournament rules? (If minimum rank required and player is too low → show reason)

If ANY check fails, the player sees an **ineligible page** that explains WHY and what action they can take. For example:
- "You don't have a Valorant game profile yet. [Set up your game profile →]"
- "This tournament requires Diamond rank or higher. Your current rank is Gold 3."

### Step 3: Smart Registration Form Loads

If all checks pass, the registration form appears. This is a **single page** with sections:

#### Section 1: Player Information (Auto-filled)
```
┌─────────────────────────────────────┐
│ 👤 Player Information               │
│                                     │
│ Name: Ahmed Rahman          🔒     │
│ Email: ahmed@example.com    🔒     │
│ Phone: +880 171XXXXXXX     ✏️      │
│ Country: 🇧🇩 Bangladesh      ✏️      │
│ Discord: ahmed#1234         ✏️      │
│                                     │
│ ✅ 5/5 fields filled               │
└─────────────────────────────────────┘
```

The 🔒 icon means the field is locked (comes from verified profile data). The ✏️ icon means the player can edit it if needed.

#### Section 2: Game Information (Auto-filled from Game Passport)
```
┌─────────────────────────────────────┐
│ 🎮 Valorant Profile                 │
│                                     │
│ Riot ID: Ahmed#BD01         ✏️      │
│ Rank: Diamond 2             ✏️      │
│ Platform: PC                ✏️      │
│                                     │
│ ✅ 3/3 fields filled               │
└─────────────────────────────────────┘
```

#### Section 3: Custom Questions (If tournament has them)
```
┌─────────────────────────────────────┐
│ 📋 Additional Questions             │
│                                     │
│ What role do you main?              │
│ [Duelist ▼]                         │
│                                     │
│ Have you competed before?           │
│ ○ Yes  ○ No                        │
└─────────────────────────────────────┘
```

#### Section 4: Payment (If entry fee > 0)
```
┌─────────────────────────────────────┐
│ 💰 Entry Fee: ৳500                  │
│                                     │
│ Payment method:                     │
│ ○ bKash  ○ Nagad  ○ DeltaCoin      │
│                                     │
│ (Payment details shown after submit)│
└─────────────────────────────────────┘
```

#### Readiness Bar
```
Profile completeness: ████████░░ 80%
Missing: Phone number — [Add to profile →]
```

### Step 4: Player Reviews and Submits

The player scrolls through, checks everything looks right, and clicks "Submit Registration."

### Step 5: What Happens After Submit

The system:
1. Creates a `Registration` record in the database
2. Takes a snapshot of the player's info at this moment
3. If it's a **free tournament with auto-approve**: Status → `confirmed` (done!)
4. If it's a **paid tournament**: Status → `pending`, creates a `Payment` record
5. If it **needs manual review**: Status → `needs_review`

### Step 6: Success Page

The player sees a success page:
```
┌─────────────────────────────────────┐
│ ✅ Registration Submitted!           │
│                                     │
│ Registration #: VCS-2026-000042     │
│ Status: Pending Payment             │
│                                     │
│ Next step: Complete your payment    │
│ Deadline: Feb 21, 2026 3:30 PM     │
│                                     │
│ [Go to Payment →]                   │
│ [View My Registrations →]           │
└─────────────────────────────────────┘
```

---

## 4. Team Registration — Step by Step

### What's Different from Solo

- The captain (or manager/owner) registers on behalf of the entire team
- The system shows the team roster with each member's game info
- All team members are included in the registration

### Step 1-2: Same as Solo (Click Register, Eligibility Check)

Extra eligibility checks for teams:
- Does the player have any teams for this game?
- Does the player have permission to register the team? (Must be owner, manager, or captain)
- Does the team have enough members?

### Step 3: Team Selection

If the player has multiple teams for this game, they pick one:
```
┌─────────────────────────────────────┐
│ 🏆 Select Your Team                 │
│                                     │
│ ● Phoenix Rising (5 members)        │
│ ○ Shadow Squad (4 members) ⚠️      │
│   ↳ Needs 5 players minimum        │
│                                     │
│ Don't have a team?                  │
│ [Create a Team →]                   │
└─────────────────────────────────────┘
```

If they only have one team, it's auto-selected.

### Step 4: Roster Display

The form shows all team members with their game info:
```
┌─────────────────────────────────────────────────┐
│ 📋 Team Roster (5/5 required)                     │
│                                                   │
│ 👑 captain_phx (Captain)                         │
│    Riot ID: PhxCaptain#1234  ✅                   │
│    Rank: Diamond 2                                │
│                                                   │
│ 👤 player_two                                    │
│    Riot ID: PlayerTwo#5678   ✅                   │
│    Rank: Platinum 3                               │
│                                                   │
│ 👤 player_three                                  │
│    Riot ID: P3#9012          ✅                   │
│    Rank: Diamond 1                                │
│                                                   │
│ 👤 player_four                                   │
│    Riot ID: P4#3456          ⚠️ Missing game ID  │
│    Rank: —                                        │
│                                                   │
│ 👤 player_five                                   │
│    Riot ID: P5#7890          ✅                   │
│    Rank: Platinum 2                               │
│                                                   │
│ ✅ 4/5 members have complete game profiles        │
│ ⚠️ player_four needs to set up their Valorant    │
│   profile before the organizer can verify them    │
└─────────────────────────────────────────────────┘
```

Green checkmarks mean the member has a Game Passport for this game. Yellow warnings flag missing info.

### Step 5-6: Same as Solo

Captain fills custom questions (if any), selects payment method (if paid), and submits. The entire team is registered together.

### Roster Snapshot

At submit time, the system saves a **snapshot** of the roster. This is important because:
- If a player leaves the team later, the registration still shows who was on it
- The organizer can see exactly who was on the team at registration time
- No one can swap players after registering (unless organizer allows it)

---

## 5. Guest Team Registration — Step by Step

### When This Is Used

Some tournaments want to let teams participate even if not all members have DeltaCrown accounts. For example:
- A local LAN tournament where teams sign up at the venue
- An open tournament that wants maximum participation
- Teams transitioning from other platforms

The tournament organizer must enable "Allow Guest Teams" for this to work.

### How It Works

#### Step 1: Player Clicks Register, Sees Options

```
┌─────────────────────────────────────────────────┐
│ How would you like to register?                   │
│                                                   │
│ [🏆 Register with your DeltaCrown team]          │
│ Your teams: Phoenix Rising, Shadow Squad          │
│                                                   │
│ [➕ Create a new team & register]                │
│ Create a team first, then register it             │
│                                                   │
│ [👥 Register as guest team]                      │
│ Your teammates don't need DeltaCrown accounts     │
└─────────────────────────────────────────────────┘
```

#### Step 2: Guest Team Form

If they choose "Guest Team", they fill in team info manually:

```
┌─────────────────────────────────────────────────┐
│ 👥 Guest Team Information                         │
│                                                   │
│ Team Name: [Apex Predators        ]               │
│ Team Tag:  [APX                   ]               │
│ Team Logo: [📎 Upload]                            │
│                                                   │
│ 📋 Roster (minimum 5 players)                     │
│                                                   │
│ Player 1 (You — Captain):                         │
│  Name: Ahmed Rahman (auto-filled)                 │
│  Game ID: Ahmed#BD01 (auto-filled)                │
│  Contact: ahmed#1234 (auto-filled)                │
│                                                   │
│ Player 2:                                         │
│  Name: [_______________]                          │
│  Game ID: [_______________]                       │
│  Contact: [_______________] (Discord/email)       │
│                                                   │
│ Player 3:                                         │
│  Name: [_______________]                          │
│  Game ID: [_______________]                       │
│  Contact: [_______________]                       │
│                                                   │
│ [+ Add Player]                                    │
│                                                   │
│ ℹ️ Guest teams always require manual review       │
│   by the organizer before confirmation.            │
└─────────────────────────────────────────────────┘
```

#### Step 3: Submit

On submit:
- Registration is created with `is_guest_team = True`
- Team data is stored in `guest_team_data` (JSONB field)
- Status is **always** `needs_review` for guest teams
- Organizer sees it flagged for manual verification

#### Smart Conversion (Optional, Later)

After registering as a guest team, the captain gets an option:
- "Want full team features? Invite your teammates to create DeltaCrown accounts."
- Share a special link → teammates create accounts → system matches game IDs
- Once all members are on the platform → guest team converts to a real team
- Benefits: team stats, leaderboards, future tournament auto-fill

---

## 6. What "Smart Auto-Fill" Does

### The Problem It Solves

Nobody likes filling out forms. In gaming, players have to enter their game ID, rank, and other info for every tournament they join. This is annoying and error-prone.

### How It Works

DeltaCrown stores your gaming information in two places:

1. **User Profile** — your real name, email, phone, country, avatar
2. **Game Passport** — your in-game info for each game you play (Riot ID, Steam ID, rank, etc.)

When you register for a tournament, the system:
1. Looks at which game the tournament is for (e.g., Valorant)
2. Finds your Game Passport for that game
3. Pre-fills the registration form with all your info
4. Shows you a "readiness score" (e.g., 80% — missing phone number)

### What Gets Auto-Filled

| Field | Source | Can You Edit? |
|-------|--------|---------------|
| Your name | User Profile | No (locked) |
| Email | Account | No (locked) |
| Phone number | User Profile | Yes |
| Country | User Profile | Yes |
| In-Game Name | Game Passport | Yes (override) |
| Game ID (Riot ID, Steam ID, etc.) | Game Passport | Yes (override) |
| Current rank | Game Passport | Yes (override) |
| Platform (PC/Console) | Game Passport | Yes |
| Team name | Team model | No (locked) |
| Team tag | Team model | No (locked) |
| Discord | User Profile | Yes |

### Why Some Fields Are Locked

Locked fields come from **verified data** — your account email, display name, team name. These can't be changed during registration to prevent fraud (someone claiming to be on a different team or using a fake name).

Override-allowed fields (like Game ID) let you update if your info has changed since you set up your Game Passport.

---

## 7. How Payment Works

### Free Tournaments

No payment needed. If the organizer enabled auto-approve, you're confirmed immediately. If not, the organizer manually approves you.

### Paid Tournaments — Manual Methods (bKash, Nagad, Rocket)

This is the most common scenario for Bangladesh esports:

#### Step 1: Choose Payment Method

During registration, you select bKash, Nagad, or Rocket.

#### Step 2: See Instructions

After submitting the registration, you see payment instructions:

```
Send ৳500 to:
bKash: 01XXXXXXXXX
Reference: VCS-2026-000042

You have 48 hours to complete payment.
Deadline: Feb 21, 2026 3:30 PM
```

#### Step 3: Make Payment on Your Phone

You open your bKash/Nagad/Rocket app, send the money to the given number, and get a confirmation from the payment app.

#### Step 4: Upload Proof

Come back to DeltaCrown, go to your registration, and:
1. Enter the transaction ID from your payment confirmation
2. Upload a screenshot of the confirmation
3. Click "Submit Payment Proof"

#### Step 5: Wait for Verification

The organizer sees your payment in their verification queue. They:
1. Open your proof screenshot
2. Check the transaction ID and amount match
3. Click "Verify" → your registration is confirmed!

Or if there's a problem:
1. Click "Reject" with a reason (e.g., "Amount doesn't match")
2. You get notified and can resubmit with correct proof

#### Step 6: Deadline

If you don't pay within 48 hours (configurable):
- Your registration is automatically cancelled
- Your slot opens up for waitlisted players

### Paid Tournaments — DeltaCoin (Platform Currency)

DeltaCoin is DeltaCrown's virtual currency:
1. During registration, select "Pay with DeltaCoin"
2. System shows your balance: "Your balance: 1,250 DC. Cost: 500 DC."
3. Click "Pay 500 DC" → instant deduction → auto-verified → you're confirmed immediately
4. If you cancel later → DeltaCoin refunded to your wallet

### Fee Waivers

Organizers can waive the entry fee for specific registrations (e.g., invited teams, staff).

---

## 8. What the Organizer Does After Registration

### The Organizer Dashboard

Organizers access their registration management page at:
`/tournaments/<slug>/manage/registrations/`

Here they see all registrations in a table with:
- Player/team name
- Registration status (pending, confirmed, etc.)
- Payment status (not paid, submitted, verified)
- Registration date
- Action buttons

### What Organizers Verify Manually

Since DeltaCrown doesn't yet have automated verification, organizers manually check:

| What | How |
|------|-----|
| **Payment proof** | Open the screenshot, verify transaction ID + amount |
| **Game ID is real** | Click on the game ID to open tracker.gg / op.gg / similar sites |
| **Team roster is complete** | Check member count meets tournament requirements |
| **No duplicate players** | System auto-flags, organizer resolves |
| **Guest team is legitimate** | Contact captain via provided Discord/email |
| **Eligibility rules met** | Check rank, age, region if required |

### Actions Organizers Can Take

| Action | Effect |
|--------|--------|
| **Approve** | Registration → confirmed |
| **Reject** | Registration → rejected (with reason) |
| **Verify Payment** | Payment → verified, may auto-confirm registration |
| **Reject Payment** | Payment → rejected (with reason), player can retry |
| **Waive Fee** | Skip payment requirement for this registration |
| **Move to Waitlist** | If over-capacity, put on waitlist |
| **Promote from Waitlist** | Move waitlisted player/team to active |
| **Export CSV** | Download all registration data |
| **Send Message** | Notify all confirmed participants |

---

## 9. What Happens When Things Go Wrong

### Problem: Player's Game ID Is Wrong

1. Organizer sees incorrect/suspicious Game ID in registration detail
2. Organizer clicks "Reject" with reason: "Game ID doesn't match any account. Please update your Valorant profile and re-register."
3. Player gets notified via email + in-app
4. Player can re-register with correct info

### Problem: Payment Proof Is Invalid

1. Organizer sees blurry screenshot or wrong amount
2. Organizer clicks "Reject Payment" with reason: "Amount shown is ৳400, tournament fee is ৳500"
3. Player gets notified and can submit new payment proof
4. This creates a new attempt — old proof is kept for records

### Problem: Team Member Left After Registration

1. The registration has a **roster snapshot** frozen at registration time
2. The organizer can see the original roster
3. Options: allow substitute (if enabled) or request team to re-register with new roster

### Problem: Tournament Is Cancelled

1. Organizer cancels tournament
2. All registrations → `cancelled`
3. Paid registrations → refunds processed (manual refund or DeltaCoin auto-refund)
4. All participants notified

### Problem: Player Registered Twice for Different Teams

1. System auto-detects: same game ID appears in two registrations
2. Both registrations flagged for organizer review
3. Organizer contacts players, resolves conflict
4. One registration rejected, one approved

---

## 10. The Waitlist

### How It Works

When a tournament reaches max capacity:

1. New registrants see: "Tournament is full. Join the waitlist?"
2. If they click "Join Waitlist" → Registration created with status `waitlisted`
3. They see: "You're #3 on the waitlist. We'll notify you if a slot opens."
4. When a confirmed player cancels or is removed:
   - First person on waitlist gets notified: "A slot opened! You have 48 hours to confirm."
   - If paid tournament: they also need to complete payment within the deadline
   - If they don't respond in time → next person on waitlist is promoted

### Waitlist Priority

First come, first served. The system tracks waitlist position by registration timestamp.

---

## 11. Check-In on Tournament Day

### Why Check-In Exists

Some tournaments require participants to "check in" before the tournament starts to confirm they're actually available to play. This prevents empty slots from no-shows.

### How It Works

1. Tournament has `enable_check_in = True` and `check_in_window = 30 minutes`
2. 30 minutes before tournament start time:
   - All confirmed participants get a notification: "Check in now! You have 30 minutes."
   - "Check In" button appears on the tournament page
3. Participant clicks "Check In" → status updated → ready to play
4. When the window closes:
   - Players who didn't check in → status: `no_show`
   - Their slots open to waitlist
   - Tournament proceeds with checked-in players only

### What Organizer Sees

```
Check-In Status:
✅ Checked in: 28/32
⏳ Not yet: 3/32
❌ No-show: 1/32

Options: [Force check-in for specific player] [Extend window]
```

---

## 12. The Full Timeline

Here's the complete timeline of a typical tournament registration:

```
Day 1: Organizer creates tournament, configures registration settings
         ↓
Day 7: Registration opens
         ↓
Day 7-14: Players and teams register
         ├── System auto-fills forms
         ├── Players submit registrations
         ├── Paid players upload payment proofs
         └── Organizer verifies payments and game IDs
         ↓
Day 14: Registration closes
         ↓
Day 14-15: Organizer reviews remaining pending registrations
         ├── Approves valid ones
         ├── Rejects invalid ones
         └── Promotes from waitlist if slots available
         ↓
Day 16 (Tournament Day):
         ├── Check-in opens (30 min before)
         ├── Players check in
         ├── No-shows marked, waitlist promoted
         └── Tournament begins with checked-in players
```

---

## Summary

The registration system is designed to be:

- **Fast for players** — smart auto-fill means most fields are pre-populated
- **Flexible for organizers** — configure rules, questions, payment methods per tournament
- **Transparent for everyone** — clear status tracking, reasons for rejection, deadline visibility
- **Manual-first** — organizers verify everything manually now, with automation hooks for later
- **Bangladesh-optimized** — bKash/Nagad/Rocket payment support, local game preferences

The single `SmartRegistrationView` handles all modes (solo, team, guest team) based on tournament configuration. No separate views, no wizard steps, no confusion.

---

*For the detailed system plan, see `02_REGISTRATION_SYSTEM_PLAN.md`*  
*For all 62 questions answered, see `04_ALL_QUESTIONS_ANSWERED.md`*
