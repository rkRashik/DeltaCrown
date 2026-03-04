"""
TOC API Views — Sprint 28: Lobby / Server Management tab.

GET   lobby/                     — Full lobby dashboard
POST  lobby/servers/             — Add a server
PUT   lobby/servers/<pk>/        — Update a server
DEL   lobby/servers/<pk>/        — Delete a server
POST  lobby/create/              — Create lobby for a match
POST  lobby/close/               — Close lobby for a match
POST  lobby/chat/                — Send chat message
GET   lobby/chat/<match_id>/     — Get match chat
POST  lobby/config/              — Update lobby config
"""

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.lobby_service import TOCLobbyService


class LobbyDashboardView(TOCBaseView):
    """Full lobby dashboard."""

    def get(self, request, slug):
        result = TOCLobbyService.get_lobby_dashboard(self.tournament)
        return Response(result)


class LobbyServerView(TOCBaseView):
    """Add a server to the pool."""

    def post(self, request, slug):
        result = TOCLobbyService.add_server(self.tournament, request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class LobbyServerDetailView(TOCBaseView):
    """Update / delete a server."""

    def put(self, request, slug, pk):
        result = TOCLobbyService.update_server(self.tournament, pk, request.data)
        return Response(result)

    def delete(self, request, slug, pk):
        result = TOCLobbyService.delete_server(self.tournament, pk)
        return Response(result)


class LobbyCreateView(TOCBaseView):
    """Create a lobby for a match."""

    def post(self, request, slug):
        match_id = request.data.get("match_id")
        result = TOCLobbyService.create_lobby(
            self.tournament, match_id=int(match_id), data=request.data,
        )
        return Response(result, status=status.HTTP_201_CREATED)


class LobbyCloseView(TOCBaseView):
    """Close a match lobby."""

    def post(self, request, slug):
        match_id = request.data.get("match_id")
        result = TOCLobbyService.close_lobby(self.tournament, match_id=int(match_id))
        return Response(result)


class LobbyChatView(TOCBaseView):
    """Send / get chat messages for a match lobby."""

    def post(self, request, slug):
        match_id = request.data.get("match_id")
        message = request.data.get("message", "")
        result = TOCLobbyService.add_chat_message(
            self.tournament, match_id=int(match_id),
            user=request.user, message=message,
        )
        return Response(result, status=status.HTTP_201_CREATED)


class LobbyChatDetailView(TOCBaseView):
    """Get chat for a specific match."""

    def get(self, request, slug, match_id):
        result = TOCLobbyService.get_match_chat(
            self.tournament, match_id=int(match_id),
        )
        return Response(result)


class LobbyConfigView(TOCBaseView):
    """Update lobby configuration."""

    def post(self, request, slug):
        result = TOCLobbyService.update_lobby_config(self.tournament, request.data)
        return Response(result)
