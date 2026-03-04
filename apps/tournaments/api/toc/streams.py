"""
TOC API Views — Sprint 28: Streams & Media tab.

GET   streams/                     — Full streams dashboard
POST  streams/stations/            — Add a broadcast station
PUT   streams/stations/<pk>/       — Update a station
DEL   streams/stations/<pk>/       — Delete a station
POST  streams/assign/              — Assign stream to a match
POST  streams/vods/                — Add a VOD
DEL   streams/vods/<pk>/           — Delete a VOD
GET   streams/overlay/<match_id>/  — Real-time OBS overlay data
POST  streams/overlay-key/         — Generate overlay API key
"""

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.streams_service import TOCStreamsService


class StreamsDashboardView(TOCBaseView):
    """Full streams & media dashboard."""

    def get(self, request, slug):
        result = TOCStreamsService.get_streams_dashboard(self.tournament)
        return Response(result)


class StreamsStationView(TOCBaseView):
    """CRUD for broadcast stations."""

    def post(self, request, slug):
        result = TOCStreamsService.add_station(self.tournament, request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class StreamsStationDetailView(TOCBaseView):
    """Update / delete a station."""

    def put(self, request, slug, pk):
        result = TOCStreamsService.update_station(self.tournament, pk, request.data)
        return Response(result)

    def delete(self, request, slug, pk):
        result = TOCStreamsService.delete_station(self.tournament, pk)
        return Response(result)


class StreamsAssignView(TOCBaseView):
    """Assign stream URL to a match."""

    def post(self, request, slug):
        match_id = request.data.get("match_id")
        stream_url = request.data.get("stream_url", "")
        result = TOCStreamsService.assign_stream(
            self.tournament, match_id=int(match_id), stream_url=stream_url,
        )
        return Response(result)


class StreamsVodView(TOCBaseView):
    """Add a VOD entry."""

    def post(self, request, slug):
        result = TOCStreamsService.add_vod(self.tournament, request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class StreamsVodDetailView(TOCBaseView):
    """Delete a VOD entry."""

    def delete(self, request, slug, pk):
        result = TOCStreamsService.delete_vod(self.tournament, pk)
        return Response(result)


class StreamsOverlayView(TOCBaseView):
    """Real-time overlay data for OBS."""

    def get(self, request, slug, match_id):
        result = TOCStreamsService.get_overlay_data(
            self.tournament, match_id=int(match_id),
        )
        return Response(result)


class StreamsOverlayKeyView(TOCBaseView):
    """Generate overlay API key."""

    def post(self, request, slug):
        result = TOCStreamsService.generate_overlay_key(self.tournament)
        return Response(result)
