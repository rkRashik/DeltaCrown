# apps/teams/views/__init__.py
"""
DeltaCrown teams views (finalized package).

Public API:
  - apps.teams.views.public   (public-facing pages: list/detail/search, etc.)
  - apps.teams.views.manage   (team management: create/edit/invite/members)

We re-export callables at the package level from both submodules so code like
`from apps.teams import views as v` continues to work.

Additionally, we provide:
  - package-level compatibility alias `team_index` → public.{team_index|team_list|teams_index|index}
  - ensure `apps.teams.views.manage` also exposes `team_index` for tests
"""

# Explicit submodules so callers can do `from .views import public, manage`
from . import public as public       # noqa: F401
from . import manage as manage       # noqa: F401

def _export_all_from(mod):
    """Re-export names from a submodule into this package namespace."""
    names = getattr(mod, "__all__", None)
    if names is None:
        names = [n for n in dir(mod) if not n.startswith("_")]
    g = globals()
    for n in names:
        g[n] = getattr(mod, n)

# Re-export everything (non-private) from submodules
_export_all_from(public)
_export_all_from(manage)

# ---------------------------------------------------------------------------
# Compatibility: ensure `team_index` exists at the package level
# ---------------------------------------------------------------------------
if "team_index" not in globals():
    for _cand in ("team_index", "team_list", "teams_index", "index"):
        if hasattr(public, _cand):
            team_index = getattr(public, _cand)  # noqa: F401
            break

# ---------------------------------------------------------------------------
# Compatibility: ensure manage module ALSO has team_index for tests
# ---------------------------------------------------------------------------
if not hasattr(manage, "team_index"):
    for _cand in ("team_index", "team_list", "teams_index", "index"):
        if hasattr(public, _cand):
            setattr(manage, "team_index", getattr(public, _cand))
            break

# Clean helper
del _export_all_from
