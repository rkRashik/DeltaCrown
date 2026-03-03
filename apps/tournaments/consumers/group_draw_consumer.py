"""
Group Draw Ceremony WebSocket Consumer

Interactive group draw ceremony with organizer control and public spectator broadcast.
Spec: docs/architecture/LIVE_DRAW_DIRECTOR.md

URL route: ws/tournament/<tournament_id>/group-draw/
Channel group: live_group_draw_{tournament_id}

Actions (organizer only):
    init_draw       — Initialize draw session with participant queue
    draw_next       — Draw next player from queue, assign to group
    draw_all        — Auto-draw all remaining players at once
    undo_last       — Pull last drawn player back into queue
    assign_override — Move last-drawn player to a different group
    finalize_draw   — Commit assignments to DB, generate matches
    abort_draw      — Discard session without committing

Broadcast events:
    draw_session_open    — Session created, groups & total announced
    draw_session_snapshot— Full session state on reconnect
    player_drawn         — Single player drawn and assigned to group
    draw_undone          — Last drawn player returned to queue
    viewer_count         — Number of active WebSocket viewers
    draw_complete        — All players drawn & committed to DB
    draw_aborted         — Session discarded by organizer
"""
import hashlib
import json
import logging
import random

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

DRAW_SESSION_TTL = 60 * 60 * 4  # 4 hours


class GroupDrawConsumer(AsyncJsonWebsocketConsumer):
    """Interactive group draw ceremony consumer."""

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #

    async def connect(self):
        self.tournament_id = self.scope["url_route"]["kwargs"]["tournament_id"]
        self.group_name = f"live_group_draw_{self.tournament_id}"
        self.user = self.scope.get("user")

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Track viewer count
        await self._incr_viewers(1)
        await self._broadcast_viewer_count()

        # Send current session snapshot (if draw is in progress)
        session = await self._get_session()
        if session:
            await self.send_json({
                "type": "draw_session_snapshot",
                "session": self._sanitize_session(session),
            })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self._incr_viewers(-1)
        await self._broadcast_viewer_count()

    # ------------------------------------------------------------------ #
    # Action router
    # ------------------------------------------------------------------ #

    async def receive_json(self, content, **kwargs):
        action = content.get("action")
        handlers = {
            "init_draw": self._handle_init_draw,
            "draw_next": self._handle_draw_next,
            "draw_all": self._handle_draw_all,
            "undo_last": self._handle_undo_last,
            "manual_assign": self._handle_manual_assign,
            "assign_override": self._handle_assign_override,
            "finalize_draw": self._handle_finalize_draw,
            "abort_draw": self._handle_abort_draw,
        }
        handler = handlers.get(action)
        if handler is None:
            await self.send_json({"type": "error", "message": f"Unknown action: {action}"})
            return

        # All write actions require organizer auth
        if not await self._is_organizer():
            await self.send_json({"type": "error", "message": "Organizer only."})
            return

        await handler(content)

    # ------------------------------------------------------------------ #
    # Action handlers
    # ------------------------------------------------------------------ #

    async def _handle_init_draw(self, content):
        """Initialize a draw session. Builds participant queue and group grid.

        Accepts optional configuration:
            group_architecture: {"num_groups": int, "group_size": int, "advancement_count": int}
            pot_config: list of {"pot": int, "user_ids": [int, ...]}
            fill_strategy: "round_robin" (default) | "sequential"
            prevent_region_clash: bool (default False)
        """
        # Prevent double-init
        existing = await self._get_session()
        if existing and not existing.get("finalized"):
            await self.send_json({
                "type": "error",
                "message": "A draw session is already active. Abort it first.",
            })
            return

        # Load confirmed participants
        participants = await self._get_confirmed_participants()
        if not participants:
            await self.send_json({
                "type": "error",
                "message": "No confirmed participants to draw.",
            })
            return

        # ── Group Architecture: Create/update groups if config provided ──
        arch = content.get("group_architecture")
        if arch:
            num_groups = int(arch.get("num_groups", 0))
            g_size = int(arch.get("group_size", 4))
            adv_count = int(arch.get("advancement_count", 2))
            total_slots = num_groups * g_size
            if num_groups < 1 or g_size < 2:
                await self.send_json({
                    "type": "error",
                    "message": "Invalid group architecture: need at least 1 group with 2 slots.",
                })
                return
            if total_slots < len(participants):
                await self.send_json({
                    "type": "error",
                    "message": f"Not enough group slots ({total_slots}) for {len(participants)} participants. "
                               f"Increase groups or group size.",
                })
                return
            if adv_count >= g_size:
                await self.send_json({
                    "type": "error",
                    "message": f"Advancement count ({adv_count}) must be less than group size ({g_size}).",
                })
                return
            await self._ensure_group_architecture(num_groups, g_size, adv_count)

        # Load group configuration
        groups_info = await self._get_groups()
        if not groups_info:
            await self.send_json({
                "type": "error",
                "message": "No groups configured. Configure groups first.",
            })
            return

        group_names = [g["name"] for g in groups_info]
        group_size = max(g["max_participants"] for g in groups_info) if groups_info else 4

        # ── Parse draw configuration ──
        pot_config = content.get("pot_config")          # [{pot:1, user_ids:[...]}, ...]
        fill_strategy = content.get("fill_strategy", "round_robin")  # "round_robin" | "sequential"
        prevent_region_clash = content.get("prevent_region_clash", False)
        broadcast_config = content.get("broadcast_config")  # {accent_color, background_url}
        org_constraint = content.get("org_constraint")      # {max_per_group: int} or None
        locked_seeds = content.get("locked_seeds")          # [{user_id, group_index, slot_index}] or None

        # ── Build queue ──
        if pot_config:
            # Pot-ordered queue: shuffle within each pot, then interleave
            # so draw_next with round-robin fill guarantees 1 per pot per group
            pot_lookup = {}  # user_id → pot number
            for pot_def in pot_config:
                pot_num = pot_def.get("pot", 0)
                for uid in pot_def.get("user_ids", []):
                    pot_lookup[uid] = pot_num

            # Tag participants with pot info
            for p in participants:
                p["pot"] = pot_lookup.get(p["user_id"], 0)

            # Group by pot, shuffle within each pot
            pots = {}
            unassigned = []
            for p in participants:
                pot_num = p.get("pot", 0)
                if pot_num > 0:
                    pots.setdefault(pot_num, []).append(p)
                else:
                    unassigned.append(p)

            for pot_players in pots.values():
                random.shuffle(pot_players)
            random.shuffle(unassigned)

            # Interleave: Pot 1 first, then Pot 2, etc.
            # This ensures round-robin fill places one from each pot per group
            queue = []
            sorted_pots = sorted(pots.keys())
            for pot_num in sorted_pots:
                queue.extend(pots[pot_num])
            queue.extend(unassigned)
        else:
            # Pure random
            random.shuffle(participants)
            queue = participants

        session = {
            "tournament_id": self.tournament_id,
            "organizer_id": self.user.id if self.user else None,
            "groups": group_names,
            "groups_info": groups_info,
            "group_size": group_size,
            "queue": queue,
            "assignments": {g: [] for g in group_names},
            "draw_log": [],           # ordered list of (player, group) for undo
            "next_group_index": 0,
            "drawn_count": 0,
            "total": len(queue),
            "fill_strategy": fill_strategy,
            "pot_config": pot_config,
            "prevent_region_clash": prevent_region_clash,
            "broadcast_config": broadcast_config,
            "org_constraint": org_constraint,
            "started_at": timezone.now().isoformat(),
            "finalized": False,
        }

        # ── Process locked seeds: pre-assign teams to specific slots ──
        if locked_seeds:
            locked_user_ids = set()
            for seed in locked_seeds:
                uid = seed.get("user_id")
                g_idx = seed.get("group_index", 0)
                if uid is None or g_idx is None:
                    continue
                if g_idx < 0 or g_idx >= len(group_names):
                    continue
                target_g = group_names[g_idx]
                # Find the player in queue and move to assignment
                for i, p in enumerate(session["queue"]):
                    if p.get("user_id") == uid:
                        player = session["queue"].pop(i)
                        session["assignments"][target_g].append(player)
                        session["draw_log"].append({"player": player, "group": target_g, "locked": True})
                        session["drawn_count"] += 1
                        locked_user_ids.add(uid)
                        break

            # Recompute group index after pre-placed seeds
            if locked_user_ids:
                self._recompute_group_index(session, fill_strategy)
                session["total"] = len(session["queue"]) + session["drawn_count"]

        await self._save_session(session)

        # Build queue data for spectator roulette pool and director queue
        queue_data = [
            {
                "user_id": p.get("user_id"),
                "registration_id": p.get("registration_id"),
                "name": p.get("name", ""),
                "display_name": p.get("display_name", p.get("name", "")),
                "avatar_url": p.get("avatar_url", ""),
            }
            for p in queue
        ]

        # Broadcast draw_session_open
        await self.channel_layer.group_send(self.group_name, {
            "type": "group_draw.session_open",
            "tournament_id": self.tournament_id,
            "total": session["total"],
            "groups": group_names,
            "group_size": group_size,
            "fill_strategy": fill_strategy,
            "pot_config": pot_config,
            "started_at": session["started_at"],
            "queue": queue_data,
            "broadcast_config": broadcast_config,
            "pre_assigned": session["assignments"] if session["drawn_count"] > 0 else None,
        })

    async def _handle_draw_next(self, content):
        """Pop next player from queue and assign to current group.

        Supports fill strategies:
        - round_robin: Slot 1 in all groups, then Slot 2, etc.
        - sequential: Fill Group A completely, then Group B, etc.
        """
        session = await self._get_session()
        if not session:
            await self.send_json({"type": "error", "message": "No active draw session."})
            return
        if not session["queue"]:
            await self.send_json({
                "type": "error",
                "message": "Draw queue is empty. Call finalize_draw.",
            })
            return

        # Pop next player
        player = session["queue"].pop(0)

        # Determine target group based on fill strategy
        fill_strategy = session.get("fill_strategy", "round_robin")
        target_group = self._pick_target_group(session, fill_strategy, player=player)

        if target_group is None:
            await self.send_json({"type": "error", "message": "All groups are full."})
            session["queue"].insert(0, player)
            await self._save_session(session)
            return

        session["assignments"][target_group].append(player)

        # Record in draw log for undo
        draw_log = session.setdefault("draw_log", [])
        draw_log.append({"player": player, "group": target_group})

        # Advance group pointer
        self._advance_group_index(session, fill_strategy)

        session["drawn_count"] += 1
        await self._save_session(session)

        # Broadcast player_drawn
        await self.channel_layer.group_send(self.group_name, {
            "type": "group_draw.player_drawn",
            "player": player,
            "assigned_group": target_group,
            "group_slot": len(session["assignments"][target_group]),
            "group_count": len(session["assignments"][target_group]),
            "drawn_count": session["drawn_count"],
            "remaining": len(session["queue"]),
            "total": session["total"],
        })

    async def _handle_draw_all(self, content):
        """Auto-draw all remaining players at once (fast-forward)."""
        session = await self._get_session()
        if not session:
            await self.send_json({"type": "error", "message": "No active draw session."})
            return
        if not session["queue"]:
            await self.send_json({"type": "error", "message": "Queue already empty."})
            return

        fill_strategy = session.get("fill_strategy", "round_robin")
        results = []

        while session["queue"]:
            player = session["queue"].pop(0)
            target_group = self._pick_target_group(session, fill_strategy, player=player)
            if target_group is None:
                session["queue"].insert(0, player)
                break
            session["assignments"][target_group].append(player)
            draw_log = session.setdefault("draw_log", [])
            draw_log.append({"player": player, "group": target_group})
            self._advance_group_index(session, fill_strategy)
            session["drawn_count"] += 1
            results.append({
                "player": player,
                "assigned_group": target_group,
                "group_slot": len(session["assignments"][target_group]),
            })

        await self._save_session(session)

        # Broadcast bulk draw result
        await self.channel_layer.group_send(self.group_name, {
            "type": "group_draw.bulk_drawn",
            "results": results,
            "drawn_count": session["drawn_count"],
            "remaining": len(session["queue"]),
            "total": session["total"],
        })

    async def _handle_undo_last(self, content):
        """Pull the last drawn player back into the front of the queue."""
        session = await self._get_session()
        if not session:
            await self.send_json({"type": "error", "message": "No active draw session."})
            return

        draw_log = session.get("draw_log", [])
        if not draw_log:
            await self.send_json({"type": "error", "message": "Nothing to undo."})
            return

        last_entry = draw_log.pop()
        player = last_entry["player"]
        group = last_entry["group"]

        # Remove player from group assignments
        group_players = session["assignments"].get(group, [])
        for i in range(len(group_players) - 1, -1, -1):
            if group_players[i].get("user_id") == player.get("user_id"):
                group_players.pop(i)
                break

        # Put player back at front of queue
        session["queue"].insert(0, player)
        session["drawn_count"] = max(0, session["drawn_count"] - 1)

        # Recompute group index
        fill_strategy = session.get("fill_strategy", "round_robin")
        self._recompute_group_index(session, fill_strategy)

        await self._save_session(session)

        # Broadcast undo event
        await self.channel_layer.group_send(self.group_name, {
            "type": "group_draw.draw_undone",
            "player": player,
            "from_group": group,
            "drawn_count": session["drawn_count"],
            "remaining": len(session["queue"]),
            "total": session["total"],
        })

    async def _handle_manual_assign(self, content):
        """Pick a specific player from the queue and assign to a chosen group.

        Sent by the Director in Manual Pick mode. Unlike ``draw_next`` which
        pops from the front of the queue and round-robins, this lets the
        organizer choose *who* goes *where*.  The broadcast event is the same
        ``player_drawn`` so Director and Spectator UIs behave uniformly.
        """
        session = await self._get_session()
        if not session:
            await self.send_json({"type": "error", "message": "No active draw session."})
            return

        player_user_id = content.get("player_user_id")
        target_group = content.get("target_group")

        if not player_user_id or not target_group:
            await self.send_json({
                "type": "error",
                "message": "manual_assign requires player_user_id and target_group.",
            })
            return

        if target_group not in session["groups"]:
            await self.send_json({"type": "error", "message": f"Invalid group: {target_group}"})
            return

        if len(session["assignments"].get(target_group, [])) >= session["group_size"]:
            await self.send_json({"type": "error", "message": f"{target_group} is already full."})
            return

        # Find and remove the player from the queue
        found_idx = None
        for i, p in enumerate(session["queue"]):
            if p.get("user_id") == player_user_id:
                found_idx = i
                break

        if found_idx is None:
            await self.send_json({"type": "error", "message": "Player not found in queue."})
            return

        player = session["queue"].pop(found_idx)
        session["assignments"][target_group].append(player)
        session["drawn_count"] += 1

        # Record in draw log for undo
        draw_log = session.setdefault("draw_log", [])
        draw_log.append({"player": player, "group": target_group})

        # Recompute next_group_index (find first non-full group)
        session["next_group_index"] = 0
        for i, g in enumerate(session["groups"]):
            if len(session["assignments"][g]) < session["group_size"]:
                session["next_group_index"] = i
                break
            session["next_group_index"] = i + 1

        await self._save_session(session)

        # Broadcast player_drawn (same event as draw_next for uniform UI)
        await self.channel_layer.group_send(self.group_name, {
            "type": "group_draw.player_drawn",
            "player": player,
            "assigned_group": target_group,
            "group_slot": len(session["assignments"][target_group]),
            "group_count": len(session["assignments"][target_group]),
            "drawn_count": session["drawn_count"],
            "remaining": len(session["queue"]),
            "total": session["total"],
            "manual": True,
        })

    async def _handle_assign_override(self, content):
        """Override group assignment for the last drawn player."""
        session = await self._get_session()
        if not session:
            await self.send_json({"type": "error", "message": "No active draw session."})
            return

        player_user_id = content.get("player_user_id")
        target_group = content.get("target_group")

        if target_group not in session["groups"]:
            await self.send_json({"type": "error", "message": f"Invalid group: {target_group}"})
            return

        if len(session["assignments"].get(target_group, [])) >= session["group_size"]:
            await self.send_json({"type": "error", "message": f"{target_group} is already full."})
            return

        # Find and remove player from current assignment
        found = False
        old_group = None
        for group_name, players in session["assignments"].items():
            for i, p in enumerate(players):
                if p.get("user_id") == player_user_id or p.get("registration_id") == player_user_id:
                    player = players.pop(i)
                    old_group = group_name
                    found = True
                    break
            if found:
                break

        if not found:
            await self.send_json({"type": "error", "message": "Player not found in assignments."})
            return

        # Assign to new group
        session["assignments"][target_group].append(player)

        # Recompute next_group_index (find first non-full group)
        session["next_group_index"] = 0
        for i, g in enumerate(session["groups"]):
            if len(session["assignments"][g]) < session["group_size"]:
                session["next_group_index"] = i
                break
            session["next_group_index"] = i + 1

        await self._save_session(session)

        # Broadcast override event
        await self.channel_layer.group_send(self.group_name, {
            "type": "group_draw.player_override",
            "player": player,
            "old_group": old_group,
            "new_group": target_group,
            "drawn_count": session["drawn_count"],
            "remaining": len(session["queue"]),
        })

    async def _handle_finalize_draw(self, content):
        """Commit draw assignments to database and generate group matches."""
        session = await self._get_session()
        if not session:
            await self.send_json({"type": "error", "message": "No active draw session."})
            return
        if session["queue"]:
            await self.send_json({
                "type": "error",
                "message": f"{len(session['queue'])} players still undrawn.",
            })
            return

        assignments = session["assignments"]

        # Compute tamper-evident hash
        canonical = json.dumps(assignments, sort_keys=True, ensure_ascii=True)
        seed_hash = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

        # Commit assignments to DB
        result = await self._commit_assignments(assignments, session.get("groups_info", []))

        # Mark session finalized and clean up
        session["finalized"] = True
        await self._delete_session()

        # Broadcast draw_complete
        # Build clean assignments for broadcast (just names, no internal IDs)
        clean_assignments = {}
        for group_name, players in assignments.items():
            clean_assignments[group_name] = [
                {"user_id": p.get("user_id"), "display_name": p.get("display_name", p.get("name", ""))}
                for p in players
            ]

        await self.channel_layer.group_send(self.group_name, {
            "type": "group_draw.draw_complete",
            "assignments": clean_assignments,
            "seed_hash": seed_hash,
            "total_assigned": result.get("total_assigned", 0),
            "total_matches": result.get("total_matches", 0),
        })

    async def _handle_abort_draw(self, content):
        """Discard the active draw session without committing."""
        await self._delete_session()
        reason = content.get("reason", "Organizer aborted the draw.")
        await self.channel_layer.group_send(self.group_name, {
            "type": "group_draw.draw_aborted",
            "reason": reason,
        })

    # ------------------------------------------------------------------ #
    # Channel layer event handlers
    # ------------------------------------------------------------------ #

    async def group_draw_session_open(self, event):
        await self.send_json({**event, "type": "draw_session_open"})

    async def group_draw_player_drawn(self, event):
        await self.send_json({**event, "type": "player_drawn"})

    async def group_draw_player_override(self, event):
        await self.send_json({**event, "type": "player_override"})

    async def group_draw_draw_complete(self, event):
        await self.send_json({**event, "type": "draw_complete"})

    async def group_draw_draw_aborted(self, event):
        await self.send_json({**event, "type": "draw_aborted"})

    async def group_draw_bulk_drawn(self, event):
        await self.send_json({**event, "type": "bulk_drawn"})

    async def group_draw_draw_undone(self, event):
        await self.send_json({**event, "type": "draw_undone"})

    async def group_draw_viewer_count(self, event):
        await self.send_json({**event, "type": "viewer_count"})

    # ------------------------------------------------------------------ #
    # Fill strategy helpers
    # ------------------------------------------------------------------ #

    def _pick_target_group(self, session, fill_strategy, player=None):
        """Return the next group name to receive a player, or None if all full.

        Supports org_constraint: if set, avoid placing more than N teams from
        the same organization into a single group (best-effort).
        """
        groups = session["groups"]
        assignments = session["assignments"]
        group_size = session["group_size"]
        org_constraint = session.get("org_constraint")

        # Determine player's org for constraint checking
        player_org_id = None
        if player and org_constraint:
            player_org_id = player.get("organization_id")

        def _org_ok(group_name):
            """Check if placing this player's org in group_name violates the constraint."""
            if not player_org_id or not org_constraint:
                return True
            max_per = org_constraint.get("max_per_group", 1)
            count = sum(
                1 for p in assignments.get(group_name, [])
                if p.get("organization_id") == player_org_id
            )
            return count < max_per

        if fill_strategy == "sequential":
            # Fill Group A completely, then Group B, etc.
            # First pass: respect org constraint
            if player_org_id:
                for g in groups:
                    if len(assignments.get(g, [])) < group_size and _org_ok(g):
                        return g
            # Fallback: ignore org constraint (best-effort)
            for g in groups:
                if len(assignments.get(g, [])) < group_size:
                    return g
            return None
        else:
            # round_robin: Slot 1 in all groups, then Slot 2, etc.
            idx = session.get("next_group_index", 0)
            if idx < len(groups):
                target = groups[idx]
                if len(assignments.get(target, [])) < group_size:
                    if _org_ok(target):
                        return target
                    # Org conflict: try other groups at the same fill level
                    if player_org_id:
                        target_count = len(assignments.get(target, []))
                        for g in groups:
                            if (len(assignments.get(g, [])) == target_count
                                    and len(assignments.get(g, [])) < group_size
                                    and _org_ok(g)):
                                return g
                    # Best-effort fallback: use the original target anyway
                    return target
            # Fallback: scan ALL groups for any non-full slot
            if player_org_id:
                for g in groups:
                    if len(assignments.get(g, [])) < group_size and _org_ok(g):
                        return g
            for g in groups:
                if len(assignments.get(g, [])) < group_size:
                    return g
            return None

    def _advance_group_index(self, session, fill_strategy):
        """Move the group pointer after an assignment."""
        if fill_strategy == "sequential":
            return  # sequential just fills first non-full
        # round_robin: advance to next group, wrap if needed
        groups = session["groups"]
        assignments = session["assignments"]
        idx = session.get("next_group_index", 0) + 1
        if idx >= len(groups):
            # Check if we need to wrap (next round of slots)
            counts = [len(assignments.get(g, [])) for g in groups]
            if len(set(counts)) <= 1:
                idx = 0  # start new round — all groups equal
            else:
                # Partial round: find first group with the minimum count
                min_count = min(counts)
                for i, g in enumerate(groups):
                    if len(assignments.get(g, [])) == min_count:
                        idx = i
                        break
        session["next_group_index"] = idx

    def _recompute_group_index(self, session, fill_strategy):
        """Recompute next_group_index after an undo or manual op."""
        groups = session["groups"]
        assignments = session["assignments"]
        group_size = session["group_size"]

        if fill_strategy == "sequential":
            session["next_group_index"] = 0
            for i, g in enumerate(groups):
                if len(assignments.get(g, [])) < group_size:
                    session["next_group_index"] = i
                    return
            session["next_group_index"] = len(groups)
        else:
            # Round-robin: find the group with fewest players that should go next
            min_count = min(len(assignments.get(g, [])) for g in groups) if groups else 0
            for i, g in enumerate(groups):
                if len(assignments.get(g, [])) == min_count:
                    session["next_group_index"] = i
                    return
            session["next_group_index"] = 0

    # ------------------------------------------------------------------ #
    # Redis session helpers
    # ------------------------------------------------------------------ #

    async def _get_session(self):
        return await database_sync_to_async(cache.get)(
            f"draw_session:{self.tournament_id}"
        )

    async def _save_session(self, session):
        await database_sync_to_async(cache.set)(
            f"draw_session:{self.tournament_id}", session, DRAW_SESSION_TTL
        )

    async def _delete_session(self):
        await database_sync_to_async(cache.delete)(
            f"draw_session:{self.tournament_id}"
        )

    def _sanitize_session(self, session):
        """Return a safe copy of session for client consumption."""
        # Include full queue data so spectator/director can build UI
        queue_data = [
            {
                "user_id": p.get("user_id"),
                "registration_id": p.get("registration_id"),
                "name": p.get("name", ""),
                "display_name": p.get("display_name", p.get("name", "")),
                "avatar_url": p.get("avatar_url", ""),
            }
            for p in session.get("queue", [])
        ]
        return {
            "tournament_id": session.get("tournament_id"),
            "groups": session.get("groups", []),
            "group_size": session.get("group_size", 4),
            "assignments": session.get("assignments", {}),
            "drawn_count": session.get("drawn_count", 0),
            "remaining": len(session.get("queue", [])),
            "total": session.get("total", 0),
            "started_at": session.get("started_at"),
            "finalized": session.get("finalized", False),
            "fill_strategy": session.get("fill_strategy", "round_robin"),
            "pot_config": session.get("pot_config"),
            "broadcast_config": session.get("broadcast_config"),
            "can_undo": len(session.get("draw_log", [])) > 0,
            "queue": queue_data,
        }

    # ------------------------------------------------------------------ #
    # Viewer count helpers
    # ------------------------------------------------------------------ #

    async def _incr_viewers(self, delta):
        """Increment or decrement the viewer count for this draw."""
        key = f"draw_viewers:{self.tournament_id}"
        try:
            current = await database_sync_to_async(cache.get)(key) or 0
            new_count = max(0, current + delta)
            await database_sync_to_async(cache.set)(key, new_count, DRAW_SESSION_TTL)
        except Exception:
            pass

    async def _broadcast_viewer_count(self):
        """Send current viewer count to all connected clients."""
        key = f"draw_viewers:{self.tournament_id}"
        try:
            count = await database_sync_to_async(cache.get)(key) or 0
            await self.channel_layer.group_send(self.group_name, {
                "type": "group_draw.viewer_count",
                "count": count,
            })
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Database helpers
    # ------------------------------------------------------------------ #

    @database_sync_to_async
    def _is_organizer(self):
        if not self.user or not self.user.is_authenticated:
            return False
        try:
            from apps.tournaments.models import Tournament
            tournament = Tournament.objects.get(id=self.tournament_id)

            # Direct owner, platform superuser, or staff — always allowed
            if (
                tournament.organizer_id == self.user.id
                or self.user.is_superuser
                or self.user.is_staff
            ):
                return True

            # Staff with manage_brackets capability via TournamentStaffAssignment
            from apps.tournaments.models.staffing import TournamentStaffAssignment
            return TournamentStaffAssignment.objects.filter(
                tournament=tournament,
                user=self.user,
                is_active=True,
                role__capabilities__has_key="manage_brackets",
            ).exists()
        except Exception:
            return False

    @database_sync_to_async
    def _get_confirmed_participants(self):
        """Get all confirmed registrations as a list of dicts."""
        from apps.tournaments.models import Registration
        registrations = Registration.objects.filter(
            tournament_id=self.tournament_id,
            status=Registration.CONFIRMED,
            is_deleted=False,
        ).select_related("user", "user__profile")

        participants = []
        for reg in registrations:
            name = ""
            user_id = None
            avatar_url = ""
            org_id = None  # Track organization for org-constraint feature
            if reg.user:
                name = reg.user.username
                user_id = reg.user.id
                try:
                    profile = getattr(reg.user, 'profile', None)
                    if profile:
                        avatar_url = profile.get_avatar_url() or ""
                except Exception:
                    pass
            elif reg.team_id:
                try:
                    from apps.organizations.models import Team
                    team = Team.objects.get(id=reg.team_id)
                    name = team.name
                    logo = team.get_effective_logo_url()
                    if hasattr(logo, 'url'):
                        avatar_url = logo.url
                    elif isinstance(logo, str):
                        avatar_url = logo
                    # Track organization for org-constraint feature
                    if hasattr(team, 'organization_id') and team.organization_id:
                        org_id = team.organization_id
                    else:
                        org_id = None
                except Exception:
                    name = f"Team #{reg.team_id}"
                    org_id = None
                user_id = reg.team_id
            else:
                name = f"Registration #{reg.registration_number}"
                user_id = reg.id

            participants.append({
                "registration_id": reg.id,
                "user_id": user_id,
                "name": name,
                "display_name": name,
                "avatar_url": avatar_url,
                "organization_id": org_id,
            })
        return participants

    @database_sync_to_async
    def _get_groups(self):
        """Get configured groups for this tournament."""
        from apps.tournaments.models.group import Group
        groups = Group.objects.filter(
            tournament_id=self.tournament_id,
            is_deleted=False,
        ).order_by("display_order", "name")

        return [
            {
                "id": g.id,
                "name": g.name.split()[-1] if " " in g.name else g.name,
                "full_name": g.name,
                "max_participants": g.max_participants,
                "advancement_count": g.advancement_count,
            }
            for g in groups
        ]

    @database_sync_to_async
    def _ensure_group_architecture(self, num_groups, group_size, advancement_count):
        """Create or update Group objects to match the requested architecture.

        Deletes excess groups, creates missing ones, updates existing.
        Also creates/updates the GroupStage model.
        """
        from apps.tournaments.models.group import Group, GroupStage

        existing = list(Group.objects.filter(
            tournament_id=self.tournament_id, is_deleted=False,
        ).order_by("display_order", "name"))

        letters = [chr(65 + i) for i in range(num_groups)]  # A, B, C, ...

        # Delete excess groups
        if len(existing) > num_groups:
            for g in existing[num_groups:]:
                g.is_deleted = True
                g.save(update_fields=["is_deleted"])
            existing = existing[:num_groups]

        # Update existing groups
        for i, g in enumerate(existing):
            g.name = f"Group {letters[i]}"
            g.display_order = i
            g.max_participants = group_size
            g.advancement_count = advancement_count
            g.save(update_fields=["name", "display_order", "max_participants", "advancement_count"])

        # Create missing groups
        for i in range(len(existing), num_groups):
            Group.objects.create(
                tournament_id=self.tournament_id,
                name=f"Group {letters[i]}",
                display_order=i,
                max_participants=group_size,
                advancement_count=advancement_count,
            )

        # Ensure GroupStage record
        gs, created = GroupStage.objects.get_or_create(
            tournament_id=self.tournament_id,
            defaults={
                "num_groups": num_groups,
                "group_size": group_size,
                "advancement_count_per_group": advancement_count,
            },
        )
        if not created:
            gs.num_groups = num_groups
            gs.group_size = group_size
            gs.advancement_count_per_group = advancement_count
            gs.save(update_fields=["num_groups", "group_size", "advancement_count_per_group"])

    @database_sync_to_async
    def _commit_assignments(self, assignments, groups_info):
        """Commit draw assignments to DB via GroupStageService."""
        from apps.tournaments.models.group import Group, GroupStanding
        from apps.tournaments.models import Tournament

        tournament = Tournament.objects.get(id=self.tournament_id)
        is_team = tournament.format_type in ("team", "team_based") if hasattr(tournament, "format_type") else False

        # Build group lookup: letter → Group object
        group_objs = {
            (g.name.split()[-1] if " " in g.name else g.name): g
            for g in Group.objects.filter(
                tournament_id=self.tournament_id, is_deleted=False
            )
        }

        total_assigned = 0
        for group_letter, players in assignments.items():
            group = group_objs.get(group_letter)
            if not group:
                logger.warning("Group %s not found for tournament %s", group_letter, self.tournament_id)
                continue
            for player in players:
                user_id = player.get("user_id")
                reg_id = player.get("registration_id")

                # Determine if this is a team or solo entry
                if is_team:
                    # For teams, user_id holds the team_id from _get_participants
                    exists = GroupStanding.objects.filter(
                        group=group, team_id=user_id, is_deleted=False
                    ).exists()
                    if exists:
                        continue
                    GroupStanding.objects.create(
                        group=group,
                        team_id=user_id,
                        rank=0,
                        matches_played=0,
                        matches_won=0,
                        matches_drawn=0,
                        matches_lost=0,
                        points=0,
                    )
                else:
                    exists = GroupStanding.objects.filter(
                        group=group, user_id=user_id, is_deleted=False
                    ).exists()
                    if exists:
                        continue
                    GroupStanding.objects.create(
                        group=group,
                        user_id=user_id,
                        rank=0,
                        matches_played=0,
                        matches_won=0,
                        matches_drawn=0,
                        matches_lost=0,
                        points=0,
                    )
                total_assigned += 1

        # Try to generate matches via the service
        total_matches = 0
        try:
            from apps.tournaments.services.group_stage_service import GroupStageService
            # Find group stage
            from apps.tournaments.models.stage import TournamentStage
            stage = TournamentStage.objects.filter(
                tournament_id=self.tournament_id,
                group_stage__isnull=False,
            ).first()
            if stage and hasattr(stage, "group_stage"):
                total_matches = GroupStageService.generate_group_matches(
                    stage_id=stage.group_stage.id
                )
        except Exception as e:
            logger.error("Failed to generate group matches: %s", e)

        # Store audit hash in group stage config
        try:
            from apps.tournaments.models.group import GroupStage
            gs = GroupStage.objects.filter(tournament_id=self.tournament_id).first()
            if gs:
                config = gs.config or {}
                config["draw_audit"] = {
                    "seed_hash": "sha256:" + hashlib.sha256(
                        json.dumps(assignments, sort_keys=True).encode()
                    ).hexdigest(),
                    "drawn_at": timezone.now().isoformat(),
                    "total_assigned": total_assigned,
                }
                gs.config = config
                gs.save(update_fields=["config"])
        except Exception as e:
            logger.error("Failed to save draw audit: %s", e)

        return {"total_assigned": total_assigned, "total_matches": total_matches}
