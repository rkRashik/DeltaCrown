# apps/teams/models/__init__.py
"""
Teams models package.

This package exposes the same public API as the former monolithic
`apps.teams.models` module, but now split by concern.

Implementation note:
- We first move the legacy file to `_legacy.py` (verbatim).
- These thin modules import & re-export from `_legacy` to avoid behavior changes.
- Later, you may move actual class bodies into these files without changing imports.
"""

# Re-export the core models via the topical modules
from .team import Team, team_logo_path            # noqa: F401
from .membership import TeamMembership            # noqa: F401
from .invite import TeamInvite                    # noqa: F401

# If the legacy file defined constants/choices, surface them here too.
# These imports are optional—only defined if present in _legacy.py.
try:  # max roster/caps, etc.
    from ._legacy import TEAM_MAX_ROSTER as TEAM_MAX_ROSTER  # noqa: F401
except Exception:
    pass

try:  # invite status/choices if they exist
    from ._legacy import INVITE_STATUS as INVITE_STATUS      # noqa: F401
except Exception:
    pass

# Public API (best-effort; won't fail if optional names are absent)
__all__ = [
    name for name in (
        "Team",
        "TeamMembership",
        "TeamInvite",
        "team_logo_path",
        "TEAM_MAX_ROSTER",
        "INVITE_STATUS",
    )
    if name in globals()
]
