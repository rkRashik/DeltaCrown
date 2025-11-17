# FE-T-001: Tournament List Page
# Purpose: Public-facing tournament discovery and listing page with filters
# Source: Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md (Section 1.1)
# Source: Documents/ExecutionPlan/FrontEnd/Screens/FRONTEND_TOURNAMENT_SITEMAP.md (Section 1.1)

"""
Tournament Frontend Views (Main)

These views serve the tournament-focused frontend pages using Django templates.
All views integrate with existing backend APIs from apps/tournaments/api/

Sprint 1 Implementation (November 15, 2025):
- FE-T-001: Tournament List/Discovery Page
- FE-T-002: Tournament Detail Page  
- FE-T-003: Registration CTA States (integrated in detail view)
"""

from django.views.generic import ListView, DetailView
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from apps.tournaments.models import Tournament, TournamentAnnouncement
from apps.tournaments.services.registration_service import RegistrationService
from django.core.exceptions import ValidationError
import requests


class TournamentListView(ListView):
    """
    FE-T-001: Tournament List/Discovery Page
    
    URL: /tournaments/
    Template: templates/tournaments/browse/list.html
    
    Features:
    - Tournament cards with key info (game, format, prize, date, slots)
    - Filters: Game, Status (upcoming, registration open, live, completed)
    - Search by tournament name
    - Pagination
    - Responsive design (mobile-first)
    
    Backend API: GET /api/tournaments/tournament-discovery/ (discovery_views.py)
    """
    template_name = 'tournaments/public/browse/list.html'
    context_object_name = 'tournament_list'
    paginate_by = 20
    
    def get_queryset(self):
        """
        Filter tournaments matching the discovery API parameters.
        Parameters mirror GET /api/tournaments/tournament-discovery/ (discovery_views.py)
        
        Supported filters (from planning docs):
        - game: Game slug or name filter (game is ForeignKey to Game model)
        - status: published, registration_open, live, completed
        - search: Full-text search on name, description
        - format: Tournament format filter
        - free_only: Boolean for free tournaments
        """
        # Optimize query with select_related for ForeignKey fields
        queryset = Tournament.objects.select_related('game', 'organizer').filter(
            status__in=['published', 'registration_open', 'live', 'completed']
        ).order_by('-tournament_start')
        
        # Filter by game (match API param: ?game=<slug>)
        # Tournament.game is ForeignKey to Game model
        game_filter = self.request.GET.get('game')
        if game_filter:
            queryset = queryset.filter(game__slug=game_filter)
        
        # Filter by status (match API param: ?status=<status>)
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by format (match API param: ?format=<format>)
        format_filter = self.request.GET.get('format')
        if format_filter:
            queryset = queryset.filter(format=format_filter)  # NOTE: Model field is 'format' not 'tournament_format'
        
        # Search by name/description (match API param: ?search=<query>)
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # Free tournaments only (match API param: ?free_only=true)
        free_only = self.request.GET.get('free_only')
        if free_only and free_only.lower() in ['true', '1', 'yes']:
            queryset = queryset.filter(Q(entry_fee__isnull=True) | Q(entry_fee=0))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add games for filter dropdown (from planning docs: Game dropdown filter)
        # Query all active games from Game model and convert to list
        from apps.tournaments.models import Game
        context['games'] = list(Game.objects.filter(is_active=True).values('slug', 'name'))
        
        # Add current filter values (all parameters must be URL-synced)
        context['current_game'] = self.request.GET.get('game', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_search'] = self.request.GET.get('search', '')
        context['current_format'] = self.request.GET.get('format', '')
        context['current_free_only'] = self.request.GET.get('free_only', '')
        
        # Status options for filter tabs (from Sitemap Section 1.1)
        context['status_options'] = [
            {'value': '', 'label': 'All'},
            {'value': 'registration_open', 'label': 'Registration Open'},
            {'value': 'live', 'label': 'Live'},
            {'value': 'published', 'label': 'Upcoming'},
            {'value': 'completed', 'label': 'Completed'},
        ]
        
        # Format options for additional filtering
        context['format_options'] = [
            {'value': '', 'label': 'All Formats'},
            {'value': 'single_elimination', 'label': 'Single Elimination'},
            {'value': 'double_elimination', 'label': 'Double Elimination'},
            {'value': 'round_robin', 'label': 'Round Robin'},
            {'value': 'swiss', 'label': 'Swiss'},
        ]
        
        return context


class TournamentDetailView(DetailView):
    """
    FE-T-002: Tournament Detail Page
    
    URL: /tournaments/<slug>/
    Template: templates/tournaments/detail/overview.html
    
    Features:
    - Hero section with banner, game badge, status
    - Key info bar (format, date, prize, slots)
    - Tabs: Overview, Schedule, Prizes, Rules/FAQ
    - Registration CTA with dynamic states (FE-T-003)
    - Adapts based on tournament state (before/during/after)
    
    Backend APIs:
    - GET /api/tournaments/<id>/ (tournament_views.py)
    - GET /api/tournaments/registrations/status/ (registrations.py)
    """
    model = Tournament
    template_name = 'tournaments/public/detail/overview.html'
    context_object_name = 'tournament'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        user = self.request.user
        
        # FE-T-003: Registration CTA state logic with backend eligibility checks (Enhanced Sprint 5)
        # Source: FRONTEND_TOURNAMENT_BACKLOG.md Section 1.3 + 1.4
        # Sprint 5 Enhancement: Add payment, approval, check-in validation states
        # States: login_required, open, closed, full, registered, payment_pending, approval_pending, 
        #         check_in_required, checked_in, upcoming, not_eligible, no_team_permission
        
        # Default state: Login required (for non-authenticated users)
        context['cta_state'] = 'login_required'
        context['cta_label'] = 'Login to Register'
        context['cta_disabled'] = False
        context['cta_reason'] = 'You must be logged in to register'
        context['is_registered'] = False
        context['can_register'] = False
        context['registration_status'] = None
        
        # Calculate slots info (always visible)
        from apps.tournaments.models import Registration
        slots_filled = Registration.objects.filter(
            tournament=tournament,
            status__in=[Registration.PENDING, Registration.PAYMENT_SUBMITTED, Registration.CONFIRMED],
            is_deleted=False
        ).count()
        context['slots_filled'] = slots_filled
        context['slots_total'] = tournament.max_participants
        context['slots_percentage'] = (slots_filled / tournament.max_participants * 100) if tournament.max_participants > 0 else 0
        
        if user.is_authenticated:
            # Check if user is already registered
            try:
                is_registered = Registration.objects.filter(
                    tournament=tournament,
                    user=user,
                    is_deleted=False
                ).exclude(
                    status__in=[Registration.CANCELLED, Registration.REJECTED]
                ).exists()
                context['is_registered'] = is_registered
                
                if is_registered:
                    # Sprint 5: Enhanced validation states for registered users
                    registration_status = self._get_registration_status(tournament, user)
                    context['registration_status'] = registration_status
                    
                    # Determine CTA state based on registration sub-state
                    if registration_status['state'] == 'payment_pending':
                        context['cta_state'] = 'payment_pending'
                        context['cta_label'] = 'Payment Required'
                        context['cta_disabled'] = False
                        context['cta_reason'] = registration_status['reason']
                    elif registration_status['state'] == 'approval_pending':
                        context['cta_state'] = 'approval_pending'
                        context['cta_label'] = 'Awaiting Approval'
                        context['cta_disabled'] = True
                        context['cta_reason'] = registration_status['reason']
                    elif registration_status['state'] == 'check_in_required':
                        context['cta_state'] = 'check_in_required'
                        context['cta_label'] = 'Check-In Required'
                        context['cta_disabled'] = False
                        context['cta_reason'] = registration_status['reason']
                    elif registration_status['state'] == 'checked_in':
                        context['cta_state'] = 'checked_in'
                        context['cta_label'] = "You're Checked In ✓"
                        context['cta_disabled'] = True
                        context['cta_reason'] = 'You are checked in and ready for the tournament'
                    else:
                        # Default registered state (payment confirmed, approved, no check-in yet)
                        context['cta_state'] = 'registered'
                        context['cta_label'] = "You're Registered"
                        context['cta_disabled'] = False
                        context['cta_reason'] = 'You have successfully registered for this tournament'
                    context['can_register'] = False
                else:
                    # Use RegistrationService to check eligibility
                    # This handles: capacity, registration window, participation type, team permissions
                    try:
                        RegistrationService.check_eligibility(
                            tournament=tournament,
                            user=user,
                            team_id=None  # TODO: Get selected team from session/form state
                        )
                        # Eligibility check passed - user can register
                        context['cta_state'] = 'open'
                        context['cta_label'] = 'Register Now'
                        context['cta_disabled'] = False
                        context['cta_reason'] = 'Registration is open'
                        context['can_register'] = True
                        
                    except ValidationError as e:
                        # Eligibility check failed - determine specific reason
                        error_message = str(e.message) if hasattr(e, 'message') else str(e)
                        context['cta_reason'] = error_message
                        context['can_register'] = False
                        
                        # Map backend errors to specific CTA states
                        if 'full' in error_message.lower():
                            context['cta_state'] = 'full'
                            context['cta_label'] = 'Tournament Full'
                            context['cta_disabled'] = True
                        elif 'closed' in error_message.lower() or 'ended' in error_message.lower():
                            context['cta_state'] = 'closed'
                            context['cta_label'] = 'Registration Closed'
                            context['cta_disabled'] = True
                        elif 'not started' in error_message.lower() or 'not open' in error_message.lower():
                            context['cta_state'] = 'upcoming'
                            context['cta_label'] = 'Coming Soon'
                            context['cta_disabled'] = True
                        elif 'permission' in error_message.lower():
                            context['cta_state'] = 'no_team_permission'
                            context['cta_label'] = 'No Permission'
                            context['cta_disabled'] = True
                        elif 'requires team' in error_message.lower():
                            context['cta_state'] = 'not_eligible'
                            context['cta_label'] = 'Team Required'
                            context['cta_disabled'] = True
                        elif 'solo participants' in error_message.lower():
                            context['cta_state'] = 'not_eligible'
                            context['cta_label'] = 'Solo Only'
                            context['cta_disabled'] = True
                        else:
                            # Generic not eligible state
                            context['cta_state'] = 'not_eligible'
                            context['cta_label'] = 'Not Eligible'
                            context['cta_disabled'] = True
            
            except Exception as e:
                # Fallback for unexpected errors
                context['cta_state'] = 'closed'
                context['cta_label'] = 'Registration Closed'
                context['cta_disabled'] = True
                context['cta_reason'] = 'Unable to check registration status'
                context['can_register'] = False
        
        # Add announcements for this tournament
        announcements = TournamentAnnouncement.objects.filter(
            tournament=tournament
        ).select_related('created_by').order_by('-is_pinned', '-created_at')[:10]
        context['announcements'] = announcements
        
        return context
    
    def _get_registration_status(self, tournament, user):
        """
        Sprint 5 Helper: Get detailed registration validation status
        
        Returns dict with:
        - state: str (payment_pending, approval_pending, check_in_required, checked_in, confirmed)
        - reason: str (human-readable message)
        - check_in_window: dict (if applicable)
        - payment_status: str (if applicable)
        - approval_status: bool (if applicable)
        """
        from apps.tournaments.models import Registration
        from apps.tournaments.services.check_in_service import CheckInService
        
        try:
            registration = Registration.objects.get(
                tournament=tournament,
                user=user,
                is_deleted=False
            )
        except Registration.DoesNotExist:
            return {'state': 'not_registered', 'reason': 'Not registered'}
        
        # Check 1: Payment status (if tournament has entry fee)
        if hasattr(tournament, 'has_entry_fee') and tournament.has_entry_fee:
            if hasattr(registration, 'payment_status'):
                if registration.payment_status == Registration.PAYMENT_PENDING:
                    return {
                        'state': 'payment_pending',
                        'reason': f'Payment required: ${tournament.entry_fee}. Please submit payment proof.',
                        'payment_status': 'pending',
                    }
                elif registration.payment_status == Registration.PAYMENT_SUBMITTED:
                    return {
                        'state': 'approval_pending',
                        'reason': 'Payment submitted. Waiting for organizer approval.',
                        'payment_status': 'submitted',
                    }
        
        # Check 2: Approval status (if tournament requires approval)
        if hasattr(tournament, 'requires_approval') and tournament.requires_approval:
            if hasattr(registration, 'status'):
                if registration.status == Registration.PENDING:
                    return {
                        'state': 'approval_pending',
                        'reason': 'Your registration is awaiting organizer approval.',
                        'approval_status': 'pending',
                    }
        
        # Check 3: Check-in status (if check-in window open or closed)
        if hasattr(registration, 'check_in_status'):
            check_in_window = {
                'opens_at': CheckInService.get_check_in_opens_at(tournament),
                'closes_at': CheckInService.get_check_in_closes_at(tournament),
                'is_open': CheckInService.is_check_in_window_open(tournament),
            }
            
            now = timezone.now()
            
            # Already checked in
            if registration.check_in_status == 'checked_in':
                return {
                    'state': 'checked_in',
                    'reason': f'Checked in at {registration.checked_in_at.strftime("%b %d, %H:%M")}',
                    'check_in_window': check_in_window,
                }
            
            # Check-in window is open, but not checked in yet
            if check_in_window['is_open']:
                return {
                    'state': 'check_in_required',
                    'reason': f'Check-in required before {check_in_window["closes_at"].strftime("%b %d, %H:%M")}',
                    'check_in_window': check_in_window,
                }
            
            # Check-in window not yet open (but tournament soon)
            if now < check_in_window['opens_at']:
                return {
                    'state': 'confirmed',
                    'reason': f'Registration confirmed. Check-in opens {check_in_window["opens_at"].strftime("%b %d, %H:%M")}',
                    'check_in_window': check_in_window,
                }
        
        # Default: Confirmed registration (no pending actions)
        return {
            'state': 'confirmed',
            'reason': 'Registration confirmed',
        }


# ============================================================================
# Participant Check-in
# ============================================================================

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

@login_required
@require_POST
def participant_checkin(request, slug):
    """
    Allow participant to check themselves in during check-in window
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get user's registration
    from apps.tournaments.models import Registration
    try:
        registration = Registration.objects.get(
            tournament=tournament,
            user=request.user,
            is_deleted=False
        )
    except Registration.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Registration not found'}, status=404)
    
    # Check if registration is confirmed
    if registration.status != 'confirmed':
        return JsonResponse({'success': False, 'error': 'Registration must be confirmed before check-in'}, status=400)
    
    # Check if already checked in
    if registration.checked_in:
        return JsonResponse({'success': False, 'error': 'Already checked in'}, status=400)
    
    # Check if check-in window is open
    if tournament.enable_check_in:
        now = timezone.now()
        check_in_opens = tournament.tournament_start - timezone.timedelta(minutes=tournament.check_in_minutes_before or 60)
        check_in_closes = tournament.tournament_start - timezone.timedelta(minutes=tournament.check_in_closes_minutes_before or 0)
        
        if now < check_in_opens:
            return JsonResponse({
                'success': False, 
                'error': f'Check-in opens at {check_in_opens.strftime("%b %d, %H:%M")}'
            }, status=400)
        
        if now > check_in_closes:
            return JsonResponse({
                'success': False, 
                'error': 'Check-in window has closed'
            }, status=400)
    
    # Perform check-in
    registration.checked_in = True
    registration.checked_in_at = timezone.now()
    registration.checked_in_by = request.user  # Self check-in
    registration.save()
    
    return JsonResponse({
        'success': True, 
        'message': 'Successfully checked in!',
        'checked_in_at': registration.checked_in_at.isoformat()
    })
