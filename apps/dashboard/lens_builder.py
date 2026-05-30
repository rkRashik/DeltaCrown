"""
Performance Lens builder — Command Center dashboard.

Data priority:
  1. tournaments.Match (team_id, winner_id) → W/L/streak       [has real data]
  2. user_profile.GameProfile (rank_name, win_rate, matches_played) → rank display
  3. leaderboards.LeaderboardEntry (points, rank) → Crown Points [may be empty]

Solo game-passport lenses added for games with no team.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .helpers import _safe_model

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

logger = logging.getLogger(__name__)

TIERS = ["Rookie", "Challenger", "Elite", "Master", "Legend", "The Crown"]
TIER_COLORS = {
    "Rookie": "#94A3B8", "Challenger": "#6849E5", "Elite": "#3EA7FF",
    "Master": "#BF3868", "Legend": "#CFA75A", "The Crown": "#CFA75A",
}
GAME_GRADIENTS = {
    "valorant": ("#FF4655", "#6849E5"), "mlbb": ("#BF3868", "#6849E5"),
    "pubgm": ("#2ECC71", "#0A84FF"), "pubg mobile": ("#2ECC71", "#0A84FF"),
    "cs2": ("#CFA75A", "#75591F"), "freefire": ("#FF4D5E", "#CFA75A"),
    "free fire": ("#FF4D5E", "#CFA75A"), "efootball": ("#0A84FF", "#6849E5"),
    "ea-fc": ("#3EA7FF", "#0A84FF"), "codm": ("#FF4D5E", "#232936"),
    "rocketleague": ("#0A84FF", "#6849E5"), "dota2": ("#BF3868", "#232936"),
    "r6siege": ("#CFA75A", "#232936"),
}
FALLBACK_GRADIENTS = [
    ("#0A84FF", "#6849E5"), ("#BF3868", "#6849E5"), ("#2ECC71", "#0A84FF"),
    ("#CFA75A", "#75591F"), ("#FF4D5E", "#CFA75A"), ("#8470EE", "#6849E5"),
]


def _crest_gradient(slug: str, idx: int) -> tuple[str, str]:
    key = (slug or "").lower().replace("-", "").replace(" ", "")
    for k, v in GAME_GRADIENTS.items():
        if k.replace("-", "").replace(" ", "") in key or key in k.replace("-", "").replace(" ", ""):
            return v
    return FALLBACK_GRADIENTS[idx % len(FALLBACK_GRADIENTS)]


def _tier_for_points(pts: int) -> str:
    if pts >= 25000: return "The Crown"
    if pts >= 15000: return "Legend"
    if pts >= 8000:  return "Master"
    if pts >= 4000:  return "Elite"
    if pts >= 1500:  return "Challenger"
    return "Rookie"


def _next_tier(tier: str) -> str:
    idx = TIERS.index(tier) if tier in TIERS else 0
    return TIERS[idx + 1] if idx + 1 < len(TIERS) else tier


def _streak_label(n: int) -> str:
    if n == 0:  return "no active streak · warming up"
    if n >= 10: return f"{n} wins in a row · unstoppable"
    if n >= 5:  return f"{n} wins in a row · on fire"
    return f"{n} wins in a row"


def _fmt_pts(cp: int) -> str:
    return f"{cp/1000:.1f}k" if cp >= 1000 else str(cp)


def _default_rank(game_name: str) -> dict:
    return {
        "tier": "Rookie", "tier_color": TIER_COLORS["Rookie"],
        "pos": f"Unranked · {game_name}", "pts": "0", "cp": 0, "cp_delta": 0,
        "level": 1, "xp_current": 0, "xp_needed": 500, "xp_pct": 0,
        "next_tier": "Challenger",
        "promo_text": "1,500 CP to Challenger promotion",
        "promo_color": "var(--dc-fg-soft)",
        "game_rank": "",  # in-game rank name (e.g. Gold 1)
    }


def _match_stats_and_streak(user, team_id: int, Match) -> tuple[dict, dict]:
    """Compute W/L/D and current streak from tournaments.Match by team_id.

    Ordering: most-recent first (by id desc).
    Current streak: consecutive wins from the most recent match going back.
    Best streak: maximum consecutive wins found anywhere in history.
    """
    stats = {"win_rate": 0, "wins": 0, "losses": 0, "draws": 0}
    streak = {"current": 0, "label": _streak_label(0), "last_5": [], "best": 0}
    if not Match or not team_id:
        return stats, streak
    try:
        from django.db.models import Q
        matches = list(
            Match.objects.filter(
                Q(participant1_id=team_id) | Q(participant2_id=team_id),
                state__in=["completed", "finished", "done"],
                is_deleted=False,
            )
            .values("id", "participant1_id", "participant2_id", "winner_id")
            .order_by("-id")[:80]  # most recent first
        )
        wins = losses = draws = 0
        last_5: list[str] = []

        # Current streak: count from most-recent until first non-win
        cur_streak = 0
        tracking = True

        # Best streak: scan all matches (chronological within our window)
        run = 0
        best_streak = 0
        for m in reversed(matches):  # oldest-first for best-streak pass
            wid = m["winner_id"]
            if wid == team_id:
                run += 1
                best_streak = max(best_streak, run)
            else:
                run = 0

        for m in matches:  # most-recent first
            wid = m["winner_id"]
            p1 = m["participant1_id"]
            p2 = m["participant2_id"]
            if p1 != team_id and p2 != team_id:
                continue
            if wid is None:
                outcome = "d"; draws += 1
                if tracking: tracking = False
            elif wid == team_id:
                outcome = "w"; wins += 1
                if tracking: cur_streak += 1
            else:
                outcome = "l"; losses += 1
                if tracking: tracking = False

            if len(last_5) < 5:
                last_5.append(outcome)

        total = wins + losses + draws
        wr = round(wins / total * 100) if total else 0
        stats = {"win_rate": wr, "wins": wins, "losses": losses, "draws": draws}
        streak = {"current": cur_streak, "label": _streak_label(cur_streak), "last_5": last_5, "best": best_streak}
    except Exception:
        logger.debug("Lens: match stats failed for team %s", team_id, exc_info=True)
    return stats, streak


def _game_passport_stats(user, game_id: int, GameProfile) -> dict:
    """Get per-game stats from the game passport (win_rate, matches_played, rank_name)."""
    result: dict = {}
    if not GameProfile or not game_id:
        return result
    try:
        gp = GameProfile.objects.filter(user=user, game_id=game_id).first()
        if gp:
            result["win_rate_gp"] = float(gp.win_rate or 0)
            result["matches_played_gp"] = int(gp.matches_played or 0)
            result["rank_name"] = (gp.rank_name or "").strip()
            result["rank_tier"] = int(gp.rank_tier or 0)
    except Exception:
        logger.debug("Lens: GameProfile lookup failed for game %s", game_id, exc_info=True)
    return result


def _leaderboard_rank(user, team_id: int, game_slug: str, LeaderboardEntry) -> dict:
    """Get Crown Points and rank from LeaderboardEntry. Falls back to 0 if empty."""
    result = {"cp": 0, "rank_pos": None}
    if not LeaderboardEntry:
        return result
    try:
        entry = (
            LeaderboardEntry.objects.filter(team_id=team_id, is_active=True).order_by("rank").first()
            or LeaderboardEntry.objects.filter(player=user, game=game_slug, is_active=True).order_by("rank").first()
        )
        if entry:
            result["cp"] = int(getattr(entry, "points", 0) or 0)
            result["rank_pos"] = getattr(entry, "rank", None)
    except Exception:
        pass
    return result


def _build_rank_data(game_name: str, cp: int, rank_pos, gp_info: dict, wins: int = 0, losses: int = 0) -> dict:
    tier = _tier_for_points(cp)
    tier_color = TIER_COLORS.get(tier, "#94A3B8")
    next_t = _next_tier(tier)
    level = max(1, cp // 400)
    xp_current = cp % 400
    xp_needed = max(200, level * 500)
    xp_pct = min(100, int(xp_current / xp_needed * 100)) if xp_needed else 0
    remaining = max(0, xp_needed - xp_current)
    promo_txt = ("You have reached The Crown ♕" if tier == "The Crown"
                 else f"{remaining:,} XP to {next_t} promotion")
    promo_col = TIER_COLORS.get(next_t, "var(--dc-fg-soft)") if tier != "The Crown" else "#CFA75A"
    pos_str = f"#{rank_pos} · Bangladesh · {game_name}" if rank_pos else f"Unranked · {game_name}"
    game_rank = gp_info.get("rank_name", "")
    cp_pending = (cp == 0)  # flag: no leaderboard data yet
    return {
        "tier": tier, "tier_color": tier_color, "pos": pos_str,
        "pts": _fmt_pts(cp) if cp > 0 else "—", "cp": cp, "cp_delta": 0,
        "cp_pending": cp_pending,
        "wins": wins, "losses": losses,
        "level": level, "xp_current": xp_current, "xp_needed": xp_needed, "xp_pct": xp_pct,
        "next_tier": next_t, "promo_text": promo_txt, "promo_color": promo_col,
        "game_rank": game_rank,
    }


def _board_for_team(user, team_id: int, game_slug: str, game_name: str, tag: str, LeaderboardEntry) -> list[dict]:
    board: list[dict] = []
    if not LeaderboardEntry:
        return board
    try:
        qs = (
            LeaderboardEntry.objects.filter(game=game_slug, is_active=True).order_by("rank")[:4]
            if game_slug
            else LeaderboardEntry.objects.filter(team_id=team_id, is_active=True).order_by("rank")[:4]
        )
        for e in qs:
            is_me = (getattr(e, "player_id", None) == user.id or getattr(e, "team_id", None) == team_id)
            g1, g2 = ("#0A84FF", "#6849E5") if is_me else _crest_gradient(game_slug, 0)
            pts_raw = int(getattr(e, "points", 0) or 0)
            board.append({
                "r": f"#{e.rank}",
                "tag": str(getattr(e, "team__tag", None) or (tag if is_me else "TM"))[:4].upper(),
                "name": getattr(e, "team__name", None) or ("You" if is_me else f"Rank #{e.rank}"),
                "pts": _fmt_pts(pts_raw), "is_me": is_me, "g1": g1, "g2": g2,
            })
    except Exception:
        pass
    return board


def build_lenses(
    user: "AbstractUser",
    my_teams: list[dict],
    game_detail_map: dict,
    game_passports: list[dict] | None = None,
) -> list[dict]:
    lenses: list[dict] = []
    game_passports = game_passports or []

    Match = _safe_model("tournaments.Match")
    GameProfile = _safe_model("user_profile.GameProfile")
    LeaderboardEntry = _safe_model("leaderboards.LeaderboardEntry")

    covered_game_ids: set[int] = set()

    for idx, team in enumerate(my_teams[:6]):
        team_id = team["id"]
        game_id = team.get("game_id") or 0
        game_name = team.get("game_name", "")
        game_slug = team.get("game_slug", "")
        tag = (team.get("tag") or game_name[:3] or "TM").upper()[:4]
        is_primary = idx == 0

        # Stats from tournament matches (primary source)
        stats, streak = _match_stats_and_streak(user, team_id, Match)

        # Rank info from GameProfile (has in-game rank like "Gold_1")
        gp_info = _game_passport_stats(user, game_id, GameProfile)

        # If GameProfile has win_rate and MatchReport is empty, supplement
        if stats["wins"] == 0 and stats["losses"] == 0 and gp_info.get("win_rate_gp", 0) > 0:
            mp = gp_info.get("matches_played_gp", 0)
            wr = gp_info.get("win_rate_gp", 0)
            estimated_wins = round(wr / 100 * mp)
            estimated_losses = mp - estimated_wins
            stats = {"win_rate": round(wr), "wins": estimated_wins, "losses": estimated_losses, "draws": 0}

        # Crown Points from LeaderboardEntry (may be 0)
        lb = _leaderboard_rank(user, team_id, game_slug, LeaderboardEntry)
        rank_data = _build_rank_data(game_name, lb["cp"], lb["rank_pos"], gp_info,
                                     wins=stats["wins"], losses=stats["losses"])

        board = _board_for_team(user, team_id, game_slug, game_name, tag, LeaderboardEntry)
        g1, g2 = _crest_gradient(game_slug or game_name, idx)
        covered_game_ids.add(game_id)

        lenses.append({
            "id": f"team_{team_id}",
            "label": game_name or tag,
            "game_name": game_name,
            "game_slug": game_slug,
            "game_id": game_id,
            "game_icon": team.get("game_icon", ""),
            "crest": tag,
            "crest_g1": g1,
            "crest_g2": g2,
            "is_primary": is_primary,
            "is_solo": False,
            "rank": rank_data,
            "stats": stats,
            "streak": streak,
            "board": board,
        })

    # Solo lenses for game passport games with no team
    for gp_entry in game_passports:
        gp_game_name = gp_entry.get("game_name", "")
        gp_game_id = None
        # Try to match game_id from game_detail_map by name
        for gid, gd in game_detail_map.items():
            if gd.get("name", "").lower() == gp_game_name.lower():
                gp_game_id = gid
                break
        if gp_game_id and gp_game_id in covered_game_ids:
            continue
        if not gp_game_name:
            continue

        ign = gp_entry.get("ign", "") or gp_game_name[:3]
        crest = (ign[:3] or gp_game_name[:3]).upper()
        gp_slug = game_detail_map.get(gp_game_id, {}).get("slug", "") if gp_game_id else ""
        gp_info = _game_passport_stats(user, gp_game_id, GameProfile) if gp_game_id else {}
        lb = _leaderboard_rank(user, None, gp_slug, LeaderboardEntry)
        rank_data = _build_rank_data(gp_game_name, lb["cp"], lb["rank_pos"], gp_info)

        solo_stats = {"win_rate": round(gp_info.get("win_rate_gp", 0)), "wins": 0, "losses": 0, "draws": 0}
        mp = gp_info.get("matches_played_gp", 0)
        wr = gp_info.get("win_rate_gp", 0)
        if mp > 0 and wr > 0:
            w = round(wr / 100 * mp)
            solo_stats = {"win_rate": round(wr), "wins": w, "losses": mp - w, "draws": 0}

        g1, g2 = _crest_gradient(gp_slug or gp_game_name, len(lenses))
        if gp_game_id:
            covered_game_ids.add(gp_game_id)

        lenses.append({
            "id": f"solo_{(gp_slug or gp_game_name).lower().replace(' ', '_')}",
            "label": f"{gp_game_name} · Solo",
            "game_name": gp_game_name,
            "game_slug": gp_slug,
            "game_id": gp_game_id,
            "game_icon": gp_entry.get("game_icon", ""),
            "crest": crest,
            "crest_g1": g1,
            "crest_g2": g2,
            "is_primary": False,
            "is_solo": True,
            "ign": ign,
            "rank": rank_data,
            "stats": solo_stats,
            "streak": {"current": 0, "label": _streak_label(0), "last_5": [], "best": 0},
            "board": [],
        })

    return lenses
