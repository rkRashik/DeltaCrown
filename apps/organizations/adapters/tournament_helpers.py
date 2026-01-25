"""
Tournament Integration Helpers for TeamAdapter

This module provides integration points for tournaments to use the TeamAdapter
without modifying complex existing tournament service files.

Usage in tournaments app:
    from apps.organizations.adapters.tournament_helpers import (
        get_team_url_for_tournament,
        validate_team_roster_for_tournament,
    )

Phase 3 Strategy:
- Provide wrapper functions that tournaments can call
- Minimal changes to existing tournament code (just import swap)
- Zero breaking changes to legacy team behavior

Phase 4 Goals:
- Migrate tournament services to call these helpers directly
- Deprecate direct team model access in tournaments
"""

from typing import Dict, Any, Optional

from .team_adapter import TeamAdapter
from apps.organizations.services.exceptions import NotFoundError


def get_team_url_for_tournament(team_id: int) -> str:
    """
    Generate team detail URL for tournament notifications/links.
    
    This function routes to correct team system (legacy or vNext) automatically.
    
    Args:
        team_id: Primary key of team
        
    Returns:
        Absolute URL path for team detail page
        
    Raises:
        NotFoundError: If team_id invalid
        
    Usage Example:
        # In tournaments/services/registration_service.py
        from apps.organizations.adapters.tournament_helpers import get_team_url_for_tournament
        
        team_url = get_team_url_for_tournament(registration.team_id)
        notify_team(team, url=team_url, title="Tournament Registration Confirmed")
    
    Performance:
        ≤2 queries (routing decision + URL lookup)
    """
    adapter = TeamAdapter()
    return adapter.get_team_url(team_id)


def validate_team_roster_for_tournament(
    team_id: int,
    tournament_id: Optional[int] = None,
    game_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Validate team roster eligibility for tournament registration.
    
    This function routes to correct team system (legacy or vNext) automatically.
    
    Args:
        team_id: Primary key of team
        tournament_id: Optional tournament ID for tournament-specific rules
        game_id: Optional game ID for game-specific validation
        
    Returns:
        Dictionary with:
            - is_valid: bool
            - errors: List[str]  # Blocking errors
            - warnings: List[str]  # Non-blocking warnings
            - roster_data: Dict[str, Any]  # Debug info
            
    Raises:
        NotFoundError: If team_id invalid
        
    Usage Example:
        # In tournaments/services/eligibility_service.py
        from apps.organizations.adapters.tournament_helpers import validate_team_roster_for_tournament
        
        validation = validate_team_roster_for_tournament(
            team_id=request.POST['team_id'],
            tournament_id=tournament.id,
            game_id=tournament.game_id,
        )
        
        if not validation['is_valid']:
            return render(request, 'error.html', {'errors': validation['errors']})
    
    Performance:
        ≤6 queries (routing + roster lookup + validation logic)
    """
    adapter = TeamAdapter()
    return adapter.validate_roster(
        team_id=team_id,
        tournament_id=tournament_id,
        game_id=game_id,
    )


def get_team_identity_for_tournament(team_id: int) -> Dict[str, Any]:
    """
    Retrieve team branding/metadata for tournament brackets and displays.
    
    This function routes to correct team system (legacy or vNext) automatically.
    
    Args:
        team_id: Primary key of team
        
    Returns:
        Dictionary with team identity fields (see contracts.py for structure)
        
    Raises:
        NotFoundError: If team_id invalid
        
    Usage Example:
        # In tournaments/services/bracket_generator.py
        from apps.organizations.adapters.tournament_helpers import get_team_identity_for_tournament
        
        team_identity = get_team_identity_for_tournament(match.team1_id)
        bracket_data['team1'] = {
            'name': team_identity['name'],
            'logo': team_identity['logo_url'],
            'badge': team_identity['badge_url'],  # Org badge if applicable
        }
    
    Performance:
        ≤3 queries (routing + team lookup with select_related)
    """
    adapter = TeamAdapter()
    return adapter.get_team_identity(team_id)


# ============================================================================
# MIGRATION NOTES FOR TOURNAMENTS APP
# ============================================================================

"""
PHASE 3 MIGRATION GUIDE FOR TOURNAMENTS APP:

1. ROSTER VALIDATION (HIGH PRIORITY):
   Current Location: tournaments/services/eligibility_service.py
   Current Code:
       from apps.teams.models import Team, TeamMembership
       team = Team.objects.get(id=team_id)
       members = TeamMembership.objects.filter(team=team, status='ACTIVE')
   
   Updated Code (Phase 3):
       from apps.organizations.adapters.tournament_helpers import validate_team_roster_for_tournament
       validation = validate_team_roster_for_tournament(team_id, tournament_id=tournament.id)
       if not validation['is_valid']:
           return {'error': validation['errors']}

2. TEAM URL GENERATION (MEDIUM PRIORITY):
   Current Location: tournaments/signals.py, tournaments/views.py
   Current Code:
       from django.urls import reverse
       team_url = reverse('teams:team_detail', kwargs={'slug': team.slug})
   
   Updated Code (Phase 3):
       from apps.organizations.adapters.tournament_helpers import get_team_url_for_tournament
       team_url = get_team_url_for_tournament(team.id)

3. BRACKET GENERATION (MEDIUM PRIORITY):
   Current Location: tournaments/services/bracket_generator.py
   Current Code:
       team_data = {
           'name': team.name,
           'logo': team.logo.url if team.logo else '',
       }
   
   Updated Code (Phase 3):
       from apps.organizations.adapters.tournament_helpers import get_team_identity_for_tournament
       team_identity = get_team_identity_for_tournament(team.id)
       team_data = {
           'name': team_identity['name'],
           'logo': team_identity['logo_url'],
           'badge': team_identity['badge_url'],  # New: org badge support
       }

TIMELINE:
- Phase 3 (current): Provide helpers, document migration points
- Phase 4: Migrate high-priority integrations (roster validation, URLs)
- Phase 5: Complete migration of all tournament<->team integrations
- Phase 6-7: Remove legacy team model imports from tournaments

TESTING STRATEGY:
- Create integration tests in tournaments app
- Test with both legacy and vNext teams
- Verify zero breaking changes to existing tournament registrations
"""
