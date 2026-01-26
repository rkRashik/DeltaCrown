"""
OrganizationService - Service layer for Organization operations (vNext system).

Organizations are professional entities that own multiple teams across games.
This service handles organization lifecycle, membership management, and
team ownership operations.

Performance Targets (p95 latency):
- Simple reads (get_organization): <50ms, ≤3 queries
- Complex reads (list_teams): <100ms, ≤5 queries
- Writes (create_organization): <100ms, ≤5 queries
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    ConflictError,
    OrganizationServiceError,
)


# ============================================================================
# DATA TRANSFER OBJECTS (DTOs)
# ============================================================================

@dataclass
class OrganizationInfo:
    """
    Display-ready organization metadata.
    
    Used by: user_profile (org cards), leaderboards (org rankings),
             tournaments (org team listings).
    """
    organization_id: int
    name: str
    slug: str
    logo_url: Optional[str]
    badge_url: Optional[str]
    is_verified: bool
    ceo_user_id: int
    ceo_username: str
    team_count: int
    created_date: str  # ISO 8601 format


@dataclass
class OrganizationMember:
    """
    Organization membership with role and permissions.
    
    Used by: organization dashboard, permission checks.
    """
    user_id: int
    username: str
    display_name: str
    role: str  # CEO, ADMIN, MANAGER, ANALYST, VIEWER
    permissions: List[str]
    joined_date: str  # ISO 8601 format


# ============================================================================
# ORGANIZATIONSERVICE - PUBLIC API
# ============================================================================

class OrganizationService:
    """
    Unified service layer for Organization operations.
    
    Organizations are vNext-only (no legacy equivalent). All methods
    query apps.organizations models exclusively.
    
    Thread Safety: All methods are thread-safe (no shared mutable state).
    """
    
    # ========================================================================
    # ORGANIZATION LIFECYCLE
    # ========================================================================
    
    @staticmethod
    def create_organization(
        *,
        name: str,
        ceo_user_id: int,
        slug: Optional[str] = None,
        logo: Optional[Any] = None,
        description: Optional[str] = None,
        website: Optional[str] = None,
        twitter: Optional[str] = None
    ) -> int:
        """
        Create a new professional organization.
        
        Args:
            name: Organization legal/brand name (e.g., 'SYNTAX', 'Cloud9 BD')
            ceo_user_id: User who will own/manage the organization
            slug: URL-safe identifier (auto-generated from name if omitted)
            logo: Organization logo file (optional)
            description: Organization bio/mission statement (optional)
            website: Official website URL (optional)
            twitter: Twitter handle without @ (optional)
        
        Returns:
            New organization ID (integer primary key)
        
        Raises:
            NotFoundError: If ceo_user_id does not exist
            ValidationError: If name is invalid (empty, too long, special chars)
            ConflictError: If slug or name already exists
            PermissionDeniedError: If user already owns an organization
        
        Performance Notes:
            - Target: <100ms (p95), ≤3 queries
            - Slug generation may require counter increment for uniqueness
            - Auto-creates OrganizationRanking via post_save signal (if configured)
        
        Security Notes:
            - User ownership validated (ceo_user_id must exist)
            - Prevents multiple organization ownership (one CEO per user)
            - Name/slug validated for injection attacks
        
        Business Rules:
            - One user can own max 1 organization (CEO role)
            - Organization name must be globally unique
            - Slug auto-generated if not provided (slugify + uniqueness check)
            - Verified badge granted manually by platform admins (separate flow)
        
        Example:
            org_id = OrganizationService.create_organization(
                name="SYNTAX Esports",
                ceo_user_id=request.user.id,
                description="Professional esports organization",
                website="https://syntax.gg"
            )
        """
        from django.db import transaction
        from django.contrib.auth import get_user_model
        from django.utils.text import slugify
        from apps.organizations.models import Organization, OrganizationMembership, OrganizationRanking
        
        User = get_user_model()
        
        # Validation: Name cannot be empty or too long
        if not name or not name.strip():
            raise ValidationError(
                message="Organization name cannot be empty",
                error_code="INVALID_ORG_NAME",
                details={"name": name}
            )
        
        if len(name) > 100:
            raise ValidationError(
                message="Organization name too long (max 100 characters)",
                error_code="INVALID_ORG_NAME",
                details={"name": name, "length": len(name)}
            )
        
        # Validation: Check if user exists (1 query)
        try:
            ceo = User.objects.get(id=ceo_user_id)
        except User.DoesNotExist:
            raise NotFoundError(
                message=f"User not found: id={ceo_user_id}",
                resource_type="User",
                resource_id=ceo_user_id
            )
        
        # Validation: Check if user already owns an organization (1 query)
        existing_ownership = OrganizationMembership.objects.filter(
            user=ceo,
            role='CEO'
        ).exists()
        
        if existing_ownership:
            raise PermissionDeniedError(
                message=f"User {ceo.username} already owns an organization",
                error_code="USER_ALREADY_CEO",
                details={"ceo_user_id": ceo_user_id, "username": ceo.username}
            )
        
        # Generate slug if not provided
        if not slug:
            slug = slugify(name)
        
        # Atomic transaction: Create org + CEO membership + ranking (1 query for create)
        with transaction.atomic():
            # Check slug uniqueness
            if Organization.objects.filter(slug=slug).exists():
                raise ConflictError(
                    message=f"Organization slug already exists: {slug}",
                    error_code="SLUG_CONFLICT",
                    details={"slug": slug, "name": name}
                )
            
            # Check name uniqueness
            if Organization.objects.filter(name=name).exists():
                raise ConflictError(
                    message=f"Organization name already exists: {name}",
                    error_code="NAME_CONFLICT",
                    details={"name": name}
                )
            
            # Create organization
            org = Organization.objects.create(
                name=name,
                slug=slug,
                ceo=ceo,
                logo=logo,
                description=description or "",
                website=website or "",
                twitter=twitter or ""
            )
            
            # Create CEO membership
            OrganizationMembership.objects.create(
                organization=org,
                user=ceo,
                role='CEO',
                permissions={}  # Full permissions implied by CEO role
            )
            
            # Create initial ranking (if OrganizationRanking model requires manual creation)
            # Note: If post_save signal auto-creates ranking, this is redundant
            try:
                OrganizationRanking.objects.get_or_create(
                    organization=org,
                    defaults={
                        'current_cp': 0,
                        'season_cp': 0,
                        'all_time_cp': 0,
                        'empire_score': 0,
                        'tier': 'UNRANKED'
                    }
                )
            except Exception:
                # If OrganizationRanking doesn't exist or is created by signal, ignore
                pass
        
        return org.id
    
    @staticmethod
    def get_organization(
        org_id: Optional[int] = None,
        org_slug: Optional[str] = None
    ) -> OrganizationInfo:
        """
        Retrieve organization metadata for display.
        
        Supports lookup by ID or slug (exactly one required).
        
        Args:
            org_id: Organization primary key (optional)
            org_slug: Organization URL slug (optional)
        
        Returns:
            OrganizationInfo DTO with all display fields
        
        Raises:
            ValidationError: If both or neither org_id and org_slug provided
            NotFoundError: If organization does not exist (error_code='ORG_NOT_FOUND')
        
        Performance Notes:
            - Target: <50ms (p95), ≤1-2 queries
            - Uses select_related('ceo') to prevent N+1
            - team_count computed via annotate() (efficient)
        
        Example:
            org = OrganizationService.get_organization(org_id=42)
            template_context['org_name'] = org.name
        """
        from django.db.models import Count, Q
        from apps.organizations.models import Organization
        
        # Validation: Exactly one identifier required
        if (org_id is None and org_slug is None) or (org_id is not None and org_slug is not None):
            raise ValidationError(
                message="Exactly one of org_id or org_slug must be provided",
                error_code="INVALID_LOOKUP_PARAMS",
                details={"org_id_provided": org_id is not None, "org_slug_provided": org_slug is not None}
            )
        
        # Build lookup query (1 query with select_related + annotate)
        try:
            lookup = Q(id=org_id) if org_id is not None else Q(slug=org_slug)
            org = (
                Organization.objects
                .select_related('ceo')  # Prevent N+1 for CEO username
                .annotate(
                    total_team_count=Count(
                        'teams',
                        filter=Q(teams__status='ACTIVE', teams__is_temporary=False)
                    )
                )
                .get(lookup)
            )
        except Organization.DoesNotExist:
            identifier = f"id={org_id}" if org_id is not None else f"slug={org_slug}"
            raise NotFoundError(
                message=f"Organization not found: {identifier}",
                resource_type="Organization",
                resource_id=org_id or org_slug
            )
        
        # Build DTO (all metadata in memory, no additional queries)
        return OrganizationInfo(
            organization_id=org.id,
            name=org.name,
            slug=org.slug,
            logo_url=org.logo.url if org.logo else None,
            badge_url=org.badge.url if org.badge else None,
            is_verified=org.is_verified,
            ceo_user_id=org.ceo.id,
            ceo_username=org.ceo.username,
            team_count=org.total_team_count,
            created_date=org.created_at.isoformat()
        )
    
    @staticmethod
    def update_organization(
        organization_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        website: Optional[str] = None,
        twitter: Optional[str] = None,
        logo: Optional[Any] = None,
        banner: Optional[Any] = None,
        enforce_brand: Optional[bool] = None,
        revenue_split_config: Optional[Dict[str, float]] = None
    ) -> None:
        """
        Update organization profile fields.
        
        Only provided fields are updated (omitted fields unchanged).
        
        Args:
            organization_id: Organization primary key
            name: New organization name (optional)
            description: New bio/mission statement (optional)
            website: New website URL (optional)
            twitter: New Twitter handle (optional)
            logo: New logo file (optional)
            banner: New banner file (optional)
            enforce_brand: Force teams to use org logo (optional)
            revenue_split_config: Prize distribution percentages (optional)
        
        Raises:
            NotFoundError: If organization_id does not exist
            ValidationError: If any field value is invalid
            ConflictError: If new name already exists
        
        Performance Notes:
            - Target: <100ms (p95), ≤3 queries
            - Only updates provided fields (no full model reload)
            - Image uploads may take longer (file processing async)
        
        Example:
            OrganizationService.update_organization(
                organization_id=42,
                description="Updated mission statement",
                enforce_brand=True
            )
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    # ========================================================================
    # MEMBERSHIP MANAGEMENT
    # ========================================================================
    
    @staticmethod
    def add_member(
        organization_id: int,
        *,
        user_id: int,
        role: str,
        added_by_user_id: int
    ) -> None:
        """
        Add a user to organization with specified role.
        
        Roles:
        - CEO: Full control (auto-assigned at creation, cannot add manually)
        - ADMIN: Can add/remove members, assign roles
        - MANAGER: Can manage teams, register tournaments
        - ANALYST: Read-only access to org data
        - VIEWER: Read-only access to public org info
        
        Args:
            organization_id: Organization primary key
            user_id: User to add as member
            role: Organization role (ADMIN, MANAGER, ANALYST, VIEWER)
            added_by_user_id: User performing the addition (for audit log)
        
        Raises:
            NotFoundError: If organization_id or user_id does not exist
            ValidationError: If role is invalid or CEO role specified
            ConflictError: If user already member of this organization
            PermissionDeniedError: If added_by_user_id lacks permission
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Permission check queries organization membership (indexed)
            - Creates TeamActivityLog entry for audit (1 additional query)
        
        Example:
            OrganizationService.add_member(
                organization_id=42,
                user_id=123,
                role='MANAGER',
                added_by_user_id=request.user.id
            )
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    @staticmethod
    def remove_member(
        organization_id: int,
        *,
        user_id: int,
        removed_by_user_id: int
    ) -> None:
        """
        Remove a user from organization membership.
        
        Args:
            organization_id: Organization primary key
            user_id: User to remove from organization
            removed_by_user_id: User performing the removal (for audit log)
        
        Raises:
            NotFoundError: If organization_id or user_id does not exist
            ValidationError: If attempting to remove CEO
            PermissionDeniedError: If removed_by_user_id lacks permission
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Permission check queries organization membership
            - Soft-delete (sets status=REMOVED, preserves history)
        
        Business Rules:
            - Cannot remove CEO (must transfer ownership first)
            - Removed members lose access to all org teams
            - Membership record preserved for audit trail
        
        Example:
            OrganizationService.remove_member(
                organization_id=42,
                user_id=123,
                removed_by_user_id=request.user.id
            )
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    @staticmethod
    def transfer_ownership(
        organization_id: int,
        *,
        new_ceo_user_id: int,
        current_ceo_user_id: int
    ) -> None:
        """
        Transfer organization ownership (CEO role) to another user.
        
        Args:
            organization_id: Organization primary key
            new_ceo_user_id: User to become new CEO
            current_ceo_user_id: Current CEO (for verification)
        
        Raises:
            NotFoundError: If organization_id or new_ceo_user_id does not exist
            ValidationError: If new_ceo_user_id is already CEO
            PermissionDeniedError: If current_ceo_user_id is not actual CEO
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Updates organization.ceo field
            - Updates OrganizationMembership roles (old CEO → ADMIN, new CEO assigned)
        
        Business Rules:
            - Only current CEO can transfer ownership
            - New CEO must be existing organization member (or added automatically)
            - Previous CEO becomes ADMIN (not removed)
        
        Example:
            OrganizationService.transfer_ownership(
                organization_id=42,
                new_ceo_user_id=456,
                current_ceo_user_id=request.user.id
            )
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    # ========================================================================
    # TEAM MANAGEMENT
    # ========================================================================
    
    @staticmethod
    def list_organization_teams(
        organization_id: int,
        *,
        status: str = "ACTIVE"
    ) -> List[int]:
        """
        Retrieve all team IDs owned by organization.
        
        Args:
            organization_id: Organization primary key
            status: Team status filter (ACTIVE, DELETED, SUSPENDED, DISBANDED, ALL)
        
        Returns:
            List of team IDs (use TeamService.get_team_identity() for details)
        
        Raises:
            NotFoundError: If organization_id does not exist
            ValidationError: If status is invalid
        
        Performance Notes:
            - Target: <50ms (p95), ≤2 queries
            - Returns IDs only (consumers fetch details as needed)
            - Filtered by status (indexed query)
        
        Example:
            team_ids = OrganizationService.list_organization_teams(org_id=42)
            teams = [TeamService.get_team_identity(tid) for tid in team_ids]
        """
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
    
    @staticmethod
    def get_organization_members(
        organization_id: int,
        *,
        role: Optional[str] = None
    ) -> List[OrganizationMember]:
        """
        Retrieve organization membership roster.
        
        Args:
            organization_id: Organization primary key
            role: Filter by role (CEO, ADMIN, MANAGER, ANALYST, VIEWER) or None for all
        
        Returns:
            List of OrganizationMember DTOs sorted by role hierarchy
        
        Raises:
            NotFoundError: If organization_id does not exist
            ValidationError: If role is invalid
        
        Performance Notes:
            - Target: <100ms (p95), ≤3 queries
            - Uses select_related('user') to prevent N+1
            - Sorted by role hierarchy then join date
        
        Example:
            members = OrganizationService.get_organization_members(org_id=42)
            for member in members:
                print(f"{member.username} ({member.role})")
        """
        from apps.organizations.models import Organization, OrganizationMembership
        
        # Verify organization exists
        if not Organization.objects.filter(id=organization_id).exists():
            raise NotFoundError(
                message=f"Organization with ID {organization_id} not found",
                resource_type="Organization",
                resource_id=organization_id
            )
        
        # Validate role filter if provided
        valid_roles = ['CEO', 'MANAGER', 'SCOUT', 'ANALYST']
        if role and role not in valid_roles:
            raise ValidationError(
                message=f"Invalid role filter: {role}",
                error_code="INVALID_ROLE",
                details={"role": role, "valid_roles": valid_roles}
            )
        
        # Build query (1-2 queries with select_related)
        queryset = (
            OrganizationMembership.objects
            .filter(organization_id=organization_id)
            .select_related('user')  # Prevent N+1
            .order_by('joined_at')
        )
        
        if role:
            queryset = queryset.filter(role=role)
        
        # Role hierarchy for sorting (CEO first, then managers, etc.)
        role_order = {'CEO': 1, 'MANAGER': 2, 'SCOUT': 3, 'ANALYST': 4}
        
        # Build DTOs
        members = []
        for membership in queryset:
            member = OrganizationMember(
                user_id=membership.user.id,
                username=membership.user.username,
                display_name=getattr(membership.user, 'display_name', membership.user.username),
                role=membership.role,
                permissions=list(membership.permissions.keys()) if membership.permissions else [],
                joined_date=membership.joined_at.isoformat()
            )
            members.append(member)
        
        # Sort by role hierarchy, then by join date
        members.sort(key=lambda m: (role_order.get(m.role, 99), m.joined_date))
        
        return members
    
    # ========================================================================
    # ORGANIZATION MANAGEMENT (P3-T5)
    # ========================================================================
    
    @staticmethod
    def get_organization_detail(
        *,
        org_id: Optional[int] = None,
        org_slug: Optional[str] = None,
        include_members: bool = True,
        include_teams: bool = True
    ) -> Dict[str, Any]:
        """
        Get complete organization details with members and teams.
        
        Args:
            org_id: Organization primary key (optional)
            org_slug: Organization URL slug (optional)
            include_members: Include member list (default: True)
            include_teams: Include team list (default: True)
        
        Returns:
            Dict with org info, members, and teams
        
        Raises:
            ValidationError: If both or neither identifiers provided
            NotFoundError: If organization does not exist
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Uses select_related/prefetch_related to prevent N+1
        
        Example:
            data = OrganizationService.get_organization_detail(org_slug='syntax')
            # Returns: {'org': {...}, 'members': [...], 'teams': [...]}
        """
        from django.db.models import Count, Q, Prefetch
        from apps.organizations.models import Organization, OrganizationMembership, Team
        
        # Validation: Exactly one identifier required
        if (org_id is None and org_slug is None) or (org_id is not None and org_slug is not None):
            raise ValidationError(
                message="Exactly one of org_id or org_slug must be provided",
                error_code="INVALID_LOOKUP_PARAMS",
                details={"org_id_provided": org_id is not None, "org_slug_provided": org_slug is not None}
            )
        
        # Build base query
        lookup = Q(id=org_id) if org_id is not None else Q(slug=org_slug)
        queryset = Organization.objects.select_related('ceo')
        
        # Optimize member/team loading with prefetch
        if include_members:
            queryset = queryset.prefetch_related(
                Prefetch(
                    'staff_memberships',
                    queryset=OrganizationMembership.objects.select_related('user').order_by('joined_at')
                )
            )
        
        if include_teams:
            queryset = queryset.prefetch_related(
                Prefetch(
                    'teams',
                    queryset=Team.objects.filter(status='ACTIVE', is_temporary=False).select_related('game')
                )
            )
        
        # Execute query
        try:
            org = queryset.get(lookup)
        except Organization.DoesNotExist:
            identifier = f"id={org_id}" if org_id is not None else f"slug={org_slug}"
            raise NotFoundError(
                message=f"Organization not found: {identifier}",
                resource_type="Organization",
                resource_id=org_id or org_slug
            )
        
        # Build response data
        result = {
            'org': {
                'id': org.id,
                'name': org.name,
                'slug': org.slug,
                'logo_url': org.logo.url if org.logo else None,
                'banner_url': org.banner.url if org.banner else None,
                'is_verified': org.is_verified,
                'ceo_id': org.ceo.id,
                'ceo_username': org.ceo.username,
                'description': org.description or '',
                'website': org.website or '',
                'twitter': org.twitter or '',
                'primary_color': getattr(org, 'primary_color', '#667eea'),
                'tagline': getattr(org, 'tagline', ''),
                'created_at': org.created_at.isoformat(),
            },
            'members': [],
            'teams': []
        }
        
        # Add members if requested
        if include_members:
            role_order = {'CEO': 1, 'MANAGER': 2, 'SCOUT': 3, 'ANALYST': 4}
            members_list = list(org.staff_memberships.all())
            members_list.sort(key=lambda m: (role_order.get(m.role, 99), m.joined_at))
            
            result['members'] = [{
                'id': m.id,
                'user_id': m.user.id,
                'username': m.user.username,
                'display_name': getattr(m.user, 'display_name', m.user.username),
                'role': m.role,
                'permissions': list(m.permissions.keys()) if m.permissions else [],
                'joined_at': m.joined_at.isoformat(),
                'status': 'active'
            } for m in members_list]
        
        # Add teams if requested
        if include_teams:
            result['teams'] = [{
                'id': t.id,
                'name': t.name,
                'slug': t.slug,
                'tag': t.tag,
                'game_name': t.game.name if t.game else 'Unknown',
                'game_slug': t.game.slug if t.game else '',
                'region': t.region,
                'status': t.status,
                'member_count': t.members.filter(status='ACTIVE').count(),
                'created_at': t.created_at.isoformat()
            } for t in org.teams.all()]
        
        return result
    
    @staticmethod
    def add_organization_member(
        *,
        organization_id: int,
        user_id: int,
        role: str,
        added_by_user_id: int
    ) -> int:
        """
        Add a new member to an organization.
        
        Args:
            organization_id: Organization primary key
            user_id: User to add as member
            role: Organization role (MANAGER, SCOUT, ANALYST)
            added_by_user_id: User performing the action (permission check)
        
        Returns:
            New membership ID
        
        Raises:
            NotFoundError: If organization or user not found
            PermissionDeniedError: If added_by_user lacks permission
            ValidationError: If role invalid or user already member
            ConflictError: If user already a member
        
        Performance Notes:
            - Target: <100ms (p95), ≤5 queries
            - Uses transaction.atomic for safety
        
        Example:
            membership_id = OrganizationService.add_organization_member(
                organization_id=42,
                user_id=123,
                role='MANAGER',
                added_by_user_id=1  # CEO
            )
        """
        from django.db import transaction
        from django.contrib.auth import get_user_model
        from apps.organizations.models import Organization, OrganizationMembership
        
        User = get_user_model()
        
        # Validate role
        valid_roles = ['MANAGER', 'SCOUT', 'ANALYST']
        if role not in valid_roles:
            raise ValidationError(
                message=f"Invalid role: {role}. Must be one of: {valid_roles}",
                error_code="INVALID_ROLE",
                details={"role": role, "valid_roles": valid_roles}
            )
        
        with transaction.atomic():
            # Verify organization exists
            try:
                org = Organization.objects.select_for_update().get(id=organization_id)
            except Organization.DoesNotExist:
                raise NotFoundError(
                    message=f"Organization with ID {organization_id} not found",
                    resource_type="Organization",
                    resource_id=organization_id
                )
            
            # Permission check: CEO or MANAGER can add members
            added_by_membership = OrganizationMembership.objects.filter(
                organization_id=organization_id,
                user_id=added_by_user_id
            ).first()
            
            if not added_by_membership or added_by_membership.role not in ['CEO', 'MANAGER']:
                raise PermissionDeniedError(
                    message="Only CEO or Managers can add organization members",
                    error_code="INSUFFICIENT_PERMISSIONS",
                    details={"required_role": "CEO or MANAGER"}
                )
            
            # Verify user exists
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise NotFoundError(
                    message=f"User with ID {user_id} not found",
                    error_code="USER_NOT_FOUND",
                    details={"user_id": user_id}
                )
            
            # Check if user already member
            if OrganizationMembership.objects.filter(organization_id=organization_id, user_id=user_id).exists():
                raise ConflictError(
                    message=f"User {user.username} is already a member of this organization",
                    error_code="ALREADY_MEMBER",
                    details={"user_id": user_id, "username": user.username}
                )
            
            # Create membership
            membership = OrganizationMembership.objects.create(
                organization=org,
                user=user,
                role=role,
                permissions={}
            )
            
            return membership.id
    
    @staticmethod
    def update_member_role(
        *,
        membership_id: int,
        new_role: str,
        updated_by_user_id: int
    ) -> None:
        """
        Update an organization member's role.
        
        Args:
            membership_id: OrganizationMembership primary key
            new_role: New role (MANAGER, SCOUT, ANALYST)
            updated_by_user_id: User performing the action (permission check)
        
        Raises:
            NotFoundError: If membership not found
            PermissionDeniedError: If updater lacks permission or trying to demote CEO
            ValidationError: If new_role invalid
        
        Performance Notes:
            - Target: <100ms (p95), ≤3 queries
            - Uses transaction.atomic for safety
        
        Business Rules:
            - CEO cannot be demoted (only platform admins can change CEO)
            - Only CEO or Managers can change roles
            - Managers cannot demote other Managers (only CEO can)
        
        Example:
            OrganizationService.update_member_role(
                membership_id=123,
                new_role='SCOUT',
                updated_by_user_id=1  # CEO
            )
        """
        from django.db import transaction
        from apps.organizations.models import OrganizationMembership
        
        # Validate new role
        valid_roles = ['MANAGER', 'SCOUT', 'ANALYST']
        if new_role not in valid_roles:
            raise ValidationError(
                message=f"Invalid role: {new_role}. Must be one of: {valid_roles}",
                error_code="INVALID_ROLE",
                details={"new_role": new_role, "valid_roles": valid_roles}
            )
        
        with transaction.atomic():
            # Get membership being modified
            try:
                membership = OrganizationMembership.objects.select_for_update().select_related('organization').get(id=membership_id)
            except OrganizationMembership.DoesNotExist:
                raise NotFoundError(
                    message=f"Membership with ID {membership_id} not found",
                    error_code="MEMBERSHIP_NOT_FOUND",
                    details={"membership_id": membership_id}
                )
            
            # HARD RULE: Cannot change CEO role
            if membership.role == 'CEO':
                raise PermissionDeniedError(
                    message="Cannot change CEO role. Contact platform administrators.",
                    error_code="CANNOT_CHANGE_CEO",
                    details={"membership_id": membership_id}
                )
            
            # Get updater's membership
            updater_membership = OrganizationMembership.objects.filter(
                organization=membership.organization,
                user_id=updated_by_user_id
            ).first()
            
            if not updater_membership:
                raise PermissionDeniedError(
                    message="You are not a member of this organization",
                    error_code="NOT_ORGANIZATION_MEMBER",
                    details={"user_id": updated_by_user_id}
                )
            
            # Permission check: Only CEO or Managers can change roles
            if updater_membership.role not in ['CEO', 'MANAGER']:
                raise PermissionDeniedError(
                    message="Only CEO or Managers can change member roles",
                    error_code="INSUFFICIENT_PERMISSIONS",
                    details={"required_role": "CEO or MANAGER"}
                )
            
            # BUSINESS RULE: Managers can't change other Manager roles (only CEO can)
            if membership.role == 'MANAGER' and updater_membership.role != 'CEO':
                raise PermissionDeniedError(
                    message="Only the CEO can change Manager roles",
                    error_code="CANNOT_CHANGE_MANAGER_ROLE",
                    details={"required_role": "CEO"}
                )
            
            # Update role
            membership.role = new_role
            membership.save(update_fields=['role'])
    
    @staticmethod
    def remove_organization_member(
        *,
        membership_id: int,
        removed_by_user_id: int
    ) -> None:
        """
        Remove a member from an organization.
        
        Args:
            membership_id: OrganizationMembership primary key
            removed_by_user_id: User performing the action (permission check)
        
        Raises:
            NotFoundError: If membership not found
            PermissionDeniedError: If remover lacks permission or trying to remove CEO
        
        Performance Notes:
            - Target: <100ms (p95), ≤3 queries
            - Uses transaction.atomic for safety
        
        Business Rules:
            - CEO cannot be removed (only platform admins)
            - Only CEO or Managers can remove members
            - Managers cannot remove other Managers (only CEO can)
        
        Example:
            OrganizationService.remove_organization_member(
                membership_id=123,
                removed_by_user_id=1  # CEO
            )
        """
        from django.db import transaction
        from apps.organizations.models import OrganizationMembership
        
        with transaction.atomic():
            # Get membership being removed
            try:
                membership = OrganizationMembership.objects.select_for_update().select_related('organization').get(id=membership_id)
            except OrganizationMembership.DoesNotExist:
                raise NotFoundError(
                    message=f"Membership with ID {membership_id} not found",
                    error_code="MEMBERSHIP_NOT_FOUND",
                    details={"membership_id": membership_id}
                )
            
            # HARD RULE: Cannot remove CEO
            if membership.role == 'CEO':
                raise PermissionDeniedError(
                    message="Cannot remove CEO. Contact platform administrators.",
                    error_code="CANNOT_REMOVE_CEO",
                    details={"membership_id": membership_id}
                )
            
            # Get remover's membership
            remover_membership = OrganizationMembership.objects.filter(
                organization=membership.organization,
                user_id=removed_by_user_id
            ).first()
            
            if not remover_membership:
                raise PermissionDeniedError(
                    message="You are not a member of this organization",
                    error_code="NOT_ORGANIZATION_MEMBER",
                    details={"user_id": removed_by_user_id}
                )
            
            # Permission check: Only CEO or Managers can remove members
            if remover_membership.role not in ['CEO', 'MANAGER']:
                raise PermissionDeniedError(
                    message="Only CEO or Managers can remove members",
                    error_code="INSUFFICIENT_PERMISSIONS",
                    details={"required_role": "CEO or MANAGER"}
                )
            
            # BUSINESS RULE: Managers can't remove other Managers (only CEO can)
            if membership.role == 'MANAGER' and remover_membership.role != 'CEO':
                raise PermissionDeniedError(
                    message="Only the CEO can remove Managers",
                    error_code="CANNOT_REMOVE_MANAGER",
                    details={"required_role": "CEO"}
                )
            
            # Delete membership
            membership.delete()
    
    @staticmethod
    def update_organization_settings(
        *,
        organization_id: int,
        updated_by_user_id: int,
        logo_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        primary_color: Optional[str] = None,
        tagline: Optional[str] = None
    ) -> None:
        """
        Update organization branding settings.
        
        Args:
            organization_id: Organization primary key
            updated_by_user_id: User performing the action (permission check)
            logo_url: New logo URL (optional)
            banner_url: New banner URL (optional)
            primary_color: New primary color (hex format, optional)
            tagline: New tagline (optional)
        
        Raises:
            NotFoundError: If organization not found
            PermissionDeniedError: If updater lacks permission
            ValidationError: If color format invalid
        
        Performance Notes:
            - Target: <100ms (p95), ≤3 queries
            - Uses transaction.atomic for safety
        
        Business Rules:
            - Only CEO or Managers can update settings
        
        Example:
            OrganizationService.update_organization_settings(
                organization_id=42,
                updated_by_user_id=1,
                primary_color='#ff5733',
                tagline='Victory Awaits'
            )
        """
        from django.db import transaction
        from apps.organizations.models import Organization, OrganizationMembership
        import re
        
        # Validate color format if provided
        if primary_color and not re.match(r'^#[0-9a-fA-F]{6}$', primary_color):
            raise ValidationError(
                message="Invalid color format. Must be hex format like #ff5733",
                error_code="INVALID_COLOR_FORMAT",
                details={"primary_color": primary_color}
            )
        
        with transaction.atomic():
            # Verify organization exists
            try:
                org = Organization.objects.select_for_update().get(id=organization_id)
            except Organization.DoesNotExist:
                raise NotFoundError(
                    message=f"Organization with ID {organization_id} not found",
                    resource_type="Organization",
                    resource_id=organization_id
                )
            
            # Permission check: CEO or MANAGER can update settings
            updater_membership = OrganizationMembership.objects.filter(
                organization_id=organization_id,
                user_id=updated_by_user_id
            ).first()
            
            if not updater_membership or updater_membership.role not in ['CEO', 'MANAGER']:
                raise PermissionDeniedError(
                    message="Only CEO or Managers can update organization settings",
                    error_code="INSUFFICIENT_PERMISSIONS",
                    details={"required_role": "CEO or MANAGER"}
                )
            
            # Update fields (only if provided)
            updated_fields = []
            
            if logo_url is not None:
                org.logo_url = logo_url
                updated_fields.append('logo_url')
            
            if banner_url is not None:
                org.banner_url = banner_url
                updated_fields.append('banner_url')
            
            if primary_color is not None:
                org.primary_color = primary_color
                updated_fields.append('primary_color')
            
            if tagline is not None:
                org.tagline = tagline
                updated_fields.append('tagline')
            
            if updated_fields:
                org.save(update_fields=updated_fields)
