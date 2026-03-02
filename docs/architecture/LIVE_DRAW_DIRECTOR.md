# Phase 3 — Live Draw Director: Architecture Specification
**Scope**: TOC §5.10 — Interactive group draw ceremony with organizer control and public spectator broadcast  
**Depends on**: TOC Group Stage system (GroupStageService.create_groups / assign_participant)  
**Supersedes**: Current `LiveDrawConsumer.start_draw` auto-fire behaviour (bracket seed path, keep untouched)

---

## 1. Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Organizer Browser                  Public Browser(s)                        │
│  /tournaments/{id}/draw/director/   /tournaments/{id}/draw/live/             │
│                                                                              │
│  [Director Panel]                   [Spectator View]                         │
│   • "Draw Next Player" button        • Animated pot card flip                │
│   • Group grid (A-H, filling)        • Group grid (read-only, live fills)    │
│   • Pending queue count              • "X players remaining"                 │
│                                                                              │
└──────────────┬──────────────────────────────────┬────────────────────────────┘
               │ WS (director actions)             │ WS (events only)
               ▼                                   ▼
        ┌─────────────────────────────────────────────┐
        │        GroupDrawConsumer                     │
        │   ws/tournament/<id>/group-draw/             │
        │                                              │
        │  Actions:  init_draw, draw_next,             │
        │            assign_override, finalize_draw,   │
        │            abort_draw                        │
        │                                              │
        │  Events:   draw_session_open, player_drawn,  │
        │            draw_complete, draw_aborted       │
        └──────────────────┬──────────────────────────┘
                           │
               ┌───────────┴────────────────────────┐
               │ Redis Channel Layer                 │ Redis Cache
               │ group: live_group_draw_{tid}        │ key: draw_session:{tid}
               └─────────────────────────────────────┘
                           │
               ┌───────────┴────────────────────────┐
               │ GroupStageService.assign_participant │
               │ on finalize_draw only               │
               └─────────────────────────────────────┘
```

---

## 2. New File: `GroupDrawConsumer`

**Path**: `apps/tournaments/consumers/group_draw_consumer.py`

This is a **new consumer** — it does NOT replace `LiveDrawConsumer` (which handles bracket seed reveals).

### 2.1 Connection & Auth

```python
class GroupDrawConsumer(AsyncJsonWebsocketConsumer):
    """
    Interactive group draw ceremony consumer.

    URL route: ws/tournament/<tournament_id>/group-draw/

    Channel group: live_group_draw_{tournament_id}
        - Organizer connects first (init_draw)
        - Spectators connect and receive real-time events
        - Organizer actions are permission-gated; spectators are read-only
    """

    async def connect(self):
        self.tournament_id = self.scope["url_route"]["kwargs"]["tournament_id"]
        self.group_name = f"live_group_draw_{self.tournament_id}"
        self.user = self.scope.get("user")

        # Reject anonymous connections (spectators must be logged in too, or
        # change to allow anon for public read-only)
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # On connect, send current draw session state (if active) to this client
        session = await self._get_session()
        if session:
            await self.send_json({
                "type": "draw_session_snapshot",
                "session": session,
            })
```

### 2.2 Action Router

```python
    async def receive_json(self, content):
        action = content.get("action")
        handlers = {
            "init_draw":       self._handle_init_draw,
            "draw_next":       self._handle_draw_next,
            "assign_override": self._handle_assign_override,
            "finalize_draw":   self._handle_finalize_draw,
            "abort_draw":      self._handle_abort_draw,
        }
        handler = handlers.get(action)
        if handler is None:
            await self.send_json({"type": "error", "message": f"Unknown action: {action}"})
            return

        # All write actions require organizer auth
        if action != "draw_next" or True:   # all actions are write-gated
            if not await self._is_organizer():
                await self.send_json({"type": "error", "message": "Organizer only."})
                return

        await handler(content)
```

---

## 3. Draw Session State (Redis)

**Cache key**: `draw_session:{tournament_id}`  
**TTL**: 4 hours (prevents orphaned sessions)

```python
# Session schema
{
    "tournament_id": 42,
    "organizer_id": 7,
    "stage_id": 3,
    "groups": ["A", "B", "C", "D", "E", "F", "G", "H"],
    "group_size": 4,
    "queue": [
        # Ordered list of undrawn participants
        {"user_id": 101, "username": "ucl_kronos", "display_name": "Kronos", "pot": 1},
        {"user_id": 102, "username": "ucl_phantom_x", "display_name": "Phantom_X", "pot": 1},
        # ...
    ],
    "assignments": {
        # group_name → list of drawn participants
        "A": [],
        "B": [],
        # ...
    },
    "next_group_index": 0,   # which group receives the next drawn player
    "drawn_count": 0,
    "total": 32,
    "started_at": "2025-07-01T14:00:00Z",
    "finalized": false,
}
```

### State helpers (async, using `cache`)

```python
import json
from django.core.cache import cache

DRAW_SESSION_TTL = 60 * 60 * 4  # 4 hours

async def _get_session(self) -> dict | None:
    data = await sync_to_async(cache.get)(f"draw_session:{self.tournament_id}")
    return data

async def _save_session(self, session: dict) -> None:
    await sync_to_async(cache.set)(
        f"draw_session:{self.tournament_id}", session, DRAW_SESSION_TTL
    )

async def _delete_session(self) -> None:
    await sync_to_async(cache.delete)(f"draw_session:{self.tournament_id}")
```

---

## 4. Action Handlers

### 4.1 `init_draw`

**Sent by**: Organizer  
**When**: Before first draw; sets up the session.

```python
# Request
{
    "action": "init_draw",
    "stage_id": 3,
    "pot_config": [
        # Optional. If omitted, all 32 participants go in one pot (random order).
        {"pot": 1, "user_ids": [101, 102, 103, 104, 105, 106, 107, 108]},
        {"pot": 2, "user_ids": [109, 110, ...]}
    ]
}

# Broadcast to all:
{
    "type": "draw_session_open",
    "tournament_id": 42,
    "stage_id": 3,
    "total": 32,
    "groups": ["A", "B", "C", "D", "E", "F", "G", "H"],
    "group_size": 4,
    "started_at": "2025-07-01T14:00:00Z"
}
```

**Logic**:
```python
async def _handle_init_draw(self, content):
    stage_id = content["stage_id"]
    pot_config = content.get("pot_config")  # optional

    # Load confirmed participants
    registrations = await _get_confirmed_registrations(self.tournament_id)

    # Build queue
    if pot_config:
        # Pot-ordered shuffle (snake draft: Pot 1 fills first slot in each group)
        queue = _build_pot_queue(registrations, pot_config)
    else:
        # Pure random
        queue = [_reg_to_dict(r) for r in registrations]
        random.shuffle(queue)

    groups = await _get_group_names(stage_id)

    session = {
        "tournament_id": self.tournament_id,
        "organizer_id": self.user.id,
        "stage_id": stage_id,
        "groups": groups,
        "group_size": len(registrations) // len(groups),
        "queue": queue,
        "assignments": {g: [] for g in groups},
        "next_group_index": 0,
        "drawn_count": 0,
        "total": len(queue),
        "started_at": timezone.now().isoformat(),
        "finalized": False,
    }
    await self._save_session(session)

    await self.channel_layer.group_send(self.group_name, {
        "type": "group_draw.session_open",
        "tournament_id": self.tournament_id,
        "stage_id": stage_id,
        "total": len(queue),
        "groups": groups,
    })
```

---

### 4.2 `draw_next`

**Sent by**: Organizer  
**When**: Organizer clicks "Draw Next Player" button.

```python
# Request
{"action": "draw_next"}

# Broadcast to ALL (organizer + all spectators):
{
    "type": "player_drawn",
    "player": {
        "user_id": 101,
        "username": "ucl_kronos",
        "display_name": "Kronos",
        "pot": 1
    },
    "assigned_group": "A",
    "group_count": 1,         # total players now in Group A
    "drawn_count": 1,
    "remaining": 31
}
```

**Logic**:
```python
async def _handle_draw_next(self, content):
    session = await self._get_session()
    if not session:
        await self.send_json({"type": "error", "message": "No active draw session."})
        return
    if not session["queue"]:
        await self.send_json({"type": "error", "message": "Draw queue is empty. Call finalize_draw."})
        return

    # Pop next player
    player = session["queue"].pop(0)

    # Determine target group (round-robin fill: A×4, B×4, ...)
    # Advance to next group when current group is full
    now_group = session["groups"][session["next_group_index"]]
    session["assignments"][now_group].append(player)

    # Advance group pointer if full
    if len(session["assignments"][now_group]) >= session["group_size"]:
        session["next_group_index"] += 1

    session["drawn_count"] += 1
    await self._save_session(session)

    # Broadcast to all
    await self.channel_layer.group_send(self.group_name, {
        "type": "group_draw.player_drawn",
        "player": player,
        "assigned_group": now_group,
        "group_count": len(session["assignments"][now_group]),
        "drawn_count": session["drawn_count"],
        "remaining": len(session["queue"]),
    })
```

---

### 4.3 `assign_override`

Organizer manually overrides the group for the LAST drawn player (before confirming the next).

```python
# Request
{"action": "assign_override", "player_user_id": 101, "target_group": "B"}
```

**Logic**: Pop the player from their current group assignment and append to `target_group`. Validation: target not already full.

---

### 4.4 `finalize_draw`

**Sent by**: Organizer after all players drawn.  Commits assignments via service, generates matches.

```python
# Request
{"action": "finalize_draw"}

# Broadcast to ALL:
{
    "type": "draw_complete",
    "assignments": {
        "A": [{"user_id": 101, "display_name": "Kronos"}, ...],
        "B": [...],
        ...
    },
    "seed_hash": "sha256:abc123...",    // tamper-evident audit
    "total_matches": 48
}
```

**Logic**:
```python
async def _handle_finalize_draw(self, content):
    session = await self._get_session()
    if not session:
        await self.send_json({"type": "error", "message": "No active draw session."})
        return
    if session["queue"]:
        await self.send_json({
            "type": "error",
            "message": f"{len(session['queue'])} players still undrawn."
        })
        return

    stage_id    = session["stage_id"]
    assignments = session["assignments"]

    # Compute tamper-evident hash
    import hashlib, json
    canonical = json.dumps(assignments, sort_keys=True, ensure_ascii=True)
    seed_hash = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    # Commit to DB via service layer (async wrapper)
    group_map = await sync_to_async(
        lambda: {g.name.split()[-1]: g for g in Group.objects.filter(
            tournament_id=self.tournament_id
        )}
    )()

    total_assigned = 0
    for group_letter, players in assignments.items():
        group = group_map.get(group_letter)
        if not group:
            continue
        for player in players:
            await sync_to_async(GroupStageService.assign_participant)(
                stage_id=stage_id,
                participant_id=player["user_id"],
                group_id=group.id,
                is_team=False,
            )
            total_assigned += 1

    # Generate matches
    total_matches = await sync_to_async(
        GroupStageService.generate_group_matches
    )(stage_id=stage_id)

    # Persist hash in GroupStage config
    await sync_to_async(_save_draw_audit)(stage_id, seed_hash, assignments)

    # Clean up Redis session
    session["finalized"] = True
    await self._delete_session()

    # Broadcast
    await self.channel_layer.group_send(self.group_name, {
        "type": "group_draw.draw_complete",
        "assignments": assignments,
        "seed_hash": seed_hash,
        "total_matches": total_matches,
    })
```

---

### 4.5 `abort_draw`

Organizer discards the active session without committing anything.

```python
async def _handle_abort_draw(self, content):
    await self._delete_session()
    await self.channel_layer.group_send(self.group_name, {
        "type": "group_draw.draw_aborted",
        "reason": content.get("reason", "Organizer aborted draw"),
    })
```

---

## 5. Channel Layer Event Handlers

```python
# These methods receive events from channel_layer.group_send() and forward to WS

async def group_draw_session_open(self, event):
    await self.send_json({**event, "type": "draw_session_open"})

async def group_draw_player_drawn(self, event):
    await self.send_json({**event, "type": "player_drawn"})

async def group_draw_draw_complete(self, event):
    await self.send_json({**event, "type": "draw_complete"})

async def group_draw_draw_aborted(self, event):
    await self.send_json({**event, "type": "draw_aborted"})
```

---

## 6. URL Routing

**`deltacrown/routing.py`** — add:

```python
re_path(
    r"^ws/tournament/(?P<tournament_id>\d+)/group-draw/$",
    GroupDrawConsumer.as_asgi(),
)
```

**Django template URLs** — add to `apps/tournaments/urls.py`:

```python
path(
    "tournaments/<int:tournament_id>/draw/director/",
    views.GroupDrawDirectorView.as_view(),
    name="group-draw-director",
),
path(
    "tournaments/<int:tournament_id>/draw/live/",
    views.GroupDrawPublicView.as_view(),
    name="group-draw-public",
),
```

The director view requires `LoginRequiredMixin` and checks `tournament.organizer == request.user`.  
The public view is accessible to all (no login required for spectators).

---

## 7. Frontend Integration (TOC Groups Tab)

When a tournament is in format `group_playoff` and groups are NOT yet finalized:

1. **Organizer sees**: "Start Group Draw" button under Brackets tab → navigates to `/tournaments/{id}/draw/director/`
2. **Director panel** (organizer):
   - Top: Group grid A-H, each showing empty slots
   - Bottom: "🎲 Draw Next Player" button (disabled until session initialized)
   - Side: Remaining queue count badge
3. **Public page** (`/tournaments/{id}/draw/live/`):
   - Same group grid, read-only
   - Connects to same WS channel as WebSocket spectator
   - On `player_drawn` event: animate a "card flip" reveal in the correct group column
4. **Both views** reconnect automatically on disconnect (standard WS reconnect logic)

---

## 8. Implementation Steps (Sprint Plan)

| # | Task | File | Estimate |
|---|---|---|---|
| 1 | Create `GroupDrawConsumer` skeleton (connect / auth / router) | `consumers/group_draw_consumer.py` | 1h |
| 2 | Implement `init_draw` + Redis session helpers | same | 1h |
| 3 | Implement `draw_next` + `player_drawn` broadcast | same | 1h |
| 4 | Implement `assign_override` | same | 30m |
| 5 | Implement `finalize_draw` (service calls + hash) | same | 1.5h |
| 6 | Implement `abort_draw` + channel event handlers | same | 30m |
| 7 | Wire URL route in `routing.py` | `deltacrown/routing.py` | 15m |
| 8 | Add `GroupDrawDirectorView` + `GroupDrawPublicView` | `apps/tournaments/views/` | 1h |
| 9 | Director HTML template (group grid + draw button) | `templates/tournaments/draw_director.html` | 2h |
| 10 | Public HTML template + JS animation on `player_drawn` | `templates/tournaments/draw_live.html` | 2h |
| 11 | Unit tests for `GroupDrawConsumer` | `tests/tournament/test_group_draw_consumer.py` | 2h |
| 12 | Integration test using `seed_uradhura_ucl` fixture | `tests/tournament/test_group_draw_integration.py` | 1h |

**Total estimate**: ~14 hours

---

## 9. Testing Strategy

Use `seed_uradhura_ucl` to provision the 32-player UCL tournament in a test DB, then:

```python
# tests/tournament/test_group_draw_consumer.py

@pytest.mark.django_db(transaction=True)
class TestGroupDrawConsumer:

    async def test_full_draw_ceremony(self, ucl_tournament):
        """Drive a complete 32-player draw end-to-end."""
        communicator = WebsocketCommunicator(
            application, f"/ws/tournament/{ucl_tournament.id}/group-draw/"
        )
        communicator.scope["user"] = ucl_tournament.organizer
        connected, _ = await communicator.connect()
        assert connected

        # init_draw
        await communicator.send_json_to({"action": "init_draw", "stage_id": ucl_tournament.stage.id})
        response = await communicator.receive_json_from()
        assert response["type"] == "draw_session_open"
        assert response["total"] == 32

        # draw 32 players
        for i in range(32):
            await communicator.send_json_to({"action": "draw_next"})
            response = await communicator.receive_json_from()
            assert response["type"] == "player_drawn"
            assert response["remaining"] == 31 - i

        # finalize
        await communicator.send_json_to({"action": "finalize_draw"})
        response = await communicator.receive_json_from()
        assert response["type"] == "draw_complete"
        assert response["total_matches"] == 48
        assert response["seed_hash"].startswith("sha256:")

        # Verify DB state
        from apps.tournaments.models import GroupStanding, Match
        assert await GroupStanding.objects.filter(tournament=ucl_tournament).acount() == 32
        assert await Match.objects.filter(tournament=ucl_tournament).acount() == 48
```

---

## 10. Security Considerations

| Risk | Mitigation |
|---|---|
| Non-organizer sends `draw_next` | `_is_organizer()` check on every write action |
| Two organizer tabs send concurrent `draw_next` | Redis `WATCH`/optimistic lock OR Django cache `add()` for mutex |
| Spectator replays `draw_complete` event from stale WS message | `finalized: true` flag in session prevents double-commit |
| Draw result is disputed | SHA-256 seed hash stored in `GroupStage.config["draw_audit"]` |
| Abusive abort of in-progress draw | Only tournament organizer can `abort_draw` |
