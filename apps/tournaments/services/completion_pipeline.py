"""
Tournament Completion Pipeline — Post-completion processing.

Once a tournament transitions to COMPLETED status, this pipeline handles:
1. Final standings calculation and persistence
2. Winner determination and prize allocation
3. Certificate generation triggers
4. Statistics and analytics snapshot
5. Participant notification

Usage (called automatically by the wrapup task, or manually):
    from apps.tournaments.services.completion_pipeline import CompletionPipeline
    report = CompletionPipeline.run(tournament_id=42, actor=request.user)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament

logger = logging.getLogger(__name__)


@dataclass
class CompletionReport:
    """Result of running the completion pipeline for one tournament."""

    tournament_id: int
    tournament_name: str
    status: str = 'success'
    winners: List[Dict[str, Any]] = field(default_factory=list)
    standings_count: int = 0
    certificates_queued: int = 0
    notifications_sent: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == 'success'


class CompletionPipeline:
    """
    Orchestrates the post-completion processing steps.

    Each step is isolated so that a failure in one (e.g. certificate
    generation) does not block the others.  Errors are collected in the
    returned ``CompletionReport``.
    """

    @classmethod
    def run(
        cls,
        tournament_id: int,
        *,
        actor=None,
        skip_certificates: bool = False,
        skip_notifications: bool = False,
    ) -> CompletionReport:
        """
        Execute all completion steps for a tournament.

        Args:
            tournament_id: PK of the tournament (must be COMPLETED).
            actor: User who triggered the pipeline (None = system).
            skip_certificates: If True, don't queue certificate generation.
            skip_notifications: If True, don't send participant notifications.

        Returns:
            CompletionReport with details of each step.

        Raises:
            Tournament.DoesNotExist: If tournament not found.
            ValidationError: If tournament is not in COMPLETED status.
        """
        tournament = Tournament.objects.select_related('game', 'organizer').get(id=tournament_id)

        if tournament.status != Tournament.COMPLETED:
            raise ValidationError(
                f"Completion pipeline requires COMPLETED status, got '{tournament.status}'"
            )

        report = CompletionReport(
            tournament_id=tournament.id,
            tournament_name=tournament.name,
        )

        # Step 1: Final standings
        cls._step_standings(tournament, report)

        # Step 2: Winner determination
        cls._step_winners(tournament, report)

        # Step 3: Certificates
        if not skip_certificates:
            cls._step_certificates(tournament, report)

        # Step 4: Analytics snapshot
        cls._step_analytics(tournament, report)

        # Step 5: Notifications
        if not skip_notifications:
            cls._step_notifications(tournament, report, actor)

        # Persist pipeline metadata in config
        cls._save_pipeline_metadata(tournament, report)

        if report.errors:
            report.status = 'partial'
            logger.warning(
                "Completion pipeline for %s finished with %d error(s): %s",
                tournament.name, len(report.errors), report.errors,
            )
        else:
            logger.info(
                "Completion pipeline for %s finished successfully: "
                "%d winners, %d standings, %d certificates",
                tournament.name, len(report.winners),
                report.standings_count, report.certificates_queued,
            )

        return report

    # ── step implementations ───────────────────────────────────────────

    @classmethod
    def _step_standings(cls, tournament: Tournament, report: CompletionReport) -> None:
        """Calculate and persist final standings."""
        try:
            from apps.tournaments.services.group_stage_service import GroupStageService
            from apps.tournaments.models.group import Group

            # For group playoff format, recalculate group standings
            if tournament.format == Tournament.GROUP_PLAYOFF:
                groups = Group.objects.filter(tournament=tournament, is_deleted=False)
                for group in groups:
                    GroupStageService.calculate_standings(
                        group_id=group.id,
                        game_slug=tournament.game.slug,
                    )
                report.standings_count += groups.count()

            # Overall standings from bracket/matches
            from apps.tournaments.models.match import Match

            completed_matches = Match.objects.filter(
                tournament=tournament,
                state='completed',
                is_deleted=False,
            ).count()
            report.standings_count += completed_matches

            logger.info("[completion] Standings calculated for %s", tournament.name)
        except Exception as e:
            report.errors.append(f"standings: {e}")
            logger.exception("[completion] Standings failed for %s", tournament.name)

    @classmethod
    def _step_winners(cls, tournament: Tournament, report: CompletionReport) -> None:
        """Determine and persist tournament winners."""
        try:
            from apps.tournaments.services.winner_service import WinnerDeterminationService

            winners = WinnerDeterminationService.determine_winners(tournament.id)
            report.winners = [
                {
                    'place': w.get('place', idx + 1),
                    'name': w.get('name', 'Unknown'),
                    'prize': str(w.get('prize', '')),
                }
                for idx, w in enumerate(winners if isinstance(winners, list) else [])
            ]
            logger.info(
                "[completion] %d winner(s) determined for %s",
                len(report.winners), tournament.name,
            )
        except Exception as e:
            report.errors.append(f"winners: {e}")
            logger.exception("[completion] Winner determination failed for %s", tournament.name)

    @classmethod
    def _step_certificates(cls, tournament: Tournament, report: CompletionReport) -> None:
        """Queue certificate generation for all participants."""
        try:
            from apps.tournaments.services import CertificateService

            if CertificateService is None:
                report.errors.append("certificates: CertificateService not available (missing deps)")
                return

            from apps.tournaments.models.registration import Registration

            participants = Registration.objects.filter(
                tournament=tournament,
                status='confirmed',
                is_deleted=False,
            )
            count = 0
            for reg in participants.iterator():
                try:
                    CertificateService.generate_certificate(
                        tournament_id=tournament.id,
                        registration_id=reg.id,
                    )
                    count += 1
                except Exception as cert_err:
                    logger.warning(
                        "[completion] Certificate failed for reg %s: %s",
                        reg.id, cert_err,
                    )

            report.certificates_queued = count
            logger.info("[completion] %d certificates queued for %s", count, tournament.name)
        except Exception as e:
            report.errors.append(f"certificates: {e}")
            logger.exception("[completion] Certificate step failed for %s", tournament.name)

    @classmethod
    def _step_analytics(cls, tournament: Tournament, report: CompletionReport) -> None:
        """Create a final analytics snapshot."""
        try:
            from apps.tournaments.services.analytics_service import analytics_service

            if analytics_service:
                analytics_service.create_snapshot(tournament.id)
                logger.info("[completion] Analytics snapshot created for %s", tournament.name)
        except Exception as e:
            report.errors.append(f"analytics: {e}")
            logger.exception("[completion] Analytics snapshot failed for %s", tournament.name)

    @classmethod
    def _step_notifications(
        cls,
        tournament: Tournament,
        report: CompletionReport,
        actor=None,
    ) -> None:
        """Send completion notifications to all participants."""
        try:
            from apps.tournaments.services.notification_service import TournamentNotificationService

            count = TournamentNotificationService.notify_tournament_completed(
                tournament_id=tournament.id,
            )
            report.notifications_sent = count if isinstance(count, int) else 0
            logger.info(
                "[completion] %d notifications sent for %s",
                report.notifications_sent, tournament.name,
            )
        except Exception as e:
            report.errors.append(f"notifications: {e}")
            logger.exception("[completion] Notification step failed for %s", tournament.name)

    @classmethod
    def _save_pipeline_metadata(cls, tournament: Tournament, report: CompletionReport) -> None:
        """Persist pipeline results in the tournament config JSON field."""
        try:
            config = tournament.config or {}
            config['completion_pipeline'] = {
                'ran_at': timezone.now().isoformat(),
                'status': report.status,
                'winners_count': len(report.winners),
                'standings_count': report.standings_count,
                'certificates_queued': report.certificates_queued,
                'notifications_sent': report.notifications_sent,
                'errors': report.errors,
            }
            tournament.config = config
            tournament.save(update_fields=['config'])
        except Exception as e:
            logger.exception("[completion] Failed to save pipeline metadata: %s", e)
