# apps/teams/models/__init__.py
"""
Teams models package — public API surface remains:
from apps.teams.models import Team, TeamMembership, TeamInvite, team_logo_path
"""
from .team import Team, team_logo_path            # noqa: F401
from .membership import TeamMembership            # noqa: F401
from .invite import TeamInvite                    # noqa: F401

# Optional constants exposed if present
try:
    from ._legacy import TEAM_MAX_ROSTER          # noqa: F401
except Exception:
    pass

__all__ = [name for name in ("Team", "TeamMembership", "TeamInvite", "team_logo_path", "TEAM_MAX_ROSTER") if name in globals()]
