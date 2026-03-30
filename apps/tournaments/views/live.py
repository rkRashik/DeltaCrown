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
from django.utils.safestring import mark_safe
import json
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
            'bracket'
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
        
        bracket_available = self._is_bracket_available(tournament)
        context['bracket_available'] = bracket_available
        
        if bracket_available:
            all_matches = list(tournament.matches.all())

            # Batch-load team logos/names for team tournaments
            teams_map = {}
            if tournament.participation_type == 'team' and all_matches:
                from apps.organizations.models import Team
                pids = set()
                for m in all_matches:
                    if m.participant1_id:
                        pids.add(m.participant1_id)
                    if m.participant2_id:
                        pids.add(m.participant2_id)
                if pids:
                    for t in Team.objects.filter(id__in=pids).only('id', 'name', 'logo', 'tag'):
                        try:
                            logo = t.logo.url if t.logo else ''
                        except Exception:
                            logo = ''
                        teams_map[t.id] = {'name': t.name, 'logo': logo, 'tag': t.tag}

            # Organize matches by round with enriched data
            matches_by_round = {}
            for match in all_matches:
                round_num = match.round_number
                if round_num not in matches_by_round:
                    matches_by_round[round_num] = {
                        'round_number': round_num,
                        'round_name': self._get_round_name(round_num, tournament),
                        'matches': []
                    }

                # Determine bracket type for double-elim
                if tournament.format == 'double_elimination' and match.round_number:
                    if 5 <= match.round_number <= 10:
                        bracket_type = 'losers'
                    elif match.round_number == 11:
                        bracket_type = 'grand_final'
                    else:
                        bracket_type = 'winners'
                else:
                    bracket_type = 'main'

                # Team info enrichment
                t1 = teams_map.get(match.participant1_id, {})
                t2 = teams_map.get(match.participant2_id, {})

                # Parse map scores
                map_scores = []
                gs = match.game_scores or {}
                gs_maps = gs.get('maps', []) if isinstance(gs, dict) else gs if isinstance(gs, list) else []
                for gm in gs_maps:
                    map_scores.append({
                        'map_name': gm.get('map', gm.get('map_name', '')),
                        'p1_score': gm.get('p1', gm.get('p1_score', gm.get('team1_rounds', 0))),
                        'p2_score': gm.get('p2', gm.get('p2_score', gm.get('team2_rounds', 0))),
                        'winner_side': gm.get('winner_side', gm.get('winner_slot', 0)),
                    })

                best_of_label = ''
                if match.best_of and match.best_of > 1:
                    best_of_label = f'BO{match.best_of}'

                match_data = {
                    'id': match.id,
                    'match_number': match.match_number,
                    'round_number': match.round_number,
                    'state': match.state,
                    'bracket_type': bracket_type,
                    'round_label': self._get_round_name(round_num, tournament),
                    'team1_name': t1.get('name') or match.participant1_name or 'TBD',
                    'team2_name': t2.get('name') or match.participant2_name or 'TBD',
                    'team1_logo': t1.get('logo', ''),
                    'team2_logo': t2.get('logo', ''),
                    'team1_tag': t1.get('tag', ''),
                    'team2_tag': t2.get('tag', ''),
                    'participant1_id': match.participant1_id,
                    'participant2_id': match.participant2_id,
                    'score1': match.participant1_score,
                    'score2': match.participant2_score,
                    'winner_id': match.winner_id,
                    'team1_is_winner': match.winner_id and match.participant1_id == match.winner_id,
                    'team2_is_winner': match.winner_id and match.participant2_id == match.winner_id,
                    'is_live': match.state == 'live',
                    'is_completed': match.state in ('completed', 'forfeit'),
                    'scheduled_time': match.scheduled_time,
                    'best_of_label': best_of_label,
                    'map_scores': mark_safe(json.dumps(map_scores)),
                }
                matches_by_round[round_num]['matches'].append(match_data)
            
            context['matches_by_round'] = sorted(
                matches_by_round.values(),
                key=lambda x: x['round_number']
            )
            context['bracket'] = tournament.bracket
            context['is_double_elim'] = tournament.format == 'double_elimination'

            # Flatten all match dicts for the template
            all_match_dicts = []
            for rd in context['matches_by_round']:
                all_match_dicts.extend(rd['matches'])
            context['all_matches'] = all_match_dicts
        else:
            context['matches_by_round'] = []
            context['bracket'] = None
            context['not_ready_reason'] = self._get_not_ready_reason(tournament)
            context['is_double_elim'] = False
            context['all_matches'] = []
        
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
                if isinstance(round_data, dict) and round_data.get('round_number') == round_number:
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
            round_label = None
            if getattr(match, 'bracket_id', None) and getattr(match, 'bracket', None):
                try:
                    round_label = match.bracket.get_round_name(match.round_number)
                except Exception:
                    round_label = None
            context['round_label'] = round_label or f'Round {match.round_number}'

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
            has_match_stat_soft_delete = any(
                f.name == 'is_deleted' for f in MatchPlayerStat._meta.get_fields()
            )

            player_stats_qs = MatchPlayerStat.objects.filter(match=match)
            if has_match_stat_soft_delete:
                player_stats_qs = player_stats_qs.filter(is_deleted=False)
            player_stats_qs = player_stats_qs.order_by('-acs')

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
            map_stat_field_names = {f.name for f in MatchMapPlayerStat._meta.get_fields()}
            uses_match_stat_relation = 'match_stat' in map_stat_field_names

            if uses_match_stat_relation:
                map_stats_qs = MatchMapPlayerStat.objects.filter(match_stat__match=match)
                if has_match_stat_soft_delete:
                    map_stats_qs = map_stats_qs.filter(match_stat__is_deleted=False)
                map_stats_qs = map_stats_qs.select_related('match_stat').order_by('map_number', '-kills')
            else:
                map_stats_qs = MatchMapPlayerStat.objects.filter(match=match).select_related('player').order_by('map_number', '-kills')

            map_player_stats = {}
            for mps in map_stats_qs:
                mn = mps.map_number
                if mn not in map_player_stats:
                    map_player_stats[mn] = {
                        'map_number': mn,
                        'map_name': maps[mn - 1]['map_name'] if mn <= len(maps) else f'Map {mn}',
                        'players': [],
                    }

                if uses_match_stat_relation:
                    player_name = mps.match_stat.display_name or mps.match_stat.player_name
                    team_id = mps.match_stat.team_id
                else:
                    player_name = mps.player.username if getattr(mps, 'player', None) else ''
                    team_id = getattr(mps, 'team_id', None)

                map_player_stats[mn]['players'].append({
                    'player_name': player_name,
                    'team_id': team_id,
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
            is_part = (
                match.participant1_id == self.request.user.id or
                match.participant2_id == self.request.user.id
            )
            if not is_part and tournament.participant_type == 'team':
                from apps.organizations.models import TeamMembership
                active_teams = set(TeamMembership.objects.filter(user=self.request.user, status=TeamMembership.Status.ACTIVE).values_list('team_id', flat=True))
                if match.participant1_id in active_teams or match.participant2_id in active_teams:
                    is_part = True
            context['is_participant'] = is_part
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
            from apps.organizations.models import Team
            team = Team.objects.filter(id=participant_id).first()
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
