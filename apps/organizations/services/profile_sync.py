# apps/organizations/services/profile_sync.py
"""
Bridge between organizations and user_profile apps.

Keeps UserProfile.primary_team in sync with active organization memberships.

Call `sync_primary_team(user)` after any membership lifecycle event:
  - Member added (create_membership / accept invite)
  - Member removed / kicked
  - Member leaves team
  - Transfer ownership
"""
from __future__ import annotations

import logging

from django.apps import apps
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


def sync_primary_team(user) -> bool:
    """
    Ensure UserProfile.primary_team reflects the user's active membership.

    Logic:
      1. If user has an active membership AND primary_team is NULL:
         Set primary_team to the first active team.
      2. If user has NO active memberships AND primary_team is set:
         Clear primary_team.
      3. If user's current primary_team doesn't match any active membership:
         Update to the first active team found.

    Returns True if primary_team was changed, False otherwise.
    """
    try:
        UserProfile = apps.get_model("user_profile", "UserProfile")
        Team = apps.get_model("organizations", "Team")
        TeamMembership = apps.get_model("organizations", "TeamMembership")
    except LookupError as e:
        logger.warning("profile_sync: model not found — %s", e)
        return False

    profile = getattr(user, "profile", None)
    if not profile:
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return False

    active_memberships = (
        TeamMembership.objects
        .filter(user=user, status='ACTIVE')
        .select_related("team")
        .order_by("joined_at")
    )

    if not active_memberships.exists():
        if profile.primary_team_id:
            profile.primary_team = None
            profile.save(update_fields=["primary_team"])
            logger.info(
                "profile_sync: cleared primary_team for user %s (no active memberships)",
                user.pk,
            )
            return True
        return False

    active_team_ids = set(active_memberships.values_list("team_id", flat=True))

    if profile.primary_team_id and profile.primary_team_id in active_team_ids:
        return False

    first_team = active_memberships.first().team
    profile.primary_team = first_team
    profile.save(update_fields=["primary_team"])
    logger.info(
        "profile_sync: set primary_team=%s for user %s",
        first_team.id, user.pk,
    )
    return True


def get_unified_memberships(user_profile) -> list:
    """
    Return a list of membership dicts for the career tab.

    Each dict contains:
        team_name, team_slug, team_tag, game, role, roster_slot,
        joined_at, status, source
    """
    try:
        TeamMembership = apps.get_model("organizations", "TeamMembership")
    except LookupError:
        return []

    results = []
    qs = (
        TeamMembership.objects
        .filter(user=user_profile.user)
        .select_related("team")
        .order_by("-joined_at")
    )
    seen_slugs = set()
    for m in qs:
        slug = m.team.slug
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        results.append({
            "team_name": m.team.name,
            "team_slug": slug,
            "team_tag": getattr(m.team, "tag", ""),
            "game": str(getattr(m.team, "game_id", "")),
            "role": m.role,
            "roster_slot": getattr(m, "roster_slot", ""),
            "joined_at": m.joined_at,
            "left_at": getattr(m, "left_at", None),
            "status": getattr(m, "status", "ACTIVE"),
            "is_active": getattr(m, "is_active", True),
            "source": "vnext",
        })

    return results
