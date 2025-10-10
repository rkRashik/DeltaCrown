"""
CSV Export Service (Task 6 - Phase 2)

Provides CSV export functionality for analytics data.
Supports team statistics, player statistics, and match records.
"""
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
from django.http import HttpResponse
from django.db.models import QuerySet

from apps.teams.models import TeamAnalytics, PlayerStats, MatchRecord


class CSVExportService:
    """
    Service for exporting analytics data to CSV format.
    """
    
    @staticmethod
    def export_team_analytics(queryset: QuerySet[TeamAnalytics], 
                             filename: str = 'team_analytics.csv') -> HttpResponse:
        """
        Export team analytics to CSV.
        
        Args:
            queryset: QuerySet of TeamAnalytics objects
            filename: Output filename
        
        Returns:
            HttpResponse with CSV data
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Team Name',
            'Game',
            'Total Matches',
            'Wins',
            'Losses',
            'Draws',
            'Win Rate %',
            'Total Points',
            'Current Streak',
            'Best Win Streak',
            'Tournaments Participated',
            'Tournaments Won',
            'Last Match Date',
            'Updated At'
        ])
        
        # Write data rows
        for analytics in queryset.select_related('team'):
            writer.writerow([
                analytics.team.name,
                analytics.game,
                analytics.total_matches,
                analytics.matches_won,
                analytics.matches_lost,
                analytics.matches_drawn,
                f"{analytics.win_rate:.2f}",
                analytics.total_points,
                analytics.current_streak,
                analytics.best_win_streak,
                analytics.tournaments_participated,
                analytics.tournaments_won,
                analytics.last_match_date.strftime('%Y-%m-%d %H:%M:%S') if analytics.last_match_date else 'N/A',
                analytics.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    
    @staticmethod
    def export_player_stats(queryset: QuerySet[PlayerStats],
                          filename: str = 'player_stats.csv') -> HttpResponse:
        """
        Export player statistics to CSV.
        
        Args:
            queryset: QuerySet of PlayerStats objects
            filename: Output filename
        
        Returns:
            HttpResponse with CSV data
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Player',
            'Team',
            'Game',
            'Tournaments Played',
            'Matches Played',
            'Matches Won',
            'Attendance Rate %',
            'MVP Count',
            'Contribution Score',
            'Individual Rating',
            'Is Active',
            'Last Active',
            'Created At'
        ])
        
        # Write data rows
        for stats in queryset.select_related('player__user', 'team'):
            writer.writerow([
                stats.player.user.username,
                stats.team.name,
                stats.game,
                stats.tournaments_played,
                stats.matches_played,
                stats.matches_won,
                f"{stats.attendance_rate:.2f}",
                stats.mvp_count,
                f"{stats.contribution_score:.2f}",
                f"{stats.individual_rating:.2f}",
                'Yes' if stats.is_active else 'No',
                stats.last_active.strftime('%Y-%m-%d %H:%M:%S') if stats.last_active else 'Never',
                stats.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    
    @staticmethod
    def export_match_records(queryset: QuerySet[MatchRecord],
                           filename: str = 'match_records.csv') -> HttpResponse:
        """
        Export match records to CSV.
        
        Args:
            queryset: QuerySet of MatchRecord objects
            filename: Output filename
        
        Returns:
            HttpResponse with CSV data
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Match Date',
            'Team',
            'Game',
            'Opponent',
            'Result',
            'Score',
            'Team Score',
            'Opponent Score',
            'Points Earned',
            'Tournament',
            'Map',
            'Duration (minutes)',
            'Replay URL'
        ])
        
        # Write data rows
        for match in queryset.select_related('team', 'tournament'):
            writer.writerow([
                match.match_date.strftime('%Y-%m-%d %H:%M:%S'),
                match.team.name,
                match.game,
                match.opponent_name,
                match.get_result_display(),
                match.score,
                match.team_score,
                match.opponent_score,
                match.points_earned,
                match.tournament.name if match.tournament else 'N/A',
                match.map_played or 'N/A',
                match.duration_minutes if match.duration_minutes else 'N/A',
                match.replay_url or 'N/A'
            ])
        
        return response
    
    @staticmethod
    def export_team_summary_report(team_id: int, game: str,
                                  filename: str = 'team_summary_report.csv') -> HttpResponse:
        """
        Export comprehensive team summary report.
        
        Args:
            team_id: Team ID
            game: Game identifier
            filename: Output filename
        
        Returns:
            HttpResponse with CSV data
        """
        from apps.teams.services.analytics_calculator import AnalyticsCalculator
        
        summary = AnalyticsCalculator.calculate_team_performance_summary(team_id, game)
        
        if 'error' in summary:
            # Return error CSV
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            writer = csv.writer(response)
            writer.writerow(['Error', summary['error']])
            return response
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Team Summary Section
        writer.writerow(['TEAM SUMMARY REPORT'])
        writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        writer.writerow(['Team ID', summary['team_id']])
        writer.writerow(['Game', summary['game']])
        writer.writerow(['Total Matches', summary['total_matches']])
        writer.writerow(['Win Rate %', f"{summary['win_rate']:.2f}"])
        writer.writerow(['Total Points', summary['total_points']])
        writer.writerow(['Current Streak', summary['current_streak']])
        writer.writerow(['Best Win Streak', summary['best_win_streak']])
        writer.writerow(['Tournaments Participated', summary['tournaments_participated']])
        writer.writerow(['Tournaments Won', summary['tournaments_won']])
        writer.writerow([])
        
        # Recent Form Section
        writer.writerow(['RECENT FORM (Last 5 Matches)'])
        writer.writerow(['Date', 'Opponent', 'Result', 'Score'])
        for match in summary['recent_form']:
            writer.writerow([
                match['date'].strftime('%Y-%m-%d'),
                match['opponent'],
                match['result'].upper(),
                match['score']
            ])
        writer.writerow([])
        
        # Top Performers Section
        writer.writerow(['TOP PERFORMERS'])
        writer.writerow(['Player', 'Contribution Score', 'MVP Count', 'Matches Played', 'Attendance %'])
        for performer in summary['top_performers']:
            writer.writerow([
                performer['player'],
                f"{performer['contribution_score']:.2f}",
                performer['mvp_count'],
                performer['matches_played'],
                f"{performer['attendance_rate']:.2f}"
            ])
        
        return response
    
    @staticmethod
    def export_leaderboard(game: str, leaderboard_type: str = 'team',
                          limit: int = 50,
                          filename: Optional[str] = None) -> HttpResponse:
        """
        Export leaderboard to CSV.
        
        Args:
            game: Game identifier
            leaderboard_type: 'team' or 'player'
            limit: Number of entries to export
            filename: Optional custom filename
        
        Returns:
            HttpResponse with CSV data
        """
        from apps.teams.services.analytics_calculator import AnalyticsCalculator
        
        if not filename:
            filename = f'{game}_{leaderboard_type}_leaderboard.csv'
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        if leaderboard_type == 'team':
            leaderboard = AnalyticsCalculator.get_team_leaderboard(game, limit)
            
            writer.writerow(['TEAM LEADERBOARD'])
            writer.writerow(['Game', game])
            writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            writer.writerow(['Rank', 'Team Name', 'Total Points', 'Win Rate %', 
                           'Total Matches', 'Current Streak', 'Tournaments Won'])
            
            for entry in leaderboard:
                writer.writerow([
                    entry['rank'],
                    entry['team_name'],
                    entry['total_points'],
                    f"{entry['win_rate']:.2f}",
                    entry['total_matches'],
                    entry['current_streak'],
                    entry['tournaments_won']
                ])
        
        elif leaderboard_type == 'player':
            leaderboard = AnalyticsCalculator.get_player_leaderboard(game, limit)
            
            writer.writerow(['PLAYER LEADERBOARD'])
            writer.writerow(['Game', game])
            writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            writer.writerow(['Rank', 'Player Name', 'Team', 'Contribution Score', 
                           'MVP Count', 'Matches Played', 'Attendance %'])
            
            for entry in leaderboard:
                writer.writerow([
                    entry['rank'],
                    entry['player_name'],
                    entry['team_name'],
                    f"{entry['contribution_score']:.2f}",
                    entry['mvp_count'],
                    entry['matches_played'],
                    f"{entry['attendance_rate']:.2f}"
                ])
        
        return response
    
    @staticmethod
    def export_match_history_with_participants(team_id: int, game: Optional[str] = None,
                                              limit: int = 50,
                                              filename: str = 'match_history_detailed.csv') -> HttpResponse:
        """
        Export detailed match history including participant performance.
        
        Args:
            team_id: Team ID
            game: Optional game filter
            limit: Number of matches to export
            filename: Output filename
        
        Returns:
            HttpResponse with CSV data
        """
        from apps.teams.services.analytics_calculator import AnalyticsCalculator
        
        history = AnalyticsCalculator.get_match_history(team_id, game, limit)
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Match ID',
            'Date',
            'Game',
            'Opponent',
            'Result',
            'Score',
            'Points Earned',
            'Tournament',
            'Player',
            'Role',
            'MVP',
            'Performance Score'
        ])
        
        # Write data rows (one row per participant)
        for match in history:
            for participant in match['participants']:
                writer.writerow([
                    match['match_id'],
                    match['date'].strftime('%Y-%m-%d %H:%M:%S'),
                    match['game'],
                    match['opponent'],
                    match['result'].upper(),
                    match['score'],
                    match['points_earned'],
                    match['tournament'] or 'N/A',
                    participant['player'],
                    participant['role'],
                    'Yes' if participant['was_mvp'] else 'No',
                    f"{participant['performance_score']:.2f}"
                ])
        
        return response
    
    @staticmethod
    def export_to_string_buffer(data: List[Dict[str, Any]], 
                               headers: List[str]) -> str:
        """
        Export data to CSV string buffer (for testing or API responses).
        
        Args:
            data: List of dictionaries containing row data
            headers: List of header column names
        
        Returns:
            CSV formatted string
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(headers)
        
        # Write data rows
        for row_dict in data:
            writer.writerow([row_dict.get(header, '') for header in headers])
        
        csv_string = output.getvalue()
        output.close()
        
        return csv_string
