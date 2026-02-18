"""
Tournament Staff Management Models (LEGACY).

DEPRECATED — Phase 2 Service Consolidation, Task 2.6.

All new code should use the Phase 7 models in ``staffing.py``:
- ``StaffRole`` (JSON-based capabilities, replaces TournamentStaffRole)
- ``TournamentStaffAssignment`` (replaces TournamentStaff)
- ``MatchRefereeAssignment`` (new, no legacy equivalent)

These legacy models are kept for backward-compatibility with:
- Existing database rows / migrations
- StaffPermissionChecker fallback path
- Admin site registrations

Source: Documents/Reports/TOURNAMENT_SYSTEM_IMPROVEMENTS_PLAN.md Section 3.1
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()


class TournamentStaffRole(models.Model):
    """
    DEPRECATED: Use StaffRole (staffing.py) instead.
    This legacy model uses rigid boolean permission fields.
    Phase 7 StaffRole uses flexible JSON capabilities.
    Kept for backward-compat. Migration target: Phase 1+.
    
    Defines staff roles with granular permissions for tournament management.
    
    Roles define what actions staff members can perform and what data they can access.
    Each role has specific permission flags and access levels for PII/payment data.
    
    Default Roles (created via migration):
    - Participant Reviewer: Reviews registrations
    - Payment Verifier: Verifies payment proofs
    - Bracket Manager: Manages brackets and scheduling
    - Scorekeeper: Enters match scores
    - Dispute Resolver: Handles match disputes
    - Support Staff: Provides participant support
    - Social Media Manager: Manages announcements
    - Tournament Admin: Full access to all features
    """
    
    # Basic information
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text='Role name (e.g., "Participant Reviewer")'
    )
    slug = models.SlugField(
        max_length=60,
        unique=True,
        db_index=True,
        help_text='URL-safe identifier'
    )
    description = models.TextField(
        help_text='Detailed description of this role and its responsibilities'
    )
    
    # Tournament Management Permissions
    can_review_participants = models.BooleanField(
        default=False,
        help_text='Can review and approve/reject participant registrations'
    )
    can_verify_payments = models.BooleanField(
        default=False,
        help_text='Can verify payment proofs and mark payments as confirmed'
    )
    can_manage_brackets = models.BooleanField(
        default=False,
        help_text='Can create, edit, and manage tournament brackets'
    )
    can_manage_matches = models.BooleanField(
        default=False,
        help_text='Can schedule, reschedule, and configure matches'
    )
    can_enter_scores = models.BooleanField(
        default=False,
        help_text='Can enter and verify match scores and results'
    )
    can_handle_disputes = models.BooleanField(
        default=False,
        help_text='Can view, investigate, and resolve match disputes'
    )
    can_send_notifications = models.BooleanField(
        default=False,
        help_text='Can send notifications and announcements to participants'
    )
    can_manage_social_media = models.BooleanField(
        default=False,
        help_text='Can post updates and manage tournament social media'
    )
    can_access_support = models.BooleanField(
        default=False,
        help_text='Can access support tickets and communicate with participants'
    )
    can_modify_tournament = models.BooleanField(
        default=False,
        help_text='Can edit tournament settings and configuration (admin only)'
    )
    
    # Data Access Permissions (for PII compliance)
    can_view_pii = models.BooleanField(
        default=False,
        help_text='Can view personally identifiable information (names, emails, phone numbers)'
    )
    can_view_payment_proofs = models.BooleanField(
        default=False,
        help_text='Can view uploaded payment proof images and bank details'
    )
    can_export_data = models.BooleanField(
        default=False,
        help_text='Can export participant data to CSV/Excel'
    )
    
    # Role metadata
    is_system_role = models.BooleanField(
        default=False,
        help_text='System-defined role (cannot be deleted or significantly modified)'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this role is available for assignment'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournaments_staff_role'
        verbose_name = 'Tournament Staff Role'
        verbose_name_plural = 'Tournament Staff Roles'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_permissions_summary(self):
        """Return a list of granted permissions for display."""
        permissions = []
        permission_fields = [
            ('can_review_participants', 'Review Participants'),
            ('can_verify_payments', 'Verify Payments'),
            ('can_manage_brackets', 'Manage Brackets'),
            ('can_manage_matches', 'Manage Matches'),
            ('can_enter_scores', 'Enter Scores'),
            ('can_handle_disputes', 'Handle Disputes'),
            ('can_send_notifications', 'Send Notifications'),
            ('can_manage_social_media', 'Manage Social Media'),
            ('can_access_support', 'Access Support'),
            ('can_modify_tournament', 'Modify Tournament'),
            ('can_view_pii', 'View PII'),
            ('can_view_payment_proofs', 'View Payment Proofs'),
            ('can_export_data', 'Export Data'),
        ]
        
        for field, label in permission_fields:
            if getattr(self, field):
                permissions.append(label)
        
        return permissions
    
    def has_any_permission(self):
        """Check if this role has at least one permission granted."""
        return any([
            self.can_review_participants,
            self.can_verify_payments,
            self.can_manage_brackets,
            self.can_manage_matches,
            self.can_enter_scores,
            self.can_handle_disputes,
            self.can_send_notifications,
            self.can_manage_social_media,
            self.can_access_support,
            self.can_modify_tournament,
        ])


class TournamentStaff(models.Model):
    """
    DEPRECATED: Use ``TournamentStaffAssignment`` (staffing.py) instead.
    
    Assigns staff members to tournaments with specific roles.
    Kept for backward-compatibility with existing data and migrations.
    New code should use TournamentStaffAssignment with StaffRole capabilities.
    """
    
    # Relations
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='staff_assignments',
        help_text='Tournament this staff member is assigned to'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tournament_staff_roles',
        help_text='User assigned as staff'
    )
    role = models.ForeignKey(
        TournamentStaffRole,
        on_delete=models.PROTECT,
        related_name='staff_assignments',
        help_text='Role and permissions for this staff member'
    )
    
    # Assignment details
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this staff assignment is currently active'
    )
    notes = models.TextField(
        blank=True,
        help_text='Internal notes about this staff assignment (not visible to staff member)'
    )
    
    # Assignment tracking
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When this staff member was assigned'
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_assignments_made',
        help_text='Organizer who assigned this staff member'
    )
    
    # Deactivation tracking
    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this assignment was deactivated'
    )
    deactivated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_assignments_deactivated',
        help_text='Who deactivated this assignment'
    )
    
    class Meta:
        db_table = 'tournaments_staff_assignment'
        verbose_name = 'Tournament Staff Assignment'
        verbose_name_plural = 'Tournament Staff Assignments'
        ordering = ['tournament', 'role__name', 'user__username']
        unique_together = [('tournament', 'user', 'role')]
        indexes = [
            models.Index(fields=['tournament', 'is_active']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['tournament', 'user']),
        ]
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        return f"{status} {self.user.username} - {self.role.name} @ {self.tournament.name}"
    
    def clean(self):
        """Validate staff assignment."""
        super().clean()
        
        # Prevent assigning tournament organizer as staff (they already have full access)
        if self.tournament.organizer_id == self.user_id:
            raise ValidationError({
                'user': 'Tournament organizer cannot be assigned as staff (already has full access).'
            })
        
        # Warn if role has no permissions (but allow it)
        if not self.role.has_any_permission():
            raise ValidationError({
                'role': f'Role "{self.role.name}" has no permissions assigned. Please configure role permissions first.'
            })
    
    def deactivate(self, deactivated_by=None):
        """
        Deactivate this staff assignment.
        
        Args:
            deactivated_by: User who is deactivating this assignment
        """
        from django.utils import timezone
        
        self.is_active = False
        self.deactivated_at = timezone.now()
        if deactivated_by:
            self.deactivated_by = deactivated_by
        self.save(update_fields=['is_active', 'deactivated_at', 'deactivated_by'])
    
    def reactivate(self):
        """Reactivate this staff assignment."""
        self.is_active = True
        self.deactivated_at = None
        self.deactivated_by = None
        self.save(update_fields=['is_active', 'deactivated_at', 'deactivated_by'])
    
    # Permission check methods (delegate to role)
    def can_review_participants(self):
        return self.is_active and self.role.can_review_participants
    
    def can_verify_payments(self):
        return self.is_active and self.role.can_verify_payments
    
    def can_manage_brackets(self):
        return self.is_active and self.role.can_manage_brackets
    
    def can_manage_matches(self):
        return self.is_active and self.role.can_manage_matches
    
    def can_enter_scores(self):
        return self.is_active and self.role.can_enter_scores
    
    def can_handle_disputes(self):
        return self.is_active and self.role.can_handle_disputes
    
    def can_send_notifications(self):
        return self.is_active and self.role.can_send_notifications
    
    def can_manage_social_media(self):
        return self.is_active and self.role.can_manage_social_media
    
    def can_access_support(self):
        return self.is_active and self.role.can_access_support
    
    def can_modify_tournament(self):
        return self.is_active and self.role.can_modify_tournament
    
    def can_view_pii(self):
        return self.is_active and self.role.can_view_pii
    
    def can_view_payment_proofs(self):
        return self.is_active and self.role.can_view_payment_proofs
    
    def can_export_data(self):
        return self.is_active and self.role.can_export_data


# Staff permission checker utility
class StaffPermissionChecker:
    """
    Utility class for checking tournament staff permissions.
    
    Usage:
        checker = StaffPermissionChecker(tournament, user)
        if checker.can_verify_payments():
            # Allow payment verification
    """
    
    def __init__(self, tournament, user):
        self.tournament = tournament
        self.user = user
        self._assignments = None
    
    def _get_assignments(self):
        """Lazy-load active staff assignments for this user."""
        if self._assignments is None:
            self._assignments = TournamentStaff.objects.filter(
                tournament=self.tournament,
                user=self.user,
                is_active=True
            ).select_related('role')
        return self._assignments
    
    def is_organizer(self):
        """Check if user is the tournament organizer."""
        return self.tournament.organizer_id == self.user.id
    
    def is_staff(self):
        """Check if user has any active staff assignment."""
        return self._get_assignments().exists()
    
    def has_permission(self, permission_name):
        """
        Check if user has a specific permission.
        
        Args:
            permission_name: Name of permission field (e.g., 'can_verify_payments')
        
        Returns:
            True if user is organizer or has any role with this permission
        """
        if self.is_organizer():
            return True
        
        assignments = self._get_assignments()
        return any(getattr(a.role, permission_name, False) for a in assignments)
    
    # Convenience methods for common permission checks
    def can_review_participants(self):
        return self.has_permission('can_review_participants')
    
    def can_verify_payments(self):
        return self.has_permission('can_verify_payments')
    
    def can_manage_brackets(self):
        return self.has_permission('can_manage_brackets')
    
    def can_manage_matches(self):
        return self.has_permission('can_manage_matches')
    
    def can_enter_scores(self):
        return self.has_permission('can_enter_scores')
    
    def can_handle_disputes(self):
        return self.has_permission('can_handle_disputes')
    
    def can_send_notifications(self):
        return self.has_permission('can_send_notifications')
    
    def can_manage_social_media(self):
        return self.has_permission('can_manage_social_media')
    
    def can_access_support(self):
        return self.has_permission('can_access_support')
    
    def can_modify_tournament(self):
        return self.has_permission('can_modify_tournament')
    
    def can_view_pii(self):
        return self.has_permission('can_view_pii')
    
    def can_view_payment_proofs(self):
        return self.has_permission('can_view_payment_proofs')
    
    def can_export_data(self):
        return self.has_permission('can_export_data')
    
    def get_roles(self):
        """Get all active roles for this user in this tournament."""
        return [assignment.role for assignment in self._get_assignments()]
    
    def get_permissions_summary(self):
        """Get a set of all permission names granted to this user."""
        if self.is_organizer():
            return {'organizer', 'all_permissions'}
        
        permissions = set()
        for assignment in self._get_assignments():
            permissions.update(assignment.role.get_permissions_summary())
        
        return permissions
