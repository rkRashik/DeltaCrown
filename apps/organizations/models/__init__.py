"""
Model exports for apps.organizations.

All models use explicit db_table with 'organizations_*' prefix.
This ensures complete separation from legacy 'teams_*' tables.

Database Tables Created:
- organizations_organization: Professional esports brands
- organizations_org_membership: Organization-level staff
- organizations_team: Competitive units
- organizations_membership: Team roster assignments
- organizations_ranking: Team Crown Point rankings
- organizations_org_ranking: Organization Empire Score rankings
- organizations_migration_map: Legacy-to-vNext bridge (Phase 5-7)
- organizations_activity_log: Audit trail for all actions

HARD RULE: Do NOT import from apps.teams.models in this app.
"""

import os

from .organization import Organization, OrganizationMembership
from .team import Team

_MINIMAL_TEST_APPS = os.environ.get("DELTA_MINIMAL_TEST_APPS") == "1"

__all__ = [
    'Organization',
    'OrganizationMembership',
    'Team',
]

if not _MINIMAL_TEST_APPS:
    from .organization_profile import OrganizationProfile
    from .membership import TeamMembership
    from .membership_event import TeamMembershipEvent
    from .team_invite import TeamInvite
    from .ranking import TeamRanking, OrganizationRanking
    from .migration import TeamMigrationMap
    from .activity import TeamActivityLog
    from .announcement import TeamAnnouncement
    from .team_media import TeamMedia, TeamHighlight
    from .team_follower import TeamFollower
    from .discord_sync import DiscordChatMessage
    from .join_request import TeamJoinRequest
    from .recruitment import RecruitmentPosition, RecruitmentRequirement
    from .journey import TeamJourneyMilestone

    __all__.extend([
        'OrganizationProfile',
        'TeamMembership',
        'TeamMembershipEvent',
        'TeamInvite',
        'TeamRanking',
        'OrganizationRanking',
        'TeamMigrationMap',
        'TeamActivityLog',
        'TeamAnnouncement',
        'TeamMedia',
        'TeamHighlight',
        'DiscordChatMessage',
        'TeamJoinRequest',
        'RecruitmentPosition',
        'RecruitmentRequirement',
        'TeamJourneyMilestone',
    ])
