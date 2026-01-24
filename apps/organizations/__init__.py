"""
Team & Organization Management vNext

This app replaces the legacy apps/teams system.
External apps should ONLY import from services/ module (Phase 2+).

Database Tables:
- All tables use 'organizations_*' prefix
- Completely independent from legacy 'teams_*' tables
- No foreign keys to legacy tables (except TeamMigrationMap)

Phase 1: Models only (no services, views, or APIs yet)
Phase 2: Service layer implementation
Phase 3+: Feature rollout

Related Documentation:
- TEAM_ORG_VNEXT_MASTER_PLAN.md - Overall strategy
- TEAM_ORG_ARCHITECTURE.md - System architecture
- TEAM_ORG_ENGINEERING_STANDARDS.md - Code standards
- TEAM_ORG_PERFORMANCE_CONTRACT.md - Performance requirements
"""

default_app_config = 'apps.organizations.apps.OrganizationsConfig'

# Public API exports (Phase 2+)
# from .services import TeamService, OrganizationService, RankingService
# from .permissions import require_team_permission, require_org_permission

__all__ = [
    # Services will be exported in Phase 2
]
