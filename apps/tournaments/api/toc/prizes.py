"""
TOC API — Prize Tab views.

Sits alongside the existing /prize-pool/ endpoints (which surface only the
legacy single-pool data). These endpoints back the modern Prize tab:

  GET  /api/toc/<slug>/prizes/        — full prize config + live placements
  POST /api/toc/<slug>/prizes/save/   — persist prize configuration
  POST /api/toc/<slug>/prizes/publish/ — recompute placements + persist

Permission: organizer/staff (TOCBaseView default).
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.cache_utils import bump_toc_scopes
from apps.tournaments.services.placement_service import PlacementService
from apps.tournaments.services.prize_config_service import PrizeConfigService

logger = logging.getLogger(__name__)


class PrizeConfigView(TOCBaseView):
    """GET /api/toc/<slug>/prizes/  — full prize config + live placements."""

    def get(self, request, slug):
        config = PrizeConfigService.get_config(self.tournament)
        public_payload = PrizeConfigService.public_payload(self.tournament)
        return Response({
            'config': config,
            'public_preview': public_payload,
        })


class PrizeConfigSaveView(TOCBaseView):
    """POST /api/toc/<slug>/prizes/save/  — persist prize configuration."""

    def post(self, request, slug):
        try:
            saved = PrizeConfigService.save_config(
                self.tournament, request.data or {}, actor=request.user,
            )
        except (TypeError, ValueError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        bump_toc_scopes(self.tournament.id, 'overview', 'analytics')
        return Response({'config': saved, 'status': 'saved'})


class PrizePublishView(TOCBaseView):
    """
    POST /api/toc/<slug>/prizes/publish/

    Re-derive placements (1..4 + standings) and persist them onto the
    TournamentResult. Idempotent. Safe to call any time post-completion.
    Returns the live public payload so the frontend can refresh in place.
    """

    def post(self, request, slug):
        try:
            PlacementService.persist_standings(self.tournament, actor=request.user)
        except Exception as e:
            logger.exception('Prize publish failed for %s', slug)
            return Response(
                {'error': str(e), 'status': 'failed'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        public_payload = PrizeConfigService.public_payload(self.tournament)
        bump_toc_scopes(self.tournament.id, 'overview', 'analytics', 'standings')
        return Response({'public_preview': public_payload, 'status': 'published'})
