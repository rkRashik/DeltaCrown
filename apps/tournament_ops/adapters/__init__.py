"""
Service Adapter Interfaces for Cross-Domain Communication.

This package contains adapter interfaces (protocols) and base classes that enable
TournamentOps to communicate with other domains (Games, Teams, Users, Economy, Tournaments)
without direct model imports.

All adapters must:
- Use DTOs for data transfer (once defined in tournament_ops/dtos/)
- Not import models from other apps
- Be easily mockable for testing
- Follow the adapter pattern for clean separation of concerns

Adapters:
- TeamAdapter: Access team data and validate membership
- UserAdapter: Access user/profile data and check eligibility
- GameAdapter: Fetch game configs, identity fields, and validation rules
- EconomyAdapter: Handle payments, refunds, and balance queries

Reference: ARCH_PLAN_PART_1.md - Section 2.2 Service Adapters & DTOs
"""

from .base import BaseAdapter, SupportsHealthCheck
from .team_adapter import TeamAdapter, TeamAdapterProtocol
from .user_adapter import UserAdapter, UserAdapterProtocol
from .game_adapter import GameAdapter, GameAdapterProtocol
from .economy_adapter import EconomyAdapter, EconomyAdapterProtocol
from .tournament_adapter import TournamentAdapter, TournamentAdapterProtocol
from .match_adapter import MatchAdapter, MatchAdapterProtocol

__all__ = [
    'BaseAdapter',
    'SupportsHealthCheck',
    'TeamAdapter',
    'TeamAdapterProtocol',
    'UserAdapter',
    'UserAdapterProtocol',
    'GameAdapter',
    'GameAdapterProtocol',
    'EconomyAdapter',
    'EconomyAdapterProtocol',
    'TournamentAdapter',
    'TournamentAdapterProtocol',
    'MatchAdapter',
    'MatchAdapterProtocol',
]
