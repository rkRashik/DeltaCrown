"""
Organizer console views for tournament management.

Provides a non-admin interface for tournament organizers to manage their tournaments,
view registrations, monitor matches, and handle disputes.

Source Documents:
- Documents/Planning/PART_4.5_ADMIN_ORGANIZER_SCREENS.md
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone

# Import from actual models package
from apps.tournaments.models import Tournament, Registration, Match, Dispute


class OrganizerRequiredMixin(UserPassesTestMixin):
    """
    Mixin to restrict access to organizers only.
    
    Permission Model:
    - Superuser: Full access to all tournaments
    - Staff (is_staff=True): Full access to all tournaments
    - Non-staff organizer: Access only to tournaments where user is set as Tournament.organizer
    - Regular users: No access (403 Forbidden)
    
    This mixin is used on dashboard views and should be combined with queryset filtering
    in individual views to ensure users only see their own tournaments.
    """
    
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        
        # Superusers and staff always have access to organizer console
        if user.is_superuser or user.is_staff:
            return True
        
        # Non-staff users must be organizer of at least one tournament
        return Tournament.objects.filter(organizer=user).exists()
    
    def handle_no_permission(self):
        """
        Override to provide clearer error for non-organizers.
        Returns 403 Forbidden instead of redirecting to login.
        """
        from django.core.exceptions import PermissionDenied
        if self.request.user.is_authenticated:
            raise PermissionDenied("You must be a tournament organizer to access this page.")
        return super().handle_no_permission()


class OrganizerDashboardView(LoginRequiredMixin, OrganizerRequiredMixin, ListView):
    """
    Organizer dashboard showing all tournaments the user organizes.
    
    Displays tournament list with key metrics:
    - Registration count
    - Match count
    - Status
    - Actions
    """
    model = Tournament
    template_name = 'tournaments/organizer/dashboard.html'
    context_object_name = 'tournaments'
    paginate_by = 20
    
    def get_queryset(self):
        """
        Filter tournaments based on user permissions.
        
        - Superuser/Staff: See all tournaments
        - Non-staff organizer: See only tournaments where user is Tournament.organizer
        """
        user = self.request.user
        
        # Staff and superusers see all tournaments
        if user.is_superuser or user.is_staff:
            queryset = Tournament.objects.all()
        else:
            # Non-staff users see only tournaments they organize
            queryset = Tournament.objects.filter(organizer=user)
        
        # Annotate with counts for dashboard display
        queryset = queryset.annotate(
            registration_count=Count('registrations', distinct=True),
            match_count=Count('matches', distinct=True)
        )
        
        # Order by most recent first
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Summary statistics
        user = self.request.user
        if user.is_superuser or user.is_staff:
            base_queryset = Tournament.objects.all()
        else:
            base_queryset = Tournament.objects.filter(organizer=user)
        
        context['stats'] = {
            'total_tournaments': base_queryset.count(),
            'active_tournaments': base_queryset.filter(
                status__in=[
                    Tournament.REGISTRATION_OPEN,
                    Tournament.REGISTRATION_CLOSED,
                    Tournament.LIVE
                ]
            ).count(),
            'draft_tournaments': base_queryset.filter(status=Tournament.DRAFT).count(),
            'completed_tournaments': base_queryset.filter(status=Tournament.COMPLETED).count(),
        }
        
        return context


class OrganizerTournamentDetailView(LoginRequiredMixin, OrganizerRequiredMixin, DetailView):
    """
    Tournament management detail view for organizers.
    
    Shows comprehensive tournament information including:
    - Tournament details
    - Registration list with counts
    - Match list with status
    - Dispute list
    - Quick actions
    """
    model = Tournament
    template_name = 'tournaments/organizer/tournament_detail.html'
    context_object_name = 'tournament'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        """
        Ensure user can only access tournaments they organize (unless staff/superuser).
        
        - Superuser/Staff: Can access any tournament
        - Non-staff organizer: Can only access tournaments where user is Tournament.organizer
        
        Returns 404 if tournament not found in user's accessible queryset.
        """
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return Tournament.objects.all()
        # Non-staff users can only access their own tournaments
        return Tournament.objects.filter(organizer=user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Registration statistics with actual queryset
        registrations = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).select_related('user').order_by('-created_at')
        
        context['registrations'] = registrations[:50]  # Limit to 50 for performance
        context['all_registrations_count'] = registrations.count()
        context['registration_stats'] = {
            'total': registrations.count(),
            'pending': registrations.filter(status=Registration.PENDING).count(),
            'confirmed': registrations.filter(status=Registration.CONFIRMED).count(),
            'rejected': registrations.filter(status=Registration.REJECTED).count(),
            'cancelled': registrations.filter(status=Registration.CANCELLED).count(),
            'checked_in': registrations.filter(checked_in=True).count(),
        }
        
        # Match statistics with actual queryset
        matches = Match.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).select_related('tournament').order_by('-scheduled_time')
        
        context['matches'] = matches[:50]  # Limit to 50 for performance
        context['all_matches_count'] = matches.count()
        context['match_stats'] = {
            'total': matches.count(),
            'scheduled': matches.filter(state=Match.SCHEDULED).count(),
            'live': matches.filter(state=Match.LIVE).count(),
            'completed': matches.filter(state=Match.COMPLETED).count(),
            'pending_result': matches.filter(state=Match.PENDING_RESULT).count(),
        }
        
        # Payment statistics
        from apps.tournaments.models import Payment
        payments = Payment.objects.filter(
            registration__tournament=tournament
        ).select_related('registration', 'registration__user').order_by('-submitted_at')
        
        context['payments'] = payments[:50]  # Limit to 50 for performance
        context['all_payments_count'] = payments.count()
        context['payment_stats'] = {
            'total': payments.count(),
            'pending': payments.filter(status=Payment.PENDING).count(),
            'submitted': payments.filter(status=Payment.SUBMITTED).count(),
            'verified': payments.filter(status=Payment.VERIFIED).count(),
            'rejected': payments.filter(status=Payment.REJECTED).count(),
        }
        
        # Dispute statistics
        disputes = Dispute.objects.filter(
            match__tournament=tournament
        ).select_related('match').order_by('-created_at')
        
        context['disputes'] = disputes[:20]  # Limit to 20 for performance
        context['all_disputes_count'] = disputes.count()
        context['dispute_stats'] = {
            'total': disputes.count(),
            'open': disputes.filter(status=Dispute.OPEN).count(),
            'under_review': disputes.filter(status=Dispute.UNDER_REVIEW).count(),
            'resolved': disputes.filter(status=Dispute.RESOLVED).count(),
        }
        
        # Time-based status
        now = timezone.now()
        context['time_status'] = {
            'is_registration_open': (
                tournament.registration_start <= now <= tournament.registration_end and
                tournament.status == Tournament.REGISTRATION_OPEN
            ),
            'days_until_start': (tournament.tournament_start - now).days if tournament.tournament_start > now else 0,
            'is_live': tournament.status == Tournament.LIVE,
        }
        
        return context
