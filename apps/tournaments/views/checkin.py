"""
Sprint 5: Tournament Check-In Views

FE-T-007: Tournament Lobby / Participant Hub
Handles check-in actions and lobby page rendering for registered participants.
"""

from django.views.generic import DetailView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, F, Prefetch

from apps.tournaments.models import Tournament, Registration, Match
from apps.tournaments.services.check_in_service import CheckInService


class TournamentLobbyView(LoginRequiredMixin, DetailView):
    """
    FE-T-007: Tournament Lobby / Participant Hub
    
    Central hub for registered participants before tournament starts.
    Displays check-in widget, roster, schedule, and announcements.
    
    Access: Registered participants only (redirects non-participants to detail page)
    
    URL: /tournaments/<slug>/lobby/
    Template: tournaments/lobby/hub.html
    Context:
        - tournament: Tournament object
        - registration: User's registration
        - check_in_window: Dict with opens_at, closes_at, is_open
        - roster: List of all participants with check-in status
        - announcements: Organizer announcements (future)
        - next_match: User's next scheduled match (if bracket generated)
    """
    model = Tournament
    template_name = 'tournaments/lobby/hub.html'
    context_object_name = 'tournament'
    login_url = '/accounts/login/'
    
    def get_queryset(self):
        """Optimize queries with select_related."""
        return Tournament.objects.filter(
            is_deleted=False
        ).select_related(
            'game',
            'organizer'
        )
    
    def dispatch(self, request, *args, **kwargs):
        """Check participant access before rendering."""
        tournament = self.get_object()
        
        # Check if user is registered participant
        # Allow access for pending, payment_submitted, and confirmed registrations
        from apps.teams.models import TeamMembership
        
        # First check for individual registration
        registration = Registration.objects.filter(
            tournament=tournament,
            user=request.user,
            is_deleted=False,
            status__in=[
                Registration.PENDING,
                Registration.PAYMENT_SUBMITTED,
                Registration.CONFIRMED
            ]
        ).first()
        
        # If no individual registration, check if user is in a registered team
        if not registration:
            # Get team IDs where user is an active member
            user_team_ids = TeamMembership.objects.filter(
                profile__user=request.user,
                status=TeamMembership.Status.ACTIVE
            ).values_list('team_id', flat=True)
            
            # Check if any of those teams have a registration for this tournament
            registration = Registration.objects.filter(
                tournament=tournament,
                team_id__in=user_team_ids,
                is_deleted=False,
                status__in=[
                    Registration.PENDING,
                    Registration.PAYMENT_SUBMITTED,
                    Registration.CONFIRMED
                ]
            ).first()
        
        if not registration:
            messages.warning(
                request,
                "You must be registered for this tournament to access the lobby. "
                "Please complete your registration first."
            )
            return redirect('tournaments:detail', slug=tournament.slug)
        
        # Store registration for later use
        self.registration = registration
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add lobby-specific context."""
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Add registration
        context['registration'] = self.registration
        
        # Check-in window info
        context['check_in_window'] = {
            'opens_at': CheckInService.get_check_in_opens_at(tournament),
            'closes_at': CheckInService.get_check_in_closes_at(tournament),
            'is_open': CheckInService.is_check_in_window_open(tournament),
            'can_check_in': CheckInService.can_check_in(tournament, self.request.user),
        }
        
        # Roster with check-in status (all participants)
        context['roster'] = self._get_roster(tournament)
        
        # Check-in stats
        total_participants = context['roster'].count()
        checked_in_count = context['roster'].filter(
            checked_in=True
        ).count()
        context['check_in_stats'] = {
            'total': total_participants,
            'checked_in': checked_in_count,
            'pending': total_participants - checked_in_count,
        }
        
        # Next match (if bracket generated)
        context['next_match'] = self._get_next_match(tournament, self.request.user)
        
        # Announcements (placeholder for future implementation)
        context['announcements'] = []
        
        return context
    
    def _get_roster(self, tournament):
        """
        Get all registered participants with check-in status.
        
        Returns QuerySet of Registration objects with related user/team.
        """
        return Registration.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).select_related(
            'user',
            'user__userprofile',
            'team'
        ).order_by(
            # Checked-in participants first, then by registration date
            '-checked_in',
            'created_at'
        )
    
    def _get_next_match(self, tournament, user):
        """
        Get user's next scheduled match (if bracket generated).
        
        Returns Match object or None.
        """
        try:
            bracket = tournament.bracket
        except Tournament.bracket.RelatedObjectDoesNotExist:
            return None
        
        # Find user's registration
        try:
            registration = Registration.objects.get(
                tournament=tournament,
                user=user,
                is_deleted=False
            )
        except Registration.DoesNotExist:
            return None
        
        # Find next match where user is participant
        next_match = Match.objects.filter(
            tournament=tournament,
            state__in=['scheduled', 'ready'],
            is_deleted=False
        ).filter(
            Q(participant1_id=registration.id) | Q(participant2_id=registration.id)
        ).select_related(
            'participant1__user',
            'participant1__team',
            'participant2__user',
            'participant2__team'
        ).order_by('scheduled_time').first()
        
        return next_match


class CheckInActionView(LoginRequiredMixin, View):
    """
    Check-in action endpoint.
    
    Handles POST requests to check in a participant.
    Returns JSON response for HTMX or redirect for traditional forms.
    
    URL: /tournaments/<slug>/check-in/
    Method: POST
    Body: { confirm: true }
    Response: JSON { success: bool, message: str, checked_in_at: str }
    """
    login_url = '/accounts/login/'
    
    def post(self, request, slug):
        """Handle check-in action."""
        tournament = get_object_or_404(
            Tournament,
            slug=slug,
            is_deleted=False
        )
        
        # Validate check-in eligibility
        can_check_in = CheckInService.can_check_in(tournament, request.user)
        
        if not can_check_in:
            error_message = self._get_error_message(tournament, request.user)
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': False,
                    'message': error_message
                }, status=403)
            else:
                messages.error(request, error_message)
                return redirect('tournaments:lobby', slug=slug)
        
        # Perform check-in
        try:
            registration = CheckInService.check_in(tournament, request.user)
            
            success_message = f"You're checked in! See you at {tournament.tournament_start.strftime('%b %d, %H:%M')}."
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'checked_in_at': registration.checked_in_at.isoformat() if registration.checked_in_at else None
                })
            else:
                messages.success(request, success_message)
                return redirect('tournaments:lobby', slug=slug)
        
        except ValidationError as e:
            error_message = str(e)
            
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': False,
                    'message': error_message
                }, status=400)
            else:
                messages.error(request, error_message)
                return redirect('tournaments:lobby', slug=slug)
    
    def _get_error_message(self, tournament, user):
        """Get appropriate error message based on check-in validation failure."""
        # Check if registered
        try:
            registration = Registration.objects.get(
                tournament=tournament,
                user=user,
                is_deleted=False
            )
        except Registration.DoesNotExist:
            return "You must be registered to check in."
        
        # Check if already checked in
        if registration.checked_in:
            return "You're already checked in!"
        
        # Check if check-in window is open
        if not CheckInService.is_check_in_window_open(tournament):
            opens_at = CheckInService.get_check_in_opens_at(tournament)
            closes_at = CheckInService.get_check_in_closes_at(tournament)
            now = timezone.now()
            
            if now < opens_at:
                return f"Check-in opens at {opens_at.strftime('%b %d, %H:%M')}."
            elif now >= closes_at:
                return "Check-in window has closed."
        
        return "You cannot check in at this time."


class CheckInStatusView(LoginRequiredMixin, View):
    """
    HTMX endpoint for polling check-in status.
    
    Returns partial HTML with updated check-in widget.
    
    URL: /tournaments/<slug>/check-in-status/
    Method: GET
    Response: HTML fragment (check-in widget)
    """
    login_url = '/accounts/login/'
    
    def get(self, request, slug):
        """Return updated check-in widget HTML."""
        from django.template.loader import render_to_string
        
        tournament = get_object_or_404(
            Tournament,
            slug=slug,
            is_deleted=False
        )
        
        # Get user's registration
        try:
            registration = Registration.objects.get(
                tournament=tournament,
                user=request.user,
                is_deleted=False
            )
        except Registration.DoesNotExist:
            return HttpResponseForbidden("Not registered")
        
        # Check-in window info
        check_in_window = {
            'opens_at': CheckInService.get_check_in_opens_at(tournament),
            'closes_at': CheckInService.get_check_in_closes_at(tournament),
            'is_open': CheckInService.is_check_in_window_open(tournament),
            'can_check_in': CheckInService.can_check_in(tournament, request.user),
        }
        
        # Render partial
        html = render_to_string(
            'tournaments/lobby/_checkin.html',
            {
                'tournament': tournament,
                'registration': registration,
                'check_in_window': check_in_window,
            },
            request=request
        )
        
        return JsonResponse({'html': html}) if request.headers.get('HX-Request') else JsonResponse({'html': html})


class RosterView(View):
    """
    Public roster endpoint (no auth required).
    
    Returns list of all participants with check-in status.
    Can be used by spectators to see roster.
    
    URL: /tournaments/<slug>/roster/
    Method: GET
    Response: HTML fragment (roster list) or JSON
    """
    
    def get(self, request, slug):
        """Return roster with check-in status."""
        from django.template.loader import render_to_string
        
        tournament = get_object_or_404(
            Tournament,
            slug=slug,
            is_deleted=False
        )
        
        # Get roster
        roster = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).select_related(
            'user',
            'user__userprofile',
            'team'
        ).order_by(
            '-checked_in',
            'created_at'
        )
        
        # Check if user is participant (for highlighting)
        user_registration_id = None
        if request.user.is_authenticated:
            try:
                user_reg = roster.get(user=request.user)
                user_registration_id = user_reg.id
            except Registration.DoesNotExist:
                pass
        
        # Return JSON if requested
        if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
            roster_data = [
                {
                    'id': reg.id,
                    'name': reg.team.name if reg.team else reg.user.username,
                    'avatar': reg.user.userprofile.avatar.url if reg.user and hasattr(reg.user, 'userprofile') and reg.user.userprofile.avatar else None,
                    'check_in_status': reg.checked_in,
                    'checked_in_at': reg.checked_in_at.isoformat() if reg.checked_in_at else None,
                    'is_current_user': reg.id == user_registration_id,
                }
                for reg in roster
            ]
            return JsonResponse({'roster': roster_data})
        
        # Return HTML fragment for HTMX
        html = render_to_string(
            'tournaments/lobby/_roster.html',
            {
                'tournament': tournament,
                'roster': roster,
                'user_registration_id': user_registration_id,
            },
            request=request
        )
        
        return JsonResponse({'html': html}) if request.headers.get('HX-Request') else JsonResponse({'html': html})
