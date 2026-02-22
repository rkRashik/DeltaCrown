"""
Sprint 5: Tournament Check-In Views

FE-T-007: Tournament Lobby / Participant Hub
Handles check-in actions for registered participants.

Note: The lobby page (TournamentLobbyView) now redirects to The Hub (v3).
The Sprint 10 lobby views (lobby.py) and the old lobby template have been removed.
"""

from django.views import View
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ValidationError

from apps.tournaments.models import Tournament, Registration
from apps.tournaments.services.check_in_service import CheckInService


class TournamentLobbyView(LoginRequiredMixin, View):
    """
    Legacy /lobby/ URL — redirects to The Hub (v3).

    Kept for backward-compatibility so bookmarks and external links
    continue to work.
    """
    login_url = '/accounts/login/'

    def get(self, request, slug):
        return redirect('tournaments:tournament_hub', slug=slug)


class CheckInActionView(LoginRequiredMixin, View):
    """
    Check-in action endpoint.

    Handles POST requests to check in a participant.
    Returns JSON response for HTMX or redirect for traditional forms.

    URL: /tournaments/<slug>/check-in/
    Method: POST
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
                return redirect('tournaments:tournament_hub', slug=slug)

        # Perform check-in
        try:
            registration = CheckInService.check_in(tournament, request.user)

            if tournament.tournament_start:
                success_message = f"You're checked in! See you at {tournament.tournament_start.strftime('%b %d, %H:%M')}."
            else:
                success_message = "You're checked in!"

            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'checked_in_at': registration.checked_in_at.isoformat() if registration.checked_in_at else None
                })
            else:
                messages.success(request, success_message)
                return redirect('tournaments:tournament_hub', slug=slug)

        except (ValidationError, Exception) as e:
            error_message = str(e)

            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': False,
                    'message': error_message
                }, status=400)
            else:
                messages.error(request, error_message)
                return redirect('tournaments:tournament_hub', slug=slug)

    def _get_error_message(self, tournament, user):
        """Get appropriate error message based on check-in validation failure."""
        try:
            registration = Registration.objects.get(
                tournament=tournament,
                user=user,
                is_deleted=False
            )
        except Registration.DoesNotExist:
            return "You must be registered to check in."

        if registration.checked_in:
            return "You're already checked in!"

        if not CheckInService.is_check_in_window_open(tournament):
            opens_at = CheckInService.get_check_in_opens_at(tournament)
            closes_at = CheckInService.get_check_in_closes_at(tournament)
            now = timezone.now()

            if now < opens_at:
                return f"Check-in opens at {opens_at.strftime('%b %d, %H:%M')}."
            elif now >= closes_at:
                return "Check-in window has closed."

        return "You cannot check in at this time."
