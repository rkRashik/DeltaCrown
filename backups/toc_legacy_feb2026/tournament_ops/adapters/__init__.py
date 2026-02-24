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
from .smart_registration_adapter import SmartRegistrationAdapter, SmartRegistrationAdapterProtocol
from .result_submission_adapter import ResultSubmissionAdapter, ResultSubmissionAdapterProtocol
from .schema_validation_adapter import SchemaValidationAdapter, SchemaValidationAdapterProtocol
from .dispute_adapter import DisputeAdapter, DisputeAdapterProtocol
from .review_inbox_adapter import ReviewInboxAdapter, ReviewInboxAdapterProtocol
from .notification_adapter import NotificationAdapter, NotificationAdapterProtocol
from .staffing_adapter import StaffingAdapter
from .match_ops_adapter import MatchOpsAdapter
from .audit_log_adapter import AuditLogAdapter, AuditLogAdapterProtocol
from .help_content_adapter import HelpContentAdapter, HelpContentAdapterProtocol
from .user_stats_adapter import UserStatsAdapter, UserStatsAdapterProtocol
from .team_stats_adapter import TeamStatsAdapter, TeamStatsAdapterProtocol
from .team_ranking_adapter import TeamRankingAdapter, TeamRankingAdapterProtocol
from .match_history_adapter import MatchHistoryAdapter, DjangoMatchHistoryAdapter
from .analytics_adapter import AnalyticsAdapter, AnalyticsAdapterProtocol

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
    'SmartRegistrationAdapter',
    'SmartRegistrationAdapterProtocol',
    'ResultSubmissionAdapter',
    'ResultSubmissionAdapterProtocol',
    'SchemaValidationAdapter',
    'SchemaValidationAdapterProtocol',
    'DisputeAdapter',
    'DisputeAdapterProtocol',
    'ReviewInboxAdapter',
    'ReviewInboxAdapterProtocol',
    'NotificationAdapter',
    'NotificationAdapterProtocol',
    'StaffingAdapter',
    'MatchOpsAdapter',
    'AuditLogAdapter',
    'AuditLogAdapterProtocol',
    'HelpContentAdapter',
    'HelpContentAdapterProtocol',
    'UserStatsAdapter',
    'UserStatsAdapterProtocol',
    'TeamStatsAdapter',
    'TeamStatsAdapterProtocol',
    'TeamRankingAdapter',
    'TeamRankingAdapterProtocol',
    'MatchHistoryAdapter',
    'DjangoMatchHistoryAdapter',
    'AnalyticsAdapter',
    'AnalyticsAdapterProtocol',
]
