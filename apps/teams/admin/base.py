# apps/teams/admin/base.py
"""
Compatibility shim for legacy imports.

Some tests (and possibly external code) still do:
    from apps.teams.admin.base import export_teams_csv

We split the admin into a package; this module re-exports the CSV action
so the legacy import path keeps working. No behavior change.
"""
from .exports import export_teams_csv

__all__ = ["export_teams_csv"]
