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


# TournamentStaff model removed in Phase 1 cleanup.
# Use TournamentStaffAssignment (staffing.py) instead.


# Staff permission checker utility
class StaffPermissionChecker:
    """
    Utility class for checking tournament staff permissions.
    Uses TournamentStaffAssignment exclusively (legacy TournamentStaff removed).
    """

    def __init__(self, tournament, user):
        self.tournament = tournament
        self.user = user
        self._assignments = None

    def _get_assignments(self):
        if self._assignments is None:
            from apps.tournaments.models.staffing import TournamentStaffAssignment
            self._assignments = TournamentStaffAssignment.objects.filter(
                tournament=self.tournament,
                user=self.user,
                is_active=True
            ).select_related('role')
        return self._assignments

    def is_organizer(self):
        return self.tournament.organizer_id == self.user.id

    def is_staff(self):
        return self._get_assignments().exists()

    def has_permission(self, permission_name):
        if self.is_organizer():
            return True
        assignments = self._get_assignments()
        return any(getattr(a.role, permission_name, False) for a in assignments)

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
