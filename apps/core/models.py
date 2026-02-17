# apps/core/models.py
"""
Core models module - Re-exports for convenience.

The actual Game model lives in apps.tournaments.models,
but many parts of the codebase expect to import it from apps.core.models.
"""

from apps.games.models.game import Game

__all__ = ['Game']
