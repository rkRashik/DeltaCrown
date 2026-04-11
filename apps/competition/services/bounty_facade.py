"""
Unified Bounty Facade — Provides a single query interface across both
bounty systems.

Two bounty models exist for different use-cases:
  - ``apps.competition.models.Bounty`` — Team-issued competitive bounties
    (BEAT_US, WIN_STREAK, TOURNAMENT_WIN, etc.)
  - ``apps.user_profile.models.Bounty`` — Peer-to-peer escrow bounties
    (SOLO, TEAM with proofs, disputes, acceptance flow)

This facade normalises both into a common dict shape for dashboard,
profile, and feed rendering.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db.models import Q

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

logger = logging.getLogger(__name__)


def get_active_bounties_for_user(user: "AbstractUser", *, limit: int = 12) -> list[dict]:
    """
    Return up to *limit* active bounties across both systems,
    normalised into a common shape.
    """
    results: list[dict] = []

    # ── Competition bounties (team-issued) ───────────────────────────
    try:
        from apps.competition.models import Bounty as CompBounty

        team_ids = list(
            user.teams.values_list("id", flat=True)
        ) if hasattr(user, "teams") else []

        comp_filter = Q(created_by=user)
        if team_ids:
            comp_filter |= Q(issuer_team_id__in=team_ids)

        comp_qs = (
            CompBounty.objects
            .filter(comp_filter)
            .exclude(status__in=["CANCELLED", "EXPIRED"])
            .select_related("game", "issuer_team", "created_by")
            .order_by("-created_at")[: limit // 2]
        )
        for b in comp_qs:
            results.append(_normalize_competition_bounty(b))
    except Exception:
        logger.debug("bounty_facade: competition bounty query failed", exc_info=True)

    # ── Profile bounties (peer-to-peer) ──────────────────────────────
    try:
        from apps.user_profile.models import Bounty as ProfileBounty

        profile_filter = Q(creator=user) | Q(acceptor=user)
        profile_qs = (
            ProfileBounty.objects
            .filter(profile_filter)
            .exclude(status__in=["cancelled", "expired"])
            .select_related("game", "creator", "acceptor")
            .order_by("-created_at")[: limit // 2]
        )
        for b in profile_qs:
            results.append(_normalize_profile_bounty(b))
    except Exception:
        logger.debug("bounty_facade: profile bounty query failed", exc_info=True)

    # Sort combined results newest-first
    results.sort(key=lambda r: r["created_at"], reverse=True)
    return results[:limit]


# ── normalizers ──────────────────────────────────────────────────────────

def _normalize_competition_bounty(b) -> dict:
    return {
        "id": str(b.id),
        "source": "competition",
        "title": b.title,
        "bounty_type": getattr(b, "bounty_type", "CUSTOM"),
        "status": b.status,
        "reward_amount": float(getattr(b, "reward_amount", 0) or 0),
        "reward_type": getattr(b, "reward_type", "CP"),
        "game_name": b.game.name if b.game else "",
        "game_icon": getattr(b.game, "icon_url", "") if b.game else "",
        "issuer_name": b.issuer_team.name if b.issuer_team else "",
        "is_claimable": getattr(b, "is_claimable", False),
        "expires_at": getattr(b, "expires_at", None),
        "created_at": b.created_at,
    }


def _normalize_profile_bounty(b) -> dict:
    return {
        "id": str(b.id),
        "source": "profile",
        "title": getattr(b, "title", str(b)),
        "bounty_type": getattr(b, "bounty_type", "SOLO"),
        "status": b.status,
        "reward_amount": float(getattr(b, "amount", 0) or 0),
        "reward_type": "CP",
        "game_name": b.game.name if getattr(b, "game", None) else "",
        "game_icon": getattr(b.game, "icon_url", "") if getattr(b, "game", None) else "",
        "issuer_name": b.creator.username if getattr(b, "creator", None) else "",
        "is_claimable": getattr(b, "status", "") in ("open", "OPEN", "active", "ACTIVE"),
        "expires_at": getattr(b, "expires_at", None),
        "created_at": b.created_at,
    }
