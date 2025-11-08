"""
Check-in Service Layer for Tournament Registrations

Handles check-in business logic including:
- Single and bulk check-in operations
- Check-in validation and timing rules
- Undo check-in with organizer override
- Audit logging for all check-in actions

Author: DeltaCrown Development Team
Date: November 8, 2025
"""

from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth import get_user_model

from apps.tournaments.models import Registration, Tournament
from apps.tournaments.security.audit import audit_event, AuditAction

User = get_user_model()


class CheckinService:
    """Service for managing tournament check-ins"""
    
    # Check-in timing constants (in minutes)
    CHECK_IN_WINDOW_BEFORE_START = 30  # Open 30 minutes before
    CHECK_IN_UNDO_WINDOW = 15  # Can undo within 15 minutes
    
    @staticmethod
    @transaction.atomic
    def check_in(registration_id: int, actor: User) -> Registration:
        """
        Check in a registration for tournament.
        
        Args:
            registration_id: ID of registration to check in
            actor: User performing the check-in
            
        Returns:
            Updated Registration instance
            
        Raises:
            Registration.DoesNotExist: If registration not found
            ValidationError: If check-in not allowed
            PermissionDenied: If actor not authorized
        """
        # Fetch registration with related data
        # Note: Cannot use select_related with select_for_update on nullable FKs
        # PostgreSQL doesn't allow FOR UPDATE on nullable side of outer join
        registration = Registration.objects.select_related(
            'tournament',
        ).select_for_update().get(id=registration_id)
        
        tournament = registration.tournament
        
        # Validate check-in eligibility
        CheckinService._validate_check_in_eligibility(
            registration, tournament, actor
        )
        
        # Idempotent: if already checked in, return without error
        if registration.checked_in:
            return registration
        
        # Perform check-in
        registration.checked_in = True
        registration.checked_in_at = timezone.now()
        # Note: checked_in_by field not yet added to model (future enhancement)
        registration.save(update_fields=['checked_in', 'checked_in_at'])
        
        # Audit log
        audit_event(
            user=actor,
            action='REGISTRATION_CHECKIN',
            meta={
                'registration_id': registration.id,
                'tournament_id': tournament.id,
                'user_id': registration.user_id if registration.user_id else None,
                'team_id': registration.team_id if registration.team_id else None,
                'checked_in_by': actor.id,
            }
        )
        
        return registration
    
    @staticmethod
    @transaction.atomic
    def undo_check_in(
        registration_id: int,
        actor: User,
        reason: Optional[str] = None
    ) -> Registration:
        """
        Undo check-in for a registration.
        
        Args:
            registration_id: ID of registration to undo check-in
            actor: User performing the undo
            reason: Optional reason for undo
            
        Returns:
            Updated Registration instance
            
        Raises:
            Registration.DoesNotExist: If registration not found
            ValidationError: If undo not allowed
            PermissionDenied: If actor not authorized
        """
        # Fetch registration with related data
        # Note: Cannot use select_related with select_for_update on nullable FKs
        # PostgreSQL doesn't allow FOR UPDATE on nullable side of outer join
        registration = Registration.objects.select_related(
            'tournament',
        ).select_for_update().get(id=registration_id)
        
        tournament = registration.tournament
        
        # Must be currently checked in
        if not registration.checked_in:
            raise ValidationError("Registration is not checked in")
        
        # Check permissions and timing
        is_organizer = CheckinService._is_organizer_or_admin(actor, tournament)
        is_owner = CheckinService._is_registration_owner(actor, registration)
        
        if not is_organizer and not is_owner:
            raise PermissionDenied("You don't have permission to undo this check-in")
        
        # Organizer can always undo; owner only within window
        if not is_organizer:
            if not CheckinService._is_within_undo_window(registration):
                raise ValidationError(
                    f"Check-in can only be undone within "
                    f"{CheckinService.CHECK_IN_UNDO_WINDOW} minutes"
                )
        
        # Perform undo
        registration.checked_in = False
        registration.checked_in_at = None
        # Note: checked_in_by field not yet added to model (future enhancement)
        registration.save(update_fields=['checked_in', 'checked_in_at'])
        
        # Audit log
        audit_event(
            user=actor,
            action='REGISTRATION_CHECKIN_REVERT',
            meta={
                'registration_id': registration.id,
                'tournament_id': tournament.id,
                'user_id': registration.user_id if registration.user_id else None,
                'team_id': registration.team_id if registration.team_id else None,
                'reverted_by': actor.id,
                'is_organizer_override': is_organizer,
                'reason': reason or '',
            }
        )
        
        return registration
    
    @staticmethod
    @transaction.atomic
    def bulk_check_in(
        registration_ids: List[int],
        actor: User
    ) -> Dict[str, List[Dict]]:
        """
        Bulk check-in multiple registrations (organizer only).
        
        Args:
            registration_ids: List of registration IDs to check in
            actor: User performing bulk check-in (must be organizer/admin)
            
        Returns:
            Dict with 'success', 'skipped', 'errors' lists
        """
        if len(registration_ids) > 200:
            raise ValidationError("Cannot check in more than 200 registrations at once")
        
        results = {
            'success': [],
            'skipped': [],
            'errors': []
        }
        
        # Fetch all registrations
        registrations = Registration.objects.select_related(
            'tournament',
            'user'
        ).filter(id__in=registration_ids)
        
        # Verify actor is organizer for all tournaments
        tournament_ids = set(reg.tournament_id for reg in registrations)
        for tournament_id in tournament_ids:
            tournament = Tournament.objects.get(id=tournament_id)
            if not CheckinService._is_organizer_or_admin(actor, tournament):
                raise PermissionDenied(
                    f"You must be organizer of tournament {tournament.title} "
                    f"to perform bulk check-in"
                )
        
        # Process each registration
        for registration in registrations:
            try:
                # Check if already checked in (skip)
                if registration.checked_in:
                    results['skipped'].append({
                        'id': registration.id,
                        'reason': 'Already checked in'
                    })
                    continue
                
                # Validate eligibility
                try:
                    CheckinService._validate_check_in_eligibility(
                        registration,
                        registration.tournament,
                        actor,
                        skip_permission_check=True  # Already checked above
                    )
                except ValidationError as e:
                    results['errors'].append({
                        'id': registration.id,
                        'reason': str(e)
                    })
                    continue
                
                # Perform check-in
                registration.checked_in = True
                registration.checked_in_at = timezone.now()
                # Note: checked_in_by field not yet added to model (future enhancement)
                registration.save(update_fields=[
                    'checked_in', 'checked_in_at'
                ])
                
                results['success'].append({
                    'id': registration.id
                })
                
                # Audit log
                audit_event(
                    user=actor,
                    action='REGISTRATION_CHECKIN',
                    meta={
                        'registration_id': registration.id,
                        'tournament_id': registration.tournament_id,
                        'bulk_operation': True,
                        'checked_in_by': actor.id,
                    }
                )
                
            except Exception as e:
                results['errors'].append({
                    'id': registration.id,
                    'reason': str(e)
                })
        
        return results
    
    # ========================
    # Private Helper Methods
    # ========================
    
    @staticmethod
    def _validate_check_in_eligibility(
        registration: Registration,
        tournament: Tournament,
        actor: User,
        skip_permission_check: bool = False
    ) -> None:
        """
        Validate if check-in is allowed.
        
        Raises:
            ValidationError: If check-in not allowed
            PermissionDenied: If actor not authorized
        """
        # Registration must be confirmed
        if registration.status != 'confirmed':
            raise ValidationError(
                f"Registration must be confirmed. Current status: {registration.status}"
            )
        
        # Registration must not be cancelled
        if registration.status == 'cancelled':
            raise ValidationError("Cannot check in cancelled registration")
        
        # Check-in window must be open
        if not CheckinService._is_check_in_window_open(tournament):
            raise ValidationError(
                f"Check-in opens {CheckinService.CHECK_IN_WINDOW_BEFORE_START} "
                f"minutes before tournament start"
            )
        
        # Tournament must not have started yet
        if tournament.tournament_start and timezone.now() >= tournament.tournament_start:
            raise ValidationError("Tournament has already started")
        
        # Check permissions
        if not skip_permission_check:
            is_organizer = CheckinService._is_organizer_or_admin(actor, tournament)
            is_owner = CheckinService._is_registration_owner(actor, registration)
            
            if not is_organizer and not is_owner:
                raise PermissionDenied(
                    "Only registration owner or tournament organizer can check in"
                )
    
    @staticmethod
    def _is_check_in_window_open(tournament: Tournament) -> bool:
        """Check if check-in window is currently open"""
        if not tournament.tournament_start:
            return False
        
        now = timezone.now()
        check_in_opens_at = tournament.tournament_start - timezone.timedelta(
            minutes=CheckinService.CHECK_IN_WINDOW_BEFORE_START
        )
        
        return now >= check_in_opens_at and now < tournament.tournament_start
    
    @staticmethod
    def _is_within_undo_window(registration: Registration) -> bool:
        """Check if registration is within undo window"""
        if not registration.checked_in_at:
            return False
        
        now = timezone.now()
        undo_deadline = registration.checked_in_at + timezone.timedelta(
            minutes=CheckinService.CHECK_IN_UNDO_WINDOW
        )
        
        return now <= undo_deadline
    
    @staticmethod
    def _is_organizer_or_admin(user: User, tournament: Tournament) -> bool:
        """Check if user is tournament organizer or admin"""
        return user.is_superuser or tournament.organizer_id == user.id
    
    @staticmethod
    def _is_registration_owner(user: User, registration: Registration) -> bool:
        """Check if user is registration owner"""
        # For solo registrations
        if registration.user_id:
            return registration.user_id == user.id
        
        # For team registrations (check if captain)
        if registration.team_id:
            try:
                from apps.teams.models import TeamMembership
                
                membership = TeamMembership.objects.filter(
                    team_id=registration.team_id,
                    user=user,
                    role='OWNER',
                    status='ACTIVE'
                ).exists()
                
                return membership
            except Exception:
                return False
        
        return False
