# DeltaCrown — Manual Testing Guide

*Complete walkthrough for testing the DeltaCrown esports platform, covering the full Smart Registration system, Guest Teams, TOC modules, Match Medic, DeltaCoin Economy, and all platform features. Written for anyone — no technical experience required.*

**Last Updated:** February 20, 2026 — Phase 4 Complete (180 automated tests passing)

---

## Before You Begin

**What is this?**
DeltaCrown is an esports tournament platform — think of it as a website where gamers create teams, join tournaments, and compete against each other. This guide walks you through every part of the site to make sure everything works properly.

**What you'll need:**
- A web browser (Chrome, Firefox, or Edge)
- The website running at: **http://127.0.0.1:8000** (your local test server)
- The admin panel at: **http://127.0.0.1:8000/admin/**
- About 90–120 minutes for a full pass

**What's already set up:**
The database has been pre-loaded ("seeded") with sample data so you have something to test with. You'll find 100 test users, 24 teams, 3 organizations, and 19 tournaments already created — covering various games like Valorant, CS2, League of Legends, Dota 2, Apex Legends, Rocket League, Overwatch 2, and FC 25.

### Starting the Test Server

Open a terminal in the project folder and run:

```
python manage.py runserver
```

This uses the main `deltacrown.settings` which reads the production database URL from the `.env` file.

The site will be available at http://127.0.0.1:8000

---

## Quick Reference — Test Accounts

Every test account uses the same password: **`DeltaCrown2025!`**

| Who | Username | Role | Good For Testing |
|-----|----------|------|------------------|
| Omar (Caster) | `dc_omar` | Tournament organizer | Creating & managing tournaments, TOC |
| Nabil (Org CEO) | `dc_nabil` | Organization CEO | Managing Titan Esports org & teams |
| Tanvir (Pro) | `dc_tanvir` | Team captain | Leading Crimson Syndicate (Valorant) |
| Sakib (IGL) | `dc_sakib` | Team captain | Leading Velocity X BD (Valorant) |
| Rifat (Pro) | `dc_rifat` | Team captain | Leading Old School BD (CS2) |
| Sumon (Multi-game) | `dc_sumon` | Player + Org CEO | Crown Dynasty org, plays Val/CS2/LoL |
| FC Master | `dc_fc_master` | Solo player | FC 25 solo tournament testing |
| Bot Slayer | `dc_bot_slayer` | Casual player | Casual user experience |
| Jamal (Caster) | `dc_jamal` | Non-player staff | User with no games linked |

---

## Part 1 — The Home Page (First Impressions)

**Goal:** Make sure the front door of the website looks right and works.

1. Open your browser and go to **http://127.0.0.1:8000**

**Check:**
- [ ] Does the page load without any errors?
- [ ] Do all the navigation links at the top work?
- [ ] Does the "Tournaments" link take you to the tournament listing?
- [ ] Does the "Teams" link take you to the team directory?
- [ ] Does "About" page load? → http://127.0.0.1:8000/about/
- [ ] Does "Community" page load? → http://127.0.0.1:8000/community/

---

## Part 2 — Signing In & Accounts

**Goal:** Log into the platform as different users and test account flows.

### Test A: Log in as a Tournament Organizer

1. Go to **http://127.0.0.1:8000/account/login/**
2. Enter username: **dc_omar** / password: **DeltaCrown2025!**
3. Click "Sign In"

**Check:**
- [ ] Did you land on the homepage or dashboard after login?
- [ ] Does the navigation bar show you're logged in?
- [ ] Can you see a dashboard link?

### Test B: Log in as a Player

1. Log out → log in as **dc_tanvir** (password: `DeltaCrown2025!`)

**Check:**
- [ ] Does login work for a different user?
- [ ] Can you navigate to your profile?

### Test C: Sign Up (New Account)

1. Go to **http://127.0.0.1:8000/account/signup/**
2. Create a new account with any username, email, and password

**Check:**
- [ ] Does the signup form appear?
- [ ] Can you create a new account successfully?

---

## Part 3 — User Profiles

**Goal:** Verify that player profiles display correctly.

### View Your Own Profile

1. Log in as **dc_tanvir** → go to **http://127.0.0.1:8000/@dc_tanvir/**

**Check:**
- [ ] Does the profile page load?
- [ ] Can you see the display name "Tanvir.Gaming"?
- [ ] Is the bio shown: "Pro player for Crimson Syndicate"?
- [ ] Are game passports (linked games) visible?
- [ ] Does the activity tab work? → http://127.0.0.1:8000/@dc_tanvir/activity/

### Edit Your Profile

1. Go to **http://127.0.0.1:8000/me/edit/**

**Check:**
- [ ] Does the edit page load?
- [ ] Can you change the bio and save?
- [ ] Does the change appear on the profile?

### Profile Settings & Privacy

**Check:**
- [ ] Settings loads: **http://127.0.0.1:8000/me/settings/**
- [ ] Privacy loads: **http://127.0.0.1:8000/me/privacy/**

---

## Part 4 — Browsing Tournaments

**Goal:** Make sure visitors can find and view tournaments.

### Tournament List

1. Go to **http://127.0.0.1:8000/tournaments/**

**Check:**
- [ ] Does the page show a list of tournaments?
- [ ] Can you see tournaments with different statuses (live, completed, open)?
- [ ] Browse page works? → http://127.0.0.1:8000/tournaments/browse/

### View a Completed Tournament

1. Go to **http://127.0.0.1:8000/tournaments/valorant-invitational-s1/**

**Check:**
- [ ] Does the tournament detail page load?
- [ ] Can you see the tournament name, game (Valorant), status (Completed)?
- [ ] Is the prize pool shown (৳50,000)?
- [ ] Bracket view works? → …/bracket/
- [ ] Results page works? → …/results/

### View a Live Tournament

1. Go to **http://127.0.0.1:8000/tournaments/radiant-rising-s2/**

**Check:**
- [ ] Does it show as "Live"?
- [ ] Can you see registered teams and ongoing matches?
- [ ] Does the bracket page show match results?

### View an Open Registration Tournament

1. Go to **http://127.0.0.1:8000/tournaments/valorant-scrims-44/**

**Check:**
- [ ] Does it show as "Registration Open"?
- [ ] Is there a "Register" button visible?
- [ ] Can you see slots filled vs. total?

---

## Part 5 — Smart Registration Flow (Phase 1–4)

**Goal:** Test the complete Smart Registration system — the new multi-step wizard, eligibility checks, and payment flows.

### 5A: Eligibility Pre-Check

1. Log in as **dc_bot_slayer**
2. Navigate to an open tournament
3. Click "Register" — the system should check your eligibility first

**Check:**
- [ ] Does the eligibility check run before showing the registration form?
- [ ] If your team meets requirements, does it proceed to the wizard?
- [ ] If requirements are NOT met, does it show a clear error message?
- [ ] Does it correctly detect if you have an eligible team for the game?

### 5B: Registration Wizard (Smart Registration)

1. Log in as a team captain (e.g., **dc_tanvir**)
2. Navigate to an open team tournament for Valorant
3. Click "Register" → the Smart Registration wizard should load

**Check:**
- [ ] Does the wizard show Step 1 (team selection or solo info)?
- [ ] Does it auto-fill known data (team name, roster from team record)?
- [ ] Can you proceed through all wizard steps?
- [ ] Does the roster/lineup confirmation step show your team members?
- [ ] Does the final review step summarize everything before submission?
- [ ] After submission, does the registration appear in "My Registrations"?

### 5C: Solo Registration

1. Log in as **dc_fc_master**
2. Go to **http://127.0.0.1:8000/tournaments/fc25-solo-championship/**
3. Register as a solo player

**Check:**
- [ ] Does solo registration work without team selection?
- [ ] Does it only ask for individual player info?

### 5D: Registration with Entry Fee (DeltaCoin)

1. Navigate to a tournament with an entry fee (e.g., `cs2-comp-league-spring` — ৳500)
2. Try to register

**Check:**
- [ ] Does the entry fee amount show during registration?
- [ ] Does the DeltaCoin payment flow trigger?
- [ ] Does it show your wallet balance?
- [ ] If you have sufficient balance, can you pay and register?
- [ ] If insufficient balance, does it show a clear message?

### 5E: Registration Rule Auto-Evaluation (P4-T05)

This tests the automatic rule enforcement system. Rules are set by organizers.

1. As organizer (**dc_omar**), go to tournament settings and add a RegistrationRule:
   - Type: `AUTO_REJECT`
   - Condition: `{"account_age_days": {"lte": 29}}`
   - Reason: "Your account must be at least 30 days old"
2. Log in as a brand new user (freshly created account)
3. Try to register for that tournament

**Check:**
- [ ] Does the eligibility check catch the rule violation?
- [ ] Is the error message clear ("Your account must be at least 30 days old")?
- [ ] Does an older account pass the same rule check?

---

## Part 6 — Guest Team Registration (Phase 2 + Phase 4)

**Goal:** Test the guest team registration system and the new guest-to-real conversion flow.

### 6A: Register a Guest Team

1. Log in as **dc_omar** (organizer)
2. Navigate to an open team tournament
3. Look for "Register as Guest Team" option
4. Fill in guest team details:
   - Team name (doesn't need to exist on the platform)
   - Roster: list of player Game IDs (e.g., "Player1#TAG", "Player2#TAG")

**Check:**
- [ ] Does the guest team registration option appear?
- [ ] Can you enter a team name and roster of player IGNs?
- [ ] Does it show as a guest registration after submission?
- [ ] Is the `is_guest_team` badge visible in the registration listing?

### 6B: Guest Team Cap Enforcement

1. Check the tournament's `max_guest_teams` setting
2. Register guest teams until the cap is reached
3. Try one more

**Check:**
- [ ] Does the system enforce the maximum guest team limit?
- [ ] Does it block further guest registrations with a clear message?

### 6C: Guest-to-Real Team Conversion (P4-T04)

1. Log in as organizer (**dc_omar**)
2. Find a guest team registration in the TOC
3. Click "Generate Invite Link"

**Check:**
- [ ] Does the invite link generate successfully?
- [ ] Is the invite token unique and URL-safe?
- [ ] Is the `conversion_status` set to "pending"?

4. Copy the invite link and open it in a new browser/incognito
5. Log in as a player whose Game ID matches one of the guest roster entries
6. On the conversion page, enter the matching Game ID

**Check:**
- [ ] Does the conversion page load with roster details?
- [ ] Does claiming a slot with a matching Game ID succeed?
- [ ] Is the case-insensitive matching working? (e.g., "alpha#1" matches "Alpha#1")
- [ ] Does the progress bar update (e.g., "1 of 3 claimed")?
- [ ] Does claiming with an incorrect Game ID show a clear error?
- [ ] Can the same user claim only once (double-claim prevention)?

7. Have all roster members claim their slots

**Check:**
- [ ] When all slots are claimed, does auto-conversion trigger?
- [ ] Does `is_guest_team` flip to `False`?
- [ ] Is the original seed and bracket slot preserved?

### 6D: Partial Conversion Approval

1. Have only some roster members claim their slots
2. As organizer, go to the registration and click "Approve Partial Conversion"

**Check:**
- [ ] Can the organizer approve even if not all members joined?
- [ ] Does the registration convert to a real team?
- [ ] Is the `conversion_status` set to "approved"?

---

## Part 7 — Waitlist System (Phase 2)

**Goal:** Test the automatic waitlist when tournaments reach capacity.

1. Fill a tournament to max capacity with registrations
2. Register one more player/team

**Check:**
- [ ] Does the system automatically place them on the waitlist?
- [ ] Does the UI show "You have been placed on the waitlist"?
- [ ] When a confirmed registration is cancelled, does the first waitlisted entry get promoted?
- [ ] Does the promoted player receive a notification?

---

## Part 8 — Tournament Organizer Console (TOC) — Phase 3

**Goal:** Test all TOC modules from the organizer's perspective.

### 8A: Access the TOC

1. Log in as **dc_omar**
2. Go to **http://127.0.0.1:8000/tournaments/organizer/radiant-rising-s2/**

**Check:**
- [ ] Does the TOC (Organizer Hub) load?
- [ ] Can you see tabs/navigation for all modules?

### 8B: Bracket Generation & Publishing

1. In the TOC, go to the Brackets tab
2. Click "Generate Brackets" (if tournament is in correct state)

**Check:**
- [ ] Does bracket generation work for single elimination?
- [ ] Does it correctly determine the number of rounds?
- [ ] Are participants seeded (or randomly assigned)?
- [ ] Can you publish the bracket?

### 8C: Drag-Drop Seeding

1. Before publishing the bracket, look for a drag-drop seeding interface

**Check:**
- [ ] Can you drag participants to rearrange their seeds?
- [ ] Does the new seeding persist after saving?
- [ ] Does it work on both desktop and mobile viewports?

### 8D: Live Draw — WebSocket Broadcast (P4-T07)

1. In the TOC Brackets area, look for "Live Draw" button
2. Open the draw page in another browser tab as a spectator

**Check:**
- [ ] Does the Live Draw page load? → `…/draw/`
- [ ] Does the WebSocket connection indicator show green (connected)?
- [ ] When organizer clicks "Start Live Draw":
  - [ ] Are seeds revealed one by one with 2-3 second delays?
  - [ ] Does each seed card animate in (fade + slide)?
  - [ ] Do spectators see the reveals in real-time?
- [ ] After the draw completes:
  - [ ] Are the seeds permanently stored in the database?
  - [ ] Does the bracket view reflect the draw order?
- [ ] **Fallback test:** Disable WebSocket (or test in a browser that blocks WS)
  - [ ] Does the page fall back to 3-second polling?
  - [ ] Does the polling indicator show amber?
  - [ ] Do the draw results still appear (just without animation)?

### 8E: Scheduling Panel

1. In the TOC, go to the Schedule tab

**Check:**
- [ ] Can you see scheduled matches with times?
- [ ] Can you manually reschedule a match?

### 8F: Check-In Control Panel

1. In the TOC Schedule tab, look for the Check-In Control section

**Check:**
- [ ] Can you open/close check-in for a round?
- [ ] Can you force-check-in a specific participant?
- [ ] Does the check-in status update in real-time?

### 8G: Display Name Override Toggle

1. In the TOC Settings, look for the "Display Name Override" toggle

**Check:**
- [ ] Can you toggle between showing team names vs. organization names?
- [ ] Does the change reflect in brackets and match cards?

### 8H: Dispute Resolution

1. In the TOC, go to the Disputes tab

**Check:**
- [ ] Can you see any active disputes?
- [ ] Can you resolve a dispute (accept/reject/reset match)?

---

## Part 9 — Match Medic (Phase 3)

**Goal:** Test the match healing/recovery system for organizers.

1. In the TOC Matches tab, find a match in error or disputed state
2. Look for the "Match Medic" option

**Check:**
- [ ] Can the organizer reset a match to a previous state?
- [ ] Can scores be corrected?
- [ ] Does the correction propagate through the bracket?
- [ ] Is there an audit log of the correction?

---

## Part 10 — DeltaCoin Economy (Phase 4)

**Goal:** Test the DeltaCoin virtual currency integration.

### 10A: View Wallet

1. Log in as any user
2. Go to the wallet/economy section

**Check:**
- [ ] Does your DeltaCoin wallet show a balance?
- [ ] Can you see transaction history?

### 10B: DeltaCoin Tournament Payment (P4-T01)

1. Register for a tournament with a DeltaCoin entry fee
2. Complete the payment

**Check:**
- [ ] Does the payment deduct from your wallet?
- [ ] Is a transaction record created with correct reason?
- [ ] Does the registration status update to `payment_submitted`?

### 10C: Payment Expiry (P4-T02)

1. Start a registration that requires payment but do NOT submit payment
2. Wait for the payment deadline (or check via admin)

**Check:**
- [ ] Does the payment expire after the deadline?
- [ ] Is the registration moved to an expired/cancelled state?
- [ ] Are DeltaCoins refunded if payment was partially processed?

---

## Part 11 — Notification System (Phase 4)

**Goal:** Verify notifications fire correctly for all tournament events.

### 11A: Registration Notifications (P4-T06)

1. Register for a tournament

**Check:**
- [ ] Do you receive an in-app notification for "Registration Submitted"?
- [ ] Does it appear in the notification bell/dropdown?

2. Have the organizer approve/reject the registration

**Check:**
- [ ] Do you receive "Registration Confirmed" or "Registration Rejected" notification?
- [ ] Does the rejection notification include a reason?

### 11B: Payment Notifications

1. Submit a payment for a tournament

**Check:**
- [ ] Do you receive "Payment Submitted" notification?
- [ ] When payment is verified: "Payment Verified" notification?
- [ ] When payment is rejected: "Payment Rejected" notification with reason?

### 11C: Check-In Open Notification

1. As organizer, open check-in for a tournament round

**Check:**
- [ ] Do ALL confirmed participants receive "Check-In is Now Open" notification?

### 11D: Waitlist Promotion Notification

1. Cancel a confirmed registration
2. Check the next person on the waitlist

**Check:**
- [ ] Does the promoted player receive a "Waitlist Promotion" notification?

---

## Part 12 — Teams & Organizations

**Goal:** Verify team browsing, creation, and management.

### Browse & View Teams

1. Go to **http://127.0.0.1:8000/teams/**
2. Click on **Crimson Syndicate** → **http://127.0.0.1:8000/teams/crimson-syndicate/**

**Check:**
- [ ] Does the team directory load?
- [ ] Can you see team names, tags, and games?
- [ ] Does the detail page show roster, game, and tag?

### Manage Your Team

1. Log in as **dc_tanvir** → **http://127.0.0.1:8000/teams/crimson-syndicate/manage/**

**Check:**
- [ ] Does the management page load?
- [ ] Can you see team settings and roster controls?
- [ ] Are member roles visible?

### Create a New Team

1. Go to **http://127.0.0.1:8000/teams/create/**

**Check:**
- [ ] Does the team creation form load?
- [ ] Can you fill in name, tag, game and create successfully?

### Organizations

**Check:**
- [ ] Org listing: **http://127.0.0.1:8000/orgs/**
- [ ] Org detail: **http://127.0.0.1:8000/orgs/titan-esports/**
- [ ] Org hub (logged in as dc_nabil): **http://127.0.0.1:8000/orgs/titan-esports/hub/**

---

## Part 13 — Organizer Console — Tournament Creation

**Goal:** Test tournament creation from scratch.

1. Log in as **dc_omar**
2. Go to **http://127.0.0.1:8000/tournaments/organizer/create/**
3. Fill in the form:
   - **Name:** "Test Tournament Alpha"
   - **Game:** VALORANT
   - **Format:** Single Elimination
   - **Participation Type:** Team
   - **Platform:** PC
   - **Mode:** Online
   - **Max Participants:** 8
   - **Min Participants:** 4
   - **Dates:** Registration start (today), end (+1 week), tournament start (+2 weeks)
   - **Prize Pool:** 5000
   - **Description:** "A test tournament for manual testing"
4. Toggle options: Featured, Check-in, Certificates

**Check:**
- [ ] Does the form load with all fields?
- [ ] Do dropdowns work for Game, Format, Platform, Mode, Participation Type?
- [ ] Do toggle switches work?
- [ ] Does the tournament get created successfully?
- [ ] Are you redirected to the tournament's organizer page?

---

## Part 14 — Dashboard & My Tournaments

**Goal:** Check the player dashboard and personal tournament views.

1. Log in as **dc_tanvir**

**Check:**
- [ ] Dashboard loads: **http://127.0.0.1:8000/dashboard/**
- [ ] My Tournaments loads: **http://127.0.0.1:8000/tournaments/my/**
- [ ] My Registrations loads: **http://127.0.0.1:8000/tournaments/my/registrations/**
- [ ] Can you distinguish active vs completed tournaments?

---

## Part 15 — Search

**Goal:** Test the search functionality.

1. Go to **http://127.0.0.1:8000/search/**

**Check:**
- [ ] Search "Valorant" — tournament results appear?
- [ ] Search "Crimson" — team shows up?
- [ ] Search "dc_tanvir" — user shows up?

---

## Part 16 — Spectator View

**Goal:** Test the public spectator pages.

1. Go to **http://127.0.0.1:8000/spectator/**

**Check:**
- [ ] Does the spectator tournament list load?
- [ ] Can you view tournament details from spectator view?

---

## Part 17 — The Admin Panel

**Goal:** Verify the Django admin panel works correctly.

### Admin Dashboard Performance

1. Go to **http://127.0.0.1:8000/admin/**

**Check:**
- [ ] Does the admin dashboard load **quickly** (under 2 seconds)?
- [ ] Can you see stat cards (tournaments, registrations, matches, users)?
- [ ] Do the charts render (Tournament Status bar chart, Trends line chart)?
- [ ] Does the "Recent Registrations" table show 8 entries with tournament names?
- [ ] Does the "Upcoming Tournaments" table show slot fill counts?
- [ ] Are quick action buttons working?

### Admin CRUD

**Check:**
- [ ] Tournaments: list, view, edit, filter by status
- [ ] Registrations: list, view, filter by status
- [ ] Matches: list, view, filter by state
- [ ] Teams: list, view
- [ ] Users: list, view, search

---

## Part 18 — Edge Cases & Error Handling

### Non-existent Pages

**Check:**
- [ ] **http://127.0.0.1:8000/tournaments/this-does-not-exist/** → proper 404
- [ ] **http://127.0.0.1:8000/@nonexistent_user/** → 404 or "not found"

### Permission Boundaries

1. Log in as **dc_bot_slayer** (regular player)
2. Try to access organizer pages for someone else's tournament

**Check:**
- [ ] Are you blocked from managing someone else's tournament?
- [ ] Do you get a permission error or redirect?

### Duplicate Registration Prevention

1. Register for a tournament
2. Try to register again for the same tournament

**Check:**
- [ ] Does the system prevent duplicate registrations?
- [ ] Is the error message clear?

---

## Part 19 — Static Pages & Policies

**Check:**
- [ ] Privacy Policy: http://127.0.0.1:8000/privacy/
- [ ] Terms of Service: http://127.0.0.1:8000/terms/
- [ ] Cookie Policy: http://127.0.0.1:8000/cookies/
- [ ] Game Passport Rules: http://127.0.0.1:8000/game-passport-rules/

---

## Summary Checklist

| # | Section | What to Test | Status |
|---|---------|-------------|--------|
| 1 | Homepage | Page loads, navigation works | ☐ |
| 2 | Sign In | Login/logout/signup flows | ☐ |
| 3 | Profiles | View, edit, privacy settings | ☐ |
| 4 | Browse Tournaments | List, detail pages for all statuses | ☐ |
| 5 | Smart Registration | Eligibility, wizard, solo, fees, rules | ☐ |
| 6 | Guest Teams | Register, cap, conversion, invite link | ☐ |
| 7 | Waitlist | Auto-waitlist, promotion, notification | ☐ |
| 8 | TOC (Organizer) | Brackets, seeding, draw, schedule, check-in, disputes | ☐ |
| 9 | Match Medic | Reset, score correction, bracket propagation | ☐ |
| 10 | DeltaCoin Economy | Wallet, payment, expiry, refund | ☐ |
| 11 | Notifications | Reg/payment/check-in/waitlist events | ☐ |
| 12 | Teams & Orgs | Browse, create, manage, organization hub | ☐ |
| 13 | Tournament Creation | Full creation form with all options | ☐ |
| 14 | Dashboard | Player dashboard, my tournaments/registrations | ☐ |
| 15 | Search | Tournaments, teams, players | ☐ |
| 16 | Spectator | Public spectator views | ☐ |
| 17 | Admin Panel | Dashboard performance, CRUD, charts | ☐ |
| 18 | Edge Cases | 404s, permissions, duplicate prevention | ☐ |
| 19 | Static Pages | Privacy, terms, cookies | ☐ |

---

## Automated Test Coverage Reference

The automated test suite covers the following (run with `pytest`):

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_phase1_registration.py` | 32 | Core registration, eligibility, status flow |
| `test_phase2_registration.py` | 45 | Guest teams, waitlist, cap enforcement |
| `test_phase2_part2.py` | 32 | Check-in, display name override, draft auto-save |
| `test_phase3_part1.py` | 30 | Bracket generation, seeding, match medic |
| `test_phase3_part2.py` | 25 | Scheduling, disputes, Swiss rounds, 3rd place |
| `test_phase4_part1.py` | 22 | DeltaCoin payment, expiry, payment consolidation |
| `test_phase4_part2.py` | 26 | Guest conversion, rule evaluation, notifications, live draw |
| **Total** | **180 passed, 2 skipped** | |

Run the full suite:
```bash
python -m pytest tests/tournaments/ --tb=short -W ignore
```

---

## Seeded Data At a Glance

**19 Tournaments across 8 games:**
- 6 Completed (Valorant, CS2, LoL, Rocket League, FC 25)
- 7 Live (Valorant, Dota 2, Apex Legends, Overwatch 2, Rocket League)
- 6 Open Registration (Valorant, CS2, FC 25, LoL, Dota 2)

**24 Teams:**
- 6 Valorant, 4 CS2, 3 LoL, 3 Dota 2, 3 Apex, 3 Rocket League, 2 Overwatch 2
- FC 25 is solo — no teams

**3 Organizations:**
- Titan Esports (CEO: dc_nabil) — Dhaka Leviathans, Titan Valorant, Fury Esports
- Eclipse Gaming (CEO: dc_shafiq) — Dust2 Demons, Ancient Defense
- Crown Dynasty (CEO: dc_sumon) — AimBot Activated

**100 Users (all password: `DeltaCrown2025!`):**
- 40 "Grinders" — competitive players
- 40 "Casuals" — fun/relaxed players
- 20 "Pros" — pro players, org owners, casters
