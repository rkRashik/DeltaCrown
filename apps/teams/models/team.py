# apps/teams/models/team.py
"""
Thin re-export module for Team model (+ helper paths).

We import from `_legacy` to keep behavior 100% identical. You may later
move the actual class definition here and delete the import.
"""
from ._legacy import Team, team_logo_path  # noqa: F401
