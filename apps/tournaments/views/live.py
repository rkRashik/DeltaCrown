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
from decimal import Decimal
import json

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
        """Add match-specific context with team data, player stats, and map scores."""
        context = super().get_context_data(**kwargs)
        match = self.object
        tournament = match.tournament

        context['tournament'] = tournament

        # ── Round label ──
        DOUBLE_ELIM_LABELS = {
            1: 'UB Round 1', 2: 'UB Quarterfinals', 3: 'UB Semifinals', 4: 'UB Final',
            5: 'LB Round 1', 6: 'LB Round 2', 7: 'LB Round 3', 8: 'LB Round 4',
            9: 'LB Semifinal', 10: 'LB Final', 11: 'Grand Final',
        }
        if tournament.format == 'double_elimination' and match.round_number:
            context['round_label'] = DOUBLE_ELIM_LABELS.get(match.round_number, f'Round {match.round_number}')
        else:
            context['round_label'] = match.round_name or f'Round {match.round_number}'

        # ── Team info (for team tournaments) ──
        team1 = self._get_team(match.participant1_id)
        team2 = self._get_team(match.participant2_id)
        context['team1'] = team1
        context['team2'] = team2
        context['is_team_tournament'] = team1 is not None or team2 is not None

        # Fallback: participant details (for 1v1)
        if not context['is_team_tournament']:
            context['participant1'] = self._get_participant_details(match.participant1_id)
            context['participant2'] = self._get_participant_details(match.participant2_id)

        # ── Map scores from game_scores JSON ──
        maps = []
        game_scores = match.game_scores or {}
        for m in game_scores.get('maps', []):
            maps.append({
                'map_name': m.get('map_name', ''),
                'team1_rounds': m.get('team1_rounds', 0),
                'team2_rounds': m.get('team2_rounds', 0),
                'winner_side': m.get('winner_side'),
            })
        context['maps'] = maps
        context['best_of'] = game_scores.get('best_of', match.best_of or 1)

        # ── Per-player stats (MatchPlayerStat + MatchMapPlayerStat) ──
        try:
            from apps.tournaments.models.match_player_stats import MatchPlayerStat, MatchMapPlayerStat
            player_stats_qs = MatchPlayerStat.objects.filter(
                match=match, is_deleted=False
            ).order_by('-acs')

            team1_stats = []
            team2_stats = []
            for ps in player_stats_qs:
                stat_dict = {
                    'id': ps.id,
                    'player_name': ps.player_name,
                    'display_name': ps.display_name or ps.player_name,
                    'agent': ps.agent or '',
                    'kills': ps.kills or 0,
                    'deaths': ps.deaths or 0,
                    'assists': ps.assists or 0,
                    'kd_ratio': float(ps.kd_ratio) if ps.kd_ratio else 0.0,
                    'acs': float(ps.acs) if ps.acs else 0.0,
                    'adr': float(ps.adr) if ps.adr else 0.0,
                    'hs_pct': float(ps.hs_pct) if ps.hs_pct else 0.0,
                    'first_kills': ps.first_kills or 0,
                    'first_deaths': ps.first_deaths or 0,
                    'clutches': ps.clutches or 0,
                    'is_mvp': ps.is_mvp,
                }
                if ps.team_id == match.participant1_id:
                    team1_stats.append(stat_dict)
                elif ps.team_id == match.participant2_id:
                    team2_stats.append(stat_dict)

            # If team_id matching fails, split by order
            if not team1_stats and not team2_stats and player_stats_qs.exists():
                all_stats = [s for s in player_stats_qs]
                mid = len(all_stats) // 2
                for ps in all_stats[:mid]:
                    team1_stats.append({
                        'player_name': ps.player_name,
                        'display_name': ps.display_name or ps.player_name,
                        'agent': ps.agent or '', 'kills': ps.kills or 0,
                        'deaths': ps.deaths or 0, 'assists': ps.assists or 0,
                        'kd_ratio': float(ps.kd_ratio) if ps.kd_ratio else 0.0,
                        'acs': float(ps.acs) if ps.acs else 0.0,
                        'adr': float(ps.adr) if ps.adr else 0.0,
                        'hs_pct': float(ps.hs_pct) if ps.hs_pct else 0.0,
                        'first_kills': ps.first_kills or 0, 'first_deaths': ps.first_deaths or 0,
                        'clutches': ps.clutches or 0, 'is_mvp': ps.is_mvp,
                    })
                for ps in all_stats[mid:]:
                    team2_stats.append({
                        'player_name': ps.player_name,
                        'display_name': ps.display_name or ps.player_name,
                        'agent': ps.agent or '', 'kills': ps.kills or 0,
                        'deaths': ps.deaths or 0, 'assists': ps.assists or 0,
                        'kd_ratio': float(ps.kd_ratio) if ps.kd_ratio else 0.0,
                        'acs': float(ps.acs) if ps.acs else 0.0,
                        'adr': float(ps.adr) if ps.adr else 0.0,
                        'hs_pct': float(ps.hs_pct) if ps.hs_pct else 0.0,
                        'first_kills': ps.first_kills or 0, 'first_deaths': ps.first_deaths or 0,
                        'clutches': ps.clutches or 0, 'is_mvp': ps.is_mvp,
                    })

            context['team1_stats'] = sorted(team1_stats, key=lambda x: -x['acs'])
            context['team2_stats'] = sorted(team2_stats, key=lambda x: -x['acs'])

            # Per-map stats
            map_stats_qs = MatchMapPlayerStat.objects.filter(
                match_stat__match=match, match_stat__is_deleted=False
            ).select_related('match_stat').order_by('map_number', '-kills')

            map_player_stats = {}
            for mps in map_stats_qs:
                mn = mps.map_number
                if mn not in map_player_stats:
                    map_player_stats[mn] = {
                        'map_number': mn,
                        'map_name': maps[mn - 1]['map_name'] if mn <= len(maps) else f'Map {mn}',
                        'players': [],
                    }
                map_player_stats[mn]['players'].append({
                    'player_name': mps.match_stat.display_name or mps.match_stat.player_name,
                    'team_id': mps.match_stat.team_id,
                    'kills': mps.kills or 0, 'deaths': mps.deaths or 0, 'assists': mps.assists or 0,
                    'acs': float(mps.acs) if mps.acs else 0.0,
                    'adr': float(mps.adr) if mps.adr else 0.0,
                })
            context['map_player_stats'] = sorted(map_player_stats.values(), key=lambda x: x['map_number'])
        except ImportError:
            context['team1_stats'] = []
            context['team2_stats'] = []
            context['map_player_stats'] = []

        # MVP
        mvp_stat = next((s for s in (context.get('team1_stats', []) + context.get('team2_stats', [])) if s.get('is_mvp')), None)
        context['mvp'] = mvp_stat

        # Is participant?
        if self.request.user.is_authenticated:
            context['is_participant'] = (
                match.participant1_id == self.request.user.id or
                match.participant2_id == self.request.user.id
            )
        else:
            context['is_participant'] = False
        context['show_lobby_info'] = context['is_participant'] and match.lobby_info

        # Timeline
        context['timeline'] = self._build_match_timeline(match)

        return context

    def _get_team(self, participant_id):
        """Get team details for a participant ID. Returns None if not found."""
        if not participant_id:
            return None
        try:
            from apps.teams.models import Team
            team = Team.objects.filter(id=participant_id, is_deleted=False).first()
            if team:
                return {
                    'id': team.id,
                    'name': team.name,
                    'tag': getattr(team, 'tag', ''),
                    'logo_url': team.logo.url if team.logo else None,
                }
        except (ImportError, Exception):
            pass
        return None
    
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
