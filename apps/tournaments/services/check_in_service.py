"""
Sprint 5: Check-In Service

Business logic for tournament check-in operations.
Validates check-in eligibility and manages check-in state transitions.
"""

from datetime import timedelta
from typing import Optional
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.tournaments.models import Tournament, Registration


class CheckInService:
    """
    Service class for tournament check-in business logic.
    
    Handles:
    - Check-in window validation
    - Check-in action processing
    - Roster retrieval with check-in status
    - No-show disqualification (scheduled task)
    """
    
    @staticmethod
    def get_check_in_opens_at(tournament: Tournament):
        """
        Calculate when check-in window opens for a tournament.
        
        Args:
            tournament: Tournament instance
        
        Returns:
            datetime: Check-in opens at timestamp
        """
        minutes_before = getattr(tournament, 'check_in_minutes_before', 60)
        return tournament.tournament_start - timedelta(minutes=minutes_before)
    
    @staticmethod
    def get_check_in_closes_at(tournament: Tournament):
        """
        Calculate when check-in window closes for a tournament.
        
        Args:
            tournament: Tournament instance
        
        Returns:
            datetime: Check-in closes at timestamp
        """
        minutes_before = getattr(tournament, 'check_in_closes_minutes_before', 10)
        return tournament.tournament_start - timedelta(minutes=minutes_before)
    
    @staticmethod
    def is_check_in_window_open(tournament: Tournament) -> bool:
        """
        Check if check-in window is currently open.
        
        Args:
            tournament: Tournament instance
        
        Returns:
            bool: True if check-in window is open, False otherwise
        """
        now = timezone.now()
        opens_at = CheckInService.get_check_in_opens_at(tournament)
        closes_at = CheckInService.get_check_in_closes_at(tournament)
        
        return opens_at <= now < closes_at
    
    @staticmethod
    def can_check_in(tournament: Tournament, user) -> bool:
        """
        Validate if user can check in for tournament.
        
        Checks:
        - User is registered
        - Check-in window is open
        - Not already checked in
        - Registration is confirmed (not pending payment/approval)
        
        Args:
            tournament: Tournament instance
            user: User attempting to check in
        
        Returns:
            bool: True if can check in, False otherwise
        """
        # Check if registered
        try:
            registration = Registration.objects.get(
                tournament=tournament,
                user=user,
                is_deleted=False
            )
        except Registration.DoesNotExist:
            return False
        
        # Check if already checked in
        if registration.check_in_status == 'checked_in':
            return False
        
        # Check if registration is confirmed
        if hasattr(registration, 'state') and registration.state != 'confirmed':
            return False
        
        # Check if check-in window is open
        if not CheckInService.is_check_in_window_open(tournament):
            return False
        
        return True
    
    @staticmethod
    @transaction.atomic
    def check_in(tournament: Tournament, user) -> Registration:
        """
        Perform check-in action for a participant.
        
        Args:
            tournament: Tournament instance
            user: User checking in
        
        Returns:
            Registration: Updated registration with checked_in status
        
        Raises:
            ValidationError: If check-in validation fails
        """
        # Validate check-in eligibility
        if not CheckInService.can_check_in(tournament, user):
            raise ValidationError("You cannot check in at this time.")
        
        # Get registration
        try:
            registration = Registration.objects.select_for_update().get(
                tournament=tournament,
                user=user,
                is_deleted=False
            )
        except Registration.DoesNotExist:
            raise ValidationError("Registration not found.")
        
        # Check if already checked in (race condition protection)
        if registration.check_in_status == 'checked_in':
            return registration  # Idempotent: return existing check-in
        
        # Update check-in status
        registration.check_in_status = 'checked_in'
        registration.checked_in_at = timezone.now()
        registration.save(update_fields=['check_in_status', 'checked_in_at', 'updated_at'])
        
        return registration
    
    @staticmethod
    def get_roster(tournament: Tournament):
        """
        Get all registered participants with check-in status.
        
        Args:
            tournament: Tournament instance
        
        Returns:
            QuerySet: Registration objects with check-in status
        """
        return Registration.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).select_related(
            'user',
            'user__userprofile',
            'team'
        ).order_by(
            '-check_in_status',  # Checked-in first
            'created_at'
        )
    
    @staticmethod
    @transaction.atomic
    def process_no_shows(tournament: Tournament) -> int:
        """
        Mark participants who didn't check in as no-shows/disqualified.
        
        Called by scheduled task after check-in window closes.
        
        Args:
            tournament: Tournament instance
        
        Returns:
            int: Number of participants marked as no-show
        """
        # Ensure check-in window has closed
        if CheckInService.is_check_in_window_open(tournament):
            raise ValidationError("Check-in window is still open.")
        
        # Find participants who didn't check in
        no_shows = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
            check_in_status__in=['pending', 'not_required']
        )
        
        # Update state if field exists
        if hasattr(Registration, 'state'):
            no_shows = no_shows.filter(state='confirmed')
            count = no_shows.update(
                check_in_status='no_show',
                state='disqualified',
                updated_at=timezone.now()
            )
        else:
            count = no_shows.update(
                check_in_status='no_show',
                updated_at=timezone.now()
            )
        
        return count
    
    @staticmethod
    def get_check_in_stats(tournament: Tournament) -> dict:
        """
        Get check-in statistics for a tournament.
        
        Args:
            tournament: Tournament instance
        
        Returns:
            dict: {
                'total': int,
                'checked_in': int,
                'pending': int,
                'no_show': int,
                'percentage': float
            }
        """
        registrations = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False
        )
        
        total = registrations.count()
        checked_in = registrations.filter(check_in_status='checked_in').count()
        pending = registrations.filter(check_in_status='pending').count()
        no_show = registrations.filter(check_in_status='no_show').count()
        
        percentage = (checked_in / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'checked_in': checked_in,
            'pending': pending,
            'no_show': no_show,
            'percentage': round(percentage, 1)
        }
