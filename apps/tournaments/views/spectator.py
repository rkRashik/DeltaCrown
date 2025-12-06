"""
Public Spectator View for live tournaments.

This view provides a comprehensive spectator experience combining:
- Live bracket visualization
- Tournament leaderboard
- Group standings (if applicable)
- Match results
- Tournament information

Implementation Date: November 20, 2025
Feature: FE-T-006 (P1)
"""

from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.http import Http404

from apps.tournaments.models import Tournament
from apps.tournaments.services.bracket_service import BracketService
from apps.tournaments.services.group_stage_service import GroupStageService


class PublicSpectatorView(TemplateView):
    """
    Public spectator view for live tournaments.
    
    Provides a unified interface for spectators to:
    - View live bracket progress
    - Check current standings/leaderboard
    - View match results
    - Access tournament information
    
    No authentication required - fully public.
    Tab-based navigation between different views.
    """
    
    template_name = 'tournaments/spectator/hub.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get tournament
        slug = self.kwargs.get('slug')
        tournament = get_object_or_404(
            Tournament.objects.select_related('organizer', 'game'),
            slug=slug
        )
        
        # Only show spectator view for live/completed tournaments
        if tournament.status not in ['live', 'completed']:
            raise Http404("Spectator view only available for live or completed tournaments")
        
        context['tournament'] = tournament
        
        # Get active tab (default: bracket)
        context['active_tab'] = self.request.GET.get('tab', 'bracket')
        
        # Bracket data (always available)
        try:
            bracket_service = BracketService()
            context['bracket'] = bracket_service.get_bracket(tournament)
            context['has_bracket'] = True
        except Exception:
            context['has_bracket'] = False
        
        # Group stage data (if applicable)
        if tournament.format in ['group_stage', 'group_knockout']:
            try:
                context['groups'] = tournament.groups.prefetch_related(
                    'standings__user',
                    'standings__team'
                ).all()
                context['has_groups'] = len(context['groups']) > 0
                
                # Get game-specific columns for standings
                if context['has_groups'] and tournament.game:
                    from apps.games.services import game_service
                    canonical_slug = game_service.normalize_slug(tournament.game.slug)
                    context['game_columns'] = GroupStageService._get_game_columns(canonical_slug)
            except Exception:
                context['has_groups'] = False
        else:
            context['has_groups'] = False
        
        # Leaderboard data
        context['standings'] = tournament.standings.select_related(
            'user',
            'team'
        ).order_by('-points', '-wins', 'losses')[:50]  # Top 50
        
        # Recent matches
        context['recent_matches'] = tournament.matches.select_related(
            'participant1__user',
            'participant1__team',
            'participant2__user',
            'participant2__team'
        ).filter(
            status='completed'
        ).order_by('-completed_at')[:10]  # Last 10 matches
        
        # Upcoming matches
        context['upcoming_matches'] = tournament.matches.select_related(
            'participant1__user',
            'participant1__team',
            'participant2__user',
            'participant2__team'
        ).filter(
            status='scheduled',
            scheduled_time__isnull=False
        ).order_by('scheduled_time')[:10]  # Next 10 matches
        
        # Tournament stats
        context['total_matches'] = tournament.matches.count()
        context['completed_matches'] = tournament.matches.filter(status='completed').count()
        context['live_matches'] = tournament.matches.filter(status='in_progress').count()
        
        return context
