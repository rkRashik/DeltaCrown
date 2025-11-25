"""
Response Export Views

Views for exporting registration form responses.
"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from datetime import datetime
from apps.tournaments.models import TournamentRegistrationForm, Tournament
from apps.tournaments.services.response_export import ResponseExportService


class ExportResponsesView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Export form responses to various formats.
    
    Supports CSV, Excel, and JSON exports with filtering.
    """
    
    def test_func(self):
        """Only allow tournament organizer to export"""
        form = self.get_tournament_form()
        if form is None:
            return False
        return (
            self.request.user == form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_tournament_form(self):
        # Try to get the form, if it doesn't exist, check if tournament exists
        try:
            return get_object_or_404(
                TournamentRegistrationForm.objects.select_related('tournament', 'based_on_template'),
                tournament__slug=self.kwargs['tournament_slug']
            )
        except:
            # Check if tournament exists to provide helpful error
            tournament = get_object_or_404(Tournament, slug=self.kwargs['tournament_slug'])
            return None  # Will be handled in get() method
    
    def get(self, request, *args, **kwargs):
        tournament_form = self.get_tournament_form()
        
        # Check if form exists
        if tournament_form is None:
            tournament = get_object_or_404(Tournament, slug=self.kwargs['tournament_slug'])
            return HttpResponse(
                f'<h2>Registration Form Not Created</h2>'
                f'<p>The tournament "<strong>{tournament.name}</strong>" does not have a registration form yet.</p>'
                f'<p>Please create a registration form first in the organizer dashboard.</p>'
                f'<p><a href="/tournaments/organizer/{tournament.slug}/">Go to Organizer Dashboard</a></p>',
                status=404,
                content_type='text/html'
            )
        
        export_service = ResponseExportService(tournament_form.id)
        
        # Get export format
        export_format = request.GET.get('format', 'csv').lower()
        
        # Get filters
        status = request.GET.getlist('status')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        has_paid = request.GET.get('has_paid')
        payment_verified = request.GET.get('payment_verified')
        search = request.GET.get('search')
        
        # Parse dates
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d')
            except ValueError:
                date_from = None
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d')
            except ValueError:
                date_to = None
        
        # Parse booleans
        if has_paid:
            has_paid = has_paid.lower() == 'true'
        else:
            has_paid = None
        
        if payment_verified:
            payment_verified = payment_verified.lower() == 'true'
        else:
            payment_verified = None
        
        # Export based on format
        if export_format == 'excel':
            return export_service.export_to_excel(
                status=status,
                date_from=date_from,
                date_to=date_to,
                has_paid=has_paid,
                payment_verified=payment_verified,
                search=search,
            )
        elif export_format == 'json':
            include_analytics = request.GET.get('include_analytics', 'false').lower() == 'true'
            return export_service.export_to_json(
                status=status,
                date_from=date_from,
                date_to=date_to,
                has_paid=has_paid,
                payment_verified=payment_verified,
                search=search,
                include_analytics=include_analytics,
            )
        else:  # Default to CSV
            include_metadata = request.GET.get('include_metadata', 'true').lower() == 'true'
            return export_service.export_to_csv(
                status=status,
                date_from=date_from,
                date_to=date_to,
                has_paid=has_paid,
                payment_verified=payment_verified,
                search=search,
                include_metadata=include_metadata,
            )


class ExportPreviewView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Preview export data before downloading.
    
    Returns JSON with sample rows.
    """
    
    def test_func(self):
        """Only allow tournament organizer"""
        form = self.get_tournament_form()
        if form is None:
            return False
        return (
            self.request.user == form.tournament.organizer or
            self.request.user.is_staff
        )
    
    def get_tournament_form(self):
        try:
            return get_object_or_404(
                TournamentRegistrationForm.objects.select_related('tournament', 'based_on_template'),
                tournament__slug=self.kwargs['tournament_slug']
            )
        except:
            return None
    
    def get(self, request, *args, **kwargs):
        tournament_form = self.get_tournament_form()
        export_service = ResponseExportService(tournament_form.id)
        
        # Get filters
        status = request.GET.getlist('status')
        limit = int(request.GET.get('limit', 10))
        
        # Get preview
        preview = export_service.get_export_preview(
            limit=limit,
            status=status if status else None,
        )
        
        return JsonResponse(preview)
