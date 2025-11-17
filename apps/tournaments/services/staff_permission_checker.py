"""
StaffPermissionChecker - Centralized permission checking for tournament staff

Checks permissions based on TournamentStaff roles and their assigned permissions.
Used throughout organizer hub to gate actions.
"""

from django.contrib.auth.models import User
from apps.tournaments.models import Tournament, TournamentStaff


class StaffPermissionChecker:
    """
    Permission checker for tournament staff actions.
    
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
        self._staff = None
        self._permissions = None
        
    @property
    def staff(self):
        """Lazy load staff record"""
        if self._staff is None:
            try:
                self._staff = TournamentStaff.objects.select_related('role').get(
                    tournament=self.tournament,
                    user=self.user,
                    is_active=True
                )
            except TournamentStaff.DoesNotExist:
                self._staff = False
        return self._staff if self._staff is not False else None
    
    @property
    def permissions(self):
        """Get all permissions for this staff member"""
        if self._permissions is None:
            if self.is_organizer():
                # Organizers have ALL permissions
                self._permissions = [
                    'manage_registrations', 'approve_payments', 'manage_brackets',
                    'resolve_disputes', 'make_announcements', 'edit_settings',
                    'manage_staff', 'view_all'
                ]
            elif self.staff and self.staff.role:
                # Get permissions from role
                self._permissions = self.staff.role.permissions or []
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
        """Check if user is an active staff member"""
        return self.staff is not None
    
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
