# 🏗️ ENTERPRISE LIFECYCLE AUDIT — DeltaCrown Esports Platform

> **Audit Date**: April 1, 2026
> **Auditor**: Lead Platform Architect
> **Scope**: Full Tournament Lifecycle — Creation → Registration → Brackets → Match Lobbies → Results → Standings → Conclusion
> **Benchmark**: Faceit, Battlefy, Toornament
> **Constraint**: 512 MB RAM production server

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Critical Blockers & Logical Failures](#3-critical-blockers--logical-failures)
4. [Game-Adaptation Strategy](#4-game-adaptation-strategy)
5. [Codebase Cleanup List](#5-codebase-cleanup-list)
6. [The Refactor Roadmap](#6-the-refactor-roadmap)

---

## 1. Executive Summary

### Current State

DeltaCrown is an **ambitious but architecturally fragmented** esports platform. The codebase spans **88+ Django models**, **50+ REST endpoints**, **4 WebSocket consumers**, **22+ TOC frontend modules**, and **~10,000+ lines of Vanilla JS**. It covers an impressive breadth of features — from multi-format bracket generation to real-time match lobbies with coin tosses and map vetoes, dynamic registration forms, payment verification, dispute resolution, and a full tournament operations center.

### What Works

| Area | Verdict | Notes |
|------|---------|-------|
| **Service-Layer Architecture** | ✅ Solid | Clean adapter + DTO + service pattern (ADR-001). `tournament_ops/` decouples business logic from ORM. |
| **Game Configuration as Data** | ✅ Good Foundation | 11 games supported via DB-driven config (`GameRosterConfig`, `GameTournamentConfig`, `GameScoringRule`, `GameMatchResultSchema`). No hardcoded game logic in models. |
| **Match Room Real-Time** | ✅ Functional | MatchConsumer with presence tracking, heartbeat (25s), reconnect with exponential backoff, role-based message routing. |
| **Bracket Generation** | ✅ Extensible | Registry pattern with pluggable generators (SE, DE, RR, Swiss). DTO-only — no ORM coupling in service layer. |
| **WebSocket Security** | ✅ Layered | JWT middleware + session fallback + origin validation + token-bucket rate limiter (per-user and per-IP). |
| **TOC Command Center** | ✅ Feature-Rich | 22+ tabs, lazy-loaded, with unified overview API (Sprint 25), lifecycle stepper, health scoring, analytics. |

### What Is Broken or Dangerous

| Area | Verdict | Risk |
|------|---------|------|
| **Tournament State Machine** | 🔴 Not Enforced | Status field is a `CharField` with choices — zero state transition validation. Any code can set `COMPLETED → DRAFT`. |
| **Match Participant IDs** | 🔴 Dangling References | `participant1_id`/`participant2_id` are plain `IntegerField`, not FKs. No DB constraint validates they exist. |
| **Hub Polling Storm** | 🔴 RAM Killer | State poll (20s) + announcement poll (15s) + per-tab cache poll = **4-6 HTTP requests/minute per connected user**. On 512 MB, 50 concurrent hub users = collapse. |
| **WebSocket Broadcast Triplication** | 🟠 Wasteful | Match completion signal broadcasts to `match_{id}`, `tournament_bracket_{slug}`, AND `tournament_{id}` — three separate `group_send()` calls for one event. |
| **CSRF Gaps on AJAX POSTs** | 🟠 Exploitable | Some match room workflow POSTs rely on fetch header CSRF with multi-source fallback cascade. Stale tokens possible on long-lived pages. |
| **match-room.js Monolith** | 🟠 Bloated | Single 3,000+ line IIFE. All game types bundled. No code splitting. ~80-100 KB minified. Every socket message triggers full `renderAll()` — no selective re-render. |
| **No Idempotency on Result Submission** | 🟠 Data Integrity | Double-POST creates duplicate `MatchResultSubmission` records. The `idempotency_key` field exists on PaymentVerification but is never checked. |
| **Dead Code Accumulation** | 🟡 Tech Debt | Deprecated registration wizard, legacy `Dispute` model (replaced by `DisputeRecord`), unused `TemplateRating`/`RatingHelpful` models, deferred Steam API stubs. |

### Verdict vs. Industry Benchmarks

| Benchmark | Faceit | Battlefy | Toornament | DeltaCrown |
|-----------|--------|----------|------------|------------|
| Game-adaptive match flow | ✅ Per-game pipeline | ✅ Config-driven | ✅ Plugin system | 🟡 2 pipelines only (Valorant, eFootball) |
| Real-time match room | ✅ WebSocket + fallback | ✅ SSE + polling | ✅ WebSocket | ✅ WebSocket + poll fallback |
| Bracket formats | ✅ SE/DE/RR/Swiss/Groups | ✅ SE/DE/RR/Swiss | ✅ SE/DE/RR/Swiss/Custom | ✅ SE/DE/RR/Swiss/Groups |
| State machine enforcement | ✅ Strict (server-side) | ✅ Strict | ✅ Strict | 🔴 Not enforced |
| Map veto system | ✅ Full veto engine | ❌ External | ✅ Configurable | 🟡 Exists but only for Valorant |
| Anti-cheat integration | ✅ Native (Faceit AC) | ❌ None | ❌ None | 🔴 No hooks |
| Memory efficiency | ✅ Microservices | 🟡 Moderate | 🟡 Moderate | 🔴 Monolith, no optimization for 512 MB |

---

## 2. Architecture Overview

### App Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                        DJANGO APPS                               │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│  tournaments │ tournament_ops│    games     │   competition      │
│  (ORM/Views) │ (Services/   │ (Game Config │   (Rankings/       │
│              │  Adapters/   │  Rules/Roles)│    Match Reports)  │
│  88+ models  │  DTOs/Tasks) │  7 models    │   7 models         │
│  19 views    │  12 adapters │  1 service   │   3 services       │
│  50+ URLs    │  50+ APIs    │  2 URLs      │   Bounties         │
│  6 Celery    │  6 Celery    │              │                    │
│  4 WS cons.  │              │              │                    │
├──────────────┴──────────────┴──────────────┴────────────────────┤
│                        SHARED LAYERS                             │
├─────────────┬──────────────┬──────────────┬─────────────────────┤
│  accounts   │ organizations│  economy     │  notifications      │
│  (Users/    │ (Teams/      │ (Wallet/     │  (Email/Discord/    │
│   OAuth)    │  Roster)     │  DeltaCoin)  │   Push)             │
├─────────────┴──────────────┴──────────────┴─────────────────────┤
│                      INFRASTRUCTURE                              │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│   Redis      │  PostgreSQL  │   Celery     │  Django Channels   │
│  (Cache/WS/  │  (Primary    │  (Async      │  (WebSocket        │
│   Broker)    │   Store)     │   Tasks)     │   Consumers)       │
│  DB 0-3      │  Neon/Supabase│  Soft 2m    │  Capacity: 500     │
└──────────────┴──────────────┴──────────────┴────────────────────┘
```

### Tournament Lifecycle Flow

```
Tournament Creation (Organizer)
  │
  ├─→ DRAFT → PENDING_APPROVAL → PUBLISHED
  │
  ├─→ REGISTRATION_OPEN
  │     │
  │     ├─ Solo Registration (User → Form → Payment → Confirm)
  │     ├─ Team Registration (Captain → Roster → Payment → Confirm)
  │     └─ Smart Registration (Q&A → Auto-Approve/Review → Confirm)
  │
  ├─→ REGISTRATION_CLOSED
  │     │
  │     ├─ Bracket Generation (SE/DE/RR/Swiss/Group)
  │     ├─ Group Draw (Pot-based seeding, live ceremony WS)
  │     └─ Seed Assignment (slot-order, random, ranked, manual)
  │
  ├─→ LIVE
  │     │
  │     ├─ Match Lifecycle:
  │     │   SCHEDULED → CHECK_IN → READY → LIVE → PENDING_RESULT → COMPLETED
  │     │                                                    ↓
  │     │                                              DISPUTED → RESOLVED
  │     │                                                    ↓
  │     │                                                 FORFEIT
  │     │
  │     ├─ Match Room Pipeline (per game):
  │     │   Coin Toss → Veto/Direct → Lobby Setup → Server Live → Results
  │     │
  │     ├─ Group Stage → Standings Update → Advancement
  │     └─ Bracket Progression → Winner Advances → Next Round
  │
  └─→ COMPLETED → ARCHIVED
        │
        ├─ Prize Distribution (Wallet integration)
        ├─ Certificate Generation
        ├─ Ranking Score Computation
        └─ Trophy/Achievement Awards
```

### WebSocket Architecture

```
Client Browser
  │
  ├─ ws/match/<match_id>/          → MatchConsumer
  │   ├─ Presence tracking (15s heartbeat, 45s stale)
  │   ├─ Chat (400 char limit, dedup via message ID)
  │   ├─ State sync (score_updated, match_completed, dispute_created)
  │   └─ Credential broadcast (lobby codes, server info)
  │
  ├─ ws/tournament/<id>/           → TournamentConsumer
  │   ├─ Hub state updates (bracket, standings, announcements)
  │   └─ Check-in status broadcasts
  │
  ├─ ws/tournament/<id>/draw/      → LiveDrawConsumer
  │   └─ Dramatic seed reveal (2.5s delay per reveal)
  │
  └─ ws/tournament/<id>/group-draw/ → GroupDrawConsumer
      └─ Interactive pot-based group assignment with undo
```

### Redis Memory Map (512 MB Constraint)

```
DB 0 — Cache (framework cache, TOC overview, standings)
DB 1 — Celery Broker (task queue)
DB 2 — Celery Results (task state)
DB 3 — Channels (WebSocket groups, presence)

Channel Layer: capacity=500, expiry=10s, prefix='dc-ws'
WS Rate Limits: 10 msg/s/user, 20 burst, 3 connections/user, 16 KB max payload
```

---

## 3. Critical Blockers & Logical Failures

### 🔴 SEVERITY: CRITICAL (Must Fix Before Any New Features)

#### 3.1 Tournament State Machine Not Enforced

**Location**: `apps/tournaments/models/tournament.py` — `status` field
**Problem**: The `status` field is a plain `CharField(choices=...)`. Any code path can set any status at any time. There is no server-side state machine that validates transitions.

```
Current: tournament.status = 'COMPLETED'  # ← Works even from DRAFT
Expected: StateMachine.transition(tournament, 'COMPLETED')  # ← Validates LIVE → COMPLETED only
```

**Impact**: Invalid state transitions corrupt tournament lifecycle. A race condition in Celery tasks could advance a tournament that hasn't finished registration. Signals fire on `post_save` regardless of transition validity — notifications sent for phantom state changes.

**Evidence**: `apps/tournament_ops/services/tournament_lifecycle_service.py` has `auto_advance()` but exceptions are silently caught and passed. `apps/tournaments/signals.py` trusts the status field blindly.

**Fix**: Implement `django-fsm` or a custom `StateMachineService` with explicit `ALLOWED_TRANSITIONS` dict. Add a `CheckConstraint` or custom `save()` override that rejects invalid transitions.

---

#### 3.2 Match Participant IDs Are Dangling References

**Location**: `apps/tournaments/models/match.py` — `participant1_id`, `participant2_id`
**Problem**: These are `IntegerField`, not `ForeignKey`. No database constraint validates they reference existing users or teams. If a team is deleted or a user deactivated, matches remain with phantom participant IDs.

**Impact**: `signals.py` → `handle_match_state_change()` attempts to resolve participant recipients for notifications. If the participant doesn't exist, the signal fails silently — no notification sent, no error logged. Bracket progression can advance a ghost participant.

**Fix**: Add a `CheckConstraint` or service-level validation that confirms participant existence before match state transitions. Consider replacing with actual FK fields (with `SET_NULL` on delete) or maintaining a `MatchParticipant` junction table.

---

#### 3.3 Hub Polling Overwhelms 512 MB Server

**Location**: `static/tournaments/js/hub-engine.js`
**Problem**: Each hub user generates:
- State poll: every 20s (45s when WS healthy)
- Announcements poll: every 15s (60s when WS healthy)
- Per-tab data fetches on switch (matches, standings, bracket, participants, schedule, prizes, resources, support tickets)
- Fallback sync timer if WS drops: every 20s

**Math**: 50 concurrent hub users × 4 requests/min = **200 req/min**. Each hub state response is ~15 KB. At 50 users: **3 MB/min** of JSON traffic, plus Django view processing overhead.

**Impact**: On a 512 MB server running Django + Daphne + Celery + Redis, this saturates the worker pool. Response times degrade. WebSocket connections drop under load, triggering MORE polling.

**Fix**: 
1. Merge state + announcements into a single unified poll endpoint with ETag support.
2. Use WebSocket as primary delivery (already partially implemented in S27) — push state diffs, not full snapshots.
3. Add `Cache-Control: max-age=10` headers on standings/bracket/prizes endpoints (they change infrequently).
4. Implement conditional GETs (304 Not Modified) for all hub API endpoints.

---

#### 3.4 CSRF Protection Gaps on State-Changing Endpoints

**Location**: `apps/tournaments/views/match_room.py`, `apps/tournaments/views/hub.py`
**Problem**: Several AJAX POST endpoints rely on a multi-source CSRF token fallback cascade:

```javascript
// match-room.js — CSRF resolution
token = payload.csrf_token || document.querySelector('[name=csrfmiddlewaretoken]')?.value
     || document.querySelector('meta[name=csrf-token]')?.content
     || getCookie('csrftoken');
```

If the match room page has been open for hours (common during tournament day), the CSRF token in `payload.csrf_token` (embedded at render time) may be stale. The cookie-based fallback works but is less secure against CSRF attacks where the attacker can read cookies.

**Additional Gap**: `MatchRoomWorkflowView` POST (lobby credential broadcast, match start) uses `@login_required` but does not explicitly add `@csrf_protect`. It relies on Django's `CsrfViewMiddleware` being in `MIDDLEWARE`. If middleware ordering changes or is conditionally disabled (e.g., for API views), CSRF protection silently disappears.

**Fix**:
1. Explicitly decorate all state-changing views with `@csrf_protect`.
2. Refresh CSRF token via a lightweight endpoint or WebSocket message on heartbeat.
3. Add `SameSite=Lax` to session cookies (if not already set) to mitigate cross-origin POST attacks.

---

#### 3.5 Payment Verification Race Condition

**Location**: `apps/tournaments/models/payment_verification.py`, `apps/tournament_ops/services/payment_orchestration_service.py`
**Problem**: `mark_verified()` and `mark_rejected()` lack idempotency enforcement. The `idempotency_key` field exists but is never checked during status transitions. Two staff members clicking "Verify" simultaneously create two notification dispatches and potentially double-credit the participant's registration.

**Impact**: Financial integrity compromised. Participant could receive duplicate "Payment Verified" notifications. Registration status could be toggled twice (PENDING → CONFIRMED → CONFIRMED again triggers duplicate signal).

**Fix**: Add `select_for_update()` in the payment orchestration service. Check `idempotency_key` before processing. Use `F()` expressions or `update()` with a WHERE clause to ensure atomic transitions.

---

#### 3.6 Dispute Evidence File Upload — No Type Validation

**Location**: `apps/tournaments/models/dispute.py` — `evidence_file` field, `apps/tournaments/views/result_submission.py`
**Problem**: The `evidence_file` upload path is `/disputes/evidence/%Y/%m/` with user-controlled filename. No `FileExtensionValidator` restricts file types. No MIME type validation.

**Impact**: Attackers could upload:
- SVG files with embedded JavaScript (Stored XSS)
- HTML files that execute in the browser context
- `.exe` or `.bat` files that other staff might download

**Fix**: Add `FileExtensionValidator(['jpg', 'jpeg', 'png', 'mp4', 'webm'])`. Validate MIME type server-side with `python-magic`. Rename uploaded files to UUID-based names. Serve from a separate domain/CDN with `Content-Disposition: attachment`.

---

### 🟠 SEVERITY: HIGH (Fix Before Launch)

#### 3.7 WebSocket Broadcast Triplication

**Location**: `apps/tournaments/consumers.py` — `broadcast_match_update()` signal handler
**Problem**: When a match completes, the `post_save` signal broadcasts to three separate channel groups:
1. `match_{id}` (match-specific updates)
2. `tournament_bracket_{slug}` (legacy bracket consumer)
3. `tournament_{id}` (hub updates)

Each `group_send()` is a Redis PUBLISH operation. With 30 concurrent matches completing in rapid succession (group stage), this creates **90 Redis PUBLISHes** in a burst.

**Fix**: Consolidate to a single `tournament_{id}` broadcast. Match room JS and bracket JS should subscribe to the tournament-level group and filter by match ID client-side. This reduces Redis operations by 66%.

---

#### 3.8 Result Submission Lacks Idempotency

**Location**: `apps/tournament_ops/services/result_submission_service.py` — `submit_result()`
**Problem**: No deduplication check. Submitting the same result twice creates two `MatchResultSubmission` records with different PKs. The auto-confirm task runs on both, potentially racing.

**Impact**: Two opponents could both submit "we won" — both records enter `PENDING` state — both auto-confirm after 24h timeout — conflicting winners determined.

**Fix**: Use `get_or_create()` with a composite key `(match_id, submitted_by, source)`. Return existing submission if duplicate detected. Add a database `UNIQUE` constraint on `(match, submitted_by)`.

---

#### 3.9 N+1 Query in Bracket View

**Location**: `apps/tournaments/views/live.py` — `TournamentBracketView`
**Problem**: Team enrichment for bracket visualization queries teams sequentially per match. For a 64-team bracket (63 matches), this creates 63+ database queries.

**Fix**: Collect all participant IDs upfront, batch query teams with `Team.objects.filter(id__in=all_pids)`, build a lookup dict, then iterate matches with O(1) dict lookups. This reduces queries from O(n) to O(1).

---

#### 3.10 Group Standing Recalculation is O(n²)

**Location**: `apps/tournaments/signals.py` — `sync_match_completion_progression()`
**Problem**: Every match completion triggers `GroupStageService.calculate_group_standings(stage.id)`. This recalculates ALL groups in the stage, not just the affected group. For a 64-team tournament with 8 groups, every match result recomputes all 8 groups.

**Fix**: Accept `group_id` parameter. Only recalculate the specific group containing the two match participants. This reduces computation by 7/8 (87.5%) for an 8-group stage.

---

#### 3.11 Presence Registry Memory Leak

**Location**: `apps/tournaments/realtime/match_consumer.py`
**Problem**: The presence registry is an in-memory dict on the consumer class. Entries are cleaned when the 45s stale timeout fires. But if the Daphne process restarts (common on 512 MB under memory pressure), presence state is lost entirely — all users appear offline until they send another heartbeat.

**Fix**: Move presence state to Redis with TTL keys. `SETEX presence:match:{id}:user:{uid} 50 {json_data}`. This survives process restarts and is inspectable for debugging.

---

#### 3.12 Match Room JS Monolith (3,000+ Lines)

**Location**: `static/tournaments/js/match-room.js`
**Problem**: Single IIFE containing all match room logic for all game types. No code splitting. Every WebSocket message triggers `renderAll()` which re-renders header, rules, phase tracker, engine, presence — even if only chat changed.

**Impact on 512 MB Constraint**: Gzipped ~25-30 KB transfer, but parse time is ~50-100ms on low-end mobile. More critically, the full `renderAll()` triggers 10-20 reflows/repaints per minute from presence and chat updates.

**Fix**:
1. Extract game-specific modules (Valorant pipeline, eFootball pipeline) into separate files loaded conditionally.
2. Implement selective re-render: `renderChat()`, `renderPresence()`, `renderPhase()` as independent functions.
3. Use `requestAnimationFrame()` to batch DOM updates.

---

### 🟡 SEVERITY: MEDIUM (Address in Sprint Backlog)

#### 3.13 Prize Transaction Not Atomic

**Location**: `apps/tournaments/models/prize.py`, tournament_ops services
**Problem**: `PrizeTransaction` and `DeltaCrownTransaction` (economy app) are created in separate ORM calls without wrapping in `transaction.atomic()`. If the economy service fails after the prize record is created, the participant sees "Prize Distributed" but never receives the funds.

---

#### 3.14 No Anti-Cheat Integration Hooks

**Problem**: The platform has no mechanism to flag suspicious results, integrate with third-party anti-cheat services, or automatically detect statistically improbable outcomes (e.g., a Bronze-tier team beating a Diamond-tier team 13-0 in every round).

---

#### 3.15 Tournament Detail Page HTMX Auto-Refresh Storm

**Location**: `templates/spectator/tournament_detail.html`
**Problem**: Every spectator page fires HTMX requests every 15s (matches) and 10s (leaderboard). During a live tournament final with 500 spectators: **500 × 6/min = 3,000 requests/min** for the spectator page alone.

**Fix**: Use the existing `TournamentConsumer` WebSocket to push updates. Only HTMX-refresh on WS event, not on a timer.

---

#### 3.16 TOC String Concatenation XSS Vector

**Location**: `static/tournaments/toc/js/toc-overview.js`, `toc-settings.js`
**Problem**: HTML is built via string concatenation. An `esc()` helper exists but is used inconsistently. If a tournament name contains `<script>alert(1)</script>` and the organizer is also a participant, the TOC overview could execute it.

**Fix**: Enforce `esc()` on ALL user-sourced data in template literals. Better: adopt a micro-template library (e.g., `lit-html`) or build DOM programmatically with `textContent`.

---

#### 3.17 Soft Delete Inconsistency

**Problem**: Some models use `SoftDeleteModel` (Tournament, Registration, Match). Others use raw `is_deleted` booleans without a manager filter (Group). Others use neither (BracketNode, Payment). Deleted data can leak into queries.

---

#### 3.18 Orphaned JavaScript Timers

**Location**: `static/tournaments/js/match-room.js` — `presenceTimer`, `fallbackSyncTimer`, `noShowTimer`
**Problem**: Timers are not cleared on `beforeunload` or `pagehide`. If the user navigates away without closing the tab, timers keep firing, making background network requests.

---

## 4. Game-Adaptation Strategy

### Current State

The system has a **strong foundation** for game-specific intelligence via the `apps/games/` configuration models:

| Model | Purpose | Games Configured |
|-------|---------|-----------------|
| `Game` | Identity, branding, category, platforms | 11 games |
| `GameRosterConfig` | Team size, subs, coaches, roles | Per-game |
| `GameTournamentConfig` | Match formats, scoring type, tiebreakers, brackets | Per-game |
| `GameScoringRule` | Scoring algorithm (win_loss, points, placement, time) | Per-game |
| `GameMatchResultSchema` | Result field definitions and validation | Per-game |
| `GamePlayerIdentityConfig` | Player identity fields (Riot ID, Steam ID, etc.) | Per-game |
| `GameRole` | In-game roles (Duelist, Controller, etc.) | Per-game |

**However**, the match room only implements **two concrete pipelines**:
1. **Valorant Pipeline**: Coin Toss → Map Veto → Lobby Setup → Live → Results
2. **eFootball Pipeline**: Direct Ready Check → Lobby Setup → Live → Results

**All other games** (CS2, R6, Dota 2, PUBG Mobile, Mobile Legends, Free Fire, CoD Mobile, Rocket League) default to the Valorant pipeline. This is incorrect — a BR game like PUBG Mobile should not have a map veto flow designed for 5v5 tactical shooters.

### Required Game Archetypes

We need **5 match room pipeline archetypes**, each configurable per game:

#### Archetype 1: Tactical FPS (Valorant, CS2, R6 Siege)
```
Coin Toss → Map Veto (ban/pick sequence) → Side Selection → Lobby Setup → Live → Results
```
- **Scoring**: Round-based (first to 13/16, overtime rules)
- **Veto**: Configurable ban/pick sequences per map pool size
- **Server Selection**: Regional preference matching
- **Stats**: Kills, Deaths, Assists, Plants, Defuses, Clutches, ADR
- **Series**: BO1, BO3, BO5 with per-map scores
- **Special**: Tactical timeout tracking, agent/operator bans

#### Archetype 2: MOBA (Dota 2, Mobile Legends)
```
Coin Toss → Hero Draft (ban/pick alternating) → Side Selection → Lobby Setup → Live → Results
```
- **Scoring**: Win/Loss per game
- **Draft**: Alternating ban/pick phases (e.g., 2B-3P-2B-2P per team)
- **Stats**: Kills, Deaths, Assists, GPM, XPM, Hero Damage, Tower Damage
- **Series**: BO1, BO3, BO5 with per-game hero drafts
- **Special**: First pick/second pick advantage tracking

#### Archetype 3: Battle Royale (PUBG Mobile, Free Fire, CoD Mobile)
```
Lobby Distribution → Server Assignment → Live → Results (Placement + Kills)
```
- **Scoring**: Placement-based points matrix + kill bonuses
- **No Veto**: BR games don't have map vetoes (organizer pre-selects map)
- **Multi-team**: 16-100 teams per match (not 1v1)
- **Stats**: Placement, Kills, Damage, Survival Time
- **Series**: Multi-round cumulative scoring
- **Special**: Custom room code distribution to many teams simultaneously

#### Archetype 4: Sports (EA FC, eFootball, Rocket League)
```
Direct Ready Check → Lobby Setup → Live → Results (Goals/Score)
```
- **Scoring**: Goal/score differential
- **No Draft/Veto**: Simplified flow
- **Stats**: Goals, Assists, Possession, Saves (Rocket League), Shots
- **Series**: BO1 (legs), BO3 with aggregate scoring option
- **Special**: Extra time and penalty shootout support

#### Archetype 5: 1v1/Duel (Fighting Games, CCG, Future Titles)
```
Direct Ready Check → Platform Match → Live → Results
```
- **Scoring**: Win/Loss or rounds won
- **Minimal Setup**: Players match directly on platform
- **Stats**: Game-specific (rounds won, damage dealt, cards played)
- **Series**: BO3, BO5, BO7 (FGC standard)
- **Special**: Stage/character bans possible

### Database Refactoring for Game Intelligence

#### New Model: `GameMatchPipeline`

```python
class GameMatchPipeline(models.Model):
    """Defines the match room phase sequence for a game archetype."""
    game = models.OneToOneField('games.Game', on_delete=models.CASCADE, related_name='match_pipeline')
    archetype = models.CharField(max_length=20, choices=ARCHETYPE_CHOICES)
    phases = models.JSONField(help_text="Ordered list of phase configs")
    # Example phases:
    # [
    #   {"key": "coin_toss", "required": true, "config": {}},
    #   {"key": "veto", "required": true, "config": {"type": "ban_pick", "sequence": "BBPBPBP"}},
    #   {"key": "lobby_setup", "required": true, "config": {"credential_schema": [...]}},
    #   {"key": "live", "required": true, "config": {"allow_pause": false}},
    #   {"key": "results", "required": true, "config": {"fields": ["score", "screenshot"]}}
    # ]
    credential_schema = models.JSONField(help_text="Lobby credential fields")
    result_entry_schema = models.JSONField(help_text="Result submission form fields")
```

#### New Model: `VetoConfiguration`

```python
class VetoConfiguration(models.Model):
    """Game-specific veto/draft rules."""
    game = models.ForeignKey('games.Game', on_delete=models.CASCADE)
    veto_type = models.CharField(choices=[('map', 'Map Veto'), ('hero', 'Hero Draft'), ('stage', 'Stage Ban')])
    pool_source = models.CharField(choices=[('map_pool', 'MapPoolEntry'), ('hero_pool', 'GameRole')])
    sequence = models.JSONField()  # e.g., ["ban_a", "ban_b", "pick_a", "pick_b", "ban_a", "ban_b", "decider"]
    time_per_action_seconds = models.PositiveIntegerField(default=30)
```

#### Frontend: Dynamic Phase Loader

```javascript
// Instead of hardcoded game checks:
// OLD: if (game === 'valorant') { showVeto() } else if (game === 'efootball') { showDirect() }
// NEW:
const pipeline = state.room.game.match_pipeline;
for (const phase of pipeline.phases) {
    const PhaseModule = await import(`./phases/${phase.key}.js`);
    PhaseModule.render(phase.config, state);
}
```

---

## 5. Codebase Cleanup List

### 🗑️ Models to Remove

| Model | Location | Reason |
|-------|----------|--------|
| `Dispute` | `apps/tournaments/models/` | Replaced by `DisputeRecord` (Phase 6). Still imported in admin. |
| `TemplateRating` | `apps/tournaments/models/` | Deprecated marketplace feature. No references in active views. |
| `RatingHelpful` | `apps/tournaments/models/` | Sub-model of deprecated TemplateRating. |
| `TournamentStaff` (legacy) | `apps/tournaments/models/` | Replaced by `TournamentStaffAssignment` (Phase 7). |
| `LobbyAnnouncement` | `apps/tournaments/models/` | Replaced by `TournamentAnnouncement`. |
| `Payment` (legacy) | `apps/tournaments/models/` | Replaced by `PaymentVerification`. Check for lingering FK references. |

### 🗑️ Views to Remove

| View | Location | Reason |
|------|----------|--------|
| `TournamentRegistrationView` | `apps/tournaments/views/registration.py` | Deprecated 5-step wizard. Replaced by SmartRegistration (Phase 5). Already commented out in urls.py. |
| `RegistrationDashboardView` | `apps/tournaments/views/dynamic_registration.py` | Legacy form builder. Superseded. |

### 🗑️ Templates to Archive

| Path | Reason |
|------|--------|
| `templates/tournaments/registration/wizard_*.html` | Legacy wizard templates (if they exist). |
| Any template referencing `LobbyAnnouncement` | Legacy model. |

### 🗑️ JS/CSS to Consolidate

| File | Issue | Action |
|------|-------|--------|
| `static/tournaments/js/match-room.js` | 3,000+ line monolith | Split into `match-room-core.js` + per-archetype modules |
| `static/tournaments/public/js/lobby-updates.js` | 50-line HTMX polling shim | Merge into hub-engine.js or replace with WS |

### 🗑️ Dead Code Patterns

| Pattern | Location | Action |
|---------|----------|--------|
| `TODO: Phase X` comments | Throughout tournament_ops services | Remove or convert to GitHub Issues |
| `poll_pending_steam_matches()` | `apps/tournament_ops/tasks/match_polling.py` | Stub function. Remove or implement. |
| `fetch_steam_match_result()` | Same file | Stub. Remove or implement. |
| Triple WebSocket broadcast | `apps/tournaments/consumers.py` | Consolidate to single group |
| Legacy `consumers.py` TournamentBracketConsumer | `apps/tournaments/consumers.py` | Replace with TournamentConsumer in `realtime/` |

### 📦 Migration Candidates

These models/features have grown beyond their app boundaries and should be extracted:

| Feature | Current Location | Recommended Location |
|---------|-----------------|---------------------|
| Match Room Pipeline | `tournaments/views/match_room.py` + `consumers/` | Dedicated `apps/match_engine/` app |
| Dispute Resolution | `tournaments/models/dispute.py` + `tournament_ops/services/dispute_service.py` | Dedicated `apps/disputes/` app |
| Certificate Generation | `tournaments/models/certificate.py` | Move to `apps/rewards/` alongside trophies |
| Bracket Generation | `tournament_ops/services/bracket_engine_service.py` + generators | Dedicated `apps/brackets/` app |

---

## 6. The Refactor Roadmap

### Phase 0: Foundation Hardening (Week 1-2)

**Goal**: Fix critical blockers without changing architecture. Zero new features.

| # | Task | Priority | Effort | Files Affected |
|---|------|----------|--------|----------------|
| 0.1 | **Implement Tournament State Machine** — Add `ALLOWED_TRANSITIONS` dict in TournamentLifecycleService. Override `Tournament.save()` to validate transitions. Add `CheckConstraint` for valid states. | 🔴 Critical | 2 days | `models/tournament.py`, `services/tournament_lifecycle_service.py`, `signals.py` |
| 0.2 | **Fix Match Participant Validation** — Add service-level check in `MatchService.create_match()` and `update_match_state()` that confirms participant IDs reference existing registrations. | 🔴 Critical | 1 day | `tournament_ops/services/match_service.py`, `tournament_ops/adapters/match_adapter.py` |
| 0.3 | **Add `@csrf_protect` to All State-Changing Views** — Explicit decorator on MatchRoomWorkflowView POST, HubCheckInAPIView POST, HubMatchRescheduleProposalAPIView POST, HubPrizeClaimAPIView POST. | 🔴 Critical | 0.5 day | `views/match_room.py`, `views/hub.py` |
| 0.4 | **Add FileExtensionValidator to Evidence Uploads** — Restrict to `['jpg', 'jpeg', 'png', 'mp4', 'webm']`. Add MIME validation. Rename uploaded files to UUIDs. | 🔴 Critical | 0.5 day | `models/dispute.py`, `views/result_submission.py` |
| 0.5 | **Payment Verification Idempotency** — Wrap `mark_verified()` and `mark_rejected()` in `select_for_update()`. Check status hasn't already transitioned. | 🔴 Critical | 1 day | `models/payment_verification.py`, `tournament_ops/services/payment_orchestration_service.py` |
| 0.6 | **Result Submission Deduplication** — Add `unique_together = ('match', 'submitted_by')` constraint. Use `get_or_create()` in service. | 🟠 High | 0.5 day | `models/match_result_submission.py`, `tournament_ops/services/result_submission_service.py` |
| 0.7 | **Move Presence to Redis** — Replace in-memory presence dict with Redis SETEX keys (50s TTL). Rebuild snapshot from `KEYS presence:match:{id}:*`. | 🟠 High | 1 day | `realtime/match_consumer.py` |
| 0.8 | **Clean Up Dead Models** — Remove `Dispute` (legacy), `TemplateRating`, `RatingHelpful`, `LobbyAnnouncement`. Create migration. | 🟡 Med | 1 day | `models/__init__.py`, `admin.py`, migrations |

---

### Phase 1: Memory Optimization (Week 3-4)

**Goal**: Bring runtime footprint under 512 MB with 100 concurrent users.

| # | Task | Priority | Effort | Impact |
|---|------|----------|--------|--------|
| 1.1 | **Consolidate Hub Polling** — Merge `/hub/api/state/` and `/hub/api/announcements/` into single endpoint. Add `ETag` and `Cache-Control: max-age=10` headers. | 🔴 Critical | 2 days | -50% hub HTTP traffic |
| 1.2 | **WebSocket-First Hub Updates** — Complete S27 WebSocket integration. Push state diffs (JSON Patch) instead of full snapshots. Reduce poll to 60s safety-net. | 🔴 Critical | 3 days | -80% polling load |
| 1.3 | **Consolidate WebSocket Broadcasts** — Replace triple broadcast (match + bracket + tournament groups) with single `tournament_{id}` group. Client-side filters by match ID. | 🟠 High | 1 day | -66% Redis PUBLISHes |
| 1.4 | **Spectator View: Replace HTMX Timer with WS** — Use TournamentConsumer to push match updates to spectators. Remove 15s/10s HTMX auto-refresh. | 🟠 High | 1 day | Eliminates 6 req/min/spectator |
| 1.5 | **Lazy Load Hub Tabs** — Render tab shells (empty containers) in initial HTML. Fetch tab content on first activation. | 🟠 High | 2 days | -40% initial HTML payload |
| 1.6 | **Add Response Caching Headers** — `Cache-Control: max-age=30` on `/hub/api/standings/`, `/hub/api/bracket/`, `/hub/api/prizes/`. | 🟡 Med | 0.5 day | Reduces repeated fetches |
| 1.7 | **Reduce Redis Channel Capacity** — Already at 500 (down from 1500). Monitor with Grafana. Consider 300 if stable. | 🟡 Med | 0.5 day | ~5 MB RAM savings |
| 1.8 | **Celery Worker Tuning** — Confirm `CELERY_WORKER_MAX_TASKS_PER_CHILD=50`. Add `--max-memory-per-child=150000` (150 MB). | 🟡 Med | 0.5 day | Prevents worker memory bloat |

---

### Phase 2: Match Room Refactor (Week 5-7)

**Goal**: Split match-room.js monolith. Implement game archetype pipelines. Selective re-rendering.

| # | Task | Priority | Effort | Impact |
|---|------|----------|--------|--------|
| 2.1 | **Create `GameMatchPipeline` Model** — DB-driven phase sequence per game. Admin UI for organizers to customize pipelines. | 🔴 Critical | 2 days | Enables dynamic game adaptation |
| 2.2 | **Split match-room.js** — Extract into: `match-room-core.js` (state, WS, render orchestrator), `phase-coin-toss.js`, `phase-veto.js`, `phase-draft.js`, `phase-direct.js`, `phase-lobby.js`, `phase-live.js`, `phase-results.js`. Dynamic import based on pipeline. | 🔴 Critical | 4 days | Per-game code loading, smaller bundles |
| 2.3 | **Implement Selective Re-Render** — Replace monolithic `renderAll()` with targeted: `renderChat()` on `match_chat`, `renderPresence()` on `match_presence`, `renderPhase()` on `match_room_event`. Use `requestAnimationFrame()` batching. | 🟠 High | 2 days | -70% unnecessary DOM updates |
| 2.4 | **Battle Royale Archetype** — New `phase-br-lobby.js` for multi-team lobby distribution (16-100 teams). Custom result entry with placement + kills matrix. New `BRScoringMatrix` integration. | 🟠 High | 3 days | Supports PUBG, Free Fire, CoD Mobile |
| 2.5 | **MOBA Draft Archetype** — New `phase-draft.js` for hero ban/pick sequences. Configurable draft order (2B-3P-2B-2P). Timer per action. | 🟡 Med | 2 days | Supports Dota 2, Mobile Legends |
| 2.6 | **Clean Up Timer Lifecycle** — Add `beforeunload` and `pagehide` listeners to clear all intervals. Implement `AbortController` for in-flight fetches. | 🟡 Med | 0.5 day | Eliminates ghost background requests |
| 2.7 | **WebSocket Close Code Differentiation** — Show specific messages per close code: 4001 → "Session expired", 4003 → "Origin blocked", 4004 → "Match not found", 1006 → "Connection lost, reconnecting..." | 🟡 Med | 0.5 day | Better UX on failures |

---

### Phase 3: Data Integrity & Security (Week 8-9)

**Goal**: Harden all data paths. Atomic transactions. Anti-abuse measures.

| # | Task | Priority | Effort | Impact |
|---|------|----------|--------|--------|
| 3.1 | **Atomic Prize Distribution** — Wrap `PrizeTransaction` + `DeltaCrownTransaction` in `transaction.atomic()`. Rollback on any failure. | 🔴 Critical | 1 day | Prevents partial payouts |
| 3.2 | **Chat Rate Limiting** — Max 1 message per 2s per user in MatchConsumer. Return `error: rate_limited` on excess. | 🟠 High | 0.5 day | Prevents chat spam |
| 3.3 | **Lobby Credential Schema Validation** — Define JSON Schema per game for `lobby_info`. Validate on MatchRoomWorkflowView POST. Reject malformed data with 400. | 🟠 High | 1 day | Prevents injection |
| 3.4 | **Hub `view_as` Parameter Hardening** — Restrict `view_as=participant` to users who are BOTH staff AND registered participants. Log all mode switches to AuditLog. | 🟠 High | 0.5 day | Prevents privilege escalation |
| 3.5 | **Guest Invite Token Rate Limiting** — Add `@ratelimit(key='ip', rate='10/h')` to `generate_invite_link` and `conversion_page`. | 🟡 Med | 0.5 day | Prevents brute-force |
| 3.6 | **TOC XSS Audit** — Ensure all user-sourced data in TOC JS modules passes through `esc()`. Add CSP `script-src` without `unsafe-inline` (requires nonce-based approach). | 🟡 Med | 2 days | Eliminates stored XSS |
| 3.7 | **Discord Webhook Encryption** — Encrypt `discord_webhook_url` at rest using `Fernet` (django-cryptography). Decrypt only during webhook dispatch. | 🟡 Med | 1 day | Protects webhook on DB breach |

---

### Phase 4: Performance & Scalability (Week 10-12)

**Goal**: Handle 500+ concurrent users on 512 MB. Sub-200ms p99 response times.

| # | Task | Priority | Effort | Impact |
|---|------|----------|--------|--------|
| 4.1 | **Fix N+1 in Bracket View** — Batch-query teams with `Team.objects.filter(id__in=all_pids)`. Build dict. O(1) lookups per match. | 🔴 Critical | 0.5 day | 63 queries → 1 query (64-team bracket) |
| 4.2 | **Incremental Group Standing Updates** — Accept `group_id` parameter in `calculate_group_standings()`. Only recompute affected group on match completion. | 🟠 High | 1 day | 87.5% reduction in computation |
| 4.3 | **Hub API Endpoint `select_related` Audit** — Add `select_related('tournament', 'tournament__game')` to all hub views. Add `prefetch_related('registrations')` where needed. | 🟠 High | 1 day | -50% query count |
| 4.4 | **Bracket Structure Caching** — Cache `Bracket.get_round_name()` and round structure in Redis (5 min TTL). Invalidate on bracket update. | 🟡 Med | 0.5 day | Eliminates JSON parsing per render |
| 4.5 | **TOC Virtual Scrolling** — Implement virtual scroll for match list in `toc-matches.js` when >100 matches. Only render visible rows + 10 buffer. | 🟡 Med | 2 days | Smooth UI with 1000+ matches |
| 4.6 | **CSS Performance** — Replace `backdrop-filter: blur()` on scroll containers with static blurred background images. Reduce to max 3 concurrent backdrop-filters. | 🟡 Med | 1 day | Eliminates 60fps drops |
| 4.7 | **Add `Cache-Control` to Static Assets** — Ensure `whitenoise` or CDN serves JS/CSS with `Cache-Control: public, max-age=31536000, immutable` and content-hashed filenames. | 🟡 Med | 0.5 day | Zero re-downloads on revisit |

---

### Phase 5: Game Intelligence & Feature Parity (Week 13-16)

**Goal**: Match Faceit/Battlefy on game-specific features. Full archetype coverage.

| # | Task | Priority | Effort | Impact |
|---|------|----------|--------|--------|
| 5.1 | **Implement All 5 Archetypes** — Tactical FPS, MOBA, Battle Royale, Sports, 1v1. Each with pipeline, credential schema, result entry, stats tracking. | 🔴 Critical | 2 weeks | Full game-specific intelligence |
| 5.2 | **VetoConfiguration Model** — DB-driven veto/draft rules per game. Configurable sequences, timers, pool sources. | 🟠 High | 2 days | Organizers customize vetoes per tournament |
| 5.3 | **Per-Map/Per-Game Stats** — Expand `MatchPlayerStat` and `MatchMapPlayerStat` with game-specific stat schemas from `GameMatchResultSchema`. | 🟠 High | 3 days | Rich post-match analytics |
| 5.4 | **Automated Result Ingestion** — Complete Riot API integration (+finish Steam/Valve stub). Add Epic Games (Fortnite), Supercell (Brawl Stars) adapters. | 🟡 Med | 2 weeks | Reduces manual result entry |
| 5.5 | **Anti-Cheat Hooks** — Add `MatchIntegrityCheck` model. Post-match: compare submitted score vs API-ingested score. Flag discrepancies. Alert staff in TOC. | 🟡 Med | 3 days | Automated fraud detection |
| 5.6 | **Spectator Dashboard** — Rich spectator view with live bracket updates, match-by-match results, player stats, MVP tracking. Replace HTMX polling with WS-only. | 🟡 Med | 1 week | Engaging viewer experience |

---

### Phase 6: Architecture Cleanup (Week 17-18)

**Goal**: Extract domains into dedicated apps. Remove all dead code. Standardize patterns.

| # | Task | Priority | Effort | Impact |
|---|------|----------|--------|--------|
| 6.1 | **Extract `apps/match_engine/`** — Move MatchConsumer, match_room views, match-room JS, match pipeline models into dedicated app. | 🟠 High | 3 days | Clean separation of concerns |
| 6.2 | **Extract `apps/brackets/`** — Move BracketEngineService, generators, Bracket/BracketNode models. | 🟡 Med | 2 days | Reusable bracket engine |
| 6.3 | **Standardize Soft Deletes** — Apply `SoftDeleteModel` to all historical models (Group, BracketNode, Payment). Add custom manager that filters `is_deleted=False` by default. | 🟡 Med | 1 day | No more deleted data leaks |
| 6.4 | **Remove Legacy Consumers** — Delete `apps/tournaments/consumers.py` (legacy TournamentBracketConsumer). All WS through `realtime/` package. | 🟡 Med | 0.5 day | Single source of truth for WS |
| 6.5 | **Consolidate State Tracking Signals** — Extract generic `track_status_change()` mixin used by payment, match, and tournament signals. | 🟡 Med | 1 day | DRY signal pattern |
| 6.6 | **Remove Deprecated Views** — Delete `TournamentRegistrationView`, `RegistrationDashboardView`, and associated URL patterns. | 🟡 Med | 0.5 day | Less dead code |
| 6.7 | **Type Hints & mypy** — Add type annotations to all service layer functions. Configure mypy in CI. | 🟡 Low | 3 days | Catch type errors early |

---

### Summary Timeline

```
Week  1-2:  Phase 0 — Foundation Hardening (State machine, CSRF, file validation)
Week  3-4:  Phase 1 — Memory Optimization (Polling consolidation, WS-first, lazy tabs)
Week  5-7:  Phase 2 — Match Room Refactor (Code splitting, archetypes, selective render)
Week  8-9:  Phase 3 — Data Integrity & Security (Atomic txns, rate limits, XSS)
Week 10-12: Phase 4 — Performance & Scalability (N+1 fixes, caching, virtual scroll)
Week 13-16: Phase 5 — Game Intelligence (5 archetypes, veto config, API ingestion)
Week 17-18: Phase 6 — Architecture Cleanup (App extraction, dead code, soft deletes)
```

### Definition of Done (Enterprise Standard)

Each phase is complete when:
- [ ] All listed tasks have passing unit tests
- [ ] Integration tests cover the critical path (registration → match → result → standings)
- [ ] No new `TODO` comments introduced
- [ ] Memory profiling confirms ≤512 MB under 100 concurrent users
- [ ] WebSocket load test: 200 concurrent connections, <50ms p95 broadcast latency
- [ ] API load test: 100 req/s, <200ms p99 response time
- [ ] Zero OWASP Top 10 violations in affected code
- [ ] Grafana dashboard confirms no Redis memory spikes or Celery queue backlog

---

*End of Enterprise Lifecycle Audit — DeltaCrown Esports Platform*
