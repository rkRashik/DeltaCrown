"""
Group Draw Ceremony WebSocket Consumer

Interactive group draw ceremony with organizer control and public spectator broadcast.
Spec: docs/architecture/LIVE_DRAW_DIRECTOR.md

URL route: ws/tournament/<tournament_id>/group-draw/
Channel group: live_group_draw_{tournament_id}

Actions (organizer only):
    init_draw       — Initialize draw session with participant queue
    draw_next       — Draw next player from queue, assign to group
    assign_override — Move last-drawn player to a different group
    finalize_draw   — Commit assignments to DB, generate matches
    abort_draw      — Discard session without committing

Broadcast events:
    draw_session_open    — Session created, groups & total announced
    draw_session_snapshot— Full session state on reconnect
    player_drawn         — Single player drawn and assigned to group
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

        # Send current session snapshot (if draw is in progress)
        session = await self._get_session()
        if session:
            await self.send_json({
                "type": "draw_session_snapshot",
                "session": self._sanitize_session(session),
            })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ------------------------------------------------------------------ #
    # Action router
    # ------------------------------------------------------------------ #

    async def receive_json(self, content, **kwargs):
        action = content.get("action")
        handlers = {
            "init_draw": self._handle_init_draw,
            "draw_next": self._handle_draw_next,
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
        """Initialize a draw session. Builds participant queue and group grid."""
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

        # Shuffle queue randomly
        random.shuffle(participants)

        session = {
            "tournament_id": self.tournament_id,
            "organizer_id": self.user.id if self.user else None,
            "groups": group_names,
            "groups_info": groups_info,
            "group_size": group_size,
            "queue": participants,
            "assignments": {g: [] for g in group_names},
            "next_group_index": 0,
            "drawn_count": 0,
            "total": len(participants),
            "started_at": timezone.now().isoformat(),
            "finalized": False,
        }
        await self._save_session(session)

        # Broadcast draw_session_open
        await self.channel_layer.group_send(self.group_name, {
            "type": "group_draw.session_open",
            "tournament_id": self.tournament_id,
            "total": len(participants),
            "groups": group_names,
            "group_size": group_size,
            "started_at": session["started_at"],
        })

    async def _handle_draw_next(self, content):
        """Pop next player from queue and assign to current group."""
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

        # Determine target group (round-robin fill across groups)
        group_idx = session["next_group_index"]
        if group_idx >= len(session["groups"]):
            await self.send_json({"type": "error", "message": "All groups are full."})
            session["queue"].insert(0, player)  # Put player back
            await self._save_session(session)
            return

        target_group = session["groups"][group_idx]
        session["assignments"][target_group].append(player)

        # Advance group pointer if current group is full
        if len(session["assignments"][target_group]) >= session["group_size"]:
            session["next_group_index"] += 1

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
        }

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
        ).select_related("user")

        participants = []
        for reg in registrations:
            name = ""
            user_id = None
            if reg.user:
                name = reg.user.username
                user_id = reg.user.id
            elif reg.team_id:
                try:
                    from apps.organizations.models import Team
                    team = Team.objects.get(id=reg.team_id)
                    name = team.name
                except Exception:
                    name = f"Team #{reg.team_id}"
                user_id = reg.team_id
            else:
                name = f"Registration #{reg.registration_number}"
                user_id = reg.id

            participants.append({
                "registration_id": reg.id,
                "user_id": user_id,
                "name": name,
                "display_name": name,
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
            }
            for g in groups
        ]

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
