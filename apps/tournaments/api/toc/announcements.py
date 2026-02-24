"""
TOC API Views — Sprint 8: Announcements & Quick Comms.

S8-B7 GET/POST announcements/          — List / create announcement
S8-B7 PUT/DEL  announcements/<id>/     — Update / delete
S8-B7 POST     announcements/broadcast/— Broadcast with targeting
S8-B8 POST     announcements/quick-comms/ — Quick Comms template send
"""

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.announcements_service import TOCAnnouncementsService


class AnnouncementListView(TOCBaseView):
    """GET announcements / POST to create."""

    def get(self, request, slug):
        search = request.query_params.get("search", "")
        pinned = request.query_params.get("pinned") == "true"
        data = TOCAnnouncementsService.list_announcements(
            self.tournament, search=search, pinned_only=pinned,
        )
        stats = TOCAnnouncementsService.get_stats(self.tournament)
        return Response({"announcements": data, "stats": stats})

    def post(self, request, slug):
        result = TOCAnnouncementsService.create_announcement(
            self.tournament, request.data, user=request.user,
        )
        return Response(result, status=status.HTTP_201_CREATED)


class AnnouncementDetailView(TOCBaseView):
    """PUT to update / DELETE to remove."""

    def put(self, request, slug, pk):
        result = TOCAnnouncementsService.update_announcement(pk, request.data)
        return Response(result)

    def delete(self, request, slug, pk):
        result = TOCAnnouncementsService.delete_announcement(pk)
        return Response(result)


class AnnouncementBroadcastView(TOCBaseView):
    """POST to create + push notifications with recipient targeting."""

    def post(self, request, slug):
        result = TOCAnnouncementsService.broadcast(
            self.tournament, request.data, user=request.user,
        )
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)


class QuickCommsView(TOCBaseView):
    """POST to send a pre-built Quick Comms template."""

    def post(self, request, slug):
        template_key = request.data.get("template")
        if not template_key:
            return Response(
                {"error": "template key is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = TOCAnnouncementsService.quick_comms(
            self.tournament, template_key, user=request.user,
        )
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_201_CREATED)
