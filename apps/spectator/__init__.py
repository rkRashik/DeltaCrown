"""
Spectator App

Phase G: Spectator Live Views

Read-only views for tournament spectators. Provides mobile-first UI with:
- Tournament overview with live leaderboards
- Match detail pages with live score updates
- htmx-powered auto-refresh for real-time updates
- WebSocket integration for instant notifications

IDs-Only Discipline:
- All views return tournament_id, match_id, participant_id, team_id
- No display names, usernames, or emails
- Client-side name resolution via external APIs (future enhancement)
"""

default_app_config = 'apps.spectator.apps.SpectatorConfig'
