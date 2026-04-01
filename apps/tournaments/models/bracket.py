"""
Phase 6 backward-compat shim u2014 Bracket and BracketNode now live in apps.brackets.models.

All existing imports from this path continue to work.
"""

from apps.brackets.models import Bracket, BracketNode  # noqa: F401

__all__ = ["Bracket", "BracketNode"]
