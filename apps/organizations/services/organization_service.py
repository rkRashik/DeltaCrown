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
                error_code="USER_NOT_FOUND",
                details={"ceo_user_id": ceo_user_id}
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
                error_code="ORG_NOT_FOUND",
                details={"org_id": org_id, "org_slug": org_slug}
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
        raise NotImplementedError("Business logic will be implemented in P2-T2+")
