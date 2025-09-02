# apps/teams/views/__init__.py
"""
DeltaCrown teams views package.

This package exposes two submodules:
  - apps.teams.views.public   → forwards to apps/teams/views_impl.py (legacy)
  - apps.teams.views.manage   → forwards to apps/teams/views_impl.py (legacy)

We also re-export all callables from the legacy implementation at the package
level so older imports like `from apps.teams import views as v` still work.
"""

# Submodules (so callers can do: from .views import public, manage)
from . import public as public      # noqa: F401
from . import manage as manage      # noqa: F401

# Re-export legacy callables at the package level (non-recursive)
from ..views_impl import *  # noqa: F401,F403
