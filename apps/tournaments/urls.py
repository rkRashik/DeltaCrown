"""
Tournament URL configuration.

Sprint 1 Frontend Implementation (November 15, 2025):
- FE-T-001: Tournament List Page (/tournaments/)
- FE-T-002: Tournament Detail Page (/tournaments/<slug>/)
- FE-T-003: Registration CTA States (part of detail page)
- FE-T-004: Registration Wizard (/tournaments/<slug>/register/)

Sprint 2 Frontend Implementation (November 15, 2025):
- FE-T-005: My Tournaments Dashboard (/tournaments/my/)
- My Matches View (/tournaments/my/matches/)

Sprint 3 Frontend Implementation (November 15, 2025):
- FE-T-008: Live Bracket View (/tournaments/<slug>/bracket/)
- FE-T-009: Match Detail Page (/tournaments/<slug>/matches/<id>/)
- FE-T-018: Tournament Results Page (/tournaments/<slug>/results/)

Sprint 4 Frontend Implementation (November 16, 2025):
- FE-T-010: Tournament Leaderboard Page (/tournaments/<slug>/leaderboard/)

Sprint 5 Frontend Implementation (November 16, 2025):
- FE-T-007: Tournament Lobby/Participant Hub (/tournaments/<slug>/lobby/)
- Check-In Action (/tournaments/<slug>/check-in/)
- Check-In Status Polling (/tournaments/<slug>/check-in-status/)
- Roster View (/tournaments/<slug>/roster/)

Backend APIs:
- Admin panel: /admin/tournaments/ (Django admin)
- API endpoints: /api/tournaments/ (Module 3.1)

Source Documents:
- Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md
- Documents/ExecutionPlan/FrontEnd/Screens/FRONTEND_TOURNAMENT_SITEMAP.md
- Documents/ExecutionPlan/FrontEnd/SPRINT_4_LEADERBOARDS_PLAN.md
- Documents/ExecutionPlan/FrontEnd/SPRINT_5_CHECK_IN_PLAN.md
"""

from django.urls import path
from django.views.generic import RedirectView
from apps.tournaments import views
from apps.tournaments.views import (
    TournamentRegistrationView,
    TournamentRegistrationSuccessView,
)
from apps.tournaments.views.player import (
    TournamentPlayerDashboardView,
    TournamentPlayerMatchesView,
)
from apps.tournaments.views.live import (
    TournamentBracketView,
    MatchDetailView,
    TournamentResultsView,
)
from apps.tournaments.views.leaderboard import (
    TournamentLeaderboardView,
)
from apps.tournaments.views import checkin

app_name = 'tournaments'

urlpatterns = [
    # FE-T-001: Tournament List/Discovery Page
    path('', views.TournamentListView.as_view(), name='list'),
    
    # Sprint 2: Player Dashboard URLs (must be before <slug> pattern)
    path('my/', TournamentPlayerDashboardView.as_view(), name='my_tournaments'),
    path('my/matches/', TournamentPlayerMatchesView.as_view(), name='my_matches'),
    
    # FE-T-002: Tournament Detail Page (includes FE-T-003: CTA states)
    path('<slug:slug>/', views.TournamentDetailView.as_view(), name='detail'),
    
    # FE-T-004: Registration Wizard
    path('<slug:slug>/register/', TournamentRegistrationView.as_view(), name='register'),
    path('<slug:slug>/register/success/', TournamentRegistrationSuccessView.as_view(), name='register_success'),
    
    # Sprint 3: Public Live Tournament Experience
    # FE-T-008: Live Bracket View
    path('<slug:slug>/bracket/', TournamentBracketView.as_view(), name='bracket'),
    # FE-T-009: Match Watch / Match Detail Page
    path('<slug:slug>/matches/<int:match_id>/', MatchDetailView.as_view(), name='match_detail'),
    # FE-T-018: Tournament Results Page
    path('<slug:slug>/results/', TournamentResultsView.as_view(), name='results'),
    
    # Sprint 4: Leaderboard & Standings
    # FE-T-010: Tournament Leaderboard Page
    path('<slug:slug>/leaderboard/', TournamentLeaderboardView.as_view(), name='leaderboard'),
    
    # Sprint 5: Check-In & Tournament Lobby (FE-T-007)
    path('<slug:slug>/lobby/', checkin.TournamentLobbyView.as_view(), name='lobby'),
    path('<slug:slug>/check-in/', checkin.CheckInActionView.as_view(), name='check_in'),
    path('<slug:slug>/check-in-status/', checkin.CheckInStatusView.as_view(), name='check_in_status'),
    path('<slug:slug>/roster/', checkin.RosterView.as_view(), name='roster'),
    
    # Legacy URL compatibility
    path('hub/', RedirectView.as_view(pattern_name='tournaments:list', permanent=True), name='hub'),
]

# Note: Actual tournament management is done through:
# 1. Django Admin: /admin/tournaments/
# 2. REST API: /api/tournaments/ (Module 3.1)
# 3. Future frontend will be rebuilt from scratch

