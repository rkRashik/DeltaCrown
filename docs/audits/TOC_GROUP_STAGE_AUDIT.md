# TOC Group Stage — Architecture & Gap Audit
**Scope**: TOC_MASTER_PLANNING_DOCUMENT.md §5.5 (Group Stage System) and §5.10 (Live Broadcast Director)
**Date**: 2025-07
**Method**: Code archaeology — direct inspection of service layer, models, consumers, and management commands

---

## Executive Summary

The Epic 3.2 group stage pipeline (`create_groups → assign_participant → generate_group_matches → calculate_group_standings`) is **structurally sound** and ready for integration tests.  Three bugs in the **legacy** `calculate_standings()` method have been fixed as part of this audit.  Four planned features are still missing: double round-robin, 3rd-place cross-group advancement, group rebalancing, and the Live Draw Director control panel.

---

## 1. Method Inventory

| Method | Location | Status | Notes |
|---|---|---|---|
| `create_groups()` | `group_stage_service.py:640` | ✅ Works | Creates GroupStage + N Groups |
| `assign_participant()` | `group_stage_service.py:711` | ✅ Works | Creates GroupStanding correctly |
| `generate_group_matches()` | `group_stage_service.py:848` | ✅ Works | Single RR only (see Gap #1) |
| `calculate_group_standings()` | `group_stage_service.py:900` | ✅ Works | Epic 3.2 path — `state=Match.COMPLETED`, `lobby_info__group_id` filter |
| `get_advancers()` | `group_stage_service.py:566` | ✅ Works | Returns `Dict[group_name → List[GroupStanding]]` |
| `generate_knockout_from_groups()` | `bracket_service.py:440` | ✅ Works | Calls `get_advancers()`, seeds bracket correctly |
| `calculate_standings()` (legacy) | `group_stage_service.py:329` | 🔴 → ✅ Fixed | **3 bugs fixed** (see §2) |
| `draw_groups()` (legacy) | `group_stage_service.py:151` | ⚠️ Legacy | Predates Epic 3.2 GroupStage model; avoid in new code |
| `configure_groups()` (legacy) | `group_stage_service.py:50` | ⚠️ Legacy | Predates Epic 3.2; callers should migrate to `create_groups()` |
| `LiveDrawConsumer` | `consumers/live_draw_consumer.py:1` | ⚠️ Partial | Auto-fire bracket seed reveals only; no group draw ceremony (see §5.10) |

---

## 2. Bugs Found and Fixed

### Bug 2-A — `calculate_standings()`: `status` instead of `state`
**File**: `apps/tournaments/services/group_stage_service.py` ~line 356  
**Severity**: Critical — standings never computed (0 matches always returned)

```python
# BEFORE (broken)
matches = Match.objects.filter(tournament=..., status='completed', ...)

# AFTER (fixed)
matches = Match.objects.filter(tournament=..., state=Match.COMPLETED, ...)
```

**Root cause**: `Match` model uses `state` (not `status`) with `Match.COMPLETED = 'completed'`.

---

### Bug 2-B — `calculate_standings()`: Non-existent field traversals in Q-filter
**File**: Same method, Q-filter block  
**Severity**: Critical — Django raises `FieldError` at runtime; method never reaches standings logic

```python
# BEFORE (broken) — `participant1_user`, `participant1_team` etc. do not exist on Match
Q(participant1_user__in=[...]) | Q(participant1_team__in=[...]) | ...

# AFTER (fixed) — Match stores participant IDs as plain integers
Q(participant1_id__in=user_ids + team_ids) | Q(participant2_id__in=user_ids + team_ids)
```

**Root cause**: `Match` model stores `participant1_id` / `participant2_id` as `PositiveIntegerField` (not ForeignKeys).

---

### Bug 2-C — `_update_standing_from_match()`: `winner_participant` field does not exist
**File**: Same service, `_update_standing_from_match()` ~line 427  
**Severity**: Critical — `AttributeError` raised on every match; no points ever assigned

```python
# BEFORE (broken)
if match.winner_participant == 1: ...
elif match.winner_participant == 2: ...

# AFTER (fixed) — Match.winner_id is the actual participant PK (or None for draw)
if match.winner_id == match.participant1_id: ...
elif match.winner_id == match.participant2_id: ...
```

Also fixed the participant lookup in the same method:
```python
# BEFORE (broken)
standing1 = next((s for s in standings if s.user == match.participant1_user ...), None)

# AFTER (fixed)
def _pid(s): return s.user_id if s.user_id else s.team_id
standing1 = next((s for s in standings if _pid(s) == match.participant1_id), None)
```

---

### Deprecation Applied
`calculate_standings()` docstring now carries a `.. deprecated::` notice pointing callers to `calculate_group_standings(stage_id)` (Epic 3.2 path, which was already correct).

---

## 3. Gap Analysis — §5.5 Group Stage System

### Gap 3.1 — Double Round-Robin ❌ NOT IMPLEMENTED
**Plan says**: "Each pair meets twice (home + away)."  
**Current**: `generate_group_matches()` generates each pairing exactly once (standard RR).

**Workaround for stress-test**: Run `generate_group_matches(stage_id)` twice.  
**Proper fix**: Add `rounds=2` parameter to `generate_group_matches()` and loop pairings N times.

```python
# Proposed signature change:
def generate_group_matches(stage_id: int, rounds: int = 1) -> int:
    ...
    for round_number in range(1, rounds + 1):
        for idx, (p1, p2) in enumerate(pairings, start=1):
            Match.objects.create(
                round_number=round_number,
                ...
            )
```

**Impact**: Without double-RR, UCL-format tournaments have half the expected matches.  Double-RR also affects standings display (max wins = 2×(n-1) not (n-1)).

---

### Gap 3.2 — 3rd-Place Cross-Group Advancement ❌ NOT IMPLEMENTED
**Plan says**: "Best N 3rd-place teams from all groups may advance (e.g., UEFA Euro format)."  
**Current**: `get_advancers()` returns the top `group.advancement_count` standings per group — no cross-group comparison.

**Impact**: Any tournament using "best 4 of 8 3rd-place teams" cannot run.

**Proposed fix**: Extend `get_advancers()` with an optional `wildcard_count` parameter:
```python
# After collecting per-group advancers, optionally collect 3rd-place wildcards:
if wildcard_count:
    third_place = [group_standings[2] for group_standings in all_groups if len >= 3]
    third_place.sort(key=lambda s: (-s.points, -s.goal_difference, -s.goals_for))
    wildcards = third_place[:wildcard_count]
    result["__wildcards__"] = wildcards
```

---

### Gap 3.3 — Group Rebalancing ❌ NOT IMPLEMENTED
**Plan says**: "Organizer can move a player between groups if no matches have started."  
**Current**: No service method for moving a GroupStanding from one group to another.

**Proposed fix**: New `GroupStageService.rebalance_group(stage_id, standing_id, target_group_id)` method that:
1. Verifies no completed matches exist for this participant in the source group.
2. Updates `standing.group = target_group`.
3. Checks target group capacity.
4. Re-runs `generate_group_matches` for affected groups (requires deleting existing SCHEDULED matches first).

---

### Gap 3.4 — Group Draw Animation / Ceremony ⚠️ PARTIAL
**Current**: `LiveDrawConsumer.start_draw` action does a bracket seed reveal only (auto-fires with 2.5 s delay between each participant, no group assignment logic).  
**Missing**: A step-by-step group assignment ceremony — organizer clicks "Draw Next", pot ball animates, player is revealed and pot is assigned.

This gap is covered in full in §5 (Phase 3 architecture).

---

### Gap 3.5 — Frontend Standings Table Connection ⚠️ UNKNOWN
The audit did not find a REST endpoint that calls `calculate_group_standings(stage_id)` and returns JSON consumable by the TOC Groups tab.  
**Recommendation**: Audit `apps/api/` for a `/tournaments/{id}/group-standings/` endpoint.  If absent, add it before the group stage tab is wired up.

---

## 4. Gap Analysis — §5.10 Live Broadcast Director

### Gap 4.1 — No Director Control Panel ❌ NOT IMPLEMENTED
**Plan says**: Organizer authenticates to a "Director" view, clicks "Draw Next Player", and the draw is broadcast live to a public spectator URL.

**Current state**: `LiveDrawConsumer` at `ws/tournament/<id>/draw/` accepts one action (`start_draw`) and then auto-fires all reveals in a single coroutine with fixed 2.5 s delays.  There is no `draw_next` action, no pending queue persistence, no group-assignment logic, and no split between director auth and public view.

**Missing components** (fully specced in the Phase 3 Architecture doc):
1. `draw_next` WebSocket action (organizer-controlled)
2. Draw session state in Redis cache
3. Group assignment tracking during draw
4. `finalize_draw` action to commit assignments via `GroupStageService.assign_participant()`
5. Director URL guarded by tournament organizer permission
6. Public spectator URL (read-only) at the same channel group

---

### Gap 4.2 — No Pre-Draw Pot Seeding UI ❌ NOT IMPLEMENTED
**Plan says**: Organizer configures seed pots before draw (e.g., Pot 1 = top 8 ranked teams).  
**Current**: `draw_groups()` accepts `draw_method='seeded'` but the UI for building pots does not exist.

---

### Gap 4.3 — No Seed Verification / Audit Log ❌ NOT IMPLEMENTED  
**Plan says**: After draw, a seed hash is published so the result is tamper-evident.  
**Current**: No hash/audit trail on draws.

**Proposed**: At `finalize_draw`, SHA-256 hash the ordered assignment list and store in `GroupStage.config["draw_audit"]`.

---

## 5. Summary Scorecard

| Feature | §5.5 Status | Gap |
|---|---|---|
| Group creation (A-H) | ✅ Done | — |
| Random / seeded draw | ✅ Done | Legacy path; Epic 3.2 uses `assign_participant` |
| Single round-robin matches | ✅ Done | — |
| Standings calculation (Epic 3.2) | ✅ Done | — |
| Standings calculation (legacy) | 🔴→✅ Fixed | 3 bugs now patched; marked deprecated |
| Group → Knockout advancement | ✅ Done | — |
| Double round-robin | ❌ Missing | No `rounds` param on `generate_group_matches` |
| 3rd-place wildcard advancement | ❌ Missing | No cross-group comparison in `get_advancers` |
| Group rebalancing | ❌ Missing | No service method exists |
| Draw ceremony (`draw_next`) | ❌ Missing | Covered in Phase 3 |

| Feature | §5.10 Status | Gap |
|---|---|---|
| Auto-fire bracket seed reveal | ✅ Done | `LiveDrawConsumer.start_draw` |
| Director panel (step-by-step) | ❌ Missing | Phase 3 |
| `draw_next` WS action | ❌ Missing | Phase 3 |
| Public spectator view | ❌ Missing | Phase 3 |
| Draw session persistence (Redis) | ❌ Missing | Phase 3 |
| Seed hash / audit log | ❌ Missing | Gap 4.3 |
| Pot seeding UI | ❌ Missing | Gap 4.2 |

---

## 6. Recommended Fix Priority

1. **P0** (Now) — ✅ All 3 `calculate_standings` bugs fixed.
2. **P1** (Next sprint) — `generate_group_matches(rounds=2)` for double-RR support.
3. **P1** (Next sprint) — Live Draw Director WebSocket architecture (Phase 3).
4. **P2** (Following sprint) — `get_advancers(wildcard_count=N)` for 3rd-place advancement.
5. **P2** (Following sprint) — `rebalance_group()` method + admin UI.
6. **P3** (Backlog) — Draw audit hash, pot seeding UI.
