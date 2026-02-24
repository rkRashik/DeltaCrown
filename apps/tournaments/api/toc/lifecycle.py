"""
TOC API — Lifecycle Endpoints (Transition, Freeze, Unfreeze).

POST /api/toc/<slug>/lifecycle/transition/
POST /api/toc/<slug>/lifecycle/freeze/
POST /api/toc/<slug>/lifecycle/unfreeze/

Sprint 1: S1-B3, S1-B4, S1-B5
PRD: §2.2, §2.7
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.serializers import (
    FreezeInputSerializer,
    LifecycleTransitionInputSerializer,
    UnfreezeInputSerializer,
)
from apps.tournaments.api.toc.service import TOCService


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

        return Response({
            'message': 'Tournament unfrozen. Operations resumed.',
        })
