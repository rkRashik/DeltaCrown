# apps/tournaments/views/__init__.py
"""
DeltaCrown tournaments views package.

This package exposes two submodules:
  - apps.tournaments.views.public     → forwards to apps/tournaments/views_public.py
  - apps.tournaments.views.dashboard  → forwards to apps/tournaments/views_dashboard_impl.py

We also re-export all callables from both implementation modules at the package
level so legacy imports like `from apps.tournaments import views as views_pkg`
can still find top-level callables (e.g., match_review_view) if referenced.
"""

# Submodules (so callers can do: from .views import public, dashboard)
from . import public as public   # noqa: F401
from . import dashboard as dashboard  # noqa: F401

# Re-export legacy callables at the package level (non-recursive)
from ..views_public import *  # noqa: F401,F403
from ..views_dashboard_impl import *  # noqa: F401,F403
