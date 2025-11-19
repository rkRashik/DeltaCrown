"""
Tournament Analytics Service

Provides insights and statistics for tournaments.
"""

from typing import Dict, List, Optional
from django.db.models import Count, Avg, Q, F, Sum, Max, Min
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament, Match, Registration


class TournamentAnalytics:
    """Analytics service for tournament insights"""
    
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
    
    def get_overview_stats(self) -> Dict:
        """Get high-level tournament statistics"""
        registrations = Registration.objects.filter(
            tournament=self.tournament,
            is_deleted=False
        )
        
        matches = Match.objects.filter(tournament=self.tournament)
        
        return {
            'total_registrations': registrations.count(),
            'confirmed_participants': registrations.filter(status=Registration.CONFIRMED).count(),
            'pending_registrations': registrations.filter(status=Registration.PENDING).count(),
            'checked_in_count': registrations.filter(checked_in=True).count(),
            'total_matches': matches.count(),
            'completed_matches': matches.filter(state=Match.COMPLETED).count(),
            'in_progress_matches': matches.filter(state=Match.IN_PROGRESS).count(),
            'scheduled_matches': matches.filter(state=Match.SCHEDULED).count(),
            'current_round': matches.filter(state__in=[Match.IN_PROGRESS, Match.COMPLETED]).aggregate(Max('round_number'))['round_number__max'] or 0,
            'completion_percentage': self._calculate_completion_percentage(),
        }
    
    def get_participant_stats(self) -> Dict:
        """Get participant demographics and statistics"""
        registrations = Registration.objects.filter(
            tournament=self.tournament,
            status=Registration.CONFIRMED,
            is_deleted=False
        )
        
        # Calculate average rating of participants
        avg_rating = 0
        if registrations.filter(user__isnull=False).exists():
            # Solo tournament
            avg_rating = registrations.filter(
                user__isnull=False
            ).aggregate(
                avg=Avg('user__profile__rating')
            )['avg'] or 1000
        
        return {
            'total_participants': registrations.count(),
            'solo_participants': registrations.filter(user__isnull=False).count(),
            'team_participants': registrations.filter(team__isnull=False).count(),
            'average_rating': round(avg_rating, 2),
            'registration_trend': self._get_registration_trend(),
        }
    
    def get_match_stats(self) -> Dict:
        """Get match statistics"""
        matches = Match.objects.filter(tournament=self.tournament)
        completed = matches.filter(state=Match.COMPLETED)
        
        if not completed.exists():
            return {
                'average_match_duration': None,
                'fastest_match': None,
                'longest_match': None,
                'total_games_played': 0,
            }
        
        # Calculate average match duration
        durations = []
        for match in completed:
            if match.started_at and match.completed_at:
                duration = (match.completed_at - match.started_at).total_seconds() / 60
                durations.append(duration)
        
        return {
            'average_match_duration': round(sum(durations) / len(durations), 2) if durations else None,
            'fastest_match': round(min(durations), 2) if durations else None,
            'longest_match': round(max(durations), 2) if durations else None,
            'total_games_played': completed.count(),
            'disputes': matches.filter(has_dispute=True).count(),
        }
    
    def get_financial_stats(self) -> Dict:
        """Get tournament financial statistics"""
        registrations = Registration.objects.filter(
            tournament=self.tournament,
            is_deleted=False
        )
        
        confirmed = registrations.filter(status=Registration.CONFIRMED)
        
        total_revenue = confirmed.count() * (self.tournament.entry_fee or 0)
        pending_revenue = registrations.filter(
            status=Registration.PENDING
        ).count() * (self.tournament.entry_fee or 0)
        
        return {
            'entry_fee': self.tournament.entry_fee or 0,
            'total_revenue': total_revenue,
            'pending_revenue': pending_revenue,
            'prize_pool': self.tournament.prize_pool or 0,
            'net_revenue': total_revenue - (self.tournament.prize_pool or 0),
            'confirmed_payments': confirmed.filter(payment_verified=True).count(),
            'pending_payments': confirmed.filter(payment_verified=False).count(),
        }
    
    def get_engagement_stats(self) -> Dict:
        """Get participant engagement metrics"""
        registrations = Registration.objects.filter(
            tournament=self.tournament,
            status=Registration.CONFIRMED,
            is_deleted=False
        )
        
        total = registrations.count()
        if total == 0:
            return {
                'check_in_rate': 0,
                'completion_rate': 0,
                'dropout_rate': 0,
            }
        
        checked_in = registrations.filter(checked_in=True).count()
        
        # Calculate completion rate (participants who finished all their matches)
        completed_participants = self._count_completed_participants()
        
        return {
            'check_in_rate': round((checked_in / total) * 100, 2),
            'completion_rate': round((completed_participants / total) * 100, 2) if total > 0 else 0,
            'dropout_rate': round(((total - completed_participants) / total) * 100, 2) if total > 0 else 0,
        }
    
    def get_leaderboard_preview(self, limit: int = 5) -> List[Dict]:
        """Get top performers in tournament"""
        from apps.tournaments.views.leaderboard import TournamentLeaderboardView
        
        view = TournamentLeaderboardView()
        view.tournament = self.tournament
        standings = view._calculate_standings()
        
        return standings[:limit]
    
    def _calculate_completion_percentage(self) -> float:
        """Calculate tournament completion percentage"""
        total_matches = Match.objects.filter(tournament=self.tournament).count()
        if total_matches == 0:
            return 0.0
        
        completed_matches = Match.objects.filter(
            tournament=self.tournament,
            state=Match.COMPLETED
        ).count()
        
        return round((completed_matches / total_matches) * 100, 2)
    
    def _get_registration_trend(self) -> List[Dict]:
        """Get registration trend over time"""
        registrations = Registration.objects.filter(
            tournament=self.tournament,
            is_deleted=False
        ).order_by('created_at')
        
        # Group by day
        trend = []
        current_date = None
        daily_count = 0
        
        for reg in registrations:
            reg_date = reg.created_at.date()
            if current_date != reg_date:
                if current_date:
                    trend.append({
                        'date': current_date.isoformat(),
                        'count': daily_count
                    })
                current_date = reg_date
                daily_count = 1
            else:
                daily_count += 1
        
        if current_date:
            trend.append({
                'date': current_date.isoformat(),
                'count': daily_count
            })
        
        return trend
    
    def _count_completed_participants(self) -> int:
        """Count participants who completed all their matches"""
        # TODO: Implement logic to check if participant finished all matches
        # For now, return estimate based on final round
        final_round = Match.objects.filter(
            tournament=self.tournament
        ).aggregate(Max('round_number'))['round_number__max']
        
        if not final_round:
            return 0
        
        # Participants in final matches are considered completers
        return Match.objects.filter(
            tournament=self.tournament,
            round_number=final_round,
            state=Match.COMPLETED
        ).count() * 2  # Both participants
    
    def export_stats_report(self) -> Dict:
        """Export comprehensive stats report"""
        return {
            'tournament': {
                'id': self.tournament.id,
                'name': self.tournament.name,
                'status': self.tournament.status,
                'format': self.tournament.format,
            },
            'overview': self.get_overview_stats(),
            'participants': self.get_participant_stats(),
            'matches': self.get_match_stats(),
            'financial': self.get_financial_stats(),
            'engagement': self.get_engagement_stats(),
            'leaderboard': self.get_leaderboard_preview(10),
            'generated_at': timezone.now().isoformat(),
        }
