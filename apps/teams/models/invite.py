# apps/teams/models/invite.py
"""
Thin re-export module for TeamInvite model (+ any related constants).

We import from `_legacy` to keep behavior 100% identical. You may later
move the actual class definition here and delete the import.
"""
from ._legacy import TeamInvite  # noqa: F401
