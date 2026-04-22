"""TOC API views for Match Center presentation controls."""

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.match_center_service import TOCMatchCenterService


class MatchCenterConfigView(TOCBaseView):
    """Read and update public Match Center configuration for a tournament."""

    def get(self, request, slug):
        payload = TOCMatchCenterService.get_config(self.tournament)
        return Response(payload)

    def post(self, request, slug):
        payload = TOCMatchCenterService.update_config(self.tournament, request.data)
        return Response(payload, status=status.HTTP_200_OK)
