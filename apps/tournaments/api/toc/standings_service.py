"""
TOC Standings / Leaderboards Service — Sprint 28.

Live standings with rank, W/L/D record, points, tiebreakers,
multi-stage views, historical snapshots, and qualification tracking.
"""

import logging
from datetime import datetime
from typing import Optional
from django.db.models import Q, F, Sum, Count, Case, When, IntegerField, Value
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.match import Match

logger = logging.getLogger("toc.standings")


class TOCStandingsService:
    """All read operations for the Standings / Leaderboards tab."""

    @staticmethod
    def _sorted_group_rows(rows: list[dict]) -> list[dict]:
        def _num(value, default=0):
            try:
                return float(value)
            except (TypeError, ValueError):
                return float(default)

        return sorted(
            rows,
            key=lambda row: (
                -_num(row.get("points"), 0),
                -_num(row.get("wins"), 0),
                -_num(row.get("goal_difference"), 0),
                -_num(row.get("goals_for"), 0),
                str(row.get("name") or "").lower(),
            ),
        )

    @staticmethod
    def _build_name_map(team_ids, user_ids):
        """Batch-resolve team/user names in 1-2 queries instead of N."""
        name_map = {}
        if team_ids:
            from apps.organizations.models.team import Team as OrgTeam
            for tid, tname in OrgTeam.objects.filter(id__in=team_ids).values_list("id", "name"):
                name_map[("team", tid)] = tname or f"Team #{tid}"
        if user_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            for uid, uname in User.objects.filter(id__in=user_ids).values_list("id", "username"):
                name_map[("user", uid)] = uname or f"Player #{uid}"
        return name_map

    @staticmethod
    def _batch_recent_form(tournament, participant_ids, limit=5):
        """Batch-fetch recent form for all participants in 1 query."""
        if not participant_ids:
            return {}
        matches = (
            Match.objects.filter(
                tournament=tournament,
                state="completed",
                is_deleted=False,
            )
            .filter(Q(participant1_id__in=participant_ids) | Q(participant2_id__in=participant_ids))
            .order_by("-completed_at")
            .values("participant1_id", "participant2_id", "winner_id")
        )
        # Collect per-participant results (capped at limit)
        form_map = {pid: [] for pid in participant_ids}
        for m in matches:
            for pid in (m["participant1_id"], m["participant2_id"]):
                if pid in form_map and len(form_map[pid]) < limit:
                    if m["winner_id"] == pid:
                        form_map[pid].append("W")
                    elif m["winner_id"] is None:
                        form_map[pid].append("D")
                    else:
                        form_map[pid].append("L")
        return form_map

    @staticmethod
    def get_standings(tournament: Tournament, group_id: str = "", stage: str = "") -> dict:
        """Return full standings data for the tournament."""
        from apps.tournaments.models.group import Group, GroupStanding, GroupStage

        groups = Group.objects.filter(tournament=tournament, is_deleted=False).order_by("display_order", "name")
        if group_id:
            groups = groups.filter(id=group_id)

        stages = GroupStage.objects.filter(tournament=tournament).values("id", "name", "format", "state")
        stage_list = list(stages)

        # Collect all standings first to batch-resolve names and form
        all_standings_by_group = {}
        all_team_ids = set()
        all_user_ids = set()
        all_participant_ids = set()
        for g in groups:
            standings = list(
                GroupStanding.objects.filter(group=g, is_deleted=False)
                .order_by("rank")
                .values(
                    "id", "rank", "team_id", "user_id",
                    "matches_played", "matches_won", "matches_drawn", "matches_lost",
                    "points", "goals_for", "goals_against", "goal_difference",
                    "rounds_won", "rounds_lost", "round_difference",
                    "total_kills", "total_deaths", "placement_points",
                    "average_placement", "total_assists", "kda_ratio",
                    "total_score", "game_stats",
                    "is_advancing", "is_eliminated",
                )
            )
            all_standings_by_group[g] = standings
            for s in standings:
                if s["team_id"]:
                    all_team_ids.add(s["team_id"])
                    all_participant_ids.add(s["team_id"])
                elif s["user_id"]:
                    all_user_ids.add(s["user_id"])
                    all_participant_ids.add(s["user_id"])

        # Batch resolve names (1-2 queries) and form (1 query)
        name_map = TOCStandingsService._build_name_map(all_team_ids, all_user_ids)
        form_map = TOCStandingsService._batch_recent_form(tournament, all_participant_ids)

        group_standings = []
        for g, standings in all_standings_by_group.items():
            rows = []
            for s in standings:
                # Resolve display name from batch map
                if s["team_id"]:
                    name = name_map.get(("team", s["team_id"]), f"Team #{s['team_id']}")
                elif s["user_id"]:
                    name = name_map.get(("user", s["user_id"]), f"Player #{s['user_id']}")
                else:
                    name = "Unknown"

                pid = s["team_id"] or s["user_id"]
                win_rate = round(s["matches_won"] / s["matches_played"] * 100, 1) if s["matches_played"] > 0 else 0
                form = form_map.get(pid, [])

                rows.append({
                    "id": s["id"],
                    "rank": s["rank"],
                    "team_id": s["team_id"],
                    "user_id": s["user_id"],
                    "name": name,
                    "matches_played": s["matches_played"],
                    "wins": s["matches_won"],
                    "draws": s["matches_drawn"],
                    "losses": s["matches_lost"],
                    "points": s["points"],
                    "goals_for": s["goals_for"],
                    "goals_against": s["goals_against"],
                    "goal_difference": s["goal_difference"],
                    "rounds_won": s["rounds_won"],
                    "rounds_lost": s["rounds_lost"],
                    "round_difference": s["round_difference"],
                    "kills": s["total_kills"],
                    "deaths": s["total_deaths"],
                    "assists": s["total_assists"],
                    "kda": s["kda_ratio"],
                    "placement_points": s["placement_points"],
                    "avg_placement": s["average_placement"],
                    "total_score": s["total_score"],
                    "game_stats": s["game_stats"] or {},
                    "is_advancing": s["is_advancing"],
                    "is_eliminated": s["is_eliminated"],
                    "win_rate": win_rate,
                    "form": form,
                })

            qualify_count = g.advancement_count or 0
            config = g.config or {}

            rows = TOCStandingsService._sorted_group_rows(rows)
            for idx, row in enumerate(rows, start=1):
                row["rank"] = idx

            group_standings.append({
                "group_id": g.id,
                "group_name": g.name,
                "qualify_count": qualify_count,
                "points_system": config.get("points_system", {"win": 3, "draw": 1, "loss": 0}),
                "tiebreaker_rules": config.get("tiebreaker_rules", ["goal_difference", "goals_for", "head_to_head"]),
                "match_format": config.get("match_format", "bo1"),
                "standings": rows,
            })

        # Overall summary
        total_teams = sum(len(gs["standings"]) for gs in group_standings)
        total_advancing = sum(gs["qualify_count"] for gs in group_standings)
        match_agg = Match.objects.filter(tournament=tournament, is_deleted=False).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(state="completed")),
        )
        total_matches = match_agg["total"]
        completed_matches = match_agg["completed"]
        completion_pct = round(completed_matches / total_matches * 100) if total_matches > 0 else 0

        # Determine leader: team/player with highest points across all groups
        leader = "-"
        best_pts = -1
        for gs in group_standings:
            for row in gs["standings"]:
                if row["points"] > best_pts:
                    best_pts = row["points"]
                    leader = row["name"]

        # Current tournament stage
        current_stage = None
        if hasattr(tournament, 'get_current_stage'):
            current_stage = tournament.get_current_stage()

        # Knockout bracket standings (if bracket exists)
        bracket_standings = TOCStandingsService._get_bracket_standings(tournament)

        return {
            "groups": group_standings,
            "stages": stage_list,
            "current_stage": current_stage,
            "bracket_standings": bracket_standings,
            "summary": {
                "total_teams": total_teams,
                "total_groups": len(group_standings),
                "advancing": total_advancing,
                "total_matches": total_matches,
                "completed_matches": completed_matches,
                "completion_pct": completion_pct,
                "leader": leader,
            },
        }

    @staticmethod
    def _get_bracket_standings(tournament: Tournament) -> Optional[dict]:
        """Build knockout bracket standings from BracketNodes and their matches."""
        try:
            from apps.brackets.models import Bracket, BracketNode
        except ImportError:
            return None

        bracket = Bracket.objects.filter(tournament=tournament).first()
        if not bracket:
            return None

        nodes = (
            BracketNode.objects.filter(bracket=bracket)
            .select_related("match")
            .order_by("round_number", "match_number_in_round")
        )
        if not nodes.exists():
            return None

        is_team = tournament.participation_type != "solo"

        # Collect all participant IDs for name resolution
        pid_set = set()
        for n in nodes:
            if n.participant1_id:
                pid_set.add(n.participant1_id)
            if n.participant2_id:
                pid_set.add(n.participant2_id)

        name_map = {}
        if is_team and pid_set:
            try:
                from apps.organizations.models.team import Team as OrgTeam
                for t in OrgTeam.objects.filter(id__in=pid_set).only("id", "name"):
                    name_map[t.id] = t.name
            except Exception:
                pass
        elif pid_set:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            for u in User.objects.filter(id__in=pid_set).only("id", "username"):
                name_map[u.id] = u.username

        rounds = {}
        for n in nodes:
            rn = n.round_number or 0
            if rn not in rounds:
                rounds[rn] = []
            match_obj = getattr(n, "match", None)
            rounds[rn].append({
                "node_id": n.id,
                "round_number": rn,
                "match_number": n.match_number_in_round,
                "participant1_id": n.participant1_id,
                "participant1_name": name_map.get(n.participant1_id, "TBD") if n.participant1_id else "TBD",
                "participant2_id": n.participant2_id,
                "participant2_name": name_map.get(n.participant2_id, "TBD") if n.participant2_id else "TBD",
                "winner_id": n.winner_id,
                "winner_name": name_map.get(n.winner_id, "") if n.winner_id else "",
                "is_bye": n.is_bye,
                "match_id": match_obj.id if match_obj else None,
                "match_state": match_obj.state if match_obj else None,
                "round_label": bracket.get_round_name(rn),
            })

        total_nodes = sum(len(ms) for ms in rounds.values())
        completed_nodes = sum(
            1 for ms in rounds.values() for m in ms if m["winner_id"]
        )

        return {
            "bracket_id": bracket.id,
            "format": bracket.format,
            "total_rounds": bracket.total_rounds,
            "is_finalized": bracket.is_finalized,
            "rounds": [
                {"round": rn, "round_label": bracket.get_round_name(rn), "matches": ms}
                for rn, ms in sorted(rounds.items())
            ],
            "total_matches": total_nodes,
            "completed_matches": completed_nodes,
            "completion_pct": round(completed_nodes / total_nodes * 100) if total_nodes > 0 else 0,
        }

    @staticmethod
    def _get_recent_form(tournament, participant_id, is_team=True, limit=5):
        """Get last N match results as W/L/D form string."""
        if not participant_id:
            return []
        field = "participant1_id" if is_team else "participant1_id"
        matches = (
            Match.objects.filter(
                tournament=tournament,
                state="completed",
            )
            .filter(Q(participant1_id=participant_id) | Q(participant2_id=participant_id))
            .order_by("-completed_at")[:limit]
        )
        form = []
        for m in matches:
            if m.winner_id == participant_id:
                form.append("W")
            elif m.winner_id is None:
                form.append("D")
            else:
                form.append("L")
        return form

    @staticmethod
    def get_standings_snapshot(tournament: Tournament, round_number: int = 0) -> dict:
        """Get standings as they were after a specific round."""
        result = TOCStandingsService.get_standings(tournament)
        if round_number <= 0:
            return result

        # Filter form to only include matches up to requested round
        for group in result["groups"]:
            for row in group["standings"]:
                # Recalculate based on matches up to this round
                pid = row["team_id"] or row["user_id"]
                if not pid:
                    continue
                matches = Match.objects.filter(
                    tournament=tournament,
                    state="completed",
                    round_number__lte=round_number,
                ).filter(Q(participant1_id=pid) | Q(participant2_id=pid))

                wins = losses = draws = gf = ga = 0
                for m in matches:
                    is_p1 = m.participant1_id == pid
                    if m.winner_id == pid:
                        wins += 1
                    elif m.winner_id is None:
                        draws += 1
                    else:
                        losses += 1
                    if is_p1:
                        gf += m.participant1_score or 0
                        ga += m.participant2_score or 0
                    else:
                        gf += m.participant2_score or 0
                        ga += m.participant1_score or 0

                ps = group.get("points_system", {})
                pts = wins * ps.get("win", 3) + draws * ps.get("draw", 1) + losses * ps.get("loss", 0)
                row.update({
                    "matches_played": wins + draws + losses,
                    "wins": wins, "draws": draws, "losses": losses,
                    "points": pts,
                    "goals_for": gf, "goals_against": ga,
                    "goal_difference": gf - ga,
                })
            # Re-sort by points desc, then goal_difference desc
            group["standings"].sort(key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"]))
            for i, row in enumerate(group["standings"]):
                row["rank"] = i + 1

        return result

    @staticmethod
    def get_qualification_tracker(tournament: Tournament) -> dict:
        """Track which teams qualify from groups to playoffs."""
        from apps.tournaments.models.group import Group, GroupStanding

        groups = list(Group.objects.filter(tournament=tournament, is_deleted=False))

        # Collect all participant IDs across all groups for batch name resolution
        all_standings_by_group = {}
        all_team_ids = set()
        all_user_ids = set()
        for g in groups:
            standings = list(
                GroupStanding.objects.filter(group=g, is_deleted=False).order_by(
                    "-points", "-matches_won", "-goal_difference", "-goals_for", "id",
                ).values("id", "team_id", "user_id", "points", "is_advancing", "is_eliminated")
            )
            all_standings_by_group[g] = standings
            for s in standings:
                if s["team_id"]:
                    all_team_ids.add(s["team_id"])
                elif s["user_id"]:
                    all_user_ids.add(s["user_id"])

        name_map = TOCStandingsService._build_name_map(all_team_ids, all_user_ids)

        tracker = []
        for g in groups:
            standings = all_standings_by_group[g]
            adv_count = g.advancement_count or 0
            rows = []
            qualified = []
            for idx, s in enumerate(standings, start=1):
                if s["team_id"]:
                    name = name_map.get(("team", s["team_id"]), f"Team #{s['team_id']}")
                elif s["user_id"]:
                    name = name_map.get(("user", s["user_id"]), f"Player #{s['user_id']}")
                else:
                    name = "Unknown"

                qualifies = idx <= adv_count if adv_count > 0 else False
                rows.append({
                    "rank": idx,
                    "team_id": s["team_id"],
                    "user_id": s["user_id"],
                    "name": name,
                    "points": s["points"],
                    "qualifies": qualifies,
                    "is_advancing": s["is_advancing"],
                    "is_eliminated": s["is_eliminated"],
                })
                if qualifies or s["is_advancing"]:
                    qualified.append({"name": name, "rank": idx})

            tracker.append({
                "group_id": g.id,
                "group_name": g.name,
                "qualify_count": adv_count,
                "teams": rows,
                "qualified": qualified,
            })
        return {"groups": tracker}

    @staticmethod
    def export_standings(tournament: Tournament, format: str = "csv") -> list[dict]:
        """Export all standings as flat rows for CSV/image export."""
        data = TOCStandingsService.get_standings(tournament)
        rows = []
        for group in data["groups"]:
            for row in group["standings"]:
                rows.append({
                    "Group": group["group_name"],
                    "Rank": row["rank"],
                    "Team": row["name"],
                    "P": row["matches_played"],
                    "W": row["wins"],
                    "D": row["draws"],
                    "L": row["losses"],
                    "GF": row["goals_for"],
                    "GA": row["goals_against"],
                    "GD": row["goal_difference"],
                    "Pts": row["points"],
                    "Form": "".join(row["form"]),
                    "Status": "Advancing" if row["is_advancing"] else ("Eliminated" if row["is_eliminated"] else "Active"),
                })
        return rows
