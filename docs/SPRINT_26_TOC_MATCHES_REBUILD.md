# Sprint 26: TOC Matches Tab — Full Rebuild & System Hardening

> **Date**: March 3, 2026  
> **Scope**: Fix all 500 errors, rebuild Matches UI for production-grade admin experience, harden backend APIs, bridge the tournament lifecycle from draw → match operations.  
> **Prerequisite**: Sprint 25 committed (`8f6db80b`) — Overview + Matches HTML/JS shell in place.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Audit](#2-current-state-audit)
3. [Backend Bugs Fixed (Pre-Sprint)](#3-backend-bugs-fixed-pre-sprint)
4. [Architecture Overview](#4-architecture-overview)
5. [Sprint 26 Implementation Plan](#5-sprint-26-implementation-plan)
6. [Gap Analysis — Full Platform Gaps](#6-gap-analysis--full-platform-gaps)
7. [File Inventory](#7-file-inventory)
8. [Risk Register](#8-risk-register)

---

## 1. Executive Summary

### Problem Statement

The TOC Matches tab (`/toc/<slug>/#matches`) is currently non-functional:

- **500 errors** on `/api/toc/<slug>/stats/` and `/api/toc/<slug>/audit-log/` crashed the Overview tab's async side-channels, spamming the console on every 30s poll.
- **Match list is empty** because the tournament (`uradhura-ucl-s1`) has 8 finalized groups from a draw but **0 matches created** — match generation hasn't been triggered yet.
- **UI is skeletal** — Sprint 25 shipped the HTML structure (master-detail layout, filter bar, tabs) but with tiny fonts (`text-[8px]`, `text-[9px]`, `text-[10px]`) and missing content since no matches exist.
- **`group_label` is absent** from the match serializer — the frontend expects it for group pill filters but the API never returns it.
- **No lobby room integration** — matches don't link to match rooms, no lobby codes, no check-in status visible.

### What Exists (and is strong)

| System | Status | Details |
|--------|--------|---------|
| **115 TOC API endpoints** | ✅ All wired | 11 sprints of backend across overview, lifecycle, participants, payments, brackets, matches, disputes, settings, announcements, stats, RBAC, audit |
| **Match Operations APIs** | ✅ All wired | mark-live, pause, resume, force-complete, score, verify, reset, reschedule, forfeit, add-note, media, detail |
| **Tournament Hub (participant)** | ✅ Complete SPA | 11 tabs, 13 API endpoints, game theming, check-in, squad management |
| **Match Room (participant)** | ✅ Complete | Phase-aware lobby with codes, per-match check-in, result submission |
| **WebSocket Infrastructure** | ✅ Consumers ready | `TournamentConsumer` + `MatchConsumer` with JWT auth, heartbeat, role-based access |
| **Draw System** | ✅ Complete | 8 groups drawn and finalized for `uradhura-ucl-s1` |

### What's Broken/Missing

| Issue | Impact | Fix Priority |
|-------|--------|-------------|
| stats_service.py used wrong field names (`status` instead of `state`, `group_stage` FKs that don't exist) | 500 error on every page load | ✅ **FIXED** |
| audit_service.py used wrong field names (`tournament` instead of `tournament_id`, `created_at` instead of `timestamp`, `extra_data` instead of `metadata`) | 500 error on every poll | ✅ **FIXED** |
| `_serialize_match` doesn't return `group_label`, `bracket_id`, `lobby_info`, `check_in_deadline`, `participant_checked_in` | Frontend group filters + lobby features broken | **P0** |
| No match generation after draw | Match list permanently empty | **P0** |
| Tiny fonts (`text-[8px]`, `text-[9px]`) throughout matches tab | Unreadable UI | **P1** |
| No lobby integration in match detail (codes, check-in, map/server) | Admin can't manage match logistics | **P1** |
| No match room link from TOC | Admin can't observe matches | **P2** |
| `prompt()` used for dispute creation | Breaks immersive UI | **P2** |
| No XSS escaping on team names in match list | Security vulnerability | **P1** |
| No touch events for evidence pan/zoom | Mobile admin broken | **P3** |

---

## 2. Current State Audit

### 2.1 Match Model (from `apps/tournaments/models/match.py`)

**State machine** (9 states):
```
SCHEDULED → CHECK_IN → READY → LIVE → PENDING_RESULT → COMPLETED
                                  ↓                        ↑
                              DISPUTED ────────────────────┘
                              FORFEIT
                              CANCELLED
```

**Key fields**:
| Field | Type | Purpose |
|-------|------|---------|
| `tournament` | FK | Direct FK to Tournament |
| `bracket` | FK (nullable) | Links to Bracket (for elimination brackets) |
| `round_number` | PositiveInt | Round within stage |
| `match_number` | PositiveInt | Match sequence number |
| `participant1_id/name` | Int/Char | Side A identity |
| `participant2_id/name` | Int/Char | Side B identity |
| `participant1_score/2_score` | Int | Match score |
| `winner_id` / `loser_id` | Int | Result |
| `state` | Char | Current match state |
| `lobby_info` | JSONField | `{lobby_code, password, map, server, game_mode, notes[], paused, force_completed_by}` |
| `participant1_checked_in` / `participant2_checked_in` | Bool | Per-match check-in |
| `check_in_deadline` | DateTime | Per-match check-in window |
| `scheduled_time` / `started_at` / `completed_at` | DateTime | Lifecycle timestamps |
| `stream_url` | URL | Spectator stream |

### 2.2 Current `_serialize_match` Output

```python
{
    'id', 'round_number', 'match_number',
    'participant1_id', 'participant1_name',
    'participant2_id', 'participant2_name',
    'participant1_score', 'participant2_score',
    'state', 'winner_id', 'loser_id',
    'scheduled_time', 'started_at', 'completed_at',
    'stream_url', 'is_paused', 'notes_count'
}
```

**Missing**: `bracket_id`, `group_label`, `lobby_info`, `participant1_checked_in`, `participant2_checked_in`, `check_in_deadline`

### 2.3 Group System

- `GroupStage` → one per tournament, tracks `num_groups`, `group_size`, `format`, `state`
- `Group` → 8 groups for this tournament (A through H), all `is_finalized: True`
- `GroupStanding` → per-group per-user standings with full stats
- **No direct `Group` FK on Match** — the match-to-group relationship is through `lobby_info` or bracket logic, not a model field

### 2.4 Tournament State (`uradhura-ucl-s1`)

| Property | Value |
|----------|-------|
| Status | `registration_open` |
| Registrations | 32 |
| Groups | 8 (finalized) |
| Matches | **0** (need generation) |
| GroupStage state | `active` |

### 2.5 TOC Matches API Summary (12 endpoints)

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `matches/` | GET | List with `?state=&round=&search=` filters | Works, returns `{matches: []}` |
| `matches/<pk>/detail/` | GET | Full detail (submissions, media, disputes, notes, verification) | Works |
| `matches/<pk>/score/` | POST | Submit/override score | Works |
| `matches/<pk>/mark-live/` | POST | Transition to LIVE | Works |
| `matches/<pk>/pause/` | POST | Pause match | Works |
| `matches/<pk>/resume/` | POST | Resume match | Works |
| `matches/<pk>/force-complete/` | POST | Force completion | Works |
| `matches/<pk>/reschedule/` | POST | Reschedule with reason | Works |
| `matches/<pk>/forfeit/` | POST | Forfeit by participant | Works |
| `matches/<pk>/add-note/` | POST | Add admin note | Works |
| `matches/<pk>/media/` | GET/POST | Evidence media | Works |
| `matches/<pk>/verify/` | POST | Confirm/dispute/note result | Works |

### 2.6 Frontend Audit (`toc-matches.js` — 850 lines)

**Issues found**:
1. **XSS** — Team names, group labels not HTML-escaped in `renderMatchList()` and group pills
2. **`group_label` always undefined** — API doesn't return it, frontend tries to render it
3. **`prompt()` for disputes** — Native browser dialog instead of styled modal
4. **Accessibility** — Match cards are `<div onclick>` without `tabindex`, `role`, `aria-*`
5. **Silent API failures** — `selectMatch()` catch block only console.error, no toast
6. **Keyboard handler global** — Runs on every keydown even when on other tabs
7. **No touch events** — Evidence viewer pan/zoom is mouse-only
8. **Dead HTML** — `#score-drawer`, `#match-detail-drawer` containers never used
9. **Font sizes** — `text-[8px]` and `text-[9px]` below WCAG minimum for readability

### 2.7 Hub & Lobby System (Participant-Facing)

| URL | Purpose |
|-----|---------|
| `/tournaments/<slug>/hub/` | Participant SPA with 11 tabs (Overview, Match Lobby, Squad, Bracket, Standings, Schedule, Prizes, Resources, Participants, Rulebook, Support) |
| `/tournaments/<slug>/matches/<id>/room/` | Per-match room (lobby codes, check-in, result submission) |
| `/tournaments/<slug>/matches/<id>/submit-result/` | Result submission form |
| `/tournaments/<slug>/matches/<id>/report-dispute/` | Dispute report |

**Key finding**: The Hub uses HTTP polling (20s/45s intervals), not WebSockets, despite `TournamentConsumer` being fully implemented. The Match Room uses `setTimeout → location.reload()` every 30s.

---

## 3. Backend Bugs Fixed (Pre-Sprint)

### 3.1 `stats_service.py` — 3 bugs fixed

| Bug | Fix |
|-----|-----|
| `Q(group_stage__group__tournament=t)` — `group_stage` FK doesn't exist on Match | Changed to `Match.objects.filter(tournament=t)` |
| `status="completed"` etc. — field is `state` not `status` | Changed all references to `state` |
| `status="in_progress"` / `status="pending"` — wrong values | Changed to `state="live"` and `state__in=["scheduled", "check_in", "ready", "pending_result"]` |
| DisputeRecord has no `tournament` FK | Changed to `submission__match__tournament=t` |
| Missing `forfeits` count | Added `forfeit_matches = matches_qs.filter(state="forfeit").count()` |

### 3.2 `audit_service.py` — 4 bugs fixed

| Bug | Fix |
|-----|-----|
| `tournament=self.tournament` — field is `tournament_id` IntegerField | Changed to `tournament_id=self.tournament.id` |
| `order_by("-created_at")` — field is `timestamp` | Changed to `order_by("-timestamp")` |
| `created_at__gte` filter — field is `timestamp` | Changed to `timestamp__gte` |
| `extra_data` references throughout — field is `metadata` | Changed all to `metadata` |
| `a.created_at` in serializer — field is `timestamp` | Changed to `a.timestamp` |

---

## 4. Architecture Overview

### 4.1 System Map

```
┌─────────────────────────────────────────────────────────────────┐
│                      PARTICIPANTS                                │
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│   │  Tournament   │───▶│  The Hub     │───▶│  Match Room  │      │
│   │  Detail Page  │    │  (11 tabs)   │    │  (per-match) │      │
│   └──────────────┘    └──────────────┘    └──────────────┘      │
│                             │ HTTP poll 20s     │ reload 30s     │
│                             ▼                   ▼                │
│                    ┌──────────────────────────────┐              │
│                    │  WebSocket Consumers          │              │
│                    │  (TournamentConsumer,         │              │
│                    │   MatchConsumer)              │              │
│                    │  ⚠️ NOT connected to Hub/Room │              │
│                    └──────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      ORGANIZER / STAFF                           │
│                                                                  │
│   ┌──────────────────────────────────────────────────────┐      │
│   │  TOC — Tournament Operations Console                  │      │
│   │  `/toc/<slug>/` — Single-page with 15 tabs            │      │
│   │                                                       │      │
│   │  ┌─────────┐ ┌──────────────┐ ┌──────────────┐       │      │
│   │  │Overview  │ │ Matches ★    │ │ Participants │       │      │
│   │  │(Command  │ │ (Control     │ │ Payments     │       │      │
│   │  │ Center)  │ │  Room)       │ │ Brackets     │       │      │
│   │  └─────────┘ └──────────────┘ │ Schedule     │       │      │
│   │                               │ Disputes     │       │      │
│   │  115 API endpoints            │ Announcements│       │      │
│   │  across 11 sprints            │ Settings     │       │      │
│   │                               │ Audit Log    │       │      │
│   │                               └──────────────┘       │      │
│   └──────────────────────────────────────────────────────┘      │
│                             │                                    │
│                             ▼  HTTP API                          │
│                    ┌──────────────────────┐                      │
│                    │  /api/toc/<slug>/     │                      │
│                    │  TOCMatchesService    │                      │
│                    │  + 10 other services  │                      │
│                    └──────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Match Lifecycle (Organizer Perspective in TOC)

```
                    ┌─────────────────────────┐
                    │  Group Draw Complete     │
                    │  (Sprint 10J)           │
                    │  8 groups finalized      │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  Match Generation        │  ← NOT YET TRIGGERED
                    │  Round-robin within      │    Need: /api/toc/<slug>/
                    │  each group              │    schedule/auto-generate
                    └────────┬────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │  SCHEDULED                   │
              │  Visible in TOC Matches tab  │
              │  Admin sets lobby_info       │
              └──────────┬──────────────────┘
                         │  Admin or auto → CHECK_IN
              ┌──────────▼──────────────────┐
              │  CHECK_IN                    │
              │  Participants check in       │
              │  per-match in Match Room     │
              └──────────┬──────────────────┘
                         │  Both checked in → READY
              ┌──────────▼──────────────────┐
              │  READY                       │
              │  Admin clicks "Mark Live"    │
              └──────────┬──────────────────┘
                         │
              ┌──────────▼──────────────────┐
              │  LIVE                        │
              │  Score updates possible      │
              │  Can pause/resume            │
              └──────────┬──────────────────┘
                         │  Result submitted
              ┌──────────▼──────────────────┐
              │  PENDING_RESULT              │
              │  Verify screen (Sprint 9)    │
              │  Compare evidence            │
              └──────────┬──────────────────┘
                         │  Admin verifies
              ┌──────────▼──────────────────┐
              │  COMPLETED                   │
              │  Scores final                │
              │  Bracket advances            │
              └─────────────────────────────┘
```

---

## 5. Sprint 26 Implementation Plan

### Phase A: Backend Hardening (P0)

#### A1. Enrich Match Serializer

**File**: `apps/tournaments/api/toc/matches_service.py` → `_serialize_match`

Add fields:
```python
'bracket_id': m.bracket_id,
'group_label': cls._resolve_group_label(m),  # new helper
'lobby_info': {
    'lobby_code': m.lobby_info.get('lobby_code'),
    'map': m.lobby_info.get('map'),
    'server': m.lobby_info.get('server'),
    'game_mode': m.lobby_info.get('game_mode'),
},
'participant1_checked_in': m.participant1_checked_in,
'participant2_checked_in': m.participant2_checked_in,
'check_in_deadline': m.check_in_deadline.isoformat() if m.check_in_deadline else None,
```

**New helper** — `_resolve_group_label(m)`:  
Since there's no FK from Match to Group, resolve via:
1. Check `m.lobby_info.get('group_label')` (set during match generation)
2. Fallback: Query `GroupStanding` to find which group contains `m.participant1_id`
3. Cache results in a class-level dict during list serialization

#### A2. Add `group_label` to Match Generation

When matches are generated (via `schedule/auto-generate` or bracket service), store `group_label` in `lobby_info`:
```python
match.lobby_info['group_label'] = group.name  # e.g., "Group A"
```

**File**: `apps/tournaments/api/toc/brackets_service.py` → match creation flow  
**File**: `apps/tournament_ops/services/match_service.py` → if match creation happens here

#### A3. Add Group Filter to Match List API

**File**: `apps/tournaments/api/toc/matches_service.py` → `get_matches()`

Accept new `?group=` query parameter:
```python
if group:
    qs = qs.filter(lobby_info__group_label=group)
```

#### A4. Fix Silent Exception Swallowing

**File**: `apps/tournaments/api/toc/matches_service.py`

In `submit_score`, `mark_live`, `forfeit_match` — replace bare `except Exception` with:
```python
except MatchService.TransitionError as e:
    # Fallback is acceptable for transition issues
    ...
except Exception as e:
    logger.error("Unexpected error in X: %s", e, exc_info=True)
    raise  # Don't silently mask real bugs
```

#### A5. Add Match Count Pagination

**File**: `apps/tournaments/api/toc/matches_service.py` → `get_matches()`

Add pagination support (`?page=1&per_page=50`) or at minimum return a `total_count` alongside the list so the UI knows when there are more.

---

### Phase B: Frontend Overhaul — UI/UX (P0–P1)

#### B1. Font Size & Readability Pass

All instances below WCAG-recommended 12px must be bumped:

| Current | New | Where |
|---------|-----|-------|
| `text-[8px]` | `text-[11px]` | State badges, submission pills, evidence buttons |
| `text-[9px]` | `text-xs` (12px) | Group pills, match metadata, form labels, medic buttons |
| `text-[10px]` | `text-xs` or `text-sm` | Filter controls, stat items, detail labels, action buttons |
| `text-xs` (12px) | Keep or bump to `text-sm` (14px) for body text | Audit trail, score display, descriptions |

**Files**: `templates/tournaments/toc/base.html` (Matches tab HTML), `static/tournaments/toc/js/toc-matches.js` (rendered HTML in JS)

#### B2. Match List Card Redesign

Current cards are too compact. Redesign for scannability:

```
┌─────────────────────────────────────┐
│  [Live dot]  R1 · Match #3          │
│                                      │
│  Team Alpha          3              │
│  Team Beta           1              │
│                                      │
│  ◎ Group A    ⏱ 12:45     ✓ P1 P2  │
│            └ lobby status  └ checkin │
└─────────────────────────────────────┘
```

Features per card:
- Round + match number header
- Team names in **14px** (not 12px)
- Score beside each team (bold, color-coded for winner)
- Bottom bar: Group pill, time/duration, check-in indicators
- Selection highlight: 3px left border + subtle background
- Live matches: Pulsing green dot + "LIVE" badge
- Disputed: Red border glow

#### B3. Detail Panel Improvements

**Header**:
- Team names: **18px** → **20px**
- Score display: **30px** → **36px**
- Add lobby info row: Code / Map / Server (if set)
- Add check-in status: ✓P1, ✓P2 with green/gray indicators
- Add direct link to participant Match Room: `[👁 View Match Room]` button

**Score Editor**:
- Larger inputs (current: `text-xl`/20px → `text-2xl`/24px)
- Better label contrast
- Winner auto-highlight based on score entry

**Evidence Viewer**:
- Larger thumbnails (current 120px → 180px)
- Add touch event support for pan/zoom on mobile
- Keyboard shortcuts (← → to switch sides)

**Audit Trail**:
- Show actor avatars
- Color-code by action type
- Expandable detail (currently flat list)

#### B4. Action Row Improvements

Current buttons are too small (`text-[10px]`). Redesign:
- Minimum button height: **36px** (was ~28px)
- Font size: **text-sm** (14px)
- Group by intent: [Primary actions] [Danger zone]
- Add confirmation dialog for destructive actions (Reset, Force Complete, Forfeit)
- Replace `prompt()` in `openDispute()` with a proper modal

#### B5. Empty State Enhancement

When no matches exist, show an informative state instead of a bare "0 matches":

```
┌─────────────────────────────────────────────┐
│                                              │
│        ⊘ No Matches Yet                      │
│                                              │
│   Matches haven't been generated for this    │
│   tournament. To begin:                      │
│                                              │
│   1. Ensure groups/brackets are finalized    │
│   2. Go to Schedule tab → Auto-Generate      │
│                                              │
│   [Go to Schedule →]                         │
│                                              │
└─────────────────────────────────────────────┘
```

#### B6. XSS Protection

Add HTML escaping to all rendered user content:
```javascript
function esc(s) {
    var d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}
```

Apply to: `participant1_name`, `participant2_name`, `group_label`, `admin_note`, all user-submitted text.

#### B7. Accessibility

- Match cards: `tabindex="0"`, `role="button"`, `aria-label="Match N: Team A vs Team B"`
- Group pills: `aria-pressed="true/false"` for active filter
- Detail tabs: `role="tablist"`, `role="tab"`, `aria-selected`, `role="tabpanel"`
- Score inputs: proper `<label for="">` associations
- Medic buttons: `aria-label` on icon-only buttons
- Keyboard: Enter/Space to select match card (not just ArrowUp/Down)

---

### Phase C: Lobby Integration (P1)

#### C1. Lobby Info Panel in Match Detail

Add a collapsible "Lobby" section in the detail panel (between header and tabs):

```
┌─ LOBBY INFO ─────────────────────────────┐
│  Code: ABC123 [📋]   Map: Haven           │
│  Server: AP-SE       Mode: Competitive     │
│  Password: ●●●● [👁]                      │
│                                            │
│  Match Room:  [Open Room →]  [Copy Link]  │
└────────────────────────────────────────────┘
```

**API change**: `_serialize_match` already has `lobby_info` (from Phase A). Just render it.

#### C2. Lobby Editor Overlay

When admin clicks a match, enable editing `lobby_info` fields:
- Lobby code, password, map, server, game_mode
- Auto-generate button for random lobby code
- Save calls existing `matches/<pk>/add-note/` or a new `matches/<pk>/lobby-info/` endpoint

**Backend**: May need a new `MatchLobbyInfoView` — or extend `lobby_info` update through the existing `matches/<pk>/` PATCH (if it exists) or through a dedicated endpoint.

#### C3. Check-In Status Display

Show per-match check-in in the match list cards and detail panel:
- Two dots: ✓P1, ✓P2 (green if checked in, gray if not)
- Check-in deadline countdown if the match is in `check_in` state
- Ability for admin to force check-in (toggle) via existing `toggle-checkin` patterns

---

### Phase D: Polish & Production Quality (P2)

#### D1. Custom Dispute Modal

Replace `prompt()` with a styled modal:
- Reason code dropdown (game_bug, cheating, wrong_score, disconnection, other)
- Description textarea
- Severity selector
- Evidence upload
- Assignee selector (from RBAC staff list)

#### D2. Mobile Responsiveness

- When `grid-cols-[380px_1fr]` collapses to single column on mobile:
  - Add a "← Back to List" button in detail panel
  - Add swipe gesture to return to list
  - Make action row sticky at bottom
  - Stack score inputs vertically

#### D3. Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑/↓` | Navigate match list (existing) |
| `Enter` | Select highlighted match |
| `Escape` | Close detail / clear selection |
| `1/2/3` | Switch detail tabs (Score/Evidence/Audit) |
| `S` | Focus score input |
| `D` | Open dispute |
| `N` | Add note |

#### D4. Real-Time Updates (Future)

Currently the matches tab uses manual refresh. Future WebSocket integration:
- Connect to `TournamentConsumer` ws channel
- Listen for `match_started`, `score_updated`, `match_completed`, `dispute_created`
- Auto-update match list and detail panel without polling
- Show live activity indicator (pulsing dot in tab)

---

## 6. Gap Analysis — Full Platform Gaps

### 6.1 Participant-Facing Gaps

| Gap | Severity | Current State | Needed |
|-----|----------|---------------|--------|
| Hub uses HTTP polling, not WebSockets | Medium | `setInterval` 20s/45s | Connect to `TournamentConsumer` for sub-second updates |
| Match Room uses page reload | Medium | `setTimeout → location.reload()` 30s | Connect to `MatchConsumer` |
| No map veto / pick-ban UI | High | `lobby_info` stores map post-decision | Interactive veto interface in Match Room |
| No in-app chat / comms | Medium | Discord links only | WebSocket-based lobby chat |
| No push notifications | Medium | Rely on user being in Hub | Web Push for check-in reminders, match-ready alerts |
| No automated game server lobby creation | Medium | Manual `lobby_info` | API integration with game servers (VALORANT custom games, etc.) |
| No match replay/VOD storage | Low | `stream_url` only | Upload + playback for post-match review |

### 6.2 Organizer-Facing Gaps (TOC)

| Gap | Severity | Current State | Needed |
|-----|----------|---------------|--------|
| Match list has no group filter API | High | Only `?state=&round=&search=` | Add `?group=` filter |
| No pagination on match list | Medium | Hard-coded `[:500]` | Proper pagination for large tournaments |
| No bulk match operations | Medium | One-by-one actions | Bulk mark-live, bulk force-complete |
| No lobby info editor | High | No UI to set codes/maps/servers | Lobby editor overlay |
| No match generation from TOC | High | Must use separate endpoint | "Generate Matches" button in Matches tab |
| No match room observer link | Medium | Admin can't easily watch matches | Direct link to Match Room from detail |
| Freeze uses config JSONB, not a status | Low | `config['frozen']` flag | Dedicated frozen status field |
| Alert IDs are ephemeral | Low | Enumeration index as ID | Persistent alert IDs |

### 6.3 Cross-Cutting Gaps

| Gap | Severity | Description |
|-----|----------|-------------|
| No anti-cheat integration | High | No screenshot verification, replay upload, or client-side anti-cheat checks |
| No warm-up / practice mode | Low | No pre-match warm-up room feature |
| No seeding visibility before bracket | Low | Participants can't preview seeds |
| No self-service match scheduling | Low | Flexible-time formats need participant-driven scheduling |

---

## 7. File Inventory

### Files to Modify

| File | What Changes | Phase |
|------|-------------|-------|
| `apps/tournaments/api/toc/matches_service.py` | Enrich serializer, add group filter, fix exception handling, add pagination | A |
| `apps/tournaments/api/toc/matches.py` | Pass new query params | A |
| `templates/tournaments/toc/base.html` | Font sizes, match card layout, lobby info section, empty state, accessibility | B |
| `static/tournaments/toc/js/toc-matches.js` | XSS fixes, card rendering, lobby display, modal for disputes, keyboard shortcuts, accessibility attrs | B, C, D |
| `apps/tournaments/api/toc/brackets_service.py` | Store `group_label` in `lobby_info` during match generation | A |

### Files Already Fixed (Pre-Sprint)

| File | What Was Fixed |
|------|---------------|
| `apps/tournaments/api/toc/stats_service.py` | Wrong field names: `status`→`state`, `group_stage` removed, `DisputeRecord.tournament` → `submission__match__tournament`, added forfeits count |
| `apps/tournaments/api/toc/audit_service.py` | Wrong field names: `tournament`→`tournament_id`, `created_at`→`timestamp`, `extra_data`→`metadata` |

### Files for Reference (Read-Only)

| File | Purpose |
|------|---------|
| `apps/tournaments/models/match.py` | Match model definition |
| `apps/tournaments/models/lobby.py` | TournamentLobby + CheckIn models |
| `apps/tournaments/views/hub.py` | Hub view + 400-line `_build_hub_context()` |
| `apps/tournaments/views/match_room.py` | Match Room view (participant page) |
| `templates/tournaments/hub/hub.html` | Hub SPA template |
| `templates/tournaments/match_room/room.html` | Match Room template |
| `static/tournaments/js/hub-engine.js` | Hub JS engine (1481 lines) |
| `apps/tournaments/realtime/consumers.py` | TournamentConsumer |
| `apps/tournaments/realtime/match_consumer.py` | MatchConsumer |
| `apps/tournaments/services/command_center_service.py` | Alert generation logic |
| `apps/tournament_ops/services/match_service.py` | Core match state machine |

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Match generation creates invalid lobby_info structure | Medium | High | Write test that generates matches and validates serialization |
| Group filter breaks for bracket-stage matches (no group) | Medium | Medium | Handle `null` group_label gracefully — show "Bracket" or "Playoffs" |
| Font size increase breaks layout in tight areas | Low | Medium | Test on 1366x768 resolution minimum |
| XSS escaping breaks legitimate HTML in admin notes | Low | Low | render admin notes as plain text, not HTML |
| Lobby info editor creates race condition with Match Room | Low | Medium | Use optimistic locking or `updated_at` check |
| Large tournament (500+ matches) hits performance wall | Medium | High | Implement pagination + virtual scrolling for match list |

---

## Summary

**Sprint 26 is a 4-phase operation:**

| Phase | Focus | Effort |
|-------|-------|--------|
| **A** | Backend hardening (serializer, group filter, error handling) | ~4 hours |
| **B** | Frontend UI/UX overhaul (fonts, cards, detail, empty state, XSS, a11y) | ~8 hours |
| **C** | Lobby integration (info panel, editor, check-in display) | ~4 hours |
| **D** | Polish (dispute modal, mobile, keyboard shortcuts) | ~4 hours |

**Total estimated: ~20 hours across 4 phases.**

The most critical path is **Phase A** (backend must return correct data before frontend can display it) followed by **Phase B** (the visible UI problems the user reported).
