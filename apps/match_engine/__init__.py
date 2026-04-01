"""
Match Engine app — coordination layer for match-room lifecycle.

Owns:
  • MatchConsumer (WebSocket consumer for live match rooms)
  • GameMatchPipeline model (per-game phase sequence configuration)
  • Match-room WS routing

Phase 6 extraction from apps.tournaments and apps.games.
"""

default_app_config = "apps.match_engine.apps.MatchEngineConfig"
