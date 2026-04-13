"""
TOC API Views — Sprint 8: Announcements & Quick Comms.

S8-B7 GET/POST announcements/          — List / create announcement
S8-B7 PUT/DEL  announcements/<id>/     — Update / delete
S8-B7 POST     announcements/broadcast/— Broadcast with targeting
S8-B8 POST     announcements/quick-comms/ — Quick Comms template send
S8-B9 GET/PUT  announcements/automation/ — Smart lifecycle automation config
"""

import logging

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.announcements_service import TOCAnnouncementsService

logger = logging.getLogger("toc.announcements")

# Canonical list of automatable lifecycle event categories.
# Grouped by tournament phase for operator control panel.
# wiring: fully_wired | feed_only | notification_only | coming_soon
# channel: both | feed | notification | none
AUTOMATION_CATEGORIES = [
    # ── Registration ─────────────────────────────────────────────
    {"key": "registration_open",      "label": "Registration Open",      "group": "registration", "audience": "public",      "trigger": "Status → registration_open",         "default_message": "Registration is now open — sign up before spots fill.",            "wiring": "notification_only", "channel": "notification"},
    {"key": "registration_closing",   "label": "Registration Closing",   "group": "registration", "audience": "public",      "trigger": "24 h before registration deadline",   "default_message": "Registration closes in 24 hours.",                                 "wiring": "coming_soon",       "channel": "none"},
    {"key": "registrations_closed",   "label": "Registration Closed",    "group": "registration", "audience": "all",         "trigger": "Status → registration_closed",        "default_message": "Registration is now closed.",                                      "wiring": "fully_wired",       "channel": "both"},
    # ── Check-in ─────────────────────────────────────────────────
    {"key": "checkin_open",           "label": "Check-in Open",          "group": "checkin",      "audience": "all",         "trigger": "Check-in window opens",               "default_message": "Check-in is open — confirm your attendance now.",                  "wiring": "notification_only", "channel": "notification"},
    {"key": "checkin_closing",        "label": "Check-in Closing",       "group": "checkin",      "audience": "not_checked_in", "trigger": "15 min before check-in closes",    "default_message": "Check-in closes in 15 minutes. Don't miss it.",                    "wiring": "coming_soon",       "channel": "none"},
    # ── Group Stage ──────────────────────────────────────────────
    {"key": "group_draw_completed",   "label": "Group Draw Completed",   "group": "group",        "audience": "all",         "trigger": "Groups drawn & published",            "default_message": "Group draw is complete — see your group assignment.",              "wiring": "fully_wired",       "channel": "both"},
    {"key": "matches_generated",      "label": "Matches Generated",      "group": "group",        "audience": "all",         "trigger": "Group matches created",               "default_message": "Group stage matches generated and ready for play.",                "wiring": "feed_only",         "channel": "feed"},
    {"key": "group_stage_completed",  "label": "Group Stage Completed",  "group": "group",        "audience": "all",         "trigger": "All group matches concluded",         "default_message": "All group matches concluded. Final standings locked.",             "wiring": "feed_only",         "channel": "feed"},
    {"key": "qualified_to_knockout",  "label": "Qualified for Knockout",  "group": "group",        "audience": "personal",    "trigger": "Participant qualifies from group",    "default_message": "You advanced from group stage to the knockout bracket.",           "wiring": "coming_soon",       "channel": "none"},
    # ── Knockout Stage ───────────────────────────────────────────
    {"key": "bracket_published",      "label": "Bracket Published",      "group": "knockout",     "audience": "all",         "trigger": "Bracket seeded & published",          "default_message": "Knockout bracket seeded and published.",                           "wiring": "fully_wired",       "channel": "both"},
    {"key": "knockout_live",          "label": "Knockout Stage Live",    "group": "knockout",     "audience": "all",         "trigger": "First knockout match begins",         "default_message": "Knockout stage is now live.",                                      "wiring": "feed_only",         "channel": "feed"},
    {"key": "advanced_to_next_round", "label": "Advanced to Next Round", "group": "knockout",     "audience": "personal",    "trigger": "Winner of bracket match",             "default_message": "You won and are moving forward in the bracket.",                   "wiring": "coming_soon",       "channel": "none"},
    {"key": "eliminated",             "label": "Eliminated",             "group": "knockout",     "audience": "personal",    "trigger": "Participant knocked out",             "default_message": "Your tournament run has ended.",                                   "wiring": "coming_soon",       "channel": "none"},
    # ── Match / Lobby ────────────────────────────────────────────
    {"key": "opponent_assigned",      "label": "Opponent Assigned",      "group": "match",        "audience": "personal",    "trigger": "Next-round matchup determined",       "default_message": "Your next opponent has been determined.",                          "wiring": "coming_soon",       "channel": "none"},
    {"key": "lobby_opens_soon",       "label": "Lobby Opens Soon",       "group": "match",        "audience": "personal",    "trigger": "~30 min before lobby opens",          "default_message": "Your match lobby opens in less than 30 minutes.",                  "wiring": "coming_soon",       "channel": "none"},
    {"key": "lobby_is_open",          "label": "Lobby is Open",          "group": "match",        "audience": "personal",    "trigger": "Match lobby check-in window starts",  "default_message": "Check in now to confirm your participation.",                      "wiring": "coming_soon",       "channel": "none"},
    {"key": "lobby_expired",          "label": "Missed Lobby / Expired", "group": "match",        "audience": "personal",    "trigger": "Check-in window closes without entry", "default_message": "You missed the check-in window for a match.",                     "wiring": "coming_soon",       "channel": "none"},
    {"key": "match_live",             "label": "Match Now Live",         "group": "match",        "audience": "personal",    "trigger": "Match transitions to live state",     "default_message": "Your match is now live — good luck!",                              "wiring": "coming_soon",       "channel": "none"},
    # ── Completion / Broadcast ───────────────────────────────────
    {"key": "stream_live",            "label": "Stream is Live",         "group": "completion",   "audience": "public",      "trigger": "Organizer starts broadcast",          "default_message": "The tournament stream is now live — tune in!",                     "wiring": "coming_soon",       "channel": "none"},
    {"key": "tournament_completed",   "label": "Tournament Completed",   "group": "completion",   "audience": "all",         "trigger": "Status → completed",                  "default_message": "All matches concluded. Final standings and prizes are available.", "wiring": "fully_wired",       "channel": "both"},
]

# Quick lookup for valid keys
_AUTOMATION_KEYS = frozenset(c["key"] for c in AUTOMATION_CATEGORIES)

# Group metadata for frontend rendering
AUTOMATION_GROUPS = [
    {"key": "registration", "label": "Registration",          "icon": "clipboard-list"},
    {"key": "checkin",      "label": "Check-in",              "icon": "user-check"},
    {"key": "group",        "label": "Group Stage",           "icon": "layers"},
    {"key": "knockout",     "label": "Knockout Stage",        "icon": "swords"},
    {"key": "match",        "label": "Match / Lobby",         "icon": "gamepad-2"},
    {"key": "completion",   "label": "Completion / Broadcast", "icon": "trophy"},
]


class AnnouncementListView(TOCBaseView):
    """GET announcements / POST to create."""

    def get(self, request, slug):
        search = request.query_params.get("search", "")
        pinned = request.query_params.get("pinned") == "true"
        data = TOCAnnouncementsService.list_announcements(
            self.tournament, search=search, pinned_only=pinned,
        )
        stats = TOCAnnouncementsService.get_stats(self.tournament)

        # Append derived lifecycle events (system-generated)
        include_lifecycle = request.query_params.get("lifecycle", "true") != "false"
        lifecycle = []
        if include_lifecycle and not pinned and not search:
            try:
                from apps.tournaments.services.lifecycle_announcements import (
                    derive_tournament_events,
                )
                raw_events = derive_tournament_events(self.tournament)

                # Respect automation config — filter out disabled categories
                auto_config = _get_automation_config(self.tournament)

                lifecycle = [
                    {
                        "id": f"lifecycle-{evt['event_type']}",
                        "title": _apply_custom_message(evt, auto_config).get("title", evt["title"]),
                        "message": _apply_custom_message(evt, auto_config).get("message", evt["message"]),
                        "author": "System",
                        "created_at": evt["timestamp"].isoformat()
                            if evt.get("timestamp") else None,
                        "is_pinned": False,
                        "is_important": evt.get("urgent", False),
                        "is_derived": True,
                        "icon": evt.get("icon", "info"),
                        "color": evt.get("color", "cyan"),
                        "category": evt.get("category", "system"),
                        "scope": evt.get("scope", "global"),
                    }
                    for evt in raw_events
                    if auto_config.get(evt["event_type"], {}).get("enabled", True)
                ]
            except Exception:
                logger.warning(
                    "Failed to derive lifecycle events", exc_info=True,
                )

        return Response({
            "announcements": data,
            "lifecycle": lifecycle,
            "stats": stats,
        })

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
        result = TOCAnnouncementsService.delete_announcement(pk, tournament=self.tournament)
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


# ── Automation config helpers ────────────────────────────────────────────────

def _get_automation_config(tournament):
    """Read announcement_automation from tournament.config JSON."""
    config = getattr(tournament, 'config', None) or {}
    return config.get('announcement_automation', {})


def _apply_custom_message(evt, auto_config):
    """If organizer set a custom_message for this event type, use it."""
    cat_config = auto_config.get(evt['event_type'], {})
    custom = cat_config.get('custom_message')
    if custom:
        return {'title': evt['title'], 'message': custom}
    return {'title': evt['title'], 'message': evt['message']}


class AnnouncementAutomationView(TOCBaseView):
    """
    GET: Return current automation config with all categories.
    PUT: Update automation config (enable/disable categories, custom messages).

    Config is stored in tournament.config['announcement_automation'] as a dict:
    {
        "group_stage_completed": {"enabled": true, "custom_message": null},
        "qualified_to_knockout": {"enabled": false},
        ...
    }
    """

    def get(self, request, slug):
        auto_config = _get_automation_config(self.tournament)
        categories = []
        for cat in AUTOMATION_CATEGORIES:
            saved = auto_config.get(cat['key'], {})
            categories.append({
                'key': cat['key'],
                'label': cat['label'],
                'group': cat['group'],
                'audience': cat['audience'],
                'trigger': cat['trigger'],
                'default_message': cat['default_message'],
                'enabled': saved.get('enabled', True),
                'custom_message': saved.get('custom_message') or '',
                'wiring': cat.get('wiring', 'coming_soon'),
                'channel': cat.get('channel', 'none'),
            })
        return Response({
            'categories': categories,
            'groups': AUTOMATION_GROUPS,
        })

    def put(self, request, slug):
        updates = request.data.get('categories', [])
        if not isinstance(updates, list):
            return Response(
                {'error': 'categories must be a list'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_keys = _AUTOMATION_KEYS
        auto_config = _get_automation_config(self.tournament)

        for item in updates:
            key = item.get('key', '')
            if key not in valid_keys:
                continue
            auto_config[key] = {
                'enabled': bool(item.get('enabled', True)),
                'custom_message': (item.get('custom_message') or '').strip() or None,
            }

        # Persist to tournament.config
        config = self.tournament.config or {}
        config['announcement_automation'] = auto_config
        from apps.tournaments.models.tournament import Tournament
        Tournament.objects.filter(pk=self.tournament.pk).update(config=config)
        self.tournament.config = config

        return Response({'success': True, 'updated': len(updates)})
