"""
Tournament Registration Service

This module provides high-level service methods for tournament registration workflow.
"""
from __future__ import annotations

from django.db import transaction
from django.core.exceptions import ValidationError
from django.apps import apps
from django.utils import timezone
from typing import Dict, Any, Optional, List


class TournamentRegistrationService:
    """
    Service class handling team tournament registration workflow.
    """
    
    def __init__(self, team, tournament):
        """Initialize service for specific team and tournament."""
        self.team = team
        self.tournament = tournament
    
    def can_register(self) -> Dict[str, Any]:
        """
        Check if team can register for tournament.
        Returns dict with 'allowed' (bool) and 'reasons' (list) keys.
        """
        reasons = []
        warnings = []
        
        # Check if tournament accepts team registrations
        if hasattr(self.tournament, 'tournament_type'):
            if self.tournament.tournament_type == 'SOLO':
                reasons.append("This tournament is for solo players only")
        
        # Check if registration is open
        if not self.tournament.registration_open:
            reasons.append("Tournament registration is not currently open")
        
        # Check if tournament is full
        if hasattr(self.tournament, 'is_full') and self.tournament.is_full:
            reasons.append("Tournament has reached maximum capacity")
        
        # Check game match
        if self.team.game != self.tournament.game:
            reasons.append(
                f"Team plays {self.team.game} but tournament is for {self.tournament.game}"
            )
        
        # Check if already registered
        TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
        
        existing = TeamTournamentRegistration.objects.filter(
            team=self.team,
            tournament=self.tournament
        ).first()
        
        if existing:
            if existing.status in ['approved', 'confirmed']:
                reasons.append("Team is already registered for this tournament")
            elif existing.status == 'pending':
                reasons.append("Team has a pending registration for this tournament")
            elif existing.status == 'rejected':
                warnings.append("Team's previous registration was rejected")
        
        # Check team has enough active members
        from apps.teams.game_config import GAME_CONFIGS
        
        game_config = GAME_CONFIGS.get(self.team.game, {})
        min_size = game_config.get('team_size', 5)
        
        TeamMembership = apps.get_model('teams', 'TeamMembership')
        active_count = TeamMembership.objects.filter(
            team=self.team,
            status='ACTIVE'
        ).count()
        
        if active_count < min_size:
            reasons.append(
                f"Team has only {active_count} active members, but {min_size} required for {self.team.game}"
            )
        
        # Check for captain
        if not self.team.captain:
            reasons.append("Team must have a captain to register")
        
        return {
            'allowed': len(reasons) == 0,
            'reasons': reasons,
            'warnings': warnings,
            'existing_registration': existing
        }
    
    @transaction.atomic
    def register_team(
        self,
        captain_profile,
        payment_reference: str = "",
        payment_method: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Register team for tournament.
        
        Args:
            captain_profile: UserProfile of captain registering
            payment_reference: Payment transaction reference
            payment_method: Payment method used
            **kwargs: Additional registration parameters
            
        Returns:
            Dict with registration result
        """
        TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
        
        # Verify captain
        if captain_profile != self.team.captain:
            return {
                'success': False,
                'error': 'Only team captain can register for tournaments'
            }
        
        # Check if registration allowed
        check = self.can_register()
        if not check['allowed']:
            return {
                'success': False,
                'error': 'Registration not allowed',
                'reasons': check['reasons']
            }
        
        # Create registration
        registration = TeamTournamentRegistration.objects.create(
            team=self.team,
            tournament=self.tournament,
            registered_by=captain_profile,
            status='pending',
            payment_reference=payment_reference,
            max_roster_size=kwargs.get('max_roster_size'),
            min_starters=kwargs.get('min_starters'),
            allowed_roles=kwargs.get('allowed_roles', [])
        )
        
        # Validate roster
        validation = registration.validate_roster()
        
        registration.validation_passed = validation['valid']
        registration.validation_errors = validation['errors']
        registration.save(update_fields=['validation_passed', 'validation_errors'])
        
        # Create roster snapshot
        registration.create_roster_snapshot()
        
        # If validation passed and auto-approve enabled, approve immediately
        if validation['valid']:
            # Check if tournament has auto-approval
            if not self.tournament.entry_fee or self.tournament.entry_fee == 0:
                # Free tournament - auto-approve
                registration.approve_registration()
                registration.confirm_registration()
        
        # Send notification
        self._send_registration_notification(registration, validation)
        
        # Create activity record
        self._create_registration_activity(registration)
        
        return {
            'success': True,
            'registration': registration,
            'validation': validation,
            'message': 'Registration submitted successfully'
        }
    
    def update_registration_status(
        self,
        registration_id: int,
        new_status: str,
        admin_user=None,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Update registration status (admin action).
        
        Args:
            registration_id: Registration ID
            new_status: New status value
            admin_user: Admin performing action
            reason: Reason for status change
            
        Returns:
            Dict with update result
        """
        TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
        
        try:
            registration = TeamTournamentRegistration.objects.get(id=registration_id)
        except TeamTournamentRegistration.DoesNotExist:
            return {
                'success': False,
                'error': 'Registration not found'
            }
        
        old_status = registration.status
        
        with transaction.atomic():
            if new_status == 'approved':
                registration.approve_registration(admin_user)
            elif new_status == 'rejected':
                registration.reject_registration(reason, admin_user)
            elif new_status == 'confirmed':
                registration.confirm_registration(admin_user)
            else:
                registration.status = new_status
                registration.save(update_fields=['status'])
            
            # Send notification about status change
            self._send_status_change_notification(
                registration,
                old_status,
                new_status,
                reason
            )
        
        return {
            'success': True,
            'registration': registration,
            'old_status': old_status,
            'new_status': new_status
        }
    
    def verify_payment(
        self,
        registration_id: int,
        verified_by,
        payment_reference: str = ""
    ) -> Dict[str, Any]:
        """
        Verify payment for registration.
        
        Args:
            registration_id: Registration ID
            verified_by: User verifying payment
            payment_reference: Updated payment reference if needed
            
        Returns:
            Dict with verification result
        """
        TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
        
        try:
            registration = TeamTournamentRegistration.objects.get(id=registration_id)
        except TeamTournamentRegistration.DoesNotExist:
            return {
                'success': False,
                'error': 'Registration not found'
            }
        
        with transaction.atomic():
            if payment_reference:
                registration.payment_reference = payment_reference
            
            registration.confirm_registration(verified_by)
            
            # Send confirmation notification
            self._send_payment_verified_notification(registration)
        
        return {
            'success': True,
            'registration': registration,
            'message': 'Payment verified and registration confirmed'
        }
    
    def lock_tournament_rosters(self) -> Dict[str, Any]:
        """
        Lock all confirmed registrations' rosters for this tournament.
        Typically called when tournament starts.
        
        Returns:
            Dict with lock results
        """
        TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
        
        registrations = TeamTournamentRegistration.objects.filter(
            tournament=self.tournament,
            status='confirmed',
            is_roster_locked=False
        )
        
        locked_count = 0
        
        for registration in registrations:
            registration.lock_roster()
            locked_count += 1
            
            # Notify team
            self._send_roster_locked_notification(registration)
        
        return {
            'success': True,
            'locked_count': locked_count,
            'message': f'Locked {locked_count} team rosters'
        }
    
    def _send_registration_notification(self, registration, validation):
        """Send notification about registration submission."""
        NotificationService = apps.get_model('notifications', 'NotificationService')
        TeamMembership = apps.get_model('teams', 'TeamMembership')
        
        # Get all team members
        members = TeamMembership.objects.filter(
            team=self.team,
            status='ACTIVE'
        ).select_related('profile__user')
        
        # Prepare notification data
        if validation['valid']:
            title = f"✅ Tournament Registration Successful"
            message = f"Your team '{self.team.name}' has been registered for {self.tournament.name}"
        else:
            title = f"⚠️ Tournament Registration Issues"
            message = f"Registration submitted for {self.tournament.name} but roster validation found issues"
        
        # Send to all members (implementation depends on notification system)
        # This is a placeholder - adjust based on your notification system
        try:
            for membership in members:
                if hasattr(membership.profile, 'user'):
                    # Create notification
                    pass  # Implement based on your notification model
        except Exception:
            pass
    
    def _send_status_change_notification(
        self,
        registration,
        old_status,
        new_status,
        reason
    ):
        """Send notification about registration status change."""
        # Implementation depends on your notification system
        pass
    
    def _send_payment_verified_notification(self, registration):
        """Send notification about payment verification."""
        # Implementation depends on your notification system
        pass
    
    def _send_roster_locked_notification(self, registration):
        """Send notification about roster lock."""
        # Implementation depends on your notification system
        pass
    
    def _create_registration_activity(self, registration):
        """Create team activity record for registration."""
        TeamActivity = apps.get_model('teams', 'TeamActivity')
        
        try:
            TeamActivity.objects.create(
                team=self.team,
                activity_type='tournament_registration',
                actor=registration.registered_by,
                description=f"Registered for tournament: {self.tournament.name}",
                metadata={
                    'tournament_id': self.tournament.id,
                    'tournament_name': self.tournament.name,
                    'registration_id': registration.id
                },
                is_public=True
            )
        except Exception:
            pass  # Fail soft if activity creation fails
    
    @classmethod
    def get_team_registrations(
        cls,
        team,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all registrations for a team.
        
        Args:
            team: Team instance
            status: Filter by status (optional)
            
        Returns:
            List of registration dictionaries
        """
        TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
        
        # NOTE: tournament is now IntegerField (tournament_id), removed select_related
        # Tournament system moved to legacy - return empty list
        registrations = TeamTournamentRegistration.objects.filter(
            team=team
        ).select_related('registered_by')
        
        if status:
            registrations = registrations.filter(status=status)
        
        registrations = registrations.order_by('-registered_at')
        
        # Return simplified data (tournament object not available)
        return [
            {
                'id': reg.id,
                'tournament': {
                    'id': reg.tournament_id,
                    'name': f'Legacy Tournament {reg.tournament_id}',
                    'slug': f'legacy-{reg.tournament_id}',
                    'game': 'N/A',
                    'start_date': None,
                },
                'status': reg.status,
                'registered_at': reg.registered_at,
                'registered_by': reg.registered_by.display_name,
                'is_roster_locked': reg.is_roster_locked,
                'validation_passed': reg.validation_passed,
                'validation_errors': reg.validation_errors,
            }
            for reg in registrations
        ]
    
    @classmethod
    def get_tournament_teams(
        cls,
        tournament,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all teams registered for a tournament.
        
        Args:
            tournament: Tournament instance
            status: Filter by status (optional)
            
        Returns:
            List of team dictionaries
        """
        TeamTournamentRegistration = apps.get_model('teams', 'TeamTournamentRegistration')
        
        registrations = TeamTournamentRegistration.objects.filter(
            tournament=tournament
        ).select_related('team', 'registered_by')
        
        if status:
            registrations = registrations.filter(status=status)
        
        registrations = registrations.order_by('-registered_at')
        
        return [
            {
                'registration_id': reg.id,
                'team': {
                    'id': reg.team.id,
                    'name': reg.team.name,
                    'tag': reg.team.tag,
                    'logo': reg.team.logo.url if reg.team.logo else None,
                    'captain': reg.team.captain.display_name if reg.team.captain else None,
                },
                'status': reg.status,
                'registered_at': reg.registered_at,
                'roster_count': len(reg.roster_snapshot.get('roster', [])),
                'is_roster_locked': reg.is_roster_locked,
                'validation_passed': reg.validation_passed,
            }
            for reg in registrations
        ]
