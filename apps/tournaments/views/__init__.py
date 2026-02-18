"""
Tournament Views Package

Organizes tournament-related views:
- discovery.py:               Tournament list/discovery (FE-T-001)
- detail.py:                   Tournament detail + check-in (FE-T-002, FE-T-003)
- registration.py:             Registration wizard views (FE-T-004)
- organizer.py:                Organizer hub + dashboard (core classes)
- organizer_participants.py:   Participant management FBVs (FE-T-022)
- organizer_payments.py:       Payment management FBVs (FE-T-023)
- organizer_matches.py:        Match management FBVs (FE-T-024)

Phase 3 Restructure: Views split from monolithic main.py + organizer.py.
"""

from apps.tournaments.views.discovery import TournamentListView  # noqa: F401
from apps.tournaments.views.detail import TournamentDetailView, participant_checkin  # noqa: F401

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

