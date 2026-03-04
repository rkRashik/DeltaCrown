"""
TOC API Views — Sprint 28: Notifications Center tab.

GET   notifications/                    — Full notifications dashboard
POST  notifications/templates/          — Create template
PUT   notifications/templates/<id>/     — Update template
DEL   notifications/templates/<id>/     — Delete template
POST  notifications/send/               — Send immediate notification
POST  notifications/schedule/           — Schedule future notification
POST  notifications/cancel/<id>/        — Cancel scheduled notification
POST  notifications/auto-rules/         — Update auto-notification rules
POST  notifications/channels/           — Update delivery channels
POST  notifications/team-message/       — Send team message
"""

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.notifications_service import TOCNotificationsService


class NotificationsDashboardView(TOCBaseView):
    """Full notifications center dashboard."""

    def get(self, request, slug):
        result = TOCNotificationsService.get_notifications_dashboard(self.tournament)
        return Response(result)


class NotificationsTemplateView(TOCBaseView):
    """Create a notification template."""

    def post(self, request, slug):
        result = TOCNotificationsService.create_template(self.tournament, request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class NotificationsTemplateDetailView(TOCBaseView):
    """Update / delete a notification template."""

    def put(self, request, slug, template_id):
        result = TOCNotificationsService.update_template(
            self.tournament, template_id=template_id, data=request.data,
        )
        return Response(result)

    def delete(self, request, slug, template_id):
        result = TOCNotificationsService.delete_template(
            self.tournament, template_id=template_id,
        )
        return Response(result)


class NotificationsSendView(TOCBaseView):
    """Send an immediate notification."""

    def post(self, request, slug):
        result = TOCNotificationsService.send_notification(self.tournament, request.data)
        return Response(result)


class NotificationsScheduleView(TOCBaseView):
    """Schedule a future notification."""

    def post(self, request, slug):
        result = TOCNotificationsService.schedule_notification(self.tournament, request.data)
        return Response(result, status=status.HTTP_201_CREATED)


class NotificationsCancelView(TOCBaseView):
    """Cancel a scheduled notification."""

    def post(self, request, slug, scheduled_id):
        result = TOCNotificationsService.cancel_scheduled(
            self.tournament, scheduled_id=scheduled_id,
        )
        return Response(result)


class NotificationsAutoRulesView(TOCBaseView):
    """Update auto-notification rules."""

    def post(self, request, slug):
        result = TOCNotificationsService.update_auto_rules(
            self.tournament, rules=request.data.get("rules", []),
        )
        return Response(result)


class NotificationsChannelsView(TOCBaseView):
    """Update notification delivery channels."""

    def post(self, request, slug):
        result = TOCNotificationsService.update_channels(self.tournament, request.data)
        return Response(result)


class NotificationsTeamMessageView(TOCBaseView):
    """Send a notification to a specific team."""

    def post(self, request, slug):
        team_id = request.data.get("team_id")
        if not team_id:
            return Response({"error": "team_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        result = TOCNotificationsService.send_team_message(
            self.tournament, team_id=int(team_id), data=request.data,
        )
        return Response(result)
