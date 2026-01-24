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

from .organization import Organization, OrganizationMembership
from .team import Team
from .membership import TeamMembership
from .ranking import TeamRanking, OrganizationRanking
from .migration import TeamMigrationMap
from .activity import TeamActivityLog

__all__ = [
    # Organization models
    'Organization',
    'OrganizationMembership',
    
    # Team models
    'Team',
    'TeamMembership',
    
    # Ranking models
    'TeamRanking',
    'OrganizationRanking',
    
    # Migration bridge
    'TeamMigrationMap',
    
    # Audit logging
    'TeamActivityLog',
]
