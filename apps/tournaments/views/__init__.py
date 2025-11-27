"""
Tournament Views Package

Organizes tournament-related views:
- main.py: Main list and detail views (FE-T-001, FE-T-002, FE-T-003)
- registration.py: Registration wizard views (FE-T-004)

Sprint 1 Implementation (November 15, 2025):
All Sprint 1 views are exported from this package for consistent imports.
"""

from apps.tournaments.views.main import (
    TournamentListView,
    TournamentDetailView,
    participant_checkin,
)

from apps.tournaments.views.registration import (
    TournamentRegistrationView,
    TournamentRegistrationSuccessView,
)

from apps.tournaments.views.tournament_team_registration import (
    RegistrationSuccessView,
)

__all__ = [
    # Sprint 1 main views (FE-T-001, FE-T-002, FE-T-003)
    'TournamentListView',
    'TournamentDetailView',
    'participant_checkin',
    
    # Registration wizard views (FE-T-004)
    'TournamentRegistrationView',
    'TournamentRegistrationSuccessView',
    
    # Demo registration views
    'RegistrationSuccessView',
]

