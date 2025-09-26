# apps/teams/services/__init__.py
"""
Team Services Package

Provides business logic services for team-related operations.
"""

from .ranking_service import ranking_service, TeamRankingService

__all__ = ['ranking_service', 'TeamRankingService']