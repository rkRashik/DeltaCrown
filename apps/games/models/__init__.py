"""
Games app models.
"""

import os

from .game import Game
# Phase 6: GameMatchPipeline moved to apps.match_engine — re-export for compat
from apps.match_engine.models import GameMatchPipeline  # noqa: F401

__all__ = ['Game', 'GameMatchPipeline']

if os.environ.get("DELTA_MINIMAL_TEST_APPS") != "1":
    from .roster_config import GameRosterConfig
    from .player_identity import GamePlayerIdentityConfig
    from .tournament_config import GameTournamentConfig
    from .role import GameRole
    from .rules import (
        GameMatchResultSchema,
        GameScoringRule,
        VetoConfiguration,
    )

    __all__.extend([
        'GameRosterConfig',
        'GamePlayerIdentityConfig',
        'GameTournamentConfig',
        'GameRole',
        'GameMatchResultSchema',
        'GameScoringRule',
        'VetoConfiguration',
    ])
