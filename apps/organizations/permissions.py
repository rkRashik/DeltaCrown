"""
Organization permission system - Single Source of Truth.

This module provides centralized permission checking for all organization-related views.
All views (Detail, Hub, Control Plane) must use these functions to avoid permission drift.
"""

from django.contrib.auth.models import User
from typing import Tuple


def get_org_role(user: User, organization) -> str:
    """
    Determine user's role within an organization.
    
    Returns one of:
    - 'STAFF': Platform staff (site-wide admin)
    - 'CEO': Organization CEO (owner)
    - 'ADMIN': Organization admin staff member
    - 'MANAGER': Organization manager staff member
    - 'NONE': No special role (public user)
    
    This is the single source of truth for role determination.
    All views must use this function instead of duplicating logic.
    """
    # Platform staff bypass all org-level checks
    if user.is_staff:
        return 'STAFF'
    
    # Check if user is the CEO
    if organization.ceo_id == user.id:
        return 'CEO'
    
    # Check staff membership role
    membership = organization.staff_memberships.filter(user=user).first()
    if membership:
        return membership.role  # 'ADMIN' or 'MANAGER'
    
    return 'NONE'


def can_access_control_plane(role: str) -> bool:
    """
    Check if a role can access the Control Plane.
    
    Control Plane access is granted to:
    - Platform staff
    - Organization CEO
    - Organization ADMIN
    - Organization MANAGER
    """
    return role in ['STAFF', 'CEO', 'ADMIN', 'MANAGER']


def can_manage_org(role: str) -> bool:
    """
    Check if a role can manage general organization settings.
    
    General management includes:
    - Identity (name, description)
    - Branding (logo, colors)
    - Teams (squad control)
    - Recruitment settings
    - Media integrations
    - Sponsors
    - Notifications
    """
    return role in ['STAFF', 'CEO', 'ADMIN', 'MANAGER']


def can_view_financials(role: str) -> bool:
    """
    Check if a role can view financial information.
    
    Financial access restricted to:
    - Platform staff (for support)
    - Organization CEO
    - Organization ADMIN
    
    Managers cannot view financials.
    """
    return role in ['STAFF', 'CEO', 'ADMIN']


def can_manage_staff(role: str) -> bool:
    """
    Check if a role can add/remove staff members.
    
    Staff management restricted to:
    - Platform staff (for support)
    - Organization CEO
    
    Admins and Managers cannot modify staff roster.
    """
    return role in ['STAFF', 'CEO']


def can_modify_governance(role: str) -> bool:
    """
    Check if a role can modify governance settings (2FA, security policies).
    
    Governance modification restricted to:
    - Platform staff
    - Organization CEO
    """
    return role in ['STAFF', 'CEO']


def can_execute_terminal_actions(role: str) -> bool:
    """
    Check if a role can execute terminal actions (dissolve org, delete data).
    
    Terminal actions restricted to:
    - Organization CEO only
    
    Not even platform staff should have this power (use Django admin for that).
    """
    return role == 'CEO'


def get_permission_context(user: User, organization) -> dict:
    """
    Get complete permission context for templates.
    
    Returns a dictionary with:
    - viewer_role: str (STAFF/CEO/ADMIN/MANAGER/NONE)
    - can_access_control_plane: bool
    - can_manage_org: bool
    - can_view_financials: bool
    - can_manage_staff: bool
    - can_modify_governance: bool
    - can_execute_terminal_actions: bool
    
    Usage in views:
        context = get_permission_context(request.user, organization)
        context['organization'] = organization
        return render(request, 'template.html', context)
    """
    role = get_org_role(user, organization)
    
    return {
        'viewer_role': role,
        'can_access_control_plane': can_access_control_plane(role),
        'can_manage_org': can_manage_org(role),
        'can_view_financials': can_view_financials(role),
        'can_manage_staff': can_manage_staff(role),
        'can_modify_governance': can_modify_governance(role),
        'can_execute_terminal_actions': can_execute_terminal_actions(role),
    }


# ============================================================================
# PHASE 8: TEAM PERMISSION SYSTEM
# ============================================================================

def get_team_role(user: User, team) -> str:
    """
    Determine user's role within a team.
    
    Returns one of:
    - 'CREATOR': User who created the team
    - 'MANAGER': Team manager
    - 'COACH': Team coach
    - 'MEMBER': Team member
    - 'NONE': Not a team member
    """
    if not user or not user.is_authenticated:
        return 'NONE'
    
    # Check if user created the team
    if hasattr(team, 'created_by') and team.created_by == user:
        return 'CREATOR'
    
    # Check team membership
    from apps.organizations.models import TeamMembership
    membership = TeamMembership.objects.filter(
        team=team,
        user=user,
        status='ACTIVE'
    ).first()
    
    if membership:
        return membership.role
    
    return 'NONE'


def can_view_team(user: User, team) -> bool:
    """
    Check if user can view team.
    
    Public teams: Anyone
    Private teams: Members only
    Unlisted teams: Anyone with link
    """
    if user and user.is_authenticated and user.is_superuser:
        return True
    
    if team.visibility == 'PUBLIC':
        return True
    
    if team.visibility == 'UNLISTED':
        return True
    
    # Private teams require membership
    if user and user.is_authenticated:
        team_role = get_team_role(user, team)
        if team_role != 'NONE':
            return True
        
        # Org members can view org teams
        org_role = get_org_role(user, team.organization)
        if org_role != 'NONE':
            return True
    
    return False


def can_manage_team(user: User, team) -> bool:
    """
    Check if user can manage team.
    
    Management hierarchy:
    1. Org CEO (full control)
    2. Org MANAGER (can manage all org teams)
    3. Team Creator
    4. Team Manager/Coach
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    # Check org-level permissions
    org_role = get_org_role(user, team.organization)
    if org_role in ['CEO', 'MANAGER', 'ADMIN']:
        return True
    
    # Check team-level permissions
    team_role = get_team_role(user, team)
    if team_role in ['CREATOR', 'MANAGER', 'COACH']:
        return True
    
    return False


def can_create_team_in_org(user: User, organization) -> bool:
    """Check if user can create teams in organization."""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    role = get_org_role(user, organization)
    return role in ['CEO', 'MANAGER', 'ADMIN']

