# apps/tournaments/views/__init__.py
"""
DeltaCrown tournaments views (finalized package).

Public API:
  - apps.tournaments.views.public     (public-facing pages)
  - apps.tournaments.views.dashboard  (dashboard/admin-style views)

For backwards compatibility, we re-export callables at the package level from
both submodules so code like `from apps.tournaments import views as v` continues
to work. Implementations now live inside this package (no legacy modules).
"""

# Explicit submodules so callers can do `from .views import public, dashboard`
from . import public as public       # noqa: F401
from . import dashboard as dashboard # noqa: F401

# Re-export selected symbols from submodules at the package level.
# We avoid wildcard import to keep linting sane and prevent accidental private leaks.
# If your submodules define __all__, you can import * safely; otherwise export everything non-private.

# Try to prefer __all__ if present; otherwise export all non-private names.
def _export_all_from(mod):
    names = getattr(mod, "__all__", None)
    if names is None:
        names = [n for n in dir(mod) if not n.startswith("_")]
    g = globals()
    for n in names:
        g[n] = getattr(mod, n)

_export_all_from(public)
_export_all_from(dashboard)

# Keep module globals clean
del _export_all_from
