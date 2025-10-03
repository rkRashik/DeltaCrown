"""
Tournament Capacity Model

Handles all capacity and team size related logic for tournaments.
Separates capacity concerns from the main Tournament model.

Fields:
    - slot_size: Number of total slots/positions
    - max_teams: Maximum teams allowed
    - min_team_size: Minimum players per team
    - max_team_size: Maximum players per team
    - registration_mode: Open, approval-based, or invite-only
    - waitlist_enabled: Allow teams to join waitlist when full
    - current_registrations: Cached count (updated on save)

Properties:
    - is_full: Check if tournament is at capacity
    - available_slots: Remaining slots
    - registration_progress_percent: Registration progress as percentage
    - can_accept_registrations: Check if accepting new registrations

Author: DeltaCrown Development Team
Date: October 3, 2025
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class TournamentCapacity(models.Model):
    """
    Manages tournament capacity and team size constraints.
    
    This model encapsulates all capacity-related logic including:
    - Total slots and team limits
    - Team size constraints (per game)
    - Registration mode (open, approval, invite)
    - Waitlist functionality
    - Real-time availability tracking
    """
    
    # Registration Modes
    MODE_OPEN = 'open'
    MODE_APPROVAL = 'approval'
    MODE_INVITE = 'invite'
    
    REGISTRATION_MODE_CHOICES = [
        (MODE_OPEN, _('Open Registration')),
        (MODE_APPROVAL, _('Approval Required')),
        (MODE_INVITE, _('Invite Only')),
    ]
    
    # Relationships
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='capacity',
        verbose_name=_('Tournament'),
        help_text=_('The tournament this capacity configuration belongs to')
    )
    
    # Capacity Fields
    slot_size = models.PositiveIntegerField(
        verbose_name=_('Total Slots'),
        validators=[MinValueValidator(2), MaxValueValidator(1024)],
        help_text=_('Total number of slots/positions available (2-1024)')
    )
    
    max_teams = models.PositiveIntegerField(
        verbose_name=_('Maximum Teams'),
        validators=[MinValueValidator(2), MaxValueValidator(1024)],
        help_text=_('Maximum number of teams allowed (usually same as slot_size)')
    )
    
    # Team Size Constraints
    min_team_size = models.PositiveIntegerField(
        verbose_name=_('Minimum Team Size'),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text=_('Minimum number of players per team (1 for solo, 5 for Valorant, etc.)')
    )
    
    max_team_size = models.PositiveIntegerField(
        verbose_name=_('Maximum Team Size'),
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text=_('Maximum number of players per team (including substitutes)')
    )
    
    # Registration Configuration
    registration_mode = models.CharField(
        max_length=20,
        choices=REGISTRATION_MODE_CHOICES,
        default=MODE_OPEN,
        verbose_name=_('Registration Mode'),
        help_text=_('How teams can register for this tournament')
    )
    
    waitlist_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Enable Waitlist'),
        help_text=_('Allow teams to join waitlist when tournament is full')
    )
    
    # Cached Data (updated on registration changes)
    current_registrations = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Current Registrations'),
        help_text=_('Cached count of active registrations (auto-updated)')
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Tournament Capacity')
        verbose_name_plural = _('Tournament Capacities')
        db_table = 'tournaments_capacity'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['registration_mode']),
            models.Index(fields=['current_registrations']),
        ]
    
    def __str__(self):
        return f"{self.tournament.name} - Capacity ({self.current_registrations}/{self.max_teams})"
    
    def clean(self):
        """Validate capacity configuration"""
        errors = {}
        
        # Validate team size relationship
        if self.min_team_size > self.max_team_size:
            errors['min_team_size'] = _(
                'Minimum team size cannot be greater than maximum team size'
            )
        
        # Validate max_teams vs slot_size
        if self.max_teams > self.slot_size:
            errors['max_teams'] = _(
                'Maximum teams cannot exceed total slots'
            )
        
        # Validate reasonable capacity
        if self.slot_size < 2:
            errors['slot_size'] = _(
                'Tournament must have at least 2 slots'
            )
        
        # Validate current_registrations doesn't exceed max_teams
        if self.current_registrations > self.max_teams:
            errors['current_registrations'] = _(
                f'Current registrations ({self.current_registrations}) exceeds maximum teams ({self.max_teams})'
            )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Ensure validation before save"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    # ==========================================
    # Properties - Computed Values
    # ==========================================
    
    @property
    def is_full(self) -> bool:
        """Check if tournament is at capacity"""
        return self.current_registrations >= self.max_teams
    
    @property
    def available_slots(self) -> int:
        """Get number of remaining slots"""
        return max(0, self.max_teams - self.current_registrations)
    
    @property
    def registration_progress_percent(self) -> float:
        """Get registration progress as percentage (0-100)"""
        if self.max_teams == 0:
            return 0.0
        return round((self.current_registrations / self.max_teams) * 100, 1)
    
    @property
    def can_accept_registrations(self) -> bool:
        """
        Check if tournament can accept new registrations.
        Considers mode, capacity, and waitlist.
        """
        # Invite-only tournaments don't accept open registrations
        if self.registration_mode == self.MODE_INVITE:
            return False
        
        # If not full, can accept
        if not self.is_full:
            return True
        
        # If full but waitlist enabled, can still accept
        return self.waitlist_enabled
    
    @property
    def is_solo_tournament(self) -> bool:
        """Check if this is a solo (1v1) tournament"""
        return self.min_team_size == 1 and self.max_team_size == 1
    
    @property
    def requires_full_squad(self) -> bool:
        """Check if tournament requires full squad (min == max)"""
        return self.min_team_size == self.max_team_size
    
    # ==========================================
    # Methods - Actions
    # ==========================================
    
    def increment_registrations(self, count: int = 1) -> None:
        """
        Increment the current registrations count.
        
        Args:
            count: Number of registrations to add (default: 1)
            
        Raises:
            ValidationError: If increment would exceed max_teams
        """
        new_count = self.current_registrations + count
        
        if new_count > self.max_teams and not self.waitlist_enabled:
            raise ValidationError(
                f'Cannot add {count} registrations. '
                f'Would exceed maximum teams ({self.max_teams})'
            )
        
        self.current_registrations = new_count
        self.save(update_fields=['current_registrations', 'updated_at'])
    
    def decrement_registrations(self, count: int = 1) -> None:
        """
        Decrement the current registrations count.
        
        Args:
            count: Number of registrations to remove (default: 1)
        """
        self.current_registrations = max(0, self.current_registrations - count)
        self.save(update_fields=['current_registrations', 'updated_at'])
    
    def refresh_registration_count(self) -> int:
        """
        Refresh current_registrations from actual database count.
        
        Returns:
            int: Updated registration count
        """
        from apps.tournaments.models.registration import TournamentRegistration
        
        actual_count = TournamentRegistration.objects.filter(
            tournament=self.tournament,
            status__in=['pending', 'approved']
        ).count()
        
        if actual_count != self.current_registrations:
            self.current_registrations = actual_count
            self.save(update_fields=['current_registrations', 'updated_at'])
        
        return self.current_registrations
    
    def validate_team_size(self, team_size: int) -> tuple[bool, str]:
        """
        Validate if a team size is acceptable for this tournament.
        
        Args:
            team_size: Number of players in the team
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if team_size < self.min_team_size:
            return False, f'Team must have at least {self.min_team_size} players'
        
        if team_size > self.max_team_size:
            return False, f'Team cannot exceed {self.max_team_size} players'
        
        return True, 'Team size is valid'
    
    def get_capacity_display(self) -> str:
        """Get human-readable capacity status"""
        if self.is_full:
            return f'FULL ({self.current_registrations}/{self.max_teams})'
        
        return f'{self.current_registrations}/{self.max_teams} ({self.available_slots} slots remaining)'
    
    def get_registration_mode_display_extended(self) -> str:
        """Get extended description of registration mode"""
        mode_descriptions = {
            self.MODE_OPEN: 'Open to all teams - instant registration',
            self.MODE_APPROVAL: 'Requires admin approval after registration',
            self.MODE_INVITE: 'Invite-only - closed registration',
        }
        return mode_descriptions.get(self.registration_mode, self.get_registration_mode_display())
    
    # ==========================================
    # Helper Methods
    # ==========================================
    
    def clone_for_tournament(self, target_tournament) -> 'TournamentCapacity':
        """
        Create a copy of this capacity configuration for another tournament.
        
        Args:
            target_tournament: Tournament instance to link the clone to
            
        Returns:
            TournamentCapacity: New capacity instance
        """
        return TournamentCapacity.objects.create(
            tournament=target_tournament,
            slot_size=self.slot_size,
            max_teams=self.max_teams,
            min_team_size=self.min_team_size,
            max_team_size=self.max_team_size,
            registration_mode=self.registration_mode,
            waitlist_enabled=self.waitlist_enabled,
            current_registrations=0  # New tournament starts with 0
        )
    
    def to_dict(self) -> dict:
        """Convert capacity to dictionary for API/serialization"""
        return {
            'slot_size': self.slot_size,
            'max_teams': self.max_teams,
            'min_team_size': self.min_team_size,
            'max_team_size': self.max_team_size,
            'registration_mode': self.registration_mode,
            'registration_mode_display': self.get_registration_mode_display(),
            'waitlist_enabled': self.waitlist_enabled,
            'current_registrations': self.current_registrations,
            'is_full': self.is_full,
            'available_slots': self.available_slots,
            'progress_percent': self.registration_progress_percent,
            'can_accept_registrations': self.can_accept_registrations,
            'is_solo': self.is_solo_tournament,
            'requires_full_squad': self.requires_full_squad,
        }
