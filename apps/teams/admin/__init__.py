# apps/teams/admin/__init__.py
"""Teams admin package init — ensure registrations load."""
from .teams import *       # noqa: F401,F403
from .exports import *     # noqa: F401,F403
from .inlines import *     # noqa: F401,F403
from .achievements import *  # noqa: F401,F403  (TeamAchievement, TeamStats)
from .ranking_settings import *  # noqa: F401,F403  (TeamRankingSettings)
