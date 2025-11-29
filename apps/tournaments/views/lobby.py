"""
Tournament Lobby Views - FE-T-007

Implements:
- FE-T-007: Tournament Lobby / Participant Hub

Sprint Implementation - November 20, 2025
Source: FRONTEND_TOURNAMENT_BACKLOG.md Section 2.1
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError

from apps.tournaments.models import Tournament, TournamentLobby, CheckIn
from apps.tournaments.services.lobby_service import LobbyService


class TournamentLobbyView(LoginRequiredMixin, View):
    """
    FE-T-007: Tournament Lobby / Participant Hub
    
    Central hub for registered participants before tournament starts.
    Shows:
    - Check-in countdown and button
    - Participant roster with check-in status
    - Organizer announcements
    - Tournament info (rules, brackets, prizes)
    """
    
    template_name = 'tournaments/lobby/hub.html'
    
    def get(self, request, slug):
        """Render lobby page."""
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Check if user is registered (allow pending, payment_submitted, confirmed)
        from apps.tournaments.models import Registration
        registration = Registration.objects.filter(
            user=request.user,
            tournament=tournament,
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
            return redirect('tournaments:detail', slug=slug)
        
        # Get or create lobby
        if not hasattr(tournament, 'lobby'):
            messages.info(request, "Tournament lobby is not yet available")
            return redirect('tournaments:detail', slug=slug)
        
        lobby = tournament.lobby
        
        # Get user's check-in status
        check_in = CheckIn.objects.filter(
            tournament=tournament,
            user=request.user,
            is_deleted=False
        ).first()
        
        # Get roster
        roster_data = LobbyService.get_roster(tournament.id)
        
        # Get announcements
        announcements = LobbyService.get_announcements(tournament.id)
        
        context = {
            'tournament': tournament,
            'lobby': lobby,
            'registration': registration,  # Pass registration for status display
            'check_in': check_in,
            'roster_data': roster_data,
            'announcements': announcements,
            'is_check_in_open': lobby.is_check_in_open,
            'check_in_status': lobby.check_in_status,
            'check_in_countdown': lobby.check_in_countdown_seconds,
        }
        
        return render(request, self.template_name, context)


class CheckInView(LoginRequiredMixin, View):
    """
    Check-in action endpoint.
    
    POST endpoint to perform check-in.
    """
    
    def post(self, request, slug):
        """Perform check-in."""
        tournament = get_object_or_404(Tournament, slug=slug)
        
        try:
            # Get team_id if team tournament
            team_id = None
            if tournament.participation_type == 'team':
                # Find user's team registration
                registration = tournament.registrations.filter(
                    team__memberships__user=request.user,
                    status='confirmed',
                    is_deleted=False
                ).first()
                
                if registration and registration.team:
                    team_id = registration.team.id
            
            # Perform check-in
            check_in = LobbyService.perform_check_in(
                tournament_id=tournament.id,
                user_id=request.user.id,
                team_id=team_id
            )
            
            messages.success(request, "✓ Check-in successful! You're all set for the tournament.")
            
            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Check-in successful',
                    'checked_in_at': check_in.checked_in_at.isoformat() if check_in.checked_in_at else None
                })
            
            return redirect('tournaments:lobby', slug=slug)
        
        except ValidationError as e:
            messages.error(request, str(e))
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            
            return redirect('tournaments:lobby', slug=slug)
        except Exception as e:
            messages.error(request, f"Check-in failed: {str(e)}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
            
            return redirect('tournaments:lobby', slug=slug)


class LobbyRosterAPIView(LoginRequiredMixin, View):
    """
    API endpoint to get current roster with check-in status.
    
    Used for real-time updates via HTMX/AJAX polling.
    """
    
    def get(self, request, slug):
        """Get roster data as JSON."""
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Check if user is registered
        is_registered = tournament.registrations.filter(
            user=request.user,
            status='confirmed',
            is_deleted=False
        ).exists()
        
        if not is_registered:
            return JsonResponse({'error': 'Not registered'}, status=403)
        
        try:
            roster_data = LobbyService.get_roster(tournament.id)
            return JsonResponse(roster_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class LobbyAnnouncementsAPIView(LoginRequiredMixin, View):
    """
    API endpoint to get lobby announcements.
    
    Used for real-time updates via HTMX/AJAX polling.
    """
    
    def get(self, request, slug):
        """Get announcements as JSON."""
        tournament = get_object_or_404(Tournament, slug=slug)
        
        # Check if user is registered
        is_registered = tournament.registrations.filter(
            user=request.user,
            status='confirmed',
            is_deleted=False
        ).exists()
        
        if not is_registered:
            return JsonResponse({'error': 'Not registered'}, status=403)
        
        try:
            announcements = LobbyService.get_announcements(tournament.id)
            
            # Serialize announcements
            announcements_data = []
            for announcement in announcements:
                announcements_data.append({
                    'id': announcement.id,
                    'title': announcement.title,
                    'message': announcement.message,
                    'type': announcement.announcement_type,
                    'is_pinned': announcement.is_pinned,
                    'posted_by': announcement.posted_by.username if announcement.posted_by else 'Organizer',
                    'created_at': announcement.created_at.isoformat(),
                })
            
            return JsonResponse({'announcements': announcements_data})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
