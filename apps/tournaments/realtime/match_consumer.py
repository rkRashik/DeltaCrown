"""
Phase 6 backward-compat shim — MatchConsumer now lives in apps.match_engine.consumers.

All existing imports from this path continue to work.
"""

from apps.match_engine.consumers import MatchConsumer, parse_datetime  # noqa: F401

__all__ = ["MatchConsumer", "parse_datetime"]
