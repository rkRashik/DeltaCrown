"""
Match Integrity Check — Phase 1 (AUTOMATED_TOURNAMENTS_ROADMAP.md)

Validates that the players found in an API-fetched match payload are the same
people registered for that match.  Unregistered PUUIDs / Steam IDs indicate a
potential smurf account or wrong match submission.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from apps.tournaments.models.match import Match
from apps.tournaments.models.registration import Registration
from apps.user_profile.models import ProviderAccount

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config — games where every player must be registered (no extras allowed)
# ---------------------------------------------------------------------------

INTEGRITY_STRICT_GAMES: frozenset[str] = frozenset({"valorant"})
INTEGRITY_RELAXED_GAMES: frozenset[str] = frozenset({"cs2", "dota2"})


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class IntegrityCheckResult:
    passed: bool
    unregistered_ids: list[str] = field(default_factory=list)
    absent_registered_ids: list[str] = field(default_factory=list)
    notes: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_participant_puuids(
    match: Match,
    payload_provider_ids: set[str],
    provider: str = ProviderAccount.Provider.RIOT,
) -> IntegrityCheckResult:
    """
    Cross-reference provider IDs found in the match payload against the
    ProviderAccount records of the registered participants.

    Args:
        match: The Match instance being validated.
        payload_provider_ids: Set of provider IDs (PUUIDs / Steam64 IDs)
            extracted from the raw API response.
        provider: Which ProviderAccount.Provider to look up (default: RIOT).

    Returns:
        IntegrityCheckResult with:
            - passed=True if all payload IDs are registered (strict mode) or
              no more than 1 unregistered ID (relaxed mode).
            - unregistered_ids: IDs in payload not found in any registration.
            - absent_registered_ids: Registered IDs not present in payload.
    """
    p1_ids = _get_provider_ids_for_participant(match.participant1_id, match, provider)
    p2_ids = _get_provider_ids_for_participant(match.participant2_id, match, provider)
    registered_ids = p1_ids | p2_ids

    game_slug = ""
    try:
        game_slug = match.tournament.game.slug.lower()
    except Exception:
        pass

    strict = game_slug in INTEGRITY_STRICT_GAMES
    relaxed = game_slug in INTEGRITY_RELAXED_GAMES

    unregistered = list(payload_provider_ids - registered_ids)
    absent = list(registered_ids - payload_provider_ids)

    if not unregistered and not absent:
        return IntegrityCheckResult(passed=True)

    if relaxed and len(unregistered) <= 1 and not absent:
        # Allow ±1 for coach / observer slots
        return IntegrityCheckResult(
            passed=True,
            unregistered_ids=unregistered,
            notes="Within relaxed tolerance (±1 non-registered slot allowed)",
        )

    passed = False
    notes_parts = []
    if unregistered:
        notes_parts.append(
            f"{len(unregistered)} unregistered ID(s) in match payload: "
            + ", ".join(unregistered[:5])
            + ("..." if len(unregistered) > 5 else "")
        )
    if absent:
        notes_parts.append(
            f"{len(absent)} registered participant(s) absent from payload: "
            + ", ".join(absent[:5])
            + ("..." if len(absent) > 5 else "")
        )

    result = IntegrityCheckResult(
        passed=passed,
        unregistered_ids=unregistered,
        absent_registered_ids=absent,
        notes="; ".join(notes_parts),
    )

    logger.warning(
        "[IntegrityCheck] match_id=%s game=%s FAILED: %s",
        match.pk,
        game_slug,
        result.notes,
    )
    return result


def flag_integrity_failure(
    match: Match,
    submission,
    integrity_result: IntegrityCheckResult,
) -> None:
    """
    Transition a match to DISPUTED and create a DisputeRecord when an
    integrity check has failed.

    Args:
        match: The Match instance.
        submission: The MatchResultSubmission that was auto-ingested.
        integrity_result: The failed IntegrityCheckResult.
    """
    from django.db import transaction
    from apps.tournaments.models.dispute import DisputeRecord

    with transaction.atomic():
        submission.status = submission.STATUS_DISPUTED
        submission.save(update_fields=["status"])

        match.state = Match.DISPUTED
        match.save(update_fields=["state", "updated_at"])

        DisputeRecord.objects.create(
            submission=submission,
            reason_code=DisputeRecord.REASON_CHEATING_SUSPICION,
            status=DisputeRecord.OPEN,
            description=(
                "Automated integrity check failed: "
                + integrity_result.notes
            ),
            flagged_by_system=True,
        )

    logger.warning(
        "[IntegrityCheck] match_id=%s flagged DISPUTED. Notes: %s",
        match.pk,
        integrity_result.notes,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_provider_ids_for_participant(
    participant_id: int | None,
    match: Match,
    provider: str,
) -> set[str]:
    """Return the set of provider IDs for all users in a Registration."""
    if not participant_id:
        return set()

    try:
        reg = Registration.objects.select_related("user").get(
            pk=participant_id,
            tournament_id=match.tournament_id,
        )
    except Registration.DoesNotExist:
        logger.warning(
            "[IntegrityCheck] Registration pk=%s not found for match_id=%s",
            participant_id,
            match.pk,
        )
        return set()

    if reg.team_id:
        # Team tournament: look up provider accounts for all team members.
        # Lazy import to avoid circular dependency with the players/teams app.
        user_ids = _get_team_member_user_ids(reg.team_id)
    else:
        user_ids = [reg.user_id] if reg.user_id else []

    if not user_ids:
        return set()

    return set(
        ProviderAccount.objects.filter(
            provider=provider,
            user_id__in=user_ids,
        ).values_list("provider_account_id", flat=True)
    )


def _get_team_member_user_ids(team_id: int) -> list[int]:
    """
    Return user IDs for all active members of a team.

    Uses a lazy import of the organizations/players app so this module
    doesn't force a import-time dependency on the teams model.
    """
    try:
        from apps.organizations.models import TeamMember
        return list(
            TeamMember.objects.filter(
                team_id=team_id,
                is_active=True,
            ).values_list("user_id", flat=True)
        )
    except Exception:
        pass

    try:
        from apps.players.models import TeamMember
        return list(
            TeamMember.objects.filter(
                team_id=team_id,
                is_active=True,
            ).values_list("user_id", flat=True)
        )
    except Exception:
        logger.warning(
            "[IntegrityCheck] Could not resolve team members for team_id=%s", team_id
        )
        return []
