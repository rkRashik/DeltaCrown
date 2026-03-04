"""
TOC Teams / Roster Management Service — Sprint 28.

Roster overview, lock/unlock, lineup submissions, change log,
eligibility verification, captain assignment.

Data model (team tournaments):
- ONE Registration per registered team (registration.team_id = IntegerField → organizations.Team.id)
- registration.user is NULL for team registrations
- registration.lineup_snapshot = JSON list of player dicts (user_id, username, display_name,
  roster_slot, player_role, role, avatar, …)
- Game IDs (IGNs) live in apps.user_profile.models.GameProfile, NOT in lineup_snapshot
"""

import logging
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.registration import Registration

logger = logging.getLogger("toc.rosters")
User = get_user_model()

# Active statuses for participants in the tournament
ACTIVE_STATUSES = ["confirmed", "auto_approved"]

# Lazy-loaded optional models
def _get_org_team_model():
    try:
        from apps.organizations.models.team import Team as OrgTeam
        return OrgTeam
    except ImportError:
        return None

def _get_game_profile_model():
    try:
        from apps.user_profile.models import GameProfile
        return GameProfile
    except ImportError:
        return None


class TOCRostersService:
    """All read/write operations for the Rosters tab."""

    @staticmethod
    def get_rosters_dashboard(tournament: Tournament) -> dict:
        """Full roster management dashboard.

        For team tournaments: reads one Registration per team, extracts all
        players from lineup_snapshot, enriches with GameProfile IGNs and
        org Team metadata.  For solo tournaments: one registration per player.
        """
        config = tournament.config or {}
        roster_config = config.get("rosters", {})

        locked = roster_config.get("locked", False)
        lock_deadline = roster_config.get("lock_deadline", None)
        min_roster = roster_config.get("min_roster_size", 1)
        max_roster = roster_config.get("max_roster_size", 10)

        # ── Resolve tournament game display name for GameProfile lookup ──
        game_dn = ""
        try:
            game_dn = getattr(tournament.game, "display_name", "") or ""
        except Exception:
            pass

        # ── Batch-load GameProfile IGNs for this game ──
        user_ign_map: dict[int, str] = {}
        if game_dn:
            GameProfile = _get_game_profile_model()
            if GameProfile is not None:
                try:
                    qs = GameProfile.objects.filter(
                        game_display_name__iexact=game_dn
                    ).exclude(ign="").values("user_id", "ign")
                    user_ign_map = {row["user_id"]: row["ign"] for row in qs}
                except Exception:
                    pass

        # ── Fetch all active registrations ──
        registrations = Registration.objects.filter(
            tournament=tournament,
            status__in=ACTIVE_STATUSES,
        ).select_related("user")

        # ── Batch-load org Team metadata for all team_ids ──
        all_team_ids = list({r.team_id for r in registrations if r.team_id})
        team_meta: dict[int, dict] = {}
        if all_team_ids:
            OrgTeam = _get_org_team_model()
            if OrgTeam is not None:
                try:
                    for obj in OrgTeam.objects.filter(id__in=all_team_ids).only(
                        "id", "name", "tag", "logo", "primary_color"
                    ):
                        logo_url = ""
                        try:
                            logo_url = obj.logo.url if obj.logo else ""
                        except Exception:
                            pass
                        team_meta[obj.id] = {
                            "name": obj.name or f"Team {obj.id}",
                            "tag": getattr(obj, "tag", "") or "",
                            "logo_url": logo_url,
                            "primary_color": getattr(obj, "primary_color", "") or "",
                        }
                except Exception:
                    pass

        # ── Build team and solo player structures ──
        teams: dict[int, dict] = {}       # team_id -> team dict
        solo_players: list[dict] = []
        seen_team_ids: set[int] = set()   # deduplicate if multiple regs per team

        for reg in registrations:
            if reg.team_id:
                tid = reg.team_id
                meta = team_meta.get(tid, {})
                team_name = meta.get("name") or f"Team {tid}"

                if tid not in seen_team_ids:
                    seen_team_ids.add(tid)
                    teams[tid] = {
                        "team_id": tid,
                        "registration_id": reg.pk,
                        "team_name": team_name,
                        "tag": meta.get("tag", ""),
                        "logo_url": meta.get("logo_url", ""),
                        "primary_color": meta.get("primary_color", ""),
                        "checked_in": reg.checked_in,
                        "status": reg.status,
                        "captain_id": None,
                        "captain_name": "",
                        "players": [],
                        "roster_valid": True,
                        "registered_at": reg.registered_at.isoformat() if reg.registered_at else None,
                    }

                    # Build players from lineup_snapshot (authoritative player list)
                    snapshot = reg.lineup_snapshot or []
                    for entry in snapshot:
                        uid = entry.get("user_id")
                        slot = entry.get("roster_slot", "STARTER")
                        is_igl = (
                            entry.get("role") == "OWNER"
                            or bool(entry.get("is_igl"))
                            or bool(entry.get("is_tournament_captain"))
                        )
                        display_name = (
                            entry.get("display_name")
                            or entry.get("username")
                            or (f"User #{uid}" if uid else "Unknown")
                        )
                        ign = user_ign_map.get(uid, "") if uid else ""

                        player_dict = {
                            "user_id": uid,
                            "username": entry.get("username", ""),
                            "display_name": display_name,
                            "roster_slot": slot,
                            "player_role": entry.get("player_role", ""),
                            "is_igl": is_igl,
                            "game_id": ign,
                            "avatar": entry.get("avatar", ""),
                            "checked_in": reg.checked_in,  # team-level check-in
                        }
                        teams[tid]["players"].append(player_dict)

                        if is_igl and teams[tid]["captain_id"] is None:
                            teams[tid]["captain_id"] = uid
                            teams[tid]["captain_name"] = display_name

                else:
                    # Duplicate team registration — just update if it's more active
                    pass

            else:
                # Solo registration (individual tournament)
                solo_players.append({
                    "user_id": reg.user_id,
                    "username": reg.user.username if reg.user else "",
                    "display_name": (
                        getattr(reg.user, "display_name", None)
                        or (reg.user.username if reg.user else f"Reg #{reg.id}")
                    ),
                    "game_id": user_ign_map.get(reg.user_id, "")
                        if reg.user_id else (reg.registration_data or {}).get("game_id", ""),
                    "checked_in": reg.checked_in,
                    "registration_id": reg.pk,
                    "registered_at": reg.registered_at.isoformat() if reg.registered_at else None,
                })

        # ── Finalize team list ──
        team_list = list(teams.values())
        valid_count = 0
        for t in team_list:
            starters = sum(1 for p in t["players"] if p["roster_slot"] == "STARTER")
            total = len(t["players"])
            t["size"] = total
            t["starter_count"] = starters
            t["roster_valid"] = min_roster <= starters <= max_roster
            t["has_game_ids"] = all(p["game_id"] for p in t["players"] if p["roster_slot"] == "STARTER")
            if t["roster_valid"]:
                valid_count += 1

        # Roster change log
        change_log = roster_config.get("change_log", [])

        total_players = sum(t["size"] for t in team_list) + len(solo_players)
        players_with_game_ids = sum(
            1 for t in team_list for p in t["players"] if p.get("game_id")
        ) + sum(1 for s in solo_players if s.get("game_id"))

        return {
            "config": {
                "locked": locked,
                "lock_deadline": lock_deadline,
                "min_roster_size": min_roster,
                "max_roster_size": max_roster,
                "allow_subs": roster_config.get("allow_subs", True),
                "max_subs": roster_config.get("max_subs", 2),
            },
            "teams": team_list,
            "solo_players": solo_players,
            "change_log": change_log[-50:],
            "summary": {
                "total_teams": len(team_list),
                "total_solo": len(solo_players),
                "valid_rosters": valid_count,
                "invalid_rosters": len(team_list) - valid_count,
                "total_players": total_players,
                "players_with_game_ids": players_with_game_ids,
                "locked": locked,
            },
        }

    @staticmethod
    def lock_rosters(tournament: Tournament) -> dict:
        """Lock all rosters — no more changes allowed."""
        config = tournament.config or {}
        roster_config = config.get("rosters", {})
        roster_config["locked"] = True
        roster_config["locked_at"] = timezone.now().isoformat()
        config["rosters"] = roster_config

        log = roster_config.get("change_log", [])
        log.append({
            "action": "rosters_locked",
            "timestamp": timezone.now().isoformat(),
        })
        roster_config["change_log"] = log

        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"locked": True}

    @staticmethod
    def unlock_rosters(tournament: Tournament) -> dict:
        """Unlock rosters — allow changes again."""
        config = tournament.config or {}
        roster_config = config.get("rosters", {})
        roster_config["locked"] = False
        roster_config.pop("locked_at", None)
        config["rosters"] = roster_config

        log = roster_config.get("change_log", [])
        log.append({
            "action": "rosters_unlocked",
            "timestamp": timezone.now().isoformat(),
        })
        roster_config["change_log"] = log

        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"locked": False}

    @staticmethod
    def set_captain(tournament: Tournament, team_id: int, user_id: int) -> dict:
        """Assign a player as team captain using registration_data JSON."""
        config = tournament.config or {}
        roster_config = config.get("rosters", {})
        if roster_config.get("locked"):
            return {"error": "Rosters are locked"}

        regs = Registration.objects.filter(
            tournament=tournament, team_id=team_id,
            status__in=ACTIVE_STATUSES,
        )

        # Clear captain flag from all team members, set for new captain
        for reg in regs:
            data = reg.registration_data or {}
            data["is_captain"] = (reg.user_id == user_id)
            reg.registration_data = data
            reg.save(update_fields=["registration_data"])

        # Log
        log = roster_config.get("change_log", [])
        log.append({
            "action": "set_captain",
            "team_id": team_id,
            "user_id": user_id,
            "timestamp": timezone.now().isoformat(),
        })
        roster_config["change_log"] = log
        config["rosters"] = roster_config
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"captain_id": user_id, "team_id": team_id}

    @staticmethod
    def remove_player(tournament: Tournament, team_id: int, user_id: int) -> dict:
        """Remove a player from a team roster (cancel their registration)."""
        config = tournament.config or {}
        roster_config = config.get("rosters", {})
        if roster_config.get("locked"):
            return {"error": "Rosters are locked"}

        Registration.objects.filter(
            tournament=tournament, team_id=team_id, user_id=user_id,
        ).update(status="cancelled")

        log = roster_config.get("change_log", [])
        log.append({
            "action": "remove_player",
            "team_id": team_id,
            "user_id": user_id,
            "timestamp": timezone.now().isoformat(),
        })
        roster_config["change_log"] = log
        config["rosters"] = roster_config
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"removed": True}

    @staticmethod
    def add_player(tournament: Tournament, team_id: int, data: dict) -> dict:
        """Add a player to a team roster."""
        config = tournament.config or {}
        roster_config = config.get("rosters", {})
        if roster_config.get("locked"):
            return {"error": "Rosters are locked"}

        max_roster = roster_config.get("max_roster_size", 10)
        current_count = Registration.objects.filter(
            tournament=tournament, team_id=team_id,
            status__in=ACTIVE_STATUSES,
        ).count()

        if current_count >= max_roster:
            return {"error": f"Roster full ({max_roster} max)"}

        user_id = data.get("user_id")
        if not user_id:
            return {"error": "user_id required"}

        reg, created = Registration.objects.get_or_create(
            tournament=tournament, user_id=user_id,
            defaults={"team_id": team_id, "status": "confirmed"},
        )
        if not created:
            reg.team_id = team_id
            reg.status = "confirmed"
            reg.save(update_fields=["team_id", "status"])

        log = roster_config.get("change_log", [])
        log.append({
            "action": "add_player",
            "team_id": team_id,
            "user_id": user_id,
            "timestamp": timezone.now().isoformat(),
        })
        roster_config["change_log"] = log
        config["rosters"] = roster_config
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"added": True, "user_id": user_id}

    @staticmethod
    def update_roster_config(tournament: Tournament, data: dict) -> dict:
        """Update roster configuration."""
        config = tournament.config or {}
        roster_config = config.get("rosters", {})

        for key in ("min_roster_size", "max_roster_size", "allow_subs", "max_subs", "lock_deadline"):
            if key in data:
                roster_config[key] = data[key]

        config["rosters"] = roster_config
        tournament.config = config
        tournament.save(update_fields=["config"])
        return roster_config

    @staticmethod
    def submit_lineup(tournament: Tournament, team_id: int, data: dict) -> dict:
        """Submit a match-day lineup."""
        config = tournament.config or {}
        roster_config = config.get("rosters", {})
        lineups = roster_config.get("lineups", {})

        match_id = str(data.get("match_id", "current"))
        player_ids = data.get("player_ids", [])

        lineups[f"{team_id}_{match_id}"] = {
            "team_id": team_id,
            "match_id": match_id,
            "player_ids": player_ids,
            "submitted_at": timezone.now().isoformat(),
        }

        roster_config["lineups"] = lineups
        config["rosters"] = roster_config
        tournament.config = config
        tournament.save(update_fields=["config"])
        return lineups[f"{team_id}_{match_id}"]

    @staticmethod
    def check_eligibility(tournament: Tournament, team_id: int) -> dict:
        """Verify team roster eligibility."""
        config = tournament.config or {}
        roster_config = config.get("rosters", {})
        min_roster = roster_config.get("min_roster_size", 1)
        max_roster = roster_config.get("max_roster_size", 10)

        regs = Registration.objects.filter(
            tournament=tournament, team_id=team_id,
            status__in=ACTIVE_STATUSES,
        ).select_related("user")

        count = regs.count()
        issues = []

        if count < min_roster:
            issues.append(f"Roster too small: {count} < {min_roster}")
        if count > max_roster:
            issues.append(f"Roster too large: {count} > {max_roster}")

        # Check captain from registration_data
        has_captain = any(
            (r.registration_data or {}).get("is_captain", False)
            for r in regs
        )
        if not has_captain:
            issues.append("No captain assigned")

        return {
            "team_id": team_id,
            "eligible": len(issues) == 0,
            "roster_size": count,
            "issues": issues,
        }
