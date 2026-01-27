"""
UI Views for vNext Organization and Team management.

This package provides modular views for the vNext system:
- hub.py: Hub/landing page views
- team.py: Team creation, detail, and invites
- org.py: Organization detail and management

Feature Flag Protection:
- All vNext UI views check feature flags before rendering
- If flags disabled, redirect appropriately

Security:
- All views require authentication where needed
- Permission checks for organization/team access
"""

# Import public views for easy access
from .hub import vnext_hub
from .team import team_create, team_detail, team_invites
from .org import organization_detail, org_create, org_hub, org_control_plane
from .org_directory import org_directory

__all__ = [
    'vnext_hub',
    'team_create',
    'team_detail',
    'team_invites',
    'organization_detail',
    'org_create',
    'org_hub',
    'org_control_plane',
    'org_directory',
]
