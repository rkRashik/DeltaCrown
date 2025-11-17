# apps/teams/models/__init__.py
"""
Teams models package — public API surface remains:
from apps.teams.models import Team, TeamMembership, TeamInvite, TeamJoinRequest, team_logo_path
"""
from .team import Team, team_logo_path            # noqa: F401
from .membership import TeamMembership            # noqa: F401
from .invite import TeamInvite                    # noqa: F401
from .join_request import TeamJoinRequest          # noqa: F401

# Optional constants exposed if present
try:
    from ._legacy import TEAM_MAX_ROSTER          # noqa: F401
except Exception:
    pass

from .presets import EfootballTeamPreset, ValorantTeamPreset, ValorantPlayerPreset  # noqa: F401
from .achievement import TeamAchievement  # noqa: F401
from .stats import TeamStats as LegacyTeamStats  # noqa: F401  # Legacy simple stats
from .ranking_settings import TeamRankingSettings  # noqa: F401
from .ranking import RankingCriteria, TeamRankingHistory, TeamRankingBreakdown  # noqa: F401

# Tournament Integration models (Task 5)
from .tournament_integration import (  # noqa: F401
    TeamTournamentRegistration,
    TournamentParticipation,
    TournamentRosterLock,
)

# Analytics models (Task 6)
from .analytics import (  # noqa: F401
    TeamAnalytics,  # New comprehensive analytics
    PlayerStats,
    MatchRecord,
    MatchParticipation,
)

# Social & Community models (Task 7)
from .chat import (  # noqa: F401
    TeamChatMessage,
    ChatMessageReaction,
    ChatReadReceipt,
    ChatTypingIndicator,
)
from .discussions import (  # noqa: F401
    TeamDiscussionPost,
    TeamDiscussionComment,
    DiscussionSubscription,
    DiscussionNotification,
)

# Sponsorship & Monetization models (Task 8)
from .sponsorship import (  # noqa: F401
    TeamSponsor,
    SponsorInquiry,
    TeamMerchItem,
    TeamPromotion,
)

# Game-specific models (new roster management system)
from .base import BaseTeam, BasePlayerMembership  # noqa: F401
from .game_specific import (  # noqa: F401
    # Team models
    ValorantTeam, CS2Team, Dota2Team, MLBBTeam,
    PUBGTeam, FreeFireTeam, EFootballTeam, FC26Team, CODMTeam,
    # Membership models
    ValorantPlayerMembership, CS2PlayerMembership, Dota2PlayerMembership,
    MLBBPlayerMembership, PUBGPlayerMembership, FreeFirePlayerMembership,
    EFootballPlayerMembership, FC26PlayerMembership, CODMPlayerMembership,
    # Model registries
    GAME_TEAM_MODELS, GAME_MEMBERSHIP_MODELS,
    get_team_model_for_game, get_membership_model_for_game,
)

__all__ = [name for name in (
    # Legacy models
    "Team", "TeamMembership", "TeamInvite", "TeamJoinRequest", "team_logo_path",
    "TEAM_MAX_ROSTER", "EfootballTeamPreset", "ValorantTeamPreset", "ValorantPlayerPreset",
    "TeamAchievement", "LegacyTeamStats", "TeamRankingSettings",
    "RankingCriteria", "TeamRankingHistory", "TeamRankingBreakdown",
    # Tournament Integration (Task 5)
    "TeamTournamentRegistration", "TournamentParticipation", "TournamentRosterLock",
    # Analytics models (Task 6) - New comprehensive analytics
    "TeamAnalytics", "PlayerStats", "MatchRecord", "MatchParticipation",
    # Social & Community models (Task 7)
    "TeamChatMessage", "ChatMessageReaction", "ChatReadReceipt", "ChatTypingIndicator",
    "TeamDiscussionPost", "TeamDiscussionComment", "DiscussionSubscription", "DiscussionNotification",
    # Sponsorship & Monetization models (Task 8)
    "TeamSponsor", "SponsorInquiry", "TeamMerchItem", "TeamPromotion",
    # Base models
    "BaseTeam", "BasePlayerMembership",
    # Game-specific team models
    "ValorantTeam", "CS2Team", "Dota2Team", "MLBBTeam",
    "PUBGTeam", "FreeFireTeam", "EFootballTeam", "FC26Team", "CODMTeam",
    # Game-specific membership models
    "ValorantPlayerMembership", "CS2PlayerMembership", "Dota2PlayerMembership",
    "MLBBPlayerMembership", "PUBGPlayerMembership", "FreeFirePlayerMembership",
    "EFootballPlayerMembership", "FC26PlayerMembership", "CODMPlayerMembership",
    # Utilities
    "GAME_TEAM_MODELS", "GAME_MEMBERSHIP_MODELS",
    "get_team_model_for_game", "get_membership_model_for_game",
) if name in globals()]
