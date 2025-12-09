"""
Staff and Referee Role Models - Phase 7, Epic 7.3

Tournament-level staff and referee assignment models.

Architecture:
- Staff roles with capability-based permissions
- Per-tournament staff assignments
- Per-match referee assignments
- Load tracking for referees

Reference: ROADMAP_AND_EPICS_PART_4 Phase 7, Epic 7.3
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class StaffRole(models.Model):
    """
    Global staff role definition with capability-based permissions.
    
    Roles define what staff members can do in tournaments.
    Examples: Admin, Moderator, Referee, Streamer, Observer
    
    Reference: Phase 7, Epic 7.3 - Staff Role System
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Display name of the role (e.g., 'Tournament Referee')"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Short identifier (e.g., 'referee', 'admin')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of role responsibilities"
    )
    
    # Capability flags (soft permissions model)
    capabilities = models.JSONField(
        default=dict,
        help_text="Capability flags as JSON (e.g., {'can_schedule': true, 'can_resolve_disputes': true})"
    )
    
    # Referee-specific flag
    is_referee_role = models.BooleanField(
        default=False,
        help_text="True if this role can be assigned to referee matches"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournament_staff_roles'
        ordering = ['name']
        verbose_name = 'Staff Role'
        verbose_name_plural = 'Staff Roles'
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def has_capability(self, capability_name: str) -> bool:
        """Check if role has a specific capability."""
        return self.capabilities.get(capability_name, False)
    
    def clean(self):
        """Validate model fields."""
        super().clean()
        
        if self.is_referee_role and not self.has_capability('can_referee_matches'):
            raise ValidationError(
                "Referee roles must have 'can_referee_matches' capability"
            )


class TournamentStaffAssignment(models.Model):
    """
    Assignment of a user to a staff role for a specific tournament.
    
    Links users to tournaments with specific roles and permissions.
    
    Reference: Phase 7, Epic 7.3 - Staff Assignment
    """
    
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='epic73_staff_assignments',
        help_text="Tournament this assignment belongs to"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='epic73_tournament_staff_assignments',
        help_text="User assigned to staff role"
    )
    role = models.ForeignKey(
        StaffRole,
        on_delete=models.PROTECT,
        related_name='assignments',
        help_text="Staff role assigned"
    )
    
    # Assignment status
    is_active = models.BooleanField(
        default=True,
        help_text="False if assignment has been revoked"
    )
    
    # Optional stage-specific assignment
    stage = models.ForeignKey(
        'tournaments.TournamentStage',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='epic73_staff_assignments',
        help_text="Optional: limit assignment to specific stage"
    )
    
    # Assignment metadata
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='epic73_staff_assignments_made',
        help_text="Organizer who made this assignment"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about this assignment"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournament_staff_assignments'
        unique_together = [
            ('tournament', 'user', 'role'),  # One assignment per user+role per tournament
        ]
        indexes = [
            models.Index(fields=['tournament', 'is_active']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['role', 'is_active']),
        ]
        ordering = ['-assigned_at']
        verbose_name = 'Tournament Staff Assignment'
        verbose_name_plural = 'Tournament Staff Assignments'
    
    def __str__(self):
        return f"{self.user.username} - {self.role.name} on {self.tournament.name}"
    
    def clean(self):
        """Validate assignment."""
        super().clean()
        
        # If stage is specified, ensure it belongs to tournament
        if self.stage and self.stage.tournament_id != self.tournament_id:
            raise ValidationError(
                f"Stage {self.stage.name} does not belong to tournament {self.tournament.name}"
            )


class MatchRefereeAssignment(models.Model):
    """
    Assignment of a referee to a specific match.
    
    Links staff assignments (with referee role) to matches.
    
    Reference: Phase 7, Epic 7.3 - Match Referee Assignment
    """
    
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='epic73_referee_assignments',
        help_text="Match being refereed"
    )
    staff_assignment = models.ForeignKey(
        TournamentStaffAssignment,
        on_delete=models.CASCADE,
        related_name='epic73_match_assignments',
        help_text="Staff assignment (must have referee role)"
    )
    
    # Referee priority
    is_primary = models.BooleanField(
        default=True,
        help_text="True for primary referee, False for backup/secondary"
    )
    
    # Assignment metadata
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='epic73_referee_assignments_made',
        help_text="Organizer who assigned this referee"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about this referee assignment"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'match_referee_assignments'
        unique_together = [
            ('match', 'staff_assignment'),  # One assignment per match+staff
        ]
        indexes = [
            models.Index(fields=['match', 'is_primary']),
            models.Index(fields=['staff_assignment']),
        ]
        ordering = ['-is_primary', '-assigned_at']
        verbose_name = 'Match Referee Assignment'
        verbose_name_plural = 'Match Referee Assignments'
    
    def __str__(self):
        primary_label = "Primary" if self.is_primary else "Secondary"
        return f"{primary_label} Referee: {self.staff_assignment.user.username} for Match {self.match.id}"
    
    def clean(self):
        """Validate referee assignment."""
        super().clean()
        
        # Ensure staff assignment has referee role
        if not self.staff_assignment.role.is_referee_role:
            raise ValidationError(
                f"Staff assignment must have a referee role. "
                f"Current role: {self.staff_assignment.role.name}"
            )
        
        # Ensure staff assignment belongs to match's tournament
        if self.staff_assignment.tournament_id != self.match.tournament_id:
            raise ValidationError(
                "Staff assignment must be for the same tournament as the match"
            )
        
        # Ensure staff assignment is active
        if not self.staff_assignment.is_active:
            raise ValidationError(
                "Cannot assign inactive staff to matches"
            )
