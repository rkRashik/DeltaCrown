"""Dropzone API views."""
from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.economy.exceptions import InsufficientFunds

from .models import RoyaleEntry, RoyaleLobby
from .serializers import (
    RoyaleEntrySerializer,
    RoyaleLobbyDetailSerializer,
    RoyaleLobbyListSerializer,
)
from .services import RoyaleService


logger = logging.getLogger(__name__)


def _redact_room_credentials(lobby: RoyaleLobby, viewer) -> dict:
    """Serialize a lobby — but blank out room_id/password until match time.

    Confirmed entrants see credentials immediately at scheduled_at.
    Spectators / non-entrants never see credentials.
    """
    data = RoyaleLobbyDetailSerializer(lobby).data
    now = timezone.now()
    is_entrant = (
        viewer.is_authenticated
        and RoyaleEntry.objects.filter(
            lobby=lobby, user=viewer,
            status__in=['RESERVED', 'CONFIRMED', 'SCORED', 'NO_SHOW'],
        ).exists()
    )
    if not is_entrant or now < lobby.scheduled_at:
        data['room_id'] = ''
        data['room_password'] = ''
    return data


class RoyaleLobbyListView(APIView):
    """``GET /api/v1/royale/lobbies/`` — list scheduled custom rooms."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        game_id = request.query_params.get('game')
        status_filter = request.query_params.get('status')

        qs = RoyaleLobby.objects.filter(is_public=True).select_related('game')
        if game_id:
            qs = qs.filter(game_id=game_id)
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        else:
            qs = qs.exclude(status__in=['SETTLED', 'CANCELLED'])

        return Response(
            RoyaleLobbyListSerializer(qs[:50], many=True).data
        )


class RoyaleLobbyDetailView(APIView):
    """``GET /api/v1/royale/lobbies/<id>/`` — full lobby state.

    Room credentials are redacted unless the viewer has a confirmed entry
    in the lobby AND the scheduled match time has passed.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, lobby_id):
        lobby = get_object_or_404(
            RoyaleLobby.objects.select_related('game'),
            pk=lobby_id,
        )
        return Response(_redact_room_credentials(lobby, request.user))


class RoyaleReserveView(APIView):
    """``POST /api/v1/royale/lobbies/<id>/reserve/`` — pay entry fee + reserve a slot."""

    permission_classes = [IsAuthenticated]

    def post(self, request, lobby_id):
        try:
            entry = RoyaleService.reserve_slot(
                user=request.user,
                lobby_id=lobby_id,
            )
        except InsufficientFunds as e:
            return Response(
                {'detail': str(e), 'code': 'INSUFFICIENT_FUNDS'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            RoyaleEntrySerializer(entry).data,
            status=status.HTTP_201_CREATED,
        )


class RoyaleCancelReservationView(APIView):
    """``POST /api/v1/royale/entries/<id>/cancel/`` — cancel a slot pre-match."""

    permission_classes = [IsAuthenticated]

    def post(self, request, entry_id):
        entry = get_object_or_404(
            RoyaleEntry.objects.select_related('lobby'), pk=entry_id
        )
        if entry.user_id != request.user.id and not request.user.is_staff:
            return Response(
                {'detail': 'Not allowed.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            entry = RoyaleService.cancel_reservation(
                entry_id=entry_id, actor=request.user
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RoyaleEntrySerializer(entry).data)


class MyRoyaleEntriesView(APIView):
    """``GET /api/v1/royale/my/`` — list the current user's reservations."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = RoyaleEntry.objects.filter(user=request.user).select_related(
            'lobby', 'lobby__game'
        )
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return Response(RoyaleEntrySerializer(qs[:50], many=True).data)
