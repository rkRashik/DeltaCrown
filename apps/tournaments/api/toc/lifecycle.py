"""
TOC API — Lifecycle Endpoints (Transition, Freeze, Unfreeze, Finalize).

POST /api/toc/<slug>/lifecycle/transition/
POST /api/toc/<slug>/lifecycle/freeze/
POST /api/toc/<slug>/lifecycle/unfreeze/
POST /api/toc/<slug>/lifecycle/finalize/

Sprint 1: S1-B3, S1-B4, S1-B5
PRD: §2.2, §2.7
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.cache_utils import bump_toc_scopes
from apps.tournaments.api.toc.serializers import (
    FreezeInputSerializer,
    LifecycleTransitionInputSerializer,
    UnfreezeInputSerializer,
)
from apps.tournaments.api.toc.service import TOCService
from apps.tournaments.services.lifecycle_service import TournamentLifecycleService


class LifecycleTransitionView(TOCBaseView):
    """
    POST — Trigger a lifecycle state transition.

    Body: {to_status, reason?, force?}
    Returns: {status, status_display, message}
    """

    def post(self, request, slug):
        serializer = LifecycleTransitionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        to_status = serializer.validated_data['to_status']
        reason = serializer.validated_data.get('reason', '')
        force = serializer.validated_data.get('force', False)

        # Only superusers can force
        if force and not request.user.is_superuser:
            return Response(
                {'error': 'Force override requires superuser permissions.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            updated = TOCService.execute_transition(
                self.tournament,
                to_status=to_status,
                actor=request.user,
                reason=reason,
                force=force,
            )
        except DjangoValidationError as e:
            return Response(
                {'error': str(e.message if hasattr(e, 'message') else e.messages[0])},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bump_toc_scopes(
            self.tournament.id,
            'overview', 'analytics', 'brackets', 'matches', 'participants', 'participants_adv', 'payments', 'disputes', 'rosters',
        )

        return Response({
            'status': updated.status,
            'status_display': updated.get_status_display(),
            'message': f'Transitioned to {updated.get_status_display()}.',
        })


class FreezeView(TOCBaseView):
    """
    POST — Execute Global Killswitch (§2.7).

    Body: {reason}
    Returns: {message, frozen_at}
    """

    def post(self, request, slug):
        serializer = FreezeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data['reason']

        try:
            updated = TOCService.freeze_tournament(
                self.tournament, actor=request.user, reason=reason,
            )
        except DjangoValidationError as e:
            return Response(
                {'error': str(e.message if hasattr(e, 'message') else e.messages[0])},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bump_toc_scopes(
            self.tournament.id,
            'overview', 'analytics', 'brackets', 'matches', 'participants', 'participants_adv', 'payments', 'disputes', 'rosters',
        )

        config = updated.config or {}
        frozen_at = config.get('frozen', {}).get('frozen_at', '')

        return Response({
            'message': 'Tournament frozen. All automation halted.',
            'frozen_at': frozen_at,
        })


class UnfreezeView(TOCBaseView):
    """
    POST — Lift Global Killswitch freeze.

    Body: {reason?}
    Returns: {message}
    """

    def post(self, request, slug):
        serializer = UnfreezeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get('reason', '')

        try:
            TOCService.unfreeze_tournament(
                self.tournament, actor=request.user, reason=reason,
            )
        except DjangoValidationError as e:
            return Response(
                {'error': str(e.message if hasattr(e, 'message') else e.messages[0])},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bump_toc_scopes(
            self.tournament.id,
            'overview', 'analytics', 'brackets', 'matches', 'participants', 'participants_adv', 'payments', 'disputes', 'rosters',
        )

        return Response({
            'message': 'Tournament unfrozen. Operations resumed.',
        })


class FinalizeView(TOCBaseView):
    """
    POST — Recovery action: finalize a LIVE tournament whose final match
    completed without auto-finalize firing (legacy data, signal failure,
    bracket structure missing, etc.).

    Body: {force?: bool}
        force=true bypasses the "all matches completed" guard. Superuser only.

    Returns: {finalized, status, status_display, message}
    """

    def post(self, request, slug):
        force = bool(request.data.get('force', False))

        if force and not request.user.is_superuser:
            return Response(
                {'error': 'Force finalize requires superuser permissions.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Idempotent path #1: if a TournamentResult with winner already exists
        # OR the tournament is already COMPLETED, this becomes a sync-and-return
        # (rather than an error). Run PlacementService once so standings are
        # populated even on the legacy path.
        from apps.tournaments.models.tournament import Tournament as _T
        from apps.tournaments.models.result import TournamentResult as _TR

        try:
            already_has_winner = _TR.objects.filter(
                tournament_id=self.tournament.id, is_deleted=False,
            ).exclude(winner_id__isnull=True).exists()
        except Exception:
            already_has_winner = False

        if self.tournament.status == _T.COMPLETED or already_has_winner:
            # Sync persisted status if it drifted from effective.
            if self.tournament.status != _T.COMPLETED and already_has_winner:
                try:
                    TournamentLifecycleService.transition(
                        self.tournament.id, _T.COMPLETED,
                        actor=request.user,
                        reason='Idempotent finalize sync — TournamentResult winner present',
                        force=True,
                    )
                except Exception as e:
                    # Non-blocking — we still report idempotent success below.
                    import logging
                    logging.getLogger(__name__).warning(
                        'Finalize sync transition failed for %s: %s',
                        self.tournament.id, e,
                    )
            # Re-run the full post-finalization pipeline so standings,
            # achievements, announcement, and caches converge — even if the
            # original finalize fired but its downstream steps were partial.
            try:
                from apps.tournaments.services.post_finalization_service import (
                    PostFinalizationService,
                )
                PostFinalizationService.run(
                    self.tournament, actor=request.user,
                )
            except Exception:
                import logging
                logging.getLogger(__name__).exception(
                    'Idempotent post-finalization failed for %s',
                    self.tournament.id,
                )
            bump_toc_scopes(
                self.tournament.id,
                'overview', 'analytics', 'brackets', 'matches',
                'prizes', 'announcements',
            )
            self.tournament.refresh_from_db()
            return Response({
                'finalized': True,
                'idempotent': True,
                'already_completed': True,
                'status': self.tournament.status,
                'status_display': self.tournament.get_status_display(),
                'message': (
                    'Finalization confirmed. Standings, prizes, achievements, '
                    'and announcements are up to date. Refresh to see the '
                    'completed state.'
                ),
            })

        finalized, reason = TournamentLifecycleService.maybe_finalize_tournament(
            self.tournament.id,
            actor=request.user,
            force=force,
        )

        if not finalized:
            return Response(
                {
                    'finalized': False,
                    'status': self.tournament.status,
                    'reason': reason or 'Could not finalize.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bump_toc_scopes(
            self.tournament.id,
            'overview', 'analytics', 'brackets', 'matches',
            'participants', 'participants_adv', 'payments',
            'disputes', 'rosters',
        )

        self.tournament.refresh_from_db()
        return Response({
            'finalized': True,
            'status': self.tournament.status,
            'status_display': self.tournament.get_status_display(),
            'message': f'Tournament finalized: {self.tournament.get_status_display()}.',
        })
