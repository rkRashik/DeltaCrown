"""
Games app models.
"""

import os

from .game import Game

__all__ = ['Game']

if os.environ.get("DELTA_MINIMAL_TEST_APPS") != "1":
    from .roster_config import GameRosterConfig
    from .player_identity import GamePlayerIdentityConfig
    from .tournament_config import GameTournamentConfig
    from .role import GameRole
    from .rules import (
        GameMatchResultSchema,
        GameScoringRule,
    )

    __all__.extend([
        'GameRosterConfig',
        'GamePlayerIdentityConfig',
        'GameTournamentConfig',
        'GameRole',
        'GameMatchResultSchema',
        'GameScoringRule',
    ])
