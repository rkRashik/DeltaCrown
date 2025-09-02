# apps/teams/admin/base.py
"""
Compatibility shim for legacy imports used by tests or external code.

Allows:
    from apps.teams.admin.base import export_teams_csv

We split Teams admin into a package with exports living in:
    apps/teams/admin/exports.py
"""

from .exports import export_teams_csv

__all__ = ["export_teams_csv"]
