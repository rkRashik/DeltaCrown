# apps/teams/models/__init__.py
"""
FROZEN STUB — Teams models package.

Only Team is exported here for FK resolution from other apps' migrations.
All new development uses apps.organizations.models.

DO NOT add new models, imports, or logic here.
"""
from ._legacy import Team, team_logo_path, TEAM_MAX_ROSTER  # noqa: F401

# Re-export membership/invite for migration FK resolution only
try:
    from .membership import TeamMembership  # noqa: F401
except Exception:
    pass

try:
    from .invite import TeamInvite  # noqa: F401
except Exception:
    pass

try:
    from .join_request import TeamJoinRequest  # noqa: F401
except Exception:
    pass

# Ranking models — still queried by tournament views & dual_write_service
try:
    from .ranking import (  # noqa: F401
        RankingCriteria,
        TeamRankingHistory,
        TeamRankingBreakdown,
        TeamGameRanking,
    )
except Exception:
    pass

__all__ = [
    "Team",
    "TeamMembership",
    "TeamInvite",
    "TeamJoinRequest",
    "RankingCriteria",
    "TeamRankingHistory",
    "TeamRankingBreakdown",
    "TeamGameRanking",
    "team_logo_path",
    "TEAM_MAX_ROSTER",
]
