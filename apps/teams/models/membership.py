# apps/teams/models/membership.py
"""
Thin re-export module for TeamMembership model.

We import from `_legacy` to keep behavior 100% identical. You may later
move the actual class definition here and delete the import.
"""
from ._legacy import TeamMembership  # noqa: F401
