# apps/teams/models/team.py
"""
Thin re-export module for Team model (+ helper paths).
We import from `_legacy` to keep behavior identical and imports stable.
"""

from ._legacy import Team, team_logo_path  # noqa: F401
