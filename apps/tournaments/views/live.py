"""
Sprint 3: Public Live Tournament Experience Views

FE-T-008: Live Bracket View
FE-T-009: Match Watch / Match Detail Page
FE-T-018: Tournament Results Page

Public-facing views for spectators and participants to view live tournaments,
watch matches, and view final results.
"""

from django.views.generic import DetailView
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.http import Http404

from apps.tournaments.models import Tournament, Match, Registration
from apps.tournaments.models.result import TournamentResult


class TournamentBracketView(DetailView):
    """
    FE-T-008: Live Bracket View
    
    Displays tournament bracket structure with matches organized by round.
    Public access (no authentication required).
    
    URL: /tournaments/<slug>/bracket/
    Template: tournaments/live/bracket.html
    """
    model = Tournament
    template_name = 'tournaments/public/live/bracket.html'
    context_object_name = 'tournament'
    
    def get_queryset(self):
        """Optimize queries with select_related and prefetch_related."""
        return Tournament.objects.filter(
            is_deleted=False
        ).select_related(
            'game',
            'organizer',
            'bracket'  # OneToOne relationship
        ).prefetch_related(
            Prefetch(
                'matches',
                queryset=Match.objects.filter(
                    is_deleted=False
                ).select_related(
                    'tournament'
                ).order_by('round_number', 'match_number')
            )
        )
    
    def get_context_data(self, **kwargs):
        """Add bracket-specific context."""
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Check if bracket is available
        bracket_available = self._is_bracket_available(tournament)
        context['bracket_available'] = bracket_available
        
        if bracket_available:
            # Organize matches by round
            matches_by_round = {}
            for match in tournament.matches.all():
                round_num = match.round_number
                if round_num not in matches_by_round:
                    matches_by_round[round_num] = {
                        'round_number': round_num,
                        'round_name': self._get_round_name(round_num, tournament),
                        'matches': []
                    }
                matches_by_round[round_num]['matches'].append(match)
            
            # Sort by round number
            context['matches_by_round'] = sorted(
                matches_by_round.values(),
                key=lambda x: x['round_number']
            )
            context['bracket'] = tournament.bracket
        else:
            context['matches_by_round'] = []
            context['bracket'] = None
            context['not_ready_reason'] = self._get_not_ready_reason(tournament)
        
        return context
    
    def _is_bracket_available(self, tournament):
        """Determine if bracket can be displayed."""
        # Too early states
        if tournament.status in [
            Tournament.DRAFT,
            Tournament.PENDING_APPROVAL,
            Tournament.PUBLISHED,
            Tournament.REGISTRATION_OPEN
        ]:
            return False
        
        # Cancelled tournament
        if tournament.status == Tournament.CANCELLED:
            return False
        
        # No bracket generated
        if not hasattr(tournament, 'bracket') or not tournament.bracket:
            return False
        
        # Bracket generation not complete
        if not tournament.bracket.is_finalized:
            return False
        
        return True
    
    def _get_not_ready_reason(self, tournament):
        """Get human-readable reason why bracket is not available."""
        if tournament.status == Tournament.CANCELLED:
            return "Tournament has been cancelled."
        
        if tournament.status in [Tournament.DRAFT, Tournament.PENDING_APPROVAL]:
            return "Tournament is not yet published."
        
        if tournament.status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN]:
            return "Tournament is still accepting registrations. Bracket will be generated once registration closes."
        
        if tournament.status == Tournament.REGISTRATION_CLOSED:
            return "Bracket is being generated. Please check back soon."
        
        if not hasattr(tournament, 'bracket') or not tournament.bracket:
            return "Bracket has not been generated yet."
        
        if hasattr(tournament, 'bracket') and not tournament.bracket.is_generated:
            return "Bracket generation is in progress."
        
        return "Bracket is not available at this time."
    
    def _get_round_name(self, round_number, tournament):
        """Get friendly name for round (e.g., 'Quarter Finals', 'Semi Finals')."""
        if hasattr(tournament, 'bracket') and tournament.bracket:
            bracket_structure = tournament.bracket.bracket_structure or {}
            rounds = bracket_structure.get('rounds', [])
            
            for round_data in rounds:
                if round_data.get('round_number') == round_number:
                    return round_data.get('round_name', f'Round {round_number}')
        
        # Fallback naming
        return f'Round {round_number}'


class MatchDetailView(DetailView):
    """
    FE-T-009: Match Watch / Match Detail Page
    
    Displays detailed match information including participants, scores,
    timeline, and lobby info (for participants only).
    Public access (no authentication required).
    
    URL: /tournaments/<slug>/matches/<int:match_id>/
    Template: tournaments/live/match_detail.html
    """
    model = Match
    template_name = 'tournaments/public/live/match_detail.html'
    context_object_name = 'match'
    pk_url_kwarg = 'match_id'
    
    def get_queryset(self):
        """Filter by tournament slug for security and optimize queries."""
        tournament_slug = self.kwargs.get('slug')
        return Match.objects.filter(
            tournament__slug=tournament_slug,
            is_deleted=False
        ).select_related(
            'tournament',
            'tournament__game',
            'tournament__organizer'
        )
    
    def get_object(self, queryset=None):
        """Override to validate tournament slug matches."""
        if queryset is None:
            queryset = self.get_queryset()
        
        match_id = self.kwargs.get(self.pk_url_kwarg)
        tournament_slug = self.kwargs.get('slug')
        
        try:
            obj = queryset.get(pk=match_id)
        except Match.DoesNotExist:
            raise Http404(f"Match not found in tournament '{tournament_slug}'")
        
        return obj
    
    def get_context_data(self, **kwargs):
        """Add match-specific context."""
        context = super().get_context_data(**kwargs)
        match = self.object
        
        # Add tournament context
        context['tournament'] = match.tournament
        
        # Participant details (user lookup for display)
        context['participant1'] = self._get_participant_details(match.participant1_id)
        context['participant2'] = self._get_participant_details(match.participant2_id)
        
        # Check if current user is participant
        if self.request.user.is_authenticated:
            context['is_participant'] = (
                match.participant1_id == self.request.user.id or 
                match.participant2_id == self.request.user.id
            )
        else:
            context['is_participant'] = False
        
        # Show lobby info only to participants
        context['show_lobby_info'] = context['is_participant'] and match.lobby_info
        
        # Match timeline (basic events)
        context['timeline'] = self._build_match_timeline(match)
        
        return context
    
    def _get_participant_details(self, user_id):
        """Get user details for a participant."""
        if not user_id:
            return None
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    def _build_match_timeline(self, match):
        """Build timeline of match events."""
        timeline = []
        
        # Match scheduled
        if match.scheduled_time:
            timeline.append({
                'timestamp': match.scheduled_time,
                'event': 'Match Scheduled',
                'icon': 'calendar',
                'description': f'Match scheduled for {match.scheduled_time.strftime("%B %d, %Y at %I:%M %p")}'
            })
        
        # Match started (if live or completed)
        if match.state in [Match.LIVE, Match.COMPLETED, Match.PENDING_RESULT]:
            timeline.append({
                'timestamp': match.updated_at,  # Approximate
                'event': 'Match Started',
                'icon': 'play',
                'description': 'Match is now live'
            })
        
        # Match completed
        if match.state == Match.COMPLETED and match.winner_id:
            winner = self._get_participant_details(match.winner_id)
            winner_name = winner.username if winner else 'Unknown'
            timeline.append({
                'timestamp': match.updated_at,
                'event': 'Match Completed',
                'icon': 'check',
                'description': f'{winner_name} won the match'
            })
        
        # Match forfeit
        if match.state == Match.FORFEIT:
            timeline.append({
                'timestamp': match.updated_at,
                'event': 'Match Forfeit',
                'icon': 'alert',
                'description': 'Match ended by forfeit'
            })
        
        return timeline


class TournamentResultsView(DetailView):
    """
    FE-T-018: Tournament Results Page
    
    Displays final tournament results including winners podium,
    final leaderboard, and match history.
    Public access (no authentication required).
    
    URL: /tournaments/<slug>/results/
    Template: tournaments/live/results.html
    """
    model = Tournament
    template_name = 'tournaments/public/live/results.html'
    context_object_name = 'tournament'
    
    def get_queryset(self):
        """Only show results for completed tournaments. Optimize queries."""
        return Tournament.objects.filter(
            is_deleted=False
        ).select_related(
            'game',
            'organizer',
            'result',  # OneToOne TournamentResult
            'result__winner',
            'result__winner__user',
            'result__runner_up',
            'result__runner_up__user',
            'result__third_place',
            'result__third_place__user'
        ).prefetch_related(
            Prefetch(
                'registrations',
                queryset=Registration.objects.filter(
                    is_deleted=False
                ).select_related('user').order_by('seed')
            ),
            Prefetch(
                'matches',
                queryset=Match.objects.filter(
                    is_deleted=False,
                    state=Match.COMPLETED
                ).select_related('tournament').order_by('round_number', 'match_number')
            )
        )
    
    def get_object(self, queryset=None):
        """Override to provide better error message for incomplete tournaments."""
        obj = super().get_object(queryset)
        
        # Check if tournament is completed
        if obj.status not in [Tournament.COMPLETED, Tournament.ARCHIVED]:
            # Allow viewing results if TournamentResult exists (manual finalization)
            if not hasattr(obj, 'result') or not obj.result:
                raise Http404("Tournament results are not available yet. Tournament is still in progress.")
        
        return obj
    
    def get_context_data(self, **kwargs):
        """Add results-specific context."""
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Results
        has_results = hasattr(tournament, 'result') and tournament.result is not None
        context['has_results'] = has_results
        context['result'] = tournament.result if has_results else None
        
        if has_results:
            result = tournament.result
            
            # Winners (with user details)
            context['winner'] = result.winner
            context['runner_up'] = result.runner_up
            context['third_place'] = result.third_place
            
            # Determination method (for display)
            context['determination_method'] = result.get_determination_method_display()
        
        # All completed matches
        context['completed_matches'] = tournament.matches.filter(state=Match.COMPLETED)
        
        # Leaderboard (all registrations)
        # Note: In production, this would be sorted by final placement
        # For now, we use seed as proxy
        context['leaderboard'] = tournament.registrations.all()
        
        # Tournament stats
        context['stats'] = self._calculate_tournament_stats(tournament)
        
        return context
    
    def _calculate_tournament_stats(self, tournament):
        """Calculate tournament statistics."""
        stats = {
            'total_participants': tournament.registrations.count(),
            'total_matches': tournament.matches.count(),
            'completed_matches': tournament.matches.filter(state=Match.COMPLETED).count(),
        }
        
        # Tournament duration
        if tournament.tournament_start and tournament.tournament_end:
            duration = tournament.tournament_end - tournament.tournament_start
            stats['duration_days'] = duration.days
            stats['duration_hours'] = duration.total_seconds() / 3600
        
        return stats
