"""
Dashboard secondary data loaders — sections 8-19 of the command center.

Extracted from dashboard_index() to keep the view function focused on
request handling and context assembly.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db.models import Q

from .helpers import _safe_model, _safe_int, _img_url, _avatar_fallback

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

logger = logging.getLogger(__name__)


def load_secondary_data(
    user: "AbstractUser",
    *,
    profile=None,
    my_teams: list[dict] | None = None,
    game_detail_map: dict | None = None,
    now=None,
    week_offset: int = 0,
) -> dict:
    """
    Load all secondary dashboard sections (8-19) in one call.

    Returns a dict that can be merged directly into the template context.
    """
    from django.utils import timezone as tz

    my_teams = my_teams or []
    game_detail_map = game_detail_map or {}
    team_ids = [t["id"] for t in my_teams]
    now = now or tz.now()

    from apps.organizations.models import Team

    data: dict = {}

    data.update(_load_wallet(user, profile))
    data.update(_load_badges(profile))
    data.update(_load_notifications(user))
    data.update(_load_social(profile))
    data.update(_load_orders(user))
    data.update(_load_organizations(user, Team))
    data.update(_load_game_passports(user, game_detail_map))
    data.update(_load_recruitment(my_teams, game_detail_map))
    data.update(_load_featured_product())
    data.update(_load_support_tickets(user))
    data.update(_load_challenges(user, team_ids, game_detail_map))
    data.update(_load_bounties(user))
    # New Command Center sections
    data.update(_load_ops_counts(user, team_ids))
    data.update(_load_daily_reward(profile))
    data.update(_load_week_schedule(user, team_ids, now, week_offset=week_offset))
    data.update(_load_join_requests(user, game_detail_map))

    return data


# ── Section 8: Wallet / Economy ──────────────────────────────────────────

def _load_wallet(user, profile) -> dict:
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
    return {"wallet": wallet_data}


# ── Section 9: Badges / Achievements ────────────────────────────────────

def _load_badges(profile) -> dict:
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
    return {"badges": badges}


# ── Section 10: Notifications ────────────────────────────────────────────

def _load_notifications(user) -> dict:
    from apps.notifications.models import Notification

    recent_notifications = []
    unread_notif_count = 0
    try:
        notifs = Notification.objects.filter(recipient=user).order_by("-created_at")[:8]

        follow_request_meta = {}
        follow_request_ids = [
            n.action_object_id
            for n in notifs
            if n.type == 'follow_request' and getattr(n, 'action_object_id', None)
        ]
        if follow_request_ids:
            FollowRequest = _safe_model("user_profile.FollowRequest")
            if FollowRequest:
                for req in FollowRequest.objects.filter(id__in=follow_request_ids).select_related("requester", "requester__user"):
                    requester_name = getattr(req.requester, 'display_name', '') or req.requester.user.username
                    follow_request_meta[req.id] = {
                        'actor_name': requester_name,
                        'actor_avatar': _img_url(req.requester, 'avatar') or _avatar_fallback(requester_name, '0f3460'),
                        'is_pending': req.status == FollowRequest.STATUS_PENDING,
                    }

        for n in notifs:
            follow_meta = follow_request_meta.get(getattr(n, 'action_object_id', None), {}) if n.type == 'follow_request' else {}
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
                "actor_name": follow_meta.get('actor_name', ''),
                "actor_avatar": follow_meta.get('actor_avatar', ''),
                "follow_request_pending": follow_meta.get('is_pending', False),
            })
        unread_notif_count = _safe_int(
            lambda: Notification.objects.filter(recipient=user, is_read=False).count()
        )
    except Exception:
        logger.debug("Dashboard: notifications query failed", exc_info=True)
    return {
        "recent_notifications": recent_notifications,
        "unread_notif_count": unread_notif_count,
    }


# ── Section 11: Social Stats ────────────────────────────────────────────

def _load_social(profile) -> dict:
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
    return {"social_stats": social_stats}


# ── Section 12: Recent Orders ───────────────────────────────────────────

def _load_orders(user) -> dict:
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
    return {"recent_orders": recent_orders}


# ── Section 13: Organization Memberships ─────────────────────────────────

def _load_organizations(user, Team) -> dict:
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
                member_count = 0
                pending_requests = 0
                try:
                    team_count_in_org = Team.objects.filter(organization=org, status="ACTIVE").count()
                except Exception:
                    pass
                try:
                    member_count = OrgMembership.objects.filter(organization=org).count()
                except Exception:
                    pass
                try:
                    from apps.organizations.models.join_request import TeamJoinRequest
                    org_team_ids = list(Team.objects.filter(organization=org).values_list("id", flat=True))
                    if org_team_ids:
                        pending_requests = TeamJoinRequest.objects.filter(
                            team_id__in=org_team_ids, status="PENDING"
                        ).count()
                except Exception:
                    pass
                is_owner = getattr(om, "role", "").upper() in ("OWNER", "CEO", "FOUNDER")
                my_organizations.append({
                    "id": org.id,
                    "name": org.name,
                    "slug": org.slug,
                    "logo_url": _img_url(org),
                    "role": om.role,
                    "is_verified": getattr(org, "is_verified", False),
                    "is_owner": is_owner,
                    "team_count": team_count_in_org,
                    "member_count": member_count,
                    "pending_requests": pending_requests,
                    "monthly_dc": 0,
                    "joined_at": om.joined_at,
                })
    except Exception:
        logger.debug("Dashboard: organizations query failed", exc_info=True)
    return {
        "my_organizations": my_organizations,
        "org_count": len(my_organizations),
    }


# ── Section 14: Game Passports ───────────────────────────────────────────

def _load_game_passports(user, game_detail_map) -> dict:
    game_passports = []
    try:
        GameProfile = _safe_model("user_profile.GameProfile")
        if GameProfile:
            gps = GameProfile.objects.filter(user=user).select_related("game").order_by("game__name")
            for gp in gps:
                game_passports.append({
                    "id": gp.id,
                    "game_name": gp.game.name if gp.game else "",
                    "game_icon": _img_url(gp.game, "icon") if gp.game else "",
                    "game_color": getattr(gp.game, "primary_color", "#6366F1") if gp.game else "#6366F1",
                    "ign": getattr(gp, "ign", "") or getattr(gp, "game_display_name", ""),
                    "is_lft": getattr(gp, "is_lft", False),
                })
    except Exception:
        logger.debug("Dashboard: game passports query failed", exc_info=True)
    return {"game_passports": game_passports}


# ── Section 15: Recruitment Positions ────────────────────────────────────

def _load_recruitment(my_teams, game_detail_map) -> dict:
    recruitment_positions = []
    try:
        RecruitmentPosition = _safe_model("organizations.RecruitmentPosition")
        if RecruitmentPosition and my_teams:
            team_ids = [t["id"] for t in my_teams]
            positions = (
                RecruitmentPosition.objects.filter(team_id__in=team_ids, is_active=True)
                .select_related("team")
                .order_by("-id")[:5]
            )
            for pos in positions:
                gd = game_detail_map.get(getattr(pos.team, "game_id", None), {})
                recruitment_positions.append({
                    "id": pos.id,
                    "team_name": pos.team.name if pos.team else "",
                    "team_slug": pos.team.slug if pos.team else "",
                    "team_logo": _img_url(pos.team) if pos.team else "",
                    "title": getattr(pos, "title", ""),
                    "role_category": getattr(pos, "role_category", ""),
                    "game_name": gd.get("name", ""),
                    "game_icon": gd.get("icon", ""),
                })
    except Exception:
        logger.debug("Dashboard: recruitment positions query failed", exc_info=True)
    return {"recruitment_positions": recruitment_positions}


# ── Section 16: Featured Product ─────────────────────────────────────────

def _load_featured_product() -> dict:
    featured_product = None
    try:
        Product = _safe_model("ecommerce.Product")
        if Product:
            prod = Product.objects.filter(is_featured=True, stock__gt=0).order_by("-created_at").first()
            if prod:
                featured_product = {
                    "id": prod.id,
                    "name": prod.name,
                    "slug": getattr(prod, "slug", ""),
                    "price": float(getattr(prod, "price", 0) or 0),
                    "original_price": float(getattr(prod, "original_price", 0) or 0),
                    "image": _img_url(prod, "featured_image"),
                    "rarity": getattr(prod, "rarity", "common"),
                    "product_type": getattr(prod, "product_type", ""),
                    "is_limited": getattr(prod, "is_limited_edition", False),
                }
    except Exception:
        logger.debug("Dashboard: featured product query failed", exc_info=True)
    return {"featured_product": featured_product}


# ── Section 17: Support Tickets ──────────────────────────────────────────

def _load_support_tickets(user) -> dict:
    support_tickets = []
    try:
        ContactMessage = _safe_model("support.ContactMessage")
        if ContactMessage:
            tickets = (
                ContactMessage.objects.filter(user=user)
                .exclude(status="CLOSED")
                .order_by("-created_at")[:3]
            )
            for t in tickets:
                support_tickets.append({
                    "id": t.id,
                    "subject": getattr(t, "subject", ""),
                    "status": getattr(t, "status", ""),
                    "priority": getattr(t, "priority", "MEDIUM"),
                    "created_at": t.created_at,
                })
    except Exception:
        logger.debug("Dashboard: support tickets query failed", exc_info=True)
    return {"support_tickets": support_tickets}


# ── Section 18: Challenges ───────────────────────────────────────────────

def _load_challenges(user, team_ids, game_detail_map) -> dict:
    active_challenges = []
    try:
        # Prefer canonical Competition Challenge, fall back to legacy
        Challenge = _safe_model("competition.Challenge") or _safe_model("challenges.Challenge")
        if Challenge:
            # Competition Challenge uses challenger_team; legacy uses team
            team_fk = "challenger_team_id" if hasattr(Challenge, "challenger_team") else "team_id"
            c_filter = Q(created_by=user)
            if team_ids:
                c_filter |= Q(**{f"{team_fk}__in": team_ids})
            select = []
            if hasattr(Challenge, "challenger_team"):
                select.append("challenger_team")
            if hasattr(Challenge, "team"):
                select.append("team")
            select.append("created_by")
            challenges_qs = (
                Challenge.objects.filter(c_filter)
                .exclude(status__in=["CANCELLED", "EXPIRED", "cancelled", "expired"])
                .select_related(*select)
                .order_by("-created_at")[:6]
            )
            for c in challenges_qs:
                gd = game_detail_map.get(getattr(c, "game_id", None), {})
                c_team = getattr(c, "challenger_team", None) or getattr(c, "team", None)
                c_opponent = getattr(c, "challenged_team", None) or getattr(c, "opponent_team", None)
                active_challenges.append({
                    "id": str(c.id),
                    "title": c.title,
                    "type": getattr(c, "challenge_type", "SCRIM"),
                    "status": c.status,
                    "format": getattr(c, "format", None) or f"BO{getattr(c, 'best_of', 1)}",
                    "prize": getattr(c, "prize_amount", 0) or 0,
                    "currency": getattr(c, "prize_currency", getattr(c, "prize_type", "DC")),
                    "team_name": c_team.name if c_team else "",
                    "opponent": c_opponent.name if c_opponent else "Open",
                    "game_name": gd.get("name", ""),
                    "game_icon": gd.get("icon", ""),
                    "created_at": c.created_at,
                    "expires_at": getattr(c, "expires_at", None),
                })
    except Exception:
        logger.debug("Dashboard: challenges query failed", exc_info=True)
    return {"active_challenges": active_challenges}


# ── Section 19: Bounties ────────────────────────────────────────────────

def _load_bounties(user) -> dict:
    active_bounties = []
    try:
        from apps.competition.services.bounty_facade import get_active_bounties_for_user
        active_bounties = get_active_bounties_for_user(user, limit=6)
    except Exception:
        logger.debug("Dashboard: bounties facade failed", exc_info=True)
    return {"active_bounties": active_bounties}


# ── Section 20: Competitive Operations counts ────────────────────────────

def _load_ops_counts(user, team_ids: list) -> dict:
    counts = {"showdown_live": 0, "missions_done": 0, "missions_total": 0, "bounty_claimable": 0, "dropzone_open": 0}
    try:
        Challenge = _safe_model("competition.Challenge")
        if Challenge:
            counts["showdown_live"] = _safe_int(
                lambda: Challenge.objects.filter(
                    status__in=["ACTIVE", "active"],
                    challenge_type__in=["SHOWDOWN", "REWARD"],
                ).count()
            )
    except Exception:
        pass
    try:
        MissionEnrollment = _safe_model("competition.MissionEnrollment")
        if MissionEnrollment:
            today_qs = MissionEnrollment.objects.filter(user=user)
            counts["missions_total"] = _safe_int(lambda: today_qs.count())
            counts["missions_done"] = _safe_int(
                lambda: today_qs.filter(status__in=["COMPLETED", "CLAIMED"]).count()
            )
    except Exception:
        pass
    try:
        BountyClaim = _safe_model("competition.BountyClaim")
        if BountyClaim:
            counts["bounty_claimable"] = _safe_int(
                lambda: BountyClaim.objects.filter(
                    claimant=user, status__in=["APPROVED", "VERIFIED"]
                ).count()
            )
    except Exception:
        pass
    try:
        RoyaleLobby = _safe_model("competition.RoyaleLobby")
        if RoyaleLobby:
            counts["dropzone_open"] = _safe_int(
                lambda: RoyaleLobby.objects.filter(status__in=["OPEN", "REGISTRATION_OPEN"]).count()
            )
    except Exception:
        pass
    return {"ops_counts": counts}


# ── Section 21: Daily Reward / Login Streak ──────────────────────────────

def _load_daily_reward(profile) -> dict:
    default = {"daily_reward": None}
    if not profile:
        return default
    try:
        from datetime import timedelta
        from apps.economy.services.daily_reward_service import get_platform_date

        DailyLoginStreak = _safe_model("economy.DailyLoginStreak")
        DailyRewardConfig = _safe_model("economy.DailyRewardConfig")
        DailyRewardClaim = _safe_model("economy.DailyRewardClaim")
        if not DailyLoginStreak:
            return default

        streak, _ = DailyLoginStreak.objects.get_or_create(profile=profile)
        config = DailyRewardConfig.get_active() if DailyRewardConfig else None
        platform_today = get_platform_date()

        # Query ACTUAL claim records for this week (not just last_claim_date)
        claimed_dates: set = set()
        if DailyRewardClaim:
            days_since_thu = (platform_today.weekday() - 3) % 7
            week_start = platform_today - timedelta(days=days_since_thu)
            week_end = week_start + timedelta(days=7)
            claimed_dates = set(
                DailyRewardClaim.objects.filter(
                    user=profile.user,
                    platform_date__gte=week_start,
                    platform_date__lt=week_end,
                ).values_list("platform_date", flat=True)
            )

        if config:
            today_idx = (platform_today.weekday() - 3) % 7
            today_entry = config.get_day(today_idx)
            week = config.week_with_state(claimed_dates, platform_today)
        else:
            today_entry = {"xp": 25, "dc": 0}
            week = []

        # Next milestone
        next_milestone = None
        try:
            DailyRewardMilestone = _safe_model("economy.DailyRewardMilestone")
            if DailyRewardMilestone:
                next_milestone = (
                    DailyRewardMilestone.objects.filter(
                        streak_days__gt=streak.current_streak, is_active=True
                    ).order_by("streak_days").values("streak_days", "bonus_xp", "bonus_dc", "label").first()
                )
        except Exception:
            pass

        return {
            "daily_reward": {
                "current_streak": streak.current_streak,
                "best_streak": streak.best_streak,
                "today_claimable": streak.today_claimable,
                "today_xp": today_entry["xp"],
                "today_dc": today_entry["dc"],
                "week_schedule": week,
                "next_milestone": next_milestone,
            },
        }
    except Exception:
        logger.debug("Dashboard: daily reward query failed", exc_info=True)
        return default


# ── Section 22: This-Week schedule ──────────────────────────────────────

def _load_week_schedule(user, team_ids: list, now, *, week_offset: int = 0) -> dict:
    from datetime import timedelta

    today = now.date()
    # Platform week starts Thursday
    days_since_thu = (today.weekday() - 3) % 7
    this_thursday = today - timedelta(days=days_since_thu)
    # Apply week offset (±N weeks from current Thursday)
    thursday = this_thursday + timedelta(days=week_offset * 7)
    dow_names = ["Thu", "Fri", "Sat", "Sun", "Mon", "Tue", "Wed"]

    week = [
        {
            "date": thursday + timedelta(days=i),
            "dow": dow_names[i],
            "day_num": (thursday + timedelta(days=i)).day,
            "is_today": (thursday + timedelta(days=i)) == today,
            "events": [],
        }
        for i in range(7)
    ]
    day_map = {w["date"]: w for w in week}
    week_end = thursday + timedelta(days=7)

    # Upcoming matches
    try:
        Match = _safe_model("tournaments.Match")
        if Match and team_ids:
            from django.db.models import Q as DQ
            matches = (
                Match.objects.filter(
                    DQ(participant1_id__in=team_ids) | DQ(participant2_id__in=team_ids),
                    scheduled_time__isnull=False,
                    scheduled_time__date__gte=thursday,
                    scheduled_time__date__lt=week_end,
                    is_deleted=False,
                )
                .only("scheduled_time", "state")[:30]
            )
            for m in matches:
                d = m.scheduled_time.date()
                if d in day_map:
                    state = getattr(m, "state", "") or ""
                    if state == "live":
                        label = "live"
                    elif state == "completed":
                        label = "done"
                    else:
                        try:
                            label = m.scheduled_time.strftime("%I%p").lstrip("0").lower()
                        except Exception:
                            label = "match"
                    day_map[d]["events"].append({"type": "match", "label": label})
    except Exception:
        pass

    # Invite expiries
    try:
        from apps.organizations.models.team_invite import TeamInvite
        invites = TeamInvite.objects.filter(
            invited_user=user, status="PENDING",
            expires_at__date__gte=thursday, expires_at__date__lt=week_end,
        ).only("expires_at")[:10]
        for inv in invites:
            d = inv.expires_at.date()
            if d in day_map:
                day_map[d]["events"].append({"type": "exp", "label": "Invite exp"})
    except Exception:
        pass

    return {"week_schedule": week}


# ── Section 23: Join Requests (sent by the user) ─────────────────────────

def _load_join_requests(user, game_detail_map: dict) -> dict:
    join_requests = []
    try:
        from apps.organizations.models.join_request import TeamJoinRequest
        jrs = (
            TeamJoinRequest.objects.filter(user=user)
            .exclude(status="WITHDRAWN")
            .select_related("team")
            .order_by("-created_at")[:8]
        )
        for jr in jrs:
            t = jr.team
            gd = game_detail_map.get(getattr(t, "game_id", None), {}) if t else {}
            join_requests.append({
                "id": jr.id,
                "team_name": t.name if t else "",
                "team_slug": getattr(t, "slug", "") if t else "",
                "team_logo": _img_url(t) if t else "",
                "team_tag": getattr(t, "tag", "") if t else "",
                "game_name": gd.get("name", ""),
                "role": getattr(jr, "applied_position", "") or "",
                "status": jr.status,
                "created_at": jr.created_at,
                "team_url": f"/teams/{getattr(t, 'slug', '')}/" if t else "",
            })
    except Exception:
        logger.debug("Dashboard: join requests query failed", exc_info=True)
    return {"join_requests": join_requests}
