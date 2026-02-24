"""
TOC API — Base mixins for tournament lookup + permission checks.

All TOC API views inherit from TOCBaseView which:
1. Resolves the tournament from the URL slug
2. Checks organizer/staff permission
3. Injects self.tournament for subclasses
"""

from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tournaments.models.tournament import Tournament


class TOCBaseView(APIView):
    """
    Base class for all TOC API endpoints.

    URL pattern: /api/toc/<slug:slug>/...
    """

    permission_classes = [IsAuthenticated]

    def get_tournament(self):
        slug = self.kwargs.get('slug')
        try:
            return Tournament.objects.select_related('game', 'organizer').get(slug=slug)
        except Tournament.DoesNotExist:
            raise Http404(f'Tournament not found: {slug}')

    def check_toc_permission(self, tournament, user):
        """Verify user has organizer-level access to this tournament."""
        if user.is_superuser or user.is_staff:
            return True
        if tournament.organizer_id == user.id:
            return True
        return False

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.tournament = self.get_tournament()
        if not self.check_toc_permission(self.tournament, request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have access to this tournament.')
