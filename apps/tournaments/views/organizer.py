"""
Organizer console views for tournament management.

Provides a non-admin interface for tournament organizers to manage their tournaments,
view registrations, monitor matches, and handle disputes.

Source Documents:
- Documents/Planning/PART_4.5_ADMIN_ORGANIZER_SCREENS.md
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, View
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required

# Import from actual models package
from apps.tournaments.models import (
    Tournament, Registration, Match, Dispute, Payment, 
    Bracket, TournamentStaff, TournamentPaymentMethod, TournamentAnnouncement
)
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker


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


# ============================================================================
# NEW: Comprehensive Organizer Hub with 7 Tabs
# ============================================================================

class OrganizerHubView(LoginRequiredMixin, View):
    """
    Main organizer hub with 7 tabs:
    - Overview: Stats, quick actions, recent activity
    - Participants: Registration list with approve/reject
    - Payments: Payment tracking and verification
    - Brackets: Bracket management and match list
    - Disputes: Dispute handling
    - Announcements: Create/manage announcements
    - Settings: Tournament settings and staff management
    """
    
    def get_tournament(self, slug):
        """Get tournament and check permissions"""
        user = self.request.user
        
        if user.is_superuser or user.is_staff:
            tournament = get_object_or_404(Tournament, slug=slug)
        else:
            tournament = get_object_or_404(Tournament, slug=slug, organizer=user)
        
        return tournament
    
    def check_permission(self, tournament, permission_code):
        """Check if user has specific permission"""
        checker = StaffPermissionChecker(tournament, self.request.user)
        if not checker.has_permission(permission_code):
            return False
        return True
    
    def get(self, request, slug, tab='overview'):
        """Render organizer hub with requested tab"""
        tournament = self.get_tournament(slug)
        checker = StaffPermissionChecker(tournament, request.user)
        
        if not checker.can_access_organizer_hub():
            return HttpResponseForbidden("You do not have permission to access this tournament's organizer hub.")
        
        # Route to appropriate tab handler
        if tab == 'overview':
            return self.overview_tab(request, tournament, checker)
        elif tab == 'participants':
            return self.participants_tab(request, tournament, checker)
        elif tab == 'payments':
            return self.payments_tab(request, tournament, checker)
        elif tab == 'brackets':
            return self.brackets_tab(request, tournament, checker)
        elif tab == 'disputes':
            return self.disputes_tab(request, tournament, checker)
        elif tab == 'announcements':
            return self.announcements_tab(request, tournament, checker)
        elif tab == 'settings':
            return self.settings_tab(request, tournament, checker)
        else:
            return redirect('tournaments:organizer_tournament_detail', slug=slug)
    
    def overview_tab(self, request, tournament, checker):
        """Overview tab: stats, quick actions, recent activity"""
        # Registration stats
        registrations = Registration.objects.filter(tournament=tournament, is_deleted=False)
        reg_stats = {
            'total': registrations.count(),
            'pending': registrations.filter(status='pending').count(),
            'confirmed': registrations.filter(status='confirmed').count(),
            'checked_in': registrations.filter(checked_in=True).count(),
        }
        
        # Payment stats
        payments = Payment.objects.filter(registration__tournament=tournament)
        payment_stats = {
            'total': payments.count(),
            'pending': payments.filter(status='pending').count(),
            'verified': payments.filter(status='verified').count(),
            'total_amount': payments.filter(status='verified').aggregate(Sum('amount'))['amount__sum'] or 0,
        }
        
        # Match stats
        matches = Match.objects.filter(tournament=tournament, is_deleted=False)
        match_stats = {
            'total': matches.count(),
            'scheduled': matches.filter(state='scheduled').count(),
            'live': matches.filter(state='live').count(),
            'completed': matches.filter(state='completed').count(),
        }
        
        # Dispute stats
        disputes = Dispute.objects.filter(match__tournament=tournament)
        dispute_stats = {
            'total': disputes.count(),
            'open': disputes.filter(status='open').count(),
            'under_review': disputes.filter(status='under_review').count(),
        }
        
        # Recent activity (last 10 registrations)
        recent_registrations = registrations.select_related('user').order_by('-created_at')[:10]
        
        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'overview',
            'reg_stats': reg_stats,
            'payment_stats': payment_stats,
            'match_stats': match_stats,
            'dispute_stats': dispute_stats,
            'recent_registrations': recent_registrations,
        }
        
        return render(request, 'tournaments/organizer/hub_overview.html', context)
    
    def participants_tab(self, request, tournament, checker):
        """Participants tab: registration list with actions"""
        if not checker.has_any(['manage_registrations', 'view_all']):
            messages.error(request, "You don't have permission to view participants.")
            return redirect('tournaments:organizer_hub', slug=tournament.slug, tab='overview')
        
        # Get filter parameters
        status_filter = request.GET.get('status', '')
        search = request.GET.get('search', '')
        checked_in_filter = request.GET.get('checked_in', '')
        
        # Base queryset
        registrations = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).select_related('user', 'team')
        
        # Apply filters
        if status_filter:
            registrations = registrations.filter(status=status_filter)
        if checked_in_filter:
            registrations = registrations.filter(checked_in=(checked_in_filter == 'yes'))
        if search:
            registrations = registrations.filter(
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(team__name__icontains=search)
            )
        
        registrations = registrations.order_by('-created_at')
        
        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'participants',
            'registrations': registrations,
            'can_manage': checker.can_manage_registrations(),
        }
        
        return render(request, 'tournaments/organizer/hub_participants.html', context)
    
    def payments_tab(self, request, tournament, checker):
        """Payments tab: payment tracking and verification"""
        if not checker.has_any(['approve_payments', 'view_all']):
            messages.error(request, "You don't have permission to view payments.")
            return redirect('tournaments:organizer_hub', slug=tournament.slug, tab='overview')
        
        # Get filter parameters
        status_filter = request.GET.get('status', '')
        method_filter = request.GET.get('method', '')
        
        # Base queryset
        payments = Payment.objects.filter(
            registration__tournament=tournament
        ).select_related('registration', 'registration__user')
        
        # Apply filters
        if status_filter:
            payments = payments.filter(status=status_filter)
        if method_filter:
            payments = payments.filter(payment_method=method_filter)
        
        payments = payments.order_by('-submitted_at')
        
        # Payment statistics
        payment_stats = {
            'total_submitted': payments.filter(status__in=['submitted', 'verified']).count(),
            'total_amount': payments.filter(status='verified').aggregate(Sum('amount'))['amount__sum'] or 0,
            'pending_verification': payments.filter(status='submitted').count(),
        }
        
        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'payments',
            'payments': payments,
            'payment_stats': payment_stats,
            'can_approve': checker.can_approve_payments(),
        }
        
        return render(request, 'tournaments/organizer/hub_payments.html', context)
    
    def brackets_tab(self, request, tournament, checker):
        """Brackets tab: bracket management and match list"""
        if not checker.has_any(['manage_brackets', 'view_all']):
            messages.error(request, "You don't have permission to view brackets.")
            return redirect('tournaments:organizer_hub', slug=tournament.slug, tab='overview')
        
        # Get bracket if exists
        try:
            bracket = Bracket.objects.get(tournament=tournament)
        except Bracket.DoesNotExist:
            bracket = None
        
        # Get matches
        matches = Match.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).select_related('participant1', 'participant2').order_by('round_number', 'match_number')
        
        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'brackets',
            'bracket': bracket,
            'matches': matches,
            'can_manage': checker.can_manage_brackets(),
        }
        
        return render(request, 'tournaments/organizer/hub_brackets.html', context)
    
    def disputes_tab(self, request, tournament, checker):
        """Disputes tab: dispute handling"""
        if not checker.has_any(['resolve_disputes', 'view_all']):
            messages.error(request, "You don't have permission to view disputes.")
            return redirect('tournaments:organizer_hub', slug=tournament.slug, tab='overview')
        
        # Get filter parameters
        status_filter = request.GET.get('status', '')
        
        # Base queryset
        disputes = Dispute.objects.filter(
            match__tournament=tournament
        ).select_related('match', 'filed_by')
        
        # Apply filters
        if status_filter:
            disputes = disputes.filter(status=status_filter)
        
        disputes = disputes.order_by('-created_at')
        
        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'disputes',
            'disputes': disputes,
            'can_resolve': checker.can_resolve_disputes(),
        }
        
        return render(request, 'tournaments/organizer/hub_disputes.html', context)
    
    def announcements_tab(self, request, tournament, checker):
        """Announcements tab: create/manage announcements"""
        if not checker.has_any(['make_announcements', 'view_all']):
            messages.error(request, "You don't have permission to view announcements.")
            return redirect('tournaments:organizer_hub', slug=tournament.slug, tab='overview')
        
        # Handle POST request for creating announcements
        if request.method == 'POST' and checker.can_make_announcements():
            title = request.POST.get('title', '').strip()
            message = request.POST.get('message', '').strip()
            is_pinned = request.POST.get('is_pinned') == 'on'
            is_important = request.POST.get('is_important') == 'on'
            
            if title and message:
                announcement = TournamentAnnouncement.objects.create(
                    tournament=tournament,
                    title=title,
                    message=message,
                    created_by=request.user,
                    is_pinned=is_pinned,
                    is_important=is_important
                )
                messages.success(request, f"Announcement '{title}' created successfully.")
                return redirect('tournaments:organizer_hub', slug=tournament.slug, tab='announcements')
            else:
                messages.error(request, "Title and message are required.")
        
        # Get all announcements for this tournament
        announcements = TournamentAnnouncement.objects.filter(
            tournament=tournament
        ).select_related('created_by').order_by('-is_pinned', '-created_at')
        
        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'announcements',
            'announcements': announcements,
            'can_announce': checker.can_make_announcements(),
        }
        
        return render(request, 'tournaments/organizer/hub_announcements.html', context)
    
    def settings_tab(self, request, tournament, checker):
        """Settings tab: tournament settings and staff management"""
        if not checker.has_any(['edit_settings', 'manage_staff']):
            messages.error(request, "You don't have permission to view settings.")
            return redirect('tournaments:organizer_hub', slug=tournament.slug, tab='overview')
        
        # Get payment methods
        payment_methods = TournamentPaymentMethod.objects.filter(tournament=tournament).order_by('display_order')
        
        # Get staff members
        staff_members = TournamentStaff.objects.filter(
            tournament=tournament
        ).select_related('user', 'role')
        
        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'settings',
            'payment_methods': payment_methods,
            'staff_members': staff_members,
            'can_edit': checker.can_edit_settings(),
            'can_manage_staff': checker.can_manage_staff(),
        }
        
        return render(request, 'tournaments/organizer/hub_settings.html', context)


# ============================================================================
# AJAX Actions for Organizer Hub
# ============================================================================

@login_required
@require_POST
def approve_registration(request, slug, registration_id):
    """Approve a registration"""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    
    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)
    registration.status = 'confirmed'
    registration.save()
    
    messages.success(request, f"Registration for {registration.user.username} approved.")
    return JsonResponse({'success': True})


@login_required
@require_POST
def reject_registration(request, slug, registration_id):
    """Reject a registration"""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    
    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)
    registration.status = 'rejected'
    registration.save()
    
    messages.success(request, f"Registration for {registration.user.username} rejected.")
    return JsonResponse({'success': True})


@login_required
@require_POST
def verify_payment(request, slug, payment_id):
    """Verify a payment"""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    
    if not checker.can_approve_payments():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    payment = get_object_or_404(Payment, id=payment_id, registration__tournament=tournament)
    payment.status = 'verified'
    payment.verified_by = request.user
    payment.verified_at = timezone.now()
    payment.save()
    
    messages.success(request, f"Payment verified for {payment.registration.user.username}.")
    return JsonResponse({'success': True})


@login_required
@require_POST
def reject_payment(request, slug, payment_id):
    """Reject a payment"""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    
    if not checker.can_approve_payments():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    payment = get_object_or_404(Payment, id=payment_id, registration__tournament=tournament)
    payment.status = 'rejected'
    payment.save()
    
    messages.warning(request, f"Payment rejected for {payment.registration.user.username}.")
    return JsonResponse({'success': True})


@login_required
@require_POST
def toggle_checkin(request, slug, registration_id):
    """Toggle check-in status for a registration (organizer only)"""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    
    if not checker.can_manage_registrations():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)
    
    if registration.checked_in:
        # Uncheck
        registration.checked_in = False
        registration.checked_in_at = None
        registration.checked_in_by = None
        registration.save()
        messages.info(request, f"{registration.user.username} check-in removed.")
    else:
        # Check in
        registration.checked_in = True
        registration.checked_in_at = timezone.now()
        registration.checked_in_by = request.user
        registration.save()
        messages.success(request, f"{registration.user.username} checked in successfully.")
    
    return JsonResponse({'success': True, 'checked_in': registration.checked_in})


@login_required
@require_POST
def update_dispute_status(request, slug, dispute_id):
    """Update dispute status (e.g., open -> under_review)"""
    import json
    
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    
    if not checker.can_resolve_disputes():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    dispute = get_object_or_404(Dispute, id=dispute_id, match__tournament=tournament)
    
    data = json.loads(request.body)
    new_status = data.get('status')
    
    if new_status not in ['open', 'under_review', 'resolved']:
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    
    dispute.status = new_status
    dispute.save()
    
    messages.info(request, f"Dispute status updated to {new_status.replace('_', ' ').title()}.")
    return JsonResponse({'success': True})


@login_required
@require_POST
def resolve_dispute(request, slug, dispute_id):
    """Resolve a dispute with resolution notes"""
    import json
    
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    
    if not checker.can_resolve_disputes():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    dispute = get_object_or_404(Dispute, id=dispute_id, match__tournament=tournament)
    
    data = json.loads(request.body)
    resolution_notes = data.get('resolution_notes', '').strip()
    
    if not resolution_notes:
        return JsonResponse({'success': False, 'error': 'Resolution notes required'}, status=400)
    
    dispute.status = 'resolved'
    dispute.resolution_notes = resolution_notes
    dispute.resolved_by = request.user
    dispute.resolved_at = timezone.now()
    dispute.save()
    
    messages.success(request, f"Dispute resolved successfully.")
    return JsonResponse({'success': True})


@login_required
@require_POST
def submit_match_score(request, slug, match_id):
    """Submit or update match score"""
    import json
    
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)
    
    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    match = get_object_or_404(Match, id=match_id, tournament=tournament)
    
    data = json.loads(request.body)
    score1 = data.get('score1')
    score2 = data.get('score2')
    
    # Validate scores
    try:
        score1 = int(score1)
        score2 = int(score2)
        if score1 < 0 or score2 < 0:
            return JsonResponse({'success': False, 'error': 'Scores must be non-negative'}, status=400)
        if score1 == score2:
            return JsonResponse({'success': False, 'error': 'Scores cannot be tied'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid score values'}, status=400)
    
    # Update match
    match.score1 = score1
    match.score2 = score2
    match.state = 'completed'
    
    # Determine winner
    if score1 > score2:
        match.winner_id = match.participant1_id
        match.loser_id = match.participant2_id
    else:
        match.winner_id = match.participant2_id
        match.loser_id = match.participant1_id
    
    match.save()
    
    messages.success(request, f"Match score submitted: {score1}-{score2}")
    return JsonResponse({'success': True, 'score1': score1, 'score2': 'score2'})


@login_required
def create_tournament(request):
    """Frontend view for creating a new tournament"""
    from apps.tournaments.forms.tournament_create import TournamentCreateForm
    
    # Check permissions
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'You do not have permission to create tournaments.')
        return redirect('tournaments:list')
    
    if request.method == 'POST':
        form = TournamentCreateForm(request.POST)
        if form.is_valid():
            tournament = form.save(commit=False)
            tournament.organizer = request.user
            tournament.status = 'draft'  # Start as draft
            tournament.save()
            
            messages.success(request, f'Tournament "{tournament.name}" created successfully!')
            return redirect('tournaments:organizer_tournament_detail', slug=tournament.slug)
    else:
        form = TournamentCreateForm()
    
    return render(request, 'tournaments/organizer/create_tournament.html', {
        'form': form,
        'page_title': 'Create New Tournament',
    })
