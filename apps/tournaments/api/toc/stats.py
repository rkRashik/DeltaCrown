"""
TOC Sprint 9 — Stats, Certificates & Trust Index API Views
===========================================================
S9-B1  Tournament stats summary
S9-B2  Certificate template CRUD + generate / download
S9-B3  Trophy / achievement endpoints
S9-B4  Trust Index read
S9-B5  Trust event log
"""

from rest_framework import status
from rest_framework.response import Response

from .base import TOCBaseView
from .stats_service import TOCStatsService


# ------------------------------------------------------------------
# S9-B1  Stats Summary
# ------------------------------------------------------------------
class StatsOverviewView(TOCBaseView):
    """GET — aggregated tournament stats."""

    def get(self, request, slug):
        svc = TOCStatsService(self.tournament)
        return Response(svc.get_tournament_stats())


# ------------------------------------------------------------------
# S9-B2  Certificate Templates
# ------------------------------------------------------------------
class CertificateTemplateListView(TOCBaseView):
    """GET — list templates  |  POST — create template."""

    def get(self, request, slug):
        svc = TOCStatsService(self.tournament)
        return Response(svc.list_certificate_templates())

    def post(self, request, slug):
        svc = TOCStatsService(self.tournament)
        result = svc.create_certificate_template(request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class CertificateTemplateDetailView(TOCBaseView):
    """PUT — update  |  DELETE — remove template."""

    def put(self, request, slug, pk):
        svc = TOCStatsService(self.tournament)
        result = svc.update_certificate_template(pk, request.data)
        return Response(result)

    def delete(self, request, slug, pk):
        svc = TOCStatsService(self.tournament)
        svc.delete_certificate_template(pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CertificateGenerateView(TOCBaseView):
    """POST — generate certificate for a single user."""

    def post(self, request, slug, pk):
        svc = TOCStatsService(self.tournament)
        user_id = request.data.get("user_id")
        extra = request.data.get("extra_context")
        result = svc.generate_certificate(pk, user_id, extra)
        return Response(result, status=status.HTTP_201_CREATED)


class CertificateBulkGenerateView(TOCBaseView):
    """POST — bulk-generate certificates for all approved or selected users."""

    def post(self, request, slug, pk):
        svc = TOCStatsService(self.tournament)
        user_ids = request.data.get("user_ids")  # None → all approved
        result = svc.bulk_generate_certificates(pk, user_ids)
        return Response(result, status=status.HTTP_201_CREATED)


# ------------------------------------------------------------------
# S9-B3  Trophies / Achievements
# ------------------------------------------------------------------
class TrophyListView(TOCBaseView):
    """GET — list all defined trophies."""

    def get(self, request, slug):
        svc = TOCStatsService(self.tournament)
        return Response(svc.list_trophies())


class TrophyAwardView(TOCBaseView):
    """POST — award a trophy  |  DELETE — revoke a trophy."""

    def post(self, request, slug, pk):
        svc = TOCStatsService(self.tournament)
        user_id = request.data.get("user_id")
        result = svc.award_trophy(pk, user_id)
        return Response(result, status=status.HTTP_201_CREATED)

    def delete(self, request, slug, pk):
        svc = TOCStatsService(self.tournament)
        user_id = request.data.get("user_id")
        svc.revoke_trophy(pk, user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserTrophiesView(TOCBaseView):
    """GET — list trophies earned by a user."""

    def get(self, request, slug, user_id):
        svc = TOCStatsService(self.tournament)
        return Response(svc.get_user_trophies(user_id))


# ------------------------------------------------------------------
# S9-B4 / B5  Trust Index
# ------------------------------------------------------------------
class TrustIndexView(TOCBaseView):
    """GET — current trust index for a user."""

    def get(self, request, slug, user_id):
        svc = TOCStatsService(self.tournament)
        return Response(svc.get_trust_index(user_id))


class TrustEventListView(TOCBaseView):
    """GET — trust event log  |  POST — add manual event."""

    def get(self, request, slug, user_id):
        svc = TOCStatsService(self.tournament)
        return Response(svc.get_trust_events(user_id))

    def post(self, request, slug, user_id):
        svc = TOCStatsService(self.tournament)
        result = svc.add_trust_event(
            user_id,
            request.data.get("event_type"),
            int(request.data.get("delta", 0)),
            request.data.get("reason", ""),
        )
        return Response(result, status=status.HTTP_201_CREATED)
