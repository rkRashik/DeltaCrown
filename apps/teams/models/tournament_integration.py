"""
Tournament Integration Models for Teams

This module provides models for:
1. TeamTournamentRegistration - Team registration for tournaments with validation
2. TournamentParticipation - Player participation tracking
3. TournamentRosterLock - Roster lock state during tournaments
"""
from __future__ import annotations

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from typing import Dict, List, Any, Optional


class TeamTournamentRegistration(models.Model):
    """
    Tracks team registration for tournaments with game-specific validation.
    Ensures roster requirements are met and prevents conflicts.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('confirmed', 'Confirmed'),  # Payment verified, ready to play
    ]
    
    # Core relations
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='tournament_registrations'
    )
    
    # NOTE: Changed to IntegerField - tournament app moved to legacy (Nov 2, 2025)
    tournament_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Legacy tournament ID (reference only)")
    
    # Registration metadata
    registered_by = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.PROTECT,
        related_name='team_tournament_registrations',
        help_text="Captain who registered the team"
    )
    
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Roster snapshot at registration time
    roster_snapshot = models.JSONField(
        default=dict,
        help_text="Snapshot of team roster at registration time (player IDs, roles, IGNs)"
    )
    
    # Validation results
    validation_passed = models.BooleanField(
        default=False,
        help_text="Whether roster validation passed"
    )
    
    validation_errors = models.JSONField(
        default=list,
        help_text="List of validation errors if any"
    )
    
    # Tournament-specific roster settings (can override team defaults)
    max_roster_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Max roster for this tournament (overrides game default)"
    )
    
    min_starters = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minimum starting players required"
    )
    
    allowed_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Specific roles allowed for this tournament (empty = all)"
    )
    
    # Roster lock
    is_roster_locked = models.BooleanField(
        default=False,
        help_text="Whether roster is locked for this tournament"
    )
    
    locked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When roster was locked"
    )
    
    # Payment tracking
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Payment transaction reference"
    )
    
    payment_verified = models.BooleanField(
        default=False,
        help_text="Whether payment has been verified"
    )
    
    payment_verified_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    payment_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_team_registrations'
    )
    
    # Admin notes
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal admin notes about this registration"
    )
    
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection if applicable"
    )
    
    # Timestamps
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "teams_tournament_registration"
        verbose_name = "Team Tournament Registration"
        verbose_name_plural = "Team Tournament Registrations"
        ordering = ['-registered_at']
        indexes = [
            models.Index(fields=['tournament_id', 'status']),
            models.Index(fields=['team', 'tournament_id']),
            models.Index(fields=['status', '-registered_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'tournament_id'],
                name='unique_team_tournament_registration'
            )
        ]

    def __str__(self):
        return f"{self.team.name} → Tournament#{self.tournament_id} ({self.status})"

    def clean(self):
        """Validate registration requirements."""
        errors = {}
        
        # NOTE: Validation disabled - tournament app moved to legacy
        # Can be re-enabled when new Tournament Engine is built
        
        # Check if captain is registering
        if self.registered_by != self.team.captain:
            errors['registered_by'] = "Only team captain can register the team"
        
        # Check for duplicate registration
        if not self.pk:  # Only for new registrations
            existing = TeamTournamentRegistration.objects.filter(
                team=self.team,
                tournament=self.tournament
            ).exists()
            
            if existing:
                errors['team'] = "Team is already registered for this tournament"
        
        if errors:
            raise ValidationError(errors)

    def validate_roster(self) -> Dict[str, Any]:
        """
        Validate team roster against tournament and game requirements.
        Returns dict with 'valid' (bool) and 'errors' (list) keys.
        """
        from apps.games.services import game_service
        from apps.teams.models import TeamMembership
        
        errors = []
        warnings = []
        
        # Get active roster
        active_members = TeamMembership.objects.filter(
            team=self.team,
            status=TeamMembership.Status.ACTIVE
        ).select_related('profile')
        
        roster_count = active_members.count()
        
        # Get game roster limits
        game_obj = game_service.get_game(self.team.game) if self.team.game else None
        roster_limits = game_service.get_roster_limits(game_obj) if game_obj else {}
        if not game_obj:
            errors.append(f"Unknown game: {self.team.game}")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        # Check minimum roster size
        min_size = game_config.get('team_size', 5)
        if roster_count < min_size:
            errors.append(
                f"Roster has only {roster_count} players, but game requires minimum {min_size} players"
            )
        
        # Check maximum roster size (tournament override or game default)
        max_size = self.max_roster_size or game_config.get('max_substitutes', 0) + game_config.get('team_size', 5)
        if roster_count > max_size:
            errors.append(
                f"Roster has {roster_count} players, exceeding maximum {max_size} allowed"
            )
        
        # Check minimum starters if specified
        if self.min_starters:
            starters = active_members.exclude(
                role=TeamMembership.Role.SUB
            ).count()
            
            if starters < self.min_starters:
                errors.append(
                    f"Only {starters} starters, but tournament requires minimum {self.min_starters}"
                )
        
        # Check for captain
        has_captain = active_members.filter(
            role=TeamMembership.Role.CAPTAIN
        ).exists()
        
        if not has_captain:
            errors.append("Team must have an active captain")
        
        # Check pending invites
        pending_invites = self.team.invites.filter(status='PENDING').count()
        if pending_invites > 0:
            warnings.append(
                f"Team has {pending_invites} pending invite(s). Complete roster before tournament starts."
            )
        
        # Check allowed roles if specified
        if self.allowed_roles:
            for member in active_members:
                role = member.role
                if role not in self.allowed_roles:
                    errors.append(
                        f"Player {member.profile.display_name} has role '{role}' which is not allowed in this tournament"
                    )
        
        # Check for duplicate tournament participation
        # (same player in multiple teams for same tournament)
        if not errors:  # Only check if basic validation passed
            duplicate_check = self._check_duplicate_participation()
            if duplicate_check['has_duplicates']:
                errors.extend(duplicate_check['errors'])
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'roster_count': roster_count,
            'min_size': min_size,
            'max_size': max_size
        }

    def _check_duplicate_participation(self) -> Dict[str, Any]:
        """Check if any team members are registered in another team for same tournament."""
        from apps.teams.models import TeamMembership
        
        # Get all player IDs in this team
        player_ids = list(
            TeamMembership.objects.filter(
                team=self.team,
                status=TeamMembership.Status.ACTIVE
            ).values_list('profile_id', flat=True)
        )
        
        # Find other confirmed registrations for same tournament
        other_registrations = TeamTournamentRegistration.objects.filter(
            tournament=self.tournament,
            status__in=['approved', 'confirmed']
        ).exclude(
            team=self.team
        ).select_related('team')
        
        conflicts = []
        
        for other_reg in other_registrations:
            # Get their roster
            other_roster = TeamMembership.objects.filter(
                team=other_reg.team,
                status=TeamMembership.Status.ACTIVE,
                profile_id__in=player_ids
            ).select_related('profile')
            
            for membership in other_roster:
                conflicts.append({
                    'player': membership.profile.display_name,
                    'other_team': other_reg.team.name,
                    'error': f"Player {membership.profile.display_name} is already registered with team '{other_reg.team.name}' for this tournament"
                })
        
        return {
            'has_duplicates': len(conflicts) > 0,
            'conflicts': conflicts,
            'errors': [c['error'] for c in conflicts]
        }

    def create_roster_snapshot(self):
        """Create a snapshot of current roster for audit trail."""
        from apps.teams.models import TeamMembership
        
        members = TeamMembership.objects.filter(
            team=self.team,
            status=TeamMembership.Status.ACTIVE
        ).select_related('profile__user')
        
        snapshot = {
            'captured_at': timezone.now().isoformat(),
            'roster': []
        }
        
        for member in members:
            snapshot['roster'].append({
                'profile_id': member.profile.id,
                'user_id': member.profile.user.id,
                'display_name': member.profile.display_name,
                'in_game_name': getattr(member.profile, 'in_game_name', ''),
                'role': member.role,
                'joined_at': member.joined_at.isoformat() if member.joined_at else None,
            })
        
        self.roster_snapshot = snapshot
        self.save(update_fields=['roster_snapshot'])

    def lock_roster(self):
        """Lock the roster for tournament, preventing changes."""
        if not self.is_roster_locked:
            self.is_roster_locked = True
            self.locked_at = timezone.now()
            self.save(update_fields=['is_roster_locked', 'locked_at'])
            
            # Create roster lock record
            TournamentRosterLock.objects.create(
                registration=self,
                locked_by_system=True,
                reason="Tournament started - roster auto-locked"
            )

    def unlock_roster(self, unlocked_by=None, reason=""):
        """Unlock the roster (admin only)."""
        if self.is_roster_locked:
            self.is_roster_locked = False
            self.save(update_fields=['is_roster_locked'])
            
            # Log unlock
            TournamentRosterLock.objects.create(
                registration=self,
                is_unlock=True,
                unlocked_by=unlocked_by,
                reason=reason or "Manual roster unlock by admin"
            )

    def approve_registration(self, admin_user=None):
        """Approve the registration after validation."""
        with transaction.atomic():
            # Validate roster
            validation = self.validate_roster()
            
            if not validation['valid']:
                raise ValidationError({
                    'status': 'Cannot approve registration with invalid roster',
                    'errors': validation['errors']
                })
            
            self.status = 'approved'
            self.validation_passed = True
            self.validation_errors = []
            self.updated_at = timezone.now()
            
            # Create roster snapshot
            self.create_roster_snapshot()
            
            self.save(update_fields=[
                'status',
                'validation_passed',
                'validation_errors',
                'updated_at'
            ])
            
            # Create participation records for all roster members
            self.create_participation_records()

    def confirm_registration(self, verified_by=None):
        """Confirm registration after payment verification."""
        with transaction.atomic():
            self.status = 'confirmed'
            self.payment_verified = True
            self.payment_verified_at = timezone.now()
            self.payment_verified_by = verified_by
            
            self.save(update_fields=[
                'status',
                'payment_verified',
                'payment_verified_at',
                'payment_verified_by'
            ])

    def reject_registration(self, reason="", rejected_by=None):
        """Reject the registration."""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.save(update_fields=['status', 'rejection_reason'])

    def create_participation_records(self):
        """Create TournamentParticipation records for all roster members."""
        from apps.teams.models import TeamMembership
        
        members = TeamMembership.objects.filter(
            team=self.team,
            status=TeamMembership.Status.ACTIVE
        )
        
        for member in members:
            TournamentParticipation.objects.get_or_create(
                registration=self,
                player=member.profile,
                defaults={
                    'role': member.role,
                    'is_starter': member.role != TeamMembership.Role.SUB
                }
            )

    def get_roster_display(self) -> List[Dict[str, Any]]:
        """Get roster information for display."""
        from apps.teams.models import TeamMembership
        
        members = TeamMembership.objects.filter(
            team=self.team,
            status=TeamMembership.Status.ACTIVE
        ).select_related('profile__user').order_by(
            '-role',  # Captain first
            'joined_at'
        )
        
        return [
            {
                'display_name': member.profile.display_name,
                'in_game_name': getattr(member.profile, 'in_game_name', ''),
                'role': member.get_role_display(),
                'avatar': member.profile.avatar_url if hasattr(member.profile, 'avatar_url') else None,
                'is_captain': member.role == TeamMembership.Role.CAPTAIN
            }
            for member in members
        ]


class TournamentParticipation(models.Model):
    """
    Tracks individual player participation in tournaments via team registration.
    Prevents duplicate participation and maintains audit trail.
    """
    
    registration = models.ForeignKey(
        TeamTournamentRegistration,
        on_delete=models.CASCADE,
        related_name='participations'
    )
    
    player = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='tournament_participations'
    )
    
    role = models.CharField(
        max_length=16,
        help_text="Player's role in the team for this tournament"
    )
    
    is_starter = models.BooleanField(
        default=True,
        help_text="Whether player is in starting lineup"
    )
    
    # Performance tracking
    matches_played = models.PositiveIntegerField(
        default=0,
        help_text="Number of matches this player participated in"
    )
    
    mvp_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times player was MVP"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "teams_tournament_participation"
        verbose_name = "Tournament Participation"
        verbose_name_plural = "Tournament Participations"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['player', 'registration']),
            models.Index(fields=['registration', 'is_starter']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['registration', 'player'],
                name='unique_player_per_registration'
            )
        ]

    def __str__(self):
        return f"{self.player.display_name} in Tournament#{self.registration.tournament_id}"

    def clean(self):
        """Validate participation."""
        # Check if player is in another team for same tournament
        tournament_id = self.registration.tournament_id
        
        other_participations = TournamentParticipation.objects.filter(
            registration__tournament_id=tournament_id,
            player=self.player,
            registration__status__in=['approved', 'confirmed']
        ).exclude(
            registration=self.registration
        ).select_related('registration__team')
        
        if other_participations.exists():
            other_team = other_participations.first().registration.team
            raise ValidationError({
                'player': f"Player {self.player.display_name} is already participating with team '{other_team.name}' in this tournament"
            })


class TournamentRosterLock(models.Model):
    """
    Audit trail for roster lock/unlock events during tournaments.
    """
    
    registration = models.ForeignKey(
        TeamTournamentRegistration,
        on_delete=models.CASCADE,
        related_name='lock_history'
    )
    
    is_unlock = models.BooleanField(
        default=False,
        help_text="True if this is an unlock event, False for lock"
    )
    
    locked_by_system = models.BooleanField(
        default=False,
        help_text="Whether lock was automatic (tournament start)"
    )
    
    unlocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Admin who unlocked roster (if manual)"
    )
    
    reason = models.TextField(
        blank=True,
        help_text="Reason for lock/unlock"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "teams_tournament_roster_lock"
        verbose_name = "Tournament Roster Lock"
        verbose_name_plural = "Tournament Roster Locks"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['registration', '-created_at']),
        ]

    def __str__(self):
        action = "Unlocked" if self.is_unlock else "Locked"
        return f"{action} roster for {self.registration.team.name} at {self.created_at}"
