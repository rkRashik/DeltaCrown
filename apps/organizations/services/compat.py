"""
Legacy ↔ vNext compatibility helpers.

Provides bridge utilities for code that may still reference team IDs
from the legacy ``teams_team`` table while the codebase migrates to
``organizations_team``.

Created during Phase-A legacy removal — can be deleted once all FK
columns in the DB are fully migrated to organizations.Team IDs.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from django.apps import apps

logger = logging.getLogger(__name__)


# ─── Team ID bridge ──────────────────────────────────────────────────

def get_team_by_any_id(team_id: int):
    """Resolve an ``organizations.Team`` from *either* an org PK or a legacy PK.

    During the migration period, some tables (registrations, lobby slots,
    etc.) still store ``teams_team.id`` values.  This helper tries the org
    table first, then falls back to the ``TeamMigrationMap`` to translate
    legacy IDs.

    Returns ``None`` when the team cannot be found in either table.
    """
    Team = apps.get_model("organizations", "Team")
    TeamMigrationMap = apps.get_model("organizations", "TeamMigrationMap")

    # Fast path — try the org table directly
    try:
        return Team.objects.get(pk=team_id)
    except Team.DoesNotExist:
        pass

    # Slow path — translate via migration map
    try:
        mapping = TeamMigrationMap.objects.get(legacy_team_id=team_id)
        return Team.objects.get(pk=mapping.vnext_team_id)
    except (TeamMigrationMap.DoesNotExist, Team.DoesNotExist):
        logger.warning(
            "get_team_by_any_id: no org team found for id=%s", team_id
        )
        return None


def legacy_id_to_org_id(legacy_team_id: int) -> int | None:
    """Translate a single legacy ``teams_team.id`` → ``organizations_team.id``.

    Returns ``None`` when no mapping exists.
    """
    TeamMigrationMap = apps.get_model("organizations", "TeamMigrationMap")
    try:
        return TeamMigrationMap.objects.values_list(
            "vnext_team_id", flat=True
        ).get(legacy_team_id=legacy_team_id)
    except TeamMigrationMap.DoesNotExist:
        return None


def org_id_to_legacy_id(org_team_id: int) -> int | None:
    """Translate a single ``organizations_team.id`` → ``teams_team.id``."""
    TeamMigrationMap = apps.get_model("organizations", "TeamMigrationMap")
    try:
        return TeamMigrationMap.objects.values_list(
            "legacy_team_id", flat=True
        ).get(vnext_team_id=org_team_id)
    except TeamMigrationMap.DoesNotExist:
        return None


# ─── Membership bridge ───────────────────────────────────────────────

def user_from_profile(profile):
    """Given a ``UserProfile`` instance, return the associated ``User``.

    Convenience for code that was written against the legacy
    ``TeamMembership.profile`` FK and is now calling
    ``TeamMembership.objects.filter(user=...)``.
    """
    if profile is None:
        return None
    return getattr(profile, "user", None)
