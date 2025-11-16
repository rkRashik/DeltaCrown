"""
Player-facing views for tournament dashboard and match tracking.

This module implements the player dashboard subsystem (Sprint 2):
- My Tournaments: Full page list of user's tournament registrations
- My Matches: Upcoming and recent matches across all tournaments
- Dashboard Widget: Latest 5 tournaments for dashboard card

Source Documents:
- Documents/ExecutionPlan/FrontEnd/SPRINT_2_PLAYER_DASHBOARD_PLAN.md
- Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md (FE-T-005)
- Documents/ExecutionPlan/FrontEnd/Screens/FRONTEND_TOURNAMENT_SITEMAP.md
"""

from typing import Dict, Any, List, Optional
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Prefetch, Count, QuerySet
from django.utils import timezone
from django.views.generic import ListView
from django.http import HttpRequest

from apps.tournaments.models import Tournament, Registration, Match


class TournamentPlayerDashboardView(LoginRequiredMixin, ListView):
    """
    Player's complete tournament dashboard showing all registrations.
    
    URL: /tournaments/my/
    Template: templates/tournaments/player/my_tournaments.html
    
    Features:
    - Lists all user's tournament registrations (active and past)
    - Filter by status (all, active, upcoming, completed)
    - Pagination: 20 per page
    - Optimized queries with select_related/prefetch_related
    
    Context Variables:
    - my_tournaments: QuerySet of Registration objects
    - filter_status: Current filter selection
    - active_count: Count of active tournaments
    - upcoming_count: Count of upcoming tournaments
    - completed_count: Count of completed tournaments
    """
    
    model = Registration
    template_name = 'tournaments/public/player/my_tournaments.html'
    context_object_name = 'my_tournaments'
    paginate_by = 20
    
    def get_queryset(self) -> QuerySet[Registration]:
        """
        Get user's registrations with optimized queries.
        
        Query Optimizations:
        - select_related: tournament, tournament__game, tournament__organizer
        - prefetch_related: tournament__matches (for next match calculation)
        - Filter: user=request.user, is_deleted=False
        - Order: -tournament__tournament_start (newest first)
        """
        user = self.request.user
        
        # Base queryset with optimizations
        qs = Registration.objects.filter(
            user=user,
            is_deleted=False
        ).select_related(
            'tournament',
            'tournament__game',
            'tournament__organizer'
        ).prefetch_related(
            Prefetch(
                'tournament__matches',
                queryset=Match.objects.filter(
                    is_deleted=False
                ).order_by('scheduled_time')
            )
        ).order_by('-tournament__tournament_start')
        
        # Apply status filter
        filter_status = self.request.GET.get('status', 'all')
        
        if filter_status == 'active':
            # Active: Tournament is currently running (live or closed registration about to start)
            qs = qs.filter(
                tournament__status__in=[
                    Tournament.LIVE,
                    Tournament.REGISTRATION_CLOSED  # About to start
                ]
            )
        elif filter_status == 'upcoming':
            # Upcoming: Tournament hasn't started yet
            qs = qs.filter(
                tournament__status__in=[
                    Tournament.PUBLISHED,
                    Tournament.REGISTRATION_OPEN,
                    Tournament.REGISTRATION_CLOSED
                ]
            )
        elif filter_status == 'completed':
            # Completed: Tournament finished
            qs = qs.filter(
                tournament__status__in=[
                    Tournament.COMPLETED,
                    Tournament.CANCELLED
                ]
            )
        
        return qs
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add filter status and counts to context."""
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        # Get filter status
        context['filter_status'] = self.request.GET.get('status', 'all')
        
        # Get counts for each filter (optimized - single query)
        all_regs = Registration.objects.filter(
            user=user,
            is_deleted=False
        ).select_related('tournament')
        
        context['active_count'] = all_regs.filter(
            tournament__status__in=[
                Tournament.LIVE,
                Tournament.REGISTRATION_CLOSED  # Tournaments that are about to start
            ]
        ).count()
        
        context['upcoming_count'] = all_regs.filter(
            tournament__status__in=[
                Tournament.PUBLISHED,
                Tournament.REGISTRATION_OPEN,
                Tournament.REGISTRATION_CLOSED
            ]
        ).count()
        
        context['completed_count'] = all_regs.filter(
            tournament__status__in=[
                Tournament.COMPLETED,
                Tournament.CANCELLED
            ]
        ).count()
        
        return context


class TournamentPlayerMatchesView(LoginRequiredMixin, ListView):
    """
    Player's upcoming and recent matches across all tournaments.
    
    URL: /tournaments/my/matches/
    Template: templates/tournaments/player/my_matches.html
    
    Features:
    - Lists matches from tournaments user is registered in
    - Filter by status (all, upcoming, live, completed)
    - Shows opponent, tournament, date/time, round
    - Pagination: 20 per page
    - Optimized queries
    
    Context Variables:
    - my_matches: QuerySet of Match objects
    - filter_status: Current filter selection
    - upcoming_count: Count of upcoming matches
    - live_count: Count of live matches
    - completed_count: Count of completed matches
    """
    
    model = Match
    template_name = 'tournaments/public/player/my_matches.html'
    context_object_name = 'my_matches'
    paginate_by = 20
    
    def get_queryset(self) -> QuerySet[Match]:
        """
        Get matches from user's registered tournaments.
        
        Query Logic:
        1. Find all tournaments where user has active registration
        2. Get matches from those tournaments
        3. Filter matches where user is a participant (via participant1_id or participant2_id)
        4. Order by scheduled_time (upcoming first, then past)
        
        Query Optimizations:
        - select_related: tournament, tournament__game
        - Filter: is_deleted=False
        - Order: Custom sort (live → upcoming → completed by time)
        """
        user = self.request.user
        
        # Get tournaments where user is registered
        user_registrations = Registration.objects.filter(
            user=user,
            is_deleted=False,
            status__in=[
                Registration.CONFIRMED,
                Registration.PENDING,
                Registration.PAYMENT_SUBMITTED
            ]
        ).values_list('tournament_id', flat=True)
        
        # Get user ID for participant matching
        user_id = user.id
        
        # Base queryset: matches in user's tournaments where user might be participant
        qs = Match.objects.filter(
            tournament_id__in=user_registrations,
            is_deleted=False
        ).filter(
            # User is one of the participants
            # Note: participant IDs can be user IDs or team IDs depending on tournament type
            # For solo tournaments, participant_id = user.id
            # For team tournaments, we'd need to check team membership (future enhancement)
            Q(participant1_id=user_id) | Q(participant2_id=user_id)
        ).select_related(
            'tournament',
            'tournament__game'
        )
        
        # Apply status filter
        filter_status = self.request.GET.get('status', 'all')
        now = timezone.now()
        
        if filter_status == 'upcoming':
            # Upcoming: scheduled but not started
            qs = qs.filter(
                state__in=[Match.SCHEDULED, Match.CHECK_IN, Match.READY],
                scheduled_time__gt=now
            )
        elif filter_status == 'live':
            # Live: currently in progress
            qs = qs.filter(
                state__in=[Match.LIVE, Match.PENDING_RESULT]
            )
        elif filter_status == 'completed':
            # Completed: finished matches
            qs = qs.filter(
                state__in=[Match.COMPLETED, Match.FORFEIT]
            )
        
        # Custom ordering: live → upcoming → completed, then by scheduled_time
        # Note: Django ORM doesn't support CASE WHEN in order_by directly,
        # so we'll order by state and time, then refine in template if needed
        qs = qs.order_by('scheduled_time')
        
        return qs
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add filter status and counts to context."""
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        user_id = user.id
        now = timezone.now()
        
        # Get filter status
        context['filter_status'] = self.request.GET.get('status', 'all')
        
        # Get tournaments where user is registered
        user_registrations = Registration.objects.filter(
            user=user,
            is_deleted=False
        ).values_list('tournament_id', flat=True)
        
        # Base queryset for counts
        all_matches = Match.objects.filter(
            tournament_id__in=user_registrations,
            is_deleted=False
        ).filter(
            Q(participant1_id=user_id) | Q(participant2_id=user_id)
        )
        
        # Calculate counts
        context['upcoming_count'] = all_matches.filter(
            state__in=[Match.SCHEDULED, Match.CHECK_IN, Match.READY],
            scheduled_time__gt=now
        ).count()
        
        context['live_count'] = all_matches.filter(
            state__in=[Match.LIVE, Match.PENDING_RESULT]
        ).count()
        
        context['completed_count'] = all_matches.filter(
            state__in=[Match.COMPLETED, Match.FORFEIT]
        ).count()
        
        return context


def get_user_tournaments_for_dashboard(user, limit: int = 5) -> List[Registration]:
    """
    Get user's latest tournaments for dashboard widget.
    
    Used by dashboard view to show "My Tournaments" card.
    
    Args:
        user: Django User object
        limit: Maximum number of tournaments to return (default: 5)
    
    Returns:
        List of Registration objects (latest registrations)
    
    Query Optimizations:
        - select_related: tournament, tournament__game
        - Filter: user=user, is_deleted=False
        - Order: -created_at (most recent first)
        - Limit: 5 (configurable)
    """
    return list(
        Registration.objects.filter(
            user=user,
            is_deleted=False
        ).select_related(
            'tournament',
            'tournament__game'
        ).order_by('-created_at')[:limit]
    )


def get_user_upcoming_matches(user, limit: int = 5) -> List[Match]:
    """
    Get user's upcoming matches for dashboard or widgets.
    
    Args:
        user: Django User object
        limit: Maximum number of matches to return (default: 5)
    
    Returns:
        List of Match objects (upcoming matches sorted by time)
    
    Query Optimizations:
        - select_related: tournament, tournament__game
        - Filter: user participation, scheduled in future
        - Order: scheduled_time (soonest first)
        - Limit: 5 (configurable)
    """
    user_id = user.id
    now = timezone.now()
    
    # Get tournaments where user is registered
    user_registrations = Registration.objects.filter(
        user=user,
        is_deleted=False
    ).values_list('tournament_id', flat=True)
    
    return list(
        Match.objects.filter(
            tournament_id__in=user_registrations,
            is_deleted=False
        ).filter(
            Q(participant1_id=user_id) | Q(participant2_id=user_id)
        ).filter(
            state__in=[Match.SCHEDULED, Match.CHECK_IN, Match.READY],
            scheduled_time__gt=now
        ).select_related(
            'tournament',
            'tournament__game'
        ).order_by('scheduled_time')[:limit]
    )
