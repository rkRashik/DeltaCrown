"""
Registration Dashboard View

Player's "My Registrations" history page.
Legacy DynamicRegistrationView and wizard flow removed — replaced by SmartRegistrationView.
"""
from django.views.generic import View
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.tournaments.models import FormResponse


class RegistrationDashboardView(LoginRequiredMixin, View):
    """View user's registration history"""
    template_name = 'tournaments/form_builder/registration_dashboard.html'
    
    def get(self, request):
        """Display user's registrations"""
        registrations = FormResponse.objects.filter(
            user=request.user
        ).select_related('tournament').order_by('-created_at')
        
        context = {
            'registrations': registrations,
            'draft_count': registrations.filter(status='draft').count(),
            'submitted_count': registrations.filter(status='submitted').count(),
            'approved_count': registrations.filter(status='approved').count()
        }
        
        return render(request, self.template_name, context)
