from __future__ import annotations
from datetime import datetime, timedelta
from typing import Iterable, Optional

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Q, Count, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .forms import MyMatchesFilterForm

logger = __import__("logging").getLogger(__name__)


# ─── Helper: safe model fetcher ─────────────────────────────────────────────
def _safe_model(label: str):
    """Return model class or None — never raises."""
    try:
        return apps.get_model(*label.split("."))
    except Exception:
        return None


def _safe_qs(fn):
    """Run a queryset lambda, return [] on any error."""
    try:
        return fn()
    except Exception:
        return []


def _safe_int(fn, default=0):
    try:
        return fn()
    except Exception:
        return default


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

def _build_game_lookup():
    """Build {game_id: game_name} lookup from games.Game."""
    Game = _safe_model("games.Game")
    if not Game:
        return {}
    try:
        return {g.id: g.name for g in Game.objects.all().only("id", "name")}
    except Exception:
        return {}


def _logo_url(obj, field="logo"):
    try:
        f = getattr(obj, field, None)
        return f.url if f else None
    except Exception:
        return None


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

    # ── 1. USER PROFILE ─────────────────────────────────────────────────
    profile = None
    profile_data = {}
    try:
        Profile = _safe_model("user_profile.UserProfile")
        if Profile:
            profile = Profile.objects.filter(user=user).first()
        if profile:
            avatar = None
            try:
                avatar = profile.avatar.url if profile.avatar else None
            except Exception:
                pass
            profile_data = {
                "display_name": getattr(profile, "display_name", "") or user.get_full_name() or user.username,
                "avatar_url": avatar,
                "slug": getattr(profile, "slug", user.username),
                "lft_status": getattr(profile, "lft_status", None) or getattr(profile, "LFTStatus", None),
                "kyc_status": getattr(profile, "kyc_status", ""),
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
            .select_related("team")
            .order_by("-joined_at")[:8]
        )
        for m in memberships:
            t = m.team
            member_ct = _safe_int(
                lambda: TeamMembership.objects.filter(team=t, status=MembershipStatus.ACTIVE).count()
            )
            my_teams.append({
                "id": t.id, "name": t.name, "slug": t.slug,
                "logo_url": _logo_url(t),
                "role": m.role,
                "game_name": game_map.get(t.game_id, ""),
                "member_count": member_ct,
                "tag": getattr(t, "tag", "") or "",
                "status": getattr(t, "status", ""),
            })
    except Exception:
        logger.debug("Dashboard: teams query failed", exc_info=True)

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
    try:
        Registration = _safe_model("tournaments.Registration")
        Tournament = _safe_model("tournaments.Tournament")
        Match = _safe_model("tournaments.Match")
        if Registration and Tournament:
            regs = (
                Registration.objects.filter(
                    Q(team__in=[t["id"] for t in my_teams]) | Q(user=user)
                )
                .select_related("tournament")
                .order_by("-created_at")[:6]
            )
            for reg in regs:
                t = reg.tournament
                if t:
                    active_tournaments.append({
                        "id": t.id,
                        "name": t.name,
                        "slug": getattr(t, "slug", ""),
                        "status": getattr(t, "status", ""),
                        "game_name": game_map.get(getattr(t, "game_id", None), ""),
                        "scheduled_at": getattr(t, "scheduled_at", None),
                        "tournament_start": getattr(t, "tournament_start", None),
                        "prize_pool": getattr(t, "prize_pool", None),
                        "format": getattr(t, "format", ""),
                        "reg_status": getattr(reg, "status", ""),
                        "is_live": getattr(t, "status", "") == "live",
                    })
            tournament_count = Registration.objects.filter(
                Q(team__in=[t["id"] for t in my_teams]) | Q(user=user)
            ).values("tournament").distinct().count()

        # Find user's next upcoming match across all tournaments
        if Match:
            upcoming_states = ["scheduled", "check_in", "ready", "live"]
            user_team_ids = [t["id"] for t in my_teams]
            q_participant = Q(participant1_id=user.id) | Q(participant2_id=user.id)
            if user_team_ids:
                q_participant |= Q(participant1_id__in=user_team_ids) | Q(participant2_id__in=user_team_ids)
            nm = (
                Match.objects.filter(q_participant, state__in=upcoming_states, is_deleted=False)
                .select_related("tournament")
                .order_by("scheduled_time", "round_number", "match_number")
                .first()
            )
            if nm:
                next_match_info = {
                    "match_id": nm.id,
                    "tournament_name": nm.tournament.name if nm.tournament else "",
                    "tournament_slug": nm.tournament.slug if nm.tournament else "",
                    "opponent_name": nm.participant2_name if nm.participant1_id == user.id or nm.participant1_id in user_team_ids else nm.participant1_name,
                    "scheduled_time": nm.scheduled_time,
                    "state": nm.state,
                    "is_live": nm.state == "live",
                }
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

    # ── 8. WALLET / ECONOMY ──────────────────────────────────────────────
    wallet_data = {"balance": 0, "has_wallet": False, "recent_txns": []}
    try:
        Wallet = _safe_model("economy.DeltaCrownWallet")
        Transaction = _safe_model("economy.DeltaCrownTransaction")
        if Wallet and profile:
            wallet = Wallet.objects.filter(profile=profile).first()
            if wallet:
                wallet_data["has_wallet"] = True
                wallet_data["balance"] = float(getattr(wallet, "cached_balance", 0) or 0)
                if Transaction:
                    txns = Transaction.objects.filter(wallet=wallet).order_by("-created_at")[:5]
                    for txn in txns:
                        wallet_data["recent_txns"].append({
                            "amount": float(txn.amount),
                            "reason": str(getattr(txn, "reason", "")),
                            "created_at": txn.created_at,
                        })
    except Exception:
        logger.debug("Dashboard: wallet query failed", exc_info=True)

    # ── 9. BADGES / ACHIEVEMENTS ─────────────────────────────────────────
    badges = []
    try:
        UserBadge = _safe_model("user_profile.UserBadge")
        if UserBadge and profile:
            ubadges = UserBadge.objects.filter(profile=profile).select_related("badge").order_by("-awarded_at")[:6]
            for ub in ubadges:
                b = ub.badge
                badges.append({
                    "name": getattr(b, "name", ""),
                    "icon": getattr(b, "icon", "") or getattr(b, "icon_url", ""),
                    "description": getattr(b, "description", ""),
                    "rarity": getattr(b, "rarity", ""),
                    "awarded_at": getattr(ub, "awarded_at", None),
                })
    except Exception:
        logger.debug("Dashboard: badges query failed", exc_info=True)

    # ── 10. NOTIFICATIONS ────────────────────────────────────────────────
    recent_notifications = []
    unread_notif_count = 0
    try:
        notifs = Notification.objects.filter(recipient=user).order_by("-created_at")[:8]
        for n in notifs:
            recent_notifications.append({
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "body": getattr(n, "body", "") or getattr(n, "message", ""),
                "url": n.url,
                "is_read": n.is_read,
                "created_at": n.created_at,
                "action_type": getattr(n, "action_type", ""),
                "action_object_id": getattr(n, "action_object_id", None),
            })
        unread_notif_count = _safe_int(
            lambda: Notification.objects.filter(recipient=user, is_read=False).count()
        )
    except Exception:
        logger.debug("Dashboard: notifications query failed", exc_info=True)

    # ── 11. SOCIAL STATS (followers / following) ─────────────────────────
    social_stats = {"followers": 0, "following": 0}
    try:
        Follow = _safe_model("user_profile.Follow")
        if Follow and profile:
            social_stats["followers"] = _safe_int(
                lambda: Follow.objects.filter(following=profile).count()
            )
            social_stats["following"] = _safe_int(
                lambda: Follow.objects.filter(follower=profile).count()
            )
    except Exception:
        pass

    # ── 12. RECENT ORDERS (ecommerce) ────────────────────────────────────
    recent_orders = []
    try:
        Order = _safe_model("ecommerce.Order")
        if Order:
            orders = Order.objects.filter(user=user).order_by("-created_at")[:3]
            for o in orders:
                recent_orders.append({
                    "id": o.id,
                    "status": getattr(o, "status", ""),
                    "total": float(getattr(o, "total", 0) or 0),
                    "created_at": o.created_at,
                })
    except Exception:
        pass

    # ── 13. ORGANIZATION MEMBERSHIPS ─────────────────────────────────────
    my_organizations = []
    try:
        OrgMembership = _safe_model("organizations.OrganizationMembership")
        if OrgMembership:
            org_memberships = (
                OrgMembership.objects.filter(user=user)
                .select_related("organization")
                .order_by("-joined_at")[:5]
            )
            for om in org_memberships:
                org = om.organization
                team_count_in_org = 0
                try:
                    team_count_in_org = Team.objects.filter(
                        organization=org, status="ACTIVE"
                    ).count()
                except Exception:
                    pass
                my_organizations.append({
                    "id": org.id,
                    "name": org.name,
                    "slug": org.slug,
                    "logo_url": _logo_url(org),
                    "role": om.role,
                    "is_verified": getattr(org, "is_verified", False),
                    "team_count": team_count_in_org,
                    "joined_at": om.joined_at,
                })
    except Exception:
        logger.debug("Dashboard: organizations query failed", exc_info=True)

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
        # Leaderboard
        "leaderboard_data": leaderboard_data,
        # Economy
        "wallet": wallet_data,
        # Badges
        "badges": badges,
        # Notifications
        "recent_notifications": recent_notifications,
        "unread_notif_count": unread_notif_count,
        # Social
        "social_stats": social_stats,
        # Orders
        "recent_orders": recent_orders,
        # Organizations
        "my_organizations": my_organizations,
        "org_count": len(my_organizations),
        # Games map (for template use)
        "games": list(game_map.values()),
    }
    return render(request, "dashboard/index.html", context)
