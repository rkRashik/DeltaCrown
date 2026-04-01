"""
Phase 6 re-export — BracketEngineService is proxied here for canonical access.

The actual implementation stays in apps.tournament_ops.services.bracket_engine_service
(DTO-only, framework-light).  Consumers should import from apps.brackets.services.
"""

from apps.tournament_ops.services.bracket_engine_service import BracketEngineService  # noqa: F401

__all__ = ["BracketEngineService"]
