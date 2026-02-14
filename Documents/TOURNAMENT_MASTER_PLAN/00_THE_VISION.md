# The DeltaCrown Tournament System — A Complete Vision

*Written February 14, 2026*  
*Read time: ~20 minutes*

---

## What This Document Is

This is the story of what we're building, told in plain language. No code snippets. No architecture diagrams yet. Just a clear picture of what the tournament system should feel like, how it should work, and why every decision matters.

Read this first. Everything else builds on this.

---

## Part 1: What Are We Actually Building?

Imagine a player named **Rafid** from Dhaka. He loves playing Valorant. He heard about DeltaCrown from a friend and signed up last week. Today, he wants to compete.

Here's what his journey should look like:

### Rafid Discovers a Tournament

He opens DeltaCrown. The homepage shows him **featured tournaments** — not a random list, but tournaments that match his game, his skill level, and his region. There's one tonight: "Valorant Rising Stars — Solo Queue, BO3, ৳50 entry, ৳5,000 prize pool." The card shows the game's color theme, a countdown timer, 47 of 64 slots filled, and a "Register Now" button that pulses with energy.

He clicks it.

### The Registration Experience

Instead of a long, confusing form, he sees a **smart registration wizard**. Because he already linked his Riot account in his Game Passport, the form already knows his Riot ID and region. Those fields are pre-filled and locked — no typos, no disputes about identity later.

The form shows him a checklist:
- ✅ Riot ID verified
- ✅ Account level 20+ (minimum requirement)  
- ✅ Age 16+ confirmed
- ⬜ Entry fee: ৳50

He pays with bKash — taps, confirms, done. His registration is **instantly confirmed** because the system verified everything automatically. No waiting for an admin to check his screenshot. He gets a notification: "You're in! Check-in opens 30 minutes before the tournament starts."

If he's registering a team instead of solo, the wizard is equally smart. He selects his team, the system pulls the roster from the organizations app, verifies each player's Game Passport, checks roster size against the game's config (5 players minimum for Valorant, up to 2 subs), and flags any issues upfront: **"Player3 hasn't linked a Riot account yet — they need to do this before you can register."**

### The Lobby

Thirty minutes before the tournament starts, Rafid gets a notification: "Check-in is open." He opens the **Tournament Lobby** — a real-time hub where he can see:

- Who else checked in (with live counter: 58/64 checked in)
- Tournament announcements from the organizer
- His match schedule (first match in 15 minutes)
- A bracket preview showing where he's seeded
- A chat area to talk with fellow competitors

He taps "Check In." His name lights up green. He's ready.

### The Match

His first match is called. He sees a **Match Detail Page** with:
- His opponent's name, team, Riot ID, and recent form (W-W-L-W)
- The map pool, format (BO3), and rules
- A timer counting down to the match start
- Instructions for joining the custom lobby

They play. Rafid wins 2-1. Now comes the important part.

### Result Submission

Both players submit their results through the platform. Rafid clicks "Submit Result," selects his scores (13-8, 7-13, 13-10), and uploads a screenshot. His opponent receives a notification: "Your opponent submitted a result. Please verify."

**If both agree**, the result is confirmed instantly. The bracket updates in real-time. Both players see their next match.

**If they disagree**, a dispute is automatically created. The system assigns a referee (if the tournament has staff) or queues it for the organizer. Both players can submit evidence. The resolution follows a clear workflow with deadlines.

### The Bracket Comes Alive

As matches complete, the bracket **updates in real-time**. Spectators watching from outside can see the live bracket without logging in. Each match node shows scores, winner highlights, and you can click into any match for details.

For group stage formats, the standings table recalculates after every match — points, tiebreakers, head-to-head, game difference. All automatic, all instant.

### Tournament Completion

The final match is played. The system determines the winner using game-specific scoring rules. Then, automatically:

1. **Results are finalized** — Winner, runner-up, top 4, all placements locked
2. **Prizes are distributed** — ৳5,000 split according to the tournament's coin policy, automatically credited to wallets
3. **Stats are updated** — Win rates, K/D ratios, ELO ratings, all recalculated across the leaderboards app
4. **Certificates are generated** — PDFs with QR codes for verification
5. **Notifications fire** — Winners notified, all participants get a summary
6. **The tournament archive is created** — A permanent record with full bracket, all match results, every statistic

### The Archive

Months later, Rafid can go back and look at this tournament. Every match, every score, every participant. The data is permanent and useful — for his profile (showing his tournament history), for organizers (seeing participation trends), and for the platform (powering rankings and recommendations).

---

## Part 2: The Organizer's Perspective

Now let's follow **Nadia**, a community organizer running weekly Valorant tournaments on DeltaCrown.

### Creating a Tournament

Nadia opens the **Organizer Dashboard**. She clicks "Create Tournament" and sees a clean, step-by-step wizard:

**Step 1 — Basics:**
- Tournament name, description
- Select game (Valorant) — the system immediately loads game-specific configuration
- Format: Single Elimination, Double Elimination, Round Robin, Swiss, or Group Stage → Bracket
- Team size (auto-filled from Valorant's roster config: 5v5)
- Schedule: start date, registration opens/closes

**Step 2 — Rules & Scoring:**
- Match format: BO1 / BO3 / BO5 (options loaded from game config)
- Map pool, ban system
- Custom rules (text editor)
- Scoring type (Win/Loss for elimination, points for groups)
- Tiebreaker order (game-specific defaults provided)

**Step 3 — Registration Settings:**
- Maximum participants
- Entry fee (free, fixed amount, or custom)
- Registration deadline
- Check-in requirement (yes/no, window duration)
- Eligibility requirements (min rank, region lock, age restriction, etc.)
- Custom registration questions
- Auto-approve or manual review

**Step 4 — Prizes & Rewards:**
- Prize pool distribution (winner, runner-up, top 4, participation)
- Coin policy configuration
- Certificate toggles

**Step 5 — Staff & Permissions:**
- Assign co-organizers, referees, moderators
- Each role gets specific permissions
- Referees can be assigned to specific matches later

**Step 6 — Review & Publish:**
- Full preview of how the tournament page will look
- Save as draft or publish immediately
- Option to save as template for recurring events

### The Organizer Hub

Once the tournament is live, Nadia has a **command center**:

**Overview Tab:** Tournament health at a glance — registrations, check-ins, match progress, disputes, revenue.

**Participants Tab:** Every registration with status (confirmed, pending payment, rejected). She can approve, reject, refund, or message any participant. Bulk actions for efficiency.

**Bracket Tab:** Visual bracket editor. She can swap seeds, set byes, and manually adjust matches if needed. The bracket updates for everyone in real-time.

**Matches Tab:** Every match with its status. She can report results on behalf of players, resolve disputes, assign referees, add moderator notes, and force-complete stuck matches.

**Results Tab:** An inbox of pending result submissions. She can verify, reject, or override. She can also export all results to CSV.

**Finances Tab:** Revenue breakdown — total entry fees, payouts, platform fee. Transaction history for full auditability.

**Staff Tab:** Manage her tournament team. See which referee handled which matches. Staff performance metrics.

**Analytics Tab:** Participation trends, dropout rates, average match duration, game-specific stats, check-in rates.

### After the Tournament

Nadia clicks "Complete Tournament." The system runs the full completion pipeline:
- Determines final placements
- Runs prize distribution
- Generates certificates
- Archives everything
- Sends summary notifications

She can also **clone the tournament** for next week — one click, all settings copied, new dates applied.

---

## Part 3: The Admin's Perspective

The DeltaCrown platform admin — let's call him **Arif** — needs a different view.

### Platform-Wide Tournament Management

Arif can see all tournaments across the platform:
- Active tournaments (ongoing right now)
- Upcoming tournaments (registration open)
- Completed tournaments (archived)
- Problematic tournaments (disputes, stuck matches, late organizers)

He has override powers on any tournament. He can cancel a tournament, refund all participants, suspend an organizer, or intervene in a dispute.

### Financial Oversight

He can see all DeltaCrown transactions related to tournaments — entry fees, payouts, refunds. He can audit any transaction. He can set platform fees. He can approve withdrawal requests from organizers.

### Quality & Moderation

- Flagged tournaments (reported by players)
- Organizer reputation scores
- Player reports and bans
- Dispute escalation queue (disputes that organizers couldn't resolve)

### Data & Analytics

- Daily/weekly/monthly tournament counts
- Player engagement metrics
- Revenue dashboards
- Game popularity trends
- Regional activity heatmaps

---

## Part 4: What Makes This "Smart"

DeltaCrown isn't just a bracket generator. Here's what makes it modern:

### 1. Game-Aware Everything
The tournament system doesn't know what "Valorant" is. It asks the Games app. The Games app says: "5v5, BO3 default, these maps, these roles, these identity fields, this scoring schema." Tournaments just render whatever the game tells them. Adding a new game means adding its config — zero tournament code changes.

### 2. Identity Verification Built In
Every player's game identity comes from their Game Passport (GameProfile model). When they register for a tournament, the system cross-references their verified identity. No more "I swear that's my Riot ID" — the platform knows.

### 3. Automatic Everything
- Registration eligibility → automatic
- Payment verification → automatic (when using DeltaCrown wallet)
- Result confirmation → automatic (when both players agree)
- Prize distribution → automatic
- Stats updates → automatic (via event bus)
- Certificate generation → automatic
- Check-in enforcement → automatic

### 4. Event-Driven Architecture
When a match completes, the tournament app doesn't need to call the leaderboards app, the notifications app, the economy app, and the user profile app one by one. It publishes a single event: `match.completed`. Every other app listens and reacts independently. Clean, decoupled, scalable.

### 5. Multi-Format Support
Single elimination, double elimination, round robin, Swiss, group stage into bracket — all supported by the same engine, configured by the game's tournament config. The bracket generator is pluggable: adding a new format means adding one new generator class.

### 6. Full Lifecycle Tracking
Every tournament goes through a clear lifecycle:

```
DRAFT → PUBLISHED → REGISTRATION_OPEN → REGISTRATION_CLOSED → CHECK_IN → 
LIVE → COMPLETING → COMPLETED → ARCHIVED
```

Every transition is logged, event-published, and permission-gated. You can't skip states. You can't go backwards (except cancellation). The system enforces the lifecycle.

### 7. Archival as a First-Class Feature
Completed tournaments aren't just "done." They become permanent records — searchable, linkable, and useful. A player's profile shows their tournament history. An organizer's page shows their track record. The platform shows its most prestigious events.

---

## Part 5: The Technical Reality Check

We're not starting from zero. And we're not keeping everything. Here's the honest situation:

### What We KEEP (Working Code)
- **All 40+ tournament models** — they represent real data, real schema, and real database tables
- **Bracket generation logic** — single/double elimination works
- **Match state machine** — the state transitions are solid
- **Registration data model** — Registration, Payment, PaymentVerification
- **Certificate generation** — PDF/PNG with QR codes
- **Group stage models** — Group, GroupStanding, GroupStage
- **Smart registration models** — RegistrationDraft, RegistrationQuestion, RegistrationAnswer, RegistrationRule
- **Tournament template model** — for cloning

### What We REBUILD (Clean Up)
- **Views** — current views bypass tournament_ops entirely, reference deleted fields, and have massive duplication
- **Services** — there are 3 registration services, 2 check-in services, 2 bracket services, 2 analytics services. We consolidate to one each.
- **Adapters** — several are stubs (economy, notification). Others reference wrong field names. All need to be verified.
- **Templates** — 3 variants per registration step, backup directories, marketplace templates. We build clean.
- **URLs** — 80 URL patterns is too many. We organize into logical groups.

### What We REMOVE (Legacy Garbage)
- The legacy `Game` model inside tournaments (the canonical one is in apps.games)
- All `riot_id` / `steam_id` hardcoded references
- `views_old_backup.py`
- `registration_demo_backup/` templates
- `marketplace/` templates (feature removed)
- `old_backup/` templates
- Duplicate services (keep the better one, delete the worse one)
- The old boolean-flag staff system (keep the Phase 7 capability-based one)
- The old `Dispute` model in match.py (keep the Phase 6 `DisputeRecord`)

### What We BUILD (New)
- Unified service layer that each view calls
- Clean template set with no duplicates
- Proper event publishing from tournaments
- Wired adapters for economy and notifications
- Organizer command center UI
- Tournament archive pages
- Tournament cloning
- Real-time lobby with WebSocket (future, not MVP)

---

## Part 6: The Two-App Architecture

We're keeping two apps for clear separation of concerns:

### `apps/tournaments/` — The Data Layer
This app owns:
- All Django models (database tables)
- Database migrations
- Django admin registrations
- Django signals that fire on model changes
- Management commands
- Celery tasks for background work

It's the **source of truth** for tournament data.

### `apps/tournament_ops/` — The Logic Layer
This app owns:
- Business logic services (registration, matching, disputes, results)
- Adapters to external apps (games, organizations, economy, notifications, leaderboards)
- DTOs for clean data transfer
- Domain events for cross-app communication
- Validation and eligibility rules

It's the **brain** that orchestrates operations.

### Views — Where Do They Live?
The views (URL handlers) live in `apps/tournaments/views/` because they render Django templates from `templates/tournaments/`. But they call `tournament_ops` services for all business logic.

```
User clicks "Register" 
  → tournaments/views/registration.py handles the HTTP request
  → calls tournament_ops/services/registration_service.py for logic
  → which calls tournament_ops/adapters/* to talk to other apps
  → result comes back to the view
  → view renders the template
```

This is the clean architecture pattern: views are thin, services are thick, adapters are boundaries.

---

## Part 7: Feature Map — Everything This System Does

Here's the complete feature list, organized by who uses it:

### For Players
1. **Browse & Discover** tournaments by game, format, region, entry fee, date
2. **Smart Registration** with game-identity auto-fill and eligibility pre-check
3. **Team Registration** with roster verification
4. **DeltaCrown Wallet Payment** for entry fees
5. **Tournament Lobby** with check-in, announcements, schedule
6. **Match Detail** with opponent info, rules, and result submission
7. **Result Submission** with screenshot upload and mutual verification
8. **Dispute Filing** with evidence and deadline tracking
9. **Certificate Download** for achievements
10. **Tournament History** on their profile
11. **Real-Time Stats** updated after every match
12. **Live Bracket View** as matches progress

### For Teams
13. **Team Registration** with automatic roster validation
14. **Roster Management** during registration (swap players, add subs)
15. **Team Stats** and tournament history
16. **Team Leaderboard** ranking (ELO, Crown Points)

### For Organizers
17. **Tournament Creation Wizard** (6-step, game-aware)
18. **Tournament Templates** (save & clone configurations)
19. **Registration Management** (approve, reject, refund, bulk actions)
20. **Bracket Editor** (manual seeding, bye assignment, swap participants)
21. **Match Management** (report results, force-complete, assign referees)
22. **Result Review Inbox** (verify/reject submitted results)
23. **Dispute Resolution Panel** (evidence review, ruling, penalties)
24. **Staff Management** (assign roles, track workload)
25. **Financial Dashboard** (entry fees, payouts, refunds)
26. **Analytics Dashboard** (participation, completion rates, timing)
27. **Check-In Management** (open/close check-in, substitute no-shows)
28. **Tournament Announcements** (broadcast to all participants)
29. **Tournament Health Monitor** (stuck matches, overdue results)
30. **Export Data** (CSV/Excel of participants, results, finances)

### For Platform Admins
31. **Platform-wide Tournament Listing** with filters and search
32. **Organizer Management** (verify, suspend, promote)
33. **Global Dispute Queue** (escalated disputes)
34. **Financial Oversight** (transactions, platform fees, auditing)
35. **Tournament Override** (cancel, complete, modify any tournament)
36. **Analytics & Reports** (platform health, trends, revenue)

### For the System (Automated)
37. **Eligibility Engine** — auto-check registration requirements
38. **Auto-Approve Registration** — when all rules pass
39. **Auto-Confirm Results** — when both parties agree
40. **Auto-Distribute Prizes** — on tournament completion
41. **Auto-Generate Certificates** — on placement determination
42. **Auto-Update Stats** — via event bus on match completion
43. **Auto-Escalate Disputes** — after deadline expiry
44. **Auto-Remind Players** — for pending result verification
45. **Check-In Deadline Enforcement** — auto-disqualify no-shows
46. **Lifecycle State Machine** — enforce valid state transitions
47. **Event Publishing** — match.completed, tournament.completed, etc.

---

## Part 8: What We Don't Build Yet (Future Features)

These are features we've seen on other platforms that we're not building in this phase, but we're designing the system so they can be added later:

1. **Real-Time WebSocket Updates** — brackets/scores updating live without page refresh (requires Django Channels, already in ASGI setup)
2. **Automatic Game API Integration** — pulling match results directly from Riot/Epic APIs (requires per-game API clients)
3. **League / Circuit System** — connecting multiple tournaments into a season with cumulative standings
4. **Prediction System** — bracket predictions for spectators
5. **Embeddable Widgets** — bracket/roster/standings widgets for external sites
6. **Streaming Integration** — linking Twitch/YouTube streams to matches
7. **Matchmaking Queue** — ELO-based automatic pairing (FACEIT-style, requires real-time infrastructure)

We will design the models and services so adding these later doesn't require rewriting core code. For example, the lifecycle state machine already has hooks for future states, and the event bus can power predictions and streaming alerts.

---

## Part 9: Success Criteria

How do we know we're done? When all of this works:

1. A player can browse tournaments, register (solo or team), pay, check in, play matches, submit results, receive prizes, and download certificates — all through clean, working pages.

2. An organizer can create a tournament from scratch, manage registrations, run the bracket, resolve disputes, distribute prizes, and archive the event — all from their dashboard.

3. An admin can see all tournaments, intervene when needed, and audit financial transactions.

4. The code has zero legacy references — no `riot_id`, no `apps.teams` FKs, no duplicate services, no backup files.

5. Every service in `tournament_ops` is wired to its adapter and connected to its view.

6. Events are published for all major actions and consumed by leaderboards/notifications.

7. Templates are clean — one version per page, using design tokens, no hardcoded game colors.

8. The full lifecycle works: DRAFT → PUBLISHED → REGISTRATION → CHECK-IN → LIVE → COMPLETED → ARCHIVED.

---

*This vision document sets the direction. The next documents break this into executable phases, specific tasks, and tracking mechanisms. But first, read this twice and make sure this is the platform you want to build. If it is, everything else follows.*
