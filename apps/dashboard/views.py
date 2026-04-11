from __future__ import annotations
from datetime import datetime, timedelta
from typing import Iterable, Optional
from urllib.parse import quote

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Q, Count, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .forms import MyMatchesFilterForm
from .helpers import (
    _safe_model, _safe_qs, _safe_int,
    _build_game_lookup, _logo_url, _ts, _img_url, _avatar_fallback,
)
from .command_center import build_cc_data as _build_cc_data

from django.utils.timesince import timesince as _timesince

logger = __import__("logging").getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# MATCH FILTERING (legacy — kept for /my/matches/ route)
# ═══════════════════════════════════════════════════════════════════════════

def _filter_matches_for_user(user, form: MyMatchesFilterForm):
    if not hasattr(form, "cleaned_data") or form.cleaned_data is None:
        form.is_valid()
    if not hasattr(form, "cleaned_data"):
        form.cleaned_data = {}
    # Tournament Match model is unavailable in vNext
    return None, [], []


@login_required
def my_matches_view(request: HttpRequest) -> HttpResponse:
    form = MyMatchesFilterForm(request.GET or None)
    form.is_valid()
    context = {"form": form, "matches": [], "team_fields": [], "tchoices": []}
    return render(request, "dashboard/my_matches.html", context)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD — COMPREHENSIVE COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════════════


@login_required
def dashboard_index(request: HttpRequest) -> HttpResponse:
    """
    Comprehensive Dashboard — the user's command center.

    Pulls data from every major subsystem with graceful degradation:
    teams, invites, tournaments, matches, leaderboards, economy,
    notifications, profile, achievements.
    """
    from apps.organizations.models import Team
    from apps.organizations.models.membership import TeamMembership
    from apps.organizations.models.team_invite import TeamInvite
    from apps.organizations.choices import MembershipStatus
    from apps.notifications.models import Notification

    user = request.user
    now = timezone.now()
    game_map = _build_game_lookup()

    # Detailed game lookup with icons/colors
    game_detail_map = {}
    try:
        Game = _safe_model("games.Game")
        if Game:
            for g in Game.objects.all().only("id", "name", "icon", "logo", "primary_color", "short_code"):
                game_detail_map[g.id] = {
                    "name": g.name,
                    "icon": _img_url(g, "icon"),
                    "logo": _img_url(g, "logo"),
                    "color": getattr(g, "primary_color", "#6366F1") or "#6366F1",
                    "code": getattr(g, "short_code", "") or "",
                }
    except Exception:
        pass

    # ── 1. USER PROFILE ─────────────────────────────────────────────────
    profile = None
    profile_data = {}
    try:
        Profile = _safe_model("user_profile.UserProfile")
        if Profile:
            profile = Profile.objects.filter(user=user).first()
        if profile:
            avatar = None
            banner = None
            try:
                avatar = profile.avatar.url if profile.avatar else None
            except Exception:
                pass
            try:
                banner = profile.banner.url if profile.banner else None
            except Exception:
                pass
            profile_data = {
                "display_name": getattr(profile, "display_name", "") or user.get_full_name() or user.username,
                "avatar_url": avatar,
                "banner_url": banner,
                "slug": getattr(profile, "slug", user.username),
                "lft_status": getattr(profile, "lft_status", None) or getattr(profile, "LFTStatus", None),
                "kyc_status": getattr(profile, "kyc_status", ""),
                "reputation_score": getattr(profile, "reputation_score", 100),
                "level": getattr(profile, "level", 1),
                "xp": getattr(profile, "xp", 0),
            }
        else:
            profile_data = {
                "display_name": user.get_full_name() or user.username,
                "avatar_url": None,
                "slug": user.username,
                "lft_status": None,
                "kyc_status": "",
            }
    except Exception:
        profile_data = {
            "display_name": user.get_full_name() or user.username,
            "avatar_url": None,
            "slug": user.username,
            "lft_status": None,
            "kyc_status": "",
        }

    # ── 2. MY TEAMS ─────────────────────────────────────────────────────
    my_teams = []
    try:
        memberships = (
            TeamMembership.objects.filter(user=user, status=MembershipStatus.ACTIVE)
            .select_related("team", "team__organization")
            .order_by("-joined_at")[:8]
        )
        for m in memberships:
            t = m.team
            member_ct = _safe_int(
                lambda: TeamMembership.objects.filter(team=t, status=MembershipStatus.ACTIVE).count()
            )
            # Pending join request count for admins/owners
            jr_count = 0
            if m.role in ('OWNER', 'MANAGER'):
                try:
                    from apps.organizations.models.join_request import TeamJoinRequest
                    jr_count = TeamJoinRequest.objects.filter(
                        team=t,
                        status__in=['PENDING', 'TRYOUT_SCHEDULED', 'TRYOUT_COMPLETED', 'OFFER_SENT'],
                    ).count()
                except Exception:
                    pass
            # Organization association
            org_obj = getattr(t, 'organization', None)
            team_org = None
            if org_obj:
                team_org = {
                    "name": org_obj.name,
                    "slug": getattr(org_obj, "slug", ""),
                    "logo": _img_url(org_obj),
                    "verified": getattr(org_obj, "is_verified", False),
                }
            gd = game_detail_map.get(t.game_id, {})
            my_teams.append({
                "id": t.id, "name": t.name, "slug": t.slug,
                "logo_url": _img_url(t),
                "role": m.role,
                "game_name": game_map.get(t.game_id, ""),
                "game_icon": gd.get("icon", ""),
                "game_color": gd.get("color", "#6366F1"),
                "member_count": member_ct,
                "tag": getattr(t, "tag", "") or "",
                "status": getattr(t, "status", ""),
                "pending_jr_count": jr_count,
                "org": team_org,
            })
    except Exception:
        logger.debug("Dashboard: teams query failed", exc_info=True)

    # Batch-fetch roster data for team cards
    try:
        if my_teams:
            team_id_list = [t["id"] for t in my_teams]
            roster_qs = (
                TeamMembership.objects.filter(
                    team_id__in=team_id_list,
                    status=MembershipStatus.ACTIVE,
                )
                .select_related("user")
                .order_by("team_id", "joined_at")
            )

            # Batch-load user avatars
            member_user_ids = [rm.user_id for rm in roster_qs]
            Profile = _safe_model("user_profile.UserProfile")
            avatar_map = {}
            if Profile and member_user_ids:
                for p in Profile.objects.filter(user_id__in=member_user_ids).only("user_id", "avatar"):
                    avatar_map[p.user_id] = _img_url(p, "avatar")

            roster_data = {}
            for rm in roster_qs:
                lst = roster_data.setdefault(rm.team_id, [])
                if len(lst) < 5:
                    uname = rm.user.username
                    initials = ''.join([w[0] for w in uname.split()[:2]]).upper() or 'U'
                    avatar = avatar_map.get(rm.user_id) or (
                        'https://ui-avatars.com/api/?name=%s&background=222&color=fff&size=64' % initials
                    )
                    lst.append({
                        "name": "You" if rm.user_id == user.id else uname,
                        "isCaptain": rm.role in ("OWNER", "CAPTAIN"),
                        "avatar": avatar,
                        "role": rm.role,
                    })
            for t in my_teams:
                t["roster"] = roster_data.get(t["id"], [])
    except Exception:
        logger.debug("Dashboard: roster query failed", exc_info=True)

    # ── 3. PENDING INVITES ──────────────────────────────────────────────
    pending_invites = []
    try:
        invites = (
            TeamInvite.objects.filter(
                invited_user=user, status="PENDING", expires_at__gt=now,
            )
            .select_related("team", "inviter")
            .order_by("-created_at")[:5]
        )
        for inv in invites:
            pending_invites.append({
                "id": inv.id,
                "team_name": inv.team.name,
                "team_slug": inv.team.slug,
                "team_logo": _logo_url(inv.team),
                "role": inv.role,
                "inviter": inv.inviter.username if inv.inviter else "Unknown",
                "created_at": inv.created_at,
                "expires_at": inv.expires_at,
            })
    except Exception:
        logger.debug("Dashboard: invites query failed", exc_info=True)

    # ── 4. RECENT MATCHES (competition.MatchReport) ─────────────────────
    recent_matches = []
    try:
        MatchReport = _safe_model("competition.MatchReport")
        if MatchReport:
            team_ids = [t["id"] for t in my_teams]
            if team_ids:
                reports = (
                    MatchReport.objects.filter(
                        Q(team1_id__in=team_ids) | Q(team2_id__in=team_ids)
                    )
                    .select_related("team1", "team2")
                    .order_by("-created_at")[:6]
                )
                for r in reports:
                    t1_name = getattr(r.team1, "name", "TBD") if r.team1 else "TBD"
                    t2_name = getattr(r.team2, "name", "TBD") if r.team2 else "TBD"
                    recent_matches.append({
                        "id": r.id,
                        "team1_name": t1_name,
                        "team2_name": t2_name,
                        "result": getattr(r, "result", ""),
                        "match_type": getattr(r, "match_type", ""),
                        "game_name": game_map.get(getattr(r, "game_id", None), ""),
                        "game_icon": game_detail_map.get(getattr(r, "game_id", None), {}).get("icon", ""),
                        "created_at": r.created_at,
                        "score_team1": getattr(r, "score_team1", None),
                        "score_team2": getattr(r, "score_team2", None),
                    })
    except Exception:
        logger.debug("Dashboard: matches query failed", exc_info=True)

    # ── 5. MATCH STATS (W / L / D) ──────────────────────────────────────
    match_stats = {"wins": 0, "losses": 0, "draws": 0, "total": 0, "win_rate": 0}
    try:
        MatchReport = _safe_model("competition.MatchReport")
        if MatchReport and my_teams:
            team_ids = [t["id"] for t in my_teams]
            all_reports = MatchReport.objects.filter(
                Q(team1_id__in=team_ids) | Q(team2_id__in=team_ids)
            )
            for r in all_reports:
                result = str(getattr(r, "result", "")).upper()
                is_team1 = r.team1_id in team_ids
                if result == "WIN":
                    if is_team1:
                        match_stats["wins"] += 1
                    else:
                        match_stats["losses"] += 1
                elif result == "LOSS":
                    if is_team1:
                        match_stats["losses"] += 1
                    else:
                        match_stats["wins"] += 1
                elif result == "DRAW":
                    match_stats["draws"] += 1
                match_stats["total"] += 1
            if match_stats["total"] > 0:
                match_stats["win_rate"] = round(
                    match_stats["wins"] / match_stats["total"] * 100
                )
    except Exception:
        logger.debug("Dashboard: match stats query failed", exc_info=True)

    # ── 6. TOURNAMENTS ───────────────────────────────────────────────────
    active_tournaments = []
    tournament_count = 0
    next_match_info = None  # User's upcoming match with room link
    imminent_lobby_alert = None
    try:
        Registration = _safe_model("tournaments.Registration")
        Tournament = _safe_model("tournaments.Tournament")
        Match = _safe_model("tournaments.Match")
        TournamentStaffAssignment = _safe_model("tournaments.TournamentStaffAssignment")
        if Registration and Tournament:
            excluded_statuses = ["cancelled", "rejected", "draft"]
            reg_filter = Q(is_deleted=False)
            reg_filter &= ~Q(status__in=excluded_statuses)
            reg_filter &= (Q(user=user) | Q(team_id__in=[t["id"] for t in my_teams])) if my_teams else Q(user=user)

            regs = list(
                Registration.objects.filter(reg_filter)
                .select_related("tournament", "tournament__game")
                .order_by("-created_at")[:8]
            )
            tournament_ids = [r.tournament_id for r in regs if getattr(r, "tournament_id", None)]
            vnext_staff_tournament_ids = set()

            if tournament_ids and TournamentStaffAssignment:
                try:
                    vnext_staff_tournament_ids = set(
                        TournamentStaffAssignment.objects.filter(
                            user=user,
                            is_active=True,
                            tournament_id__in=tournament_ids,
                        ).values_list("tournament_id", flat=True)
                    )
                except Exception:
                    vnext_staff_tournament_ids = set()

            for reg in regs:
                t = reg.tournament
                if t:
                    can_manage = bool(
                        user.is_staff
                        or getattr(t, "organizer_id", None) == user.id
                        or t.id in vnext_staff_tournament_ids
                    )
                    active_tournaments.append({
                        "id": t.id,
                        "name": t.name,
                        "slug": getattr(t, "slug", ""),
                        "status": getattr(t, "status", ""),
                        "game_name": t.game.display_name if t.game else game_map.get(getattr(t, "game_id", None), ""),
                        "game_icon": _img_url(t.game, "icon") if t.game else None,
                        "banner_url": _img_url(t, "banner_image"),
                        "thumbnail_url": _img_url(t, "thumbnail_image"),
                        "scheduled_at": getattr(t, "scheduled_at", None),
                        "tournament_start": getattr(t, "tournament_start", None),
                        "prize_pool": getattr(t, "prize_pool", None),
                        "format": getattr(t, "format", ""),
                        "reg_status": getattr(reg, "status", ""),
                        "is_live": getattr(t, "status", "") == "live",
                        "platform": getattr(t, "platform", ""),
                        "max_participants": getattr(t, "max_participants", 0),
                        "can_manage": can_manage,
                    })
            tournament_count = (
                Registration.objects.filter(reg_filter)
                .values("tournament").distinct().count()
            )

        # Find user's next upcoming match across all tournaments
        if Match:
            upcoming_states = ["scheduled", "check_in", "ready", "live"]
            user_team_ids = [t["id"] for t in my_teams]
            q_participant = Q(participant1_id=user.id) | Q(participant2_id=user.id)
            if user_team_ids:
                q_participant |= Q(participant1_id__in=user_team_ids) | Q(participant2_id__in=user_team_ids)
            # Participant IDs may store Registration.id — include those too
            try:
                user_reg_ids = list(
                    Registration.objects.filter(
                        user=user, is_deleted=False,
                    ).values_list("id", flat=True)
                )
                if user_reg_ids:
                    q_participant |= Q(participant1_id__in=user_reg_ids) | Q(participant2_id__in=user_reg_ids)
            except Exception:
                user_reg_ids = []
            nm = (
                Match.objects.filter(q_participant, state__in=upcoming_states, is_deleted=False)
                .select_related("tournament")
                .order_by("scheduled_time", "round_number", "match_number")
                .first()
            )
            if nm:
                nm_lobby_info = nm.lobby_info if isinstance(nm.lobby_info, dict) else {}
                nm_lobby_code = (nm_lobby_info.get('lobby_code') or nm_lobby_info.get('code') or '').strip()
                nm_lobby_status = str(nm_lobby_info.get('status') or '').strip().lower()
                nm_lobby_open = bool(nm_lobby_code) and nm_lobby_status not in {'closed', 'completed', 'cancelled'}
                all_participant_ids = set([user.id] + user_team_ids + user_reg_ids)
                next_match_info = {
                    "match_id": nm.id,
                    "tournament_name": nm.tournament.name if nm.tournament else "",
                    "tournament_slug": nm.tournament.slug if nm.tournament else "",
                    "opponent_name": nm.participant2_name if nm.participant1_id in all_participant_ids else nm.participant1_name,
                    "scheduled_time": nm.scheduled_time,
                    "state": nm.state,
                    "is_live": nm.state == "live",
                    "match_room_url": '/tournaments/%s/matches/%s/room/' % (nm.tournament.slug, nm.id) if nm.tournament else '',
                    "lobby_code": nm_lobby_code,
                    "lobby_status": nm_lobby_status,
                    "lobby_open": nm_lobby_open,
                    "game_icon": _img_url(nm.tournament.game, "icon") if nm.tournament and nm.tournament.game else None,
                }

            window_start = now - timedelta(minutes=5)
            window_end = now + timedelta(minutes=60)
            window_matches = (
                Match.objects.filter(
                    q_participant,
                    state__in=["scheduled", "check_in", "ready", "live"],
                    is_deleted=False,
                    scheduled_time__gte=window_start,
                    scheduled_time__lte=window_end,
                )
                .select_related("tournament", "tournament__game")
                .order_by("scheduled_time", "round_number", "match_number")[:8]
            )
            for wm in window_matches:
                lobby_info = wm.lobby_info if isinstance(wm.lobby_info, dict) else {}
                lobby_code = (lobby_info.get('lobby_code') or lobby_info.get('code') or '').strip()
                lobby_status = str(lobby_info.get('status') or '').strip().lower()
                lobby_open = bool(lobby_code) and lobby_status not in {'closed', 'completed', 'cancelled'}

                starts_in_minutes = max(int((wm.scheduled_time - now).total_seconds() // 60), 0)

                all_participant_ids = set([user.id] + user_team_ids + user_reg_ids)
                imminent_lobby_alert = {
                    "match_id": wm.id,
                    "tournament_name": wm.tournament.name if wm.tournament else "",
                    "tournament_slug": wm.tournament.slug if wm.tournament else "",
                    "opponent_name": wm.participant2_name if wm.participant1_id in all_participant_ids else wm.participant1_name,
                    "scheduled_time": wm.scheduled_time,
                    "starts_in_minutes": starts_in_minutes,
                    "lobby_code": lobby_code,
                    "lobby_status": lobby_status,
                    "lobby_open": lobby_open,
                    "match_room_url": '/tournaments/%s/matches/%s/room/' % (wm.tournament.slug, wm.id) if wm.tournament else '',
                    "game_icon": _img_url(wm.tournament.game, "icon") if wm.tournament and wm.tournament.game else None,
                    "match_state": wm.state,
                }
                break
    except Exception:
        logger.debug("Dashboard: tournaments query failed", exc_info=True)

    # ── 7. LEADERBOARD POSITION ──────────────────────────────────────────
    leaderboard_data = []
    try:
        LeaderboardEntry = _safe_model("leaderboards.LeaderboardEntry")
        if LeaderboardEntry:
            entries = (
                LeaderboardEntry.objects.filter(player=user)
                .order_by("rank")[:3]
            )
            for e in entries:
                leaderboard_data.append({
                    "rank": e.rank,
                    "points": getattr(e, "points", 0),
                    "leaderboard_type": getattr(e, "leaderboard_type", ""),
                    "game_name": game_map.get(getattr(e, "game_id", None), ""),
                    "wins": getattr(e, "wins", 0),
                    "losses": getattr(e, "losses", 0),
                    "win_rate": getattr(e, "win_rate", 0),
                })
    except Exception:
        logger.debug("Dashboard: leaderboard query failed", exc_info=True)

    # ── SECTIONS 8–19: Secondary data (wallet, badges, social, etc.) ────
    from .secondary_data import load_secondary_data
    secondary = load_secondary_data(
        user,
        profile=profile,
        my_teams=my_teams,
        game_detail_map=game_detail_map,
    )

    # ── ASSEMBLE CONTEXT ─────────────────────────────────────────────────
    context = {
        # Profile
        "profile": profile_data,
        # Teams
        "my_teams": my_teams,
        "team_count": len(my_teams),
        # Invites
        "pending_invites": pending_invites,
        "invite_count": len(pending_invites),
        # Matches
        "recent_matches": recent_matches,
        "match_stats": match_stats,
        # Tournaments
        "active_tournaments": active_tournaments,
        "tournament_count": tournament_count,
        "next_match_info": next_match_info,
        "imminent_lobby_alert": imminent_lobby_alert,
        # Leaderboard
        "leaderboard_data": leaderboard_data,
        # Games map (for template use)
        "games": list(game_map.values()),
    }
    # Merge secondary data (wallet, badges, notifications, social, etc.)
    context.update(secondary)

    # ── BUILD COMMAND CENTER DATA ────────────────────────────────────────
    context["cc_data"] = _build_cc_data(context, user, now)

    return render(request, "dashboard/index.html", context)
