"""
Form Analytics Dashboard Views

Admin views for analyzing registration form performance.
"""
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from apps.tournaments.models import TournamentRegistrationForm
from apps.tournaments.services.form_analytics import FormAnalyticsService


class FormAnalyticsDashboardView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Comprehensive analytics dashboard for tournament registration forms.
    
    Shows:
    - Overview metrics (conversion rates, completion time)
    - Conversion funnel
    - Field-level analytics
    - Abandonment analysis
    - Time-series data
    - Step analytics (for multi-step forms)
    """
    
    model = TournamentRegistrationForm
    template_name = 'tournaments/analytics/dashboard.html'
    context_object_name = 'tournament_form'
    
    def test_func(self):
        """Only allow tournament organizer to view analytics"""
        form = self.get_object()
        return (
            self.request.user == form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_object(self):
        return get_object_or_404(
            TournamentRegistrationForm.objects.select_related(
                'tournament', 'based_on_template'
            ),
            tournament__slug=self.kwargs['tournament_slug']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        analytics = FormAnalyticsService(self.object.id)
        
        # Get all analytics data
        context['overview'] = analytics.get_overview_metrics()
        context['funnel'] = analytics.get_conversion_funnel()
        context['field_analytics'] = analytics.get_field_analytics()
        context['abandonment'] = analytics.get_abandonment_analysis()
        context['step_analytics'] = analytics.get_step_analytics()
        context['time_series'] = analytics.get_time_series_data(days=30)
        context['device_analytics'] = analytics.get_device_analytics()
        
        return context


class FormAnalyticsAPIView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    JSON API endpoint for analytics data.
    
    Used for AJAX requests and chart updates.
    """
    
    model = TournamentRegistrationForm
    
    def test_func(self):
        """Only allow tournament organizer to access analytics"""
        form = self.get_object()
        return (
            self.request.user == form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_object(self):
        return get_object_or_404(
            TournamentRegistrationForm.objects.select_related(
                'tournament', 'based_on_template'
            ),
            tournament__slug=self.kwargs['tournament_slug']
        )
    
    def get(self, request, *args, **kwargs):
        tournament_form = self.get_object()
        analytics = FormAnalyticsService(tournament_form.id)
        
        # Get requested data type
        data_type = request.GET.get('type', 'overview')
        days = int(request.GET.get('days', 30))
        
        if data_type == 'overview':
            data = analytics.get_overview_metrics()
        elif data_type == 'funnel':
            data = analytics.get_conversion_funnel()
        elif data_type == 'fields':
            data = analytics.get_field_analytics()
        elif data_type == 'abandonment':
            data = analytics.get_abandonment_analysis()
        elif data_type == 'steps':
            data = analytics.get_step_analytics()
        elif data_type == 'timeseries':
            data = analytics.get_time_series_data(days=days)
        elif data_type == 'device':
            data = analytics.get_device_analytics()
        elif data_type == 'export':
            data = analytics.export_analytics_report()
        else:
            data = {'error': 'Invalid data type'}
        
        return JsonResponse(data, safe=False)
