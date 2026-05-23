"""Homepage live-data context builder.

Builds the dynamic data shape consumed by templates/home.html:
live ribbon, game posters, leaderboard, featured tournament, ticker, etc.

Cached for 10 minutes via apps.siteui.cache_safe.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.apps import apps
from django.db.models import Count, Sum
from django.utils import timezone

from apps.siteui.cache_safe import safe_cache_get, safe_cache_set


# Handoff JPG fallbacks for the 11-game poster grid. Keys cover common
# slug variants so we render an image even if the DB slug doesn't exactly
# match the handoff filename.
_POSTER_FALLBACK = {
    "valorant": "valorant.jpg",
    "cs2": "cs2.jpg", "csgo": "cs2.jpg", "counter-strike-2": "cs2.jpg",
    "dota2": "dota2.jpg", "dota-2": "dota2.jpg", "dota": "dota2.jpg",
    "mlbb": "mlbb.jpg", "mobile-legends": "mlbb.jpg",
    "mobile-legends-bang-bang": "mlbb.jpg",
    "pubg": "pubg.jpg", "pubg-mobile": "pubg.jpg", "pubgm": "pubg.jpg",
    "freefire": "freefire.jpg", "free-fire": "freefire.jpg", "ff": "freefire.jpg",
    "codm": "codm.jpg", "cod-mobile": "codm.jpg", "call-of-duty-mobile": "codm.jpg",
    "r6": "r6.jpg", "r6-siege": "r6.jpg", "rainbow-six-siege": "r6.jpg",
    "rocketleague": "rocketleague.jpg", "rocket-league": "rocketleague.jpg",
    "rl": "rocketleague.jpg",
    "fc26": "fc26.jpg", "ea-fc-26": "fc26.jpg", "fc-26": "fc26.jpg", "fc25": "fc26.jpg",
    "efootball": "efootball.jpg", "efootball-26": "efootball.jpg",
    "efootball-2026": "efootball.jpg", "pes": "efootball.jpg",
}


def _safe_model(app: str, name: str):
    try:
        return apps.get_model(app, name)
    except Exception:
        return None


def _img_url(field) -> str:
    if not field:
        return ""
    try:
        return field.url
    except Exception:
        return ""


def _poster_for_game(game) -> str:
    """Prefer card_image → banner → handoff JPG → icon → empty."""
    if game is None:
        return ""
    url = _img_url(getattr(game, "card_image", None))
    if url:
        return url
    url = _img_url(getattr(game, "banner", None))
    if url:
        return url
    slug = (getattr(game, "slug", "") or "").lower()
    fname = _POSTER_FALLBACK.get(slug)
    if fname:
        return f"/static/img/games/posters/{fname}"
    # Last resort: use the game icon as the poster (will be styled differently)
    url = _img_url(getattr(game, "icon", None))
    return url


def _icon_for_game(game) -> str:
    """Return the game icon URL (small logo for schedule/schedule strips)."""
    if game is None:
        return ""
    return _img_url(getattr(game, "icon", None))


def _color_for_game(game) -> str:
    """Return the game's primary_color for fallback card backgrounds."""
    if game is None:
        return "#1a1a2e"
    color = getattr(game, "primary_color", "") or ""
    return color if color.startswith("#") else "#1a1a2e"


def _format_compact(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.0f}K"
    return str(n)


def _short_time_ago(dt) -> str:
    if not dt:
        return ""
    delta = timezone.now() - dt
    if delta.days >= 1:
        return f"{delta.days}d"
    h = delta.seconds // 3600
    if h >= 1:
        return f"{h}h"
    m = max(1, delta.seconds // 60)
    return f"{m}m"


# --- Section builders -------------------------------------------------------

def _hero_stats() -> Dict[str, Any]:
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        players = User.objects.count()
    except Exception:
        players = 0

    Tournament = _safe_model("tournaments", "Tournament")
    tournaments_total = active = 0
    if Tournament is not None:
        try:
            tournaments_total = Tournament.objects.filter(
                is_deleted=False,
                status__in=["live", "registration_open", "published", "completed"],
            ).count()
            active = Tournament.objects.filter(
                is_deleted=False, status__in=["live", "registration_open"],
            ).count()
        except Exception:
            pass

    Team = _safe_model("organizations", "Team")
    teams = 0
    if Team is not None:
        try:
            teams = Team.objects.filter(status="ACTIVE").count()
        except Exception:
            pass

    active_prize_label = ""
    prize_lakh = "0"
    if Tournament is not None:
        try:
            agg = Tournament.objects.filter(
                is_deleted=False,
                status__in=["live", "registration_open"],
            ).aggregate(t=Sum("prize_pool"))
            total = agg.get("t") or Decimal("0")
            if total:
                total_f = float(total)
                lakh = total_f / 100_000
                if lakh >= 100:
                    prize_lakh = str(int(lakh))
                else:
                    prize_lakh = f"{lakh:.1f}".rstrip("0").rstrip(".")
                # Smart label for UI display
                if total_f >= 10_000_000:
                    active_prize_label = f"৳{total_f/1_000_000:.1f}M+"
                elif total_f >= 100_000:
                    active_prize_label = f"৳{int(lakh)}L+"
                elif total_f >= 1_000:
                    active_prize_label = f"৳{int(total_f/1000)}K+"
                else:
                    active_prize_label = f"৳{int(total_f):,}"
        except Exception:
            pass

    # Lifetime prizes paid (completed tournaments)
    lifetime_prize_label = ""
    if Tournament is not None:
        try:
            agg2 = Tournament.objects.filter(
                is_deleted=False,
                status__in=["completed", "archived"],
            ).aggregate(t=Sum("prize_pool"))
            paid = float(agg2.get("t") or 0)
            if paid >= 10_000_000:
                lifetime_prize_label = f"৳{paid/1_000_000:.1f}M"
            elif paid >= 100_000:
                lifetime_prize_label = f"৳{int(paid/100_000)}L"
            elif paid >= 1_000:
                lifetime_prize_label = f"৳{int(paid/1000)}K"
            elif paid > 0:
                lifetime_prize_label = f"৳{int(paid):,}"
        except Exception:
            pass

    # Active game count
    Game = _safe_model("games", "Game")
    games_count = 0
    if Game is not None:
        try:
            games_count = Game.objects.filter(is_active=True).count()
        except Exception:
            games_count = 0

    return {
        "players": players,
        "tournaments_total": tournaments_total,
        "tournaments_active": active,
        "teams": teams,
        "prize_lakh": prize_lakh or "0",
        "active_prize_label": active_prize_label,
        "lifetime_prize_label": lifetime_prize_label,
        "games_count": games_count or 11,
    }


def _get_participant_logo(match, slot: str) -> str:
    """Return a logo URL for a match participant (team or player)."""
    pid = getattr(match, f"participant{slot}_id", None)
    if not pid:
        return ""
    try:
        p_type = str(getattr(match.tournament, "participation_type", "") or "").lower()
        if p_type == "team":
            Team = _safe_model("organizations", "Team")
            if Team is not None:
                team = Team.objects.filter(pk=pid).only("logo").first()
                if team:
                    return _img_url(getattr(team, "logo", None))
        else:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(pk=pid).select_related("profile").first()
            if user:
                profile = getattr(user, "profile", None)
                return _img_url(getattr(profile, "avatar", None)) if profile else ""
    except Exception:
        pass
    return ""


def _batch_team_logos(team_ids: list) -> dict:
    """Return {team_id: logo_url} for a batch of team IDs in one query."""
    if not team_ids:
        return {}
    logos = {}
    try:
        Team = _safe_model("organizations", "Team")
        if Team is not None:
            for team in Team.objects.filter(pk__in=team_ids).only("id", "logo"):
                logos[team.id] = _img_url(getattr(team, "logo", None))
    except Exception:
        pass
    return logos


def _live_ribbon(limit: int = 5) -> List[Dict[str, Any]]:
    Match = _safe_model("tournaments", "Match")
    if Match is None:
        return []
    try:
        rows = list(
            Match.objects.filter(is_deleted=False, state="live")
            .select_related("tournament", "tournament__game")
            .order_by("scheduled_time", "id")[:limit]
        )
    except Exception:
        rows = []
    if not rows:
        return []

    # Batch-load team logos in one query (avoid N+1)
    team_ids = [
        m.participant1_id for m in rows
        if m.participant1_id and str(getattr(m.tournament, "participation_type", "")).lower() == "team"
    ] + [
        m.participant2_id for m in rows
        if m.participant2_id and str(getattr(m.tournament, "participation_type", "")).lower() == "team"
    ]
    logo_map = _batch_team_logos(list(set(team_ids)))

    out = []
    for m in rows:
        game = getattr(m.tournament, "game", None) if m.tournament else None
        game_name = (game.display_name or game.name or "").strip() if game else ""
        type_label = ""
        if game and hasattr(game, "get_game_type_display"):
            try:
                type_label = game.get_game_type_display() or ""
            except Exception:
                pass
        bo = getattr(m, "best_of", None)
        rn = getattr(m, "round_number", None)
        round_parts = []
        if isinstance(bo, int) and bo > 1:
            round_parts.append(f"BO{bo}")
        if rn:
            round_parts.append(f"Rd {rn}")
        round_label = " · ".join(round_parts) or (type_label or "In progress")

        p_type = str(getattr(m.tournament, "participation_type", "") or "").lower()
        a_logo = logo_map.get(m.participant1_id, "") if p_type == "team" else ""
        b_logo = logo_map.get(m.participant2_id, "") if p_type == "team" else ""

        out.append({
            "game": (game_name or "MATCH").upper(),
            "tag": (type_label or "Live").upper(),
            "team_a": (m.participant1_name or "Team A").strip(),
            "team_b": (m.participant2_name or "Team B").strip(),
            "team_a_logo": a_logo,
            "team_b_logo": b_logo,
            "score_a": m.participant1_score or 0,
            "score_b": m.participant2_score or 0,
            "map_label": round_label,
            "time_label": "LIVE",
            "match_url": (f"/tournaments/{m.tournament.slug}/" if m.tournament else "#"),
        })
    return out


def _recent_ribbon(limit: int = 4) -> List[Dict[str, Any]]:
    """Recent completed matches — fallback ribbon when no live matches exist."""
    Match = _safe_model("tournaments", "Match")
    if Match is None:
        return []
    try:
        rows = list(
            Match.objects.filter(is_deleted=False, state="completed")
            .select_related("tournament", "tournament__game")
            .order_by("-completed_at")[:limit]
        )
    except Exception:
        rows = []

    if not rows:
        return []

    # Batch logos — one DB query for all participants
    team_ids = [
        pid for m in rows
        for pid in (m.participant1_id, m.participant2_id)
        if pid and str(getattr(m.tournament, "participation_type", "")).lower() == "team"
    ]
    logo_map = _batch_team_logos(list(set(team_ids)))

    out = []
    for m in rows:
        game = getattr(m.tournament, "game", None) if m.tournament else None
        game_name = (game.display_name or game.name or "").strip() if game else ""
        a = m.participant1_score or 0
        b = m.participant2_score or 0
        winner = (m.participant1_name or "A") if a >= b else (m.participant2_name or "B")
        bo = getattr(m, "best_of", None)
        rn = getattr(m, "round_number", None)
        round_parts = []
        if isinstance(bo, int) and bo > 1:
            round_parts.append(f"BO{bo}")
        if rn:
            round_parts.append(f"Rd {rn}")
        round_label = " · ".join(round_parts) or "Completed"
        p_type = str(getattr(m.tournament, "participation_type", "") or "").lower()
        a_logo = logo_map.get(m.participant1_id, "") if p_type == "team" else ""
        b_logo = logo_map.get(m.participant2_id, "") if p_type == "team" else ""

        out.append({
            "game": (game_name or "MATCH").upper(),
            "tag": round_label.upper(),
            "team_a": (m.participant1_name or "Team A").strip(),
            "team_b": (m.participant2_name or "Team B").strip(),
            "team_a_logo": a_logo,
            "team_b_logo": b_logo,
            "score_a": a,
            "score_b": b,
            "map_label": _short_time_ago(getattr(m, "completed_at", None)) + " ago",
            "time_label": "RESULT",
            "match_url": (f"/tournaments/{m.tournament.slug}/" if m.tournament else "#"),
            "is_result": True,
            "winner": winner,
        })
    return out


def _game_posters(limit: int = 12) -> List[Dict[str, Any]]:
    Game = _safe_model("games", "Game")
    if Game is None:
        return []
    try:
        games = list(
            Game.objects.filter(is_active=True).order_by("name")[:limit]
        )
    except Exception:
        games = []

    out = []
    for idx, g in enumerate(games, start=1):
        platforms_list = list(g.platforms or [])
        type_label = ""
        if hasattr(g, "get_game_type_display"):
            try:
                type_label = g.get_game_type_display() or ""
            except Exception:
                type_label = ""
        meta_parts = [p for p in platforms_list if p]
        if type_label:
            meta_parts.append(type_label)
        out.append({
            "index": idx,
            "slug": g.slug,
            "name": g.display_name or g.name,
            "meta": " · ".join(meta_parts) or "Esports",
            "poster_url": _poster_for_game(g),
            "icon_url": _icon_for_game(g),
            "primary_color": _color_for_game(g),
            "url": f"/tournaments/?game={g.slug}",
            "live_count": 0,
            "event_count": 0,
        })

    # Annotate counts in 2 grouped queries.
    if out:
        slug_to_idx = {item["slug"]: i for i, item in enumerate(out)}
        Match = _safe_model("tournaments", "Match")
        if Match is not None:
            try:
                for row in (
                    Match.objects.filter(
                        is_deleted=False, state="live",
                        tournament__game__slug__in=list(slug_to_idx),
                    )
                    .values("tournament__game__slug")
                    .annotate(c=Count("id"))
                ):
                    i = slug_to_idx.get(row["tournament__game__slug"])
                    if i is not None:
                        out[i]["live_count"] = row["c"]
            except Exception:
                pass
        Tournament = _safe_model("tournaments", "Tournament")
        if Tournament is not None:
            try:
                for row in (
                    Tournament.objects.filter(
                        is_deleted=False,
                        status__in=["live", "registration_open", "published"],
                        game__slug__in=list(slug_to_idx),
                    )
                    .values("game__slug")
                    .annotate(c=Count("id"))
                ):
                    i = slug_to_idx.get(row["game__slug"])
                    if i is not None:
                        out[i]["event_count"] = row["c"]
            except Exception:
                pass
    return out


def _quick_jump(limit: int = 5) -> List[Dict[str, Any]]:
    games = _game_posters()
    games.sort(key=lambda g: (-(g.get("live_count") or 0),
                              -(g.get("event_count") or 0)))
    return games[:limit]


def _ticker_items(limit: int = 14) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    Match = _safe_model("tournaments", "Match")
    if Match is not None:
        try:
            for m in (
                Match.objects.filter(is_deleted=False, state="live")
                .select_related("tournament", "tournament__game")[:3]
            ):
                game = (
                    (m.tournament.game.display_name or m.tournament.game.name)
                    if m.tournament and m.tournament.game else "MATCH"
                )
                items.append({
                    "kind": "live",
                    "text": f"{game.upper()} — "
                            f"{m.participant1_name or 'A'} vs. {m.participant2_name or 'B'}",
                })
        except Exception:
            pass

    Tournament = _safe_model("tournaments", "Tournament")
    if Tournament is not None:
        try:
            for t in (
                Tournament.objects.filter(
                    is_deleted=False,
                    status__in=["live", "registration_open"],
                )
                .select_related("game")
                .order_by("-tournament_start")[:2]
            ):
                game = (
                    (t.game.display_name or t.game.name) if t.game else ""
                ).upper()
                items.append({
                    "kind": "tournament",
                    "text": f"{game} · {t.name}",
                })
        except Exception:
            pass

    Registration = _safe_model("tournaments", "Registration")
    if Registration is not None:
        try:
            since = timezone.now() - timedelta(hours=24)
            count = Registration.objects.filter(
                created_at__gte=since, is_deleted=False,
            ).count()
            if count > 0:
                items.append({
                    "kind": "signup",
                    "text": f"{count} new registrations · last 24h",
                })
        except Exception:
            pass

    # Pad with platform-truth fallbacks so the marquee never looks sparse.
    if len(items) < 8:
        fallbacks = [
            {"kind": "info", "text": "Crown Points · 6 tiers · ELO-scaled"},
            {"kind": "info", "text": "Escrow-backed reward operations"},
            {"kind": "info", "text": "Verified results · audit trail"},
            {"kind": "info", "text": "Showdown · Missions · Bounty · Dropzone"},
            {"kind": "info", "text": "11 titles · mobile to PC"},
            {"kind": "info", "text": "Disputes resolved · platform-managed"},
            {"kind": "info", "text": "Team HQ · scrims · tryouts · VOD review"},
            {"kind": "info", "text": "Bangladesh-first · built for esports"},
        ]
        for f in fallbacks:
            if len(items) >= limit:
                break
            items.append(f)
    return items[:limit]


def _featured_tournament() -> Optional[Dict[str, Any]]:
    Tournament = _safe_model("tournaments", "Tournament")
    Registration = _safe_model("tournaments", "Registration")
    if Tournament is None:
        return None

    t = None
    try:
        # Prefer featured tournaments starting soonest (gives game-balance over time).
        t = (
            Tournament.objects.filter(
                is_featured=True, is_deleted=False,
                status__in=["live", "registration_open", "published"],
            )
            .select_related("game", "organizer")
            .order_by("tournament_start")  # earliest first
            .first()
        )
        if t is None:
            t = (
                Tournament.objects.filter(
                    is_deleted=False, status="registration_open",
                )
                .select_related("game", "organizer")
                .order_by("tournament_start")
                .first()
            )
    except Exception:
        t = None
    if t is None:
        return None

    reg_count = 0
    if Registration is not None:
        try:
            reg_count = Registration.objects.filter(
                tournament=t, is_deleted=False,
                status__in=["pending", "payment_submitted", "confirmed"],
            ).count()
        except Exception:
            reg_count = 0
    max_slots = getattr(t, "max_participants", None)
    fill_pct = int((reg_count / max_slots) * 100) if max_slots else 0
    fill_pct = max(0, min(100, fill_pct))

    game = getattr(t, "game", None)
    poster = _img_url(getattr(t, "banner_image", None)) or _poster_for_game(game)

    fmt_label = ""
    if hasattr(t, "get_format_display"):
        try:
            fmt_label = t.get_format_display()
        except Exception:
            fmt_label = ""
    if not fmt_label:
        fmt_label = (getattr(t, "format", "") or "").replace("_", " ").title() or "Bracket"

    # Countdown deadline: registration_end first, then tournament_start as fallback.
    deadline = None
    deadline_label = ""
    if getattr(t, "registration_end", None):
        deadline = t.registration_end
        deadline_label = "Closes"
    elif getattr(t, "tournament_start", None):
        deadline = t.tournament_start
        deadline_label = "Starts"

    return {
        "name": t.name,
        "slug": t.slug,
        "game_name": ((game.display_name or game.name) if game else "").upper(),
        "format_label": fmt_label,
        "poster_url": poster,
        "prize_pool_label": (
            f"৳{int(t.prize_pool):,}" if t.prize_pool else "TBD"
        ),
        "slot_fill_pct": fill_pct,
        "slot_count": reg_count,
        "slot_max": max_slots or 0,
        "deadline_iso": deadline.isoformat() if deadline else "",
        "deadline_label": deadline_label,
        # Back-compat alias used by older template blocks.
        "reg_end_iso": deadline.isoformat() if deadline else "",
        "register_url": f"/tournaments/{t.slug}/register/",
        "view_url": f"/tournaments/{t.slug}/",
    }


def _upcoming_cards(limit: int = 4, exclude_id: Optional[int] = None) -> List[Dict[str, Any]]:
    Tournament = _safe_model("tournaments", "Tournament")
    Registration = _safe_model("tournaments", "Registration")
    if Tournament is None:
        return []
    try:
        qs = (
            Tournament.objects.filter(
                is_deleted=False,
                status__in=["registration_open", "live", "published"],
            )
            .select_related("game")
            .order_by("-tournament_start")
        )
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        rows = list(qs[:limit])
    except Exception:
        rows = []

    out = []
    for t in rows:
        reg_count = 0
        if Registration is not None:
            try:
                reg_count = Registration.objects.filter(
                    tournament=t, is_deleted=False,
                    status__in=["pending", "payment_submitted", "confirmed"],
                ).count()
            except Exception:
                reg_count = 0
        max_slots = getattr(t, "max_participants", None)
        fill_pct = int((reg_count / max_slots) * 100) if max_slots else 0
        fill_pct = max(0, min(100, fill_pct))
        game = t.game
        poster = _img_url(getattr(t, "banner_image", None)) or _poster_for_game(game)
        fmt_label = ""
        if hasattr(t, "get_format_display"):
            try:
                fmt_label = t.get_format_display()
            except Exception:
                fmt_label = ""
        if not fmt_label:
            fmt_label = (getattr(t, "format", "") or "").replace("_", " ").title() or "Bracket"

        out.append({
            "name": t.name,
            "slug": t.slug,
            "game_name": ((game.display_name or game.name) if game else "").upper(),
            "poster_url": poster,
            "prize_label": (
                f"৳{_format_compact(int(t.prize_pool))}"
                if t.prize_pool else "Free"
            ),
            "is_free": (not t.prize_pool),
            "is_live": t.status == "live",
            "format_label": fmt_label,
            "slot_count": reg_count,
            "slot_max": max_slots or 0,
            "slot_fill_pct": fill_pct,
            "scheduled": (
                t.tournament_start.strftime("%b %d") if t.tournament_start else ""
            ),
            "scheduled_time": (
                t.tournament_start.strftime("%H:%M") if t.tournament_start else ""
            ),
            "tournament_start_iso": (
                t.tournament_start.isoformat() if t.tournament_start else ""
            ),
            "url": f"/tournaments/{t.slug}/",
        })
    return out


# DB tier → display style. Labels match the public tier ladder defined in
# Documents/.../COMPETITIVE_SYSTEM_DESIGN.md (Rookie → The Crown).
_TIER_STYLE = {
    "THE_CROWN":  {"label": "The Crown", "color": "gold",   "is_crown": True},
    "LEGEND":     {"label": "Legend",    "color": "gold"},
    "MASTER":     {"label": "Master",    "color": "violet"},
    "ELITE":      {"label": "Elite",     "color": "violet"},
    "CHALLENGER": {"label": "Challenger","color": "teal"},
    "ROOKIE":     {"label": "Rookie",    "color": "teal"},
}


def _top_teams(limit: int = 7) -> List[Dict[str, Any]]:
    """Top teams with Crown Points + verified W-L from completed team matches."""
    TeamRanking = _safe_model("organizations", "TeamRanking")
    Game = _safe_model("games", "Game")
    Match = _safe_model("tournaments", "Match")
    if TeamRanking is None:
        return []
    try:
        rankings = list(
            TeamRanking.objects.select_related("team")
            .filter(team__status="ACTIVE")
            .order_by("-current_cp")[:limit]
        )
    except Exception:
        rankings = []

    team_ids = [r.team.id for r in rankings]

    game_names: Dict[int, str] = {}
    if Game is not None:
        try:
            game_ids = {r.team.game_id for r in rankings
                        if getattr(r.team, "game_id", None)}
            if game_ids:
                for g in Game.objects.filter(id__in=game_ids):
                    game_names[g.id] = (g.display_name or g.name).upper()
        except Exception:
            game_names = {}

    wins_map: Dict[int, int] = {}
    total_map: Dict[int, int] = {}
    if Match is not None and team_ids:
        try:
            base = Match.objects.filter(
                is_deleted=False,
                state="completed",
                tournament__participation_type="team",
            )
            # Wins: where this team is the winner.
            for row in (
                base.filter(winner_id__in=team_ids)
                .values("winner_id")
                .annotate(c=Count("id"))
            ):
                wins_map[row["winner_id"]] = row["c"]
            # Total appearances (either participant slot).
            for slot in ("participant1_id", "participant2_id"):
                for row in (
                    base.filter(**{f"{slot}__in": team_ids})
                    .values(slot)
                    .annotate(c=Count("id"))
                ):
                    total_map[row[slot]] = total_map.get(row[slot], 0) + row["c"]
        except Exception:
            wins_map = {}
            total_map = {}

    out = []
    for idx, r in enumerate(rankings, start=1):
        team = r.team
        game_name = game_names.get(getattr(team, "game_id", None), "")
        wins = wins_map.get(team.id, 0)
        total = total_map.get(team.id, 0)
        losses = max(0, total - wins)
        meta_parts = []
        if game_name:
            meta_parts.append(game_name)
        if total:
            meta_parts.append(f"{wins}W-{losses}L")
        change = getattr(r, "rank_change_7d", 0) or 0
        style = _TIER_STYLE.get(r.tier, {"label": r.tier.title(), "color": "teal"})
        rank_color = (
            "gold" if idx <= 2 else
            "violet" if idx <= 5 else
            "teal"
        )
        out.append({
            "rank": idx,
            "rank_label": f"#{idx:02d}",
            "rank_color": rank_color,
            "team_name": team.name,
            "team_logo": _img_url(getattr(team, "logo", None)),
            "team_url": f"/teams/{team.slug}/",
            "meta": " · ".join(meta_parts),
            "tier_label": style["label"],
            "tier_color": style["color"],
            "is_crown": style.get("is_crown", False),
            "cp": r.current_cp,
            "cp_label": f"{r.current_cp:,}",
            "change": change,
        })
    return out


def _player_spotlight() -> Optional[Dict[str, Any]]:
    """Pick a featured player.

    Strategy (best signal first):
      1. Captain of the team with the highest current_cp (true competitive flex).
      2. Captain of any team on a hot streak (`is_hot_streak=True`).
      3. None (template shows a stylised empty state).
    """
    TeamRanking = _safe_model("organizations", "TeamRanking")
    Team = _safe_model("organizations", "Team")
    if TeamRanking is None or Team is None:
        return None

    chosen_team = None
    try:
        # Highest CP first
        top = (
            TeamRanking.objects.select_related("team", "team__captain")
            .filter(team__status="ACTIVE", current_cp__gt=0)
            .order_by("-current_cp")
            .first()
        )
        if top and getattr(top.team, "captain_id", None):
            chosen_team = top.team
        else:
            # Fall back to a hot-streak team
            streak = (
                TeamRanking.objects.select_related("team", "team__captain")
                .filter(team__status="ACTIVE", is_hot_streak=True)
                .order_by("-streak_count")
                .first()
            )
            if streak and getattr(streak.team, "captain_id", None):
                chosen_team = streak.team
    except Exception:
        chosen_team = None

    if chosen_team is None:
        return None

    captain = getattr(chosen_team, "captain", None)
    if captain is None:
        return None

    profile = getattr(captain, "profile", None)
    display = ""
    avatar_url = ""
    username = getattr(captain, "username", "") or ""
    if profile is not None:
        display = (getattr(profile, "display_name", "") or "").strip()
        avatar_url = _img_url(getattr(profile, "avatar", None))
    if not display:
        display = username or "Featured player"

    initials = "".join(p[0] for p in display.split()[:2]).upper() or "DC"

    # Subtitle: team + game
    team_meta_parts = [chosen_team.name]
    Game = _safe_model("games", "Game")
    if Game is not None and getattr(chosen_team, "game_id", None):
        try:
            g = Game.objects.filter(pk=chosen_team.game_id).only("display_name", "name").first()
            if g:
                team_meta_parts.append((g.display_name or g.name).upper())
        except Exception:
            pass

    return {
        "display_name": display,
        "initials": initials,
        "subtitle": " · ".join(team_meta_parts),
        "profile_url": f"/players/{username}/" if username else "#",
        "team_url": f"/teams/{chosen_team.slug}/",
        "team_name": chosen_team.name,
        "avatar_url": avatar_url,
    }


def _activity_feed(limit: int = 6) -> List[Dict[str, str]]:
    """Live ecosystem signal: recent match wins, Showdowns, Bounties, Dropzones,
    Missions, and rank-ups (when audit data is available)."""
    items: List[Dict[str, Any]] = []
    now = timezone.now()

    # Match wins (tournament + Showdown match results)
    Match = _safe_model("tournaments", "Match")
    if Match is not None:
        try:
            for m in (
                Match.objects.filter(state="completed", is_deleted=False)
                .select_related("tournament")
                .order_by("-completed_at")[:3]
            ):
                a = m.participant1_score or 0
                b = m.participant2_score or 0
                p1 = m.participant1_name or "Team A"
                p2 = m.participant2_name or "Team B"
                winner = p1 if a >= b else p2
                loser = p2 if a >= b else p1
                items.append({
                    "kind": "WIN", "kind_color": "gold", "ts": getattr(m, "completed_at", now),
                    "highlight": winner,
                    "text": f"defeat {loser} {max(a,b)}-{min(a,b)}",
                })
        except Exception:
            pass

    # Showdown acceptances (Challenge)
    Challenge = _safe_model("competition", "Challenge")
    if Challenge is not None:
        try:
            for c in (
                Challenge.objects.filter(is_deleted=False, status__in=["accepted", "in_progress", "completed"])
                .order_by("-created_at")[:2]
            ):
                title = getattr(c, "title", None) or getattr(c, "name", None) or "Showdown"
                items.append({
                    "kind": "SHOWDOWN", "kind_color": "violet", "ts": getattr(c, "created_at", now),
                    "highlight": str(title)[:48],
                    "text": "accepted · escrow locked",
                })
        except Exception:
            pass

    # Bounty claims
    BountyClaim = _safe_model("competition", "BountyClaim")
    if BountyClaim is not None:
        try:
            for bc in (
                BountyClaim.objects.filter(is_deleted=False, status__in=["approved", "submitted"])
                .order_by("-created_at")[:2]
            ):
                items.append({
                    "kind": "BOUNTY", "kind_color": "gold", "ts": getattr(bc, "created_at", now),
                    "highlight": "Bounty",
                    "text": "claim submitted for review",
                })
        except Exception:
            pass

    # Dropzone lobby fills (settled or near-full)
    RoyaleLobby = _safe_model("royale", "RoyaleLobby")
    if RoyaleLobby is not None:
        try:
            for lb in (
                RoyaleLobby.objects.filter(status__in=["settled", "open", "locked"])
                .order_by("-created_at")[:2]
            ):
                name = getattr(lb, "name", None) or getattr(lb, "title", None) or "Dropzone"
                items.append({
                    "kind": "DROPZONE", "kind_color": "teal", "ts": getattr(lb, "created_at", now),
                    "highlight": str(name)[:48],
                    "text": "Dropzone scheduled",
                })
        except Exception:
            pass

    # Mission completions
    Enrollment = _safe_model("contracts", "ContractEnrollment")
    if Enrollment is not None:
        try:
            for e in (
                Enrollment.objects.filter(status__in=["complete", "completed"])
                .order_by("-id")[:2]
            ):
                items.append({
                    "kind": "MISSION", "kind_color": "teal", "ts": getattr(e, "created_at", now),
                    "highlight": "Mission",
                    "text": "completed · reward paid",
                })
        except Exception:
            pass

    # New registrations (aggregate) — useful even at low signal volume
    Registration = _safe_model("tournaments", "Registration")
    if Registration is not None:
        try:
            since = now - timedelta(hours=24)
            count = Registration.objects.filter(
                created_at__gte=since, is_deleted=False,
            ).count()
            if count > 0:
                items.append({
                    "kind": "JOIN", "kind_color": "teal", "ts": now,
                    "highlight": f"{count} players",
                    "text": "registered in last 24h",
                })
        except Exception:
            pass

    # Sort by timestamp desc, then format the time labels
    items.sort(key=lambda r: r.get("ts") or now, reverse=True)
    out = []
    for it in items[:limit]:
        out.append({
            "kind": it["kind"],
            "kind_color": it["kind_color"],
            "highlight": it["highlight"],
            "text": it["text"],
            "time_label": _short_time_ago(it.get("ts")),
        })

    if not out:
        out = [
            {"kind": "INFO", "kind_color": "teal",
             "highlight": "Quiet right now", "text": "be the first to compete today",
             "time_label": "—"},
        ]
    return out


# --- Static design copy ----------------------------------------------------

def _tier_rail() -> List[Dict[str, Any]]:
    """The 6-tier Crown Points ladder. Thresholds from COMPETITIVE_SYSTEM_DESIGN.md."""
    return [
        {"name": "Rookie",     "range": "0 – 100 CP",      "color": "teal",   "active": True},
        {"name": "Challenger", "range": "100 – 500 CP",    "color": "teal",   "active": True},
        {"name": "Elite",      "range": "500 – 2,000 CP",  "color": "violet", "active": True},
        {"name": "Master",     "range": "2K – 8K CP",      "color": "violet", "active": True},
        {"name": "Legend",     "range": "8K – 30K CP",     "color": "gold",   "active": False},
        {"name": "The Crown",  "range": "30K+ CP",         "color": "gold",   "active": False, "is_crown": True},
    ]


def _ecosystem_modules() -> List[Dict[str, str]]:
    """The eight platform pillars, each backed by a real Django app.

    Order is intentional — positions 1 and 6 have special visual treatment in
    the bento grid (feature 2×2 and DeltaCoin orbit animation respectively).
    """
    return [
        # Position 1 — bento-feature (2×2 hero cell)
        {"icon": "fa-trophy",          "name": "Tournaments",       "color": "violet",
         "blurb": "Single / double elim, Swiss, round-robin, group-to-playoff, and battle-royale. Brackets, check-in, match rooms, disputes, certificates — one engine."},
        # Positions 2–5 — regular cells (fills the 4 slots alongside the 2×2 feature)
        {"icon": "fa-shield-halved",   "name": "Teams & Orgs",      "color": "teal",
         "blurb": "Persistent organizations with captains, managers, coaches, and staff. Branding, recruitment, sponsors, and history that travel across games."},
        {"icon": "fa-id-card",         "name": "Player Identity",   "color": "gold",
         "blurb": "Not just a username. Verified profiles, Game Passports across 11 titles, match history, achievements, and reputation."},
        {"icon": "fa-chalkboard-user", "name": "Team HQ Training",  "color": "teal",
         "blurb": "Scrims, tryouts, practice sessions, and VOD review — kept separate from reward operations so improvement stays low-stakes."},
        {"icon": "fa-crosshairs",      "name": "Competitive Hub",   "color": "violet",
         "blurb": "Showdown, Missions, Bounty, and Dropzone — escrow-backed reward matches that live alongside tournaments."},
        # Position 6 — bento-coin (span-2 DeltaCoin animation cell)
        {"icon": "fa-coins",           "name": "DeltaCoin",         "color": "gold",
         "blurb": "Closed-loop utility currency. Earn by competing and progressing; spend on entries, services, and Crown Store items."},
        # Positions 7–8 — regular cells
        {"icon": "fa-chart-line",      "name": "Rankings & Seasons","color": "teal",
         "blurb": "Crown Points across 6 tiers. ELO-scaled, anti-farming protected, seasonal soft-resets, and verified-only results."},
        {"icon": "fa-bag-shopping",    "name": "Crown Store",       "color": "violet",
         "blurb": "Team merch, gear, digital products, and competitive entries. Orgs monetize directly; brands plug into a verified audience."},
    ]


def _competitive_pillars() -> List[Dict[str, str]]:
    """The 4 Competitive Hub pillars (Showdown / Missions / Bounty / Dropzone).

    Public language from Documents/Other Competitive Matches/Competitive_Ecosystem.md.
    All icons are FA 6.4 Free Solid.
    """
    return [
        {"icon": "fa-bolt", "color": "teal",
         "name": "Showdown",
         "tagline": "Head-to-head reward matches",
         "blurb": "Team vs team or 1v1 with escrow-locked entries. Built-in match room, structured result submission, and platform-managed dispute review.",
         "url": "/dashboard/competitive/"},
        {"icon": "fa-bullseye", "color": "violet",
         "name": "Missions",
         "tagline": "Solo skill challenges",
         "blurb": "Defined goals with a deadline — placement targets, streak goals, game-specific tasks. Complete to earn rewards and profile signals.",
         "url": "/dashboard/competitive/"},
        {"icon": "fa-flag-checkered", "color": "gold",
         "name": "Bounty",
         "tagline": "Open reward challenges",
         "blurb": "Teams post a skill-based bounty; eligible challengers compete to claim it. Rules, proof, and settlement all handled by the platform.",
         "url": "/dashboard/competitive/"},
        {"icon": "fa-parachute-box", "color": "teal",
         "name": "Dropzone",
         "tagline": "Battle-royale lobbies",
         "blurb": "Scheduled custom rooms for PUBG Mobile, Free Fire, and other BR formats. Slot reservation, credential reveal, placement and kill scoring.",
         "url": "/dashboard/competitive/"},
    ]


def _personas() -> List[Dict[str, Any]]:
    return [
        {
            "id": "p-players", "name": "Players", "color": "teal", "icon": "fa-user-astronaut",
            "headline_html": (
                'Build a <span class="brand-grad-text">verified competitive '
                'identity</span> that travels with you — every match, every '
                'result, every climb.'
            ),
            "bullets": [
                "Public profile with verified match history",
                "Game Passports across 11 titles",
                "Crown Points · Rookie → The Crown",
                "Free agency and team discovery",
                "Showdown, Missions, Bounty, Dropzone",
                "Reputation signals and achievements",
            ],
            "primary_cta": {"text": "Create your account", "url": "/account/signup/"},
            "secondary_cta": {"text": "Browse teams", "url": "/teams/"},
        },
        {
            "id": "p-teams", "name": "Teams", "color": "violet", "icon": "fa-shield-halved",
            "headline_html": (
                'Operate like a <span class="brand-grad-text">real '
                'organization</span> — rosters, staff, recruitment, training, history.'
            ),
            "bullets": [
                "Roles: captains, managers, coaches, staff",
                "Recruitment positions and join requests",
                "Team HQ — scrims, tryouts, VOD review",
                "Persistent identity across games",
                "Branding, kits, and Crown Store presence",
                "Tournament participation and rankings",
            ],
            "primary_cta": {"text": "Build a team", "url": "/teams/"},
            "secondary_cta": {"text": "Team tools", "url": "/teams/"},
        },
        {
            "id": "p-orgs", "name": "Organizers", "color": "gold", "icon": "fa-tower-broadcast",
            "headline_html": (
                'Run any format, any size — <span class="brand-grad-text">the '
                'engine handles brackets</span>, scheduling, disputes, and settlement.'
            ),
            "bullets": [
                "Single / double elim, Swiss, RR, group-to-playoff",
                "Eligibility, registration, and check-in",
                "Match rooms, results, and dispute review",
                "Escrow-backed reward operations",
                "Audit trail for every operator action",
                "Bangladesh-local payment awareness",
            ],
            "primary_cta": {"text": "Browse tournaments", "url": "/tournaments/"},
            "secondary_cta": {"text": "Read the platform docs", "url": "/about/"},
        },
        {
            "id": "p-sponsors", "name": "Sponsors", "color": "teal", "icon": "fa-handshake",
            "headline_html": (
                'Reach an audience of <span class="brand-grad-text">verified '
                'competitors</span>, not just impressions. Plug into teams, events, and storefronts.'
            ),
            "bullets": [
                "Team discovery and deal flow",
                "Event activation across 11 titles",
                "Verified competitive output metrics",
                "Co-branded prize pools",
                "Crown Store placement",
                "Long-term brand presence",
            ],
            "primary_cta": {"text": "Get in touch", "url": "/about/"},
            "secondary_cta": {"text": "About DeltaCrown", "url": "/about/"},
        },
    ]


def _comparison_rows() -> List[Dict[str, str]]:
    """Old way (Discord/spreadsheets/IOUs) vs DeltaCrown way.
    All icons are FA 6.4 Free Solid — no Pro icons used.
    """
    return [
        {
            "old_icon": "fa-comments",       "old_title": "Scattered group chats",
            "old_blurb": "Match arrangements live in Discord DMs and WhatsApp threads. Nothing is verified.",
            "new_icon": "fa-circle-check",   "new_title": "Verified match rooms",
            "new_blurb": "Every reward match runs in a structured room with eligibility, check-in, and proof.",
        },
        {
            "old_icon": "fa-user-slash",     "old_title": "Pay-later, ghost-later",
            "old_blurb": "No-shows, scams, IOUs after the match. The winner chases the loser for the prize.",
            "new_icon": "fa-lock",           "new_title": "Escrow-locked entries",
            "new_blurb": "Coins are locked before the match starts. Winners are paid by the platform, automatically.",
        },
        {
            "old_icon": "fa-fire",           "old_title": "Arguments over scores",
            "old_blurb": '"You disconnected first." "No, you did." Manual arguments with no neutral referee.',
            "new_icon": "fa-gavel",          "new_title": "Platform-managed disputes",
            "new_blurb": "Submit proof, the system locks the pot, and an admin reviews on a clear evidence trail.",
        },
        {
            "old_icon": "fa-eye-slash",      "old_title": "Results that don't count",
            "old_blurb": "Wins evaporate. There's no shared history, no rank, no proof when scouts come asking.",
            "new_icon": "fa-chart-line",     "new_title": "Crown Points & history",
            "new_blurb": "Verified results move your Crown Points and stack into a competitive résumé that travels.",
        },
    ]


def _testimonials() -> List[Dict[str, str]]:
    """Seeded scenario cards, not verified customer testimonials."""
    return [
        {
            "quote": "Check-in, result proof, and dispute notes live in one match room instead of scattered chat threads.",
            "name": "Organizer workflow",
            "context": "Weekend cup operations · CS2",
            "color": "teal",
        },
        {
            "quote": "Verified wins can move from screenshots into Crown Points, team history, and a profile record players can show.",
            "name": "Team captain flow",
            "context": "Ranking history · Valorant",
            "color": "violet",
        },
        {
            "quote": "Reward matches start with the rules, entry state, and settlement path visible before kickoff.",
            "name": "Roster manager use case",
            "context": "Reward match setup · eFootball",
            "color": "gold",
        },
    ]


def _roadmap_items() -> List[Dict[str, str]]:
    return [
        {"phase": "Live now", "tone": "live",
         "items": "Tournaments, Teams, Crown Points seasons, Showdown, Bounty, Missions, Dropzone, Crown Store, Game Passports."},
        {"phase": "Shipping next", "tone": "next",
         "items": "Public Dropzone detail pages, richer proof upload, dispute review UI, Team HQ training calendar, ranking momentum surfaces."},
        {"phase": "On the horizon", "tone": "soon",
         "items": "Sponsorship marketplace, deeper game-API verification, organizer monetisation tools, regional expansion outside Bangladesh."},
    ]


def _organizer_steps() -> List[Dict[str, str]]:
    return [
        {"icon": "fa-screwdriver-wrench", "title": "Create",
         "blurb": "Pick a format, set entry rules, prize pool, and schedule. Single elim to BR — the engine handles brackets."},
        {"icon": "fa-bullhorn", "title": "Invite",
         "blurb": "Open registration, run check-in, surface your event on the homepage and across team feeds."},
        {"icon": "fa-broadcast-tower", "title": "Run match day",
         "blurb": "Match rooms auto-spawn on schedule. Refs and mods watch the live queue. Disputes route to the review panel automatically."},
        {"icon": "fa-vault", "title": "Settle & payout",
         "blurb": "Verified result triggers escrow release. Platform handles transfers, receipts, and the full audit trail — no manual chasing."},
    ]


def _path_stages() -> List[Dict[str, str]]:
    return [
        {"num": "01", "color": "teal",   "icon": "fa-user-plus",
         "title": "Sign up & link your games",
         "blurb": "Create your DeltaCrown account, link game IDs through Game Passports, and set up your public profile.",
         "tag": "Free · ~2 minutes"},
        {"num": "02", "color": "violet", "icon": "fa-bolt",
         "title": "Compete to climb",
         "blurb": "Enter free or paid tournaments, accept Showdowns, take on Missions and Bounties. Every verified result moves your Crown Points.",
         "tag": "Crown Points · 6 tiers"},
        {"num": "03", "color": "gold",   "icon": "fa-users",
         "title": "Find a team",
         "blurb": "Join an active roster, scout free agents, or start your own organization. Recruitment, tryouts, and scrims happen in Team HQ.",
         "tag": "Recruitment · Tryouts"},
        {"num": "04", "color": "grad",   "icon": "fa-crown",
         "title": "Build a career",
         "blurb": "Stack verified results into a competitive résumé. Earn season rewards, attract sponsors, and operate like a real esports professional.",
         "tag": "The Crown awaits"},
    ]


# --- Public entry point ----------------------------------------------------

def get_homepage_extras(request=None) -> Dict[str, Any]:
    """Build the homepage live-data context (cached 10 minutes)."""
    cache_key = "homepage_extras"
    cached = safe_cache_get(cache_key)
    if cached is not None:
        return cached

    featured = _featured_tournament()
    exclude_id = None
    if featured:
        Tournament = _safe_model("tournaments", "Tournament")
        if Tournament is not None:
            try:
                exclude_id = Tournament.objects.filter(slug=featured["slug"]).values_list("id", flat=True).first()
            except Exception:
                exclude_id = None

    live = _live_ribbon()
    recent = _recent_ribbon() if not live else []
    context = {
        "v3": {
            "hero_stats": _hero_stats(),
            "live_ribbon": live,
            "recent_ribbon": recent,
            "any_live_url": live[0]["match_url"] if live else "/tournaments/?status=live",
            "quick_jump_games": _quick_jump(),
            "ticker_items": _ticker_items(),
            "featured_tournament": featured,
            "upcoming_tournaments": _upcoming_cards(exclude_id=exclude_id),
            "game_posters": _game_posters(),
            "ecosystem_modules": _ecosystem_modules(),
            "competitive_pillars": _competitive_pillars(),
            "tier_rail": _tier_rail(),
            "top_teams": _top_teams(),
            "player_spotlight": _player_spotlight(),
            "activity_feed": _activity_feed(),
            "comparison_rows": _comparison_rows(),
            "testimonials": _testimonials(),
            "roadmap": _roadmap_items(),
            "organizer_steps": _organizer_steps(),
            "personas": _personas(),
            "path_stages": _path_stages(),
            "platform": {
                "availability": "monitored",
                "payout_flow": "tracked",
                "review_flow": "admin-reviewed",
            },
        }
    }
    safe_cache_set(cache_key, context, 600)
    return context
