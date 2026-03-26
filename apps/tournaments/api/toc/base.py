"""
TOC API — Base mixins for tournament lookup + permission checks.

All TOC API views inherit from TOCBaseView which:
1. Resolves the tournament from the URL slug
2. Checks organizer/staff permission
3. Injects self.tournament for subclasses
"""

import logging
import time

from django.core.cache import cache
from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.lifecycle_service import TournamentLifecycleService


logger = logging.getLogger("toc.request")


class TOCBaseView(APIView):
    """
    Base class for all TOC API endpoints.

    URL pattern: /api/toc/<slug:slug>/...
    """

    permission_classes = [IsAuthenticated]
    slow_request_ms = 250
    perf_counter_ttl_seconds = 60 * 90

    def get_tournament(self):
        slug = self.kwargs.get('slug')
        try:
            tournament = Tournament.objects.select_related('game', 'organizer').get(slug=slug)
            try:
                TournamentLifecycleService.auto_advance(tournament)
                tournament.refresh_from_db(fields=['status'])
            except Exception:
                pass
            return tournament
        except Tournament.DoesNotExist:
            raise Http404(f'Tournament not found: {slug}')

    def check_toc_permission(self, tournament, user):
        """Verify user has organizer-level access to this tournament."""
        if user.is_superuser or user.is_staff:
            return True
        if tournament.organizer_id == user.id:
            return True
        # Keep API permissions in parity with TOC shell access rules.
        from apps.tournaments.models.staffing import TournamentStaffAssignment
        return TournamentStaffAssignment.objects.filter(
            tournament=tournament,
            user=user,
            is_active=True,
        ).exists()

    def initial(self, request, *args, **kwargs):
        self._toc_request_started_at = time.perf_counter()
        super().initial(request, *args, **kwargs)
        self.tournament = self.get_tournament()
        if not self.check_toc_permission(self.tournament, request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have access to this tournament.')

    def finalize_response(self, request, response, *args, **kwargs):
        finalized = super().finalize_response(request, response, *args, **kwargs)

        started_at = getattr(self, '_toc_request_started_at', None)
        if started_at is None:
            return finalized

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        finalized['X-TOC-Elapsed-MS'] = str(elapsed_ms)

        status_code = getattr(finalized, 'status_code', 0)
        tournament_id = getattr(getattr(self, 'tournament', None), 'id', None)
        should_log = elapsed_ms >= self.slow_request_ms or status_code >= 400
        if should_log:
            logger.info(
                "TOC request method=%s view=%s path=%s status=%s elapsed_ms=%s tournament_id=%s user_id=%s",
                getattr(request, 'method', 'UNKNOWN'),
                self.__class__.__name__,
                getattr(request, 'path', ''),
                status_code,
                elapsed_ms,
                tournament_id,
                getattr(getattr(request, 'user', None), 'id', None),
            )

        if tournament_id:
            minute_bucket = int(time.time() // 60)
            prefix = f"toc:perf:{tournament_id}:{minute_bucket}"
            self._increment_perf_counter(f"{prefix}:total")
            if elapsed_ms >= self.slow_request_ms:
                self._increment_perf_counter(f"{prefix}:slow")
            if status_code >= 400:
                self._increment_perf_counter(f"{prefix}:error")

        return finalized

    def _increment_perf_counter(self, key: str) -> None:
        """Cache-safe increment with fallback for backends that don't support atomic incr."""
        try:
            cache.incr(key)
            cache.touch(key, timeout=self.perf_counter_ttl_seconds)
            return
        except Exception:
            pass

        current = cache.get(key)
        if current is None:
            cache.set(key, 1, timeout=self.perf_counter_ttl_seconds)
            return

        try:
            cache.set(key, int(current) + 1, timeout=self.perf_counter_ttl_seconds)
        except Exception:
            # Best-effort metrics only; never fail request flow.
            pass
