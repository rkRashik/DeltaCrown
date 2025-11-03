# apps/tournaments/admin/base.py
from __future__ import annotations
"""
Safe, no-surprises admin extensions.

This module must NEVER:
- append to tuple attributes directly,
- import or rely on module-level action functions from other modules.

If you want to extend attributes later, use _extend_tuple_attr() and
ONLY add method-name strings that exist on the admin class.
"""

from typing import Iterable

def _extend_tuple_attr(admin_cls, name: str, additions: Iterable[str] | None):
    """
    Safely extend a ModelAdmin class attribute that may be a tuple or list.

    We only support adding *strings* (method names) here, because your actions
    are implemented as methods on TournamentAdmin. Avoid mixing callables.
    """
    if not admin_cls or not additions:
        return
    existing = getattr(admin_cls, name, ())
    if isinstance(existing, tuple):
        current = list(existing)
    elif isinstance(existing, list):
        current = existing[:]
    else:
        current = []

    for item in additions:
        if isinstance(item, str) and item and item not in current:
            current.append(item)

    setattr(admin_cls, name, tuple(current))


# Try to load TournamentAdmin to optionally extend it (idempotent and safe).
try:
    from .tournaments import TournamentAdmin  # defines & registers admin
except Exception:
    TournamentAdmin = None  # pragma: no cover

# If you ever need to tack on more method-based actions later, do it like this:
# _extend_tuple_attr(TournamentAdmin, "actions", ("some_method_action_name",))
# For now, do nothing to avoid conflicting with your current setup.
