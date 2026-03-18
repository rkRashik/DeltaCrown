"""
Event handler: match.completed → CP ranking update.

Subscribes to the core EventBus and delegates to
MatchResultIntegrator.process_match_result() so that every
completed tournament match feeds the Crown Point pipeline.
"""

import logging

logger = logging.getLogger(__name__)


def handle_match_completed_for_rankings(event):
    """
    Update vNext CP rankings when a match completes.

    Looks up the Match to obtain both winner and loser IDs, then
    delegates to the existing MatchResultIntegrator which handles
    feature-flag checks, vNext team detection, and CP application.
    """
    from apps.tournaments.models import Match
    from apps.organizations.services.match_integration import MatchResultIntegrator

    match_id = event.data.get("match_id")
    if not match_id:
        logger.warning("match.completed event missing match_id, skipping ranking update")
        return

    try:
        match = Match.objects.only(
            "id", "winner_id", "loser_id", "tournament_id", "state"
        ).get(id=match_id)
    except Match.DoesNotExist:
        logger.error("Match %s not found for ranking update", match_id)
        return

    if not match.winner_id or not match.loser_id:
        logger.debug("Match %s has no winner/loser yet, skipping", match_id)
        return

    result = MatchResultIntegrator.process_match_result(
        winner_team_id=match.winner_id,
        loser_team_id=match.loser_id,
        match_id=match.id,
        is_tournament_match=bool(match.tournament_id),
    )

    if result.success and result.vnext_processed:
        logger.info(
            "Match %s → CP updated (winner=%s, loser=%s, tier_changed=%s/%s)",
            match_id, match.winner_id, match.loser_id,
            result.winner_tier_changed, result.loser_tier_changed,
        )
    elif not result.success:
        logger.warning(
            "Match %s ranking update failed: %s", match_id, result.error_message
        )
