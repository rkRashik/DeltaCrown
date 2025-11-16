"""
Sprint 4: Tournament Leaderboard & Standings View

FE-T-010: Tournament Leaderboard Page

Public-facing view for displaying real-time tournament standings with 
participant rankings based on match results.
"""

from django.views.generic import DetailView
from django.db.models import Q, Count, Case, When, IntegerField
from django.shortcuts import get_object_or_404

from apps.tournaments.models import Tournament, Match, Registration


class TournamentLeaderboardView(DetailView):
    """
    FE-T-010: Tournament Leaderboard Page
    
    Displays real-time tournament leaderboard with participant standings.
    Calculates ranks based on wins/losses and points from completed matches.
    
    Public access (no authentication required).
    Highlights current user's row if authenticated and participating.
    
    URL: /tournaments/<slug>/leaderboard/
    Template: tournaments/leaderboard/index.html
    Context:
        - tournament: Tournament object
        - standings: List of dicts with rank, participant, stats
        - user_rank: Current user's rank (if participant)
    """
    model = Tournament
    template_name = 'tournaments/public/leaderboard/index.html'
    context_object_name = 'tournament'
    
    def get_queryset(self):
        """Optimize queries with select_related."""
        return Tournament.objects.filter(
            is_deleted=False
        ).select_related(
            'game',
            'organizer',
            'bracket'
        )
    
    def get_context_data(self, **kwargs):
        """Add leaderboard standings to context."""
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Calculate leaderboard standings
        standings = self._calculate_standings(tournament)
        context['standings'] = standings
        
        # Find current user's rank if authenticated and participating
        if self.request.user.is_authenticated:
            user_standing = self._find_user_standing(standings, self.request.user)
            context['user_rank'] = user_standing['rank'] if user_standing else None
            context['user_standing'] = user_standing
        else:
            context['user_rank'] = None
            context['user_standing'] = None
        
        return context
    
    def _calculate_standings(self, tournament):
        """
        Calculate tournament standings from match results.
        
        Returns list of dicts:
        [
            {
                'rank': 1,
                'participant': User or Team object,
                'registration': Registration object,
                'games_played': 5,
                'wins': 4,
                'losses': 1,
                'points': 12,
                'is_current_user': True/False
            },
            ...
        ]
        
        Sorting: Points DESC, Wins DESC, Games Played ASC, Registration ID ASC
        """
        # Get all confirmed registrations with related data
        registrations = tournament.registrations.select_related(
            'user'
        ).filter(
            status=Registration.CONFIRMED,
            is_deleted=False
        ).order_by('id')  # Stable sort for ties
        
        # Check if any completed matches exist
        has_completed_matches = Match.objects.filter(
            tournament=tournament,
            state=Match.COMPLETED,
            is_deleted=False
        ).exists()
        
        # If no completed matches, return empty standings to show empty state
        if not has_completed_matches:
            return []
        
        # Get all completed matches for this tournament - fetch once
        completed_matches = list(Match.objects.filter(
            tournament=tournament,
            state=Match.COMPLETED,
            is_deleted=False
        ).values('participant1_id', 'participant2_id', 'winner_id', 'loser_id'))
        
        # Build standings list
        standings = []
        for registration in registrations:
            # Determine participant (user or team)
            participant = registration.user if registration.user_id else None
            participant_id = registration.user_id if registration.user_id else registration.team_id
            
            # Calculate stats from completed matches (in-memory to avoid N+1)
            games_played = 0
            wins = 0
            losses = 0
            
            for match in completed_matches:
                if match['participant1_id'] == participant_id or match['participant2_id'] == participant_id:
                    games_played += 1
                    if match['winner_id'] == participant_id:
                        wins += 1
                    elif match['loser_id'] == participant_id:
                        losses += 1
            
            points = wins * 3  # Standard tournament scoring: 3 points per win
            
            # Check if this is the current user
            is_current_user = False
            if self.request.user.is_authenticated:
                if registration.user_id:
                    is_current_user = (self.request.user.id == registration.user_id)
                elif registration.team_id:
                    # For team tournaments, would need team membership check
                    # Skipping for now as Sprint 4 focuses on solo tournaments
                    pass
            
            standings.append({
                'rank': 0,  # Will be assigned after sorting
                'participant': participant,
                'registration': registration,
                'games_played': games_played,
                'wins': wins,
                'losses': losses,
                'points': points,
                'is_current_user': is_current_user,
                'registration_id': registration.id,  # For tie-breaking
            })
        
        # Sort by: points DESC, wins DESC, games_played ASC, registration_id ASC
        standings.sort(
            key=lambda x: (
                -x['points'],      # Higher points first
                -x['wins'],        # More wins first
                x['games_played'], # Fewer games first (efficiency)
                x['registration_id']  # Lower ID first (stable sort)
            )
        )
        
        # Assign ranks
        for idx, standing in enumerate(standings, start=1):
            standing['rank'] = idx
        
        return standings
    
    def _find_user_standing(self, standings, user):
        """
        Find the current user's standing in the leaderboard.
        
        Returns the standing dict if found, None otherwise.
        """
        for standing in standings:
            if standing['is_current_user']:
                return standing
        return None
