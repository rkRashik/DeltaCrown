# DeltaCrown — Esports Platform Architecture Audit

*A narrative guide to how DeltaCrown compares to top-tier esports platforms, where the gaps are, and how to close them.*

---

## 1. The Check-in Dilemma

### The Story of Two Check-ins

Imagine you've registered for a 64-person Valorant tournament on FACEIT. Tournament day arrives. You open the platform 30 minutes before kickoff and click **Check In**. That's it — you've told the system "I'm here, I'm ready, don't give my slot away." This is the **tournament-level check-in**, and every serious platform has one.

Now the bracket goes live. Your first match is in 10 minutes. You click into your match room, and suddenly there's *another* check-in — a small "Ready" button you need to press before the match timer starts. This is the **match-level micro-check-in**, and it's where things get interesting.

### The Industry Standard

**FACEIT** uses a two-tier system. Tournament check-in confirms you're present for the event. Then, each match has its own ready-up with a tight 5-minute window. Miss it, and you're auto-forfeited. This is considered the gold standard because it handles the most common real-world scenario: a player registers for a tournament, checks in on time, but then disappears between rounds (went to eat, had a power outage, rage-quit after the first loss and didn't bother forfeiting).

**start.gg (formerly smash.gg)** leans more casual — there's a tournament check-in, but individual match readiness is handled by the TO (tournament organizer) calling names at physical events, or by a simple "report results" honor system online. This works for community events but falls apart at scale.

**The Rule**: The larger and more automated your tournament, the more you need per-match micro-check-ins.

### What DeltaCrown Has Today

DeltaCrown already has both tiers built:

1. **Tournament Check-in**: The `TournamentLobby` model has `check_in_opens_at`, `check_in_closes_at`, `auto_forfeit_no_show`. The `CheckIn` model tracks who confirmed. A dedicated check-in API (`CheckinViewSet`) handles opens, closes, force-check-ins, and blast reminders. This is solid.

2. **Match-Level Presence**: The match room uses WebSocket presence tracking. When you enter the room, your consumer registers you in Redis. Both players must be online for the waiting overlay to clear and the match workflow to begin. There's a 10-minute lobby auto-close timer. This effectively IS a micro-check-in — you're confirming readiness by being present.

### What DeltaCrown Should Do

The presence-based approach is actually more elegant than a manual "Ready" button, because it removes a redundant click. However, DeltaCrown should add one refinement: **an explicit "Ready" confirmation during the `direct_ready` or `lobby_setup` phase**, distinct from mere presence. Here's why:

Being in the room and being *ready to play* are different things. A player might enter the match room to review the opponent's profile or read the rules, but they aren't actually at their console yet. The phase pipeline already has `direct_ready` — this is where the explicit confirmation should live. Presence unlocks the room. The "Ready" button in the direct_ready phase confirms "I am sitting at my screen, my game is loaded, let's go."

**Recommendation**: Keep the current two-tier system. Tournament check-in for day-of attendance. WebSocket presence for match-room access. Then require an explicit "Ready" action in the first pipeline phase before the match clock starts.

---

## 2. The Ideal Match Lobby

### The Perfect 12-Minute Journey

Let's walk through what should happen from the moment two players are matched to the moment a winner is declared. We'll use a Valorant BO1 as the example, since it exercises every phase.

#### Minute 0 — The Pairing

The bracket engine has spoken. **Player A** and **Player B** are matched for Round 2, Match #7. Both receive a push notification: *"Your next match is ready. Enter the Match Room."*

On the hub, their match card shifts from "Scheduled" to "Lobby Open" with a glowing green border. A live countdown appears: *"Lobby closes in 9m 47s."*

#### Minutes 0–1 — Entering the Room

Player A clicks "Enter Match Room" and lands in the match room shell. The screen shows a clean split layout — their avatar on the left, a silhouette on the right labeled "Waiting for opponent." A subtle heartbeat animation pulses on the opponent's presence dot.

Player B enters 40 seconds later. Both presence dots light green. The waiting overlay dissolves. A system message appears in the chat: *"Both players connected. Match flow starting."*

#### Minutes 1–2 — Coin Toss

The `coin_toss` phase activates. A visual coin flip animation plays. Player A wins the toss. They choose: **Map Pick advantage** (meaning they get the first pick in the veto sequence). A banner confirms the result. Both players see it in real-time via WebSocket.

#### Minutes 2–4 — Map Veto

The `map_veto` phase activates. The map pool appears — 7 maps in a grid. The veto sequence is: A bans → B bans → A bans → B bans → A picks → B picks → last map is decider.

Each player gets 30 seconds per action. A live timer ticks down. When Player A bans Ascent, it grays out with a red "X" on both screens simultaneously. After the sequence, the final map — Haven — is confirmed with a brief spotlight animation.

#### Minutes 4–5 — Side Selection & Lobby Setup

Player B (who lost the toss) chooses their starting side: Attacker. Player A gets Defender. Both see the assignment.

The `lobby_setup` phase activates. A form appears where Player A (the host, determined by toss) enters the custom game lobby code and password. They type in `LOBBY123` / `pass456`. The system validates the fields aren't empty, then reveals them to Player B in a secure card. Player B copies the code and joins the lobby on their game client.

Both players click "In Lobby" to confirm they've joined the in-game lobby. A "Ready to Start" button appears.

#### Minutes 5–7 — Live Match

Both click Ready. The `live` phase activates. The match room transforms — a timer starts counting up, the background subtly shifts to the game's accent color (cyan for Valorant). The chat remains open for coordination or banter. A live score entry form is available but not mandatory during play.

#### Minutes 7–10 — Result Submission

The match ends in-game. Player A won 13–8. They enter the score on the results phase form: 13 (me) — 8 (opponent). They optionally upload a screenshot of the final scoreboard.

The system sends a confirmation request to Player B: *"Player A reported a 13–8 victory. Do you confirm?"* Player B has three options: **Confirm**, **Dispute**, or **Submit Different Score**. They click Confirm.

#### Minute 10 — Resolution

The match state transitions to `COMPLETED`. Winner advances in the bracket. Both players see the result card with a green check. The bracket node updates in real-time for all spectators on the hub.

If Player B had Disputed, the match would transition to `DISPUTED`, and a dispute record would be created with a reason code. An organizer would review the evidence and make a ruling.

If Player B goes AFK and doesn't respond within 24 hours, the result is `AUTO_CONFIRMED`.

### This Is What DeltaCrown Already Supports

The remarkable thing is that DeltaCrown's architecture already covers this entire flow. The tournament hub renders match cards with state-aware badges. The match room shell has a phase-based pipeline. The coin toss, map veto, side selection, lobby setup, live, and results phases are all defined. WebSocket presence tracking, real-time chat, dispute records, and evidence attachments all exist.

The experience described above is achievable today with the current codebase — it's a matter of polishing each phase's UI, tightening the timing, and ensuring the WebSocket layer delivers messages reliably.

---

## 3. eFootball vs. Valorant — Two Worlds, One Platform

### The Core Problem

eFootball and Valorant are as different as chess and basketball. One is a 1v1 sports simulation where two players share a virtual pitch. The other is a 5v5 tactical shooter where ten people coordinate across a complex map with abilities, economy, and round-by-round strategy. A platform that treats them the same will fail at both.

### eFootball: The Gentleman's Duel

**What makes it different:**
- **1v1 only.** There are no teams. Two players, one match.
- **No map veto.** There are no maps in the Valorant sense. There might be a stadium selection, but it's cosmetic.
- **No side selection.** Both players play on the same pitch — there's no "Attacker vs. Defender."
- **Platform match.** Players exchange their eFootball IDs, find each other in-game via friend invite or match code, and play. The platform doesn't host the match — it coordinates it.
- **Score is simple.** It's goals scored: 3–1, 0–0 (then penalties), etc.
- **Matches are fast.** An eFootball match takes 12–15 minutes.

**The ideal DeltaCrown flow for eFootball:**

```
direct_ready → lobby_setup → live → results → completed
```

Phase 1 (`direct_ready`): Both players confirm they're at their console and their game is loaded. No coin toss needed — there's no advantage to choose. The pipeline skips coin_toss, map_veto, and side_selection entirely.

Phase 2 (`lobby_setup`): The credential exchange. Player A's eFootball ID is revealed to Player B, and vice versa. This is pulled automatically from their Game Passport profile. One player creates a friend match in eFootball; the other joins using the shared ID. Both click "In Match" to confirm.

Phase 3 (`live`): Timer runs. Chat is open.

Phase 4 (`results`): Score submission — goals for each side. Screenshot proof of the final result. Opponent confirms or disputes.

**The key insight for eFootball**: Speed and simplicity. An eFootball tournament with 64 players means 63 matches. If each match takes 15 minutes but the pre-match ceremony takes 8 minutes, you've added 8 hours of dead time. The pipeline must be 2 minutes or less before kickoff.

### Valorant: The War Room

**What makes it different:**
- **5v5 teams.** Ten players must coordinate. A team captain represents the team in the match room.
- **Map veto is critical.** The map directly affects strategy, agent composition, and win probability. Teams prepare specific strategies for specific maps. A fair veto process is non-negotiable.
- **Side selection matters.** Attacker vs. Defender on certain maps (like Breeze or Icebox) is a meaningful competitive advantage.
- **Custom lobby hosting.** One team creates a private custom game in Valorant, generates a lobby code, and shares it with the opponent.
- **Score is round-based.** 13–8, 14–12, 13–11 in overtime. The score breakdown by half (first half vs. second half) can be relevant for tiebreakers.
- **Matches are long.** A BO1 takes 30–45 minutes. A BO3 can take 2+ hours.

**The ideal DeltaCrown flow for Valorant:**

```
coin_toss → map_veto → side_selection → lobby_setup → live → results → completed
```

Phase 1 (`coin_toss`): Fair randomization determines which team gets an advantage — usually first map pick or first ban in the veto sequence.

Phase 2 (`map_veto`): The full ban/pick ceremony with the configured map pool. Both captains take turns. 30-second timers per action. Real-time WebSocket updates show each action as it happens.

Phase 3 (`side_selection`): The team that lost the toss (or a configured rule) picks their starting side on the selected map.

Phase 4 (`lobby_setup`): Host team creates the custom game in Valorant client. They enter the lobby code and password into the match room form. The opposing team receives the credentials and joins. All 10 players confirm "In Lobby."

Phases 5–6 (`live → results`): Match plays out. Score submitted with optional screenshot. Confirmed by opposing captain.

**The key insight for Valorant**: Every pre-match phase matters competitively. Cutting corners (like skipping the veto) would make the platform unsuitable for serious competition. But the phases must be smooth and fast — a laggy veto UI or a broken lobby code exchange will hemorrhage users.

### How DeltaCrown Handles This Today

DeltaCrown's archetype system already differentiates the two:

- **`sports` archetype** (eFootball, EA FC, Rocket League): `['direct_ready', 'lobby_setup', 'live', 'results', 'completed']`
- **`tactical_fps` archetype** (Valorant, CS2, R6 Siege): `['coin_toss', 'map_veto', 'side_selection', 'lobby_setup', 'live', 'results', 'completed']`

The `GameMatchPipeline` model stores the phase order per game, and the frontend's `match-room-core.js` dynamically renders only the phases in the pipeline. This is architecturally correct.

The gap isn't in the architecture — it's in the **polish of each phase module**. The coin toss needs a satisfying visual animation. The map veto needs real-time ban/pick rendering with countdown timers. The lobby setup needs seamless credential exchange, ideally auto-populated from the Game Passport.

---

## 4. DeltaCrown Gap Analysis — What's Missing to Beat the Best

### What DeltaCrown Already Does Well

Before listing gaps, it's important to acknowledge what's already strong:

1. **Phase-based match pipeline.** The archetype system with configurable phase order is more flexible than FACEIT's one-size-fits-all approach. DeltaCrown can support any game by defining a new archetype.

2. **Real-time WebSocket infrastructure.** Match rooms have presence tracking, heartbeat health checks, live chat, and group broadcast. The consumer architecture with Redis-backed presence is production-grade.

3. **Tournament lifecycle management.** The state machine (draft → published → registration → live → completed) with enforced transitions is robust. The bracket engine supports single/double elimination, round robin, Swiss, and group+playoff.

4. **Multi-game Game Passport.** The `GameProfile` model supports 11+ games with structured identity fields, verification status, and rank tracking. This is more comprehensive than most competitors.

5. **Dispute system.** Full dispute workflow with reason codes, evidence attachments, escalation, and organizer resolution. Most indie platforms have nothing beyond a Discord DM.

6. **Team infrastructure.** Organizations, teams, rosters, invitations, role-based membership — the social layer exists.

### Gap 1: Anti-Cheat & Match Integrity

**What FACEIT has**: A proprietary anti-cheat client (FACEIT AC) that runs during matches for FPS games. Server-side demo recording. Automated replay analysis for suspicious behavior.

**What DeltaCrown lacks**: Any form of automated anti-cheat or match integrity verification. The `MatchVerification` model has confidence levels (HIGH, MEDIUM, LOW, NONE), but there's no automated system feeding into it. Everything relies on manual organizer review and screenshot evidence.

**What to build**: For the immediate future, DeltaCrown doesn't need a custom anti-cheat. Instead:
- **Mandatory screenshot proof** for result submissions (already supported, just needs to be enforced per-game).
- **Riot API / Steam API score ingestion** — automatically pull match results from the game's API to cross-reference against player-submitted scores. The `source` field on `MatchResultSubmission` already supports `riot_api` and `steam_api` — the integration just needs to be built.
- **Statistical anomaly detection** — flag matches where reported scores are wildly inconsistent with player skill ratings (e.g., a Bronze player allegedly beating a Radiant 13–0).

### Gap 2: Automated Bracket Advancement

**What FACEIT has**: When a match concludes, the winner is *automatically* placed into the next bracket node. If it's a BO3, the system tracks map scores across the series and advances the overall winner.

**What DeltaCrown has**: The `BracketNode` model has a doubly-linked tree with `parent_node` / `parent_slot` / `child1_node` / `child2_node`. The bracket generation service creates the structure.

**What's missing**: A clear **automated advancement service** that listens for match completion events (via WebSocket or signal) and automatically:
1. Sets the winner on the current `BracketNode`
2. Writes the winner's ID and name into the parent node's corresponding slot (`parent_slot = 1` or `2`)
3. Creates or activates the next match if both slots in the parent are now filled
4. Handles losers bracket progression in double elimination
5. Broadcasts bracket update to the tournament WebSocket group

This should be a post-save signal on `Match` that triggers when `state` transitions to `COMPLETED`.

### Gap 3: BO3/BO5 Series Management

**What FACEIT has**: A series is treated as a container for multiple maps. The veto determines the order of maps. If Team A wins map 1 and map 2, the series ends 2–0 without playing map 3. Score tracking per map, per series.

**What DeltaCrown has**: The `GameMatchConfig` supports `BO1, BO3, BO5, BO7` formats. The `MatchVetoSession` handles the veto sequence.

**What's missing**: A **Series model** (or series tracking on the Match model) that:
1. Links multiple map matches under a single series
2. Tracks the overall series score (2–1, 2–0, etc.)
3. Ends the series early when one team clinches (e.g., 2 wins in BO3)
4. Runs the map veto sequence once at the start, then progresses through maps in order
5. Handles server-swap rules between maps (loser picks side on next map)

Currently, each match is standalone. For BO3+, DeltaCrown would need to either add a `parent_series_id` field to Match or create a dedicated `MatchSeries` model.

### Gap 4: Queue/Matchmaking System

**What FACEIT has**: The flagship feature — a queue where players join, get ELO-matched with opponents, and a match is automatically created. No need for a tournament bracket.

**What DeltaCrown has**: Only bracket-based tournament matching. No ad-hoc queue.

**What to build**: For competitive ladders and casual ranked play, DeltaCrown needs:
1. A `MatchmakingQueue` model per game, with ELO/skill-based grouping
2. A background task (Celery) that periodically pops paired players from the queue
3. Auto-created matches with reduced ceremony (skip tournament-level check-in, go straight to match room)
4. A ranked ladder leaderboard that updates from queue match results

This is a major feature, but it's the single biggest differentiator that would let DeltaCrown compete with FACEIT for daily active engagement (not just tournament days).

### Gap 5: Spectator & Broadcast Integration

**What FACEIT has**: Match rooms have spectator access. Organizers can share match room links with casters. Live stats feeds power overlay widgets for streams.

**What DeltaCrown has**: The WebSocket consumer has role-based access (Organizer/Admin/Participant/Spectator), and there are `stream_youtube_url` / `stream_twitch_url` fields on the Tournament model.

**What's missing**:
- A **spectator view** of the match room (read-only, no action buttons, sees presence + chat + score updates) — the consumer already supports non-participant connections, but the frontend doesn't have a spectator-mode layout.
- **OBS/stream overlay integration** — a lightweight JSON endpoint or WebSocket feed that overlay widgets can consume to show live bracket progress, current match scores, and player stats.

### Gap 6: ELO / Skill Rating System

**What FACEIT has**: A proprietary ELO system that updates after every match. Visible on profiles. Used for matchmaking and seeding.

**What DeltaCrown has**: The `GameProfile` model has `rank_name`, `rank_points`, `peak_rank`, `matches_played`, `win_rate`, `kd_ratio`. The bracket system supports `RANKED` seeding method. The `MatchVerification` model has `ranking_weight` based on confidence level.

**What's missing**: An active **ELO calculation engine** that:
1. Runs after each confirmed match result
2. Updates both players' skill ratings based on the outcome and the rating difference
3. Stores rating history for graphs/trends
4. Integrates with the bracket engine for seeded tournaments (higher-rated players get favorable draws)

The data model is ready — the calculation logic and the feedback loop between match results and player ratings need to be built.

### Gap 7: Webhook & Discord Bot Ecosystem

**What FACEIT has**: Extensive webhook system for match results, bracket updates, and player stats. Community-built bots automate tournament management in Discord servers.

**What DeltaCrown has**: `discord_webhook_url` on both Tournament and Team models. A support ticket bridge.

**What's missing**: An actual **event webhook dispatch system** that fires HTTP POST payloads to configured URLs when key events happen:
- Tournament status changes (registration opened, bracket live, completed)
- Match results (with scores, winner, verification status)
- Brackets updated (new round started, finals scheduled)
- Disputes opened/resolved

This is relatively straightforward to build with Django signals and Celery tasks, and it would unlock the entire Discord bot ecosystem for DeltaCrown tournaments.

### Gap 8: Mobile-Native Match Room Experience

**What FACEIT has**: A mobile app with match room functionality — notifications, ready up, score report, chat — all in a native-feeling mobile interface.

**What DeltaCrown has**: Responsive web design. The match room templates use Tailwind responsive utilities. Mobile-specific nav behavior exists (`initMobileTopNavBehavior`).

**What to progress**: The web-based mobile experience is functional but could be improved with:
- **Push notifications via Service Worker** — "Your match is ready" / "Opponent entered the lobby" / "Please submit your score"
- **Haptic feedback** on key actions (match found, coin toss result)
- **Reduced ceremony** on mobile — collapse verbose phases, use swipe gestures for veto actions

---

## Closing Perspective

DeltaCrown is architecturally more complete than most indie esports platforms. The tournament lifecycle, bracket engine, multi-game support, phase pipeline, and real-time WebSocket infrastructure are all production-grade. The archetype system for game-specific match flows is a genuinely clever design that most competitors lack.

The gaps are primarily in three areas:

1. **Automation** — bracket advancement, ELO updates, and API-based result verification need to happen automatically, not manually.
2. **Engagement loops** — matchmaking queues and daily ranked ladders keep players coming back between tournament days.
3. **Ecosystem** — webhooks, spectator views, and stream integration turn DeltaCrown from a tournament tool into a platform that organizers build communities around.

None of these gaps are architectural — the data models and infrastructure are in place. They're implementation tasks that build on what already exists. The foundation is solid. Now it's about filling in the floors.
