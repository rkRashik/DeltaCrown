"""
TOC API Views — Sprint 7: Disputes.

S7-B1 GET  disputes/
S7-B2 GET  disputes/<id>/
S7-B3 POST disputes/<id>/resolve/
S7-B4 POST disputes/<id>/escalate/
S7-B5 POST disputes/<id>/assign/
S7-B6 POST disputes/<id>/add-evidence/
S7-B7 POST disputes/<id>/update-status/
"""

from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.cache_utils import bump_toc_scopes, toc_cache_key
from apps.tournaments.api.toc.disputes_service import TOCDisputesService


class DisputeListView(TOCBaseView):
    """S7-B1: Dispute queue with filters."""

    def get(self, request, slug):
        cache_bucket = int(timezone.now().timestamp() // 8)
        query_sig = request.META.get('QUERY_STRING', '')
        cache_key = toc_cache_key('disputes', self.tournament.id, cache_bucket, query_sig)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data = TOCDisputesService.get_disputes(
            self.tournament,
            status_filter=request.query_params.get('status'),
            search=request.query_params.get('search'),
        )
        open_count = TOCDisputesService.get_open_count(self.tournament)
        payload = {'disputes': data, 'open_count': open_count}
        cache.set(cache_key, payload, timeout=12)
        return Response(payload)


class DisputeDetailView(TOCBaseView):
    """S7-B2: Full dispute detail with evidence."""

    def get(self, request, slug, pk):
        cache_bucket = int(timezone.now().timestamp() // 8)
        cache_key = toc_cache_key('disputes', self.tournament.id, 'detail', pk, cache_bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data = TOCDisputesService.get_dispute_detail(pk, self.tournament)
        cache.set(cache_key, data, timeout=12)
        return Response(data)


class DisputeResolveView(TOCBaseView):
    """S7-B3: Issue ruling."""

    def post(self, request, slug, pk):
        data = TOCDisputesService.resolve_dispute(
            dispute_id=pk,
            tournament=self.tournament,
            ruling=request.data.get('ruling', 'submitter_wins'),
            resolution_notes=request.data.get('resolution_notes', ''),
            user_id=request.user.id,
        )
        bump_toc_scopes(self.tournament.id, 'disputes', 'matches', 'overview', 'analytics')
        return Response(data)


class DisputeEscalateView(TOCBaseView):
    """S7-B4: Escalate dispute."""

    def post(self, request, slug, pk):
        data = TOCDisputesService.escalate_dispute(
            dispute_id=pk,
            tournament=self.tournament,
            reason=request.data.get('reason', ''),
            user_id=request.user.id,
        )
        bump_toc_scopes(self.tournament.id, 'disputes', 'matches', 'overview', 'analytics')
        return Response(data)


class DisputeAssignView(TOCBaseView):
    """S7-B5: Assign to staff member."""

    def post(self, request, slug, pk):
        data = TOCDisputesService.assign_dispute(
            dispute_id=pk,
            tournament=self.tournament,
            staff_user_id=int(request.data.get('staff_user_id')),
        )
        bump_toc_scopes(self.tournament.id, 'disputes')
        return Response(data)


class DisputeAddEvidenceView(TOCBaseView):
    """S7-B6: Add evidence to dispute. Supports URL and/or file upload."""
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, slug, pk):
        from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
        evidence_file = request.FILES.get('evidence_file')
        data = TOCDisputesService.add_evidence(
            dispute_id=pk,
            tournament=self.tournament,
            evidence_type=request.data.get('evidence_type', 'screenshot'),
            url=request.data.get('url', ''),
            evidence_file=evidence_file,
            notes=request.data.get('notes', ''),
            user_id=request.user.id,
        )
        bump_toc_scopes(self.tournament.id, 'disputes')
        return Response(data, status=status.HTTP_201_CREATED)


class DisputeUpdateStatusView(TOCBaseView):
    """S7-B7: Change dispute status."""

    def post(self, request, slug, pk):
        data = TOCDisputesService.update_status(
            dispute_id=pk,
            tournament=self.tournament,
            new_status=request.data.get('status'),
        )
        bump_toc_scopes(self.tournament.id, 'disputes', 'matches', 'overview', 'analytics')
        return Response(data)
