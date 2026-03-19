"""
Automated Match Ingestion Service — Phase 1 (AUTOMATED_TOURNAMENTS_ROADMAP.md)

Handles writing API-fetched match results to the database in an idempotent,
atomic way.  Called by provider-specific fetchers (Riot, Steam) after raw
result data has been parsed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.tournaments.models.match import Match
from apps.tournaments.models.result_submission import MatchResultSubmission

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data transfer object returned by provider parsers
# ---------------------------------------------------------------------------

@dataclass
class ParsedMatchResult:
    """
    Normalised result extracted from a provider API response.

    winner_slot: 1 → participant1 wins, 2 → participant2 wins
    game_scores: list of per-game dicts for BO3/BO5 series
                 e.g. [{"game": 1, "p1": 13, "p2": 8, "winner_slot": 1}]
    """
    winner_slot: int          # 1 or 2
    participant1_score: int   # series wins
    participant2_score: int
    game_scores: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Ingestion service
# ---------------------------------------------------------------------------

class MatchIngestionService:
    """
    Write an API-fetched match result into the database.

    Usage::

        from apps.tournament_ops.services.match_ingestion_service import (
            MatchIngestionService, ParsedMatchResult,
        )

        service = MatchIngestionService()
        submission = service.ingest(
            match=match,
            parsed_result=ParsedMatchResult(winner_slot=1, participant1_score=2, participant2_score=0),
            raw_payload=raw_api_response,
            source=MatchResultSubmission.SOURCE_RIOT_API,
            ingestion_fingerprint="riot:APAC1-12345",
        )
    """

    def ingest(
        self,
        match: Match,
        parsed_result: ParsedMatchResult,
        raw_payload: dict[str, Any],
        source: str,
        ingestion_fingerprint: str,
    ) -> MatchResultSubmission:
        """
        Atomically write a match result and create a MatchResultSubmission.

        Returns the existing submission if the fingerprint has already been
        processed (idempotent — safe to retry).

        Steps:
        1. Idempotency guard via ingestion_fingerprint unique constraint.
        2. Update Match scores, winner, state → COMPLETED.
        3. Create MatchResultSubmission(status=AUTO_CONFIRMED, source=source).
        4. Queue bracket advancement task (fire-and-forget).
        """
        # --- 1. Idempotency guard ------------------------------------------
        existing = MatchResultSubmission.objects.filter(
            ingestion_fingerprint=ingestion_fingerprint
        ).first()
        if existing:
            logger.info(
                "[MatchIngestion] Fingerprint '%s' already ingested (submission_id=%s) — skipping.",
                ingestion_fingerprint,
                existing.pk,
            )
            return existing

        now = timezone.now()

        with transaction.atomic():
            # --- 2. Update Match -------------------------------------------
            winner_id = (
                match.participant1_id
                if parsed_result.winner_slot == 1
                else match.participant2_id
            )
            loser_id = (
                match.participant2_id
                if parsed_result.winner_slot == 1
                else match.participant1_id
            )

            match.participant1_score = parsed_result.participant1_score
            match.participant2_score = parsed_result.participant2_score
            match.winner_id = winner_id
            match.loser_id = loser_id
            match.game_scores = parsed_result.game_scores
            match.state = Match.COMPLETED
            match.completed_at = now
            match.save(update_fields=[
                "participant1_score",
                "participant2_score",
                "winner_id",
                "loser_id",
                "game_scores",
                "state",
                "completed_at",
                "updated_at",
            ])

            # --- 3. Create submission ---------------------------------------
            # submitted_by_user is a required FK; use the match's first participant's
            # user as a proxy.  When a true system-user sentinel is added to the
            # codebase this can be swapped out without changing the rest of the logic.
            submitter = _resolve_submitter(match)

            try:
                submission = MatchResultSubmission.objects.create(
                    match=match,
                    submitted_by_user=submitter,
                    raw_result_payload=raw_payload,
                    status=MatchResultSubmission.STATUS_AUTO_CONFIRMED,
                    source=source,
                    ingestion_fingerprint=ingestion_fingerprint,
                    ingested_at=now,
                    # Deadline in the past — submission is already confirmed.
                    auto_confirm_deadline=now,
                )
            except IntegrityError:
                # Race condition: another worker beat us to it.
                submission = MatchResultSubmission.objects.get(
                    ingestion_fingerprint=ingestion_fingerprint
                )
                logger.warning(
                    "[MatchIngestion] Race condition on fingerprint '%s' — returning existing submission %s.",
                    ingestion_fingerprint,
                    submission.pk,
                )
                return submission

        logger.info(
            "[MatchIngestion] Ingested: match_id=%s submission_id=%s source=%s fingerprint=%s",
            match.pk,
            submission.pk,
            source,
            ingestion_fingerprint,
        )

        # --- 4. Advance bracket (deferred import to avoid circular deps) ---
        try:
            from apps.tournament_ops.tasks.match_polling import advance_bracket_after_match
            advance_bracket_after_match.delay(match.pk)
        except Exception:
            logger.exception(
                "[MatchIngestion] Failed to queue bracket advancement for match_id=%s", match.pk
            )

        return submission


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_submitter(match: Match):
    """
    Return a User instance to attach as submitted_by_user.

    Preference order:
    1. User linked to participant1 Registration (if solo tournament)
    2. First team member of participant1 Registration
    3. The tournament's created_by user (organizer fallback)

    This avoids a hard dependency on a sentinel system user while the
    SYSTEM_USER_ID setting is not yet universally available.
    """
    from django.contrib.auth import get_user_model
    from apps.tournaments.models.registration import Registration

    User = get_user_model()

    try:
        reg = Registration.objects.select_related("user", "tournament__created_by").get(
            pk=match.participant1_id,
            tournament=match.tournament,
        )
        if reg.user_id:
            return reg.user
    except Registration.DoesNotExist:
        pass

    # Fallback to tournament organizer
    try:
        return match.tournament.created_by
    except Exception:
        pass

    # Last resort — first superuser
    return User.objects.filter(is_superuser=True).order_by("pk").first()
