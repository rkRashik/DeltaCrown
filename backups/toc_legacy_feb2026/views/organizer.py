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
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.http import HttpResponseForbidden
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
    
    def get_common_context(self, tournament):
        """Get common context data for all tabs (badge counts for nav)."""
        open_disputes_count = Dispute.objects.filter(
            match__tournament=tournament,
            status='open'
        ).count()

        # Registration badge
        reg_pending = Registration.objects.filter(
            tournament=tournament, is_deleted=False, status='pending'
        ).count()

        # Payment badge
        payment_pending = Payment.objects.filter(
            registration__tournament=tournament, status='pending'
        ).count()

        # Match badge (pending result confirmation)
        from apps.tournaments.models import Match
        match_pending = Match.objects.filter(
            tournament=tournament,
            state__in=['scheduled', 'check_in', 'ready', 'live', 'pending_result']
        ).count()

        return {
            'open_disputes_count': open_disputes_count,
            'reg_stats': {'pending': reg_pending},
            'payment_stats': {'pending': payment_pending},
            'match_stats': {'pending': match_pending},
        }
    
    def check_permission(self, tournament, permission_code):
        """Check if user has specific permission"""
        checker = StaffPermissionChecker(tournament, self.request.user)
        if not checker.has_permission(permission_code):
            return False
        return True
    
    def get(self, request, slug, tab='overview'):
        """Render organizer hub with requested tab"""
        return self._dispatch_tab(request, slug, tab)

    def post(self, request, slug, tab='overview'):
        """Handle POST requests (e.g., announcement creation)"""
        return self._dispatch_tab(request, slug, tab)

    def _dispatch_tab(self, request, slug, tab):
        """Route to appropriate tab handler"""
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
        elif tab == 'matches':
            return self.matches_tab(request, tournament, checker)
        elif tab == 'schedule':
            return self.schedule_tab(request, tournament, checker)
        elif tab == 'disputes':
            return self.disputes_tab(request, tournament, checker)
        elif tab == 'announcements':
            return self.announcements_tab(request, tournament, checker)
        elif tab == 'settings':
            return self.settings_tab(request, tournament, checker)
        else:
            return redirect('tournaments:organizer_tournament_detail', slug=slug)
    
    def overview_tab(self, request, tournament, checker):
        """Command Center tab: alerts, stats, lifecycle, quick actions, recent activity"""
        from apps.tournaments.services.command_center_service import CommandCenterService

        # Registration stats
        registrations = Registration.objects.filter(tournament=tournament, is_deleted=False)
        reg_stats = {
            'total': registrations.count(),
            'pending': registrations.filter(status='pending').count(),
            'confirmed': registrations.filter(status='confirmed').count(),
            'waitlisted': registrations.filter(status='waitlisted').count(),
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

        # Command Center alerts
        alerts = CommandCenterService.get_alerts(
            tournament, reg_stats, payment_stats, dispute_stats, match_stats
        )

        # Lifecycle progress
        lifecycle = CommandCenterService.get_lifecycle_progress(tournament)

        # Upcoming events
        upcoming_events = CommandCenterService.get_upcoming_events(tournament)
        
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
            'alerts': alerts,
            'lifecycle': lifecycle,
            'upcoming_events': upcoming_events,
            'recent_registrations': recent_registrations,
        }
        context.update(self.get_common_context(tournament))
        
        return render(request, 'tournaments/manage/overview.html', context)
    
    def participants_tab(self, request, tournament, checker):
        """Participants tab: registration list with actions, pagination, and search"""
        if not checker.has_any(['manage_registrations', 'view_all']):
            messages.error(request, "You don't have permission to view participants.")
            return redirect('tournaments:organizer_hub', slug=tournament.slug, tab='overview')
        
        # Get filter parameters
        status_filter = request.GET.get('status', '')
        search = request.GET.get('search', '')
        checked_in_filter = request.GET.get('checked_in', '')
        page_number = request.GET.get('page', 1)
        
        # Base queryset
        registrations = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).select_related('user')
        
        # Stats — computed before filtering for the header
        from django.db.models import Count
        reg_stats = registrations.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            confirmed=Count('id', filter=Q(status='confirmed')),
            payment_submitted=Count('id', filter=Q(status='payment_submitted')),
            waitlisted=Count('id', filter=Q(status='waitlisted')),
            rejected=Count('id', filter=Q(status='rejected')),
            checked_in_count=Count('id', filter=Q(checked_in=True)),
        )
        
        # Apply filters
        if status_filter:
            if status_filter == 'checked_in':
                registrations = registrations.filter(checked_in=True)
            else:
                registrations = registrations.filter(status=status_filter)
        if checked_in_filter:
            registrations = registrations.filter(checked_in=(checked_in_filter == 'yes'))
        if search:
            registrations = registrations.filter(
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(registration_number__icontains=search) |
                Q(registration_data__game_id__icontains=search)
            )
        
        registrations = registrations.order_by('-created_at')
        
        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(registrations, 20)
        page_obj = paginator.get_page(page_number)
        
        # Status tabs for filter bar
        status_tabs = [
            ('pending', 'Pending', reg_stats['pending']),
            ('confirmed', 'Confirmed', reg_stats['confirmed']),
            ('payment_submitted', 'Payment Queue', reg_stats['payment_submitted']),
            ('waitlisted', 'Waitlisted', reg_stats['waitlisted']),
            ('rejected', 'Rejected', reg_stats['rejected']),
            ('checked_in', 'Checked In', reg_stats['checked_in_count']),
        ]
        
        # ── Team name resolution ──
        team_ids = set()
        for r in page_obj:
            if r.team_id:
                team_ids.add(r.team_id)
        team_name_map = {}
        if team_ids:
            try:
                from apps.organizations.models.team import Team
                for t in Team.objects.filter(id__in=team_ids).only('id', 'name', 'tag'):
                    team_name_map[t.id] = {'name': t.name, 'tag': t.tag or ''}
            except Exception:
                pass

        # ── Verification summary (lightweight) ──
        verification_summary = None
        try:
            from apps.tournaments.services.registration_verification import RegistrationVerificationService
            vresult = RegistrationVerificationService.verify_tournament(tournament)
            verification_summary = vresult['summary']
            # Build a quick map: reg_id -> highest severity flag
            verification_flag_map = {}
            for reg_id, flags in vresult['per_registration'].items():
                max_sev = 'INFO'
                for f in flags:
                    if f['severity'] == 'CRITICAL':
                        max_sev = 'CRITICAL'
                        break
                    elif f['severity'] == 'WARNING':
                        max_sev = 'WARNING'
                verification_flag_map[reg_id] = max_sev
        except Exception:
            verification_flag_map = {}

        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'participants',
            'registrations': page_obj,
            'page_obj': page_obj,
            'reg_stats': reg_stats,
            'status_tabs': status_tabs,
            'max_participants': tournament.max_participants,
            'can_manage': checker.can_manage_registrations(),
            'team_name_map': team_name_map,
            'verification_summary': verification_summary,
            'verification_flag_map': verification_flag_map,
        }
        context.update(self.get_common_context(tournament))
        
        return render(request, 'tournaments/manage/participants.html', context)
    
    def payments_tab(self, request, tournament, checker):
        """Payments tab: payment tracking and verification with queue focus"""
        if not checker.has_any(['approve_payments', 'view_all']):
            messages.error(request, "You don't have permission to view payments.")
            return redirect('tournaments:organizer_hub', slug=tournament.slug, tab='overview')
        
        # Get filter parameters — default to submitted (pending queue)
        status_filter = request.GET.get('status', 'submitted')
        method_filter = request.GET.get('method', '')
        search = request.GET.get('search', '')
        page_number = request.GET.get('page', 1)
        
        # Base queryset
        payments = Payment.objects.filter(
            registration__tournament=tournament
        ).select_related('registration', 'registration__user')
        
        # Payment statistics (before filtering)
        from django.db.models import Count
        all_payment_stats = payments.aggregate(
            total=Count('id'),
            submitted=Count('id', filter=Q(status='submitted')),
            verified=Count('id', filter=Q(status='verified')),
            rejected=Count('id', filter=Q(status='rejected')),
            total_amount=Sum('amount', filter=Q(status='verified')),
        )
        
        # Apply filters
        if status_filter and status_filter != 'all':
            payments = payments.filter(status=status_filter)
        if method_filter:
            payments = payments.filter(payment_method=method_filter)
        if search:
            payments = payments.filter(
                Q(registration__user__username__icontains=search) |
                Q(registration__registration_number__icontains=search) |
                Q(transaction_id__icontains=search)
            )
        
        payments = payments.order_by('-submitted_at')
        
        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(payments, 20)
        page_obj = paginator.get_page(page_number)
        
        payment_stats = {
            'total': all_payment_stats['total'] or 0,
            'submitted': all_payment_stats['submitted'] or 0,
            'verified': all_payment_stats['verified'] or 0,
            'rejected': all_payment_stats['rejected'] or 0,
            'total_amount': all_payment_stats['total_amount'] or 0,
        }

        # Per-method breakdown for verified payments
        method_breakdown = []
        try:
            from django.db.models.functions import Coalesce
            methods_qs = Payment.objects.filter(
                registration__tournament=tournament, status='verified'
            ).values('payment_method').annotate(
                method_count=Count('id'),
                method_total=Coalesce(Sum('amount'), 0),
            ).order_by('-method_total')
            method_breakdown = list(methods_qs)
        except Exception:
            pass
        
        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'payments',
            'payments': page_obj,
            'page_obj': page_obj,
            'payment_stats': payment_stats,
            'method_breakdown': method_breakdown,
            'can_approve': checker.can_approve_payments(),
        }
        context.update(self.get_common_context(tournament))
        
        return render(request, 'tournaments/manage/payments.html', context)
    
    def brackets_tab(self, request, tournament, checker):
        """Brackets tab: bracket management, seeding, and match list"""
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
        ).order_by('round_number', 'match_number')
        
        # Count pending results for badge notification
        pending_results_count = Match.objects.filter(
            tournament=tournament,
            state='pending_result',
            is_deleted=False
        ).count()

        # Build bracket_data for visualization
        from apps.tournaments.views.organizer_brackets import (
            _build_bracket_data, _seed_list_from_matches, _any_match_started,
            _get_confirmed_participants,
        )
        bracket_data = _build_bracket_data(tournament, bracket) if bracket else None

        # Seed list for drag-and-drop seeding panel
        seed_list = _seed_list_from_matches(tournament) if bracket else []

        # Confirmed participant count for generate gate
        confirmed_count = _get_confirmed_participants(tournament).count()

        # Lock state
        matches_started = _any_match_started(tournament)
        bracket_locked = matches_started or (bracket and bracket.is_finalized)

        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'brackets',
            'bracket': bracket,
            'bracket_data': bracket_data,
            'matches': matches,
            'seed_list': seed_list,
            'confirmed_count': confirmed_count,
            'matches_started': matches_started,
            'bracket_locked': bracket_locked,
            'pending_results_count': pending_results_count,
            'can_manage': checker.can_manage_brackets(),
            'can_manage_bracket': checker.can_manage_brackets(),
        }
        context.update(self.get_common_context(tournament))
        
        return render(request, 'tournaments/manage/brackets.html', context)
    
    def matches_tab(self, request, tournament, checker):
        """Matches tab: Match Medic — all match operations, scores, controls."""
        from apps.tournaments.models import Match

        matches_qs = Match.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).order_by('round_number', 'match_number')

        # Tab filter (state-based)
        status_filter = request.GET.get('status', '')
        state_map = {
            'active': ['live'],
            'upcoming': ['scheduled', 'check_in', 'ready'],
            'completed': ['completed', 'forfeit'],
            'paused': ['pending_result'],
        }
        if status_filter and status_filter in state_map:
            matches_qs = matches_qs.filter(state__in=state_map[status_filter])
        elif status_filter:
            matches_qs = matches_qs.filter(state=status_filter)

        # Stats (always unfiltered)
        all_matches = Match.objects.filter(tournament=tournament, is_deleted=False)
        total_matches = all_matches.count()
        active_matches = all_matches.filter(state='live').count()
        completed_matches = all_matches.filter(state__in=['completed', 'forfeit']).count()
        pending_matches = all_matches.filter(
            state__in=['scheduled', 'check_in', 'ready', 'pending_result']
        ).count()

        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'matches',
            'matches': matches_qs,
            'status_filter': status_filter,
            'total_matches': total_matches,
            'active_matches': active_matches,
            'completed_matches': completed_matches,
            'pending_matches': pending_matches,
            'can_manage': checker.can_manage_brackets(),
        }
        context.update(self.get_common_context(tournament))

        return render(request, 'tournaments/manage/matches.html', context)

    def schedule_tab(self, request, tournament, checker):
        """Schedule tab: tournament timeline, check-in windows, round scheduling."""
        from apps.tournaments.models import Match
        from datetime import timedelta
        from collections import OrderedDict

        # All matches (for round-by-round schedule)
        all_matches = Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).order_by('round_number', 'match_number')

        # Group matches by round
        rounds_dict = OrderedDict()
        for m in all_matches:
            rn = m.round_number
            if rn not in rounds_dict:
                rounds_dict[rn] = []
            rounds_dict[rn].append(m)

        rounds_data = []
        for rn, matches in rounds_dict.items():
            scheduled_count = sum(1 for m in matches if m.scheduled_time)
            completed_count = sum(1 for m in matches if m.state in ('completed', 'forfeit'))
            rounds_data.append({
                'round_number': rn,
                'matches': matches,
                'total': len(matches),
                'scheduled': scheduled_count,
                'completed': completed_count,
                'all_scheduled': scheduled_count == len(matches),
            })

        # Upcoming matches (not yet completed)
        upcoming_matches = all_matches.filter(
            state__in=['scheduled', 'check_in', 'ready', 'live']
        )[:20]

        # Check-in participants list (confirmed registrations)
        checkin_registrations = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
            status='confirmed',
        ).select_related('user').order_by('checked_in', 'created_at')

        # Check-in stats
        total_confirmed = checkin_registrations.count()
        checked_in_count = checkin_registrations.filter(checked_in=True).count()
        not_checked_in = total_confirmed - checked_in_count
        checkin_percentage = int((checked_in_count / total_confirmed) * 100) if total_confirmed else 0

        checkin_stats = {
            'total_confirmed': total_confirmed,
            'checked_in': checked_in_count,
            'not_checked_in': not_checked_in,
            'percentage': checkin_percentage,
        }

        # Check-in window status
        now = timezone.now()
        checkin_window = {
            'is_open': False,
            'opens_at': None,
            'closes_at': None,
            'can_open_early': False,
            'can_extend': False,
        }
        if tournament.enable_check_in and tournament.tournament_start:
            minutes_before = getattr(tournament, 'check_in_minutes_before', 30) or 30
            close_minutes = getattr(tournament, 'check_in_closes_minutes_before', 10) or 10
            opens_at = tournament.tournament_start - timedelta(minutes=minutes_before)
            closes_at = tournament.tournament_start - timedelta(minutes=close_minutes)
            checkin_window['opens_at'] = opens_at
            checkin_window['closes_at'] = closes_at
            checkin_window['is_open'] = opens_at <= now < closes_at
            checkin_window['can_open_early'] = now < opens_at
            checkin_window['can_extend'] = now >= closes_at and now < tournament.tournament_start

        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'schedule',
            'rounds_data': rounds_data,
            'upcoming_matches': upcoming_matches,
            'checkin_stats': checkin_stats,
            'checkin_registrations': checkin_registrations,
            'checkin_window': checkin_window,
        }
        context.update(self.get_common_context(tournament))

        return render(request, 'tournaments/manage/schedule.html', context)

    def disputes_tab(self, request, tournament, checker):
        """Disputes tab: dispute handling"""
        if not checker.has_any(['resolve_disputes', 'view_all']):
            messages.error(request, "You don't have permission to view disputes.")
            return redirect('tournaments:organizer_hub', slug=tournament.slug, tab='overview')
        
        # Get filter parameters
        status_filter = request.GET.get('status', '')
        
        # Base queryset
        all_disputes = Dispute.objects.filter(
            match__tournament=tournament
        ).select_related('match')
        
        # Calculate stats
        open_count = all_disputes.filter(status='open').count()
        under_review_count = all_disputes.filter(status='under_review').count()
        resolved_count = all_disputes.filter(status='resolved').count()
        total_count = all_disputes.count()
        
        # Apply filters for display
        disputes = all_disputes
        if status_filter:
            disputes = disputes.filter(status=status_filter)
        
        disputes = disputes.order_by('-created_at')
        
        context = {
            'tournament': tournament,
            'checker': checker,
            'active_tab': 'disputes',
            'disputes': disputes,
            'open_count': open_count,
            'under_review_count': under_review_count,
            'resolved_count': resolved_count,
            'total_count': total_count,
            'can_resolve': checker.can_resolve_disputes(),
        }
        context.update(self.get_common_context(tournament))
        
        return render(request, 'tournaments/manage/disputes.html', context)
    
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
        context.update(self.get_common_context(tournament))
        
        return render(request, 'tournaments/manage/announcements.html', context)
    
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
        context.update(self.get_common_context(tournament))
        
        return render(request, 'tournaments/manage/settings.html', context)


# ============================================================================
# Tournament Creation
# ============================================================================


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
            # Check if we need to redirect to form builder
            if form.cleaned_data.get('redirect_to_form_builder'):
                # Save tournament first
                tournament = form.save(commit=False)
                tournament.organizer = request.user
                tournament.status = 'draft'
                tournament.save()
                
                messages.info(request, f'Tournament "{tournament.name}" created! Now let\'s build your custom registration form.')
                return redirect('tournaments:form_builder', slug=tournament.slug)
            
            # Normal save with form configuration
            tournament = form.save(commit=False)
            tournament.organizer = request.user
            tournament.status = 'draft'  # Start as draft
            tournament.save()
            
            # Form configuration is created in form.save()
            
            messages.success(request, f'Tournament "{tournament.name}" created successfully!')
            return redirect('tournaments:organizer_tournament_detail', slug=tournament.slug)
    else:
        form = TournamentCreateForm()
    
    return render(request, 'tournaments/organizer/create_tournament.html', {
        'form': form,
        'page_title': 'Create New Tournament',
    })


# FBVs extracted to:
# - organizer_participants.py  (FE-T-022: approve, reject, toggle, bulk, disqualify, export)
# - organizer_payments.py      (FE-T-023: verify, reject, bulk, refund, export, history)
# - organizer_matches.py       (FE-T-024: submit_score, reschedule, forfeit, override, cancel)
