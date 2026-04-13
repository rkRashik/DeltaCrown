"""
Sprint 4: Tournament Leaderboard & Standings View

FE-T-010: Tournament Leaderboard Page
"""

from django.views.generic import DetailView
from django.db.models import Q, Count, Case, When, IntegerField
from django.shortcuts import get_object_or_404

from apps.tournaments.models import Tournament, Match, Registration
from apps.tournaments.models.group import GroupStanding


class TournamentLeaderboardView(DetailView):
    """
    FE-T-010: Tournament Leaderboard Page
    
    Displays real-time tournament leaderboard with participant standings.
    Supports both solo and team tournaments.
    
    URL: /tournaments/<slug>/leaderboard/
    """
    model = Tournament
    template_name = 'tournaments/public/leaderboard/index.html'
    context_object_name = 'tournament'
    
    def get_queryset(self):
        return Tournament.objects.filter(
            is_deleted=False
        ).select_related('game', 'organizer', 'bracket')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Effective status for template consistency
        effective_status = getattr(tournament, 'get_effective_status', lambda: tournament.status)()
        context['effective_status'] = effective_status
        context['current_stage'] = getattr(tournament, 'get_current_stage', lambda: None)()
        
        standings = self._calculate_standings(tournament)
        context['standings'] = standings
        context['standings_source'] = getattr(self, '_standings_source', 'matches')
        
        if self.request.user.is_authenticated:
            user_standing = self._find_user_standing(standings, self.request.user)
            context['user_rank'] = user_standing['rank'] if user_standing else None
            context['user_standing'] = user_standing
        else:
            context['user_rank'] = None
            context['user_standing'] = None
        
        return context
    
    def _calculate_standings(self, tournament):
        registrations = list(tournament.registrations.select_related(
            'user', 'user__profile'
        ).filter(
            status=Registration.CONFIRMED,
            is_deleted=False
        ).order_by('id'))
        
        has_completed_matches = Match.objects.filter(
            tournament=tournament,
            state__in=[Match.COMPLETED, 'forfeit'],
            is_deleted=False
        ).exists()
        
        if not has_completed_matches:
            # Try GroupStanding data (group_playoff / round_robin formats)
            group_standings = self._build_from_group_standings(tournament)
            if group_standings:
                self._standings_source = 'groups'
                return group_standings
            return []
        
        completed_matches = list(Match.objects.filter(
            tournament=tournament,
            state=Match.COMPLETED,
            is_deleted=False
        ).values('participant1_id', 'participant2_id', 'winner_id', 'loser_id',
                 'participant1_score', 'participant2_score', 'game_scores'))

        # Batch-load teams for team tournaments
        is_team = tournament.participation_type == 'team'
        teams_map = {}
        if is_team:
            team_ids = [r.team_id for r in registrations if r.team_id]
            if team_ids:
                from apps.organizations.models import Team
                for t in Team.objects.filter(id__in=team_ids).only('id', 'name', 'logo', 'tag', 'region'):
                    try:
                        logo = t.logo.url if t.logo else ''
                    except Exception:
                        logo = ''
                    teams_map[t.id] = {
                        'name': t.name, 'logo': logo,
                        'tag': t.tag, 'region': t.region or '',
                    }

        standings = []
        for registration in registrations:
            if is_team and registration.team_id:
                team_info = teams_map.get(registration.team_id, {})
                participant_name = team_info.get('name', f'Team {registration.team_id}')
                participant_id = registration.team_id
                logo = team_info.get('logo', '')
                tag = team_info.get('tag', '')
                region = team_info.get('region', '')
            elif registration.user:
                profile = getattr(registration.user, 'profile', None)
                participant_name = (profile.display_name if profile and profile.display_name
                                    else registration.user.username)
                participant_id = registration.user_id
                try:
                    logo = profile.avatar.url if profile and profile.avatar else ''
                except Exception:
                    logo = ''
                tag = ''
                region = getattr(profile, 'region', '') if profile else ''
            else:
                continue
            
            games_played = 0
            wins = 0
            draws = 0
            losses = 0
            goals_for = 0
            goals_against = 0
            maps_won = 0
            maps_lost = 0
            
            for match in completed_matches:
                if match['participant1_id'] == participant_id or match['participant2_id'] == participant_id:
                    games_played += 1
                    is_p1 = match['participant1_id'] == participant_id

                    # Goals for/against from match scores
                    p1s = match.get('participant1_score') or 0
                    p2s = match.get('participant2_score') or 0
                    if is_p1:
                        goals_for += p1s
                        goals_against += p2s
                    else:
                        goals_for += p2s
                        goals_against += p1s

                    if match['winner_id'] == participant_id:
                        wins += 1
                    elif match['loser_id'] == participant_id:
                        losses += 1
                    else:
                        # Draw: winner_id is None and scores equal
                        draws += 1

                    # Map differential
                    gs = match.get('game_scores') or {}
                    gs_maps = gs.get('maps', []) if isinstance(gs, dict) else gs if isinstance(gs, list) else []
                    for gm in gs_maps:
                        ws = gm.get('winner_side', gm.get('winner_slot', 0))
                        if (ws == 1 and is_p1) or (ws == 2 and not is_p1):
                            maps_won += 1
                        else:
                            maps_lost += 1
            
            points = wins * 3 + draws * 1
            goal_diff = goals_for - goals_against
            win_rate = round(wins / games_played * 100) if games_played > 0 else 0
            
            is_current_user = False
            if self.request.user.is_authenticated:
                if registration.user_id:
                    is_current_user = (self.request.user.id == registration.user_id)
            
            standings.append({
                'rank': 0,
                'name': participant_name,
                'logo': logo,
                'tag': tag,
                'region': region,
                'participant': registration.user if registration.user_id else None,
                'registration': registration,
                'games_played': games_played,
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'goals_for': goals_for,
                'goals_against': goals_against,
                'goal_diff': goal_diff,
                'points': points,
                'maps_won': maps_won,
                'maps_lost': maps_lost,
                'map_diff': maps_won - maps_lost,
                'win_rate': win_rate,
                'is_current_user': is_current_user,
                'registration_id': registration.id,
                'is_team': is_team,
            })
        
        standings.sort(
            key=lambda x: (-x['points'], -x['goal_diff'], -x['goals_for'], -x['wins'], x['games_played'], x['registration_id'])
        )
        
        for idx, standing in enumerate(standings, start=1):
            standing['rank'] = idx
        
        return standings
    
    def _build_from_group_standings(self, tournament):
        """Build leaderboard from GroupStanding records (group_playoff / round_robin)."""
        gs_qs = GroupStanding.objects.filter(
            group__tournament=tournament,
            is_deleted=False,
        ).select_related('group', 'user', 'user__profile').order_by(
            '-points', '-goal_difference', '-goals_for', 'rank'
        )
        if not gs_qs.exists():
            return []

        is_team = tournament.participation_type == 'team'
        teams_map = {}
        if is_team:
            team_ids = [gs.team_id for gs in gs_qs if gs.team_id]
            if team_ids:
                from apps.organizations.models import Team
                for t in Team.objects.filter(id__in=team_ids).only('id', 'name', 'logo', 'tag', 'region'):
                    try:
                        logo = t.logo.url if t.logo else ''
                    except Exception:
                        logo = ''
                    teams_map[t.id] = {
                        'name': t.name, 'logo': logo,
                        'tag': t.tag, 'region': t.region or '',
                    }

        standings = []
        for gs in gs_qs:
            if is_team and gs.team_id:
                team_info = teams_map.get(gs.team_id, {})
                name = team_info.get('name', f'Team {gs.team_id}')
                logo = team_info.get('logo', '')
                tag = team_info.get('tag', '')
                region = team_info.get('region', '')
            elif gs.user:
                profile = getattr(gs.user, 'profile', None)
                name = (profile.display_name if profile and profile.display_name
                        else gs.user.username)
                try:
                    logo = profile.avatar.url if profile and profile.avatar else ''
                except Exception:
                    logo = ''
                tag = ''
                region = getattr(profile, 'region', '') if profile else ''
            else:
                continue

            is_current_user = False
            if self.request.user.is_authenticated and gs.user_id:
                is_current_user = (self.request.user.id == gs.user_id)

            standings.append({
                'rank': 0,
                'name': name,
                'logo': logo,
                'tag': tag,
                'region': region,
                'games_played': gs.matches_played,
                'wins': gs.matches_won,
                'draws': gs.matches_drawn,
                'losses': gs.matches_lost,
                'goals_for': gs.goals_for,
                'goals_against': gs.goals_against,
                'goal_diff': gs.goal_difference,
                'points': int(gs.points),
                'is_current_user': is_current_user,
                'is_team': is_team,
                'registration_id': 0,
                'is_advancing': gs.is_advancing,
                'is_eliminated': gs.is_eliminated,
                'group_name': gs.group.name if gs.group else '',
            })

        # Already sorted by queryset order; assign ranks per group
        # Sort by group_name first, then by points/GD within each group
        standings.sort(key=lambda s: (s['group_name'], -s['points'], -s['goal_diff'], -s['goals_for']))
        current_group = None
        rank_in_group = 0
        for s in standings:
            if s['group_name'] != current_group:
                current_group = s['group_name']
                rank_in_group = 1
            else:
                rank_in_group += 1
            s['rank'] = rank_in_group

        return standings

    def _find_user_standing(self, standings, user):
        for standing in standings:
            if standing['is_current_user']:
                return standing
        return None
