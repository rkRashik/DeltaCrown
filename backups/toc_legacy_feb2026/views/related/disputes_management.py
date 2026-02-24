"""
Comprehensive Dispute Management View for Organizers.

Provides full dispute resolution interface including:
- List of all disputes with filtering
- Detailed dispute information
- Resolution actions (Accept A, Accept B, Override, Reject)
- Evidence review
- Resolution history

Implementation Date: November 20, 2025
Feature: FE-T-025 (P2)
"""

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404

from apps.tournaments.models import Tournament
from apps.tournaments.models.match import Dispute
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker


class DisputeManagementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Comprehensive dispute management view for tournament organizers.
    
    Features:
    - List all disputes with status filtering
    - View dispute details and evidence
    - Resolve disputes with multiple decision types
    - Track resolution history
    """
    
    template_name = 'tournaments/organizer/disputes.html'
    
    def test_func(self):
        """Check if user has permission to manage disputes."""
        tournament = get_object_or_404(Tournament, slug=self.kwargs.get('slug'))
        checker = StaffPermissionChecker(tournament, self.request.user)
        return checker.can_resolve_disputes()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        slug = self.kwargs.get('slug')
        tournament = get_object_or_404(Tournament, slug=slug)
        
        context['tournament'] = tournament
        
        # Get all disputes for this tournament
        disputes = Dispute.objects.filter(
            match__tournament=tournament
        ).select_related(
            'match',
            'match__participant1__user',
            'match__participant1__team',
            'match__participant2__user',
            'match__participant2__team',
            'initiated_by',
            'resolved_by'
        ).order_by('-created_at')
        
        # Stats
        context['all_disputes_count'] = disputes.count()
        context['open_count'] = disputes.filter(status=Dispute.OPEN).count()
        context['under_review_count'] = disputes.filter(status=Dispute.UNDER_REVIEW).count()
        context['resolved_count'] = disputes.filter(status=Dispute.RESOLVED).count()
        
        # Filter by status if requested
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter in dict(Dispute.STATUS_CHOICES).keys():
            disputes = disputes.filter(status=status_filter)
        
        context['disputes'] = disputes
        context['status_filter'] = status_filter
        
        return context
