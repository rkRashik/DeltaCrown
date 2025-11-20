"""
Tournament Health Metrics Dashboard (FE-T-026)
Provides real-time health metrics and monitoring for tournament organizers.
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Avg
from datetime import timedelta

from apps.tournaments.models import Tournament, Match, Registration, Dispute
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker


class TournamentHealthMetricsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Real-time health metrics dashboard for tournament organizers.
    Shows system status, performance metrics, and alerts.
    """
    template_name = 'tournaments/organizer/health_metrics.html'

    def test_func(self):
        """Verify user has organizer permissions"""
        slug = self.kwargs.get('slug')
        tournament = get_object_or_404(Tournament, slug=slug)
        checker = StaffPermissionChecker(tournament, self.request.user)
        return checker.can_access_organizer()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug')
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Time windows for metrics
        now = timezone.now()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        # System Health Status
        health_status = self._calculate_health_status(tournament, now)
        
        # Performance Metrics
        performance_metrics = self._calculate_performance_metrics(tournament, last_hour, last_day)
        
        # Active Connections & Load
        load_metrics = self._calculate_load_metrics(tournament, now)
        
        # Alerts & Issues
        alerts = self._generate_alerts(tournament, now)
        
        # Historical Data (last 24 hours)
        historical_data = self._generate_historical_data(tournament, last_day, now)
        
        context.update({
            'tournament': tournament,
            'health_status': health_status,
            'performance_metrics': performance_metrics,
            'load_metrics': load_metrics,
            'alerts': alerts,
            'historical_data': historical_data,
            'refresh_interval': 30,  # seconds
        })
        
        return context
    
    def _calculate_health_status(self, tournament, now):
        """Calculate overall system health"""
        # Check for critical issues
        pending_disputes = Dispute.objects.filter(
            tournament=tournament,
            status__in=['OPEN', 'UNDER_REVIEW']
        ).count()
        
        overdue_matches = Match.objects.filter(
            tournament=tournament,
            status='SCHEDULED',
            scheduled_time__lt=now - timedelta(hours=2)
        ).count()
        
        pending_results = Match.objects.filter(
            tournament=tournament,
            status='PENDING_VERIFICATION'
        ).count()
        
        # Determine status
        if overdue_matches > 5 or pending_disputes > 10:
            status = 'critical'
            status_text = 'Critical'
            status_color = 'red'
        elif overdue_matches > 2 or pending_disputes > 5 or pending_results > 10:
            status = 'warning'
            status_text = 'Warning'
            status_color = 'yellow'
        else:
            status = 'healthy'
            status_text = 'Healthy'
            status_color = 'green'
        
        return {
            'status': status,
            'status_text': status_text,
            'status_color': status_color,
            'pending_disputes': pending_disputes,
            'overdue_matches': overdue_matches,
            'pending_results': pending_results,
        }
    
    def _calculate_performance_metrics(self, tournament, last_hour, last_day):
        """Calculate performance metrics"""
        # Match completion rate
        completed_today = Match.objects.filter(
            tournament=tournament,
            status='COMPLETED',
            updated_at__gte=last_day
        ).count()
        
        scheduled_today = Match.objects.filter(
            tournament=tournament,
            scheduled_time__gte=last_day,
            scheduled_time__lte=timezone.now()
        ).count()
        
        completion_rate = (completed_today / scheduled_today * 100) if scheduled_today > 0 else 0
        
        # Average match duration (simulated - would need real timing data)
        avg_match_duration = 18.5  # minutes (mock data)
        
        # Dispute resolution time (average time from OPEN to RESOLVED)
        resolved_disputes = Dispute.objects.filter(
            tournament=tournament,
            status='RESOLVED',
            resolved_at__gte=last_day
        )
        
        avg_resolution_hours = 4.2  # hours (mock data - would calculate from resolved_at - created_at)
        
        # Check-in success rate
        total_registrations = Registration.objects.filter(
            tournament=tournament,
            status='CONFIRMED'
        ).count()
        
        checked_in = Registration.objects.filter(
            tournament=tournament,
            status='CONFIRMED',
            has_checked_in=True
        ).count()
        
        checkin_rate = (checked_in / total_registrations * 100) if total_registrations > 0 else 0
        
        return {
            'completion_rate': round(completion_rate, 1),
            'avg_match_duration': avg_match_duration,
            'avg_resolution_hours': avg_resolution_hours,
            'checkin_rate': round(checkin_rate, 1),
            'completed_today': completed_today,
            'scheduled_today': scheduled_today,
        }
    
    def _calculate_load_metrics(self, tournament, now):
        """Calculate current load metrics"""
        # Active participants (checked in)
        active_participants = Registration.objects.filter(
            tournament=tournament,
            status='CONFIRMED',
            has_checked_in=True
        ).count()
        
        # Ongoing matches
        ongoing_matches = Match.objects.filter(
            tournament=tournament,
            status='IN_PROGRESS'
        ).count()
        
        # Pending actions (need organizer attention)
        pending_actions = (
            Registration.objects.filter(tournament=tournament, status='PENDING').count() +
            Match.objects.filter(tournament=tournament, status='PENDING_VERIFICATION').count() +
            Dispute.objects.filter(tournament=tournament, status='OPEN').count()
        )
        
        return {
            'active_participants': active_participants,
            'ongoing_matches': ongoing_matches,
            'pending_actions': pending_actions,
        }
    
    def _generate_alerts(self, tournament, now):
        """Generate alerts and warnings"""
        alerts = []
        
        # Check for overdue matches
        overdue = Match.objects.filter(
            tournament=tournament,
            status='SCHEDULED',
            scheduled_time__lt=now - timedelta(hours=2)
        ).count()
        
        if overdue > 0:
            alerts.append({
                'severity': 'high' if overdue > 5 else 'medium',
                'title': f'{overdue} Overdue Match{"es" if overdue != 1 else ""}',
                'message': f'{overdue} match{"es" if overdue != 1 else ""} scheduled over 2 hours ago not yet completed',
                'action_url': f'/tournaments/organizer/{tournament.slug}/matches/',
                'action_text': 'View Matches',
                'timestamp': now,
            })
        
        # Check for pending disputes
        open_disputes = Dispute.objects.filter(
            tournament=tournament,
            status='OPEN'
        ).count()
        
        if open_disputes > 0:
            alerts.append({
                'severity': 'high' if open_disputes > 5 else 'medium',
                'title': f'{open_disputes} Open Dispute{"s" if open_disputes != 1 else ""}',
                'message': f'{open_disputes} dispute{"s" if open_disputes != 1 else ""} awaiting review',
                'action_url': f'/tournaments/organizer/{tournament.slug}/disputes/manage/',
                'action_text': 'Resolve Disputes',
                'timestamp': now,
            })
        
        # Check for pending registrations
        pending_regs = Registration.objects.filter(
            tournament=tournament,
            status='PENDING'
        ).count()
        
        if pending_regs > 10:
            alerts.append({
                'severity': 'low',
                'title': f'{pending_regs} Pending Registrations',
                'message': f'{pending_regs} registration{"s" if pending_regs != 1 else ""} awaiting approval',
                'action_url': f'/tournaments/organizer/{tournament.slug}/participants/',
                'action_text': 'Review Registrations',
                'timestamp': now,
            })
        
        # Sort by severity
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        alerts.sort(key=lambda x: severity_order.get(x['severity'], 3))
        
        return alerts
    
    def _generate_historical_data(self, tournament, start_time, end_time):
        """Generate historical metrics for charts (last 24 hours)"""
        # Mock data for demonstration - would query actual metrics
        # In production, this would come from time-series data or aggregated logs
        
        hours = []
        matches_completed = []
        disputes_opened = []
        participants_checked_in = []
        
        current = start_time
        while current <= end_time:
            hours.append(current.strftime('%H:%M'))
            # Mock data - would be real queries
            matches_completed.append(Match.objects.filter(
                tournament=tournament,
                status='COMPLETED',
                updated_at__gte=current,
                updated_at__lt=current + timedelta(hours=1)
            ).count())
            disputes_opened.append(Dispute.objects.filter(
                tournament=tournament,
                created_at__gte=current,
                created_at__lt=current + timedelta(hours=1)
            ).count())
            participants_checked_in.append(Registration.objects.filter(
                tournament=tournament,
                has_checked_in=True,
                updated_at__gte=current,
                updated_at__lt=current + timedelta(hours=1)
            ).count())
            current += timedelta(hours=1)
        
        return {
            'labels': hours,
            'matches_completed': matches_completed,
            'disputes_opened': disputes_opened,
            'participants_checked_in': participants_checked_in,
        }
