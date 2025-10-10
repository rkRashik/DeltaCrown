"""
Analytics Calculator Service (Task 6 - Phase 2)

Provides calculation and aggregation services for team and player analytics.
Handles win rate calculations, points progression, and game-specific stat aggregations.
"""
from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.db.models import Avg, Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta

from apps.teams.models import (
    TeamAnalytics,
    PlayerStats,
    MatchRecord,
    MatchParticipation,
    Team
)
from apps.teams.analytics_schemas import get_game_schema, GAME_STATS_SCHEMAS


class AnalyticsCalculator:
    """
    Core analytics calculation service.
    Handles all calculations for team and player statistics.
    """
    
    @staticmethod
    def calculate_win_rate(matches_won: int, total_matches: int) -> Decimal:
        """
        Calculate win rate percentage.
        
        Args:
            matches_won: Number of matches won
            total_matches: Total number of matches played
        
        Returns:
            Win rate as Decimal (0-100)
        """
        if total_matches == 0:
            return Decimal('0.00')
        return Decimal((matches_won / total_matches) * 100).quantize(Decimal('0.01'))
    
    @staticmethod
    def calculate_kda_ratio(kills: int, deaths: int, assists: int) -> Decimal:
        """
        Calculate KDA (Kill/Death/Assist) ratio.
        Formula: (Kills + Assists) / Deaths
        
        Args:
            kills: Number of kills
            deaths: Number of deaths
            assists: Number of assists
        
        Returns:
            KDA ratio as Decimal
        """
        if deaths == 0:
            return Decimal(kills + assists)
        return Decimal((kills + assists) / deaths).quantize(Decimal('0.01'))
    
    @staticmethod
    def update_team_analytics(team_id: int, game: str, match_result: str, 
                            points_change: int = 0,
                            game_specific_stats: Optional[Dict] = None) -> TeamAnalytics:
        """
        Update team analytics after a match.
        
        Args:
            team_id: Team ID
            game: Game identifier
            match_result: 'win', 'loss', or 'draw'
            points_change: Points earned/lost
            game_specific_stats: Game-specific statistics to merge
        
        Returns:
            Updated TeamAnalytics instance
        """
        team_analytics, created = TeamAnalytics.objects.get_or_create(
            team_id=team_id,
            game=game,
            defaults={
                'game_specific_stats': get_game_schema(game, 'team') if game.lower() in GAME_STATS_SCHEMAS else {}
            }
        )
        
        # Use the model's built-in method
        team_analytics.add_match_result(match_result, points_change)
        
        # Merge game-specific stats
        if game_specific_stats:
            AnalyticsCalculator.merge_game_specific_stats(
                team_analytics.game_specific_stats,
                game_specific_stats
            )
            team_analytics.save(update_fields=['game_specific_stats'])
        
        return team_analytics
    
    @staticmethod
    def merge_game_specific_stats(current_stats: Dict, new_stats: Dict) -> None:
        """
        Merge new game-specific statistics into existing stats.
        Aggregates numeric values, keeps most recent for strings.
        
        Args:
            current_stats: Current statistics dictionary (modified in-place)
            new_stats: New statistics to merge in
        """
        for key, value in new_stats.items():
            if key not in current_stats:
                current_stats[key] = value
            elif isinstance(value, (int, float)):
                current_stats[key] = current_stats.get(key, 0) + value
            elif isinstance(value, dict):
                if not isinstance(current_stats.get(key), dict):
                    current_stats[key] = {}
                AnalyticsCalculator.merge_game_specific_stats(current_stats[key], value)
            else:
                # For strings and other types, keep the new value
                current_stats[key] = value
    
    @staticmethod
    def calculate_points_progression(team_id: int, game: str, 
                                    days: int = 30) -> List[Dict[str, Any]]:
        """
        Calculate points progression over time.
        
        Args:
            team_id: Team ID
            game: Game identifier
            days: Number of days to look back
        
        Returns:
            List of {date, points, change} dictionaries
        """
        try:
            team_analytics = TeamAnalytics.objects.get(team_id=team_id, game=game)
            points_history = team_analytics.points_history or []
            
            # Filter to last N days
            cutoff_date = timezone.now() - timedelta(days=days)
            recent_history = [
                entry for entry in points_history
                if datetime.fromisoformat(entry['date'].replace('Z', '+00:00')) >= cutoff_date
            ]
            
            return recent_history
        except TeamAnalytics.DoesNotExist:
            return []
    
    @staticmethod
    def update_player_stats(player_id: int, team_id: int, game: str,
                          match_participation: MatchParticipation) -> PlayerStats:
        """
        Update player statistics after a match.
        
        Args:
            player_id: Player (UserProfile) ID
            team_id: Team ID
            game: Game identifier
            match_participation: MatchParticipation instance with performance data
        
        Returns:
            Updated PlayerStats instance
        """
        player_stats, created = PlayerStats.objects.get_or_create(
            player_id=player_id,
            team_id=team_id,
            game=game,
            defaults={
                'game_specific_stats': get_game_schema(game, 'player') if game.lower() in GAME_STATS_SCHEMAS else {}
            }
        )
        
        # Update basic stats
        player_stats.matches_played += 1
        if match_participation.match.result == 'win':
            player_stats.matches_won += 1
        
        if match_participation.was_mvp:
            player_stats.mvp_count += 1
        
        # Update contribution score (weighted average)
        if player_stats.matches_played > 1:
            player_stats.contribution_score = (
                (player_stats.contribution_score * (player_stats.matches_played - 1) +
                 match_participation.performance_score) / player_stats.matches_played
            )
        else:
            player_stats.contribution_score = match_participation.performance_score
        
        # Merge game-specific performance stats
        if match_participation.game_specific_performance:
            AnalyticsCalculator.merge_game_specific_stats(
                player_stats.game_specific_stats,
                match_participation.game_specific_performance
            )
        
        player_stats.last_active = timezone.now()
        player_stats.save()
        
        return player_stats
    
    @staticmethod
    def calculate_team_performance_summary(team_id: int, game: str) -> Dict[str, Any]:
        """
        Calculate comprehensive team performance summary.
        
        Args:
            team_id: Team ID
            game: Game identifier
        
        Returns:
            Dictionary with performance metrics
        """
        try:
            team_analytics = TeamAnalytics.objects.get(team_id=team_id, game=game)
        except TeamAnalytics.DoesNotExist:
            return {
                'error': 'No analytics data found',
                'team_id': team_id,
                'game': game
            }
        
        # Get recent matches
        recent_matches = MatchRecord.objects.filter(
            team_id=team_id,
            game=game
        ).order_by('-match_date')[:10]
        
        # Calculate recent form (last 5 matches)
        recent_form = []
        for match in recent_matches[:5]:
            recent_form.append({
                'result': match.result,
                'opponent': match.opponent_name,
                'score': match.score,
                'date': match.match_date
            })
        
        # Get player statistics
        player_stats = PlayerStats.objects.filter(
            team_id=team_id,
            game=game,
            is_active=True
        ).order_by('-contribution_score')[:5]
        
        top_performers = [
            {
                'player': ps.player.user.username,
                'contribution_score': float(ps.contribution_score),
                'mvp_count': ps.mvp_count,
                'matches_played': ps.matches_played,
                'attendance_rate': float(ps.attendance_rate)
            }
            for ps in player_stats
        ]
        
        return {
            'team_id': team_id,
            'game': game,
            'total_matches': team_analytics.total_matches,
            'win_rate': float(team_analytics.win_rate),
            'total_points': team_analytics.total_points,
            'current_streak': team_analytics.current_streak,
            'best_win_streak': team_analytics.best_win_streak,
            'recent_form': recent_form,
            'top_performers': top_performers,
            'last_match_date': team_analytics.last_match_date,
            'tournaments_participated': team_analytics.tournaments_participated,
            'tournaments_won': team_analytics.tournaments_won,
        }
    
    @staticmethod
    def calculate_player_contribution_score(match_participation: MatchParticipation) -> Decimal:
        """
        Calculate player contribution score for a match based on performance.
        This is a simplified algorithm - can be enhanced with game-specific weighting.
        
        Args:
            match_participation: MatchParticipation instance
        
        Returns:
            Contribution score as Decimal (0-100)
        """
        score = Decimal('50.00')  # Base score
        
        # Bonus for MVP
        if match_participation.was_mvp:
            score += Decimal('25.00')
        
        # Bonus for starter
        if match_participation.was_starter:
            score += Decimal('10.00')
        
        # Bonus for winning
        if match_participation.match.result == 'win':
            score += Decimal('15.00')
        else:
            score -= Decimal('10.00')
        
        # Game-specific adjustments
        game_stats = match_participation.game_specific_performance
        if game_stats:
            # KDA-based games (Valorant, CS2, MLBB, etc.)
            if 'kills' in game_stats and 'deaths' in game_stats:
                kda = AnalyticsCalculator.calculate_kda_ratio(
                    game_stats.get('kills', 0),
                    game_stats.get('deaths', 1),
                    game_stats.get('assists', 0)
                )
                if kda >= 2.0:
                    score += Decimal('10.00')
                elif kda >= 1.0:
                    score += Decimal('5.00')
                elif kda < 0.5:
                    score -= Decimal('5.00')
            
            # eFootball/FC26 specific
            if 'goals' in game_stats:
                score += Decimal(game_stats['goals'] * 3)
            if 'assists' in game_stats and 'kills' not in game_stats:  # Avoid double counting
                score += Decimal(game_stats['assists'] * 2)
        
        # Clamp between 0 and 100
        score = max(Decimal('0.00'), min(Decimal('100.00'), score))
        
        return score.quantize(Decimal('0.01'))
    
    @staticmethod
    def get_team_leaderboard(game: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get team leaderboard for a specific game.
        
        Args:
            game: Game identifier
            limit: Maximum number of teams to return
        
        Returns:
            List of team dictionaries sorted by total points
        """
        top_teams = TeamAnalytics.objects.filter(
            game=game
        ).select_related('team').order_by('-total_points')[:limit]
        
        leaderboard = []
        for rank, team_analytics in enumerate(top_teams, start=1):
            leaderboard.append({
                'rank': rank,
                'team_name': team_analytics.team.name,
                'team_id': team_analytics.team_id,
                'total_points': team_analytics.total_points,
                'win_rate': float(team_analytics.win_rate),
                'total_matches': team_analytics.total_matches,
                'current_streak': team_analytics.current_streak,
                'tournaments_won': team_analytics.tournaments_won,
            })
        
        return leaderboard
    
    @staticmethod
    def get_player_leaderboard(game: str, limit: int = 10, 
                              team_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get player leaderboard for a specific game.
        
        Args:
            game: Game identifier
            limit: Maximum number of players to return
            team_id: Optional team ID to filter by
        
        Returns:
            List of player dictionaries sorted by contribution score
        """
        queryset = PlayerStats.objects.filter(
            game=game,
            is_active=True
        ).select_related('player__user', 'team')
        
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        
        top_players = queryset.order_by('-contribution_score')[:limit]
        
        leaderboard = []
        for rank, player_stats in enumerate(top_players, start=1):
            leaderboard.append({
                'rank': rank,
                'player_name': player_stats.player.user.username,
                'player_id': player_stats.player_id,
                'team_name': player_stats.team.name,
                'team_id': player_stats.team_id,
                'contribution_score': float(player_stats.contribution_score),
                'mvp_count': player_stats.mvp_count,
                'matches_played': player_stats.matches_played,
                'attendance_rate': float(player_stats.attendance_rate),
            })
        
        return leaderboard
    
    @staticmethod
    def calculate_attendance_rates(team_id: int, game: str) -> None:
        """
        Recalculate attendance rates for all players in a team for a specific game.
        
        Args:
            team_id: Team ID
            game: Game identifier
        """
        # Get total matches for the team
        team_analytics = TeamAnalytics.objects.filter(team_id=team_id, game=game).first()
        if not team_analytics:
            return
        
        total_team_matches = team_analytics.total_matches
        
        # Update all player attendance rates
        player_stats = PlayerStats.objects.filter(team_id=team_id, game=game)
        for ps in player_stats:
            ps.update_attendance_rate(total_team_matches)
    
    @staticmethod
    def get_match_history(team_id: int, game: Optional[str] = None, 
                         limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get match history for a team.
        
        Args:
            team_id: Team ID
            game: Optional game filter
            limit: Maximum number of matches to return
        
        Returns:
            List of match dictionaries
        """
        queryset = MatchRecord.objects.filter(team_id=team_id)
        
        if game:
            queryset = queryset.filter(game=game)
        
        matches = queryset.order_by('-match_date')[:limit]
        
        history = []
        for match in matches:
            # Get participants
            participants = MatchParticipation.objects.filter(
                match=match
            ).select_related('player__user')
            
            participant_data = [
                {
                    'player': p.player.user.username,
                    'role': p.role_played,
                    'was_mvp': p.was_mvp,
                    'performance_score': float(p.performance_score)
                }
                for p in participants
            ]
            
            history.append({
                'match_id': match.id,
                'date': match.match_date,
                'game': match.game,
                'opponent': match.opponent_name,
                'result': match.result,
                'score': match.score,
                'points_earned': match.points_earned,
                'tournament': match.tournament.name if match.tournament else None,
                'participants': participant_data,
            })
        
        return history


class AnalyticsAggregator:
    """
    Service for aggregating analytics data across multiple dimensions.
    """
    
    @staticmethod
    def aggregate_team_stats_by_period(team_id: int, game: str, 
                                      period: str = 'month') -> Dict[str, Any]:
        """
        Aggregate team statistics by time period.
        
        Args:
            team_id: Team ID
            game: Game identifier
            period: 'week', 'month', or 'year'
        
        Returns:
            Aggregated statistics dictionary
        """
        # Calculate date range
        now = timezone.now()
        if period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=30)  # Default to month
        
        # Get matches in period
        matches = MatchRecord.objects.filter(
            team_id=team_id,
            game=game,
            match_date__gte=start_date
        )
        
        total_matches = matches.count()
        wins = matches.filter(result='win').count()
        losses = matches.filter(result='loss').count()
        draws = matches.filter(result='draw').count()
        
        total_points = matches.aggregate(Sum('points_earned'))['points_earned__sum'] or 0
        
        return {
            'period': period,
            'start_date': start_date,
            'end_date': now,
            'total_matches': total_matches,
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'win_rate': float(AnalyticsCalculator.calculate_win_rate(wins, total_matches)),
            'total_points': total_points,
        }
    
    @staticmethod
    def aggregate_player_stats_by_role(team_id: int, game: str) -> Dict[str, Any]:
        """
        Aggregate player statistics grouped by role.
        
        Args:
            team_id: Team ID
            game: Game identifier
        
        Returns:
            Dictionary mapping roles to aggregated stats
        """
        participations = MatchParticipation.objects.filter(
            match__team_id=team_id,
            match__game=game
        ).select_related('player__user', 'match')
        
        role_stats = {}
        
        for participation in participations:
            role = participation.role_played
            if role not in role_stats:
                role_stats[role] = {
                    'count': 0,
                    'total_performance': Decimal('0.00'),
                    'mvp_count': 0,
                    'players': set()
                }
            
            role_stats[role]['count'] += 1
            role_stats[role]['total_performance'] += participation.performance_score
            if participation.was_mvp:
                role_stats[role]['mvp_count'] += 1
            role_stats[role]['players'].add(participation.player.user.username)
        
        # Calculate averages and convert to serializable format
        result = {}
        for role, stats in role_stats.items():
            result[role] = {
                'matches_played': stats['count'],
                'average_performance': float(stats['total_performance'] / stats['count']),
                'mvp_count': stats['mvp_count'],
                'unique_players': len(stats['players']),
                'players': list(stats['players'])
            }
        
        return result
    
    @staticmethod
    def get_comparative_stats(team_id: int, game: str, 
                             compare_team_id: int) -> Dict[str, Any]:
        """
        Get comparative statistics between two teams.
        
        Args:
            team_id: First team ID
            game: Game identifier
            compare_team_id: Second team ID to compare against
        
        Returns:
            Comparative statistics dictionary
        """
        try:
            team1_analytics = TeamAnalytics.objects.get(team_id=team_id, game=game)
            team2_analytics = TeamAnalytics.objects.get(team_id=compare_team_id, game=game)
        except TeamAnalytics.DoesNotExist:
            return {'error': 'One or both teams have no analytics data'}
        
        return {
            'team1': {
                'team_id': team_id,
                'team_name': team1_analytics.team.name,
                'win_rate': float(team1_analytics.win_rate),
                'total_points': team1_analytics.total_points,
                'total_matches': team1_analytics.total_matches,
            },
            'team2': {
                'team_id': compare_team_id,
                'team_name': team2_analytics.team.name,
                'win_rate': float(team2_analytics.win_rate),
                'total_points': team2_analytics.total_points,
                'total_matches': team2_analytics.total_matches,
            },
            'comparison': {
                'win_rate_diff': float(team1_analytics.win_rate - team2_analytics.win_rate),
                'points_diff': team1_analytics.total_points - team2_analytics.total_points,
                'matches_diff': team1_analytics.total_matches - team2_analytics.total_matches,
            }
        }
