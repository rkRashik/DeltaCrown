"""
StaffPermissionChecker - Centralized permission checking for tournament staff.

Phase 2 consolidation: Uses Phase 7 ``TournamentStaffAssignment`` + ``StaffRole``
(capability-based JSON permissions) as the primary source.  Falls back to the
legacy ``TournamentStaff`` model when the Phase 7 assignment doesn't exist.
"""

import logging
from django.contrib.auth.models import User
from apps.tournaments.models import Tournament

logger = logging.getLogger(__name__)


def _get_phase7_assignment(tournament_id: int, user_id: int):
    """Return the active Phase 7 TournamentStaffAssignment or None."""
    try:
        from apps.tournaments.models.staffing import TournamentStaffAssignment
        return (
            TournamentStaffAssignment.objects
            .select_related('role')
            .filter(tournament_id=tournament_id, user_id=user_id, is_active=True)
            .first()
        )
    except Exception:
        return None


def _get_legacy_staff(tournament_id: int, user_id: int):
    """Return the active legacy TournamentStaff record or None."""
    try:
        from apps.tournaments.models import TournamentStaff
        return (
            TournamentStaff.objects
            .select_related('role')
            .filter(tournament_id=tournament_id, user_id=user_id, is_active=True)
            .first()
        )
    except Exception:
        return None


class StaffPermissionChecker:
    """
    Permission checker for tournament staff actions.
    
    Checks Phase 7 ``TournamentStaffAssignment`` first (capability-based JSON
    permissions via ``StaffRole.capabilities``).  Falls back to legacy
    ``TournamentStaff`` if no Phase 7 record exists.
    
    Usage:
        checker = StaffPermissionChecker(tournament, user)
        if checker.can_manage_registrations():
            # Allow action
        
        # Or check multiple permissions
        if checker.has_any(['manage_registrations', 'view_registrations']):
            # Allow action
    """
    
    def __init__(self, tournament: Tournament, user: User):
        self.tournament = tournament
        self.user = user
        self._staff = None          # legacy TournamentStaff
        self._assignment = None     # Phase 7 TournamentStaffAssignment
        self._permissions = None
        self._loaded = False
    
    def _load(self):
        """Lazy-load staff records (Phase 7 first, legacy fallback)."""
        if self._loaded:
            return
        self._loaded = True
        self._assignment = _get_phase7_assignment(self.tournament.id, self.user.id)
        if self._assignment is None:
            self._staff = _get_legacy_staff(self.tournament.id, self.user.id)
    
    @property
    def staff(self):
        """Lazy load staff record (legacy)"""
        self._load()
        return self._staff
    
    @property
    def assignment(self):
        """Lazy load Phase 7 staff assignment"""
        self._load()
        return self._assignment
    
    @property
    def permissions(self):
        """Get all permissions for this staff member."""
        if self._permissions is not None:
            return self._permissions
        
        if self.is_organizer():
            # Organizers have ALL permissions
            self._permissions = [
                'manage_registrations', 'approve_payments', 'manage_brackets',
                'resolve_disputes', 'make_announcements', 'edit_settings',
                'manage_staff', 'view_all',
            ]
        elif self.assignment and self.assignment.role:
            # Phase 7: capabilities JSON → permission list
            caps = self.assignment.role.capabilities or {}
            self._permissions = [k for k, v in caps.items() if v]
        elif self.staff and self.staff.role:
            # Legacy fallback
            self._permissions = getattr(self.staff.role, 'permissions', None) or []
        else:
            self._permissions = []
        return self._permissions
    
    def is_organizer(self) -> bool:
        """Check if user is the tournament organizer"""
        return self.tournament.organizer_id == self.user.id
    
    def is_superuser(self) -> bool:
        """Check if user is superuser/staff"""
        return self.user.is_superuser or self.user.is_staff
    
    def is_staff_member(self) -> bool:
        """Check if user is an active staff member (Phase 7 or legacy)"""
        return self.assignment is not None or self.staff is not None
    
    def can_access_organizer_hub(self) -> bool:
        """Check if user can access organizer hub at all"""
        return self.is_organizer() or self.is_superuser() or self.is_staff_member()
    
    def has_permission(self, permission_code: str) -> bool:
        """Check if user has specific permission"""
        if self.is_organizer() or self.is_superuser():
            return True
        return permission_code in self.permissions
    
    def has_any(self, permission_codes: list) -> bool:
        """Check if user has ANY of the specified permissions"""
        if self.is_organizer() or self.is_superuser():
            return True
        return any(code in self.permissions for code in permission_codes)
    
    def has_all(self, permission_codes: list) -> bool:
        """Check if user has ALL of the specified permissions"""
        if self.is_organizer() or self.is_superuser():
            return True
        return all(code in self.permissions for code in permission_codes)
    
    # Specific permission checks
    def can_manage_registrations(self) -> bool:
        """Can approve/reject registrations"""
        return self.has_permission('manage_registrations')
    
    def can_approve_payments(self) -> bool:
        """Can verify and approve payment proofs"""
        return self.has_permission('approve_payments')
    
    def can_manage_brackets(self) -> bool:
        """Can create, edit, finalize brackets"""
        return self.has_permission('manage_brackets')
    
    def can_resolve_disputes(self) -> bool:
        """Can respond to and resolve disputes"""
        return self.has_permission('resolve_disputes')
    
    def can_make_announcements(self) -> bool:
        """Can create tournament announcements"""
        return self.has_permission('make_announcements')
    
    def can_edit_settings(self) -> bool:
        """Can edit tournament settings"""
        return self.has_permission('edit_settings')
    
    def can_manage_staff(self) -> bool:
        """Can add/remove staff and assign roles"""
        return self.has_permission('manage_staff')
    
    def can_view_analytics(self) -> bool:
        """Can view tournament analytics"""
        return self.has_permission('view_all')
