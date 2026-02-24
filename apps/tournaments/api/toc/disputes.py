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

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.disputes_service import TOCDisputesService


class DisputeListView(TOCBaseView):
    """S7-B1: Dispute queue with filters."""

    def get(self, request, slug):
        data = TOCDisputesService.get_disputes(
            self.tournament,
            status_filter=request.query_params.get('status'),
            search=request.query_params.get('search'),
        )
        open_count = TOCDisputesService.get_open_count(self.tournament)
        return Response({'disputes': data, 'open_count': open_count})


class DisputeDetailView(TOCBaseView):
    """S7-B2: Full dispute detail with evidence."""

    def get(self, request, slug, pk):
        data = TOCDisputesService.get_dispute_detail(pk, self.tournament)
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
        return Response(data)


class DisputeAssignView(TOCBaseView):
    """S7-B5: Assign to staff member."""

    def post(self, request, slug, pk):
        data = TOCDisputesService.assign_dispute(
            dispute_id=pk,
            tournament=self.tournament,
            staff_user_id=int(request.data.get('staff_user_id')),
        )
        return Response(data)


class DisputeAddEvidenceView(TOCBaseView):
    """S7-B6: Add evidence to dispute."""

    def post(self, request, slug, pk):
        data = TOCDisputesService.add_evidence(
            dispute_id=pk,
            tournament=self.tournament,
            evidence_type=request.data.get('evidence_type', 'screenshot'),
            url=request.data.get('url', ''),
            notes=request.data.get('notes', ''),
            user_id=request.user.id,
        )
        return Response(data, status=status.HTTP_201_CREATED)


class DisputeUpdateStatusView(TOCBaseView):
    """S7-B7: Change dispute status."""

    def post(self, request, slug, pk):
        data = TOCDisputesService.update_status(
            dispute_id=pk,
            tournament=self.tournament,
            new_status=request.data.get('status'),
        )
        return Response(data)
