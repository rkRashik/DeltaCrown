# apps/organizations/services/profile_sync.py
"""
Bridge between organizations (vNext) and user_profile apps.

Keeps UserProfile.primary_team in sync with active organization memberships,
using the TeamMigrationMap to resolve vNext â†’ legacy team IDs.

Call `sync_primary_team(user)` after any membership lifecycle event:
  - Member added (create_membership / accept invite)
  - Member removed / kicked
  - Member leaves team
  - Transfer ownership

This module also provides `get_career_memberships(user_profile)` as a
unified query that merges both legacy and vNext memberships for the
career tab service.
"""
from __future__ import annotations

import logging
from typing import Optional

from django.apps import apps
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


def sync_primary_team(user) -> bool:
    """
    Ensure UserProfile.primary_team reflects the user's active organization
    membership.

    Logic:
      1. If user has an active org membership AND primary_team is NULL:
         â†’ Set primary_team to the legacy Team equivalent (via TeamMigrationMap)
      2. If user has NO active org memberships AND primary_team is set:
         â†’ Clear primary_team (user has no team)
      3. If user's current primary_team doesn't match any active membership:
         â†’ Update to the first active team found

    Returns True if primary_team was changed, False otherwise.
    """
    try:
        UserProfile = apps.get_model("user_profile", "UserProfile")
        VNextTeam = apps.get_model("organizations", "Team")
        VNextMembership = apps.get_model("organizations", "TeamMembership")
        LegacyTeam = apps.get_model("organizations", "Team")
        TeamMigrationMap = apps.get_model("organizations", "TeamMigrationMap")
    except LookupError as e:
        logger.warning("profile_sync: model not found â€” %s", e)
        return False

    profile = getattr(user, "profile", None)
    if not profile:
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            return False

    # Get user's active vNext memberships ordered by joined_at
    active_memberships = (
        VNextMembership.objects
        .filter(user=user, status='ACTIVE')
        .exclude(status="REMOVED")
        .select_related("team")
        .order_by("joined_at")
    )

    if not active_memberships.exists():
        # No active memberships â€” clear primary_team if set
        if profile.primary_team_id:
            profile.primary_team = None
            profile.save(update_fields=["primary_team"])
            logger.info(
                "profile_sync: cleared primary_team for user %s (no active memberships)",
                user.pk,
            )
            return True
        return False

    # Get legacy team IDs for all active vNext teams
    vnext_team_ids = list(active_memberships.values_list("team_id", flat=True))
    mappings = dict(
        TeamMigrationMap.objects
        .filter(vnext_team_id__in=vnext_team_ids)
        .values_list("vnext_team_id", "legacy_team_id")
    )

    # Check if current primary_team matches any active membership
    if profile.primary_team_id:
        current_legacy_ids = set(mappings.values())
        if profile.primary_team_id in current_legacy_ids:
            # Current primary_team is valid â€” no change needed
            return False

    # Pick the first active team's legacy equivalent
    for vnext_id in vnext_team_ids:
        legacy_id = mappings.get(vnext_id)
        if legacy_id:
            try:
                legacy_team = LegacyTeam.objects.get(id=legacy_id)
                profile.primary_team = legacy_team
                profile.save(update_fields=["primary_team"])
                logger.info(
                    "profile_sync: set primary_team=%s for user %s (vNext team %s)",
                    legacy_id, user.pk, vnext_id,
                )
                return True
            except LegacyTeam.DoesNotExist:
                continue

    # No legacy mapping found â€” try to create via dual-write if possible
    first_membership = active_memberships.first()
    if first_membership:
        try:
            from apps.organizations.services.dual_write_service import DualWriteService
            result = DualWriteService.sync_team_created(first_membership.team_id)
            if result.get("success") and result.get("legacy_team_id"):
                legacy_team = LegacyTeam.objects.get(id=result["legacy_team_id"])
                profile.primary_team = legacy_team
                profile.save(update_fields=["primary_team"])
                logger.info(
                    "profile_sync: created legacy mapping and set primary_team=%s for user %s",
                    result["legacy_team_id"], user.pk,
                )
                return True
        except Exception as e:
            logger.warning("profile_sync: dual-write fallback failed â€” %s", e)

    return False


def get_unified_memberships(user_profile) -> list:
    """
    Return a unified list of membership dicts from BOTH legacy and vNext
    systems, deduplicated by team slug.

    Each dict contains:
        team_name, team_slug, team_tag, game, role, roster_slot,
        joined_at, status, source ('legacy' or 'vnext')

    Used by the career tab service to show complete team history.
    """
    try:
        LegacyMembership = apps.get_model("organizations", "TeamMembership")
        VNextMembership = apps.get_model("organizations", "TeamMembership")
    except LookupError:
        return []

    results = {}
    seen_slugs = set()

    # 1. Query vNext memberships (preferred / authoritative)
    vnext_qs = (
        VNextMembership.objects
        .filter(user=user_profile.user)
        .select_related("team")
        .order_by("-joined_at")
    )
    for m in vnext_qs:
        slug = m.team.slug
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        results[slug] = {
            "team_name": m.team.name,
            "team_slug": slug,
            "team_tag": getattr(m.team, "tag", ""),
            "game": str(getattr(m.team, "game_id", "")),
            "role": m.role,
            "roster_slot": getattr(m, "roster_slot", ""),
            "joined_at": m.joined_at,
            "left_at": getattr(m, "left_at", None),
            "status": getattr(m, "status", "ACTIVE"),
            "is_active": m.is_active,
            "source": "vnext",
        }

    # 2. Query legacy memberships (fill gaps)
    legacy_qs = (
        LegacyMembership.objects
        .filter(user=user_profile.user)
        .select_related("team")
        .order_by("-joined_at")
    )
    for m in legacy_qs:
        slug = m.team.slug
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        results[slug] = {
            "team_name": m.team.name,
            "team_slug": slug,
            "team_tag": getattr(m.team, "tag", ""),
            "game": getattr(m.team, "game", ""),
            "role": getattr(m, "role", ""),
            "roster_slot": getattr(m, "roster_slot", ""),
            "joined_at": m.joined_at,
            "left_at": getattr(m, "left_at", None),
            "status": getattr(m, "status", "ACTIVE"),
            "is_active": getattr(m, "is_active", True),
            "source": "legacy",
        }

    # Sort by joined_at descending
    return sorted(results.values(), key=lambda x: x.get("joined_at") or "", reverse=True)
